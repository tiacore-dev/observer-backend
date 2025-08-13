from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Path, status
from loguru import logger
from tiacore_lib.config import get_settings
from tiacore_lib.handlers.auth_handler import require_superadmin
from tiacore_lib.handlers.dependency_handler import require_permission_in_context
from tiacore_lib.utils.validate_helpers import validate_exists
from tortoise.expressions import Q

from app.database.models import AnalysingModelTypes, AnalysisResult, Chat, Message, Prompt
from app.pydantic_models.analysis_schema import (
    AnalysisCreateSchema,
    AnalysisListSchema,
    AnalysisReport,
    AnalysisReportFilters,
    AnalysisReportSchema,
    AnalysisResponseSchema,
    AnalysisSchema,
    AnalysisShortSchema,
    analysis_filter_params,
)
from app.utils.validate_helpers import check_company_access
from app.yandex_funcs.yandex_funcs import yandex_analyze

analysis_router = APIRouter()


@analysis_router.post(
    "/create",
    response_model=AnalysisResponseSchema,
    summary="Добавление новой промпта",
    status_code=status.HTTP_201_CREATED,
)
async def create_analysis(
    data: AnalysisCreateSchema = Body(...),
    context=Depends(require_permission_in_context("create_analysis")),
    settings=Depends(get_settings),
):
    logger.info(f"Создание анализа: {data.model_dump()}")
    check_company_access(data.company_id, context)
    try:
        await validate_exists(Prompt, data.prompt_id, "Prompt")
        await validate_exists(Chat, data.chat_id, "Chat")

        date_from_dt = datetime.fromtimestamp(data.date_from)
        date_to_dt = datetime.fromtimestamp(data.date_to)
        messages = (
            await Message.filter(
                chat_id=data.chat_id,
                timestamp__gte=date_from_dt,
                timestamp__lte=date_to_dt,
            )
            .order_by("timestamp")
            .prefetch_related("account", "chat")
            .all()
        )
        logger.debug(f"Найдено {len(messages)} сообщений.")
        result_text, tokens_input, tokens_output = await yandex_analyze(data.prompt_id, messages, settings)
        analysis = await AnalysisResult.create(
            result_text=result_text,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            prompt_id=data.prompt_id,
            chat_id=data.chat_id,
            date_from=data.date_from,
            date_to=data.date_to,
            company_id=data.company_id,
            analysing_model=AnalysingModelTypes.YA_GPT_PRO,
        )
        logger.success(f"Анализ успешно создан с id {analysis.id}")
        return AnalysisResponseSchema(analysis_id=analysis.id)
    except Exception as e:
        logger.exception("Ошибка при создании анализа")
        raise HTTPException(status_code=500, detail="Ошибка сервера") from e


@analysis_router.get(
    "/report",
    response_model=AnalysisReport,
    summary="Получение списка анализов с фильтрацией",
)
async def get_analyses_report(
    filters: AnalysisReportFilters = Depends(),
    _=Depends(require_superadmin),
):
    logger.info(f"Запрос отчета по компании: {filters}")

    analyses = (
        await AnalysisResult.filter(
            company_id=filters.company_id, created_at__lte=filters.date_to, created_at__gte=filters.date_from
        )
        .order_by("-created_at")
        .select_related("schedule", "prompt")
        .all()
    )

    total_tokens_input = sum((analysis.tokens_input or 0) for analysis in analyses)
    total_tokens_output = sum((analysis.tokens_output or 0) for analysis in analyses)
    logger.success(f"Найдено анализов: {len(analyses)}")
    return AnalysisReport(
        analyses=[
            AnalysisReportSchema(
                schedule_name=analysis.schedule.name
                if analysis.schedule and analysis.schedule.name
                else "Создано вручную или расписание не имеет имени",
                prompt_name=analysis.prompt.name,
                date=analysis.created_at,
                tokens_input=analysis.tokens_input,
                tokens_output=analysis.tokens_output,
            )
            for analysis in analyses
        ],
        total_tokens_input=total_tokens_input or 0,
        total_tokens_output=total_tokens_output or 0,
    )


@analysis_router.get(
    "/all",
    response_model=AnalysisListSchema,
    summary="Получение списка анализов с фильтрацией",
)
async def get_analyses(
    filters: dict = Depends(analysis_filter_params),
    context=Depends(require_permission_in_context("get_all_analyses")),
):
    logger.info(f"Запрос на список анализов: {filters}")

    query = Q()
    # Если не суперадмин — ограничить по company_id
    if not context["is_superadmin"]:
        if context.get("company_id"):
            query &= Q(company_id=context["company_id"])
        else:
            # Нет доступа ни к одной компании
            return AnalysisListSchema(total=0, analysis=[])

    if filters.get("analysing_model"):
        query &= Q(analysing_model=filters["analysing_model"])
    if filters.get("company_id"):
        query &= Q(company_id=filters["company_id"])
    if filters.get("chat_id"):
        query &= Q(chat_id=filters["chat_id"])
    if filters.get("schedule_id"):
        query &= Q(schedule_id=filters["schedule_id"])
    if filters.get("prompt_id"):
        query &= Q(prompt_id=filters["prompt_id"])

    order_by = f"{'-' if filters.get('order') == 'desc' else ''}{filters.get('sort_by', 'created_at')}"
    page = filters.get("page", 1)
    page_size = filters.get("page_size", 10)

    total_count = await AnalysisResult.filter(query).count()

    analyses = await AnalysisResult.filter(query).order_by(order_by).offset((page - 1) * page_size).limit(page_size)

    logger.success(f"Найдено анализов: {len(analyses)} из {total_count}")
    return AnalysisListSchema(
        total=total_count,
        analysis=[AnalysisShortSchema.model_validate(analisis) for analisis in analyses],
    )


@analysis_router.get("/{analysis_id}", response_model=AnalysisSchema, summary="Просмотр анализа")
async def get_analysis(
    analysis_id: UUID = Path(..., title="ID анализа", description="ID просматриваемого анализа"),
    context=Depends(require_permission_in_context("view_analysis")),
):
    logger.info(f"Запрос на просмотр анализа: {analysis_id}")

    analysis = await AnalysisResult.filter(id=analysis_id).first()

    if analysis is None:
        logger.warning(f"Анализ {analysis_id} не найден")
        raise HTTPException(status_code=404, detail="Анализ не найден")
    check_company_access(analysis.company_id, context)

    analysis_schema = AnalysisSchema.model_validate(analysis)

    logger.success(f"Анализ найден: {analysis_schema.id}")
    return analysis_schema
