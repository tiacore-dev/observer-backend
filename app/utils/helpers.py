from datetime import time

from loguru import logger


def parse_time_string(t: str) -> time:
    return time.fromisoformat(t)


# +++ хелпер для удаления очереди
async def delete_rabbit_queue(broker_url: str, queue_name: str) -> None:
    try:
        import aio_pika  # используем то же семейство, что и большинство async-клиентов к Rabbit
    except Exception as e:
        logger.warning("Skip queue delete: aio-pika not installed (%s)", e)
        return

    try:
        connection = await aio_pika.connect_robust(broker_url)
        async with connection:
            channel = await connection.channel()
            try:
                await channel.queue_delete(queue_name, if_unused=False, if_empty=False)
                logger.info("RabbitMQ queue deleted: %s", queue_name)
            except Exception as e:
                # очередь может уже не существовать — не считаем это ошибкой
                msg = str(e).lower()
                if "not found" in msg or "404" in msg:
                    logger.info("Queue already absent: %s", queue_name)
                else:
                    logger.warning("Queue delete failed for %s: %s", queue_name, e)
    except Exception as e:
        logger.warning("Queue delete connection error for %s: %s", queue_name, e)
