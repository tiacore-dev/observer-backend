import os

from dotenv import load_dotenv
from tiacore_lib.config import ConfigName

from app.config import _load_settings

load_dotenv()

# Порт и биндинг
PORT = os.getenv("PORT", 8000)
CONFIG_NAME = ConfigName(os.getenv("CONFIG_NAME", "development"))
settings = _load_settings(config_name=CONFIG_NAME)

TORTOISE_ORM = {
    "connections": {"default": settings.db_url},
    "apps": {
        "models": {
            # Укажите только модуль
            "models": ["app.database.models", "aerich.models"],
            "default_connection": "default",
        },
    },
    "use_tz": False,  # <--- обязательно
    "timezone": "UTC",
}
