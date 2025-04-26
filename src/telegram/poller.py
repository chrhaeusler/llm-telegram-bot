# src/telegram/poller.py

import asyncio
import datetime
import logging
import os
import time
from typing import Any, Dict, List, Optional

from src.commands.handlers import help  # noqa: F401
from src.config_loader import config_loader
from src.services.service_groq import GroqService
from src.services.service_mistral import MistralService
from src.services.services_base import BaseLLMService
from src.session.session_manager import get_maxtoken, get_session, get_temperature
from src.telegram.client import TelegramClient
from src.utils.markdown import safe_message

logger = logging.getLogger(__name__)
# suppress very verbose aiohttp debug logs

logging.basicConfig(
    level=logging.DEBUG,  # Ensure DEBUG messages are logged
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# after this many seconds of no activity, back off
ACTIVE_PERIOD = 300


class ChatSession:
    """
    Wrapper for a chat session that provides:
      - send_message(text): handles Telegram message sending
      - access to session state like active_service, active_bot, etc.
    """

    def __init__(self, client: TelegramClient, chat_id: int):
        self.client = client
        self.chat_id = chat_id
        self._session = get_session(chat_id)  # ← the real stateful session

    async def send_message(self, text: str) -> None:
        self.client.chat_id = self.chat_id
        text = safe_message(text)
        await self.client.send_message(text)

    # Optional passthroughs
    @property
    def active_service(self):
        return self._session.active_service

    @property
    def active_bot(self):
        return self._session.active_bot

    @property
    def messaging_paused(self):
        return self._session.messaging_paused


class PollingLoop:
    def __init__(self, bot_name: str, client: TelegramClient, config: Dict[str, Any]):
        self.bot_name = bot_name
        self.client = client
        self.config = config

        telegram_conf = config["telegram"]
        self.bot_config = telegram_conf.get(bot_name, {})
        self.chat_id: Optional[int] = self.bot_config.get("chat_id")
        if not isinstance(self.chat_id, int):
            raise ValueError(
                f"[PollingLoop] Invalid chat_id for {bot_name}: {self.chat_id!r}"
            )

        logger.debug(f"[PollingLoop] Init bot={bot_name} chat_id={self.chat_id}")

        # polling intervals (per-bot override or global default)
        self.active_interval = self.bot_config.get(
            "polling_interval_active", telegram_conf["polling_interval_active"]
        )
        self.idle_interval = self.bot_config.get(
            "polling_interval_idle", telegram_conf["polling_interval_idle"]
        )

        # state trackers
        self.last_event_time = time.time()
        self.current_interval = self.active_interval
        self.last_update_id = None
        self._running = True

        # prepare download dir (used by client.download_file)
        base = telegram_conf.get("download_path", "tmp")
        self.download_dir = os.path.join(base, bot_name, str(self.chat_id))
        os.makedirs(self.download_dir, exist_ok=True)

        # instantiate the LLM service for this bot
        svc_name = self.bot_config["default"]["service"]
        svc_conf = config["services"].get(svc_name)
        # explicitly tell MyPy the intended interface
        if svc_conf is None:
            raise ValueError(f"No configuration for service '{svc_name}'")
        self.llm_service: BaseLLMService
        if svc_name == "groq":
            self.llm_service = GroqService(config=svc_conf)
        elif svc_name == "mistral":
            self.llm_service = MistralService(config=svc_conf)
        else:
            raise ValueError(f"Unsupported service '{svc_name}'")

        logging.debug(
            f"[PollingLoop] Initialized bot={bot_name}, "
            f"service={svc_name}, model={self.bot_config['default']['model']}"
        )

    def stop(self) -> None:
        self._running = False

    async def run(self) -> None:
        logger.info(f"[PollingLoop] Starting poll loop for '{self.bot_name}'")
        while self._running:
            try:
                updates = await self._get_updates_with_retries()

                if updates.get("ok") and updates.get("result"):
                    for upd in updates["result"]:
                        self.last_update_id = upd["update_id"] + 1
                        await self.handle_update(upd)

                    # reset back to active rate
                    self.last_event_time = time.time()
                    if self.current_interval != self.active_interval:
                        logger.info(
                            f"[PollingLoop] Activity → switching to active interval {self.active_interval}s"
                        )
                    self.current_interval = self.active_interval

                else:
                    idle = time.time() - self.last_event_time
                    if idle > ACTIVE_PERIOD:
                        new_int = min(
                            self.current_interval + self.active_interval,
                            self.idle_interval,
                        )
                        if new_int != self.current_interval:
                            last_seen = datetime.datetime.fromtimestamp(
                                self.last_event_time
                            ).strftime("%Y-%m-%d %H:%M:%S")
                            logger.info(
                                f"[PollingLoop] No activity for {int(idle)}s (last at {last_seen}), backing off to {new_int}s"
                            )
                        self.current_interval = new_int

                await asyncio.sleep(self.current_interval)

            except asyncio.CancelledError:
                logger.info("[PollingLoop] Cancelled by shutdown signal.")
                break
            except Exception:
                logger.exception(
                    "[PollingLoop] Unexpected error, sleeping idle interval"
                )
                await asyncio.sleep(self.idle_interval)

    async def _get_updates_with_retries(self) -> Dict[str, Any]:
        attempts, max_attempts = 0, 5
        delay = 5
        while attempts < max_attempts:
            attempts += 1
            try:
                # logger.debug(f"[PollingLoop] getUpdates attempt {attempts}")
                return await self.client.get_updates(offset=self.last_update_id)
            except Exception as e:
                logger.error(
                    f"[PollingLoop] get_updates failed ({attempts}/{max_attempts}): {e}"
                )
                if attempts >= max_attempts:
                    logger.error(
                        "[PollingLoop] All retries failed, returning {{'ok': False}}"
                    )
                    return {"ok": False}
                await asyncio.sleep(delay)
        return {"ok": False}

    async def handle_update(self, update: dict[str, Any]):
        """
        Called for every incoming update.
        1) If it's a document, fetch & download it.
        2) If it's text, route commands or send to the LLM service.
        """
        try:
            msg = update.get("message")
            if not msg:
                logger.debug("[PollingLoop] update with no message, skipping")
                return

            chat_id = msg["chat"]["id"]
            # Wrap our TelegramClient + chat into a ChatSession helper
            from src.telegram.poller import ChatSession

            session = ChatSession(self.client, chat_id)

            # Bring in all helpers
            from src.llm.dispatcher import get_service_for_name
            from src.session.session_manager import get_session, is_paused, set_service
            from src.telegram.routing import route_message

            state = get_session(chat_id)

            # ── Initialize default service if not set ─────────────────────────
            if state.active_service is None:
                default_svc = self.config.get("factorydefault", {}).get(
                    "service"
                ) or next(iter(self.config.get("services", {})), None)
                set_service(chat_id, default_svc)

            # ── Document Handling ───────────────────────────────────────────────
            if "document" in msg:
                file_id = msg["document"]["file_id"]
                file_name = msg["document"]["file_name"]
                logger.info(f"[PollingLoop] Document → {file_name} (id={file_id})")

                details = await self.client.get_file(file_id)
                if details.get("ok") and "result" in details:
                    path = details["result"]["file_path"]
                    await self.client.download_file(
                        file_path=path, original_name=file_name
                    )
                else:
                    logger.error(f"[PollingLoop] get_file failed: {details}")
                    await session.send_message(f"❌ Could not retrieve '{file_name}'")
                return  # skip further processing

            # ── Text Handling ──────────────────────────────────────────────────
            if "text" in msg:
                text = msg["text"].strip()

                # Slash‐command?
                # error: "Unexpected keyword argument "session" for "route_message""
                if text.startswith("/"):
                    await route_message(
                        session=session,
                        message=msg,
                        llm_call=None,  # ignored for commands
                        model="",  # ignored
                        temperature=0.0,  # ignored
                        maxtoken=0,  # ignored
                    )
                    return

                # Paused?
                if is_paused(chat_id):
                    logger.info(
                        f"[PollingLoop] Messaging paused for {chat_id}, skipping LLM"
                    )
                    return

                # ── Build LLM parameters from active service ────────────────────────────
                bot_def = self.bot_config["default"]
                bot_def_service = bot_def.get("service")
                bot_def_model = bot_def.get("model")
                bot_def_temp = bot_def.get("temperature")
                bot_def_max = bot_def.get("maxtoken")

                svc_name = state.active_service
                assert svc_name is not None, "active_service was not initialized"
                svc_conf = self.config.get("services", {}).get(svc_name, {})

                from src.session.session_manager import get_model

                # 1) Manual override for model wins
                manual_model = get_model(chat_id)
                if manual_model:
                    model = manual_model
                elif svc_name == bot_def_service:
                    model = bot_def_model
                else:
                    model = svc_conf.get("model", bot_def_model)

                # 2) Manual override for temperature and tokens
                manual_temp = get_temperature(chat_id)
                manual_tokens = get_maxtoken(chat_id)

                if manual_temp is not None:
                    temperature = manual_temp
                else:
                    if svc_name == bot_def_service:
                        temperature = bot_def_temp
                    else:
                        temperature = svc_conf.get("temperature", bot_def_temp)

                if manual_tokens is not None:
                    maxtoken = manual_tokens
                else:
                    if svc_name == bot_def_service:
                        maxtoken = bot_def_max
                    else:
                        maxtoken = svc_conf.get("maxtoken", bot_def_max)

                # Instantiate the correct LLM service and send prompt
                service = get_service_for_name(svc_name, svc_conf)
                reply = await service.send_prompt(
                    prompt=text,
                    model=model,
                    temperature=temperature,
                    maxtoken=maxtoken,
                )
                await session.send_message(reply)

        except Exception as e:
            logger.exception(f"[PollingLoop] error in handle_update: {e}")
            # best-effort fallback message
            try:
                fallback = ChatSession(self.client, update["message"]["chat"]["id"])
                await fallback.send_message(f"❌ Error processing update: {e}")
            except:
                pass


if __name__ == "__main__":
    import sys

    async def main():
        config = config_loader()
        bot_names = sys.argv[1:] or list(config["telegram"].keys())
        # only pick keys starting with "bot_" and marked enabled
        bot_names = [
            n
            for n in bot_names
            if n.startswith("bot_")
            and config["telegram"].get(n, {}).get("enabled", False)
        ]

        tasks: List[asyncio.Task] = []
        for bot in bot_names:
            logger.info(f"[BOOT] Initializing {bot}")
            conf = config["telegram"][bot]
            client = TelegramClient(
                token=conf["token"],
                chat_id=conf["chat_id"],
                bot_name=bot,
                download_path=config["telegram"]["download_path"],
                chat_history_path=config["telegram"]["chat_history_path"],
            )
            await client.init_session()
            poller = PollingLoop(bot, client, config)
            tasks.append(asyncio.create_task(poller.run()))

        if tasks:
            logger.info(f"[Main] Running {len(tasks)} bot(s): {', '.join(bot_names)}")
            await asyncio.gather(*tasks)
        else:
            logger.warning("[Main] No bots started; check your config.")

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    asyncio.run(main())
