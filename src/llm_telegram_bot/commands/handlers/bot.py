# src/llm_telegram_bot/commands/handlers/bot.py

import html
from typing import Any, List

from llm_telegram_bot.commands.commands_registry import register_command
from llm_telegram_bot.config.config_loader import load_config
from llm_telegram_bot.config.schemas import BotConfig
from llm_telegram_bot.session.session_manager import (
    get_active_char,
    get_active_user,
    get_max_tokens,
    get_model,
    get_service,
    get_session,
    get_temperature,
    is_paused,
    pause,
    resume,
)
from llm_telegram_bot.utils.logger import logger

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
    # 1) Load config and locate this bot’s config by name
    cfg = load_config()  # RootConfig
    tg_cfg = cfg.telegram  # TelegramConfig

    bot_name = session.client.bot_name  # e.g. "bot_1" or "bot_2"
    bot_conf: BotConfig | None = tg_cfg.bots.get(bot_name)
    if not bot_conf:
        await session.send_message("❌ Bot configuration not found.")
        return

    default_conf = bot_conf.default  # BotDefaults

    # 2) Gather state
    chat_id = session.chat_id
    bot_name = session.bot_name
    display_name = bot_conf.name  # e.g. "General Purpose"
    status = "Sending to LLM: ⏸️" if is_paused(chat_id, bot_name) else "Sending to LLM: ✅"
    sess = get_session(session.chat_id, session.bot_name)
    history = "History: ✅" if sess.history_on else "History ⏸️"

    service = get_service(chat_id, bot_name) or ""  # string
    manual_model = get_model(chat_id, bot_name)  # optional override
    model = manual_model if manual_model else default_conf.model

    temperature = get_temperature(chat_id, bot_name)
    maxtoken = get_max_tokens(chat_id, bot_name)

    # user and char
    current_user = get_active_user(session.chat_id, bot_name)
    current_char = get_active_char(session.chat_id, bot_name)

    # 3) Escape for HTML
    safe = html.escape
    lines = [
        f"<b>{safe(display_name)}</b> ({safe(bot_name)})",
        status,
        history,
        f"Service: {safe(service)}",
        f"Model: {safe(model)}",
        f"Tokens: {safe(str(maxtoken))}",
        f"Temp: {safe(str(temperature))}",
    ]

    # add user info to output
    if current_user and session.active_user_data:
        user_data = session.active_user_data
        user_name = user_data.get("identity", {}).get("name", "(unknown)")
        text = f"User: {user_name} (<code>{current_user}.yaml</code>)"
        lines.append(text)

    # add char info to output
    if current_char and session.active_char_data:
        char_data = session.active_char_data
        char_name = char_data.get("identity", {}).get("name", "(unknown)")
        text = f"Char: {char_name} (<code>{current_char}.yaml</code>)"
        lines.append(text)

    # 4) No args → show status
    if not args:
        await session.send_message("\n".join(lines), parse_mode="HTML")
        return

    # 5) Handle subcommands
    cmd = args[0].lower()
    if cmd == "pause":
        pause(chat_id, bot_name)
        await session.send_message("⏸️ Bot messaging paused.")
    elif cmd == "resume":
        resume(chat_id, bot_name)
        await session.send_message("✅ Bot messaging resumed.")
    else:
        await session.send_message("⚠️ Invalid argument. Use /bot [pause|resume]")
