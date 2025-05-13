# src/llm_telegram_bot/session/history_manager.py
import datetime
import re
from collections import Counter, deque
from dataclasses import dataclass, field
from typing import Deque, Dict

from llm_telegram_bot.utils.logger import logger
from llm_telegram_bot.utils.summarize import extract_named_entities, safe_summarize
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
    who: str  # non-default
    lang: str  # non-default
    text: str  # non-default
    tokens: int  # non-default
    ts: datetime.datetime = field(default_factory=datetime.datetime.utcnow)


@dataclass
class MegaSummary:
    text: str
    keywords: list[str]
    tokens: int
    span_start: datetime.datetime
    span_end: datetime.datetime
    is_stub: bool = True  # a flag so your async loop can “upgrade” it via LLM


class HistoryManager:
    """
    Collects every incoming/outgoing message into tiered deques
    and applies summarization later.
    """

    # ── tuning constants ───────────────────────────────────────────────
    FRACTION_TO_SUMMARIZE = 0.25  # % of N1 to pull each batch
    MEGA_SENTENCES = 5  # how many sentences for the LLM summary
    MAX_KEYWORDS = 50  # cap of rolling keyword list

    def __init__(
        self,
        bot_name: str,
        chat_id: int,
        *,
        N0=10,
        N1=20,
        K=5,
        T0_cap=100,
        T1_cap=50,
        T2_cap=200,
    ):
        self.bot_name = bot_name
        self.chat_id = chat_id
        self.N0 = N0
        self.N1 = N1
        self.K = K
        self.T0_cap = T0_cap
        self.T1_cap = T1_cap
        self.T2_cap = T2_cap

        self.tier0: Deque[Message] = deque()
        self.tier1: Deque[Summary] = deque()
        self.tier2: Deque[MegaSummary] = deque()

        logger.debug(
            f"[HistoryManager] init {bot_name}:{chat_id} → "
            f"N0={N0}, N1={N1}, K={K}, caps=(T0={T0_cap},T1={T1_cap},T2={T2_cap})"
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

    # (Optional) expose a method to fetch everything you’ll inject into your prompt:
    def get_all_context(self) -> Dict[str, Deque]:
        return {
            "tier0": self.tier0,  # Deque[Message]
            "tier1": self.tier1,  # Deque[Summary]
            "tier2": self.tier2,  # Deque[MegaSummary]
        }

    def _maybe_promote(self) -> None:
        # ── Tier-0 → Tier-1 ────────────────────────────────────────────
        while len(self.tier0) > self.N0:
            old: Message = self.tier0.popleft()
            # compress into a Summary-object (you already have _compress_t1)
            summ: Summary = self._compress_t1(old)
            self.tier1.append(summ)
            logger.debug(f"[HistoryManager] promoted to tier1: {summ}")

        # ── Tier-1 → Tier-2 rolling mega ────────────────────────────────
        while len(self.tier1) > self.N1:
            # decide how many tier1 summaries to fold in
            fraction = max(1, int(self.N1 * self.FRACTION_TO_SUMMARIZE))
            batch_size = min(fraction, self.K, len(self.tier1))
            batch = [self.tier1.popleft() for _ in range(batch_size)]

            # stitch together
            new_blob = " ".join(s.text for s in batch)
            span_start = getattr(batch[0], "span_start", datetime.datetime.utcnow())
            span_end = getattr(batch[-1], "span_end", datetime.datetime.utcnow())

            # if we already had a mega, prepend it so we never lose context
            if self.tier2:
                prev = self.tier2.popleft()
                new_blob = prev.text + "\n\n" + new_blob
                span_start = min(span_start, prev.span_start)
                span_end = max(span_end, prev.span_end)
                prev_keywords = deque(prev.keywords)
            else:
                prev_keywords = deque()

            # pick the dominant language among the batch
            langs = [getattr(s, "lang", "unknown") for s in batch]
            non_unknown = [l for l in langs if l != "unknown"]
            chosen_lang = non_unknown and Counter(non_unknown).most_common(1)[0][0] or "english"

            # 1) make a steering prompt + run safe_summarize
            steering = {
                "de": "Fasse die folgende Unterhaltung in eine kurze Erzählung zusammen:",
                "en": "Summarize the following conversation into a short narrative:",
            }.get(chosen_lang[:2], "Summarize the following conversation:")
            to_summarize = f"{steering}\n\n{new_blob}"

            mega_text = safe_summarize(
                new_blob,
                num_sentences=self.MEGA_SENTENCES,
                lang=chosen_lang,
                method="textrank",
            )

            mega_tokens = min(count_tokens(mega_text), self.T2_cap)

            # 2) extract NER keywords & merge de-dup into prev_keywords
            new_keys = extract_named_entities(new_blob, lang=chosen_lang)
            for k in new_keys:
                if k not in prev_keywords:
                    prev_keywords.append(k)
            # cap rolling keywords
            while len(prev_keywords) > self.MAX_KEYWORDS:
                prev_keywords.popleft()

            mega = MegaSummary(
                text=mega_text,
                keywords=list(prev_keywords),
                tokens=mega_tokens,
                span_start=span_start,
                span_end=span_end,
                is_stub=True,
            )
            self.tier2.append(mega)
            logger.debug(f"[HistoryManager] promoted to tier2: {mega}")

    def add_user_message(self, msg: Message) -> None:
        """
        Add a Message originating from the user into tier-0,
        then trigger any necessary promotions to higher tiers.
        """
        # 1) compress just-in-time
        self._compress_t0(msg)
        logger.debug(
            f"[HistoryManager] add_user_message → {msg.ts!r}@{msg.who}, "
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
            f"[HistoryManager] add_bot_message → {msg.ts!r}@{msg.who}, "
            f"orig={msg.tokens_text}, comp={msg.tokens_compressed}"
        )
        self.tier0.append(msg)

        self._maybe_promote()

    def remove_lettered_lists(self, text: str) -> str:
        """
        Remove lines that look like:
        a) Something
        b) Something else
        c) Yet another
        """
        # This will drop any line that starts with optional whitespace,
        # then a single lowercase letter or digit, then a parenthesis,
        # then the rest of the line.
        cleaned = re.sub(r'(?m)^\s*[a-z0-9]\)\s.*$', '', text)
        # And collapse any now–empty blank lines:
        cleaned = re.sub(r'\n{2,}', '\n\n', cleaned).strip()
        return cleaned

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
        # do some cleaning
        raw = msg.text.replace('...', '.')  # cleaning because "..." confuses Sumy
        prepped = self.remove_lettered_lists(raw)

        try:
            summary = safe_summarize(
                # summarize with texrank (or switch to lexrank)
                prepped,
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
            ts=msg.ts,
            who=msg.who,
            lang=msg.lang,
            text=summary_text,
            tokens=tokens,
        )
