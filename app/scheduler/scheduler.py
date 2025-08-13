from loguru import logger

from app.database.models import ChatSchedule
from app.scheduler.add_or_remove_schedules import add_schedule_job
from app.scheduler.init_scheduler import scheduler


async def start_scheduler(settings):
    schedules = await ChatSchedule.filter(enabled=True).prefetch_related("chat", "prompt", "bot")
    logger.debug(f"👟 Запускаем планировщик. Загружено {len(schedules)} задач")
    for schedule in schedules:
        add_schedule_job(schedule, settings)

    scheduler.start()
    logger.info("Планировщик успешно запущен с задачами из базы.")


def list_scheduled_jobs():
    """
    Выводит список всех запланированных задач.
    """
    for job in scheduler.get_jobs():
        logger.info(f"Job ID: {job.id}, trigger: {job.trigger}")


def clear_existing_jobs():
    """
    Удаляет все существующие задачи из планировщика.
    """
    try:
        scheduler.remove_all_jobs()
        logger.info("Все задачи успешно удалены из планировщика.")
    except Exception as e:
        logger.error(f"Ошибка при удалении всех задач: {e}")
