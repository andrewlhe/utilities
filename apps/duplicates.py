#!/usr/bin/env python3
"""Duplicate file remover - standalone program.

Scans a directory (optionally subfolders), hashes every file with MD5, and
lists duplicates for removal.

Usage:
    python apps/duplicates.py <directory> [--no-subfolders] [--remove]
    python apps/duplicates.py --gui
"""
from __future__ import annotations

import argparse
import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import List, Optional

# Make the library importable when run as a script.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils_lib import duplicate_remover  # noqa: E402


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


class DuplicatePanel(ttk.Frame):
    directory: Optional[str] = None
    duplicates: List[str] = []

    def _build(self) -> None:
        top = ttk.Frame(self)
        top.pack(side="top", fill="x")
        ttk.Button(top, text="Open", command=self._on_open).pack(side="left")
        self.scan_btn = ttk.Button(top, text="Start", command=self._on_scan)
        self.scan_btn.pack(side="left")
        self.remove_btn = ttk.Button(top, text="Remove", command=self._on_remove)
        self.remove_btn.pack(side="left")
        self.remove_btn.configure(state="disabled")

        self.sub_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(top, text="Include Subfolders", variable=self.sub_var).pack(side="left")

        self.text = tk.Text(self, wrap="word", font=("Consolas", 11))
        self.text.pack(side="top", fill="both", expand=True)
        self._set_text(
            "Duplicate Remover\n"
            "================\n"
            "Finds files with identical content (by MD5 hash) and lists redundant copies.\n\n"
            "How to use:\n"
            "  1. Click \"Open\" to choose a folder to scan.\n"
            "  2. Check \"Include Subfolders\" to scan subdirectories too.\n"
            "  3. Click \"Start\" to scan.\n"
            "  4. Review the list of duplicates found.\n"
            "  5. Click \"Remove\" to delete the redundant copies.\n\n"
            "Expected result:\n"
            "  The report shows total files scanned, number of duplicates, and the\n"
            "  redundant files. The first copy of each file is always kept; all later\n"
            "  copies with the same MD5 are listed for removal."
        )

    def _set_text(self, text: str) -> None:
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("end", text)
        self.text.see("end")
        self.text.configure(state="disabled")

    def _append(self, msg: str) -> None:
        self.text.configure(state="normal")
        self.text.insert("end", msg + "\n")
        self.text.see("end")
        self.text.configure(state="disabled")

    def _on_open(self) -> None:
        path = filedialog.askdirectory(title="Choose a directory")
        if not path:
            self._set_text("Open command cancelled by user.")
            return
        self.directory = path
        self._set_text(f"Directory selected: {path}\n")

    def _on_scan(self) -> None:
        if not self.directory:
            self._set_text("Please choose a directory.")
            return
        self._set_text("")
        result = duplicate_remover.find_duplicates(
            self.directory, include_subfolders=self.sub_var.get(), log=self._append
        )
        self.duplicates = result.duplicates
        self._append(duplicate_remover.format_report(result))
        self.remove_btn.configure(state="normal" if self.duplicates else "disabled")

    def _on_remove(self) -> None:
        if not messagebox.askokcancel("Remove", "You can't undo this action.\nDo you want to remove the files?"):
            return
        duplicate_remover.remove_duplicates(self.duplicates)
        self.duplicates = []
        self.remove_btn.configure(state="disabled")
        self._append("")
        self._append("Done!")

    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master)
        self._build()


def run_gui() -> int:
    root = tk.Tk()
    root.title("Duplicate Remover")
    root.geometry("800x500")
    DuplicatePanel(root).pack(fill="both", expand=True)
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

