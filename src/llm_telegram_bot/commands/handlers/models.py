# src/llm_telegram_bot/commands/handlers/models.py

from typing import Any, Dict, List

from llm_telegram_bot.commands.commands_registry import register_command
from llm_telegram_bot.config.config_loader import load_config
from llm_telegram_bot.config.schemas import BotConfig, ModelInfo
from llm_telegram_bot.session.session_manager import get_model, get_session
from llm_telegram_bot.utils.logger import logger

logger.info("[Models Handler] models.py is being loaded")


@register_command("/models")
async def models_handler(session: Any, message: Dict[str, Any], args: List[str]) -> None:
    """
    /models
    List all models available for the current active service.
    """
    # Load typed config
    cfg = load_config()  # RootConfig
    tg_cfg = cfg.telegram  # TelegramConfig

    bot_name = session.client.bot_name
    bot_conf: BotConfig | None = tg_cfg.bots.get(bot_name)
    if not bot_conf:
        await session.send_message("❌ Bot configuration not found.")
        return

    # Determine which service we’re on
    sess = get_session(session.chat_id, session.bot_name)
    svc = sess.active_service or bot_conf.default.service

    # Fetch that service’s model map from your JSON
    svc_models_map: Dict[str, ModelInfo] = cfg.models_info.get(svc, {})

    # If no models → warn
    if not svc_models_map:
        await session.send_message(f"⚠️ No models configured for service '{svc}'")
        return

    # Build the list, marking the currently active model
    current_model = get_model(session.chat_id, session.bot_name) or bot_conf.default.model
    lines = [f"<b>Models for {svc}:</b>"]
    for idx, model_name in enumerate(svc_models_map.keys(), start=1):
        mark = "✅" if model_name == current_model else "  "
        lines.append(f"{idx}. {mark} {model_name}")

    await session.send_message("\n".join(lines), parse_mode="HTML")
