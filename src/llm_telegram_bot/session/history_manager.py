# src/llm_telegram_bot/session/history_manager.py
import datetime
import re
from collections import Counter, deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional

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

        self._last_bot_ts: Optional[datetime.datetime] = None

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
        # Tier-0 → Tier-1 promotion
        while len(self.tier0) > self.N0:
            old = self.tier0.popleft()
            summ = self._compress_t1(old)
            self.tier1.append(summ)
            for k in summ.keywords:
                self.tier1_keys.append(k)

        # Tier-1 → Tier-2 promotion
        while len(self.tier1) > self.N1:
            # at least 1
            # never more than K at once
            # never more than you have
            # = usually the fraction of K (at the moment 25%)
            batch_size = min(
                max(1, int(self.N1 * self.FRACTION_TO_SUMMARIZE)),
                self.K,
                len(self.tier1),
            )

            batch: list[Summary] = [self.tier1.popleft() for _ in range(batch_size)]
            # some cleaning of the sentences so they get summarized better
            processed_texts = []
            for s in batch:
                text = s.text.rstrip()
                if not text.endswith(('.', '!', '?')):
                    text += "."
                processed_texts.append(text)

            batch_blob = " ".join(processed_texts)

            # Get time span of current batch
            span_start = min(s.ts for s in batch)
            span_end = max(s.ts for s in batch)

            # Include previous Tier-2 summary (if exists)
            if self.tier2:
                prev = self.tier2.popleft()
                full_blob = prev.text + "\n\n" + batch_blob
                span_start = min(span_start, prev.span_start)
                span_end = max(span_end, prev.span_end)
                existing_keys = deque(prev.keywords)
            else:
                full_blob = batch_blob
                existing_keys = deque()

            # Choose language from current batch
            langs = [s.lang for s in batch if s.lang != "unknown"]
            chosen_lang = Counter(langs).most_common(1)[0][0] if langs else "english"

            # Summarize the full blob into Tier-2 "mega summary"
            cap = self.T2_cap
            num_sents = max(1, cap // TOKENS_PER_SENTENCE)
            mega_text = safe_summarize(
                full_blob,
                num_sentences=num_sents,
                lang=chosen_lang,
                method="lsa",  # or texrank or lexrank
            )

            mega_tokens = count_tokens(mega_text)

            # Extract fresh keywords from batch_blob only (Tier-1 summaries)
            new_keys = deque(extract_named_entities(batch_blob, lang=chosen_lang))

            # Merge with existing Tier-2 keys (from previous summary)
            for k in new_keys:
                existing_keys.append(k)

            # Deduplicate and truncate keys
            deduped = list(dict.fromkeys(existing_keys))  # preserves order
            deduped = deduped[-self.max_ner_t2 :]  # keep last N only

            # Save new Tier-2 mega-summary
            mega = MegaSummary(
                text=mega_text,
                keywords=deduped,
                tokens=mega_tokens,
                span_start=span_start,
                span_end=span_end,
                is_stub=True,
            )
            self.tier2.append(mega)

            # Refresh Tier-2 keyword bucket
            self.tier2_keys.clear()
            for k in deduped:
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

        # logger.debug(f"[add_user] {msg.who} at {msg.ts}, toks={msg.tokens_compressed}, keys={msg.keywords}")
        self.tier0.append(msg)

        # ---- record last‐bot timestamp for context logic ----
        try:
            # parse your ts format "YYYY-MM-DD_HH-MM-SS"
            self._last_bot_ts = datetime.datetime.strptime(msg.ts, "%Y-%m-%d_%H-%M-%S")
        except Exception:
            logger.warning(f"[HistoryManager] could not parse bot ts: {msg.ts}")
            self._last_bot_ts = None

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

        # logger.debug(f"[add_bot] {msg.who} at {msg.ts}, toks={msg.tokens_compressed}, keys={msg.keywords}")
        self.tier0.append(msg)
        self._maybe_promote()

    # this is for chars suggestion a list of option on how to proceed the conversation
    def remove_lettered_lists(self, text: str) -> str:
        cleaned = re.sub(r'(?m)^\s*[a-z0-9]\)\s.*$', '', text)
        return re.sub(r'\n{2,}', '\n\n', cleaned).strip()

    def _compress_t0(self, msg: Message) -> None:
        # always remove lettered list
        # for chars giving options on how to proceed, like a) option 1, b) option 2
        msg.text = self.remove_lettered_lists(msg.text.replace("...", "."))

        # just take short messages as they are
        L, cap = msg.tokens_text, self.T0_cap
        if L <= cap:
            msg.compressed = msg.text
            msg.tokens_compressed = L
            return

        num_sents = max(1, cap // TOKENS_PER_SENTENCE)
        try:
            summary = safe_summarize(
                msg.text,
                num_sentences=num_sents,
                lang=msg.lang,
                method="lsa",  # or texrank or lexrank
            )

        except Exception as e:
            logger.warning(f"[compress_t0] failed: {e}")
            summary = msg.text

        msg.compressed = summary
        msg.tokens_compressed = count_tokens(summary)

    def _compress_t1(self, msg: Message) -> Summary:
        cap = self.T1_cap
        num_sents = max(1, cap // TOKENS_PER_SENTENCE)
        try:
            text = safe_summarize(
                msg.compressed, num_sentences=num_sents, lang=msg.lang, method="lsa"  # or texrank or lexrank
            )

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

    @property
    def last_llm_response_time(self) -> Optional[datetime.datetime]:
        """
        Returns the timestamp of the most recent bot (LLM) message in tier0,
        parsed into a datetime, or None if no such message exists.
        """
        bot_name = self.bot_name  # the identity name used for LLM replies
        # scan tier0 in reverse (newest messages at the end of deque)
        for msg in reversed(self.tier0):
            if msg.who == bot_name:
                try:
                    # assuming ts format is "YYYY-MM-DD_HH-MM-SS"
                    return datetime.datetime.strptime(msg.ts, "%Y-%m-%d_%H-%M-%S")
                except ValueError:
                    logger.warning(f"[HistoryManager] could not parse ts: {msg.ts}")
                    return None

        return self._last_bot_ts
