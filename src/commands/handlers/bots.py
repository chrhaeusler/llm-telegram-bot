# src/commands/handlers/bots.py

from typing import Any, List

from src.commands.commands_registry import register_command
from src.config_loader import config_loader
from src.utils.logger import logger

# Log that the help handler is being loaded
logger.info("[Bots Handler] bots.py is being loaded")


@register_command("/bots")
async def bots_handler(session: Any, message: dict, args: List[str]) -> None:
    """
    /bots
    List all configured bots (display name and Telegram handle).
    """
    config = config_loader()
    telegram_conf = config.get("telegram", {})


    bots_list: List[tuple[str, str]] = []  # list of (name, handle)
    for key, conf in telegram_conf.items():
        # Identify bot entries by key prefix
        if not key.startswith("bot_") or not isinstance(conf, dict):
            continue
        # Only include enabled bots
        if not conf.get("enabled", False):
            continue
        name = conf.get("name", key)
        handle = conf.get("handle", "")
        bots_list.append((name, handle))

    if not bots_list:
        await session.send_message("⚠️ No bots configured.")
        return

    lines = ["<b>Configured and enabled bots:</b>"]
    for idx, (name, handle) in enumerate(bots_list):
        # Display index, name, and handle
        if handle:
            lines.append(f"{idx+1}. {name} ({handle})")
        else:
            lines.append(f"{idx+1}. {name}")

    await session.send_message("\n".join(lines), parse_mode="HTML")
