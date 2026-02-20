from __future__ import annotations
import time
from typing import Any, Dict, List, Optional
import tkinter as tk

class ParseLogger:
    """Lightweight parse logger with a Toplevel viewer."""
    def __init__(self) -> None:
        self.entries: List[Dict[str, Any]] = []
        self._top: Optional[tk.Toplevel] = None  # <-- Track the window

    def log(self, message: str, level: str = 'warning', context: str = '') -> None:
        self.entries.append({
            'timestamp': time.time(),
            'level': level,
            'message': message,
            'context': (context or '')[:400]
        })

    def summary_text(self, limit: int = 200) -> str:
        if not self.entries:
            return "No warnings or errors recorded."
        lines = ["=" * 64, f"Parse Log (last {min(limit, len(self.entries))} of {len(self.entries)})", "=" * 64, ""]
        for e in self.entries[-limit:]:
            ts = time.strftime('%H:%M:%S', time.localtime(e['timestamp']))
            lines.append(f"[{ts}] {e['level'].upper()}: {e['message']}")
            if e['context']:
                lines.append(f"  Context: {e['context']}")
        return "\n".join(lines)

    def show(self, parent: tk.Tk) -> None:
        # If window exists, just raise it
        if self._top and self._top.winfo_exists():
            self._top.lift()
            self._top.focus_set()
            # Refresh content in case new logs were added
            self._update_content()
            return

        # Create new window
        self._top = tk.Toplevel(parent)
        self._top.title("Parse Log")
        self.a_top.geometry("800x500")
        
        # --- Add protocol handler to clear reference on close ---
        self._top.protocol("WM_DELETE_WINDOW", self._on_log_close)
        
        txt = tk.Text(self._top, wrap='word', font=("Courier New", 9), name="log_text")
        txt.pack(fill=tk.BOTH, expand=True)
        txt.insert('1.0', self.summary_text())
        txt.configure(state='disabled')

    def _update_content(self) -> None:
        """Helper to refresh text in an existing window."""
        if not self._top or not self._top.winfo_exists():
            return
        try:
            # Find the Text widget
            txt = self._top.nametowidget("log_text")
            txt.configure(state='normal')
            txt.delete('1.0', tk.END)
            txt.insert('1.0', self.summary_text())
            txt.configure(state='disabled')
        except Exception:
            pass # Widget might not be found

    def _on_log_close(self) -> None:
        """Called when user closes the log window."""
        if self._top:
            self._top.destroy()
            self._top = None
            
    def close(self) -> None:
        """Public method for app.py to force-close the window."""
        if self._top and self._top.winfo_exists():
            self._on_log_close()