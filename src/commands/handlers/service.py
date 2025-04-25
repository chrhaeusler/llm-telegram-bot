# src/commands/handlers/service.py

import logging

from src.commands.commands_registry import register_command
from src.config_loader import config_loader
from src.session import session_manager

logger = logging.getLogger(__name__)


@register_command("/service")
async def service_handler(session, message, args):
    """
    /service [<name>|<index>]
    Show current + available services, or switch to a different one.
    """
    try:
        chat_id = session.chat_id
        cfg = config_loader()
        services_conf = cfg.get("services", {})

        if not services_conf:
            await session.send_message("⚠️ No services configured.")
            return

        # Show current service and available options
        if not args:
            current = session_manager.get_service(chat_id)
            lines = [f"*{current or 'None'}*", "Available:"]
            for i, name in enumerate(services_conf.keys(), 1):
                lines.append(f"{i}. {name}")
            await session.send_message("\n".join(lines))
            return

        # Determine new service by index or name
        arg = args[0].lower()
        available = list(services_conf.keys())
        if arg.isdigit():
            idx = int(arg) - 1
            if not 0 <= idx < len(available):
                await session.send_message(f"❌ Service index out of range: {arg}")
                return
            new_service = available[idx]
        else:
            if arg not in available:
                await session.send_message(f"❌ Unknown service: {arg}")
                return
            new_service = arg

        # Update service
        session_manager.set_service(chat_id, new_service)

        # Optionally update model, temperature, maxtoken
        new_conf = services_conf.get(new_service, {})
        model = new_conf.get("model")
        temperature = new_conf.get("temperature", 0.7)  # fallback if not set
        maxtoken = new_conf.get("maxtoken", 4096)

        session.model = model
        session.temperature = temperature
        session.maxtoken = maxtoken

        await session.send_message(
            f"✅ Switched to\n*{new_service}*\n"
            f"{model}\n"
            f"Temp: {temperature}\n"
            f"Tokens: {maxtoken}"
        )

    except Exception as e:
        logger.exception("[/service] Error handling service switch")
        await session.send_message(f"❌ Could not change service: {e}")
