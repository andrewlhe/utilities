#!/usr/bin/env python3
import argparse
import os
import re
import sqlite3
import sys
from pathlib import Path


SQLITE_HEADER = b'SQLite format 3\x00'
COMMON_SQLITE_STRINGS = [
    b'CREATE TABLE', b'sqlite_master', b'message', b'chat', b'IMMessage',
    b'MicroMsg', b'Conversation', b'Chat_'
]


def read_bytes(path: Path, n: int = 64):
    with open(path, 'rb') as fh:
        return fh.read(n)


def print_header(path: Path):
    print(f'File: {path}')
    print(f'Exists: {path.exists()}')
    if path.exists():
        print(f'Size: {path.stat().st_size} bytes')
        print('Header bytes:', read_bytes(path).hex())


def try_sqlite_open(path: Path):
    try:
        conn = sqlite3.connect(f'file:{path.as_posix()}?mode=ro', uri=True)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' LIMIT 20;")
        tables = cur.fetchall()
        print('\nSQLite open succeeded.')
        print('Tables found:')
        if not tables:
            print('  <none>')
        else:
            for table in tables:
                print(f'  - {table[0]}')
        conn.close()
        return True
    except Exception as exc:
        print(f'\nSQLite open failed: {type(exc).__name__}: {exc}')
        return False


def scan_for_sqlite_text(path: Path):
    try:
        data = path.read_bytes()
    except Exception as exc:
        print(f'Error reading file: {exc}')
        return []

    hits = []
    for token in COMMON_SQLITE_STRINGS:
        idx = data.find(token)
        if idx != -1:
            hits.append((token.decode('latin1', 'ignore'), idx))
    return hits


def scan_for_schema_strings(path: Path):
    try:
        data = path.read_bytes()
    except Exception as exc:
        print(f'Error reading file: {exc}')
        return []

    patterns = [
        rb'CREATE\s+TABLE\s+.*?\(',
        rb'sqlite_master',
        rb'CREATE\s+INDEX\s+.*?\(',
        rb'INSERT\s+INTO\s+.*?\(',
    ]
    results = []
    for pattern in patterns:
        for match in re.finditer(pattern, data, flags=re.IGNORECASE | re.DOTALL):
            snippet = match.group(0)[:200]
            results.append(snippet.decode('latin1', 'ignore'))
    return results[:20]


def attempt_sqlite_recovery(path: Path):
    print('=== SQLite recovery probe ===')
    print_header(path)

    header = read_bytes(path, 64)
    if header.startswith(SQLITE_HEADER):
        print('\nSQLite format header detected.')
    else:
        print('\nSQLite header not found at start of file.')

    found = scan_for_sqlite_text(path)
    if found:
        print('\nLikely SQLite-related strings found:')
        for token, idx in found:
            print(f'  - {token!r} at byte {idx}')
    else:
        print('\nNo obvious SQLite schema/message markers found in the first scan.')

    schema_hits = scan_for_schema_strings(path)
    if schema_hits:
        print('\nLikely schema fragments:')
        for snippet in schema_hits:
            print('  - ' + snippet.replace('\n', ' ')[:180])

    print('\nAttempting direct SQLite read...')
    try_sqlite_open(path)


def main():
    parser = argparse.ArgumentParser(description='Probe a .bak file for SQLite metadata and recoverable table/schema information.')
    parser.add_argument('path', help='Path to the .bak file to inspect')
    args = parser.parse_args()

    path = Path(args.path).expanduser().resolve()
    if not path.exists():
        print(f'File not found: {path}')
        return 1

    attempt_sqlite_recovery(path)
    return 0


if __name__ == '__main__':
    sys.exit(main())
