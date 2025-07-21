import json
from uuid import UUID

import aio_pika

from app.config import BaseConfig, TestConfig


async def publish_schedule_event(schedule_id: UUID, settings: BaseConfig | TestConfig, action: str = "add"):
    connection = await aio_pika.connect_robust(settings.BROKER_DATA)
    async with connection:
        channel = await connection.channel()
        await channel.declare_queue("schedules", durable=True)

        await channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(
                    {
                        "action": action,
                        "schedule_id": str(schedule_id),
                    }
                ).encode()
            ),
            routing_key="schedules",
        )
