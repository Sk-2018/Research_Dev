
# Create the enhanced launcher with test data generation capability
enhanced_launcher = '''# -*- coding: utf-8 -*-
"""
EnhancedPayloadLauncher.py

Enhanced tool to test PayloadDiffViewer with properly formatted CSV/XLSX files.
Features:
- Generate sample payload comparison data
- Test with your own CSV/XLSX files
- Auto-detects and launches PayloadDiffViewer
"""

import os
import sys
import csv
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from datetime import datetime
import json

APP_VERSION = "1.1-enhanced-launcher"
HERE = Path(__file__).resolve().parent

# Viewer candidates to search for
CANDIDATES = [
    "PayloadDiffViewer.exe", "GeminiPayloadDiff.exe",
    "payload_diff_viewer.py", "PayloadDiffViewer.py", 
    "GeminiPayloadDiff.py", "Test103.py"
]

def generate_sample_data(output_path: Path, num_rows: int = 10) -> Path:
    """Generate a sample CSV file with proper payload comparison format."""
    # Sample JSON payloads for testing
    sample_configs = [
        {
            "name": "acq_profl",
            "key": "VISA_CREDIT_US",
            "current": {
                "merchantId": "123456",
                "terminalId": "T001",
                "currency": "USD",
                "timeout": 30,
                "enableRetry": True,
                "retryCount": 3
            },
            "old": {
                "merchantId": "123456",
                "terminalId": "T001",
                "currency": "USD",
                "timeout": 20,
                "enableRetry": True,
                "retryCount": 2
            }
        },
        {
            "name": "acq_profl",
            "key": "MC_DEBIT_EU",
            "current": {
                "processingCode": "003000",
                "networkId": "MC001",
                "routingPriority": "PRIMARY",
                "encryptionType": "AES256"
            },
            "old": {
                "processingCode": "003000",
                "networkId": "MC001",
                "routingPriority": "SECONDARY",
                "encryptionType": "AES128"
            }
        },
        {
            "name": "scheme_config",
            "key": "AMEX_GLOBAL",
            "current": {
                "schemeId": "AMEX",
                "region": "GLOBAL",
                "settlementCurrency": "USD",
                "feeStructure": {
                    "interchangeFee": 2.5,
                    "assessmentFee": 0.15
                }
            },
            "old": {
                "schemeId": "AMEX",
                "region": "GLOBAL",
                "settlementCurrency": "USD",
                "feeStructure": {
                    "interchangeFee": 2.3,
                    "assessmentFee": 0.15
                }
            }
        },
        {
            "name": "routing_rule",
            "key": "DOMESTIC_PRIORITY",
            "current": {
                "ruleId": "R101",
                "priority": 1,
                "conditions": ["amount<1000", "domestic=true"],
                "targetProcessor": "PROCESSOR_A"
            },
            "old": {
                "ruleId": "R101",
                "priority": 2,
                "conditions": ["amount<500", "domestic=true"],
                "targetProcessor": "PROCESSOR_B"
            }
        },
        {
            "name": "fraud_config",
            "key": "HIGH_RISK_MONITORING",
            "current": {
                "enabled": True,
                "thresholds": {
                    "velocityCheck": 5,
                    "amountLimit": 5000,
                    "geoBlocking": ["CN", "RU"]
                },
                "actions": ["DECLINE", "ALERT"]
            },
            "old": {
                "enabled": True,
                "thresholds": {
                    "velocityCheck": 3,
                    "amountLimit": 3000,
                    "geoBlocking": ["CN"]
                },
                "actions": ["ALERT"]
            }
        }
    ]
    
    # Generate test data
    rows = []
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    for i in range(num_rows):
        config = sample_configs[i % len(sample_configs)]
        row = {
            "Config Name": config["name"],
            "Config Key": f"{config['key']}_{i+1:03d}",
            "CURRENT PAYLOAD": json.dumps(config["current"], indent=2),
            "OLD PAYLOAD": json.dumps(config["old"], indent=2),
            "config_eff_ts": timestamp,
            "param_exp_ts": "2099-12-31 23:59:59",
            "rec_sts": "ACTIVE"
        }
        rows.append(row)
    
    # Write CSV
    fieldnames = ["Config Name", "Config Key", "CURRENT PAYLOAD", "OLD PAYLOAD", 
                  "config_eff_ts", "param_exp_ts", "rec_sts"]
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    return output_path


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
        log_callback("❌ No PayloadDiffViewer found")
        messagebox.showerror(
            "Viewer Not Found",
            f"PayloadDiffViewer not found. Place one of these files next to this script:\\n\\n" +
            "\\n".join(CANDIDATES) +
            "\\n\\nOr set PAYLOADDIFF_VIEWER_PATH environment variable."
        )
        return False
    
    log_callback(f"✅ Found viewer: {viewer.name}")
    
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
            log_callback(f"✅ Launched with: {' '.join([os.path.basename(a) for a in args[:2]])} {os.path.basename(str(file_path))}")
            return True
        except Exception as e:
            log_callback(f"⚠️  Attempt failed: {e}")
    
    log_callback("❌ All launch attempts failed")
    messagebox.showerror("Launch Failed", "Could not launch PayloadDiffViewer with any known arguments.")
    return False


class EnhancedLauncherApp(tk.Tk):
    """Enhanced GUI for testing PayloadDiffViewer integration."""
    
    def __init__(self):
        super().__init__()
        self.title(f"Enhanced Payload Launcher {APP_VERSION}")
        self.geometry("900x650")
        self.selected_file = None
        
        # Main container
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title = ttk.Label(
            main_frame, 
            text="Enhanced Payload Comparison Launcher",
            font=("Arial", 16, "bold")
        )
        title.pack(pady=(0, 10))
        
        # Instructions
        instructions = ttk.Label(
            main_frame,
            text="Generate test data or select your own CSV/XLSX file for PayloadDiffViewer",
            font=("Arial", 10)
        )
        instructions.pack(pady=(0, 15))
        
        # === GENERATE TEST DATA SECTION ===
        generate_frame = ttk.LabelFrame(main_frame, text="Generate Sample Data", padding="15")
        generate_frame.pack(fill=tk.X, pady=(0, 15))
        
        gen_info = ttk.Label(
            generate_frame,
            text="Create a properly formatted CSV with sample payload comparison data",
            foreground="gray"
        )
        gen_info.pack(anchor=tk.W, pady=(0, 10))
        
        gen_controls = ttk.Frame(generate_frame)
        gen_controls.pack(fill=tk.X)
        
        ttk.Label(gen_controls, text="Number of rows:").pack(side=tk.LEFT, padx=(0, 10))
        
        self.rows_var = tk.StringVar(value="10")
        rows_spinbox = ttk.Spinbox(gen_controls, from_=5, to=100, textvariable=self.rows_var, width=10)
        rows_spinbox.pack(side=tk.LEFT, padx=(0, 20))
        
        ttk.Button(
            gen_controls, 
            text="🎲 Generate Sample CSV", 
            command=self.generate_sample
        ).pack(side=tk.LEFT)
        
        # === FILE SELECTION SECTION ===
        file_frame = ttk.LabelFrame(main_frame, text="Or Select Existing File", padding="15")
        file_frame.pack(fill=tk.X, pady=(0, 15))
        
        file_select = ttk.Frame(file_frame)
        file_select.pack(fill=tk.X)
        
        ttk.Label(file_select, text="Selected File:").pack(side=tk.LEFT, padx=(0, 10))
        
        self.file_entry = ttk.Entry(file_select, width=60)
        self.file_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        ttk.Button(file_select, text="Browse...", command=self.browse_file).pack(side=tk.LEFT)
        
        # File format requirements
        format_info = ttk.Label(
            file_frame,
            text="Required columns: 'Config Name', 'Config Key', 'CURRENT PAYLOAD', 'OLD PAYLOAD'",
            foreground="gray",
            font=("Arial", 9)
        )
        format_info.pack(anchor=tk.W, pady=(5, 0))
        
        # === VIEWER INFO SECTION ===
        viewer_frame = ttk.LabelFrame(main_frame, text="Viewer Information", padding="15")
        viewer_frame.pack(fill=tk.X, pady=(0, 15))
        
        viewer_path = find_viewer()
        if viewer_path:
            status_text = f"✅ Found: {viewer_path.name}"
            status_color = "green"
            location_text = f"Full path: {viewer_path}"
        else:
            status_text = "❌ PayloadDiffViewer not found"
            status_color = "red"
            location_text = f"Search location: {HERE}"
        
        self.viewer_label = ttk.Label(
            viewer_frame, 
            text=status_text,
            foreground=status_color,
            font=("Arial", 10, "bold")
        )
        self.viewer_label.pack(anchor=tk.W)
        
        ttk.Label(viewer_frame, text=location_text, foreground="gray").pack(anchor=tk.W, pady=(2, 0))
        
        # === LAUNCH BUTTON ===
        self.launch_btn = ttk.Button(
            main_frame,
            text="🚀 Launch Viewer",
            command=self.launch_viewer,
            state=tk.DISABLED
        )
        self.launch_btn.pack(pady=15)
        
        # === LOG AREA ===
        log_frame = ttk.LabelFrame(main_frame, text="Launch Log", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        # Add scrollbar
        log_scroll = ttk.Scrollbar(log_frame)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.log_text = tk.Text(log_frame, height=10, wrap=tk.WORD, yscrollcommand=log_scroll.set)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        log_scroll.config(command=self.log_text.yview)
        
        # Initial log
        self.log(f"Enhanced Payload Launcher v{APP_VERSION} started")
        self.log(f"Looking for viewer in: {HERE}")
        if viewer_path:
            self.log(f"✅ Viewer detected: {viewer_path.name}")
        else:
            self.log("❌ No viewer found - place it in the same folder")
    
    def generate_sample(self):
        """Generate sample CSV file for testing."""
        try:
            num_rows = int(self.rows_var.get())
            if num_rows < 1 or num_rows > 100:
                raise ValueError("Rows must be between 1 and 100")
        except ValueError as e:
            messagebox.showerror("Invalid Input", f"Please enter a valid number of rows (1-100)\\n{e}")
            return
        
        # Create output filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = HERE / f"sample_payload_data_{timestamp}.csv"
        
        try:
            self.log(f"Generating {num_rows} sample rows...")
            generate_sample_data(output_file, num_rows)
            self.log(f"✅ Generated: {output_file.name}")
            
            # Set as selected file
            self.selected_file = output_file
            self.file_entry.delete(0, tk.END)
            self.file_entry.insert(0, str(self.selected_file))
            self.launch_btn.configure(state=tk.NORMAL)
            
            messagebox.showinfo(
                "Sample Generated", 
                f"Created sample file with {num_rows} rows:\\n\\n{output_file.name}\\n\\nYou can now launch the viewer!"
            )
        except Exception as e:
            self.log(f"❌ Generation failed: {e}")
            messagebox.showerror("Generation Failed", f"Could not generate sample data:\\n{e}")
    
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
            messagebox.showwarning("No File", "Please generate sample data or select a CSV/XLSX file first.")
            return
        
        if not self.selected_file.exists():
            messagebox.showerror("File Not Found", f"The selected file does not exist:\\n{self.selected_file}")
            self.log(f"❌ File not found: {self.selected_file}")
            return
        
        self.log(f"\\n{'='*50}")
        self.log(f"Launching viewer with: {self.selected_file.name}")
        self.log(f"File size: {self.selected_file.stat().st_size:,} bytes")
        
        success = launch_viewer(self.selected_file, self.log)
        
        if success:
            self.log(f"✅ SUCCESS - Viewer launched!")
            messagebox.showinfo(
                "Launch Successful", 
                f"PayloadDiffViewer launched!\\n\\nFile: {self.selected_file.name}\\n\\nCheck if the data loaded correctly in the viewer."
            )
        else:
            self.log(f"❌ FAILED - Could not launch viewer")
    
    def log(self, message: str):
        """Add a message to the log area."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\\n")
        self.log_text.see(tk.END)


if __name__ == "__main__":
    app = EnhancedLauncherApp()
    app.mainloop()
'''

