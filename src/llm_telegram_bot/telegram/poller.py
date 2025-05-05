# src/telegram/poller.py

import asyncio
import datetime
import os
import time
from typing import Any, Dict, Optional

import llm_telegram_bot.commands.handlers  # noqa: F401
from llm_telegram_bot.config.config_loader import load_config
from llm_telegram_bot.config.schemas import BotConfig, RootConfig
from llm_telegram_bot.llm.dispatcher import get_service_for_name
from llm_telegram_bot.services.service_groq import GroqService
from llm_telegram_bot.services.service_mistral import MistralService
from llm_telegram_bot.session.session_manager import (
    add_memory,
    get_effective_llm_params,
    get_session,
    is_paused,
    set_max_tokens,
    set_model,
    set_service,
    set_temperature,
)
from llm_telegram_bot.telegram.client import TelegramClient
from llm_telegram_bot.utils.logger import logger
from llm_telegram_bot.utils.message_utils import split_message


class ChatSession:
    """
    Wrapper for a chat session that provides:
      - send_message(text): handles Telegram message sending
      - access to session state like active_service, active_bot, etc.
    """

    def __init__(self, client: TelegramClient, chat_id: int, bot_name: str):
        self.client = client
        self.chat_id = chat_id
        self.bot_name = bot_name
        self._session = get_session(chat_id, bot_name)

    async def send_message(self, text: str, *, parse_mode: str = "MarkdownV2", **kwargs) -> None:
        # ensure client knows which chat
        self.client.chat_id = self.chat_id
        # forward text and parse_mode+kwargs to the client
        await self.client.send_message(text, parse_mode=parse_mode, **kwargs)

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

    @property
    def active_char(self) -> Optional[str]:
        return self._session.active_char

    @property
    def active_user(self) -> Optional[str]:
        return self._session.active_user

    @property
    def active_char_data(self):
        return self._session.active_char_data

    @property
    def active_user_data(self):
        return self._session.active_user_data


