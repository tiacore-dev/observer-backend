from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID

from fastapi import Query
from pydantic import BaseModel, Field

from app.database.models import AnalysingModelTypes

# Main schemas


class AnalysisCreateSchema(BaseModel):
    prompt_id: UUID = Field(...)
    chat_id: int = Field(...)
    date_from: int = Field(...)
    date_to: int = Field(...)
    company_id: UUID = Field(...)


class AnalysisResponseSchema(BaseModel):
    analysis_id: UUID


class AnalysisSchema(BaseModel):
    id: UUID = Field(..., alias="analysis_id")
    prompt_id: UUID
    chat_id: int
    result_text: str
    schedule_id: Optional[UUID] = None
    company_id: UUID
    created_at: datetime
    date_to: datetime
    date_from: datetime
    tokens_input: int
    tokens_output: int
    send_time: Optional[int]
    analysing_model: Optional[AnalysingModelTypes] = None

    class Config:
        from_attributes = True
        populate_by_name = True


class AnalysisShortSchema(BaseModel):
    id: UUID = Field(..., alias="analysis_id")
    prompt_id: UUID
    chat_id: int
    company_id: UUID
    created_at: datetime
    tokens_input: int
    tokens_output: int
    analysing_model: Optional[AnalysingModelTypes] = None

    class Config:
        from_attributes = True
        populate_by_name = True


class AnalysisListSchema(BaseModel):
    total: int
    analysis: List[AnalysisShortSchema]


def analysis_filter_params(
    company_id: Optional[UUID] = Query(None),
    chat_id: Optional[int] = Query(None),
    schedule_id: Optional[UUID] = Query(None),
    prompt_id: Optional[UUID] = Query(None),
    analysing_model: Optional[AnalysingModelTypes] = Query(None),
    sort_by: Literal["created_at"] = Query("created_at", description="Поле сортировки"),
    order: Literal["asc", "desc"] = Query("desc", description="asc / desc"),
    page: Optional[int] = Query(1, ge=1),
    page_size: Optional[int] = Query(10, ge=1, le=100),
):
    return {
        "company_id": company_id,
        "analysing_model": analysing_model,
        "chat_id": chat_id,
        "schedule_id": schedule_id,
        "prompt_id": prompt_id,
        "sort_by": sort_by,
        "order": order,
        "page": page,
        "page_size": page_size,
    }


#  Report schemas
class AnalysisReportFilters(BaseModel):
    company_id: UUID
    date_to: datetime
    date_from: datetime


class AnalysisReportSchema(BaseModel):
    schedule_name: str
    prompt_name: str
    date: datetime
    tokens_input: int
    tokens_output: int


class AnalysisReport(BaseModel):
    analyses: List[AnalysisReportSchema]
    total_tokens_input: int
    total_tokens_output: int
