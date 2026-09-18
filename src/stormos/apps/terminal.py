"""StormOS Terminal Application.

Provides a cinematic dark storm console supporting shell commands,
file manipulation, math calculations, app launching, and system diagnostics.
"""

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QKeyEvent, QTextCursor
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from stormos.apps.calculator import evaluate_expression
from stormos.apps.registry import AppRegistry
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
    ORG_NAME,
)
from stormos.core.paths import USERS_DIR
from stormos.core.security import sanitize_filename
from stormos.services.user_manager import UserProfile


class TerminalApp(QWidget):
    """Interactive StormOS cyber console."""

    exit_requested = Signal()
    app_launch_requested = Signal(str)

    def __init__(self, current_user: Optional[UserProfile] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.current_user = current_user
        self.root_dir = self._get_user_root()
        self.current_dir = self.root_dir
        self.history: List[str] = []
        self.history_index: int = 0

        self._setup_ui()
        self._print_welcome_banner()

    def _get_user_root(self) -> Path:
        if self.current_user and self.current_user.username:
            d = USERS_DIR / self.current_user.username
        else:
            d = Path("users/guest")
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _get_prompt_str(self) -> str:
        username = self.current_user.username if self.current_user else "guest"
        try:
            rel = "~/" + str(self.current_dir.relative_to(self.root_dir)).replace("\\", "/")
            if rel == "~/." or rel == "~/":
                rel = "~"
        except Exception:
            rel = "~"
        return f"{username}@stormos:{rel}$ "

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        self.output_view = QPlainTextEdit()
        self.output_view.setReadOnly(True)
        self.output_view.setStyleSheet(
            f"""
            QPlainTextEdit {{
                background-color: #070B16;
                color: #A9EBFF;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
                border: 1px solid {COLOR_PANEL_EDGE};
                border-radius: 8px;
                padding: 10px;
                line-height: 1.4;
            }}
            """
        )
        layout.addWidget(self.output_view, 1)

        # Prompt input bar
        input_container = QFrame()
        input_container.setStyleSheet(
            f"""
            QFrame {{
                background-color: {COLOR_RAISED_PANEL};
                border: 1px solid {COLOR_PANEL_EDGE};
                border-radius: 6px;
                padding: 2px 6px;
            }}
            """
        )
        input_layout = QHBoxLayout(input_container)
        input_layout.setContentsMargins(4, 2, 4, 2)
        input_layout.setSpacing(6)

        self.prompt_label = QLabel(self._get_prompt_str())
        self.prompt_label.setStyleSheet(
            f"color: {COLOR_LIGHTNING}; font-family: 'Consolas', monospace; font-size: 12px; font-weight: bold; background: transparent;"
        )
        input_layout.addWidget(self.prompt_label)

        self.command_input = QLineEdit()
        self.command_input.setStyleSheet(
            f"""
            QLineEdit {{
                background: transparent;
                border: none;
                color: {COLOR_TEXT_MAIN};
                font-family: 'Consolas', monospace;
                font-size: 12px;
            }}
            """
        )
        self.command_input.returnPressed.connect(self._handle_command)
        input_layout.addWidget(self.command_input, 1)

        layout.addWidget(input_container)

    def _print_welcome_banner(self):
        banner = (
            f"⚡ {APP_NAME} Console [Version {APP_VERSION}]\n"
            f"   (c) {ORG_NAME}. All rights reserved.\n"
            f"   Type 'help' for a list of built-in commands.\n"
            "--------------------------------------------------\n"
        )
        self._append_output(banner)

    def _append_output(self, text: str):
        self.output_view.appendPlainText(text)
        self.output_view.moveCursor(QTextCursor.MoveOperation.End)

    def _handle_command(self):
        raw_cmd = self.command_input.text().strip()
        self.command_input.clear()
        if not raw_cmd:
            return

        prompt = self._get_prompt_str()
        self._append_output(f"{prompt}{raw_cmd}")

        self.history.append(raw_cmd)
        self.history_index = len(self.history)

        parts = raw_cmd.split()
        cmd = parts[0].lower()
        args = parts[1:]

        if cmd == "help":
            self._cmd_help()
        elif cmd in ("ver", "version"):
            self._append_output(f"{APP_NAME} v{APP_VERSION} ({ORG_NAME})")
        elif cmd == "clear":
            self.output_view.clear()
        elif cmd == "calc":
            self._cmd_calc(" ".join(args))
        elif cmd in ("ls", "dir"):
            self._cmd_ls(args)
        elif cmd == "pwd":
            self._append_output(str(self.current_dir))
        elif cmd == "cd":
            self._cmd_cd(args[0] if args else "")
        elif cmd == "cat":
            self._cmd_cat(args[0] if args else "")
        elif cmd == "mkdir":
            self._cmd_mkdir(args[0] if args else "")
        elif cmd == "touch":
            self._cmd_touch(args[0] if args else "")
        elif cmd == "rm":
            self._cmd_rm(args[0] if args else "")
        elif cmd == "whoami":
            user = self.current_user.username if self.current_user else "guest"
            role = self.current_user.role if self.current_user else "guest"
            self._append_output(f"User: {user} | Role: {role}")
        elif cmd == "date":
            self._append_output(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        elif cmd == "echo":
            self._append_output(" ".join(args))
        elif cmd == "apps":
            self._cmd_apps()
        elif cmd == "open":
            if args:
                self.app_launch_requested.emit(args[0].lower())
                self._append_output(f"Launching app '{args[0]}'...")
            else:
                self._append_output("Usage: open <app_id>")
        elif cmd in ("exit", "quit"):
            self.exit_requested.emit()
        else:
            self._append_output(f"Unknown command: '{cmd}'. Type 'help' for available commands.")

        self.prompt_label.setText(self._get_prompt_str())

    def _cmd_help(self):
        text = (
            "Available Commands:\n"
            "  help             - Show this help summary\n"
            "  ver              - Show StormOS version information\n"
            "  clear            - Clear terminal output\n"
            "  calc <expr>      - Evaluate a math formula (e.g. calc (100 * 1.15) + sqrt(144))\n"
            "  ls [dir]         - List files in current or target folder\n"
            "  pwd              - Print current working directory\n"
            "  cd <dir>         - Change directory within sandbox\n"
            "  cat <file>       - Display contents of a text file\n"
            "  mkdir <dir>      - Create a new directory\n"
            "  touch <file>     - Create an empty file\n"
            "  rm <file>        - Delete a file or empty directory\n"
            "  apps             - List all registered applications\n"
            "  open <app_id>    - Launch an application\n"
            "  whoami           - Show current user and role\n"
            "  date             - Display current system date and time\n"
            "  echo <msg>       - Print text to screen\n"
            "  exit             - Close terminal window\n"
        )
        self._append_output(text)

    def _cmd_calc(self, expr: str):
        if not expr:
            self._append_output("Usage: calc <expression> (e.g. calc 145 * 1.15)")
            return
        valid, res = evaluate_expression(expr)
        if valid:
            self._append_output(f"= {res}")
        else:
            self._append_output(f"Error: {res}")

    def _cmd_ls(self, args: List[str]):
        target = self.current_dir
        if args:
            safe = sanitize_filename(args[0])
            target = (self.current_dir / safe).resolve()

        if not str(target).startswith(str(self.root_dir.resolve())):
            self._append_output("Access denied: path outside sandbox")
            return

        if not target.exists():
            self._append_output(f"No such directory: {target.name}")
            return

        lines = []
        for item in sorted(target.iterdir()):
            suffix = "/" if item.is_dir() else ""
            lines.append(f"  {item.name}{suffix}")
        self._append_output("\n".join(lines) if lines else "  <Empty Directory>")

    def _cmd_cd(self, path_str: str):
        if not path_str or path_str == "~":
            self.current_dir = self.root_dir
            return

        if path_str == "..":
            parent = self.current_dir.parent
            if str(parent.resolve()).startswith(str(self.root_dir.resolve())):
                self.current_dir = parent
            return

        safe = sanitize_filename(path_str)
        target = (self.current_dir / safe).resolve()
        if not str(target).startswith(str(self.root_dir.resolve())):
            self._append_output("Access denied: path outside sandbox")
            return

        if target.exists() and target.is_dir():
            self.current_dir = target
        else:
            self._append_output(f"Directory not found: {path_str}")

    def _cmd_cat(self, filename: str):
        if not filename:
            self._append_output("Usage: cat <filename>")
            return
        safe = sanitize_filename(filename)
        target = self.current_dir / safe
        if not target.exists() or not target.is_file():
            self._append_output(f"File not found: {filename}")
            return
        try:
            with open(target, "r", encoding="utf-8", errors="ignore") as f:
                self._append_output(f.read())
        except Exception as e:
            self._append_output(f"Failed to read file: {e}")

    def _cmd_mkdir(self, dir_name: str):
        if not dir_name:
            self._append_output("Usage: mkdir <folder_name>")
            return
        safe = sanitize_filename(dir_name)
        target = self.current_dir / safe
        target.mkdir(exist_ok=True)
        self._append_output(f"Created directory '{safe}'")

    def _cmd_touch(self, filename: str):
        if not filename:
            self._append_output("Usage: touch <filename>")
            return
        safe = sanitize_filename(filename)
        target = self.current_dir / safe
        target.touch(exist_ok=True)
        self._append_output(f"Touched file '{safe}'")

    def _cmd_rm(self, filename: str):
        if not filename:
            self._append_output("Usage: rm <filename>")
            return
        safe = sanitize_filename(filename)
        target = self.current_dir / safe
        if not target.exists():
            self._append_output(f"File not found: {filename}")
            return
        try:
            if target.is_dir():
                target.rmdir()
            else:
                target.unlink()
            self._append_output(f"Removed '{safe}'")
        except Exception as e:
            self._append_output(f"Failed to delete: {e}")

    def _cmd_apps(self):
        apps = AppRegistry.get_instance().list_apps()
        self._append_output("Registered Applications:")
        for a in apps:
            self._append_output(f"  {a.icon} {a.id.ljust(12)} - {a.name} ({a.category})")

    def keyPressEvent(self, event: QKeyEvent):
        # Command history navigation
        if event.key() == Qt.Key.Key_Up:
            if self.history and self.history_index > 0:
                self.history_index -= 1
                self.command_input.setText(self.history[self.history_index])
            event.accept()
            return
        elif event.key() == Qt.Key.Key_Down:
            if self.history and self.history_index < len(self.history) - 1:
                self.history_index += 1
                self.command_input.setText(self.history[self.history_index])
            else:
                self.history_index = len(self.history)
                self.command_input.clear()
            event.accept()
            return
        super().keyPressEvent(event)
