# src/commands/handlers/help.py
import logging

from src.commands.commands_loader import format_help_text, load_commands_yaml
from src.commands.commands_registry import register_command

# Configure logger
logger = logging.getLogger(__name__)
logger.info("[Help Handler] help.py is being loaded")  # Add this at the top of help.py


@register_command("/help")
async def help_handler(session, message, _args):
    """Handle the /help command and send a formatted help message."""
    logger.info("[Help Handler] Called with args: %s", _args)  # Debug log
    try:
        commands = load_commands_yaml()  # Load the available commands
        help_text = format_help_text(commands)  # Format them into a readable list
        await session.send_message(help_text)  # Send the help message to the user
    except Exception as e:
        logger.error("[Help Handler] Error: %s", e)
        await session.send_message(f"❌ Error loading help: {str(e)}")
