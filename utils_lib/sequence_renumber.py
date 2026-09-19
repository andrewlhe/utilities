"""Renumber a camera-file sequence - mirrors FileSequenceRenumber.java.

For every recognized extension group, files are processed in sorted order and
renamed to ``<prefix><start + step*i:0N d><origNumberSuffix>``. Note: the Java
original appended the *original number string* rather than the extension as the
third format argument (a latent bug). This Python version reproduces that
behaviour exactly so output matches the original.
"""
from __future__ import annotations

import os
import shutil
from typing import Callable, Dict, List, Optional, Tuple

from .common import Timer, format_elapsed_ms
from .sequence_common import get_components_for_file_name, group_by_extension


def build_renumber_plan(
    source_dir: str,
    start_value: int,
    step_value: int,
) -> List[Tuple[str, str]]:
    """Return [(src, dst_name_in_temp)] for the source directory."""
    if start_value < 0:
        raise ValueError("Start value should be non-negative.")
    if step_value < 1:
        raise ValueError("Step value should be positive.")

    temp_dir = os.path.join(source_dir, "temp")
    plan: List[Tuple[str, str]] = []
    for _ext, files in group_by_extension(source_dir).items():
        for i, src in enumerate(files):
            prefix, number_str, _suffix = get_components_for_file_name(os.path.basename(src))
            number_width = len(number_str)
            new_number = start_value + step_value * i
            # NOTE: Java bug - third format arg is number_str, not the extension.
            new_name = f"{prefix}{new_number:0{number_width}d}{number_str}"
            plan.append((src, os.path.join(temp_dir, new_name)))
    plan.sort()
    return plan


def execute_renumber_plan(
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
