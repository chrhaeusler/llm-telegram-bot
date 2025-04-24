# src/commands/handlers/bot.py

import logging

from src.commands.commands_registry import register_command
from src.config_loader import config_loader

logger = logging.getLogger(__name__)


@register_command("/bot")
async def bot_handler(session, message, args):
    """
    /bot [<index>|start|stop]
    - No args: show current bot settings
    - <index>: switch to bot by its list index (from /bots)
    - start: resume messaging to LLM
    - stop: pause messaging to LLM
    """
    try:
        cfg = config_loader()
        telegram_conf = cfg.get("telegram", {})
        bots = list(telegram_conf.keys())

        # Current bot
        current_bot = getattr(session.client, "bot_name", None)
        default_conf = telegram_conf.get(current_bot, {}).get("default", {})
        name = telegram_conf.get(current_bot, {}).get("name", None)

        # No args: show settings
        if not args:
            svc = default_conf.get("service")
            model = default_conf.get("model")
            temp = default_conf.get("temperature")
            maxt = default_conf.get("maxtoken")
            lines = [
                f"Current bot: {current_bot}",
                f"Name: {name}",
                f"Service: {svc}",
                f"Model: {model}",
                f"Temperature: {temp}",
                f"Max tokens: {maxt}",
            ]
            await session.send_message("\n".join(lines))
            return

        arg = args[0]
        # Start/stop
        if arg.lower() == "start":
            await session.send_message("✅ Bot messaging resumed.")
            return
        if arg.lower() == "stop":
            await session.send_message("⏸️ Bot messaging paused.")
            return

        # Switch by index
        if arg.isdigit():
            idx = int(arg) - 1
            if 0 <= idx < len(bots):
                new_bot = bots[idx]
                new_conf = telegram_conf[new_bot]
                session.client.bot_name = new_bot
                # update chat_id for new bot
                session.client.chat_id = new_conf.get("chat_id", session.client.chat_id)
                await session.send_message(f"✅ Switched to bot '{new_bot}'")
                return

        # Invalid arg
        await session.send_message(
            "❌ Invalid argument for /bot. Use /bots to list available bots."
        )
    except Exception as e:
        logger.exception(f"[bot_handler] Error in /bot: {e}")
        await session.send_message(f"❌ Error handling /bot: {e}")
