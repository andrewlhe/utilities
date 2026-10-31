#!/usr/bin/env python3
"""Renumber a camera-file sequence - standalone program.

Usage:
    python apps/renumber.py <directory> [--start 0] [--step 1]
                            [--prefix PREFIX] [--width W] [--suffix SUFFIX]
    python apps/renumber.py             (no args = GUI)
"""
from __future__ import annotations

import argparse
import os
import sys
import tkinter as tk
from tkinter import messagebox, ttk
from typing import List, Optional

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


def _opt_str(value: Optional[str]) -> Optional[str]:
    """Blank / '-' CLI values mean 'keep original' (None)."""
    if value is None:
        return None
    s = value.strip()
    return s if s and s != "-" else None


def run_cli(args: argparse.Namespace) -> int:
    plan = sequence_renumber.build_renumber_plan(
        args.directory,
        args.start,
        args.step,
        prefix=_opt_str(args.prefix),
        width=args.width,
        suffix=_opt_str(args.suffix),
        output_dir=args.output_dir,
    )
    for src, dst in plan:
        print(f"{os.path.basename(src)} -> {os.path.basename(dst)}")
    print(f"{len(plan)} files\n")
    if not plan:
        return 0
    if input("Do you want to proceed? (Y/N) ").strip().upper() != "Y":
        print("Aborted")
        return 0
    sequence_renumber.execute_renumber_plan(args.directory, plan, output_dir=args.output_dir)
    return 0


def run_gui() -> int:
    root = make_window("Renumber Sequence", 860, 680)

    dir_frame, dir_var = make_field(root, "Directory:", "dir")

    # --- start / step ---
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

    # --- custom naming rule (blank = keep original) ---
    pref_frame, pref_var = make_field(root, "Prefix (blank=keep):", "")
    width_frame, width_var = make_field(root, "Digit width (blank=keep):", "")
    suff_frame, suff_var = make_field(root, "Suffix (blank=keep):", "")

    # --- output folder (blank = rename in place) ---
    out_frame, out_var = make_field(root, "Output folder (blank=in place):", "dir")

    # --- preview table ---
    prev_frame = ttk.Frame(root)
    prev_frame.pack(side="top", fill="both", expand=True, padx=8, pady=4)
    tree = ttk.Treeview(prev_frame, columns=("old", "new"), show="headings", height=14)
    tree.heading("old", text="Current name")
    tree.heading("new", text="New name")
    tree.column("old", width=360, stretch=True)
    tree.column("new", width=360, stretch=True)
    vsb = ttk.Scrollbar(prev_frame, command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    vsb.pack(side="right", fill="y")
    tree.pack(side="left", fill="both", expand=True)

    text = make_output(root)

    # --- buttons ---
    btn = ttk.Frame(root)
    btn.pack(side="top", fill="x", padx=8, pady=4)

    state = {"dir": None, "plan": None}

    def _build_plan() -> Optional[List[tuple]]:
        d = dir_var.get().strip()
        if not d:
            return None
        try:
            start = int(start_var.get().strip() or "0")
            step = int(step_var.get().strip() or "1")
        except ValueError:
            messagebox.showwarning("Invalid value", "Start and Step must be integers.")
            return None
        w = width_var.get().strip()
        try:
            width = int(w) if w else None
        except ValueError:
            messagebox.showwarning("Invalid value", "Digit width must be an integer.")
            return None
        return sequence_renumber.build_renumber_plan(
            d,
            start,
            step,
            prefix=pref_var.get().strip() or None,
            width=width,
            suffix=suff_var.get().strip() or None,
            output_dir=out_var.get().strip() or None,
        )

    def do_preview() -> None:
        plan = _build_plan()
        if plan is None:
            messagebox.showwarning("Missing input", "Pick a directory first.")
            return
        state["dir"] = dir_var.get().strip()
        state["output"] = out_var.get().strip() or None
        state["plan"] = plan
        tree.delete(*tree.get_children())
        for src, dst in plan:
            tree.insert("", "end", values=(os.path.basename(src), os.path.basename(dst)))
        set_output(text, f"Preview: {len(plan)} files will be renamed.\n")
        exec_btn.configure(state="normal" if plan else "disabled")

    def do_execute() -> None:
        plan = state["plan"]
        if not plan:
            messagebox.showwarning("No preview", "Run Preview first.")
            return
        if not messagebox.askokcancel(
            "Execute",
            f"Rename {len(plan)} files?\nThis cannot be undone.",
        ):
            return

        def worker(log) -> None:
            sequence_renumber.execute_renumber_plan(
                state["dir"], plan, log=log, output_dir=state["output"]
            )

        run_async(text, worker, on_done=lambda: exec_btn.configure(state="disabled"))

    ttk.Button(btn, text="Preview", command=do_preview).pack(side="left")
    exec_btn = ttk.Button(btn, text="Execute", command=do_execute)
    exec_btn.pack(side="left", padx=6)
    exec_btn.configure(state="disabled")

    set_output(
        text,
        "Sequence Renumber\n"
        "=================\n"
        "Renames camera-file sequences so they start at a given number with a fixed step.\n"
        "\n"
        "How to use:\n"
        "  1. Pick a directory with camera files.\n"
        "  2. Set Start value and Step value.\n"
        "  3. Optionally customise the naming rule (blank keeps the original):\n"
        "       - Prefix: fixed prefix, e.g. DSC_  (blank = keep each file's prefix)\n"
        "       - Digit width: zero-padded width, e.g. 5 -> 00001 (blank = keep)\n"
        "       - Suffix: extension, e.g. .ARW or ARW (blank = keep)\n"
        "  4. Output folder: blank = rename in place; pick a folder to move the\n"
        "     renamed files there instead.\n"
        "  5. Click Preview to see the old -> new mapping before changing anything.\n"
        "  6. Review the table, then click Execute to rename.\n"
        "\n"
        "Expected result:\n"
        "  Files are grouped by extension and renamed in sorted order. A temp folder\n"
        "  is used to avoid name collisions.",
    )

    root.mainloop()
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Renumber a camera-file sequence")
    p.add_argument("directory", nargs="?", help="Directory (omit to open GUI)")
    p.add_argument("--start", type=int, default=0)
    p.add_argument("--step", type=int, default=1)
    p.add_argument("--prefix", default=None, help="Custom prefix (default: keep original)")
    p.add_argument("--width", type=int, default=None, help="Zero-padded digit width (default: keep)")
    p.add_argument("--suffix", default=None, help="Extension like .ARW (default: keep original)")
    p.add_argument("--output-dir", default=None, help="Output folder for renamed files (default: rename in place)")
    args = p.parse_args(argv)
    if not args.directory:
        return run_gui()
    return run_cli(args)


if __name__ == "__main__":
    sys.exit(main())
