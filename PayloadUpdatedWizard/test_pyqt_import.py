import traceback

try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QFileDialog, QMessageBox, QTreeWidget,
        QTreeWidgetItem, QTextEdit, QPushButton, QComboBox, QListWidget,
        QVBoxLayout, QWidget, QHBoxLayout, QLabel, QProgressBar, QSplitter,
        QToolBar, QDialog, QFormLayout, QLineEdit, QDialogButtonBox,
        QTableWidget, QTableWidgetItem, QSizePolicy
    )
    from PyQt6.QtCore import Qt, QThread, pyqtSignal as Signal
    from PyQt6.QtGui import QAction
    print('PyQt6 grouped import: OK')
except Exception as e:
    print('PyQt6 grouped import: FAILED')
    traceback.print_exc()

try:
    from PyQt5.QtWidgets import QApplication
    print('PyQt5 import: OK')
except Exception as e:
    print('PyQt5 import: FAILED')
    traceback.print_exc()
