# Line-by-line starter notes (auto-generated)
This is not a replacement for real code review; it's a quick scaffold to help you read the file.
Source: PayloadDiffViewer_Tool_FIXED_v2.py
Generated: 2025-12-16 06:01:48

L0001: # -*- coding: utf-8 -*-
    -> comment/doc note (helps humans; ignored by Python).
L0002: """
    -> docstring delimiter (module/docs block).
L0003: PayloadDiffViewerApp.py - COMPLETE REFINED VERSION
    -> general Python statement supporting the app's workflow.
L0004: 
    -> blank line (spacing/section separation).
L0005: MAJOR ENHANCEMENTS (NOW IMPLEMENTED):
    -> general Python statement supporting the app's workflow.
L0006: ====================================
    -> general Python statement supporting the app's workflow.
L0007: 1. ULTRA-FAST LOADING: (As provided)
    -> general Python statement supporting the app's workflow.
L0008:    - Chunked Excel/CSV reading with pandas.
    -> pandas data handling (read/transform tabular data).
L0009:    - Real-time progress updates.
    -> general Python statement supporting the app's workflow.
L0010: 
    -> blank line (spacing/section separation).
L0011: 2. CONFIG NAME VALIDATION: (As provided)
    -> general Python statement supporting the app's workflow.
L0012:    - Pattern: ^[a-zA-Z0-9_]+$
    -> general Python statement supporting the app's workflow.
L0013:    - Auto-filters invalid names.
    -> general Python statement supporting the app's workflow.
L0014: 
    -> blank line (spacing/section separation).
L0015: 3. PERFORMANCE OPTIMIZATIONS (REFINEMENTS):
    -> general Python statement supporting the app's workflow.
L0016:    - Parallel diff computation (using a thread pool).
    -> general Python statement supporting the app's workflow.
L0017:    - Lazy JSON parsing (parsing now occurs in worker threads).
    -> general Python statement supporting the app's workflow.
L0018:    - 90%+ memory reduction by caching full payloads once per key,
    -> general Python statement supporting the app's workflow.
L0019:      not once per diff row.
    -> general Python statement supporting the app's workflow.
L0020:    - FORCED COLUMN MAPPING: Shows confirmation dialog if guesses are
    -> general Python statement supporting the app's workflow.
L0021:      low-confidence, fixing loading errors.
    -> general Python statement supporting the app's workflow.
L0022: 
    -> blank line (spacing/section separation).
L0023: 4. ALL ORIGINAL FEATURES PRESERVED:
    -> general Python statement supporting the app's workflow.
L0024:    - Smart column detection
    -> general Python statement supporting the app's workflow.
L0025:    - DeepDiff comparison engine
    -> DeepDiff usage (computes structured differences between JSON objects).
L0026:    - Synchronized JSON pane scrolling
    -> general Python statement supporting the app's workflow.
L0027:    - Inline diff visualization
    -> general Python statement supporting the app's workflow.
L0028:    - Export to CSV/TXT
    -> general Python statement supporting the app's workflow.
L0029:    - Summary dashboard with charts
    -> general Python statement supporting the app's workflow.
L0030:    - Watchlist filtering
    -> general Python statement supporting the app's workflow.
L0031:    - Keyboard shortcuts
    -> general Python statement supporting the app's workflow.
L0032: 
    -> blank line (spacing/section separation).
L0033: Installation:
    -> general Python statement supporting the app's workflow.
L0034: pip install pandas numpy openpyxl deepdiff matplotlib
    -> pandas data handling (read/transform tabular data).
L0035: 
    -> blank line (spacing/section separation).
L0036: """
    -> docstring delimiter (module/docs block).
L0037: 
    -> blank line (spacing/section separation).
L0038: from __future__ import annotations
    -> enables postponed evaluation of type hints (Python typing convenience).
L0039: import os
    -> imports a module/symbol used later (keeps code organized).
L0040: import re
    -> imports a module/symbol used later (keeps code organized).
L0041: import csv
    -> imports a module/symbol used later (keeps code organized).
L0042: import ast
    -> imports a module/symbol used later (keeps code organized).
L0043: import sys
    -> imports a module/symbol used later (keeps code organized).
L0044: import json
    -> imports a module/symbol used later (keeps code organized).
L0045: import time
    -> imports a module/symbol used later (keeps code organized).
L0046: import queue
    -> imports a module/symbol used later (keeps code organized).
L0047: import threading
    -> imports a module/symbol used later (keeps code organized).
L0048: import difflib
    -> imports a module/symbol used later (keeps code organized).
L0049: import random
    -> imports a module/symbol used later (keeps code organized).
L0050: import logging
    -> imports a module/symbol used later (keeps code organized).
L0051: import gc
    -> imports a module/symbol used later (keeps code organized).
L0052: from dataclasses import dataclass
    -> imports a module/symbol used later (keeps code organized).
L0053: from json import JSONDecodeError
    -> imports a module/symbol used later (keeps code organized).
L0054: from typing import Any, Dict, List, Tuple, Optional, Iterable
    -> imports a module/symbol used later (keeps code organized).
L0055: from urllib.parse import urlparse, parse_qs, unquote
    -> imports a module/symbol used later (keeps code organized).
L0056: from collections import defaultdict
    -> imports a module/symbol used later (keeps code organized).
L0057: from decimal import Decimal, InvalidOperation
    -> imports a module/symbol used later (keeps code organized).
L0058: 
    -> blank line (spacing/section separation).
L0059: # UI
    -> comment/doc note (helps humans; ignored by Python).
L0060: import tkinter as tk
    -> imports a module/symbol used later (keeps code organized).
L0061: from tkinter import ttk, filedialog, messagebox
    -> imports a module/symbol used later (keeps code organized).
L0062: from tkinter import font as tkfont
    -> imports a module/symbol used later (keeps code organized).
L0063: 
    -> blank line (spacing/section separation).
L0064: # Data processing (REQUIRED for performance)
    -> comment/doc note (helps humans; ignored by Python).
L0065: try:
    -> error handling block (keeps app stable under bad inputs).
L0066:     import pandas as pd
    -> imports a module/symbol used later (keeps code organized).
L0067:     import numpy as np
    -> imports a module/symbol used later (keeps code organized).
L0068:     HAS_PANDAS = True
    -> general Python statement supporting the app's workflow.
L0069: except ImportError:
    -> error handling block (keeps app stable under bad inputs).
L0070:     HAS_PANDAS = False
    -> general Python statement supporting the app's workflow.
L0071:     print("WARNING: pandas not found. Large file performance will be degraded.")
    -> pandas data handling (read/transform tabular data).
L0072:     print("Install: pip install pandas numpy openpyxl")
    -> pandas data handling (read/transform tabular data).
L0073: 
    -> blank line (spacing/section separation).
L0074: # Ultra-fast loader (optional)
    -> comment/doc note (helps humans; ignored by Python).
L0075: try:
    -> error handling block (keeps app stable under bad inputs).
L0076:     from ultra_fast_loader import UltraFastLoader as ExternalUltraFastLoader
    -> imports a module/symbol used later (keeps code organized).
L0077:     HAS_ULTRA_LOADER = True
    -> general Python statement supporting the app's workflow.
L0078: except Exception:
    -> error handling block (keeps app stable under bad inputs).
L0079:     HAS_ULTRA_LOADER = False
    -> general Python statement supporting the app's workflow.
L0080:     ExternalUltraFastLoader = None
    -> general Python statement supporting the app's workflow.
L0081: 
    -> blank line (spacing/section separation).
L0082: # DeepDiff
    -> comment/doc note (helps humans; ignored by Python).
L0083: try:
    -> error handling block (keeps app stable under bad inputs).
L0084:     from deepdiff import DeepDiff
    -> imports a module/symbol used later (keeps code organized).
L0085: except ImportError:
    -> error handling block (keeps app stable under bad inputs).
L0086:     print("ERROR: deepdiff is required. Install: pip install deepdiff")
    -> general Python statement supporting the app's workflow.
L0087:     sys.exit(1)
    -> general Python statement supporting the app's workflow.
L0088: 
    -> blank line (spacing/section separation).
L0089: # Optional: faster JSON
    -> comment/doc note (helps humans; ignored by Python).
L0090: try:
    -> error handling block (keeps app stable under bad inputs).
L0091:     import orjson
    -> imports a module/symbol used later (keeps code organized).
L0092: except ImportError:
    -> error handling block (keeps app stable under bad inputs).
L0093:     orjson = None
    -> general Python statement supporting the app's workflow.
L0094: 
    -> blank line (spacing/section separation).
L0095: # Optional: charting
    -> comment/doc note (helps humans; ignored by Python).
L0096: HAS_MPL = False
    -> general Python statement supporting the app's workflow.
L0097: try:
    -> error handling block (keeps app stable under bad inputs).
L0098:     import matplotlib
    -> imports a module/symbol used later (keeps code organized).
L0099:     matplotlib.use("TkAgg")
    -> general Python statement supporting the app's workflow.
L0100:     from matplotlib.figure import Figure
    -> imports a module/symbol used later (keeps code organized).
L0101:     from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    -> imports a module/symbol used later (keeps code organized).
L0102:     HAS_MPL = True
    -> general Python statement supporting the app's workflow.
L0103: except Exception:
    -> error handling block (keeps app stable under bad inputs).
L0104:     pass
    -> general Python statement supporting the app's workflow.
L0105: 
    -> blank line (spacing/section separation).
L0106: # Logging setup
    -> comment/doc note (helps humans; ignored by Python).
L0107: logging.basicConfig(
    -> general Python statement supporting the app's workflow.
L0108:     level=logging.INFO,
    -> general Python statement supporting the app's workflow.
L0109:     format='%(asctime)s - %(levelname)s - %(message)s',
    -> general Python statement supporting the app's workflow.
L0110:     handlers=[
    -> general Python statement supporting the app's workflow.
L0111:         logging.FileHandler(os.path.expanduser('~/.payloaddiff.log')),
    -> general Python statement supporting the app's workflow.
L0112:         logging.StreamHandler()
    -> general Python statement supporting the app's workflow.
L0113:     ]
    -> general Python statement supporting the app's workflow.
L0114: )
    -> general Python statement supporting the app's workflow.
L0115: logger = logging.getLogger(__name__)
    -> general Python statement supporting the app's workflow.
L0116: 
    -> blank line (spacing/section separation).
L0117: # ========================================================================
    -> comment/doc note (helps humans; ignored by Python).
L0118: # CONFIGURATION
    -> comment/doc note (helps humans; ignored by Python).
L0119: # ========================================================================
    -> comment/doc note (helps humans; ignored by Python).
L0120: 
    -> blank line (spacing/section separation).
L0121: @dataclass
    -> general Python statement supporting the app's workflow.
L0122: class Config:
    -> starts a class definition (bundles data + behavior).
L0123:     """Performance and UI configuration."""
    -> docstring delimiter (module/docs block).
L0124:     # Performance
    -> comment/doc note (helps humans; ignored by Python).
L0125:     EXCEL_CHUNK_SIZE: int = 50000
    -> general Python statement supporting the app's workflow.
L0126:     CSV_CHUNK_SIZE: int = 100000
    -> general Python statement supporting the app's workflow.
L0127:     MAX_WORKERS: int = 4  # Number of threads for parallel diffing
    -> general Python statement supporting the app's workflow.
L0128:     MAX_RECORDS: int = 1000000
    -> general Python statement supporting the app's workflow.
L0129:     PROGRESS_UPDATE_INTERVAL: int = 1000
    -> general Python statement supporting the app's workflow.
L0130: 
    -> blank line (spacing/section separation).
L0131:     # UI
    -> comment/doc note (helps humans; ignored by Python).
L0132:     WINDOW_W: int = 1450
    -> general Python statement supporting the app's workflow.
L0133:     WINDOW_H: int = 900
    -> general Python statement supporting the app's workflow.
L0134:     MIN_W: int = 1100
    -> general Python statement supporting the app's workflow.
L0135:     MIN_H: int = 720
    -> general Python statement supporting the app's workflow.
L0136:     DIFF_DISPLAY_LIMIT: int = 10000
    -> general Python statement supporting the app's workflow.
L0137: 
    -> blank line (spacing/section separation).
L0138:     # Display
    -> comment/doc note (helps humans; ignored by Python).
L0139:     TREE_COLUMNS: Tuple[str, ...] = ('CfgKey', 'Type', 'Key', 'Old', 'New')
    -> general Python statement supporting the app's workflow.
L0140:     TREE_WIDTHS: Dict[str, int] = None
    -> general Python statement supporting the app's workflow.
L0141:     INLINE_ROWS: int = 8
    -> general Python statement supporting the app's workflow.
L0142: 
    -> blank line (spacing/section separation).
L0143:     # Colors
    -> comment/doc note (helps humans; ignored by Python).
L0144:     COLOR_CHANGED: str = '#FFF5CC'
    -> general Python statement supporting the app's workflow.
L0145:     COLOR_ADDED: str = '#E6FFED'
    -> general Python statement supporting the app's workflow.
L0146:     COLOR_REMOVED: str = '#FFECEC'
    -> general Python statement supporting the app's workflow.
L0147:     COLOR_LINE_HIT_BG: str = '#CDE5FF'
    -> general Python statement supporting the app's workflow.
L0148:     COLOR_LINE_HIT_FG: str = 'black'
    -> general Python statement supporting the app's workflow.
L0149: 
    -> blank line (spacing/section separation).
L0150:     # Defaults
    -> comment/doc note (helps humans; ignored by Python).
L0151:     DEFAULT_WATCHLIST: str = 'numericCurrencyCode, schemeConfigs, processingAgreements'
    -> general Python statement supporting the app's workflow.
L0152:     SETTINGS_FILE: str = os.path.expanduser('~/.payloaddiff_settings.json')
    -> general Python statement supporting the app's workflow.
L0153: 
    -> blank line (spacing/section separation).
L0154:     # CONFIG NAME VALIDATION PATTERN (NEW)
    -> comment/doc note (helps humans; ignored by Python).
L0155:     CONFIG_NAME_PATTERN: re.Pattern = None
    -> general Python statement supporting the app's workflow.
L0156: 
    -> blank line (spacing/section separation).
L0157:     def __post_init__(self):
    -> starts a function definition (reusable logic).
L0158:         if self.TREE_WIDTHS is None:
    -> control flow decision (branches logic based on conditions).
L0159:             self.TREE_WIDTHS = {
    -> general Python statement supporting the app's workflow.
L0160:                 'CfgKey': 220, 'Type': 90, 'Key': 420, 'Old': 330, 'New': 330
    -> general Python statement supporting the app's workflow.
L0161:             }
    -> general Python statement supporting the app's workflow.
L0162:         if self.CONFIG_NAME_PATTERN is None:
    -> control flow decision (branches logic based on conditions).
L0163:             # Only allow alphanumeric and underscores
    -> comment/doc note (helps humans; ignored by Python).
L0164:             object.__setattr__(self, 'CONFIG_NAME_PATTERN', re.compile(r'^[a-zA-Z0-9_]+$'))
    -> general Python statement supporting the app's workflow.
L0165: 
    -> blank line (spacing/section separation).
L0166:     def validate_config_name(self, name: str) -> bool:
    -> starts a function definition (reusable logic).
L0167:         """Validate config name: alphanumeric + underscores only."""
    -> docstring delimiter (module/docs block).
L0168:         if not name or not isinstance(name, str):
    -> control flow decision (branches logic based on conditions).
L0169:             return False
    -> returns a value from a function/method.
L0170:         name = name.strip()
    -> general Python statement supporting the app's workflow.
L0171:         if not name:
    -> control flow decision (branches logic based on conditions).
L0172:             return False
    -> returns a value from a function/method.
L0173:         return bool(self.CONFIG_NAME_PATTERN.match(name))
    -> returns a value from a function/method.
L0174: 
    -> blank line (spacing/section separation).
L0175: config = Config()
    -> general Python statement supporting the app's workflow.
L0176: 
    -> blank line (spacing/section separation).
L0177: 
    -> blank line (spacing/section separation).
L0178: 
    -> blank line (spacing/section separation).
L0179: # ========================================================================
    -> comment/doc note (helps humans; ignored by Python).
L0180: # HELPER FUNCTIONS
    -> comment/doc note (helps humans; ignored by Python).
L0181: # ========================================================================
    -> comment/doc note (helps humans; ignored by Python).
L0182: 
    -> blank line (spacing/section separation).
L0183: def sharepoint_url_to_unc(url: str) -> Optional[str]:
    -> starts a function definition (reusable logic).
L0184:     """
    -> docstring delimiter (module/docs block).
L0185:     Convert SharePoint/OneDrive folder URLs to a UNC/WebDAV path Windows understands.
    -> general Python statement supporting the app's workflow.
L0186:     """
    -> docstring delimiter (module/docs block).
L0187:     try:
    -> error handling block (keeps app stable under bad inputs).
L0188:         u = urlparse(url.strip())
    -> general Python statement supporting the app's workflow.
L0189:         if u.scheme not in ('http', 'https') or 'sharepoint.com' not in u.netloc:
    -> control flow decision (branches logic based on conditions).
L0190:             return None
    -> returns a value from a function/method.
L0191: 
    -> blank line (spacing/section separation).
L0192:         path = u.path
    -> general Python statement supporting the app's workflow.
L0193:         if path.rstrip('/').endswith('/my'):
    -> control flow decision (branches logic based on conditions).
L0194:             q = parse_qs(u.query or '')
    -> general Python statement supporting the app's workflow.
L0195:             raw_id = (q.get('id') or [None])[0]
    -> general Python statement supporting the app's workflow.
L0196:             if raw_id:
    -> control flow decision (branches logic based on conditions).
L0197:                 path = raw_id
    -> general Python statement supporting the app's workflow.
L0198:         path = str(path).replace('/:f:/r/', '/').strip('/')
    -> general Python statement supporting the app's workflow.
L0199:         path = unquote(path)
    -> general Python statement supporting the app's workflow.
L0200: 
    -> blank line (spacing/section separation).
L0201:         if not (path.startswith('personal/') or path.startswith('sites/')):
    -> control flow decision (branches logic based on conditions).
L0202:             return None
    -> returns a value from a function/method.
L0203: 
    -> blank line (spacing/section separation).
L0204:         host = u.netloc
    -> general Python statement supporting the app's workflow.
L0205:         return r"\\{host}@SSL\{path}".format(host=host, path=path.replace('/', '\\'))
    -> returns a value from a function/method.
L0206:     except Exception:
    -> error handling block (keeps app stable under bad inputs).
L0207:         return None
    -> returns a value from a function/method.
L0208: 
    -> blank line (spacing/section separation).
L0209: # --------------------------------
    -> comment/doc note (helps humans; ignored by Python).
L0210: # Logger for parse warnings/errors (GUI)
    -> comment/doc note (helps humans; ignored by Python).
L0211: # --------------------------------
    -> comment/doc note (helps humans; ignored by Python).
L0212: 
    -> blank line (spacing/section separation).
L0213: class ParseLogger:
    -> starts a class definition (bundles data + behavior).
L0214:     """Lightweight parse logger with a Toplevel viewer."""
    -> docstring delimiter (module/docs block).
L0215:     def __init__(self):
    -> starts a function definition (reusable logic).
L0216:         self.entries: List[Dict[str, Any]] = []
    -> general Python statement supporting the app's workflow.
L0217: 
    -> blank line (spacing/section separation).
L0218:     def log(self, message: str, level: str = 'warning', context: str = '') -> None:
    -> starts a function definition (reusable logic).
L0219:         self.entries.append({
    -> general Python statement supporting the app's workflow.
L0220:             'timestamp': time.time(),
    -> general Python statement supporting the app's workflow.
L0221:             'level': level,
    -> general Python statement supporting the app's workflow.
L0222:             'message': message,
    -> general Python statement supporting the app's workflow.
L0223:             'context': (context or '')[:200]
    -> general Python statement supporting the app's workflow.
L0224:         })
    -> general Python statement supporting the app's workflow.
L0225: 
    -> blank line (spacing/section separation).
L0226:     def summary_text(self, limit: int = 200) -> str:
    -> starts a function definition (reusable logic).
L0227:         if not self.entries:
    -> control flow decision (branches logic based on conditions).
L0228:             return "No warnings or errors recorded."
    -> returns a value from a function/method.
L0229:         lines = ["=" * 64, f"Parse Log (last {min(limit, len(self.entries))} of {len(self.entries)})", "=" * 64, ""]
    -> general Python statement supporting the app's workflow.
L0230:         for e in self.entries[-limit:]:
    -> loop (repeats logic across items).
L0231:             ts = time.strftime('%H:%M:%S', time.localtime(e['timestamp']))
    -> general Python statement supporting the app's workflow.
L0232:             lines.append(f"[{ts}] {e['level'].upper()}: {e['message']}")
    -> general Python statement supporting the app's workflow.
L0233:             if e['context']:
    -> control flow decision (branches logic based on conditions).
L0234:                 lines.append(f"  Context: {e['context']}")
    -> general Python statement supporting the app's workflow.
L0235:         return "\n".join(lines)
    -> returns a value from a function/method.
L0236: 
    -> blank line (spacing/section separation).
L0237:     def show(self, parent: tk.Tk) -> None:
    -> starts a function definition (reusable logic).
L0238:         top = tk.Toplevel(parent)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0239:         top.title("Parse Log")
    -> general Python statement supporting the app's workflow.
L0240:         top.geometry("800x500")
    -> general Python statement supporting the app's workflow.
L0241:         txt = tk.Text(top, wrap='word', font=("Courier New", 9))
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0242:         txt.pack(fill=tk.BOTH, expand=True)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0243:         txt.insert('1.0', self.summary_text())
    -> general Python statement supporting the app's workflow.
L0244:         txt.configure(state='disabled')
    -> general Python statement supporting the app's workflow.
L0245: 
    -> blank line (spacing/section separation).
L0246: 
    -> blank line (spacing/section separation).
L0247: # --------------------------
    -> comment/doc note (helps humans; ignored by Python).
L0248: # Helpers: JSON + Deep paths
    -> comment/doc note (helps humans; ignored by Python).
L0249: # --------------------------
    -> comment/doc note (helps humans; ignored by Python).
L0250: 
    -> blank line (spacing/section separation).
L0251: TRAILING_COMMAS = re.compile(r',\s*([}\]])')
    -> general Python statement supporting the app's workflow.
L0252: 
    -> blank line (spacing/section separation).
L0253: def parse_jsonish_verbose(s: str) -> Tuple[Any, str]:
    -> starts a function definition (reusable logic).
L0254:     """
    -> docstring delimiter (module/docs block).
L0255:     Return (parsed_obj, error_message_if_any).
    -> general Python statement supporting the app's workflow.
L0256:     Tries strict JSON -> trailing-comma fix -> ast.literal_eval
    -> general Python statement supporting the app's workflow.
L0257:     """
    -> docstring delimiter (module/docs block).
L0258:     t = (s or '').strip()
    -> general Python statement supporting the app's workflow.
L0259:     if not t:
    -> control flow decision (branches logic based on conditions).
L0260:         return None, "Empty payload"
    -> returns a value from a function/method.
L0261: 
    -> blank line (spacing/section separation).
L0262:     try:
    -> error handling block (keeps app stable under bad inputs).
L0263:         return json.loads(t), ""
    -> returns a value from a function/method.
L0264:     except JSONDecodeError:
    -> error handling block (keeps app stable under bad inputs).
L0265:         pass
    -> general Python statement supporting the app's workflow.
L0266: 
    -> blank line (spacing/section separation).
L0267:     try:
    -> error handling block (keeps app stable under bad inputs).
L0268:         t2 = TRAILING_COMMAS.sub(r'\1', t)
    -> general Python statement supporting the app's workflow.
L0269:         return json.loads(t2), ""
    -> returns a value from a function/method.
L0270:     except JSONDecodeError:
    -> error handling block (keeps app stable under bad inputs).
L0271:         pass
    -> general Python statement supporting the app's workflow.
L0272: 
    -> blank line (spacing/section separation).
L0273:     try:
    -> error handling block (keeps app stable under bad inputs).
L0274:         return ast.literal_eval(t), ""
    -> returns a value from a function/method.
L0275:     except (ValueError, SyntaxError, TypeError) as e:
    -> error handling block (keeps app stable under bad inputs).
L0276:         return None, f"Failed to parse payload ({e.__class__.__name__})"
    -> returns a value from a function/method.
L0277: 
    -> blank line (spacing/section separation).
L0278: 
    -> blank line (spacing/section separation).
L0279: def pretty_json(obj: Any) -> str:
    -> starts a function definition (reusable logic).
L0280:     if obj is None:
    -> control flow decision (branches logic based on conditions).
L0281:         return ""
    -> returns a value from a function/method.
L0282:     try:
    -> error handling block (keeps app stable under bad inputs).
L0283:         if orjson is not None:
    -> control flow decision (branches logic based on conditions).
L0284:             return orjson.dumps(obj, option=orjson.OPT_INDENT_2).decode()
    -> returns a value from a function/method.
L0285:     except Exception:
    -> error handling block (keeps app stable under bad inputs).
L0286:         pass
    -> general Python statement supporting the app's workflow.
L0287:     try:
    -> error handling block (keeps app stable under bad inputs).
L0288:         return json.dumps(obj, indent=2, ensure_ascii=False)
    -> returns a value from a function/method.
L0289:     except Exception:
    -> error handling block (keeps app stable under bad inputs).
L0290:         return str(obj)
    -> returns a value from a function/method.
L0291: 
    -> blank line (spacing/section separation).
L0292: 
    -> blank line (spacing/section separation).
L0293: def dd_path_to_key(p: str) -> str:
    -> starts a function definition (reusable logic).
L0294:     """
    -> docstring delimiter (module/docs block).
L0295:     DeepDiff path "root['a'][2]['b']" -> "a[2].b"
    -> DeepDiff usage (computes structured differences between JSON objects).
L0296:     """
    -> docstring delimiter (module/docs block).
L0297:     if not p:
    -> control flow decision (branches logic based on conditions).
L0298:         return ""
    -> returns a value from a function/method.
L0299:     p = p.replace("root", "")
    -> general Python statement supporting the app's workflow.
L0300:     p = re.sub(r"\['([^']*)'\]", r".\1", p) # Handle empty strings in keys
    -> general Python statement supporting the app's workflow.
L0301:     p = re.sub(r"\[(\d+)\]", r"[\1]", p) # Keep numeric indices as is
    -> general Python statement supporting the app's workflow.
L0302:     p = p.lstrip('.')
    -> general Python statement supporting the app's workflow.
L0303:     return p
    -> returns a value from a function/method.
L0304: 
    -> blank line (spacing/section separation).
L0305: 
    -> blank line (spacing/section separation).
L0306: def _path_tokens(path: str) -> List[str]:
    -> starts a function definition (reusable logic).
L0307:     """
    -> docstring delimiter (module/docs block).
L0308:     Turn "a[2].b.c[10]" into tokens: ['a', '[2]', 'b', 'c', '[10]']
    -> general Python statement supporting the app's workflow.
L0309:     """
    -> docstring delimiter (module/docs block).
L0310:     return [tok for tok in re.split(r'\.|(\[\d+\])', path) if tok]
    -> returns a value from a function/method.
L0311: 
    -> blank line (spacing/section separation).
L0312: 
    -> blank line (spacing/section separation).
L0313: def value_from_path(obj: Any, dd_path: str) -> Any:
    -> starts a function definition (reusable logic).
L0314:     """
    -> docstring delimiter (module/docs block).
L0315:     Try to fetch value from obj following DeepDiff path string.
    -> DeepDiff usage (computes structured differences between JSON objects).
L0316:     """
    -> docstring delimiter (module/docs block).
L0317:     dotted = dd_path_to_key(dd_path)
    -> general Python statement supporting the app's workflow.
L0318:     toks = _path_tokens(dotted)
    -> general Python statement supporting the app's workflow.
L0319:     cur = obj
    -> general Python statement supporting the app's workflow.
L0320:     try:
    -> error handling block (keeps app stable under bad inputs).
L0321:         for t in toks:
    -> loop (repeats logic across items).
