# payload_viewer/json_utils.py
from __future__ import annotations

import re
import json
import ast
from typing import Any, List, Tuple, Optional

try:
    import orjson  # optional, faster pretty JSON
except Exception:
    orjson = None


TRAILING_COMMAS = re.compile(r',\s*([}\]])')


def parse_jsonish_verbose(s: str) -> Tuple[Any, str]:
    """
    Return (parsed_obj, error_message_if_any).

    Tries, in order:
      1) strict json.loads
      2) json.loads after removing trailing commas
      3) ast.literal_eval (Python literal)

    If all fail, returns (None, "<reason>").
    """
    t = (s or "").strip()
    if not t:
        return None, "Empty payload"

    # 1) strict JSON
    try:
        return json.loads(t), ""
    except json.JSONDecodeError:
        pass

    # 2) remove trailing commas
    try:
        t2 = TRAILING_COMMAS.sub(r"\1", t)
        return json.loads(t2), ""
    except json.JSONDecodeError:
        pass

    # 3) Python literal
    try:
        return ast.literal_eval(t), ""
    except (ValueError, SyntaxError, TypeError) as e:
        return None, f"Failed to parse payload ({e.__class__.__name__})"


def pretty_json(obj: Any) -> str:
    """
    Pretty print a Python object as JSON text.
    Uses orjson if available, else json.dumps.
    """
    if obj is None:
        return ""
    # orjson first
    if orjson is not None:
        try:
            return orjson.dumps(obj, option=orjson.OPT_INDENT_2).decode("utf-8")
        except Exception:
            pass
    # stdlib
    try:
        return json.dumps(obj, indent=2, ensure_ascii=False)
    except Exception:
        return str(obj)


def dd_path_to_key(p: str) -> str:
    """
    Convert DeepDiff paths like:   root['a'][2]['b']
    into a readable dotted/index path: a[2].b
    """
    if not p:
        return ""
    out = p.replace("root", "")
    out = re.sub(r"\['([^']*)'\]", r".\1", out)   # keys
    out = re.sub(r"\[(\d+)\]", r"[\1]", out)      # indices (kept)
    return out.lstrip(".")


def _path_tokens(path: str) -> List[str]:
    """
    Split 'a[2].b.c[10]' -> ['a', '[2]', 'b', 'c', '[10]']
    """
    return [tok for tok in re.split(r'\.|(\[\d+\])', path) if tok]


def value_from_path(obj: Any, dd_path: str) -> Any:
    """
    Follow a DeepDiff path string in obj and return the value if found.
    dd_path example: "root['a'][2]['b']"
    """
    dotted = dd_path_to_key(dd_path)  # a[2].b
    toks = _path_tokens(dotted)
    cur = obj
    try:
        for t in toks:
            if t.startswith('[') and t.endswith(']'):
                idx = int(t[1:-1])
                cur = cur[idx]
            else:
                cur = cur[t]
        return cur
    except (KeyError, IndexError, TypeError):
        return None


def build_fragment_from_path_value(path: str, value: Any) -> Any:
    """
    Build a minimal JSON fragment showing the leaf at `path` with `value`.
    Example: path="a.b[2].c" -> {"a":{"b":[null,null,{"c": value}]}}
    """
    tokens = _path_tokens(path)
    if not tokens:
        return value

    fragment: Any = value
    for tok in reversed(tokens):
        if tok.startswith('[') and tok.endswith(']'):
            idx = int(tok[1:-1])
            new_list: List[Any] = [None] * (idx + 1)
            new_list[idx] = fragment
            fragment = new_list
        else:
            fragment = {tok: fragment}
    return fragment


__all__ = [
    "parse_jsonish_verbose",
    "pretty_json",
    "dd_path_to_key",
    "value_from_path",
    "build_fragment_from_path_value",
]