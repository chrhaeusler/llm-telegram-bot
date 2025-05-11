# src/llm_telegram_bot/utils/message_utils.py

import datetime
import logging
from typing import Any, Dict, List, Union

from llm_telegram_bot.config.config_loader import load_jailbreaks
from llm_telegram_bot.templates.jinja import render_template
from llm_telegram_bot.utils.logger import logger

logger = logging.getLogger(__name__)


def iso_ts() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def split_message(text: str, limit: int = 4096) -> list[str]:
    """
    Splits a long message into chunks suitable for Telegram (max 4096 chars).
    Attempts to split at paragraph or sentence boundaries if possible.
    """
    chunks: List[str] = []
    while len(text) > limit:
        # Try to split at the last newline before limit
        split_index = text.rfind("\n", 0, limit)
        if split_index == -1:
            # Try to split at the last space
            split_index = text.rfind(" ", 0, limit)
        if split_index == -1:
            split_index = limit  # hard cut

        chunks.append(text[:split_index].strip())
        text = text[split_index:].strip()

    if text:
        chunks.append(text)
    return chunks


# ─── History Summarization Utilities ─────────────────────────────────────


def summarize_history(history: list[dict]) -> str:
    """
    Fallback summarizer: take the last 5 entries and format them as 'who: text'.
    """
    lines = [f"{entry['who']}: {entry['text']}" for entry in history if 'who' in entry and 'text' in entry]
    return "\n".join(lines[-5:]) if lines else "No summary available."


# ─── Full Prompt Builder ─────────────────────────────────────────────────


def build_full_prompt(
    char: dict[str, Any],
    user: dict[str, Any],
    jailbreak: Union[int, str, bool],
    context: Dict[str, List[Any]],  # {'overview': [...], 'midterm': [...], 'recent': [...]}
    user_text: str,
    *,
    system_enabled: bool = True,
) -> str:
    """
    Assemble the LLM prompt in five stages:
      1) Rendered jailbreak / system instructions
      2) [OVERVIEW] (Tier-2 aggregated summaries)
      3) [SUMMARY] (Tier-1 intermediate summaries)
      4) [RECENT] (Tier-0 raw or lightly-compressed messages)
      5) [PROMPT] user's current message
    """

    # 1) Render jailbreak/system block
    rendered_jb = ""
    if isinstance(jailbreak, str):
        jb = load_jailbreaks().get(jailbreak, {})
        tpl = jb.get("prompt", "").strip()
        if tpl and isinstance(char, dict) and isinstance(user, dict):
            try:
                rendered_jb = render_template(tpl, char=char, user=user)
            except Exception as e:
                logger.warning(f"[Prompt] Skipping jailbreak render: {e}")

    parts: List[str] = []
    if system_enabled and rendered_jb:
        parts.append(rendered_jb)

    # 2) Tier-2 OVERVIEW
    overview = context.get("overview", [])
    if overview:
        parts.append("[OVERVIEW]")
        for mega in overview:
            parts.append(f"- {mega.text}  ({mega.tokens} toks)")

    # 3) Tier-1 SUMMARY
    midterm = context.get("midterm", [])
    if midterm:
        parts.append("[SUMMARY]")
        for summ in midterm:
            parts.append(f"- {summ.text}  ({summ.tokens} toks)")

    # 4) Tier-0 RECENT MESSAGES
    recent = context.get("recent", [])
    if recent:
        parts.append("[RECENT]")
        for msg in recent:
            who = msg.who
            snippet = getattr(msg, "compressed", msg.text)
            toks = msg.tokens_compressed
            parts.append(f"{who}: {snippet}  ({toks} toks)")

    # 5) Final user prompt
    parts.append("[PROMPT]")
    parts.append(user_text)

    return "\n\n".join(parts)
