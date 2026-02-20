import json
import re
from typing import Any, Optional, Tuple

try:
    import orjson
    ORJSON_AVAILABLE = True
except ImportError:
    ORJSON_AVAILABLE = False
    # Fallback to standard json
    import json as orjson # type: ignore
    print("orjson not found, falling back to standard json library.")


def try_parse_json(text: str) -> Tuple[Any | None, str | None]:
    """
    Tries to parse a string as JSON, preferring orjson if available.

    Args:
        text: The input string.

    Returns:
        A tuple (parsed_object, error_message).
        If successful, (object, None).
        If failed, (None, error_string).
    """
    if not text:
        return None, "Empty input"
        
    try:
        # orjson is significantly faster
        return orjson.loads(text), None
    except (orjson.JSONDecodeError, TypeError) as e:
        # Fallback for simple values json.loads might handle differently
        # or just to get a standard error message
        try:
            # Standard json might parse simple values orjson rejects
            return json.loads(text), None
        except json.JSONDecodeError as json_e:
            return None, f"JSON parse error: {json_e}"
    except Exception as e:
        return None, f"Unexpected parse error: {e}"


def json_to_pretty_text(obj: Any) -> str:
    """
    Converts a Python object to a pretty-printed, indented JSON string.

    Args:
        obj: The object to serialize.

    Returns:
        A formatted string.
    """
    if obj is None:
        return "null"
    if isinstance(obj, (str, int, float, bool)):
        return str(obj)
        
    try:
        if ORJSON_AVAILABLE:
            # Use orjson for performance, ensuring bytes are decoded
            options = orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS
            return orjson.dumps(obj, option=options).decode('utf-8')
        else:
            # Fallback to standard json
            return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False)
    except Exception as e:
        # Handle non-serializable objects gracefully
        return f"[Error: Could not serialize object of type {type(obj).__name__}]\n{obj}"


def stringify_for_diff(val: Any) -> str:
    """
    Creates a stable string representation of a value for diffing or display.
    Ensures that "2.0" and 2 are treated as distinct in *display*
    but handles simple types.

    Args:
        val: The value to stringify.

    Returns:
        A string representation.
    """
    if val is None:
        return "None"
    if isinstance(val, str):
        return f'"{val}"' # Add quotes to distinguish from numbers
    if isinstance(val, (int, float, bool)):
        return str(val)
    
    # For complex types, use compact JSON
    try:
        if ORJSON_AVAILABLE:
            return orjson.dumps(val).decode('utf-8')
        else:
            return json.dumps(val, ensure_ascii=False)
    except Exception:
        return str(val)


def find_line_index(
    text: str, 
    key_regex: str, 
    value_hint: str | None = None
) -> int | None:
    """
    Finds the line number (1-based) in a text block that matches a key
    and optionally a value hint.

    Args:
        text: The multi-line text (e.g., pretty JSON).
        key_regex: A compiled regex object or string to match the key.
                   e.g., r'"my_key"\s*:'
        value_hint: A string representation of the value (e.g., json.dumps(val))
                    to increase match accuracy.

    Returns:
        The 1-based line index, or None if not found.
    """
    if not text or not key_regex:
        return None

    try:
        key_pattern = re.compile(key_regex)
    except re.error as e:
        print(f"Invalid regex in find_line_index: {key_regex} ({e})")
        return None

    lines = text.splitlines()
    best_match_line = None

    for i, line in enumerate(lines):
        if key_pattern.search(line):
            if value_hint:
                # If a value hint is provided, the line *must* contain it
                # We strip a few chars in case of trailing comma/bracket
                line_trimmed = line.strip().rstrip(',').rstrip(']').rstrip('}')
                if value_hint in line_trimmed or value_hint in line:
                    return i + 1  # Found a perfect match
            else:
                # No value hint, first key match is best guess
                if best_match_line is None:
                     best_match_line = i + 1

    # Return first key match if no value-hinted match was found
    return best_match_line