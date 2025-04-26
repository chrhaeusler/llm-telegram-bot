# src/commands/__init__.py

# Explicitly import handlers so their @register_command decorators run
from src.commands.handlers import (
    bot,
    bots,
    help,
    model,
    models,
    service,
    status,
    temperature,
    tokens,
    undo,
)
