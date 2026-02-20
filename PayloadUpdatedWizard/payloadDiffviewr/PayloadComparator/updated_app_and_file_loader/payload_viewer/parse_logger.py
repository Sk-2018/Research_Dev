import tkinter as tk
from tkinter import ttk, scrolledtext
import datetime

from . import ui_config

class ParseLogger:
    """
    A simple logging window that can be shown/hidden.
    Appends timestamped messages to a Text widget.
    """
    
    def __init__(self, parent: tk.Tk | tk.Toplevel):
        self._parent = parent
        self._window: tk.Toplevel | None = None
        self._text_widget: scrolledtext.ScrolledText | None = None
        self._log_level = "INFO" # Could be configurable

    def _create_window(self) -> None:
        """Creates the Toplevel window if it doesn't exist."""
        if self._window and self._window.winfo_exists():
            self._window.lift()
            return

        self._window = tk.Toplevel(self._parent)
        self._window.title("Parse Log")
        self._window.geometry("700x400")
        
        # Handle window close to just hide, not destroy
        self._window.protocol("WM_DELETE_WINDOW", self.hide)
        
        self._window.grid_rowconfigure(0, weight=1)
        self._window.grid_columnconfigure(0, weight=1)

        self._text_widget = scrolledtext.ScrolledText(
            self._window,
            wrap=tk.WORD,
            font=ui_config.FONT_CODE,
            state="disabled",
            bg=ui_config.COLOR_BG_TEXT_READONLY,
            fg=ui_config.COLOR_FG_TEXT
        )
        self._text_widget.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        btn_frame = ttk.Frame(self._window)
        btn_frame.grid(row=1, column=0, sticky="e", padx=5, pady=(0, 5))
        
        clear_btn = ttk.Button(btn_frame, text="Clear Log", command=self.clear)
        clear_btn.pack(side=tk.LEFT, padx=5)
        
        close_btn = ttk.Button(btn_frame, text="Close", command=self.hide)
        close_btn.pack(side=tk.LEFT)

    def log(self, level: str, message: str) -> None:
        """
        Appends a formatted log message to the text widget.
        
        Args:
            level: Log level (e.g., "INFO", "WARN", "ERROR").
            message: The log message.
        """
        if not self._window or not self._text_widget:
            # Don't create window just for logging, wait for user to show it
            # But we could cache messages here if needed
            return
            
        if not self._window.winfo_exists():
            return # Window was destroyed

        try:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_entry = f"{timestamp} [{level:<5}] {message}\n"
            
            self._text_widget.config(state="normal")
            self._text_widget.insert(tk.END, log_entry)
            
            # Add color tags for levels
            line_index = self._text_widget.index(f"end-{len(log_entry)}c").split('.')[0]
            start_index = f"{line_index}.0"
            end_index = f"{line_index}.end"
            
            if level == "ERROR":
                self._text_widget.tag_configure("ERROR", foreground="red")
                self._text_widget.tag_add("ERROR", start_index, end_index)
            elif level == "WARN":
                self._text_widget.tag_configure("WARN", foreground="#b08000")
                self._text_widget.tag_add("WARN", start_index, end_index)
            
            self._text_widget.config(state="disabled")
            self._text_widget.see(tk.END) # Auto-scroll
        except tk.TclError:
            # Window might be in process of closing
            pass

    def info(self, message: str) -> None:
        self.log("INFO", message)
    
    def warn(self, message: str) -> None:
        self.log("WARN", message)

    def error(self, message: str) -> None:
        self.log("ERROR", message)

    def show(self) -> None:
        """Creates (if needed) and shows the log window."""
        if not self._window or not self._window.winfo_exists():
            self._create_window()
        self._window.deiconify()
        self._window.lift()

    def hide(self) -> None:
        """Hides the log window."""
        if self._window:
            self._window.withdraw()

    def clear(self) -> None:
        """Clears all text from the log window."""
        if self._text_widget:
            self._text_widget.config(state="normal")
            self._text_widget.delete("1.0", tk.END)
            self._text_widget.config(state="disabled")