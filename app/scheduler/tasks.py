# from celery import app

from datetime import datetime, timezone

from aiogram import Bot
from loguru import logger

from app.database.models import AnalysingModelTypes, AnalysisResult, Chat, ChatSchedule, Message, TargetChat
from app.yandex_funcs.yandex_funcs import yandex_analyze


async def analyze(schedule: ChatSchedule, settings):
    if not (schedule.chat and schedule.prompt):
        raise ValueError(f"Попытка провести анализ для неполного расписания: {schedule.id}")
    chat_id = schedule.chat.id
    chat = schedule.chat

    analysis_end = datetime.now(timezone.utc)
    first_run = schedule.last_run_at is None

    # Первый запуск: от самого старого сообщения (если есть), иначе от created_at
    if first_run:
        analysis_start = schedule.created_at
        lower_op = "gte"
    else:
        analysis_start = schedule.last_run_at
        lower_op = "gt"  # избегаем дублей на границе

    time_filter = {f"timestamp__{lower_op}": analysis_start, "timestamp__lte": analysis_end}

    messages = await (
        Message.filter(chat_id=chat_id, **time_filter).select_related("account", "chat").order_by("timestamp")
    )

    prompt = schedule.prompt

    analysis_result = None
    tokens_input = tokens_output = 0

    if messages or schedule.run_on_empty_chat:
        analysis_result, tokens_input, tokens_output = await yandex_analyze(prompt.id, messages, settings)

    # Сдвигаем watermark даже при пустом окне (чтобы не гонять одно и то же)
    await ChatSchedule.filter(id=schedule.id, last_run_at=schedule.last_run_at).update(last_run_at=analysis_end)

    return {
        "chat": chat,
        "analysis_result": analysis_result,
        "tokens_input": tokens_input,
        "tokens_output": tokens_output,
        "prompt": prompt,
        "date_to": analysis_end,
        "date_from": analysis_start,
        "schedule": schedule,
        "company_id": schedule.company_id,
    }


async def save_analysis_result(data):
    """
    Сохраняет результат анализа в базу данных.
    """
    logger.info(f"Сохранение результата анализа для чата {data['chat'].id}.")

    if data["analysis_result"]:
        analysis = await AnalysisResult.create(
            prompt=data["prompt"],
            chat=data["chat"],
            result_text=data["analysis_result"],
            tokens_input=data["tokens_input"],
            tokens_output=data["tokens_output"],
            schedule=data["schedule"],
            date_to=data["date_to"],
            date_from=data["date_from"],
            company_id=data["company_id"],
            analysing_model=AnalysingModelTypes.YA_GPT_PRO,
        )
        logger.debug(f"💾 Сохранили анализ: {analysis.id} — тип: {type(analysis.id)}")

        logger.info(f"Результат анализа сохранён для чата {data['chat'].id}.")
        return analysis.id
    else:
        logger.info(f"Для чата {data['chat']} нет анализа для сохранения.")


async def send_analysis_result(target_chats: list[Chat], chat_name, bot_token, analysis_result, message_intro):
    """
    Отправляет результат анализа в Telegram.
    """
    bot = Bot(bot_token)

    me = await bot.get_me()
    logger.debug(f"🤖 Бот: {me.username} ({me.id})")
    if not message_intro:
        message_intro = ""
    message_text = f"""{message_intro}
                {analysis_result}"""

    try:
        for chat in target_chats:
            logger.debug(f"📨 Пытаемся отправить в chat_id={chat.id} ({type(chat.id)})")
            await bot.send_message(chat_id=chat.id, text=message_text)
        logger.info(f"""Результат анализа для чата {chat_name} успешно отправлен.""")
    except Exception as e:
        logger.error(
            f"""Ошибка при отправке результата в Telegram для чата {chat_name}: {e}""",
            exc_info=True,
        )
    finally:
        await bot.session.close()


async def send_notification(schedule: ChatSchedule):
    """
    Отправляет результат анализа в Telegram.
    """
    bot_token = schedule.bot.bot_token
    bot = Bot(bot_token)

    me = await bot.get_me()
    logger.debug(f"🤖 Бот: {me.username} ({me.id})")
    if not schedule.message_intro:
        message_intro = ""
    message_text = f"""{message_intro}
                {schedule.notification_text}"""
    target_chats = await TargetChat.filter(schedule=schedule).prefetch_related("chat").all()
    chats = [target_chat.chat for target_chat in target_chats]
    try:
        for chat in chats:
            logger.debug(f"📨 Пытаемся отправить в chat_id={chat.id} ({type(chat.id)})")
            await bot.send_message(chat_id=chat.id, text=message_text)
        logger.info("Уведомления успешно отправлены")
    except Exception as e:
        logger.error(
            f"""Ошибка при отправке уведомлений в Telegram: {e}""",
            exc_info=True,
        )
    finally:
        await bot.session.close()
