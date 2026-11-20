"""Cross-platform compatibility layer for StormOS.

Provides platform detection, data directory resolution, and system-specific
utilities to enable StormOS to run on Windows, Linux, and macOS.

Usage:
    from stormos.core.platform_compat import Platform, get_platform, get_data_dir
    
    platform = get_platform()
    data_dir = get_data_dir()
"""

import os
import sys
import platform
import subprocess
import logging
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Platform enumeration
class Platform:
    """Supported operating system platforms."""
    WINDOWS = "windows"
    LINUX = "linux"
    MACOS = "macos"
    UNKNOWN = "unknown"
    
    # Desktop environment detection (Linux)
    DE_UNKNOWN = "unknown"
    DE_GNOME = "gnome"
    DE_KDE = "kde"
    DE_XFCE = "xfce"
    DE_MATE = "mate"
    DE_CINNAMON = "cinnamon"
    DE_OTHER = "other"


# Cache the detected platform
_detected_platform: Optional[str] = None
_detected_desktop_env: Optional[str] = None


def get_platform() -> str:
    """Detect and return the current operating system platform.
    
    Returns:
        One of Platform.WINDOWS, Platform.LINUX, Platform.MACOS, or Platform.UNKNOWN.
    """
    global _detected_platform
    
    if _detected_platform is not None:
        return _detected_platform
    
    system = platform.system().lower()
    
    if system == "windows":
        _detected_platform = Platform.WINDOWS
    elif system == "linux":
        _detected_platform = Platform.LINUX
    elif system == "darwin":
        _detected_platform = Platform.MACOS
    else:
        _detected_platform = Platform.UNKNOWN
        logger.warning("Unknown platform detected: %s", system)
    
    logger.info("Detected platform: %s (%s)", _detected_platform, platform.platform())
    return _detected_platform


def is_windows() -> bool:
    """Check if running on Windows."""
    return get_platform() == Platform.WINDOWS


def is_linux() -> bool:
    """Check if running on Linux."""
    return get_platform() == Platform.LINUX


def is_macos() -> bool:
    """Check if running on macOS."""
    return get_platform() == Platform.MACOS


def get_desktop_environment() -> str:
    """Detect the Linux desktop environment.
    
    Returns:
        One of Platform.DE_* constants. Returns DE_UNKNOWN on non-Linux systems.
    """
    global _detected_desktop_env
    
    if get_platform() != Platform.LINUX:
        return Platform.DE_UNKNOWN
    
    if _detected_desktop_env is not None:
        return _detected_desktop_env
    
    # Check XDG_CURRENT_DESKTOP first
    desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
    
    if "gnome" in desktop or "unity" in desktop:
        _detected_desktop_env = Platform.DE_GNOME
    elif "kde" in desktop or "plasma" in desktop:
        _detected_desktop_env = Platform.DE_KDE
    elif "xfce" in desktop:
        _detected_desktop_env = Platform.DE_XFCE
    elif "mate" in desktop:
        _detected_desktop_env = Platform.DE_MATE
    elif "cinnamon" in desktop:
        _detected_desktop_env = Platform.DE_CINNAMON
    else:
        # Fallback: check DESKTOP_SESSION
        session = os.environ.get("DESKTOP_SESSION", "").lower()
        if "gnome" in session:
            _detected_desktop_env = Platform.DE_GNOME
        elif "kde" in session or "plasma" in session:
            _detected_desktop_env = Platform.DE_KDE
        elif "xfce" in session:
            _detected_desktop_env = Platform.DE_XFCE
        else:
            _detected_desktop_env = Platform.DE_OTHER
    
    logger.info("Detected desktop environment: %s", _detected_desktop_env)
    return _detected_desktop_env


