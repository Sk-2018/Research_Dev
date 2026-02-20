# -*- coding: utf-8 -*-
"""
SimplePayloadLauncher.py

A simplified tool to test CSV/XLSX file loading with PayloadDiffViewer.
Just select your CSV or XLSX file and click "Launch Viewer" to test the integration.
"""

import os
import sys
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from datetime import datetime

APP_VERSION = "1.0-simple-launcher"
HERE = Path(__file__).resolve().parent

# Viewer candidates to search for
CANDIDATES = [
    "PayloadDiffViewer.exe", "GeminiPayloadDiff.exe",
    "payload_diff_viewer.py", "PayloadDiffViewer.py", 
    "GeminiPayloadDiff.py", "Test103.py"
]

def find_viewer() -> Path | None:
    """Find the PayloadDiffViewer executable or script."""
    # Check environment variable first
    env = os.environ.get("PAYLOADDIFF_VIEWER_PATH", "").strip()
    if env and Path(env).exists():
        return Path(env)

    # Search in the same directory as this script
    for name in CANDIDATES:
        p = HERE / name
        if p.exists():
            return p

    return None

def launch_viewer(file_path: Path, log_callback) -> bool:
    """Launch the PayloadDiffViewer with the specified file."""
    viewer = find_viewer()

    if not viewer:
        # Fallback: try to open with default application
        try:
            if os.name == "nt":  # Windows
                os.startfile(str(file_path))
                log_callback(f"✅ Viewer not found. Opened {file_path.name} with default application.")
                return True
            else:  # macOS/Linux
                subprocess.Popen(["xdg-open", str(file_path)])
                log_callback(f"✅ Viewer not found. Opened {file_path.name} with default application.")
                return True
        except Exception as e:
            log_callback(f"❌ Fallback open failed: {e}")
            messagebox.showerror(
                "Viewer Not Found",
                f"PayloadDiffViewer not found. Place one of these files next to this script:\n\n" +
                "\n".join(CANDIDATES) +
                "\n\nOr set PAYLOADDIFF_VIEWER_PATH environment variable."
            )
            return False

    log_callback(f"Found viewer: {viewer.name}")

    # Determine if it's a Python script or executable
    is_py = viewer.suffix.lower() == ".py"
    base = [sys.executable, str(viewer)] if is_py else [str(viewer)]

    # Try different command-line argument variations
    variants = [
        base + ["--open", str(file_path)],
        base + ["-o", str(file_path)],
        base + ["--file", str(file_path)],
        base + ["-f", str(file_path)],
        base + [str(file_path)],
    ]

    for args in variants:
        try:
            subprocess.Popen(args)
            log_callback(f"✅ Launched viewer with: {' '.join(args)}")
            return True
        except Exception as e:
            log_callback(f"⚠️  Attempt failed: {' '.join(args)} :: {e}")

    log_callback("❌ All launch attempts failed.")
    messagebox.showerror("Launch Failed", "Could not launch PayloadDiffViewer with any known arguments.")
    return False


class SimpleLauncherApp(tk.Tk):
    """Simple GUI for testing PayloadDiffViewer integration."""

    def __init__(self):
        super().__init__()
        self.title(f"Simple Payload Launcher {APP_VERSION}")
        self.geometry("800x500")
        self.selected_file = None

        # Main container
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title = ttk.Label(
            main_frame, 
            text="Simple Payload Comparison Launcher",
            font=("Arial", 16, "bold")
        )
        title.pack(pady=(0, 20))

        # Instructions
        instructions = ttk.Label(
            main_frame,
            text="Select a CSV or XLSX file to test with PayloadDiffViewer:",
            font=("Arial", 10)
        )
        instructions.pack(pady=(0, 10))

        # File selection section
        file_frame = ttk.Frame(main_frame)
        file_frame.pack(fill=tk.X, pady=10)

        ttk.Label(file_frame, text="Selected File:").pack(side=tk.LEFT, padx=(0, 10))

        self.file_entry = ttk.Entry(file_frame, width=60)
        self.file_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

        ttk.Button(file_frame, text="Browse...", command=self.browse_file).pack(side=tk.LEFT)

        # Viewer info
        viewer_frame = ttk.LabelFrame(main_frame, text="Viewer Information", padding="10")
        viewer_frame.pack(fill=tk.X, pady=20)

        viewer_path = find_viewer()
        if viewer_path:
            status_text = f"✅ Found: {viewer_path.name}"
            status_color = "green"
        else:
            status_text = "⚠️  PayloadDiffViewer not found (will use default app)"
            status_color = "orange"

        self.viewer_label = ttk.Label(
            viewer_frame, 
            text=status_text,
            foreground=status_color,
            font=("Arial", 10, "bold")
        )
        self.viewer_label.pack()

        location_text = f"Search location: {HERE}" if not viewer_path else f"Full path: {viewer_path}"
        ttk.Label(viewer_frame, text=location_text, foreground="gray").pack()

        # Launch button
        self.launch_btn = ttk.Button(
            main_frame,
            text="🚀 Launch Viewer",
            command=self.launch_viewer,
            state=tk.DISABLED
        )
        self.launch_btn.pack(pady=20)

        # Log area
        log_frame = ttk.LabelFrame(main_frame, text="Launch Log", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = tk.Text(log_frame, height=10, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # Initial log
        self.log(f"Simple Payload Launcher v{APP_VERSION} started")
        self.log(f"Looking for viewer in: {HERE}")
        if viewer_path:
            self.log(f"✅ Viewer detected: {viewer_path.name}")
        else:
            self.log("⚠️  No viewer found - will use default application")

    def browse_file(self):
        """Open file browser to select CSV or XLSX file."""
        file_path = filedialog.askopenfilename(
            title="Select CSV or XLSX file",
            filetypes=[
                ("Data files", "*.csv *.xlsx"),
                ("CSV files", "*.csv"),
                ("Excel files", "*.xlsx"),
                ("All files", "*.*")
            ]
        )

        if file_path:
            self.selected_file = Path(file_path)
            self.file_entry.delete(0, tk.END)
            self.file_entry.insert(0, str(self.selected_file))
            self.launch_btn.configure(state=tk.NORMAL)
            self.log(f"Selected file: {self.selected_file.name}")

    def launch_viewer(self):
        """Launch PayloadDiffViewer with the selected file."""
        if not self.selected_file:
            messagebox.showwarning("No File", "Please select a CSV or XLSX file first.")
            return

        if not self.selected_file.exists():
            messagebox.showerror("File Not Found", f"The selected file does not exist:\n{self.selected_file}")
            self.log(f"❌ File not found: {self.selected_file}")
            return

        self.log(f"Launching viewer with: {self.selected_file.name}")
        success = launch_viewer(self.selected_file, self.log)

        if success:
            messagebox.showinfo(
                "Success", 
                f"PayloadDiffViewer launched successfully!\n\nFile: {self.selected_file.name}"
            )

    def log(self, message: str):
        """Add a message to the log area."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)


if __name__ == "__main__":
    app = SimpleLauncherApp()
    app.mainloop()
