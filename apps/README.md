# Standalone Programs

Each script under `apps/` is a self-contained utility split from the original
Transaction Utility JAR.

**Default behavior:** run without arguments → opens the GUI.
To use the CLI, pass the required arguments on the command line.

---

## duplicates.py

Find and delete duplicate files by MD5 hash.

```bash
python apps/duplicates.py                          # GUI
python apps/duplicates.py /path/to/scan --remove   # CLI
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

## gpx.py

Convert an Apple plist track dump to GPX.

```bash
python apps/gpx.py                                    # GUI
python apps/gpx.py --input data.plist --output data.gpx   # CLI
```

---

## photos_gallery.py

Copy photos listed in a CSV/XLSX into date-named folders.

```bash
python apps/photos_gallery.py                                              # GUI
python apps/photos_gallery.py --csv gallery.xlsx --drive M:/ --output /out   # CLI
```

---

## photos_posted.py

Build a CSV of photos posted on specific dates from `YYMMDD` folders.

```bash
python apps/photos_posted.py                          # GUI
python apps/photos_posted.py /photos --output out.csv   # CLI
```

---

## photos_social.py

Copy social-media originals listed in a CSV/XLSX into `YYMM/DD` folders.

```bash
python apps/photos_social.py                                                      # GUI
python apps/photos_social.py --csv photos.xlsx --drive /Volumes/Memories --output /out   # CLI
```

---

## vocabulary.py

GRE vocabulary pipeline: raw → cleaned → merged → JSON.

```bash
python apps/vocabulary.py                                                        # GUI
python apps/vocabulary.py produce --input overall.txt --pronunciation pron.txt --output gre.json   # CLI
```

---

## test_files.py

Generate synthetic camera-file sequences for testing.

```bash
python apps/test_files.py                # GUI
python apps/test_files.py /test-root      # CLI
```
