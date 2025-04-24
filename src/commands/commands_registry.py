# src/telegram/commands_registry.py

"""
Defines a commands_registry dictionary to map command strings (like /help) to
handler functions.
Provides a @register_command("/name") decorator to easily attach functions to commands.
Adds get_registered_commands() to fetch a list of what’s implemented.
"""

import logging
from typing import Awaitable, Callable, Optional

logger = logging.getLogger(__name__)

CommandHandler = Callable[..., Awaitable[None]]
_command_registry: dict[str, CommandHandler] = {}


def register_command(name: str):
    """Decorator to register a command handler."""

    def decorator(func: CommandHandler):
        # Normalize key by stripping leading slash
        key = name.lstrip("/")
        logger.debug(f"Registering command: {key} with handler {func.__name__}")
        _command_registry[key] = func
        return func

    return decorator


def get_command_handler(name: str) -> Optional[CommandHandler]:
    """Return the handler for a given command name, or None if not implemented."""
    handler = _command_registry.get(name)
    if handler is None:
        logger.warning(f"Command not implemented: {name}")
    return handler


def is_command_implemented(name: str) -> bool:
    logger.info("[Registry] Checking if command is implemented: %s", name)  # Debug log
    return name in _command_registry


async def dummy_handler(*args, **kwargs) -> None:
    """Placeholder handler for known but unimplemented commands."""
    if "session" in kwargs:
        await kwargs["session"].send_message(
            "⚠️ This command is known but not yet implemented."
        )


def get_known_handlers() -> dict[str, CommandHandler]:
    """Return a copy of all known command handlers."""
    return _command_registry.copy()
