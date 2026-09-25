# Utilities

This folder contains a small set of practical browser-based and local-analysis
utilities for day-to-day calculations and lightweight tools: static HTML
calculators plus standalone Python programs (each with a GUI and a CLI).

## Structure

```
utilities/
  apps/                # Runnable Python programs (GUI by default, CLI with args)
  utils_lib/           # Shared Python library used by apps/
  archive/             # Older or historical versions of utility scripts
  Airline.html         # Airline / travel cost calculator
  eBaycalculator.html  # eBay pricing / fee calculator
  Hotel.html           # Hotel cost / travel-related utility page
  International_Wire.html  # International wire transfer / currency helper
  README.md
```

## Python tools (`apps/`)

Each program is self-contained. **Run without arguments → opens the GUI.**
Pass CLI arguments to use the command line.

| Program | What it does |
| --- | --- |
| `duplicates.py` | Find duplicate files by MD5; pick which copies to delete (scan history, progress bar). |
| `file_manager.py` | Batch copy / delete files whose names match a regex. |
| `renumber.py` | Renumber a camera-file sequence (ARW/CR2/DNG/NEF/XMP/JPG/TIF...). |
| `append_head.py` | Fix a gapped camera sequence: move the head run after the tail run. |
| `epub2pdf_tool.py` | Convert EPUB to PDF via Calibre's `ebook-convert` (see `README-epub2pdf.md`). |

```bash
cd C:\Users\helew\Documents\utilities

python apps/duplicates.py                # GUI
python apps/duplicates.py /path --remove # CLI

python apps/renumber.py                  # GUI
python apps/renumber.py /photos --start 0 --step 1  # CLI
```

### Shared library (`utils_lib/`)

`apps/` import their logic from `utils_lib/` (duplicate remover, file manager,
sequence tools, GPX/photo/vocabulary helpers, MD5 checksum, shared Tkinter
helpers). Import with `from utils_lib import <module>`.

## HTML utilities

These files are static browser-based utilities. Open them directly in a
browser to use them. If a page depends on local assets or browser security
restrictions, run them from a local file or a lightweight local web server.

## Notes

- This folder is intended to hold general-purpose personal utilities.
- The WeChat analysis and recovery scripts have been moved to a separate
  project folder for cleaner organization.
- Some files are historical or experiment-specific and may require adaptation
  for new use cases.

## License

This folder does not appear to contain an explicit project license. If you
plan to redistribute or publish code from this directory, confirm the
appropriate licensing or institutional usage terms before doing so.
