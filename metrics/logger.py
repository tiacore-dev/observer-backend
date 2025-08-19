import logging
import sys

from loguru import logger
from prometheus_client import Counter

# 📊 Prometheus метрики
error_counter = Counter("fastapi_errors_total", "Total number of FastAPI errors")
error_counter_by_user = Counter(
    "fastapi_errors_total_by_user",
    "Total number of errors per user",
    ["user_id", "login", "role"],
)


def exclude_metrics_log(record):
    # Исключаем только access-логи /metrics
    message = record.get("message", "")
    if "GET /metrics" in message and "200" in message:
        return False
    return True


# 📈 Прометеевский хук — реагирует на ERROR и выше
def prometheus_hook(message):
    record = message.record
    if record["level"].no >= 40:
        error_counter.inc()
        try:
            error_counter_by_user.labels(
                user_id=record.get("extra", {}).get("user_id", "unknown"),
                login=record.get("extra", {}).get("login", "system"),
                role=record.get("extra", {}).get("role", "system"),
            ).inc()
        except Exception as e:
            print(f"[PrometheusHook] Ошибка при инкременте метрик: {e}")


# 🔁 Перехват логов из logging в loguru
class InterceptHandler(logging.Handler):
    def emit(self, record):
        message = record.getMessage()

        # 💡 Отфильтровываем /metrics для access-логов
        if "GET /metrics" in message and ("200" in message or "307" in message):
            return

        try:
            level = logger.level(record.levelname).name
        except Exception:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, message)


# 🛠 Настройка логгера
def setup_logger():
    logger.remove()

    # 🎯 STDOUT для Loki (можно включить serialize=True)
    logger.add(
        sys.stdout,
        level="DEBUG",
        format="""{time:YYYY-MM-DDTHH:mm:ss.SSSZ} | {level} 
        | {name}:{function}:{line} - {message}""",
        enqueue=True,
        backtrace=True,
        diagnose=True,
        filter=exclude_metrics_log,
    )

    # 🧾 Файл логов
    logger.add(
        "logs/app.log",
        level="DEBUG",
        rotation="10 MB",
        retention="7 days",
        format="""{time:YYYY-MM-DD HH:mm:ss} | {level:<8}
          | {name}:{function}:{line} - {message}""",
        enqueue=True,
    )

    # 📡 Интеграция Prometheus hook
    logger.add(prometheus_hook, level="ERROR")

    # 🔗 Перехват логов
    logging.basicConfig(handlers=[InterceptHandler()], level=logging.INFO, force=True)

    for name in (
        "uvicorn",
        "uvicorn.error",
        "uvicorn.access",
        "fastapi",
        "gunicorn",
        "gunicorn.access",
        "gunicorn.error",
    ):
        logging.getLogger(name).handlers = [InterceptHandler()]
        logging.getLogger(name).setLevel(logging.INFO)

    return logger
