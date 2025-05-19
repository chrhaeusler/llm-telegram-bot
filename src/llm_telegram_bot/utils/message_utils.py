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
def _unique_preserve_order(items: List[str]) -> List[str]:
    """Deduplicate a list of strings (case‐insensitive), preserving first occurrence."""
    seen = set()
    out = []
    for it in items:
        key = it.lower()
        if key not in seen:
            seen.add(key)
            out.append(it)
    return out


def build_full_prompt(
    char: Dict[str, Any],
    user: Dict[str, Any],
    jailbreak: Union[int, str, bool],
    context: Dict[str, List[Any]],  # now includes 'tier0', 'tier0_keys', etc.
    user_text: str,
    *,
    system_enabled: bool = True,
) -> str:
    """
    Assemble the LLM prompt in five stages, now including per-tier NER buckets:
      1) Rendered jailbreak / system instructions
      2) [START OF THE CONVERSATION] (Tier-2 summaries)
        + [NAMED ENTITIES IN START OF CONVERSATION] (tier2_keys)
      3) [EARLY CONVERSATION] (Tier-1 summaries)
        + [NAMED ENTITIES IN EARLY CONVERSATION] (tier1_keys)
      4) [RECENT CONVERSATION] (Tier-0 messages)
        + [NAMED ENTITIES IN RECENT CONVERSATION] (tier0_keys)
      5) [PROMPT] user's current message
    """
    parts: List[str] = []

    # 1) System / jailbreak
    rendered_jb = ""
    if isinstance(jailbreak, str):
        jb = load_jailbreaks().get(jailbreak, {})
        tpl = jb.get("prompt", "").strip()
        if tpl:
            try:
                rendered_jb = render_template(tpl, char=char, user=user)
            except Exception as e:
                logger.warning(f"[Prompt] Skipping jailbreak render: {e}")
    if system_enabled and rendered_jb:
        parts.append(rendered_jb)

    # Tier-2 NERs
    tier2 = context.get("tier2", [])
    tier2_keys = _unique_preserve_order(context.get("tier2_keys", []))
    if tier2:
        parts.append("[START OF THE CONVERSATION]")
        for mega in tier2:
            parts.append(mega.text)
        if tier2_keys:
            parts.append("[NAMED ENTITIES IN START OF CONVERSATION]")
            parts.append(", ".join(tier2_keys))

    # Tier-1 text
    tier1 = context.get("tier1", [])
    tier1_keys = _unique_preserve_order(context.get("tier1_keys", []))
    if tier1:
        parts.append("[EARLY CONVERSATION]")
        for summ in tier1:
            parts.append(f"{summ.who.capitalize()}: {summ.text}")
        if tier1_keys:
            parts.append("[NAMED ENTITIES IN EARLY CONVERSATION]")
            parts.append(", ".join(tier1_keys))

    # Tier-0 text
    tier0 = context.get("tier0", [])
    tier0_keys = _unique_preserve_order(context.get("tier0_keys", []))
    if tier0:
        parts.append("[RECENT CONVERSATION]")
        for msg in tier0:
            snippet = getattr(msg, "compressed", msg.text)
            parts.append(f"{msg.who}: {snippet}")

        # For now do not provide named entities in tier0
        if tier0_keys:
            parts.append("[NAMED ENTITIES IN RECENT CONVERSATION]")
            parts.append(", ".join(tier0_keys))

    # Final user prompt
    parts.append("[PROMPT]")
    parts.append(user_text)

    return "\n\n".join(parts)
