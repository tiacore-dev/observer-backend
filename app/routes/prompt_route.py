from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Path, status
from loguru import logger
from tiacore_lib.handlers.dependency_handler import require_permission_in_context
from tortoise.expressions import Q

from app.database.models import Prompt
from app.pydantic_models.prompt_schemas import (
    PromptCreateSchema,
    PromptEditSchema,
    PromptListResponseSchema,
    PromptResponseSchema,
    PromptSchema,
    prompt_filter_params,
)
from app.utils.validate_helpers import check_company_access

prompt_router = APIRouter()


@prompt_router.post(
    "/add",
    response_model=PromptResponseSchema,
    summary="Добавление новой промпта",
    status_code=status.HTTP_201_CREATED,
)
async def add_prompt(
    data: PromptCreateSchema = Body(...),
    context=Depends(require_permission_in_context("add_prompt")),
):
    check_company_access(data.company_id, context)
    prompt = await Prompt.create(**data.model_dump(exclude_unset=True))
    if not prompt:
        logger.error("Не удалось создать промпту")
        raise HTTPException(status_code=500, detail="Не удалось создать промпту")

    logger.success(f"промпта {prompt.name} ({prompt.id}) успешно создана")
    return PromptResponseSchema(prompt_id=prompt.id)


@prompt_router.patch("/{prompt_id}", summary="Изменение промпта", status_code=status.HTTP_204_NO_CONTENT)
async def edit_prompt(
    prompt_id: UUID = Path(..., title="ID промпта", description="ID изменяемой промпта"),
    data: PromptEditSchema = Body(...),
    context=Depends(require_permission_in_context("edit_prompt")),
):
    logger.info(f"Обновление промпта {prompt_id}")

    prompt = await Prompt.filter(id=prompt_id).first()
    if not prompt:
        logger.warning(f"промпта {prompt_id} не найдена")
        raise HTTPException(status_code=404, detail="промпта не найдена")
    check_company_access(prompt.company_id, context)
    await prompt.update_from_dict(data.model_dump(exclude_unset=True))
    await prompt.save()


@prompt_router.delete("/{prompt_id}", summary="Удаление промпта", status_code=status.HTTP_204_NO_CONTENT)
async def delete_prompt(
    prompt_id: UUID = Path(..., title="ID промпта", description="ID удаляемой промпта"),
    context=Depends(require_permission_in_context("delete_prompt")),
):
    prompt = await Prompt.filter(id=prompt_id).first()
    if not prompt:
        logger.warning(f"промпта {prompt_id} не найдена")
        raise HTTPException(status_code=404, detail="промпта не найдена")
    check_company_access(prompt.company_id, context)
    await prompt.delete()


@prompt_router.get(
    "/all",
    response_model=PromptListResponseSchema,
    summary="Получение списка промптов с фильтрацией",
)
async def get_prompts(
    filters: dict = Depends(prompt_filter_params),
    context=Depends(require_permission_in_context("get_all_prompts")),
):
    query = Q()
    # Если не суперадмин — ограничить по company_id
    if not context["is_superadmin"]:
        if context.get("company_id"):
            query &= Q(company_id=context["company_id"])
        else:
            # Нет доступа ни к одной компании
            return PromptListResponseSchema(total=0, prompts=[])

    if filters.get("company_id"):
        query &= Q(company_id=filters["company_id"])

    if filters.get("prompt_name"):
        query &= Q(name__icontains=filters["prompt_name"])
    if filters.get("text"):
        query &= Q(text__icontains=filters["text"])

    order_by = f"{'-' if filters.get('order') == 'desc' else ''}{filters.get('sort_by', 'name')}"
    page = filters.get("page", 1)
    page_size = filters.get("page_size", 10)

    total_count = await Prompt.filter(query).count()

    prompts = await Prompt.filter(query).order_by(order_by).offset((page - 1) * page_size).limit(page_size)

    return PromptListResponseSchema(
        total=total_count,
        prompts=[PromptSchema.model_validate(prompt) for prompt in prompts],
    )


@prompt_router.get("/{prompt_id}", response_model=PromptSchema, summary="Просмотр промпта")
async def get_prompt(
    prompt_id: UUID = Path(..., title="ID промпта", description="ID просматриваемого промпта"),
    context=Depends(require_permission_in_context("view_prompt")),
):
    logger.info(f"Запрос на просмотр промпта: {prompt_id}")
    prompt = await Prompt.filter(id=prompt_id).first()

    if prompt is None:
        logger.warning(f"Промпт {prompt_id} не найден")
        raise HTTPException(status_code=404, detail="Промпт не найден")
    check_company_access(prompt.company_id, context)

    prompt_schema = PromptSchema.model_validate(prompt)

    logger.success(f"Промпт найден: {prompt_schema}")
    return prompt_schema
