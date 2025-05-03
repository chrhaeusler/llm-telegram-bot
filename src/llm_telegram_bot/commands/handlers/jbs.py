# src/commands/handlers/jb.py
from llm_telegram_bot.commands.commands_registry import register_command


@register_command("/jbs")
async def sendjailbreak_handler(session, message, args):
    await session.send_message("⚠️ /jbs not yet implemented.")
