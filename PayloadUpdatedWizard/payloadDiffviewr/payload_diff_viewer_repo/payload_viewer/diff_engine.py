
"""DeepDiff wrapper and normalization utilities."""
from __future__ import annotations

from typing import Any

from deepdiff import DeepDiff


def _coerce_numeric_like(x: Any) -> Any:
    # Try int, then float; otherwise return x as-is
    if isinstance(x, str):
        s = x.strip()
        try:
            return int(s)
        except Exception:
            try:
                return float(s)
            except Exception:
                return x
    return x


def normalize_for_diff(x: Any, *, coerce_numeric: bool = True) -> Any:
    if isinstance(x, dict):
        return {k: normalize_for_diff(v, coerce_numeric=coerce_numeric) for k, v in x.items()}
    if isinstance(x, list):
        return [normalize_for_diff(v, coerce_numeric=coerce_numeric) for v in x]
    return _coerce_numeric_like(x) if coerce_numeric else x


def run_deepdiff(old: Any, new: Any, *, ignore_order: bool, coerce_numeric: bool = True) -> dict:
    norm_old = normalize_for_diff(old, coerce_numeric=coerce_numeric)
    norm_new = normalize_for_diff(new, coerce_numeric=coerce_numeric)
    diff = DeepDiff(
        norm_old,
        norm_new,
        ignore_order=ignore_order,
        report_repetition=True,
        verbose_level=2,
        view="tree",
    )
    return diff.to_dict()
