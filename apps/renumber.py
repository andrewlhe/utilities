#!/usr/bin/env python3
"""Renumber a camera-file sequence - standalone program.

Usage:
    python apps/renumber.py <directory> [--start 0] [--step 1]
    python apps/renumber.py --gui
"""
from __future__ import annotations

import argparse
import os
import sys
import tkinter as tk
from tkinter import ttk

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils_lib import sequence_renumber  # noqa: E402
from utils_lib.gui_common import (  # noqa: E402
    append_output,
    make_field,
    make_output,
    make_window,
    run_async,
    set_output,
)


def run_cli(args: argparse.Namespace) -> int:
    plan = sequence_renumber.build_renumber_plan(args.directory, args.start, args.step)
    for src, dst in plan:
        print(f"{os.path.basename(src)} -> {os.path.basename(dst)}")
    print(f"{len(plan)} files\n")
    if not plan:
        return 0
    if input("Do you want to proceed? (Y/N) ").strip().upper() != "Y":
        print("Aborted")
        return 0
    sequence_renumber.execute_renumber_plan(args.directory, plan)
    return 0


def run_gui() -> int:
    root = make_window("Renumber Sequence")
    dir_frame, dir_var = make_field(root, "Directory:", "dir")
    start_frame = ttk.Frame(root)
    start_frame.pack(side="top", fill="x", pady=2)
    ttk.Label(start_frame, text="Start value:", width=18).pack(side="left")
    start_var = tk.StringVar(value="0")
    ttk.Entry(start_frame, textvariable=start_var, width=10).pack(side="left")
    step_frame = ttk.Frame(root)
    step_frame.pack(side="top", fill="x", pady=2)
    ttk.Label(step_frame, text="Step value:", width=18).pack(side="left")
    step_var = tk.StringVar(value="1")
    ttk.Entry(step_frame, textvariable=step_var, width=10).pack(side="left")

    text = make_output(root)
    set_output(text, "Sequence Renumber\n=================\nRenames camera-file sequences so they start at a given number with a fixed step.\n\nHow to use:\n  1. Pick a directory with camera files.\n  2. Set Start value and Step value.\n  3. Click Run.\n\nExpected result:\n  Files are grouped by extension and renamed in sorted order to\n  <prefix><start + step*i:0Nd><oldNumberSuffix>. A temp folder is used\n  to avoid name collisions.")

    def on_run(log) -> None:
        d = dir_var.get()
        if not d:
            log("Pick a directory first.")
            return
        plan = sequence_renumber.build_renumber_plan(d, int(start_var.get()), int(step_var.get()))
        for src, dst in plan:
            log(f"{os.path.basename(src)} -> {os.path.basename(dst)}")
        log(f"{len(plan)} files")
        if plan:
            sequence_renumber.execute_renumber_plan(d, plan, log=log)

    ttk.Button(root, text="Run", command=lambda: run_async(text, on_run)).pack(pady=4)
    root.mainloop()
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Renumber a camera-file sequence")
    p.add_argument("directory", nargs="?")
    p.add_argument("--start", type=int, default=0)
    p.add_argument("--step", type=int, default=1)
    args = p.parse_args(argv)
    if not args.directory:
        return run_gui()
    return run_cli(args)


if __name__ == "__main__":
    sys.exit(main())

