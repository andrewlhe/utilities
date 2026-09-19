"""MD5 checksum of a file, byte-for-byte compatible with MD5Checksum.java."""
from __future__ import annotations

import hashlib


def create_checksum(filename: str) -> bytes:
    """Return the raw MD5 digest bytes of *filename*."""
    md5 = hashlib.md5()
    with open(filename, "rb") as f:
        while True:
            chunk = f.read(1024)
            if not chunk:
                break
            md5.update(chunk)
    return md5.digest()


def get_md5_checksum(filename: str) -> str:
    """Return the lowercase hex MD5 of *filename*."""
    return create_checksum(filename).hex()
