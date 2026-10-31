# -*- coding: utf-8 -*-
"""全量产物抽查：libraw 可打开 + 渲染与原图(ICC->sRGB)对比 + 关键标签。"""
import io
import sys
from pathlib import Path

import numpy as np
import pillow_heif
import rawpy
import tifffile
from PIL import Image, ImageCms

SRC = Path(r"W:\Travel\2022\iPhone\DJY\HEIF")
DNG = Path(r"W:\Travel\2022\iPhone\DJY\DNG")
SAMPLE = ["IMG_0000", "IMG_0100", "IMG_0221", "IMG_0333", "IMG_0439"]

out_lines = []
def log(s):
    out_lines.append(str(s))
    print(s)

for stem in SAMPLE:
    dng = DNG / (stem + ".dng")
    log("==" + stem)
    with tifffile.TiffFile(dng) as tf:
        p = tf.pages[0]
        t = p.tags
        log("  Photometric=%s WhiteLevel=%s CalIllum1=%s" % (
            t[262].value, list(t[50717].value), t[50778].value))
    try:
        with rawpy.imread(str(dng)) as r:
            rgb = r.postprocess(use_camera_wb=True, no_auto_bright=False)
    except Exception as e:
        log("  rawpy FAILED: %r" % e)
        continue
    src = SRC / (stem + ".heif")
    hf = pillow_heif.open_heif(str(src))
    img = hf.to_pillow().convert("RGB")
    icc = hf.info.get("icc_profile")
    if icc:
        prof = ImageCms.ImageCmsProfile(io.BytesIO(icc))
        srgb = ImageCms.createProfile("sRGB")
        img2 = ImageCms.profileToProfile(img, prof, srgb, renderingIntent=0, outputMode="RGB")
    else:
        img2 = img
    orig = np.asarray(img2).astype(np.float32)
    if rgb.shape[:2] == orig.shape[:2]:
        d = np.abs(rgb.astype(np.float32) - orig)
        log("  render mean=%s | diff mean=%.2f per=%s" % (
            [round(float(v), 1) for v in rgb.mean(axis=(0, 1))], float(d.mean()),
            [round(float(v), 2) for v in d.mean(axis=(0, 1))]))
    else:
        log("  size mismatch %s vs %s" % (rgb.shape, orig.shape))

with open(r"C:\Users\helew\Documents\Transaction-Utility\spot_check_v2.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out_lines))
