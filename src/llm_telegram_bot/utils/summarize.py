# src/llm_telegram_bot/utils/summarize.py

import os
import re

import nltk
import spacy
from sumy.nlp.tokenizers import Tokenizer
from sumy.parsers.plaintext import PlaintextParser
from sumy.summarizers.lex_rank import LexRankSummarizer
from sumy.summarizers.lsa import LsaSummarizer
from sumy.summarizers.text_rank import TextRankSummarizer

nltk.data.path.append(os.path.join(os.getcwd(), '.venv/nltk_data'))

from typing import List

from llm_telegram_bot.utils.logger import logger

# Cache for models
_NLP_CACHE = {}

# de_core_news_sm, de_core_news_md, de_core_news_lg, de_core_news_trf
_GERMAN_MODEL = "de_core_news_md"
# en_core_web_sm, en_core_web_md, en_core_web_lg, en_core_web_trf
_ENGLISH_MODEL = "en_core_web_sm"

# the English labels you care about:
_EN_LABELS = {
    "PERSON",
    "WORK_OF_ART",  # movies, books etc.
    "GPE",  # geopolitical entities: countries, states, cities
    # "LOC",  # locations, including regions and geographical features
    # "FAC",  # facilities: buildings ("Empire State Building") or airports
    # "ORG",  # organizations: companies, universities, or teams
    # "NORP",  # nationalities, religious groups, political parties
    # "EVENT",  # events, like "Olympics" or "World Cup".
    # "PRODUCT",  # such as "iPhone" or "Nike shoes"
}

# the German labels spaCy actually uses:
_DE_LABELS = {
    "PER",  # equivalent of english model's "PERSON"
    "MISC",  # often WORK_OF_ART or similar
    "GPE",  # geopolitical entities: countries, states, cities
    "LOC",  # locations, including regions and geographical features
    "ORG",  # organizations: companies, universities, or teams
}

_EMOJI_RE = re.compile(
    "["
    "\U0001f300-\U0001f6ff"  # symbols & pictographs
    "\U0001f900-\U0001f9ff"  # supplemental symbols & pictographs
    "\u2600-\u26ff"  # miscellaneous symbols
    "\u2700-\u27bf"  # dingbats
    "]"
)

# only allow letters, spaces, hyphens, apostrophes inside
# means name has at least one forbidden character (e.g. +, *, /, punctuation, emoji)
_INTERNAL_CLEAN_RE = re.compile(r"[^\w\s\-']")


def _get_nlp(lang: str):
    """
    Load or cache a spaCy model for en / de fallback.

    Note: well, de_core_news_md is shit even for German persons and movie names,
    but what you gonna

    """
    model = _GERMAN_MODEL if lang.startswith("de") else _ENGLISH_MODEL
    if model not in _NLP_CACHE:
        try:
            _NLP_CACHE[model] = spacy.load(model)
        except Exception:
            logger.warning(f"spaCy model {model} not found; falling back to english")
            _NLP_CACHE[model] = spacy.load("en_core_web_sm")
    return _NLP_CACHE[model]


def extract_named_entities(text: str, lang: str = "english") -> List[str]:
    """
    Extract PERSON/LOC/MISC (German) or PERSON/LOC/GPE/WORK_OF_ART (English),
    then aggressively clean:
      - strip punctuation and emojis at ends
      - drop entries with internal emojis or stray symbols
      - require each word to start uppercase
    """
    # 1) Normalize bullets & whitespace
    # Remove leading “- ” on each line
    no_bullets = re.sub(r"(?m)^\s*-\s*", "", text)
    # Collapse newlines/tabs into spaces; then collapse multiple spaces down to one
    cleaned = no_bullets.replace("\n", " ").replace("\t", " ")
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()

    # 2) spaCy NER pass
    code = "de" if lang.startswith("de") else "en"
    nlp = _get_nlp(code)
    doc = nlp(cleaned)

    # 3) Choose allowed labels by language
    if code == "de":
        allowed = _DE_LABELS
    else:
        allowed = _EN_LABELS

    seen = set()
    raw = []
    for ent in doc.ents:
        if ent.label_ not in allowed:
            continue
        # require at least one PROPN
        if not any(tok.pos_ == "PROPN" for tok in ent):
            continue
        raw.append(ent.text.strip())

    # logger.debug(f"[NER] pre‐clean: {raw}")

    # 4) Post‐filter & normalize
    out = []
    for name in raw:
        # a) strip leading/trailing punctuation & emojis
        name = name.strip(" \t\n" + "!?',.:;…—–-")  # common punctuation
        name = _EMOJI_RE.sub("", name).strip()

        # b) drop if empty or too short
        if len(name) < 3:
            continue
        # c) drop if internal emojis or forbidden chars
        if _EMOJI_RE.search(name):
            continue
        if _INTERNAL_CLEAN_RE.search(name):
            continue
        # d) require each word to start uppercase
        # words = name.split()
        # if not w[1].isupper() for w in words):
        #     continue

        key = name.lower()
        if key not in seen:
            seen.add(key)
            out.append(name)

    # logger.debug(f"[NER] post‐clean: {out}")

    # 5) German fallback
    if code == "de" and not out:
        pattern = re.compile(r"(?m)^\s*-\s*([^,]+)")
        for m in pattern.findall(text):
            nm = m.strip()
            # apply same cleaning
            nm = nm.strip(" \t\n!?,.:;…—–-")
            nm = _EMOJI_RE.sub("", nm).strip()
            if len(nm) < 2 or _INTERNAL_CLEAN_RE.search(nm):
                continue
            words = nm.split()
            if any(not w[0].isupper() for w in words):
                continue
            key = nm.lower()
            if key not in seen:
                seen.add(key)
                out.append(nm)

    return out


def summarize_text(text: str, num_sentences: int, lang: str = "english") -> str:
    """
    Summarize `text` down to `num_sentences` using TextRank,
    with language‐specific tokenization.
    """
    parser = PlaintextParser.from_string(text, Tokenizer(lang))
    summarizer = TextRankSummarizer()
    summary = " ".join(str(sentence) for sentence in summarizer(parser.document, num_sentences))

    return summary


def get_summarizer(method: str):
    if method.lower() == "lexrank":
        return LexRankSummarizer()
    if method.lower() == "lsa":
        return LsaSummarizer()
    return TextRankSummarizer()


def safe_summarize(text: str, num_sentences: int, lang: str = "en", method: str = "lexrank") -> str:
    """
    Try summarizing `text` to `num_sentences` using LexRank (by default).
    If that fails for any reason, fall back to English, then to the raw text.
    """
    for attempt_lang in (lang, "en"):

        try:
            parser = PlaintextParser.from_string(text, Tokenizer(attempt_lang))

            # logger.info(f"[Summarizer] Using {method} to summarize text in langugae '{attempt_lang}'")

            summarizer = get_summarizer(method)
            summary_sentences = summarizer(parser.document, num_sentences)
            return " ".join(str(s) for s in summary_sentences)

        except Exception as e:
            logger.warning(f"[Summarizer] {method} failed on lang={attempt_lang}: {e}")

    # Give up and return raw
    return text
