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


def _norm_suffix(suffix: Optional[str]) -> Optional[str]:
    """Normalise a user-provided suffix: '.ARW' or 'ARW' -> '.ARW'; '' -> None."""
    if suffix is None:
        return None
    s = suffix.strip()
    if not s:
        return None
    if not s.startswith("."):
        s = "." + s
    return s


def build_renumber_plan(
    source_dir: str,
    start_value: int,
    step_value: int,
    prefix: Optional[str] = None,
    width: Optional[int] = None,
    suffix: Optional[str] = None,
    output_dir: Optional[str] = None,
) -> List[Tuple[str, str]]:
    """Return [(src, dst_name_in_temp)] for the source directory.

    Naming rule (per file, in sorted order within each extension group):
        new_name = <prefix><start + step*i:0<width>d><suffix>

    * prefix: custom prefix; None keeps the original prefix of each file.
    * width:  digit width (zero-padded); None keeps the original width.
    * suffix: extension like '.ARW'; None keeps the original extension.
    * output_dir: where the renamed files will land (temp folder lives there).
      None keeps the files in source_dir (rename in place).
    """
    if start_value < 0:
        raise ValueError("Start value should be non-negative.")
    if step_value < 1:
        raise ValueError("Step value should be positive.")
    if width is not None and width < 1:
        raise ValueError("Width should be a positive integer.")

    norm_suffix = _norm_suffix(suffix)

    temp_dir = os.path.join(output_dir or source_dir, "temp")
    plan: List[Tuple[str, str]] = []
    for _ext, files in group_by_extension(source_dir).items():
        for i, src in enumerate(files):
            old_prefix, number_str, old_suffix = get_components_for_file_name(
                os.path.basename(src)
            )
            new_prefix = old_prefix if prefix is None else prefix
            new_width = len(number_str) if width is None else width
            new_suffix = old_suffix if norm_suffix is None else norm_suffix
            new_number = start_value + step_value * i
            new_name = f"{new_prefix}{new_number:0{new_width}d}{new_suffix}"
            plan.append((src, os.path.join(temp_dir, new_name)))
    plan.sort()
    return plan


def execute_renumber_plan(
    source_dir: str,
    plan: List[Tuple[str, str]],
    log: Optional[Callable[[str], None]] = None,
    output_dir: Optional[str] = None,
) -> Tuple[int, int, List[str]]:
    """Move files according to *plan*; the final files land in output_dir or, if
    None, back in source_dir (rename in place)."""
    log = log or (lambda s: None)
    target_dir = output_dir or source_dir
    if target_dir != source_dir:
        os.makedirs(target_dir, exist_ok=True)
    temp_dir = os.path.join(target_dir, "temp")
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
            dst = os.path.join(target_dir, name)
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
