# src/commands/handlers/status.py

from typing import Any, Dict, List

from llm_telegram_bot.commands.commands_registry import register_command
from llm_telegram_bot.config.config_loader import load_config
from llm_telegram_bot.session.session_manager import (
    get_max_tokens,
    get_model,
    get_session,
    get_temperature,
    is_paused,
)
from llm_telegram_bot.utils.escape_html import html_escape
from llm_telegram_bot.utils.logger import logger

# Log that the help handler is being loaded
logger.info("[Help Handler] status.py is being loaded")


@register_command("/status")
async def status_handler(session: Any, message: Dict[str, Any], args: List[str]) -> None:
    """
    /status
    Show current LLM service, model, temperature, max tokens, and pause state.
    """
    chat_id = session.chat_id
    bot_name = session.bot_name
    state = get_session(chat_id, bot_name)

    # Service
    svc = state.active_service or "None"

    # Model (manual override wins, else bot default)
    manual_model = get_model(chat_id, bot_name)
    if manual_model:
        mdl = manual_model
    else:
        cfg = load_config()
        bot_conf = cfg["telegram"][session.client.bot_name]["default"]
        mdl = bot_conf.get("model", "None")

    # Temperature
    tmp = get_temperature(chat_id, bot_name)
    if tmp is None:
        cfg = load_config()
        bot_conf = cfg["telegram"][session.client.bot_name]["default"]
        tmp = bot_conf.get("temperature", 0.0)

    # Max tokens
    mx = get_max_tokens(chat_id, bot_name)
    if mx is None:
        cfg = load_config()
        bot_conf = cfg["telegram"][session.client.bot_name]["default"]
        mx = bot_conf.get("maxtoken", 0)

    # Paused?
    paused = "✅ Yes" if is_paused(chat_id, bot_name) else "❌ No"

    # Build and send
    lines: List[str] = [
        "<b>📊 Current Status</b>",
        f"• Service: <b>{html_escape(svc)}</b>",
        f"• Model: <b>{html_escape(mdl)}</b>",
        f"• Temperature: {html_escape(str(tmp))}",
        f"• Max tokens: {html_escape(str(mx))}",
        f"• Paused: {paused}",
    ]
    await session.send_message("\n".join(lines), parse_mode="HTML")
