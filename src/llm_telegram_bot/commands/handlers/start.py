# src/commands/handlers/start.py

from typing import Any, Dict, List

from llm_telegram_bot.commands.commands_registry import register_command
from llm_telegram_bot.commands.handlers.bot import bot_handler


@register_command("/start")
async def start_handler(session: Any, message: Dict[str, Any], args: List[str]) -> None:
    """
    /start
    Telegram’s initial “hello” command – alias of /bot to show current settings.
    """
    # Just delegate to bot_handler with no args
    await bot_handler(session=session, message=message, args=[])
