from typing import Any
from deepdiff import DeepDiff
import decimal

# Helper to check if a string can be numeric
def is_numeric_string(s: Any) -> bool:
    """Check if a string represents an integer or float."""
    if not isinstance(s, str):
        return False
    if s.isdigit(): # Fast path for integers
        return True
    try:
        float(s)
        return True
    except (ValueError, TypeError):
        return False

def normalize_for_diff(x: Any, *, coerce_numeric: bool = True) -> Any:
    """
    Recursively normalizes an object for comparison.
    If coerce_numeric is True, converts numeric-like strings to numbers.
    
    Args:
        x: The object (dict, list, value) to normalize.
        coerce_numeric: Flag to enable numeric string coercion.

    Returns:
        A new object with normalized values.
    """
    if isinstance(x, dict):
        return {
            k: normalize_for_diff(v, coerce_numeric=coerce_numeric)
            for k, v in x.items()
        }
    if isinstance(x, list):
        return [
            normalize_for_diff(v, coerce_numeric=coerce_numeric)
            for v in x
        ]
    
    if coerce_numeric and is_numeric_string(x):
        try:
            # Use Decimal for precision, avoids 975 vs 975.0 issues
            return decimal.Decimal(x)
        except (decimal.InvalidOperation, TypeError):
            return x # Not numeric after all
            
    if isinstance(x, (int, float)):
        return decimal.Decimal(x)

    return x

def run_deepdiff(old: Any, new: Any, *, ignore_order: bool, coerce_numeric: bool = True) -> dict:
    """
    Runs DeepDiff comparison with optional numeric coercion.

    Args:
        old: The "old" Python object (parsed from JSON).
        new: The "new" Python object (parsed from JSON).
        ignore_order: Whether to treat lists as sets for comparison.
        coerce_numeric: Whether to treat "975" and 975 as identical.

    Returns:
        The raw DeepDiff result dictionary.
    """
    
    old_normalized = old
    new_normalized = new

    if coerce_numeric:
        # Apply normalization *before* diffing.
        # This makes "975" and 975.0 both become Decimal('975')
        # so DeepDiff sees them as identical.
        old_normalized = normalize_for_diff(old, coerce_numeric=True)
        new_normalized = normalize_for_diff(new, coerce_numeric=True)

    # Note: DeepDiff's 'number_to_string_func' is for the *other* way
    # (treating numbers as strings). We want string-to-number, so
    # pre-processing is the most reliable way.
    
    # We also set ignore_numeric_type_changes=True just in case
    # our Decimal conversion isn't perfect (e.g., int vs Decimal)
    diff = DeepDiff(
        old_normalized,
        new_normalized,
        ignore_order=ignore_order,
        verbose_level=2,
        view='tree',
        ignore_numeric_type_changes=coerce_numeric,
        # We don't need 'significant_digits', as we use Decimal
    )
    
    # Return the diff as a standard dictionary
    return diff.to_dict()