import os
import subprocess
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Note: On Arch, to TEST these, you'd need to prefix commands with 'wine'
TEXCONV_EXE = os.path.join(BASE_DIR, "bin", "DirectXTex", "texconv.exe")
ARCHIVEFIX_EXE = os.path.join(BASE_DIR, "bin", "ArchiveFix", "ArchiveFix.exe")


class GtaVHelper(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GTA V Helper - Batch Texture Tool")
        self.setMinimumWidth(500)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # --- Batch Queue Section ---
        queue_group = QGroupBox("Conversion Queue")
        queue_layout = QVBoxLayout()

        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QAbstractItemView.ExtendedSelection)

        queue_layout.addWidget(self.file_list)

        btn_row = QHBoxLayout()
        btn_add = QPushButton("Add Images")
        btn_add.clicked.connect(self.add_images)
        btn_clear = QPushButton("Clear Queue")
        btn_clear.clicked.connect(lambda: self.file_list.clear())
        btn_row.addWidget(btn_add)
        btn_row.addWidget(btn_clear)
        queue_layout.addLayout(btn_row)

        queue_group.setLayout(queue_layout)
        layout.addWidget(queue_group)

        # --- Settings Section ---
        settings_group = QGroupBox("DDS Settings")
        settings_layout = QHBoxLayout()

        self.combo_compression = QComboBox()
        self.combo_compression.addItems(["DXT1", "DXT5", "BC7_UNORM"])
        self.check_mipmaps = QCheckBox("Mipmaps")
        self.check_mipmaps.setChecked(True)

        settings_layout.addWidget(QLabel("Format:"))
        settings_layout.addWidget(self.combo_compression)
        settings_layout.addStretch()
        settings_layout.addWidget(self.check_mipmaps)
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)

        # --- Action Buttons ---
        self.btn_convert = QPushButton("PROCESS BATCH")
        self.btn_convert.setStyleSheet(
            "background-color: #2e7d32; color: white; height: 40px; font-weight: bold;"
        )
        self.btn_convert.clicked.connect(self.process_batch)
        layout.addWidget(self.btn_convert)

        btn_fix = QPushButton("FIX GTA V ARCHIVE (RPF)")
        btn_fix.setStyleSheet(
            "background-color: #c62828; color: white; font-weight: bold;"
        )
        btn_fix.clicked.connect(self.fix_rpf_archive)
        layout.addWidget(btn_fix)

    def add_images(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Images", "", "Images (*.png *.jpg *.jpeg)"
        )
        if files:
            self.file_list.addItems(files)

    def process_batch(self):
        count = self.file_list.count()
        if count == 0:
            return QMessageBox.warning(self, "Empty", "Add some images first!")

        fmt = self.combo_compression.currentText()
        mips = "-m 0" if self.check_mipmaps.isChecked() else "-m 1"

        success_count = 0
        for i in range(count):
            file_path = self.file_list.item(i).text()
            output_dir = os.path.dirname(file_path)

            # On Linux, you would use ["wine", TEXCONV_EXE, ...] to test
            cmd = [TEXCONV_EXE, "-f", fmt, mips, "-y", "-o", output_dir, file_path]

            try:
                subprocess.run(
                    cmd, check=True, creationflags=subprocess.CREATE_NO_WINDOW
                )
                success_count += 1
            except Exception:
                continue

        QMessageBox.information(
            self, "Done", f"Successfully converted {success_count}/{count} images."
        )

    def fix_rpf_archive(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select RPF", "", "Archive (*.rpf)"
        )
        if file_path:
            try:
                subprocess.run(
                    [ARCHIVEFIX_EXE, file_path],
                    check=True,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                QMessageBox.information(self, "Success", "Archive Fixed!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed: {e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GtaVHelper()
    window.show()
    sys.exit(app.exec())
