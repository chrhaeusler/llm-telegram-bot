# src/commands/handlers/sr.py
from src.commands.commands_registry import register_command


@register_command("/sr")
async def saveresponse_handler(session, message, args):
    await session.send_message("⚠️ /sr not yet implemented.")
