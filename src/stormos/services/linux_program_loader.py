"""Linux Program Loader — scans and wraps native Linux desktop entries.

Scans `/usr/share/applications/*.desktop` files for installed Linux programs,
parses them, creates StormOS AppMetadata wrappers, and registers them in the
AppRegistry so they appear in the App Store and Start menu.

This service only works on Linux systems. On Windows or macOS it returns empty
results gracefully.
"""

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from stormos.apps.registry import AppMetadata, AppRegistry
from stormos.core.platform_compat import get_platform


# Common Linux applications directories
DESKTOP_DIRS = [
    "/usr/share/applications",
    "/usr/local/share/applications",
    "/local/share/applications",  # relative to XDG_DATA_HOME
]

# Categories mapping from freedesktop.org to StormOS categories
CATEGORY_MAP = {
    "AudioVideo": "Multimedia",
    "Audio": "Multimedia",
    "Video": "Multimedia",
    "Player": "Multimedia",
    "Music": "Multimedia",
    "Development": "Development",
    "IDE": "Development",
    "TextEditor": "Development",
    "Building": "Development",
    "Debugger": "Development",
    "Education": "Education",
    "Game": "Games",
    "Graphics": "Graphics",
    "Office": "Productivity",
    "Spreadsheet": "Productivity",
    "Presentation": "Productivity",
    "WordProcessor": "Productivity",
    "Network": "Network",
    "WebBrowser": "Network",
    "Email": "Network",
    "Filesystem": "Utilities",
    "System": "System",
    "Settings": "System",
    "Utility": "Utilities",
}


@dataclass
class LinuxDesktopEntry:
    """Parsed Linux .desktop file entry."""
    name: str
    exec_command: str
    icon: str
    categories: List[str]
    comment: str = ""
    terminal: bool = False
    path: str = ""
    desktop_file_path: str = ""


