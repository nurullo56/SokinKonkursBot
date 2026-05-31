import json
import os

_JSON_PATH = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "custom_emojis.json"))


def _load() -> dict[str, str]:
    if os.path.exists(_JSON_PATH):
        with open(_JSON_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


_CE: dict[str, str] = _load()


def ce(emoji: str) -> str:
    eid = _CE.get(emoji)
    if eid:
        return f'<tg-emoji emoji-id="{eid}">{emoji}</tg-emoji>'
    return emoji


def reload() -> None:
    _CE.clear()
    _CE.update(_load())
