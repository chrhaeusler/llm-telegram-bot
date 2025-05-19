# src/telegram/poller.py

import asyncio
import datetime
import os
import time
from typing import Any, Dict, Optional

from langdetect import LangDetectException, detect

import llm_telegram_bot.commands.handlers  # noqa: F401
from llm_telegram_bot.config.config_loader import load_config
from llm_telegram_bot.config.schemas import BotConfig, RootConfig
from llm_telegram_bot.llm.dispatcher import get_service_for_name
from llm_telegram_bot.services.service_groq import GroqService
from llm_telegram_bot.services.service_mistral import MistralService
from llm_telegram_bot.session.history_manager import Message
from llm_telegram_bot.session.session_manager import (
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
from llm_telegram_bot.utils.message_utils import (
    build_full_prompt,
    split_message,
)
from llm_telegram_bot.utils.token_utils import count_tokens


class ChatSession:
    """
    Wrapper for a chat session that provides:
      - send_message(text): handles Telegram message sending
      - access to session state like active_service, active_bot, etc.
      - one HistoryManager per chat/bot
    """

    def __init__(self, client: TelegramClient, chat_id: int, bot_name: str):
        self.client = client
        self.chat_id = chat_id
        self.bot_name = bot_name
        self._session = get_session(chat_id, bot_name)
        # History Manager for Summarization of tiers 0-2
        self.history_mgr = self._session.history_mgr
        # History Buffer for writing to file
        self.history_buffer: list[dict] = []

    async def send_message(self, text: str, *, parse_mode: str = "MarkdownV2", **kwargs) -> None:
        self.client.chat_id = self.chat_id
        await self.client.send_message(text, parse_mode=parse_mode, **kwargs)

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
        # history_mgr will be lazily created once we see the first text message

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
        logger.info(f"[Poller: Loop] Starting poll loop for '{self.bot_name}'")
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
                            f"[Poller: Loop] Activity → switching to active interval {self.polling_interval_active}s"
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
                                f"[Poller: Loop] No activity for {int(idle)}s (last at {last_seen}), backing off to {new_int}s"
                            )
                        self.current_interval = new_int

                await asyncio.sleep(self.current_interval)

            except asyncio.CancelledError:
                logger.info("[Poller: Loop] Cancelled by shutdown signal.")
                break
            except Exception:
                logger.exception("[Poller: Loop] Unexpected error, sleeping idle interval")
                await asyncio.sleep(self.polling_interval_idle)

    async def _get_updates_with_retries(self) -> Dict[str, Any]:
        attempts, max_attempts = 0, 5
        delay = 5
        while attempts < max_attempts:
            attempts += 1
            try:
                # logger.debug(f"[Poller: Loop] getUpdates attempt {attempts}")
                return await self.client.get_updates(offset=self.last_update_id)
            except Exception as e:
                logger.error(f"[Poller: Loop] get_updates failed ({attempts}/{max_attempts}): {e}")
                if attempts >= max_attempts:
                    logger.error("[Poller: Loop] All retries failed, returning {{'ok': False}}")
                    return {"ok": False}
                await asyncio.sleep(delay)
        return {"ok": False}

    async def handle_update(self, update: Dict[str, Any]):
        msg = update.get("message")
        if not msg:
            return

        chat_id = msg["chat"]["id"]
        # Wrap into session + state
        session = ChatSession(self.client, chat_id, self.bot_name)
        state = get_session(chat_id, self.bot_name)

        # ── Init LLM service if missing ───────────────────────
        if state.active_service is None:
            default = self.config.factorydefault.service or next(iter(self.config.services), None)
            set_service(chat_id, default, self.bot_name)

        # 1) documents
        if "document" in msg:
            return await self._handle_document(msg, session)

        # 2) text
        if "text" in msg:
            return await self._handle_text(msg, session, state)

    async def _handle_document(self, msg: Dict, session: Any):
        file_id = msg["document"]["file_id"]
        file_name = msg["document"]["file_name"]

        # Log
        logger.info(f"[Poller] Downloading document {file_name}")

        details = await self.client.get_file(file_id)
        if details.get("ok"):
            await self.client.download_file(details["result"]["file_path"], file_name)
        else:
            await session.send_message(f"❌ Could not retrieve '{file_name}'")
        return

    async def _handle_text(self, msg: Dict, session: Any, state: Any):
        user_text = msg["text"].strip()
        chat_id = session.chat_id
        bot_name = session.bot_name

        # Commands
        if user_text.startswith("/"):
            # late import avoids circularity
            from llm_telegram_bot.telegram.routing import route_message

            await route_message(session=session, message=msg, llm_call=None, model="", temperature=0, maxtoken=0)
            return

        # Paused?
        if is_paused(chat_id, bot_name):
            return

        # Detect language of user input
        try:
            language_user = detect(user_text)
        except LangDetectException:
            language_user = "unknown"

        logger.debug(f"[Poller] Detected language of user text: {language_user}")

        # Gather config + persona
        svc_name = state.active_service
        bot_def = self.config.factorydefault
        svc_conf = self.config.services[svc_name]

        # Build context dict for prompt
        raw_ctx = session.history_mgr.get_all_context()
        context = {
            "tier0": raw_ctx["tier0"],  # recent messages
            "tier1": raw_ctx["tier1"],  # midterm summaries
            "tier2": raw_ctx["tier2"],  # overview/mega summaries
            "tier0_keys": raw_ctx["tier0_keys"],  # NER bucket for recent
            "tier1_keys": raw_ctx["tier1_keys"],  # NER bucket for midterm
            "tier2_keys": raw_ctx["tier2_keys"],  # NER bucket for overview
        }

        # Render full prompt
        full_prompt = build_full_prompt(
            char=session.active_char_data or {},
            user=session.active_user_data or {},
            jailbreak=state.jailbreak,
            context=context,
            user_text=user_text,
        )

        # count tokens
        tokens_user_text = count_tokens(user_text)
        tokens_full = count_tokens(full_prompt)
        logger.debug(f"[Poller] Full prompt hast ({tokens_full} toks)]\n{full_prompt}")

        # Send Feedback about Prompt and History
        # Send Feedback about Prompt and History
        mgr = session.history_mgr
        stats = mgr.token_stats()
        caps = mgr

        # also get counts of items in each tier
        counts = {
            "tier0": len(mgr.tier0),
            "tier1": len(mgr.tier1),
            "tier2": len(mgr.tier2),
        }

        await session.send_message(
            "<b>🔢 History Manager's Token Parameters</b>:\n"
            f"• N0: {caps.N0} msgs max; {caps.T0_cap} tokens each\n"
            f"• N1: max {caps.N1} msgs max; {caps.T1_cap} tokens each\n"
            f"• K:  {caps.K} batches; 5 sentences\n\n"
            "<b>🧮 Current Context Usage</b>:\n"
            f"• overview: {counts['tier2']} mega-summaries ({stats['tier2']} toks)\n"
            f"• midterm: {counts['tier1']} summaries ({stats['tier1']} toks)\n"
            f"• recent: {counts['tier0']} msgs ({stats['tier0']} toks)\n"
            f"• full prompt: {tokens_full} toks\n"
            f"• your text: {tokens_user_text} toks",
            parse_mode="HTML",
        )

        # Record into HistoryManager
        ts = time.strftime("%Y-%m-%d_%H-%M-%S")

        prompt_msg = Message(
            ts=ts,
            who=session.active_user_data["identity"]["name"],  # state.active_user,
            lang=language_user,
            text=user_text,
            tokens_text=tokens_user_text,
            compressed=user_text,
            tokens_compressed=tokens_user_text,
        )

        # Get parameter for calling LLM
        service = get_service_for_name(svc_name, svc_conf)
        model, temp, max_tk = get_effective_llm_params(
            chat_id,
            bot_name,
            bot_def,
            svc_conf,
        )

        # Call LLM and guard against API errors
        try:
            reply = await service.send_prompt(
                prompt=full_prompt,
                model=model,
                temperature=temp,
                maxtoken=max_tk,
            )
        except Exception as err:
            # report it but do NOT record it in history
            logger.exception("[PollingLoop] LLM API error")
            await session.send_message(f"❌ LLM error: {err}")
            return

        # detect reply language
        try:
            language_reply = detect(reply)
        except LangDetectException:
            language_reply = "unknown"

        logger.debug(f"[Poller] Detected language of LLM reply: {language_reply}")

        # record LLM reply
        tokens_reply = count_tokens(reply)
        logger.debug(f"[Poller] Tokens in reply: {tokens_reply}")

        reply_msg = Message(
            ts=ts,
            who=session.active_char_data["identity"]["name"],
            lang=language_reply,
            text=reply,
            tokens_text=tokens_reply,
            compressed=reply,
            tokens_compressed=tokens_reply,
        )

        # Send back to user (with splitting)
        for chunk in split_message(reply):
            await session.send_message(chunk)

        # Update HistoryManager (for summarization))
        session.history_mgr.add_user_message(prompt_msg)
        session.history_mgr.add_bot_message(reply_msg)

        if session.history_mgr.tier2 and session.history_mgr.tier2[-1].is_stub:
            mega = session.history_mgr.tier2.pop()
            # generate a fresh LLM narrative
            fresh = await service.send_prompt(
                prompt=mega.text,  # your steering+blob is already baked in
                model=model,
                temperature=0.3,
                maxtoken=250,  # TO DO: make this a variable to be set in config.yaml
            )
            mega.text = fresh
            mega.tokens = count_tokens(fresh)
            mega.is_stub = False
            session.history_mgr.tier2.append(mega)
        import ipdb

        ipdb.set_trace()

        # Append to History Buffer (for recording to file)
        state.history_buffer.append(
            {
                "who": prompt_msg.who,
                "ts": prompt_msg.ts,
                "lang": prompt_msg.lang,
                "text": prompt_msg.text,
                "tokens_text": prompt_msg.tokens_text,
                "tokens_compressed": prompt_msg.tokens_compressed,
            }
        )

        state.history_buffer.append(
            {
                "who": reply_msg.who,
                "ts": reply_msg.ts,
                "lang": reply_msg.lang,
                "text": reply_msg.text,
                "tokens_text": reply_msg.tokens_text,
                "tokens_compressed": reply_msg.tokens_compressed,
            }
        )


if __name__ == "__main__":
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
