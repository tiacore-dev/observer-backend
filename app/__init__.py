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

from app.config import ProdConfig, ServerConfig, TestConfig, _load_settings
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
        if not isinstance(settings, TestConfig):
            from app.database.config import TORTOISE_ORM

            await Tortoise.init(config=TORTOISE_ORM)
            Tortoise.init_models(["app.database.models"], "models")
            redis_url = settings.REDIS_URL
            redis_client = redis.from_url(redis_url)
            FastAPICache.init(RedisBackend(redis_client), prefix="fastapi-cache")
            app.state.redis = redis_client
            consumer = EventConsumer(
                rabbit_url=settings.AUTH_BROKER_URL,
                queue_name="observer-service",
                routing_keys=["user.*"],
            )
            app.state.rabbit_consumer = consumer
            task = asyncio.create_task(consumer.connect_and_consume(partial(handle_user_event, settings=settings)))
            app.state.rabbit_task = task

        yield
        # shutdown
        if not isinstance(settings, TestConfig):
            # остановить consumer
            task = getattr(app.state, "rabbit_task", None)
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            consumer = getattr(app.state, "rabbit_consumer", None)
            if consumer and hasattr(consumer, "close"):
                await consumer.close()
            # закрыть Redis
            redis_client = getattr(app.state, "redis", None)
            if redis_client:
                await redis_client.aclose()

            await Tortoise.close_connections()

    app = FastAPI(title="Observer", redirect_slashes=False, lifespan=lifespan)
    app.dependency_overrides[get_settings] = provide_settings(config_name)
    setup_logger()
    if isinstance(settings, (ServerConfig, ProdConfig)):
        origins_raw = settings.CORS_ALLOW_ORIGINS
        origins = [o.strip() for o in origins_raw.split(",") if o.strip()]
        if not origins or origins == ["*"]:
            # чтобы не словить баг с credentials
            raise RuntimeError("CORS_ALLOW_ORIGINS must be explicit in stage/prod")
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
            max_age=600,
        )
    else:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=False,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    if config_name is ConfigName.PRODUCTION:
        init_tracer(app)

    register_routes(app)

    return app
