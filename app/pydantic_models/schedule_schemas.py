from datetime import datetime, time
from typing import List, Optional
from uuid import UUID

from apscheduler.triggers.cron import CronTrigger
from fastapi import Query
from pydantic import BaseModel, Field, field_validator, model_validator

from app.database.models import ScheduleStrategy, ScheduleType, SendStrategy


class ScheduleCreateSchema(BaseModel):
    schedule_strategy: ScheduleStrategy
    name: Optional[str] = Field(None, alias="schedule_name")
    chat_id: Optional[int] = Field(None)
    prompt_id: Optional[UUID] = Field(None)
    schedule_type: ScheduleType = Field(...)

    notification_text: Optional[str] = Field(None)
    message_intro: Optional[str] = Field(None)

    interval_hours: Optional[int] = Field(None)
    interval_minutes: Optional[int] = Field(None)
    cron_expression: Optional[str] = Field(None)

    company_id: UUID = Field(...)
    target_chats: List[int] = Field(...)
    bot_id: int = Field(...)
    enabled: Optional[bool] = True

    description: Optional[str] = Field(None)

    send_strategy: Optional[SendStrategy] = Field(
        None,
        description="fixed — в указанное время, relative — через X минут после анализа",
    )
    time_to_send: Optional[time] = Field(None)
    send_after_minutes: Optional[int] = Field(None)

    @field_validator("cron_expression")
    @classmethod
    def validate_cron_expression(cls, value):
        if value:
            try:
                CronTrigger.from_crontab(value)
            except Exception as e:
                raise ValueError(f"Некорректное cron-выражение: {e}") from e
        return value

    @model_validator(mode="after")
    def validate_required_fields(self):
        # Валидация типа расписания
        match self.schedule_type:
            case ScheduleType.INTERVAL:
                if self.interval_hours is None and self.interval_minutes is None:
                    raise ValueError(
                        """Для типа interval необходимо указать 
                        interval_hours или interval_minutes"""
                    )

            case ScheduleType.CRON:
                if self.cron_expression is None:
                    raise ValueError("Для типа cron необходимо указать cron_expression")
        # Валидация стратегии отправки
        match self.send_strategy:
            case SendStrategy.FIXED:
                if not self.time_to_send:
                    raise ValueError("Для стратегии 'fixed' необходимо указать time_to_send")

            case SendStrategy.RELATIVE:
                if not self.send_after_minutes:
                    raise ValueError("Для стратегии 'relative' необходимо указать send_after_minutes")
        match self.schedule_strategy:
            case ScheduleStrategy.ANALYSIS:
                if not self.prompt_id and not self.chat_id and not self.send_strategy:
                    raise ValueError("Для анализа необходимы промпт и анализируемый чат")
            case ScheduleStrategy.NOTIFICATION:
                if not self.notification_text:
                    raise ValueError("Для уведомления обязательно указать текст сообщения")
        return self


class ScheduleEditSchema(BaseModel):
    name: Optional[str] = Field(None, alias="schedule_name")
    schedule_strategy: Optional[ScheduleStrategy] = Field(None)
    notification_text: Optional[str] = Field(None)

    chat_id: Optional[int] = Field(None)
    prompt_id: Optional[UUID] = Field(None)
    schedule_type: Optional[ScheduleType] = Field(None)

    message_intro: Optional[str] = Field(None)

    interval_hours: Optional[int] = Field(None)
    interval_minutes: Optional[int] = Field(None)

    cron_expression: Optional[str] = Field(None)

    target_chats: Optional[List[int]] = Field(None)
    removed_chats: Optional[List[int]] = Field(None)
    bot_id: Optional[int] = Field(None)
    enabled: Optional[bool] = Field(None)

    send_strategy: Optional[SendStrategy] = Field(None)
    time_to_send: Optional[time] = Field(None)
    send_after_minutes: Optional[int] = Field(None)

    company_id: Optional[UUID] = Field(None)

    description: Optional[str] = Field(None)

    @field_validator("cron_expression")
    @classmethod
    def validate_cron_expression(cls, value):
        if value:
            try:
                CronTrigger.from_crontab(value)
            except Exception as e:
                raise ValueError(f"Некорректное cron-выражение: {e}") from e
        return value


class ScheduleSchema(BaseModel):
    id: UUID = Field(..., alias="schedule_id")
    name: Optional[str] = Field(None, alias="schedule_name")
    schedule_strategy: ScheduleStrategy
    notification_text: Optional[str] = None
    chat_id: Optional[int] = Field(None)
    prompt_id: Optional[UUID] = Field(None)
    company_id: UUID
    schedule_type: ScheduleType

    message_intro: Optional[str] = Field(None)

    interval_hours: Optional[int] = None
    interval_minutes: Optional[int] = None

    cron_expression: Optional[str] = None

    enabled: bool
    last_run_at: Optional[datetime] = None
    created_at: datetime
    send_strategy: Optional[SendStrategy] = None
    time_to_send: Optional[time] = None
    send_after_minutes: Optional[int] = None

    description: Optional[str] = Field(None)

    bot_id: int

    target_chats: list[int]

    class Config:
        from_attributes = True
        populate_by_name = True


class ScheduleShortSchema(BaseModel):
    id: UUID = Field(..., alias="schedule_id")
    schedule_strategy: ScheduleStrategy
    prompt_id: Optional[UUID] = Field(None)
    schedule_type: ScheduleType
    enabled: bool
    company_id: UUID
    chat_id: Optional[int] = Field(None)
    created_at: datetime
    bot_id: int
    last_run_at: Optional[datetime] = None
    send_strategy: Optional[SendStrategy] = None

    class Config:
        from_attributes = True
        populate_by_name = True


class ScheduleListSchema(BaseModel):
    total: int
    schedules: List[ScheduleShortSchema]


class ScheduleResponseSchema(BaseModel):
    schedule_id: UUID


def schedule_filter_params(
    company_id: Optional[UUID] = Query(None),
    chat_id: Optional[UUID] = Query(None),
    schedule_type: Optional[ScheduleType] = Query(None),
    enabled: Optional[bool] = Query(None),
    sort_by: Optional[str] = Query("schedule_type", description="Поле сортировки"),
    order: Optional[str] = Query("asc", description="asc / desc"),
    page: Optional[int] = Query(1, ge=1),
    page_size: Optional[int] = Query(10, ge=1, le=100),
):
    return {
        "company": company_id,
        "chat": chat_id,
        "schedule_type": schedule_type,
        "enabled": enabled,
        "sort_by": sort_by,
        "order": order,
        "page": page,
        "page_size": page_size,
    }
