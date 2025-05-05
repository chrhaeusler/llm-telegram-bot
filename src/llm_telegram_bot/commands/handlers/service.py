# src/commands/handlers/service.py

from typing import Any, List

from llm_telegram_bot.commands.commands_registry import register_command
from llm_telegram_bot.config.config_loader import load_config
from llm_telegram_bot.session import session_manager
from llm_telegram_bot.utils.logger import logger

# Log that the service handler is being loaded
logger.info("[Service Handler] service.py is being loaded")


@register_command("/service")
@register_command("/services")  # Alias for /service list
async def service_handler(session: Any, message: dict[str, Any], args: List[str]) -> None:
    """
    /service [<name>|<index>]
    Show current + available services, or switch to a different one.
    """
    try:
        chat_id = session.chat_id
        bot_name = session.bot_name
        cfg = load_config()
        services_conf = cfg.services

        if not services_conf:
            await session.send_message("⚠️ No services configured.")
            return

        service_names = list(services_conf.keys())
        current = session.active_service

        # Show current service and available options
        if not args or (args and args[0].lower() == "list"):
            lines = ["<b>Available services:</b>"]
            for i, name in enumerate(service_names, 1):
                if name == current:
                    lines.append(f"<b>{i}. {name}</b> 👈")
                else:
                    lines.append(f"{i}. {name}")
            await session.send_message("\n".join(lines), parse_mode="HTML")
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
        session_manager.set_service(chat_id, bot_name, new_service)

        # Get the per-service config block
        new_conf = services_conf[new_service]  # Direct access to the config block

        # Update the model in session state
        from llm_telegram_bot.session.session_manager import set_model

        default_model = new_conf.model  # Accessing attribute directly
        if default_model:
            set_model(chat_id, bot_name, default_model)

        # Optionally update temperature and maxtoken too
        temperature = new_conf.temperature if hasattr(new_conf, "temperature") else 0.7
        maxtoken = new_conf.maxtoken if hasattr(new_conf, "maxtoken") else 4096

        session.model = default_model
        session.temperature = temperature
        session.maxtoken = maxtoken

        await session.send_message(
            f"✅ Switched to\n<b>{new_service}</b>\n"
            f"Model: {default_model}\n"
            f"Temp: {temperature}\n"
            f"Tokens: {maxtoken}",
            parse_mode="HTML",
        )

    except Exception as e:
        logger.exception("[/service] Error handling service switch")
        await session.send_message(f"❌ Could not change service: {e}")
