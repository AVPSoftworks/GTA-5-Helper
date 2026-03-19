import os
import subprocess
import sys

from PySide2.QtCore import Qt, QThread, Signal
from PySide2.QtGui import QColor, QFont, QPalette
from PySide2.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

# --- Path Configuration ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEXCONV_EXE = os.path.join(BASE_DIR, "bin", "DirectXTex", "texconv.exe")
ARCHIVEFIX_EXE = os.path.join(BASE_DIR, "bin", "ArchiveFix", "ArchiveFix.exe")


# ─────────────────────────────────────────────
#  Background worker thread for batch convert
# ─────────────────────────────────────────────
class ConvertWorker(QThread):
    progress = Signal(int)  # 0-100
    file_done = Signal(str, bool)  # path, success
    finished = Signal(int, int)  # success_count, total

    def __init__(self, files, fmt, gen_mipmaps, out_dir):
        super().__init__()
        self.files = files
        self.fmt = fmt
        self.gen_mipmaps = gen_mipmaps
        self.out_dir = out_dir

    def run(self):
        total = len(self.files)
        success = 0

        for idx, file_path in enumerate(self.files):
            out_dir = self.out_dir if self.out_dir else os.path.dirname(file_path)

            cmd = [
                TEXCONV_EXE,
                "-f",
                self.fmt,
                "-m",
                "0" if self.gen_mipmaps else "1",  # 0 = full mip chain, 1 = no mips
                "-y",  # overwrite
                "-o",
                out_dir,
                file_path,
            ]

            ok = False
            try:
                result = subprocess.run(
                    cmd,
                    check=True,
                    capture_output=True,
                    creationflags=0x08000000,  # CREATE_NO_WINDOW
                )
                ok = True
                success += 1
            except subprocess.CalledProcessError:
                ok = False
            except Exception:
                ok = False

            self.file_done.emit(file_path, ok)
            self.progress.emit(int((idx + 1) / total * 100))

        self.finished.emit(success, total)


# ─────────────────────────────────────────────
#  Main Window
# ─────────────────────────────────────────────
DARK_BG = "#1a1a2e"
PANEL_BG = "#16213e"
ACCENT = "#0f3460"
GREEN = "#2ecc71"
RED = "#e74c3c"
ORANGE = "#e67e22"
TEXT = "#ecf0f1"
SUBTEXT = "#95a5a6"
BORDER = "#2c3e50"


STYLESHEET = f"""
QMainWindow, QWidget {{
    background-color: {DARK_BG};
    color: {TEXT};
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 13px;
}}

QGroupBox {{
    border: 1px solid {BORDER};
    border-radius: 6px;
    margin-top: 10px;
    padding: 10px;
    color: {SUBTEXT};
    font-size: 11px;
    letter-spacing: 1px;
    text-transform: uppercase;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}}

QListWidget {{
    background-color: {PANEL_BG};
    border: 1px solid {BORDER};
    border-radius: 4px;
    color: {TEXT};
    padding: 4px;
    font-size: 12px;
}}
QListWidget::item:selected {{
    background-color: {ACCENT};
}}
QListWidget::item:hover {{
    background-color: #0a2540;
}}

QComboBox {{
    background-color: {PANEL_BG};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 4px 8px;
    color: {TEXT};
    min-width: 120px;
}}
QComboBox::drop-down {{
    border: none;
    width: 20px;
}}
QComboBox QAbstractItemView {{
    background-color: {PANEL_BG};
    border: 1px solid {BORDER};
    color: {TEXT};
    selection-background-color: {ACCENT};
}}

QCheckBox {{
    spacing: 6px;
    color: {TEXT};
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {BORDER};
    border-radius: 3px;
    background-color: {PANEL_BG};
}}
QCheckBox::indicator:checked {{
    background-color: {GREEN};
    border-color: {GREEN};
}}

QPushButton {{
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 6px 14px;
    background-color: {PANEL_BG};
    color: {TEXT};
    font-family: 'Consolas', 'Courier New', monospace;
}}
QPushButton:hover {{
    background-color: {ACCENT};
    border-color: #1a5276;
}}
QPushButton:pressed {{
    background-color: #0a2540;
}}
QPushButton:disabled {{
    color: {SUBTEXT};
    background-color: {PANEL_BG};
}}

QProgressBar {{
    border: 1px solid {BORDER};
    border-radius: 4px;
    background-color: {PANEL_BG};
    text-align: center;
    color: {TEXT};
    font-size: 11px;
}}
QProgressBar::chunk {{
    background-color: {GREEN};
    border-radius: 3px;
}}

QLabel {{
    color: {TEXT};
}}

QScrollBar:vertical {{
    background: {PANEL_BG};
    width: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: {BORDER};
    border-radius: 4px;
    min-height: 20px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
"""


