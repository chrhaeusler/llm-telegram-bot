# src/commands/handlers/services.py

import logging

from src.commands.commands_registry import register_command
from src.config_loader import config_loader

logger = logging.getLogger(__name__)


@register_command("/services")
async def services_handler(session, message, args):
    """List all available LLM services."""
    try:
        cfg = config_loader()
        services_conf = cfg.get("services", {})
        if not services_conf:
            await session.send_message("⚠️ No services configured.")
            return

        lines = ["Available services:"]
        for idx, service_name in enumerate(services_conf.keys(), start=1):
            lines.append(f"{idx}. {service_name}")

        await session.send_message("\n".join(lines))
    except Exception as e:
        logger.exception(f"[services_handler] Error listing services: {e}")
        await session.send_message(f"❌ Could not list services: {e}")
