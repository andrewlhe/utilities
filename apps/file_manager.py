#!/usr/bin/env python3
"""File Manager - standalone program.

Batch copy or delete files whose names match a regex.

Usage:
    python apps/file_manager.py copy <from-dir> [--to-dir <to-dir>] [--pattern ".*\\.ARW"] [--no-subfolders] [--execute]
    python apps/file_manager.py delete <from-dir> [--pattern ".*\\.ARW"] [--no-subfolders] [--execute]
    python apps/file_manager.py --gui
"""
from __future__ import annotations

import argparse
import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils_lib import file_manager  # noqa: E402


def run_cli(args: argparse.Namespace) -> int:
    err, plan = file_manager.plan_files(
        mode=args.mode,
        from_dir=args.from_dir,
        to_dir=args.to_dir,
        filename_regex=args.pattern,
        include_subfolders=not args.no_subfolders,
    )
    if err:
        print("Error:", err)
        return 2
    print(file_manager.format_plan_report(plan, args.mode))
    if args.execute:
        question = "Type 'yes' to copy: " if args.mode == "copy" else "Type 'yes' to delete: "
        if input(question).strip().lower() != "yes":
            print("Aborted.")
            return 0
        file_manager.execute_plan(plan, args.mode)
    return 0


class FileManagerPanel(ttk.Frame):
    def _build(self) -> None:
        top = ttk.Frame(self)
        top.pack(side="top", fill="x")
        self.mode_var = tk.StringVar(value="copy")
        ttk.Radiobutton(top, text="Copy", variable=self.mode_var, value="copy").pack(side="left")
        ttk.Radiobutton(top, text="Delete", variable=self.mode_var, value="delete").pack(side="left")

        frm = ttk.Frame(self)
        frm.pack(side="top", fill="x")
        ttk.Label(frm, text="From:").pack(side="left")
        self.from_var = tk.StringVar(value="")
        ttk.Entry(frm, textvariable=self.from_var, width=40).pack(side="left")
        ttk.Button(frm, text="Browse...", command=self._browse_from).pack(side="left")

        tofrm = ttk.Frame(self)
        tofrm.pack(side="top", fill="x")
        ttk.Label(tofrm, text="To:").pack(side="left")
        self.to_var = tk.StringVar(value="")
        self.to_entry = ttk.Entry(tofrm, textvariable=self.to_var, width=40)
        self.to_entry.pack(side="left")
        self.to_browse = ttk.Button(tofrm, text="Browse...", command=self._browse_to)
        self.to_browse.pack(side="left")

        nfr = ttk.Frame(self)
        nfr.pack(side="top", fill="x")
        ttk.Label(nfr, text="File name regex:").pack(side="left")
        self.pattern_var = tk.StringVar(value="")
        ttk.Entry(nfr, textvariable=self.pattern_var, width=20).pack(side="left")
        self.sub_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(nfr, text="Include subfolders", variable=self.sub_var).pack(side="left")

        btn = ttk.Frame(self)
        btn.pack(side="top", fill="x")
        self.scan_btn = ttk.Button(btn, text="Start", command=self._on_start)
        self.scan_btn.pack(side="left")
        self.exec_btn = ttk.Button(btn, text="Copy", command=self._on_execute)
        self.exec_btn.pack(side="left")
        self.exec_btn.configure(state="disabled")
        self.mode_var.trace_add("write", lambda *_: self._on_mode_change())

        self.text = tk.Text(self, wrap="word", font=("Consolas", 11))
        self.text.pack(side="top", fill="both", expand=True)
        self._set_text(
            "File Manager\n"
            "============\n"
            "Batch copy or delete files whose names match a regular expression.\n"
            "\n"
            "How to use:\n"
            "  1. Choose Mode: copy or delete.\n"
            "  2. Pick Source (From) and Target (To) folders.\n"
            "  3. Set the filename regex (e.g. .*\\.ARW). Leave empty for all files.\n"
            "  4. Check \"Include subfolders\" if needed.\n"
            "  5. Click \"Start\" to preview what will happen.\n"
            "  6. Click \"Copy\" or \"Delete\" to perform the action.\n"
            "\n"
            "Expected result:\n"
            "  Start shows a list of files and their destination (copy) or deletion.\n"
            "  Execute performs the action. Copy mode preserves the directory structure\n"
            "  under the target. Delete mode removes matching files."
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

    def _on_mode_change(self) -> None:
        is_copy = self.mode_var.get() == "copy"
        self.to_entry.configure(state="normal" if is_copy else "disabled")
        self.to_browse.configure(state="normal" if is_copy else "disabled")
        self.exec_btn.configure(text="Copy" if is_copy else "Delete")

    def _browse_from(self) -> None:
        path = filedialog.askdirectory(title="From folder")
        if path:
            self.from_var.set(path)

    def _browse_to(self) -> None:
        path = filedialog.askdirectory(title="To folder")
        if path:
            self.to_var.set(path)

    def _on_start(self) -> None:
        err, plan = file_manager.plan_files(
            mode=self.mode_var.get(),
            from_dir=self.from_var.get(),
            to_dir=self.to_var.get() or None,
            filename_regex=self.pattern_var.get(),
            include_subfolders=self.sub_var.get(),
        )
        if err:
            messagebox.showwarning("Warning", err)
            return
        self.plan = plan
        self._set_text(file_manager.format_plan_report(plan, self.mode_var.get()))
        self.exec_btn.configure(state="normal" if plan.moves else "disabled")

    def _on_execute(self) -> None:
        mode = self.mode_var.get()
        title = "Do you want to copy the files?" if mode == "copy" else "Do you want to remove the files?"
        if not messagebox.askokcancel(title, "You can't undo this action."):
            return
        file_manager.execute_plan(self.plan, mode, log=self._append)
        self.exec_btn.configure(state="disabled")

    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master)
        self.plan = None
        self._build()


def run_gui() -> int:
    root = tk.Tk()
    root.title("File Manager")
    root.geometry("800x500")
    FileManagerPanel(root).pack(fill="both", expand=True)
    root.mainloop()
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Batch copy/delete files by name regex")
    p.add_argument("mode", nargs="?", choices=["copy", "delete"])
    p.add_argument("from_dir", nargs="?")
    p.add_argument("--to-dir")
    p.add_argument("--pattern", default="", help="Regex on file name (default .+)")
    p.add_argument("--no-subfolders", action="store_true")
    p.add_argument("--execute", action="store_true")
    args = p.parse_args(argv)
    if not args.mode or not args.from_dir:
        return run_gui()
    return run_cli(args)


if __name__ == "__main__":
    sys.exit(main())

