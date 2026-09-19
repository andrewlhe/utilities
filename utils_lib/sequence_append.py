"""Append the head run of a camera sequence to the tail.

Finds a contiguous head run, a jump, then a contiguous tail run that reaches
the last file. Renames the head-run files so they continue after the tail run
(numbered with the original digit width). Uses a temp folder to avoid
collisions. Mirrors FileSequenceAppendHeadToEnd.java.
"""
from __future__ import annotations

import os
from typing import Callable, List, Optional, Tuple

from .common import Timer, format_elapsed_ms
from .sequence_common import get_components_for_file_name, group_by_extension


def get_bounds_for_file_sequence(file_numbers: List[int]) -> Optional[List[int]]:
    """Return [headLower, headUpper, tailLower, tailUpper] or None if no valid split.

    The Java logic walks the sorted numbers once:
      * start with the first number as the head run.
      * when a gap appears, open the tail run at the current number.
      * when a second gap appears, give up.
      * require the tail run to extend to the very last number.
    """
    if not file_numbers:
        return None

    head_lower = head_upper = file_numbers[0]
    head_found = False
    tail_lower = -1
    tail_upper = -1
    tail_found = False

    for i in range(1, len(file_numbers)):
        if file_numbers[i] - file_numbers[i - 1] == 1:
            if not head_found:
                head_upper = file_numbers[i]
            else:
                tail_upper = file_numbers[i]
        else:
            if not head_found:
                head_found = True
                tail_lower = file_numbers[i]
                tail_upper = file_numbers[i]
            else:
                tail_found = True
                break

    if tail_upper != file_numbers[-1]:
        return None
    bounds = [head_lower, head_upper, tail_lower, tail_upper]
    if any(b < 0 for b in bounds):
        return None
    return bounds


def build_append_plan(source_dir: str) -> List[Tuple[str, str]]:
    """Return [(src, dst_name_in_temp)] that moves the head run to the tail."""
    temp_dir = os.path.join(source_dir, "temp")
    plan: List[Tuple[str, str]] = []
    for _ext, files in group_by_extension(source_dir).items():
        try:
            numbers = [
                int(get_components_for_file_name(os.path.basename(p))[1]) for p in files
            ]
        except ValueError:
            continue
        bounds = get_bounds_for_file_sequence(numbers)
        if bounds is None:
            continue
        head_lower, head_upper, _tail_lower, tail_upper = bounds
        for src in files:
            prefix, number_str, suffix = get_components_for_file_name(os.path.basename(src))
            file_number = int(number_str)
            if file_number < head_lower or file_number > head_upper:
                continue
            number_width = len(number_str)
            new_number = tail_upper + file_number - head_lower + 1
            new_name = f"{prefix}{new_number:0{number_width}d}{suffix}"
            plan.append((src, os.path.join(temp_dir, new_name)))
    plan.sort()
    return plan


def execute_append_plan(
    source_dir: str,
    plan: List[Tuple[str, str]],
    log: Optional[Callable[[str], None]] = None,
) -> Tuple[int, int, List[str]]:
    log = log or (lambda s: None)
    temp_dir = os.path.join(source_dir, "temp")
    os.makedirs(temp_dir, exist_ok=True)
    successes = 0
    failures = 0
    failure_msgs: List[str] = []
    with Timer() as t:
        n = len(plan)
        for i, (src, dst) in enumerate(plan, start=1):
            label = f"{os.path.basename(src)} -> {os.path.basename(dst)} ({i}/{n})"
            try:
                os.rename(src, dst)
                log(f"Success: {label}")
                successes += 1
            except OSError as e:
                log(f"Failure: {label} | {e}")
                failure_msgs.append(label)
                failures += 1
        log("")
        log("Finalizing...")
        if os.path.isdir(temp_dir):
            for name in sorted(os.listdir(temp_dir)):
                src = os.path.join(temp_dir, name)
                dst = os.path.join(source_dir, name)
                try:
                    os.rename(src, dst)
                except OSError:
                    pass
            try:
                os.rmdir(temp_dir)
            except OSError:
                log("")
                log("Unable to remove the temp directory.")
                log("Please remove manually.")
    log("")
    log(f"{successes} successes")
    log(f"{failures} failures")
    log(format_elapsed_ms(t.ms))
    if failures:
        log("")
        log("Failures:")
        for m in failure_msgs:
            log(m)
    log("")
    log("Completed")
    return successes, failures, failure_msgs
