import asyncio
from telegram import Bot
from telegram.error import TelegramError
from app.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


async def send_message(text: str) -> bool:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[telegram] TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set — skipping")
        return False
    try:
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=text, parse_mode="HTML")
        print(f"[telegram] Message sent: {text[:80]}...")
        return True
    except TelegramError as e:
        print(f"[telegram] Error: {e}")
        return False


async def telegram_test() -> None:
    print("[telegram] Sending test message...")
    ok = await send_message(
        "🤖 <b>Cita Previa Bot</b>\n\nTest message — bot is alive and configured correctly."
    )
    if ok:
        print("[telegram] Test passed.")
    else:
        print("[telegram] Test failed — check your .env credentials.")
