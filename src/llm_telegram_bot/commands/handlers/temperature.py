# src/commands/handlers/temperature.py

from typing import Any, Dict, List

from llm_telegram_bot.commands.commands_registry import register_command
from llm_telegram_bot.config.config_loader import load_config
from llm_telegram_bot.session.session_manager import (
    get_temperature,
    set_temperature,
)
from llm_telegram_bot.utils.escape_html import html_escape
from llm_telegram_bot.utils.logger import logger

# Log that the help handler is being loaded
logger.info("[Temperature Handler] temperature.py is being loaded")


@register_command("/temp")
async def temperature_handler(session: Any, message: Dict[str, Any], args: List[str]) -> None:
    """
    /temperature [<value>]
    Show or set the current temperature for the LLM model:
      • no value: show current temperature
      • <value>: set temperature to <value>
    """
    chat_id = session.chat_id
    bot_name = session.bot_name

    if not args:
        # No argument, show current temperature
        current_temperature = get_temperature(chat_id, bot_name)
        if current_temperature is None:
            current_temperature = load_config()["telegram"][session.client.bot_name]["default"].get("temperature", 0.0)

        await session.send_message(
            f"Current temperature: <b>{html_escape(str(current_temperature))}</b>",
            parse_mode="HTML",
        )
        return

    try:
        # Try to parse the argument as a float
        new_temperature = float(args[0])
    except ValueError:
        await session.send_message(
            "⚠️ Invalid temperature value. Please provide a valid number.",
            parse_mode="HTML",
        )
        return

    # Set new temperature
    set_temperature(chat_id, bot_name, new_temperature)

    await session.send_message(
        f"✅ Temperature has been set to <b>{html_escape(str(new_temperature))}</b>",
        parse_mode="HTML",
    )
