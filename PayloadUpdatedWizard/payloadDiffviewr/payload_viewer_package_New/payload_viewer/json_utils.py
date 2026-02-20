from __future__ import annotations

import ast
import json
import re
from json import JSONDecodeError
from typing import Any, List, Tuple

try:
    import orjson  # type: ignore
except Exception:
    orjson = None  # type: ignore

TRAILING_COMMAS = re.compile(r",\s*([}\]])")

def parse_jsonish_verbose(s: str) -> Tuple[Any, str]:
    """Return (parsed_obj, error_message_if_any).
    Tries strict JSON -> trailing-comma fix -> ast.literal_eval.
    """
    t = (s or "").strip()
    if not t:
        return None, "Empty payload"

    try:
        return json.loads(t), ""
    except JSONDecodeError:
        pass

    try:
        t2 = TRAILING_COMMAS.sub(r"\1", t)
        return json.loads(t2), ""
    except JSONDecodeError:
        pass

    try:
        return ast.literal_eval(t), ""
    except (ValueError, SyntaxError, TypeError) as e:
        return None, f"Failed to parse payload ({e.__class__.__name__})"

def pretty_json(obj: Any) -> str:
    if obj is None:
        return ""
    if orjson is not None:
        try:
            return orjson.dumps(obj, option=orjson.OPT_INDENT_2).decode()
        except Exception:
            pass
    try:
        return json.dumps(obj, indent=2, ensure_ascii=False)
    except Exception:
        return str(obj)

def dd_path_to_key(p: str) -> str:
    """DeepDiff path "root['a'][2]['b']" -> "a[2].b"""
    if not p:
        return ""
    p = p.replace("root", "")
    p = re.sub(r"\['([^']*)'\]", r".\1", p)
    p = re.sub(r"\[(\d+)\]", r"[\1]", p)
    return p.lstrip(".")

def _path_tokens(path: str) -> List[str]:
    """Turn 'a[2].b.c[10]' into ['a', '[2]', 'b', 'c', '[10]']"""
    return [tok for tok in re.split(r"\.|(\[\d+\])", path) if tok]

def value_from_path(obj: Any, dd_path: str) -> Any:
    dotted = dd_path_to_key(dd_path)
    toks = _path_tokens(dotted)
    cur = obj
    try:
        for t in toks:
            if t.startswith("[") and t.endswith("]"):
                idx = int(t[1:-1])
                cur = cur[idx]
            else:
                cur = cur[t]
        return cur
    except (KeyError, IndexError, TypeError):
        return None

def build_fragment_from_path_value(path: str, value: Any) -> Any:
    tokens = _path_tokens(path)
    if not tokens:
        return value
    fragment = value
    for tok in reversed(tokens):
        if tok.startswith("[") and tok.endswith("]"):
            idx = int(tok[1:-1])
            new_list = [None] * (idx + 1)
            new_list[idx] = fragment
            fragment = new_list
        else:
            fragment = {tok: fragment}
    return fragment

def format_cell_value(v: Any) -> str:
    """Render a value for the table with a light type hint for primitives."""
    if v is None:
        return ""
    if isinstance(v, bool):
        return f"{json.dumps(v)} (bool)"
    if isinstance(v, (int, float)):
        return f"{v} ({type(v).__name__})"
    if isinstance(v, str):
        return f"{json.dumps(v)} (str)"
    if isinstance(v, (dict, list)):
        try:
            return json.dumps(v, ensure_ascii=False)
        except TypeError:
            return str(v)
    return str(v)
