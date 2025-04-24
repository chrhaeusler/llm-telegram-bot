# src/commands/handlers/bots.py

import logging

from src.commands.commands_registry import register_command
from src.config_loader import config_loader

logger = logging.getLogger(__name__)


@register_command("/bots")
async def bots_handler(session, message, args):
    """List all available bots and their enabled status."""
    try:
        cfg = config_loader()
        telegram_conf = cfg.get("telegram", {})
        if not telegram_conf:
            await session.send_message("⚠️ No bots configured.")
            return

        lines = ["Available bots:"]
        for idx, (bot_name, bot_conf) in enumerate(telegram_conf.items(), start=1):
            enabled = bot_conf.get("enabled", False)
            status = "enabled" if enabled else "disabled"
            lines.append(f"{idx}. {bot_name} ({status})")

        await session.send_message("\n".join(lines))
    except Exception as e:
        logger.exception(f"[bots_handler] Error listing bots: {e}")
        await session.send_message(f"❌ Could not list bots: {e}")
