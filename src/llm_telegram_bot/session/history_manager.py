# src/llm_telegram_bot/session/history_manager.py

import datetime
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict

from llm_telegram_bot.utils.logger import logger
from llm_telegram_bot.utils.summarize import safe_summarize
from llm_telegram_bot.utils.token_utils import count_tokens

TOKENS_PER_SENTENCE = 30  # yes, TexRank like long sentences with sometime >30 tokens


@dataclass
class Message:
    ts: str
    who: str
    lang: str
    text: str  # the raw, unmodified message
    tokens_text: int
    compressed: str  # compressed text for prompt-injection
    tokens_compressed: int  # TO DO: change this to time stamp


@dataclass
class Summary:
    text: str
    tokens: int
    who: str  # 'user' or 'bot'
    ts: datetime.datetime = field(default_factory=datetime.datetime.utcnow)


@dataclass
class MegaSummary:
    text: str  # 2–3 sentence capsule
    # keywords: list[str]  # e.g. ["Alice","Bob","API","Meetup"]
    tokens: int  # count(text)
    span_start: datetime
    span_end: datetime


class HistoryManager:
    """
    Collects every incoming/outgoing message into tiered deques
    and applies summarization later.
    """

    def __init__(
        self,
        bot_name: str,
        chat_id: int,
        *,
        N0: int = 9,  # max raw messages before promoting to tier1
        N1: int = 19,  # max summaries before promoting to tier2
        K: int = 6,  # how many summaries to batch into one mega
        T0_cap: int = 99,
        T1_cap: int = 49,
        T2_cap: int = 199,
    ):
        self.bot_name = bot_name
        self.chat_id = chat_id

        # tier sizes and caps
        self.N0 = N0
        self.N1 = N1
        self.K = K
        self.T0_cap = T0_cap
        self.T1_cap = T1_cap
        self.T2_cap = T2_cap

        # Tiered storage
        self.tier0: Deque[Message] = deque()  # raw or lightly‐compressed messages
        self.tier1: Deque[Summary] = deque()  # medium summaries
        self.tier2: Deque[MegaSummary] = deque()  # high-level summaries

        logger.debug(
            f"[HistoryManager] init {bot_name}:{chat_id} → "
            f"N0={self.N0}, N1={self.N1}, K={self.K},"
            f"caps=(T0={self.T0_cap},T1={self.T1_cap},T2={self.T2_cap})"
        )

    def token_stats(self) -> Dict[str, int]:
        """
        Returns the total compressed‐token count in each tier.
        """
        return {
            "tier0": sum(msg.tokens_compressed for msg in self.tier0),
            "tier1": sum(s.tokens for s in self.tier1),
            "tier2": sum(m.tokens for m in self.tier2),
        }

    def _compress_t0(self, msg: Message) -> None:
        """
        Tier-0 “compression”:
         • if msg.tokens_text ≤ T0_cap: keep raw
         • else: summarize down to ≈ T0_cap tokens
        """
        L = msg.tokens_text
        cap = self.T0_cap

        # 1) under the cap: no change
        if L <= cap:
            msg.compressed = msg.text
            msg.tokens_compressed = L
            return

        # 2) otherwise we need a summary
        # translate token-budget into sentence-budget
        avg_toks_per_sent = TOKENS_PER_SENTENCE
        # ensure at least 1 sentence
        num_sents = max(1, cap // avg_toks_per_sent)

        try:
            summary = safe_summarize(
                # summarize with texrank (or switch to lexrank)
                msg.text,
                num_sentences=num_sents,
                lang=msg.lang,
                method="texrank",
            )

        except Exception as e:
            logger.warning(f"[compress_t0] summarization failed: {e}; falling back to raw")
            summary = msg.text

        msg.compressed = summary
        msg.tokens_compressed = count_tokens(summary)

    def _compress_t1(self, msg: Message) -> Summary:
        """
        Tier-1 compression:
        Take the Tier-0 compressed message and compress it to a single sentence (~T1_cap tokens).
        """
        cap = self.T1_cap

        # 2) otherwise we need a summary
        # translate token-budget into sentence-budget
        avg_toks_per_sent = TOKENS_PER_SENTENCE
        # ensure at least 1 sentence
        num_sents = max(1, cap // avg_toks_per_sent)

        try:
            summary_text = safe_summarize(
                text=msg.compressed,
                num_sentences=num_sents,
                lang=msg.lang,
                method="textrank",
            )
        
        except Exception as e:
            logger.warning(f"[compress_t1] summarization failed: {e}; falling back to t0 summary")
            summary_text = msg.compressed

        tokens = count_tokens(summary_text)

        return Summary(
            text=summary_text,
            tokens=tokens,
            who=msg.who,
            ts=msg.ts,
        )

    def add_user_message(self, msg: Message) -> None:
        """
        Add a Message originating from the user into tier-0,
        then trigger any necessary promotions to higher tiers.
        """
        # 1) compress just-in-time
        self._compress_t0(msg)
        logger.debug(
            f"[HistoryManager] add_user_message → {msg.who!r}@{msg.ts}, "
            f"orig={msg.tokens_text}, comp={msg.tokens_compressed}"
        )
        # 2) store into tier-0
        self.tier0.append(msg)

        self._maybe_promote()

    def add_bot_message(self, msg: Message) -> None:
        """
        Add a Message originating from the bot (LLM reply) into tier-0,
        then trigger any necessary promotions to higher tiers.
        """
        # compress LLM replies as well
        self._compress_t0(msg)
        logger.debug(
            f"[HistoryManager] add_bot_message → {msg.who!r}@{msg.ts}, "
            f"orig={msg.tokens_text}, comp={msg.tokens_compressed}"
        )
        self.tier0.append(msg)

        self._maybe_promote()

    def _maybe_promote(self) -> None:
        # Tier-0 → Tier-1
        if len(self.tier0) > self.N0:
            old: Message = self.tier0.popleft()
            summ = self._compress_t1(old)
            self.tier1.append(summ)
            logger.debug(f"[HistoryManager] promoted to tier1: {summ}")

        # Tier-1 → Tier-2
        if len(self.tier1) > self.N1:
            # batch first K summaries
            batch = [self.tier1.popleft() for _ in range(min(self.K, len(self.tier1)))]
            combined = " ".join(s.text for s in batch)
            span_start = getattr(batch[0], "span_start", datetime.datetime.utcnow())
            span_end = getattr(batch[-1], "span_end", datetime.datetime.utcnow())
            # TODO: generate mega summary capped at T2_cap
            mega_text = f"(mega summary of {len(batch)} items)"
            mega = MegaSummary(
                text=mega_text,
                tokens=min(sum(s.tokens for s in batch), self.T2_cap),
                span_start=span_start,
                span_end=span_end,
            )
            self.tier2.append(mega)
            logger.debug(f"[HistoryManager] promoted to tier2: {mega}")

    # (Optional) expose a method to fetch everything you’ll inject into your prompt:
    def get_all_context(self) -> Dict[str, Deque]:
        return {
            "tier0": self.tier0,  # Deque[Message]
            "tier1": self.tier1,  # Deque[Summary]
            "tier2": self.tier2,  # Deque[MegaSummary]
        }