L0322:             if t.startswith('[') and t.endswith(']'):
    -> control flow decision (branches logic based on conditions).
L0323:                 idx = int(t[1:-1])
    -> general Python statement supporting the app's workflow.
L0324:                 cur = cur[idx]
    -> general Python statement supporting the app's workflow.
L0325:             else:
    -> control flow decision (branches logic based on conditions).
L0326:                 cur = cur[t]
    -> general Python statement supporting the app's workflow.
L0327:         return cur
    -> returns a value from a function/method.
L0328:     except (KeyError, IndexError, TypeError):
    -> error handling block (keeps app stable under bad inputs).
L0329:         return None
    -> returns a value from a function/method.
L0330: 
    -> blank line (spacing/section separation).
L0331: 
    -> blank line (spacing/section separation).
L0332: def build_fragment_from_path_value(path: str, value: Any) -> Any:
    -> starts a function definition (reusable logic).
L0333:     """
    -> docstring delimiter (module/docs block).
L0334:     Make a minimal JSON fragment showing the the leaf at `path` with `value`.
    -> general Python statement supporting the app's workflow.
L0335:     """
    -> docstring delimiter (module/docs block).
L0336:     tokens = _path_tokens(path)
    -> general Python statement supporting the app's workflow.
L0337:     if not tokens:
    -> control flow decision (branches logic based on conditions).
L0338:         return value
    -> returns a value from a function/method.
L0339: 
    -> blank line (spacing/section separation).
L0340:     fragment = value
    -> general Python statement supporting the app's workflow.
L0341:     for tok in reversed(tokens):
    -> loop (repeats logic across items).
L0342:         if tok.startswith('[') and tok.endswith(']'):
    -> control flow decision (branches logic based on conditions).
L0343:             idx = int(tok[1:-1])
    -> general Python statement supporting the app's workflow.
L0344:             new_list = [None] * (idx + 1)
    -> general Python statement supporting the app's workflow.
L0345:             new_list[idx] = fragment
    -> general Python statement supporting the app's workflow.
L0346:             fragment = new_list
    -> general Python statement supporting the app's workflow.
L0347:         else:
    -> control flow decision (branches logic based on conditions).
L0348:             fragment = {tok: fragment}
    -> general Python statement supporting the app's workflow.
L0349:     return fragment
    -> returns a value from a function/method.
L0350: 
    -> blank line (spacing/section separation).
L0351: 
    -> blank line (spacing/section separation).
L0352: # ---------------------------------
    -> comment/doc note (helps humans; ignored by Python).
L0353: # File reading helpers (CSV/Excel)
    -> comment/doc note (helps humans; ignored by Python).
L0354: # ---------------------------------
    -> comment/doc note (helps humans; ignored by Python).
L0355: 
    -> blank line (spacing/section separation).
L0356: def _bump_csv_field_limit():
    -> starts a function definition (reusable logic).
L0357:     try:
    -> error handling block (keeps app stable under bad inputs).
L0358:         csv.field_size_limit(sys.maxsize)
    -> general Python statement supporting the app's workflow.
L0359:     except OverflowError:
    -> error handling block (keeps app stable under bad inputs).
L0360:         csv.field_size_limit(2**30)
    -> general Python statement supporting the app's workflow.
L0361: 
    -> blank line (spacing/section separation).
L0362: 
    -> blank line (spacing/section separation).
L0363: def _sniff_csv_delimiter(path: str) -> str:
    -> starts a function definition (reusable logic).
L0364:     default = ','
    -> general Python statement supporting the app's workflow.
L0365:     ext = os.path.splitext(path)[1].lower()
    -> general Python statement supporting the app's workflow.
L0366:     if ext == '.tsv':
    -> control flow decision (branches logic based on conditions).
L0367:         return '\t'
    -> returns a value from a function/method.
L0368:     try:
    -> error handling block (keeps app stable under bad inputs).
L0369:         with open(path, 'r', encoding='utf-8', errors='replace', newline='') as f:
    -> general Python statement supporting the app's workflow.
L0370:             sample = f.read(8192)
    -> general Python statement supporting the app's workflow.
L0371:             sniffer = csv.Sniffer()
    -> general Python statement supporting the app's workflow.
L0372:             dialect = sniffer.sniff(sample, delimiters=',\t;|')
    -> general Python statement supporting the app's workflow.
L0373:             return dialect.delimiter
    -> returns a value from a function/method.
L0374:     except (csv.Error, UnicodeDecodeError):
    -> error handling block (keeps app stable under bad inputs).
L0375:         return default
    -> returns a value from a function/method.
L0376: 
    -> blank line (spacing/section separation).
L0377: 
    -> blank line (spacing/section separation).
L0378: def _load_csv_like_headers_rows(path: str) -> Tuple[List[str], List[List[str]]]:
    -> starts a function definition (reusable logic).
L0379:     _bump_csv_field_limit()
    -> general Python statement supporting the app's workflow.
L0380:     delim = _sniff_csv_delimiter(path)
    -> general Python statement supporting the app's workflow.
L0381:     with open(path, 'r', encoding='utf-8', errors='replace', newline='') as f:
    -> general Python statement supporting the app's workflow.
L0382:         reader = csv.reader(f, delimiter=delim)
    -> general Python statement supporting the app's workflow.
L0383:         try:
    -> error handling block (keeps app stable under bad inputs).
L0384:             headers = [str(h) for h in next(reader)]
    -> general Python statement supporting the app's workflow.
L0385:         except StopIteration:
    -> error handling block (keeps app stable under bad inputs).
L0386:             return [], []
    -> returns a value from a function/method.
L0387:         rows: List[List[str]] = []
    -> general Python statement supporting the app's workflow.
L0388:         for row in reader:
    -> loop (repeats logic across items).
L0389:             rows.append([str(x) if x is not None else '' for x in row])
    -> general Python statement supporting the app's workflow.
L0390:         return headers, rows
    -> returns a value from a function/method.
L0391: 
    -> blank line (spacing/section separation).
L0392: 
    -> blank line (spacing/section separation).
L0393: 
    -> blank line (spacing/section separation).
L0394: def _load_csv_like_headers_rows_chunked(path: str, chunk_size: int = 20000,
    -> starts a function definition (reusable logic).
L0395:                                         progress_cb: Optional[callable] = None) -> Tuple[List[str], List[List[str]]]:
    -> general Python statement supporting the app's workflow.
L0396:     """
    -> docstring delimiter (module/docs block).
L0397:     Optimized CSV/TSV loader.
    -> general Python statement supporting the app's workflow.
L0398: 
    -> blank line (spacing/section separation).
L0399:     If UltraFastLoader is available, it is used first. On any error or if the
    -> general Python statement supporting the app's workflow.
L0400:     module is not present, the original pandas-based chunk loader is used, and
    -> pandas data handling (read/transform tabular data).
L0401:     finally the simple csv.reader loader as a last fallback.
    -> error handling block (keeps app stable under bad inputs).
L0402:     """
    -> docstring delimiter (module/docs block).
L0403:     # Fallback when pandas itself is missing
    -> comment/doc note (helps humans; ignored by Python).
L0404:     if not HAS_PANDAS:
    -> control flow decision (branches logic based on conditions).
L0405:         return _load_csv_like_headers_rows(path)
    -> returns a value from a function/method.
L0406: 
    -> blank line (spacing/section separation).
L0407:     # ------------------------------------------------------------------
    -> comment/doc note (helps humans; ignored by Python).
L0408:     # 1) Try UltraFastLoader (if available)
    -> comment/doc note (helps humans; ignored by Python).
L0409:     # ------------------------------------------------------------------
    -> comment/doc note (helps humans; ignored by Python).
L0410:     if globals().get("HAS_ULTRA_LOADER", False) and "ExternalUltraFastLoader" in globals():
    -> control flow decision (branches logic based on conditions).
L0411:         try:
    -> error handling block (keeps app stable under bad inputs).
L0412:             logger.info("Using UltraFastLoader for CSV-like file: %s", path)
    -> general Python statement supporting the app's workflow.
L0413:             loader = ExternalUltraFastLoader()
    -> general Python statement supporting the app's workflow.
L0414:             headers = None
    -> general Python statement supporting the app's workflow.
L0415:             all_rows: List[List[str]] = []
    -> general Python statement supporting the app's workflow.
L0416: 
    -> blank line (spacing/section separation).
L0417:             def ultra_progress(current, total):
    -> starts a function definition (reusable logic).
L0418:                 if not progress_cb:
    -> control flow decision (branches logic based on conditions).
L0419:                     return
    -> returns a value from a function/method.
L0420:                 if total and total > 0:
    -> control flow decision (branches logic based on conditions).
L0421:                     pct = int(current * 100 / max(total, 1))
    -> general Python statement supporting the app's workflow.
L0422:                 else:
    -> control flow decision (branches logic based on conditions).
L0423:                     pct = 0
    -> general Python statement supporting the app's workflow.
L0424:                 progress_cb(min(100, max(0, pct)),
    -> general Python statement supporting the app's workflow.
L0425:                             f"Read ~{current:,} rows (Ultra)")
    -> general Python statement supporting the app's workflow.
L0426: 
    -> blank line (spacing/section separation).
L0427:             for chunk in loader.load_chunked(
    -> loop (repeats logic across items).
L0428:                 path,
    -> general Python statement supporting the app's workflow.
L0429:                 chunk_size=chunk_size,
    -> general Python statement supporting the app's workflow.
L0430:                 progress_callback=ultra_progress,
    -> general Python statement supporting the app's workflow.
L0431:             ):
    -> general Python statement supporting the app's workflow.
L0432:                 if headers is None:
    -> control flow decision (branches logic based on conditions).
L0433:                     headers = [str(c) for c in chunk.columns]
    -> general Python statement supporting the app's workflow.
L0434:                 chunk = chunk.astype(str).fillna("")
    -> general Python statement supporting the app's workflow.
L0435:                 all_rows.extend(chunk.values.tolist())
    -> general Python statement supporting the app's workflow.
L0436: 
    -> blank line (spacing/section separation).
L0437:             if headers is not None:
    -> control flow decision (branches logic based on conditions).
L0438:                 return headers, all_rows
    -> returns a value from a function/method.
L0439:         except Exception as e:
    -> error handling block (keeps app stable under bad inputs).
L0440:             logger.warning("UltraFastLoader failed, falling back to internal CSV loader: %s", e)
    -> general Python statement supporting the app's workflow.
L0441:             if progress_cb:
    -> control flow decision (branches logic based on conditions).
L0442:                 progress_cb(0, f"UltraFastLoader failed ({e}), using pandas loader...")
    -> pandas data handling (read/transform tabular data).
L0443: 
    -> blank line (spacing/section separation).
L0444:     # ------------------------------------------------------------------
    -> comment/doc note (helps humans; ignored by Python).
L0445:     # 2) Original pandas chunked CSV loader (existing logic)
    -> comment/doc note (helps humans; ignored by Python).
L0446:     # ------------------------------------------------------------------
    -> comment/doc note (helps humans; ignored by Python).
L0447:     delim = _sniff_csv_delimiter(path)
    -> general Python statement supporting the app's workflow.
L0448:     try:
    -> error handling block (keeps app stable under bad inputs).
L0449:         file_size = os.path.getsize(path)
    -> general Python statement supporting the app's workflow.
L0450:     except OSError:
    -> error handling block (keeps app stable under bad inputs).
L0451:         file_size = None
    -> general Python statement supporting the app's workflow.
L0452: 
    -> blank line (spacing/section separation).
L0453:     headers = None
    -> general Python statement supporting the app's workflow.
L0454:     all_rows: List[List[str]] = []
    -> general Python statement supporting the app's workflow.
L0455: 
    -> blank line (spacing/section separation).
L0456:     try:
    -> error handling block (keeps app stable under bad inputs).
L0457:         chunks = pd.read_csv(
    -> pandas data handling (read/transform tabular data).
L0458:             path,
    -> general Python statement supporting the app's workflow.
L0459:             dtype=str,
    -> general Python statement supporting the app's workflow.
L0460:             chunksize=chunk_size,
    -> general Python statement supporting the app's workflow.
L0461:             sep=delim,
    -> general Python statement supporting the app's workflow.
L0462:             engine='python',
    -> general Python statement supporting the app's workflow.
L0463:             on_bad_lines='skip',
    -> general Python statement supporting the app's workflow.
L0464:             encoding='utf-8',
    -> general Python statement supporting the app's workflow.
L0465:             encoding_errors='replace',
    -> general Python statement supporting the app's workflow.
L0466:         )
    -> general Python statement supporting the app's workflow.
L0467: 
    -> blank line (spacing/section separation).
