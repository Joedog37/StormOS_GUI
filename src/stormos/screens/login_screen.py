"""Login Screen for StormOS.

Presents a storm-cloud backdrop with a translucent storm-glass login card,
secure credential verification, user account selection, and quick test login.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from stormos.core.constants import (
    APP_NAME,
    COLOR_ERROR,
    COLOR_LIGHTNING,
    COLOR_LIGHTNING_GLOW,
    COLOR_NIGHT_SKY,
    COLOR_PANEL_EDGE,
    COLOR_RAISED_PANEL,
    COLOR_STORM_CLOUD,
    COLOR_TEXT_MAIN,
    COLOR_TEXT_SECONDARY,
    COLOR_WARNING,
)
from stormos.core.paths import get_asset_path
from stormos.screens.signup_dialog import SignUpDialog
from stormos.services.user_manager import UserManager, UserProfile


class LoginScreen(QWidget):
    """Translucent glass login interface for StormOS."""

    login_successful = Signal(object)  # Emits UserProfile
    exit_requested = Signal()

    def __init__(self, user_manager: UserManager | None = None, parent: QWidget | None = None):
        super().__init__(parent)
        self.user_manager = user_manager or UserManager()
        self.user_manager.ensure_default_account()

        self._bg_pixmap: QPixmap | None = None
        self._load_background()
        self._setup_ui()
        self.refresh_users()

    def _load_background(self):
        """Load the wallpaper asset for the login backdrop."""
        wp_path = get_asset_path("wallpaper.png")
        if wp_path.exists():
            pix = QPixmap(str(wp_path))
            if not pix.isNull():
                self._bg_pixmap = pix

    def paintEvent(self, event):
        """Paint background wallpaper with dark storm-glass overlay."""
        painter = QPainter(self)
        if self._bg_pixmap and not self._bg_pixmap.isNull():
            scaled = self._bg_pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            # Center the scaled wallpaper
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)
            # Dark atmospheric overlay
            painter.fillRect(self.rect(), QColor(7, 11, 22, 190))
        else:
            painter.fillRect(self.rect(), QColor(COLOR_NIGHT_SKY))

    def _setup_ui(self):
        """Construct the login card layout."""
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Central Glass Card
        self.card = QFrame()
        self.card.setFixedWidth(380)
        self.card.setStyleSheet(
            f"""
            QFrame {{
                background-color: rgba(23, 35, 61, 0.92);
                border: 1px solid {COLOR_PANEL_EDGE};
                border-radius: 14px;
                padding: 16px;
            }}
            """
        )

        card_layout = QVBoxLayout(self.card)
        card_layout.setSpacing(10)
        card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Avatar / Crest Icon
        logo_path = get_asset_path("stormos_logo.png")
        if logo_path.exists():
            avatar_label = QLabel()
            pix = QPixmap(str(logo_path))
            if not pix.isNull():
                avatar_label.setPixmap(
                    pix.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                )
            avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            card_layout.addWidget(avatar_label)

        # Title
        title = QLabel(f"{APP_NAME} Access")
        title.setStyleSheet(
            f"""
            font-size: 20px;
            font-weight: 700;
            color: {COLOR_TEXT_MAIN};
            letter-spacing: 1px;
            """
        )
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(title)

        subtitle = QLabel("Sign in to your StormOS workstation")
        subtitle.setStyleSheet(f"font-size: 11px; color: {COLOR_TEXT_SECONDARY};")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(subtitle)

        # Username selector / input
        self.user_combo = QComboBox()
        self.user_combo.setStyleSheet(
            f"""
            QComboBox {{
                background-color: {COLOR_STORM_CLOUD};
                color: {COLOR_TEXT_MAIN};
                border: 1px solid {COLOR_PANEL_EDGE};
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 14px;
            }}
            QComboBox:focus {{
                border: 1px solid {COLOR_LIGHTNING};
            }}
            QComboBox QAbstractItemView {{
                background-color: {COLOR_RAISED_PANEL};
                color: {COLOR_TEXT_MAIN};
                selection-background-color: {COLOR_LIGHTNING};
                selection-color: {COLOR_NIGHT_SKY};
                border: 1px solid {COLOR_PANEL_EDGE};
            }}
            """
        )
        card_layout.addWidget(self.user_combo)

        # Password Input
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Enter password...")
        self.password_input.setStyleSheet(
            f"""
            QLineEdit {{
                background-color: {COLOR_STORM_CLOUD};
                color: {COLOR_TEXT_MAIN};
                border: 1px solid {COLOR_PANEL_EDGE};
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 14px;
            }}
            QLineEdit:focus {{
                border: 1px solid {COLOR_LIGHTNING};
                background-color: rgba(16, 26, 49, 0.95);
            }}
            """
        )
        self.password_input.returnPressed.connect(self._handle_login)
        card_layout.addWidget(self.password_input)

        # Error / Status message
        self.status_label = QLabel("")
        self.status_label.setStyleSheet(f"font-size: 12px; color: {COLOR_ERROR}; min-height: 16px;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.status_label)

        # Sign In Button
        self.login_btn = QPushButton("Sign In")
        self.login_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {COLOR_LIGHTNING};
                color: {COLOR_NIGHT_SKY};
                font-weight: 700;
                font-size: 15px;
                border: none;
                border-radius: 8px;
                padding: 10px 16px;
            }}
            QPushButton:hover {{
                background-color: {COLOR_LIGHTNING_GLOW};
            }}
            QPushButton:pressed {{
                background-color: #2BA0CC;
            }}
            """
        )
        self.login_btn.clicked.connect(self._handle_login)
        card_layout.addWidget(self.login_btn)

        # Secondary Actions Row (Create Account & Quick Login)
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(10)

        self.signup_btn = QPushButton("+ Create Account")
        self.signup_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: transparent;
                color: {COLOR_TEXT_MAIN};
                font-size: 12px;
                font-weight: 600;
                border: 1px solid {COLOR_PANEL_EDGE};
                border-radius: 6px;
                padding: 7px 12px;
            }}
            QPushButton:hover {{
                border: 1px solid {COLOR_LIGHTNING};
                color: {COLOR_LIGHTNING};
                background-color: rgba(56, 201, 255, 0.08);
            }}
            """
        )
        self.signup_btn.clicked.connect(self._open_signup_dialog)
        actions_layout.addWidget(self.signup_btn)

        # Quick Test Login Helper
        self.quick_test_btn = QPushButton("⚡ Quick Login ('storm')")
        self.quick_test_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: transparent;
                color: {COLOR_LIGHTNING};
                font-size: 12px;
                border: 1px dashed {COLOR_PANEL_EDGE};
                border-radius: 6px;
                padding: 7px 12px;
            }}
            QPushButton:hover {{
                border: 1px solid {COLOR_LIGHTNING};
                background-color: rgba(56, 201, 255, 0.1);
            }}
            """
        )
        self.quick_test_btn.clicked.connect(self._quick_login_storm)
        actions_layout.addWidget(self.quick_test_btn)

        card_layout.addLayout(actions_layout)

        # Exit action
        exit_layout = QHBoxLayout()
        exit_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        exit_btn = QPushButton("Exit StormOS")
        exit_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: transparent;
                color: {COLOR_TEXT_SECONDARY};
                font-size: 12px;
                border: none;
                padding: 4px;
            }}
            QPushButton:hover {{
                color: {COLOR_ERROR};
                text-decoration: underline;
            }}
            """
        )
        exit_btn.clicked.connect(self.exit_requested.emit)
        exit_layout.addWidget(exit_btn)
        card_layout.addLayout(exit_layout)

        main_layout.addWidget(self.card)

    def refresh_users(self):
        """Populate user accounts into the dropdown."""
        self.user_combo.clear()
        users = self.user_manager.list_users()
        for user in users:
            self.user_combo.addItem(f"{user.display_name} ({user.username})", user.username)

    def _get_selected_username(self) -> str:
        """Return the currently selected username."""
        data = self.user_combo.currentData()
        if data:
            return str(data)
        # Fallback to combo text
        return self.user_combo.currentText().strip()

    def _handle_login(self):
        """Validate credentials and trigger login signal."""
        username = self._get_selected_username()
        password = self.password_input.text()

        if not username:
            self.set_status("Please select a user account", is_error=True)
            return

        if not password:
            self.set_status("Please enter your password", is_error=True)
            return

        profile = self.user_manager.authenticate(username, password)
        if profile:
            self.status_label.setText("")
            self.password_input.clear()
            self.login_successful.emit(profile)
        else:
            self.set_status("Invalid password. Access denied.", is_error=True)
            self.password_input.selectAll()
            self.password_input.setFocus()

    def _quick_login_storm(self):
        """Perform fast one-click login with default test credentials."""
        self.user_manager.ensure_default_account()
        # Find 'storm' index in combo
        idx = self.user_combo.findData("storm")
        if idx >= 0:
            self.user_combo.setCurrentIndex(idx)
        self.password_input.setText("storm")
        self._handle_login()

    def _open_signup_dialog(self):
        """Open the account registration dialog."""
        dialog = SignUpDialog(self.user_manager, self)
        if dialog.exec():
            # Refresh list and select the newly created user
            self.refresh_users()
            if dialog.created_profile:
                new_user = dialog.created_profile.username
                idx = self.user_combo.findData(new_user)
                if idx >= 0:
                    self.user_combo.setCurrentIndex(idx)
                self.set_status(f"Account '{new_user}' created! Enter password to sign in.", is_error=False)
                self.password_input.clear()
                self.password_input.setFocus()

    def set_status(self, text: str, is_error: bool = False):
        """Display an informational or error status message."""
        self.status_label.setText(text)
        color = COLOR_ERROR if is_error else COLOR_LIGHTNING
        self.status_label.setStyleSheet(f"font-size: 12px; color: {color}; min-height: 16px;")
