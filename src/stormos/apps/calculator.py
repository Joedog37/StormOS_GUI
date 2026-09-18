"""Storm Power Calculator for StormOS.

A versatile mathematical workbench featuring natural expression parsing,
live previews, interactive calculation tape/history, multi-unit conversions,
programmer multi-base calculations, and financial utility helpers.
"""

import math
import re
from typing import List, Optional, Tuple
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QKeyEvent
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTabWidget,
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
from stormos.services.user_manager import UserProfile


# Safe math scope for evaluation
MATH_ENV = {
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "log": math.log10,
    "ln": math.log,
    "abs": abs,
    "round": round,
    "pi": math.pi,
    "e": math.e,
}


def evaluate_expression(expr: str) -> Tuple[bool, str]:
    """Safely evaluate a mathematical formula string."""
    cleaned = expr.strip()
    if not cleaned:
        return False, ""

    # Replace syntax shortcuts: ^ -> **, % -> / 100, × -> *, ÷ -> /
    sanitized = cleaned.replace("×", "*").replace("÷", "/").replace("^", "**")
    
    # Handle percentage: e.g. 100 + 15% -> 100 + (100 * 0.15) or x% -> (x / 100)
    sanitized = re.sub(r"(\d+(\.\d+)?)%", r"(\1/100)", sanitized)

    # Restrict allowed characters
    if not re.match(r"^[0-9\.\+\-\*\/\(\)\,\s\w\^]+$", sanitized):
        return False, "Invalid characters"

    try:
        # Evaluate with restricted globals and math functions
        result = eval(sanitized, {"__builtins__": {}}, MATH_ENV)
        if isinstance(result, float):
            if result.is_integer():
                return True, str(int(result))
            return True, f"{result:.8g}"
        return True, str(result)
    except Exception as e:
        return False, "Syntax Error"


