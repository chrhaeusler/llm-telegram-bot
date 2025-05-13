# src/llm_telegram_bot/utils/summarize.py
import os

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

# Cache small models
_NLP_CACHE = {}


def _get_nlp(lang: str):
    """Load or cache a spaCy model for en / de fallback."""
    model = "en_core_web_sm" if lang.startswith("en") else "de_core_news_sm"
    if model not in _NLP_CACHE:
        try:
            _NLP_CACHE[model] = spacy.load(model)
        except Exception:
            logger.warning(f"spaCy model {model} not found; falling back to english")
            _NLP_CACHE[model] = spacy.load("en_core_web_sm")
    return _NLP_CACHE[model]


def extract_named_entities(text: str, lang: str = "english") -> List[str]:
    """
    Pull out PERSON, ORG, GPE, DATE and proper nouns from `text`.
    """
    # map lang token to spaCy model key
    code = "en" if lang.startswith("en") else "de"
    nlp = _get_nlp(code)
    doc = nlp(text)
    ents = [ent.text for ent in doc.ents if ent.label_ in {"PERSON", "ORG", "GPE", "DATE"}]
    # also grab proper nouns not in ents
    # ents += [tok.text for tok in doc if tok.pos_ == "PROPN"]
    # preserve order & dedupe
    seen = set()
    out = []
    for e in ents:
        if e.lower() not in seen:
            seen.add(e.lower())
            out.append(e)
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

            logger.info(f"[Summarizer] Using {method} to summarize text in langugae '{attempt_lang}'")

            summarizer = get_summarizer(method)
            summary_sentences = summarizer(parser.document, num_sentences)
            return " ".join(str(s) for s in summary_sentences)

        except Exception as e:
            logger.warning(f"[Summarizer] {method} failed on lang={attempt_lang}: {e}")

    # Give up and return raw
    return text
