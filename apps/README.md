# Standalone Programs

Each script under `apps/` is a self-contained utility with both a GUI and a
CLI.

**Default behavior:** run without arguments → opens the GUI.
To use the CLI, pass the required arguments on the command line.

---

## duplicates.py

Find duplicate files by MD5, grouped by content; pick which copies to delete.

Features: scan history (switch between past scans), per-file checkboxes,
progress bar, Keep First shortcut.

```bash
python apps/duplicates.py                          # GUI
python apps/duplicates.py /path/to/scan --remove   # CLI (keeps first copy)
```

---

## file_manager.py

Batch copy or delete files whose names match a regular expression.

```bash
python apps/file_manager.py                                        # GUI
python apps/file_manager.py copy /from --to-dir /to --pattern ".*\.ARW" --execute  # CLI
```

---

## renumber.py

Renumber a camera-file sequence (ARW/CR2/DNG/NEF/XMP/JPG/JPEG/TIF/TIFF).

```bash
python apps/renumber.py                      # GUI
python apps/renumber.py /photos --start 0 --step 1   # CLI
```

---

## append_head.py

For a camera sequence with a gap, move the head run after the tail run.

```bash
python apps/append_head.py          # GUI
python apps/append_head.py /photos  # CLI
```

---

## epub2pdf_tool.py

Convert EPUB files to PDF using Calibre's `ebook-convert` engine.

Requires [Calibre](https://calibre-ebook.com/download) (auto-detected).
See `README-epub2pdf.md` for details.

```bash
python apps/epub2pdf_tool.py                            # GUI
python apps/epub2pdf_tool.py input.epub --output out.pdf  # CLI
```
