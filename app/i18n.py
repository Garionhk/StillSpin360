"""Interface translation, in the same style as EasyAI.

Strings are looked up by their English text, so the source stays readable and a missing
translation falls back to English:

    label.setText(t("Create 360° Spin"))

Catalogues live in app/lang/<code>.json as a flat {english: translated} map. Placeholders
are filled after lookup, so a translation can move {fields} to wherever its grammar needs.
"""

import json
import locale
import os
from pathlib import Path

LANG_DIR = Path(__file__).resolve().parent / "lang"

# Each language is named in itself, so someone stuck in the wrong one can still find the way out.
LANGUAGES = {
    "en": "English",
    "zh-Hant": "繁體中文",
}
DEFAULT = "en"

_current = DEFAULT
_catalogue: dict[str, str] = {}
_missing: set[str] = set()


def detect() -> str:
    """Guess from Windows: zh-TW / zh-HK / zh-MO open in Traditional Chinese."""
    try:
        raw = locale.getdefaultlocale()[0] or ""
    except (ValueError, TypeError):
        raw = ""
    raw = (raw or os.environ.get("LANG", "")).replace("_", "-").lower()
    if raw.startswith("zh") and ("hant" in raw or any(r in raw for r in ("-tw", "-hk", "-mo"))):
        return "zh-Hant"
    return DEFAULT


def load(code: str) -> str:
    """Switch language; returns the code actually in use."""
    global _current, _catalogue
    if code not in LANGUAGES:
        code = DEFAULT
    _catalogue = {}
    if code != DEFAULT:
        try:
            # utf-8-sig: Notepad saves JSON with a byte order mark.
            raw = json.loads((LANG_DIR / f"{code}.json").read_text(encoding="utf-8-sig"))
            _catalogue = {k: v for k, v in raw.items() if not k.startswith("_") and isinstance(v, str) and v}
        except (OSError, json.JSONDecodeError):
            code = DEFAULT    # a damaged catalogue must never stop the app opening
    _current = code
    return code


def current() -> str:
    return _current


def t(text: str, **fields) -> str:
    out = _catalogue.get(text, text)
    if out is text and _current != DEFAULT:
        _missing.add(text)
    if fields:
        try:
            out = out.format(**fields)
        except (KeyError, IndexError, ValueError):
            try:
                out = text.format(**fields)
            except (KeyError, IndexError, ValueError):
                return text
    return out


def N(text: str) -> str:
    """Mark text for translation without translating it yet (for tables defined at import)."""
    return text


def missing() -> set[str]:
    return set(_missing)
