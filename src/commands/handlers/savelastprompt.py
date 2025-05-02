import os
import time
from pathlib import Path
from typing import Any, List

from src.commands.commands_registry import register_command
from src.config_loader import config_loader
from src.session.session_manager import get_memory
from src.utils.logger import logger


@register_command("/slp")
async def slp_handler(session: Any, message: dict, args: List[str]):
    # 1) Fetch last prompt
    mem = get_memory(session.chat_id).get("last_prompt", [])
    if not mem:
        return await session.send_message("⚠️ No prompt in memory to save.")
    prompt = mem[-1]

    ts = time.strftime("%Y-%m-%d_%H-%M-%S")

    # 2) Determine filename
    if args:
        fname = Path(args[0]).name
        fname = f"{ts}_{fname}"
    else:
        fname = f"{ts}_saved-prompt.txt"

    # 3) Save into the same download_path/<bot>/<chat_id> dir
    cfg = config_loader()
    bot_name = session.client.bot_name
    path_root = cfg["telegram"][bot_name].get("download_path", "tmp")
    outdir = os.path.join(path_root, bot_name, str(session.chat_id))
    os.makedirs(outdir, exist_ok=True)
    full = os.path.join(outdir, fname)

    try:
        with open(full, "w", encoding="utf-8") as f:
            f.write(prompt)
        logger.info(f"[slp] Saved last prompt to {full}")
        await session.send_message(f"✅ Saved last prompt as `{fname}`")
    except Exception as e:
        logger.exception("[slp] Error saving prompt")
        await session.send_message(f"❌ Could not save: {e}")
