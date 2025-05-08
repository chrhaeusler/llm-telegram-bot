# Responsibilities:
# Maintain three deques/lists:
# tier0: deque[Message]
# tier1: deque[Summary]
# tier2: deque[MegaSummary]
# Expose methods:
# add_user_message(text: str) / add_bot_message(text: str)
#
# Internally:
# language detection & cleanup
# Tier-0 compression (length-gradient) → Message(summary, tokens)
# If len(tier0)>N0, demote to Tier-1 via tighter summary
# If len(tier1)>N1, demote batch to Tier-2 mega-summary
# get_prompt_block() → returns the concatenated block
# Emit debug logs at each step: original token count, compressed token count, tier
#
# TO DO
# Create a word counter that counts the words (most will be tokens anyway) of outgoing
# prompt, best also per part, and provide feedback how the structure looks like when
# above a certain threshold; possibly include automatic truncing

# src/session/history_manager.py
# src/llm_telegram_bot/session/history_manager.py

import datetime
import logging
from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict

logger = logging.getLogger(__name__)


@dataclass
class Message:
    ts: str
    who: str  # who spoke: the user‐key or char‐key
    text: str  # raw or compressed text
    tokens_original: int  # count before compression
    tokens_compressed: int  # count after compression


@dataclass
class Summary:
    text: str
    tokens: int


@dataclass
class MegaSummary:
    text: str
    tokens: int
    span_start: datetime.datetime
    span_end: datetime.datetime


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
        N0: int = 10,  # max raw messages before promoting to tier1
        N1: int = 20,  # max summaries before promoting to tier2
        K: int = 5,  # how many summaries to batch into one mega
        T0_cap: int = 100,
        T1_cap: int = 50,
        T2_cap: int = 200,
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
            f"N0={self.N0}, N1={self.N1}, K={self.K}, caps=(T0={self.T0_cap},T1={self.T1_cap},T2={self.T2_cap})"
        )

    def add_user_message(self, msg: Message) -> None:
        """
        Add a Message originating from the user into tier-0,
        then trigger any necessary promotions to higher tiers.
        """
        logger.debug(f"[HistoryManager] add_user_message → who={msg.who!r}, tokens={msg.tokens_original}")
        logger.debug(f"[HistoryManager] add_user_message → {msg.who!r}@{msg.ts}, {msg.tokens_original} toks")
        self.tier0.append(msg)
        self._maybe_promote()

    def add_bot_message(self, msg: Message) -> None:
        """
        Add a Message originating from the bot (LLM reply) into tier-0,
        then trigger any necessary promotions to higher tiers.
        """
        logger.debug(f"[HistoryManager] add_bot_message → {msg.who!r}@{msg.ts}, {msg.tokens_original} toks")
        self.tier0.append(msg)
        self._maybe_promote()

    def _maybe_promote(self) -> None:
        # Tier-0 → Tier-1
        if len(self.tier0) > self.N0:
            old: Message = self.tier0.popleft()
            # TODO: generate a Summary with actual summarization capped at T1_cap
            summary_text = f"(summary of: {old.text[:30]}…)"
            summ = Summary(text=summary_text, tokens=min(old.tokens_compressed, self.T1_cap))
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
