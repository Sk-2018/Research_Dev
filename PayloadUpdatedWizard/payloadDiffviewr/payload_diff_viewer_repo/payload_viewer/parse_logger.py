
"""Parse logger with in-memory buffer and Tk viewer."""
from __future__ import annotations

import datetime as _dt
import threading
from tkinter import Toplevel, Text, BOTH, END
from tkinter import ttk


class ParseLogger:
    def __init__(self) -> None:
        self._lines: list[str] = []
        self._lock = threading.Lock()

    def log(self, msg: str) -> None:
        ts = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] {msg}"
        with self._lock:
            self._lines.append(line)

    def dump(self) -> str:
        with self._lock:
            return "\n".join(self._lines)

    # Tk viewer
    def show_viewer(self, master) -> None:
        win = Toplevel(master)
        win.title("Parse Log")
        win.geometry("900x500")
        txt = Text(win, wrap="word")
        txt.pack(fill=BOTH, expand=True)
        txt.insert(END, self.dump())
        txt.configure(state="disabled")
        ttk.Button(win, text="Close", command=win.destroy).pack(pady=6)