def get_data_dir(app_name: str = "StormOS") -> Path:
    """Get the appropriate data directory for the application based on platform.
    
    Follows platform conventions:
    - Windows: %APPDATA%/StormOS
    - macOS: ~/Library/Application Support/StormOS
    - Linux: ~/.local/share/stormos (XDG Base Directory spec)
    
    Args:
        app_name: Application name for directory naming.
        
    Returns:
        Path to the application data directory.
    """
    plat = get_platform()
    
    if plat == Platform.WINDOWS:
        appdata = os.environ.get("APPDATA")
        if appdata:
            data_dir = Path(appdata) / app_name
        else:
            data_dir = Path.home() / "AppData" / "Roaming" / app_name
    
    elif plat == Platform.MACOS:
        home = Path.home()
        data_dir = home / "Library" / "Application Support" / app_name
    
    elif plat == Platform.LINUX:
        # Follow XDG Base Directory specification
        xdg_data = os.environ.get("XDG_DATA_HOME")
        if xdg_data:
            data_dir = Path(xdg_data) / app_name.lower()
        else:
            data_dir = Path.home() / ".local" / "share" / app_name.lower()
    
    else:
        # Fallback to home directory
        data_dir = Path.home() / f".{app_name.lower()}"
    
    # Create directory if it doesn't exist
    data_dir.mkdir(parents=True, exist_ok=True)
    
    logger.debug("Data directory: %s", data_dir)
    return data_dir


def get_cache_dir(app_name: str = "StormOS") -> Path:
    """Get the appropriate cache directory for the application based on platform.
    
    Follows platform conventions:
    - Windows: %LOCALAPPDATA%/StormOS/Cache
    - macOS: ~/Library/Caches/StormOS
    - Linux: ~/.cache/stormos (XDG Base Directory spec)
    
    Args:
        app_name: Application name for directory naming.
        
    Returns:
        Path to the application cache directory.
    """
    plat = get_platform()
    
    if plat == Platform.WINDOWS:
        localappdata = os.environ.get("LOCALAPPDATA")
        if localappdata:
            cache_dir = Path(localappdata) / app_name / "Cache"
        else:
            cache_dir = Path.home() / "AppData" / "Local" / app_name / "Cache"
    
    elif plat == Platform.MACOS:
        home = Path.home()
        cache_dir = home / "Library" / "Caches" / app_name
    
    elif plat == Platform.LINUX:
        xdg_cache = os.environ.get("XDG_CACHE_HOME")
        if xdg_cache:
            cache_dir = Path(xdg_cache) / app_name.lower()
        else:
            cache_dir = Path.home() / ".cache" / app_name.lower()
    
    else:
        cache_dir = get_data_dir(app_name) / "cache"
    
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def get_config_dir(app_name: str = "StormOS") -> Path:
    """Get the appropriate config directory for the application based on platform.
    
    Follows platform conventions:
    - Windows: %APPDATA%/StormOS
    - macOS: ~/Library/Preferences/StormOS
    - Linux: ~/.config/stormos (XDG Base Directory spec)
    
    Args:
        app_name: Application name for directory naming.
        
    Returns:
        Path to the application config directory.
    """
    plat = get_platform()
    
    if plat == Platform.WINDOWS:
        return get_data_dir(app_name)
    
    elif plat == Platform.MACOS:
        home = Path.home()
        config_dir = home / "Library" / "Preferences" / app_name
    
    elif plat == Platform.LINUX:
        xdg_config = os.environ.get("XDG_CONFIG_HOME")
        if xdg_config:
            config_dir = Path(xdg_config) / app_name.lower()
        else:
            config_dir = Path.home() / ".config" / app_name.lower()
    
    else:
        config_dir = get_data_dir(app_name)
    
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_python_executable() -> str:
    """Get the Python executable path for the current platform.
    
    Returns:
        Path to the Python executable ('python' on Windows, 'python3' on Unix).
    """
    if is_windows():
        return "python"
    else:
        return "python3"


