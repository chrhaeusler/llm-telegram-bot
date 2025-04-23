# src/telegram/command_registry.py

# A simple dictionary to map command names (e.g., '/help') to functions
"""
Defines a command_registry dictionary to map command strings (like /help) to
handler functions; Provides a @register_command("/name") decorator to easily attach
functions to commands; Adds get_registered_commands() to fetch a list of
what’s implemented.
"""
# This dictionary holds the mapping from command name to handler function
# src/telegram/command_registry.py

from typing import Awaitable, Callable

CommandHandler = Callable[..., Awaitable[str]]
_command_registry: dict[str, CommandHandler] = {}


def register_command(name: str):
    """Decorator to register a command handler."""

    def decorator(func: CommandHandler):
        _command_registry[name] = func
        return func

    return decorator


def get_command_handler(name: str) -> CommandHandler | None:
    """Return the handler for a given command name, or None if not implemented."""
    return _command_registry.get(name)


def is_command_implemented(name: str) -> bool:
    return name in _command_registry


async def dummy_handler(*args, **kwargs) -> str:
    return "Sorry, this command is known but not yet implemented."


def get_known_handlers() -> dict[str, CommandHandler]:
    return _command_registry.copy()
