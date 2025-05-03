# src/llm_telegram_bot/commands/handlers/bot.py

import html
from typing import Any, List

from llm_telegram_bot.commands.commands_registry import register_command
from llm_telegram_bot.config.config_loader import load_config
from llm_telegram_bot.config.schemas import BotConfig
from llm_telegram_bot.session.session_manager import (
    get_max_tokens,
    get_model,
    get_service,
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
    status = "⏸️ offline" if is_paused(chat_id, bot_name) else "✅ online"

    service = get_service(chat_id, bot_name) or ""  # string
    manual_model = get_model(chat_id, bot_name)  # optional override
    model = manual_model if manual_model else default_conf.model

    temperature = get_temperature(chat_id, bot_name)
    maxtoken = get_max_tokens(chat_id, bot_name)

    # 3) Escape for HTML
    safe = html.escape
    lines = [
        f"<b>{safe(display_name)}</b> ({safe(bot_name)})",
        status,
        f"Service: {safe(service)}",
        f"Model: {safe(model)}",
        f"Temp: {safe(str(temperature))}",
        f"Tokens: {safe(str(maxtoken))}",
    ]

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