def open_file_explorer(path: Path) -> bool:
    """Open the system file explorer at the given path.
    
    Args:
        path: Directory path to open.
        
    Returns:
        True if the explorer was successfully launched.
    """
    try:
        plat = get_platform()
        
        if plat == Platform.WINDOWS:
            os.startfile(str(path))
            return True
        
        elif plat == Platform.MACOS:
            subprocess.Popen(["open", str(path)])
            return True
        
        elif plat == Platform.LINUX:
            # Try xdg-open first, then fallback to platform-specific tools
            desktop = get_desktop_environment()
            
            if desktop == Platform.DE_GNOME:
                subprocess.Popen(["xdg-open", str(path)])
            elif desktop == Platform.DE_KDE:
                subprocess.Popen(["kioclient", "exec", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
            return True
        
    except Exception as e:
        logger.error("Failed to open file explorer: %s", e)
        return False
    
    return False


def open_url(url: str) -> bool:
    """Open a URL in the default web browser.
    
    Args:
        url: URL to open.
        
    Returns:
        True if the browser was successfully launched.
    """
    try:
        import webbrowser
        return webbrowser.open(url)
    except Exception as e:
        logger.error("Failed to open URL: %s", e)
        return False


def get_screen_scale_factor() -> float:
    """Get the screen scale factor for HiDPI displays.
    
    This is a fallback for when Qt's screen scale is not available.
    
    Returns:
        Scale factor (1.0 for standard, 1.25, 1.5, 2.0 for HiDPI).
    """
    try:
        if is_windows():
            # Windows DPI awareness
            try:
                import ctypes
                user32 = ctypes.windll.user32
                user32.SetProcessDPIAware()
                # Get DPI from primary monitor
                hdc = ctypes.windll.user32.GetDC(0)
                dpi = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)  # LOGPIXELSX
                ctypes.windll.user32.ReleaseDC(0, hdc)
                return dpi / 96.0
            except Exception:
                return 1.0
        
        elif is_macos():
            # macOS typically uses 2x scaling on Retina displays
            return 2.0
        
        else:
            return 1.0
    
    except Exception as e:
        logger.warning("Could not determine screen scale factor: %s", e)
        return 1.0


def check_display_server() -> Tuple[bool, str]:
    """Check for a running display server on Linux.
    
    Returns:
        Tuple of (has_display, display_type) where display_type is one of:
        'x11', 'wayland', 'none'
    """
    if get_platform() != Platform.LINUX:
        return True, "native"
    
    display = os.environ.get("DISPLAY", "")
    wayland = os.environ.get("WAYLAND_DISPLAY", "")
    
    if wayland:
        return True, "wayland"
    elif display:
        return True, "x11"
    else:
        return False, "none"


def get_system_info() -> dict:
    """Get comprehensive system information.
    
    Returns:
        Dictionary containing system information keys:
        - platform: Detected platform string
        - system: OS name (from platform.system())
        - release: OS release version
        - machine: Hardware architecture
        - processor: Processor type
        - python_version: Python version string
        - desktop_env: Desktop environment (Linux only)
        - display_server: Display server type (Linux only)
    """
    has_display, display_type = check_display_server()
    
    info = {
        "platform": get_platform(),
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
        "desktop_env": get_desktop_environment() if is_linux() else None,
        "display_server": display_type if is_linux() else None,
        "has_display": has_display,
    }
    
    return info


def setup_platform() -> dict:
    """Initialize platform-specific settings and return system info.
    
    This function should be called once at application startup to set up
    platform-specific directories and detect system capabilities.
    
    Returns:
        Dictionary containing system information.
    """
    logger.info("Setting up platform compatibility layer...")
    
    # Detect platform
    plat = get_platform()
    logger.info("Platform: %s", plat)
    
    # Create necessary directories
    data_dir = get_data_dir()
    cache_dir = get_cache_dir()
    config_dir = get_config_dir()
    
    logger.info("Data directory: %s", data_dir)
    logger.info("Cache directory: %s", cache_dir)
    logger.info("Config directory: %s", config_dir)
    
    # Check display server on Linux
    if is_linux():
        has_display, display_type = check_display_server()
        if not has_display:
            logger.warning("No display server detected! GUI may not work.")
        else:
            logger.info("Display server: %s", display_type)
    
    # Get system info
    info = get_system_info()
    
    logger.info("Platform setup complete.")
    return info


def get_line_ending() -> str:
    """Get the appropriate line ending for the current platform.
    
    Returns:
        '\\r\\n' for Windows, '\\n' for Unix-like systems.
    """
    if is_windows():
        return "\r\n"
    else:
        return "\n"


def get_path_separator() -> str:
    """Get the path separator for the current platform.
    
    Returns:
        '\\' for Windows, '/' for Unix-like systems.
    """
    return os.sep


def normalize_path(path: str) -> str:
    """Normalize a path string for the current platform.
    
    Converts forward slashes to backslashes on Windows and vice versa.
    
    Args:
        path: Path string to normalize.
        
    Returns:
        Normalized path string.
    """
    # Replace all separators with the platform-specific one
    return path.replace("/", os.sep).replace("\\", os.sep) if os.sep == "\\" else path.replace("\\", "/")
