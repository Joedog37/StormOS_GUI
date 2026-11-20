"""Tests for LinuxProgramLoader service.

Tests desktop entry parsing, app wrapper creation, category mapping,
and edge cases (missing icons, invalid entries, non-Linux platforms).
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from stormos.services.linux_program_loader import (
    LinuxProgramLoader,
    LinuxDesktopEntry,
    DESKTOP_DIRS,
    CATEGORY_MAP,
)
from stormos.apps.registry import AppRegistry


# Valid .desktop file content
VALID_DESKTOP = """[Desktop Entry]
Version=1.0
Type=Application
Name=Firefox Web Browser
Comment=Browse the World Wide Web
Exec=firefox %u
Icon=firefox
Terminal=false
Categories=Network;WebBrowser;
Path=
"""

# Minimal valid .desktop file
MINIMAL_DESKTOP = """[Desktop Entry]
Type=Application
Name=Test App
Exec=/usr/bin/test-app
"""

# Invalid: no [Desktop Entry] section
INVALID_NO_SECTION = """Name=Broken App
Exec=/usr/bin/broken
"""

# Invalid: not an Application type
INVALID_TYPE = """[Desktop Entry]
Type=Link
Name=Some Link
URL=https://example.com
"""

# Invalid: no Exec field
INVALID_NO_EXEC = """[Desktop Entry]
Type=Application
Name=No Exec App
"""

# Terminal app
TERMINAL_DESKTOP = """[Desktop Entry]
Type=Application
Name=Terminal Emulator
Exec=/usr/bin/xterm
Icon=utilities-terminal
Terminal=true
Categories=System;TerminalEmulator;
"""


@pytest.fixture(autouse=True)
def reset_loader():
    """Reset the singleton before each test."""
    LinuxProgramLoader._instance = None
    LinuxProgramLoader._loaded = False
    AppRegistry._instance = None
    yield
    # Cleanup after test
    LinuxProgramLoader._instance = None
    LinuxProgramLoader._loaded = False
    AppRegistry._instance = None


class TestCategoryMap:
    """Test the freedesktop to StormOS category mapping."""

    def test_audio_video_maps_to_multimedia(self):
        assert CATEGORY_MAP["AudioVideo"] == "Multimedia"
        assert CATEGORY_MAP["Audio"] == "Multimedia"
        assert CATEGORY_MAP["Video"] == "Multimedia"

    def test_development_categories(self):
        assert CATEGORY_MAP["Development"] == "Development"
        assert CATEGORY_MAP["IDE"] == "Development"
        assert CATEGORY_MAP["TextEditor"] == "Development"

    def test_network_categories(self):
        assert CATEGORY_MAP["Network"] == "Network"
        assert CATEGORY_MAP["WebBrowser"] == "Network"
        assert CATEGORY_MAP["Email"] == "Network"

    def test_productivity_categories(self):
        assert CATEGORY_MAP["Office"] == "Productivity"
        assert CATEGORY_MAP["Spreadsheet"] == "Productivity"
        assert CATEGORY_MAP["WordProcessor"] == "Productivity"

    def test_system_categories(self):
        assert CATEGORY_MAP["System"] == "System"
        assert CATEGORY_MAP["Settings"] == "System"

    def test_games_category(self):
        assert CATEGORY_MAP["Game"] == "Games"

    def test_graphics_category(self):
        assert CATEGORY_MAP["Graphics"] == "Graphics"

    def test_education_category(self):
        assert CATEGORY_MAP["Education"] == "Education"


class TestLinuxDesktopEntry:
    """Test the LinuxDesktopEntry dataclass."""

    def test_create_entry(self):
        entry = LinuxDesktopEntry(
            name="Test App",
            exec_command="/usr/bin/test",
            icon="test-icon",
            categories=["Utility"],
        )
        assert entry.name == "Test App"
        assert entry.exec_command == "/usr/bin/test"
        assert entry.icon == "test-icon"
        assert entry.categories == ["Utility"]
        assert entry.comment == ""
        assert entry.terminal is False
        assert entry.path == ""

    def test_entry_defaults(self):
        entry = LinuxDesktopEntry(
            name="App",
            exec_command="cmd",
            icon="",
            categories=[],
        )
        assert entry.comment == ""
        assert entry.terminal is False
        assert entry.path == ""
        assert entry.desktop_file_path == ""


class TestLinuxProgramLoaderSingleton:
    """Test the singleton pattern."""

    def test_get_instance_returns_same_object(self):
        loader1 = LinuxProgramLoader.get_instance()
        loader2 = LinuxProgramLoader.get_instance()
        assert loader1 is loader2

    def test_is_available_returns_false_on_windows(self):
        with patch("stormos.services.linux_program_loader.get_platform") as mock_platform:
            mock_platform.return_value = "windows"
            loader = LinuxProgramLoader.get_instance()
            assert loader.is_available() is False

    def test_is_available_returns_true_on_linux(self):
        with patch("stormos.services.linux_program_loader.get_platform") as mock_platform:
            mock_platform.return_value = "linux"
            loader = LinuxProgramLoader.get_instance()
            assert loader.is_available() is True


class TestDesktopFileParsing:
    """Test .desktop file parsing."""

    def test_parse_valid_desktop_file(self, tmp_path):
        desktop_file = tmp_path / "firefox.desktop"
        desktop_file.write_text(VALID_DESKTOP, encoding="utf-8")

        loader = LinuxProgramLoader.get_instance()
        entry = loader._parse_desktop_file(desktop_file)

        assert entry is not None
        assert entry.name == "Firefox Web Browser"
        assert entry.exec_command == "firefox %u"
        assert entry.icon == "firefox"
        assert entry.comment == "Browse the World Wide Web"
        assert entry.categories == ["Network", "WebBrowser"]
        assert entry.terminal is False

    def test_parse_minimal_desktop_file(self, tmp_path):
        desktop_file = tmp_path / "test.desktop"
        desktop_file.write_text(MINIMAL_DESKTOP, encoding="utf-8")

        loader = LinuxProgramLoader.get_instance()
        entry = loader._parse_desktop_file(desktop_file)

        assert entry is not None
        assert entry.name == "Test App"
        assert entry.exec_command == "/usr/bin/test-app"
        assert entry.icon == ""
        assert entry.categories == []

    def test_parse_invalid_no_section(self, tmp_path):
        desktop_file = tmp_path / "broken.desktop"
        desktop_file.write_text(INVALID_NO_SECTION, encoding="utf-8")

        loader = LinuxProgramLoader.get_instance()
        entry = loader._parse_desktop_file(desktop_file)

        assert entry is None

    def test_parse_invalid_type(self, tmp_path):
        desktop_file = tmp_path / "link.desktop"
        desktop_file.write_text(INVALID_TYPE, encoding="utf-8")

        loader = LinuxProgramLoader.get_instance()
        entry = loader._parse_desktop_file(desktop_file)

        assert entry is None

    def test_parse_invalid_no_exec(self, tmp_path):
        desktop_file = tmp_path / "noexec.desktop"
        desktop_file.write_text(INVALID_NO_EXEC, encoding="utf-8")

        loader = LinuxProgramLoader.get_instance()
        entry = loader._parse_desktop_file(desktop_file)

        assert entry is None

    def test_parse_terminal_app(self, tmp_path):
        desktop_file = tmp_path / "terminal.desktop"
        desktop_file.write_text(TERMINAL_DESKTOP, encoding="utf-8")

        loader = LinuxProgramLoader.get_instance()
        entry = loader._parse_desktop_file(desktop_file)

        assert entry is not None
        assert entry.terminal is True
        assert entry.name == "Terminal Emulator"

    def test_parse_field_method(self):
        loader = LinuxProgramLoader.get_instance()

        content = """[Desktop Entry]