# Write the enhanced launcher
with open('EnhancedPayloadLauncher.py', 'w', encoding='utf-8') as f:
    f.write(enhanced_launcher)

print("✅ Created EnhancedPayloadLauncher.py")
print("\n" + "="*60)
print("ENHANCED PAYLOAD LAUNCHER CREATED")
print("="*60)
print("\nFile: EnhancedPayloadLauncher.py")
print(f"Size: {len(enhanced_launcher):,} characters")
print("\nKey Features:")
print("✅ Generate properly formatted sample CSV files")
print("✅ Customizable number of test rows (5-100)")
print("✅ Sample data with realistic payload JSON")
print("✅ Browse and select existing CSV/XLSX files")
print("✅ Auto-detects PayloadDiffViewer")
print("✅ Enhanced logging with timestamps")
print("✅ Proper column format for GeminiPayloadDiff.py")
print("\nSample Data Includes:")
print("• Config Name: acq_profl, scheme_config, routing_rule, fraud_config")
print("• Config Keys: VISA_CREDIT_US, MC_DEBIT_EU, AMEX_GLOBAL, etc.")
print("• CURRENT PAYLOAD: JSON with changed values")
print("• OLD PAYLOAD: JSON with original values")
print("• Timestamps and status fields")
print("\nTo Use:")
print("1. Run: python EnhancedPayloadLauncher.py")
print("2. Click 'Generate Sample CSV' to create test data")
print("3. Click 'Launch Viewer' to test with GeminiPayloadDiff.py")
print("\nThis will create files with the exact format expected by the viewer!")
