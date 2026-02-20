# -*- coding: utf-8 -*-
"""
Full PyQt conversion for GeminiPayloadDiff (core parity)

This file implements a PyQt6/PyQt5-compatible frontend that aims to
mirror the key features from the Tkinter app:
- Open CSV/Excel files via existing FileLoader
- Column auto-mapping with mapping editor
- Config Name selector + Config Key multi-select
- Compare using Qt-native QThread workers + signals
- Diff tree, inline diff panes, full JSON panes
- Export CSV and parse-log viewer
- Optional matplotlib summary panel (if matplotlib available)

It reuses helper functions from the original module when available
(`GeminiPayloadDiff_GeminiUltra_FIXED_optimized_FIXED.py`).

Run:
    pip install PyQt6 deepdiff pandas openpyxl matplotlib
    python GeminiPayloadDiff_GeminiUltra_FIXED_optimized_FULL_PyQt.py

"""

from __future__ import annotations
import sys
import os
import json
import logging
from typing import Any, Dict, List, Tuple, Optional

# Try Qt bindings
PYQT_VER = None
try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QFileDialog, QMessageBox, QTreeWidget, QTreeWidgetItem,
        QTextEdit, QPushButton, QComboBox, QListWidget, QVBoxLayout, QWidget, QHBoxLayout,
        QLabel, QProgressBar, QSplitter, QToolBar, QDialog, QFormLayout, QLineEdit,
        QDialogButtonBox, QTableWidget, QTableWidgetItem, QSizePolicy
    )
    from PyQt6.QtCore import Qt, QThread, pyqtSignal as Signal
    # QAction lives in QtGui for PyQt6
    from PyQt6.QtGui import QAction
    # QSizePolicy enums moved under QSizePolicy.Policy in PyQt6
    _QSIZEPOLICY_EXPANDING = getattr(QSizePolicy, 'Policy', QSizePolicy).Expanding
    PYQT_VER = 6
except Exception:
    try:
        from PyQt5.QtWidgets import (
            QApplication, QMainWindow, QFileDialog, QMessageBox, QTreeWidget, QTreeWidgetItem,
            QTextEdit, QPushButton, QComboBox, QListWidget, QVBoxLayout, QWidget, QHBoxLayout,
            QLabel, QProgressBar, QSplitter, QToolBar, QAction, QDialog, QFormLayout, QLineEdit,
            QDialogButtonBox, QTableWidget, QTableWidgetItem, QSizePolicy
        )
        from PyQt5.QtCore import Qt, QThread, pyqtSignal as Signal
        PYQT_VER = 5
    except Exception:
        PYQT_VER = None

if PYQT_VER is None:
    raise ModuleNotFoundError("PyQt5 or PyQt6 required. Install PyQt6 or PyQt5 in your venv.")

# Compatibility aliases for dialog return codes
try:
    if PYQT_VER == 6:
        DIALOG_ACCEPTED = QDialog.DialogCode.Accepted
        DIALOG_REJECTED = QDialog.DialogCode.Rejected
    else:
        DIALOG_ACCEPTED = QDialog.Accepted
        DIALOG_REJECTED = QDialog.Rejected
except Exception:
    DIALOG_ACCEPTED = 1
    DIALOG_REJECTED = 0

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to reuse original helpers
_helpers = None
try:
    import GeminiPayloadDiff_GeminiUltra_FIXED_optimized_FIXED as core
    _helpers = core
except Exception:
    _helpers = None

# Try to use TestNew.FileLoader if available
try:
    from TestNew import FileLoader
except Exception:
    FileLoader = None

# Try DeepDiff
try:
    from deepdiff import DeepDiff
except Exception:
    DeepDiff = None

# Optional matplotlib
HAS_MPL = False
try:
    import matplotlib
    matplotlib.use('QtAgg')
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    HAS_MPL = True
except Exception:
    HAS_MPL = False


def pretty_json(obj: Any) -> str:
    if obj is None:
        return ""
    try:
        return json.dumps(obj, indent=2, ensure_ascii=False)
    except Exception:
        return str(obj)


