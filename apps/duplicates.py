#!/usr/bin/env python3
"""Duplicate file remover - standalone program.

Scans a directory (optionally subfolders), hashes every file with MD5, and
lists duplicates for removal.

Usage:
    python apps/duplicates.py <directory> [--no-subfolders] [--remove]
    python apps/duplicates.py             (no args = GUI)
"""
from __future__ import annotations

import argparse
import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import List, Optional

# Make the library importable when run as a script.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils_lib import duplicate_remover  # noqa: E402
from utils_lib.gui_common import set_output  # noqa: E402


def run_cli(args: argparse.Namespace) -> int:
    result = duplicate_remover.find_duplicates(
        args.directory, include_subfolders=not args.no_subfolders
    )
    print(duplicate_remover.format_report(result))
    if args.remove and result.duplicates:
        confirm = input("Type 'yes' to remove the listed files: ")
        if confirm.strip().lower() == "yes":
            duplicate_remover.remove_duplicates(result.duplicates)
            print("Done!")
        else:
            print("Aborted.")
    return 0


WELCOME = (
    "Duplicate Remover\n"
    "================\n"
    "Finds files with identical content (by MD5 hash) and lists redundant copies.\n"
    "\n"
    "How to use:\n"
    "  1. Click \"Open\" to choose a folder to scan.\n"
    "  2. Check \"Include Subfolders\" to scan subdirectories too.\n"
    "  3. Click \"Start\" to scan.\n"
    "  4. Review the list of duplicates found.\n"
    "  5. Click \"Remove\" to delete the redundant copies.\n"
    "\n"
    "Expected result:\n"
    "  The report shows total files scanned, number of duplicates, and the\n"
    "  redundant files. The first copy of each file is always kept; all later\n"
    "  copies with the same MD5 are listed for removal."
)


def run_gui() -> int:
    root = tk.Tk()
    root.title("Duplicate Remover")
    root.geometry("900x600")

    state = {"directory": None, "duplicates": []}

    # --- top row ---
    top = ttk.Frame(root)
    top.pack(side="top", fill="x", padx=8, pady=4)

    def pick_dir() -> None:
        path = filedialog.askdirectory(title="Choose a directory")
        if path:
            state["directory"] = path
            dir_var.set(path)

    dir_var = tk.StringVar()
    ttk.Button(top, text="Open...", command=pick_dir).pack(side="left")
    ttk.Entry(top, textvariable=dir_var, width=70).pack(side="left", padx=6)

    sub_var = tk.BooleanVar(value=True)
    ttk.Checkbutton(top, text="Include Subfolders", variable=sub_var).pack(side="left", padx=6)

    # --- progress row ---
    prog_frame = ttk.Frame(root)
    prog_frame.pack(side="top", fill="x", padx=8)
    progress = ttk.Progressbar(prog_frame, mode="determinate", maximum=1000)
    progress.pack(side="left", fill="x", expand=True)
    status_var = tk.StringVar(value="Ready")
    ttk.Label(prog_frame, textvariable=status_var, width=30, anchor="e").pack(side="left", padx=6)

    # --- output (with scrollbar) ---
    out_frame = ttk.Frame(root)
    out_frame.pack(side="top", fill="both", expand=True, padx=8, pady=4)
    text = tk.Text(out_frame, wrap="word", font=("Consolas", 10))
    vsb = ttk.Scrollbar(out_frame, command=text.yview)
    text.configure(yscrollcommand=vsb.set, state="disabled")
    vsb.pack(side="right", fill="y")
    text.pack(side="left", fill="both", expand=True)

    set_output(text, WELCOME)

    # --- buttons row ---
    btn_frame = ttk.Frame(root)
    btn_frame.pack(side="top", fill="x", padx=8, pady=4)

    # shared state: written by worker thread, read by UI poll
    scan_state = {"done": False, "result": None, "scanned": 0, "total": 0}

    def poll_progress() -> None:
        """UI thread: update progress bar every 100ms."""
        if scan_state["done"]:
            return
        total = scan_state["total"]
        n = scan_state["scanned"]
        if total > 0:
            progress["value"] = (n / total) * 1000
            status_var.set(f"Scanning {n}/{total}")
        root.after(100, poll_progress)

    def worker() -> None:
        d = state["directory"]
        from utils_lib.common import iter_files
        all_files = list(iter_files(d, sub_var.get()))
        total = len(all_files)
        scan_state["total"] = total

        def progress_log(msg: str) -> None:
            # lib calls log(path) then log(checksum) per file;
            # just bump the counter, don't touch the UI text.
            scan_state["scanned"] += 1

        res = duplicate_remover.find_duplicates(
            d, include_subfolders=sub_var.get(), log=progress_log
        )
        scan_state["result"] = res
        scan_state["done"] = True
        root.after(0, on_scan_done)

    def on_scan_done() -> None:
        res = scan_state["result"]
        state["duplicates"] = res.duplicates
        progress["value"] = 1000 if scan_state["total"] else 0
        status_var.set(f"Done - {len(res.duplicates)} duplicates")
        set_output(text, duplicate_remover.format_report(res))
        remove_btn.configure(state="normal" if res.duplicates else "disabled")
        start_btn.configure(state="normal")

    def start_scan() -> None:
        d = state["directory"]
        if not d:
            set_output(text, "Please choose a directory first.")
            return
        start_btn.configure(state="disabled")
        remove_btn.configure(state="disabled")
        set_output(text, f"Scanning {d} ...")
        progress["value"] = 0
        scan_state["done"] = False
        scan_state["scanned"] = 0
        scan_state["total"] = 0
        threading.Thread(target=worker, daemon=True).start()
        root.after(100, poll_progress)

    def do_remove() -> None:
        if not state["duplicates"]:
            return
        if not messagebox.askokcancel(
            "Remove",
            f"You can't undo this action.\nRemove {len(state['duplicates'])} files?",
        ):
            return
        duplicate_remover.remove_duplicates(state["duplicates"])
        n = len(state["duplicates"])
        state["duplicates"] = []
        remove_btn.configure(state="disabled")
        set_output(text, f"Removed {n} files.\n")

    start_btn = ttk.Button(btn_frame, text="Start", command=start_scan)
    start_btn.pack(side="left")
    remove_btn = ttk.Button(btn_frame, text="Remove", command=do_remove)
    remove_btn.pack(side="left", padx=6)
    remove_btn.configure(state="disabled")

    root.mainloop()
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Find and remove duplicate files by MD5")
    p.add_argument("directory", nargs="?", help="Directory to scan (omit to open GUI)")
    p.add_argument("--no-subfolders", action="store_true")
    p.add_argument("--remove", action="store_true", help="Actually delete after confirmation")
    args = p.parse_args(argv)
    if not args.directory:
        return run_gui()
    return run_cli(args)


if __name__ == "__main__":
    sys.exit(main())
