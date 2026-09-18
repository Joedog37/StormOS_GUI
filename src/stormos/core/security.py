"""Security utilities for StormOS.

Implements salted hashing, safe comparison, and input sanitization.
"""

import hashlib
import hmac
import re
import secrets
from typing import Tuple

# Password hashing constants
PBKDF2_ALGORITHM = "sha256"
PBKDF2_ITERATIONS = 120_000
SALT_SIZE_BYTES = 32

# Validation patterns
USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9_-]{3,32}$")


def hash_password(password: str, salt_hex: str | None = None) -> Tuple[str, str]:
    """Hash a password with PBKDF2-HMAC-SHA256 and a cryptographically secure salt.

    Returns:
        Tuple of (hash_hex, salt_hex)
    """
    if salt_hex is None:
        salt_bytes = secrets.token_bytes(SALT_SIZE_BYTES)
        salt_hex = salt_bytes.hex()
    else:
        salt_bytes = bytes.fromhex(salt_hex)

    derived_key = hashlib.pbkdf2_hmac(
        hash_name=PBKDF2_ALGORITHM,
        password=password.encode("utf-8"),
        salt=salt_bytes,
        iterations=PBKDF2_ITERATIONS,
    )
    return derived_key.hex(), salt_hex


def verify_password(password: str, stored_hash_hex: str, stored_salt_hex: str) -> bool:
    """Verify a password against stored PBKDF2 hash using timing-safe comparison."""
    if not password or not stored_hash_hex or not stored_salt_hex:
        return False
    try:
        calculated_hash_hex, _ = hash_password(password, salt_hex=stored_salt_hex)
        return hmac.compare_digest(calculated_hash_hex, stored_hash_hex)
    except Exception:
        return False


def validate_username(username: str) -> bool:
    """Check whether a username conforms to security rules.

    Must be 3-32 characters, alphanumeric with underscores and hyphens only.
    Disallows directory traversal characters.
    """
    if not isinstance(username, str):
        return False
    return bool(USERNAME_REGEX.match(username))


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename to avoid path traversal and reserved characters."""
    from pathlib import PurePath

    # Isolate basename to prevent path traversal
    base_name = PurePath(filename).name or filename
    clean = re.sub(r"[^\w\-. ]", "_", base_name)
    clean = clean.strip(". ")
    return clean or "unnamed"
