# src/llm_telegram_bot/session/history_manager.py
import datetime
import re
from collections import Counter, deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List

from llm_telegram_bot.utils.logger import logger
from llm_telegram_bot.utils.summarize import extract_named_entities, safe_summarize
from llm_telegram_bot.utils.token_utils import count_tokens

TOKENS_PER_SENTENCE = 30  # rough tokens per sentence for sentence-budgeting


def keyword_extractor(text: str, lang: str) -> List[str]:
    """Wrap NER extractor with safe fallback."""
    try:
        return extract_named_entities(text, lang=lang)
    except Exception as e:
        logger.warning(f"[keyword_extractor] failed: {e}")
        return []


@dataclass
class Message:
    ts: str
    who: str
    lang: str
    text: str
    tokens_text: int
    compressed: str
    tokens_compressed: int
    keywords: List[str] = field(default_factory=list)


@dataclass
class Summary:
    who: str
    lang: str
    text: str
    tokens: int
    ts: datetime.datetime = field(default_factory=datetime.datetime.utcnow)
    keywords: List[str] = field(default_factory=list)


@dataclass
class MegaSummary:
    text: str
    keywords: List[str]
    tokens: int
    span_start: datetime.datetime
    span_end: datetime.datetime
    is_stub: bool = True


class HistoryManager:
    """
    Tiered history + optional, per-tier NER buckets.
    """

    FRACTION_TO_SUMMARIZE = 0.25

    def __init__(
        self,
        bot_name: str,
        chat_id: int,
        *,
        N0: int = 10,
        N1: int = 20,
        K: int = 5,
        T0_cap: int = 100,
        T1_cap: int = 50,
        T2_cap: int = 200,
        # When to extract NERs
        extract_ner_t0_before: bool = True,  # extract NERs before summarization?
        extract_ner_t0_after: bool = False,
        extract_ner_t1: bool = False,  # extract NERs after tier1 summary and use these?
        # NER parameters:
        max_ner_t0: int = 20,
        max_ner_t1: int = 20,
        max_ner_t2: int = 50,
    ):
        self.bot_name = bot_name
        self.chat_id = chat_id

        # tier caps
        self.N0, self.N1, self.K = N0, N1, K
        self.T0_cap, self.T1_cap, self.T2_cap = T0_cap, T1_cap, T2_cap

        # NER settings
        self.max_ner_t0 = max_ner_t0
        self.max_ner_t1 = max_ner_t1
        self.max_ner_t2 = max_ner_t2
        self.extract_ner_t0_before = extract_ner_t0_before
        self.extract_ner_t0_after = extract_ner_t0_after
        self.extract_ner_t1 = extract_ner_t1

        # data tiers
        self.tier0: Deque[Message] = deque()
        self.tier1: Deque[Summary] = deque()
        self.tier2: Deque[MegaSummary] = deque()

        # rolling NER buckets per tier
        self.tier0_keys: deque[str] = deque(maxlen=self.max_ner_t0)
        self.tier1_keys: deque[str] = deque(maxlen=self.max_ner_t1)
        self.tier2_keys: deque[str] = deque(maxlen=self.max_ner_t2)

        logger.debug(
            f"[HistoryManager] init {bot_name}:{chat_id} "
            f"N0={N0},N1={N1},caps=(T0={T0_cap},T1={T1_cap},T2={T2_cap}) "
            f"NER caps=(t0={max_ner_t0},t1={max_ner_t1},t2={max_ner_t2}) "
            f"extract_ner_t0_before={extract_ner_t0_before},"
            f"after={extract_ner_t0_after},t1={extract_ner_t1}"
        )

    def token_stats(self) -> Dict[str, int]:
        return {
            "tier0": sum(m.tokens_compressed for m in self.tier0),
            "tier1": sum(s.tokens for s in self.tier1),
            "tier2": sum(m.tokens for m in self.tier2),
        }

    def get_all_context(self) -> Dict[str, Any]:
        """
        Returns all three tiers plus their rolling NER buckets,
        each as a simple list for easy iteration/serialization.
        """
        return {
            "tier0": list(self.tier0),  # List[Message]
            "tier1": list(self.tier1),  # List[Summary]
            "tier2": list(self.tier2),  # List[MegaSummary]
            "tier0_keys": list(self.tier0_keys),  # List[str]
            "tier1_keys": list(self.tier1_keys),  # List[str]
            "tier2_keys": list(self.tier2_keys),  # List[str]
        }

    def _maybe_promote(self) -> None:
        # Tier-0 → Tier-1
        while len(self.tier0) > self.N0:
            old = self.tier0.popleft()
            summ = self._compress_t1(old)
            self.tier1.append(summ)
            # roll into tier1 bucket
            for k in summ.keywords:
                self.tier1_keys.append(k)
            # logger.debug(f"[promote] tier0→1: {summ}")

        # Tier-1 → Tier-2
        while len(self.tier1) > self.N1:
            batch_size = min(
                max(1, int(self.N1 * self.FRACTION_TO_SUMMARIZE)),
                self.K,
                len(self.tier1),
            )
            batch = [self.tier1.popleft() for _ in range(batch_size)]

            # build blob + spans
            new_blob = " ".join(s.text for s in batch)
            span_start = getattr(batch[0], "span_start", datetime.datetime.utcnow())
            span_end = getattr(batch[-1], "span_end", datetime.datetime.utcnow())

            # prepend previous mega
            if self.tier2:
                prev = self.tier2.popleft()
                new_blob = prev.text + "\n\n" + new_blob
                span_start = min(span_start, prev.span_start)
                span_end = max(span_end, prev.span_end)
                prev_keys = deque(prev.keywords)
            else:
                prev_keys = deque()

            # determine language
            langs = [s.lang for s in batch if s.lang != "unknown"]
            chosen_lang = Counter(langs).most_common(1)[0][0] if langs else "english"

            # calculate number of sentences for T2
            cap = self.T2_cap
            num_sents = max(1, cap // TOKENS_PER_SENTENCE)
            # summarize
            mega_text = safe_summarize(
                new_blob,
                num_sentences=num_sents,
                lang=chosen_lang,
                method="textrank",
            )
            mega_tokens = min(count_tokens(mega_text), self.T2_cap)

            # take over tier1 bucket as tier2 bucket (fresh snapshot)
            # NB: you could also re-extract here if you prefer.
            for k in self.tier1_keys:
                prev_keys.append(k)
            while len(prev_keys) > self.max_ner_t2:
                prev_keys.popleft()

            mega = MegaSummary(
                text=mega_text,
                keywords=list(prev_keys),
                tokens=mega_tokens,
                span_start=span_start,
                span_end=span_end,
                is_stub=True,
            )
            self.tier2.append(mega)
            # roll into tier2 bucket
            self.tier2_keys.clear()
            for k in mega.keywords:
                self.tier2_keys.append(k)

            logger.debug(f"[promote] tier1→2: {mega}")

    def add_user_message(self, msg: Message) -> None:
        # Tier-0 NER before or after compress
        if self.extract_ner_t0_before:
            msg.keywords = keyword_extractor(msg.text, msg.lang)
        self._compress_t0(msg)
        if self.extract_ner_t0_after:
            msg.keywords = keyword_extractor(msg.compressed, msg.lang)

        # roll into bucket
        for k in msg.keywords:
            self.tier0_keys.append(k)

        logger.debug(f"[add_user] {msg.who}@{msg.ts}, toks={msg.tokens_compressed}, keys={msg.keywords}")
        self.tier0.append(msg)
        self._maybe_promote()

    def add_bot_message(self, msg: Message) -> None:
        # same as user
        if self.extract_ner_t0_before:
            msg.keywords = keyword_extractor(msg.text, msg.lang)
        self._compress_t0(msg)
        if self.extract_ner_t0_after:
            msg.keywords = keyword_extractor(msg.compressed, msg.lang)

        for k in msg.keywords:
            self.tier0_keys.append(k)

        logger.debug(f"[add_bot] {msg.who}@{msg.ts}, toks={msg.tokens_compressed}, keys={msg.keywords}")
        self.tier0.append(msg)
        self._maybe_promote()

    def remove_lettered_lists(self, text: str) -> str:
        cleaned = re.sub(r'(?m)^\s*[a-z0-9]\)\s.*$', '', text)
        return re.sub(r'\n{2,}', '\n\n', cleaned).strip()

    def _compress_t0(self, msg: Message) -> None:
        L, cap = msg.tokens_text, self.T0_cap
        if L <= cap:
            msg.compressed = msg.text
            msg.tokens_compressed = L
            return

        num_sents = max(1, cap // TOKENS_PER_SENTENCE)
        prepped = self.remove_lettered_lists(msg.text.replace("...", "."))
        try:
            summary = safe_summarize(prepped, num_sentences=num_sents, lang=msg.lang, method="textrank")
        except Exception as e:
            logger.warning(f"[compress_t0] failed: {e}")
            summary = msg.text

        msg.compressed = summary
        msg.tokens_compressed = count_tokens(summary)

    def _compress_t1(self, msg: Message) -> Summary:
        cap = self.T1_cap
        num_sents = max(1, cap // TOKENS_PER_SENTENCE)
        try:
            text = safe_summarize(msg.compressed, num_sentences=num_sents, lang=msg.lang, method="textrank")
        except Exception as e:
            logger.warning(f"[compress_t1] failed: {e}")
            text = msg.compressed

        tokens = count_tokens(text)

        # NER on tier1 if requested, else inherit from message
        if self.extract_ner_t1:
            keys = keyword_extractor(text, msg.lang)
        else:
            keys = msg.keywords.copy()

        return Summary(
            ts=msg.ts,
            who=msg.who,
            lang=msg.lang,
            text=text,
            tokens=tokens,
            keywords=keys[: self.max_ner_t1],
        )
