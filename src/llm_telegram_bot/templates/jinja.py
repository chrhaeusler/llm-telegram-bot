# src/llm_telegram_bot/templates/jinja.py

from types import SimpleNamespace
from typing import Any, Union

from jinja2 import Template


def _to_namespace(obj: Any) -> Any:
    if isinstance(obj, dict):
        return SimpleNamespace(**{k: _to_namespace(v) for k, v in obj.items()})
    elif isinstance(obj, list):
        return [_to_namespace(v) for v in obj]
    else:
        return obj


def render_template(
    template_str: str,
    *,
    char: Union[dict, SimpleNamespace],
    user: Union[dict, SimpleNamespace],
    **kwargs: Any,
) -> str:
    """
    Render Jinja2 template string with char, user, and optional extra context.
    """
    char_ns = _to_namespace(char) if isinstance(char, dict) else char
    user_ns = _to_namespace(user) if isinstance(user, dict) else user

    template = Template(template_str)
    # Pass char, user plus all extra kwargs to the template
    return template.render(char=char_ns, user=user_ns, **kwargs)
