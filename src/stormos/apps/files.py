"""StormOS Files Application (User Storage & File Explorer).

Provides a secure, sandboxed file manager allowing users to browse, create,
edit, preview, and organize files and folders within their profile storage.
"""

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional
from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from stormos.core.constants import (
    COLOR_ERROR,
    COLOR_LIGHTNING,
    COLOR_MIST_BLUE,
    COLOR_NIGHT_SKY,
    COLOR_PANEL_EDGE,
    COLOR_RAISED_PANEL,
    COLOR_STORM_CLOUD,
    COLOR_TEXT_MAIN,
    COLOR_TEXT_SECONDARY,
    COLOR_WARNING,
)
from stormos.core.paths import USERS_DIR
from stormos.core.security import sanitize_filename
from stormos.services.user_manager import UserProfile


class FilesApp(QWidget):
    """Secure user storage and file management application."""

    def __init__(self, current_user: Optional[UserProfile] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.current_user = current_user
        self.root_dir = self._get_user_root()
        self.current_dir = self.root_dir
        self.history: list[Path] = [self.root_dir]
        self._setup_ui()
        self.navigate_to(self.root_dir)

    def _get_user_root(self) -> Path:
        if self.current_user and self.current_user.username:
            d = USERS_DIR / self.current_user.username
        else:
            d = Path("users/guest")
        d.mkdir(parents=True, exist_ok=True)
        # Ensure standard folders exist
        for sub in ("documents", "downloads", "pictures", "notes", "apps"):
            (d / sub).mkdir(exist_ok=True)
        return d

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        # 1. Navigation Toolbar
        toolbar = QFrame()
        toolbar.setStyleSheet(
            f"background-color: {COLOR_STORM_CLOUD}; border: 1px solid {COLOR_PANEL_EDGE}; border-radius: 8px; padding: 4px 8px;"
        )
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(4, 4, 4, 4)
        tb_layout.setSpacing(8)

        btn_style = f"""
            QPushButton {{
                background-color: {COLOR_RAISED_PANEL};
                color: {COLOR_TEXT_MAIN};
                border: 1px solid {COLOR_PANEL_EDGE};
                border-radius: 6px;
                padding: 6px 10px;
                font-weight: bold;
                font-size: 11px;
            }}
            QPushButton:hover {{
                border-color: {COLOR_LIGHTNING};
                color: {COLOR_LIGHTNING};
            }}
        """

        self.btn_back = QPushButton("◀ Back")
        self.btn_back.setStyleSheet(btn_style)
        self.btn_back.clicked.connect(self._go_back)
        tb_layout.addWidget(self.btn_back)

        self.btn_up = QPushButton("▲ Up")
        self.btn_up.setStyleSheet(btn_style)
        self.btn_up.clicked.connect(self._go_up)
        tb_layout.addWidget(self.btn_up)

        self.btn_refresh = QPushButton("⟳ Refresh")
        self.btn_refresh.setStyleSheet(btn_style)
        self.btn_refresh.clicked.connect(lambda: self.navigate_to(self.current_dir))
        tb_layout.addWidget(self.btn_refresh)

        # Address Path Display
        self.path_bar = QLineEdit()
        self.path_bar.setReadOnly(True)
        self.path_bar.setStyleSheet(
            f"background-color: {COLOR_RAISED_PANEL}; color: {COLOR_LIGHTNING}; border: 1px solid {COLOR_PANEL_EDGE}; border-radius: 6px; padding: 6px 10px; font-size: 12px; font-weight: 600;"
        )
        tb_layout.addWidget(self.path_bar, 1)

        # Action Buttons
        self.btn_new_folder = QPushButton("📁 + Folder")
        self.btn_new_folder.setStyleSheet(btn_style)
        self.btn_new_folder.clicked.connect(self._create_folder)
        tb_layout.addWidget(self.btn_new_folder)

        self.btn_new_file = QPushButton("📄 + File")
        self.btn_new_file.setStyleSheet(btn_style)
        self.btn_new_file.clicked.connect(self._create_file)
        tb_layout.addWidget(self.btn_new_file)

        self.btn_delete = QPushButton("🗑️ Delete")
        self.btn_delete.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {COLOR_RAISED_PANEL};
                color: {COLOR_ERROR};
                border: 1px solid {COLOR_ERROR};
                border-radius: 6px;
                padding: 6px 10px;
                font-weight: bold;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: {COLOR_ERROR};
                color: {COLOR_NIGHT_SKY};
            }}
            """
        )
        self.btn_delete.clicked.connect(self._delete_selected)
        tb_layout.addWidget(self.btn_delete)

        main_layout.addWidget(toolbar)

        # 2. Main Content Splitter (File Table on left, Preview on right)
        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.setStyleSheet(
            f"""
            QSplitter::handle {{
                background-color: {COLOR_PANEL_EDGE};
                width: 2px;
            }}
            """
        )

        # File Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Name", "Size", "Type", "Modified"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.setStyleSheet(
            f"""
            QTableWidget {{
                background-color: {COLOR_STORM_CLOUD};
                border: 1px solid {COLOR_PANEL_EDGE};
                border-radius: 8px;
                color: {COLOR_TEXT_MAIN};
                font-size: 12px;
            }}
            QHeaderView::section {{
                background-color: {COLOR_RAISED_PANEL};
                color: {COLOR_LIGHTNING};
                padding: 6px;
                border: 1px solid {COLOR_PANEL_EDGE};
                font-weight: bold;
            }}
            QTableWidget::item {{
                padding: 6px;
                border-bottom: 1px solid rgba(48, 69, 103, 0.4);
            }}
            QTableWidget::item:selected {{
                background-color: rgba(56, 201, 255, 0.2);
                color: {COLOR_LIGHTNING};
            }}
            """
        )
        self.table.cellDoubleClicked.connect(self._on_item_double_clicked)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        splitter.addWidget(self.table)

        # Preview Panel
        preview_frame = QFrame()
        preview_frame.setStyleSheet(
            f"background-color: {COLOR_STORM_CLOUD}; border: 1px solid {COLOR_PANEL_EDGE}; border-radius: 8px; padding: 10px;"
        )
        pv_layout = QVBoxLayout(preview_frame)
        pv_layout.setContentsMargins(8, 8, 8, 8)
        pv_layout.setSpacing(8)

        pv_title = QLabel("👁️ Item Preview")
        pv_title.setStyleSheet(f"font-weight: bold; color: {COLOR_LIGHTNING}; font-size: 12px; border: none;")
        pv_layout.addWidget(pv_title)

        self.preview_image = QLabel()
        self.preview_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_image.setStyleSheet("border: none;")
        self.preview_image.hide()
        pv_layout.addWidget(self.preview_image)

        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setStyleSheet(
            f"background-color: {COLOR_RAISED_PANEL}; color: {COLOR_TEXT_MAIN}; border: 1px solid {COLOR_PANEL_EDGE}; border-radius: 6px; font-size: 11px;"
        )
        pv_layout.addWidget(self.preview_text, 1)

        self.preview_info = QLabel("Select a file to inspect details")
        self.preview_info.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 11px; border: none;")
        pv_layout.addWidget(self.preview_info)

        splitter.addWidget(preview_frame)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        main_layout.addWidget(splitter, 1)

        # Status Bar
        self.status_label = QLabel()
        self.status_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 11px;")
        main_layout.addWidget(self.status_label)

    def navigate_to(self, target_path: Path):
        """Navigate to a directory safely within user sandbox."""
        resolved = target_path.resolve()
        # Security: Sandbox check
        if not str(resolved).startswith(str(self.root_dir.resolve())):
            resolved = self.root_dir

        self.current_dir = resolved
        rel_str = "~/" + str(self.current_dir.relative_to(self.root_dir)).replace("\\", "/")
        if rel_str == "~/." or rel_str == "~/":
            rel_str = "~ (Home Storage)"
        self.path_bar.setText(rel_str)

        self._populate_table()

    def _populate_table(self):
        self.table.setRowCount(0)
        try:
            entries = list(self.current_dir.iterdir())
        except Exception:
            entries = []

        # Sort: directories first, then files
        entries = sorted(entries, key=lambda p: (not p.is_dir(), p.name.lower()))

        self.table.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            is_dir = entry.is_dir()
            icon = "📁 " if is_dir else "📄 "

            # Name
            name_item = QTableWidgetItem(f"{icon}{entry.name}")
            name_item.setData(Qt.ItemDataRole.UserRole, str(entry))
            self.table.setItem(row, 0, name_item)

            # Size
            if is_dir:
                size_str = "<DIR>"
            else:
                try:
                    sz = entry.stat().st_size
                    if sz < 1024:
                        size_str = f"{sz} B"
                    elif sz < 1024 * 1024:
                        size_str = f"{sz / 1024:.1f} KB"
                    else:
                        size_str = f"{sz / (1024*1024):.1f} MB"
                except Exception:
                    size_str = "—"
            size_item = QTableWidgetItem(size_str)
            self.table.setItem(row, 1, size_item)

            # Type
            type_str = "Folder" if is_dir else entry.suffix.upper()[1:] + " File" if entry.suffix else "File"
            self.table.setItem(row, 2, QTableWidgetItem(type_str))

            # Modified
            try:
                mtime = datetime.fromtimestamp(entry.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            except Exception:
                mtime = "—"
            self.table.setItem(row, 3, QTableWidgetItem(mtime))

        self.status_label.setText(f"{len(entries)} items in current folder")

    def _go_back(self):
        if len(self.history) > 1:
            self.history.pop()
            prev = self.history[-1]
            self.navigate_to(prev)

    def _go_up(self):
        parent = self.current_dir.parent
        if str(parent.resolve()).startswith(str(self.root_dir.resolve())):
            self.history.append(parent)
            self.navigate_to(parent)

    def _on_item_double_clicked(self, row: int, col: int):
        item = self.table.item(row, 0)
        if not item:
            return
        path_str = item.data(Qt.ItemDataRole.UserRole)
        p = Path(path_str)
        if p.is_dir():
            self.history.append(p)
            self.navigate_to(p)

    def _on_selection_changed(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            self.preview_image.hide()
            self.preview_text.clear()
            self.preview_info.setText("Select an item to view preview")
            return

        row = selected_rows[0].row()
        item = self.table.item(row, 0)
        if not item:
            return

        path = Path(item.data(Qt.ItemDataRole.UserRole))
        if path.is_dir():
            self.preview_image.hide()
            self.preview_text.clear()
            self.preview_info.setText(f"📁 Folder: {path.name}\nContains {len(list(path.iterdir()))} items")
            return

        # Preview File
        ext = path.suffix.lower()
        if ext in (".png", ".jpg", ".jpeg", ".bmp", ".gif"):
            self.preview_text.hide()
            pixmap = QPixmap(str(path))
            if not pixmap.isNull():
                self.preview_image.setPixmap(pixmap.scaled(240, 240, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                self.preview_image.show()
                self.preview_info.setText(f"🖼️ Image: {path.name} ({pixmap.width()}x{pixmap.height()})")
        else:
            self.preview_image.hide()
            self.preview_text.show()
            try:
                # Read first 10KB
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read(10240)
                self.preview_text.setPlainText(content)
                self.preview_info.setText(f"📄 File: {path.name} ({path.stat().st_size} bytes)")
            except Exception as e:
                self.preview_text.setPlainText(f"Unable to read file contents: {e}")
                self.preview_info.setText(f"File: {path.name}")

    def _create_folder(self):
        name, ok = QInputDialog.getText(self, "New Folder", "Enter folder name:")
        if ok and name.strip():
            safe_name = sanitize_filename(name.strip())
            new_path = self.current_dir / safe_name
            new_path.mkdir(exist_ok=True)
            self.navigate_to(self.current_dir)

    def _create_file(self):
        name, ok = QInputDialog.getText(self, "New File", "Enter file name (e.g. document.txt):")
        if ok and name.strip():
            safe_name = sanitize_filename(name.strip())
            new_path = self.current_dir / safe_name
            if not new_path.exists():
                new_path.write_text("", encoding="utf-8")
            self.navigate_to(self.current_dir)

    def _delete_selected(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            return

        row = selected_rows[0].row()
        item = self.table.item(row, 0)
        if not item:
            return

        path = Path(item.data(Qt.ItemDataRole.UserRole))
        # Prevent deleting the root directory
        if path.resolve() == self.root_dir.resolve():
            return

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete '{path.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
                self.navigate_to(self.current_dir)
            except Exception as e:
                QMessageBox.warning(self, "Delete Error", f"Failed to delete item: {e}")
