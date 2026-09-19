#!/usr/bin/env python3
"""Photo gallery CSV/XLSX -> date-foldered copies - standalone program.

Usage:
    python apps/photos_gallery.py --csv gallery.csv --drive M:/ --output /tmp/out
    python apps/photos_gallery.py --gui
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils_lib import photo_gallery  # noqa: E402
from utils_lib.gui_common import (  # noqa: E402
    make_field,
    make_output,
    make_window,
    run_async,
    set_output,
)


def run_cli(args: argparse.Namespace) -> int:
    plan = photo_gallery.build_paths(args.csv, args.drive, args.output)
    photo_gallery.execute(plan)
    return 0


def run_gui() -> int:
    root = make_window("Photo Gallery Copy")
    _, csv_var = make_field(root, "CSV / XLSX:", "file")
    _, drive_var = make_field(root, "Drive prefix:", "")
    _, out_var = make_field(root, "Output folder:", "dir")
    text = make_output(root)
    set_output(text, "Photo Gallery Builder\n=====================\nCopies photos listed in a CSV/XLSX into date-named folders.\n\nHow to use:\n  1. Choose a CSV or XLSX file.\n  2. Set the Drive root (e.g. M:/).\n  3. Set the Output folder.\n  4. Click Run.\n\nExpected result:\n  CSV columns: originalPath (1), dateTaken (2), fileName (3), fileExtension (4).\n  Output: <output>/<dateTaken>/<FileName>.<ext>")

    def on_run(log) -> None:
        plan = photo_gallery.build_paths(csv_var.get(), drive_var.get(), out_var.get())
        photo_gallery.execute(plan, log=log)

    import tkinter.ttk as ttk
    ttk.Button(root, text="Run", command=lambda: run_async(text, on_run)).pack(pady=4)
    root.mainloop()
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Copy gallery photos per CSV/XLSX into date folders")
    p.add_argument("--csv")
    p.add_argument("--drive")
    p.add_argument("--output")
    args = p.parse_args(argv)
    if not args.csv or not args.drive or not args.output:
        return run_gui()
    return run_cli(args)


if __name__ == "__main__":
    sys.exit(main())


