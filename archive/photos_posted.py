#!/usr/bin/env python3
"""Build a CSV of posted photos from date-foldered directories - standalone program.

Usage:
    python apps/photos_posted.py <directory> --output out.csv
    python apps/photos_posted.py --gui
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils_lib import posted_photo_processor  # noqa: E402
from utils_lib.gui_common import (  # noqa: E402
    make_field,
    make_output,
    make_window,
    run_async,
    set_output,
)


def run_cli(args: argparse.Namespace) -> int:
    n = posted_photo_processor.write_csv(args.directory, args.output)
    print(f"Wrote {n} rows to {args.output}")
    return 0


def run_gui() -> int:
    root = make_window("Posted Photos CSV Builder")
    _, dir_var = make_field(root, "Photos folder:", "dir")
    _, out_var = make_field(root, "Output CSV:", "save")
    text = make_output(root)
    set_output(text, "Posted Photos CSV Builder\n=========================\nBuilds a CSV of photos posted on specific dates from YYMMDD folders.\n\nHow to use:\n  1. Choose the root folder containing YYMMDD subfolders.\n  2. Choose where to save the output CSV.\n  3. Click Run.\n\nExpected result:\n  Each immediate subfolder named YYMMDD (e.g. 160322) is treated as a posting date.\n  Every image inside it is emitted as a row: datePosted,fileName,extension.")

    def on_run(log) -> None:
        n = posted_photo_processor.write_csv(dir_var.get(), out_var.get())
        log(f"Wrote {n} rows to {out_var.get()}")

    import tkinter.ttk as ttk
    ttk.Button(root, text="Build", command=lambda: run_async(text, on_run)).pack(pady=4)
    root.mainloop()
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Build posted-photos CSV from date folders")
    p.add_argument("directory", nargs="?")
    p.add_argument("--output")
    args = p.parse_args(argv)
    if not args.directory or not args.output:
        return run_gui()
    return run_cli(args)


if __name__ == "__main__":
    sys.exit(main())


