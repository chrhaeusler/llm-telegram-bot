# src/utils/history_file.py

# TO DO: obsolete now
# All of its logic (templating the filename and wrapping dicts as AttrDict) has been
# upstreamed into
# Session.flush_history_to_disk and
# Session.load_history_from_disk methods

from typing import Any, Union

from jinja2 import Template


class AttrDict(dict[str, Any]):
    def __getattr__(self, item: str) -> Union["AttrDict", Any]:
        try:
            value = self[item]
            # Recursively wrap dictionaries as AttrDict for nested access
            return AttrDict(value) if isinstance(value, dict) else value
        except KeyError:
            raise AttributeError(f"Missing attribute '{item}' in AttrDict")


def render_history_filename(template_str: str, user_data: AttrDict, char_data: AttrDict) -> str:
    template = Template(template_str)
    return template.render(user=user_data, char=char_data)
