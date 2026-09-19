"""Photo gallery CSV/XLSX -> date-foldered copies - mirrors PhotoGalleryFileManager.java.

Input is a CSV or .xlsx file (same column layout). Columns (0-indexed, after
the header row):
    1: originalPath  (e.g. "/2016/03/22/")
    2: dateTaken     (e.g. "2016-03-22")
    3: fileName
    4: fileExtension
Source: <drive><originalPath>/<fileName>.<ext>
Dest:   <output>/<dateTaken>/<fileName>.<ext>
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
        if len(tokens) < 5:
            continue
        original_path, date_taken, file_name, file_ext = tokens[1:5]
        src = f"{photo_drive}{original_path}/{file_name}.{file_ext}"
        dst = f"{output_path}/{date_taken}/{file_name}.{file_ext}"
        plan.append((src, dst))
    # TreeMap equivalent: sort by source path.
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
