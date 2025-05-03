# File: src/commands/handlers/undo.py

from typing import Any, Dict, List

from llm_telegram_bot.commands.commands_registry import register_command


@register_command("/undo")
async def undo_handler(session: Any, message: Dict[str, Any], args: List[str]) -> None:
    """
    /undo
    Undo the last configuration change (not yet implemented).
    """
    await session.send_message("⚠️ /undo not yet implemented.")
