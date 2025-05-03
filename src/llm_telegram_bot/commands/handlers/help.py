# src/commands/handlers/help.py

from llm_telegram_bot.commands.commands_loader import format_help_text, load_commands_yaml
from llm_telegram_bot.commands.commands_registry import register_command
from llm_telegram_bot.utils.logger import logger

# Log that the help handler is being loaded
logger.info("[Help Handler] help.py is being loaded")


@register_command("/help")
async def help_handler(session, message, args):  # Change _args to args
    """Handle the /help command and send a formatted help message."""
    logger.info("[Help Handler] Called with args: %s", args)  # Debug log
    try:
        commands = load_commands_yaml()  # Load the available commands
        help_text = format_help_text(commands)  # Format them into a readable list
        await session.send_message(help_text, parse_mode="HTML")  # Send the help message to the user
    except Exception as e:
        logger.error("[Help Handler] Error: %s", e)
        await session.send_message(f"❌ Error loading help: {str(e)}")
