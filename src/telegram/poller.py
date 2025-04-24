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
from src.telegram.client import TelegramClient
from src.telegram.routing import route_message

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
    A tiny wrapper so commands and routing only ever see a 'session'
    that has a send_message(text) coroutine.  Under the hood we
    sync chat_id into the shared TelegramClient.
    """

    def __init__(self, client: TelegramClient, chat_id: int):
        self.client = client
        self.chat_id = chat_id

    async def send_message(self, text: str) -> None:
        # Ensure the TelegramClient will target the right chat
        self.client.chat_id = self.chat_id
        await self.client.send_message(text)


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
                logger.debug(f"[PollingLoop] getUpdates attempt {attempts}")
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
        2) If it's text, pass to route_message → either a /command or LLM call.
        """
        try:
            msg = update.get("message")
            if not msg:
                logging.debug("[PollingLoop] update with no message, skipping")
                return

            chat_id = msg["chat"]["id"]
            from src.telegram.poller import (
                ChatSession,  # ensure ChatSession is in scope
            )

            session = ChatSession(self.client, chat_id)

            # ── Document (Attachment) Handling ────────────────────────────────
            if "document" in msg:
                file_id = msg["document"]["file_id"]
                file_name = msg["document"]["file_name"]
                logging.info(f"[PollingLoop] Document → {file_name} (id={file_id})")

                details = await self.client.get_file(file_id)
                if details.get("ok") and "result" in details:
                    file_path = details["result"]["file_path"]
                    await self.client.download_file(
                        file_path=file_path, original_name=file_name
                    )
                else:
                    logging.error(f"[PollingLoop] get_file failed: {details}")
                    await session.send_message(f"❌ Could not retrieve '{file_name}'")
                return  # Do not fall through to text handling

            # ── Text (Free Input or Slash Command) ────────────────────────────
            if "text" in msg:
                await route_message(
                    session=session,
                    message=msg,
                    llm_call=self.llm_service.send_prompt,
                    model=self.bot_config["default"]["model"],
                    temperature=self.bot_config["default"]["temperature"],
                    maxtoken=self.bot_config["default"]["maxtoken"],
                )

        except Exception as e:
            logging.exception(f"[PollingLoop] error in handle_update: {e}")
            # best effort to let the user know
            try:
                session = ChatSession(self.client, update["message"]["chat"]["id"])
                await session.send_message(f"❌ Error processing update: {e}")
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
