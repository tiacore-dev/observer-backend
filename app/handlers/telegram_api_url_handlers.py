import secrets
from uuid import UUID

import aiohttp
from fastapi import HTTPException
from loguru import logger

from app.config import BaseConfig, TestConfig
from app.database.models import Bot
from app.utils.aiohttp_helpers import fetch_bytes, fetch_json


async def validate_token_and_register(token: str, company_id: UUID, comment: str | None) -> Bot:
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://api.telegram.org/bot{token}/getMe") as resp:
            data = await resp.json()
            if not data.get("ok"):
                raise ValueError("Invalid token")
            bot_info = data["result"]
            logger.info(f"Информация о боте: {bot_info}")
    bot_exists = await Bot.filter(id=bot_info["id"]).exists()
    if bot_exists:
        raise HTTPException(status_code=419, detail=f"Бот: {bot_info['username']} уже привязан к другой компании")
    secret_token = secrets.token_urlsafe(32)
    bot = await Bot.create(
        id=bot_info["id"],
        bot_username=bot_info["username"],
        bot_first_name=bot_info["first_name"],
        bot_token=token,
        secret_token=secret_token,
        company_id=company_id,
        comment=comment,
    )

    return bot


async def get_webhook_info(bot_token: str) -> dict:
    url = f"https://api.telegram.org/bot{bot_token}/getWebhookInfo"
    async with aiohttp.ClientSession() as session:
        data = await fetch_json(session, "GET", url)
        logger.info(f"Webhook info: {data}")
        return data


async def set_webhook(bot: Bot, settings: BaseConfig | TestConfig):
    url = f"https://api.telegram.org/bot{bot.bot_token}/setWebhook"
    payload = {
        "url": f"{settings.WEBHOOK_BASE_URL}/api/webhook/updates",
        "secret_token": bot.secret_token,
        "allowed_updates": [
            "message",
            "edited_message",
            "callback_query",
            "inline_query",
            "poll",
            "chat_member",
            "my_chat_member",
        ],
    }
    async with aiohttp.ClientSession() as session:
        result = await fetch_json(session, "POST", url, json=payload)
        logger.info(f"Webhook setup result: {result}")


async def delete_webhook(bot_token: str) -> dict:
    url = f"https://api.telegram.org/bot{bot_token}/deleteWebhook"
    async with aiohttp.ClientSession() as session:
        data = await fetch_json(session, "GET", url)
        logger.info(f"Webhook deleted: {data}")
        return data


async def get_file(bot_token: str, file_id: str):
    url_get_path = f"https://api.telegram.org/bot{bot_token}/getFile?file_id={file_id}"
    async with aiohttp.ClientSession() as session:
        data = await fetch_json(session, "GET", url_get_path)
        logger.debug(f"Ответ от телеграм по файлу: {data}")
        if "result" not in data or "file_path" not in data["result"]:
            logger.warning(f"📦 Telegram не прислал путь к файлу: {data}")
            return None
        file_path = data["result"]["file_path"]
        url_get_bytes = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"
        file_bytes = await fetch_bytes(session, "GET", url_get_bytes)
        return file_bytes, file_path
