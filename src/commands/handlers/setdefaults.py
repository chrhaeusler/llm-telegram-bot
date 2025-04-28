# src/commands/handlers/setdefaults.py
from src.commands.commands_registry import register_command


@register_command("/setdefaults")
async def setdefaults_handler(session, message, args):
    await session.send_message("⚠️ /setdefaults not yet implemented.")
