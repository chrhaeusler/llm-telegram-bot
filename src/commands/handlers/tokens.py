import logging
from typing import Any, Dict, List

from src.commands.commands_registry import register_command
from src.telegram.poller import ChatSession

logger = logging.getLogger(__name__)


@register_command("/tokens")
async def handle_temperature(
    session: ChatSession, message: Dict[str, Any], args: List[str]
) -> None:
    """
    Get or set the temperature for the model in this session.
    Usage:
      /temperature           → shows current
      /temperature 0.7        → sets new temp
    """
    if not args:
        current_temp = session._session.model_config.temperature
        await session.send_message(f"🌡 Current temperature: `{current_temp}`")
        return

    try:
        new_temp = float(args[0])
        if not (0.0 <= new_temp <= 2.0):
            raise ValueError

        session._session.model_config.temperature = new_temp
        await session.send_message(f"✅ Temperature set to `{new_temp}`")
    except ValueError:
        await session.send_message(
            "⚠️ Invalid temperature. Please provide a number between 0.0 and 2.0.\nExample: `/temperature 0.7`"
        )
