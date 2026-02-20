# -*- coding: utf-8 -*-
"""
PyQt frontend for the Payload Diff Viewer

Minimal full-conversion: Open, auto-detect columns, list Config Names and Keys,
Compare selected keys (parallel), show diffs in a tree, inline diff, and full JSON panes.

Dependencies: PyQt6, deepdiff, pandas (optional for large files)

Run:
    pip install PyQt6 deepdiff pandas openpyxl
    python GeminiPayloadDiff_PyQt.py
"""

from __future__ import annotations
import sys
import os
import json
import queue
import threading
import difflib
import logging
from typing import Any, Dict, List, Tuple, Optional

# Detect available Qt binding (prefer PyQt6, then PyQt5).
PYQT_VER = None
try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QFileDialog, QMessageBox, QTreeWidget, QTreeWidgetItem,
        QTextEdit, QPushButton, QComboBox, QListWidget, QVBoxLayout, QWidget, QHBoxLayout,
        QLabel, QProgressBar, QSplitter, QToolBar
    )
    from PyQt6.QtCore import Qt, QTimer
    # QAction is provided from QtGui in PyQt6
    from PyQt6.QtGui import QAction
    PYQT_VER = 6
except Exception:
    try:
        from PyQt5.QtWidgets import (
            QApplication, QMainWindow, QFileDialog, QMessageBox, QTreeWidget, QTreeWidgetItem,
            QTextEdit, QPushButton, QComboBox, QListWidget, QVBoxLayout, QWidget, QHBoxLayout,
            QLabel, QProgressBar, QSplitter, QAction, QToolBar
        )
        from PyQt5.QtCore import Qt, QTimer
        PYQT_VER = 5
    except Exception:
        PYQT_VER = None

if PYQT_VER is None:
    raise ModuleNotFoundError("PyQt5 or PyQt6 is required. Install with: pip install PyQt6 or pip install PyQt5")

# Determine the proper ExtendedSelection constant across PyQt versions
try:
    from PyQt6.QtWidgets import QAbstractItemView as _QAV
    SELECTION_EXTENDED = _QAV.SelectionMode.ExtendedSelection
except Exception:
    try:
        from PyQt5.QtWidgets import QAbstractItemView as _QAV
        SELECTION_EXTENDED = _QAV.ExtendedSelection
    except Exception:
        SELECTION_EXTENDED = 3  # fallback integer for ExtendedSelection
# Reuse the project's FileLoader and parsing utilities where available
# TestNew.py provides a FileLoader class used for loading CSV/Excel files.
try:
    from TestNew import FileLoader
except Exception:
    FileLoader = None

# Import parsing & diff helpers from the existing module if present
_helpers = None
try:
    import GeminiPayloadDiff_GeminiUltra_FIXED_optimized_FIXED as core
    _helpers = core
except Exception:
    _helpers = None

# Try to import DeepDiff
try:
    from deepdiff import DeepDiff
except Exception:
    DeepDiff = None

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def pretty_json(obj: Any) -> str:
    if obj is None:
        return ""
    try:
        return json.dumps(obj, indent=2, ensure_ascii=False)
    except Exception:
        return str(obj)


