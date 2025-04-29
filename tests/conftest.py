# tests/conftest.py
# Ensure the project root is on the Python path so 'src' can be imported as a package
import sys
from pathlib import Path
import importlib
import pkgutil


# Calculate project root
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
# Add the project root so `import src.commands...` works
import src.commands.handlers


def import_all_handlers():
    """Dynamically import all modules in src.commands.handlers to trigger @register_command."""
    package = src.commands.handlers
    prefix = package.__name__ + "."
    for _, modname, _ in pkgutil.iter_modules(package.__path__, prefix):
        importlib.import_module(modname)
