import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import Query
from pydantic import Field
from tiacore_lib.pydantic_models.clean_model import CleanableBaseModel


class AnalysisCreateSchema(CleanableBaseModel):
    prompt_id: UUID = Field(...)
    chat_id: int = Field(...)
    date_from: int = Field(...)
    date_to: int = Field(...)
    company_id: UUID = Field(...)


class AnalysisResponseSchema(CleanableBaseModel):
    analysis_id: UUID


class AnalysisSchema(CleanableBaseModel):
    id: UUID = Field(..., alias="analysis_id")
    prompt_id: UUID
    chat_id: int
    result_text: str
    schedule_id: Optional[UUID] = None
    company_id: UUID
    created_at: datetime.datetime
    date_to: datetime.datetime
    date_from: datetime.datetime
    tokens_input: int
    tokens_output: int
    send_time: Optional[int]

    class Config:
        from_attributes = True
        populate_by_name = True


class AnalysisShortSchema(CleanableBaseModel):
    id: UUID = Field(..., alias="analysis_id")
    prompt_id: UUID
    chat_id: int
    company_id: UUID
    created_at: datetime.datetime
    tokens_input: int
    tokens_output: int

    class Config:
        from_attributes = True
        populate_by_name = True


class AnalysisListSchema(CleanableBaseModel):
    total: int
    analysis: List[AnalysisShortSchema]


def analysis_filter_params(
    company_id: Optional[UUID] = Query(None),
    chat_id: Optional[UUID] = Query(None),
    schedule_id: Optional[UUID] = Query(None),
    prompt_id: Optional[UUID] = Query(None),
    sort_by: Optional[str] = Query("created_at", description="Поле сортировки"),
    order: Optional[str] = Query("desc", description="asc / desc"),
    page: Optional[int] = Query(1, ge=1),
    page_size: Optional[int] = Query(10, ge=1, le=100),
):
    return {
        "company_id": company_id,
        "chat_id": chat_id,
        "schedule_id": schedule_id,
        "prompt_id": prompt_id,
        "sort_by": sort_by,
        "order": order,
        "page": page,
        "page_size": page_size,
    }
