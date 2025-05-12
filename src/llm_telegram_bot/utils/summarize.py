# src/llm_telegram_bot/utils/summarize.py
import os

import nltk
from sumy.nlp.tokenizers import Tokenizer
from sumy.parsers.plaintext import PlaintextParser
from sumy.summarizers.lex_rank import LexRankSummarizer
from sumy.summarizers.text_rank import TextRankSummarizer

nltk.data.path.append(os.path.join(os.getcwd(), '.venv/nltk_data'))

from llm_telegram_bot.utils.logger import logger


def summarize_text(text: str, num_sentences: int, lang: str = "english") -> str:
    """
    Summarize `text` down to `num_sentences` using TextRank,
    with language‐specific tokenization.
    """
    parser = PlaintextParser.from_string(text, Tokenizer(lang))
    summarizer = TextRankSummarizer()
    summary = " ".join(str(sentence) for sentence in summarizer(parser.document, num_sentences))

    return summary


def safe_summarize(text: str, num_sentences: int, lang: str = "english", method: str = "lexrank") -> str:
    """
    Try summarizing `text` to `num_sentences` using LexRank (by default).
    If that fails for any reason, fall back to English, then to the raw text.
    """
    for attempt_lang in (lang, "english"):

        try:
            parser = PlaintextParser.from_string(text, Tokenizer(attempt_lang))
            logger.info(f"[Summarizer] Using {method} to summarize text in langugae '{attempt_lang}'")
            summarizer = LexRankSummarizer() if method.lower() == "lexrank" else TextRankSummarizer()
            summary_sentences = summarizer(parser.document, num_sentences)
            return " ".join(str(s) for s in summary_sentences)

        except Exception as e:
            logger.warning(f"[Summarizer] {method} failed on lang={attempt_lang}: {e}")

    # Give up and return raw
    return text