class PollingLoop:
    def __init__(self, bot_name: str, client: TelegramClient, config: RootConfig):
        self.bot_name = bot_name
        self.client = client
        self.config = config

        tg_cfg = config.telegram  # TelegramConfig
        bot_cfg: BotConfig = tg_cfg.bots.get(bot_name)
        if not bot_cfg or not bot_cfg.enabled:
            raise ValueError(f"No enabled config for bot '{bot_name}'")

        self.bot_config = bot_cfg
        self.chat_id = bot_cfg.chat_id

        # polling intervals: bot override → global
        self.polling_active_period = getattr(
            bot_cfg,
            "polling_active_period",
            tg_cfg.polling_active_period,
        )
        self.polling_interval_active = getattr(
            bot_cfg,
            "polling_interval_active",
            tg_cfg.polling_interval_active,
        )
        self.polling_interval_idle = getattr(
            bot_cfg,
            "polling_interval_idle",
            tg_cfg.polling_interval_idle,
        )

        # state trackers
        self.last_event_time: float = time.time()
        self.current_interval: int = self.polling_interval_active  # annotate as int
        self.last_update_id: Optional[int] = None
        self._running: bool = True

        # prepare download dir
        self.download_dir = os.path.join(
            tg_cfg.download_path,
            bot_name,
            str(self.chat_id),
        )
        os.makedirs(self.download_dir, exist_ok=True)

        # instantiate LLM service
        svc_name = bot_cfg.default.service
        svc_conf = config.services.get(svc_name)
        if svc_conf is None:
            raise ValueError(f"No configuration found for service '{svc_name}'")

        # choose implementation (consider factoring this into a registry later)
        if svc_name == "groq":
            self.llm_service = GroqService(config=svc_conf)
        elif svc_name == "mistral":
            self.llm_service = MistralService(config=svc_conf)
        else:
            raise ValueError(f"Unsupported service '{svc_name}'")

        # Set the active service and model for this bot's chat session
        set_service(self.chat_id, self.bot_name, bot_cfg.default.service)
        set_model(self.chat_id, self.bot_name, bot_cfg.default.model)
        set_temperature(self.chat_id, self.bot_name, bot_cfg.default.temperature)
        set_max_tokens(self.chat_id, self.bot_name, bot_cfg.default.maxtoken)

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

                    # reset to active interval on activity
                    self.last_event_time = time.time()
                    if self.current_interval != self.polling_interval_active:
                        logger.info(
                            f"[PollingLoop] Activity → switching to active interval {self.polling_interval_active}s"
                        )
                    self.current_interval = self.polling_interval_active

                else:
                    idle = time.time() - self.last_event_time
                    if idle > self.polling_active_period:
                        new_int = min(
                            self.current_interval + self.polling_interval_active,
                            self.polling_interval_idle,
                        )
                        if new_int != self.current_interval:
                            last_seen = datetime.datetime.fromtimestamp(self.last_event_time).strftime(
                                "%Y-%m-%d %H:%M:%S"
                            )
                            logger.info(
                                f"[PollingLoop] No activity for {int(idle)}s (last at {last_seen}), backing off to {new_int}s"
                            )
                        self.current_interval = new_int

                await asyncio.sleep(self.current_interval)

            except asyncio.CancelledError:
                logger.info("[PollingLoop] Cancelled by shutdown signal.")
                break
            except Exception:
                logger.exception("[PollingLoop] Unexpected error, sleeping idle interval")
                await asyncio.sleep(self.polling_interval_idle)

    async def _get_updates_with_retries(self) -> Dict[str, Any]:
        attempts, max_attempts = 0, 5
        delay = 5
        while attempts < max_attempts:
            attempts += 1
            try:
                # logger.debug(f"[PollingLoop] getUpdates attempt {attempts}")
                return await self.client.get_updates(offset=self.last_update_id)
            except Exception as e:
                logger.error(f"[PollingLoop] get_updates failed ({attempts}/{max_attempts}): {e}")
                if attempts >= max_attempts:
                    logger.error("[PollingLoop] All retries failed, returning {{'ok': False}}")
                    return {"ok": False}
                await asyncio.sleep(delay)
        return {"ok": False}

    async def handle_update(self, update: dict[str, Any]):
        """
        Called for every incoming update.
        1) If it's a document, fetch & download it.
        2) If it's text, route commands or send to the LLM service (with history, jailbreak, and splitting).
        """
        # prevent circular import
        from llm_telegram_bot.telegram.poller import ChatSession
        from llm_telegram_bot.telegram.routing import route_message
        from llm_telegram_bot.utils.message_utils import build_full_prompt

        try:
            msg = update.get("message")
            if not msg:
                logger.debug("[PollingLoop] update with no message, skipping")
                return

            chat_id = msg["chat"]["id"]
            bot_name = self.bot_name

            # Wrap our TelegramClient + chat into a ChatSession helper
            session = ChatSession(self.client, chat_id, bot_name)
            state = get_session(chat_id, bot_name)

            # ── Initialize default service if not set ─────────────────────────
            if state.active_service is None:
                default_svc = self.config.factorydefault.service or next(iter(self.config.services.keys()), None)
                set_service(chat_id, default_svc, bot_name)

            # ── Document Handling ───────────────────────────────────────────────
            if "document" in msg:
                file_id = msg["document"]["file_id"]
                file_name = msg["document"]["file_name"]
                logger.info(f"[PollingLoop] Document → {file_name} (id={file_id})")

                details = await self.client.get_file(file_id)
                if details.get("ok") and "result" in details:
                    path = details["result"]["file_path"]
                    await self.client.download_file(file_path=path, original_name=file_name)
                else:
                    logger.error(f"[PollingLoop] get_file failed: {details}")
                    await session.send_message(f"❌ Could not retrieve '{file_name}'")
                return

            # ── Text Handling ──────────────────────────────────────────────────
            if "text" in msg:
                user_text = msg["text"].strip()

                # Slash‐command?
                if user_text.startswith("/"):
                    await route_message(
                        session=session, message=msg, llm_call=None, model="", temperature=0.0, maxtoken=0
                    )
                    return

                # Paused?
                if is_paused(chat_id, bot_name):
                    logger.info(f"[PollingLoop] Messaging paused for {chat_id}, skipping LLM")
                    return

                svc_name = state.active_service
                if svc_name is None:
                    raise ValueError("No active service selected")

                bot_def = self.bot_config.default
                svc_conf = self.config.services.get(svc_name)
                if svc_conf is None:
                    raise ValueError(f"Service config for '{svc_name}' not found")

                # 1) Record raw prompt in session memory
                add_memory(chat_id, bot_name, "last_prompt", user_text)

                # 2) Build full LLM prompt (inc. jailbreak, history, user/char context)
                logger.debug(f"char={type(state.active_char)}, user={type(state.active_user)}")

                char_data = session.active_char_data or {}
                user_data = session.active_user_data or {}

                full_prompt = build_full_prompt(
                    char=char_data,
                    user=user_data,
                    jailbreak=state.jailbreak,
                    history=state.history_buffer,
                    user_text=user_text,
                )

                logger.debug(f"[Prompt] Final prompt to LLM:\n{full_prompt}")

                # 3) Also store the sent prompt for debugging
                add_memory(chat_id, bot_name, "last_prompt_full", full_prompt)

                # 4) Append to history buffer (with local timestamp)
                ts = time.strftime("%Y-%m-%d_%H-%M-%S")
                entry = {
                    "who": state.active_user,
                    "ts": ts,
                    "text": user_text,
                    "prompt": full_prompt,
                }

                # add prompt to history buffer
                state.history_buffer.append(entry)

                # 5) Determine effective LLM parameters
                model, temperature, maxtoken = get_effective_llm_params(
                    chat_id=chat_id, bot_name=bot_name, bot_default=bot_def, svc_conf=svc_conf
                )

                # 6) Instantiate service and send the prompt
                service = get_service_for_name(svc_name, svc_conf)
                # Send to LLM
                reply = await service.send_prompt(
                    prompt=full_prompt,
                    model=model,
                    temperature=temperature,
                    maxtoken=maxtoken,
                )

                # 4) Append to history buffer (with local timestamp)
                entry = {
                    "who": state.active_char,
                    "ts": ts,
                    "text": reply,
                    "prompt": "",
                }

                # add response to history buffer
                state.history_buffer.append(entry)

                # we flush now based on time intervall (600 seconds;
                # s. session_manger.py "async def _periodic_flush(self)")
                # but let's be sure:
                if len(state.history_buffer) >= self.bot_config.history_flush_count:
                    try:
                        state.flush_history_to_disk()
                    except Exception as e:
                        logger.exception(f"Error flushing history: {e}")

                # flush every prompt and response
                # try:
                #     state.flush_history_to_disk()
                # except Exception as e:
                #     logger.exception(f"Error flushing history: {e}")

                # x) OUTDATED Record the raw LLM response
                add_memory(chat_id, bot_name, "last_response", reply)

                # 7) Send back, splitting long messages
                if len(reply) > 4096:
                    logger.warning(f"[PollingLoop] Splitting reply of {len(reply)} chars")
                for chunk in split_message(reply):
                    await session.send_message(chunk)

        except Exception as e:
            logger.exception(f"[PollingLoop] error in handle_update: {e}")
            # best-effort fallback
            try:
                fallback = ChatSession(self.client, update["message"]["chat"]["id"], bot_name)
                await fallback.send_message(f"❌ Error processing update: {e}")
            except:
                pass


if __name__ == "__main__":
    import asyncio
    import sys

    async def main():
        cfg = load_config()  # Pydantic RootConfig
        tg = cfg.telegram  # TelegramConfig
        all_bots = tg.bots  # Dict[str, BotConfig]

        # which bots to run?
        requested = sys.argv[1:]
        bot_names = requested or [name for name, bot in all_bots.items() if bot.enabled]

        tasks: list[asyncio.Task] = []
        for bot_name in bot_names:
            bot_conf = all_bots.get(bot_name)
            if not bot_conf or not bot_conf.enabled:
                continue

            client = TelegramClient(
                token=bot_conf.token,
                chat_id=bot_conf.chat_id,
                bot_name=bot_name,
                download_path=bot_conf.download_path,
                chat_history_path=bot_conf.chat_history_path,
            )
            await client.init_session()
            poller = PollingLoop(bot_name, client, cfg)
            tasks.append(asyncio.create_task(poller.run()))

        if tasks:
            await asyncio.gather(*tasks)
        else:
            logger.warning("[Main] No bots started; check your config or args.")

    asyncio.run(main())
