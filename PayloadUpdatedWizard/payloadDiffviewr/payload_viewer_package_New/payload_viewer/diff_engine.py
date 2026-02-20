from __future__ import annotations
from typing import Any
import re
from deepdiff import DeepDiff

# Treat plain decimal strings as numbers, but leave scientific notation as strings
_NUM_RE = re.compile(r"^-?(?:0|[1-9]\d*)(?:\.\d+)?$")

def _looks_numeric(s: str) -> bool:
    s = s.strip()
    if "e" in s.lower():       # keep 5.37126e+18 etc as string
        return False
    return bool(_NUM_RE.match(s))

def _coerce_scalar(x: Any) -> Any:
    if isinstance(x, str) and _looks_numeric(x):
        # int if possible, else float
        if "." in x:
            try:
                return float(x)
            except ValueError:
                return x
        try:
            return int(x)
        except ValueError:
            return x
    return x

def _coerce_tree(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _coerce_tree(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_coerce_tree(v) for v in obj]
    return _coerce_scalar(obj)

def run_deepdiff(
    old_obj: Any,
    new_obj: Any,
    *,
    ignore_order: bool = False,
    coerce_numeric_strings: bool = True,
    verbose_level: int = 2,
    **kwargs
) -> DeepDiff:
    """
    Compare two Python JSON-like objects with DeepDiff.

    Accepts both `coerce_numeric_strings` (preferred) and the legacy
    `coerce_numeric` keyword for backward compatibility.
    """
    # Back-compat: allow legacy kw
    if "coerce_numeric" in kwargs:
        coerce_numeric_strings = bool(kwargs.pop("coerce_numeric"))

    left = _coerce_tree(old_obj) if coerce_numeric_strings else old_obj
    right = _coerce_tree(new_obj) if coerce_numeric_strings else new_obj

    return DeepDiff(left, right, ignore_order=ignore_order, verbose_level=verbose_level)
