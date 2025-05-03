# tests/conftest.py
import sys
from pathlib import Path
import importlib
import pkgutil

# Calculate project root
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import the renamed package
import llm_telegram_bot.commands.handlers


def import_all_handlers():
    """Dynamically import all modules in llm_telegram_bot.commands.handlers to trigger @register_command."""
    package = llm_telegram_bot.commands.handlers
    prefix = package.__name__ + "."
    for _, modname, _ in pkgutil.iter_modules(package.__path__, prefix):
        importlib.import_module(modname)