class CalculatorApp(QWidget):
    """Versatile multi-mode Storm Power Calculator."""

    def __init__(self, current_user: Optional[UserProfile] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.current_user = current_user
        self.memory_val: float = 0.0
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.setStyleSheet(
            f"""
            QSplitter::handle {{
                background-color: {COLOR_PANEL_EDGE};
                width: 2px;
            }}
            """
        )

        # Left Tabs (Modes)
        tabs = QTabWidget()
        tabs.setStyleSheet(
            f"""
            QTabWidget::pane {{
                border: 1px solid {COLOR_PANEL_EDGE};
                background-color: {COLOR_STORM_CLOUD};
                border-radius: 8px;
            }}
            QTabBar::tab {{
                background-color: {COLOR_RAISED_PANEL};
                color: {COLOR_TEXT_SECONDARY};
                border: 1px solid {COLOR_PANEL_EDGE};
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                padding: 8px 14px;
                margin-right: 2px;
                font-weight: bold;
                font-size: 11px;
            }}
            QTabBar::tab:selected {{
                background-color: {COLOR_STORM_CLOUD};
                color: {COLOR_LIGHTNING};
                border-color: {COLOR_LIGHTNING};
            }}
            """
        )

        # Tab 1: Standard & Scientific
        tabs.addTab(self._build_calc_tab(), "⚡ Power Math")
        # Tab 2: Unit & Data Storage
        tabs.addTab(self._build_units_tab(), "📦 Unit Converters")
        # Tab 3: Programmer Base
        tabs.addTab(self._build_programmer_tab(), "💻 Programmer")
        # Tab 4: Quick Finance
        tabs.addTab(self._build_finance_tab(), "💰 Quick Finance")

        splitter.addWidget(tabs)

        # Right Panel: Interactive Calculation Tape
        tape_panel = self._build_history_tape()
        splitter.addWidget(tape_panel)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        main_layout.addWidget(splitter)

    def _build_calc_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # Display Area
        display_frame = QFrame()
        display_frame.setStyleSheet(
            f"""
            QFrame {{
                background-color: {COLOR_RAISED_PANEL};
                border: 1px solid {COLOR_PANEL_EDGE};
                border-radius: 8px;
                padding: 8px;
            }}
            """
        )
        display_layout = QVBoxLayout(display_frame)
        display_layout.setContentsMargins(8, 6, 8, 6)
        display_layout.setSpacing(4)

        # Main Expression Input
        self.expr_input = QLineEdit()
        self.expr_input.setPlaceholderText("Enter formula e.g. (145 * 1.15) + sqrt(144)")
        self.expr_input.setStyleSheet(
            f"""
            QLineEdit {{
                background: transparent;
                border: none;
                color: {COLOR_TEXT_MAIN};
                font-size: 18px;
                font-weight: bold;
            }}
            """
        )
        self.expr_input.textChanged.connect(self._on_expr_changed)
        self.expr_input.returnPressed.connect(self._calculate_final)
        display_layout.addWidget(self.expr_input)

        # Live Preview Label
        self.preview_label = QLabel("= 0")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.preview_label.setStyleSheet(
            f"font-size: 14px; font-weight: 600; color: {COLOR_LIGHTNING}; background: transparent; border: none;"
        )
        display_layout.addWidget(self.preview_label)

        layout.addWidget(display_frame)

        # Keypad Grid
        keypad = QGridLayout()
        keypad.setSpacing(6)

        buttons = [
            # Row 0 (Functions / Memory)
            ("MC", self._mem_clear, "mem"),
            ("MR", self._mem_recall, "mem"),
            ("M+", self._mem_add, "mem"),
            ("C", self._clear_all, "action"),
            ("CE", self._backspace, "action"),
            # Row 1
            ("sin", lambda: self._insert_token("sin("), "sci"),
            ("cos", lambda: self._insert_token("cos("), "sci"),
            ("tan", lambda: self._insert_token("tan("), "sci"),
            ("π", lambda: self._insert_token("pi"), "sci"),
            ("e", lambda: self._insert_token("e"), "sci"),
            # Row 2
            ("sqrt", lambda: self._insert_token("sqrt("), "sci"),
            ("(", lambda: self._insert_token("("), "op"),
            (")", lambda: self._insert_token(")"), "op"),
            ("^", lambda: self._insert_token("^"), "op"),
            ("÷", lambda: self._insert_token(" ÷ "), "op"),
            # Row 3
            ("ln", lambda: self._insert_token("ln("), "sci"),
            ("7", lambda: self._insert_token("7"), "num"),
            ("8", lambda: self._insert_token("8"), "num"),
            ("9", lambda: self._insert_token("9"), "num"),
            ("×", lambda: self._insert_token(" × "), "op"),
            # Row 4
            ("log", lambda: self._insert_token("log("), "sci"),
            ("4", lambda: self._insert_token("4"), "num"),
            ("5", lambda: self._insert_token("5"), "num"),
            ("6", lambda: self._insert_token("6"), "num"),
            ("-", lambda: self._insert_token(" - "), "op"),
            # Row 5
            ("%", lambda: self._insert_token("%"), "op"),
            ("1", lambda: self._insert_token("1"), "num"),
            ("2", lambda: self._insert_token("2"), "num"),
            ("3", lambda: self._insert_token("3"), "num"),
            ("+", lambda: self._insert_token(" + "), "op"),
            # Row 6
            ("abs", lambda: self._insert_token("abs("), "sci"),
            ("0", lambda: self._insert_token("0"), "num"),
            (".", lambda: self._insert_token("."), "num"),
            ("ANS", self._use_last_answer, "action"),
            ("=", self._calculate_final, "equals"),
        ]

        row = 0
        col = 0
        for text, handler, style_type in buttons:
            btn = QPushButton(text)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(36)
            btn.setStyleSheet(self._get_btn_style(style_type))
            btn.clicked.connect(handler)
            keypad.addWidget(btn, row, col)
            col += 1
            if col == 5:
                col = 0
                row += 1

        layout.addLayout(keypad)
        return widget

    def _get_btn_style(self, style_type: str) -> str:
        if style_type == "equals":
            return f"""
                QPushButton {{
                    background-color: {COLOR_LIGHTNING};
                    color: {COLOR_NIGHT_SKY};
                    font-weight: 800;
                    font-size: 15px;
                    border: none;
                    border-radius: 6px;
                }}
                QPushButton:hover {{
                    background-color: #A9EBFF;
                }}
            """
        elif style_type == "op":
            return f"""
                QPushButton {{
                    background-color: {COLOR_RAISED_PANEL};
                    color: {COLOR_LIGHTNING};
                    font-weight: bold;
                    font-size: 14px;
                    border: 1px solid {COLOR_PANEL_EDGE};
                    border-radius: 6px;
                }}
                QPushButton:hover {{
                    background-color: rgba(56, 201, 255, 0.2);
                    border-color: {COLOR_LIGHTNING};
                }}
            """
        elif style_type == "action":
            return f"""
                QPushButton {{
                    background-color: rgba(255, 92, 119, 0.15);
                    color: {COLOR_ERROR};
                    font-weight: bold;
                    font-size: 12px;
                    border: 1px solid rgba(255, 92, 119, 0.3);
                    border-radius: 6px;
                }}
                QPushButton:hover {{
                    background-color: {COLOR_ERROR};
                    color: {COLOR_NIGHT_SKY};
                }}
            """
        elif style_type == "sci":
            return f"""
                QPushButton {{
                    background-color: rgba(16, 26, 49, 0.8);
                    color: {COLOR_MIST_BLUE};
                    font-weight: 600;
                    font-size: 11px;
                    border: 1px solid {COLOR_PANEL_EDGE};
                    border-radius: 6px;
                }}
                QPushButton:hover {{
                    background-color: {COLOR_RAISED_PANEL};
                    color: {COLOR_TEXT_MAIN};
                }}
            """
        else:  # num / normal
            return f"""
                QPushButton {{
                    background-color: {COLOR_RAISED_PANEL};
                    color: {COLOR_TEXT_MAIN};
                    font-weight: bold;
                    font-size: 13px;
                    border: 1px solid {COLOR_PANEL_EDGE};
                    border-radius: 6px;
                }}
                QPushButton:hover {{
                    background-color: rgba(56, 201, 255, 0.12);
                    border-color: {COLOR_LIGHTNING};
                    color: {COLOR_LIGHTNING};
                }}
            """

    def _build_units_tab(self) -> QWidget:
        """Unit & Data Storage converter hub."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        # Data Storage Converter
        data_frame = QFrame()
        data_frame.setStyleSheet(
            f"background-color: {COLOR_RAISED_PANEL}; border: 1px solid {COLOR_PANEL_EDGE}; border-radius: 8px; padding: 12px;"
        )
        d_layout = QVBoxLayout(data_frame)
        d_layout.setSpacing(8)

        lbl = QLabel("📦 Data Storage Converter")
        lbl.setStyleSheet(f"font-weight: bold; color: {COLOR_LIGHTNING}; font-size: 13px; border: none;")
        d_layout.addWidget(lbl)

        row = QHBoxLayout()
        self.data_input = QDoubleSpinBox()
        self.data_input.setRange(0, 1000000000)
        self.data_input.setValue(1024)
        self.data_input.setStyleSheet(f"background-color: {COLOR_STORM_CLOUD}; color: {COLOR_TEXT_MAIN}; padding: 6px; border: 1px solid {COLOR_PANEL_EDGE}; border-radius: 6px;")
        row.addWidget(self.data_input, 1)

        self.data_unit = QComboBox()
        self.data_unit.addItems(["Bytes (B)", "Kilobytes (KB)", "Megabytes (MB)", "Gigabytes (GB)", "Terabytes (TB)", "Petabytes (PB)"])
        self.data_unit.setCurrentIndex(2)  # MB
        self.data_unit.setStyleSheet(f"background-color: {COLOR_STORM_CLOUD}; color: {COLOR_TEXT_MAIN}; padding: 6px; border: 1px solid {COLOR_PANEL_EDGE}; border-radius: 6px;")
        row.addWidget(self.data_unit, 1)
        d_layout.addLayout(row)

        self.data_result_lbl = QLabel()
        self.data_result_lbl.setStyleSheet(f"color: {COLOR_TEXT_MAIN}; font-size: 12px; border: none;")
        d_layout.addWidget(self.data_result_lbl)

        self.data_input.valueChanged.connect(self._update_data_conversion)
        self.data_unit.currentIndexChanged.connect(self._update_data_conversion)
        self._update_data_conversion()

        layout.addWidget(data_frame)

        # Length Converter
        len_frame = QFrame()
        len_frame.setStyleSheet(
            f"background-color: {COLOR_RAISED_PANEL}; border: 1px solid {COLOR_PANEL_EDGE}; border-radius: 8px; padding: 12px;"
        )
        l_layout = QVBoxLayout(len_frame)
        l_layout.setSpacing(8)

        l_lbl = QLabel("📏 Length & Distance")
        l_lbl.setStyleSheet(f"font-weight: bold; color: {COLOR_LIGHTNING}; font-size: 13px; border: none;")
        l_layout.addWidget(l_lbl)

        l_row = QHBoxLayout()
        self.len_input = QDoubleSpinBox()
        self.len_input.setRange(0, 1000000000)
        self.len_input.setValue(100)
        self.len_input.setStyleSheet(f"background-color: {COLOR_STORM_CLOUD}; color: {COLOR_TEXT_MAIN}; padding: 6px; border: 1px solid {COLOR_PANEL_EDGE}; border-radius: 6px;")
        l_row.addWidget(self.len_input, 1)

        self.len_unit = QComboBox()
        self.len_unit.addItems(["Meters (m)", "Kilometers (km)", "Centimeters (cm)", "Inches (in)", "Feet (ft)", "Miles (mi)"])
        self.len_unit.setStyleSheet(f"background-color: {COLOR_STORM_CLOUD}; color: {COLOR_TEXT_MAIN}; padding: 6px; border: 1px solid {COLOR_PANEL_EDGE}; border-radius: 6px;")
        l_row.addWidget(self.len_unit, 1)
        l_layout.addLayout(l_row)

        self.len_result_lbl = QLabel()
        self.len_result_lbl.setStyleSheet(f"color: {COLOR_TEXT_MAIN}; font-size: 12px; border: none;")
        l_layout.addWidget(self.len_result_lbl)

        self.len_input.valueChanged.connect(self._update_length_conversion)
        self.len_unit.currentIndexChanged.connect(self._update_length_conversion)
        self._update_length_conversion()

        layout.addWidget(len_frame)
        layout.addStretch()
        return widget

    def _update_data_conversion(self):
        val = self.data_input.value()
        idx = self.data_unit.currentIndex()
        # Scale to bytes
        powers = [1, 1024, 1024**2, 1024**3, 1024**4, 1024**5]
        bytes_val = val * powers[idx]

        kb = bytes_val / 1024
        mb = bytes_val / (1024**2)
        gb = bytes_val / (1024**3)
        tb = bytes_val / (1024**4)

        text = f"• {bytes_val:,.0f} B\n• {kb:,.2f} KB\n• {mb:,.4f} MB\n• {gb:,.6f} GB\n• {tb:,.8f} TB"
        self.data_result_lbl.setText(text)

    def _update_length_conversion(self):
        val = self.len_input.value()
        idx = self.len_unit.currentIndex()
        # Scale to meters
        to_m = [1.0, 1000.0, 0.01, 0.0254, 0.3048, 1609.344]
        meters = val * to_m[idx]

        km = meters / 1000.0
        cm = meters * 100.0
        ft = meters / 0.3048
        inches = meters / 0.0254
        mi = meters / 1609.344

        text = f"• {meters:,.4g} m | {cm:,.4g} cm | {km:,.4g} km\n• {ft:,.4g} ft | {inches:,.4g} in | {mi:,.4g} mi"
        self.len_result_lbl.setText(text)

    def _build_programmer_tab(self) -> QWidget:
        """Programmer Multi-Base & Bitwise tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        input_box = QLineEdit()
        input_box.setPlaceholderText("Enter integer (e.g. 255 or 0xFF)...")
        input_box.setStyleSheet(
            f"background-color: {COLOR_RAISED_PANEL}; color: {COLOR_TEXT_MAIN}; border: 1px solid {COLOR_PANEL_EDGE}; border-radius: 6px; padding: 10px; font-size: 14px;"
        )
        layout.addWidget(input_box)

        res_frame = QFrame()
        res_frame.setStyleSheet(
            f"background-color: {COLOR_RAISED_PANEL}; border: 1px solid {COLOR_PANEL_EDGE}; border-radius: 8px; padding: 12px;"
        )
        r_layout = QVBoxLayout(res_frame)
        r_layout.setSpacing(8)

        self.dec_lbl = QLabel("DEC: 0")
        self.hex_lbl = QLabel("HEX: 0x0")
        self.bin_lbl = QLabel("BIN: 0b0000")
        self.oct_lbl = QLabel("OCT: 0o0")

        for lbl in (self.dec_lbl, self.hex_lbl, self.bin_lbl, self.oct_lbl):
            lbl.setStyleSheet(f"font-family: monospace; font-size: 13px; color: {COLOR_LIGHTNING}; background: transparent; border: none;")
            r_layout.addWidget(lbl)

        layout.addWidget(res_frame)

        def _on_prog_input(txt: str):
            txt = txt.strip()
            if not txt:
                self.dec_lbl.setText("DEC: 0")
                self.hex_lbl.setText("HEX: 0x0")
                self.bin_lbl.setText("BIN: 0b0000")
                self.oct_lbl.setText("OCT: 0o0")
                return
            try:
                if txt.startswith("0x") or txt.startswith("0X"):
                    val = int(txt, 16)
                elif txt.startswith("0b") or txt.startswith("0B"):
                    val = int(txt, 2)
                elif txt.startswith("0o") or txt.startswith("0O"):
                    val = int(txt, 8)
                else:
                    val = int(txt)

                self.dec_lbl.setText(f"DEC: {val:,}")
                self.hex_lbl.setText(f"HEX: 0x{val:X}")
                bin_str = f"{val:b}"
                # Group into 4 bits
                grouped = " ".join([bin_str[max(i-4, 0):i] for i in range(len(bin_str), 0, -4)][::-1])
                self.bin_lbl.setText(f"BIN: 0b{grouped}")
                self.oct_lbl.setText(f"OCT: 0o{val:o}")
            except Exception:
                self.dec_lbl.setText("DEC: <Invalid Integer>")

        input_box.textChanged.connect(_on_prog_input)
        layout.addStretch()
        return widget

    def _build_finance_tab(self) -> QWidget:
        """Quick finance & tip calculation hub."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Tip & Bill Splitter
        frame = QFrame()
        frame.setStyleSheet(f"background-color: {COLOR_RAISED_PANEL}; border: 1px solid {COLOR_PANEL_EDGE}; border-radius: 8px; padding: 12px;")
        f_layout = QVBoxLayout(frame)
        f_layout.setSpacing(8)

        lbl = QLabel("💵 Tip & Bill Splitter")
        lbl.setStyleSheet(f"font-weight: bold; color: {COLOR_LIGHTNING}; font-size: 13px; border: none;")
        f_layout.addWidget(lbl)

        row = QHBoxLayout()
        bill_spin = QDoubleSpinBox()
        bill_spin.setRange(0, 100000)
        bill_spin.setValue(100.0)
        bill_spin.setPrefix("$ ")
        bill_spin.setStyleSheet(f"background-color: {COLOR_STORM_CLOUD}; color: {COLOR_TEXT_MAIN}; padding: 6px; border: 1px solid {COLOR_PANEL_EDGE}; border-radius: 6px;")
        row.addWidget(QLabel("Bill:"), 0)
        row.addWidget(bill_spin, 1)

        tip_spin = QDoubleSpinBox()
        tip_spin.setRange(0, 100)
        tip_spin.setValue(15.0)
        tip_spin.setSuffix(" %")
        tip_spin.setStyleSheet(f"background-color: {COLOR_STORM_CLOUD}; color: {COLOR_TEXT_MAIN}; padding: 6px; border: 1px solid {COLOR_PANEL_EDGE}; border-radius: 6px;")
        row.addWidget(QLabel("Tip:"), 0)
        row.addWidget(tip_spin, 1)

        split_spin = QDoubleSpinBox()
        split_spin.setRange(1, 100)
        split_spin.setValue(1)
        split_spin.setDecimals(0)
        split_spin.setPrefix("👥 ")
        split_spin.setStyleSheet(f"background-color: {COLOR_STORM_CLOUD}; color: {COLOR_TEXT_MAIN}; padding: 6px; border: 1px solid {COLOR_PANEL_EDGE}; border-radius: 6px;")
        row.addWidget(QLabel("People:"), 0)
        row.addWidget(split_spin, 1)
        f_layout.addLayout(row)

        fin_res = QLabel()
        fin_res.setStyleSheet(f"color: {COLOR_TEXT_MAIN}; font-size: 13px; font-weight: bold; border: none;")
        f_layout.addWidget(fin_res)

        def _update_finance():
            bill = bill_spin.value()
            tip_pct = tip_spin.value()
            people = split_spin.value()

            tip_amt = bill * (tip_pct / 100.0)
            total = bill + tip_amt
            per_person = total / people if people else total

            fin_res.setText(
                f"• Tip Amount: ${tip_amt:.2f}\n"
                f"• Total Bill: ${total:.2f}\n"
                f"• Per Person: ${per_person:.2f}"
            )

        bill_spin.valueChanged.connect(_update_finance)
        tip_spin.valueChanged.connect(_update_finance)
        split_spin.valueChanged.connect(_update_finance)
        _update_finance()

        layout.addWidget(frame)
        layout.addStretch()
        return widget

    def _build_history_tape(self) -> QWidget:
        panel = QFrame()
        panel.setStyleSheet(
            f"""
            QFrame {{
                background-color: {COLOR_STORM_CLOUD};
                border: 1px solid {COLOR_PANEL_EDGE};
                border-radius: 8px;
            }}
            """
        )
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        header = QHBoxLayout()
        lbl = QLabel("📜 Calculation Tape")
        lbl.setStyleSheet(f"font-weight: bold; color: {COLOR_LIGHTNING}; font-size: 12px; background: transparent; border: none;")
        header.addWidget(lbl)

        btn_clear_tape = QPushButton("Clear")
        btn_clear_tape.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {COLOR_RAISED_PANEL};
                color: {COLOR_TEXT_SECONDARY};
                border: 1px solid {COLOR_PANEL_EDGE};
                border-radius: 4px;
                padding: 2px 6px;
                font-size: 10px;
            }}
            QPushButton:hover {{
                color: {COLOR_ERROR};
                border-color: {COLOR_ERROR};
            }}
            """
        )
        btn_clear_tape.clicked.connect(self._clear_tape)
        header.addWidget(btn_clear_tape)
        layout.addLayout(header)

        self.tape_list = QListWidget()
        self.tape_list.setStyleSheet(
            f"""
            QListWidget {{
                background: transparent;
                border: none;
                color: {COLOR_TEXT_MAIN};
                font-size: 11px;
            }}
            QListWidget::item {{
                background-color: {COLOR_RAISED_PANEL};
                border: 1px solid {COLOR_PANEL_EDGE};
                border-radius: 6px;
                padding: 6px;
                margin-bottom: 4px;
            }}
            QListWidget::item:hover {{
                border-color: {COLOR_LIGHTNING};
                color: {COLOR_LIGHTNING};
            }}
            """
        )
        self.tape_list.itemClicked.connect(self._on_tape_item_clicked)
        layout.addWidget(self.tape_list)

        hint = QLabel("💡 Click history item to reuse result")
        hint.setStyleSheet(f"font-size: 10px; color: {COLOR_TEXT_SECONDARY}; background: transparent; border: none;")
        layout.addWidget(hint)

        return panel

    def _insert_token(self, token: str):
        self.expr_input.insert(token)
        self.expr_input.setFocus()

    def _clear_all(self):
        self.expr_input.clear()
        self.preview_label.setText("= 0")

    def _backspace(self):
        txt = self.expr_input.text()
        if txt:
            self.expr_input.setText(txt[:-1])

    def _on_expr_changed(self, text: str):
        valid, res = evaluate_expression(text)
        if valid and res:
            self.preview_label.setText(f"= {res}")
            self.preview_label.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {COLOR_LIGHTNING};")
        elif not text.strip():
            self.preview_label.setText("= 0")
        else:
            self.preview_label.setText("...")

    def _calculate_final(self):
        expr = self.expr_input.text().strip()
        if not expr:
            return
        valid, res = evaluate_expression(expr)
        if valid:
            self._add_to_tape(expr, res)
            self.expr_input.setText(res)
            self.preview_label.setText(f"= {res}")
            self.last_ans = res
        else:
            self.preview_label.setText(f"Error: {res}")
            self.preview_label.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {COLOR_ERROR};")

    def _add_to_tape(self, expr: str, res: str):
        item = QListWidgetItem(f"{expr}\n= {res}")
        item.setData(Qt.ItemDataRole.UserRole, res)
        self.tape_list.insertItem(0, item)

    def _on_tape_item_clicked(self, item: QListWidgetItem):
        res = item.data(Qt.ItemDataRole.UserRole)
        if res:
            self.expr_input.setText(str(res))
            self.expr_input.setFocus()

    def _clear_tape(self):
        self.tape_list.clear()

    def _use_last_answer(self):
        if hasattr(self, "last_ans"):
            self._insert_token(self.last_ans)

    def _mem_clear(self):
        self.memory_val = 0.0

    def _mem_recall(self):
        self._insert_token(str(self.memory_val))

    def _mem_add(self):
        valid, res = evaluate_expression(self.expr_input.text())
        if valid:
            try:
                self.memory_val += float(res)
            except Exception:
                pass
