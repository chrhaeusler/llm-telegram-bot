# src/handlers/savelastresponse.py

import os
import time
from pathlib import Path
from typing import Any, List

from src.commands.commands_registry import register_command
from src.config_loader import config_loader
from src.session.session_manager import get_memory
from src.utils.logger import logger


@register_command("/slr")
async def slr_handler(session: Any, message: dict, args: List[str]):
    # 1) Fetch last response
    mem = get_memory(session.chat_id).get("last_response", [])
    if not mem:
        return await session.send_message("⚠️ No response in memory to save.")
    response = mem[-1]

    # 2) Timestamp prefix
    ts = time.strftime("%Y-%m-%d_%H-%M-%S")

    # 3) Determine filename
    if args:
        fname = Path(args[0]).name
        fname = f"{ts}_{fname}"
    else:
        fname = f"{ts}_saved-response.txt"

    # 4) Determine output directory
    cfg = config_loader()
    bot_name = session.client.bot_name
    path_root = cfg["telegram"][bot_name].get("download_path", "tmp")
    outdir = os.path.join(path_root, bot_name, str(session.chat_id))
    os.makedirs(outdir, exist_ok=True)
    full = os.path.join(outdir, fname)

    # 5) Write to file
    try:
        with open(full, "w", encoding="utf-8") as f:
            f.write(response)
        logger.info(f"[slr] Saved last response to {full}")
        await session.send_message(f"✅ Saved last response as `{fname}`")
    except Exception as e:
        logger.exception("[slr] Error saving response")
        await session.send_message(f"❌ Could not save: {e}")
