#!/usr/bin/env python3
"""Video bitrate & codec scanner - standalone program.

Scans a folder for video files and lists, for each file:
  - video codec (H.264 / H.265 / other)
  - video bitrate
  - total bitrate, duration, file size

Requires ffmpeg (ffprobe). If ffprobe is not found on PATH, the GUI lets you
point to ffprobe.exe manually (the choice is remembered for next time).

Usage:
    python apps/video_bitrate.py                          # GUI
    python apps/video_bitrate.py <directory> [--recursive] [--output out.csv] [--jobs 4]
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from concurrent.futures import ThreadPoolExecutor, as_completed
from tkinter import filedialog, messagebox, ttk

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils_lib import common  # noqa: E402
from utils_lib.gui_common import make_field, make_window  # noqa: E402

VIDEO_EXTS = {
    ".mp4", ".mkv", ".avi", ".mov", ".flv", ".wmv", ".ts", ".m2ts",
    ".webm", ".m4v", ".rmvb", ".rm", ".3gp", ".mpg", ".mpeg", ".vob",
    ".ogv", ".asf", ".f4v", ".divx", ".tp", ".mts",
}

CODEC_NAMES = {
    "h264": "H.264 (AVC)", "avc1": "H.264 (AVC)",
    "hevc": "H.265 (HEVC)", "h265": "H.265 (HEVC)",
    "vp9": "VP9", "av1": "AV1", "mpeg4": "MPEG-4",
    "mpeg2video": "MPEG-2", "vp8": "VP8", "prores": "ProRes",
    "mjpeg": "MJPEG",
}

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           ".video_bitrate_ffprobe.json")


# --------------------------------------------------------------------------- #
# ffprobe discovery
# --------------------------------------------------------------------------- #
def find_ffprobe() -> str | None:
    """Find ffprobe: PATH first, then common install locations."""
    exe = shutil.which("ffprobe")
    if exe:
        return exe
    candidates = [
        r"C:\ffmpeg\bin\ffprobe.exe",
        r"C:\Program Files\ffmpeg\bin\ffprobe.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Links\ffprobe.exe"),
        os.path.expandvars(r"%USERPROFILE%\scoop\shims\ffprobe.exe"),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None


def load_saved_ffprobe() -> str | None:
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("ffprobe") or None
    except (OSError, ValueError):
        return None


def save_ffprobe(path: str) -> None:
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({"ffprobe": path}, f)
    except OSError:
        pass


def resolve_ffprobe() -> str | None:
    """Order: saved choice -> PATH -> common locations."""
    saved = load_saved_ffprobe()
    if saved and os.path.isfile(saved):
        return saved
    return find_ffprobe()


# --------------------------------------------------------------------------- #
# Probing
# --------------------------------------------------------------------------- #
def _to_int(value) -> int | None:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def probe_one(path: str, ffprobe: str) -> dict:
    """Probe a single video file; return a dict of displayable info."""
    info = {
        "name": os.path.basename(path),
        "path": path,
        "codec": "",            # h264 / h265 / other codec id / unknown
        "vcodec": "",            # raw codec name
        "vbitrate": None,        # bps
        "total_bitrate": None,   # bps
        "duration": None,        # seconds
        "size": os.path.getsize(path),
        "error": "",
    }
    try:
        r = subprocess.run(
            [ffprobe, "-v", "quiet", "-print_format", "json",
             "-show_streams", "-show_format", path],
            capture_output=True, text=True, timeout=120,
        )
        if r.returncode != 0:
            info["error"] = (r.stderr or "").strip()[:200] or "ffprobe failed"
            return info
        data = json.loads(r.stdout or "{}")
        streams = data.get("streams", [])
        fmt = data.get("format", {})
        vs = next((s for s in streams if s.get("codec_type") == "video"), None)
        if vs:
            info["vcodec"] = vs.get("codec_name", "").lower()
            info["vbitrate"] = _to_int(vs.get("bit_rate"))
        info["total_bitrate"] = _to_int(fmt.get("bit_rate"))
        try:
            dur = float((vs or {}).get("duration") or fmt.get("duration") or 0) or None
        except (TypeError, ValueError):
            dur = None
        info["duration"] = dur
        try:
            info["size"] = int(float(fmt.get("size") or 0)) or info["size"]
        except (TypeError, ValueError):
            pass
        # Estimate missing bitrates from size / duration.
        if not info["vbitrate"] and dur:
            info["vbitrate"] = int(info["size"] * 8 / dur)
        if not info["total_bitrate"] and dur:
            info["total_bitrate"] = int(info["size"] * 8 / dur)
        c = info["vcodec"]
        if c in ("h264", "avc1"):
            info["codec"] = "h264"
        elif c in ("hevc", "h265"):
            info["codec"] = "h265"
        else:
            info["codec"] = c or "unknown"
    except subprocess.TimeoutExpired:
        info["error"] = "probe timed out (>120s)"
    except Exception as e:  # noqa: BLE001
        info["error"] = str(e)[:200]
    return info


# --------------------------------------------------------------------------- #
# Formatting helpers
# --------------------------------------------------------------------------- #
def codec_display(info: dict) -> str:
    if info["error"]:
        return "FAILED"
    return CODEC_NAMES.get(info["vcodec"], info["vcodec"].upper() or "unknown")


def format_duration(seconds) -> str:
    if not seconds:
        return "-"
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def format_bitrate(bps) -> str:
    if not bps:
        return "-"
    if bps >= 1_000_000:
        return f"{bps / 1_000_000:.2f} Mbps"
    return f"{bps / 1000:.0f} kbps"


def format_size(size) -> str:
    if not size:
        return "-"
    v, unit = common.format_size(size)
    return f"{v:.1f} {unit}"


def collect_videos(directory: str, recursive: bool) -> list:
    files = common.iter_files(directory, recursive)
    return sorted(
        (p for p in files if os.path.splitext(p)[1].lower() in VIDEO_EXTS),
        key=lambda p: os.path.basename(p).lower(),
    )


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def run_cli(args: argparse.Namespace) -> int:
    ffprobe = resolve_ffprobe()
    if not ffprobe:
        print("Error: ffprobe not found. Install ffmpeg (https://ffmpeg.org/download.html)")
        print("or put ffprobe.exe somewhere on PATH, or run without arguments to use the GUI.")
        return 1

    videos = collect_videos(args.directory, args.recursive)
    if not videos:
        print(f"No video files found in {args.directory}")
        return 0

    print(f"Probing {len(videos)} files with {args.jobs} threads...\n")
    results = []
    with ThreadPoolExecutor(max_workers=args.jobs) as ex:
        futs = [ex.submit(probe_one, p, ffprobe) for p in videos]
        for fut in as_completed(futs):
            results.append(fut.result())
    results.sort(key=lambda r: r["name"].lower())

    name_w = max(len(r["name"]) for r in results)
    codec_w = max(18, max(len(codec_display(r)) for r in results))
    header = (f"{'File':<{name_w}}  {'Codec':<{codec_w}}  {'Video bitrate':>13}  "
              f"{'Total':>10}  {'Duration':>9}  {'Size':>9}")
    print("=" * len(header))
    print(header)
    print("=" * len(header))
    for r in results:
        if r["error"]:
            print(f"{r['name']:<{name_w}}  FAILED: {r['error']}")
            continue
        print(f"{r['name']:<{name_w}}  {codec_display(r):<{codec_w}}  "
              f"{format_bitrate(r['vbitrate']):>13}  {format_bitrate(r['total_bitrate']):>10}  "
              f"{format_duration(r['duration']):>9}  {format_size(r['size']):>9}")
    print("=" * len(header))

    ok = [r for r in results if not r["error"]]
    h264 = sum(1 for r in ok if r["codec"] == "h264")
    h265 = sum(1 for r in ok if r["codec"] == "h265")
    other = sum(1 for r in ok if r["codec"] not in ("h264", "h265"))
    failed = len(results) - len(ok)
    total_size = sum(r["size"] for r in ok)
    total_dur = sum(r["duration"] or 0 for r in ok)
    print(f"\n{len(results)} files | H.264: {h264} | H.265: {h265} | other: {other}"
          + (f" | failed: {failed}" if failed else ""))
    if ok:
        print(f"Total size: {format_size(total_size)} | Total duration: {format_duration(total_dur)}")

    if args.output:
        write_csv(args.output, results)
        print(f"CSV exported to: {os.path.abspath(args.output)}")
    return 0


def write_csv(path: str, results: list) -> None:
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["File", "Codec", "Video bitrate (Mbps)", "Total bitrate (Mbps)",
                    "Duration (s)", "Size (bytes)", "Error"])
        for r in results:
            w.writerow([
                r["name"], codec_display(r),
                f"{r['vbitrate'] / 1_000_000:.2f}" if r["vbitrate"] else "",
                f"{r['total_bitrate'] / 1_000_000:.2f}" if r["total_bitrate"] else "",
                f"{r['duration']:.1f}" if r["duration"] else "",
                r["size"], r["error"],
            ])


# --------------------------------------------------------------------------- #
# GUI
# --------------------------------------------------------------------------- #
class _App:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.ffprobe = resolve_ffprobe()
        self.q: "queue.Queue[tuple]" = queue.Queue()
        self.results: list = []
        self.info_by_iid: dict = {}

        self.dir_var = tk.StringVar()
        self.recursive_var = tk.BooleanVar(value=False)
        self.jobs_var = tk.IntVar(value=4)
        self.status_var = tk.StringVar(value="")
        self.summary_var = tk.StringVar(value="")

        self._build_ui()

    def _build_ui(self) -> None:
        r = self.root

        # Folder row (shared helper; keep our own var bound to its entry).
        _, var = make_field(r, "Folder:", "dir")
        self.dir_var = var

        # Options + actions row.
        row = ttk.Frame(r)
        row.pack(side="top", fill="x", pady=4)
        ttk.Checkbutton(row, text="Recurse subfolders", variable=self.recursive_var).pack(side="left", padx=4)
        ttk.Button(row, text="Scan", command=self.start_scan).pack(side="left", padx=4)
        ttk.Button(row, text="Export CSV...", command=self.export_csv).pack(side="left", padx=4)
        ttk.Button(row, text="Set ffprobe...", command=self.set_ffprobe).pack(side="left", padx=4)
        ttk.Label(row, text="Threads:", padding=(8, 0, 0, 0)).pack(side="left")
        ttk.Spinbox(row, from_=1, to=32, textvariable=self.jobs_var, width=4).pack(side="left")

        # Progress bar + status line.
        prog_row = ttk.Frame(r)
        prog_row.pack(side="top", fill="x", pady=(6, 0))
        self.progress = ttk.Progressbar(prog_row, mode="determinate")
        self.progress.pack(side="left", fill="x", expand=True, padx=(4, 8))
        ttk.Label(r, textvariable=self.status_var).pack(side="top", fill="x", padx=4)

        # Results table.
        cols = ("name", "codec", "vbitrate", "total", "duration", "size")
        heads = {"name": "File", "codec": "Video codec", "vbitrate": "Video bitrate",
                 "total": "Total bitrate", "duration": "Duration", "size": "Size"}
        widths = {"name": 300, "codec": 130, "vbitrate": 110,
                  "total": 110, "duration": 80, "size": 110}
        anchors = {"name": "w", "codec": "center", "vbitrate": "e",
                   "total": "e", "duration": "center", "size": "e"}
        table_frame = ttk.Frame(r)
        table_frame.pack(side="top", fill="both", expand=True, padx=4, pady=4)
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings")
        for c in cols:
            self.tree.heading(c, text=heads[c])
            self.tree.column(c, width=widths[c], anchor=anchors[c], stretch=(c == "name"))
        scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)
        self.tree.bind("<Double-1>", self.open_selected)

        # Summary bar.
        ttk.Label(r, textvariable=self.summary_var, padding=(4, 2)).pack(side="top", fill="x")

        if not self.ffprobe:
            self.status_var.set("ffprobe not found - install ffmpeg or click 'Set ffprobe...'")
        else:
            self.status_var.set(f"ffprobe: {self.ffprobe}")

        self.root.after(100, self._poll)

    # ---- actions --------------------------------------------------------- #
    def start_scan(self) -> None:
        d = self.dir_var.get().strip()
        if not d or not os.path.isdir(d):
            messagebox.showwarning("Video Bitrate Scanner", "Pick an existing folder first.")
            return
        if not self.ffprobe:
            ans = messagebox.askyesno(
                "ffprobe not found",
                "ffprobe was not found. ffmpeg (which includes ffprobe) is required.\n\n"
                "Open the ffmpeg download page now?",
            )
            if ans:
                import webbrowser
                webbrowser.open("https://ffmpeg.org/download.html")
            return

        self.tree.delete(*self.tree.get_children())
        self.info_by_iid.clear()
        self.results = []
        self.summary_var.set("")
        self.progress["value"] = 0
        threading.Thread(target=self._scan_worker, args=(d,), daemon=True).start()

    def _scan_worker(self, directory: str) -> None:
        try:
            videos = collect_videos(directory, self.recursive_var.get())
        except OSError as e:
            self.q.put(("status", f"Error reading folder: {e}"))
            self.q.put(("done",))
            return
        total = len(videos)
        if total == 0:
            self.q.put(("status", "No video files found in this folder."))
            self.q.put(("done",))
            return
        self.q.put(("status", f"Found {total} video files, probing..."))
        done = 0
        with ThreadPoolExecutor(max_workers=self.jobs_var.get()) as ex:
            futs = [ex.submit(probe_one, p, self.ffprobe) for p in videos]
            for fut in as_completed(futs):
                info = fut.result()
                done += 1
                self.q.put(("progress", done, total, info["name"]))
                self.q.put(("result", info))
        self.q.put(("done",))

    def export_csv(self) -> None:
        if not self.results:
            messagebox.showinfo("Video Bitrate Scanner", "Nothing to export yet - run a scan first.")
            return
        from datetime import datetime
        default = f"video_bitrate_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        path = filedialog.asksaveasfilename(
            title="Export CSV", defaultextension=".csv",
            initialfile=default, filetypes=[("CSV files", "*.csv")],
        )
        if not path:
            return
        try:
            write_csv(path, self.results)
        except OSError as e:
            messagebox.showerror("Video Bitrate Scanner", f"Could not write CSV:\n{e}")
            return
        self.status_var.set(f"Exported: {path}")

    def set_ffprobe(self) -> None:
        path = filedialog.askopenfilename(
            title="Select ffprobe.exe", filetypes=[("ffprobe", "ffprobe.exe"), ("All files", "*.*")],
        )
        if not path:
            return
        self.ffprobe = path
        save_ffprobe(path)
        self.status_var.set(f"ffprobe: {path}")

    def open_selected(self, _event=None) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        info = self.info_by_iid.get(sel[0])
        if not info:
            return
        subprocess.Popen(["explorer", "/select,", info["path"]])

    # ---- queue pumping ---------------------------------------------------- #
    def _poll(self) -> None:
        try:
            while True:
                msg = self.q.get_nowait()
                kind = msg[0]
                if kind == "progress":
                    _, done, total, name = msg
                    self.progress["maximum"] = total
                    self.progress["value"] = done
                    self.status_var.set(f"Probing... {done}/{total}  {name}")
                elif kind == "result":
                    self.results.append(msg[1])
                elif kind == "status":
                    self.status_var.set(msg[1])
                elif kind == "done":
                    self._finish_scan()
                    return
        except queue.Empty:
            pass
        self.root.after(100, self._poll)

    def _finish_scan(self) -> None:
        self.progress["value"] = self.progress["maximum"]
        self.results.sort(key=lambda r: r["name"].lower())
        for info in self.results:
            iid = self.tree.insert("", "end", values=(
                info["name"], codec_display(info),
                format_bitrate(info["vbitrate"]), format_bitrate(info["total_bitrate"]),
                format_duration(info["duration"]), format_size(info["size"]),
            ))
            self.info_by_iid[iid] = info

        ok = [r for r in self.results if not r["error"]]
        h264 = sum(1 for r in ok if r["codec"] == "h264")
        h265 = sum(1 for r in ok if r["codec"] == "h265")
        other = sum(1 for r in ok if r["codec"] not in ("h264", "h265"))
        failed = len(self.results) - len(ok)
        total_size = sum(r["size"] for r in ok)
        total_dur = sum(r["duration"] or 0 for r in ok)
        parts = [f"{len(self.results)} files", f"H.264: {h264}", f"H.265: {h265}",
                 f"other: {other}"]
        if failed:
            parts.append(f"failed: {failed}")
        if ok:
            parts.append(f"size: {format_size(total_size)}")
            parts.append(f"duration: {format_duration(total_dur)}")
        self.summary_var.set("  |  ".join(parts))
        self.status_var.set("Done.")


def run_gui() -> int:
    root = make_window("Video Bitrate & Codec Scanner", 960, 620)
    _App(root)
    root.mainloop()
    return 0


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #
def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Video bitrate & codec scanner")
    p.add_argument("directory", nargs="?", help="folder to scan (GUI if omitted)")
    p.add_argument("-r", "--recursive", action="store_true", help="recurse into subfolders")
    p.add_argument("-o", "--output", metavar="CSV", help="also export results to a CSV file")
    p.add_argument("-j", "--jobs", type=int, default=4, help="parallel probe threads (default 4)")
    args = p.parse_args(argv)
    if not args.directory:
        return run_gui()
    return run_cli(args)


if __name__ == "__main__":
    sys.exit(main())