class MappingEditor(QDialog):
    """Dialog to inspect/modify detected mapping (column index -> meaning)
    Exposes simple table of mapping keys -> column index and header name.
    """
    def __init__(self, parent, headers: List[str], mapping: Dict[str, int]):
        super().__init__(parent)
        self.setWindowTitle('Edit Column Mapping')
        self.headers = headers
        self.mapping = dict(mapping)
        self.resize(700, 420)

        layout = QVBoxLayout()
        form = QFormLayout()

        self.table = QTableWidget(len(self.mapping), 3)
        self.table.setHorizontalHeaderLabels(['Field', 'Column Index', 'Header Preview'])
        # use compatibility alias for Expanding policy (PyQt6 uses QSizePolicy.Policy.Expanding)
        try:
            self.table.setSizePolicy(_QSIZEPOLICY_EXPANDING, _QSIZEPOLICY_EXPANDING)
        except Exception:
            # fallback to attribute access if alias failed
            try:
                self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            except Exception:
                pass

        for i, (k, v) in enumerate(self.mapping.items()):
            self.table.setItem(i, 0, QTableWidgetItem(k))
            self.table.setItem(i, 1, QTableWidgetItem(str(v)))
            preview = headers[v] if (v is not None and v < len(headers)) else ''
            self.table.setItem(i, 2, QTableWidgetItem(preview))

        layout.addWidget(self.table)

        # QDialogButtonBox enum names differ between PyQt5 and PyQt6
        try:
            if PYQT_VER == 6:
                sb = QDialogButtonBox.StandardButton
                buttons = QDialogButtonBox(sb.Ok | sb.Cancel)
            else:
                buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        except Exception:
            # final fallback: construct default button box
            buttons = QDialogButtonBox()
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def get_mapping(self) -> Dict[str, int]:
        out = {}
        for r in range(self.table.rowCount()):
            k = self.table.item(r, 0).text().strip()
            try:
                v = int(self.table.item(r, 1).text().strip())
            except Exception:
                v = None
            out[k] = v
        return out


class Worker(QThread):
    """Qt-native worker thread that computes diffs and emits signals.

    Signals:
        result(cfgkey:str, old_obj, new_obj, diffs:list)
        parse_log(msg:str, level:str, context:str)
        finished()  # thread finished
    """
    result = Signal(str, object, object, list)
    parse_log = Signal(str, str, str)
    finished = Signal()

    def __init__(self, rows_items: List[Tuple[str, Dict[str, str]]], ignore_order: bool = False):
        super().__init__()
        self.rows_items = rows_items
        self.ignore_order = ignore_order
        self._stop_requested = False

    def stop(self):
        self._stop_requested = True

    def run(self):
        for cfgkey, row in self.rows_items:
            if self._stop_requested:
                break
            old_s = row.get('OLD PAYLOAD', '')
            cur_s = row.get('CURRENT PAYLOAD', '')

            # Parse using helpers if available
            old_obj = None
            cur_obj = None
            err1 = ''
            err2 = ''
            if _helpers and hasattr(_helpers, 'parse_jsonish_verbose'):
                try:
                    old_obj, err1 = _helpers.parse_jsonish_verbose(old_s)
                except Exception as e:
                    err1 = str(e)
                try:
                    cur_obj, err2 = _helpers.parse_jsonish_verbose(cur_s)
                except Exception as e:
                    err2 = str(e)
            else:
                # best effort
                try:
                    old_obj = json.loads(old_s) if old_s and old_s.strip() else None
                except Exception:
                    try:
                        import ast
                        old_obj = ast.literal_eval(old_s) if old_s and old_s.strip() else None
                    except Exception as e:
                        old_obj = None
                        err1 = str(e)
                try:
                    cur_obj = json.loads(cur_s) if cur_s and cur_s.strip() else None
                except Exception:
                    try:
                        import ast
                        cur_obj = ast.literal_eval(cur_s) if cur_s and cur_s.strip() else None
                    except Exception as e:
                        cur_obj = None
                        err2 = str(e)

            if err1:
                self.parse_log.emit(f"[{cfgkey}] OLD: {err1}", 'warning', (old_s or '')[:200])
            if err2:
                self.parse_log.emit(f"[{cfgkey}] CURRENT: {err2}", 'warning', (cur_s or '')[:200])

            diffs = []
            if DeepDiff is None:
                if old_obj != cur_obj:
                    diffs.append(('changed', '', old_obj, cur_obj))
            else:
                try:
                    dd = DeepDiff(old_obj, cur_obj, ignore_order=self.ignore_order, verbose_level=2)
                except Exception as e:
                    self.parse_log.emit(f"[{cfgkey}] DeepDiff failed: {e}", 'error', '')
                    self.result.emit(cfgkey, old_obj, cur_obj, [])
                    continue

                # Collect diffs
                for path, change in dd.get('values_changed', {}).items():
                    diffs.append(('changed', path, change.get('old_value'), change.get('new_value')))
                for path, change in dd.get('type_changes', {}).items():
                    diffs.append(('changed', path, change.get('old_value'), change.get('new_value')))
                for path in dd.get('dictionary_item_added', set()):
                    val = None
                    if _helpers and hasattr(_helpers, 'value_from_path'):
                        try:
                            val = _helpers.value_from_path(cur_obj, path)
                        except Exception:
                            val = None
                    diffs.append(('added', path, None, val))
                for path in dd.get('dictionary_item_removed', set()):
                    val = None
                    if _helpers and hasattr(_helpers, 'value_from_path'):
                        try:
                            val = _helpers.value_from_path(old_obj, path)
                        except Exception:
                            val = None
                    diffs.append(('removed', path, val, None))

            self.result.emit(cfgkey, old_obj, cur_obj, diffs)

        self.finished.emit()