class LinuxProgramLoader:
    """Scans and wraps Linux desktop entries for StormOS integration."""

    _instance: Optional["LinuxProgramLoader"] = None
    _loaded: bool = False

    def __init__(self):
        self._entries: Dict[str, LinuxDesktopEntry] = {}
        self._registered_ids: List[str] = []

    @classmethod
    def get_instance(cls) -> "LinuxProgramLoader":
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def is_available(self) -> bool:
        """Check if Linux program loading is available (only on Linux)."""
        return get_platform() == "linux"

    def scan(self, dirs: Optional[List[str]] = None) -> int:
        """Scan desktop directories for .desktop files.

        Args:
            dirs: Optional list of directories to scan. If None, uses default paths.

        Returns:
            Number of desktop entries found.
        """
        if not self.is_available():
            return 0

        self._entries.clear()
        scan_dirs = dirs or DESKTOP_DIRS

        for desktop_dir in scan_dirs:
            desktop_path = Path(desktop_dir)
            if not desktop_path.exists():
                continue

            for desktop_file in desktop_path.glob("*.desktop"):
                entry = self._parse_desktop_file(desktop_file)
                if entry is not None:
                    # Use a unique key based on the desktop file name
                    key = desktop_file.stem
                    self._entries[key] = entry

        self._loaded = True
        return len(self._entries)

    def load_to_registry(self) -> int:
        """Scan and register all Linux programs in the AppRegistry.

        Returns:
            Number of programs registered.
        """
        if not self.is_available():
            return 0

        # Unregister previously registered Linux programs
        self._unregister_all()

        # Scan if not already loaded
        if not self._loaded:
            self.scan()

        # Register each entry
        count = 0
        for key, entry in self._entries.items():
            metadata = self._create_app_metadata(key, entry)
            if metadata is not None:
                AppRegistry.get_instance().register(metadata)
                self._registered_ids.append(metadata.id)
                count += 1

        return count

    def _unregister_all(self) -> None:
        """Unregister all previously registered Linux programs."""
        for app_id in self._registered_ids:
            AppRegistry.get_instance().unregister(app_id)
        self._registered_ids.clear()

    def get_entries(self) -> Dict[str, LinuxDesktopEntry]:
        """Get all parsed desktop entries.

        Returns:
            Dictionary of entry key to LinuxDesktopEntry.
        """
        if not self._loaded:
            self.scan()
        return self._entries

    def get_entry(self, key: str) -> Optional[LinuxDesktopEntry]:
        """Get a specific desktop entry by key.

        Args:
            key: The entry key (desktop file stem).

        Returns:
            LinuxDesktopEntry or None if not found.
        """
        if not self._loaded:
            self.scan()
        return self._entries.get(key)

    def launch_program(self, key: str) -> bool:
        """Launch a Linux program by its key.

        Args:
            key: The entry key (desktop file stem).

        Returns:
            True if the program was launched successfully.
        """
        entry = self.get_entry(key)
        if entry is None:
            return False

        try:
            # Expand %f, %F, %u, %U placeholders (file/URL arguments)
            exec_cmd = entry.exec_command
            exec_cmd = re.sub(r'%[fFuU]', '', exec_cmd)

            # Set working directory
            cwd = entry.path if entry.path else None

            # Launch the process
            subprocess.Popen(
                exec_cmd,
                shell=True,
                cwd=cwd,
                start_new_session=True,
            )
            return True
        except (OSError, ValueError):
            return False

    def _parse_desktop_file(self, path: Path) -> Optional[LinuxDesktopEntry]:
        """Parse a .desktop file into a LinuxDesktopEntry.

        Args:
            path: Path to the .desktop file.

        Returns:
            LinuxDesktopEntry or None if parsing fails.
        """
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None

        # Must have [Desktop Entry] section
        if "[Desktop Entry]" not in content:
            return None

        # Must be an Application type
        if "Type=Application" not in content:
            return None

        # Parse key fields
        name = self._parse_field(content, "Name", "Unnamed Application")
        exec_cmd = self._parse_field(content, "Exec", "")
        icon = self._parse_field(content, "Icon", "")
        comment = self._parse_field(content, "Comment", "")
        categories_str = self._parse_field(content, "Categories", "")
        terminal = self._parse_field(content, "Terminal", "false").lower() == "true"
        path_dir = self._parse_field(content, "Path", "")

        if not exec_cmd:
            return None

        # Parse categories
        categories = [c.strip() for c in categories_str.split(";") if c.strip()]

        return LinuxDesktopEntry(
            name=name,
            exec_command=exec_cmd,
            icon=icon,
            categories=categories,
            comment=comment,
            terminal=terminal,
            path=path_dir,
            desktop_file_path=str(path),
        )

    def _parse_field(self, content: str, field: str, default: str = "") -> str:
        """Parse a field from a .desktop file.

        Args:
            content: Full file content.
            field: Field name to parse.
            default: Default value if not found.

        Returns:
            Field value or default.
        """
        # Look for the field in [Desktop Entry] section
        lines = content.split("\n")
        in_desktop_entry = False

        for line in lines:
            line = line.strip()
            if line == "[Desktop Entry]":
                in_desktop_entry = True
                continue
            if line.startswith("[") and line.endswith("]"):
                # Another section started
                break
            if in_desktop_entry and line.startswith(f"{field}="):
                value = line[len(field) + 1:].strip()
                return value if value else default

        return default

    def _create_app_metadata(self, key: str, entry: LinuxDesktopEntry) -> Optional[AppMetadata]:
        """Create an AppMetadata wrapper for a Linux desktop entry.

        Args:
            key: Unique key for the entry.
            entry: Parsed LinuxDesktopEntry.

        Returns:
            AppMetadata or None if the entry cannot be wrapped.
        """
        # Map freedesktop category to StormOS category
        stormos_category = "Utilities"
        for cat in entry.categories:
            # Remove vendor prefixes like "KDE;", "GNOME;"
            base_cat = cat.split(";")[0] if ";" in cat else cat
            if base_cat in CATEGORY_MAP:
                stormos_category = CATEGORY_MAP[base_cat]
                break

        # Create a launch factory for the program
        program_key = key

        def factory(user=None, parent=None):  # type: ignore[return-value]
            """Factory that launches the Linux program."""
            loader = LinuxProgramLoader.get_instance()
            loader.launch_program(program_key)
            # Return None since the program runs externally
            return None

        # Use emoji icon if the icon is a file path
        icon = entry.icon
        if icon and (Path(icon).exists() or not icon.startswith(("🔤", "😀", "🎵", "🎮", "📁", "⚙️"))):
            # It's a file path icon, use a generic emoji based on category
            icon_emoji_map = {
                "Multimedia": "🎵",
                "Development": "💻",
                "Education": "📚",
                "Games": "🎮",
                "Graphics": "🎨",
                "Productivity": "📝",
                "Network": "🌐",
                "System": "⚙️",
                "Utilities": "🔧",
            }
            icon = icon_emoji_map.get(stormos_category, "📦")

        # Use emoji if icon is empty
        if not icon:
            icon = "📦"

        # Build description from comment and categories
        description = entry.comment if entry.comment else f"Linux program: {entry.name}"
        if entry.categories:
            description += f" (Categories: {', '.join(entry.categories)})"

        return AppMetadata(
            id=f"linux.{key}",
            name=entry.name,
            description=description,
            icon=icon,
            category=stormos_category,
            is_builtin=False,
            factory=factory,
        )

    def get_program_list(self) -> List[Dict[str, str]]:
        """Get a list of all detected Linux programs.

        Returns:
            List of dictionaries with program information.
        """
        if not self._loaded:
            self.scan()

        programs = []
        for key, entry in self._entries.items():
            programs.append({
                "id": f"linux.{key}",
                "name": entry.name,
                "icon": entry.icon,
                "categories": entry.categories,
                "exec": entry.exec_command,
                "comment": entry.comment,
            })
        return programs
