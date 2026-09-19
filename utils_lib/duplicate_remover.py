"""Duplicate file remover - mirrors FileDuplicateRemover.java.

Walks a directory (optionally subfolders), hashes every file with MD5, and
keeps the *first* occurrence of each hash. Later duplicates are listed for
removal. A confirm step precedes deletion.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Set, Tuple

from .common import format_size, iter_files
from .md5_checksum import get_md5_checksum


@dataclass
class DuplicateResult:
    duplicates: List[str] = field(default_factory=list)
    bytes_reclaimable: int = 0
    seen: int = 0


def find_duplicates(
    directory: str,
    include_subfolders: bool = True,
    log: Optional[Callable[[str], None]] = None,
) -> DuplicateResult:
    """Scan *directory* and return files whose content duplicates an earlier file."""
    out = DuplicateResult()
    seen_hashes: Set[str] = set()
    log = log or (lambda s: None)
    for path in iter_files(directory, include_subfolders):
        log(path)
        try:
            checksum = get_md5_checksum(path)
        except OSError:
            continue
        log(checksum)
        out.seen += 1
        if checksum in seen_hashes:
            out.duplicates.append(path)
            try:
                out.bytes_reclaimable += os.path.getsize(path)
            except OSError:
                pass
        else:
            seen_hashes.add(checksum)
    # Keep order deterministic (TreeSet equivalent: sorted by absolute path).
    out.duplicates.sort()
    return out


def format_report(result: DuplicateResult) -> str:
    lines: List[str] = [""]
    if not result.duplicates:
        lines.append("No files to be removed.")
    else:
        lines.append("Files to be removed:")
        for p in result.duplicates:
            lines.append(p)
        size, unit = format_size(result.bytes_reclaimable)
        lines.append(f"({len(result.duplicates)} files, {size} {unit})")
    return "\n".join(lines)


def remove_duplicates(duplicates: List[str]) -> None:
    for p in duplicates:
        try:
            os.remove(p)
        except OSError:
            pass
