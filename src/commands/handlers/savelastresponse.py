# src/commands/handlers/sr.py
from src.commands.commands_registry import register_command


@register_command("/slr")
async def saveresponse_handler(session, message, args):
    await session.send_message("⚠️ /slr not yet implemented.")
