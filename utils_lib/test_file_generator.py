"""Generate synthetic camera-file sequences for testing.

Mirrors TestFileGenerator.java. Each test creates a folder under
``destination_root`` and touches empty files with the given names.
"""
from __future__ import annotations

import os
from typing import Callable, List, Optional


def generate_files(destination_path: str, file_names: List[str]) -> None:
    os.makedirs(destination_path, exist_ok=True)
    for name in file_names:
        p = os.path.join(destination_path, name)
        try:
            with open(p, "a"):
                os.utime(p, None)
        except OSError:
            pass


def _rng(start: int, stop: int) -> List[str]:
    return [f"{i:05d}.ARW" for i in range(start, stop + 1)]


def test1(root: str) -> None:
    names = _rng(101, 200) + _rng(900, 999)
    generate_files(os.path.join(root, "Test 1"), names)


def test2(root: str) -> None:
    generate_files(os.path.join(root, "Test 2"), _rng(101, 200))


def test3(root: str) -> None:
    names = _rng(101, 200) + _rng(900, 999) + _rng(9900, 9999)
    generate_files(os.path.join(root, "Test 3"), names)


def test4(root: str) -> None:
    names = [f"{101:05d}.ARW"] + _rng(900, 999)
    generate_files(os.path.join(root, "Test 4"), names)


def test5(root: str) -> None:
    names = _rng(101, 200) + [f"{999:05d}.ARW"]
    generate_files(os.path.join(root, "Test 5"), names)


def test6(root: str) -> None:
    names = [f"{101:05d}.ARW", f"{999:05d}.ARW"]
    generate_files(os.path.join(root, "Test 6"), names)


def test7(root: str) -> None:
    names = [f"{101:05d}.ARW", f"{999:05d}.ARW", f"{9909:05d}.ARW"]
    generate_files(os.path.join(root, "Test 7"), names)


def test8(root: str) -> None:
    names: List[str] = []
    for i in range(101, 201):
        names.append(f"{i:05d}.ARW")
        names.append(f"{i:05d}.xmp")
    for i in range(900, 1000):
        names.append(f"{i:05d}.ARW")
        names.append(f"{i:05d}.xmp")
    generate_files(os.path.join(root, "Test 8"), names)


def run_all(root: str) -> None:
    for fn in (test1, test2, test3, test4, test5, test6, test7, test8):
        fn(root)
