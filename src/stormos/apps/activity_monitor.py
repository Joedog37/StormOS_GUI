"""StormOS Activity and System Monitor.

Provides resource telemetry, memory and CPU usage indicators, active
window and task inspection, and OS uptime metrics.
"""

import os
import sys
import time
from datetime import datetime, timedelta
from typing import Optional
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from stormos.core.constants import (
    APP_NAME,
    APP_VERSION,
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
    ORG_NAME,
)
from stormos.services.user_manager import UserProfile


START_TIME = time.time()


class ActivityMonitorApp(QWidget):
    """System resource telemetry and task manager."""

    def __init__(self, current_user: Optional[UserProfile] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.current_user = current_user
        self._sim_tick = 0
        self._setup_ui()

        # Telemetry update timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_telemetry)
        self.timer.start(1000)
        self._update_telemetry()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(12)

        # Overview cards grid
        grid = QGridLayout()
        grid.setSpacing(10)

        # Card 1: CPU Usage
        self.card_cpu = self._create_metric_card("⚡ CPU Load", "3.4%", "8 Cores @ 3.60 GHz")
        grid.addWidget(self.card_cpu["frame"], 0, 0)

        # Card 2: Memory Usage
        self.card_mem = self._create_metric_card("🧠 Memory (RAM)", "1.8 GB / 16.0 GB", "11.2% Allocated")
        grid.addWidget(self.card_mem["frame"], 0, 1)

        # Card 3: Storage
        self.card_disk = self._create_metric_card("💾 User Sandbox", "4.2 MB", "Local Isolated Profile")
        grid.addWidget(self.card_disk["frame"], 0, 2)

        # Card 4: System Uptime
        self.card_uptime = self._create_metric_card("⏱️ StormOS Uptime", "00:00:00", f"Host: Windows Python {sys.version.split()[0]}")
        grid.addWidget(self.card_uptime["frame"], 0, 3)

        main_layout.addLayout(grid)

        # Active Tasks and Processes Table
        table_frame = QFrame()
        table_frame.setStyleSheet(
            f"background-color: {COLOR_STORM_CLOUD}; border: 1px solid {COLOR_PANEL_EDGE}; border-radius: 8px; padding: 10px;"
        )
        tf_layout = QVBoxLayout(table_frame)
        tf_layout.setSpacing(8)

        lbl = QLabel("📊 Active StormOS System Tasks & Services")
        lbl.setStyleSheet(f"font-weight: bold; color: {COLOR_LIGHTNING}; font-size: 12px; border: none;")
        tf_layout.addWidget(lbl)

        self.proc_table = QTableWidget()
        self.proc_table.setColumnCount(4)
        self.proc_table.setHorizontalHeaderLabels(["Process / Service", "PID", "Status", "Memory RSS"])
        self.proc_table.horizontalHeader().setStretchLastSection(True)
        self.proc_table.setShowGrid(False)
        self.proc_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.proc_table.setStyleSheet(
            f"""
            QTableWidget {{
                background-color: transparent;
                border: none;
                color: {COLOR_TEXT_MAIN};
                font-size: 11px;
            }}
            QHeaderView::section {{
                background-color: {COLOR_RAISED_PANEL};
                color: {COLOR_LIGHTNING};
                padding: 4px;
                border: 1px solid {COLOR_PANEL_EDGE};
                font-weight: bold;
            }}
            QTableWidget::item {{
                padding: 4px;
            }}
            """
        )
        tf_layout.addWidget(self.proc_table, 1)

        main_layout.addWidget(table_frame, 1)

    def _create_metric_card(self, title: str, val: str, sub: str) -> dict:
        frame = QFrame()
        frame.setStyleSheet(
            f"background-color: {COLOR_STORM_CLOUD}; border: 1px solid {COLOR_PANEL_EDGE}; border-radius: 8px; padding: 8px;"
        )
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"color: {COLOR_MIST_BLUE}; font-size: 11px; font-weight: bold; border: none;")
        layout.addWidget(title_lbl)

        val_lbl = QLabel(val)
        val_lbl.setStyleSheet(f"color: {COLOR_LIGHTNING}; font-size: 16px; font-weight: 800; border: none;")
        layout.addWidget(val_lbl)

        sub_lbl = QLabel(sub)
        sub_lbl.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 10px; border: none;")
        layout.addWidget(sub_lbl)

        return {"frame": frame, "val": val_lbl, "sub": sub_lbl}

    def _update_telemetry(self):
        self._sim_tick += 1
        # Uptime
        uptime_secs = int(time.time() - START_TIME)
        uptime_str = str(timedelta(seconds=uptime_secs))
        self.card_uptime["val"].setText(uptime_str)

        # Simulated dynamic CPU fluctuation
        cpu_pct = 2.5 + (self._sim_tick % 7) * 1.3
        self.card_cpu["val"].setText(f"{cpu_pct:.1f}%")

        # Telemetry table entries
        tasks = [
            ("⚡ StormOS Core Windowing System", str(os.getpid()), "Running (Optimal)", "64.2 MB"),
            ("🛡️ Storm Security & Auth Daemon", "1002", "Active (Enforcing)", "8.4 MB"),
            ("🎨 PySide6 Desktop Compositor", "1003", "Rendering 60 FPS", "42.8 MB"),
            ("📁 Storage Sandbox Monitor", "1004", "Idle", "5.1 MB"),
            ("📦 App Registry Service", "1005", "Listening", "6.7 MB"),
        ]

        self.proc_table.setRowCount(len(tasks))
        for r, (name, pid, status, mem) in enumerate(tasks):
            self.proc_table.setItem(r, 0, QTableWidgetItem(name))
            self.proc_table.setItem(r, 1, QTableWidgetItem(pid))
            self.proc_table.setItem(r, 2, QTableWidgetItem(status))
            self.proc_table.setItem(r, 3, QTableWidgetItem(mem))
