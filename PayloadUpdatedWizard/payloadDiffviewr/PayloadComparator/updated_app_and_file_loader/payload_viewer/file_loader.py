import csv
import os
import re
from typing import Any, Callable, List, Tuple, Optional, Dict

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    print("Warning: pandas not found. File loading will be limited.")

try:
    import openpyxl
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False
    print("Warning: openpyxl not found. Excel file (.xlsx) support disabled.")

from .parse_logger import ParseLogger

# Regex to find valid config/key column names
COLUMN_NAME_REGEX = re.compile(r"^[A-Za-z_]+$")

class FileLoader:
    """
    Handles loading data from CSV, TSV, TXT, and Excel files.
    """

    def __init__(self, parse_logger: ParseLogger) -> None:
        """
        Initializes the FileLoader.

        Args:
            parse_logger: Logger instance for reporting warnings/errors.
        """
        self.parse_logger = parse_logger
        if not PANDAS_AVAILABLE:
            self.parse_logger.error(
                "pandas library not found. "
                "File loading and summary features will not work."
            )

    def validate_file(self, path: str) -> Tuple[bool, str]:
        """
        Performs a quick check on a file path.

        Args:
            path: The file path.

        Returns:
            A tuple (is_valid, message).
        """
        if not os.path.exists(path):
            return False, "File not found."
        if not os.path.isfile(path):
            return False, "Path is a directory, not a file."
        
        ext = os.path.splitext(path)[1].lower()
        if ext not in ['.csv', '.tsv', '.txt', '.xlsx', '.xls']:
            return False, f"Unsupported file extension: {ext}"
            
        if ext in ['.xlsx', '.xls'] and not OPENPYXL_AVAILABLE:
            return False, "Excel file detected, but 'openpyxl' library is not installed."
            
        return True, "File appears valid."

    def load_any(
        self, 
        path: str, 
        progress_cb: Callable[[float, str], None] | None = None
    ) -> Tuple[List[str], List[List[Any]]]:
        """
        Loads data from any supported file type, dispatching to the
        correct loader.

        Args:
            path: The file path.
            progress_cb: Optional callback for progress updates.
                         Receives (percent_complete, status_message).
                         percent_complete=None means indeterminate.

        Returns:
            A tuple (headers: list[str], rows: list[list[Any]]).
        """
        if not PANDAS_AVAILABLE:
            raise ImportError("pandas is required to load files.")

        ext = os.path.splitext(path)[1].lower()
        
        try:
            if ext in ['.csv', '.tsv', '.txt']:
                return self.load_csv(path, progress_cb)
            elif ext in ['.xlsx', '.xls']:
                if not OPENPYXL_AVAILABLE:
                    raise ImportError("openpyxl is required to load Excel files.")
                # Note: pandas uses openpyxl or xlrd internally
                # Using pandas is much simpler for .xls and .xlsx
                return self.load_excel_with_pandas(path, progress_cb)
            else:
                raise ValueError(f"Unsupported file type: {ext}")
        except Exception as e:
            self.parse_logger.error(f"Failed to load file {path}: {e}")
            raise

    def sniff_delimiter(self, path: str) -> str:
        """
        Sniffs the delimiter for a text file.

        Args:
            path: Path to the text file.

        Returns:
            The detected delimiter (e.g., ',', '\t').
        """
        try:
            with open(path, 'r', encoding='utf-8-sig') as f:
                # Read a sample of the file
                sample = f.read(2048)
                sniffer = csv.Sniffer()
                dialect = sniffer.sniff(sample, delimiters=',\t;|')
                self.parse_logger.info(f"Sniffed delimiter '{dialect.delimiter}' for {path}")
                return dialect.delimiter
        except Exception as e:
            self.parse_logger.warn(f"Could not sniff delimiter for {path}, defaulting to ',': {e}")
            return ','

    def load_csv(
        self, 
        path: str, 
        progress_cb: Callable[[float, str], None] | None = None
    ) -> Tuple[List[str], List[List[Any]]]:
        """
        Loads a CSV/TSV/TXT file using pandas chunking for progress.

        Args:
            path: The file path.
            progress_cb: Progress callback.

        Returns:
            (headers, rows)
        """
        delimiter = self.sniff_delimiter(path)
        
        if progress_cb:
            progress_cb(0, "Counting rows...")
        
        # Get total rows for progress bar (approximate)
        try:
            with open(path, 'r', encoding='utf-8-sig') as f:
                total_rows = sum(1 for row in f) - 1 # -1 for header
        except Exception:
            total_rows = -1 # Indeterminate
            
        if progress_cb:
            progress_cb(0, "Reading chunks...")

        chunks = []
        rows_read = 0
        chunk_size = 5000
        
        try:
            for chunk in pd.read_csv(
                path, 
                sep=delimiter, 
                encoding='utf-8-sig', 
                chunksize=chunk_size,
                keep_default_na=False, # Keep empty strings as "" not NaN
                dtype=str # Read all as string to preserve payload fidelity
            ):
                chunks.append(chunk)
                rows_read += len(chunk)
                if progress_cb and total_rows > 0:
                    progress = min(100.0, (rows_read / total_rows) * 100)
                    progress_cb(progress, f"Rows read: {rows_read} / ~{total_rows}")
                elif progress_cb:
                    progress_cb(None, f"Rows read: {rows_read}") # Indeterminate
        
        except pd.errors.EmptyDataError:
            self.parse_logger.warn(f"File is empty: {path}")
            return [], []
        except Exception as e:
            self.parse_logger.error(f"Error reading CSV {path}: {e}")
            raise

        if not chunks:
            return [], []

        df = pd.concat(chunks, ignore_index=True)
        # Convert to native types for faster processing, but keep NaN as None
        df = df.where(pd.notna(df), None)

        if progress_cb:
            progress_cb(100, "Processing complete.")
            
        headers = df.columns.tolist()
        rows = df.values.tolist()
        return headers, rows

    def load_excel_with_pandas(
        self, 
        path: str, 
        progress_cb: Callable[[float, str], None] | None = None
    ) -> Tuple[List[str], List[List[Any]]]:
        """
        Loads an Excel file using pandas. Progress is less granular.

        Args:
            path: The file path.
            sheet: Optional sheet name. Defaults to first sheet.
            progress_cb: Progress callback.

        Returns:
            (headers, rows)
        """
        if progress_cb:
            progress_cb(None, "Opening workbook...") # Indeterminate

        try:
            # engine='openpyxl' is default for .xlsx
            # pandas handles .xls via xlrd (if installed) or openpyxl
            df = pd.read_excel(
                path, 
                sheet_name=0, # Load first sheet
                keep_default_na=False, # Keep empty strings as "" not NaN
                dtype=str # Read all as string
            )
        except Exception as e:
            self.parse_logger.error(f"Error reading Excel file {path}: {e}")
            raise
            
        if progress_cb:
            progress_cb(None, "Converting data...")
            
        # Convert to native types, NaN -> None
        df = df.where(pd.notna(df), None)

        headers = df.columns.tolist()
        rows = df.values.tolist()
        
        if progress_cb:
            progress_cb(100, "Processing complete.")
            
        return headers, rows

    def detect_best_columns(self, df: "pd.DataFrame") -> Dict[str, str]:
        """
        Analyzes DataFrame columns to find the best candidates for
        Config Name, Config Key, and payload columns.

        Args:
            df: The loaded pandas DataFrame.

        Returns:
            A dictionary with keys 'config_name_col', 'config_key_col',
            'old_payload_col', 'new_payload_col'. Values are None if
            not found.
        """
        if not PANDAS_AVAILABLE:
            return {}
            
        cols = df.columns
        
        # 1. Filter for valid *config/key* column names
        # We only want simple identifiers, not "Payload_1_JSON"
        valid_key_cols = [
            c for c in cols 
            if isinstance(c, str) and COLUMN_NAME_REGEX.match(c)
        ]
        
        # 2. Filter for valid *payload* columns
        # These can be more complex, often containing "payload", "json", "current", "old"
        valid_payload_cols = [
            c for c in cols
            if isinstance(c, str) and ("payload" in c.lower() or "json" in c.lower() or "config" in c.lower())
        ]
        if not valid_payload_cols:
             # Fallback: all string columns are potential payloads
             valid_payload_cols = [c for c in cols if isinstance(c, str)]


        result = {
            "config_name_col": None,
            "config_key_col": None,
            "old_payload_col": None,
            "new_payload_col": None,
        }

        # --- Find Config Name and Key ---
        # Strategy: Look for "Config Name" and "Config Key" or close matches
        
        # Find Config Name
        for c in valid_key_cols:
            c_lower = c.lower()
            if "config" in c_lower and "name" in c_lower:
                result["config_name_col"] = c
                break
        if not result["config_name_col"]:
            # Fallback
            for c in valid_key_cols:
                if c.lower() in ("config", "configname", "cfg_name"):
                    result["config_name_col"] = c
                    break

        # Find Config Key
        for c in valid_key_cols:
            c_lower = c.lower()
            if c == result["config_name_col"]: # Don't reuse
                continue
            if "config" in c_lower and "key" in c_lower:
                result["config_key_col"] = c
                break
        if not result["config_key_col"]:
            # Fallback
            for c in valid_key_cols:
                if c == result["config_name_col"]: continue
                if c.lower() in ("key", "configkey", "cfg_key", "id"):
                    result["config_key_col"] = c
                    break

        # --- Find Payload Columns ---
        # Strategy: Look for "old"/"current" or "left"/"right"
        old_found, new_found = False, False
        for c in valid_payload_cols:
            c_lower = c.lower()
            if not old_found and ("old" in c_lower or "left" in c_lower or "previous" in c_lower):
                result["old_payload_col"] = c
                old_found = True
            elif not new_found and ("new" in c_lower or "current" in c_lower or "right" in c_lower):
                result["new_payload_col"] = c
                new_found = True
            if old_found and new_found:
                break
        
        # Fallback: If only one payload column found, use it for both?
        # No, that's bad. Let's try to find two payload columns
        if not old_found or not new_found:
            # Get first two payload-like columns that aren't key/name
            payload_candidates = [
                c for c in valid_payload_cols
                if c not in (result["config_name_col"], result["config_key_col"])
            ]
            if len(payload_candidates) >= 2:
                if not old_found:
                    result["old_payload_col"] = payload_candidates[0]
                if not new_found:
                    # Use the *next* candidate
                    if old_found and payload_candidates[0] == result["old_payload_col"]:
                         if len(payload_candidates) > 1:
                            result["new_payload_col"] = payload_candidates[1]
                    else:
                        result["new_payload_col"] = payload_candidates[0] if not old_found else payload_candidates[1]

        self.parse_logger.info(f"Auto-detected columns: {result}")
        return result