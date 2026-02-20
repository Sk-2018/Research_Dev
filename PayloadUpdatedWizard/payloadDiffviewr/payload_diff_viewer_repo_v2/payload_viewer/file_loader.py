
"""File loader with delimiter sniffing, chunked CSV, and Excel support."""
from __future__ import annotations
import csv, os
from typing import Any, Callable
from .parse_logger import ParseLogger
try:
    import pandas as pd
except Exception:
    pd = None  # type: ignore

ProgressCB = Callable[[float, str], None]

class FileLoader:
    def __init__(self, parse_logger: ParseLogger) -> None:
        self.log = parse_logger

    def validate_file(self, path: str) -> tuple[bool, str]:
        if not os.path.exists(path):
            return False, "File not found"
        if os.path.isdir(path):
            return False, "Path is a directory"
        return True, ""

    def sniff_delimiter(self, path: str) -> str:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            sample = f.read(4096)
        try:
            dialect = csv.Sniffer().sniff(sample)
            return dialect.delimiter  # type: ignore[return-value]
        except Exception:
            return ","

    def _emit(self, cb: ProgressCB | None, pct: float, msg: str) -> None:
        if cb:
            cb(pct, msg)
        self.log.log(msg)

    def load_any(self, path: str, progress_cb: ProgressCB | None = None) -> tuple[list[str], list[list[Any]]]:
        ext = os.path.splitext(path)[1].lower()
        if ext in {".csv", ".tsv", ".txt"}:
            return self.load_csv(path, progress_cb)
        if ext == ".xlsx":
            return self.load_excel(path, None, progress_cb)
        if ext == ".xls":
            raise RuntimeError(".xls not supported—please save as .xlsx and retry.")
        raise RuntimeError(f"Unsupported file type: {ext}")

    def _to_df_from_rows(self, headers: list[str], rows: list[list[Any]]):
        if pd is None:
            return None
        try:
            return pd.DataFrame(rows, columns=headers)
        except Exception:
            return None

    def load_csv(self, path: str, progress_cb: ProgressCB | None = None) -> tuple[list[str], list[list[Any]]]:
        delim = self.sniff_delimiter(path)
        self._emit(progress_cb, 0.01, f"Detected delimiter: {repr(delim)}")
        rows: list[list[Any]] = []
        headers: list[str] | None = None
        total = os.path.getsize(path) or 1
        read_bytes = 0
        with open(path, "r", encoding="utf-8", errors="ignore", newline="") as f:
            reader = csv.reader(f, delimiter=delim)
            for i, row in enumerate(reader):
                if headers is None:
                    headers = [h.strip() for h in row]
                    continue
                rows.append(row)
                read_bytes += sum(len(c) for c in row) + len(row)
                if i % 5000 == 0:
                    self._emit(progress_cb, min(read_bytes / total, 0.99), f"Rows read: {i}")
        self._emit(progress_cb, 1.0, f"Completed. Rows read: {len(rows)}")
        return headers or [], rows

    def load_excel(self, path: str, sheet: str | None = None, progress_cb: ProgressCB | None = None
                   ) -> tuple[list[str], list[list[Any]]]:
        self._emit(progress_cb, 0.01, "Opening workbook…")
        if pd is None:
            raise RuntimeError("pandas is required for Excel loading. Please install pandas and openpyxl.")
        try:
            xls = pd.ExcelFile(path)
            sheet_name = sheet or xls.sheet_names[0]
            self._emit(progress_cb, 0.05, f"Reading sheet: {sheet_name}…")
            df = xls.parse(sheet_name=sheet_name)
            headers = [str(c) for c in df.columns.tolist()]
            rows = df.values.tolist()
            self._emit(progress_cb, 1.0, f"Completed. Rows read: {len(rows)}")
            return headers, rows
        except Exception as exc:
            raise RuntimeError(f"Failed to read Excel: {exc}")

    def detect_best_columns(self, df: "pd.DataFrame") -> dict[str, str | None]:
        import re
        def valid(name: str) -> bool:
            return bool(re.fullmatch(r"[A-Za-z_]+", name))

        name_candidates = [c for c in df.columns if valid(str(c))]
        def pick(*keys: str) -> str | None:
            lower = {str(c).lower(): str(c) for c in name_candidates}
            for k in keys:
                if k.lower() in lower:
                    return lower[k.lower()]
            return None

        config_name_col = pick("Config_Name", "ConfigName", "Name", "Config")
        config_key_col = pick("Config_Key", "ConfigKey", "Key", "CfgKey")
        payload_old = pick("Old", "Payload_Old", "Prev", "Previous")
        payload_current = pick("New", "Payload_New", "Current")

        return {
            "config_name_col": config_name_col,
            "config_key_col": config_key_col,
            "payload_old": payload_old,
            "payload_current": payload_current,
        }
