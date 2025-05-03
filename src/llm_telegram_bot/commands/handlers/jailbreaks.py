# src/commands/handlers/jailbreaks.py
from llm_telegram_bot.commands.commands_registry import register_command


@register_command("/jails")
async def jailbreaks_handler(session, message, args):
    await session.send_message("⚠️ /jails not yet implemented.")
