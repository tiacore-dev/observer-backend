import asyncio
import os

from dotenv import load_dotenv
from loguru import logger
from tiacore_lib.config import ConfigName

from app.config import _load_settings
from app.database.init_orm import init_db
from app.scheduler.rabbit_consumer import consume_schedule_events
from app.scheduler.scheduler import start_scheduler
from metrics.logger import setup_logger

load_dotenv()
setup_logger()
CONFIG_NAME = ConfigName(os.getenv("CONFIG_NAME", "development"))
settings = _load_settings(CONFIG_NAME)


async def main():
    await init_db(settings)

    # запускаем обе корутины как фоновые задачи
    asyncio.create_task(consume_schedule_events(settings))
    asyncio.create_task(start_scheduler(settings))

    logger.info("✅ Consumer и планировщик запущены")

    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(main())
