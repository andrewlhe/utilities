#!/usr/bin/env python3
"""Duplicate file remover - standalone program.

Scans a directory (optionally subfolders), hashes every file with MD5, groups
duplicates by content, and lets the user pick which copy(ies) to delete.

Usage:
    python apps/duplicates.py <directory> [--no-subfolders] [--remove]
    python apps/duplicates.py             (no args = GUI)
"""
from __future__ import annotations

import argparse
import os
import sys
import threading
import time
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


def run_gui() -> int:
    root = tk.Tk()
    root.title("Duplicate Remover")
    root.geometry("960x680")

    state = {"directory": None}
    history: List[dict] = []  # {time, total, groups: [(md5, [paths])], checked: set[int]}
    current = {"idx": -1}

    # --- top row: open + dir + subfolders + scan ---
    top = ttk.Frame(root)
    top.pack(side="top", fill="x", padx=8, pady=4)

    def pick_dir() -> None:
        path = filedialog.askdirectory(title="Choose a directory")
        if path:
            state["directory"] = path
            dir_var.set(path)

    dir_var = tk.StringVar()
    ttk.Button(top, text="Open...", command=pick_dir).pack(side="left")
    ttk.Entry(top, textvariable=dir_var, width=60).pack(side="left", padx=6)

    sub_var = tk.BooleanVar(value=True)
    ttk.Checkbutton(top, text="Include Subfolders", variable=sub_var).pack(side="left", padx=6)

    scan_btn = ttk.Button(top, text="Scan", command=None)
    scan_btn.pack(side="left", padx=6)

    # --- progress row ---
    prog_frame = ttk.Frame(root)
    prog_frame.pack(side="top", fill="x", padx=8)
    progress = ttk.Progressbar(prog_frame, mode="determinate", maximum=1000)
    progress.pack(side="left", fill="x", expand=True)
    status_var = tk.StringVar(
        value="Ready - click Open to choose a folder, then Scan. Click a row to toggle delete."
    )
    ttk.Label(prog_frame, textvariable=status_var, width=60, anchor="e").pack(side="left", padx=6)

    # --- history row ---
    hist_frame = ttk.Frame(root)
    hist_frame.pack(side="top", fill="x", padx=8, pady=4)
    ttk.Label(hist_frame, text="Scan history:").pack(side="left")
    combo = ttk.Combobox(hist_frame, state="readonly", width=56)
    combo.pack(side="left", padx=6)
    combo.bind("<<ComboboxSelected>>", lambda e: on_history_select(combo.current()))

    # --- duplicate files list (grouped, checkable) ---
    list_frame = ttk.Frame(root)
    list_frame.pack(side="top", fill="both", expand=True, padx=8, pady=4)
    tree = ttk.Treeview(
        list_frame, columns=("check", "path"), show="headings",
        selectmode="none", height=20,
    )
    tree.heading("check", text="Delete")
    tree.heading("path", text="File (click a row to toggle)")
    tree.column("check", width=80, anchor="center", stretch=False)
    tree.column("path", width=880, stretch=True)
    vsb = ttk.Scrollbar(list_frame, command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    vsb.pack(side="right", fill="y")
    tree.pack(side="left", fill="both", expand=True)
    tree.tag_configure("group", background="#ececec", foreground="#333333")

    # --- buttons row ---
    btn_frame = ttk.Frame(root)
    btn_frame.pack(side="top", fill="x", padx=8, pady=4)

    # ---------------------------------------------------------------- helpers

    def refresh_combobox() -> None:
        labels = [
            f"Scan {i + 1} - {r['time']}  ({len(r['groups'])} groups, "
            f"{sum(len(paths) for _, paths in r['groups'])} copies)"
            for i, r in enumerate(history)
        ]
        combo["values"] = labels
        if current["idx"] >= 0:
            combo.current(current["idx"])

    def update_remove_btn() -> None:
        if current["idx"] < 0:
            remove_btn.configure(text="Remove", state="disabled")
            return
        n = len(history[current["idx"]]["checked"])
        remove_btn.configure(
            text=f"Remove ({n})" if n else "Remove",
            state="normal" if n else "disabled",
        )

    def flat_files(rec: dict) -> List[str]:
        """Flatten group paths into one list; index == global file index."""
        return [p for _, paths in rec["groups"] for p in paths]

    def load_scan(idx: int) -> None:
        rec = history[idx]
        tree.delete(*tree.get_children())
        fi = 0  # global file index across groups
        for gi, (md5, paths) in enumerate(rec["groups"]):
            tree.insert(
                "", "end", iid=f"g{gi}",
                values=("", f"---- Group {gi + 1}: md5 {md5[:8]}...  ({len(paths)} copies) ----"),
                tags=("group",),
            )
            for p in paths:
                mark = "[x]" if fi in rec["checked"] else "[ ]"
                tree.insert("", "end", iid=f"f{fi}", values=(mark, p))
                fi += 1
        n = len(rec["checked"])
        if not rec["groups"]:
            status_var.set(f"Scan {idx + 1}: no duplicate files found.")
        else:
            status_var.set(
                f"Scan {idx + 1}: {len(rec['groups'])} groups, {fi} copies, "
                f"{n} selected for removal"
            )
        update_remove_btn()

    def on_history_select(idx: int) -> None:
        if idx < 0 or idx == current["idx"]:
            return
        current["idx"] = idx
        load_scan(idx)

    def on_tree_click(event: object) -> None:
        if current["idx"] < 0:
            return
        row = tree.identify("row", event.x, event.y)
        if not row or not row.startswith("f"):
            return  # only file rows are toggleable
        i = int(row[1:])
        rec = history[current["idx"]]
        if i in rec["checked"]:
            rec["checked"].discard(i)
        else:
            rec["checked"].add(i)
        tree.set(row, "check", "[x]" if i in rec["checked"] else "[ ]")
        update_remove_btn()

    tree.bind("<Button-1>", on_tree_click)

    # ------------------------------------------------------------- scanning

    scan_state = {"done": False, "result": None, "calls": 0, "total": 0}

    def poll_progress() -> None:
        if scan_state["done"]:
            return
        total = scan_state["total"]
        n = scan_state["calls"] // 2  # lib logs twice per file
        if n > total:
            n = total
        if total > 0:
            progress["value"] = (n / total) * 1000
            status_var.set(f"Scanning {n}/{total}")
        root.after(100, poll_progress)

    def worker() -> None:
        d = state["directory"]
        from utils_lib.common import iter_files
        all_files = list(iter_files(d, sub_var.get()))
        scan_state["total"] = len(all_files)

        def progress_log(msg: str) -> None:
            scan_state["calls"] += 1

        res = duplicate_remover.find_duplicate_groups(
            d, include_subfolders=sub_var.get(), log=progress_log
        )
        scan_state["result"] = res
        scan_state["done"] = True
        root.after(0, on_scan_done)

    def on_scan_done() -> None:
        res = scan_state["result"]
        progress["value"] = 1000 if scan_state["total"] else 0
        rec = {
            "time": time.strftime("%H:%M:%S"),
            "total": res.total,
            "groups": res.groups,
            "checked": set(),  # nothing selected by default: user picks locations
        }
        history.append(rec)
        current["idx"] = len(history) - 1
        refresh_combobox()
        load_scan(current["idx"])
        scan_btn.configure(state="normal")

    def start_scan() -> None:
        d = state["directory"]
        if not d:
            status_var.set("Please choose a directory first.")
            return
        scan_btn.configure(state="disabled")
        remove_btn.configure(state="disabled")
        status_var.set(f"Scanning {d} ...")
        progress["value"] = 0
        scan_state["done"] = False
        scan_state["calls"] = 0
        scan_state["total"] = 0
        threading.Thread(target=worker, daemon=True).start()
        root.after(100, poll_progress)

    scan_btn.configure(command=start_scan)

    # --------------------------------------------------------------- actions

    def select_all() -> None:
        """Check every copy of every group (deletes all copies)."""
        if current["idx"] < 0:
            return
        rec = history[current["idx"]]
        rec["checked"] = set(range(len(flat_files(rec))))
        load_scan(current["idx"])

    def keep_first() -> None:
        """Keep the first copy of each group, check the rest (common dedup)."""
        if current["idx"] < 0:
            return
        rec = history[current["idx"]]
        checked = set()
        fi = 0
        for _, paths in rec["groups"]:
            for j, _ in enumerate(paths):
                if j > 0:
                    checked.add(fi)
                fi += 1
        rec["checked"] = checked
        load_scan(current["idx"])

    def clear_all() -> None:
        if current["idx"] < 0:
            return
        rec = history[current["idx"]]
        rec["checked"] = set()
        load_scan(current["idx"])

    def do_remove() -> None:
        if current["idx"] < 0:
            return
        rec = history[current["idx"]]
        files = flat_files(rec)
        selected = [files[i] for i in sorted(rec["checked"])]
        if not selected:
            return
        if not messagebox.askokcancel(
            "Remove",
            f"You can't undo this action.\nRemove {len(selected)} selected files?",
        ):
            return
        duplicate_remover.remove_duplicates(selected)
        # rebuild groups without the deleted files
        removed = set(selected)
        new_groups = []
        for md5, paths in rec["groups"]:
            keep = [p for p in paths if p not in removed]
            if len(keep) >= 2:
                new_groups.append((md5, keep))
        rec["groups"] = new_groups
        rec["checked"] = set()
        refresh_combobox()
        load_scan(current["idx"])
        status_var.set(f"Removed {len(selected)} files.")

    ttk.Button(btn_frame, text="Select All", command=select_all).pack(side="left")
    ttk.Button(btn_frame, text="Keep First", command=keep_first).pack(side="left", padx=6)
    ttk.Button(btn_frame, text="Clear", command=clear_all).pack(side="left", padx=6)
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