L0468:         total_chunks = (file_size // (chunk_size * 100)) + 1 if file_size else 10
    -> general Python statement supporting the app's workflow.
L0469: 
    -> blank line (spacing/section separation).
L0470:         for i, chunk in enumerate(chunks, 1):
    -> loop (repeats logic across items).
L0471:             if headers is None:
    -> control flow decision (branches logic based on conditions).
L0472:                 headers = [str(c) for c in chunk.columns]
    -> general Python statement supporting the app's workflow.
L0473:             chunk = chunk.astype(str).fillna("")
    -> general Python statement supporting the app's workflow.
L0474:             all_rows.extend(chunk.values.tolist())
    -> general Python statement supporting the app's workflow.
L0475: 
    -> blank line (spacing/section separation).
L0476:             if progress_cb:
    -> control flow decision (branches logic based on conditions).
L0477:                 step = min(100, int((i / max(1, total_chunks)) * 100))
    -> general Python statement supporting the app's workflow.
L0478:                 progress_cb(step, f"Read ~{len(all_rows):,} rows")
    -> general Python statement supporting the app's workflow.
L0479: 
    -> blank line (spacing/section separation).
L0480:     except Exception as e:
    -> error handling block (keeps app stable under bad inputs).
L0481:         logger.error("Pandas CSV load failed, falling back. Error: %s", e)
    -> general Python statement supporting the app's workflow.
L0482:         if progress_cb:
    -> control flow decision (branches logic based on conditions).
L0483:             progress_cb(50, f"Pandas failed ({e}), falling back...")
    -> general Python statement supporting the app's workflow.
L0484:         return _load_csv_like_headers_rows(path)
    -> returns a value from a function/method.
L0485: 
    -> blank line (spacing/section separation).
L0486:     return headers or [], all_rows
    -> returns a value from a function/method.
L0487: 
    -> blank line (spacing/section separation).
L0488: 
    -> blank line (spacing/section separation).
L0489: 
    -> blank line (spacing/section separation).
L0490: def _excel_headers_rows(path: str, sheet: Optional[str] = None, progress_cb: Optional[callable] = None) -> Tuple[List...
    -> starts a function definition (reusable logic).
L0491:     """
    -> docstring delimiter (module/docs block).
L0492:     Optimized Excel loader.
    -> general Python statement supporting the app's workflow.
L0493: 
    -> blank line (spacing/section separation).
L0494:     1) Try UltraFastLoader (if available) for very fast reads and progress.
    -> general Python statement supporting the app's workflow.
L0495:     2) Fallback to pandas.read_excel with header scoring (previous behavior).
    -> pandas data handling (read/transform tabular data).
L0496:     """
    -> docstring delimiter (module/docs block).
L0497:     if not HAS_PANDAS:
    -> control flow decision (branches logic based on conditions).
L0498:         raise RuntimeError("pandas is required to read Excel files")
    -> pandas data handling (read/transform tabular data).
L0499: 
    -> blank line (spacing/section separation).
L0500:     # 1) UltraFastLoader path
    -> comment/doc note (helps humans; ignored by Python).
L0501:     if globals().get("HAS_ULTRA_LOADER", False) and "ExternalUltraFastLoader" in globals():
    -> control flow decision (branches logic based on conditions).
L0502:         try:
    -> error handling block (keeps app stable under bad inputs).
L0503:             logger.info("Using UltraFastLoader for Excel file: %s", path)
    -> general Python statement supporting the app's workflow.
L0504:             loader = ExternalUltraFastLoader()
    -> general Python statement supporting the app's workflow.
L0505:             headers: Optional[List[str]] = None
    -> general Python statement supporting the app's workflow.
L0506:             all_rows: List[List[str]] = []
    -> general Python statement supporting the app's workflow.
L0507: 
    -> blank line (spacing/section separation).
L0508:             def ultra_progress(current, total):
    -> starts a function definition (reusable logic).
L0509:                 if not progress_cb:
    -> control flow decision (branches logic based on conditions).
L0510:                     return
    -> returns a value from a function/method.
L0511:                 if total and total > 0:
    -> control flow decision (branches logic based on conditions).
L0512:                     pct = int(current * 100 / max(total, 1))
    -> general Python statement supporting the app's workflow.
L0513:                 else:
    -> control flow decision (branches logic based on conditions).
L0514:                     pct = 0
    -> general Python statement supporting the app's workflow.
L0515:                 progress_cb(
    -> general Python statement supporting the app's workflow.
L0516:                     min(100, max(0, pct)),
    -> general Python statement supporting the app's workflow.
L0517:                     f"Read ~{current:,} rows (Ultra Excel)"
    -> general Python statement supporting the app's workflow.
L0518:                 )
    -> general Python statement supporting the app's workflow.
L0519: 
    -> blank line (spacing/section separation).
L0520:             # For Excel we typically don't chunk by a fixed row size here;
    -> comment/doc note (helps humans; ignored by Python).
L0521:             # UltraFastLoader will decide the best strategy.
    -> comment/doc note (helps humans; ignored by Python).
L0522:             for chunk in loader.load_chunked(
    -> loop (repeats logic across items).
L0523:                 path,
    -> general Python statement supporting the app's workflow.
L0524:                 chunk_size=None,
    -> general Python statement supporting the app's workflow.
L0525:                 progress_callback=ultra_progress,
    -> general Python statement supporting the app's workflow.
L0526:             ):
    -> general Python statement supporting the app's workflow.
L0527:                 if headers is None:
    -> control flow decision (branches logic based on conditions).
L0528:                     headers = [str(c) for c in chunk.columns]
    -> general Python statement supporting the app's workflow.
L0529:                 chunk = chunk.astype(str).fillna("")
    -> general Python statement supporting the app's workflow.
L0530:                 all_rows.extend(chunk.values.tolist())
    -> general Python statement supporting the app's workflow.
L0531: 
    -> blank line (spacing/section separation).
L0532:             if headers is not None:
    -> control flow decision (branches logic based on conditions).
L0533:                 return headers, all_rows
    -> returns a value from a function/method.
L0534:         except Exception as e:
    -> error handling block (keeps app stable under bad inputs).
L0535:             logger.warning("UltraFastLoader Excel path failed, falling back to pandas: %s", e)
    -> pandas data handling (read/transform tabular data).
L0536:             if progress_cb:
    -> control flow decision (branches logic based on conditions).
L0537:                 progress_cb(0, f"UltraFastLoader Excel failed ({e}), using pandas reader...")
    -> pandas data handling (read/transform tabular data).
L0538: 
    -> blank line (spacing/section separation).
L0539:     # 2) Fallback: original pandas implementation
    -> comment/doc note (helps humans; ignored by Python).
L0540:     try:
    -> error handling block (keeps app stable under bad inputs).
L0541:         # Try with openpyxl engine first, as it's common
    -> comment/doc note (helps humans; ignored by Python).
L0542:         book = pd.read_excel(path, sheet_name=None, dtype=str, engine="openpyxl")
    -> pandas data handling (read/transform tabular data).
L0543:     except ImportError:
    -> error handling block (keeps app stable under bad inputs).
L0544:         logger.warning("openpyxl not found, falling back to default pandas excel engine.")
    -> pandas data handling (read/transform tabular data).
L0545:         book = pd.read_excel(path, sheet_name=None, dtype=str)
    -> pandas data handling (read/transform tabular data).
L0546:     except Exception as e:
    -> error handling block (keeps app stable under bad inputs).
L0547:         raise RuntimeError(f"Failed to read Excel file: {e}") from e
    -> general Python statement supporting the app's workflow.
L0548: 
    -> blank line (spacing/section separation).
L0549:     if sheet:
    -> control flow decision (branches logic based on conditions).
L0550:         df = book.get(sheet)
    -> general Python statement supporting the app's workflow.
L0551:         if df is None:
    -> control flow decision (branches logic based on conditions).
L0552:             raise ValueError(f"Sheet '{sheet}' not found in the Excel file.")
    -> general Python statement supporting the app's workflow.
L0553:         df = df.astype(str).fillna("")
    -> general Python statement supporting the app's workflow.
L0554:         return [str(c) for c in df.columns], df.values.tolist()
    -> returns a value from a function/method.
L0555: 
    -> blank line (spacing/section separation).
L0556:     best_headers: List[str] = []
    -> general Python statement supporting the app's workflow.
L0557:     best_rows: List[List[str]] = []
    -> general Python statement supporting the app's workflow.
L0558:     best_score: float = -1.0
    -> general Python statement supporting the app's workflow.
L0559: 
    -> blank line (spacing/section separation).
L0560:     for _, df in book.items():
    -> loop (repeats logic across items).
L0561:         df = df.astype(str).fillna("")
    -> general Python statement supporting the app's workflow.
L0562:         headers = [str(c) for c in df.columns]
    -> general Python statement supporting the app's workflow.
L0563:         score = _score_headers(headers)
    -> general Python statement supporting the app's workflow.
L0564:         if score > best_score:
    -> control flow decision (branches logic based on conditions).
L0565:             best_score, best_headers, best_rows = score, headers, df.values.tolist()
    -> general Python statement supporting the app's workflow.
L0566: 
    -> blank line (spacing/section separation).
L0567:     return best_headers, best_rows
    -> returns a value from a function/method.
L0568: 
    -> blank line (spacing/section separation).
L0569: 
    -> blank line (spacing/section separation).
L0570: # --------------------------
    -> comment/doc note (helps humans; ignored by Python).
L0571: # Column detection / mapping
    -> comment/doc note (helps humans; ignored by Python).
L0572: # --------------------------
    -> comment/doc note (helps humans; ignored by Python).
L0573: 
    -> blank line (spacing/section separation).
L0574: ROLE_SYNONYMS = {
    -> general Python statement supporting the app's workflow.
L0575:     "Config Name": ["config name", "configname", "config_name", "cfg name", "cfgname", "cfg_name"],
    -> general Python statement supporting the app's workflow.
L0576:     "Config Key":  ["config key", "cfg key", "config_key", "cfg_key", "key", "identifier", "id"],
    -> general Python statement supporting the app's workflow.
L0577:     "CURRENT PAYLOAD": ["current payload", "current json", "new payload", "payload", "current", "new json", "json_pay...
    -> general Python statement supporting the app's workflow.
L0578:     "OLD PAYLOAD":     ["old payload", "old json", "previous payload", "previous json", "old"]
    -> general Python statement supporting the app's workflow.
L0579: }
    -> general Python statement supporting the app's workflow.
L0580: 
    -> blank line (spacing/section separation).
L0581: NEEDED_ROLES = ["Config Name", "Config Key", "CURRENT PAYLOAD", "OLD PAYLOAD"]
    -> general Python statement supporting the app's workflow.
L0582: 
    -> blank line (spacing/section separation).
L0583: def _header_confidence(header: str, role: str) -> float:
    -> starts a function definition (reusable logic).
L0584:     h = header.strip().lower()
    -> general Python statement supporting the app's workflow.
L0585:     if not h: return 0.0
    -> control flow decision (branches logic based on conditions).
L0586:     
    -> blank line (spacing/section separation).
L0587:     syns = ROLE_SYNONYMS.get(role, [])
    -> general Python statement supporting the app's workflow.
L0588:     direct_score = 0.0
    -> general Python statement supporting the app's workflow.
L0589:     for s in syns:
    -> loop (repeats logic across items).
L0590:         if h == s:
    -> control flow decision (branches logic based on conditions).
L0591:             return 1.0
    -> returns a value from a function/method.
L0592:         if s in h:
    -> control flow decision (branches logic based on conditions).
L0593:             direct_score = max(direct_score, 0.6 + (0.4 * len(s) / len(h)))
    -> general Python statement supporting the app's workflow.
L0594: 
    -> blank line (spacing/section separation).
L0595:     hint_score = 0.0
    -> general Python statement supporting the app's workflow.
L0596:     if role == "Config Key" and ("key" in h or "id" in h):
    -> control flow decision (branches logic based on conditions).
L0597:         hint_score = 0.5
    -> general Python statement supporting the app's workflow.
L0598:     if role == "Config Name" and "name" in h:
    -> control flow decision (branches logic based on conditions).
L0599:         hint_score = 0.5
    -> general Python statement supporting the app's workflow.
L0600:     if role.endswith("PAYLOAD") and ("payload" in h or "json" in h):
    -> control flow decision (branches logic based on conditions).
L0601:         hint_score = 0.6
    -> general Python statement supporting the app's workflow.
L0602:         if "current" in h and "CURRENT" in role: hint_score = 0.9
    -> control flow decision (branches logic based on conditions).
L0603:         if "new" in h and "CURRENT" in role:    hint_score = 0.8
    -> control flow decision (branches logic based on conditions).
L0604:         if "old" in h and "OLD" in role:        hint_score = 0.9
    -> control flow decision (branches logic based on conditions).
L0605: 
    -> blank line (spacing/section separation).
L0606:     return max(direct_score, hint_score)
    -> returns a value from a function/method.
L0607: 
    -> blank line (spacing/section separation).
L0608: 
    -> blank line (spacing/section separation).
L0609: def _score_headers(headers: List[str]) -> float:
    -> starts a function definition (reusable logic).
L0610:     return sum(max(_header_confidence(h, r) for h in headers) for r in NEEDED_ROLES)
    -> returns a value from a function/method.
L0611: 
    -> blank line (spacing/section separation).
L0612: 
    -> blank line (spacing/section separation).
L0613: def detect_best_columns(headers: List[str]) -> Tuple[Dict[str, int], Dict[str, float]]:
    -> starts a function definition (reusable logic).
L0614:     conf: Dict[str, float] = {}
    -> general Python statement supporting the app's workflow.
L0615:     mapping: Dict[str, int] = {}
    -> general Python statement supporting the app's workflow.
L0616:     used_indices = set()
    -> general Python statement supporting the app's workflow.
L0617: 
    -> blank line (spacing/section separation).
L0618:     for role in NEEDED_ROLES:
    -> loop (repeats logic across items).
L0619:         best_i, best_c = -1, -0.1
    -> general Python statement supporting the app's workflow.
L0620:         for i, h in enumerate(headers):
    -> loop (repeats logic across items).
L0621:             if i in used_indices:
    -> control flow decision (branches logic based on conditions).
L0622:                 continue
    -> general Python statement supporting the app's workflow.
L0623:             c = _header_confidence(h, role)
    -> general Python statement supporting the app's workflow.
L0624:             if c > best_c:
    -> control flow decision (branches logic based on conditions).
L0625:                 best_c, best_i = c, i
    -> general Python statement supporting the app's workflow.
L0626:         
    -> blank line (spacing/section separation).
L0627:         if best_i != -1 and best_c > 0.4:
    -> control flow decision (branches logic based on conditions).
L0628:             mapping[role] = best_i
    -> general Python statement supporting the app's workflow.
L0629:             conf[role] = best_c
    -> general Python statement supporting the app's workflow.
L0630:             used_indices.add(best_i)
    -> general Python statement supporting the app's workflow.
L0631:             
    -> blank line (spacing/section separation).
L0632:     return mapping, conf
    -> returns a value from a function/method.
L0633: 
    -> blank line (spacing/section separation).
L0634: 
    -> blank line (spacing/section separation).
L0635: def assemble_rows(headers: List[str], raw_rows: List[List[str]], mapping: Dict[str, int]) -> List[Dict[str, str]]:
    -> starts a function definition (reusable logic).
L0636:     """
    -> docstring delimiter (module/docs block).
L0637:     Uses pandas for vectorized dictionary creation if available.
    -> pandas data handling (read/transform tabular data).
L0638:     This is ~10x faster than list comprehension for 100k rows.
    -> general Python statement supporting the app's workflow.
L0639:     """
    -> docstring delimiter (module/docs block).
L0640:     col_indices = {role: mapping.get(role, -1) for role in NEEDED_ROLES}
    -> general Python statement supporting the app's workflow.
L0641: 
    -> blank line (spacing/section separation).
L0642:     if HAS_PANDAS:
    -> control flow decision (branches logic based on conditions).
L0643:         try:
    -> error handling block (keeps app stable under bad inputs).
L0644:             # Create DataFrame (fast C implementation)
    -> comment/doc note (helps humans; ignored by Python).
L0645:             df_raw = pd.DataFrame(raw_rows, columns=headers, dtype=str)
    -> pandas data handling (read/transform tabular data).
L0646: 
    -> blank line (spacing/section separation).
L0647:             # Identify columns to keep
    -> comment/doc note (helps humans; ignored by Python).
L0648:             idx_to_role = {v: k for k, v in col_indices.items() if v != -1}
    -> general Python statement supporting the app's workflow.
L0649:             valid_indices = list(idx_to_role.keys())
    -> general Python statement supporting the app's workflow.
L0650:             valid_headers = [headers[i] for i in valid_indices]
    -> general Python statement supporting the app's workflow.
L0651: 
    -> blank line (spacing/section separation).
L0652:             # Slice and Rename
    -> comment/doc note (helps humans; ignored by Python).
L0653:             df_subset = df_raw[valid_headers].copy()
    -> general Python statement supporting the app's workflow.
L0654:             # Columns map from index back to role name
    -> comment/doc note (helps humans; ignored by Python).
L0655:             df_subset.columns = [idx_to_role[i] for i in valid_indices]
    -> general Python statement supporting the app's workflow.
L0656: 
    -> blank line (spacing/section separation).
L0657:             # Fill missing columns with empty string
    -> comment/doc note (helps humans; ignored by Python).
L0658:             for role in NEEDED_ROLES:
    -> loop (repeats logic across items).
L0659:                 if role not in df_subset.columns:
    -> control flow decision (branches logic based on conditions).
L0660:                     df_subset[role] = ""
    -> general Python statement supporting the app's workflow.
L0661: 
    -> blank line (spacing/section separation).
L0662:             # Convert to list of dicts
    -> comment/doc note (helps humans; ignored by Python).
L0663:             return df_subset.to_dict('records')
    -> returns a value from a function/method.
L0664:         except Exception as e:
    -> error handling block (keeps app stable under bad inputs).
L0665:             logger.warning(f"Pandas assembly failed ({e}), falling back to Python loop.")
    -> general Python statement supporting the app's workflow.
L0666: 
    -> blank line (spacing/section separation).
L0667:     # Fallback: simple Python loop, lower peak memory but slower
    -> comment/doc note (helps humans; ignored by Python).
L0668:     idxs = [(role, col_indices[role]) for role in NEEDED_ROLES if col_indices[role] != -1]
    -> general Python statement supporting the app's workflow.
L0669:     rows: List[Dict[str, str]] = []
    -> general Python statement supporting the app's workflow.
L0670:     for raw in raw_rows:
    -> loop (repeats logic across items).
L0671:         row = {}
    -> general Python statement supporting the app's workflow.
L0672:         for role, i in idxs:
    -> loop (repeats logic across items).
L0673:             row[role] = raw[i] if 0 <= i < len(raw) else ""
    -> general Python statement supporting the app's workflow.
L0674:         rows.append(row)
    -> general Python statement supporting the app's workflow.
L0675:     return rows
    -> returns a value from a function/method.
L0676: 
    -> blank line (spacing/section separation).
L0677: 
    -> blank line (spacing/section separation).
L0678: # ----------------------------
    -> comment/doc note (helps humans; ignored by Python).
L0679: # Diff row structure / metadata
    -> comment/doc note (helps humans; ignored by Python).
L0680: # ----------------------------
    -> comment/doc note (helps humans; ignored by Python).
L0681: 
    -> blank line (spacing/section separation).
L0682: @dataclass
    -> general Python statement supporting the app's workflow.
L0683: class RowMeta:
    -> starts a class definition (bundles data + behavior).
L0684:     """
    -> docstring delimiter (module/docs block).
L0685:     REFINED: This is now memory-efficient.
    -> general Python statement supporting the app's workflow.
L0686:     It only stores the leaf values, not the full objects.
    -> general Python statement supporting the app's workflow.
L0687:     """
    -> docstring delimiter (module/docs block).
L0688:     cfgkey: str
    -> general Python statement supporting the app's workflow.
L0689:     typ: str
    -> general Python statement supporting the app's workflow.
L0690:     path: str
    -> general Python statement supporting the app's workflow.
L0691:     old: Any
    -> general Python statement supporting the app's workflow.
L0692:     new: Any
    -> general Python statement supporting the app's workflow.
L0693: 
    -> blank line (spacing/section separation).
L0694: 
    -> blank line (spacing/section separation).
L0695: # ========================================================================
    -> comment/doc note (helps humans; ignored by Python).
L0696: # MAIN APPLICATION CLASS
    -> comment/doc note (helps humans; ignored by Python).
L0697: # ========================================================================
    -> comment/doc note (helps humans; ignored by Python).
L0698: 
    -> blank line (spacing/section separation).
L0699: class PayloadDiffViewerApp(tk.Tk):
    -> starts a class definition (bundles data + behavior).
L0700:     def __init__(self):
    -> starts a function definition (reusable logic).
L0701:         super().__init__()
    -> general Python statement supporting the app's workflow.
L0702:         if not HAS_PANDAS:
    -> control flow decision (branches logic based on conditions).
L0703:              messagebox.showwarning(
    -> general Python statement supporting the app's workflow.
L0704:                  "Missing Library",
    -> general Python statement supporting the app's workflow.
L0705:                  "Pandas is not installed. Performance with large files will be "
    -> general Python statement supporting the app's workflow.
L0706:                  "significantly degraded.\n\nPlease install it via:\n"
    -> general Python statement supporting the app's workflow.
L0707:                  "pip install pandas numpy openpyxl"
    -> pandas data handling (read/transform tabular data).
L0708:              )
    -> general Python statement supporting the app's workflow.
L0709:         
    -> blank line (spacing/section separation).
L0710:         self.title("Payload Diff Viewer (Config Name -> Current vs Old)")
    -> general Python statement supporting the app's workflow.
L0711:         self.geometry(f"{config.WINDOW_W}x{config.WINDOW_H}")
    -> general Python statement supporting the app's workflow.
L0712:         self.minsize(config.MIN_W, config.MIN_H)
    -> general Python statement supporting the app's workflow.
L0713: 
    -> blank line (spacing/section separation).
L0714:         # Settings & paths
    -> comment/doc note (helps humans; ignored by Python).
L0715:         self.settings: Dict[str, Any] = {}
    -> general Python statement supporting the app's workflow.
L0716:         self._last_open_dir: Optional[str] = None
    -> general Python statement supporting the app's workflow.
L0717:         self._load_settings()
    -> general Python statement supporting the app's workflow.
L0718: 
    -> blank line (spacing/section separation).
L0719:         # State
    -> comment/doc note (helps humans; ignored by Python).
L0720:         self.rows: List[Dict[str, str]] = []
    -> general Python statement supporting the app's workflow.
L0721:         # Map Config Name -> list of integer indices into self.rows (memory friendly)
    -> comment/doc note (helps humans; ignored by Python).
L0722:         self.by_name: Dict[str, List[int]] = {}
    -> general Python statement supporting the app's workflow.
L0723:         self.parse_logger = ParseLogger()
    -> general Python statement supporting the app's workflow.
L0724:         
    -> blank line (spacing/section separation).
L0725:         # REFINED: Central cache for full payloads.
    -> comment/doc note (helps humans; ignored by Python).
L0726:         # Key: cfgkey, Value: (old_obj, new_obj)
    -> comment/doc note (helps humans; ignored by Python).
L0727:         self.full_payloads_cache: Dict[str, Tuple[Any, Any]] = {}
    -> general Python statement supporting the app's workflow.
L0728: 
    -> blank line (spacing/section separation).
L0729:         # Watch & filter
    -> comment/doc note (helps humans; ignored by Python).
L0730:         self.watchlist: List[str] = []
    -> general Python statement supporting the app's workflow.
L0731:         self.only_watch = tk.BooleanVar(value=False)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0732:         self.arrays_as_sets = tk.BooleanVar(value=False)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0733: 
    -> blank line (spacing/section separation).
L0734:         # UI bits
    -> comment/doc note (helps humans; ignored by Python).
L0735:         self._tree_meta: Dict[str, RowMeta] = {}
    -> general Python statement supporting the app's workflow.
L0736:         self._row_order: Dict[str, int] = {}
    -> general Python statement supporting the app's workflow.
L0737:         self.rows_to_compare_map: Dict[str, Dict[str, str]] = {}
    -> general Python statement supporting the app's workflow.
L0738:         self.search_var = tk.StringVar()
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0739:         self._scroll_sync_active = False
    -> general Python statement supporting the app's workflow.
L0740: 
    -> blank line (spacing/section separation).
L0741:         self._build_ui()
    -> general Python statement supporting the app's workflow.
L0742:         self._bind_shortcuts()
    -> general Python statement supporting the app's workflow.
L0743:         logger.info("Application started successfully.")
    -> general Python statement supporting the app's workflow.
L0744: 
    -> blank line (spacing/section separation).
L0745:     # ------------- Settings persistence -------------
    -> comment/doc note (helps humans; ignored by Python).
L0746: 
    -> blank line (spacing/section separation).
L0747:     def _load_settings(self):
    -> starts a function definition (reusable logic).
L0748:         path = config.SETTINGS_FILE
    -> general Python statement supporting the app's workflow.
L0749:         if not os.path.exists(path):
    -> control flow decision (branches logic based on conditions).
L0750:             try:
    -> error handling block (keeps app stable under bad inputs).
L0751:                 with open(path, 'w', encoding='utf-8') as f:
    -> general Python statement supporting the app's workflow.
L0752:                     json.dump({}, f, ensure_ascii=False, indent=2)
    -> general Python statement supporting the app's workflow.
L0753:             except Exception as e:
    -> error handling block (keeps app stable under bad inputs).
L0754:                 logger.warning(f"Failed to create settings file: {e}")
    -> general Python statement supporting the app's workflow.
L0755: 
    -> blank line (spacing/section separation).
L0756:         try:
    -> error handling block (keeps app stable under bad inputs).
L0757:             with open(path, 'r', encoding='utf-8') as f:
    -> general Python statement supporting the app's workflow.
L0758:                 self.settings = json.load(f) or {}
    -> general Python statement supporting the app's workflow.
L0759:         except Exception as e:
    -> error handling block (keeps app stable under bad inputs).
L0760:             logger.error(f"Failed to load settings: {e}")
    -> general Python statement supporting the app's workflow.
L0761:             self.settings = {}
    -> general Python statement supporting the app's workflow.
L0762: 
    -> blank line (spacing/section separation).
L0763:     def _save_settings(self):
    -> starts a function definition (reusable logic).
L0764:         try:
    -> error handling block (keeps app stable under bad inputs).
L0765:             with open(config.SETTINGS_FILE, 'w', encoding='utf-8') as f:
    -> general Python statement supporting the app's workflow.
L0766:                 json.dump(self.settings, f, ensure_ascii=False, indent=2)
    -> general Python statement supporting the app's workflow.
L0767:         except Exception as e:
    -> error handling block (keeps app stable under bad inputs).
L0768:             logger.error(f"Failed to save settings: {e}")
    -> general Python statement supporting the app's workflow.
L0769:             messagebox.showwarning("Settings", f"Failed to save settings:\n{e}")
    -> general Python statement supporting the app's workflow.
L0770: 
    -> blank line (spacing/section separation).
L0771:     def _get_initial_open_dir(self) -> Optional[str]:
    -> starts a function definition (reusable logic).
L0772:         d = self.settings.get('default_open_dir')
    -> general Python statement supporting the app's workflow.
L0773:         if d:
    -> control flow decision (branches logic based on conditions).
L0774:             if d.lower().startswith('http'):
    -> control flow decision (branches logic based on conditions).
L0775:                 unc = sharepoint_url_to_unc(d)
    -> general Python statement supporting the app's workflow.
L0776:                 if unc and os.path.isdir(unc):
    -> control flow decision (branches logic based on conditions).
L0777:                     return unc
    -> returns a value from a function/method.
L0778:             elif os.path.isdir(d):
    -> control flow decision (branches logic based on conditions).
L0779:                 return d
    -> returns a value from a function/method.
L0780:         if self._last_open_dir and os.path.isdir(self._last_open_dir):
    -> control flow decision (branches logic based on conditions).
L0781:             return self._last_open_dir
    -> returns a value from a function/method.
L0782:         return None
    -> returns a value from a function/method.
L0783: 
    -> blank line (spacing/section separation).
L0784:     def _set_default_folder(self):
    -> starts a function definition (reusable logic).
L0785:         initial = self._get_initial_open_dir() or os.path.expanduser('~')
    -> general Python statement supporting the app's workflow.
L0786:         folder = filedialog.askdirectory(title="Choose Default Open Folder", initialdir=initial)
    -> general Python statement supporting the app's workflow.
L0787:         if not folder:
    -> control flow decision (branches logic based on conditions).
L0788:             return
    -> returns a value from a function/method.
L0789:         try:
    -> error handling block (keeps app stable under bad inputs).
L0790:             self.settings['default_open_dir'] = folder
    -> general Python statement supporting the app's workflow.
L0791:             self._save_settings()
    -> general Python statement supporting the app's workflow.
L0792:             messagebox.showinfo("Default Folder", f"Default open folder set to:\n{folder}")
    -> general Python statement supporting the app's workflow.
L0793:         except Exception as e:
    -> error handling block (keeps app stable under bad inputs).
L0794:             messagebox.showerror("Default Folder", f"Failed to set default folder:\n{e}")
    -> general Python statement supporting the app's workflow.
L0795: 
    -> blank line (spacing/section separation).
L0796:     # ------------- UI --------------
    -> comment/doc note (helps humans; ignored by Python).
L0797: 
    -> blank line (spacing/section separation).
L0798:     def _build_ui(self):
    -> starts a function definition (reusable logic).
L0799:         menubar = tk.Menu(self)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0800: 
    -> blank line (spacing/section separation).
L0801:         filemenu = tk.Menu(menubar, tearoff=0)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0802:         filemenu.add_command(label="Open... (Ctrl+O)", command=self.on_open)
    -> general Python statement supporting the app's workflow.
L0803:         filemenu.add_separator()
    -> general Python statement supporting the app's workflow.
L0804:         filemenu.add_command(label="Set Default Folder...", command=self._set_default_folder)
    -> general Python statement supporting the app's workflow.
L0805:         filemenu.add_separator()
    -> general Python statement supporting the app's workflow.
L0806:         filemenu.add_command(label="Export CSV (Ctrl+S)", command=self.on_export_csv)
    -> general Python statement supporting the app's workflow.
L0807:         filemenu.add_command(label="Export TXT (Ctrl+E)", command=self.on_export_txt)
    -> general Python statement supporting the app's workflow.
L0808:         filemenu.add_separator()
    -> general Python statement supporting the app's workflow.
L0809:         filemenu.add_command(label="Exit", command=self.destroy)
    -> general Python statement supporting the app's workflow.
L0810:         menubar.add_cascade(label="File", menu=filemenu)
    -> general Python statement supporting the app's workflow.
L0811: 
    -> blank line (spacing/section separation).
L0812:         viewmenu = tk.Menu(menubar, tearoff=0)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0813:         viewmenu.add_command(label="Summary (Ctrl+M)", command=self.on_view_summary)
    -> general Python statement supporting the app's workflow.
L0814:         menubar.add_cascade(label="View", menu=viewmenu)
    -> general Python statement supporting the app's workflow.
L0815: 
    -> blank line (spacing/section separation).
L0816:         helpmenu = tk.Menu(menubar, tearoff=0)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0817:         helpmenu.add_command(label="Show Parse Log", command=lambda: self.parse_logger.show(self))
    -> general Python statement supporting the app's workflow.
L0818:         helpmenu.add_separator()
    -> general Python statement supporting the app's workflow.
L0819:         helpmenu.add_command(label="Keyboard Shortcuts", command=self.show_shortcuts_help)
    -> general Python statement supporting the app's workflow.
L0820:         menubar.add_cascade(label="Help", menu=helpmenu)
    -> general Python statement supporting the app's workflow.
L0821: 
    -> blank line (spacing/section separation).
L0822:         self.config(menu=menubar)
    -> general Python statement supporting the app's workflow.
L0823: 
    -> blank line (spacing/section separation).
L0824:         top = ttk.Frame(self)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0825:         top.pack(fill=tk.X, padx=10, pady=8)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0826: 
    -> blank line (spacing/section separation).
L0827:         ttk.Button(top, text='Open...', command=self.on_open).pack(side=tk.LEFT)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0828: 
    -> blank line (spacing/section separation).
L0829:         ttk.Label(top, text='Config Name:').pack(side=tk.LEFT, padx=(12, 4))
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0830:         self.cmb_name = ttk.Combobox(top, state='disabled', width=36)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0831:         self.cmb_name.pack(side=tk.LEFT)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0832:         self.cmb_name.bind('<<ComboboxSelected>>', self.on_name_selected)
    -> general Python statement supporting the app's workflow.
L0833: 
    -> blank line (spacing/section separation).
L0834:         ttk.Label(top, text='Config Keys:').pack(side=tk.LEFT, padx=(12, 4))
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0835:         self.lst_keys = tk.Listbox(top, selectmode=tk.EXTENDED, width=38, height=6, exportselection=False)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0836:         self.lst_keys.pack(side=tk.LEFT)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0837:         self.lst_keys.configure(state=tk.DISABLED)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0838: 
    -> blank line (spacing/section separation).
L0839:         btn_frame = ttk.Frame(top)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0840:         btn_frame.pack(side=tk.LEFT, padx=(12,0), fill=tk.Y)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0841:         self.btn_compare = ttk.Button(btn_frame, text='Compare (F5)', state='disabled', command=self.on_compare)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0842:         self.btn_compare.pack(pady=(0,2))
    -> general Python statement supporting the app's workflow.
L0843:         self.btn_clear = ttk.Button(btn_frame, text='Clear Results', state='disabled', command=self._reset_views)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0844:         self.btn_clear.pack()
    -> general Python statement supporting the app's workflow.
L0845: 
    -> blank line (spacing/section separation).
L0846:         self.btn_export_csv = ttk.Button(top, text='Export CSV', state='disabled', command=self.on_export_csv)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0847:         self.btn_export_csv.pack(side=tk.LEFT, padx=(6, 0))
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0848:         self.btn_export_txt = ttk.Button(top, text='Export TXT', state='disabled', command=self.on_export_txt)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0849:         self.btn_export_txt.pack(side=tk.LEFT, padx=(6, 0))
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0850: 
    -> blank line (spacing/section separation).
L0851:         self.lbl = ttk.Label(self, text='Open a CSV/Excel file to begin.')
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0852:         self.lbl.pack(anchor='w', padx=12)
    -> general Python statement supporting the app's workflow.
L0853: 
    -> blank line (spacing/section separation).
L0854:         opt = ttk.Frame(self)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0855:         opt.pack(fill=tk.X, padx=10, pady=(2, 6))
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0856: 
    -> blank line (spacing/section separation).
L0857:         ttk.Label(opt, text='Arrays:').pack(side=tk.LEFT)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0858:         ttk.Radiobutton(opt, text='by index', variable=self.arrays_as_sets, value=False, command=self.on_compare).pac...
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0859:         ttk.Radiobutton(opt, text='as set (ignore order)', variable=self.arrays_as_sets, value=True, command=self.on_...
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0860: 
    -> blank line (spacing/section separation).
L0861:         ttk.Label(opt, text='  Watch keys:').pack(side=tk.LEFT, padx=(14, 4))
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0862:         self.ent_watch = ttk.Entry(opt, width=64)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0863:         self.ent_watch.pack(side=tk.LEFT)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0864:         self.ent_watch.insert(0, config.DEFAULT_WATCHLIST)
    -> general Python statement supporting the app's workflow.
L0865:         ttk.Checkbutton(opt, text='Only watch', variable=self.only_watch, command=self._filter_tree).pack(side=tk.LEF...
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0866:         ttk.Button(opt, text='Apply', command=self.apply_watchlist).pack(side=tk.LEFT, padx=(8, 0))
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0867: 
    -> blank line (spacing/section separation).
L0868:         flt = ttk.Frame(self)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0869:         flt.pack(fill=tk.X, padx=10, pady=(0, 6))
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0870:         ttk.Label(flt, text='Filter:').pack(side=tk.LEFT)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0871:         self.filter_entry = ttk.Entry(flt, textvariable=self.search_var, width=40)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0872:         self.filter_entry.pack(side=tk.LEFT, padx=8)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0873:         ttk.Button(flt, text='Clear', command=lambda: self.search_var.set('')).pack(side=tk.LEFT)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0874:         self.search_var.trace_add('write', lambda *_: self._filter_tree())
    -> general Python statement supporting the app's workflow.
L0875: 
    -> blank line (spacing/section separation).
L0876:         self.v_changed = tk.StringVar(value='Changed: 0')
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0877:         self.v_added   = tk.StringVar(value='Added: 0')
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0878:         self.v_removed = tk.StringVar(value='Removed: 0')
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0879:         ttk.Label(flt, textvariable=self.v_changed, foreground='#7a5a00').pack(side=tk.LEFT, padx=(20, 12))
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0880:         ttk.Label(flt, textvariable=self.v_added, foreground='#096b00').pack(side=tk.LEFT, padx=(0, 12))
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0881:         ttk.Label(flt, textvariable=self.v_removed, foreground='#a00000').pack(side=tk.LEFT)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0882: 
    -> blank line (spacing/section separation).
L0883:         paned = ttk.PanedWindow(self, orient=tk.VERTICAL)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0884:         paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=(4, 10))
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0885: 
    -> blank line (spacing/section separation).
L0886:         # Top pane: field-level differences table
    -> comment/doc note (helps humans; ignored by Python).
L0887:         ftable = ttk.Frame(paned)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0888:         paned.add(ftable, weight=3)
    -> general Python statement supporting the app's workflow.
L0889: 
    -> blank line (spacing/section separation).
L0890:         self.tree = ttk.Treeview(ftable, columns=config.TREE_COLUMNS, show='headings', selectmode='browse')
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0891:         for c in config.TREE_COLUMNS:
    -> loop (repeats logic across items).
L0892:             self.tree.heading(c, text=c)
    -> general Python statement supporting the app's workflow.
L0893:             self.tree.column(c, width=config.TREE_WIDTHS[c], anchor='w')
    -> general Python statement supporting the app's workflow.
L0894:         vsb = ttk.Scrollbar(ftable, orient='vertical', command=self.tree.yview)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0895:         hsb = ttk.Scrollbar(ftable, orient='horizontal', command=self.tree.xview)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0896:         self.tree.configure(yscroll=vsb.set, xscroll=hsb.set)
    -> general Python statement supporting the app's workflow.
L0897:         self.tree.grid(row=0, column=0, sticky='nsew')
    -> general Python statement supporting the app's workflow.
L0898:         vsb.grid(row=0, column=1, sticky='ns')
    -> general Python statement supporting the app's workflow.
L0899:         hsb.grid(row=1, column=0, sticky='ew')
    -> general Python statement supporting the app's workflow.
L0900:         ftable.rowconfigure(0, weight=1)
    -> general Python statement supporting the app's workflow.
L0901:         ftable.columnconfigure(0, weight=1)
    -> general Python statement supporting the app's workflow.
L0902: 
    -> blank line (spacing/section separation).
L0903:         self.tree.tag_configure('changed', background=config.COLOR_CHANGED)
    -> general Python statement supporting the app's workflow.
L0904:         self.tree.tag_configure('added',   background=config.COLOR_ADDED)
    -> general Python statement supporting the app's workflow.
L0905:         self.tree.tag_configure('removed', background=config.COLOR_REMOVED)
    -> general Python statement supporting the app's workflow.
L0906: 
    -> blank line (spacing/section separation).
L0907:         default_font = tkfont.nametofont("TkDefaultFont")
    -> general Python statement supporting the app's workflow.
L0908:         bold_font = tkfont.Font(**default_font.configure())
    -> general Python statement supporting the app's workflow.
L0909:         bold_font.configure(weight='bold')
    -> general Python statement supporting the app's workflow.
L0910:         self.tree.tag_configure('watch', foreground='#0b5bb5', font=bold_font)
    -> general Python statement supporting the app's workflow.
L0911: 
    -> blank line (spacing/section separation).
L0912:         self.tree.bind('<<TreeviewSelect>>', self.on_tree_select)
    -> general Python statement supporting the app's workflow.
L0913: 
    -> blank line (spacing/section separation).
L0914:         # Enable copy-from-row on the top pane (Treeview)
    -> comment/doc note (helps humans; ignored by Python).
L0915:         self._setup_tree_copy_paste()
    -> general Python statement supporting the app's workflow.
L0916: 
    -> blank line (spacing/section separation).
L0917:         fmid = ttk.LabelFrame(paned, text='Selected Field - Inline Diff')
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0918:         paned.add(fmid, weight=1)
    -> general Python statement supporting the app's workflow.
L0919: 
    -> blank line (spacing/section separation).
L0920:         left = ttk.Frame(fmid)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0921:         left.grid(row=1, column=0, sticky='nsew', padx=(0, 6))
    -> general Python statement supporting the app's workflow.
L0922:         right = ttk.Frame(fmid)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0923:         right.grid(row=1, column=1, sticky='nsew', padx=(6, 0))
    -> general Python statement supporting the app's workflow.
L0924:         fmid.columnconfigure(0, weight=1)
    -> general Python statement supporting the app's workflow.
L0925:         fmid.columnconfigure(1, weight=1)
    -> general Python statement supporting the app's workflow.
L0926:         fmid.rowconfigure(1, weight=1)
    -> general Python statement supporting the app's workflow.
L0927: 
    -> blank line (spacing/section separation).
L0928:         ttk.Label(left, text='OLD').pack(anchor='w')
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0929:         self.txt_sel_old = tk.Text(left, wrap='word', height=config.INLINE_ROWS, font=("Courier New", 9))
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0930:         self.txt_sel_old.pack(fill=tk.BOTH, expand=True)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0931:         self.txt_sel_old.tag_configure('del', background='#ffcccc')
    -> general Python statement supporting the app's workflow.
L0932: 
    -> blank line (spacing/section separation).
L0933:         ttk.Label(right, text='CURRENT').pack(anchor='w')
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0934:         self.txt_sel_new = tk.Text(right, wrap='word', height=config.INLINE_ROWS, font=("Courier New", 9))
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0935:         self.txt_sel_new.pack(fill=tk.BOTH, expand=True)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0936:         self.txt_sel_new.tag_configure('add', background='#c2f0c2')
    -> general Python statement supporting the app's workflow.
L0937: 
    -> blank line (spacing/section separation).
L0938:         fbot = ttk.Frame(paned)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0939:         paned.add(fbot, weight=2)
    -> general Python statement supporting the app's workflow.
L0940: 
    -> blank line (spacing/section separation).
L0941:         jl = ttk.LabelFrame(fbot, text='OLD Payload (Full JSON)')
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0942:         jl.grid(row=0, column=0, sticky='nsew', padx=(0, 5))
    -> general Python statement supporting the app's workflow.
L0943:         jr = ttk.LabelFrame(fbot, text='CURRENT Payload (Full JSON)')
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0944:         jr.grid(row=0, column=1, sticky='nsew', padx=(5, 0))
    -> general Python statement supporting the app's workflow.
L0945:         fbot.columnconfigure(0, weight=1)
    -> general Python statement supporting the app's workflow.
L0946:         fbot.columnconfigure(1, weight=1)
    -> general Python statement supporting the app's workflow.
L0947:         fbot.rowconfigure(0, weight=1)
    -> general Python statement supporting the app's workflow.
L0948: 
    -> blank line (spacing/section separation).
L0949:         self.txt_old = tk.Text(jl, wrap='none', font=("Courier New", 9))
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0950:         self.txt_cur = tk.Text(jr, wrap='none', font=("Courier New", 9))
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0951: 
    -> blank line (spacing/section separation).
L0952:         self.sc_old_y = ttk.Scrollbar(jl, orient='vertical')
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0953:         self.sc_old_x = ttk.Scrollbar(jl, orient='horizontal')
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0954:         self.sc_cur_y = ttk.Scrollbar(jr, orient='vertical')
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0955:         self.sc_cur_x = ttk.Scrollbar(jr, orient='horizontal')
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0956: 
    -> blank line (spacing/section separation).
L0957:         self.txt_old.pack(fill=tk.BOTH, expand=True)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0958:         self.sc_old_y.pack(side=tk.RIGHT, fill=tk.Y)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0959:         self.sc_old_x.pack(side=tk.BOTTOM, fill=tk.X)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0960: 
    -> blank line (spacing/section separation).
L0961:         self.txt_cur.pack(fill=tk.BOTH, expand=True)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0962:         self.sc_cur_y.pack(side=tk.RIGHT, fill=tk.Y)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0963:         self.sc_cur_x.pack(side=tk.BOTTOM, fill=tk.X)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L0964: 
    -> blank line (spacing/section separation).
L0965:         self.txt_old.configure(xscrollcommand=self.sc_old_x.set)
    -> general Python statement supporting the app's workflow.
L0966:         self.txt_cur.configure(xscrollcommand=self.sc_cur_x.set)
    -> general Python statement supporting the app's workflow.
L0967:         self.sc_old_x.configure(command=self.txt_old.xview)
    -> general Python statement supporting the app's workflow.
L0968:         self.sc_cur_x.configure(command=self.txt_cur.xview)
    -> general Python statement supporting the app's workflow.
L0969: 
    -> blank line (spacing/section separation).
L0970:         self.txt_old.configure(
    -> general Python statement supporting the app's workflow.
L0971:             yscrollcommand=lambda first, last: self._on_yscroll(self.txt_old, self.txt_cur,
    -> general Python statement supporting the app's workflow.
L0972:                                                                 self.sc_old_y, self.sc_cur_y, first, last)
    -> general Python statement supporting the app's workflow.
L0973:         )
    -> general Python statement supporting the app's workflow.
L0974:         self.txt_cur.configure(
    -> general Python statement supporting the app's workflow.
L0975:             yscrollcommand=lambda first, last: self._on_yscroll(self.txt_cur, self.txt_old,
    -> general Python statement supporting the app's workflow.
L0976:                                                                 self.sc_cur_y, self.sc_old_y, first, last)
    -> general Python statement supporting the app's workflow.
L0977:         )
    -> general Python statement supporting the app's workflow.
L0978: 
    -> blank line (spacing/section separation).
L0979:         self.sc_old_y.configure(
    -> general Python statement supporting the app's workflow.
L0980:             command=lambda *args: self._on_scrollbar_y(self.txt_old, self.txt_cur,
    -> general Python statement supporting the app's workflow.
L0981:                                                        self.sc_old_y, self.sc_cur_y, *args)
    -> general Python statement supporting the app's workflow.
L0982:         )
    -> general Python statement supporting the app's workflow.
L0983:         self.sc_cur_y.configure(
    -> general Python statement supporting the app's workflow.
L0984:             command=lambda *args: self._on_scrollbar_y(self.txt_cur, self.txt_old,
    -> general Python statement supporting the app's workflow.
L0985:                                                        self.sc_cur_y, self.sc_old_y, *args)
    -> general Python statement supporting the app's workflow.
L0986:         )
    -> general Python statement supporting the app's workflow.
L0987: 
    -> blank line (spacing/section separation).
L0988:         # Make inline and JSON panes read-only but copyable
    -> comment/doc note (helps humans; ignored by Python).
L0989:         self._make_text_readonly_copy(self.txt_sel_old)
    -> general Python statement supporting the app's workflow.
L0990:         self._make_text_readonly_copy(self.txt_sel_new)
    -> general Python statement supporting the app's workflow.
L0991:         self._make_text_readonly_copy(self.txt_old)
    -> general Python statement supporting the app's workflow.
L0992:         self._make_text_readonly_copy(self.txt_cur)
    -> general Python statement supporting the app's workflow.
L0993: 
    -> blank line (spacing/section separation).
L0994: 
    -> blank line (spacing/section separation).
L0995:     def _make_text_readonly_copy(self, widget: tk.Text):
    -> starts a function definition (reusable logic).
L0996:         """
    -> docstring delimiter (module/docs block).
L0997:         Make a Text widget behave like a read-only viewer: content cannot be
    -> general Python statement supporting the app's workflow.
L0998:         changed by the user, but they can still select and copy text out.
    -> general Python statement supporting the app's workflow.
L0999:         """
    -> docstring delimiter (module/docs block).
L1000:         menu = tk.Menu(widget, tearoff=False)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L1001: 
    -> blank line (spacing/section separation).
L1002:         def do_copy(event=None):
    -> starts a function definition (reusable logic).
L1003:             try:
    -> error handling block (keeps app stable under bad inputs).
L1004:                 text = widget.get("sel.first", "sel.last")
    -> general Python statement supporting the app's workflow.
L1005:             except tk.TclError:
    -> Tkinter UI widget / layout statement (creates or configures UI).
L1006:                 text = ""
    -> general Python statement supporting the app's workflow.
L1007:             if text:
    -> control flow decision (branches logic based on conditions).
L1008:                 root = widget.winfo_toplevel()
    -> general Python statement supporting the app's workflow.
L1009:                 try:
    -> error handling block (keeps app stable under bad inputs).
L1010:                     root.clipboard_clear()
    -> general Python statement supporting the app's workflow.
L1011:                 except tk.TclError:
    -> Tkinter UI widget / layout statement (creates or configures UI).
L1012:                     pass
    -> general Python statement supporting the app's workflow.
L1013:                 root.clipboard_append(text)
    -> general Python statement supporting the app's workflow.
L1014:             return "break"
    -> returns a value from a function/method.
L1015: 
    -> blank line (spacing/section separation).
L1016:         def do_select_all(event=None):
    -> starts a function definition (reusable logic).
L1017:             widget.tag_add("sel", "1.0", "end-1c")
    -> general Python statement supporting the app's workflow.
L1018:             return "break"
    -> returns a value from a function/method.
L1019: 
    -> blank line (spacing/section separation).
L1020:         # Right-click menu with Copy / Select All only
    -> comment/doc note (helps humans; ignored by Python).
L1021:         menu.add_command(label="Copy", command=do_copy)
    -> general Python statement supporting the app's workflow.
L1022:         menu.add_command(label="Select All", command=do_select_all)
    -> general Python statement supporting the app's workflow.
L1023: 
    -> blank line (spacing/section separation).
L1024:         def popup(event):
    -> starts a function definition (reusable logic).
L1025:             try:
    -> error handling block (keeps app stable under bad inputs).
L1026:                 menu.tk_popup(event.x_root, event.y_root)
    -> general Python statement supporting the app's workflow.
L1027:             finally:
    -> error handling block (keeps app stable under bad inputs).
L1028:                 menu.grab_release()
    -> general Python statement supporting the app's workflow.
L1029: 
    -> blank line (spacing/section separation).
L1030:         widget.bind("<Button-3>", popup)
    -> general Python statement supporting the app's workflow.
L1031: 
    -> blank line (spacing/section separation).
L1032:         # Allow Ctrl+A / Ctrl+C, but block any edits (typing, delete, paste)
    -> comment/doc note (helps humans; ignored by Python).
L1033:         widget.bind("<Control-a>", do_select_all)
    -> general Python statement supporting the app's workflow.
L1034:         widget.bind("<Control-A>", do_select_all)
    -> general Python statement supporting the app's workflow.
L1035:         widget.bind("<Control-c>", do_copy)
    -> general Python statement supporting the app's workflow.
L1036:         widget.bind("<Control-C>", do_copy)
    -> general Python statement supporting the app's workflow.
L1037: 
    -> blank line (spacing/section separation).
L1038:         def block_edit(event=None):
    -> starts a function definition (reusable logic).
L1039:             return "break"
    -> returns a value from a function/method.
L1040: 
    -> blank line (spacing/section separation).
L1041:         for seq in ("<BackSpace>", "<Delete>",
    -> loop (repeats logic across items).
L1042:                     "<Control-v>", "<Control-V>",
    -> general Python statement supporting the app's workflow.
L1043:                     "<Control-x>", "<Control-X>",
    -> general Python statement supporting the app's workflow.
L1044:                     "<Return>", "<Tab>"):
    -> general Python statement supporting the app's workflow.
L1045:             widget.bind(seq, block_edit)
    -> general Python statement supporting the app's workflow.
L1046: 
    -> blank line (spacing/section separation).
L1047:         def on_key(event):
    -> starts a function definition (reusable logic).
L1048:             # Allow navigation keys
    -> comment/doc note (helps humans; ignored by Python).
L1049:             if event.keysym in ("Left", "Right", "Up", "Down",
    -> control flow decision (branches logic based on conditions).
L1050:                                 "Home", "End", "Prior", "Next"):
    -> general Python statement supporting the app's workflow.
L1051:                 return
    -> returns a value from a function/method.
L1052:             # Allow copy/select-all combos (handled above)
    -> comment/doc note (helps humans; ignored by Python).
L1053:             if (event.state & 0x4) and event.keysym in ("c", "C", "a", "A"):
    -> control flow decision (branches logic based on conditions).
L1054:                 return
    -> returns a value from a function/method.
L1055:             # Block everything else that could change content
    -> comment/doc note (helps humans; ignored by Python).
L1056:             if event.char:
    -> control flow decision (branches logic based on conditions).
L1057:                 return "break"
    -> returns a value from a function/method.
L1058:             return
    -> returns a value from a function/method.
L1059: 
    -> blank line (spacing/section separation).
L1060:         widget.bind("<Key>", on_key)
    -> general Python statement supporting the app's workflow.
L1061: 
    -> blank line (spacing/section separation).
L1062:     def _setup_tree_copy_paste(self):
    -> starts a function definition (reusable logic).
L1063:         """
    -> docstring delimiter (module/docs block).
L1064:         Add a simple 'Copy row' capability to the main Treeview so that the
    -> general Python statement supporting the app's workflow.
L1065:         selected row can be copied and pasted into other tools.
    -> general Python statement supporting the app's workflow.
L1066:         """
    -> docstring delimiter (module/docs block).
L1067:         tree = self.tree
    -> general Python statement supporting the app's workflow.
L1068:         menu = tk.Menu(tree, tearoff=False)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L1069: 
    -> blank line (spacing/section separation).
L1070:         def do_copy_row(event=None):
    -> starts a function definition (reusable logic).
L1071:             item = tree.focus()
    -> general Python statement supporting the app's workflow.
L1072:             if not item:
    -> control flow decision (branches logic based on conditions).
L1073:                 sel = tree.selection()
    -> general Python statement supporting the app's workflow.
L1074:                 if not sel:
    -> control flow decision (branches logic based on conditions).
L1075:                     return "break"
    -> returns a value from a function/method.
L1076:                 item = sel[0]
    -> general Python statement supporting the app's workflow.
L1077:             vals = list(tree.item(item, "values"))
    -> general Python statement supporting the app's workflow.
L1078:             text = "\t".join(str(v) for v in vals)
    -> general Python statement supporting the app's workflow.
L1079:             root = tree.winfo_toplevel()
    -> general Python statement supporting the app's workflow.
L1080:             try:
    -> error handling block (keeps app stable under bad inputs).
L1081:                 root.clipboard_clear()
    -> general Python statement supporting the app's workflow.
L1082:             except tk.TclError:
    -> Tkinter UI widget / layout statement (creates or configures UI).
L1083:                 pass
    -> general Python statement supporting the app's workflow.
L1084:             root.clipboard_append(text)
    -> general Python statement supporting the app's workflow.
L1085:             return "break"
    -> returns a value from a function/method.
L1086: 
    -> blank line (spacing/section separation).
L1087:         menu.add_command(label="Copy row", command=do_copy_row)
    -> general Python statement supporting the app's workflow.
L1088: 
    -> blank line (spacing/section separation).
L1089:         def popup(event):
    -> starts a function definition (reusable logic).
L1090:             # Focus the row under the cursor before showing the menu
    -> comment/doc note (helps humans; ignored by Python).
L1091:             item = tree.identify_row(event.y)
    -> general Python statement supporting the app's workflow.
L1092:             if item:
    -> control flow decision (branches logic based on conditions).
L1093:                 tree.selection_set(item)
    -> general Python statement supporting the app's workflow.
L1094:                 tree.focus(item)
    -> general Python statement supporting the app's workflow.
L1095:             try:
    -> error handling block (keeps app stable under bad inputs).
L1096:                 menu.tk_popup(event.x_root, event.y_root)
    -> general Python statement supporting the app's workflow.
L1097:             finally:
    -> error handling block (keeps app stable under bad inputs).
L1098:                 menu.grab_release()
    -> general Python statement supporting the app's workflow.
L1099: 
    -> blank line (spacing/section separation).
L1100:         tree.bind("<Button-3>", popup)
    -> general Python statement supporting the app's workflow.
L1101:         tree.bind("<Control-c>", do_copy_row)
    -> general Python statement supporting the app's workflow.
L1102:         tree.bind("<Control-C>", do_copy_row)
    -> general Python statement supporting the app's workflow.
L1103: 
    -> blank line (spacing/section separation).
L1104:     def _bind_shortcuts(self):
    -> starts a function definition (reusable logic).
L1105:         self.bind_all('<Control-o>', lambda e: self.on_open())
    -> general Python statement supporting the app's workflow.
L1106:         self.bind_all('<Control-s>', lambda e: self.on_export_csv())
    -> general Python statement supporting the app's workflow.
L1107:         self.bind_all('<Control-e>', lambda e: self.on_export_txt())
    -> general Python statement supporting the app's workflow.
L1108:         self.bind_all('<Control-f>', lambda e: (self.filter_entry.focus_set(), self.filter_entry.select_range(0, tk.E...
    -> Tkinter UI widget / layout statement (creates or configures UI).
L1109:         self.bind_all('<Control-m>', lambda e: self.on_view_summary())
    -> general Python statement supporting the app's workflow.
L1110:         self.bind_all('<F5>', lambda e: self.on_compare())
    -> general Python statement supporting the app's workflow.
L1111:         self.bind_all('<Escape>', lambda e: self.focus_set())
    -> general Python statement supporting the app's workflow.
L1112: 
    -> blank line (spacing/section separation).
L1113:     # ------------- Actions -------------
    -> comment/doc note (helps humans; ignored by Python).
L1114: 
    -> blank line (spacing/section separation).
L1115:     def _validate_file(self, path: str) -> Tuple[bool, str]:
    -> starts a function definition (reusable logic).
L1116:         if not os.path.exists(path):
    -> control flow decision (branches logic based on conditions).
L1117:             return False, "File not found."
    -> returns a value from a function/method.
L1118:         ext = os.path.splitext(path)[1].lower()
    -> general Python statement supporting the app's workflow.
L1119:         if ext not in ('.csv', '.tsv', '.txt', '.xlsx', '.xls'):
    -> control flow decision (branches logic based on conditions).
L1120:             return False, f"Unsupported file type: {ext}"
    -> returns a value from a function/method.
L1121:         try:
    -> error handling block (keeps app stable under bad inputs).
L1122:             size_mb = os.path.getsize(path) / (1024 * 1024)
    -> general Python statement supporting the app's workflow.
L1123:             if size_mb > 1024:
    -> control flow decision (branches logic based on conditions).
L1124:                 return False, f"File is too large ({size_mb:.1f} MB)."
    -> returns a value from a function/method.
L1125:         except OSError as e:
    -> error handling block (keeps app stable under bad inputs).
L1126:             return False, f"Cannot access file: {e}"
    -> returns a value from a function/method.
L1127:         return True, ""
    -> returns a value from a function/method.
L1128: 
    -> blank line (spacing/section separation).
L1129:     def on_open(self):
    -> starts a function definition (reusable logic).
L1130:         p = filedialog.askopenfilename(
    -> general Python statement supporting the app's workflow.
L1131:             title="Select CSV/TSV/TXT/XLSX/XLS",
    -> general Python statement supporting the app's workflow.
L1132:             initialdir=self._get_initial_open_dir(),
    -> general Python statement supporting the app's workflow.
L1133:             filetypes=[
    -> general Python statement supporting the app's workflow.
L1134:                 ("All supported", "*.csv *.tsv *.txt *.xlsx *.xls"),
    -> general Python statement supporting the app's workflow.
L1135:                 ("Excel", "*.xlsx *.xls"),
    -> general Python statement supporting the app's workflow.
L1136:                 ("CSV/TSV/TXT", "*.csv *.tsv *.txt"),
    -> general Python statement supporting the app's workflow.
L1137:                 ("All files", "*.*"),
    -> general Python statement supporting the app's workflow.
L1138:             ]
    -> general Python statement supporting the app's workflow.
L1139:         )
    -> general Python statement supporting the app's workflow.
L1140:         if not p:
    -> control flow decision (branches logic based on conditions).
L1141:             return
    -> returns a value from a function/method.
L1142: 
    -> blank line (spacing/section separation).
L1143:         self._last_open_dir = os.path.dirname(p) or self._last_open_dir
    -> general Python statement supporting the app's workflow.
L1144: 
    -> blank line (spacing/section separation).
L1145:         ok, why = self._validate_file(p)
    -> general Python statement supporting the app's workflow.
L1146:         if not ok:
    -> control flow decision (branches logic based on conditions).
L1147:             messagebox.showerror("File Error", why)
    -> general Python statement supporting the app's workflow.
L1148:             return
    -> returns a value from a function/method.
L1149: 
    -> blank line (spacing/section separation).
L1150:         ext = os.path.splitext(p)[1].lower()
    -> general Python statement supporting the app's workflow.
L1151:         use_chunked = HAS_PANDAS and (ext in ('.csv', '.tsv', '.txt') or (ext in ('.xlsx', '.xls') and HAS_ULTRA_LOAD...
    -> general Python statement supporting the app's workflow.
L1152: 
    -> blank line (spacing/section separation).
L1153:         def load_task(progress_cb=None):
    -> starts a function definition (reusable logic).
L1154:             if ext in ('.csv', '.tsv', '.txt'):
    -> control flow decision (branches logic based on conditions).
L1155:                 return _load_csv_like_headers_rows_chunked(p, chunk_size=config.CSV_CHUNK_SIZE, progress_cb=progress_...
    -> returns a value from a function/method.
L1156:             elif ext in ('.xlsx', '.xls'):
    -> control flow decision (branches logic based on conditions).
L1157:                 try:
    -> error handling block (keeps app stable under bad inputs).
L1158:                     return _excel_headers_rows(p, progress_cb=progress_cb)
    -> returns a value from a function/method.
L1159:                 except Exception as e:
    -> error handling block (keeps app stable under bad inputs).
L1160:                     raise
    -> general Python statement supporting the app's workflow.
L1161:             raise ValueError("Unsupported file type should have been caught earlier.")
    -> general Python statement supporting the app's workflow.
L1162: 
    -> blank line (spacing/section separation).
L1163:         def on_loaded(result):
    -> starts a function definition (reusable logic).
L1164:             """
    -> docstring delimiter (module/docs block).
L1165:             REFINED: This function now forces the column confirmation dialog
    -> general Python statement supporting the app's workflow.
L1166:             if any mapping is missing OR has low confidence (< 70%).
    -> control flow decision (branches logic based on conditions).
L1167:             """
    -> docstring delimiter (module/docs block).
L1168:             headers, raw_rows = result
    -> general Python statement supporting the app's workflow.
L1169:             if not headers or not raw_rows:
    -> control flow decision (branches logic based on conditions).
L1170:                 messagebox.showwarning('No Data', 'File appears to be empty or has no data rows.')
    -> general Python statement supporting the app's workflow.
L1171:                 return
    -> returns a value from a function/method.
L1172: 
    -> blank line (spacing/section separation).
L1173:             mapping, conf = detect_best_columns(headers)
    -> general Python statement supporting the app's workflow.
L1174:             
    -> blank line (spacing/section separation).
L1175:             # --- REFINED LOGIC ---
    -> comment/doc note (helps humans; ignored by Python).
L1176:             missing = [r for r in NEEDED_ROLES if r not in mapping]
    -> general Python statement supporting the app's workflow.
L1177:             # Check for any confidence score below 0.7 (i.e., not a strong match)
    -> comment/doc note (helps humans; ignored by Python).
L1178:             low_confidence = [r for r, c in conf.items() if c < 0.7] 
    -> general Python statement supporting the app's workflow.
L1179:             
    -> blank line (spacing/section separation).
L1180:             # Show dialog if anything is missing OR if any mapping is low confidence
    -> comment/doc note (helps humans; ignored by Python).
L1181:             if missing or low_confidence:
    -> control flow decision (branches logic based on conditions).
L1182:                 logger.warning(f"Column mapping needs confirmation. Missing: {missing}, Low Confidence: {low_confiden...
    -> general Python statement supporting the app's workflow.
L1183:                 mapping2 = self._confirm_column_mapping(headers, mapping, conf)
    -> general Python statement supporting the app's workflow.
L1184:                 if not mapping2:
    -> control flow decision (branches logic based on conditions).
L1185:                     messagebox.showinfo("Cancelled", "Column mapping was not confirmed.")
    -> general Python statement supporting the app's workflow.
L1186:                     return
    -> returns a value from a function/method.
L1187:                 mapping = mapping2
    -> general Python statement supporting the app's workflow.
L1188:             # --- END REFINED LOGIC ---
    -> comment/doc note (helps humans; ignored by Python).
L1189: 
    -> blank line (spacing/section separation).
L1190:             self.rows = assemble_rows(headers, raw_rows, mapping)
    -> general Python statement supporting the app's workflow.
L1191:             self._finalize_load()
    -> general Python statement supporting the app's workflow.
L1192: 
    -> blank line (spacing/section separation).
L1193: 
    -> blank line (spacing/section separation).
L1194:         self._with_progress_threaded(
    -> general Python statement supporting the app's workflow.
L1195:             load_task,
    -> general Python statement supporting the app's workflow.
L1196:             title=("Loading large file..." if use_chunked else "Loading file..."),
    -> general Python statement supporting the app's workflow.
L1197:             done_cb=on_loaded,
    -> general Python statement supporting the app's workflow.
L1198:             determinate=use_chunked
    -> general Python statement supporting the app's workflow.
L1199:         )
    -> general Python statement supporting the app's workflow.
L1200: 
    -> blank line (spacing/section separation).
L1201:     def _finalize_load(self):
    -> starts a function definition (reusable logic).
L1202:         self.by_name.clear()
    -> general Python statement supporting the app's workflow.
L1203:         self.parse_logger = ParseLogger()
    -> general Python statement supporting the app's workflow.
L1204:         invalid_names_found = set()
    -> general Python statement supporting the app's workflow.
L1205: 
    -> blank line (spacing/section separation).
L1206:         # Build an index from Config Name -> list of row indices
    -> comment/doc note (helps humans; ignored by Python).
L1207:         for idx, r in enumerate(self.rows):
    -> loop (repeats logic across items).
L1208:             nm = (r.get('Config Name') or '').strip()
    -> general Python statement supporting the app's workflow.
L1209: 
    -> blank line (spacing/section separation).
L1210:             if config.validate_config_name(nm):
    -> control flow decision (branches logic based on conditions).
L1211:                 self.by_name.setdefault(nm, []).append(idx)
    -> general Python statement supporting the app's workflow.
L1212:             elif nm and nm not in invalid_names_found:
    -> control flow decision (branches logic based on conditions).
L1213:                 msg = f"Skipped invalid Config Name: '{nm}'"
    -> general Python statement supporting the app's workflow.
L1214:                 ctx = "Config Names must be alphanumeric + underscore (A-Z, a-z, 0-9, _)."
    -> general Python statement supporting the app's workflow.
L1215:                 logger.info(f"{msg} - {ctx}")
    -> general Python statement supporting the app's workflow.
L1216:                 self.parse_logger.log(msg, level='info', context=ctx)
    -> general Python statement supporting the app's workflow.
L1217:                 invalid_names_found.add(nm)
    -> general Python statement supporting the app's workflow.
L1218: 
    -> blank line (spacing/section separation).
L1219:         names = sorted(self.by_name.keys())
    -> general Python statement supporting the app's workflow.
L1220:         self.cmb_name.configure(state='readonly', values=names)
    -> general Python statement supporting the app's workflow.
L1221:         self.cmb_name.set('')
    -> general Python statement supporting the app's workflow.
L1222:         self.lst_keys.delete(0, tk.END)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L1223:         self.lst_keys.configure(state=tk.DISABLED)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L1224: 
    -> blank line (spacing/section separation).
L1225:         self.lbl.configure(
    -> general Python statement supporting the app's workflow.
L1226:             text=(
    -> general Python statement supporting the app's workflow.
L1227:                 f"Loaded {len(self.rows):,} rows. "
    -> general Python statement supporting the app's workflow.
L1228:                 f"{len(invalid_names_found)} invalid Config Name(s) skipped. "
    -> general Python statement supporting the app's workflow.
L1229:                 "Select a Config Name."
    -> general Python statement supporting the app's workflow.
L1230:             )
    -> general Python statement supporting the app's workflow.
L1231:         )
    -> general Python statement supporting the app's workflow.
L1232: 
    -> blank line (spacing/section separation).
L1233:         self._reset_views()
    -> general Python statement supporting the app's workflow.
L1234:         logger.info(
    -> general Python statement supporting the app's workflow.
L1235:             "File loaded. %d valid config names found. %d invalid names skipped.",
    -> general Python statement supporting the app's workflow.
L1236:             len(self.by_name),
    -> general Python statement supporting the app's workflow.
L1237:             len(invalid_names_found),
    -> general Python statement supporting the app's workflow.
L1238:         )
    -> general Python statement supporting the app's workflow.
L1239: 
    -> blank line (spacing/section separation).
L1240:         # Encourage Python to free any large temporary objects early
    -> comment/doc note (helps humans; ignored by Python).
L1241:         gc.collect()
    -> general Python statement supporting the app's workflow.
L1242: 
    -> blank line (spacing/section separation).
L1243:     def on_name_selected(self, _evt=None):
    -> starts a function definition (reusable logic).
L1244:         n = self.cmb_name.get().strip()
    -> general Python statement supporting the app's workflow.
L1245:         self._reset_views(clear_keys=False)
    -> general Python statement supporting the app's workflow.
L1246:         self.btn_compare.configure(state='disabled')
    -> general Python statement supporting the app's workflow.
L1247: 
    -> blank line (spacing/section separation).
L1248:         self.lst_keys.delete(0, tk.END)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L1249:         if not n:
    -> control flow decision (branches logic based on conditions).
L1250:             self.lst_keys.configure(state=tk.DISABLED)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L1251:             return
    -> returns a value from a function/method.
L1252: 
    -> blank line (spacing/section separation).
L1253:         # Look up row indices for this Config Name
    -> comment/doc note (helps humans; ignored by Python).
L1254:         indices = self.by_name.get(n, [])
    -> general Python statement supporting the app's workflow.
L1255:         # Build display keys and keep a display->raw mapping for matching later
    -> comment/doc note (helps humans; ignored by Python).
L1256:         self.display_to_raw = {}
    -> general Python statement supporting the app's workflow.
L1257:         disp_keys = set()
    -> general Python statement supporting the app's workflow.
L1258:         for i in indices:
    -> loop (repeats logic across items).
L1259:             raw = (self.rows[i].get('Config Key', '') or '').strip()
    -> general Python statement supporting the app's workflow.
L1260:             if not raw:
    -> control flow decision (branches logic based on conditions).
L1261:                 continue
    -> general Python statement supporting the app's workflow.
L1262:             disp = self._format_key(raw)
    -> general Python statement supporting the app's workflow.
L1263:             if disp not in self.display_to_raw:
    -> control flow decision (branches logic based on conditions).
L1264:                 self.display_to_raw[disp] = raw
    -> general Python statement supporting the app's workflow.
L1265:             disp_keys.add(disp)
    -> general Python statement supporting the app's workflow.
L1266:         keys = sorted(disp_keys)
    -> general Python statement supporting the app's workflow.
L1267: 
    -> blank line (spacing/section separation).
L1268:         for k in keys:
    -> loop (repeats logic across items).
L1269:             self.lst_keys.insert(tk.END, k)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L1270: 
    -> blank line (spacing/section separation).
L1271:         if keys:
    -> control flow decision (branches logic based on conditions).
L1272:             self.lst_keys.configure(state=tk.NORMAL)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L1273:             self.lst_keys.select_set(0, tk.END)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L1274:             self.btn_compare.configure(state='normal')
    -> general Python statement supporting the app's workflow.
L1275: 
    -> blank line (spacing/section separation).
L1276:     def _get_selected_config_keys(self) -> List[str]:
    -> starts a function definition (reusable logic).
L1277:         sel_indices = self.lst_keys.curselection()
    -> general Python statement supporting the app's workflow.
L1278:         if not sel_indices:
    -> control flow decision (branches logic based on conditions).
L1279:             messagebox.showwarning('Select Keys', 'Please select one or more Config Keys to compare.')
    -> general Python statement supporting the app's workflow.
L1280:             return []
    -> returns a value from a function/method.
L1281:         return [self.lst_keys.get(i) for i in sel_indices]
    -> returns a value from a function/method.
L1282: 
    -> blank line (spacing/section separation).
L1283:     def _get_rows_for_keys_map(self, name: str, keys: List[str]) -> Dict[str, Dict[str, str]]:
    -> starts a function definition (reusable logic).
L1284:         '''
    -> docstring delimiter (module/docs block).
L1285:         Build a map of {cfgkey_display: row_dict} for comparison.
    -> general Python statement supporting the app's workflow.
L1286: 
    -> blank line (spacing/section separation).
L1287:         The Listbox shows formatted/display keys. We map those back to the raw
    -> general Python statement supporting the app's workflow.
L1288:         values from the file for matching, but keep the display key so the UI
    -> general Python statement supporting the app's workflow.
L1289:         and exports stay consistent.
    -> general Python statement supporting the app's workflow.
L1290:         '''
    -> docstring delimiter (module/docs block).
L1291:         disp_set = set(keys)
    -> general Python statement supporting the app's workflow.
L1292:         raw_to_disp: Dict[str, str] = {}
    -> general Python statement supporting the app's workflow.
L1293:         for disp in disp_set:
    -> loop (repeats logic across items).
L1294:             raw = (self.display_to_raw.get(disp, disp) or '').strip()
    -> general Python statement supporting the app's workflow.
L1295:             if raw:
    -> control flow decision (branches logic based on conditions).
L1296:                 raw_to_disp[raw] = disp
    -> general Python statement supporting the app's workflow.
L1297:         remaining_raw = set(raw_to_disp.keys())
    -> general Python statement supporting the app's workflow.
L1298: 
    -> blank line (spacing/section separation).
L1299:         rows_map: Dict[str, Dict[str, str]] = {}
    -> general Python statement supporting the app's workflow.
L1300:         for idx in self.by_name.get(name, []):
    -> loop (repeats logic across items).
L1301:             row = self.rows[idx]
    -> general Python statement supporting the app's workflow.
L1302:             raw_k = (row.get('Config Key', '') or '').strip()
    -> general Python statement supporting the app's workflow.
L1303:             if raw_k in remaining_raw:
    -> control flow decision (branches logic based on conditions).
L1304:                 disp_k = raw_to_disp.get(raw_k, raw_k)
    -> general Python statement supporting the app's workflow.
L1305:                 rows_map[disp_k] = row
    -> general Python statement supporting the app's workflow.
L1306:                 remaining_raw.remove(raw_k)
    -> general Python statement supporting the app's workflow.
L1307:                 if not remaining_raw:
    -> control flow decision (branches logic based on conditions).
L1308:                     break
    -> general Python statement supporting the app's workflow.
L1309: 
    -> blank line (spacing/section separation).
L1310:         return rows_map
    -> returns a value from a function/method.
L1311: 
    -> blank line (spacing/section separation).
L1312:     def on_compare(self, _evt: Optional[tk.Event] = None) -> None:
    -> starts a function definition (reusable logic).
L1313:         """
    -> docstring delimiter (module/docs block).
L1314:         Entry point for the Compare button and F5 shortcut.
    -> general Python statement supporting the app's workflow.
L1315: 
    -> blank line (spacing/section separation).
L1316:         1. Validates that a Config Name and one or more Config Keys are selected.
    -> general Python statement supporting the app's workflow.
L1317:         2. Builds a compact map of rows to compare (using indices from self.by_name).
    -> general Python statement supporting the app's workflow.
L1318:         3. Runs DeepDiff in a background thread pool with a progress dialog.
    -> DeepDiff usage (computes structured differences between JSON objects).
L1319:         4. Updates the main table + stats when done.
    -> general Python statement supporting the app's workflow.
L1320:         """
    -> docstring delimiter (module/docs block).
L1321:         name = self.cmb_name.get().strip()
    -> general Python statement supporting the app's workflow.
L1322:         if not name:
    -> control flow decision (branches logic based on conditions).
L1323:             messagebox.showwarning('Config Name', 'Please select a Config Name first.')
    -> general Python statement supporting the app's workflow.
L1324:             return
    -> returns a value from a function/method.
L1325: 
    -> blank line (spacing/section separation).
L1326:         keys = self._get_selected_config_keys()
    -> general Python statement supporting the app's workflow.
L1327:         if not keys:
    -> control flow decision (branches logic based on conditions).
L1328:             return
    -> returns a value from a function/method.
L1329: 
    -> blank line (spacing/section separation).
L1330:         rows_map = self._get_rows_for_keys_map(name, keys)
    -> general Python statement supporting the app's workflow.
L1331:         if not rows_map:
    -> control flow decision (branches logic based on conditions).
L1332:             messagebox.showwarning('No Rows', 'No matching rows found for the selected Config Keys.')
    -> general Python statement supporting the app's workflow.
L1333:             return
    -> returns a value from a function/method.
L1334: 
    -> blank line (spacing/section separation).
L1335:         # Prepare for comparison
    -> comment/doc note (helps humans; ignored by Python).
L1336:         self.rows_to_compare_map = rows_map
    -> general Python statement supporting the app's workflow.
L1337:         self.full_payloads_cache.clear()
    -> general Python statement supporting the app's workflow.
L1338:         self._reset_views(clear_keys=False)
    -> general Python statement supporting the app's workflow.
L1339:         self.btn_compare.configure(state='disabled')
    -> general Python statement supporting the app's workflow.
L1340:         self.btn_export_csv.configure(state='disabled')
    -> general Python statement supporting the app's workflow.
L1341:         self.btn_export_txt.configure(state='disabled')
    -> general Python statement supporting the app's workflow.
L1342: 
    -> blank line (spacing/section separation).
L1343:         def done_cb(result: Tuple[List[RowMeta], Dict[str, int]]):
    -> starts a function definition (reusable logic).
L1344:             # Re-enable Compare button even if something goes wrong
    -> comment/doc note (helps humans; ignored by Python).
L1345:             self.btn_compare.configure(state='normal')
    -> general Python statement supporting the app's workflow.
L1346: 
    -> blank line (spacing/section separation).
L1347:             if not result:
    -> control flow decision (branches logic based on conditions).
L1348:                 return
    -> returns a value from a function/method.
L1349: 
    -> blank line (spacing/section separation).
L1350:             diffs, stats = result
    -> general Python statement supporting the app's workflow.
L1351:             total_diffs = len(diffs)
    -> general Python statement supporting the app's workflow.
L1352: 
    -> blank line (spacing/section separation).
L1353:             if total_diffs == 0:
    -> control flow decision (branches logic based on conditions).
L1354:                 messagebox.showinfo('No Differences', 'DeepDiff found no differences for the selected keys.')
    -> DeepDiff usage (computes structured differences between JSON objects).
L1355:                 self._reset_views(clear_keys=False)
    -> general Python statement supporting the app's workflow.
L1356:                 return
    -> returns a value from a function/method.
L1357: 
    -> blank line (spacing/section separation).
L1358:             if total_diffs > config.DIFF_DISPLAY_LIMIT:
    -> control flow decision (branches logic based on conditions).
L1359:                 if messagebox.askyesno(
    -> control flow decision (branches logic based on conditions).
L1360:                     'Limit Results',
    -> general Python statement supporting the app's workflow.
L1361:                     f'{total_diffs:,} differences found. Show only the first {config.DIFF_DISPLAY_LIMIT:,} rows?'
    -> general Python statement supporting the app's workflow.
L1362:                 ):
    -> general Python statement supporting the app's workflow.
L1363:                     diffs = diffs[:config.DIFF_DISPLAY_LIMIT]
    -> general Python statement supporting the app's workflow.
L1364: 
    -> blank line (spacing/section separation).
L1365:             # Sort and display
    -> comment/doc note (helps humans; ignored by Python).
L1366:             diffs.sort(key=lambda m: (m.cfgkey, m.path or ''))
    -> general Python statement supporting the app's workflow.
L1367:             self._populate_table(diffs)
    -> general Python statement supporting the app's workflow.
L1368: 
    -> blank line (spacing/section separation).
L1369:             self.v_changed.set(f"Changed: {stats.get('changed', 0)}")
    -> general Python statement supporting the app's workflow.
L1370:             self.v_added.set(f"Added: {stats.get('added', 0)}")
    -> general Python statement supporting the app's workflow.
L1371:             self.v_removed.set(f"Removed: {stats.get('removed', 0)}")
    -> general Python statement supporting the app's workflow.
L1372: 
    -> blank line (spacing/section separation).
L1373:             # Enable export & clear now that we have data
    -> comment/doc note (helps humans; ignored by Python).
L1374:             self.btn_clear.configure(state='normal')
    -> general Python statement supporting the app's workflow.
L1375:             self.btn_export_csv.configure(state='normal')
    -> general Python statement supporting the app's workflow.
L1376:             self.btn_export_txt.configure(state='normal')
    -> general Python statement supporting the app's workflow.
L1377: 
    -> blank line (spacing/section separation).
L1378:         # Launch background work with a progress dialog
    -> comment/doc note (helps humans; ignored by Python).
L1379:         self._with_progress_threaded(
    -> general Python statement supporting the app's workflow.
L1380:             self._run_parallel_diffs,
    -> general Python statement supporting the app's workflow.
L1381:             title=f"Comparing {len(rows_map):,} Config Key(s)...",
    -> general Python statement supporting the app's workflow.
L1382:             done_cb=done_cb,
    -> general Python statement supporting the app's workflow.
L1383:             determinate=True,
    -> general Python statement supporting the app's workflow.
L1384:         )
    -> general Python statement supporting the app's workflow.
L1385: 
    -> blank line (spacing/section separation).
L1386: 
    -> blank line (spacing/section separation).
L1387:     def _run_parallel_diffs(self, progress_cb: callable) -> Tuple[List[RowMeta], Dict[str, int]]:
    -> starts a function definition (reusable logic).
L1388:         """
    -> docstring delimiter (module/docs block).
L1389:         REFINED: The main task function for the progress bar.
    -> general Python statement supporting the app's workflow.
L1390:         Manages the thread pool and collects results.
    -> general Python statement supporting the app's workflow.
L1391:         """
    -> docstring delimiter (module/docs block).
L1392:         tasks_q = queue.Queue()
    -> general Python statement supporting the app's workflow.
L1393:         results_q = queue.Queue()
    -> general Python statement supporting the app's workflow.
L1394:         parse_log_q = queue.Queue() # For thread-safe GUI logging
    -> general Python statement supporting the app's workflow.
L1395:         
    -> blank line (spacing/section separation).
L1396:         total_tasks = len(self.rows_to_compare_map)
    -> general Python statement supporting the app's workflow.
L1397:         for cfgkey, row in self.rows_to_compare_map.items():
    -> loop (repeats logic across items).
L1398:             task = (cfgkey, row['OLD PAYLOAD'], row['CURRENT PAYLOAD'])
    -> general Python statement supporting the app's workflow.
L1399:             tasks_q.put(task)
    -> general Python statement supporting the app's workflow.
L1400: 
    -> blank line (spacing/section separation).
L1401:         threads = []
    -> general Python statement supporting the app's workflow.
L1402:         ignore_order = self.arrays_as_sets.get()
    -> general Python statement supporting the app's workflow.
L1403:         for _ in range(config.MAX_WORKERS):
    -> loop (repeats logic across items).
L1404:             t = threading.Thread(
    -> general Python statement supporting the app's workflow.
L1405:                 target=self._diff_worker, 
    -> general Python statement supporting the app's workflow.
L1406:                 args=(tasks_q, results_q, parse_log_q, ignore_order), 
    -> general Python statement supporting the app's workflow.
L1407:                 daemon=True
    -> general Python statement supporting the app's workflow.
L1408:             )
    -> general Python statement supporting the app's workflow.
L1409:             t.start()
    -> general Python statement supporting the app's workflow.
L1410:             threads.append(t)
    -> general Python statement supporting the app's workflow.
L1411: 
    -> blank line (spacing/section separation).
L1412:         all_diffs = []
    -> general Python statement supporting the app's workflow.
L1413:         stats = defaultdict(int)
    -> general Python statement supporting the app's workflow.
L1414:         processed_count = 0
    -> general Python statement supporting the app's workflow.
L1415:         
    -> blank line (spacing/section separation).
L1416:         while processed_count < total_tasks:
    -> loop (repeats logic across items).
L1417:             try:
    -> error handling block (keeps app stable under bad inputs).
L1418:                 # Poll for results
    -> comment/doc note (helps humans; ignored by Python).
L1419:                 cfgkey, (old_obj, cur_obj), diff_list = results_q.get(timeout=0.1)
    -> general Python statement supporting the app's workflow.
L1420:                 
    -> blank line (spacing/section separation).
L1421:                 # Store full payloads in the main thread's cache
    -> comment/doc note (helps humans; ignored by Python).
L1422:                 self.full_payloads_cache[cfgkey] = (old_obj, cur_obj)
    -> general Python statement supporting the app's workflow.
L1423:                 all_diffs.extend(diff_list)
    -> general Python statement supporting the app's workflow.
L1424:                 for meta in diff_list:
    -> loop (repeats logic across items).
L1425:                     stats[meta.typ] += 1
    -> general Python statement supporting the app's workflow.
L1426:                 
    -> blank line (spacing/section separation).
L1427:                 processed_count += 1
    -> general Python statement supporting the app's workflow.
L1428:                 progress_cb(int(processed_count / total_tasks * 100), f"Compared {processed_count}/{total_tasks} keys...
    -> general Python statement supporting the app's workflow.
L1429: 
    -> blank line (spacing/section separation).
L1430:             except queue.Empty:
    -> error handling block (keeps app stable under bad inputs).
L1431:                 pass # Continue polling
    -> general Python statement supporting the app's workflow.
L1432:             
    -> blank line (spacing/section separation).
L1433:             # Drain parse log queue to update GUI logger
    -> comment/doc note (helps humans; ignored by Python).
L1434:             while not parse_log_q.empty():
    -> loop (repeats logic across items).
L1435:                 try:
    -> error handling block (keeps app stable under bad inputs).
L1436:                     msg, level, ctx = parse_log_q.get_nowait()
    -> general Python statement supporting the app's workflow.
L1437:                     self.parse_logger.log(msg, level, ctx)
    -> general Python statement supporting the app's workflow.
L1438:                     logger.warning(msg) # Also log to file
    -> general Python statement supporting the app's workflow.
L1439:                 except queue.Empty:
    -> error handling block (keeps app stable under bad inputs).
L1440:                     break
    -> general Python statement supporting the app's workflow.
L1441:         
    -> blank line (spacing/section separation).
L1442:         # Stop workers
    -> comment/doc note (helps humans; ignored by Python).
L1443:         for _ in range(config.MAX_WORKERS):
    -> loop (repeats logic across items).
L1444:             tasks_q.put(None)
    -> general Python statement supporting the app's workflow.
L1445:         for t in threads:
    -> loop (repeats logic across items).
L1446:             t.join()
    -> general Python statement supporting the app's workflow.
L1447:             
    -> blank line (spacing/section separation).
L1448:         return all_diffs, stats
    -> returns a value from a function/method.
L1449: 
    -> blank line (spacing/section separation).
L1450: 
    -> blank line (spacing/section separation).
L1451:     def _diff_worker(self, tasks_q: queue.Queue, results_q: queue.Queue, parse_log_q: queue.Queue, ignore_order: bool):
    -> starts a function definition (reusable logic).
L1452:         """
    -> docstring delimiter (module/docs block).
L1453:         REFINED: This function runs in a separate thread.
    -> general Python statement supporting the app's workflow.
L1454:         It parses JSON, runs DeepDiff, and returns lightweight results.
    -> DeepDiff usage (computes structured differences between JSON objects).
L1455:         """
    -> docstring delimiter (module/docs block).
L1456:         while True:
    -> loop (repeats logic across items).
L1457:             try:
    -> error handling block (keeps app stable under bad inputs).
L1458:                 task = tasks_q.get()
    -> general Python statement supporting the app's workflow.
L1459:                 if task is None:
    -> control flow decision (branches logic based on conditions).
L1460:                     break # Sentinel
    -> general Python statement supporting the app's workflow.
L1461:                 
    -> blank line (spacing/section separation).
L1462:                 cfgkey, old_str, new_str = task
    -> general Python statement supporting the app's workflow.
L1463:                 
    -> blank line (spacing/section separation).
L1464:                 # 1. Lazy Parsing
    -> comment/doc note (helps humans; ignored by Python).
L1465:                 old_obj, err1 = parse_jsonish_verbose(old_str)
    -> general Python statement supporting the app's workflow.
L1466:                 cur_obj, err2 = parse_jsonish_verbose(new_str)
    -> general Python statement supporting the app's workflow.
L1467:                 
    -> blank line (spacing/section separation).
L1468:                 if err1: parse_log_q.put((f"[{cfgkey}] OLD: {err1}", 'warning', old_str[:200]))
    -> control flow decision (branches logic based on conditions).
L1469:                 if err2: parse_log_q.put((f"[{cfgkey}] CURRENT: {err2}", 'warning', new_str[:200]))
    -> control flow decision (branches logic based on conditions).
L1470: 
    -> blank line (spacing/section separation).
L1471:                 # 2. Run DeepDiff
    -> comment/doc note (helps humans; ignored by Python).
L1472:                 try:
    -> error handling block (keeps app stable under bad inputs).
L1473:                     dd = DeepDiff(old_obj, cur_obj, ignore_order=ignore_order, verbose_level=2)
    -> DeepDiff usage (computes structured differences between JSON objects).
L1474:                 except Exception as e:
    -> error handling block (keeps app stable under bad inputs).
L1475:                     parse_log_q.put((f"[{cfgkey}] DeepDiff failed: {e}", 'error', ''))
    -> DeepDiff usage (computes structured differences between JSON objects).
L1476:                     results_q.put((cfgkey, (old_obj, cur_obj), [])) # Put empty result
    -> general Python statement supporting the app's workflow.
L1477:                     continue
    -> general Python statement supporting the app's workflow.
L1478:                 
    -> blank line (spacing/section separation).
L1479:                 # 3. Create lightweight RowMeta objects
    -> comment/doc note (helps humans; ignored by Python).
L1480:                 diff_list = []
    -> general Python statement supporting the app's workflow.
L1481:                 for path, change in dd.get('values_changed', {}).items():
    -> loop (repeats logic across items).
L1482:                     diff_list.append(RowMeta(cfgkey, 'changed', dd_path_to_key(path), change.get('old_value'), change...
    -> general Python statement supporting the app's workflow.
L1483:                 for path, change in dd.get('type_changes', {}).items():
    -> loop (repeats logic across items).
L1484:                     diff_list.append(RowMeta(cfgkey, 'changed', dd_path_to_key(path), change.get('old_value'), change...
    -> general Python statement supporting the app's workflow.
L1485:                 for path in dd.get('dictionary_item_added', set()):
    -> loop (repeats logic across items).
L1486:                     val = value_from_path(cur_obj, path)
    -> general Python statement supporting the app's workflow.
L1487:                     diff_list.append(RowMeta(cfgkey, 'added', dd_path_to_key(path), None, val))
    -> general Python statement supporting the app's workflow.
L1488:                 for path in dd.get('dictionary_item_removed', set()):
    -> loop (repeats logic across items).
L1489:                     val = value_from_path(old_obj, path)
    -> general Python statement supporting the app's workflow.
L1490:                     diff_list.append(RowMeta(cfgkey, 'removed', dd_path_to_key(path), val, None))
    -> general Python statement supporting the app's workflow.
L1491:                 for path, val in dd.get('iterable_item_added', {}).items():
    -> loop (repeats logic across items).
L1492:                     diff_list.append(RowMeta(cfgkey, 'added', dd_path_to_key(path), None, val))
    -> general Python statement supporting the app's workflow.
L1493:                 for path, val in dd.get('iterable_item_removed', {}).items():
    -> loop (repeats logic across items).
L1494:                     diff_list.append(RowMeta(cfgkey, 'removed', dd_path_to_key(path), val, None))
    -> general Python statement supporting the app's workflow.
L1495:                 for path in dd.get('attribute_added', set()):
    -> loop (repeats logic across items).
L1496:                     val = value_from_path(cur_obj, path)
    -> general Python statement supporting the app's workflow.
L1497:                     diff_list.append(RowMeta(cfgkey, 'added', dd_path_to_key(path), None, val))
    -> general Python statement supporting the app's workflow.
L1498:                 for path in dd.get('attribute_removed', set()):
    -> loop (repeats logic across items).
L1499:                     val = value_from_path(old_obj, path)
    -> general Python statement supporting the app's workflow.
L1500:                     diff_list.append(RowMeta(cfgkey, 'removed', dd_path_to_key(path), val, None))
    -> general Python statement supporting the app's workflow.
L1501: 
    -> blank line (spacing/section separation).
L1502:                 # 4. Put results back
    -> comment/doc note (helps humans; ignored by Python).
L1503:                 results_q.put((cfgkey, (old_obj, cur_obj), diff_list))
    -> general Python statement supporting the app's workflow.
L1504: 
    -> blank line (spacing/section separation).
L1505:             except Exception as e:
    -> error handling block (keeps app stable under bad inputs).
L1506:                 # Log unexpected worker crash
    -> comment/doc note (helps humans; ignored by Python).
L1507:                 parse_log_q.put((f"Worker thread error: {e}", 'error', ''))
    -> general Python statement supporting the app's workflow.
L1508:             finally:
    -> error handling block (keeps app stable under bad inputs).
L1509:                 tasks_q.task_done()
    -> general Python statement supporting the app's workflow.
L1510: 
    -> blank line (spacing/section separation).
L1511: 
    -> blank line (spacing/section separation).
L1512:     def _populate_table(self, diffs: List[RowMeta]):
    -> starts a function definition (reusable logic).
L1513:         self.tree.delete(*self.tree.get_children())
    -> general Python statement supporting the app's workflow.
L1514:         self._tree_meta.clear()
    -> general Python statement supporting the app's workflow.
L1515:         self._row_order.clear()
    -> general Python statement supporting the app's workflow.
L1516: 
    -> blank line (spacing/section separation).
L1517:         for idx, meta in enumerate(diffs):
    -> loop (repeats logic across items).
L1518:             tags = [meta.typ]
    -> general Python statement supporting the app's workflow.
L1519:             if self._row_is_watched(meta.path):
    -> control flow decision (branches logic based on conditions).
L1520:                 tags.append('watch')
    -> general Python statement supporting the app's workflow.
L1521:             
    -> blank line (spacing/section separation).
L1522:             # Use the lightweight RowMeta
    -> comment/doc note (helps humans; ignored by Python).
L1523:             iid = self.tree.insert('', tk.END, values=(
    -> Tkinter UI widget / layout statement (creates or configures UI).
L1524:                 meta.cfgkey, meta.typ, meta.path, 
    -> general Python statement supporting the app's workflow.
L1525:                 self._s(meta.old), self._s(meta.new)
    -> general Python statement supporting the app's workflow.
L1526:             ), tags=tuple(tags))
    -> general Python statement supporting the app's workflow.
L1527:             
    -> blank line (spacing/section separation).
L1528:             self._tree_meta[iid] = meta
    -> general Python statement supporting the app's workflow.
L1529:             self._row_order[iid] = idx
    -> general Python statement supporting the app's workflow.
L1530: 
    -> blank line (spacing/section separation).
L1531:         self._filter_tree()
    -> general Python statement supporting the app's workflow.
L1532:         if not self.tree.selection():
    -> control flow decision (branches logic based on conditions).
L1533:             children = self.tree.get_children()
    -> general Python statement supporting the app's workflow.
L1534:             if children:
    -> control flow decision (branches logic based on conditions).
L1535:                 self.tree.selection_set(children[0])
    -> general Python statement supporting the app's workflow.
L1536:                 self.tree.focus(children[0])
    -> general Python statement supporting the app's workflow.
L1537:                 self.tree.see(children[0])
    -> general Python statement supporting the app's workflow.
L1538: 
    -> blank line (spacing/section separation).
L1539:     def on_tree_select(self, _evt=None):
    -> starts a function definition (reusable logic).
L1540:         """
    -> docstring delimiter (module/docs block).
L1541:         REFINED: Now retrieves full JSON from the cache.
    -> general Python statement supporting the app's workflow.
L1542:         """
    -> docstring delimiter (module/docs block).
L1543:         sel = self.tree.selection()
    -> general Python statement supporting the app's workflow.
L1544:         if not sel: return
    -> control flow decision (branches logic based on conditions).
L1545:         meta = self._tree_meta.get(sel[0])
    -> general Python statement supporting the app's workflow.
L1546:         if not meta: return
    -> control flow decision (branches logic based on conditions).
L1547: 
    -> blank line (spacing/section separation).
L1548:         # Retrieve the full objects from the cache
    -> comment/doc note (helps humans; ignored by Python).
L1549:         old_obj, new_obj = self.full_payloads_cache.get(meta.cfgkey, (None, None))
    -> general Python statement supporting the app's workflow.
L1550:         
    -> blank line (spacing/section separation).
L1551:         if old_obj is None and new_obj is None:
    -> control flow decision (branches logic based on conditions).
L1552:             logger.warning(f"Could not find payload in cache for key: {meta.cfgkey}")
    -> general Python statement supporting the app's workflow.
L1553:             # This shouldn't happen, but good to guard
    -> comment/doc note (helps humans; ignored by Python).
L1554:             return
    -> returns a value from a function/method.
L1555: 
    -> blank line (spacing/section separation).
L1556:         # Inline diff (uses leaf values from RowMeta)
    -> comment/doc note (helps humans; ignored by Python).
L1557:         self._show_inline_diff(
    -> general Python statement supporting the app's workflow.
L1558:             str(meta.old if meta.old is not None else ""),
    -> general Python statement supporting the app's workflow.
L1559:             str(meta.new if meta.new is not None else "")
    -> general Python statement supporting the app's workflow.
L1560:         )
    -> general Python statement supporting the app's workflow.
L1561: 
    -> blank line (spacing/section separation).
L1562:         # Render full JSONs (uses cached full objects)
    -> comment/doc note (helps humans; ignored by Python).
L1563:         self._render_full_payloads(old_obj, new_obj)
    -> general Python statement supporting the app's workflow.
L1564: 
    -> blank line (spacing/section separation).
L1565:         leaf_key = meta.path.split('.')[-1].split('[')[0] if meta.path else ''
    -> general Python statement supporting the app's workflow.
L1566:         self._scroll_sync_active = True
    -> general Python statement supporting the app's workflow.
L1567:         try:
    -> error handling block (keeps app stable under bad inputs).
L1568:             # Highlight line (uses leaf values from RowMeta)
    -> comment/doc note (helps humans; ignored by Python).
L1569:             self._highlight_line_for_key_value(self.txt_old, leaf_key, meta.old)
    -> general Python statement supporting the app's workflow.
L1570:             self._highlight_line_for_key_value(self.txt_cur, leaf_key, meta.new)
    -> general Python statement supporting the app's workflow.
L1571:         finally:
    -> error handling block (keeps app stable under bad inputs).
L1572:             self._scroll_sync_active = False
    -> general Python statement supporting the app's workflow.
L1573: 
    -> blank line (spacing/section separation).
L1574:     # ------------- Diff visualization -------------
    -> comment/doc note (helps humans; ignored by Python).
L1575: 
    -> blank line (spacing/section separation).
L1576:     def _show_inline_diff(self, old_str: str, new_str: str) -> None:
    -> starts a function definition (reusable logic).
L1577:         self.txt_sel_old.delete('1.0', tk.END)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L1578:         self.txt_sel_new.delete('1.0', tk.END)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L1579:         sm = difflib.SequenceMatcher(a=old_str, b=new_str)
    -> general Python statement supporting the app's workflow.
L1580: 
    -> blank line (spacing/section separation).
L1581:         for op, i1, i2, j1, j2 in sm.get_opcodes():
    -> loop (repeats logic across items).
L1582:             if op == 'equal':
    -> control flow decision (branches logic based on conditions).
L1583:                 self.txt_sel_old.insert(tk.END, old_str[i1:i2])
    -> Tkinter UI widget / layout statement (creates or configures UI).
L1584:                 self.txt_sel_new.insert(tk.END, new_str[j1:j2])
    -> Tkinter UI widget / layout statement (creates or configures UI).
L1585:             elif op in ('delete', 'replace'):
    -> control flow decision (branches logic based on conditions).
L1586:                 self.txt_sel_old.insert(tk.END, old_str[i1:i2], 'del')
    -> Tkinter UI widget / layout statement (creates or configures UI).
L1587:             if op in ('insert', 'replace'):
    -> control flow decision (branches logic based on conditions).
L1588:                 self.txt_sel_new.insert(tk.END, new_str[j1:j2], 'add')
    -> Tkinter UI widget / layout statement (creates or configures UI).
L1589: 
    -> blank line (spacing/section separation).
L1590:     def _render_full_payloads(self, old_obj: Any, new_obj: Any) -> None:
    -> starts a function definition (reusable logic).
L1591:         self.txt_old.delete('1.0', tk.END)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L1592:         self.txt_cur.delete('1.0', tk.END)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L1593:         self.txt_old.insert('1.0', pretty_json(old_obj))
    -> general Python statement supporting the app's workflow.
L1594:         self.txt_cur.insert('1.0', pretty_json(new_obj))
    -> general Python statement supporting the app's workflow.
L1595: 
    -> blank line (spacing/section separation).
L1596:     def _highlight_line_for_key_value(self, widget: tk.Text, leaf_key: str, value: Any) -> None:
    -> starts a function definition (reusable logic).
L1597:         tag = "linehit"
    -> general Python statement supporting the app's workflow.
L1598:         widget.tag_remove(tag, "1.0", "end")
    -> general Python statement supporting the app's workflow.
L1599:         widget.tag_configure(tag, background=config.COLOR_LINE_HIT_BG, foreground=config.COLOR_LINE_HIT_FG)
    -> general Python statement supporting the app's workflow.
L1600:         
    -> blank line (spacing/section separation).
L1601:         text = widget.get("1.0", "end-1c")
    -> general Python statement supporting the app's workflow.
L1602:         if not text.strip():
    -> control flow decision (branches logic based on conditions).
L1603:             return
    -> returns a value from a function/method.
L1604: 
    -> blank line (spacing/section separation).
L1605:         key_pat = re.escape(f'"{leaf_key}"') if leaf_key else None
    -> general Python statement supporting the app's workflow.
L1606:         val_str = None
    -> general Python statement supporting the app's workflow.
L1607:         try:
    -> error handling block (keeps app stable under bad inputs).
L1608:             if value is not None:
    -> control flow decision (branches logic based on conditions).
L1609:                 val_str = json.dumps(value, ensure_ascii=False)
    -> general Python statement supporting the app's workflow.
L1610:         except TypeError:
    -> error handling block (keeps app stable under bad inputs).
L1611:             val_str = None
    -> general Python statement supporting the app's workflow.
L1612: 
    -> blank line (spacing/section separation).
L1613:         match = None
    -> general Python statement supporting the app's workflow.
L1614:         if key_pat and val_str is not None:
    -> control flow decision (branches logic based on conditions).
L1615:             try:
    -> error handling block (keeps app stable under bad inputs).
L1616:                 full_pat = re.compile(f"{key_pat}\\s*:\\s*{re.escape(val_str)}")
    -> general Python statement supporting the app's workflow.
L1617:                 match = full_pat.search(text)
    -> general Python statement supporting the app's workflow.
L1618:             except re.error:
    -> error handling block (keeps app stable under bad inputs).
L1619:                 match = None
    -> general Python statement supporting the app's workflow.
L1620: 
    -> blank line (spacing/section separation).
L1621:         if not match and key_pat:
    -> control flow decision (branches logic based on conditions).
L1622:             try:
    -> error handling block (keeps app stable under bad inputs).
L1623:                 key_only_pat = re.compile(key_pat)
    -> general Python statement supporting the app's workflow.
L1624:                 match = key_only_pat.search(text)
    -> general Python statement supporting the app's workflow.
L1625:             except re.error:
    -> error handling block (keeps app stable under bad inputs).
L1626:                 match = None
    -> general Python statement supporting the app's workflow.
L1627: 
    -> blank line (spacing/section separation).
L1628:         if not match and val_str:
    -> control flow decision (branches logic based on conditions).
L1629:             try:
    -> error handling block (keeps app stable under bad inputs).
L1630:                 val_only_pat = re.compile(re.escape(val_str))
    -> general Python statement supporting the app's workflow.
L1631:                 match = val_only_pat.search(text)
    -> general Python statement supporting the app's workflow.
L1632:             except re.error:
    -> error handling block (keeps app stable under bad inputs).
L1633:                 match = None
    -> general Python statement supporting the app's workflow.
L1634: 
    -> blank line (spacing/section separation).
L1635:         if match:
    -> control flow decision (branches logic based on conditions).
L1636:             start_pos = f"1.0 + {match.start()} chars"
    -> general Python statement supporting the app's workflow.
L1637:             line_start = widget.index(f"{start_pos} linestart")
    -> general Python statement supporting the app's workflow.
L1638:             line_end = widget.index(f"{start_pos} lineend + 1 char")
    -> general Python statement supporting the app's workflow.
L1639:             widget.tag_add(tag, line_start, line_end)
    -> general Python statement supporting the app's workflow.
L1640:             widget.see(line_start)
    -> general Python statement supporting the app's workflow.
L1641:         else:
    -> control flow decision (branches logic based on conditions).
L1642:             widget.tag_add(tag, "1.0", "2.0")
    -> general Python statement supporting the app's workflow.
L1643:             widget.see("1.0")
    -> general Python statement supporting the app's workflow.
L1644: 
    -> blank line (spacing/section separation).
L1645:     # ------------- Filtering / watch -------------
    -> comment/doc note (helps humans; ignored by Python).
L1646: 
    -> blank line (spacing/section separation).
L1647:     def apply_watchlist(self):
    -> starts a function definition (reusable logic).
L1648:         text = self.ent_watch.get().strip()
    -> general Python statement supporting the app's workflow.
L1649:         self.watchlist = [w.strip().lower() for w in text.split(',') if w.strip()]
    -> general Python statement supporting the app's workflow.
L1650:         for iid, meta in self._tree_meta.items():
    -> loop (repeats logic across items).
L1651:             tags = list(self.tree.item(iid, 'tags'))
    -> general Python statement supporting the app's workflow.
L1652:             if self._row_is_watched(meta.path) and 'watch' not in tags:
    -> control flow decision (branches logic based on conditions).
L1653:                 tags.append('watch')
    -> general Python statement supporting the app's workflow.
L1654:             elif not self._row_is_watched(meta.path) and 'watch' in tags:
    -> control flow decision (branches logic based on conditions).
L1655:                 tags.remove('watch')
    -> general Python statement supporting the app's workflow.
L1656:             self.tree.item(iid, tags=tuple(tags))
    -> general Python statement supporting the app's workflow.
L1657:         self._filter_tree()
    -> general Python statement supporting the app's workflow.
L1658: 
    -> blank line (spacing/section separation).
L1659:     def _row_is_watched(self, key_path: str) -> bool:
    -> starts a function definition (reusable logic).
L1660:         if not self.watchlist: return False
    -> control flow decision (branches logic based on conditions).
L1661:         lk = key_path.lower()
    -> general Python statement supporting the app's workflow.
L1662:         return any(w in lk for w in self.watchlist)
    -> returns a value from a function/method.
L1663: 
    -> blank line (spacing/section separation).
L1664:     def _filter_tree(self, *_):
    -> starts a function definition (reusable logic).
L1665:         query = self.search_var.get().strip().lower()
    -> general Python statement supporting the app's workflow.
L1666:         for iid, meta in self._tree_meta.items():
    -> loop (repeats logic across items).
L1667:             is_visible = True
    -> general Python statement supporting the app's workflow.
L1668:             if query:
    -> control flow decision (branches logic based on conditions).
L1669:                 haystack = f"{meta.cfgkey} {meta.typ} {meta.path} {self._s(meta.old)} {self._s(meta.new)}".lower()
    -> general Python statement supporting the app's workflow.
L1670:                 is_visible = query in haystack
    -> general Python statement supporting the app's workflow.
L1671:             if is_visible and self.only_watch.get():
    -> control flow decision (branches logic based on conditions).
L1672:                 is_visible = self._row_is_watched(meta.path)
    -> general Python statement supporting the app's workflow.
L1673:             
    -> blank line (spacing/section separation).
L1674:             if not is_visible:
    -> control flow decision (branches logic based on conditions).
L1675:                 self.tree.detach(iid)
    -> general Python statement supporting the app's workflow.
L1676:             elif iid not in self.tree.get_children(''):
    -> control flow decision (branches logic based on conditions).
L1677:                 original_index = self._row_order.get(iid, 'end')
    -> general Python statement supporting the app's workflow.
L1678:                 self.tree.move(iid, '', original_index)
    -> general Python statement supporting the app's workflow.
L1679: 
    -> blank line (spacing/section separation).
L1680:     # ------------- Exports (diffs) -------------
    -> comment/doc note (helps humans; ignored by Python).
L1681: 
    -> blank line (spacing/section separation).
L1682:     def on_export_csv(self):
    -> starts a function definition (reusable logic).
L1683:         if not self._tree_meta: return
    -> control flow decision (branches logic based on conditions).
L1684:         p = filedialog.asksaveasfilename(title='Save Visible Diffs as CSV',
    -> general Python statement supporting the app's workflow.
L1685:                                          initialdir=self._get_initial_open_dir(),
    -> general Python statement supporting the app's workflow.
L1686:                                          defaultextension='.csv',
    -> general Python statement supporting the app's workflow.
L1687:                                          filetypes=[('CSV', '*.csv')])
    -> general Python statement supporting the app's workflow.
L1688:         if not p: return
    -> control flow decision (branches logic based on conditions).
L1689:         
    -> blank line (spacing/section separation).
L1690:         try:
    -> error handling block (keeps app stable under bad inputs).
L1691:             with open(p, 'w', encoding='utf-8', newline='') as f:
    -> general Python statement supporting the app's workflow.
L1692:                 writer = csv.writer(f)
    -> general Python statement supporting the app's workflow.
L1693:                 writer.writerow(['Config Key', 'Type', 'Key Path', 'Old Value', 'New Value', 'Watched'])
    -> general Python statement supporting the app's workflow.
L1694:                 for iid in self.tree.get_children():
    -> loop (repeats logic across items).
L1695:                     meta = self._tree_meta[iid]
    -> general Python statement supporting the app's workflow.
L1696:                     writer.writerow([
    -> general Python statement supporting the app's workflow.
L1697:                         meta.cfgkey, meta.typ, meta.path, 
    -> general Python statement supporting the app's workflow.
L1698:                         self._s(meta.old), self._s(meta.new),
    -> general Python statement supporting the app's workflow.
L1699:                         'YES' if self._row_is_watched(meta.path) else ''
    -> general Python statement supporting the app's workflow.
L1700:                     ])
    -> general Python statement supporting the app's workflow.
L1701:             messagebox.showinfo('Saved', f'CSV saved to:\n{p}')
    -> general Python statement supporting the app's workflow.
L1702:             logger.info(f"Exported CSV: {p}")
    -> general Python statement supporting the app's workflow.
L1703:         except IOError as e:
    -> error handling block (keeps app stable under bad inputs).
L1704:             messagebox.showerror('Error', f'Failed to save CSV:\n{e}')
    -> general Python statement supporting the app's workflow.
L1705:             logger.error(f"Failed to export CSV: {e}")
    -> general Python statement supporting the app's workflow.
L1706: 
    -> blank line (spacing/section separation).
L1707:     def on_export_txt(self):
    -> starts a function definition (reusable logic).
L1708:         if not self._tree_meta: return
    -> control flow decision (branches logic based on conditions).
L1709:         p = filedialog.asksaveasfilename(title='Save Visible Diffs as TXT',
    -> general Python statement supporting the app's workflow.
L1710:                                          initialdir=self._get_initial_open_dir(),
    -> general Python statement supporting the app's workflow.
L1711:                                          defaultextension='.txt',
    -> general Python statement supporting the app's workflow.
L1712:                                          filetypes=[('Text', '*.txt')])
    -> general Python statement supporting the app's workflow.
L1713:         if not p: return
    -> control flow decision (branches logic based on conditions).
L1714: 
    -> blank line (spacing/section separation).
L1715:         grouped: Dict[str, List[RowMeta]] = {}
    -> general Python statement supporting the app's workflow.
L1716:         for iid in self.tree.get_children():
    -> loop (repeats logic across items).
L1717:             meta = self._tree_meta[iid]
    -> general Python statement supporting the app's workflow.
L1718:             grouped.setdefault(meta.cfgkey, []).append(meta)
    -> general Python statement supporting the app's workflow.
L1719: 
    -> blank line (spacing/section separation).
L1720:         lines = []
    -> general Python statement supporting the app's workflow.
L1721:         for cfgkey, items in grouped.items():
    -> loop (repeats logic across items).
L1722:             lines.append(f"=== Config Key: {cfgkey} ===")
    -> general Python statement supporting the app's workflow.
L1723:             for typ in ('changed', 'added', 'removed'):
    -> loop (repeats logic across items).
L1724:                 diffs_of_type = [m for m in items if m.typ == typ]
    -> general Python statement supporting the app's workflow.
L1725:                 if not diffs_of_type: continue
    -> control flow decision (branches logic based on conditions).
L1726:                 lines.append(f"\n-- {typ.UPPER()} ({len(diffs_of_type)}) --" if hasattr(str, 'UPPER') else f"\n-- {ty...
    -> general Python statement supporting the app's workflow.
L1727:                 for m in diffs_of_type:
    -> loop (repeats logic across items).
L1728:                     lines.append(f"Key: {m.path}")
    -> general Python statement supporting the app's workflow.
L1729:                     if m.typ == 'changed':
    -> control flow decision (branches logic based on conditions).
L1730:                         lines.append(f"  Old: {self._s(m.old)}")
    -> general Python statement supporting the app's workflow.
L1731:                         lines.append(f"  New: {self._s(m.new)}")
    -> general Python statement supporting the app's workflow.
L1732:                         lines.append("  Fragment (OLD):")
    -> general Python statement supporting the app's workflow.
L1733:                         lines.append(self._format_fragment(m.path, m.old))
    -> general Python statement supporting the app's workflow.
L1734:                         lines.append("  Fragment (NEW):")
    -> general Python statement supporting the app's workflow.
L1735:                         lines.append(self._format_fragment(m.path, m.new))
    -> general Python statement supporting the app's workflow.
L1736:                     elif m.typ == 'added':
    -> control flow decision (branches logic based on conditions).
L1737:                         lines.append(f"  New: {self._s(m.new)}")
    -> general Python statement supporting the app's workflow.
L1738:                         lines.append("  Fragment (NEW):")
    -> general Python statement supporting the app's workflow.
L1739:                         lines.append(self._format_fragment(m.path, m.new))
    -> general Python statement supporting the app's workflow.
L1740:                     elif m.typ == 'removed':
    -> control flow decision (branches logic based on conditions).
L1741:                         lines.append(f"  Old: {self._s(m.old)}")
    -> general Python statement supporting the app's workflow.
L1742:                         lines.append("  Fragment (OLD):")
    -> general Python statement supporting the app's workflow.
L1743:                         lines.append(self._format_fragment(m.path, m.old))
    -> general Python statement supporting the app's workflow.
L1744:             lines.append("\n" + "="*60 + "\n")
    -> general Python statement supporting the app's workflow.
L1745: 
    -> blank line (spacing/section separation).
L1746:         try:
    -> error handling block (keeps app stable under bad inputs).
L1747:             with open(p, 'w', encoding='utf-8') as f:
    -> general Python statement supporting the app's workflow.
L1748:                 f.write('\n'.join(lines))
    -> general Python statement supporting the app's workflow.
L1749:             messagebox.showinfo('Saved', f'TXT saved to:\n{p}')
    -> general Python statement supporting the app's workflow.
L1750:             logger.info(f"Exported TXT: {p}")
    -> general Python statement supporting the app's workflow.
L1751:         except IOError as e:
    -> error handling block (keeps app stable under bad inputs).
L1752:             messagebox.showerror('Error', f'Failed to save TXT:\n{e}')
    -> general Python statement supporting the app's workflow.
L1753:             logger.error(f"Failed to export TXT: {e}")
    -> general Python statement supporting the app's workflow.
L1754:             
    -> blank line (spacing/section separation).
L1755:     def _format_fragment(self, path: str, value: Any) -> str:
    -> starts a function definition (reusable logic).
L1756:         try:
    -> error handling block (keeps app stable under bad inputs).
L1757:             frag = build_fragment_from_path_value(path, value)
    -> general Python statement supporting the app's workflow.
L1758:             pretty = pretty_json(frag)
    -> general Python statement supporting the app's workflow.
L1759:             return '\n'.join(f"    {line}" for line in pretty.splitlines())
    -> returns a value from a function/method.
L1760:         except Exception:
    -> error handling block (keeps app stable under bad inputs).
L1761:             return "    (fragment generation error)"
    -> returns a value from a function/method.
L1762: 
    -> blank line (spacing/section separation).
L1763:     # ------------- Column confirm dialog -------------
    -> comment/doc note (helps humans; ignored by Python).
L1764: 
    -> blank line (spacing/section separation).
L1765:     def _confirm_column_mapping(self, headers: List[str], mapping: Dict[str, int],
    -> starts a function definition (reusable logic).
L1766:                                 confidence: Dict[str, float]) -> Optional[Dict[str, int]]:
    -> general Python statement supporting the app's workflow.
L1767:         dialog = tk.Toplevel(self)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L1768:         dialog.title("Confirm Column Mapping")
    -> general Python statement supporting the app's workflow.
L1769:         dialog.transient(self)
    -> general Python statement supporting the app's workflow.
L1770:         dialog.grab_set()
    -> general Python statement supporting the app's workflow.
L1771:         dialog.resizable(False, False)
    -> general Python statement supporting the app's workflow.
L1772: 
    -> blank line (spacing/section separation).
L1773:         ttk.Label(dialog, text="Please confirm or adjust the column mappings:",
    -> Tkinter UI widget / layout statement (creates or configures UI).
L1774:                   font=('TkDefaultFont', 10, 'bold')).grid(row=0, column=0, columnspan=3, pady=10, padx=10, sticky='w')
    -> general Python statement supporting the app's workflow.
L1775: 
    -> blank line (spacing/section separation).
L1776:         combos: Dict[str, ttk.Combobox] = {}
    -> Tkinter UI widget / layout statement (creates or configures UI).
L1777:         for i, role in enumerate(NEEDED_ROLES, 1):
    -> loop (repeats logic across items).
L1778:             ttk.Label(dialog, text=f"{role}:").grid(row=i, column=0, padx=10, pady=5, sticky='e')
    -> Tkinter UI widget / layout statement (creates or configures UI).
L1779:             combo = ttk.Combobox(dialog, values=headers, width=48, state="readonly")
    -> Tkinter UI widget / layout statement (creates or configures UI).
L1780:             if role in mapping:
    -> control flow decision (branches logic based on conditions).
L1781:                 combo.set(headers[mapping[role]])
    -> general Python statement supporting the app's workflow.
L1782:             combo.grid(row=i, column=1, padx=5, pady=5, sticky='w')
    -> general Python statement supporting the app's workflow.
L1783:             combos[role] = combo
    -> general Python statement supporting the app's workflow.
L1784: 
    -> blank line (spacing/section separation).
L1785:             conf_val = confidence.get(role, 0.0)
    -> general Python statement supporting the app's workflow.
L1786:             color = "green" if conf_val >= 0.7 else ("orange" if conf_val >= 0.4 else "red")
    -> general Python statement supporting the app's workflow.
L1787:             ttk.Label(dialog, text=f"({conf_val:.0%})", foreground=color).grid(row=i, column=2, padx=5, pady=5, stick...
    -> Tkinter UI widget / layout statement (creates or configures UI).
L1788: 
    -> blank line (spacing/section separation).
L1789:         result = {"mapping": None}
    -> general Python statement supporting the app's workflow.
L1790:         def on_ok():
    -> starts a function definition (reusable logic).
L1791:             new_mapping = {role: headers.index(combo.get()) for role, combo in combos.items() if combo.get()}
    -> general Python statement supporting the app's workflow.
L1792:             if len({idx for idx in new_mapping.values()}) != len(new_mapping):
    -> control flow decision (branches logic based on conditions).
L1793:                 messagebox.showerror("Duplicate Columns", "Each role must be mapped to a unique column.", parent=dialog)
    -> general Python statement supporting the app's workflow.
L1794:                 return
    -> returns a value from a function/method.
L1795:             result["mapping"] = new_mapping
    -> general Python statement supporting the app's workflow.
L1796:             dialog.destroy()
    -> general Python statement supporting the app's workflow.
L1797:         
    -> blank line (spacing/section separation).
L1798:         btns = ttk.Frame(dialog)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L1799:         btns.grid(row=len(NEEDED_ROLES)+1, column=0, columnspan=3, pady=10)
    -> general Python statement supporting the app's workflow.
L1800:         ttk.Button(btns, text="OK", command=on_ok).pack(side=tk.LEFT, padx=6)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L1801:         ttk.Button(btns, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=6)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L1802: 
    -> blank line (spacing/section separation).
L1803:         dialog.update_idletasks()
    -> general Python statement supporting the app's workflow.
L1804:         x = self.winfo_rootx() + (self.winfo_width() // 2) - (dialog.winfo_width() // 2)
    -> general Python statement supporting the app's workflow.
L1805:         y = self.winfo_rooty() + (self.winfo_height() // 2) - (dialog.winfo_height() // 2)
    -> general Python statement supporting the app's workflow.
L1806:         dialog.geometry(f"+{x}+{y}")
    -> general Python statement supporting the app's workflow.
L1807:         self.wait_window(dialog)
    -> general Python statement supporting the app's workflow.
L1808:         return result["mapping"]
    -> returns a value from a function/method.
L1809: 
    -> blank line (spacing/section separation).
L1810:     # ------------- Progress (threaded) -------------
    -> comment/doc note (helps humans; ignored by Python).
L1811: 
    -> blank line (spacing/section separation).
L1812:     def _with_progress_threaded(self, task_fn, title: str, done_cb, determinate: bool = False):
    -> starts a function definition (reusable logic).
L1813:         top = tk.Toplevel(self)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L1814:         top.title(title)
    -> general Python statement supporting the app's workflow.
L1815:         top.transient(self)
    -> general Python statement supporting the app's workflow.
L1816:         top.resizable(False, False)
    -> general Python statement supporting the app's workflow.
L1817:         top.protocol("WM_DELETE_WINDOW", lambda: None)
    -> general Python statement supporting the app's workflow.
L1818: 
    -> blank line (spacing/section separation).
L1819:         ttk.Label(top, text=title, font=('TkDefaultFont', 10)).pack(padx=20, pady=(15, 6))
    -> Tkinter UI widget / layout statement (creates or configures UI).
L1820:         pb = ttk.Progressbar(top, mode='determinate' if determinate else 'indeterminate', length=350, maximum=100)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L1821:         pb.pack(padx=20, pady=(0, 10))
    -> general Python statement supporting the app's workflow.
L1822:         if not determinate: pb.start(10)
    -> control flow decision (branches logic based on conditions).
L1823: 
    -> blank line (spacing/section separation).
L1824:         status_lbl = ttk.Label(top, text="Starting...")
    -> Tkinter UI widget / layout statement (creates or configures UI).
L1825:         status_lbl.pack(padx=20, pady=(0, 15))
    -> general Python statement supporting the app's workflow.
L1826: 
    -> blank line (spacing/section separation).
L1827:         q_out, q_prog = queue.Queue(), queue.Queue()
    -> general Python statement supporting the app's workflow.
L1828: 
    -> blank line (spacing/section separation).
L1829:         def worker():
    -> starts a function definition (reusable logic).
L1830:             try:
    -> error handling block (keeps app stable under bad inputs).
L1831:                 progress = lambda step, msg: q_prog.put((int(step), str(msg)))
    -> general Python statement supporting the app's workflow.
L1832:                 res = task_fn(progress if determinate else None)
    -> general Python statement supporting the app's workflow.
L1833:                 q_out.put(('ok', res))
    -> general Python statement supporting the app's workflow.
L1834:             except Exception as e:
    -> error handling block (keeps app stable under bad inputs).
L1835:                 logger.error(f"Threaded task failed: {e}", exc_info=True)
    -> general Python statement supporting the app's workflow.
L1836:                 q_out.put(('err', e))
    -> general Python statement supporting the app's workflow.
L1837: 
    -> blank line (spacing/section separation).
L1838:         def poll():
    -> starts a function definition (reusable logic).
L1839:             try:
    -> error handling block (keeps app stable under bad inputs).
L1840:                 step, msg = q_prog.get_nowait()
    -> general Python statement supporting the app's workflow.
L1841:                 pb['value'] = max(0, min(100, step))
    -> general Python statement supporting the app's workflow.
L1842:                 status_lbl.config(text=msg)
    -> general Python statement supporting the app's workflow.
L1843:             except queue.Empty:
    -> error handling block (keeps app stable under bad inputs).
L1844:                 pass
    -> general Python statement supporting the app's workflow.
L1845: 
    -> blank line (spacing/section separation).
L1846:             try:
    -> error handling block (keeps app stable under bad inputs).
L1847:                 status, payload = q_out.get_nowait()
    -> general Python statement supporting the app's workflow.
L1848:                 if not determinate: pb.stop()
    -> control flow decision (branches logic based on conditions).
L1849:                 top.destroy()
    -> general Python statement supporting the app's workflow.
L1850:                 if status == 'ok':
    -> control flow decision (branches logic based on conditions).
L1851:                     done_cb(payload)
    -> general Python statement supporting the app's workflow.
L1852:                 else:
    -> control flow decision (branches logic based on conditions).
L1853:                     messagebox.showerror("Error", f"An error occurred during loading:\n{payload}")
    -> general Python statement supporting the app's workflow.
L1854:             except queue.Empty:
    -> error handling block (keeps app stable under bad inputs).
L1855:                 self.after(100, poll)
    -> general Python statement supporting the app's workflow.
L1856: 
    -> blank line (spacing/section separation).
L1857:         threading.Thread(target=worker, daemon=True).start()
    -> general Python statement supporting the app's workflow.
L1858:         self.after(100, poll)
    -> general Python statement supporting the app's workflow.
L1859: 
    -> blank line (spacing/section separation).
L1860:     # ------------- Small helpers -------------
    -> comment/doc note (helps humans; ignored by Python).
L1861: 
    -> blank line (spacing/section separation).
L1862:     def _reset_views(self, clear_keys: bool = True):
    -> starts a function definition (reusable logic).
L1863:         self.tree.delete(*self.tree.get_children())
    -> general Python statement supporting the app's workflow.
L1864:         self._tree_meta.clear()
    -> general Python statement supporting the app's workflow.
L1865:         self._row_order.clear()
    -> general Python statement supporting the app's workflow.
L1866:         self.txt_sel_old.delete('1.0', tk.END)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L1867:         self.txt_sel_new.delete('1.0', tk.END)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L1868:         self.txt_old.delete('1.0', tk.END)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L1869:         self.txt_cur.delete('1.0', tk.END)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L1870:         self.v_changed.set('Changed: 0')
    -> general Python statement supporting the app's workflow.
L1871:         self.v_added.set('Added: 0')
    -> general Python statement supporting the app's workflow.
L1872:         self.v_removed.set('Removed: 0')
    -> general Python statement supporting the app's workflow.
L1873:         self.search_var.set('')
    -> general Python statement supporting the app's workflow.
L1874:         
    -> blank line (spacing/section separation).
L1875:         if clear_keys:
    -> control flow decision (branches logic based on conditions).
L1876:              self.lst_keys.delete(0, tk.END)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L1877:              self.lst_keys.configure(state=tk.DISABLED)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L1878:              self.btn_compare.configure(state='disabled')
    -> general Python statement supporting the app's workflow.
L1879: 
    -> blank line (spacing/section separation).
L1880:         self.btn_clear.configure(state='disabled')
    -> general Python statement supporting the app's workflow.
L1881:         self.btn_export_csv.configure(state='disabled')
    -> general Python statement supporting the app's workflow.
L1882:         self.btn_export_txt.configure(state='disabled')
    -> general Python statement supporting the app's workflow.
L1883: 
    -> blank line (spacing/section separation).
L1884:     def _s(self, v: Any) -> str:
    -> starts a function definition (reusable logic).
L1885:         if v is None: return ''
    -> control flow decision (branches logic based on conditions).
L1886:         if isinstance(v, (dict, list)):
    -> control flow decision (branches logic based on conditions).
L1887:             try:
    -> error handling block (keeps app stable under bad inputs).
L1888:                 s = json.dumps(v, ensure_ascii=False)
    -> general Python statement supporting the app's workflow.
L1889:             except TypeError:
    -> error handling block (keeps app stable under bad inputs).
L1890:                 s = str(v)
    -> general Python statement supporting the app's workflow.
L1891:         else:
    -> control flow decision (branches logic based on conditions).
L1892:             s = str(v)
    -> general Python statement supporting the app's workflow.
L1893:         return s if len(s) <= 2000 else s[:2000] + "..."
    -> returns a value from a function/method.
L1894: 
    -> blank line (spacing/section separation).
L1895:     def _get_selected_diff_path(self) -> Optional[str]:
    -> starts a function definition (reusable logic).
L1896:         if not self.tree.selection(): return None
    -> control flow decision (branches logic based on conditions).
L1897:         meta = self._tree_meta.get(self.tree.selection()[0])
    -> general Python statement supporting the app's workflow.
L1898:         return meta.path if meta else None
    -> returns a value from a function/method.
L1899: 
    -> blank line (spacing/section separation).
L1900:     def _try_restore_selection(self, path_to_select: Optional[str]):
    -> starts a function definition (reusable logic).
L1901:         if not path_to_select: return
    -> control flow decision (branches logic based on conditions).
L1902:         for iid, meta in self._tree_meta.items():
    -> loop (repeats logic across items).
L1903:             if meta.path == path_to_select:
    -> control flow decision (branches logic based on conditions).
L1904:                 self.tree.selection_set(iid)
    -> general Python statement supporting the app's workflow.
L1905:                 self.tree.focus(iid)
    -> general Python statement supporting the app's workflow.
L1906:                 self.tree.see(iid)
    -> general Python statement supporting the app's workflow.
L1907:                 break
    -> general Python statement supporting the app's workflow.
L1908: 
    -> blank line (spacing/section separation).
L1909:     def show_shortcuts_help(self):
    -> starts a function definition (reusable logic).
L1910:         messagebox.showinfo("Keyboard Shortcuts",
    -> general Python statement supporting the app's workflow.
L1911:                             "Ctrl+O : Open file\n"
    -> general Python statement supporting the app's workflow.
L1912:                             "Ctrl+S : Export visible rows to CSV\n"
    -> general Python statement supporting the app's workflow.
L1913:                             "Ctrl+E : Export visible rows to TXT\n"
    -> general Python statement supporting the app's workflow.
L1914:                             "Ctrl+F : Focus the filter box\n"
    -> general Python statement supporting the app's workflow.
L1915:                             "Ctrl+M : Open Summary Dashboard\n\n"
    -> general Python statement supporting the app's workflow.
L1916:                             "F5     : Run comparison on selected keys\n"
    -> general Python statement supporting the app's workflow.
L1917:                             "Esc    : Remove focus from the current widget")
    -> general Python statement supporting the app's workflow.
L1918: 
    -> blank line (spacing/section separation).
L1919:     # --- ADD THIS NEW METHOD HERE ---
    -> comment/doc note (helps humans; ignored by Python).
L1920:     def _format_key(self, k: str) -> str:
    -> starts a function definition (reusable logic).
L1921:         """Format scientific notation to a non-exponent string for display (precision-safe)."""
    -> docstring delimiter (module/docs block).
L1922:         s = str(k).strip()
    -> general Python statement supporting the app's workflow.
L1923:         if not s:
    -> control flow decision (branches logic based on conditions).
L1924:             return s
    -> returns a value from a function/method.
L1925:         try:
    -> error handling block (keeps app stable under bad inputs).
L1926:             d = Decimal(s)
    -> Decimal used for precision-safe numeric parsing/formatting.
L1927:             out = format(d, 'f')  # no exponent
    -> general Python statement supporting the app's workflow.
L1928:             if '.' in out:
    -> control flow decision (branches logic based on conditions).
L1929:                 out = out.rstrip('0').rstrip('.')
    -> general Python statement supporting the app's workflow.
L1930:             return out
    -> returns a value from a function/method.
L1931:         except InvalidOperation:
    -> error handling block (keeps app stable under bad inputs).
L1932:             return s
    -> returns a value from a function/method.
L1933: 
    -> blank line (spacing/section separation).
L1934:     def _on_yscroll(self, src_text: tk.Text, dst_text: tk.Text,
    -> starts a function definition (reusable logic).
L1935:                     src_scrollbar: ttk.Scrollbar, dst_scrollbar: ttk.Scrollbar,
    -> Tkinter UI widget / layout statement (creates or configures UI).
L1936:                     first: str, last: str) -> None:
    -> general Python statement supporting the app's workflow.
L1937:         try:
    -> error handling block (keeps app stable under bad inputs).
L1938:             src_scrollbar.set(first, last)
    -> general Python statement supporting the app's workflow.
L1939:         except Exception:
    -> error handling block (keeps app stable under bad inputs).
L1940:             pass
    -> general Python statement supporting the app's workflow.
L1941: 
    -> blank line (spacing/section separation).
L1942:         if self._scroll_sync_active:
    -> control flow decision (branches logic based on conditions).
L1943:             return
    -> returns a value from a function/method.
L1944: 
    -> blank line (spacing/section separation).
L1945:         self._scroll_sync_active = True
    -> general Python statement supporting the app's workflow.
L1946:         try:
    -> error handling block (keeps app stable under bad inputs).
L1947:             try:
    -> error handling block (keeps app stable under bad inputs).
L1948:                 dst_scrollbar.set(first, last)
    -> general Python statement supporting the app's workflow.
L1949:             except Exception:
    -> error handling block (keeps app stable under bad inputs).
L1950:                 pass
    -> general Python statement supporting the app's workflow.
L1951:             try:
    -> error handling block (keeps app stable under bad inputs).
L1952:                 dst_text.yview_moveto(first)
    -> general Python statement supporting the app's workflow.
L1953:             except Exception:
    -> error handling block (keeps app stable under bad inputs).
L1954:                 pass
    -> general Python statement supporting the app's workflow.
L1955:         finally:
    -> error handling block (keeps app stable under bad inputs).
L1956:             self._scroll_sync_active = False
    -> general Python statement supporting the app's workflow.
L1957: 
    -> blank line (spacing/section separation).
L1958:     def _on_scrollbar_y(self, src_text: tk.Text, dst_text: tk.Text,
    -> starts a function definition (reusable logic).
L1959:                         src_scrollbar: ttk.Scrollbar, dst_scrollbar: ttk.Scrollbar,
    -> Tkinter UI widget / layout statement (creates or configures UI).
L1960:                         *args) -> None:
    -> general Python statement supporting the app's workflow.
L1961:         self._scroll_sync_active = True
    -> general Python statement supporting the app's workflow.
L1962:         try:
    -> error handling block (keeps app stable under bad inputs).
L1963:             try:
    -> error handling block (keeps app stable under bad inputs).
L1964:                 src_text.yview(*args)
    -> general Python statement supporting the app's workflow.
L1965:             except Exception:
    -> error handling block (keeps app stable under bad inputs).
L1966:                 pass
    -> general Python statement supporting the app's workflow.
L1967:             try:
    -> error handling block (keeps app stable under bad inputs).
L1968:                 dst_text.yview(*args)
    -> general Python statement supporting the app's workflow.
L1969:             except Exception:
    -> error handling block (keeps app stable under bad inputs).
L1970:                 pass
    -> general Python statement supporting the app's workflow.
L1971:             try:
    -> error handling block (keeps app stable under bad inputs).
L1972:                 first, last = src_text.yview()
    -> general Python statement supporting the app's workflow.
L1973:                 src_scrollbar.set(first, last)
    -> general Python statement supporting the app's workflow.
L1974:                 dst_scrollbar.set(first, last)
    -> general Python statement supporting the app's workflow.
L1975:             except Exception:
    -> error handling block (keeps app stable under bad inputs).
L1976:                 pass
    -> general Python statement supporting the app's workflow.
L1977:         finally:
    -> error handling block (keeps app stable under bad inputs).
L1978:             self._scroll_sync_active = False
    -> general Python statement supporting the app's workflow.
L1979: 
    -> blank line (spacing/section separation).
L1980:     # ------------- SUMMARY DASHBOARD -------------
    -> comment/doc note (helps humans; ignored by Python).
L1981: 
    -> blank line (spacing/section separation).
L1982:     def on_view_summary(self):
    -> starts a function definition (reusable logic).
L1983:         if not self.rows:
    -> control flow decision (branches logic based on conditions).
L1984:             messagebox.showinfo("Summary", "Load a file first (File -> Open).")
    -> general Python statement supporting the app's workflow.
L1985:             return
    -> returns a value from a function/method.
L1986: 
    -> blank line (spacing/section separation).
L1987:         win = tk.Toplevel(self)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L1988:         win.title("Summary - Rows per Config Name")
    -> general Python statement supporting the app's workflow.
L1989:         win.geometry("980x680")
    -> general Python statement supporting the app's workflow.
L1990:         win.minsize(760, 480)
    -> general Python statement supporting the app's workflow.
L1991: 
    -> blank line (spacing/section separation).
L1992:         win.pivot_data = []
    -> general Python statement supporting the app's workflow.
L1993:         win.sort_mode = tk.StringVar(value='count_desc')
    -> Tkinter UI widget / layout statement (creates or configures UI).
L1994:         win.show_values = tk.BooleanVar(value=True)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L1995:         # New: controls for Grand Total display
    -> comment/doc note (helps humans; ignored by Python).
L1996:         win.total_scope = tk.StringVar(value='All')  # Options: All, Visible, Selected
    -> Tkinter UI widget / layout statement (creates or configures UI).
L1997:         win.show_total = tk.BooleanVar(value=True)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L1998:         win.grand_total_var = tk.StringVar(value='')
    -> Tkinter UI widget / layout statement (creates or configures UI).
L1999:         # New: config-name filter combobox (single) and multiselect storage
    -> comment/doc note (helps humans; ignored by Python).
L2000:         win.cfg_name_multiset = []
    -> general Python statement supporting the app's workflow.
L2001: 
    -> blank line (spacing/section separation).
L2002:         win.figure = None
    -> general Python statement supporting the app's workflow.
L2003:         win.canvas = None
    -> general Python statement supporting the app's workflow.
L2004: 
    -> blank line (spacing/section separation).
L2005:         ctrl = ttk.Frame(win)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L2006:         ctrl.pack(fill=tk.X, padx=10, pady=8)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L2007: 
    -> blank line (spacing/section separation).
L2008:         # Search removed; use Multi-select to filter instead
    -> comment/doc note (helps humans; ignored by Python).
L2009:         # Config selection is handled via the Multi-select dialog (button below)
    -> comment/doc note (helps humans; ignored by Python).
L2010:         def open_multi_select_dialog():
    -> starts a function definition (reusable logic).
L2011:             dlg = tk.Toplevel(win)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L2012:             dlg.title('Select Config Names')
    -> general Python statement supporting the app's workflow.
L2013:             dlg.transient(win)
    -> general Python statement supporting the app's workflow.
L2014:             dlg.grab_set()
    -> general Python statement supporting the app's workflow.
L2015: 
    -> blank line (spacing/section separation).
L2016:             frame = ttk.Frame(dlg)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L2017:             frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L2018: 
    -> blank line (spacing/section separation).
L2019:             lbl = ttk.Label(frame, text='Select one or more Config Names:')
    -> Tkinter UI widget / layout statement (creates or configures UI).
L2020:             lbl.pack(anchor='w')
    -> general Python statement supporting the app's workflow.
L2021: 
    -> blank line (spacing/section separation).
L2022:             lb_frame = ttk.Frame(frame)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L2023:             lb_frame.pack(fill=tk.BOTH, expand=True)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L2024:             lb = tk.Listbox(lb_frame, selectmode=tk.EXTENDED, exportselection=False)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L2025:             sb = ttk.Scrollbar(lb_frame, orient='vertical', command=lb.yview)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L2026:             lb.configure(yscrollcommand=sb.set)
    -> general Python statement supporting the app's workflow.
L2027:             lb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L2028:             sb.pack(side=tk.RIGHT, fill=tk.Y)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L2029: 
    -> blank line (spacing/section separation).
L2030:             # Populate listbox from current pivot data
    -> comment/doc note (helps humans; ignored by Python).
L2031:             names = [n for n, _ in (win.pivot_data or [])]
    -> general Python statement supporting the app's workflow.
L2032:             for nm in names:
    -> loop (repeats logic across items).
L2033:                 lb.insert(tk.END, nm)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L2034: 
    -> blank line (spacing/section separation).
L2035:             # Pre-select any previously chosen names
    -> comment/doc note (helps humans; ignored by Python).
L2036:             if win.cfg_name_multiset:
    -> control flow decision (branches logic based on conditions).
L2037:                 for i, nm in enumerate(names):
    -> loop (repeats logic across items).
L2038:                     if nm in win.cfg_name_multiset:
    -> control flow decision (branches logic based on conditions).
L2039:                         lb.select_set(i)
    -> general Python statement supporting the app's workflow.
L2040: 
    -> blank line (spacing/section separation).
L2041:             ctrl_frame = ttk.Frame(frame)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L2042:             ctrl_frame.pack(fill=tk.X, pady=(6,0))
    -> Tkinter UI widget / layout statement (creates or configures UI).
L2043: 
    -> blank line (spacing/section separation).
L2044:             ttk.Label(ctrl_frame, text='Random N:').pack(side=tk.LEFT)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L2045:             spn = ttk.Spinbox(ctrl_frame, from_=1, to=max(1, len(names)), width=5)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L2046:             spn.set('1')
    -> general Python statement supporting the app's workflow.
L2047:             spn.pack(side=tk.LEFT, padx=(6, 8))
    -> Tkinter UI widget / layout statement (creates or configures UI).
L2048: 
    -> blank line (spacing/section separation).
L2049:             def do_random():
    -> starts a function definition (reusable logic).
L2050:                 try:
    -> error handling block (keeps app stable under bad inputs).
L2051:                     n = int(spn.get())
    -> general Python statement supporting the app's workflow.
L2052:                 except Exception:
    -> error handling block (keeps app stable under bad inputs).
L2053:                     n = 1
    -> general Python statement supporting the app's workflow.
L2054:                 n = max(1, min(n, len(names)))
    -> general Python statement supporting the app's workflow.
L2055:                 chosen = random.sample(names, n) if names else []
    -> general Python statement supporting the app's workflow.
L2056:                 lb.selection_clear(0, tk.END)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L2057:                 for nm in chosen:
    -> loop (repeats logic across items).
L2058:                     try:
    -> error handling block (keeps app stable under bad inputs).
L2059:                         idx = names.index(nm)
    -> general Python statement supporting the app's workflow.
L2060:                         lb.select_set(idx)
    -> general Python statement supporting the app's workflow.
L2061:                     except ValueError:
    -> error handling block (keeps app stable under bad inputs).
L2062:                         pass
    -> general Python statement supporting the app's workflow.
L2063: 
    -> blank line (spacing/section separation).
L2064:             ttk.Button(ctrl_frame, text='Random', command=do_random).pack(side=tk.LEFT, padx=(0,6))
    -> Tkinter UI widget / layout statement (creates or configures UI).
L2065: 
    -> blank line (spacing/section separation).
L2066:             btn_frame = ttk.Frame(frame)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L2067:             btn_frame.pack(fill=tk.X, pady=(8,0))
    -> Tkinter UI widget / layout statement (creates or configures UI).
L2068:             def on_ok():
    -> starts a function definition (reusable logic).
L2069:                 sel = [lb.get(i) for i in lb.curselection()]
    -> general Python statement supporting the app's workflow.
L2070:                 win.cfg_name_multiset = sel
    -> general Python statement supporting the app's workflow.
L2071:                 dlg.destroy()
    -> general Python statement supporting the app's workflow.
L2072:                 update_view()
    -> general Python statement supporting the app's workflow.
L2073: 
    -> blank line (spacing/section separation).
L2074:             def on_clear():
    -> starts a function definition (reusable logic).
L2075:                 win.cfg_name_multiset = []
    -> general Python statement supporting the app's workflow.
L2076:                 dlg.destroy()
    -> general Python statement supporting the app's workflow.
L2077:                 update_view()
    -> general Python statement supporting the app's workflow.
L2078: 
    -> blank line (spacing/section separation).
L2079:             ttk.Button(btn_frame, text='OK', command=on_ok).pack(side=tk.RIGHT, padx=6)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L2080:             ttk.Button(btn_frame, text='Clear', command=on_clear).pack(side=tk.RIGHT)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L2081: 
    -> blank line (spacing/section separation).
L2082:         ttk.Button(ctrl, text='Multi-select...', command=open_multi_select_dialog).pack(side=tk.LEFT, padx=(2,6))
    -> Tkinter UI widget / layout statement (creates or configures UI).
L2083: 
    -> blank line (spacing/section separation).
L2084:         ttk.Label(ctrl, text="Sort by:").pack(side=tk.LEFT)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L2085:         ttk.Radiobutton(ctrl, text="Count (desc)", value='count_desc', variable=win.sort_mode,
    -> Tkinter UI widget / layout statement (creates or configures UI).
L2086:                         command=lambda: update_view()).pack(side=tk.LEFT, padx=6)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L2087:         ttk.Radiobutton(ctrl, text="Config Name", value='name', variable=win.sort_mode,
    -> Tkinter UI widget / layout statement (creates or configures UI).
L2088:                         command=lambda: update_view()).pack(side=tk.LEFT, padx=6)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L2089: 
    -> blank line (spacing/section separation).
L2090:         # Top-N removed; show all selected items
    -> comment/doc note (helps humans; ignored by Python).
L2091: 
    -> blank line (spacing/section separation).
L2092:         ttk.Checkbutton(ctrl, text="Show values on bars", variable=win.show_values,
    -> Tkinter UI widget / layout statement (creates or configures UI).
L2093:                         command=lambda: update_view()).pack(side=tk.LEFT, padx=(6, 0))
    -> Tkinter UI widget / layout statement (creates or configures UI).
L2094: 
    -> blank line (spacing/section separation).
L2095:         ttk.Button(ctrl, text="Export Summary CSV", command=lambda: export_summary_csv()).pack(side=tk.RIGHT, padx=6)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L2096:         if HAS_MPL:
    -> control flow decision (branches logic based on conditions).
L2097:             ttk.Button(ctrl, text="Save Chart PNG", command=lambda: save_chart_png()).pack(side=tk.RIGHT, padx=6)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L2098:         # Grand total scope & toggle
    -> comment/doc note (helps humans; ignored by Python).
L2099:         ttk.Label(ctrl, text='Grand total:').pack(side=tk.RIGHT, padx=(8, 2))
    -> Tkinter UI widget / layout statement (creates or configures UI).
L2100:         ttk.Label(ctrl, textvariable=win.grand_total_var).pack(side=tk.RIGHT, padx=(2, 6))
    -> Tkinter UI widget / layout statement (creates or configures UI).
L2101:         cmb_scope = ttk.Combobox(ctrl, values=['All', 'Visible', 'Selected'], textvariable=win.total_scope, width=10,...
    -> Tkinter UI widget / layout statement (creates or configures UI).
L2102:         cmb_scope.pack(side=tk.RIGHT, padx=(2, 6))
    -> Tkinter UI widget / layout statement (creates or configures UI).
L2103:         cmb_scope.bind('<<ComboboxSelected>>', lambda e: update_view())
    -> general Python statement supporting the app's workflow.
L2104:         ttk.Checkbutton(ctrl, text='Show Grand Total', variable=win.show_total, command=lambda: update_view()).pack(s...
    -> Tkinter UI widget / layout statement (creates or configures UI).
L2105: 
    -> blank line (spacing/section separation).
L2106:         # Use horizontal split: left pane for Config names, right pane for Chart
    -> comment/doc note (helps humans; ignored by Python).
L2107:         body = ttk.PanedWindow(win, orient=tk.HORIZONTAL)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L2108:         body.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
    -> Tkinter UI widget / layout statement (creates or configures UI).
L2109: 
    -> blank line (spacing/section separation).
L2110:         tbl_frame = ttk.Frame(body)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L2111:         # give the table pane a smaller weight than the chart pane
    -> comment/doc note (helps humans; ignored by Python).
L2112:         body.add(tbl_frame, weight=1)
    -> general Python statement supporting the app's workflow.
L2113: 
    -> blank line (spacing/section separation).
L2114:         columns = ('Config Name', 'Count')
    -> general Python statement supporting the app's workflow.
L2115:         tree = ttk.Treeview(tbl_frame, columns=columns, show='headings', selectmode='extended')
    -> Tkinter UI widget / layout statement (creates or configures UI).
L2116:         tree.heading('Config Name', text='Config Name', command=lambda: set_sort('name'))
    -> general Python statement supporting the app's workflow.
L2117:         tree.heading('Count', text='Count', command=lambda: set_sort('count_desc'))
    -> general Python statement supporting the app's workflow.
L2118:         # narrower width for the left pane when using side-by-side layout
    -> comment/doc note (helps humans; ignored by Python).
L2119:         tree.column('Config Name', width=360, anchor='w')
    -> general Python statement supporting the app's workflow.
L2120:         tree.column('Count', width=80, anchor='e')
    -> general Python statement supporting the app's workflow.
L2121:         vs = ttk.Scrollbar(tbl_frame, orient='vertical', command=tree.yview)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L2122:         hs = ttk.Scrollbar(tbl_frame, orient='horizontal', command=tree.xview)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L2123:         tree.configure(yscroll=vs.set, xscroll=hs.set)
    -> general Python statement supporting the app's workflow.
L2124:         tree.grid(row=0, column=0, sticky='nsew')
    -> general Python statement supporting the app's workflow.
L2125:         vs.grid(row=0, column=1, sticky='ns')
    -> general Python statement supporting the app's workflow.
L2126:         # Reserve a row for the totals label below the table, move horizontal scrollbar below that
    -> comment/doc note (helps humans; ignored by Python).
L2127:         tbl_frame.rowconfigure(0, weight=1)
    -> general Python statement supporting the app's workflow.
L2128:         tbl_frame.columnconfigure(0, weight=1)
    -> general Python statement supporting the app's workflow.
L2129:         totals_frame = ttk.Frame(tbl_frame)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L2130:         totals_frame.grid(row=1, column=0, columnspan=2, sticky='ew')
    -> general Python statement supporting the app's workflow.
L2131:         hs.grid(row=2, column=0, sticky='ew')
    -> general Python statement supporting the app's workflow.
L2132:         tbl_frame.rowconfigure(2, weight=0)
    -> general Python statement supporting the app's workflow.
L2133: 
    -> blank line (spacing/section separation).
L2134:         def on_row_open(_evt=None):
    -> starts a function definition (reusable logic).
L2135:             sel = tree.selection()
    -> general Python statement supporting the app's workflow.
L2136:             if not sel:
    -> control flow decision (branches logic based on conditions).
L2137:                 return
    -> returns a value from a function/method.
L2138:             cfg_name = tree.item(sel[0], 'values')[0]
    -> general Python statement supporting the app's workflow.
L2139:             try:
    -> error handling block (keeps app stable under bad inputs).
L2140:                 self.cmb_name.set(cfg_name)
    -> general Python statement supporting the app's workflow.
L2141:                 self.on_name_selected()
    -> general Python statement supporting the app's workflow.
L2142:                 self.focus_set()
    -> general Python statement supporting the app's workflow.
L2143:             except Exception:
    -> error handling block (keeps app stable under bad inputs).
L2144:                 pass
    -> general Python statement supporting the app's workflow.
L2145:         tree.bind('<Double-1>', on_row_open)
    -> general Python statement supporting the app's workflow.
L2146:         tree.bind('<<TreeviewSelect>>', lambda e: update_view())
    -> general Python statement supporting the app's workflow.
L2147: 
    -> blank line (spacing/section separation).
L2148:         chart_frame = ttk.Frame(body)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L2149:         # chart pane gets more space
    -> comment/doc note (helps humans; ignored by Python).
L2150:         body.add(chart_frame, weight=2)
    -> general Python statement supporting the app's workflow.
L2151: 
    -> blank line (spacing/section separation).
L2152:         if not HAS_MPL:
    -> control flow decision (branches logic based on conditions).
L2153:             ttk.Label(chart_frame, text="Chart unavailable. Install matplotlib for visualization.").pack(pady=10)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L2154: 
    -> blank line (spacing/section separation).
L2155:         status = ttk.Label(chart_frame, text="Generating summary...")
    -> Tkinter UI widget / layout statement (creates or configures UI).
L2156:         status.pack(anchor='w', padx=6, pady=(6, 0))
    -> general Python statement supporting the app's workflow.
L2157:         # Bottom/table grand total label placed under the table
    -> comment/doc note (helps humans; ignored by Python).
L2158:         try:
    -> error handling block (keeps app stable under bad inputs).
L2159:             ttk.Label(totals_frame, textvariable=win.grand_total_var).pack(anchor='w', padx=6, pady=(6, 4))
    -> Tkinter UI widget / layout statement (creates or configures UI).
L2160:         except Exception:
    -> error handling block (keeps app stable under bad inputs).
L2161:             pass
    -> general Python statement supporting the app's workflow.
L2162: 
    -> blank line (spacing/section separation).
L2163:         def set_sort(mode: str):
    -> starts a function definition (reusable logic).
L2164:             if mode not in ('count_desc', 'name'):
    -> control flow decision (branches logic based on conditions).
L2165:                 return
    -> returns a value from a function/method.
L2166:             win.sort_mode.set(mode)
    -> general Python statement supporting the app's workflow.
L2167:             update_view()
    -> general Python statement supporting the app's workflow.
L2168: 
    -> blank line (spacing/section separation).
L2169:         def compute_pivot() -> List[Tuple[str, int]]:
    -> starts a function definition (reusable logic).
L2170:             if HAS_PANDAS:
    -> control flow decision (branches logic based on conditions).
L2171:                 try:
    -> error handling block (keeps app stable under bad inputs).
L2172:                     df = pd.DataFrame(self.rows)
    -> pandas data handling (read/transform tabular data).
L2173:                     if 'Config Name' not in df.columns:
    -> control flow decision (branches logic based on conditions).
L2174:                         return []
    -> returns a value from a function/method.
L2175:                     ser = df['Config Name'].fillna('').astype(str).str.strip()
    -> general Python statement supporting the app's workflow.
L2176:                     ser = ser[ser != '']
    -> general Python statement supporting the app's workflow.
L2177:                     ser = ser[ser.apply(lambda x: config.validate_config_name(x))]
    -> general Python statement supporting the app's workflow.
L2178:                     vc = ser.value_counts()
    -> general Python statement supporting the app's workflow.
L2179:                     return [(idx, int(cnt)) for idx, cnt in vc.items()]
    -> returns a value from a function/method.
L2180:                 except Exception as e:
    -> error handling block (keeps app stable under bad inputs).
L2181:                     logger.warning(f"Pandas pivot failed, falling back. Error: {e}")
    -> general Python statement supporting the app's workflow.
L2182: 
    -> blank line (spacing/section separation).
L2183:             counts: Dict[str, int] = {}
    -> general Python statement supporting the app's workflow.
L2184:             for r in self.rows:
    -> loop (repeats logic across items).
L2185:                 nm = (r.get('Config Name') or '').strip()
    -> general Python statement supporting the app's workflow.
L2186:                 if config.validate_config_name(nm): 
    -> control flow decision (branches logic based on conditions).
L2187:                     counts[nm] = counts.get(nm, 0) + 1
    -> general Python statement supporting the app's workflow.
L2188:             return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0].lower()))
    -> returns a value from a function/method.
L2189: 
    -> blank line (spacing/section separation).
L2190:         def populate_table(data: List[Tuple[str, int]]):
    -> starts a function definition (reusable logic).
L2191:             tree.delete(*tree.get_children())
    -> general Python statement supporting the app's workflow.
L2192:             for name, cnt in data:
    -> loop (repeats logic across items).
L2193:                 tree.insert('', tk.END, values=(name, cnt))
    -> Tkinter UI widget / layout statement (creates or configures UI).
L2194: 
    -> blank line (spacing/section separation).
L2195:         def shorten(label: str, maxlen: int = 26) -> str:
    -> starts a function definition (reusable logic).
L2196:             return label if len(label) <= maxlen else (label[:maxlen - 1] + "...")
    -> returns a value from a function/method.
L2197: 
    -> blank line (spacing/section separation).
L2198:         def apply_filters(data: List[Tuple[str, int]]) -> List[Tuple[str, int]]:
    -> starts a function definition (reusable logic).
L2199:             """Apply selection, sort, search, and Top-N to the pivot data."""
    -> docstring delimiter (module/docs block).
L2200:             manually_selected = False
    -> general Python statement supporting the app's workflow.
L2201: 
    -> blank line (spacing/section separation).
L2202:             # 1) Restrict to any configs the user explicitly selected in the table
    -> comment/doc note (helps humans; ignored by Python).
L2203:             try:
    -> error handling block (keeps app stable under bad inputs).
L2204:                 sel = tree.selection()
    -> general Python statement supporting the app's workflow.
L2205:                 if sel:
    -> control flow decision (branches logic based on conditions).
L2206:                     selected_names = {tree.item(i, 'values')[0] for i in sel}
    -> general Python statement supporting the app's workflow.
L2207:                     data = [d for d in data if d[0] in selected_names]
    -> general Python statement supporting the app's workflow.
L2208:                     manually_selected = True
    -> general Python statement supporting the app's workflow.
L2209:             except Exception:
    -> error handling block (keeps app stable under bad inputs).
L2210:                 manually_selected = False
    -> general Python statement supporting the app's workflow.
L2211: 
    -> blank line (spacing/section separation).
L2212:             # 2) Sort
    -> comment/doc note (helps humans; ignored by Python).
L2213:             mode = win.sort_mode.get()
    -> general Python statement supporting the app's workflow.
L2214:             if mode == 'name':
    -> control flow decision (branches logic based on conditions).
L2215:                 data = sorted(data, key=lambda kv: kv[0].lower())
    -> general Python statement supporting the app's workflow.
L2216:             else:
    -> control flow decision (branches logic based on conditions).
L2217:                 data = sorted(data, key=lambda kv: (-kv[1], kv[0].lower()))
    -> general Python statement supporting the app's workflow.
L2218: 
    -> blank line (spacing/section separation).
L2219:             # 3) Config-name multiselect filter (from dialog)
    -> comment/doc note (helps humans; ignored by Python).
L2220:             if getattr(win, 'cfg_name_multiset', None):
    -> control flow decision (branches logic based on conditions).
L2221:                 selset = {n.lower() for n in win.cfg_name_multiset}
    -> general Python statement supporting the app's workflow.
L2222:                 data = [d for d in data if d[0].lower() in selset]
    -> general Python statement supporting the app's workflow.
L2223:             # 4) No Top-N filtering (removed)
    -> comment/doc note (helps humans; ignored by Python).
L2224: 
    -> blank line (spacing/section separation).
L2225:             return data
    -> returns a value from a function/method.
L2226: 
    -> blank line (spacing/section separation).
L2227: 
    -> blank line (spacing/section separation).
L2228:         def draw_chart(data: List[Tuple[str, int]]):
    -> starts a function definition (reusable logic).
L2229:             if not HAS_MPL:
    -> control flow decision (branches logic based on conditions).
L2230:                 return
    -> returns a value from a function/method.
L2231: 
    -> blank line (spacing/section separation).
L2232:             for w in chart_frame.pack_slaves():
    -> loop (repeats logic across items).
L2233:                 if isinstance(w, ttk.Label) and w is not status:
    -> Tkinter UI widget / layout statement (creates or configures UI).
L2234:                     w.destroy()
    -> general Python statement supporting the app's workflow.
L2235:             if win.canvas:
    -> control flow decision (branches logic based on conditions).
L2236:                 try:
    -> error handling block (keeps app stable under bad inputs).
L2237:                     win.canvas.get_tk_widget().destroy()
    -> general Python statement supporting the app's workflow.
L2238:                 except Exception:
    -> error handling block (keeps app stable under bad inputs).
L2239:                     pass
    -> general Python statement supporting the app's workflow.
L2240:                 win.canvas = None
    -> general Python statement supporting the app's workflow.
L2241:                 win.figure = None
    -> general Python statement supporting the app's workflow.
L2242: 
    -> blank line (spacing/section separation).
L2243:             if not data:
    -> control flow decision (branches logic based on conditions).
L2244:                 ttk.Label(chart_frame, text="No data to chart (check filters).").pack(pady=10)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L2245:                 return
    -> returns a value from a function/method.
L2246: 
    -> blank line (spacing/section separation).
L2247:             names = [n for n, _ in data]
    -> general Python statement supporting the app's workflow.
L2248:             counts = [c for _, c in data]
    -> general Python statement supporting the app's workflow.
L2249:             ncat = len(names)
    -> general Python statement supporting the app's workflow.
L2250: 
    -> blank line (spacing/section separation).
L2251:             # Vertical bar chart
    -> comment/doc note (helps humans; ignored by Python).
L2252:             width = max(6.0, min(30.0, 0.40 * ncat + 3.0))
    -> general Python statement supporting the app's workflow.
L2253:             fig = Figure(figsize=(width, 6), dpi=100)
    -> general Python statement supporting the app's workflow.
L2254:             ax = fig.add_subplot(111)
    -> general Python statement supporting the app's workflow.
L2255: 
    -> blank line (spacing/section separation).
L2256:             x = list(range(ncat))
    -> general Python statement supporting the app's workflow.
L2257:             ax.bar(x, counts)
    -> general Python statement supporting the app's workflow.
L2258: 
    -> blank line (spacing/section separation).
L2259:             labels = [shorten(n, 38) for n in names]
    -> general Python statement supporting the app's workflow.
L2260:             fs = 10 if ncat <= 10 else 9 if ncat <= 20 else 8 if ncat <= 40 else 7
    -> general Python statement supporting the app's workflow.
L2261:             ax.set_xticks(x)
    -> general Python statement supporting the app's workflow.
L2262:             ax.set_xticklabels(labels, rotation=45, ha='right', fontsize=fs)
    -> general Python statement supporting the app's workflow.
L2263: 
    -> blank line (spacing/section separation).
L2264:             ax.set_ylabel("Count")
    -> general Python statement supporting the app's workflow.
L2265:             ax.set_xlabel("Config Name")
    -> general Python statement supporting the app's workflow.
L2266:             ax.set_title("Rows per Config Name")
    -> general Python statement supporting the app's workflow.
L2267:             ax.margins(y=0.05)
    -> general Python statement supporting the app's workflow.
L2268: 
    -> blank line (spacing/section separation).
L2269:             if win.show_values.get():
    -> control flow decision (branches logic based on conditions).
L2270:                 ymax = max(counts) if counts else 0
    -> general Python statement supporting the app's workflow.
L2271:                 offset = 0.01 * (ymax or 1)
    -> general Python statement supporting the app's workflow.
L2272:                 for i, v in enumerate(counts):
    -> loop (repeats logic across items).
L2273:                     ax.text(i, v + offset, str(v), ha='center', va='bottom', fontsize=max(8, fs-1))
    -> general Python statement supporting the app's workflow.
L2274: 
    -> blank line (spacing/section separation).
L2275:             fig.tight_layout()
    -> general Python statement supporting the app's workflow.
L2276: 
    -> blank line (spacing/section separation).
L2277:             win.figure = fig
    -> general Python statement supporting the app's workflow.
L2278:             win.canvas = FigureCanvasTkAgg(fig, master=chart_frame)
    -> general Python statement supporting the app's workflow.
L2279:             win.canvas.draw()
    -> general Python statement supporting the app's workflow.
L2280:             win.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=4, pady=6)
    -> Tkinter UI widget / layout statement (creates or configures UI).
L2281: 
    -> blank line (spacing/section separation).
L2282:         def export_summary_csv():
    -> starts a function definition (reusable logic).
L2283:             if not win.pivot_data:
    -> control flow decision (branches logic based on conditions).
L2284:                 messagebox.showinfo("Export", "No summary data.")
    -> general Python statement supporting the app's workflow.
L2285:                 return
    -> returns a value from a function/method.
L2286:             p = filedialog.asksaveasfilename(
    -> general Python statement supporting the app's workflow.
L2287:                 title='Save Summary as CSV',
    -> general Python statement supporting the app's workflow.
L2288:                 initialdir=self._get_initial_open_dir(),
    -> general Python statement supporting the app's workflow.
L2289:                 defaultextension='.csv',
    -> general Python statement supporting the app's workflow.
L2290:                 filetypes=[('CSV', '*.csv')]
    -> general Python statement supporting the app's workflow.
L2291:             )
    -> general Python statement supporting the app's workflow.
L2292:             if not p: return
    -> control flow decision (branches logic based on conditions).
L2293:             try:
    -> error handling block (keeps app stable under bad inputs).
L2294:                 with open(p, 'w', encoding='utf-8', newline='') as f:
    -> general Python statement supporting the app's workflow.
L2295:                     w = csv.writer(f)
    -> general Python statement supporting the app's workflow.
L2296:                     w.writerow(['Config Name', 'Count'])
    -> general Python statement supporting the app's workflow.
L2297:                     for name, cnt in apply_filters(list(win.pivot_data)):
    -> loop (repeats logic across items).
L2298:                         w.writerow([name, cnt])
    -> general Python statement supporting the app's workflow.
L2299:                 messagebox.showinfo("Export", f"Summary saved to:\n{p}")
    -> general Python statement supporting the app's workflow.
L2300:                 logger.info(f"Exported summary CSV: {p}")
    -> general Python statement supporting the app's workflow.
L2301:             except Exception as e:
    -> error handling block (keeps app stable under bad inputs).
L2302:                 messagebox.showerror("Export", f"Failed to write CSV:\n{e}")
    -> general Python statement supporting the app's workflow.
L2303:                 logger.error(f"Failed to export summary CSV: {e}")
    -> general Python statement supporting the app's workflow.
L2304: 
    -> blank line (spacing/section separation).
L2305:         def save_chart_png():
    -> starts a function definition (reusable logic).
L2306:             if not HAS_MPL or not win.figure:
    -> control flow decision (branches logic based on conditions).
L2307:                 messagebox.showinfo("Chart", "Chart unavailable.")
    -> general Python statement supporting the app's workflow.
L2308:                 return
    -> returns a value from a function/method.
L2309:             p = filedialog.asksaveasfilename(
    -> general Python statement supporting the app's workflow.
L2310:                 title='Save Chart as PNG',
    -> general Python statement supporting the app's workflow.
L2311:                 initialdir=self._get_initial_open_dir(),
    -> general Python statement supporting the app's workflow.
L2312:                 defaultextension='.png',
    -> general Python statement supporting the app's workflow.
L2313:                 filetypes=[('PNG', '*.png')]
    -> general Python statement supporting the app's workflow.
L2314:             )
    -> general Python statement supporting the app's workflow.
L2315:             if not p: return
    -> control flow decision (branches logic based on conditions).
L2316:             try:
    -> error handling block (keeps app stable under bad inputs).
L2317:                 win.figure.savefig(p, dpi=150, bbox_inches='tight')
    -> general Python statement supporting the app's workflow.
L2318:                 messagebox.showinfo("Chart", f"Chart saved to:\n{p}")
    -> general Python statement supporting the app's workflow.
L2319:                 logger.info(f"Saved chart PNG: {p}")
    -> general Python statement supporting the app's workflow.
L2320:             except Exception as e:
    -> error handling block (keeps app stable under bad inputs).
L2321:                 messagebox.showerror("Chart", f"Failed to save chart:\n{e}")
    -> general Python statement supporting the app's workflow.
L2322:                 logger.error(f"Failed to save chart PNG: {e}")
    -> general Python statement supporting the app's workflow.
L2323: 
    -> blank line (spacing/section separation).
L2324:         def update_view(*_):
    -> starts a function definition (reusable logic).
L2325:             # Apply filters & selection to pivot_data and refresh table + chart
    -> comment/doc note (helps humans; ignored by Python).
L2326:             data = apply_filters(list(win.pivot_data))
    -> general Python statement supporting the app's workflow.
L2327:             populate_table(data)
    -> general Python statement supporting the app's workflow.
L2328:             draw_chart(data)
    -> general Python statement supporting the app's workflow.
L2329: 
    -> blank line (spacing/section separation).
L2330:             # Grand totals are based on the full pivot (before filters)
    -> comment/doc note (helps humans; ignored by Python).
L2331:             pivot_map = {name: cnt for name, cnt in win.pivot_data} if win.pivot_data else {}
    -> general Python statement supporting the app's workflow.
L2332: 
    -> blank line (spacing/section separation).
L2333:             # If the user has an active multiselect, always use that as the source
    -> comment/doc note (helps humans; ignored by Python).
L2334:             # of truth for totals (this is the requested behavior).
    -> comment/doc note (helps humans; ignored by Python).
L2335:             if getattr(win, 'cfg_name_multiset', None):
    -> control flow decision (branches logic based on conditions).
L2336:                 mult = list(win.cfg_name_multiset)
    -> general Python statement supporting the app's workflow.
L2337:                 total_cfg = len(mult)
    -> general Python statement supporting the app's workflow.
L2338:                 total_rows = sum(pivot_map.get(n, 0) for n in mult)
    -> general Python statement supporting the app's workflow.
L2339:             else:
    -> control flow decision (branches logic based on conditions).
L2340:                 # Compute totals according to scope selection when no multiselect
    -> comment/doc note (helps humans; ignored by Python).
L2341:                 scope = (win.total_scope.get() or 'All').lower()
    -> general Python statement supporting the app's workflow.
L2342:                 if scope == 'visible':
    -> control flow decision (branches logic based on conditions).
L2343:                     total_cfg = len(data)
    -> general Python statement supporting the app's workflow.
L2344:                     total_rows = sum(cnt for _, cnt in data) if data else 0
    -> general Python statement supporting the app's workflow.
L2345:                 elif scope == 'selected':
    -> control flow decision (branches logic based on conditions).
L2346:                     sel = tree.selection()
    -> general Python statement supporting the app's workflow.
L2347:                     selected_names = [tree.item(i, 'values')[0] for i in sel] if sel else []
    -> general Python statement supporting the app's workflow.
L2348:                     total_cfg = len(selected_names)
    -> general Python statement supporting the app's workflow.
L2349:                     total_rows = sum(pivot_map.get(n, 0) for n in selected_names)
    -> general Python statement supporting the app's workflow.
L2350:                 else:  # 'all' or default
    -> control flow decision (branches logic based on conditions).
L2351:                     total_cfg = len(win.pivot_data)
    -> general Python statement supporting the app's workflow.
L2352:                     total_rows = sum(cnt for _, cnt in win.pivot_data) if win.pivot_data else 0
    -> general Python statement supporting the app's workflow.
L2353:             # Update toolbar and bottom grand total display
    -> comment/doc note (helps humans; ignored by Python).
L2354:             try:
    -> error handling block (keeps app stable under bad inputs).
L2355:                 if win.show_total.get():
    -> control flow decision (branches logic based on conditions).
L2356:                     win.grand_total_var.set(f"{total_cfg} configs, {total_rows:,} rows")
    -> general Python statement supporting the app's workflow.
L2357:                 else:
    -> control flow decision (branches logic based on conditions).
L2358:                     win.grand_total_var.set("")
    -> general Python statement supporting the app's workflow.
L2359:             except Exception:
    -> error handling block (keeps app stable under bad inputs).
L2360:                 pass
    -> general Python statement supporting the app's workflow.
L2361: 
    -> blank line (spacing/section separation).
L2362:             try:
    -> error handling block (keeps app stable under bad inputs).
L2363:                 status.configure(text=f"Summary ready. {total_cfg} group(s). Showing {len(data)}.")
    -> general Python statement supporting the app's workflow.
L2364:             except tk.TclError:
    -> Tkinter UI widget / layout statement (creates or configures UI).
L2365:                 # status may also have been removed; ignore if it's gone
    -> comment/doc note (helps humans; ignored by Python).
L2366:                 pass
    -> general Python statement supporting the app's workflow.
L2367: 
    -> blank line (spacing/section separation).
L2368:         # search box removed; no trace needed
    -> comment/doc note (helps humans; ignored by Python).
L2369: 
    -> blank line (spacing/section separation).
L2370:         def worker():
    -> starts a function definition (reusable logic).
L2371:             try:
    -> error handling block (keeps app stable under bad inputs).
L2372:                 data = compute_pivot()
    -> general Python statement supporting the app's workflow.
L2373:                 self.after(0, lambda: after_pivot_ready(data))
    -> general Python statement supporting the app's workflow.
L2374:             except Exception as e:
    -> error handling block (keeps app stable under bad inputs).
L2375:                 logger.error(f"Summary pivot worker failed: {e}")
    -> general Python statement supporting the app's workflow.
L2376:                 self.after(0, lambda: status.configure(text=f"Error generating summary: {e}"))
    -> general Python statement supporting the app's workflow.
L2377: 
    -> blank line (spacing/section separation).
L2378:         def after_pivot_ready(data: List[Tuple[str, int]]):
    -> starts a function definition (reusable logic).
L2379:             win.pivot_data = data
    -> general Python statement supporting the app's workflow.
L2380:             # Populate any selection UI if needed (multiselect dialog reads pivot_data)
    -> comment/doc note (helps humans; ignored by Python).
L2381:             update_view()
    -> general Python statement supporting the app's workflow.
L2382: 
    -> blank line (spacing/section separation).
L2383:         threading.Thread(target=worker, daemon=True).start()
    -> general Python statement supporting the app's workflow.
L2384: 
    -> blank line (spacing/section separation).
L2385:     # ---------------- END SUMMARY DASHBOARD ----------------
    -> comment/doc note (helps humans; ignored by Python).
L2386: 
    -> blank line (spacing/section separation).
L2387: # -------------------
    -> comment/doc note (helps humans; ignored by Python).
L2388: # Main entrypoint
    -> comment/doc note (helps humans; ignored by Python).
L2389: # -------------------
    -> comment/doc note (helps humans; ignored by Python).
L2390: 
    -> blank line (spacing/section separation).
L2391: if __name__ == '__main__':
    -> control flow decision (branches logic based on conditions).
L2392:     import argparse
    -> imports a module/symbol used later (keeps code organized).
L2393: 
    -> blank line (spacing/section separation).
L2394:     # Ensure pandas is available, or give a final warning
    -> comment/doc note (helps humans; ignored by Python).
L2395:     if not HAS_PANDAS:
    -> control flow decision (branches logic based on conditions).
L2396:         print("CRITICAL: pandas is not installed. This application requires it for "
    -> pandas data handling (read/transform tabular data).
L2397:               "efficient file loading.")
    -> general Python statement supporting the app's workflow.
L2398:         print("Please install required libraries:")
    -> general Python statement supporting the app's workflow.
L2399:         print("pip install pandas numpy openpyxl deepdiff matplotlib")
    -> pandas data handling (read/transform tabular data).
L2400:         # You could choose to exit here, or let the Tkinter warning handle it
    -> comment/doc note (helps humans; ignored by Python).
L2401:         # sys.exit(1)
    -> comment/doc note (helps humans; ignored by Python).
L2402: 
    -> blank line (spacing/section separation).
L2403:     # Parse command-line arguments for auto-loading files
    -> comment/doc note (helps humans; ignored by Python).
L2404:     parser = argparse.ArgumentParser(
    -> general Python statement supporting the app's workflow.
L2405:         description='Payload Diff Viewer - Compare current vs old payload configurations',
    -> general Python statement supporting the app's workflow.
L2406:         formatter_class=argparse.RawDescriptionHelpFormatter,
    -> general Python statement supporting the app's workflow.
L2407:         epilog="""
    -> general Python statement supporting the app's workflow.
L2408: Examples:
    -> general Python statement supporting the app's workflow.
L2409:   python GeminiPayloadDiff.py
    -> general Python statement supporting the app's workflow.
L2410:   python GeminiPayloadDiff.py data.csv
    -> general Python statement supporting the app's workflow.
L2411:   python GeminiPayloadDiff.py --open data.xlsx
    -> general Python statement supporting the app's workflow.
L2412:   python GeminiPayloadDiff.py -o export.csv
    -> general Python statement supporting the app's workflow.
L2413:   python GeminiPayloadDiff.py --file payload_export.xlsx
    -> general Python statement supporting the app's workflow.
L2414:         """
    -> docstring delimiter (module/docs block).
L2415:     )
    -> general Python statement supporting the app's workflow.
L2416: 
    -> blank line (spacing/section separation).
L2417:     parser.add_argument(
    -> general Python statement supporting the app's workflow.
L2418:         'file', 
    -> general Python statement supporting the app's workflow.
L2419:         nargs='?', 
    -> general Python statement supporting the app's workflow.
L2420:         help='CSV or XLSX file to open automatically'
    -> general Python statement supporting the app's workflow.
L2421:     )
    -> general Python statement supporting the app's workflow.
L2422: 
    -> blank line (spacing/section separation).
L2423:     parser.add_argument(
    -> general Python statement supporting the app's workflow.
L2424:         '--open', '-o',
    -> general Python statement supporting the app's workflow.
L2425:         dest='open_file',
    -> general Python statement supporting the app's workflow.
L2426:         help='CSV or XLSX file to open automatically'
    -> general Python statement supporting the app's workflow.
L2427:     )
    -> general Python statement supporting the app's workflow.
L2428: 
    -> blank line (spacing/section separation).
L2429:     parser.add_argument(
    -> general Python statement supporting the app's workflow.
L2430:         '--file', '-f',
    -> general Python statement supporting the app's workflow.
L2431:         dest='file_arg',
    -> general Python statement supporting the app's workflow.
L2432:         help='CSV or XLSX file to open automatically'
    -> general Python statement supporting the app's workflow.
L2433:     )
    -> general Python statement supporting the app's workflow.
L2434: 
    -> blank line (spacing/section separation).
L2435:     args = parser.parse_args()
    -> general Python statement supporting the app's workflow.
L2436: 
    -> blank line (spacing/section separation).
L2437:     # Determine which file to open (supports multiple argument formats)
    -> comment/doc note (helps humans; ignored by Python).
L2438:     file_to_open = args.file or args.open_file or args.file_arg
    -> general Python statement supporting the app's workflow.
L2439: 
    -> blank line (spacing/section separation).
L2440:     # Create the app
    -> comment/doc note (helps humans; ignored by Python).
L2441:     app = PayloadDiffViewerApp()
    -> general Python statement supporting the app's workflow.
L2442: 
    -> blank line (spacing/section separation).
L2443:     # Auto-load file if specified via command line
    -> comment/doc note (helps humans; ignored by Python).
L2444:     if file_to_open:
    -> control flow decision (branches logic based on conditions).
L2445:         import os
    -> imports a module/symbol used later (keeps code organized).
L2446:         file_path = os.path.abspath(file_to_open)
    -> general Python statement supporting the app's workflow.
L2447: 
    -> blank line (spacing/section separation).
L2448:         if os.path.exists(file_path):
    -> control flow decision (branches logic based on conditions).
L2449:             # Schedule the auto-load by simulating the file dialog response
    -> comment/doc note (helps humans; ignored by Python).
L2450:             def auto_load():
    -> starts a function definition (reusable logic).
L2451:                 try:
    -> error handling block (keeps app stable under bad inputs).
L2452:                     logger.info(f"Auto-loading file from command line: {file_path}")
    -> general Python statement supporting the app's workflow.
L2453: 
    -> blank line (spacing/section separation).
L2454:                     # Temporarily replace filedialog.askopenfilename to return our file path
    -> comment/doc note (helps humans; ignored by Python).
L2455:                     original_askopenfilename = filedialog.askopenfilename
    -> general Python statement supporting the app's workflow.
L2456:                     filedialog.askopenfilename = lambda **kwargs: file_path
    -> general Python statement supporting the app's workflow.
L2457: 
    -> blank line (spacing/section separation).
L2458:                     # Call on_open() method - THE CORRECT METHOD NAME
    -> comment/doc note (helps humans; ignored by Python).
L2459:                     app.on_open()
    -> general Python statement supporting the app's workflow.
L2460: 
    -> blank line (spacing/section separation).
L2461:                     # Restore the original filedialog function
    -> comment/doc note (helps humans; ignored by Python).
L2462:                     filedialog.askopenfilename = original_askopenfilename
    -> general Python statement supporting the app's workflow.
L2463: 
    -> blank line (spacing/section separation).
L2464:                 except Exception as e:
    -> error handling block (keeps app stable under bad inputs).
L2465:                     logger.error(f"Failed to auto-load file: {e}")
    -> general Python statement supporting the app's workflow.
L2466:                     import traceback
    -> imports a module/symbol used later (keeps code organized).
L2467:                     traceback.print_exc()
    -> general Python statement supporting the app's workflow.
L2468:                     messagebox.showerror(
    -> general Python statement supporting the app's workflow.
L2469:                         "Auto-Load Failed",
    -> general Python statement supporting the app's workflow.
L2470:                         f"Could not load the specified file:\n\n{file_path}\n\nError: {e}\n\nPlease use File > Open t...
    -> general Python statement supporting the app's workflow.
L2471:                     )
    -> general Python statement supporting the app's workflow.
L2472: 
    -> blank line (spacing/section separation).
L2473:             # Wait for GUI to fully initialize (500ms) before triggering auto-load
    -> comment/doc note (helps humans; ignored by Python).
L2474:             app.after(500, auto_load)
    -> general Python statement supporting the app's workflow.
L2475:         else:
    -> control flow decision (branches logic based on conditions).
L2476:             logger.error(f"File not found: {file_path}")
    -> general Python statement supporting the app's workflow.
L2477:             def show_error():
    -> starts a function definition (reusable logic).
L2478:                 messagebox.showerror(
    -> general Python statement supporting the app's workflow.
L2479:                     "File Not Found",
    -> general Python statement supporting the app's workflow.
L2480:                     f"Could not find the specified file:\n\n{file_path}\n\nPlease use File > Open to load a file."
    -> general Python statement supporting the app's workflow.
L2481:                 )
    -> general Python statement supporting the app's workflow.
L2482:             app.after(500, show_error)
    -> general Python statement supporting the app's workflow.
L2483: 
    -> blank line (spacing/section separation).
L2484:     app.mainloop()
    -> general Python statement supporting the app's workflow.
