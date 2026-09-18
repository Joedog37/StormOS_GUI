"""StormOS Notepad++ Style Code Studio & Notes Editor.

Provides a multi-tab, syntax-highlighted code and note workspace
with line numbers, auto-indentation, find/replace, code runner,
file sidebar, and telemetry status for Python, JSON, Markdown, HTML, Shell, and Plain Text.
"""

import io
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import QPoint, QRect, QRegularExpression, QSize, Qt, Signal
from PySide6.QtGui import (
    QAction,
    QColor,
    QFont,
    QFontMetrics,
    QIcon,
    QKeySequence,
    QPainter,
    QPalette,
    QPen,
    QShortcut,
    QSyntaxHighlighter,
    QTextCharFormat,
    QTextCursor,
    QTextDocument,
)
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from stormos.core.constants import (
    COLOR_ERROR,
    COLOR_LIGHTNING,
    COLOR_LIGHTNING_GLOW,
    COLOR_MIST_BLUE,
    COLOR_NIGHT_SKY,
    COLOR_PANEL_EDGE,
    COLOR_RAISED_PANEL,
    COLOR_STORM_CLOUD,
    COLOR_SUCCESS,
    COLOR_TEXT_MAIN,
    COLOR_TEXT_SECONDARY,
    COLOR_WARNING,
    FONT_FAMILY,
)
from stormos.core.paths import USERS_DIR
from stormos.core.security import sanitize_filename
from stormos.services.user_manager import UserProfile


# =====================================================================
# 1. SYNTAX HIGHLIGHTING ENGINE
# =====================================================================

class StormSyntaxHighlighter(QSyntaxHighlighter):
    """Multi-language syntax highlighter supporting Python, JSON, Markdown, HTML, Shell, and Text."""

    def __init__(self, parent: QTextDocument, language: str = "python"):
        super().__init__(parent)
        self.language = language.lower()
        self._rules: List[Tuple[QRegularExpression, QTextCharFormat]] = []
        self._setup_formats()
        self.set_language(language)

    def _setup_formats(self):
        # Keyword format (Electric Cyan / Ice Blue)
        self.fmt_keyword = QTextCharFormat()
        self.fmt_keyword.setForeground(QColor(COLOR_LIGHTNING))
        self.fmt_keyword.setFontWeight(QFont.Weight.Bold)

        # Builtin / Type format (Storm Amber)
        self.fmt_builtin = QTextCharFormat()
        self.fmt_builtin.setForeground(QColor(COLOR_WARNING))

        # String format (Neon Green / Mint)
        self.fmt_string = QTextCharFormat()
        self.fmt_string.setForeground(QColor(COLOR_SUCCESS))

        # Number format (Ice Blue / Cyan)
        self.fmt_number = QTextCharFormat()
        self.fmt_number.setForeground(QColor("#79C0FF"))

        # Comment format (Mist Blue / Muted Grey)
        self.fmt_comment = QTextCharFormat()
        self.fmt_comment.setForeground(QColor(COLOR_MIST_BLUE))
        self.fmt_comment.setFontItalic(True)

        # Decorator / Tag format (Purple / Magenta)
        self.fmt_decorator = QTextCharFormat()
        self.fmt_decorator.setForeground(QColor("#D2A8FF"))
        self.fmt_decorator.setFontWeight(QFont.Weight.Bold)

        # Markdown Header format
        self.fmt_header = QTextCharFormat()
        self.fmt_header.setForeground(QColor(COLOR_LIGHTNING))
        self.fmt_header.setFontWeight(QFont.Weight.ExtraBold)

    def set_language(self, language: str):
        self.language = language.lower()
        self._rules.clear()

        if self.language in ("python", "py"):
            self._setup_python_rules()
        elif self.language in ("json", "javascript", "js"):
            self._setup_json_js_rules()
        elif self.language in ("markdown", "md"):
            self._setup_markdown_rules()
        elif self.language in ("html", "xml"):
            self._setup_html_xml_rules()
        elif self.language in ("shell", "sh", "bash", "bat", "cmd", "ps1"):
            self._setup_shell_rules()

        self.rehighlight()

    def _setup_python_rules(self):
        keywords = [
            r"\bdef\b", r"\bclass\b", r"\breturn\b", r"\bimport\b", r"\bfrom\b",
            r"\bas\b", r"\bif\b", r"\belif\b", r"\belse\b", r"\bfor\b",
            r"\bwhile\b", r"\btry\b", r"\bexcept\b", r"\bfinally\b", r"\bwith\b",
            r"\byield\b", r"\blambda\b", r"\bpass\b", r"\bbreak\b", r"\bcontinue\b",
            r"\braise\b", r"\bassert\b", r"\bglobal\b", r"\bnonlocal\b",
            r"\basync\b", r"\bawait\b", r"\bis\b", r"\bin\b", r"\bnot\b", r"\band\b", r"\bor\b"
        ]
        for kw in keywords:
            self._rules.append((QRegularExpression(kw), self.fmt_keyword))

        builtins = [
            r"\bTrue\b", r"\bFalse\b", r"\bNone\b", r"\bself\b", r"\bcls\b",
            r"\bprint\b", r"\blen\b", r"\brange\b", r"\bstr\b", r"\bint\b",
            r"\bfloat\b", r"\bbool\b", r"\blist\b", r"\bdict\b", r"\bset\b",
            r"\btuple\b", r"\bopen\b", r"\bsuper\b", r"\btype\b", r"\benumerate\b",
            r"\bzip\b", r"\bmap\b", r"\bfilter\b", r"\ball\b", r"\bany\b"
        ]
        for b in builtins:
            self._rules.append((QRegularExpression(b), self.fmt_builtin))

        # Decorators
        self._rules.append((QRegularExpression(r"@[A-Za-z0-9_.]+"), self.fmt_decorator))

        # Numbers
        self._rules.append((QRegularExpression(r"\b0[xX][0-9a-fA-F]+\b|\b0[bB][01]+\b|\b\d+(\.\d+)?\b"), self.fmt_number))

        # Strings
        self._rules.append((QRegularExpression(r'"[^"\\]*(\\.[^"\\]*)*"'), self.fmt_string))
        self._rules.append((QRegularExpression(r"'[^'\\]*(\\.[^'\\]*)*'"), self.fmt_string))
        self._rules.append((QRegularExpression(r'f"[^"\\]*(\\.[^"\\]*)*"'), self.fmt_string))
        self._rules.append((QRegularExpression(r"f'[^'\\]*(\\.[^'\\]*)*'"), self.fmt_string))

        # Comments
        self._rules.append((QRegularExpression(r"#.*$"), self.fmt_comment))

    def _setup_json_js_rules(self):
        keywords = [
            r"\btrue\b", r"\bfalse\b", r"\bnull\b", r"\bfunction\b", r"\bvar\b",
            r"\blet\b", r"\bconst\b", r"\breturn\b", r"\bif\b", r"\belse\b",
            r"\bfor\b", r"\bwhile\b", r"\bimport\b", r"\bexport\b", r"\bfrom\b"
        ]
        for kw in keywords:
            self._rules.append((QRegularExpression(kw), self.fmt_keyword))

        # Object keys in JSON
        self._rules.append((QRegularExpression(r'"[A-Za-z0-9_$-]+"\s*:'), self.fmt_decorator))

        # Numbers
        self._rules.append((QRegularExpression(r"\b\d+(\.\d+)?\b"), self.fmt_number))

        # Strings
        self._rules.append((QRegularExpression(r'"[^"\\]*(\\.[^"\\]*)*"'), self.fmt_string))
        self._rules.append((QRegularExpression(r"'[^'\\]*(\\.[^'\\]*)*'"), self.fmt_string))

        # Comments
        self._rules.append((QRegularExpression(r"//.*$"), self.fmt_comment))

    def _setup_markdown_rules(self):
        # Headers (#, ##, ###)
        self._rules.append((QRegularExpression(r"^#{1,6}\s+.*$"), self.fmt_header))
        # Code blocks
        self._rules.append((QRegularExpression(r"`[^`]*`"), self.fmt_number))
        # Links
        self._rules.append((QRegularExpression(r"\[.*?\]\(.*?\)"), self.fmt_keyword))
        # Bold/Italic
        self._rules.append((QRegularExpression(r"\*\*.*?\*\*"), self.fmt_decorator))
        # List items
        self._rules.append((QRegularExpression(r"^\s*[-*+]\s+"), self.fmt_builtin))

    def _setup_html_xml_rules(self):
        # Tags (<tag>)
        self._rules.append((QRegularExpression(r"</?[A-Za-z0-9_-]+"), self.fmt_keyword))
        self._rules.append((QRegularExpression(r"/?>"), self.fmt_keyword))
        # Attributes
        self._rules.append((QRegularExpression(r"\b[A-Za-z0-9_-]+="), self.fmt_decorator))
        # Strings
        self._rules.append((QRegularExpression(r'"[^"]*"'), self.fmt_string))
        # Comments
        self._rules.append((QRegularExpression(r"<!--.*?-->"), self.fmt_comment))

    def _setup_shell_rules(self):
        keywords = [
            r"\becho\b", r"\bcd\b", r"\bls\b", r"\bdir\b", r"\bmkdir\b", r"\brm\b",
            r"\bpython\b", r"\bexit\b", r"\bif\b", r"\bthen\b", r"\belse\b", r"\bfi\b",
            r"\bfor\b", r"\bin\b", r"\bdo\b", r"\bdone\b", r"\bset\b", r"\bexport\b"
        ]
        for kw in keywords:
            self._rules.append((QRegularExpression(kw), self.fmt_keyword))
        self._rules.append((QRegularExpression(r"\$[A-Za-z0-9_]+|%[A-Za-z0-9_]+%"), self.fmt_decorator))
        self._rules.append((QRegularExpression(r"#.*$|rem\b.*$"), self.fmt_comment))
        self._rules.append((QRegularExpression(r'"[^"]*"'), self.fmt_string))

    def highlightBlock(self, text: str):
        for pattern, fmt in self._rules:
            match_iter = pattern.globalMatch(text)
            while match_iter.hasNext():
                match = match_iter.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), fmt)


