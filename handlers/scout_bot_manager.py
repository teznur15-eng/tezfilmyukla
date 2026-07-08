import logging
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters
)
from utils.database import get_setting

logger = logging.getLogger(__name__)

# Global reference to the separate Scout Bot Application
scout_bot_app = None

def get_scout_bot_app():
    return scout_bot_app

async def start_scout_bot(main_application=None):
    """
    Builds and starts the separate Scouting Bot dynamically in the background.
    """
    global scout_bot_app
    
    # 1. Stop existing Scout Bot if running
    await stop_scout_bot()
    
    # 2. Check if a Scout Bot token is configured
    token = get_setting("scout_bot_token")
    if not token or token.strip() == "":
        logger.info("Scout Bot is not started because 'scout_bot_token' setting is empty.")
        return False
        
    logger.info(f"Starting separate Scout Bot with token: {token[:12]}...")
    
    try:
        from handlers.scout_handler import show_scout_dashboard, handle_scout_callbacks, handle_scout_messages
        
        # Build independent application
        builder = ApplicationBuilder().token(token).concurrent_updates(True)
        app = builder.build()
        
        # Register Scout Handlers specifically for this separate bot
        async def scout_start(update, context):
            user = update.effective_user
            await show_scout_dashboard(update.message, user, context)
            
        async def scout_callback_dispatcher(update, context):
            q = update.callback_query
            # If it's a callback query we handle, do it
            if await handle_scout_callbacks(update, context):
                return
            # Check if there is some fallback or if we need to let the user know
            await q.answer("Tugma bajarilmadi.")
            
        async def scout_message_dispatcher(update, context):
            if await handle_scout_messages(update, context):
                return
            await update.message.reply_text("❓ Noma'lum buyruq. Scouting boshqaruv paneli uchun /start yozing.")
            
        app.add_handler(CommandHandler("start", scout_start))
        app.add_handler(CallbackQueryHandler(scout_callback_dispatcher))
        app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, scout_message_dispatcher))
        
        # Initialize and run polling asynchronously without blocking the main thread
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        
        scout_bot_app = app
        logger.info("🚀 Separate Scout Bot is now running and polling.")
        return True
    except Exception as e:
        logger.error(f"Failed to start separate Scout Bot: {e}", exc_info=True)
        return False

async def stop_scout_bot():
    """
    Safely stops and shutdowns the running separate Scout Bot instance.
    """
    global scout_bot_app
    if scout_bot_app:
        logger.info("Stopping separate Scout Bot...")
        try:
            if scout_bot_app.updater and scout_bot_app.updater.running:
                await scout_bot_app.updater.stop()
            await scout_bot_app.stop()
            await scout_bot_app.shutdown()
        except Exception as e:
            logger.error(f"Error while stopping Scout Bot: {e}")
        finally:
            scout_bot_app = None
