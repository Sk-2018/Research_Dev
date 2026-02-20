"""
File Loader - Robust CSV/TSV/Excel loading with progress callbacks and column detection.
"""

import os
import re
import csv
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

try:
    import openpyxl
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False

from .parse_logger import ParseLogger


class FileLoader:
    """Handles loading and validation of CSV/TSV/Excel files."""

    VALID_EXTENSIONS = {".csv", ".tsv", ".txt", ".xlsx", ".xls"}
    CHUNK_SIZE = 10000  # Rows per chunk for progress updates

    def __init__(self, parse_logger: ParseLogger) -> None:
        """
        Initialize file loader.

        Args:
            parse_logger: ParseLogger instance for logging
        """
        self.logger = parse_logger

    def validate_file(self, path: str) -> Tuple[bool, str]:
        """
        Validate file exists and has supported extension.

        Args:
            path: File path

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not os.path.isfile(path):
            return False, "File does not exist"
        
        ext = Path(path).suffix.lower()
        if ext not in self.VALID_EXTENSIONS:
            return False, f"Unsupported file type: {ext}"
        
        return True, ""

    def sniff_delimiter(self, path: str, sample_lines: int = 5) -> str:
        """
        Auto-detect delimiter for text files.

        Args:
            path: File path
            sample_lines: Number of lines to sample

        Returns:
            Detected delimiter (default: ',')
        """
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                sample = "".join([f.readline() for _ in range(sample_lines)])
            
            sniffer = csv.Sniffer()
            dialect = sniffer.sniff(sample, delimiters=",\t|;")
            self.logger.log(f"Detected delimiter: '{dialect.delimiter}'")
            return dialect.delimiter
        
        except Exception as e:
            self.logger.log(f"Could not sniff delimiter: {e}. Using ','")
            return ","

    def load_any(
        self,
        path: str,
        progress_cb: Optional[Callable[[float, str], None]] = None,
    ) -> Tuple[List[str], List[List[Any]]]:
        """
        Load any supported file type.

        Args:
            path: File path
            progress_cb: Optional callback(progress_fraction, status_message)

        Returns:
            Tuple of (headers, rows)
        """
        ext = Path(path).suffix.lower()
        
        if ext in {".csv", ".tsv", ".txt"}:
            return self.load_csv(path, progress_cb)
        elif ext in {".xlsx", ".xls"}:
            return self.load_excel(path, progress_cb=progress_cb)
        else:
            raise ValueError(f"Unsupported file extension: {ext}")

    def load_csv(
        self,
        path: str,
        progress_cb: Optional[Callable[[float, str], None]] = None,
    ) -> Tuple[List[str], List[List[Any]]]:
        """
        Load CSV/TSV/TXT file with chunked reading.

        Args:
            path: File path
            progress_cb: Optional callback(progress_fraction, status_message)

        Returns:
            Tuple of (headers, rows)
        """
        self.logger.log(f"Loading CSV: {path}")
        
        delimiter = self.sniff_delimiter(path)
        
        headers: List[str] = []
        rows: List[List[Any]] = []
        
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                reader = csv.reader(f, delimiter=delimiter)
                
                # Read header
                headers = next(reader, [])
                self.logger.log(f"Headers: {headers}")
                
                # Read rows in chunks
                row_count = 0
                for row in reader:
                    rows.append(row)
                    row_count += 1
                    
                    if progress_cb and row_count % self.CHUNK_SIZE == 0:
                        progress_cb(0.5, f"Rows read: {row_count}")
            
            self.logger.log(f"Loaded {len(rows)} rows")
            
            if progress_cb:
                progress_cb(1.0, f"Complete: {len(rows)} rows")
            
            return headers, rows
        
        except Exception as e:
            self.logger.log(f"Error loading CSV: {e}")
            raise

    def load_excel(
        self,
        path: str,
        sheet: Optional[str] = None,
        progress_cb: Optional[Callable[[float, str], None]] = None,
    ) -> Tuple[List[str], List[List[Any]]]:
        """
        Load Excel file.

        Args:
            path: File path
            sheet: Sheet name (None = first sheet)
            progress_cb: Optional callback(progress_fraction, status_message)

        Returns:
            Tuple of (headers, rows)
        """
        if not PANDAS_AVAILABLE:
            raise ImportError("pandas required for Excel files")
        
        if not OPENPYXL_AVAILABLE:
            raise ImportError("openpyxl required for Excel files")
        
        self.logger.log(f"Loading Excel: {path}")
        
        if progress_cb:
            progress_cb(0.1, "Opening workbook...")
        
        try:
            # Read with pandas
            df = pd.read_excel(path, sheet_name=sheet or 0, engine="openpyxl")
            
            if progress_cb:
                progress_cb(0.5, f"Reading sheet... {len(df)} rows")
            
            headers = df.columns.tolist()
            rows = df.values.tolist()
            
            self.logger.log(f"Loaded {len(rows)} rows from Excel")
            
            if progress_cb:
                progress_cb(1.0, f"Complete: {len(rows)} rows")
            
            return headers, rows
        
        except Exception as e:
            self.logger.log(f"Error loading Excel: {e}")
            raise

    def detect_best_columns(self, df: "pd.DataFrame") -> Dict[str, str]:
        """
        Detect Config Name, Config Key, and payload columns.

        Only accepts column names matching ^[A-Za-z_]+$ (alphabetic with underscore).

        Args:
            df: pandas DataFrame

        Returns:
            Dict with keys: config_name_col, config_key_col, old_col, new_col
        """
        if not PANDAS_AVAILABLE:
            raise ImportError("pandas required for column detection")
        
        # Regex for valid column names (alphabetic + underscore)
        valid_pattern = re.compile(r"^[A-Za-z_]+$")
        
        valid_cols = [col for col in df.columns if valid_pattern.match(str(col))]
        
        self.logger.log(f"Valid columns: {valid_cols}")
        
        result: Dict[str, str] = {
            "config_name_col": "",
            "config_key_col": "",
            "old_col": "",
            "new_col": "",
        }
        
        # Detect Config Name
        for col in valid_cols:
            if "config" in col.lower() and "name" in col.lower():
                result["config_name_col"] = col
                break
        
        # Detect Config Key
        for col in valid_cols:
            if "config" in col.lower() and "key" in col.lower():
                result["config_key_col"] = col
                break
        
        # Detect Old/Current payload columns
        for col in valid_cols:
            col_lower = col.lower()
            if "old" in col_lower or "previous" in col_lower:
                result["old_col"] = col
            elif "new" in col_lower or "current" in col_lower:
                result["new_col"] = col
        
        self.logger.log(f"Detected columns: {result}")
        
        return result
