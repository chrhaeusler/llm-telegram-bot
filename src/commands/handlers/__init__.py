# src/commands/handlers/__init__.py

import importlib
import pkgutil
from pathlib import Path

# automatically find and import every .py (except __init__.py)
package_dir = Path(__file__).parent
for module in pkgutil.iter_modules([str(package_dir)]):
    importlib.import_module(f"{__name__}.{module.name}")
