#!/usr/bin/env python3
"""Append the head run of a camera sequence to the tail - standalone program.

Usage:
    python apps/append_head.py <directory>
    python apps/append_head.py --gui
"""
from __future__ import annotations

import argparse
import os
import sys
import tkinter as tk

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils_lib import sequence_append  # noqa: E402
from utils_lib.gui_common import (  # noqa: E402
    make_field,
    make_output,
    make_window,
    run_async,
    set_output,
)


def run_cli(args: argparse.Namespace) -> int:
    plan = sequence_append.build_append_plan(args.directory)
    for src, dst in plan:
        print(f"{os.path.basename(src)} -> {os.path.basename(dst)}")
    print(f"{len(plan)} files\n")
    if not plan:
        return 0
    if input("Do you want to proceed? (Y/N) ").strip().upper() != "Y":
        print("Aborted")
        return 0
    sequence_append.execute_append_plan(args.directory, plan)
    return 0


def run_gui() -> int:
    root = make_window("Append Head to Tail")
    _, dir_var = make_field(root, "Directory:", "dir")
    text = make_output(root)
    set_output(text, "Append Head to Tail\n===================\nFor a camera sequence with a gap, moves the head run to after the tail run.\n\nHow to use:\n  1. Pick a directory with a gapped sequence.\n  2. Click Run.\n\nExpected result:\n  Example: files 101-200 and 900-999 become 900-999 and 1000-1099,\n  eliminating the gap. Only the head run (first contiguous block) is moved.")

    def on_run(log) -> None:
        d = dir_var.get()
        if not d:
            log("Pick a directory first.")
            return
        plan = sequence_append.build_append_plan(d)
        for src, dst in plan:
            log(f"{os.path.basename(src)} -> {os.path.basename(dst)}")
        log(f"{len(plan)} files")
        if plan:
            sequence_append.execute_append_plan(d, plan, log=log)

    import tkinter.ttk as ttk
    ttk.Button(root, text="Run", command=lambda: run_async(text, on_run)).pack(pady=4)
    root.mainloop()
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Append head run of a camera sequence to the tail")
    p.add_argument("directory", nargs="?")
    args = p.parse_args(argv)
    if not args.directory:
        return run_gui()
    return run_cli(args)


if __name__ == "__main__":
    sys.exit(main())


