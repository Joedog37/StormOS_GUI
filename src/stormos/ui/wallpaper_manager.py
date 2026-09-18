"""StormOS Wallpaper Manager.

Handles built-in procedural and asset-based wallpapers, custom wallpaper loading,
caching, and thumbnail generation for the Personalization Settings.
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple
from PySide6.QtCore import QPointF, QRect, QRectF, QSize, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QConicalGradient,
    QFont,
    QGradient,
    QIcon,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QRadialGradient,
)

from stormos.core.constants import (
    COLOR_LIGHTNING,
    COLOR_LIGHTNING_GLOW,
    COLOR_MIST_BLUE,
    COLOR_NIGHT_SKY,
    COLOR_PANEL_EDGE,
    COLOR_RAISED_PANEL,
    COLOR_STORM_CLOUD,
    COLOR_TEXT_MAIN,
    COLOR_TEXT_SECONDARY,
)
from stormos.core.paths import ASSETS_DIR, get_asset_path


WALLPAPER_PRESETS = [
    {
        "id": "default_storm",
        "name": "Default Storm Clouds",
        "type": "asset",
        "path": "wallpaper.png",
        "desc": "Cinematic dark thunderhead clouds with atmospheric depth.",
    },
    {
        "id": "thunder_splash",
        "name": "Thunder Crest Splash",
        "type": "asset",
        "path": "storm_splash.png",
        "desc": "Official Thunderhead Pictures StormOS backdrop.",
    },
    {
        "id": "deep_night",
        "name": "Deep Night Sky",
        "type": "procedural",
        "desc": "Minimalist ultra-dark gradient with subtle electric mist.",
    },
    {
        "id": "lightning_surge",
        "name": "Lightning Surge",
        "type": "procedural",
        "desc": "Cyber electric cyan storm energy with atmospheric aura.",
    },
    {
        "id": "midnight_nebula",
        "name": "Midnight Nebula",
        "type": "procedural",
        "desc": "Cosmic deep indigo and violet thunderstorm nebula.",
    },
    {
        "id": "electric_horizon",
        "name": "Electric Horizon",
        "type": "procedural",
        "desc": "Low-horizon stormy aura with cyber lightning highlights.",
    },
]


class WallpaperManager:
    """Manages wallpaper generation, custom image loading, and wallpaper gallery."""

    _cache: Dict[str, QPixmap] = {}

    @classmethod
    def get_presets(cls) -> List[Dict[str, str]]:
        return list(WALLPAPER_PRESETS)

    @classmethod
    def render_procedural_wallpaper(cls, preset_id: str, width: int = 1920, height: int = 1080) -> QPixmap:
        """Render a high-resolution procedural gradient wallpaper."""
        cache_key = f"proc_{preset_id}_{width}x{height}"
        if cache_key in cls._cache:
            return cls._cache[cache_key]

        pixmap = QPixmap(width, height)
        pixmap.fill(QColor(COLOR_NIGHT_SKY))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(0, 0, width, height)

        if preset_id == "deep_night":
            # Deep atmospheric gradient
            grad = QRadialGradient(QPointF(width * 0.5, height * 0.4), width * 0.8)
            grad.setColorAt(0.0, QColor(24, 38, 68))
            grad.setColorAt(0.5, QColor(16, 26, 49))
            grad.setColorAt(1.0, QColor(7, 11, 22))
            painter.fillRect(rect, grad)

            # Subtle horizon glow
            h_grad = QLinearGradient(0, height * 0.7, 0, height)
            h_grad.setColorAt(0.0, QColor(0, 0, 0, 0))
            h_grad.setColorAt(1.0, QColor(56, 201, 255, 20))
            painter.fillRect(rect, h_grad)

        elif preset_id == "lightning_surge":
            # Dark base
            grad = QLinearGradient(0, 0, width, height)
            grad.setColorAt(0.0, QColor(10, 18, 36))
            grad.setColorAt(0.6, QColor(16, 26, 49))
            grad.setColorAt(1.0, QColor(7, 11, 22))
            painter.fillRect(rect, grad)

            # Electric radial lightning surge in top center-right
            rad1 = QRadialGradient(QPointF(width * 0.7, height * 0.25), width * 0.5)
            rad1.setColorAt(0.0, QColor(56, 201, 255, 90))
            rad1.setColorAt(0.4, QColor(56, 201, 255, 25))
            rad1.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.fillRect(rect, rad1)

            # Secondary blue glow in bottom left
            rad2 = QRadialGradient(QPointF(width * 0.2, height * 0.8), width * 0.4)
            rad2.setColorAt(0.0, QColor(169, 235, 255, 45))
            rad2.setColorAt(0.5, QColor(56, 201, 255, 12))
            rad2.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.fillRect(rect, rad2)

            # Subtle cyber circuit lines
            pen = QPen(QColor(56, 201, 255, 18), 1.5)
            painter.setPen(pen)
            for y in range(0, height, 80):
                painter.drawLine(0, y, width, y)
            for x in range(0, width, 120):
                painter.drawLine(x, 0, x, height)

        elif preset_id == "midnight_nebula":
            # Cosmic deep indigo base
            grad = QRadialGradient(QPointF(width * 0.4, height * 0.45), width * 0.75)
            grad.setColorAt(0.0, QColor(48, 25, 75))
            grad.setColorAt(0.4, QColor(25, 20, 52))
            grad.setColorAt(0.8, QColor(12, 16, 36))
            grad.setColorAt(1.0, QColor(7, 11, 22))
            painter.fillRect(rect, grad)

            # Violet/cyan cross aura
            v_grad = QRadialGradient(QPointF(width * 0.65, height * 0.35), width * 0.4)
            v_grad.setColorAt(0.0, QColor(157, 78, 221, 80))
            v_grad.setColorAt(0.6, QColor(56, 201, 255, 20))
            v_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.fillRect(rect, v_grad)

        else:  # electric_horizon / fallback
            grad = QLinearGradient(0, 0, 0, height)
            grad.setColorAt(0.0, QColor(7, 11, 22))
            grad.setColorAt(0.65, QColor(16, 26, 49))
            grad.setColorAt(0.85, QColor(28, 50, 85))
            grad.setColorAt(1.0, QColor(56, 201, 255, 70))
            painter.fillRect(rect, grad)

        painter.end()
        cls._cache[cache_key] = pixmap
        return pixmap

    @classmethod
    def get_wallpaper_pixmap(cls, wp_name_or_path: str, width: int = 1920, height: int = 1080) -> QPixmap:
        """Get pixmap for any preset ID, asset name, or absolute file path."""
        # Check if it's a procedural preset
        for preset in WALLPAPER_PRESETS:
            if wp_name_or_path == preset["id"] or wp_name_or_path == preset["name"]:
                if preset["type"] == "procedural":
                    return cls.render_procedural_wallpaper(preset["id"], width, height)
                elif preset["type"] == "asset":
                    wp_name_or_path = preset["path"]
                break

        # Check in assets
        asset_p = get_asset_path(wp_name_or_path)
        if asset_p.exists():
            pix = QPixmap(str(asset_p))
            if not pix.isNull():
                return pix

        # Check direct path
        direct_p = Path(wp_name_or_path)
        if direct_p.exists() and direct_p.is_file():
            pix = QPixmap(str(direct_p))
            if not pix.isNull():
                return pix

        # Fallback to default asset
        default_p = get_asset_path("wallpaper.png")
        if default_p.exists():
            pix = QPixmap(str(default_p))
            if not pix.isNull():
                return pix

        # Ultimate fallback to procedural deep night
        return cls.render_procedural_wallpaper("deep_night", width, height)

    @classmethod
    def create_thumbnail(cls, wp_identifier: str, thumb_w: int = 160, thumb_h: int = 100) -> QPixmap:
        """Generate a scaled thumbnail with rounded corners and dark border for UI selection."""
        full_pix = cls.get_wallpaper_pixmap(wp_identifier, width=480, height=300)
        scaled = full_pix.scaled(
            thumb_w,
            thumb_h,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )

        thumb = QPixmap(thumb_w, thumb_h)
        thumb.fill(Qt.GlobalColor.transparent)

        painter = QPainter(thumb)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        path = QPainterPath()
        path.addRoundedRect(0, 0, thumb_w, thumb_h, 8, 8)
        painter.setClipPath(path)

        crop_x = (scaled.width() - thumb_w) // 2
        crop_y = (scaled.height() - thumb_h) // 2
        painter.drawPixmap(0, 0, scaled.copy(crop_x, crop_y, thumb_w, thumb_h))

        painter.setClipping(False)
        painter.setPen(QPen(QColor(COLOR_PANEL_EDGE), 1.5))
        painter.drawRoundedRect(0.5, 0.5, thumb_w - 1, thumb_h - 1, 8, 8)
        painter.end()

        return thumb
