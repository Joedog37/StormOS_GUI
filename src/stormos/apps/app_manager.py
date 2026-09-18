"""StormOS App Store and Package Manager Application.

Provides a visual interface to browse, inspect, install, and manage
StormOS applications and safe package bundles.
"""

import json
from pathlib import Path
from typing import Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from stormos.apps.registry import AppMetadata, AppRegistry
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
from stormos.services.app_installer import AppInstallerService
from stormos.services.user_manager import UserProfile


SAMPLE_PACKAGES = [
    {
        "manifest": {
            "id": "weather_radar",
            "name": "Storm Weather Radar",
            "version": "1.2.0",
            "description": "Atmospheric telemetry, barometric pressure tracker, and storm warning radar.",
            "icon": "🌩️",
            "category": "Weather",
            "author": "Thunderhead Atmospheric Labs",
        },
        "files": {
            "README.md": "# Storm Weather Radar\n\nLive atmospheric radar and barometric sensor suite.\n\n• Live Doppler tracking\n• Storm cell severity index: 94%\n• Lightning strike density: 14/min\n• Wind velocity: 48 kt NW",
        },
    },
    {
        "manifest": {
            "id": "todo_tracker",
            "name": "Task & Mission Tracker",
            "version": "1.0.4",
            "description": "Minimalist mission checklist and priority organizer for StormOS.",
            "icon": "✅",
            "category": "Productivity",
            "author": "Thunderhead Systems",
        },
        "files": {
            "README.md": "# Mission Tracker\n\nDaily high-priority tasks and system objectives:\n\n[x] Initialize Phase 4 App ecosystem\n[x] Verify PBKDF2 cryptographic baseline\n[ ] Configure custom glass wallpaper widgets\n[ ] Prepare packaging suite",
        },
    },
]


