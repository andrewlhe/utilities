# -*- coding: utf-8 -*-
"""v2 DNG 深度验证：标签 + libraw 渲染 + 与原图对比。"""
import io
import sys
from pathlib import Path

import numpy as np
import pillow_heif
import rawpy
import tifffile
from PIL import Image, ImageCms

out_lines = []
def log(s):
    out_lines.append(str(s))

SRC = Path(r"W:\Travel\2022\iPhone\DJY\HEIF")
DNG = Path(r"C:\Users\helew\Documents\Transaction-Utility\test_dng2")

for dng in sorted(DNG.glob("*.dng")):
    log("==" + dng.name)
    with tifffile.TiffFile(dng) as tf:
        p = tf.pages[0]
        t = p.tags
        def getv(code, name):
            if code in t:
                v = t[code].value
                s = str(list(v)) if isinstance(v, (tuple, list, np.ndarray)) else str(v)
                return name + "=" + s
            return name + "=MISSING"
        log("  " + getv(254, "NewSubFileType"))
        log("  " + getv(262, "Photometric"))
        log("  " + getv(50717, "WhiteLevel") + " | " + getv(50778, "CalIllum1")
            + " | " + getv(50730, "BaselineExp") + " | " + getv(50714, "BlackLevel"))
        cm = t[50721].value
        log("  ColorMatrix1[:3] = " + str([str(x) for x in cm[:3]]))
        log("  shape=" + str(p.shape) + " dtype=" + str(p.dtype))
    try:
        with rawpy.imread(str(dng)) as r:
            renders = {}
            for label, kw in [
                ("wb_autobright", {"use_camera_wb": True, "no_auto_bright": False}),
                ("wb_noauto", {"use_camera_wb": True, "no_auto_bright": True}),
                ("nowb_noauto", {"use_camera_wb": False, "no_auto_bright": True}),
            ]:
                rgb = r.postprocess(**kw)
                renders[label] = rgb
                log("  rawpy[%s]: mean=%s min=%d max=%d" % (
                    label, [round(float(v), 1) for v in rgb.mean(axis=(0, 1))],
                    int(rgb.min()), int(rgb.max())))
    except Exception as e:
        log("  rawpy FAILED: %r" % e)
        continue

    src = SRC / (dng.stem + ".heif")
    hf = pillow_heif.open_heif(str(src))
    img = hf.to_pillow().convert("RGB")
    orig_p3 = np.asarray(img).astype(np.float32)  # 原 P3 显示值
    icc = hf.info.get("icc_profile")
    if icc:
        prof = ImageCms.ImageCmsProfile(io.BytesIO(icc))
        srgb = ImageCms.createProfile("sRGB")
        img2 = ImageCms.profileToProfile(img, prof, srgb, renderingIntent=0, outputMode="RGB")
    else:
        img2 = img
    orig_srgb = np.asarray(img2).astype(np.float32)

    for label, render in renders.items():
        if render.shape[:2] == orig_srgb.shape[:2]:
            d1 = np.abs(render.astype(np.float32) - orig_srgb)
            d2 = np.abs(render.astype(np.float32) - orig_p3)
            log("  %s diff vs ICC->sRGB: mean=%.2f per=%s | vs raw P3: mean=%.2f" % (
                label, float(d1.mean()),
                [round(float(v), 2) for v in d1.mean(axis=(0, 1))], float(d2.mean())))

with open(r"C:\Users\helew\Documents\Transaction-Utility\verify_v2.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out_lines))
print("verify done")
