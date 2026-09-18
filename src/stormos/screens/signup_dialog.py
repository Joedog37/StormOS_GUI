"""Sign Up / Account Registration Dialog for StormOS.

Provides a frosted storm-glass interface for creating a new secure user profile
with PBKDF2-HMAC-SHA256 password hashing.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from stormos.core.constants import (
    COLOR_ERROR,
    COLOR_LIGHTNING,
    COLOR_LIGHTNING_GLOW,
    COLOR_NIGHT_SKY,
    COLOR_PANEL_EDGE,
    COLOR_RAISED_PANEL,
    COLOR_STORM_CLOUD,
    COLOR_TEXT_MAIN,
    COLOR_TEXT_SECONDARY,
)
from stormos.core.security import validate_username
from stormos.services.user_manager import UserManager, UserProfile


class SignUpDialog(QDialog):
    """Frosted storm-glass dialog for user registration."""

    user_created = Signal(object)  # Emits newly created UserProfile

    def __init__(self, user_manager: UserManager, parent: QWidget | None = None):
        super().__init__(parent)
        self.user_manager = user_manager
        self.created_profile: UserProfile | None = None

        self.setWindowTitle("Create StormOS Account")
        self.setModal(True)
        self.setFixedWidth(400)
        self.setStyleSheet(
            f"""
            QDialog {{
                background-color: {COLOR_RAISED_PANEL};
                color: {COLOR_TEXT_MAIN};
                border: 1px solid {COLOR_PANEL_EDGE};
                border-radius: 14px;
            }}
            """
        )

        self._setup_ui()

    def _setup_ui(self):
        """Construct the registration form UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(14)

        # Header Title
        title = QLabel("Create Account")
        title.setStyleSheet(
            f"""
            font-size: 20px;
            font-weight: 700;
            color: {COLOR_TEXT_MAIN};
            letter-spacing: 0.5px;
            """
        )
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Set up a new secure local profile on StormOS")
        subtitle.setStyleSheet(f"font-size: 12px; color: {COLOR_TEXT_SECONDARY};")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        # Username Input
        u_label = QLabel("Username")
        u_label.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {COLOR_TEXT_SECONDARY};")
        layout.addWidget(u_label)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("e.g. pilot_01 (letters, numbers, _, -)")
        self._apply_input_style(self.username_input)
        layout.addWidget(self.username_input)

        # Display Name Input
        d_label = QLabel("Display Name (Optional)")
        d_label.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {COLOR_TEXT_SECONDARY};")
        layout.addWidget(d_label)

        self.display_name_input = QLineEdit()
        self.display_name_input.setPlaceholderText("e.g. Storm Commander")
        self._apply_input_style(self.display_name_input)
        layout.addWidget(self.display_name_input)

        # Password Input
        p_label = QLabel("Password")
        p_label.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {COLOR_TEXT_SECONDARY};")
        layout.addWidget(p_label)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Enter password...")
        self._apply_input_style(self.password_input)
        layout.addWidget(self.password_input)

        # Confirm Password Input
        cp_label = QLabel("Confirm Password")
        cp_label.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {COLOR_TEXT_SECONDARY};")
        layout.addWidget(cp_label)

        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_password_input.setPlaceholderText("Confirm password...")
        self._apply_input_style(self.confirm_password_input)
        self.confirm_password_input.returnPressed.connect(self._handle_signup)
        layout.addWidget(self.confirm_password_input)

        # Status / Error Label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet(f"font-size: 12px; color: {COLOR_ERROR}; min-height: 16px;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: transparent;
                color: {COLOR_TEXT_SECONDARY};
                border: 1px solid {COLOR_PANEL_EDGE};
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {COLOR_STORM_CLOUD};
                color: {COLOR_TEXT_MAIN};
            }}
            """
        )
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        self.create_btn = QPushButton("Create Account")
        self.create_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {COLOR_LIGHTNING};
                color: {COLOR_NIGHT_SKY};
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background-color: {COLOR_LIGHTNING_GLOW};
            }}
            """
        )
        self.create_btn.clicked.connect(self._handle_signup)
        btn_layout.addWidget(self.create_btn)

        layout.addLayout(btn_layout)

    def _apply_input_style(self, widget: QLineEdit):
        """Apply uniform storm-glass styling to input field."""
        widget.setStyleSheet(
            f"""
            QLineEdit {{
                background-color: {COLOR_STORM_CLOUD};
                color: {COLOR_TEXT_MAIN};
                border: 1px solid {COLOR_PANEL_EDGE};
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border: 1px solid {COLOR_LIGHTNING};
                background-color: rgba(16, 26, 49, 0.95);
            }}
            """
        )

    def _handle_signup(self):
        """Validate input and register new user profile."""
        username = self.username_input.text().strip()
        display_name = self.display_name_input.text().strip() or None
        password = self.password_input.text()
        confirm_password = self.confirm_password_input.text()

        if not username:
            self._set_error("Username cannot be empty")
            self.username_input.setFocus()
            return

        if not validate_username(username):
            self._set_error("Username must be 3-32 characters (letters, numbers, _, -)")
            self.username_input.setFocus()
            return

        if self.user_manager.user_exists(username):
            self._set_error(f"Username '{username}' already exists")
            self.username_input.selectAll()
            self.username_input.setFocus()
            return

        if not password:
            self._set_error("Password cannot be empty")
            self.password_input.setFocus()
            return

        if len(password) < 4:
            self._set_error("Password should be at least 4 characters")
            self.password_input.setFocus()
            return

        if password != confirm_password:
            self._set_error("Passwords do not match")
            self.confirm_password_input.selectAll()
            self.confirm_password_input.setFocus()
            return

        profile = self.user_manager.create_user(
            username=username,
            password=password,
            display_name=display_name,
        )

        if profile:
            self.created_profile = profile
            self.user_created.emit(profile)
            self.accept()
        else:
            self._set_error("Failed to create account. Please try again.")

    def _set_error(self, message: str):
        """Display error message."""
        self.status_label.setText(message)
