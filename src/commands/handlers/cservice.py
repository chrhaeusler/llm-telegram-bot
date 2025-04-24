# src/commands/handlers/cservice.py
from src.commands.commands_registry import register_command

@register_command("/cservice")
async def cservice_handler(session, message, args):
    await session.send_message("⚠️ /cservice not yet implemented.")