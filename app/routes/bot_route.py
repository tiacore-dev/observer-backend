from fastapi import APIRouter, Body, Depends, HTTPException, Path, status
from loguru import logger
from tiacore_lib.handlers.dependency_handler import require_permission_in_context
from tortoise.expressions import Q

from app.database.models import Bot
from app.handlers.telegram_api_url_handlers import (
    delete_webhook,
    validate_token_and_register,
)
from app.pydantic_models.bot_schemas import (
    BotEditSchema,
    BotListSchema,
    BotSchema,
    RegisterBotRequest,
    bot_filter_params,
)
from app.utils.validate_helpers import check_company_access

bot_router = APIRouter()


@bot_router.post("/add", status_code=status.HTTP_201_CREATED)
async def add_bot(
    data: RegisterBotRequest = Body(...),
    context=Depends(require_permission_in_context("add_bot")),
):
    check_company_access(data.company_id, context)

    bot = await validate_token_and_register(data.token, data.company_id, data.comment)

    return {"bot_id": bot.id}


@bot_router.patch("/{bot_id}", summary="Изменение комментария к боту", status_code=status.HTTP_204_NO_CONTENT)
async def edit_bot(
    bot_id: int,
    data: BotEditSchema = Body(...),
    _=Depends(require_permission_in_context("edit_bot")),
):
    bot = await Bot.filter(id=bot_id).first()
    if not bot:
        raise HTTPException(status_code=404, detail="Бот не найден")
    bot.comment = data.comment
    await bot.save()


@bot_router.delete("/{bot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bot(bot_id: int, context=Depends(require_permission_in_context("delete_bot"))):
    bot = await Bot.filter(id=bot_id).first()
    if not bot:
        logger.warning(f"Бот {bot_id} не найден")
        raise HTTPException(status_code=404, detail="Бот не найден")
    check_company_access(bot.company_id, context)

    token = bot.bot_token
    await bot.delete()

    await delete_webhook(token)
    logger.success(f"Бот {bot_id} успешно удален")


@bot_router.get("/all", response_model=BotListSchema, summary="Получение списка ботов с фильтрацией")
async def get_bots(
    filters: dict = Depends(bot_filter_params),
    context=Depends(require_permission_in_context("get_all_bots")),
):
    logger.info(f"Запрос на список ботов: {filters}")

    query = Q()
    # Если не суперадмин — ограничить по company_id
    if not context["is_superadmin"]:
        if context.get("company_id"):
            query &= Q(company_id=context["company_id"])
        else:
            # Нет доступа ни к одной компании
            return BotListSchema(total=0, bots=[])
    if filters.get("company_id"):
        query &= Q(company_id=filters["company_id"])

    if filters.get("bot_username"):
        query &= Q(bot_username__icontains=filters["bot_username"])
    if filters.get("bot_first_name"):
        query &= Q(bot_first_name__icontains=filters["bot_first_name"])

    order_by = f"{'-' if filters.get('order') == 'desc' else ''}{filters.get('sort_by', 'bot_username')}"
    page = filters.get("page", 1)
    page_size = filters.get("page_size", 10)

    total_count = await Bot.filter(query).count()

    bots = (
        await Bot.filter(query)
        .order_by(order_by)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .values(
            "id",
            "bot_token",
            "bot_username",
            "bot_first_name",
            "company_id",
            "is_active",
            "created_at",
            "comment",
        )
    )

    return BotListSchema(
        total=total_count,
        bots=[BotSchema(**bot) for bot in bots],
    )


@bot_router.get("/{bot_id}", response_model=BotSchema, summary="Просмотр бота")
async def get_bot(
    bot_id: int = Path(..., title="ID бота", description="ID просматриваемого бота"),
    context=Depends(require_permission_in_context("view_bot")),
):
    logger.info(f"Запрос на просмотр бота: {bot_id}")
    bot = (
        await Bot.filter(id=bot_id)
        .first()
        .values(
            "id",
            "bot_token",
            "bot_username",
            "bot_first_name",
            "company_id",
            "is_active",
            "created_at",
            "comment",
        )
    )

    if not bot:
        logger.warning(f"Бот {bot_id} не найден")
        raise HTTPException(status_code=404, detail="Бот не найден")

    check_company_access(bot["company_id"], context)

    return BotSchema(**bot)
