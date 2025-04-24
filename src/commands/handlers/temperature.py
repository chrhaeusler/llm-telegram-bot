# src/commands/handlers/temp.py
from src.commands.commands_registry import register_command

@register_command("/temp")
async def temp_handler(session, message, args):
    await session.send_message("⚠️ /temp not yet implemented.")