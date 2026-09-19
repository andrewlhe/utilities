#!/usr/bin/env python3
"""GRE vocabulary pipeline - standalone program.

Usage:
    python apps/vocabulary.py process1 --input raw1.txt --output out1.txt
    python apps/vocabulary.py merge --input out1.txt --input2 out2.txt --output overall.txt
    python apps/vocabulary.py produce --input overall.txt --pronunciation pron.txt --output out.json
    python apps/vocabulary.py --gui
"""
from __future__ import annotations

import argparse
import os
import sys
import tkinter as tk
from tkinter import ttk

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils_lib import vocabulary  # noqa: E402
from utils_lib.gui_common import (  # noqa: E402
    make_field,
    make_output,
    make_window,
    run_async,
    set_output,
)


def run_cli(args: argparse.Namespace) -> int:
    if args.action in ("process1", "process2"):
        vocabulary.process_raw(args.input, args.output)
    elif args.action == "merge":
        vocabulary.merge(args.input, args.input2, args.output)
    elif args.action == "produce":
        vocabulary.produce(args.input, args.pronunciation, args.output)
    return 0


def run_gui() -> int:
    root = make_window("Vocabulary Pipeline")

    action_var = tk.StringVar(value="produce")
    action_frame = ttk.Frame(root)
    action_frame.pack(side="top", fill="x", pady=4)
    ttk.Label(action_frame, text="Action:").pack(side="left")
    for a in ("process1", "process2", "merge", "produce"):
        ttk.Radiobutton(action_frame, text=a, variable=action_var, value=a).pack(side="left")

    _, input_var = make_field(root, "Input:", "file")
    _, input2_var = make_field(root, "Input 2 (merge):", "file")
    _, pron_var = make_field(root, "Pronunciation (produce):", "file")
    _, output_var = make_field(root, "Output:", "save")
    text = make_output(root)
    set_output(text, "GRE Vocabulary Pipeline\n=======================\nProcesses raw vocabulary files into a final JSON with pronunciations.\n\nHow to use:\n  Step 1 - Clean: pick a raw text file, clean it into a word-definition list.\n  Step 2 - Merge: combine two cleaned files, keeping the longer definition per word.\n  Step 3 - Produce: combine merged text with a pronunciation file to output gre.json.\n\nExpected result:\n  Step 1 outputs a cleaned text file.\n  Step 2 outputs a merged text file.\n  Step 3 outputs gre.json with {word, definition, pronunciation} entries.")

    def on_run(log) -> None:
        a = action_var.get()
        if a in ("process1", "process2"):
            n = vocabulary.process_raw(input_var.get(), output_var.get())
            log(f"Wrote {n} entries to {output_var.get()}")
        elif a == "merge":
            n = vocabulary.merge(input_var.get(), input2_var.get(), output_var.get())
            log(f"Merged {n} entries to {output_var.get()}")
        elif a == "produce":
            n = vocabulary.produce(input_var.get(), pron_var.get(), output_var.get())
            log(f"Wrote JSON ({n} words) to {output_var.get()}")

    ttk.Button(root, text="Run", command=lambda: run_async(text, on_run)).pack(pady=4)
    root.mainloop()
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="GRE vocabulary raw -> text -> JSON pipeline")
    sub = p.add_subparsers(dest="action")

    for name in ("process1", "process2"):
        sp = sub.add_parser(name)
        sp.add_argument("--input", required=True)
        sp.add_argument("--output", required=True)

    sp = sub.add_parser("merge")
    sp.add_argument("--input", required=True)
    sp.add_argument("--input2", required=True)
    sp.add_argument("--output", required=True)

    sp = sub.add_parser("produce")
    sp.add_argument("--input", required=True)
    sp.add_argument("--pronunciation", required=True)
    sp.add_argument("--output", required=True)

    args = p.parse_args(argv)
    if not args.action:
        return run_gui()
    return run_cli(args)


if __name__ == "__main__":
    sys.exit(main())


