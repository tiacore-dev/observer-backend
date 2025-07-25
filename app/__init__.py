import asyncio
from contextlib import asynccontextmanager
from functools import partial

import redis.asyncio as redis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from tiacore_lib.config import ConfigName, get_settings
from tiacore_lib.rabbit.event_consumer import EventConsumer
from tiacore_lib.rabbit.handlers import handle_user_event
from tortoise import Tortoise

from app.config import TestConfig, _load_settings
from app.routes import register_routes
from metrics.logger import setup_logger
from metrics.tracer import init_tracer


def provide_settings(config_name: ConfigName):
    def _inner():
        return _load_settings(config_name)

    return _inner


def create_app(config_name: ConfigName) -> FastAPI:
    settings = _load_settings(config_name)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if type(settings) is not TestConfig:
            from app.database.config import TORTOISE_ORM

            await Tortoise.init(config=TORTOISE_ORM)
            Tortoise.init_models(["app.database.models"], "models")
            redis_url = settings.REDIS_URL
            redis_client = redis.from_url(redis_url)
            FastAPICache.init(RedisBackend(redis_client), prefix="fastapi-cache")
            consumer = EventConsumer(
                rabbit_url=settings.AUTH_BROKER_URL,
                queue_name="observer-service",
                routing_keys=["user.*"],
            )
            task = asyncio.create_task(consumer.connect_and_consume(partial(handle_user_event, settings=settings)))
            app.state.rabbit_task = task

        yield

        await Tortoise.close_connections()

    app = FastAPI(title="Observer", redirect_slashes=False, lifespan=lifespan)
    app.dependency_overrides[get_settings] = provide_settings(config_name)
    setup_logger()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    if config_name == "Production":
        init_tracer(app)

    register_routes(app)

    return app
