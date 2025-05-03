# tests/helpers/command_utils.py
import importlib
import pkgutil
import llm_telegram_bot.commands.handlers


# def import_all_handlers():
#     package = src.llm_telegram_bot.commands.handlers
#     prefix = package.__name__ + "."
#     for _, module_name, _ in pkgutil.iter_modules(package.__path__, prefix):
#         importlib.import_module(module_name)


# # tests/helpers/command_utils.py

import importlib


def import_all_handlers():
    """
    Force Python to load every handler module under src.llm_telegram_bot.commands.handlers
    so that their @register_command() decorators fire.
    """
    modules = [
        "bot",
        "bots",
        "help",
        "model",
        "models",
        "service",
        "status",
        "temperature",
        "tokens",
        # add any others you’ve created, e.g. "undo", "defaults",…
    ]
    for m in modules:
        importlib.import_module(f"src.llm_telegram_bot.commands.handlers.{m}")
