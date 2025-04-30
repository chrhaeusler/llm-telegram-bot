# src/commands/handlers/bot.py

import html
import logging
from typing import Any, List

from src.commands.commands_registry import register_command
from src.config_loader import config_loader
from src.session.session_manager import (
    get_active_bot,
    get_maxtoken,
    get_model,
    get_service,
    get_temperature,
    is_paused,
    pause,
    resume,
)

# Create logger
logger = logging.getLogger(__name__)

# Log that the help handler is being loaded
logger.info("[Help Handler] bot.py is being loaded")


@register_command("/bot")
async def bot_handler(session: Any, message: dict[str, Any], args: List[str]) -> None:
    """
    /bot [<index>|pause|resume]
    Manage the current bot:
      • no args: show current settings
      • pause: pause messaging
      • resume: resume messaging
      • <index>: switch to bot by number (see /bots)
    """
    config = config_loader()
    telegram_conf = config.get("telegram", {})

    bot_name = session.client.bot_name
    bot_conf = telegram_conf.get(bot_name, {})

    chat_id = session.chat_id

    # Defaults
    # default_conf = bot_conf.get("default", {})

    #    service = default_conf.get("service")
    #    model = default_conf.get("model")
    #    temperature = default_conf.get("temperature")
    #    maxtoken = default_conf.get("maxtoken")

    chat_id = session.chat_id
    current_bot = get_active_bot(chat_id)
    display_name = bot_conf.get("name", bot_name)
    is_active = not is_paused(chat_id)
    status = "✅ online" if is_active else "⏸️ offline"

    service = get_service(chat_id)
    model = get_model(chat_id)
    temperature = get_temperature(chat_id)
    maxtoken = get_maxtoken(chat_id)

    # Escape special characters in bot name and other fields for HTML
    safe_bot = html.escape(current_bot) if current_bot else ""  # Escape the bot name to avoid HTML issues
    safe_bot = html.unescape(safe_bot)  # Unescape any HTML entities

    safe_service = html.escape(service or "")
    safe_model = html.escape(model or "")
    safe_temperature = html.escape(str(temperature))
    safe_maxtoken = html.escape(str(maxtoken))

    # No args: show settings
    if not args:
        lines = [
            f"<b>{html.escape(display_name)}</b> ({safe_bot})",  # Display name in bold
            f"{status}",
            f"Service: {safe_service}",
            f"Model: {safe_model}",
            f"Temp: {safe_temperature}",
            f"Tokens: {safe_maxtoken}",
        ]
        await session.send_message("\n".join(lines), parse_mode="HTML")
        return

    arg = args[0].lower()

    # Pause/resume
    if arg == "pause":
        pause(chat_id)
        await session.send_message("⏸️ Bot messaging paused.")
        return
    if arg == "resume":
        resume(chat_id)
        await session.send_message("✅ Bot messaging resumed.")
        return

    await session.send_message("⚠️ Invalid argument. Use /bot [pause|resume]")
