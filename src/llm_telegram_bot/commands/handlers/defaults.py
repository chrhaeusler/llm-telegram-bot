# src/commands/handlers/defaults.py
from llm_telegram_bot.commands.commands_registry import register_command


@register_command("/defaults")
async def defaults_handler(session, message, args):
    await session.send_message("⚠️ /defaults not yet implemented.")
