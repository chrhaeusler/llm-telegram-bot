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

# Cache small models
_NLP_CACHE = {}


def _get_nlp(lang: str):
    """
    Load or cache a spaCy model for en / de fallback.

    Note: well, de_core_news_md is shit even for German persons and movie names,
    but what you gonna

    """
    # TO DO: chose an appropriate model `de_core_news_lg`
    # is to large for the raspberry pi 4
    model = "de_core_news_sm" if lang.startswith("de") else "en_core_web_sm"
    if model not in _NLP_CACHE:
        try:
            _NLP_CACHE[model] = spacy.load(model)
        except Exception:
            logger.warning(f"spaCy model {model} not found; falling back to english")
            _NLP_CACHE[model] = spacy.load("en_core_web_sm")
    return _NLP_CACHE[model]


def extract_named_entities(text: str, lang: str = "english") -> List[str]:
    """
    Pull out PERSON, ORG, GPE, DATE, proper nouns, etc. from `text`.
    Pre-clean by removing special characters and single-digit numbers.
    If lang starts with "de", run both German and English NER and merge uniques.
    """
    # Keep letters, numbers, whitespace, dots, semicolons, colons, and dashes

    cleaned = re.sub(r"[^A-Za-z0-9ÄÖÜäöüß\s\.\;\:\-\(\)]", " ", text)
    # 2) Strip standalone single-digit tokens
    cleaned = re.sub(r"\b\d\b", "", cleaned)
    # 3) Collapse multiple spaces
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()

    def _ents_from_doc(doc) -> List[str]:
        allowed = {
            "PERSON",
            "WORK_OF_ART",  # movies, books etc.
            "GPE",  # geopolitical entities: countries, states, cities
            "LOC",  # locations, including regions and geographical features
            # "FAC",  # facilities: buildings ("Empire State Building") or airports
            # "ORG",  # organizations: companies, universities, or teams
            # "NORP",  # nationalities, religious groups, political parties
            # "EVENT",  # events, like "Olympics" or "World Cup".
            # "PRODUCT",  # such as "iPhone" or "Nike shoes"
        }
        seen = set()
        out = []
        for ent in doc.ents:
            if ent.label_ in allowed:
                e = ent.text.strip()
                key = e.lower()
                if key and key not in seen:
                    seen.add(key)
                    out.append(e)
        return out

    # choose model code
    code = "de" if lang.startswith("de") else "en"
    nlp = _get_nlp(code)
    doc = nlp(cleaned)
    return _ents_from_doc(doc)


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
