"""Shared helpers: size formatting, elapsed-time formatting, scanning."""
from __future__ import annotations

import datetime as _dt
import os
import time
from typing import Iterator, List, Optional, Tuple


def format_size(num: float) -> Tuple[float, str]:
    """Format a byte count the same way the Java tool did (binary, B/KiB/...)."""
    size = float(num)
    unit = "B"
    if size >= 1024.0:
        size /= 1024.0
        unit = "KiB"
    if size >= 1024.0:
        size /= 1024.0
        unit = "MiB"
    if size >= 1024.0:
        size /= 1024.0
        unit = "GiB"
    if size >= 1024.0:
        size /= 1024.0
        unit = "TiB"
    if size >= 1024.0:
        size /= 1024.0
        unit = "PiB"
    return size, unit


def format_elapsed_ms(elapsed_ms: int) -> str:
    """Format elapsed milliseconds as HH:MM:SS.mmm (Java style)."""
    elapsed_s = elapsed_ms // 1000
    return f"{elapsed_s // 3600:02d}:{(elapsed_s % 3600) // 60:02d}:{elapsed_s % 60:02d}.{elapsed_ms % 1000:03d}"


class Timer:
    """Context manager that returns wall-clock milliseconds."""

    def __enter__(self) -> "Timer":
        self.start = time.time()
        return self

    def __exit__(self, *exc) -> None:
        self.ms = int((time.time() - self.start) * 1000)


def iter_files(directory: str, include_subfolders: bool) -> Iterator[str]:
    """Yield absolute file paths, mirroring java.io.File.listFiles order.

    When include_subfolders is False, only files directly in `directory` are
    yielded (top-level entries are not recursed into).
    """
    entries = sorted(os.listdir(directory))
    for name in entries:
        path = os.path.join(directory, name)
        if os.path.isdir(path):
            if include_subfolders:
                yield from iter_files(path, include_subfolders)
        else:
            yield path


def yes_no(prompt: str = "Do you want to proceed? (Y/N) ") -> bool:
    """Interactive confirmation. Returns True only on 'Y'."""
    try:
        ans = input(prompt).strip().upper()
    except EOFError:
        return False
    return ans == "Y"


def _cell_to_text(value: object) -> str:
    """Normalise a spreadsheet/CSV cell to a plain string.

    * datetime -> ``YYYY-MM-DD`` (drops the time component)
    * whole floats -> integer string (``100.0`` -> ``"100"``)
    * None -> empty string
    """
    if value is None:
        return ""
    if isinstance(value, _dt.datetime):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, _dt.date):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return str(value)
    return str(value)


def load_table(path: str) -> List[List[str]]:
    """Read a CSV or XLSX file as a list of rows, each a list of strings.

    Recognised extensions:
        * .csv / .txt / .tsv -> split on commas (CSV layout, same as Java)
        * .xlsx -> first sheet via openpyxl

    Old .xls files are not supported (install ``xlrd`` if you need them).
    Empty rows are skipped.
    """
    ext = os.path.splitext(path)[1].lower()
    if ext in (".csv", ".txt", ""):
        with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
            rows: List[List[str]] = []
            for line in f.read().splitlines():
                if not line.strip():
                    continue
                rows.append(line.split(","))
            return rows
    if ext == ".tsv":
        with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
            return [line.split("\t") for line in f.read().splitlines() if line.strip()]
    if ext == ".xlsx":
        try:
            import openpyxl  # type: ignore
        except ImportError as e:
            raise RuntimeError(
                "Reading .xlsx files requires openpyxl. Install it with: pip install openpyxl"
            ) from e
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        ws = wb.active
        rows = []
        for raw_row in ws.iter_rows(values_only=True):
            cells = [_cell_to_text(v) for v in raw_row]
            # Skip fully-empty rows.
            if not any(c != "" for c in cells):
                continue
            rows.append(cells)
        wb.close()
        return rows
    raise ValueError(f"Unsupported table extension: {ext!r}. Use .csv or .xlsx.")
