import base64
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class EncryptionError(Exception):
    """Raised when encryption/decryption fails."""


def _get_key(password: str, salt: bytes) -> bytes:
    """Derive a key from password and salt."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))


def encrypt_value(value: str, master_key: str) -> str:
    """Encrypt a value using a master key."""
    if not value:
        return ""
    salt = os.urandom(16)
    key = _get_key(master_key, salt)
    f = Fernet(key)
    encrypted = f.encrypt(value.encode())
    # Store salt + encrypted data
    return base64.urlsafe_b64encode(salt + encrypted).decode()


def decrypt_value(encrypted_value: str, master_key: str) -> str:
    """Decrypt a value using a master key."""
    if not encrypted_value:
        return ""
    try:
        data = base64.urlsafe_b64decode(encrypted_value.encode())
        salt = data[:16]
        encrypted = data[16:]
        key = _get_key(master_key, salt)
        f = Fernet(key)
        return f.decrypt(encrypted).decode()
    except Exception as e:
        raise EncryptionError(f"Decryption failed: {e}") from e


# For local storage, use a fixed master key derived from machine-specific info
# In production, this should be user-provided or stored securely
def get_master_key() -> str:
    """Get a master key for encryption. In a real app, this should be more secure."""
    # For demo purposes, use a fixed key. In production, use keyring or user input.
    return "taskpilot-local-key-2024"