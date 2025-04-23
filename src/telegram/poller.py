# src/telegram/poller.py

import asyncio
import datetime
import logging
import os
import time
from typing import Any, Dict, List, Optional

from src.config_loader import config_loader
from src.telegram.client import TelegramClient
from src.telegram.routing import route_message

logger = logging.getLogger(__name__)
# suppress very verbose aiohttp debug logs
logging.getLogger("aiohttp").setLevel(logging.WARNING)

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
        bot_conf = telegram_conf.get(bot_name, {})
        self.chat_id: Optional[int] = bot_conf.get("chat_id")
        if not isinstance(self.chat_id, int):
            raise ValueError(
                f"[PollingLoop] Invalid chat_id for {bot_name}: {self.chat_id!r}"
            )

        logger.debug(f"[PollingLoop] Init bot={bot_name} chat_id={self.chat_id}")

        # polling intervals (per-bot override or global default)
        self.active_interval = bot_conf.get(
            "polling_interval_active", telegram_conf["polling_interval_active"]
        )
        self.idle_interval = bot_conf.get(
            "polling_interval_idle", telegram_conf["polling_interval_idle"]
        )

        # back-off tracking
        self.last_event_time = time.time()
        self.current_interval = self.active_interval
        self.last_update_id: Optional[int] = None

        # prepare download dir (used by client.download_file)
        base = telegram_conf.get("download_path", "tmp")
        self.download_dir = os.path.join(base, bot_name, str(self.chat_id))
        os.makedirs(self.download_dir, exist_ok=True)

        self._running = True

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

    async def handle_update(self, update: Dict[str, Any]) -> None:
        """
        Called for every Telegram update.  Downloads files if present,
        otherwise invokes the router for text messages.
        """
        try:
            logger.info(f"[PollingLoop] Update: {update}")
            if "message" not in update:
                return

            msg = update["message"]
            chat_id = msg["chat"]["id"]
            session = ChatSession(self.client, chat_id)

            # Document handling
            if "document" in msg:
                fid = msg["document"]["file_id"]
                fname = msg["document"]["file_name"]
                logger.info(f"[PollingLoop] Document received: {fname} (file_id={fid})")

                file_info = await self.client.get_file(fid)
                if file_info.get("ok"):
                    path = file_info["result"]["file_path"]
                    # delegate actual download to client
                    dl = await self.client.download_file(path)
                    if not dl.get("ok"):
                        await session.send_message(
                            f"❌ Failed to download {fname}: {dl.get('description')}"
                        )
                else:
                    await session.send_message(
                        f"❌ Could not get details for file: {fname}"
                    )

            # Text routing
            if "text" in msg:
                await route_message(session, msg)

        except Exception as e:
            logger.exception(f"[PollingLoop] Error in handle_update: {e}")
            # try to notify user
            try:
                chat_id = update.get("message", {}).get("chat", {}).get("id")
                if chat_id:
                    session = ChatSession(self.client, chat_id)
                    await session.send_message(f"❌ Internal error: {e}")
            except Exception:
                logger.exception("[PollingLoop] Also failed to send error message")


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
