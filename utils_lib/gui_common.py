"""Shared Tkinter helpers for the standalone apps under apps/."""
from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Callable, Optional, Tuple


def make_field(parent: tk.Misc, label: str, browse: str = "file") -> Tuple[ttk.Frame, tk.StringVar]:
    """Build a labelled row with an entry and a Browse button.

    browse: "file", "dir", "save", or "" (no button).
    Returns (frame, var).
    """
    frame = ttk.Frame(parent)
    frame.pack(side="top", fill="x", pady=2)
    ttk.Label(frame, text=label, width=18).pack(side="left")
    var = tk.StringVar()
    ttk.Entry(frame, textvariable=var, width=50).pack(side="left", fill="x", expand=True)
    if browse:
        def _browse() -> None:
            if browse == "file":
                path = filedialog.askopenfilename()
            elif browse == "dir":
                path = filedialog.askdirectory()
            elif browse == "save":
                path = filedialog.asksaveasfilename()
            else:
                path = ""
            if path:
                var.set(path)
        ttk.Button(frame, text="Browse...", command=_browse).pack(side="left", padx=4)
    return frame, var


def make_output(parent: tk.Misc) -> tk.Text:
    """Build a read-only, scrollable output Text widget."""
    frame = ttk.Frame(parent)
    frame.pack(side="top", fill="both", expand=True)
    text = tk.Text(frame, wrap="word", font=("Consolas", 10), height=15)
    scroll = ttk.Scrollbar(frame, command=text.yview)
    text.configure(yscrollcommand=scroll.set, state="disabled")
    scroll.pack(side="right", fill="y")
    text.pack(side="left", fill="both", expand=True)
    return text


def append_output(text: tk.Text, msg: str) -> None:
    text.configure(state="normal")
    text.insert("end", msg + "\n")
    text.see("end")
    text.configure(state="disabled")


def set_output(text: tk.Text, msg: str) -> None:
    text.configure(state="normal")
    text.delete("1.0", "end")
    text.insert("end", msg)
    text.see("end")
    text.configure(state="disabled")


def run_async(
    text: tk.Text,
    worker: Callable[[Callable[[str], None]], None],
    on_done: Optional[Callable[[], None]] = None,
) -> None:
    """Run *worker* in a background thread; logs via the Text widget.

    *worker* receives a ``log(msg)`` callable. Messages are pumped to the UI
    thread via a queue.
    """
    q: "queue.Queue[str]" = queue.Queue()

    def _log(msg: str) -> None:
        q.put(msg)

    def _runner() -> None:
        try:
            worker(_log)
        except Exception as e:  # noqa: BLE001
            q.put(f"ERROR: {e}")
        q.put("__DONE__")

    def _pump() -> None:
        try:
            item = q.get_nowait()
        except queue.Empty:
            text.after(100, _pump)
            return
        if item == "__DONE__":
            if on_done:
                on_done()
            return
        append_output(text, item)
        text.after(100, _pump)

    threading.Thread(target=_runner, daemon=True).start()
    _pump()


def make_window(title: str, width: int = 700, height: int = 500) -> tk.Tk:
    root = tk.Tk()
    root.title(title)
    root.geometry(f"{width}x{height}")
    return root
