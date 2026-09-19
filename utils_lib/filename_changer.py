"""Dry-run bulk renaming to DSC%05d.<ext> - mirrors FileNameChanger.java.

Filters files ending with a fixed extension (default "XXX"), skipping those
starting with "._", and prints what the new names *would* be. The Java
original had IS_DRY_RUN = true, so no rename actually happened; this Python
module reproduces that behaviour.
"""
from __future__ import annotations

import os
from typing import List, Tuple


def build_rename_plan(
    old_dir: str,
    file_extension: str = "XXX",
    total_count: int = 10000,
) -> List[Tuple[str, str]]:
    """Return [(old_name, new_name)] sorted by old name.

    The first file becomes DSC10000.<ext> (++count + 9999 with count starting at 0).
    """
    entries: List[str] = []
    try:
        names = sorted(os.listdir(old_dir))
    except OSError:
        return entries
    for name in names:
        if name.startswith("._"):
            continue
        if not name.endswith(file_extension):
            continue
        entries.append(name)
        if len(entries) >= total_count:
            break
    plan: List[Tuple[str, str]] = []
    for count, old_name in enumerate(entries, start=1):
        new_name = f"DSC{count + 9999:05d}.{file_extension}"
        plan.append((old_name, new_name))
    return plan


def print_plan(plan: List[Tuple[str, str]]) -> None:
    for old, new in plan:
        print(f"{old} -> {new}")