class AppManagerApp(QWidget):
    """App Store and package management center."""

    app_launched = Signal(str)

    def __init__(self, current_user: Optional[UserProfile] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.current_user = current_user
        self.installer_service = AppInstallerService()
        self.selected_app_id: Optional[str] = None
        self._setup_ui()
        self.refresh_app_list()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        # Header with actions
        header_frame = QFrame()
        header_frame.setStyleSheet(
            f"background-color: {COLOR_STORM_CLOUD}; border: 1px solid {COLOR_PANEL_EDGE}; border-radius: 8px; padding: 6px 12px;"
        )
        h_layout = QHBoxLayout(header_frame)
        h_layout.setContentsMargins(4, 4, 4, 4)
        h_layout.setSpacing(10)

        title = QLabel("🛍️ StormOS App Store & Manager")
        title.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {COLOR_LIGHTNING}; background: transparent; border: none;")
        h_layout.addWidget(title)
        h_layout.addStretch()

        btn_style = f"""
            QPushButton {{
                background-color: {COLOR_RAISED_PANEL};
                color: {COLOR_TEXT_MAIN};
                border: 1px solid {COLOR_PANEL_EDGE};
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: bold;
                font-size: 11px;
            }}
            QPushButton:hover {{
                border-color: {COLOR_LIGHTNING};
                color: {COLOR_LIGHTNING};
            }}
        """

        self.btn_install_pkg = QPushButton("📦 Install .stormapp Package")
        self.btn_install_pkg.setStyleSheet(btn_style)
        self.btn_install_pkg.clicked.connect(self._open_package_file_dialog)
        h_layout.addWidget(self.btn_install_pkg)

        main_layout.addWidget(header_frame)

        # Main Splitter: App List on left, App Details on right
        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.setStyleSheet(
            f"""
            QSplitter::handle {{
                background-color: {COLOR_PANEL_EDGE};
                width: 2px;
            }}
            """
        )

        # Left: App list
        list_frame = QFrame()
        list_frame.setStyleSheet(
            f"background-color: {COLOR_STORM_CLOUD}; border: 1px solid {COLOR_PANEL_EDGE}; border-radius: 8px; padding: 8px;"
        )
        l_layout = QVBoxLayout(list_frame)
        l_layout.setContentsMargins(4, 4, 4, 4)
        l_layout.setSpacing(6)

        lbl_installed = QLabel("Installed & Built-in Apps")
        lbl_installed.setStyleSheet(f"font-weight: bold; color: {COLOR_LIGHTNING}; font-size: 11px; border: none;")
        l_layout.addWidget(lbl_installed)

        self.app_list_widget = QListWidget()
        self.app_list_widget.setStyleSheet(
            f"""
            QListWidget {{
                background: transparent;
                border: none;
                color: {COLOR_TEXT_MAIN};
            }}
            QListWidget::item {{
                background-color: {COLOR_RAISED_PANEL};
                border: 1px solid {COLOR_PANEL_EDGE};
                border-radius: 6px;
                padding: 8px;
                margin-bottom: 4px;
            }}
            QListWidget::item:selected {{
                background-color: rgba(56, 201, 255, 0.2);
                border-color: {COLOR_LIGHTNING};
                color: {COLOR_LIGHTNING};
            }}
            """
        )
        self.app_list_widget.currentRowChanged.connect(self._on_app_selected)
        l_layout.addWidget(self.app_list_widget)

        # Sample packages section
        lbl_samples = QLabel("Featured Sample Packages")
        lbl_samples.setStyleSheet(f"font-weight: bold; color: {COLOR_MIST_BLUE}; font-size: 11px; border: none; margin-top: 6px;")
        l_layout.addWidget(lbl_samples)

        for sample in SAMPLE_PACKAGES:
            m = sample["manifest"]
            btn_sample = QPushButton(f"{m['icon']} Install {m['name']}")
            btn_sample.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: {COLOR_RAISED_PANEL};
                    color: {COLOR_LIGHTNING};
                    border: 1px dashed {COLOR_LIGHTNING};
                    border-radius: 6px;
                    padding: 6px;
                    font-size: 11px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background-color: {COLOR_LIGHTNING};
                    color: {COLOR_NIGHT_SKY};
                }}
                """
            )
            btn_sample.clicked.connect(lambda _, s=sample: self._install_sample_package(s))
            l_layout.addWidget(btn_sample)

        splitter.addWidget(list_frame)

        # Right: App Details & Actions
        details_frame = QFrame()
        details_frame.setStyleSheet(
            f"background-color: {COLOR_STORM_CLOUD}; border: 1px solid {COLOR_PANEL_EDGE}; border-radius: 8px; padding: 14px;"
        )
        self.d_layout = QVBoxLayout(details_frame)
        self.d_layout.setContentsMargins(10, 10, 10, 10)
        self.d_layout.setSpacing(10)

        self.detail_icon_title = QLabel("Select an App")
        self.detail_icon_title.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {COLOR_LIGHTNING}; border: none;")
        self.d_layout.addWidget(self.detail_icon_title)

        self.detail_meta = QLabel()
        self.detail_meta.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 11px; border: none;")
        self.d_layout.addWidget(self.detail_meta)

        self.detail_desc = QTextEdit()
        self.detail_desc.setReadOnly(True)
        self.detail_desc.setStyleSheet(
            f"background-color: {COLOR_RAISED_PANEL}; color: {COLOR_TEXT_MAIN}; border: 1px solid {COLOR_PANEL_EDGE}; border-radius: 6px; padding: 10px; font-size: 12px;"
        )
        self.d_layout.addWidget(self.detail_desc, 1)

        # Action Buttons row
        action_row = QHBoxLayout()
        action_row.setSpacing(8)

        self.btn_launch_app = QPushButton("🚀 Open App")
        self.btn_launch_app.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {COLOR_LIGHTNING};
                color: {COLOR_NIGHT_SKY};
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 800;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: #A9EBFF;
            }}
            """
        )
        self.btn_launch_app.clicked.connect(self._launch_selected_app)
        action_row.addWidget(self.btn_launch_app)

        self.btn_uninstall = QPushButton("🗑️ Uninstall")
        self.btn_uninstall.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {COLOR_RAISED_PANEL};
                color: {COLOR_ERROR};
                border: 1px solid {COLOR_ERROR};
                border-radius: 6px;
                padding: 8px 14px;
                font-weight: bold;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: {COLOR_ERROR};
                color: {COLOR_NIGHT_SKY};
            }}
            """
        )
        self.btn_uninstall.clicked.connect(self._uninstall_selected_app)
        action_row.addWidget(self.btn_uninstall)

        action_row.addStretch()
        self.d_layout.addLayout(action_row)

        splitter.addWidget(details_frame)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        main_layout.addWidget(splitter, 1)

    def refresh_app_list(self):
        """Populate the app list from AppRegistry and installed apps."""
        self.app_list_widget.clear()
        apps = AppRegistry.get_instance().list_apps()
        for app in apps:
            item = QListWidgetItem(f"{app.icon}  {app.name}  [{app.category}]")
            item.setData(Qt.ItemDataRole.UserRole, app.id)
            self.app_list_widget.addItem(item)

        if self.app_list_widget.count() > 0:
            self.app_list_widget.setCurrentRow(0)

    def _on_app_selected(self, row: int):
        if row < 0:
            return
        item = self.app_list_widget.item(row)
        if not item:
            return
        app_id = item.data(Qt.ItemDataRole.UserRole)
        self.selected_app_id = app_id
        app = AppRegistry.get_instance().get_app(app_id)
        if not app:
            return

        self.detail_icon_title.setText(f"{app.icon}  {app.name}")
        type_str = "System Built-in" if app.is_builtin else "Installed Package"
        self.detail_meta.setText(f"Identifier: {app.id} • Category: {app.category} • Type: {type_str}")
        self.detail_desc.setPlainText(app.description or "No description provided.")

        self.btn_uninstall.setEnabled(not app.is_builtin)
        self.btn_uninstall.setVisible(not app.is_builtin)

    def _launch_selected_app(self):
        if self.selected_app_id:
            self.app_launched.emit(self.selected_app_id)

    def _uninstall_selected_app(self):
        if not self.selected_app_id:
            return
        app = AppRegistry.get_instance().get_app(self.selected_app_id)
        if not app or app.is_builtin:
            return

        reply = QMessageBox.question(
            self,
            "Confirm Uninstall",
            f"Are you sure you want to uninstall '{app.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            success, msg = self.installer_service.uninstall_app(self.selected_app_id, self.current_user)
            if success:
                QMessageBox.information(self, "Uninstalled", msg)
                self.refresh_app_list()
            else:
                QMessageBox.warning(self, "Error", msg)

    def _open_package_file_dialog(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select StormOS App Package", "", "StormOS Packages (*.stormapp *.zip *.json)"
        )
        if path:
            p = Path(path)
            if p.suffix == ".json":
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        manifest = json.load(f)
                    success, msg = self.installer_service.install_from_manifest_and_files(
                        manifest, user=self.current_user
                    )
                except Exception as e:
                    success, msg = False, f"Failed to read manifest JSON: {e}"
            else:
                success, msg = self.installer_service.install_package(p, user=self.current_user)

            if success:
                QMessageBox.information(self, "Installation Successful", msg)
                self.refresh_app_list()
            else:
                QMessageBox.warning(self, "Installation Failed", msg)

    def _install_sample_package(self, sample: dict):
        manifest = sample["manifest"]
        files = sample.get("files", {})
        success, msg = self.installer_service.install_from_manifest_and_files(
            manifest, files=files, user=self.current_user
        )
        if success:
            QMessageBox.information(self, "Sample Installed", msg)
            self.refresh_app_list()
        else:
            QMessageBox.warning(self, "Error", msg)
