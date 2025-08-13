# from celery import app

from datetime import datetime, timezone

from aiogram import Bot
from loguru import logger

from app.database.models import AnalysingModelTypes, AnalysisResult, Chat, ChatSchedule, Message, Prompt, TargetChat
from app.yandex_funcs.yandex_funcs import yandex_analyze


async def analyze(schedule: ChatSchedule, settings):
    """
    Анализирует сообщения в чате за указанный временной промежуток.
    """
    chat_id = schedule.chat.id  # type: ignore
    logger.info(f"Начало анализа для чата {chat_id}")
    chat = await Chat.get_or_none(id=chat_id)
    if not chat:
        logger.error(f"Чат {chat_id} не найден.")
        raise ValueError(f"Чат {chat_id} не найден.")

    now_utc = datetime.now(timezone.utc)

    # Определяем начало анализа
    if schedule.last_run_at:
        analysis_start = schedule.last_run_at
    else:
        first_message = await Message.filter(chat=chat).order_by("timestamp").first()
        if not first_message:
            logger.warning(f"Нет сообщений в чате {chat_id} для анализа")
            return {
                "chat": chat,
                "analysis_result": None,
                "tokens_input": 0,
                "tokens_output": 0,
                "prompt": schedule.prompt,
                "schedule": schedule,
                "company_id": schedule.company_id,
            }
        analysis_start = first_message.timestamp

    analysis_end = now_utc

    logger.info(f"Диапазон анализа: {analysis_start} - {analysis_end}")

    try:
        messages = (
            await Message.filter(chat=chat, timestamp__gte=analysis_start, timestamp__lte=analysis_end)
            .order_by("timestamp")
            .prefetch_related("account", "chat")
            .all()
        )
    except Exception as e:
        logger.error(f"Ошибка при получении сообщений: {e}")
        raise

    if not messages:
        logger.warning(
            f"""Нет сообщений для анализа в чате {chat_id} за
            период {analysis_start} - {analysis_end}."""
        )
        return {
            "chat": chat,
            "analysis_result": None,
            "tokens_input": 0,
            "tokens_output": 0,
            "prompt": schedule.prompt,
            "date_to": analysis_end,
            "date_from": analysis_start,
            "schedule": schedule,
            "company_id": schedule.company_id,
        }

    logger.info(f"Сообщений для анализа найдено: {len(messages)}")

    try:
        prompt = await Prompt.get_or_none(id=schedule.prompt.id)  # type: ignore
        if not prompt:
            raise ValueError(f"Промпт с ID {schedule.prompt.id} не найден.")  # type: ignore

        analysis_result, tokens_input, tokens_output = await yandex_analyze(prompt.id, messages, settings)

    except Exception as e:
        logger.error(f"Ошибка при анализе сообщений: {e}")
        raise

    logger.info(f"Анализ завершён для чата {chat_id}.")
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
