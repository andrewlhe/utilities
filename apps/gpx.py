#!/usr/bin/env python3
"""Convert an Apple plist track dump to GPX - standalone program.

Usage:
    python apps/gpx.py --input data.plist --output data.gpx
    python apps/gpx.py --gui
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils_lib import gpx_generator  # noqa: E402
from utils_lib.gui_common import (  # noqa: E402
    make_field,
    make_output,
    make_window,
    run_async,
    set_output,
)


def run_cli(args: argparse.Namespace) -> int:
    n = gpx_generator.convert(args.input, args.output)
    print(f"Wrote {n} track points to {args.output}")
    return 0


def run_gui() -> int:
    root = make_window("Plist -> GPX Converter")
    _, input_var = make_field(root, "Input plist:", "file")
    _, output_var = make_field(root, "Output GPX:", "save")
    text = make_output(root)
    set_output(text, "Plist to GPX Converter\n======================\nConverts an Apple plist track dump into a GPX file.\n\nHow to use:\n  1. Choose input .plist file.\n  2. Choose output .gpx path.\n  3. Click Convert.\n\nExpected result:\n  The plist contains an array of dicts with altitude, date, latitude, longitude.\n  The output GPX file has a <trk> with <trkseg> and <trkpt> elements.")

    def on_run(log) -> None:
        n = gpx_generator.convert(input_var.get(), output_var.get())
        log(f"Wrote {n} track points to {output_var.get()}")

    import tkinter.ttk as ttk
    ttk.Button(root, text="Convert", command=lambda: run_async(text, on_run)).pack(pady=4)
    root.mainloop()
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Convert plist track to GPX")
    p.add_argument("--input")
    p.add_argument("--output")
    args = p.parse_args(argv)
    if not args.input or not args.output:
        return run_gui()
    return run_cli(args)


if __name__ == "__main__":
    sys.exit(main())


