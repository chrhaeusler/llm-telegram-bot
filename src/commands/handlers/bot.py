# src/commands/handlers/bot.py

import html
from typing import Any, List

from src.commands.commands_registry import register_command
from src.config_loader import config_loader
from src.session.session_manager import (
    get_active_bot,
    get_max_tokens,
    get_model,
    get_service,
    get_temperature,
    is_paused,
    pause,
    resume,
)
from src.utils.logger import logger

logger.info("[Bot Handler] bot.py is being loaded")


@register_command("/bot")
async def bot_handler(session: Any, message: dict[str, Any], args: List[str]) -> None:
    """
    /bot [pause|resume]
    Manage the current bot:
      • no args: show current settings
      • pause: pause messaging
      • resume: resume messaging
    """
    cfg = config_loader()
    telegram_conf = cfg.get("telegram", {})

    bot_name = session.client.bot_name
    bot_conf = telegram_conf.get(bot_name, {})
    # pull out the “default” block so we can fall back cleanly
    default_conf = bot_conf.get("default", {})

    chat_id = session.chat_id
    current_bot = get_active_bot(chat_id) or bot_name
    display_name = bot_conf.get("name", bot_name)
    status = "✅ online" if not is_paused(chat_id) else "⏸️ offline"

    service = get_service(chat_id) or ""
    # Model (manual override wins, else bot default)
    # TO DO: initiate session with the standard model of the bot!
    manual_model = get_model(chat_id)
    if manual_model:
        mdl = manual_model
    else:
        cfg = config_loader()
        bot_conf = cfg["telegram"][session.client.bot_name]["default"]
        mdl = bot_conf.get("model", "None")
    # model parameters
    temperature = get_temperature(chat_id)
    maxtoken = get_max_tokens(chat_id)

    # Escape for HTML
    safe_display = html.escape(display_name)
    safe_bot = html.escape(current_bot)
    safe_service = html.escape(service)
    safe_model = html.escape(mdl)
    safe_temperature = html.escape(f"{temperature}")
    safe_maxtoken = html.escape(f"{maxtoken}")

    # No args: show settings
    if not args:
        lines = [
            f"<b>{safe_display}</b> ({safe_bot})",
            status,
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
