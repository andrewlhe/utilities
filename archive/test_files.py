#!/usr/bin/env python3
"""Generate synthetic camera-file sequences for testing - standalone program.

Usage:
    python apps/test_files.py <root-directory>
    python apps/test_files.py --gui
"""
from __future__ import annotations

import argparse
import os
import sys
import tkinter as tk
from tkinter import ttk

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils_lib import test_file_generator  # noqa: E402
from utils_lib.gui_common import (  # noqa: E402
    make_field,
    make_output,
    make_window,
    run_async,
    set_output,
)


def run_cli(args: argparse.Namespace) -> int:
    test_file_generator.run_all(args.root)
    print(f"Wrote test sequences under {args.root}")
    return 0


def run_gui() -> int:
    root = make_window("Test File Generator")
    _, root_var = make_field(root, "Root folder:", "dir")
    text = make_output(root)
    set_output(text, "Test File Generator\n====================\nCreates synthetic camera-file sequences for testing the renumber and append tools.\n\nHow to use:\n  1. Choose a root folder.\n  2. Click Generate.\n\nExpected result:\n  Creates Test 1 through Test 8 under the given root, each with a different\n  sequence gap pattern. Useful for verifying renumber/append behavior.")

    def on_run(log) -> None:
        r = root_var.get()
        if not r:
            log("Pick a root folder first.")
            return
        test_file_generator.run_all(r)
        log(f"Wrote test sequences under {r}")

    ttk.Button(root, text="Generate", command=lambda: run_async(text, on_run)).pack(pady=4)
    root.mainloop()
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Generate synthetic test sequences")
    p.add_argument("root", nargs="?")
    args = p.parse_args(argv)
    if not args.root:
        return run_gui()
    return run_cli(args)


if __name__ == "__main__":
    sys.exit(main())


