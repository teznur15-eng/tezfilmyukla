"""
MovieBot va Userbot Asosiy ishga tushirish fayli (main.py)
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Env faylini yuklash
load_dotenv()

# Log tayyorlash
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters
)

from utils.database import init_db
from handlers.user import (
    start_handler, button_handler, message_handler
)
from handlers.admin import (
    admin_panel, admin_callback, admin_message, ban_cmd, unban_cmd, sub_cmd, addadmin_cmd, removeadmin_cmd
)
from handlers.userbot import (
    connect_command, disconnect_command
)


async def post_init(application):
    import asyncio
    from handlers.userbot import start_userbot_manager
    from handlers.scout_agent import start_all_scout_agents
    from handlers.scout_bot_manager import start_scout_bot
    asyncio.create_task(start_userbot_manager(application))
    asyncio.create_task(start_all_scout_agents(application))
    asyncio.create_task(start_scout_bot(application))


def main():
    token = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
    if not token or token == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        logger.error("BOT_TOKEN muhit o'zgaruvchisi o'rnatilmagan! .env faylini tekshiring.")
        print("\n[XATOLIK] BOT_TOKEN topilmadi! Please set BOT_TOKEN in .env file or environment variables.\n")
        return

    # Bazani tekshirish
    init_db()

    # App yaratish
    app = ApplicationBuilder().token(token).concurrent_updates(True).post_init(post_init).build()

    # Commandlar
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("connect_api", connect_command))
    app.add_handler(CommandHandler("disconnect", disconnect_command))
    app.add_handler(CommandHandler("ban", ban_cmd))
    app.add_handler(CommandHandler("unban", unban_cmd))
    app.add_handler(CommandHandler("sub", sub_cmd))
    app.add_handler(CommandHandler("addadmin", addadmin_cmd))
    app.add_handler(CommandHandler("removeadmin", removeadmin_cmd))

    # Callbacks
    app.add_handler(CallbackQueryHandler(admin_callback, pattern="^adm_"))
    app.add_handler(CallbackQueryHandler(admin_callback, pattern="^(approve_payment_|reject_payment_)"))
    app.add_handler(CallbackQueryHandler(button_handler))

    # Messages
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, message_handler))

    logger.info("Bot muvaffaqiyatli ishga tushdi...")
    print("🚀 MovieBot Telegram Boti muvaffaqiyatli ishga tushdi...")
    app.run_polling()


if __name__ == "__main__":
    main()
