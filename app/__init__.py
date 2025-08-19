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
from app.utils.helpers import delete_rabbit_queue
from metrics.logger import setup_logger
from metrics.tracer import init_tracer


def provide_settings(config_name: ConfigName):
    def _inner():
        return _load_settings(config_name)

    return _inner


def create_app(config_name: ConfigName) -> FastAPI:
    settings = _load_settings(config_name)
    logger = setup_logger()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if not isinstance(settings, TestConfig):
            from app.database.config import TORTOISE_ORM

            await Tortoise.init(config=TORTOISE_ORM)
            Tortoise.init_models(["app.database.models"], "models")
            redis_url = settings.REDIS_URL
            redis_client = redis.from_url(redis_url)
            FastAPICache.init(RedisBackend(redis_client), prefix=f"observer:{config_name}:cache")
            try:
                ok = await redis_client.ping()

                logger.info(f"Redis connected:  {ok}, {settings.REDIS_URL}")
            except Exception as e:
                logger.error(f"Redis connect failed:  {e}, {settings.REDIS_URL}")
            app.state.redis = redis_client

            # --- старт consumer
            queue_name = "observer-service"
            consumer = EventConsumer(
                rabbit_url=settings.AUTH_BROKER_URL,
                queue_name=queue_name,
                routing_keys=["user.*"],
            )
            app.state.rabbit_consumer = consumer
            app.state.rabbit_task = asyncio.create_task(
                consumer.connect_and_consume(partial(handle_user_event, settings=settings))
            )
            app.state.rabbit_queue_name = queue_name
            app.state.rabbit_broker_url = settings.AUTH_BROKER_URL

        yield
        # --- shutdown
        if not isinstance(settings, TestConfig):
            # 1) остановить consumer-задачу
            task = getattr(app.state, "rabbit_task", None)
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

            # 2) попытаться удалить очередь отдельным подключением
            try:
                queue_name = getattr(app.state, "rabbit_queue_name", None)
                broker_url = getattr(app.state, "rabbit_broker_url", None)
                if queue_name and broker_url:
                    await delete_rabbit_queue(broker_url, queue_name)
            except Exception as e:
                logger.warning("Queue delete unexpected error: %s", e)

            # 3) закрыть consumer (соединения/каналы)
            consumer = getattr(app.state, "rabbit_consumer", None)
            if consumer and hasattr(consumer, "close"):
                try:
                    await consumer.close()
                except Exception as e:
                    logger.warning("Consumer close error: %s", e)

            # 4) закрыть Redis
            redis_client = getattr(app.state, "redis", None)
            if redis_client:
                await redis_client.aclose()

            # 5) закрыть БД
            await Tortoise.close_connections()

    app = FastAPI(title="Observer", redirect_slashes=False, lifespan=lifespan)
    app.dependency_overrides[get_settings] = provide_settings(config_name)

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
