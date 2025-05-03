# src/llm_telegram_bot/commands/handlers/bots.py

from typing import Any, List

from llm_telegram_bot.commands.commands_registry import register_command
from llm_telegram_bot.config.config_loader import load_config
from llm_telegram_bot.utils.logger import logger

logger.info("[Bots Handler] bots.py is being loaded")


@register_command("/bots")
async def bots_handler(session: Any, message: dict, args: List[str]) -> None:
    """
    /bots
    List all configured and enabled bots (display name and Telegram handle).
    """
    cfg = load_config()  # RootConfig
    tg_cfg = cfg.telegram  # TelegramConfig

    bots_list: List[tuple[str, str]] = []
    for bot_name, bot_conf in tg_cfg.bots.items():
        # Only include enabled bots
        if not bot_conf.enabled:
            continue
        name = bot_conf.name or bot_name
        handle = bot_conf.handle or ""
        bots_list.append((name, handle))

    if not bots_list:
        await session.send_message("⚠️ No bots configured.", parse_mode="HTML")
        return

    lines = ["<b>Configured and enabled bots:</b>"]
    for idx, (name, handle) in enumerate(bots_list, start=1):
        if handle:
            lines.append(f"{idx}. {name} ({handle})")
        else:
            lines.append(f"{idx}. {name}")

    await session.send_message("\n".join(lines), parse_mode="HTML")
