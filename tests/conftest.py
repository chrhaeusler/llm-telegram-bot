# tests/conftest.py
# Ensure the project root is on the Python path so 'src' can be imported as a package
import sys
from pathlib import Path

# Calculate project root (two levels up: tests/conftest.py -> tests/ -> project root)
project_root = Path(__file__).parent.parent.resolve()
# Add the project root so `import src.commands...` works
sys.path.insert(0, str(project_root))
