"""GRE vocabulary raw -> text -> JSON pipeline.

Mirrors VocabularyProcessor.java. The original had hard-coded macOS paths;
this Python version takes paths as arguments.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Optional

_WORD_RE = re.compile(r"^[\w\s\-/']+$")


def process_raw(in_path: str, out_path: str) -> int:
    """Normalise a raw word/definition pair file into blank-line-separated blocks.

    Validates that each key line matches the allowed charset; prints invalid ones.
    Returns the number of word entries written.
    """
    count = 0
    written = 0
    with open(in_path, "r", encoding="utf-8", errors="replace") as fin, \
         open(out_path, "w", encoding="utf-8") as fout:
        lines = fin.read().splitlines()
        idx = 0
        while idx < len(lines):
            key = lines[idx]
            count += 1
            if not _WORD_RE.match(key):
                print(f"{key} on line {count} is invalid")
            count += 1
            value = lines[idx + 1] if idx + 1 < len(lines) else ""
            fout.write(key + "\n")
            fout.write(value + "\n")
            fout.write("\n")
            written += 1
            idx += 2
    return written


def _read_pairs(path: str) -> List[Tuple[str, str]]:
    pairs: List[Tuple[str, str]] = []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()
    idx = 0
    while idx + 1 < len(lines):
        word = lines[idx]
        definition = lines[idx + 1]
        pairs.append((word, definition))
        idx += 3  # skip blank separator
    return pairs


def merge(path1: str, path2: str, out_path: str) -> int:
    """Merge two pair files, keeping the longer definition per lowercase word."""
    merged: Dict[str, Dict[str, str]] = {}
    for word, definition in _read_pairs(path1):
        merged[word.lower()] = {"word": word, "definition": definition}
    for word, definition in _read_pairs(path2):
        key = word.lower()
        existing = merged.get(key, {}).get("definition", "")
        if len(definition) > len(existing):
            merged[key] = {"word": word, "definition": definition}
    count = 0
    with open(out_path, "w", encoding="utf-8") as f:
        for key in sorted(merged):
            f.write(merged[key]["word"] + "\n")
            f.write(merged[key]["definition"] + "\n")
            f.write("\n")
            count += 1
    return count


def _read_overall(path: str) -> List[Tuple[str, str]]:
    return _read_pairs(path)


def _read_pronunciation_blocks(path: str) -> List[Dict[str, str]]:
    """Each word occupies 9 lines: skip 3, generic, skip 1, amE, skip 1, brE, skip 1."""
    blocks: List[Dict[str, str]] = []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()
    idx = 0
    while idx + 8 < len(lines):
        generic = lines[idx + 3]
        am_e = lines[idx + 5]
        br_e = lines[idx + 7]
        blocks.append({"generic": generic, "amE": am_e, "brE": br_e})
        idx += 9
    return blocks


def produce(
    overall_path: str,
    pronunciation_path: str,
    out_json_path: str,
    identifier: str = "gre",
    title: str = "GRE",
    cover_image: str = "BookCoverGRE",
    update_notes: str = "\u2022 Included IPA pronunciations for the entire book",
) -> int:
    """Emit the Vocab-Master-style JSON catalogue."""
    pairs = _read_overall(overall_path)
    blocks = _read_pronunciation_blocks(pronunciation_path)
    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S %z")

    catalog = {
        "identifier": identifier,
        "title": title,
        "coverImage": cover_image,
        "updated": updated,
        "updateNotes": update_notes,
        "wordList": [],
    }
    for i, (word, definition) in enumerate(pairs):
        pronunciation = ""
        if i < len(blocks):
            b = blocks[i]
            if b["generic"]:
                pronunciation = b["generic"]
            elif b["amE"] and b["brE"]:
                pronunciation = b["amE"] if b["amE"] == b["brE"] else f"AmE {b['amE']}\\nBrE {b['brE']}"
            elif b["amE"]:
                pronunciation = b["amE"]
            elif b["brE"]:
                pronunciation = b["brE"]
        catalog["wordList"].append({
            "word": word,
            "pronunciation": pronunciation,
            "definition": definition,
        })
    with open(out_json_path, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)
    return len(catalog["wordList"])
