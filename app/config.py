from typing import Optional

from pydantic_settings import SettingsConfigDict
from tiacore_lib.config import (
    BaseConfig as SharedBaseConfig,
    ConfigName,
    TestConfig as SharedTestConfig,
)


class BaseConfig(SharedBaseConfig):
    ENDPOINT_URL: Optional[str] = None
    REGION_NAME: Optional[str] = None
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    BUCKET_NAME: Optional[str] = None

    WEBHOOK_BASE_URL: Optional[str] = None
    CORS_ALLOW_ORIGINS: str = "*"
    YANDEX_SPEECHKIT_API_URL: Optional[str] = None
    YANDEX_GPT_API_URL: Optional[str] = None
    YANDEX_API_KEY: Optional[str] = None
    FOLDER_ID: Optional[str] = None

    AUTH_BROKER_URL: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    @property
    def db_url(self) -> str:
        raise NotImplementedError("db_url not implemented in base config")


class TestConfig(SharedTestConfig):
    # ... остальные обязательные поля
    ENDPOINT_URL: str = ""
    REGION_NAME: str = ""
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    BUCKET_NAME: str = ""
    CORS_ALLOW_ORIGINS: str = "*"
    WEBHOOK_BASE_URL: str = ""
    YANDEX_SPEECHKIT_API_URL: str = ""
    YANDEX_GPT_API_URL: str = ""
    YANDEX_API_KEY: str = ""
    FOLDER_ID: str = ""
    AUTH_BROKER_URL: str = ""

    model_config = SettingsConfigDict(
        env_file=".env.test",
        env_file_encoding="utf-8",
        extra="ignore",  # необязательно, но рекомендую
    )

    @property
    def db_url(self) -> str:
        return self.TEST_DATABASE_URL


class DockerConfig(BaseConfig):
    DOCKER_DATABASE_URL: str = "sqlite:///server.db"

    @property
    def db_url(self) -> str:
        return self.DOCKER_DATABASE_URL


class DevConfig(BaseConfig):
    DATABASE_URL: str = "sqlite:///server.db"

    @property
    def db_url(self) -> str:
        return self.DATABASE_URL


class ServerConfig(BaseConfig):
    DATABASE_URL: str = "sqlite:///server.db"

    @property
    def db_url(self) -> str:
        return self.DATABASE_URL


class ProdConfig(BaseConfig):
    DATABASE_URL: str = "sqlite:///server.db"

    @property
    def db_url(self) -> str:
        return self.DATABASE_URL


def _load_settings(config_name: str):
    match ConfigName(config_name):
        case ConfigName.TEST:
            return TestConfig()
        case ConfigName.DEV:
            return DevConfig()
        case ConfigName.DOCKER:
            return DockerConfig()
        case ConfigName.PRODUCTION:
            return ProdConfig()
        case ConfigName.SERVER:
            return ServerConfig()
        case _:
            raise ValueError(f"❌ Unknown config_name: {config_name}")