def apply_vibrant_theme(app: 'QApplication') -> None:
    """
    Apply a vibrant dark stylesheet to the QApplication for a higher-contrast,
    colorful UI. Works with PyQt5/PyQt6.
    """
    # Accent and base colors
    accent = '#00bcd4'  # cyan/teal accent
    bg = '#181818'
    panel = '#242424'
    text = '#e6e6e6'
    muted = '#bdbdbd'
    selection = '#005f67'

    qss = f"""
    QWidget {{ background: {bg}; color: {text}; font-family: 'Segoe UI', Roboto, Arial; }}
    QToolBar {{ background: {panel}; spacing: 6px; padding: 4px; }}
    QMenuBar {{ background: {panel}; color: {text}; }}
    QMenuBar::item:selected {{ background: rgba(255,255,255,0.02); }}
    QMenu {{ background: {panel}; color: {text}; }}

    QTreeWidget, QTableView, QListWidget {{
        background: {panel};
        alternate-background-color: #1f1f1f;
        color: {text};
        selection-background-color: {accent};
        selection-color: #111;
    }}

    QHeaderView::section {{ background: #2a2a2a; color: {text}; padding: 6px; border: 1px solid #2f2f2f; }}

    QPushButton {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {accent}, stop:1 #008ba3);
        border: none; color: #042426; padding: 6px 12px; border-radius: 6px;
    }}
    QPushButton:hover {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #00d6e6, stop:1 #00a9bb); }}

    QComboBox, QLineEdit, QTextEdit {{ background: #1f1f1f; color: {text}; border: 1px solid #333; padding: 6px; }}

    QSplitter::handle {{ background: transparent; }}

    QTextEdit {{ background: #141414; color: {text}; selection-background-color: {accent}; selection-color: #042426; font-family: 'Consolas', 'Courier New', monospace; }}

    QTreeWidget::item:selected {{ background: rgba(0,188,212,0.15); }}

    /* Scrollbar styling */
    QScrollBar:vertical {{ background: transparent; width: 12px; margin: 0px 0px 0px 0px; }}
    QScrollBar::handle:vertical {{ background: #2f2f2f; min-height: 20px; border-radius: 6px; }}
    QScrollBar::handle:vertical:hover {{ background: #3b3b3b; }}

    QLabel {{ color: {muted}; }}

    """

    try:
        app.setStyleSheet(qss)
    except Exception:
        # In case of any binding-specific issues, ignore stylesheet failure
        pass


