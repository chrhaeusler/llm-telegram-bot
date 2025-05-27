# src/llm_telegram_bot/utils/message_utils.py

import datetime
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from llm_telegram_bot.config.config_loader import load_jailbreaks
from llm_telegram_bot.templates.jinja import render_template
from llm_telegram_bot.utils.logger import logger

logger = logging.getLogger(__name__)


def iso_ts() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def strip_think_block(text: str) -> str:
    """Removes a think block from an LLM's reply

    Args:
        text (str):

    Returns:
        str: cleaned string
    """

    # 1. Cleaning of proper think bocks
    # Non-greedy match of anything between <think>...</think>
    # text_cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)

    # 2. Cleaning of strings from those models that do not sent the leading <think>
    # but just the trailing </think>
    # Look for the first occurrence of </think>
    end_idx = text.find("</think>")

    if end_idx != -1:
        # Remove everything up to and including </think>
        text_cleaned = text[end_idx + len("</think>") :].lstrip()
    else:
        text_cleaned = text

    return text_cleaned


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
    context: Dict[str, List[Any]],
    user_text: str,
    *,
    system_enabled: bool = True,
    now: Optional[datetime] = None,
    last_llm_response_time: Optional[datetime] = None,
) -> str:
    if now is None:
        now = datetime.utcnow()
    last = last_llm_response_time or now

    # 1) Compute elapsed seconds using .timestamp() to avoid tz issues
    try:
        delta_seconds = now.timestamp() - last.timestamp()
    except Exception:
        delta_seconds = 0.0

    # 2) If you want correct localized display, make `last` tz‐aware
    if now.tzinfo and not last.tzinfo:
        last = last.replace(tzinfo=now.tzinfo)

    # 3) Precompute formatting fields
    dow_last = last.strftime("%A")
    date_last = last.strftime("%Y-%m-%d")
    hour_last = last.strftime("%H")
    minute_last = last.strftime("%M")
    dow_now = now.strftime("%A")
    date_now = now.strftime("%Y-%m-%d")
    hour_now = now.strftime("%H")
    minute_now = now.strftime("%M")

    parts: List[str] = []

    # ── Stage 1: jailbreak/system ────────────────────────────────────────
    rendered_jb = ""
    if isinstance(jailbreak, str):
        jb = load_jailbreaks().get(jailbreak, {})
        tpl = jb.get("prompt", "").strip()
        if tpl:
            try:
                rendered_jb = render_template(
                    tpl,
                    char=char,
                    user=user,
                    now=now,
                    last_llm_response_time=last,
                    delta_seconds=delta_seconds,
                    day_of_week_last=dow_last,
                    date_last=date_last,
                    hour_last=hour_last,
                    minute_last=minute_last,
                    day_of_week_now=dow_now,
                    date_now=date_now,
                    hour_now=hour_now,
                    minute_now=minute_now,
                ).strip()
            except Exception as e:
                logger.warning(f"[Prompt] Skipping jailbreak render: {e}")
                logger.debug(f"Failed JB tpl: {tpl}")

    if system_enabled and rendered_jb:
        parts.append(rendered_jb)

    # ── Stage 2: Tier-2 OVERVIEW + NERs ──────────────────────────────────
    tier2 = context.get("tier2", [])
    tier2_keys = _unique_preserve_order(context.get("tier2_keys", []))
    if tier2:
        parts.append("[START OF THE CONVERSATION]")
        for mega in tier2:
            parts.append(mega.text)
        if tier2_keys:
            parts.append("[NAMED ENTITIES IN START OF CONVERSATION]")
            parts.append(", ".join(tier2_keys))

    # ── Stage 3: Tier-1 summaries + NERs ────────────────────────────────
    tier1 = context.get("tier1", [])
    tier1_keys = _unique_preserve_order(context.get("tier1_keys", []))
    if tier1:
        parts.append("[EARLY CONVERSATION]")
        for summ in tier1:
            parts.append(f"{summ.who.capitalize()}: {summ.text}")
        if tier1_keys:
            parts.append("[NAMED ENTITIES IN EARLY CONVERSATION]")
            parts.append(", ".join(tier1_keys))

    # ── Stage 4: Tier-0 messages + NERs ─────────────────────────────────
    tier0 = context.get("tier0", [])
    tier0_keys = _unique_preserve_order(context.get("tier0_keys", []))
    if tier0:
        parts.append("[RECENT CONVERSATION]")
        for msg in tier0:
            snippet = getattr(msg, "compressed", msg.text)
            parts.append(f"{msg.who}: {snippet}")
        if tier0_keys:
            parts.append("[NAMED ENTITIES IN RECENT CONVERSATION]")
            parts.append(", ".join(tier0_keys))

        # ── Stage 1b: user‐defined [CONTEXT] from user.yaml ─────────────────
    user_ctx_tpl = user.get("context", {}).get("template", "").strip()
    if user_ctx_tpl:
        try:
            rendered_user_ctx = render_template(
                user_ctx_tpl,
                char=char,
                user=user,
                now=now,
                last_llm_response_time=last,
                delta_seconds=delta_seconds,
                day_of_week_last=dow_last,
                date_last=date_last,
                hour_last=hour_last,
                minute_last=minute_last,
                day_of_week_now=dow_now,
                date_now=date_now,
                hour_now=hour_now,
                minute_now=minute_now,
            ).strip()
        except Exception as e:
            logger.warning(f"[Prompt] Skipping user-context render: {e}")
            logger.debug(f"Failed USER tpl: {user_ctx_tpl}")
            rendered_user_ctx = ""

        if rendered_user_ctx:
            parts.append("[CONTEXT]")
            parts.append(rendered_user_ctx)

    # ── Stage 5: Final user prompt ───────────────────────────────────────
    parts.append("[PROMPT]")
    parts.append(user_text)

    return "\n\n".join(parts)
