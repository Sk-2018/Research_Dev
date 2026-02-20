
"""JSON helpers: parse, pretty, stringify, and line finding for highlights."""
from __future__ import annotations

import json
import re
from typing import Any

try:
    import orjson as _orjson  # optional speedup
except Exception:  # pragma: no cover
    _orjson = None  # type: ignore


def try_parse_json(text: str) -> tuple[Any | None, str | None]:
    text = text.strip()
    if not text:
        return None, None
    try:
        if _orjson:
            return _orjson.loads(text), "orjson"
        return json.loads(text), "json"
    except Exception:
        return None, None


def json_to_pretty_text(obj: Any) -> str:
    try:
        if _orjson:
            return _orjson.dumps(
                obj,
                option=_orjson.OPT_INDENT_2 | _orjson.OPT_NON_STR_KEYS
            ).decode()
        return json.dumps(obj, indent=2, ensure_ascii=False)
    except Exception:
        return str(obj)


def stringify_for_diff(val: Any) -> str:
    # Stable representation to avoid flicker (e.g. 2 vs "2.0")
    if isinstance(val, (dict, list)):
        try:
            return json_to_pretty_text(val)
        except Exception:
            return str(val)
    return str(val)


def escape_path_for_regex(path: str) -> str:
    # Convert DeepDiff-like paths to regex-safe patterns
    # e.g., root['a'][0]['b'] → root\['a'\]\[0\]\['b'\]
    return re.sub(r"([\\.\[\]\(\){}^$+*?|])", r"\\\1", path)


def find_line_index(text: str, key_regex: str, value_hint: str | None = None) -> int | None:
    """Return 1-based line index of the best match, else None."""
    lines = text.splitlines()
    try:
        key_pat = re.compile(key_regex)
    except Exception:
        return None

    # First pass: look for lines that match key and contain value hint nearby
    if value_hint:
        for i, line in enumerate(lines, start=1):
            if key_pat.search(line):
                window = "\n".join(lines[max(1, i - 2) - 1: min(len(lines), i + 2)])
                if value_hint in window:
                    return i

    # Fallback: first line that matches key
    for i, line in enumerate(lines, start=1):
        if key_pat.search(line):
            return i

    # Last resort: search for value only
    if value_hint:
        for i, line in enumerate(lines, start=1):
            if value_hint in line:
                return i

    return None
