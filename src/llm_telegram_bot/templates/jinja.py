# src/llm_telegram_bot/templates/jinja.py

from types import SimpleNamespace
from typing import Any, Union

from jinja2 import Template


def _to_namespace(obj: Any) -> Any:
    """
    Recursively convert dict→SimpleNamespace, list→list, else leave as is.
    """
    if isinstance(obj, dict):
        return SimpleNamespace(**{k: _to_namespace(v) for k, v in obj.items()})
    elif isinstance(obj, list):
        return [_to_namespace(v) for v in obj]
    else:
        return obj


def render_template(
    template_str: str, *, char: Union[dict, SimpleNamespace], user: Union[dict, SimpleNamespace]
) -> str:
    """
    Renders a Jinja2 template string using char/user objects.
    Accepts keyword arguments 'char' and 'user' as dicts or already-namespaced objects.
    """
    # Convert plain dicts into nested Namespaces
    char_ns = _to_namespace(char) if isinstance(char, dict) else char
    user_ns = _to_namespace(user) if isinstance(user, dict) else user

    template = Template(template_str)
    return template.render(char=char_ns, user=user_ns)
