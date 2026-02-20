# payload_viewer/diff_engine.py
from __future__ import annotations
import json
from typing import Dict, List, Iterable
from deepdiff import DeepDiff

def _parse_json_maybe(s: str):
    try:
        return json.loads(s)
    except Exception:
        return None  # signal parse error

def compare_rows(
    current_rows: Iterable[Dict[str, str]],
    old_rows: Iterable[Dict[str, str]],
    array_semantics: str = "by_index",  # or "as_set"
) -> List[Dict[str, str]]:
    """
    Returns per-key diff records:
    fields: config_name, config_key, status, old_json, current_json, diff_summary, parse_error, old_typed, current_typed
    status ∈ {added, removed, changed, unchanged, parse_error}
    """
    cur_map = {}
    for r in current_rows:
        k = (r["config_name"].strip(), r["config_key"].strip())
        if k not in cur_map:
            cur_map[k] = r

    old_map = {}
    for r in old_rows:
        k = (r["config_name"].strip(), r["config_key"].strip())
        if k not in old_map:
            old_map[k] = r

    all_keys = set(cur_map.keys()) | set(old_map.keys())

    dd_kwargs = dict(
        ignore_order=(array_semantics == "as_set"),
        report_repetition=True,
    )

    results: List[Dict[str, str]] = []
    for k in sorted(all_keys):
        cn, ck = k
        cur = cur_map.get(k)
        old = old_map.get(k)

        cur_s = cur["current_json"] if cur else ""
        old_s = old["old_json"] if old else ""

        cur_obj = _parse_json_maybe(cur_s) if cur is not None else None
        old_obj = _parse_json_maybe(old_s) if old is not None else None

        parse_error = ""
        if cur is not None and cur_s and cur_obj is None:
            parse_error = "CURRENT JSON parse error"
        if old is not None and old_s and old_obj is None:
            parse_error = (parse_error + "; " if parse_error else "") + "OLD JSON parse error"

        if old is None and cur is not None:
            status = "added"; dd = None
        elif old is not None and cur is None:
            status = "removed"; dd = None
        else:
            if cur_obj is None or old_obj is None:
                status = "parse_error"; dd = None
            else:
                dd = DeepDiff(old_obj, cur_obj, **dd_kwargs)
                status = "unchanged" if not dd else "changed"

        def typed_hint(s: str) -> str:
            if not s:
                return ""
            try:
                obj = json.loads(s)
                t = type(obj).__name__
            except Exception:
                t = "str"
            return f"{s} |<{t}>"

        results.append({
            "config_name": cn,
            "config_key": ck,
            "status": status,
            "old_json": old_s,
            "current_json": cur_s,
            "diff_summary": "" if dd is None else dd.to_json(),
            "parse_error": parse_error,
            "old_typed": typed_hint(old_s),
            "current_typed": typed_hint(cur_s),
        })

    return results
