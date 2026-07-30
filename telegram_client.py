import os
import logging
from telegram import Bot

logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = Bot(token=TELEGRAM_BOT_TOKEN) if TELEGRAM_BOT_TOKEN else None

async def send_telegram_message(chat_id: int, text: str) -> bool:
    """Utility to send messages back to Telegram chats."""
    if not bot:
        logger.error("Telegram bot token not configured.")
        return False
    try:
        await bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")
        return True
    except Exception as e:
        logger.error(f"Error sending message to chat_id {chat_id}: {e}")
        return False