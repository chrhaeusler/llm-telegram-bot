# src/commands/handlers/savethis.py
from src.commands.commands_registry import register_command


@register_command("/savethis")
async def savethis_handler(session, message, args):
    await session.send_message("⚠️ /savethis not yet implemented.")
