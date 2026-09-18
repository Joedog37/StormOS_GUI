"""Theme styling and stylesheet definitions for StormOS.

Implements the dark thunderstorm, storm-glass, and electric cyan design brief from DESIGN.md.
"""

from PySide6.QtGui import QFont, QColor
from stormos.core.constants import (
    COLOR_NIGHT_SKY,
    COLOR_STORM_CLOUD,
    COLOR_RAISED_PANEL,
    COLOR_PANEL_EDGE,
    COLOR_LIGHTNING,
    COLOR_LIGHTNING_GLOW,
    COLOR_TEXT_MAIN,
    COLOR_TEXT_SECONDARY,
    FONT_FAMILY,
)

def get_base_stylesheet() -> str:
    """Return the global QSS stylesheet for StormOS."""
    return f"""
    QWidget {{
        background-color: {COLOR_NIGHT_SKY};
        color: {COLOR_TEXT_MAIN};
        font-family: {FONT_FAMILY};
        font-size: 14px;
        selection-background-color: {COLOR_LIGHTNING};
        selection-color: {COLOR_NIGHT_SKY};
    }}

    /* Storm-glass card styling */
    QFrame.glass-panel {{
        background-color: {COLOR_RAISED_PANEL};
        border: 1px solid {COLOR_PANEL_EDGE};
        border-radius: 12px;
    }}

    /* Buttons */
    QPushButton {{
        background-color: {COLOR_STORM_CLOUD};
        color: {COLOR_TEXT_MAIN};
        border: 1px solid {COLOR_PANEL_EDGE};
        border-radius: 8px;
        padding: 8px 16px;
        font-weight: 500;
    }}

    QPushButton:hover {{
        border: 1px solid {COLOR_LIGHTNING};
        background-color: {COLOR_RAISED_PANEL};
    }}

    QPushButton:pressed {{
        background-color: {COLOR_LIGHTNING};
        color: {COLOR_NIGHT_SKY};
    }}

    /* Labels */
    QLabel {{
        background-color: transparent;
    }}

    QLabel.title {{
        font-size: 24px;
        font-weight: bold;
        color: {COLOR_TEXT_MAIN};
    }}

    QLabel.subtitle {{
        font-size: 14px;
        color: {COLOR_TEXT_SECONDARY};
    }}
    """
