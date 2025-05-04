from types import SimpleNamespace
from typing import Union

from jinja2 import Template

from llm_telegram_bot.types.character import CharacterDict, UserDict


def render_template(
    template_str: str,
    *,
    char: Union[CharacterDict, SimpleNamespace],
    user: Union[UserDict, SimpleNamespace],
) -> str:
    """
    Renders a Jinja2 template string using char/user objects.
    Accepts keyword arguments 'char' and 'user' as typed dicts or objects.
    """
    if isinstance(char, str):
        raise TypeError(f"'char' should be a dict, not a string: {char}")
    if isinstance(user, str):
        raise TypeError(f"'user' should be a dict, not a string: {user}")

    char_ns = SimpleNamespace(**char) if isinstance(char, dict) else char
    user_ns = SimpleNamespace(**user) if isinstance(user, dict) else user

    template = Template(template_str)
    return template.render(char=char_ns, user=user_ns)
