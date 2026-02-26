import os
import sys
import logging
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from pathlib import Path

# Fix import path since this script is executed from the GUI
project_root = str(Path(__file__).resolve().parent.parent)
sys.path.append(project_root)

from core.llm_engine import WolfEngine

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# Cache engine to avoid recreating on every message
_engine_cache = {}

def _get_engine() -> WolfEngine:
    """Get or create a cached WolfEngine instance."""
    model_name = os.environ.get("WOLFCLAW_MODEL", "gpt-4o")
    bot_id = os.environ.get("WOLFCLAW_BOT_ID", "")
    
    # Parse fallback models from env (comma-separated)
    fallbacks_str = os.environ.get("WOLFCLAW_FALLBACKS", "")
    fallback_models = [m.strip() for m in fallbacks_str.split(",") if m.strip()] if fallbacks_str else []
    
    cache_key = f"{model_name}_{bot_id}"
    if cache_key not in _engine_cache:
        _engine_cache[cache_key] = WolfEngine(model_name, fallback_models=fallback_models)
    return _engine_cache[cache_key]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_html(
        rf"Hi {user.mention_html()}! I am powered by Wolfclaw. How can I assist you?",
    )

async def auto_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming messages via WolfEngine."""
    message = update.message
    if not message or not message.text:
        return # Ignore edited messages or messages without text
    
    user_message = message.text
    sender_id = update.effective_user.id
    
    # ─── SECURITY: Telegram User Whitelist ───
    # The first person to message the bot becomes the owner
    # All others are rejected
    owner_id = os.environ.get("WOLFCLAW_OWNER_ID", "")
    
    if not owner_id:
        # First user to message becomes the owner
        os.environ["WOLFCLAW_OWNER_ID"] = str(sender_id)
        logger.info(f"Owner set to Telegram user ID: {sender_id}")
    elif str(sender_id) != str(owner_id):
        await update.message.reply_text(
            "🛑 Unauthorized. This bot is private and only responds to its owner.\n"
            "If you need access, ask the bot owner to add your Telegram ID."
        )
        logger.warning(f"Unauthorized access attempt from user ID: {sender_id}")
        return
    
    system_prompt = os.environ.get("WOLFCLAW_PROMPT", "You are a helpful AI.")
    bot_id = os.environ.get("WOLFCLAW_BOT_ID", "") or None
    
    # Store chat history per user in context.chat_data
    if "messages" not in context.chat_data:
        context.chat_data["messages"] = []
    
    # Track message count before this turn (for screenshot detection)
    msg_count_before = len(context.chat_data["messages"])
    
    context.chat_data["messages"].append({"role": "user", "content": user_message})

    try:
        engine = _get_engine()
        response = engine.chat(
            messages=context.chat_data["messages"], 
            system_prompt=system_prompt,
            bot_id=bot_id
        )
        reply = response.choices[0].message.content
        
        # If the AI completed a terminal task but chose not to say anything
        if not reply or not reply.strip():
            reply = "*(Task completed)*"
        # Check if any new tool messages contained screenshots
        for msg in context.chat_data["messages"][msg_count_before:]:
            if msg.get("role") == "tool" and "SCREENSHOT_CAPTURED:" in msg.get("content", ""):
                try:
                    img_path = msg["content"].split("SCREENSHOT_CAPTURED:")[1].strip()
                    await update.message.reply_photo(photo=open(img_path, 'rb'))
                except Exception as e:
                    logger.error(f"Failed to send screenshot photo: {e}")
                    
        # Then send the text reply
        context.chat_data["messages"].append({"role": "assistant", "content": reply})
        
        # Try Markdown first, fall back to plain text if parsing fails
        try:
            await update.message.reply_text(reply, parse_mode="Markdown")
        except Exception:
            await update.message.reply_text(reply)
        
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        await update.message.reply_text(f"Sorry, my AI engine encountered an error: {e}")

def main() -> None:
    """Start the bot."""
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        print("Error: TELEGRAM_TOKEN environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, auto_chat))

    bot_id = os.environ.get("WOLFCLAW_BOT_ID", "unknown")
    model = os.environ.get("WOLFCLAW_MODEL", "unknown")
    logger.info(f"Wolfclaw Telegram Worker Started. Bot: {bot_id} | Model: {model}")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