Name=Test
Exec=/usr/bin/test
Comment=A comment
"""
        assert loader._parse_field(content, "Name", "") == "Test"
        assert loader._parse_field(content, "Exec", "") == "/usr/bin/test"
        assert loader._parse_field(content, "Comment", "") == "A comment"
        assert loader._parse_field(content, "Missing", "default") == "default"

    def test_parse_field_ignores_other_sections(self):
        loader = LinuxProgramLoader.get_instance()

        content = """[Desktop Entry]
Name=Main Name
Exec=/usr/bin/main

[Desktop Action test]
Name=Action Name
"""
        assert loader._parse_field(content, "Name", "") == "Main Name"


class TestScan:
    """Test scanning directories for .desktop files."""

    def test_scan_returns_zero_on_windows(self):
        with patch("stormos.services.linux_program_loader.get_platform") as mock_platform:
            mock_platform.return_value = "windows"
            loader = LinuxProgramLoader.get_instance()
            count = loader.scan()
            assert count == 0

    def test_scan_empty_directory(self, tmp_path):
        with patch("stormos.services.linux_program_loader.get_platform") as mock_platform:
            mock_platform.return_value = "linux"
            loader = LinuxProgramLoader.get_instance()
            count = loader.scan(dirs=[str(tmp_path)])
            assert count == 0

    def test_scan_finds_desktop_files(self, tmp_path):
        # Create a valid .desktop file
        desktop_file = tmp_path / "test.desktop"
        desktop_file.write_text(VALID_DESKTOP, encoding="utf-8")

        with patch("stormos.services.linux_program_loader.get_platform") as mock_platform:
            mock_platform.return_value = "linux"
            loader = LinuxProgramLoader.get_instance()
            count = loader.scan(dirs=[str(tmp_path)])
            assert count == 1

    def test_scan_skips_invalid_files(self, tmp_path):
        # Create invalid .desktop files
        (tmp_path / "invalid1.desktop").write_text(INVALID_NO_SECTION, encoding="utf-8")
        (tmp_path / "invalid2.desktop").write_text(INVALID_TYPE, encoding="utf-8")

        with patch("stormos.services.linux_program_loader.get_platform") as mock_platform:
            mock_platform.return_value = "linux"
            loader = LinuxProgramLoader.get_instance()
            count = loader.scan(dirs=[str(tmp_path)])
            assert count == 0

    def test_scan_multiple_files(self, tmp_path):
        # Create multiple valid .desktop files
        (tmp_path / "app1.desktop").write_text(VALID_DESKTOP, encoding="utf-8")
        (tmp_path / "app2.desktop").write_text(MINIMAL_DESKTOP, encoding="utf-8")
        (tmp_path / "app3.desktop").write_text(TERMINAL_DESKTOP, encoding="utf-8")

        with patch("stormos.services.linux_program_loader.get_platform") as mock_platform:
            mock_platform.return_value = "linux"
            loader = LinuxProgramLoader.get_instance()
            count = loader.scan(dirs=[str(tmp_path)])
            assert count == 3


class TestAppMetadataCreation:
    """Test AppMetadata wrapper creation."""

    def test_create_metadata_basic(self):
        loader = LinuxProgramLoader.get_instance()
        entry = LinuxDesktopEntry(
            name="Test App",
            exec_command="/usr/bin/test",
            icon="test-icon",
            categories=["Utility"],
        )
        metadata = loader._create_app_metadata("test", entry)

        assert metadata is not None
        assert metadata.id == "linux.test"
        assert metadata.name == "Test App"
        assert metadata.is_builtin is False
        assert metadata.factory is not None

    def test_create_metadata_maps_category(self):
        loader = LinuxProgramLoader.get_instance()
        entry = LinuxDesktopEntry(
            name="Firefox",
            exec_command="firefox",
            icon="firefox",
            categories=["Network", "WebBrowser"],
        )
        metadata = loader._create_app_metadata("firefox", entry)

        assert metadata is not None
        assert metadata.category == "Network"

    def test_create_metadata_uses_emoji_for_file_icon(self):
        loader = LinuxProgramLoader.get_instance()
        entry = LinuxDesktopEntry(
            name="Test App",
            exec_command="/usr/bin/test",
            icon="/usr/share/icons/test.png",
            categories=["Utility"],
        )
        metadata = loader._create_app_metadata("test", entry)

        assert metadata is not None
        # File path icons should be replaced with category emoji
        assert metadata.icon == "🔧"  # Utilities emoji

    def test_create_metadata_uses_default_emoji_for_empty_icon(self):
        loader = LinuxProgramLoader.get_instance()
        entry = LinuxDesktopEntry(
            name="Test App",
            exec_command="/usr/bin/test",
            icon="",
            categories=[],
        )
        metadata = loader._create_app_metadata("test", entry)

        assert metadata is not None
        assert metadata.icon == "📦"

    def test_create_metadata_includes_comment_in_description(self):
        loader = LinuxProgramLoader.get_instance()
        entry = LinuxDesktopEntry(
            name="Test App",
            exec_command="/usr/bin/test",
            icon="",
            categories=["Utility"],
            comment="A test application",
        )
        metadata = loader._create_app_metadata("test", entry)

        assert metadata is not None
        assert "A test application" in metadata.description

    def test_create_metadata_uses_name_in_description_if_no_comment(self):
        loader = LinuxProgramLoader.get_instance()
        entry = LinuxDesktopEntry(
            name="Test App",
            exec_command="/usr/bin/test",
            icon="",
            categories=[],
        )
        metadata = loader._create_app_metadata("test", entry)

        assert metadata is not None
        assert "Test App" in metadata.description


class TestLoadToRegistry:
    """Test loading programs into AppRegistry."""

    def test_load_to_registry_returns_zero_on_windows(self):
        with patch("stormos.services.linux_program_loader.get_platform") as mock_platform:
            mock_platform.return_value = "windows"
            loader = LinuxProgramLoader.get_instance()
            count = loader.load_to_registry()
            assert count == 0

    def test_load_to_registry_registers_programs(self, tmp_path):
        # Create a valid .desktop file
        (tmp_path / "test.desktop").write_text(VALID_DESKTOP, encoding="utf-8")

        with patch("stormos.services.linux_program_loader.get_platform") as mock_platform:
            mock_platform.return_value = "linux"
            loader = LinuxProgramLoader.get_instance()
            loader.scan(dirs=[str(tmp_path)])
            count = loader.load_to_registry()

            assert count == 1
            registry = AppRegistry.get_instance()
            app = registry.get_app("linux.test")
            assert app is not None
            assert app.name == "Firefox Web Browser"

    def test_load_to_registry_unregisters_previous(self, tmp_path):
        with patch("stormos.services.linux_program_loader.get_platform") as mock_platform:
            mock_platform.return_value = "linux"
            loader = LinuxProgramLoader.get_instance()

            # First load
            (tmp_path / "app1.desktop").write_text(VALID_DESKTOP, encoding="utf-8")
            loader.scan(dirs=[str(tmp_path)])
            loader.load_to_registry()

            # Second load with different file
            loader._entries.clear()
            loader._loaded = False
            (tmp_path / "app1.desktop").unlink()
            (tmp_path / "app2.desktop").write_text(MINIMAL_DESKTOP, encoding="utf-8")
            loader.scan(dirs=[str(tmp_path)])
            loader.load_to_registry()

            registry = AppRegistry.get_instance()
            # Old app should be unregistered
            assert registry.get_app("linux.app1") is None
            # New app should be registered
            assert registry.get_app("linux.app2") is not None


class TestGetProgramList:
    """Test get_program_list method."""

    def test_get_program_list_empty(self):
        with patch("stormos.services.linux_program_loader.get_platform") as mock_platform:
            mock_platform.return_value = "linux"
            loader = LinuxProgramLoader.get_instance()
            programs = loader.get_program_list()
            assert programs == []

    def test_get_program_list_returns_programs(self, tmp_path):
        (tmp_path / "test.desktop").write_text(VALID_DESKTOP, encoding="utf-8")

        with patch("stormos.services.linux_program_loader.get_platform") as mock_platform:
            mock_platform.return_value = "linux"
            loader = LinuxProgramLoader.get_instance()
            loader.scan(dirs=[str(tmp_path)])
            programs = loader.get_program_list()

            assert len(programs) == 1
            prog = programs[0]
            assert prog["id"] == "linux.test"
            assert prog["name"] == "Firefox Web Browser"
            assert prog["exec"] == "firefox %u"


class TestLaunchProgram:
    """Test program launching."""

    def test_launch_nonexistent_program(self):
        loader = LinuxProgramLoader.get_instance()
        result = loader.launch_program("nonexistent")
        assert result is False

    def test_launch_removes_placeholders(self):
        loader = LinuxProgramLoader.get_instance()
        entry = LinuxDesktopEntry(
            name="Test",
            exec_command="firefox %u %F",
            icon="",
            categories=[],
        )
        loader._entries["test"] = entry
        loader._loaded = True

        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = MagicMock()
            result = loader.launch_program("test")
            assert result is True
            # Check that placeholders were removed
            call_args = mock_popen.call_args[0][0]
            assert "%u" not in call_args
            assert "%F" not in call_args


class TestDesktopDirs:
    """Test desktop directory constants."""

    def test_desktop_dirs_not_empty(self):
        assert len(DESKTOP_DIRS) > 0

    def test_desktop_dirs_contains_standard_path(self):
        assert "/usr/share/applications" in DESKTOP_DIRS
