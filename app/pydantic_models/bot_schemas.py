import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import Query
from pydantic import BaseModel, Field


class BotEditSchema(BaseModel):
    comment: str = Field(...)


class RegisterBotRequest(BaseModel):
    token: str = Field(...)
    company_id: UUID = Field(...)
    comment: Optional[str] = Field(None)


class BotResponseModel(BaseModel):
    bot_id: int


class BotSchema(BaseModel):
    id: int = Field(..., alias="bot_id")
    bot_token: str
    bot_username: str
    bot_first_name: str
    company_id: UUID
    is_active: bool
    created_at: datetime.datetime
    comment: Optional[str] = None

    class Config:
        from_attributes = True
        populate_by_name = True


class BotListSchema(BaseModel):
    total: int
    bots: List[BotSchema]


def bot_filter_params(
    bot_username: Optional[str] = Query(None, description="Фильтр по названию бота"),
    bot_first_name: Optional[str] = Query(None, description="Фильтр по названию бота"),
    company_id: Optional[UUID] = Query(None, description="Фильтр по компании"),
    sort_by: Optional[str] = Query("bot_username", description="Поле сортировки"),
    order: Optional[str] = Query("asc", description="asc / desc"),
    page: Optional[int] = Query(1, ge=1),
    page_size: Optional[int] = Query(10, ge=1, le=100),
):
    return {
        "bot_username": bot_username,
        "bot_first_name": bot_first_name,
        "company_id": company_id,
        "sort_by": sort_by,
        "order": order,
        "page": page,
        "page_size": page_size,
    }
