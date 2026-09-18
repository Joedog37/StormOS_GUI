"""StormOS App Package Installer and Validation Service.

Validates application packages, enforces security baselines (no path traversal,
no auto-executing unvetted scripts, format verification), and installs app packages
into user sandboxes or system apps directory.
"""

import json
import re
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from stormos.apps.registry import AppMetadata, AppRegistry
from stormos.core.paths import APPS_DIR, USERS_DIR
from stormos.core.security import sanitize_filename, validate_username
from stormos.services.user_manager import UserProfile


MAX_PACKAGE_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB max package size
BLOCKED_EXTENSIONS = {".exe", ".dll", ".so", ".dylib", ".bat", ".cmd", ".vbs", ".ps1", ".sh"}
APP_ID_PATTERN = re.compile(r"^[a-z0-9_-]{3,32}$")


@dataclass
class InstalledAppInfo:
    """Information about an installed application package."""
    id: str
    name: str
    version: str
    description: str
    icon: str
    category: str
    author: str
    install_path: str
    is_builtin: bool = False


class AppInstallerService:
    """Service to safely validate, install, list, and uninstall StormOS app packages."""

    def __init__(self, apps_dir: Optional[Path] = None):
        self.apps_dir = apps_dir or APPS_DIR
        self.apps_dir.mkdir(parents=True, exist_ok=True)

    def validate_manifest(self, manifest: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate package manifest fields and safety constraints."""
        if not isinstance(manifest, dict):
            return False, "Invalid manifest: expected JSON object"

        app_id = manifest.get("id", "").strip().lower()
        if not app_id or not APP_ID_PATTERN.match(app_id):
            return False, "Invalid app 'id': must be 3-32 lowercase alphanumeric characters, dashes, or underscores"

        name = manifest.get("name", "").strip()
        if not name or len(name) > 64:
            return False, "Invalid 'name': must be 1-64 characters"

        version = manifest.get("version", "").strip()
        if not version or len(version) > 20:
            return False, "Invalid 'version': must be specified (up to 20 chars)"

        description = manifest.get("description", "")
        if len(description) > 500:
            return False, "Description exceeds 500 characters"

        return True, ""

    def validate_package_archive(self, archive_path: Path) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Validate a .stormapp (zip) archive for integrity and path traversal risks."""
        if not archive_path.exists():
            return False, f"Package file not found: {archive_path}", None

        file_size = archive_path.stat().st_size
        if file_size > MAX_PACKAGE_SIZE_BYTES:
            return False, f"Package exceeds maximum allowed size ({MAX_PACKAGE_SIZE_BYTES // (1024 * 1024)} MB)", None

        if not zipfile.is_zipfile(archive_path):
            return False, "Package is not a valid zip archive (.stormapp)", None

        total_uncompressed = 0
        manifest_data = None

        with zipfile.ZipFile(archive_path, "r") as zf:
            namelist = zf.namelist()

            if "manifest.json" not in namelist:
                return False, "Missing required 'manifest.json' in package root", None

            for name in namelist:
                # Security check 1: Path traversal protection
                if name.startswith("/") or name.startswith("\\") or ".." in name:
                    return False, f"Security violation: unsafe path '{name}' detected in package", None

                # Security check 2: Disallowed binary / executable formats
                lower_name = name.lower()
                for ext in BLOCKED_EXTENSIONS:
                    if lower_name.endswith(ext):
                        return False, f"Security baseline: executable script/binary '{ext}' not allowed in app package", None

                # Security check 3: Zip bomb protection
                info = zf.getinfo(name)
                total_uncompressed += info.file_size
                if total_uncompressed > MAX_PACKAGE_SIZE_BYTES * 2:
                    return False, "Uncompressed package contents exceed safety threshold", None

            # Read and validate manifest
            try:
                manifest_bytes = zf.read("manifest.json")
                manifest_data = json.loads(manifest_bytes.decode("utf-8"))
            except Exception as e:
                return False, f"Failed to parse manifest.json: {e}", None

        valid, err = self.validate_manifest(manifest_data)
        if not valid:
            return False, err, None

        return True, "Valid package", manifest_data

    def install_from_manifest_and_files(
        self,
        manifest: Dict[str, Any],
        files: Optional[Dict[str, str]] = None,
        user: Optional[UserProfile] = None,
    ) -> Tuple[bool, str]:
        """Install an application directly from a manifest and file mapping."""
        valid, err = self.validate_manifest(manifest)
        if not valid:
            return False, err

        app_id = manifest["id"].lower()
        target_dir = self._get_app_install_dir(app_id, user)
        target_dir.mkdir(parents=True, exist_ok=True)

        manifest_path = target_dir / "manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        if files:
            for rel_path, content in files.items():
                safe_name = sanitize_filename(rel_path)
                file_dest = target_dir / safe_name
                with open(file_dest, "w", encoding="utf-8") as f:
                    f.write(content)

        # Register with AppRegistry
        self._register_in_app_registry(manifest, target_dir)
        return True, f"Successfully installed '{manifest['name']}'"

    def install_package(self, archive_path: Path, user: Optional[UserProfile] = None) -> Tuple[bool, str]:
        """Safely extract and install a .stormapp package."""
        valid, msg, manifest = self.validate_package_archive(archive_path)
        if not valid or manifest is None:
            return False, msg

        app_id = manifest["id"].lower()
        target_dir = self._get_app_install_dir(app_id, user)
        target_dir.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(archive_path, "r") as zf:
            for name in zf.namelist():
                # Skip directories and sanitize relative parts
                if name.endswith("/"):
                    continue
                safe_rel = "/".join(sanitize_filename(part) for part in name.split("/") if part)
                dest_file = target_dir / safe_rel
                dest_file.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(name) as source, open(dest_file, "wb") as target:
                    shutil.copyfileobj(source, target)

        self._register_in_app_registry(manifest, target_dir)
        return True, f"Successfully installed '{manifest['name']}'"

    def uninstall_app(self, app_id: str, user: Optional[UserProfile] = None) -> Tuple[bool, str]:
        """Safely uninstall an app by app_id."""
        app_id = app_id.lower()
        target_dir = self._get_app_install_dir(app_id, user)

        if not target_dir.exists():
            # Check global apps dir
            global_dir = self.apps_dir / app_id
            if global_dir.exists():
                target_dir = global_dir
            else:
                return False, f"App '{app_id}' is not installed."

        try:
            shutil.rmtree(target_dir)
            AppRegistry.get_instance().unregister(app_id)
            return True, f"Successfully uninstalled '{app_id}'"
        except Exception as e:
            return False, f"Failed to uninstall '{app_id}': {e}"

    def list_installed_apps(self, user: Optional[UserProfile] = None) -> List[InstalledAppInfo]:
        """List all installed third-party apps."""
        results = []
        search_dirs = [self.apps_dir]
        if user and user.username:
            user_apps_dir = USERS_DIR / user.username / "apps"
            if user_apps_dir.exists():
                search_dirs.append(user_apps_dir)

        seen_ids = set()
        for base_dir in search_dirs:
            if not base_dir.exists():
                continue
            for item in base_dir.iterdir():
                if item.is_dir() and (item / "manifest.json").exists():
                    try:
                        with open(item / "manifest.json", "r", encoding="utf-8") as f:
                            data = json.loads(f.read())
                        app_id = data.get("id", item.name).lower()
                        if app_id in seen_ids:
                            continue
                        seen_ids.add(app_id)
                        results.append(
                            InstalledAppInfo(
                                id=app_id,
                                name=data.get("name", item.name),
                                version=data.get("version", "1.0.0"),
                                description=data.get("description", ""),
                                icon=data.get("icon", "📦"),
                                category=data.get("category", "Installed"),
                                author=data.get("author", "Unknown"),
                                install_path=str(item),
                                is_builtin=False,
                            )
                        )
                    except Exception:
                        pass
        return results

    def _get_app_install_dir(self, app_id: str, user: Optional[UserProfile]) -> Path:
        if user and user.username:
            return USERS_DIR / user.username / "apps" / app_id
        return self.apps_dir / app_id

    def _register_in_app_registry(self, manifest: Dict[str, Any], app_path: Path):
        """Register the installed app package into the central AppRegistry."""
        app_id = manifest["id"].lower()
        name = manifest["name"]
        description = manifest.get("description", "")
        icon = manifest.get("icon", "📦")
        category = manifest.get("category", "Custom")

        def _make_factory(m=manifest, p=app_path):
            def _create(current_user=None, parent=None):
                from PySide6.QtWidgets import QLabel, QTextEdit, QVBoxLayout, QWidget
                widget = QWidget(parent)
                layout = QVBoxLayout(widget)
                layout.setContentsMargins(20, 20, 20, 20)
                layout.setSpacing(12)

                header = QLabel(f"{m.get('icon', '📦')} {m.get('name')}")
                header.setStyleSheet("font-size: 18px; font-weight: bold; color: #38C9FF;")
                layout.addWidget(header)

                desc = QLabel(f"Version {m.get('version', '1.0')} • By {m.get('author', 'Author')}\n{m.get('description', '')}")
                desc.setStyleSheet("color: #A9BBD4; font-size: 12px;")
                layout.addWidget(desc)

                # Check if there is README or content
                readme = p / "README.md"
                content_text = f"Installed application at:\n{p}\n\nManifest Details:\n{json.dumps(m, indent=2)}"
                if readme.exists():
                    try:
                        content_text = readme.read_text(encoding="utf-8")
                    except Exception:
                        pass

                body = QTextEdit()
                body.setPlainText(content_text)
                body.setReadOnly(True)
                body.setStyleSheet("background-color: #101A31; color: #EFF7FF; border: 1px solid #304567; border-radius: 8px; padding: 10px;")
                layout.addWidget(body)
                return widget
            return _create

        metadata = AppMetadata(
            id=app_id,
            name=name,
            description=description,
            icon=icon,
            category=category,
            is_builtin=False,
            factory=_make_factory(),
        )
        AppRegistry.get_instance().register(metadata)
