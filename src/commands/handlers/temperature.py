# File: src/commands/handlers/temperature.py

import logging
from typing import Any, Dict, List

from src.commands.commands_registry import register_command

logger = logging.getLogger(__name__)


@register_command("/temp")
async def handle_temperature(
    session: Any, message: Dict[str, Any], args: List[str]
) -> None:
    """
    /temperature [value]
    Gets or sets the default temperature for the active chat session.
    """
    if not args:
        await session.send_message(f"🌡 Current temperature: {session.temperature:.2f}")
        return

    try:
        new_temp = float(args[0])
        if not 0.0 <= new_temp <= 2.0:
            raise ValueError("Temperature must be between 0.0 and 2.0")

        session.temperature = new_temp
        await session.send_message(f"✅ Temperature set to {new_temp:.2f}")

    except ValueError as e:
        await session.send_message(f"⚠️ Invalid temperature: {e}")
