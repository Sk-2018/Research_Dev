from __future__ import annotations

import time
from typing import Any, Dict, List

import tkinter as tk

class ParseLogger:
    """Lightweight parse logger with a Toplevel viewer."""

    def __init__(self) -> None:
        self.entries: List[Dict[str, Any]] = []

    def log(self, message: str, level: str = "warning", context: str = "") -> None:
        self.entries.append(
            {
                "timestamp": time.time(),
                "level": level,
                "message": message,
                "context": (context or "")[:200],
            }
        )

    def summary_text(self, limit: int = 200) -> str:
        if not self.entries:
            return "No warnings or errors recorded."
        lines = [
            "=" * 64,
            f"Parse Log (last {min(limit, len(self.entries))} of {len(self.entries)})",
            "=" * 64,
            "",
        ]
        for e in self.entries[-limit:]:
            ts = time.strftime("%H:%M:%S", time.localtime(e["timestamp"]))
            lines.append(f"[{ts}] {e['level'].upper()}: {e['message']}")
            if e["context"]:
                lines.append(f"  Context: {e['context']}")
        return "\n".join(lines)

    def show(self, parent: tk.Tk) -> None:
        top = tk.Toplevel(parent)
        top.title("Parse Log")
        top.geometry("800x500")
        txt = tk.Text(top, wrap="word", font=("Courier New", 9))
        txt.pack(fill=tk.BOTH, expand=True)
        txt.insert("1.0", self.summary_text())
        txt.configure(state="disabled")
