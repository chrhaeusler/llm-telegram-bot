# src/commands/handlers/bot.py

import logging
from typing import Any, List

from src.commands.commands_registry import register_command
from src.config_loader import config_loader
from src.session.session_manager import (
    get_active_bot,
    is_paused,
    pause,
    resume,
)

logger = logging.getLogger(__name__)


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

    # Defaults
    default_conf = bot_conf.get("default", {})
    display_name = bot_conf.get("name", bot_name)
    service = default_conf.get("service")
    model = default_conf.get("model")
    temperature = default_conf.get("temperature")
    maxtoken = default_conf.get("maxtoken")

    chat_id = session.chat_id
    # available = get_available_bots()
    current_bot = get_active_bot(chat_id)
    is_active = not is_paused(chat_id)
    status = "✅ online" if is_active else "⏸️ offline"
    # Escape underscores for Markdown
    safe_bot = current_bot.replace("_", "\\_")

    # No args: show settings
    if not args:
        lines = [
            f"*{display_name}* ({safe_bot})",
            f"{status}",
            f"Service: {service}",
            f"{model}",
            f"Temp: {temperature}",
            f"Tokens: {maxtoken}",
        ]
        await session.send_message("\n".join(lines))
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
