# src/commands/handlers/models.py

import logging
from typing import Any, Dict, List

from src.commands.commands_registry import register_command
from src.config_loader import config_loader
from src.session.session_manager import get_model, get_session

# Create logger
logger = logging.getLogger(__name__)

# Log that the help handler is being loaded
logger.info("[Help Handler] models.py is being loaded")


@register_command("/models")
async def models_handler(session: Any, message: Dict[str, Any], args: List[str]) -> None:
    """
    /models
    List all models available for the current active service.
    """
    cfg = config_loader()
    bot_name = session.client.bot_name

    # 1) Determine which service we’re on
    state = get_session(session.chat_id)
    svc = state.active_service or cfg["telegram"][bot_name]["default"]["service"]

    # 2) Fetch that service’s model map from your JSON
    svc_models_map: Dict[str, Dict] = cfg.get("models_info", {}).get(svc, {})

    # 3) If empty → warn
    if not svc_models_map:
        return await session.send_message(f"⚠️ No models configured for service '{svc}'")

    # 4) Build the list, marking the currently active model
    current_model = get_model(session.chat_id) or cfg["telegram"][bot_name]["default"]["model"]
    lines = [f"<b>Models for {svc}:</b>"]
    for idx, (model_name, meta) in enumerate(svc_models_map.items(), start=1):
        mark = "✅" if model_name == current_model else "  "
        # short_desc = meta.get("short", "")
        lines.append(f"{idx}. {mark} {model_name:<30}")  # " — {short_desc}")

    await session.send_message("\n".join(lines), parse_mode="HTML")
