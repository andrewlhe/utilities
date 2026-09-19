"""Build a CSV of posted photos from date-foldered directories.

Mirrors PostedPhotoProcessor.java. Each immediate subdirectory whose name is
YYMMDD (e.g. "160322") is treated as a posting date (2016-03-22). Every
recognised image inside it is emitted as `datePosted,fileName,extension`.
"""
from __future__ import annotations

import os
from typing import Iterable, List, Set

RECOGNIZED_EXTENSIONS: Set[str] = {"jpg", "jpeg", "png", "tif", "tiff"}


def build_csv(photo_directory: str) -> List[str]:
    rows: List[str] = []
    try:
        entries = sorted(os.listdir(photo_directory))
    except OSError:
        return rows
    for name in entries:
        d = os.path.join(photo_directory, name)
        if not os.path.isdir(d):
            continue
        # Directory name YYMMDD -> 20YY-MM-DD.
        if len(name) < 6 or not name[:6].isdigit():
            continue
        date_posted = f"20{name[0:2]}-{name[2:4]}-{name[4:6]}"
        for file_name in sorted(os.listdir(d)):
            full = os.path.join(d, file_name)
            if not os.path.isfile(full):
                continue
            idx = file_name.rfind(".")
            if idx < 0:
                continue
            base = file_name[:idx]
            ext = file_name[idx + 1:]
            if ext.lower() not in RECOGNIZED_EXTENSIONS:
                continue
            rows.append(f"{date_posted},{base},{ext}")
    return rows


def write_csv(photo_directory: str, output_file: str) -> int:
    rows = build_csv(photo_directory)
    with open(output_file, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(r + "\n")
    return len(rows)
