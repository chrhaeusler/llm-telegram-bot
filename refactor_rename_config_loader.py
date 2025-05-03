import os
import re
from pathlib import Path

SOURCE_DIR = Path("src/llm_telegram_bot")
OLD_NAME = "config_loader"
NEW_NAME = "load_config"
MODULE_IMPORT_PATH = "llm_telegram_bot.config.config_loader"

def replace_in_file(file_path: Path):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    original_content = content

    # Replace function calls: config_loader(...) → load_config(...)
    content = re.sub(rf"\b{OLD_NAME}\s*\(", f"{NEW_NAME}(", content)

    # Replace specific imports: from llm_telegram_bot.config.config_loader import config_loader → load_config
    content = re.sub(
        rf"(from\s+{re.escape(MODULE_IMPORT_PATH)}\s+import\s+){OLD_NAME}",
        rf"\1{NEW_NAME}",
        content,
    )

    # Optionally fix indirect imports like: from llm_telegram_bot.config import config_loader
    content = re.sub(
        rf"(from\s+llm_telegram_bot\.config\s+import\s+){OLD_NAME}",
        rf"from {MODULE_IMPORT_PATH} import {NEW_NAME}",
        content,
    )

    if content != original_content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"✔ Updated: {file_path}")

def walk_and_replace(directory: Path):
    for file in directory.rglob("*.py"):
        replace_in_file(file)

if __name__ == "__main__":
    print("🔍 Scanning for outdated config_loader usage...")
    walk_and_replace(SOURCE_DIR)
    print("✅ Refactor complete!")
