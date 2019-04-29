"""Default configuration files."""

from pathlib import Path

CONFIG = {
    "output_dir": "export",
    "signal_dir": Path.home() / ".config" / "Signal",
    "own_number": None,
    "include_expiring": False,
}

CONFIG_SANITIZER = {
    "output_dir": Path,
    "signal_dir": Path,
    "own_number": lambda x: str(x) if x else None,
    "include_expiring": bool,
}

SQLCIPHER_SETTINGS = {
    "cipher_page_size": 1024,
    "kdf_iter": 64000,
    "cipher_hmac_algorithm": "HMAC_SHA1",
    "cipher_kdf_algorithm": "PBKDF2_HMAC_SHA1",
}
