"""Social-media photo CSV/XLSX -> YY/MM/DD foldered copies.

Mirrors SocialMediaPhotoFileManager.java. Input is a CSV or .xlsx file (same
column layout). Columns (after header):
    2: fileName
    3: fileExtension
    5: sourcePath
    8: datePosted  (e.g. "2016-03-22")
Rows with an empty sourcePath are skipped.
Source: <drive><sourcePath><fileName>.<ext>
Dest:   <output>/<YY><MM>/<DD>/<fileName>.<ext>  (datePosted[2:4], [5:7], [8:10])
"""
from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple

from .common import Timer, format_elapsed_ms, format_size, load_table


@dataclass
class CopyResult:
    successes: int = 0
    failures: int = 0
    total_bytes: int = 0
    failure_msgs: List[str] = None  # type: ignore


def build_paths(csv_path: str, photo_drive: str, output_path: str) -> List[Tuple[str, str]]:
    plan: List[Tuple[str, str]] = []
    rows = load_table(csv_path)
    if not rows:
        return plan
    for tokens in rows[1:]:
        if len(tokens) < 9:
            continue
        source_path = tokens[5]
        date_posted = tokens[8]
        file_name = tokens[2]
        file_ext = tokens[3]
        if not source_path:
            continue
        src = f"{photo_drive}{source_path}{file_name}.{file_ext}"
        dest_dir = f"{output_path}/{date_posted[2:4]}{date_posted[5:7]}/{date_posted[8:10]}"
        dst = f"{dest_dir}/{file_name}.{file_ext}"
        plan.append((src, dst))
    plan.sort(key=lambda x: x[0])
    return plan


def execute(
    plan: List[Tuple[str, str]],
    log: Optional[Callable[[str], None]] = None,
) -> CopyResult:
    log = log or (lambda s: print(s))
    result = CopyResult(failure_msgs=[])
    with Timer() as t:
        for src, dst in plan:
            try:
                result.total_bytes += os.path.getsize(src)
            except OSError:
                pass
            parent = os.path.dirname(dst)
            if parent and not os.path.isdir(parent):
                os.makedirs(parent, exist_ok=True)
            label = f"{src} -> {dst}"
            try:
                shutil.copyfile(src, dst)
                log(f"Success: {label}")
                result.successes += 1
            except OSError:
                log(f"Failure: {label}")
                result.failures += 1
                result.failure_msgs.append(label)
    size, unit = format_size(result.total_bytes)
    log("")
    log(f"{result.successes} successes")
    log(f"{result.failures} failures")
    log(f"{size:.2f} {unit}")
    log(format_elapsed_ms(t.ms))
    if result.failures:
        log("")
        log("Failures:")
        for m in result.failure_msgs:
            log(m)
    return result
