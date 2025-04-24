# src/commands/handlers/tokens.py
from src.commands.commands_registry import register_command

@register_command("/tokens")
async def tokens_handler(session, message, args):
    await session.send_message("⚠️ /tokens not yet implemented.")