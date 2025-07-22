from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, status
from loguru import logger
from tiacore_lib.config import get_settings
from tiacore_lib.handlers.dependency_handler import require_permission_in_context
from tortoise.expressions import Q

from app.database.models import (
    Bot,
    Chat,
    ChatSchedule,
    Prompt,
    TargetChat,
)
from app.handlers.rabbit_handler import publish_schedule_event
from app.pydantic_models.schedule_schemas import (
    ScheduleCreateSchema,
    ScheduleEditSchema,
    ScheduleListSchema,
    ScheduleResponseSchema,
    ScheduleSchema,
    ScheduleShortSchema,
    schedule_filter_params,
)
from app.scheduler.scheduler import list_scheduled_jobs
from app.utils.validate_helpers import check_company_access, validate_exists

schedule_router = APIRouter()


@schedule_router.post("/add", response_model=ScheduleResponseSchema, status_code=status.HTTP_201_CREATED)
async def create_schedule(
    data: ScheduleCreateSchema = Body(...),
    context=Depends(require_permission_in_context("add_schedule")),
    settings=Depends(get_settings),
):
    check_company_access(data.company_id, context)
    await validate_exists(Chat, data.chat_id, "Чат")
    await validate_exists(Bot, data.bot_id, "Бот")
    await validate_exists(Prompt, data.prompt_id, "Промпт")

    try:
        schedule_data = data.model_dump(exclude={"target_chats"}, exclude_unset=True)
        schedule = await ChatSchedule.create(**schedule_data)

        if data.target_chats:
            for chat_id in data.target_chats:
                await TargetChat.create(schedule=schedule, chat_id=chat_id)
        await publish_schedule_event(schedule.id, settings=settings, action="add")

        return ScheduleResponseSchema(schedule_id=schedule.id)

    except Exception as e:
        logger.exception(f"Ошибка при создании расписания: {e}")
        raise HTTPException(status_code=500, detail="Ошибка сервера") from e


@schedule_router.patch("/{schedule_id}/toggle", status_code=status.HTTP_204_NO_CONTENT)
async def toggle_schedule(
    schedule_id: UUID,
    context=Depends(require_permission_in_context("toggle_schedule")),
    settings=Depends(get_settings),
):
    schedule = await ChatSchedule.get_or_none(id=schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Расписание не найдено")

    check_company_access(schedule.company_id, context)

    schedule.enabled = not schedule.enabled
    await schedule.save()
    if schedule.enabled:
        await publish_schedule_event(schedule_id, settings=settings, action="add")
    else:
        await publish_schedule_event(schedule_id, settings=settings, action="delete")


@schedule_router.patch("/{schedule_id}", response_model=ScheduleResponseSchema)
async def edit_schedule(
    schedule_id: UUID,
    data: ScheduleEditSchema = Body(...),
    context=Depends(require_permission_in_context("edit_schedule")),
    settings=Depends(get_settings),
):
    updated_data = data.model_dump(exclude_unset=True)
    updated_data.pop("target_chats", None)
    updated_data.pop("removed_chats", None)
    schedule = await ChatSchedule.get_or_none(id=schedule_id)
    if not schedule:
        logger.warning(f"Расписание {schedule_id} не найдено")
        raise HTTPException(status_code=404, detail="Расписание не найдено")
    check_company_access(schedule.company_id, context)
    await publish_schedule_event(schedule_id, settings=settings, action="delete")
    if not schedule:
        raise HTTPException(status_code=404, detail="Расписание не найдено")

    if "chat" in updated_data:
        await validate_exists(Chat, data.chat_id, "Чат")

    if "prompt" in updated_data:
        await validate_exists(Prompt, data.prompt_id, "Промпт")

    if "bot" in updated_data:
        await validate_exists(Bot, data.bot_id, "Бот")

    await schedule.update_from_dict(updated_data)
    await schedule.save()

    if schedule.enabled:
        await publish_schedule_event(schedule_id, settings=settings, action="add")
    logger.success(f"Расписание {schedule_id} успешно обновлено")
    if data.target_chats:
        # Привязываем чаты к расписанию
        for chat_id in data.target_chats:
            await validate_exists(Chat, chat_id, "Чат")

            await TargetChat.create(schedule=schedule, chat_id=chat_id)

    if data.removed_chats:
        for chat_id in data.removed_chats:
            await validate_exists(Chat, chat_id, "Чат")
            await TargetChat.filter(schedule=schedule, chat_id=chat_id).delete()
    list_scheduled_jobs()
    return ScheduleResponseSchema(schedule_id=schedule.id)


@schedule_router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule(
    schedule_id: UUID,
    context=Depends(require_permission_in_context("delete_schedule")),
    settings=Depends(get_settings),
):
    schedule = await ChatSchedule.get_or_none(id=schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Расписание не найдено")
    check_company_access(schedule.company_id, context)
    await TargetChat.filter(schedule=schedule).delete()
    await schedule.delete()
    logger.success(f"Расписание {schedule_id} удалено")
    await publish_schedule_event(schedule_id, settings=settings, action="delete")


@schedule_router.get(
    "/all",
    response_model=ScheduleListSchema,
    summary="Получение списка расписаний с фильтрацией",
)
async def get_schedules(
    filters: dict = Depends(schedule_filter_params),
    context=Depends(require_permission_in_context("get_all_schedules")),
):
    logger.info(f"Запрос на список расписаний: {filters}")

    query = Q()
    # Если не суперадмин — ограничить по company_id
    if not context["is_superadmin"]:
        if context.get("company_id"):
            query &= Q(company_id=context["company_id"])
        else:
            # Нет доступа ни к одной компании
            return ScheduleListSchema(total=0, schedules=[])

    if filters.get("company_id"):
        query &= Q(company_id=filters["company_id"])

    if filters.get("chat_id"):
        query &= Q(chat_id=filters["chat_id"])

    if filters.get("schedule_type"):
        query &= Q(schedule_type=filters["schedule_type"])

    if filters.get("enabled") is not None:
        query &= Q(enabled=filters["enabled"])

    order_by = f"{'-' if filters.get('order') == 'desc' else ''}{filters.get('sort_by', 'created_at')}"
    page = filters.get("page", 1)
    page_size = filters.get("page_size", 10)

    total_count = await ChatSchedule.filter(query).count()

    schedules = (
        await ChatSchedule.filter(query)
        .order_by(order_by)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .prefetch_related("chat", "prompt")
    )
    return ScheduleListSchema(
        total=total_count,
        schedules=[ScheduleShortSchema.model_validate(schedule) for schedule in schedules],
    )


@schedule_router.get("/{schedule_id}", response_model=ScheduleSchema)
async def get_schedule(schedule_id: UUID, context=Depends(require_permission_in_context("view_schedule"))):
    schedule = await ChatSchedule.get_or_none(id=schedule_id).prefetch_related("target_chats", "chat", "prompt", "bot")
    if not schedule:
        raise HTTPException(status_code=404, detail="Расписание не найдено")
    check_company_access(schedule.company_id, context)
    target_chat_ids = await TargetChat.filter(schedule=schedule).prefetch_related("chat").all()
    target_chats = [target_chat.chat.id for target_chat in target_chat_ids]
    schedule_dict = schedule.__dict__
    schedule_dict["target_chats"] = target_chats
    return ScheduleSchema.model_validate(schedule_dict)
