# src/commands/handlers/start.py

from typing import Any, List

from src.commands.commands_registry import register_command
from src.config_loader import config_loader
from src.session.session_manager import (
    get_max_tokens,
    get_model,
    get_service,
    get_temperature,
    is_paused,
)
from src.utils.logger import logger

# Log that the help handler is being loaded
logger.info("[Start Handler] start.py is being loaded")


@register_command("/start")
async def start_handler(session: Any, message: dict[str, Any], args: List[str]):
    """
    /start
    Interprets the /start command as /bot and returns bot info.
    """
    config = config_loader()
    bot_name = session.client.bot_name
    bot_conf = config.get("telegram", {}).get(bot_name, {})

    # Retrieve bot and chat details
    chat_id = session.chat_id
    display_name = bot_conf.get("name", bot_name)
    is_active = not is_paused(chat_id)
    status = "✅ online" if is_active else "⏸️ offline"

    service = get_service(chat_id)
    model = get_model(chat_id)
    temperature = get_temperature(chat_id)
    maxtoken = get_max_tokens(chat_id)

    # Return bot info
    bot_info = f"""
    General Purpose ({display_name})
    {status}
    Service: {service}
    Model: {model}
    Temp: {temperature}
    Tokens: {maxtoken}
    """

    await session.send_message(bot_info)
    logger.info(f"[start] Bot info sent to {chat_id}")
