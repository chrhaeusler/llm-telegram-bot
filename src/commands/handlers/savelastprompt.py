# src/commands/handlers/su.py
from src.commands.commands_registry import register_command


@register_command("/slp")
async def saveuser_handler(session, message, args):
    await session.send_message("⚠️ /slp not yet implemented.")
