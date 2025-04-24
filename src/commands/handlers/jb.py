# src/commands/handlers/jb.py
from src.commands.commands_registry import register_command


@register_command("/jb")
async def sendjailbreak_handler(session, message, args):
    await session.send_message("⚠️ /jb not yet implemented.")