class WorkerThread(threading.Thread):
    """Background worker that computes diffs for a set of rows.
    It accepts a tasks queue of (cfgkey, old_str, new_str) and puts results into results_q.
    """
    def __init__(self, tasks_q: queue.Queue, results_q: queue.Queue, parse_log_q: queue.Queue, ignore_order: bool = False):
        super().__init__(daemon=True)
        self.tasks_q = tasks_q
        self.results_q = results_q
        self.parse_log_q = parse_log_q
        self.ignore_order = ignore_order

    def run(self):
        while True:
            task = self.tasks_q.get()
            if task is None:
                self.tasks_q.task_done()
                break
            try:
                cfgkey, old_str, new_str = task
                # Parse using core utility if available
                if _helpers and hasattr(_helpers, 'parse_jsonish_verbose'):
                    old_obj, err1 = _helpers.parse_jsonish_verbose(old_str)
                    cur_obj, err2 = _helpers.parse_jsonish_verbose(new_str)
                else:
                    # best-effort: try json.loads then fallback to eval
                    try:
                        old_obj = json.loads(old_str) if old_str and old_str.strip() else None
                        err1 = ''
                    except Exception:
                        try:
                            old_obj = eval(old_str) if old_str and old_str.strip() else None
                            err1 = ''
                        except Exception as e:
                            old_obj = None
                            err1 = str(e)
                    try:
                        cur_obj = json.loads(new_str) if new_str and new_str.strip() else None
                        err2 = ''
                    except Exception:
                        try:
                            cur_obj = eval(new_str) if new_str and new_str.strip() else None
                            err2 = ''
                        except Exception as e:
                            cur_obj = None
                            err2 = str(e)

                if err1:
                    self.parse_log_q.put((f"[{cfgkey}] OLD: {err1}", 'warning', (old_str or '')[:200]))
                if err2:
                    self.parse_log_q.put((f"[{cfgkey}] CURRENT: {err2}", 'warning', (new_str or '')[:200]))

                if DeepDiff is None:
                    # No deepdiff, do a string-level diff fallback
                    diffs = []
                    if old_obj != cur_obj:
                        diffs.append(('changed', '', old_obj, cur_obj))
                else:
                    try:
                        dd = DeepDiff(old_obj, cur_obj, ignore_order=self.ignore_order, verbose_level=2)
                    except Exception as e:
                        self.parse_log_q.put((f"[{cfgkey}] DeepDiff failed: {e}", 'error', ''))
                        self.results_q.put((cfgkey, (old_obj, cur_obj), []))
                        continue

                    difflist = []
                    # values_changed
                    for path, change in dd.get('values_changed', {}).items():
                        typ = 'changed'
                        p = path
                        o = change.get('old_value')
                        n = change.get('new_value')
                        difflist.append((typ, p, o, n))
                    for path, change in dd.get('type_changes', {}).items():
                        typ = 'changed'
                        difflist.append((typ, path, change.get('old_value'), change.get('new_value')))
                    for path in dd.get('dictionary_item_added', set()):
                        val = None
                        if _helpers and hasattr(_helpers, 'value_from_path'):
                            val = _helpers.value_from_path(cur_obj, path)
                        difflist.append(('added', path, None, val))
                    for path in dd.get('dictionary_item_removed', set()):
                        val = None
                        if _helpers and hasattr(_helpers, 'value_from_path'):
                            val = _helpers.value_from_path(old_obj, path)
                        difflist.append(('removed', path, val, None))

                    diffs = difflist

                # put result
                self.results_q.put((cfgkey, (old_obj, cur_obj), diffs))

            except Exception as e:
                self.parse_log_q.put((f"Worker thread error: {e}", 'error', ''))
            finally:
                try:
                    self.tasks_q.task_done()
                except Exception:
                    pass


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Payload Diff Viewer - PyQt')
        self.resize(1200, 800)

        # Core state
        self.loader = FileLoader(ParseLogger() if FileLoader else None) if FileLoader else None
        self.rows: List[Dict[str, str]] = []
        self.by_name: Dict[str, List[int]] = {}
        self.full_payloads_cache: Dict[str, Tuple[Any, Any]] = {}

        self.tasks_q = queue.Queue()
        self.results_q = queue.Queue()
        self.parse_log_q = queue.Queue()
        self.workers: List[WorkerThread] = []

        self._build_ui()

        # Poll timer for results/logs
        self.timer = QTimer(self)
        self.timer.setInterval(150)
        self.timer.timeout.connect(self._poll_queues)
        self.timer.start()

        # runtime state for compare/cancel/progress
        self.cancel_requested = False
        self.current_compare_total = 0
        self.current_compare_done = 0

    def _build_ui(self):
        # Toolbar
        toolbar = QToolBar('Main')
        self.addToolBar(toolbar)
        act_open = QAction('Open', self)
        act_open.triggered.connect(self.on_open)
        toolbar.addAction(act_open)
        act_export_csv = QAction('Export CSV', self)
        act_export_csv.triggered.connect(self.on_export_csv)
        toolbar.addAction(act_export_csv)
        act_exit = QAction('Exit', self)
        act_exit.triggered.connect(self.close)
        toolbar.addAction(act_exit)

        # Top controls
        top_widget = QWidget()
        top_layout = QHBoxLayout()
        top_widget.setLayout(top_layout)

        top_layout.addWidget(QLabel('Config Name:'))
        self.cmb_name = QComboBox()
        self.cmb_name.currentIndexChanged.connect(self.on_name_selected)
        top_layout.addWidget(self.cmb_name)

        top_layout.addWidget(QLabel('Config Keys:'))
        self.lst_keys = QListWidget()
        try:
            self.lst_keys.setSelectionMode(SELECTION_EXTENDED)
        except Exception:
            # Fallback: try attribute on the widget directly
            try:
                self.lst_keys.setSelectionMode(self.lst_keys.ExtendedSelection)
            except Exception:
                pass
        self.lst_keys.setMaximumWidth(300)
        top_layout.addWidget(self.lst_keys)

        self.btn_compare = QPushButton('Compare')
        self.btn_compare.clicked.connect(self.on_compare)
        top_layout.addWidget(self.btn_compare)

        self.btn_cancel = QPushButton('Cancel')
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self.on_cancel_compare)
        top_layout.addWidget(self.btn_cancel)

        # Main splitters and panes
        central = QWidget()
        central_layout = QVBoxLayout()
        central.setLayout(central_layout)

        central_layout.addWidget(top_widget)

        # Support both PyQt6 and PyQt5 orientation enums
        if hasattr(Qt, 'Orientation'):
            orient_vertical = Qt.Orientation.Vertical
            orient_horizontal = Qt.Orientation.Horizontal
        else:
            orient_vertical = Qt.Vertical
            orient_horizontal = Qt.Horizontal

        splitter_v = QSplitter(orient_vertical)

        # Top: diff tree
        self.tree = QTreeWidget()
        self.tree.setColumnCount(5)
        self.tree.setHeaderLabels(['CfgKey', 'Type', 'Key', 'Old', 'New'])
        splitter_v.addWidget(self.tree)

        # Middle: inline diff
        inline_widget = QWidget()
        inline_layout = QHBoxLayout()
        inline_widget.setLayout(inline_layout)
        self.txt_sel_old = QTextEdit()
        self.txt_sel_new = QTextEdit()
        inline_layout.addWidget(self.txt_sel_old)
        inline_layout.addWidget(self.txt_sel_new)
        splitter_v.addWidget(inline_widget)

        # Bottom: full JSON panes
        bottom_split = QSplitter(orient_horizontal)
        self.txt_old = QTextEdit()
        self.txt_cur = QTextEdit()
        bottom_split.addWidget(self.txt_old)
        bottom_split.addWidget(self.txt_cur)
        splitter_v.addWidget(bottom_split)

        central_layout.addWidget(splitter_v)

        self.setCentralWidget(central)

        # Connections
        self.tree.itemSelectionChanged.connect(self.on_tree_select)

        # Status bar with progress
        try:
            self.status = self.statusBar()
            self.progress_bar = QProgressBar()
            self.progress_bar.setVisible(False)
            self.progress_bar.setMinimum(0)
            self.status.addPermanentWidget(self.progress_bar)
        except Exception:
            self.progress_bar = None

    def on_open(self):
        if not self.loader:
            QMessageBox.warning(self, 'Missing', 'FileLoader not available (TestNew.py missing).')
            return
        p, _ = QFileDialog.getOpenFileName(self, 'Open CSV/TSV/TXT/XLSX/XLS', os.path.expanduser('~'), 'All Files (*.*)')
        if not p:
            return

        ok, why = self.loader.validate_file(p)
        if not ok:
            QMessageBox.critical(self, 'File Error', why)
            return

        ext = os.path.splitext(p)[1].lower()
        try:
            if ext in ('.csv', '.tsv', '.txt'):
                # Use chunked if loader supports it
                if hasattr(self.loader, 'load_chunked'):
                    headers, rows = self.loader.load_chunked(p, chunk_size=20000)
                else:
                    headers, rows = self.loader.load_csv(p)
            else:
                headers, rows = self.loader.load_excel(p)
        except Exception as e:
            QMessageBox.critical(self, 'Load Error', str(e))
            return

        if not headers or not rows:
            QMessageBox.warning(self, 'No Data', 'File appears empty or has no rows.')
            return

        mapping, conf = self.loader.detect_best_columns(headers)
        # If missing mapping for Config Key, attempt heuristic
        if 'Config Key' not in mapping:
            pattern = __import__('re').compile(r'cfg\W*key|config\W*key|^key$|identifier|\bid\b', __import__('re').IGNORECASE)
            for i, h in enumerate(headers):
                if i in set(mapping.values()):
                    continue
                if pattern.search(h):
                    mapping['Config Key'] = i
                    conf['Config Key'] = max(conf.get('Config Key', 0.0), 0.45)
                    break

        # Show mapping confirmation to user so they can accept or abort
        try:
            mapping_preview = '\n'.join([f"{k}: column {v} -> '{headers[v] if v < len(headers) else ''}'" for k, v in mapping.items()])
        except Exception:
            mapping_preview = str(mapping)

        ok = QMessageBox.question(self, 'Confirm Mapping', f"Detected column mapping:\n\n{mapping_preview}\n\nAccept mapping and continue?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if ok != QMessageBox.StandardButton.Yes:
            QMessageBox.information(self, 'Aborted', 'Load aborted. Adjust file or headers and try again.')
            return

        self.rows = self.loader.assemble_rows(headers, rows, mapping)
        # index by Config Name
        self.by_name.clear()
        for idx, r in enumerate(self.rows):
            nm = (r.get('Config Name') or '').strip()
            if nm:
                self.by_name.setdefault(nm, []).append(idx)

        names = sorted(self.by_name.keys())
        self.cmb_name.clear()
        self.cmb_name.addItems(names)
        QMessageBox.information(self, 'Loaded', f'Loaded {len(self.rows):,} rows. {len(names)} config names found.')

    def on_name_selected(self):
        name = self.cmb_name.currentText().strip()
        self.lst_keys.clear()
        if not name:
            return
        indices = self.by_name.get(name, [])
        keys = sorted({self._format_key(self.rows[i].get('Config Key', '')) for i in indices if self.rows[i].get('Config Key', '').strip()})
        for k in keys:
            self.lst_keys.addItem(k)

    def _format_key(self, k: str) -> str:
        k_str = str(k).strip()
        try:
            if __import__('re').match(r'^[+-]?\d+(?:\.\d+)?[eE][+-]?\d+$', k_str):
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

        # Clear previous
        self.tree.clear()
        self.full_payloads_cache.clear()

        # prepare progress
        total = len(rows_map)
        self.current_compare_total = total
        self.current_compare_done = 0
        self.cancel_requested = False
        if self.progress_bar is not None:
            self.progress_bar.setMaximum(total)
            self.progress_bar.setValue(0)
            self.progress_bar.setVisible(True)
        try:
            self.btn_compare.setEnabled(False)
        except Exception:
            pass
        try:
            self.btn_cancel.setEnabled(True)
        except Exception:
            pass

        # Spawn workers
        total = len(rows_map)
        for _ in range(min(4, total)):
            w = WorkerThread(self.tasks_q, self.results_q, self.parse_log_q, ignore_order=False)
            w.start()
            self.workers.append(w)

        for cfgkey, row in rows_map.items():
            self.tasks_q.put((cfgkey, row.get('OLD PAYLOAD', ''), row.get('CURRENT PAYLOAD', '')))

        # Put sentinel
        for _ in self.workers:
            self.tasks_q.put(None)
        try:
            self.status.showMessage(f'Compare started: {total} items')
        except Exception:
            pass

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

    def _poll_queues(self):
        # Process parse log queue
        while not self.parse_log_q.empty():
            try:
                msg, level, ctx = self.parse_log_q.get_nowait()
                logger.warning(msg)
            except Exception:
                break

        # Process results queue
        updated = False
        while not self.results_q.empty():
            try:
                cfgkey, (old_obj, cur_obj), diffs = self.results_q.get_nowait()
                # Cache full objects
                self.full_payloads_cache[cfgkey] = (old_obj, cur_obj)
                # Add diffs to tree
                for d in diffs:
                    typ, path, oldv, newv = d
                    # Convert path using helper if available
                    path_key = path
                    if _helpers and hasattr(_helpers, 'dd_path_to_key'):
                        try:
                            path_key = _helpers.dd_path_to_key(path)
                        except Exception:
                            pass
                    item = QTreeWidgetItem([cfgkey, typ, path_key, pretty_json(oldv), pretty_json(newv)])
                    if typ == 'changed':
                        item.setBackground(0, Qt.GlobalColor.yellow)
                    self.tree.addTopLevelItem(item)
                updated = True
                # update progress
                try:
                    self.current_compare_done += 1
                    if self.progress_bar is not None and self.current_compare_total:
                        self.progress_bar.setValue(self.current_compare_done)
                except Exception:
                    pass
                # if canceled, skip further processing of this result
                if self.cancel_requested:
                    continue
            except Exception as e:
                logger.error('Result processing error: %s', e)
                break
        if updated:
            # Optionally expand / select first
            if self.tree.topLevelItemCount() > 0:
                it = self.tree.topLevelItem(0)
                self.tree.setCurrentItem(it)

        # If compare finished, cleanup
        if self.current_compare_total and self.current_compare_done >= self.current_compare_total:
            try:
                self.status.showMessage('Compare finished', 4000)
            except Exception:
                pass
            self._cleanup_workers()

    def on_tree_select(self):
        it = self.tree.currentItem()
        if not it:
            return
        cfgkey = it.text(0)
        path = it.text(2)
        old_s = it.text(3)
        new_s = it.text(4)
        # Show inline diff
        self._show_inline_diff(old_s, new_s)
        # Show full payloads from cache
        old_obj, new_obj = self.full_payloads_cache.get(cfgkey, (None, None))
        self.txt_old.setPlainText(pretty_json(old_obj))
        self.txt_cur.setPlainText(pretty_json(new_obj))

    def _show_inline_diff(self, old_str: str, new_str: str):
        self.txt_sel_old.clear()
        self.txt_sel_new.clear()
        sm = difflib.SequenceMatcher(a=old_str, b=new_str)
        for op, i1, i2, j1, j2 in sm.get_opcodes():
            if op == 'equal':
                self.txt_sel_old.insertPlainText(old_str[i1:i2])
                self.txt_sel_new.insertPlainText(new_str[j1:j2])
            elif op in ('delete', 'replace'):
                self.txt_sel_old.insertHtml(f"<span style='background:#ffcccc'>{old_str[i1:i2]}</span>")
            if op in ('insert', 'replace'):
                self.txt_sel_new.insertHtml(f"<span style='background:#c2f0c2'>{new_str[j1:j2]}</span>")

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

    def on_cancel_compare(self):
        # Request cancellation: set flag and enqueue sentinels to stop workers
        self.cancel_requested = True
        try:
            self.status.showMessage('Cancelling compare...')
        except Exception:
            pass
        # Clear pending tasks
        try:
            while not self.tasks_q.empty():
                try:
                    self.tasks_q.get_nowait()
                    self.tasks_q.task_done()
                except Exception:
                    break
        except Exception:
            pass
        # send sentinels to allow threads to exit
        for _ in self.workers:
            try:
                self.tasks_q.put(None)
            except Exception:
                pass
        # disable cancel button until cleanup
        try:
            self.btn_cancel.setEnabled(False)
        except Exception:
            pass

    def _cleanup_workers(self):
        # join worker threads and reset UI
        for w in self.workers:
            try:
                # threads will exit after sentinel; join briefly to be graceful
                if hasattr(w, 'join'):
                    w.join(timeout=0.1)
            except Exception:
                pass
        self.workers = []
        self.current_compare_total = 0
        self.current_compare_done = 0
        self.cancel_requested = False
        try:
            if self.progress_bar is not None:
                self.progress_bar.setVisible(False)
                self.progress_bar.setValue(0)
        except Exception:
            pass
        try:
            self.btn_compare.setEnabled(True)
            self.btn_cancel.setEnabled(False)
        except Exception:
            pass


class ParseLogger:  # lightweight local logger used when FileLoader is missing
    def __init__(self):
        self.entries = []
    def log(self, msg, level='warning', context=''):
        self.entries.append({'timestamp': 0, 'level': level, 'message': msg, 'context': context})


if __name__ == '__main__':
    app = QApplication(sys.argv)
    try:
        apply_vibrant_theme(app)
    except Exception:
        pass
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
