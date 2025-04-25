# src/commands/handlers/bot.py

import logging
from typing import Any, List

from src.commands.commands_registry import register_command
from src.config_loader import config_loader
from src.session.session_manager import (
    get_active_bot,
    get_available_bots,
    is_paused,
    pause,
    resume,
    set_active_bot,
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
    available = get_available_bots()
    current_bot = get_active_bot(chat_id)
    is_active = not is_paused(chat_id)
    status = "✅ online" if is_active else "⏸️ offline"

    # No args: show settings
    if not args:
        lines = [
            f"{current_bot} ({status})",
            f"Name: {display_name}",
            f"Service: {service}",
            f"Model: {model}",
            f"Temperature: {temperature}",
            f"Max tokens: {maxtoken}",
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

    # Switch by index:
    if arg.isdigit():
        idx = int(arg)
        if 0 <= idx < len(available):
            new_bot = available[idx]
            set_active_bot(chat_id, new_bot)
            await session.send_message(f"🔄 Switched to bot: {new_bot}")
        else:
            await session.send_message(f"⚠️ Bot index out of range: {arg}")
        return

    await session.send_message("⚠️ Invalid argument. Use /bot [<index>|pause|resume]")
