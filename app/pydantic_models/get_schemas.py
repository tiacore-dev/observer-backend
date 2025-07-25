import datetime
from typing import List, Optional

from fastapi import Query
from pydantic import BaseModel, Field


class AccountEditSchema(BaseModel):
    username: str = Field(..., alias="account_name")

    class Config:
        from_attributes = True
        populate_by_name = True


class ChatSchema(BaseModel):
    id: int = Field(..., alias="chat_id")
    name: Optional[str] = Field(None, alias="chat_name")
    created_at: datetime.datetime

    class Config:
        from_attributes = True
        populate_by_name = True


class ChatListSchema(BaseModel):
    total: int
    chats: List[ChatSchema]


def chat_filter_params(
    chat_name: Optional[str] = Query(None, description="Фильтр по названию бота"),
    bot_id: Optional[int] = Query(None, description="ID бота"),
    sort_by: Optional[str] = Query("name", description="Поле сортировки"),
    order: Optional[str] = Query("asc", description="asc / desc"),
    page: Optional[int] = Query(1, ge=1),
    page_size: Optional[int] = Query(10, ge=1, le=100),
):
    return {
        "chat_name": chat_name,
        "bot_id": bot_id,
        "sort_by": sort_by,
        "order": order,
        "page": page,
        "page_size": page_size,
    }


class AccountSchema(BaseModel):
    id: int = Field(..., alias="account_id")
    name: Optional[str] = Field(None, alias="account_name")
    username: Optional[str] = Field(None)
    created_at: datetime.datetime

    class Config:
        from_attributes = True
        populate_by_name = True


class AccountListSchema(BaseModel):
    total: int
    accounts: List[AccountSchema]


def account_filter_params(
    username: Optional[str] = Query(None, description="Фильтр по названию чата"),
    sort_by: Optional[str] = Query("username", description="Поле сортировки"),
    order: Optional[str] = Query("asc", description="asc / desc"),
    page: Optional[int] = Query(1, ge=1),
    page_size: Optional[int] = Query(10, ge=1, le=100),
):
    return {
        "username": username,
        "sort_by": sort_by,
        "order": order,
        "page": page,
        "page_size": page_size,
    }
