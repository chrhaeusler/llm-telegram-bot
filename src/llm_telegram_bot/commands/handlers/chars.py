# src/commands/handlers/chars.py
from typing import Any, List

from llm_telegram_bot.commands.commands_registry import register_command

from .char import char_handler


@register_command("/chars")
async def chars_alias(session: Any, message: dict, args: List[str]):
    # Force list view regardless of args
    await char_handler(session, message, ["list"])
