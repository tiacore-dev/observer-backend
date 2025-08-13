# tests/test_analysis_report.py
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient

from app.database.models import AnalysisResult, Chat, ChatSchedule, Prompt


@pytest.fixture
async def seed_analysis_results(
    seed_schedule: ChatSchedule,
    seed_prompt: Prompt,
    seed_chat: Chat,
):
    """
    Создаёт 2 записи в диапазоне и 1 — вне диапазона для проверки фильтра.
    """
    now = datetime.now(timezone.utc)
    company_id = seed_schedule.company_id

    in1 = await AnalysisResult.create(
        prompt=seed_prompt,
        chat=seed_chat,
        schedule=seed_schedule,
        company_id=company_id,
        result_text="in-range #1",
        date_from=now - timedelta(hours=3),
        date_to=now - timedelta(hours=2),
        tokens_input=100,
        tokens_output=10,
        created_at=now - timedelta(hours=1, minutes=30),  # в диапазоне
    )

    in2 = await AnalysisResult.create(
        prompt=seed_prompt,
        chat=seed_chat,
        schedule=seed_schedule,
        company_id=company_id,
        result_text="in-range #2",
        date_from=now - timedelta(hours=2),
        date_to=now - timedelta(hours=1),
        tokens_input=200,
        tokens_output=20,
        created_at=now - timedelta(hours=1),  # в диапазоне
    )

    out1 = await AnalysisResult.create(
        prompt=seed_prompt,
        chat=seed_chat,
        schedule=seed_schedule,
        company_id=company_id,
        result_text="out-of-range",
        date_from=now - timedelta(days=10, hours=1),
        date_to=now - timedelta(days=10),
        tokens_input=999,
        tokens_output=999,
        created_at=now - timedelta(days=10),  # ВНЕ диапазона
    )

    return in1, in2, out1


@pytest.mark.asyncio
async def test_get_analyses_report_returns_totals_and_items(
    test_app: AsyncClient,
    jwt_token_admin,
    seed_schedule: ChatSchedule,
    seed_analysis_results,
):
    REPORT_URL = "/api/analysis/report"

    now = datetime.now(timezone.utc)
    params = {
        "company_id": str(seed_schedule.company_id),
        "date_from": (now - timedelta(hours=2)).isoformat(),
        "date_to": now.isoformat(),
    }

    headers = {"Authorization": f"Bearer {jwt_token_admin['access_token']}"}

    resp = await test_app.get(REPORT_URL, params=params, headers=headers)
    assert resp.status_code == 200, resp.text

    payload = resp.json()

    # Проверяем суммы: 100+200 и 10+20
    assert payload["total_tokens_input"] == 300
    assert payload["total_tokens_output"] == 30

    # В списке должно быть ровно 2 анализа из диапазона
    analyses = payload["analyses"]
    assert isinstance(analyses, list)
    assert len(analyses) == 2

    # Проверим поля первой записи (порядок не гарантируем — просто проверим структуру)
    sample = analyses[0]
    assert "schedule_name" in sample
    assert "prompt_name" in sample
    assert "date" in sample  # поле из схемы
    assert "tokens_input" in sample
    assert "tokens_output" in sample

    # Названия должны подтянуться
    assert all(a["schedule_name"] for a in analyses)
    assert all(a["prompt_name"] for a in analyses)

    # Токены не None
    assert all(isinstance(a["tokens_input"], int) for a in analyses)
    assert all(isinstance(a["tokens_output"], int) for a in analyses)


@pytest.mark.asyncio
async def test_get_analyses_report_empty_result(
    test_app: AsyncClient,
    jwt_token_admin,
    seed_schedule: ChatSchedule,
):
    REPORT_URL = "/api/analysis/report"

    # Диапазон, где данных точно нет
    start = datetime(2000, 1, 1, tzinfo=timezone.utc)
    end = datetime(2000, 1, 2, tzinfo=timezone.utc)

    params = {
        "company_id": str(seed_schedule.company_id),
        "date_from": start.isoformat(),
        "date_to": end.isoformat(),
    }
    headers = {"Authorization": f"Bearer {jwt_token_admin['access_token']}"}

    resp = await test_app.get(REPORT_URL, params=params, headers=headers)
    assert resp.status_code == 200, resp.text

    payload = resp.json()
    assert payload["total_tokens_input"] == 0
    assert payload["total_tokens_output"] == 0
    assert payload["analyses"] == []
