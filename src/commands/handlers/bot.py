# src/commands/handlers/bot.py

import logging
from typing import Any, List

from src.commands.commands_registry import register_command
from src.config_loader import config_loader
from src.session.session_manager import pause, resume, set_active_char

logger = logging.getLogger(__name__)

from src.session.session_manager import is_paused


@register_command("/bot")
async def bot_handler(session: Any, message: dict[str, Any], args: List[str]) -> None:
    """
    /bot [<index>|pause|resume]
    Manage the current bot:
      • no args: show settings
      • <index>: switch to bot by its number (from /bots)
      • pause: pause messaging to LLM
      • resume: resume messaging to LLM

    """
    config = config_loader()
    telegram_conf = config.get("telegram", {})
    bot_name = session.client.bot_name
    bot_conf = telegram_conf.get(bot_name, {})

    # Get defaults
    default_conf = bot_conf.get("default", {})
    current_bot = bot_name
    display_name = bot_conf.get("name", current_bot)
    service = default_conf.get("service")
    model = default_conf.get("model")
    temperature = default_conf.get("temperature")
    maxtoken = default_conf.get("maxtoken")

    # No args: show current settings
    if not args:
        is_active = not is_paused(session.chat_id)
        # paused_status = "✅ Yes" if is_paused(session.chat_id) else "❌ No"
        active_status = "✅ online" if is_active else "❌ offline"
        lines = [
            f"{current_bot} ({active_status})",
            f"Name: {display_name}",
            f"Service: {service}",
            f"Model: {model}",
            f"Temperature: {temperature}",
            f"Max tokens: {maxtoken}",
        ]
        await session.send_message("\n".join(lines))
        return

    arg = args[0].lower()
    # Resume messaging
    if arg == "start":
        resume(session.chat_id)
        await session.send_message("✅ Bot messaging resumed.")
        return
    # Pause messaging
    if arg == "pause":
        pause(session.chat_id)
        await session.send_message("⏸️ Bot messaging paused.")
        return

    # Switch by index
    if arg.isdigit():
        index = int(arg) - 1
        bot_list = [n for n in telegram_conf.keys() if n.startswith("bot_")]
        if 0 <= index < len(bot_list):
            new_bot = bot_list[index]
            set_active_char(session.chat_id, new_bot)
            await session.send_message(f"🔄 Switched to bot: {new_bot}")
        else:
            await session.send_message(f"⚠️ Bot index out of range: {arg}")
        return

    # Invalid usage
    await session.send_message("⚠️ Invalid argument. Usage: /bot [<index>|start|stop]")
