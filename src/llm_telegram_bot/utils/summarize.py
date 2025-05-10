# src/llm_telegram_bot/utils/summarize.py
import os

import nltk
from sumy.nlp.tokenizers import Tokenizer
from sumy.parsers.plaintext import PlaintextParser
from sumy.summarizers.text_rank import TextRankSummarizer

nltk.data.path.append(os.path.join(os.getcwd(), '.venv/nltk_data'))


def summarize_text(text: str, num_sentences: int, lang: str = "english") -> str:
    """
    Summarize `text` down to `num_sentences` using TextRank,
    with language‐specific tokenization.
    """
    parser = PlaintextParser.from_string(text, Tokenizer(lang))
    summarizer = TextRankSummarizer()
    return " ".join(str(sentence) for sentence in summarizer(parser.document, num_sentences))
