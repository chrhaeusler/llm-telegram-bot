# src/llm_telegram_bot/commands/handlers/users.py
from typing import Any, List

from llm_telegram_bot.commands.commands_registry import register_command

from .user import user_handler


@register_command("/users")
async def users_alias(session: Any, message: dict, args: List[str]):
    # Force list view regardless of args
    await user_handler(session, message, ["list"])
