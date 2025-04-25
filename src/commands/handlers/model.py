# src/commands/handlers/models.py

import logging

from src.commands.commands_registry import register_command
from src.config_loader import config_loader

logger = logging.getLogger(__name__)


@register_command("/model")
async def models_handler(session, message, args):
    """List available models for the current LLM service."""
    try:
        cfg = config_loader()
        telegram_conf = cfg.get("telegram", {})
        # Locate this chat's bot configuration
        bot_conf = None
        for conf in telegram_conf.values():
            # Skip non-dict entries
            if not isinstance(conf, dict):
                continue
            if conf.get("chat_id") == session.chat_id:
                bot_conf = conf
                break

        if not bot_conf:
            await session.send_message("⚠️ Bot configuration not found for this chat.")
            return

        svc_name = bot_conf.get("default", {}).get("service")
        if not svc_name:
            await session.send_message("⚠️ No default service configured for this bot.")
            return

        services_conf = cfg.get("services", {})
        svc_conf = services_conf.get(svc_name, {})
        models = svc_conf.get("models") or svc_conf.get("available_models") or []

        if not models:
            await session.send_message(
                f"⚠️ No models configured for service '{svc_name}'."
            )
            return

        lines = [f"Models for service '{svc_name}':"]
        for idx, model in enumerate(models, start=1):
            lines.append(f"{idx}. {model}")

        await session.send_message("\n".join(lines))
    except Exception as e:
        logger.exception(f"[models_handler] Error listing models: {e}")
        await session.send_message(f"❌ Could not list models: {e}")
