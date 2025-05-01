# src/commands/handlers/service.py


from src.commands.commands_registry import register_command
from src.config_loader import config_loader
from src.session import session_manager
from src.utils.logger import logger

# Log that the help handler is being loaded
logger.info("[Service Handler] service.py is being loaded")


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
            lines = [f"<b>Current: {current or 'None'}</b>", "Available:"]
            for i, name in enumerate(services_conf.keys(), 1):
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
        session_manager.set_service(chat_id, new_service)

        # Get the per-service config block
        new_conf = services_conf.get(new_service, {})

        # Update the model in session state
        from src.session.session_manager import set_model

        default_model = new_conf.get("model")
        if default_model:
            set_model(chat_id, default_model)

        # Optionally update temperature and maxtoken too
        temperature = new_conf.get("temperature", 0.7)
        maxtoken = new_conf.get("maxtoken", 4096)

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
