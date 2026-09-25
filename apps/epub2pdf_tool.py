#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
epub2pdf_tool.py — EPUB to PDF converter (powered by Calibre ebook-convert)

Features:
  * GUI mode: visually pick files/folders for batch conversion, with options
    for paper size, page margins and font size
  * CLI mode: convert single files or whole directories from the command line

Requirements: Python 3.8+ (with tkinter, bundled with the official installer)
and Calibre (provides the ebook-convert engine).

Usage:
  python epub2pdf_tool.py                        # open the GUI (default)
  python epub2pdf_tool.py gui                    # same as above
  python epub2pdf_tool.py in.epub                # convert to in.pdf (same folder)
  python epub2pdf_tool.py in.epub -o out/pdf     # write PDFs into an output folder
  python epub2pdf_tool.py ./books --recursive -o ./out   # batch-convert a tree
  python epub2pdf_tool.py in.epub --paper-size a4 --margin 72 --font-size 12
"""

import argparse
import os
import queue
import shutil
import subprocess
import sys
import threading
from pathlib import Path

APP_NAME = "EPUB to PDF Tool"
VERSION = "1.2.0"

# ---------------------------------------------------------------------------
# Calibre detection and core conversion
# ---------------------------------------------------------------------------

_CALIBRE_CANDIDATES = [
    # Windows
    r"C:\Program Files\Calibre2\ebook-convert.exe",
    r"C:\Program Files (x86)\Calibre2\ebook-convert.exe",
    # macOS
    "/Applications/calibre.app/Contents/MacOS/ebook-convert",
    "/Applications/calibre.app/Contents/MacOS/calibre/ebook-convert",
    # Linux
    "/usr/bin/ebook-convert",
    "/usr/local/bin/ebook-convert",
    "/opt/calibre/ebook-convert",
]


def find_ebook_convert():
    """Locate ebook-convert in PATH and common install dirs; return path or None."""
    found = shutil.which("ebook-convert")
    if found:
        return found
    for candidate in _CALIBRE_CANDIDATES:
        if os.path.isfile(candidate):
            return candidate
    return None


def calibre_install_hint(platform_name=None):
    if platform_name is None:
        platform_name = sys.platform
    if platform_name.startswith("win"):
        return ("Download and install the Windows build from "
                "https://calibre-ebook.com/download (no setup needed afterwards)")
    if platform_name == "darwin":
        return ("Run `brew install calibre` or download the macOS build from "
                "https://calibre-ebook.com/download")
    return ("Run `sudo apt install calibre` (Debian/Ubuntu) or "
            "`sudo dnf install calibre` (Fedora), or see https://calibre-ebook.com/download")


def convert_one(epub_path, pdf_path, converter, paper_size=None, margin=None,
                font_size=None, timeout=600):
    """Convert a single EPUB to PDF via ebook-convert.

    Returns (ok, message). When ok is True, message holds the output PDF path.
    """
    if not os.path.isfile(epub_path):
        return False, "Input file does not exist"
    cmd = [converter, os.path.abspath(epub_path), os.path.abspath(pdf_path)]
    if paper_size:
        cmd += ["--paper-size", paper_size]
    if margin is not None and margin != "":
        cmd += ["--pdf-page-margin-left", str(margin),
                "--pdf-page-margin-right", str(margin),
                "--pdf-page-margin-top", str(margin),
                "--pdf-page-margin-bottom", str(margin)]
    if font_size is not None and font_size != "":
        cmd += ["--pdf-default-font-size", str(font_size)]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=timeout
        )
    except subprocess.TimeoutExpired:
        return False, "Conversion timed out (over %s seconds)" % timeout
    except OSError as exc:
        return False, "Could not launch ebook-convert: %s" % exc
    if proc.returncode != 0:
        # Keep the last few lines of error output for diagnosis
        tail = [ln for ln in (proc.stderr or "").splitlines() if ln.strip()]
        msg = (proc.stdout or "").strip()
        if not msg and tail:
            msg = "\n".join(tail[-3:])
        if not msg:
            msg = "Unknown error"
        return False, msg
    if os.path.isfile(pdf_path):
        return True, pdf_path
    return False, "Command finished but the output file was not found"


def collect_epub_files(paths, recursive=False):
    """Collect EPUB files from the given files/folders."""
    files = []
    for p in paths:
        p = Path(p)
        if p.is_file():
            if p.suffix.lower() == ".epub":
                files.append(p)
            else:
                print("[skip] not an EPUB file: %s" % p)
        elif p.is_dir():
            pattern = "**/*.epub" if recursive else "*.epub"
            found = sorted(p.glob(pattern))
            if not found:
                print("[note] no EPUB files found in: %s" % p)
            files.extend(found)
        else:
            print("[error] path does not exist: %s" % p)
    # Deduplicate while preserving order
    seen, result = set(), []
    for f in files:
        key = os.path.normcase(str(f.resolve()))
        if key not in seen:
            seen.add(key)
            result.append(f)
    return result


def run_batch(files, out_dir, converter, paper_size, margin, font_size,
              overwrite=False, delete_source=False, status_cb=None, stop_event=None):
    """Batch conversion. status_cb(index, total, file, stage, ok, message) drives progress."""
    results = []
    total = len(files)
    if out_dir is not None:
        out_dir = Path(out_dir)
    for i, epub in enumerate(files, start=1):
        if stop_event is not None and stop_event.is_set():
            break
        # Output path: same folder and base name as the source, or inside out_dir
        if out_dir:
            out_dir.mkdir(parents=True, exist_ok=True)
            pdf = out_dir / (epub.stem + ".pdf")
        else:
            pdf = epub.with_suffix(".pdf")
        if pdf.exists() and not overwrite:
            if status_cb:
                status_cb(i, total, epub, "skip", True, "Already exists, skipped (use --overwrite to force)")
            results.append((epub, pdf, True, "Already exists, skipped"))
            continue
        if status_cb:
            status_cb(i, total, epub, "convert", None, "Converting...")
        ok, msg = convert_one(str(epub), str(pdf), converter,
                              paper_size=paper_size, margin=margin,
                              font_size=font_size)
        if status_cb:
            status_cb(i, total, epub, "done", ok, msg)
        results.append((epub, pdf, ok, msg))
        if ok and delete_source:
            try:
                epub.unlink()
            except OSError as exc:
                print("[warning] failed to delete source file: %s (%s)" % (epub, exc))
    return results


# ---------------------------------------------------------------------------
# CLI mode
# ---------------------------------------------------------------------------

def cmd_convert(args):
    converter = find_ebook_convert()
    if not converter:
        print("[error] Calibre's ebook-convert was not found. %s" % calibre_install_hint())
        sys.exit(1)
    files = collect_epub_files(args.inputs, recursive=args.recursive)
    if not files:
        print("[error] No EPUB files to convert.")
        sys.exit(1)
    print("Conversion engine: %s" % converter)
    print("Converting %d file(s)..." % len(files))
    stop_event = threading.Event()  # CLI runs uninterruptibly; kept for a shared interface

    def cb(i, total, epub, stage, ok, msg):
        name = epub.name
        if stage == "convert":
            print("  [%d/%d] %s ..." % (i, total, name), end="", flush=True)
        elif stage == "done":
            if ok:
                print(" OK -> %s" % msg)
            else:
                print(" failed: %s" % msg)
        elif stage == "skip":
            print("  [%d/%d] %s skipped: %s" % (i, total, name, msg))

    results = run_batch(files, args.output, converter, args.paper_size,
                        args.margin, args.font_size,
                        overwrite=args.overwrite, delete_source=args.delete_source,
                        status_cb=cb, stop_event=stop_event)
    ok_count = sum(1 for _, _, ok, _ in results if ok)
    print("Done: %d succeeded, %d skipped/failed out of %d." % (ok_count, len(results) - ok_count, len(results)))
    if ok_count < len(results):
        print("Failures:")
        for epub, pdf, ok, msg in results:
            if not ok:
                print("  - %s: %s" % (epub.name, msg))
        sys.exit(2)
    sys.exit(0)


# ---------------------------------------------------------------------------
# GUI mode (tkinter)
# ---------------------------------------------------------------------------

def cmd_gui(args):
    try:
        import tkinter as tk
        from tkinter import ttk, filedialog, messagebox
    except ImportError:
        print("[error] tkinter is not available in this Python. "
              "Install Python with tkinter, or use command-line mode.")
        sys.exit(1)

    initial_converter = find_ebook_convert()  # may be None; warned on startup

    class App(tk.Tk):
        def __init__(self):
            super().__init__()
            self.title("%s v%s" % (APP_NAME, VERSION))
            self.geometry("820x580")
            self.minsize(720, 500)

            # High-DPI scaling on Windows
            try:
                self.tk.call("tk", "scaling", 1.5 if os.name == "nt" else 1.0)
            except Exception:
                pass

            self.converter = initial_converter
            self.file_queue = queue.Queue()
            self.busy = False
            self.stop_event = threading.Event()
            self._success_epubs = []  # source EPUBs of files converted successfully

            self._build_ui()
            self.after(150, self._poll_queue)

            if not self.converter:
                if os.environ.get("EPUB2PDF_TEST_GUI") == "1":
                    self._log("[test mode] Calibre not found, skipping prompt")
                else:
                    messagebox.showwarning(
                        APP_NAME,
                        "Calibre (ebook-convert) was not found.\n\n"
                        "Please install Calibre first:\n%s\n\n"
                        "Click \"Refresh\" once installed." % calibre_install_hint()
                    )

        # ---------------- UI ----------------
        def _build_ui(self):
            pad = {"padx": 10, "pady": 6}

            # Top bar: engine status
            top = ttk.Frame(self)
            top.pack(fill="x", **pad)
            ttk.Label(top, text="Conversion engine:").pack(side="left")
            self.engine_label = tk.Label(
                top, text=self.converter or "Calibre not found",
                fg="#1a7f37" if self.converter else "#c0392b")
            self.engine_label.pack(side="left")
            ttk.Button(top, text="Refresh", command=self._refresh_engine).pack(side="right")

            # File area
            files_frame = ttk.LabelFrame(self, text="EPUB files")
            files_frame.pack(fill="both", expand=True, **pad)
            toolbar = ttk.Frame(files_frame)
            toolbar.pack(fill="x", padx=6, pady=4)
            ttk.Button(toolbar, text="Add files...", command=self._add_files).pack(side="left")
            ttk.Button(toolbar, text="Add folder...", command=self._add_folder).pack(side="left", padx=4)
            ttk.Button(toolbar, text="Remove selected", command=self._remove_selected).pack(side="left")
            ttk.Button(toolbar, text="Clear list", command=self._clear_files).pack(side="left", padx=4)
            ttk.Label(toolbar, text="(adds EPUBs in subfolders too)").pack(side="left", padx=8)
            self.file_list = tk.Listbox(files_frame, selectmode="extended", height=10)
            self.file_list.pack(fill="both", expand=True, padx=6, pady=4)
            self.file_scroll = ttk.Scrollbar(files_frame, orient="vertical",
                                             command=self.file_list.yview)
            self.file_list.configure(yscrollcommand=self.file_scroll.set)
            self.file_scroll.pack(side="right", fill="y")

            # Options area
            opts = ttk.LabelFrame(self, text="Conversion options (empty = Calibre defaults)")
            opts.pack(fill="x", **pad)
            grid = ttk.Frame(opts)
            grid.pack(fill="x", padx=6, pady=6)
            grid.columnconfigure(1, weight=1)
            ttk.Label(grid, text="Output folder:").grid(row=0, column=0, sticky="w")
            self.out_var = tk.StringVar()
            ttk.Entry(grid, textvariable=self.out_var).grid(row=0, column=1, sticky="ew", padx=4)
            ttk.Button(grid, text="Browse...", command=self._choose_outdir).grid(row=0, column=2)

            ttk.Label(grid, text="Paper size:").grid(row=1, column=0, sticky="w", pady=4)
            self.paper_var = tk.StringVar(value="")
            papers = ["", "a4", "letter", "legal", "a5", "b5"]
            ttk.Combobox(grid, textvariable=self.paper_var, values=papers,
                         state="readonly", width=18).grid(row=1, column=1, sticky="w", padx=4)
            ttk.Label(grid, text="Margins (pt):").grid(row=1, column=2, sticky="w")
            self.margin_var = tk.StringVar(value="")
            ttk.Entry(grid, textvariable=self.margin_var, width=10).grid(row=1, column=3, sticky="w", padx=4)
            ttk.Label(grid, text="Font size (pt):").grid(row=1, column=4, sticky="w")
            self.font_var = tk.StringVar(value="")
            ttk.Entry(grid, textvariable=self.font_var, width=10).grid(row=1, column=5, sticky="w", padx=4)

            self.overwrite_var = tk.BooleanVar(value=False)
            ttk.Checkbutton(grid, text="Overwrite existing PDFs", variable=self.overwrite_var)\
                .grid(row=2, column=0, columnspan=3, sticky="w", pady=4)
            ttk.Label(grid, text="Output folder left empty = PDFs go next to the source EPUB")\
                .grid(row=2, column=3, columnspan=3, sticky="w", padx=8)

            # Bottom: progress + actions
            bottom = ttk.Frame(self)
            bottom.pack(fill="x", **pad)
            self.progress = ttk.Progressbar(bottom, maximum=100)
            self.progress.pack(fill="x")
            self.status_var = tk.StringVar(value="Ready")
            ttk.Label(bottom, textvariable=self.status_var).pack(fill="x", pady=4)
            btns = ttk.Frame(bottom)
            btns.pack(fill="x")
            self.start_btn = ttk.Button(btns, text="Convert", command=self._start_convert)
            self.start_btn.pack(side="left")
            self.stop_btn = ttk.Button(btns, text="Stop", command=self._stop_convert, state="disabled")
            self.stop_btn.pack(side="left", padx=6)
            self.delete_btn = ttk.Button(btns, text="Delete originals",
                                         command=self._delete_originals, state="disabled")
            self.delete_btn.pack(side="left", padx=6)
            ttk.Button(btns, text="Open output folder", command=self._open_outdir).pack(side="right")

            # Log
            log_frame = ttk.LabelFrame(self, text="Log")
            log_frame.pack(fill="both", expand=False, **pad)
            self.log_text = tk.Text(log_frame, height=6, state="disabled")
            self.log_text.pack(fill="both", expand=True, padx=6, pady=4)

        # ---------------- Helpers ----------------
        def _log(self, text):
            self.log_text.configure(state="normal")
            self.log_text.insert("end", text + "\n")
            self.log_text.see("end")
            self.log_text.configure(state="disabled")

        def _refresh_engine(self):
            conv = find_ebook_convert()
            self.converter = conv
            if conv:
                self.engine_label.configure(text=conv, fg="#1a7f37")
                self._log("Calibre detected: %s" % conv)
            else:
                self.engine_label.configure(text="Calibre not found", fg="#c0392b")
                messagebox.showwarning(
                    APP_NAME,
                    "Calibre still not found. Please install it first:\n%s" % calibre_install_hint())

        def _add_files(self):
            paths = filedialog.askopenfilenames(
                title="Select EPUB files",
                filetypes=[("EPUB ebooks", "*.epub"), ("All files", "*.*")])
            for p in paths:
                if p.lower().endswith(".epub"):
                    self.file_list.insert("end", p)

        def _add_folder(self):
            folder = filedialog.askdirectory(title="Select a folder containing EPUBs")
            if not folder:
                return
            for p in sorted(Path(folder).rglob("*.epub")):
                self.file_list.insert("end", str(p))

        def _remove_selected(self):
            for idx in reversed(self.file_list.curselection()):
                self.file_list.delete(idx)

        def _clear_files(self):
            self.file_list.delete(0, "end")

        def _choose_outdir(self):
            folder = filedialog.askdirectory(title="Select PDF output folder")
            if folder:
                self.out_var.set(folder)

        def _open_outdir(self):
            out = self.out_var.get().strip()
            target = out if out and os.path.isdir(out) else None
            if target:
                os.startfile(target) if os.name == "nt" else subprocess.Popen(["open", target])
            else:
                messagebox.showinfo(APP_NAME, "Please choose an output folder first.")

        # ---------------- Conversion ----------------
        def _start_convert(self):
            if self.busy:
                return
            if not self.converter:
                messagebox.showerror(APP_NAME, "Calibre not found, cannot convert. %s" % calibre_install_hint())
                return
            files = [self.file_list.get(i) for i in range(self.file_list.size())]
            files = [f for f in files if f.lower().endswith(".epub")]
            if not files:
                messagebox.showwarning(APP_NAME, "Please add EPUB files first.")
                return
            out_dir = self.out_var.get().strip() or None
            self._success_epubs = []
            self.delete_btn.configure(state="disabled", text="Delete originals")
            self.busy = True
            self.stop_event.clear()
            self.start_btn.configure(state="disabled")
            self.stop_btn.configure(state="normal")
            self.progress.configure(value=0)
            self._log("Converting %d file(s)..." % len(files))
            thread = threading.Thread(
                target=self._worker,
                args=(files, out_dir, self.converter,
                      self.paper_var.get().strip(), self.margin_var.get().strip(),
                      self.font_var.get().strip(), self.overwrite_var.get()),
                daemon=True)
            thread.start()

        def _worker(self, files, out_dir, converter, paper, margin, font, overwrite):
            results = run_batch(
                [Path(f) for f in files],
                Path(out_dir) if out_dir else None,
                converter,
                paper_size=paper or None,
                margin=margin or None,
                font_size=font or None,
                overwrite=overwrite,
                status_cb=lambda i, total, epub, stage, ok, msg: self.file_queue.put(
                    ("item", i, total, str(epub), stage, ok, msg)),
                stop_event=self.stop_event,
            )
            self.file_queue.put(("done", results))

        def _poll_queue(self):
            try:
                while True:
                    item = self.file_queue.get_nowait()
                    kind = item[0]
                    if kind == "item":
                        _, i, total, epub, stage, ok, msg = item
                        if stage == "convert":
                            self.status_var.set("Converting [%d/%d] %s" % (i, total, os.path.basename(epub)))
                            self.progress.configure(value=(i - 1) * 100.0 / total)
                        elif stage == "done":
                            self.progress.configure(value=i * 100.0 / total)
                            if ok:
                                self._log("OK [%d/%d] %s -> %s" % (i, total, os.path.basename(epub), msg))
                            else:
                                self._log("Failed [%d/%d] %s: %s" % (i, total, os.path.basename(epub), msg))
                        elif stage == "skip":
                            self._log("Skipped [%d/%d] %s: %s" % (i, total, os.path.basename(epub), msg))
                    elif kind == "done":
                        _, results = item
                        ok_count = sum(1 for _, _, ok, _ in results if ok)
                        self.busy = False
                        self.start_btn.configure(state="normal")
                        self.stop_btn.configure(state="disabled")
                        self.status_var.set("Done: %d succeeded / %d total" % (ok_count, len(results)))
                        self._log("All done: %d succeeded, %d others." % (ok_count, len(results) - ok_count))
                        # Enable deletion of originals only after results can be reviewed
                        self._success_epubs = [epub for epub, _, ok, _ in results if ok]
                        if self._success_epubs:
                            self.delete_btn.configure(
                                state="normal",
                                text="Delete originals (%d)" % len(self._success_epubs))
            except queue.Empty:
                pass
            self.after(150, self._poll_queue)

        def _stop_convert(self):
            self.stop_event.set()
            self.status_var.set("Stopping...")

        def _delete_originals(self):
            """Delete source EPUBs of successfully converted files — only on explicit user request.

            Never runs automatically: the user can review the generated PDFs first.
            """
            if self.busy:
                return
            targets = list(self._success_epubs)
            if not targets:
                messagebox.showinfo(APP_NAME, "No successfully converted source files to delete.")
                return
            if not messagebox.askyesno(
                    APP_NAME,
                    "Delete %d source EPUB file(s)?\n\n"
                    "This cannot be undone. Please make sure the converted PDFs look correct first."
                    % len(targets)):
                return
            deleted, failed = [], []
            for p in targets:
                try:
                    p.unlink()
                    deleted.append(p)
                except OSError as exc:
                    failed.append((p, exc))
            # Remove deleted entries from the file list
            deleted_norm = {os.path.normcase(str(p)) for p in deleted}
            remaining = [
                self.file_list.get(i)
                for i in range(self.file_list.size())
                if os.path.normcase(self.file_list.get(i)) not in deleted_norm
            ]
            self.file_list.delete(0, "end")
            for fp in remaining:
                self.file_list.insert("end", fp)
            self._success_epubs = []
            self.delete_btn.configure(state="disabled", text="Delete originals")
            self._log("Deleted %d source file(s)." % len(deleted))
            for p, exc in failed:
                self._log("Failed to delete %s: %s" % (p, exc))

    app = App()
    if os.environ.get("EPUB2PDF_TEST_GUI") == "1":
        # Automated test mode: close the window shortly after opening it
        app.after(600, app.destroy)
    app.mainloop()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv=None):
    args_list = list(sys.argv[1:] if argv is None else argv)
    # Default behavior: no arguments -> launch the GUI
    if not args_list:
        cmd_gui(None)
        return
    # Bare file/folder paths (without a subcommand) are treated as convert
    if args_list[0] not in ("gui", "convert", "-h", "--help"):
        args_list = ["convert"] + args_list

    parser = argparse.ArgumentParser(
        prog="epub2pdf_tool",
        description="EPUB to PDF converter (powered by Calibre ebook-convert), "
                    "with GUI and command-line modes.")
    sub = parser.add_subparsers(dest="mode")

    gui_p = sub.add_parser("gui", help="open the graphical interface")
    gui_p.set_defaults(func=cmd_gui)

    conv_p = sub.add_parser("convert", help="convert from the command line "
                                            "(or pass files directly without a subcommand)")
    conv_p.add_argument("inputs", nargs="+", help="one or more EPUB files or folders")
    conv_p.add_argument("-o", "--output", help="output folder (default: same folder as source)")
    conv_p.add_argument("-r", "--recursive", action="store_true",
                        help="search subfolders for EPUB files")
    conv_p.add_argument("--paper-size", choices=["a4", "letter", "legal", "a5", "b5"],
                        help="PDF paper size")
    conv_p.add_argument("--margin", type=int, help="page margin on all sides (pt)")
    conv_p.add_argument("--font-size", type=int, help="body font size (pt)")
    conv_p.add_argument("--overwrite", action="store_true", help="overwrite existing PDFs")
    conv_p.add_argument("-d", "--delete-source", action="store_true",
                        help="delete the source EPUB after a successful conversion")
    conv_p.set_defaults(func=cmd_convert)

    args = parser.parse_args(args_list)
    args.func(args)


if __name__ == "__main__":
    main()