class GtaVHelper(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GTA V Helper  ·  DDS Converter + RPF Fix")
        self.setMinimumWidth(560)
        self.setMinimumHeight(500)
        self.worker = None
        self.output_dir = ""

        self.setStyleSheet(STYLESHEET)
        self._build_ui()

    # ── UI Construction ────────────────────────────────────────────────────
    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        main = QVBoxLayout(root)
        main.setContentsMargins(14, 14, 14, 14)
        main.setSpacing(10)

        # Header
        header = QLabel("GTA V HELPER")
        header.setFont(QFont("Consolas", 18, QFont.Bold))
        header.setStyleSheet(f"color: {GREEN}; letter-spacing: 4px;")
        main.addWidget(header)

        sub = QLabel("GTA V Texture Converter  &  Archive Fix Utility")
        sub.setStyleSheet(f"color: {SUBTEXT}; font-size: 11px; margin-bottom: 6px;")
        main.addWidget(sub)

        # ── Queue ──
        queue_group = QGroupBox("Conversion Queue")
        ql = QVBoxLayout()
        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QListWidget.ExtendedSelection)
        self.file_list.setMinimumHeight(140)
        ql.addWidget(self.file_list)

        btn_row = QHBoxLayout()
        btn_add = QPushButton("＋  Add Images")
        btn_add.clicked.connect(self.add_images)
        btn_remove = QPushButton("－  Remove Selected")
        btn_remove.clicked.connect(self.remove_selected)
        btn_clear = QPushButton("✕  Clear All")
        btn_clear.clicked.connect(self.file_list.clear)
        btn_row.addWidget(btn_add)
        btn_row.addWidget(btn_remove)
        btn_row.addWidget(btn_clear)
        ql.addLayout(btn_row)
        queue_group.setLayout(ql)
        main.addWidget(queue_group)

        # ── DDS Settings ──
        settings_group = QGroupBox("DDS Settings")
        sl = QVBoxLayout()

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Compression:"))
        self.combo_compression = QComboBox()
        self.combo_compression.addItems(
            [
                "DXT1",  # RGB, 1-bit alpha  — smallest
                "DXT3",  # RGBA, sharp alpha
                "DXT5",  # RGBA, smooth alpha — most common
                "BC4_UNORM",  # single channel (greyscale / roughness)
                "BC5_UNORM",  # dual channel (normal maps)
                "BC7_UNORM",  # high-quality RGBA
            ]
        )
        self.combo_compression.setCurrentIndex(2)  # DXT5 default
        row1.addWidget(self.combo_compression)
        row1.addStretch()
        self.check_mipmaps = QCheckBox("Generate Mipmaps")
        self.check_mipmaps.setChecked(True)
        row1.addWidget(self.check_mipmaps)
        sl.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Output folder:"))
        self.lbl_outdir = QLabel("Same as source")
        self.lbl_outdir.setStyleSheet(f"color: {SUBTEXT}; font-size: 11px;")
        self.lbl_outdir.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.lbl_outdir.setWordWrap(True)
        btn_outdir = QPushButton("Browse…")
        btn_outdir.clicked.connect(self.pick_output_dir)
        btn_outdir_clear = QPushButton("Reset")
        btn_outdir_clear.clicked.connect(self.clear_output_dir)
        row2.addWidget(self.lbl_outdir)
        row2.addWidget(btn_outdir)
        row2.addWidget(btn_outdir_clear)
        sl.addLayout(row2)

        settings_group.setLayout(sl)
        main.addWidget(settings_group)

        # ── Progress ──
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        main.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet(f"color: {SUBTEXT}; font-size: 11px;")
        self.status_label.setVisible(False)
        main.addWidget(self.status_label)

        # ── Actions ──
        self.btn_convert = QPushButton("▶   CONVERT BATCH  →  DDS")
        self.btn_convert.setStyleSheet(
            f"background-color: {GREEN}; color: #111; font-weight: bold;"
            "height: 40px; font-size: 14px; border: none; border-radius: 5px;"
        )
        self.btn_convert.clicked.connect(self.process_batch)
        main.addWidget(self.btn_convert)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"color: {BORDER};")
        main.addWidget(sep)

        btn_fix = QPushButton("🔧   FIX GTA V  ARCHIVE  (.RPF)")
        btn_fix.setStyleSheet(
            f"background-color: {RED}; color: white; font-weight: bold;"
            "height: 36px; font-size: 13px; border: none; border-radius: 5px;"
        )
        btn_fix.clicked.connect(self.fix_rpf_archive)
        main.addWidget(btn_fix)

    # ── Slots ──────────────────────────────────────────────────────────────
    def add_images(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Images",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.tga *.tif *.tiff)",
        )
        if files:
            existing = {
                self.file_list.item(i).text() for i in range(self.file_list.count())
            }
            added = 0
            for f in files:
                if f not in existing:
                    self.file_list.addItem(f)
                    added += 1
            self._set_status(
                f"Added {added} file(s). Queue: {self.file_list.count()} total."
            )

    def remove_selected(self):
        for item in self.file_list.selectedItems():
            self.file_list.takeItem(self.file_list.row(item))

    def pick_output_dir(self):
        d = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if d:
            self.output_dir = d
            self.lbl_outdir.setText(d)
            self.lbl_outdir.setStyleSheet(f"color: {TEXT}; font-size: 11px;")

    def clear_output_dir(self):
        self.output_dir = ""
        self.lbl_outdir.setText("Same as source")
        self.lbl_outdir.setStyleSheet(f"color: {SUBTEXT}; font-size: 11px;")

    def check_tool(self, path):
        if not os.path.exists(path):
            QMessageBox.critical(
                self,
                "Missing Tool",
                f"Required executable not found:\n{path}\n\n"
                "Make sure the 'bin' folder is next to this script.",
            )
            return False
        return True

    def process_batch(self):
        if not self.check_tool(TEXCONV_EXE):
            return
        if self.file_list.count() == 0:
            QMessageBox.warning(self, "Empty Queue", "Add at least one image first.")
            return
        if self.worker and self.worker.isRunning():
            return

        files = [self.file_list.item(i).text() for i in range(self.file_list.count())]
        fmt = self.combo_compression.currentText()
        gen_mips = self.check_mipmaps.isChecked()

        self.btn_convert.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.status_label.setVisible(True)

        self.worker = ConvertWorker(files, fmt, gen_mips, self.output_dir)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.file_done.connect(self._on_file_done)
        self.worker.finished.connect(self._on_batch_done)
        self.worker.start()

    def _on_file_done(self, path, ok):
        name = os.path.basename(path)
        icon = "✔" if ok else "✘"
        color = GREEN if ok else RED
        self._set_status(f"{icon}  {name}", color)

    def _on_batch_done(self, success, total):
        self.btn_convert.setEnabled(True)
        self.progress_bar.setValue(100)
        msg = f"Converted {success} of {total} image(s) successfully."
        color = GREEN if success == total else ORANGE
        self._set_status(msg, color)
        QMessageBox.information(self, "Batch Complete", msg)

    def fix_rpf_archive(self):
        if not self.check_tool(ARCHIVEFIX_EXE):
            return
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select RPF Archive", "", "GTA V Archive (*.rpf)"
        )
        if not file_path:
            return
        try:
            subprocess.run(
                [ARCHIVEFIX_EXE, file_path],
                check=True,
                capture_output=True,
                creationflags=0x08000000,
            )
            QMessageBox.information(self, "Success", "Archive repaired successfully!")
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode(errors="replace") if e.stderr else "(no output)"
            QMessageBox.critical(
                self, "Fix Failed", f"ArchiveFix returned an error:\n{stderr}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Unexpected error:\n{e}")

    def _set_status(self, text, color=None):
        c = color or SUBTEXT
        self.status_label.setStyleSheet(f"color: {c}; font-size: 11px;")
        self.status_label.setText(text)


# ─────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GtaVHelper()
    window.show()
    sys.exit(app.exec_())  # PySide2 uses exec_() with underscore
