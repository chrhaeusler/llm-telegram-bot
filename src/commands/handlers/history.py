# src/commands/handlers/history.py
from src.commands.commands_registry import register_command


@register_command("/history")
async def history_handler(session, message, args):
    await session.send_message("⚠️ /history not yet implemented.")
