"""Camera-file sequence helpers shared by renumber / append."""
from __future__ import annotations

import os
import re
from typing import Dict, List, Optional, Tuple

# Extensions recognized by the original tools (case-insensitive match after upper-casing).
FILE_EXTENSIONS = ["ARW", "CR2", "DNG", "NEF", "XMP", "JPG", "JPEG", "TIF", "TIFF", "HEIF", "HEIC"]

_SUFFIX_RE = re.compile(r"(\.\w+)$")
_NUMBER_RE = re.compile(r"(\d+)$")
_ANY_NUMBER_RE = re.compile(r"(\d+)")


def get_file_extension(file_name: str) -> str:
    """Extension after the last dot, or '' if no dot (Java lastIndexOf(46) > 0)."""
    idx = file_name.rfind(".")
    if idx > 0:
        return file_name[idx + 1:]
    return ""


def array_contains(extensions: List[str], element: str) -> bool:
    return element in extensions


def get_components_for_file_name(file_name: str) -> Tuple[str, str, str]:
    """Split a name into (prefix, number, suffix).

    Raises ValueError if the name does not end in an extension or digits.
    Mirrors the Java regex behaviour (suffix: last `.\\w+`; number: trailing digits).
    The number is the *last* group of digits in the stem, so double-extension
    names such as ``IMG_5835.HEIC.heif`` still resolve (number ``5835``).
    """
    m = _SUFFIX_RE.search(file_name)
    if not m:
        raise ValueError(f"no suffix in {file_name!r}")
    suffix = m.group(1)
    stem = file_name[: m.start()]
    nums = list(_ANY_NUMBER_RE.finditer(stem))
    if not nums:
        raise ValueError(f"no trailing digits in {file_name!r}")
    n = nums[-1]
    number = n.group(1)
    prefix = stem[: n.start()]
    return prefix, number, suffix


def group_by_extension(source_dir: str) -> Dict[str, List[str]]:
    """Return {upper_extension: sorted [absolute path, ...]} for recognized files."""
    groups: Dict[str, List[str]] = {}
    for name in sorted(os.listdir(source_dir)):
        if name.startswith("._"):
            continue
        full = os.path.join(source_dir, name)
        if not os.path.isfile(full):
            continue
        ext = get_file_extension(name).upper()
        if ext not in FILE_EXTENSIONS:
            continue
        groups.setdefault(ext, []).append(full)
    for ext in groups:
        groups[ext].sort()
    return groups
