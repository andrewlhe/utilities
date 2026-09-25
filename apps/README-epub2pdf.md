# epub2pdf_tool — EPUB to PDF Converter

A Python tool that converts EPUB files to PDF using **Calibre's ebook-convert**
engine. Supports both a **graphical interface (GUI)** and the **command line**.

## Requirements

| Requirement | Notes |
| --- | --- |
| Python 3.8+ | Needs tkinter (included with the official Windows installer) |
| Calibre | Provides the `ebook-convert` engine — download from <https://calibre-ebook.com/download> |

> Calibre needs no configuration: the tool auto-detects it (PATH and common
> install locations).

## Quick Start

### GUI (default)

```
python epub2pdf_tool.py
```

Just run it with no arguments — the GUI opens by default.

1. Click "Add files..." to pick one or more EPUBs, or "Add folder..." to import
   a whole directory (subfolders included).
2. Optionally set an output folder, paper size, margins, font size, or enable
   overwrite.
3. Click "Convert" and watch the progress and log.
4. Once conversion finishes, check the generated PDFs. If they look correct, you
   can click **"Delete originals (N)"** to remove the successfully converted
   source EPUBs — this never happens automatically; a confirmation dialog asks
   first, and only files that converted successfully are deleted.

### Command line

```bash
# Convert a single file (PDF is written next to the source)
python epub2pdf_tool.py book.epub

# Specify an output folder
python epub2pdf_tool.py book.epub -o ./pdf_out

# Batch-convert a folder tree
python epub2pdf_tool.py ./books -r -o ./pdf_out

# Custom layout
python epub2pdf_tool.py book.epub --paper-size a4 --margin 72 --font-size 12

# Overwrite existing PDFs
python epub2pdf_tool.py book.epub --overwrite

# Delete the source EPUB after a successful conversion
python epub2pdf_tool.py book.epub -d
```

### Command-line options

| Option | Description |
| --- | --- |
| `inputs` | One or more EPUB files / folders |
| `-o, --output` | Output folder (default: same folder as the source) |
| `-r, --recursive` | Search subfolders for EPUB files |
| `--paper-size` | Paper: `a4` / `letter` / `legal` / `a5` / `b5` |
| `--margin` | Page margin on all sides (pt) |
| `--font-size` | Body font size (pt) |
| `--overwrite` | Overwrite existing PDFs |
| `-d, --delete-source` | Delete the source EPUB after conversion |

### Folder scanning

- **GUI "Add folder..."** always scans **recursively** — EPUBs in any
  subfolder depth are collected, with no switch needed.
- **Command line** scans only the folder's direct children **unless** you pass
  `-r / --recursive`, which searches every subfolder depth (`**/*.epub`).
- Every found EPUB is converted independently, wherever it sits in the tree.
- **Name clash note:** when batch-converting recursively *with* `-o`, EPUBs
  that share a base name in different subfolders (e.g. `a/x.epub` and
  `b/x.epub`) both map to the same `x.pdf`. The second one is then skipped
  because the PDF already exists — or overwrites the first if you pass
  `--overwrite`. To avoid this, leave `-o` unset (each PDF is written next to
  its own source file) or rename the files beforehand.

## How It Works

- Conversion delegates to Calibre's `ebook-convert <input.epub> <output.pdf>`,
  passing through common layout options.
- Calibre is used instead of a home-grown layout engine because EPUB is a
  reflowable format: correctly re-typesetting it to PDF (TOC, images, fonts,
  styles) is a huge engineering effort, and Calibre is the most mature engine
  available.
- Batch conversion processes files independently: one failure does not stop the
  others, and failures are summarized at the end.

## Troubleshooting

**"Calibre not found"?**
Install Calibre, then click "Refresh" in the GUI (or simply run the command again).

**Not happy with the output layout?**
Tune `--paper-size` / `--margin` / `--font-size`. Calibre supports more advanced
PDF options (e.g. `--pdf-footer-template`) that you can add in `convert_one()`.