# =====================================================================
# 2. LINE NUMBER GUTTER & CODE EDITOR
# =====================================================================

class LineNumberArea(QWidget):
    """Gutter widget rendering line numbers alongside the code editor."""

    def __init__(self, editor: "StormCodeEditor"):
        super().__init__(editor)
        self.editor = editor
        self.setCursor(Qt.CursorShape.ArrowCursor)

    def sizeHint(self) -> QSize:
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.editor.line_number_area_paint_event(event)


class StormCodeEditor(QPlainTextEdit):
    """Custom code editor with line numbers, syntax highlighting, and auto-indent."""

    cursor_telemetry_changed = Signal(int, int, int, int)  # line, col, total_lines, total_chars

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.line_number_area = LineNumberArea(self)

        # Monospace font
        font = QFont("Consolas", 11)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)
        self.setTabStopDistance(QFontMetrics(font).horizontalAdvance(' ') * 4)

        self.setCursor(Qt.CursorShape.IBeamCursor)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        # Connect signals
        self.blockCountChanged.connect(self._update_line_number_area_width)
        self.updateRequest.connect(self._update_line_number_area)
        self.cursorPositionChanged.connect(self._highlight_current_line)
        self.cursorPositionChanged.connect(self._emit_telemetry)
        self.textChanged.connect(self._emit_telemetry)

        self._update_line_number_area_width(0)
        self._highlight_current_line()
        self._apply_editor_styles()

    def _apply_editor_styles(self):
        self.setStyleSheet(
            f"""
            QPlainTextEdit {{
                background-color: {COLOR_NIGHT_SKY};
                color: {COLOR_TEXT_MAIN};
                border: 1px solid {COLOR_PANEL_EDGE};
                border-radius: 6px;
                padding: 4px;
                selection-background-color: rgba(56, 201, 255, 0.35);
                selection-color: #FFFFFF;
            }}
            """
        )

    def line_number_area_width(self) -> int:
        digits = max(1, len(str(max(1, self.blockCount()))))
        space = 20 + self.fontMetrics().horizontalAdvance('9') * digits
        return space

    def _update_line_number_area_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def _update_line_number_area(self, rect: QRect, dy: int):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())

        if rect.contains(self.viewport().rect()):
            self._update_line_number_area_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(
            QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height())
        )

    def line_number_area_paint_event(self, event):
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor(COLOR_STORM_CLOUD))

        # Right divider line
        painter.setPen(QPen(QColor(COLOR_PANEL_EDGE), 1))
        painter.drawLine(
            self.line_number_area.width() - 1,
            event.rect().top(),
            self.line_number_area.width() - 1,
            event.rect().bottom(),
        )

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())

        current_block = self.textCursor().blockNumber()

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                is_current = (block_number == current_block)

                if is_current:
                    painter.setPen(QColor(COLOR_LIGHTNING))
                    painter.setFont(QFont(self.font().family(), self.font().pointSize(), QFont.Weight.Bold))
                else:
                    painter.setPen(QColor(COLOR_TEXT_SECONDARY))
                    painter.setFont(self.font())

                painter.drawText(
                    0,
                    top,
                    self.line_number_area.width() - 8,
                    self.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight,
                    number,
                )

            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_number += 1

    def _highlight_current_line(self):
        extra_selections = []
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            line_color = QColor(COLOR_RAISED_PANEL)
            selection.format.setBackground(line_color)
            selection.format.setProperty(QTextCharFormat.Property.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extra_selections.append(selection)
        self.setExtraSelections(extra_selections)
        self.line_number_area.update()

    def _emit_telemetry(self):
        cursor = self.textCursor()
        line = cursor.blockNumber() + 1
        col = cursor.columnNumber() + 1
        total_lines = self.blockCount()
        total_chars = len(self.toPlainText())
        self.cursor_telemetry_changed.emit(line, col, total_lines, total_chars)

    def setTextCursor(self, cursor: QTextCursor):
        super().setTextCursor(cursor)
        self._emit_telemetry()

    def setPlainText(self, text: str):
        super().setPlainText(text)
        self._emit_telemetry()

    def keyPressEvent(self, event):
        # Auto-indent on Enter
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            cursor = self.textCursor()
            line_text = cursor.block().text()
            indent = len(line_text) - len(line_text.lstrip(' '))
            extra = "    " if line_text.rstrip().endswith(":") else ""

            super().keyPressEvent(event)
            self.insertPlainText(" " * indent + extra)
            return

        # Tab -> 4 spaces
        if event.key() == Qt.Key.Key_Tab and not (event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
            self.insertPlainText("    ")
            return

        # Shift + Tab -> Unindent
        if event.key() == Qt.Key.Key_Backtab or (event.key() == Qt.Key.Key_Tab and (event.modifiers() & Qt.KeyboardModifier.ShiftModifier)):
            cursor = self.textCursor()
            block = cursor.block()
            text = block.text()
            if text.startswith("    "):
                cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
                for _ in range(4):
                    cursor.deleteChar()
            elif text.startswith(" "):
                cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
                cursor.deleteChar()
            return

        # Duplicate line on Ctrl+D
        if event.key() == Qt.Key.Key_D and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            cursor = self.textCursor()
            cursor.select(QTextCursor.SelectionType.LineUnderCursor)
            line = cursor.selectedText()
            cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
            cursor.insertText("\n" + line)
            return

        super().keyPressEvent(event)


# =====================================================================
# 3. EDITOR TAB DOCUMENT CONTAINER
# =====================================================================

class DocumentTab:
    """Holds state for an open file in the editor."""

    def __init__(self, filename: str = "Untitled.py", path: Optional[Path] = None, language: str = "python"):
        self.filename = filename
        self.path = path
        self.language = language
        self.is_modified = False
        self.editor = StormCodeEditor()
        self.highlighter = StormSyntaxHighlighter(self.editor.document(), language=language)


# =====================================================================
# 4. MAIN NOTEPAD++ CODE STUDIO & NOTES APPLICATION
# =====================================================================

class NotesApp(QWidget):
    """Notepad++ style Code Studio and Notes Editor for StormOS."""

    def __init__(self, current_user: Optional[UserProfile] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.current_user = current_user
        self.notes_dir = self._get_notes_dir()
        self.user_docs_dir = self._get_user_docs_dir()
        self.tabs_data: List[DocumentTab] = []
        self._current_legacy_note_id: Optional[str] = None
        self._setup_ui()
        self._ensure_initial_notes()
        self.refresh_notes_list()

    def _get_notes_dir(self) -> Path:
        username = self.current_user.username if self.current_user else "guest"
        d = USERS_DIR / username / "notes"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _get_user_docs_dir(self) -> Path:
        username = self.current_user.username if self.current_user else "guest"
        d = USERS_DIR / username / "documents"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _ensure_initial_notes(self):
        """Ensure initial welcome note exists in notes directory."""
        welcome_file = self.notes_dir / "welcome_to_stormos.json"
        if not welcome_file.exists():
            welcome_data = {
                "id": "welcome_to_stormos",
                "title": "Welcome to StormOS Code Studio",
                "body": (
                    "# ========================================================\n"
                    "# ⚡ Welcome to StormOS Code Studio & Notepad++\n"
                    "# ========================================================\n"
                    "import sys\n\n"
                    "def main():\n"
                    '    print("⚡ StormOS Cyber Workspace Initialized")\n'
                    '    print(f"Running on Python {sys.version.split()[0]}")\n\n'
                    'if __name__ == "__main__":\n'
                    "    main()\n"
                ),
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }
            with open(welcome_file, "w", encoding="utf-8") as f:
                json.dump(welcome_data, f, indent=2)

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(6)

        self.main_splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.main_splitter.setStyleSheet(
            f"""
            QSplitter::handle {{
                background-color: {COLOR_PANEL_EDGE};
                width: 2px;
            }}
            """
        )

        # ----------------- LEFT SIDEBAR: NOTES & DOCUMENTS -----------------
        sidebar = QFrame()
        sidebar.setStyleSheet(f"background-color: {COLOR_STORM_CLOUD}; border: 1px solid {COLOR_PANEL_EDGE}; border-radius: 8px;")
        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(8, 8, 8, 8)
        sb_layout.setSpacing(6)

        # Header
        sb_header = QHBoxLayout()
        sb_title = QLabel("📝 Notes & Files")
        sb_title.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {COLOR_LIGHTNING}; background: transparent; border: none;")
        sb_header.addWidget(sb_title)

        self.btn_new = QPushButton("+ New")
        self.btn_new.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_new.setStyleSheet(self._btn_style())
        self.btn_new.clicked.connect(self.create_new_note)
        sb_header.addWidget(self.btn_new)
        sb_layout.addLayout(sb_header)

        # Search Bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search notes...")
        self.search_input.setCursor(Qt.CursorShape.IBeamCursor)
        self.search_input.setStyleSheet(f"background-color: {COLOR_RAISED_PANEL}; color: {COLOR_TEXT_MAIN}; padding: 4px; border: 1px solid {COLOR_PANEL_EDGE}; border-radius: 4px; font-size: 11px;")
        self.search_input.textChanged.connect(self._filter_notes_list)
        sb_layout.addWidget(self.search_input)

        # Notes List
        self.notes_list = QListWidget()
        self.notes_list.setCursor(Qt.CursorShape.PointingHandCursor)
        self.notes_list.setStyleSheet(
            f"""
            QListWidget {{
                background-color: {COLOR_RAISED_PANEL};
                color: {COLOR_TEXT_MAIN};
                border: 1px solid {COLOR_PANEL_EDGE};
                border-radius: 6px;
                padding: 4px;
            }}
            QListWidget::item {{
                padding: 6px;
                border-bottom: 1px solid {COLOR_PANEL_EDGE};
                border-radius: 4px;
            }}
            QListWidget::item:hover {{
                background-color: rgba(56, 201, 255, 0.15);
                color: {COLOR_LIGHTNING};
            }}
            QListWidget::item:selected {{
                background-color: rgba(56, 201, 255, 0.3);
                color: {COLOR_LIGHTNING};
                font-weight: bold;
            }}
            """
        )
        self.notes_list.itemClicked.connect(self._on_note_item_clicked)
        sb_layout.addWidget(self.notes_list, 1)

        # Sidebar footer action
        btn_delete = QPushButton("🗑️ Delete Note")
        btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_delete.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {COLOR_RAISED_PANEL};
                color: {COLOR_ERROR};
                border: 1px solid {COLOR_PANEL_EDGE};
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 92, 119, 0.2);
                border-color: {COLOR_ERROR};
            }}
            """
        )
        btn_delete.clicked.connect(self.delete_current_note)
        sb_layout.addWidget(btn_delete)

        self.main_splitter.addWidget(sidebar)

        # ----------------- RIGHT WORKSPACE: CODE STUDIO -----------------
        workspace = QWidget()
        ws_layout = QVBoxLayout(workspace)
        ws_layout.setContentsMargins(0, 0, 0, 0)
        ws_layout.setSpacing(6)

        # Top Action Bar / Toolbar
        toolbar = QFrame()
        toolbar.setStyleSheet(f"background-color: {COLOR_STORM_CLOUD}; border: 1px solid {COLOR_PANEL_EDGE}; border-radius: 6px; padding: 4px;")
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(6, 4, 6, 4)
        tb_layout.setSpacing(6)

        # Title Input (for compatibility and fast naming)
        self.title_input = QLineEdit("Untitled Note")
        self.title_input.setCursor(Qt.CursorShape.IBeamCursor)
        self.title_input.setStyleSheet(f"background-color: {COLOR_RAISED_PANEL}; color: {COLOR_LIGHTNING}; font-weight: bold; padding: 4px 8px; border: 1px solid {COLOR_PANEL_EDGE}; border-radius: 4px; font-size: 12px;")
        self.title_input.textChanged.connect(self._on_title_input_changed)
        tb_layout.addWidget(self.title_input, 1)

        btn_tb_new = QPushButton("📄 New Tab")
        btn_tb_new.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_tb_new.setStyleSheet(self._btn_style())
        btn_tb_new.clicked.connect(self.new_file)
        tb_layout.addWidget(btn_tb_new)

        btn_open = QPushButton("📁 Open File")
        btn_open.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_open.setStyleSheet(self._btn_style())
        btn_open.clicked.connect(self.open_file_dialog)
        tb_layout.addWidget(btn_open)

        self.btn_save = QPushButton("💾 Save")
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.setStyleSheet(self._btn_style())
        self.btn_save.clicked.connect(self.save_current_file)
        tb_layout.addWidget(self.btn_save)

        btn_save_as = QPushButton("Save As...")
        btn_save_as.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save_as.setStyleSheet(self._btn_style())
        btn_save_as.clicked.connect(self.save_as_file_dialog)
        tb_layout.addWidget(btn_save_as)

        # Find button
        btn_find = QPushButton("🔍 Find")
        btn_find.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_find.setStyleSheet(self._btn_style())
        btn_find.clicked.connect(self.toggle_find_bar)
        tb_layout.addWidget(btn_find)

        # Templates menu
        self.template_combo = QComboBox()
        self.template_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.template_combo.addItems([
            "⚡ Templates",
            "Python Boilerplate",
            "JSON Config",
            "Markdown Notes",
            "HTML5 Starter",
        ])
        self.template_combo.setStyleSheet(f"background-color: {COLOR_RAISED_PANEL}; color: {COLOR_TEXT_MAIN}; padding: 4px 6px; border: 1px solid {COLOR_PANEL_EDGE}; border-radius: 4px; font-size: 11px;")
        self.template_combo.currentIndexChanged.connect(self._on_template_selected)
        tb_layout.addWidget(self.template_combo)

        # Run Script Button
        btn_run = QPushButton("▶ Run Code")
        btn_run.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_run.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {COLOR_LIGHTNING};
                color: {COLOR_NIGHT_SKY};
                font-weight: bold;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: #A9EBFF;
            }}
            """
        )
        btn_run.clicked.connect(self.run_code_execution)
        tb_layout.addWidget(btn_run)

        ws_layout.addWidget(toolbar)

        # Find and Replace Panel (Collapsible)
        self.find_bar = QFrame()
        self.find_bar.setStyleSheet(f"background-color: {COLOR_RAISED_PANEL}; border: 1px solid {COLOR_PANEL_EDGE}; border-radius: 6px; padding: 6px;")
        fb_layout = QHBoxLayout(self.find_bar)
        fb_layout.setContentsMargins(8, 4, 8, 4)
        fb_layout.setSpacing(6)

        fb_layout.addWidget(QLabel("Find:"))
        self.find_input = QLineEdit()
        self.find_input.setCursor(Qt.CursorShape.IBeamCursor)
        self.find_input.setStyleSheet(f"background-color: {COLOR_STORM_CLOUD}; color: {COLOR_TEXT_MAIN}; padding: 4px; border: 1px solid {COLOR_PANEL_EDGE}; border-radius: 4px;")
        self.find_input.textChanged.connect(self._find_next)
        fb_layout.addWidget(self.find_input, 1)

        fb_layout.addWidget(QLabel("Replace:"))
        self.replace_input = QLineEdit()
        self.replace_input.setCursor(Qt.CursorShape.IBeamCursor)
        self.replace_input.setStyleSheet(f"background-color: {COLOR_STORM_CLOUD}; color: {COLOR_TEXT_MAIN}; padding: 4px; border: 1px solid {COLOR_PANEL_EDGE}; border-radius: 4px;")
        fb_layout.addWidget(self.replace_input, 1)

        btn_find_next = QPushButton("Find Next")
        btn_find_next.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_find_next.setStyleSheet(self._btn_style())
        btn_find_next.clicked.connect(self._find_next)
        fb_layout.addWidget(btn_find_next)

        btn_replace = QPushButton("Replace")
        btn_replace.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_replace.setStyleSheet(self._btn_style())
        btn_replace.clicked.connect(self._replace_match)
        fb_layout.addWidget(btn_replace)

        btn_replace_all = QPushButton("Replace All")
        btn_replace_all.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_replace_all.setStyleSheet(self._btn_style())
        btn_replace_all.clicked.connect(self._replace_all_matches)
        fb_layout.addWidget(btn_replace_all)

        btn_close_find = QPushButton("✕")
        btn_close_find.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close_find.setStyleSheet(self._btn_style())
        btn_close_find.clicked.connect(self.find_bar.hide)
        fb_layout.addWidget(btn_close_find)

        self.find_bar.hide()
        ws_layout.addWidget(self.find_bar)

        # Vertical Splitter: Tabs + Execution Console
        self.editor_splitter = QSplitter(Qt.Orientation.Vertical, self)
        self.editor_splitter.setStyleSheet(
            f"""
            QSplitter::handle {{
                background-color: {COLOR_PANEL_EDGE};
                height: 2px;
            }}
            """
        )

        # Tabs container
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        self.tab_widget.currentChanged.connect(self._on_tab_changed)
        self.tab_widget.setStyleSheet(
            f"""
            QTabWidget::pane {{
                border: 1px solid {COLOR_PANEL_EDGE};
                background-color: {COLOR_NIGHT_SKY};
                border-radius: 6px;
            }}
            QTabBar::tab {{
                background-color: {COLOR_STORM_CLOUD};
                color: {COLOR_TEXT_SECONDARY};
                border: 1px solid {COLOR_PANEL_EDGE};
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                padding: 6px 14px;
                margin-right: 2px;
                font-weight: bold;
                font-size: 11px;
            }}
            QTabBar::tab:selected {{
                background-color: {COLOR_RAISED_PANEL};
                color: {COLOR_LIGHTNING};
                border-color: {COLOR_LIGHTNING};
            }}
            """
        )
        self.editor_splitter.addWidget(self.tab_widget)

        # Output / Console Execution Panel
        self.output_panel = QFrame()
        self.output_panel.setStyleSheet(f"background-color: {COLOR_NIGHT_SKY}; border: 1px solid {COLOR_PANEL_EDGE}; border-radius: 6px;")
        op_layout = QVBoxLayout(self.output_panel)
        op_layout.setContentsMargins(6, 6, 6, 6)
        op_layout.setSpacing(4)

        op_header = QHBoxLayout()
        op_title = QLabel("💻 Execution Terminal Output:")
        op_title.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {COLOR_LIGHTNING};")
        op_header.addWidget(op_title)
        op_header.addStretch()

        btn_clear_out = QPushButton("Clear")
        btn_clear_out.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_clear_out.setStyleSheet(self._btn_style())
        btn_clear_out.clicked.connect(self._clear_output)
        op_header.addWidget(btn_clear_out)

        btn_close_out = QPushButton("✕")
        btn_close_out.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close_out.setStyleSheet(self._btn_style())
        btn_close_out.clicked.connect(self.output_panel.hide)
        op_header.addWidget(btn_close_out)

        op_layout.addLayout(op_header)

        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setCursor(Qt.CursorShape.IBeamCursor)
        self.output_text.setFont(QFont("Consolas", 10))
        self.output_text.setStyleSheet(f"background-color: #040810; color: #7EE787; border: none;")
        op_layout.addWidget(self.output_text)

        self.output_panel.hide()
        self.editor_splitter.addWidget(self.output_panel)

        ws_layout.addWidget(self.editor_splitter, 1)

        # Bottom Telemetry & Status Bar
        status_bar = QFrame()
        status_bar.setStyleSheet(f"background-color: {COLOR_STORM_CLOUD}; border: 1px solid {COLOR_PANEL_EDGE}; border-radius: 6px; padding: 3px 8px;")
        sb_layout = QHBoxLayout(status_bar)
        sb_layout.setContentsMargins(6, 2, 6, 2)
        sb_layout.setSpacing(12)

        self.telemetry_label = QLabel("Ln 1, Col 1 | 1 lines | 0 chars")
        self.telemetry_label.setStyleSheet(f"color: {COLOR_TEXT_MAIN}; font-size: 11px; font-weight: 500;")
        sb_layout.addWidget(self.telemetry_label)

        sb_layout.addStretch()

        # Language Selector
        sb_layout.addWidget(QLabel("Syntax:"))
        self.lang_combo = QComboBox()
        self.lang_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.lang_combo.addItems(["Python", "JSON", "Markdown", "HTML", "Shell", "Plain Text"])
        self.lang_combo.setStyleSheet(f"background-color: {COLOR_RAISED_PANEL}; color: {COLOR_TEXT_MAIN}; padding: 2px 6px; border: 1px solid {COLOR_PANEL_EDGE}; border-radius: 4px; font-size: 11px;")
        self.lang_combo.currentTextChanged.connect(self._on_language_changed)
        sb_layout.addWidget(self.lang_combo)

        # Zoom Controls
        btn_zoom_out = QPushButton("－")
        btn_zoom_out.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_zoom_out.setStyleSheet(self._btn_style())
        btn_zoom_out.setFixedSize(24, 22)
        btn_zoom_out.clicked.connect(self._zoom_out)
        sb_layout.addWidget(btn_zoom_out)

        self.zoom_label = QLabel("11pt")
        self.zoom_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 11px;")
        sb_layout.addWidget(self.zoom_label)

        btn_zoom_in = QPushButton("＋")
        btn_zoom_in.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_zoom_in.setStyleSheet(self._btn_style())
        btn_zoom_in.setFixedSize(24, 22)
        btn_zoom_in.clicked.connect(self._zoom_in)
        sb_layout.addWidget(btn_zoom_in)

        self.encoding_label = QLabel("UTF-8 | CRLF")
        self.encoding_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 11px;")
        sb_layout.addWidget(self.encoding_label)

        ws_layout.addWidget(status_bar)

        self.main_splitter.addWidget(workspace)
        self.main_splitter.setStretchFactor(0, 1)
        self.main_splitter.setStretchFactor(1, 3)

        main_layout.addWidget(self.main_splitter)

        # Initial Document Tab
        self._load_initial_document()

    def _btn_style(self) -> str:
        return f"""
            QPushButton {{
                background-color: {COLOR_RAISED_PANEL};
                color: {COLOR_TEXT_MAIN};
                border: 1px solid {COLOR_PANEL_EDGE};
                border-radius: 5px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                border-color: {COLOR_LIGHTNING};
                color: {COLOR_LIGHTNING};
            }}
        """

    # ----------------- COMPATIBILITY PROPERTIES -----------------

    @property
    def text_editor(self) -> QPlainTextEdit:
        doc = self.get_current_document()
        if doc:
            return doc.editor
        # Fallback dummy editor if none open
        return StormCodeEditor()

    @property
    def current_note_id(self) -> Optional[str]:
        if self._current_legacy_note_id:
            return self._current_legacy_note_id
        doc = self.get_current_document()
        if doc and doc.path:
            return doc.path.stem
        return sanitize_filename(self.title_input.text().strip().lower().replace(" ", "_"))

    # ----------------- SIDEBAR & NOTE LIST OPERATIONS -----------------

    def refresh_notes_list(self):
        """Scan user's notes directory and populate list widget."""
        self.notes_list.clear()
        if not self.notes_dir.exists():
            return

        for p in sorted(self.notes_dir.glob("*.json"), key=os.path.getmtime, reverse=True):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    title = data.get("title", p.stem)
                    item = QListWidgetItem(f"📝 {title}")
                    item.setData(Qt.ItemDataRole.UserRole, p)
                    self.notes_list.addItem(item)
            except Exception:
                pass

    def _filter_notes_list(self, query: str):
        query = query.lower()
        for i in range(self.notes_list.count()):
            item = self.notes_list.item(i)
            item.setHidden(query not in item.text().lower())

    def _on_note_item_clicked(self, item: QListWidgetItem):
        file_path = item.data(Qt.ItemDataRole.UserRole)
        if file_path and Path(file_path).exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    title = data.get("title", Path(file_path).stem)
                    body = data.get("body", "")
                    self._current_legacy_note_id = Path(file_path).stem
                    self.title_input.setText(title)

                    # Check if already open in a tab
                    for idx, tab in enumerate(self.tabs_data):
                        if tab.path == Path(file_path):
                            self.tab_widget.setCurrentIndex(idx)
                            return

                    # Open in new or current tab
                    self.add_document_tab(f"{title}.json", body, path=Path(file_path), language="json")
            except Exception as e:
                QMessageBox.critical(self, "Error Opening Note", f"Could not read note:\n{e}")

    def create_new_note(self):
        """Create a new blank note."""
        self._current_legacy_note_id = None
        self.title_input.setText("Untitled Note")
        self.add_document_tab("Untitled Note.txt", "", language="plain text")
        self.text_editor.setFocus()

    def save_current_note(self):
        """Save active content as JSON note format for backward compatibility."""
        title = self.title_input.text().strip() or "Untitled Note"
        note_id = self._current_legacy_note_id or sanitize_filename(title.lower().replace(" ", "_"))
        if not note_id:
            note_id = f"note_{int(time.time())}"

        self._current_legacy_note_id = note_id
        note_path = self.notes_dir / f"{note_id}.json"

        body = self.text_editor.toPlainText()
        data = {
            "id": note_id,
            "title": title,
            "body": body,
            "updated_at": datetime.now().isoformat(),
            "created_at": datetime.now().isoformat(),
        }

        with open(note_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        doc = self.get_current_document()
        if doc:
            doc.filename = f"{title}.json"
            doc.path = note_path
            doc.is_modified = False
            self._update_tab_title(doc)

        self.refresh_notes_list()

    def delete_current_note(self):
        """Delete currently selected or active note."""
        note_id = self.current_note_id
        if not note_id:
            return

        note_file = self.notes_dir / f"{note_id}.json"
        if note_file.exists():
            note_file.unlink()

        self._current_legacy_note_id = None
        self.refresh_notes_list()

        # Close corresponding tab
        for idx, doc in enumerate(self.tabs_data):
            if doc.path == note_file:
                self.tab_widget.removeTab(idx)
                self.tabs_data.pop(idx)
                break

        if not self.tabs_data:
            self.create_new_note()

    # ----------------- DOCUMENT & TAB MANAGEMENT -----------------

    def _load_initial_document(self):
        welcome_code = (
            '# ========================================================\n'
            '# ⚡ StormOS Code Studio & Notepad++ Editor\n'
            '# ========================================================\n'
            'import sys\n'
            'import time\n\n'
            'def main():\n'
            '    print("⚡ Welcome to StormOS Code Studio!")\n'
            '    print(f"Running on Python {sys.version.split()[0]}")\n'
            '    \n'
            '    for i in range(1, 4):\n'
            '        print(f"  • Storm Core Subsystem {i}: Operational")\n'
            '        time.sleep(0.05)\n'
            '        \n'
            '    print("⚡ System Ready for Code Creation!")\n\n'
            'if __name__ == "__main__":\n'
            '    main()\n'
        )
        self.add_document_tab("Welcome.py", welcome_code, language="python")

    def add_document_tab(self, filename: str, content: str = "", path: Optional[Path] = None, language: str = "python") -> DocumentTab:
        doc = DocumentTab(filename=filename, path=path, language=language)
        doc.editor.setPlainText(content)
        doc.editor.textChanged.connect(lambda: self._on_document_text_changed(doc))
        doc.editor.cursor_telemetry_changed.connect(self._update_telemetry)

        self.tabs_data.append(doc)
        idx = self.tab_widget.addTab(doc.editor, filename)
        self.tab_widget.setCurrentIndex(idx)
        return doc

    def get_current_document(self) -> Optional[DocumentTab]:
        idx = self.tab_widget.currentIndex()
        if 0 <= idx < len(self.tabs_data):
            return self.tabs_data[idx]
        return None

    def new_file(self):
        count = len(self.tabs_data) + 1
        self.add_document_tab(f"Untitled_{count}.py", language="python")

    def open_file_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Code or Note File",
            str(self.user_docs_dir),
            "Supported Files (*.py *.json *.md *.html *.xml *.js *.sh *.bat *.txt);;All Files (*.*)",
        )
        if file_path:
            p = Path(file_path)
            try:
                content = p.read_text(encoding="utf-8", errors="replace")
                ext = p.suffix.lower().lstrip(".")
                lang_map = {
                    "py": "python",
                    "json": "json",
                    "js": "json",
                    "md": "markdown",
                    "html": "html",
                    "xml": "html",
                    "sh": "shell",
                    "bat": "shell",
                }
                lang = lang_map.get(ext, "plain text")
                self.add_document_tab(p.name, content, path=p, language=lang)
            except Exception as e:
                QMessageBox.critical(self, "Error Opening File", f"Could not read file:\n{e}")

    def save_current_file(self) -> bool:
        doc = self.get_current_document()
        if not doc:
            return False

        # If it's a legacy json note, also save JSON
        if doc.path and doc.path.suffix.lower() == ".json" and str(doc.path).startswith(str(self.notes_dir)):
            self.save_current_note()
            return True

        if doc.path:
            try:
                doc.path.write_text(doc.editor.toPlainText(), encoding="utf-8")
                doc.is_modified = False
                self._update_tab_title(doc)
                return True
            except Exception as e:
                QMessageBox.critical(self, "Save Failed", f"Could not save file:\n{e}")
                return False
        else:
            return self.save_as_file_dialog()

    def save_as_file_dialog(self) -> bool:
        doc = self.get_current_document()
        if not doc:
            return False

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save File As",
            str(self.user_docs_dir / doc.filename),
            "Python File (*.py);;JSON File (*.json);;Markdown File (*.md);;HTML File (*.html);;Text File (*.txt);;All Files (*.*)",
        )
        if file_path:
            p = Path(file_path)
            try:
                p.write_text(doc.editor.toPlainText(), encoding="utf-8")
                doc.path = p
                doc.filename = p.name
                doc.is_modified = False
                self._update_tab_title(doc)
                return True
            except Exception as e:
                QMessageBox.critical(self, "Save Failed", f"Could not save file:\n{e}")
                return False
        return False

    def close_tab(self, index: int):
        if 0 <= index < len(self.tabs_data):
            doc = self.tabs_data[index]
            if doc.is_modified:
                reply = QMessageBox.question(
                    self,
                    "Unsaved Changes",
                    f"'{doc.filename}' has unsaved changes. Save before closing?",
                    QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                )
                if reply == QMessageBox.StandardButton.Save:
                    if not self.save_current_file():
                        return
                elif reply == QMessageBox.StandardButton.Cancel:
                    return

            self.tab_widget.removeTab(index)
            self.tabs_data.pop(index)

            if not self.tabs_data:
                self.new_file()

    def _on_tab_changed(self, index: int):
        doc = self.get_current_document()
        if doc:
            self.title_input.blockSignals(True)
            self.title_input.setText(doc.filename.replace(".json", "").replace(".py", ""))
            self.title_input.blockSignals(False)

            self.lang_combo.blockSignals(True)
            for i in range(self.lang_combo.count()):
                if self.lang_combo.itemText(i).lower() == doc.language.lower():
                    self.lang_combo.setCurrentIndex(i)
                    break
            self.lang_combo.blockSignals(False)

    def _on_title_input_changed(self, text: str):
        doc = self.get_current_document()
        if doc and not doc.path:
            doc.filename = f"{text.strip() or 'Untitled'}.py"
            self._update_tab_title(doc)

    def _on_document_text_changed(self, doc: DocumentTab):
        if not doc.is_modified:
            doc.is_modified = True
            self._update_tab_title(doc)

    def _update_tab_title(self, doc: DocumentTab):
        try:
            idx = self.tabs_data.index(doc)
            star = "*" if doc.is_modified else ""
            self.tab_widget.setTabText(idx, f"{doc.filename}{star}")
        except ValueError:
            pass

    def _on_language_changed(self, text: str):
        doc = self.get_current_document()
        if doc:
            doc.language = text.lower()
            doc.highlighter.set_language(text.lower())

    def _update_telemetry(self, line: int, col: int, total_lines: int, total_chars: int):
        self.telemetry_label.setText(f"Ln {line}, Col {col} | {total_lines} lines | {total_chars:,} chars")

    def _zoom_in(self):
        doc = self.get_current_document()
        if doc:
            f = doc.editor.font()
            size = min(28, f.pointSize() + 1)
            f.setPointSize(size)
            doc.editor.setFont(f)
            self.zoom_label.setText(f"{size}pt")

    def _zoom_out(self):
        doc = self.get_current_document()
        if doc:
            f = doc.editor.font()
            size = max(8, f.pointSize() - 1)
            f.setPointSize(size)
            doc.editor.setFont(f)
            self.zoom_label.setText(f"{size}pt")

    # ----------------- FIND & REPLACE -----------------

    def toggle_find_bar(self):
        if self.find_bar.isVisible():
            self.find_bar.hide()
        else:
            self.find_bar.show()
            self.find_input.setFocus()
            self.find_input.selectAll()

    def _find_next(self):
        query = self.find_input.text()
        if not query:
            return
        doc = self.get_current_document()
        if doc:
            found = doc.editor.find(query)
            if not found:
                # Wrap search from top
                doc.editor.moveCursor(QTextCursor.MoveOperation.Start)
                doc.editor.find(query)

    def _replace_match(self):
        query = self.find_input.text()
        replacement = self.replace_input.text()
        doc = self.get_current_document()
        if not doc or not query:
            return

        cursor = doc.editor.textCursor()
        if cursor.hasSelection() and cursor.selectedText() == query:
            cursor.insertText(replacement)
            self._find_next()

    def _replace_all_matches(self):
        query = self.find_input.text()
        replacement = self.replace_input.text()
        doc = self.get_current_document()
        if not doc or not query:
            return

        content = doc.editor.toPlainText()
        new_content = content.replace(query, replacement)
        count = content.count(query)
        doc.editor.setPlainText(new_content)
        QMessageBox.information(self, "Replace All", f"Replaced {count} occurrences of '{query}'.")

    # ----------------- TEMPLATES & CODE RUNNER -----------------

    def _on_template_selected(self, index: int):
        if index == 0:
            return

        templates = {
            1: (
                "python_script.py",
                '#!/usr/bin/env python3\n"""StormOS Application Script."""\n\n'
                'def compute():\n'
                '    data = [x**2 for x in range(10)]\n'
                '    print(f"Computed squares: {data}")\n\n'
                'if __name__ == "__main__":\n'
                '    compute()\n',
                "python",
            ),
            2: (
                "config.json",
                '{\n'
                '  "app_name": "StormOS Code Studio",\n'
                '  "version": "1.0.0",\n'
                '  "theme": "dark_storm",\n'
                '  "auto_save": true,\n'
                '  "tab_size": 4\n'
                '}\n',
                "json",
            ),
            3: (
                "notes.md",
                '# ⚡ StormOS Project Notes\n\n'
                '## Overview\n'
                '- Fast execution\n'
                '- Rich syntax highlighting\n'
                '- Sandboxed storage\n\n'
                '```python\n'
                'print("Hello StormOS")\n'
                '```\n',
                "markdown",
            ),
            4: (
                "index.html",
                '<!DOCTYPE html>\n'
                '<html lang="en">\n'
                '<head>\n'
                '  <meta charset="UTF-8">\n'
                '  <title>StormOS Web View</title>\n'
                '</head>\n'
                '<body>\n'
                '  <h1>⚡ StormOS Cyber Platform</h1>\n'
                '  <p>Interactive glass interface.</p>\n'
                '</body>\n'
                '</html>\n',
                "html",
            ),
        }

        if index in templates:
            fname, code, lang = templates[index]
            self.add_document_tab(fname, code, language=lang)
            self.template_combo.setCurrentIndex(0)

    def run_code_execution(self):
        """Execute current code in Python interpreter and stream to output console."""
        doc = self.get_current_document()
        if not doc:
            return

        code = doc.editor.toPlainText()
        self.output_panel.show()
        self.output_text.clear()
        self.output_text.append(f"⚡ [Executing {doc.filename} via Python 3.13]...\n")

        start_time = time.time()
        try:
            proc = subprocess.run(
                [sys.executable, "-c", code],
                capture_output=True,
                text=True,
                timeout=10,
            )
            duration = (time.time() - start_time) * 1000

            if proc.stdout:
                self.output_text.append(proc.stdout)
            if proc.stderr:
                self.output_text.append(f"⚠️ Errors/Traceback:\n{proc.stderr}")

            self.output_text.append(f"\n⚡ Finished with exit code {proc.returncode} in {duration:.1f}ms")
        except subprocess.TimeoutExpired:
            self.output_text.append("❌ Execution timed out (exceeded 10s safety limit).")
        except Exception as e:
            self.output_text.append(f"❌ Execution failed:\n{e}")

    def _clear_output(self):
        self.output_text.clear()
