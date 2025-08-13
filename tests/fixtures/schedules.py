from uuid import uuid4

import pytest

from app.database.models import (
    Bot,
    Chat,
    ChatSchedule,
    Prompt,
    ScheduleStrategy,
    ScheduleType,
    SendStrategy,
    TargetChat,
)


@pytest.fixture
async def seed_schedule(seed_prompt: Prompt, seed_chat: Chat, seed_bot: Bot):
    schedule = await ChatSchedule.create(
        name="New",
        schedule_strategy=ScheduleStrategy.ANALYSIS,
        prompt=seed_prompt,
        chat=seed_chat,
        schedule_type=ScheduleType.INTERVAL,
        interval_minutes=1,
        enabled=True,
        send_strategy=SendStrategy.FIXED,
        time_to_send="16:30:00",
        company_id=uuid4(),
        bot=seed_bot,
    )

    await TargetChat.create(schedule=schedule, chat=seed_chat)

    return schedule
