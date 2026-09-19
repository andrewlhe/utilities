"""Batch copy/delete by filename regex - mirrors FileManager.java."""
from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple, Pattern

from .common import Timer, format_elapsed_ms, format_size, iter_files


@dataclass
class Plan:
    """Mapping source_path -> destination_path (None in delete mode)."""
    moves: Dict[str, Optional[str]] = field(default_factory=dict)
    total_bytes: int = 0
    elapsed_ms: int = 0


def _validate_copy_dirs(from_dir: str, to_dir: str) -> Optional[str]:
    """Return an error message if the directories are unsafe, else None."""
    fa = os.path.abspath(from_dir)
    ta = os.path.abspath(to_dir)
    if fa == ta:
        return 'The "From folder" and the "To folder" cannot be the same.'
    # Java used String.contains; we mirror that loose substring test on abspaths.
    if fa in ta:
        return 'The "From folder" cannot contain the "To folder".'
    if ta in fa:
        return 'The "To folder" cannot contain the "From folder".'
    return None


def plan_files(
    mode: str,
    from_dir: str,
    to_dir: Optional[str] = None,
    filename_regex: str = "",
    include_subfolders: bool = True,
) -> Tuple[Optional[str], Plan]:
    """Build the action plan. Returns (error_message, plan)."""
    if mode not in ("copy", "delete"):
        raise ValueError("mode must be 'copy' or 'delete'")

    if mode == "copy":
        if not to_dir:
            return "To folder is required in copy mode.", Plan()
        err = _validate_copy_dirs(from_dir, to_dir)
        if err:
            return err, Plan()

    pattern: Pattern = re.compile(filename_regex or ".+")
    plan = Plan()
    with Timer() as t:
        for src in iter_files(from_dir, include_subfolders):
            name = os.path.basename(src)
            if not pattern.fullmatch(name):
                continue
            dst: Optional[str] = None
            if mode == "copy":
                rel = os.path.relpath(src, os.path.abspath(from_dir))
                dst = os.path.join(os.path.abspath(to_dir), rel)
            plan.moves[src] = dst
            try:
                plan.total_bytes += os.path.getsize(src)
            except OSError:
                pass
    plan.elapsed_ms = t.ms
    return None, plan


def format_plan_report(plan: Plan, mode: str) -> str:
    if not plan.moves:
        return "No files to be copied." if mode == "copy" else "No files to be deleted."
    lines: List[str] = ["Files to be copied:" if mode == "copy" else "Files to be deleted:"]
    for src in sorted(plan.moves):
        dst = plan.moves[src]
        if mode == "copy" and dst is not None:
            lines.append(f"{src} -> {dst}")
        else:
            lines.append(src)
    size, unit = format_size(plan.total_bytes)
    lines.append("")
    lines.append(f"{len(plan.moves)} files, {size:.2f} {unit}")
    lines.append(format_elapsed_ms(plan.elapsed_ms))
    return "\n".join(lines)


def execute_plan(
    plan: Plan,
    mode: str,
    log: Optional[Callable[[str], None]] = None,
) -> Tuple[int, int, List[str]]:
    """Execute the plan. Returns (successes, failures, failure_messages)."""
    log = log or (lambda s: None)
    successes = 0
    failures = 0
    failure_msgs: List[str] = []
    total_bytes = 0
    with Timer() as t:
        n = len(plan.moves)
        for i, (src, dst) in enumerate(sorted(plan.moves), start=1):
            try:
                total_bytes += os.path.getsize(src)
            except OSError:
                pass
            if mode == "copy":
                assert dst is not None
                parent = os.path.dirname(dst)
                if parent and not os.path.isdir(parent):
                    os.makedirs(parent, exist_ok=True)
                label = f"{src} -> {dst} ({i}/{n})"
                try:
                    shutil.copyfile(src, dst)
                    log(f"Success: {label}")
                    successes += 1
                except OSError as e:
                    log(f"Failure: {label}")
                    failure_msgs.append(f"{label} | {e}")
                    failures += 1
            else:
                label = f"{src} ({i}/{n})"
                try:
                    os.remove(src)
                    log(label)
                    successes += 1
                except OSError as e:
                    failure_msgs.append(f"{label} | {e}")
                    failures += 1
    size, unit = format_size(total_bytes)
    log("")
    log(f"{successes} successes")
    log(f"{failures} failures")
    log(f"{size:.2f} {unit}")
    log(format_elapsed_ms(t.ms))
    if failures:
        log("")
        log("")
        log("Failures:")
        for m in failure_msgs:
            log(m)
    return successes, failures, failure_msgs