class ParseLogViewer(QDialog):
    def __init__(self, parent, parse_entries: List[Dict[str, Any]]):
        super().__init__(parent)
        self.setWindowTitle('Parse Log')
        self.resize(900, 500)
        layout = QVBoxLayout()
        self.txt = QTextEdit()
        self.txt.setReadOnly(True)
        layout.addWidget(self.txt)
        self.setLayout(layout)
        self.set_entries(parse_entries)

    def set_entries(self, entries: List[Dict[str, Any]]):
        if not entries:
            self.txt.setPlainText('No parse log entries')
            return
        lines = []
        for e in entries[-200:]:
            ts = e.get('timestamp')
            lvl = e.get('level')
            msg = e.get('message')
            ctx = e.get('context')
            lines.append(f"[{lvl.upper()}] {msg}")
            if ctx:
                lines.append(f"  Context: {ctx}")
        self.txt.setPlainText('\n'.join(lines))


class ParseLogger:
    """Lightweight parse logger used by FileLoader when present.

    Stores entries as dicts with keys: timestamp, level, message, context.
    """
    def __init__(self):
        self.entries: List[Dict[str, Any]] = []

    def log(self, message: str, level: str = 'warning', context: Optional[str] = None):
        import datetime
        self.entries.append({
            'timestamp': datetime.datetime.utcnow().isoformat() + 'Z',
            'level': level,
            'message': str(message),
            'context': context,
        })

    def get_entries(self) -> List[Dict[str, Any]]:
        return list(self.entries)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Payload Diff Viewer - PyQt Full')
        self.resize(1300, 900)

        self.loader = FileLoader(ParseLogger() if FileLoader else None) if FileLoader else None
        self.rows: List[Dict[str, str]] = []
        self.by_name: Dict[str, List[int]] = {}
        self.full_payloads_cache: Dict[str, Tuple[Any, Any]] = {}
        self.parse_entries: List[Dict[str, Any]] = []

        self.workers: List[Worker] = []

        self._build_ui()

    def _build_ui(self):
        toolbar = QToolBar('Main')
        self.addToolBar(toolbar)
        act_open = QAction('Open', self)
        act_open.setShortcut('Ctrl+O')
        act_open.triggered.connect(self.on_open)
        toolbar.addAction(act_open)
        act_export = QAction('Export CSV', self)
        act_export.setShortcut('Ctrl+E')
        act_export.triggered.connect(self.on_export_csv)
        toolbar.addAction(act_export)
        act_export_txt = QAction('Export TXT', self)
        act_export_txt.triggered.connect(self.on_export_txt)
        toolbar.addAction(act_export_txt)
        act_parselog = QAction('Parse Log', self)
        act_parselog.setShortcut('Ctrl+L')
        act_parselog.triggered.connect(self.on_show_parse_log)
        toolbar.addAction(act_parselog)
        act_exit = QAction('Exit', self)
        act_exit.setShortcut('Ctrl+Q')
        act_exit.triggered.connect(self.close)
        toolbar.addAction(act_exit)

        central = QWidget()
        layout = QVBoxLayout()
        central.setLayout(layout)

        top_h = QHBoxLayout()
        top_h.addWidget(QLabel('Config Name:'))
        self.cmb_name = QComboBox()
        self.cmb_name.currentIndexChanged.connect(self.on_name_selected)
        top_h.addWidget(self.cmb_name)

        top_h.addWidget(QLabel('Filter Keys:'))
        # QLineEdit import compatible with PyQt6/PyQt5
        try:
            if PYQT_VER == 6:
                from PyQt6.QtWidgets import QLineEdit as FilterLine
            else:
                from PyQt5.QtWidgets import QLineEdit as FilterLine
        except Exception:
            FilterLine = None
        self.filter_input = FilterLine() if FilterLine else None
        if self.filter_input:
            self.filter_input.setPlaceholderText('type to filter keys (watchlist)')
            self.filter_input.textChanged.connect(self.on_filter_keys)
            self.filter_input.setMaximumWidth(260)
            top_h.addWidget(self.filter_input)
        else:
            top_h.addWidget(QLabel(''))

        top_h.addWidget(QLabel('Config Keys:'))
        self.lst_keys = QListWidget()
        self.lst_keys.setMaximumWidth(320)
        self.lst_keys.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        top_h.addWidget(self.lst_keys)

        self.btn_compare = QPushButton('Compare')
        self.btn_compare.clicked.connect(self.on_compare)
        top_h.addWidget(self.btn_compare)

        self.btn_cancel = QPushButton('Cancel')
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self.on_cancel)
        top_h.addWidget(self.btn_cancel)

        layout.addLayout(top_h)

        splitter_v = QSplitter(Qt.Orientation.Vertical)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(5)
        self.tree.setHeaderLabels(['CfgKey', 'Type', 'Key', 'Old', 'New'])
        splitter_v.addWidget(self.tree)

        inline = QWidget()
        ih = QHBoxLayout()
        inline.setLayout(ih)
        self.txt_old_sel = QTextEdit()
        self.txt_new_sel = QTextEdit()
        ih.addWidget(self.txt_old_sel)
        ih.addWidget(self.txt_new_sel)
        splitter_v.addWidget(inline)

        bottom_split = QSplitter(Qt.Orientation.Horizontal)
        self.txt_full_old = QTextEdit()
        self.txt_full_new = QTextEdit()
        # sync scrollbars
        try:
            old_sb = self.txt_full_old.verticalScrollBar()
            new_sb = self.txt_full_new.verticalScrollBar()
            self._syncing_scroll = False
            def _old_changed(v):
                if self._syncing_scroll:
                    return
                self._syncing_scroll = True
                new_sb.setValue(v)
                self._syncing_scroll = False
            def _new_changed(v):
                if self._syncing_scroll:
                    return
                self._syncing_scroll = True
                old_sb.setValue(v)
                self._syncing_scroll = False
            old_sb.valueChanged.connect(_old_changed)
            new_sb.valueChanged.connect(_new_changed)
        except Exception:
            pass
        bottom_split.addWidget(self.txt_full_old)
        bottom_split.addWidget(self.txt_full_new)
        splitter_v.addWidget(bottom_split)

        layout.addWidget(splitter_v)

        self.setCentralWidget(central)

        self.status = self.statusBar()
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.status.addPermanentWidget(self.progress)

        self.tree.itemSelectionChanged.connect(self.on_tree_select)

        # Summary canvas (matplotlib) if available
        if HAS_MPL:
            try:
                self.fig = Figure(figsize=(4,2))
                self.canvas = FigureCanvas(self.fig)
                # place at right side as a dock-like small widget
                layout.addWidget(self.canvas)
            except Exception:
                self.fig = None
                self.canvas = None

    def on_open(self):
        if not self.loader:
            QMessageBox.warning(self, 'Missing', 'FileLoader (TestNew.py) not found; cannot open files.')
            return
        p, _ = QFileDialog.getOpenFileName(self, 'Open CSV/TSV/TXT/XLSX/XLS', os.path.expanduser('~'), 'All Files (*.*)')
        if not p:
            return
        ok, why = self.loader.validate_file(p)
        if not ok:
            QMessageBox.critical(self, 'File Error', why)
            return
        try:
            ext = os.path.splitext(p)[1].lower()
            if ext in ('.csv', '.tsv', '.txt'):
                if hasattr(self.loader, 'load_chunked'):
                    headers, rows = self.loader.load_chunked(p, chunk_size=20000)
                else:
                    headers, rows = self.loader.load_csv(p)
            else:
                headers, rows = self.loader.load_excel(p)
        except Exception as e:
            QMessageBox.critical(self, 'Load Error', str(e))
            return

        mapping, conf = self.loader.detect_best_columns(headers)
        # Try heuristic for missing config key
        if 'Config Key' not in mapping:
            import re
            pattern = re.compile(r'cfg\W*key|config\W*key|^key$|identifier|\bid\b', re.IGNORECASE)
            for i, h in enumerate(headers):
                if i in set(mapping.values()):
                    continue
                if pattern.search(h):
                    mapping['Config Key'] = i
                    conf['Config Key'] = max(conf.get('Config Key', 0.0), 0.45)
                    break

        # Offer mapping editor
        editor = MappingEditor(self, headers, mapping)
        # compare against compatibility alias for dialog accepted
        try:
            result = editor.exec()
        except Exception:
            # some PyQt builds expose exec_()
            result = editor.exec_() if hasattr(editor, 'exec_') else None
        if result != DIALOG_ACCEPTED:
            QMessageBox.information(self, 'Aborted', 'Load aborted by user.')
            return
        mapping = editor.get_mapping()

        self.rows = self.loader.assemble_rows(headers, rows, mapping)
        # index
        self.by_name.clear()
        for idx, r in enumerate(self.rows):
            nm = (r.get('Config Name') or '').strip()
            if nm:
                self.by_name.setdefault(nm, []).append(idx)

        names = sorted(self.by_name.keys())
        self.cmb_name.clear()
        self.cmb_name.addItems(names)
        self.status.showMessage(f'Loaded {len(self.rows):,} rows. {len(names)} config names found.', 5000)
        # clear any cached current keys
        self.current_keys = []

    def on_name_selected(self):
        name = self.cmb_name.currentText().strip()
        self.lst_keys.clear()
        if not name:
            return
        indices = self.by_name.get(name, [])
        keys = sorted({self._format_key(self.rows[i].get('Config Key', '')) for i in indices if self.rows[i].get('Config Key', '').strip()})
        self.current_keys = keys
        for k in keys:
            self.lst_keys.addItem(k)

    def on_filter_keys(self, text: str):
        # Filter visible keys in the list based on substring match
        try:
            if not hasattr(self, 'current_keys') or not self.current_keys:
                return
            q = (text or '').strip().lower()
            self.lst_keys.clear()
            if not q:
                for k in self.current_keys:
                    self.lst_keys.addItem(k)
                return
            for k in self.current_keys:
                if q in k.lower():
                    self.lst_keys.addItem(k)
        except Exception:
            pass

    def _format_key(self, k: str) -> str:
        k_str = str(k).strip()
        try:
            import re
            if re.match(r'^[+-]?\d+(?:\.\d+)?[eE][+-]?\d+$', k_str):
                f = float(k_str)
                if f.is_integer():
                    return "{:.0f}".format(f)
                s = format(f, 'f')
                return s.rstrip('0').rstrip('.') if '.' in s else s
        except Exception:
            pass
        return k_str

    def on_compare(self):
        name = self.cmb_name.currentText().strip()
        if not name:
            QMessageBox.warning(self, 'Select', 'Please select a Config Name.')
            return
        sel = self.lst_keys.selectedItems()
        if not sel:
            QMessageBox.warning(self, 'Select Keys', 'Please select one or more Config Keys.')
            return
        keys = [it.text() for it in sel]
        rows_map = self._get_rows_for_keys_map(name, keys)
        if not rows_map:
            QMessageBox.warning(self, 'No Rows', 'No matching rows found for selected keys.')
            return

        # Clear UI
        self.tree.clear()
        self.full_payloads_cache.clear()

        items = list(rows_map.items())
        # Multi-worker: split items across N threads
        try:
            max_workers = min(4, (os.cpu_count() or 2))
        except Exception:
            max_workers = 4
        n = min(max_workers, len(items)) or 1
        chunk_size = (len(items) + n - 1) // n

        self.progress.setMaximum(len(items))
        self.progress.setValue(0)
        self.progress.setVisible(True)
        self.btn_compare.setEnabled(False)
        self.btn_cancel.setEnabled(True)

        # reset summary counters
        self.summary_counts = {'changed': 0, 'added': 0, 'removed': 0}

        for i in range(n):
            chunk = items[i*chunk_size:(i+1)*chunk_size]
            if not chunk:
                continue
            w = Worker(chunk, ignore_order=False)
            w.result.connect(self._on_worker_result)
            w.parse_log.connect(self._on_parse_log)
            w.finished.connect(self._on_worker_finished)
            self.workers.append(w)
            w.start()

    def _get_rows_for_keys_map(self, name: str, keys: List[str]) -> Dict[str, Dict[str, str]]:
        key_set = set(keys)
        rows_map: Dict[str, Dict[str, str]] = {}
        for idx in self.by_name.get(name, []):
            row = self.rows[idx]
            raw_k = row.get('Config Key', '').strip()
            formatted_k = self._format_key(raw_k)
            if formatted_k in key_set:
                rows_map[formatted_k] = row
                key_set.remove(formatted_k)
            if not key_set:
                break
        return rows_map

    def _on_worker_result(self, cfgkey: str, old_obj: object, new_obj: object, diffs: list):
        # cache
        self.full_payloads_cache[cfgkey] = (old_obj, new_obj)
        # add diffs
        for d in diffs:
            typ, path, oldv, newv = d
            path_key = path
            if _helpers and hasattr(_helpers, 'dd_path_to_key'):
                try:
                    path_key = _helpers.dd_path_to_key(path)
                except Exception:
                    pass
            item = QTreeWidgetItem([cfgkey, typ, path_key, pretty_json(oldv), pretty_json(newv)])
            self.tree.addTopLevelItem(item)
            # update summary
            try:
                if typ in self.summary_counts:
                    self.summary_counts[typ] += 1
                else:
                    self.summary_counts.setdefault(typ, 0)
                    self.summary_counts[typ] += 1
            except Exception:
                pass
        # progress update
        try:
            self.progress.setValue(self.progress.value() + 1)
        except Exception:
            pass

    def on_export_txt(self):
        p, _ = QFileDialog.getSaveFileName(self, 'Save Visible Diffs as TXT', os.path.expanduser('~'), 'Text Files (*.txt)')
        if not p:
            return
        try:
            with open(p, 'w', encoding='utf-8') as f:
                for i in range(self.tree.topLevelItemCount()):
                    it = self.tree.topLevelItem(i)
                    cfg = it.text(0)
                    typ = it.text(1)
                    path = it.text(2)
                    old = it.text(3)
                    new = it.text(4)
                    f.write(f"ConfigKey: {cfg}\nType: {typ}\nPath: {path}\nOld: {old}\nNew: {new}\n")
                    f.write('-' * 80 + '\n')
            QMessageBox.information(self, 'Saved', f'TXT saved to: {p}')
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Failed to save TXT: {e}')

    def _on_parse_log(self, msg: str, level: str, ctx: str):
        self.parse_entries.append({'timestamp': 0, 'level': level, 'message': msg, 'context': ctx})
        logger.warning(msg)

    def _on_worker_finished(self):
        # remove one finished worker entry if present
        try:
            # safe removal: pop any worker reference
            self.workers.pop()
        except Exception:
            pass

        # If all workers finished, finalize
        if not self.workers:
            try:
                self.progress.setVisible(False)
            except Exception:
                pass
            try:
                self.btn_compare.setEnabled(True)
                self.btn_cancel.setEnabled(False)
            except Exception:
                pass
            try:
                self.status.showMessage('Compare finished', 4000)
            except Exception:
                pass

            # Draw summary if available
            try:
                if HAS_MPL and getattr(self, 'fig', None) is not None and getattr(self, 'canvas', None) is not None:
                    ax = self.fig.subplots()
                    ax.clear()
                    labels = list(self.summary_counts.keys())
                    vals = [self.summary_counts.get(k, 0) for k in labels]
                    ax.bar(labels, vals, color=['#f7c873', '#9ee89e', '#f2a0a0'])
                    ax.set_title('Diff Summary')
                    self.canvas.draw()
            except Exception:
                pass

    def on_cancel(self):
        for w in self.workers:
            try:
                w.stop()
            except Exception:
                pass
        self.btn_cancel.setEnabled(False)
        self.status.showMessage('Cancellation requested...')

    def on_tree_select(self):
        it = self.tree.currentItem()
        if not it:
            return
        cfgkey = it.text(0)
        path = it.text(2)
        old_s = it.text(3)
        new_s = it.text(4)
        # inline diff
        self._show_inline(old_s, new_s)
        old_obj, new_obj = self.full_payloads_cache.get(cfgkey, (None, None))
        self.txt_full_old.setPlainText(pretty_json(old_obj))
        self.txt_full_new.setPlainText(pretty_json(new_obj))

    def _show_inline(self, old_s: str, new_s: str):
        self.txt_old_sel.clear()
        self.txt_new_sel.clear()
        try:
            import difflib
            sm = difflib.SequenceMatcher(a=old_s, b=new_s)
            for op, i1, i2, j1, j2 in sm.get_opcodes():
                if op == 'equal':
                    self.txt_old_sel.insertPlainText(old_s[i1:i2])
                    self.txt_new_sel.insertPlainText(new_s[j1:j2])
                elif op in ('delete', 'replace'):
                    self.txt_old_sel.insertHtml(f"<span style='background:#ffcccc'>{old_s[i1:i2]}</span>")
                if op in ('insert', 'replace'):
                    self.txt_new_sel.insertHtml(f"<span style='background:#c2f0c2'>{new_s[j1:j2]}</span>")
        except Exception:
            self.txt_old_sel.setPlainText(old_s)
            self.txt_new_sel.setPlainText(new_s)

    def on_export_csv(self):
        p, _ = QFileDialog.getSaveFileName(self, 'Save Visible Diffs as CSV', os.path.expanduser('~'), 'CSV Files (*.csv)')
        if not p:
            return
        try:
            import csv as _csv
            with open(p, 'w', encoding='utf-8', newline='') as f:
                w = _csv.writer(f)
                w.writerow(['Config Key', 'Type', 'Key Path', 'Old Value', 'New Value'])
                for i in range(self.tree.topLevelItemCount()):
                    it = self.tree.topLevelItem(i)
                    w.writerow([it.text(0), it.text(1), it.text(2), it.text(3), it.text(4)])
            QMessageBox.information(self, 'Saved', f'CSV saved to: {p}')
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Failed to save CSV: {e}')

    def on_show_parse_log(self):
        dlg = ParseLogViewer(self, self.parse_entries)
        dlg.exec()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
