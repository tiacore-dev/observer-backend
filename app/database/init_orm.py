from loguru import logger
from tortoise import Tortoise


async def init_db(settings):
    logger.info("🔌 Инициализация Tortoise ORM без FastAPI")
    await Tortoise.init(db_url=settings.db_url, modules={"models": ["app.database.models"]})
    # await Tortoise.generate_schemas()
    logger.info("✅ База данных готова")
