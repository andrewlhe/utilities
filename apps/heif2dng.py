#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
heif2dng.py — HEIF/HEIC 转 DNG 工具 v2（线性 DNG，16-bit，无损，Lightroom/ACR 兼容）

v2 修复：
  1) 修正致命标签号错误：50717 是 WhiteLevel（v1 误写成 CalibrationIlluminant=21，
     导致 ACR 把白点判为 21/65535，整图过曝、色彩崩坏、Lightroom 拒收）；
     CalibrationIlluminant1 实为 50778，v2 补写为 D50(23)。
  2) 补全 DNG 必填/推荐标签：NewSubFileType、BlackLevel、WhiteLevel、DefaultScale、
     DefaultCropOrigin、DefaultCropSize、BaselineExposure、BaselineNoise、
     BaselineSharpness、LinearResponseLimit、AnalogBalance。
  3) 正确色彩管线：iPhone HEIC 解码像素为 Display P3 色域（非 sRGB），
     v2 按 P3 线性化并使用 P3->XYZ(D50) 色彩矩阵，CalibrationIlluminant1=D50。

用法:
  python heif2dng.py --input "<HEIF文件夹>" [--output "<输出文件夹>"] \
         [--compression deflate|uncompressed] [--force] [--dry-run] [--jobs N]

说明:
  HEIF/HEIC 是手机已处理完成的成品图像，不包含原始传感器数据。转换得到
  "线性 DNG"（16-bit 无损封装），Lightroom / Photoshop / ACR 可直接打开编辑，
  但动态范围/宽容度不会超过原 HEIF。

依赖: pillow, pillow-heif, numpy, piexif
"""

import argparse
import shutil
import struct
import sys
import time
import zlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import piexif
import pillow_heif

# ---------------- TIFF 字段类型 ----------------
T_BYTE = 1
T_ASCII = 2
T_SHORT = 3
T_LONG = 4
T_RATIONAL = 5
T_UNDEFINED = 7
T_SRATIONAL = 10

# ---------------- TIFF / EXIF / DNG 标签 ----------------
TAG_NEW_SUBFILE_TYPE = 254
TAG_IMAGE_WIDTH = 256
TAG_IMAGE_LENGTH = 257
TAG_BITS_PER_SAMPLE = 258
TAG_COMPRESSION = 259
TAG_PHOTOMETRIC = 262
PHOTOMETRIC_LINEAR_RAW = 34892  # DNG 线性（已去马赛克 RGB）图像；2=RGB 会被 raw 读取器拒绝
TAG_STRIP_OFFSETS = 273
TAG_ORIENTATION = 274
TAG_SAMPLES_PER_PIXEL = 277
TAG_ROWS_PER_STRIP = 278
TAG_STRIP_BYTE_COUNTS = 279
TAG_X_RESOLUTION = 282
TAG_Y_RESOLUTION = 283
TAG_RESOLUTION_UNIT = 296
TAG_SOFTWARE = 305
TAG_DATETIME = 306
TAG_MAKE = 271
TAG_MODEL = 272
TAG_EXIF_IFD = 34665
TAG_GPS_IFD = 34853

DNG_VERSION = 50706
DNG_BACKWARD_VERSION = 50707
DNG_UNIQUE_CAMERA_MODEL = 50708
DNG_BLACK_LEVEL = 50714
DNG_WHITE_LEVEL = 50717
DNG_DEFAULT_SCALE = 50718
DNG_DEFAULT_CROP_ORIGIN = 50719
DNG_DEFAULT_CROP_SIZE = 50720
DNG_COLOR_MATRIX1 = 50721
DNG_COLOR_MATRIX2 = 50722
DNG_ANALOG_BALANCE = 50727
DNG_AS_SHOT_NEUTRAL = 50728
DNG_BASELINE_EXPOSURE = 50730
DNG_BASELINE_NOISE = 50731
DNG_BASELINE_SHARPNESS = 50732
DNG_LINEAR_RESPONSE_LIMIT = 50734
DNG_CAL_ILLUMINANT1 = 50778
DNG_CAL_ILLUMINANT2 = 50779

EXTS = {".heif", ".heic"}

DNG_IFD_INTEROP = 40965  # 跳过 Interop IFD 指针

# ColorMatrix1 方向约定（DNG 规范：存储矩阵为 XYZ -> 相机空间）：
# True  = 存 XYZ(D50)->P3（即 P3->XYZ 的逆矩阵），供 ACR 作 cam->XYZ 使用
# False = 存 P3->XYZ(D50)
MATRIX_XYZ_TO_CAM = True


# ---------------- 颜色与数值工具 ----------------
def display_to_linear_u16(arr8):
    """Display P3 / sRGB 的 8-bit 显示编码 -> 线性 16-bit（二者传输函数相同）。"""
    s = arr8.astype(np.float32) / 255.0
    lin = np.where(s <= 0.04045, s / 12.92, np.power((s + 0.055) / 1.055, 2.4))
    return np.clip(lin * 65535.0 + 0.5, 0.0, 65535.0).astype(np.uint16)


def to_rationals(matrix, scale=100000):
    """把 3x3 矩阵压成 (分子,分母) 列表，精度 1e-5，支持负数（SRATIONAL）。"""
    out = []
    for v in matrix.flat:
        n = int(round(float(v) * scale))
        out.append((n, scale))
    return out


def _bradford_d65_to_d50():
    return np.array(
        [
            [1.0478112, 0.0228866, -0.0501270],
            [0.0295434, 0.9904844, -0.0170491],
            [-0.0092345, 0.0150436, 0.7521316],
        ],
        dtype=np.float64,
    )


def p3_to_xyz_d50_matrix():
    p3_to_xyz_d65 = np.array(
        [
            [0.4865709486482162, 0.26566769316909306, 0.1982172852343625],
            [0.2289745640697488, 0.6917385218365064, 0.079286914093745],
            [0.0000000000000000, 0.04511338185890264, 1.0439443689009757],
        ],
        dtype=np.float64,
    )
    return _bradford_d65_to_d50() @ p3_to_xyz_d65


def srgb_to_xyz_d50_matrix():
    srgb_to_xyz_d65 = np.array(
        [
            [0.4124564, 0.3575761, 0.1804375],
            [0.2126729, 0.7151522, 0.0721750],
            [0.0193339, 0.1191920, 0.9503041],
        ],
        dtype=np.float64,
    )
    return _bradford_d65_to_d50() @ srgb_to_xyz_d65


def detect_color_space(icc: bytes) -> str:
    """根据 HEIC 内嵌 ICC 判断解码像素色域：'p3' 或 'srgb'。"""
    if icc:
        try:
            low = icc.lower()
            if b"display p3" in low or b"p3" in low:
                return "p3"
        except Exception:
            pass
    return "srgb"


# ---------------- TIFF / DNG 写入 ----------------
def prep_entry(tag, typ, value):
    """编码一个 IFD 条目。返回 (tag, typ, cnt, inline_bytes_or_None, payload_bytes_or_None)。"""
    if typ in (T_BYTE, T_UNDEFINED):
        b = value if isinstance(value, bytes) else bytes([int(value)])
        cnt = len(b)
    elif typ == T_ASCII:
        b = value if isinstance(value, bytes) else str(value).encode("utf-8", "replace")
        if not b.endswith(b"\x00"):
            b += b"\x00"
        cnt = len(b)
    elif typ == T_SHORT:
        vals = list(value) if isinstance(value, (list, tuple)) else [int(value)]
        cnt = len(vals)
        b = struct.pack("<%dH" % cnt, *vals)
    elif typ == T_LONG:
        vals = list(value) if isinstance(value, (list, tuple)) else [int(value)]
        cnt = len(vals)
        b = struct.pack("<%dI" % cnt, *vals)
    elif typ == T_RATIONAL:
        if isinstance(value, (list, tuple)) and value and isinstance(value[0], (list, tuple)):
            pairs = [tuple(p) for p in value]
        else:
            pairs = [tuple(value)]
        cnt = len(pairs)
        b = struct.pack("<%dI" % (2 * cnt), *[x for p in pairs for x in p])
    elif typ == T_SRATIONAL:
        if isinstance(value, (list, tuple)) and value and isinstance(value[0], (list, tuple)):
            pairs = [tuple(p) for p in value]
        else:
            pairs = [tuple(value)]
        cnt = len(pairs)
        b = struct.pack("<%di" % (2 * cnt), *[int(x) for p in pairs for x in p])
    else:
        raise ValueError("unsupported type %d for tag %d" % (typ, tag))
    if len(b) <= 4:
        return (tag, typ, cnt, b + b"\x00" * (4 - len(b)), None)
    return (tag, typ, cnt, None, b)


def _patch(entries, tag, new_entry):
    for i, (t, *_rest) in enumerate(entries):
        if t == tag:
            entries[i] = new_entry
            return


def build_ifd_bytes(entries, value_offsets, next_ifd):
    out = struct.pack("<H", len(entries))
    for tag, typ, cnt, inline, payload in entries:
        if inline is not None:
            vf = inline
        else:
            vf = struct.pack("<I", value_offsets[id(payload)])
        out += struct.pack("<HHI", tag, typ, cnt) + vf
    out += struct.pack("<I", next_ifd)
    return out


def assemble_dng(u16, ifd0_extras, camera_model, color_matrix, exif_entries, gps_entries, compression):
    """排布：header -> IFD0 -> 图像数据 -> IFD0 值区 -> EXIF IFD/值区 -> GPS IFD/值区。"""
    h, w = u16.shape[:2]
    if compression == "deflate":
        strip = zlib.compress(u16.tobytes(), 6)
        comp_code = 8
    else:
        strip = u16.tobytes()
        comp_code = 1

    cm = to_rationals(color_matrix)
    ifd0 = []
    ifd0.append(prep_entry(TAG_NEW_SUBFILE_TYPE, T_LONG, 0))
    ifd0.append(prep_entry(TAG_IMAGE_WIDTH, T_LONG, w))
    ifd0.append(prep_entry(TAG_IMAGE_LENGTH, T_LONG, h))
    ifd0.append(prep_entry(TAG_BITS_PER_SAMPLE, T_SHORT, [16, 16, 16]))
    ifd0.append(prep_entry(TAG_COMPRESSION, T_SHORT, comp_code))
    ifd0.append(prep_entry(TAG_PHOTOMETRIC, T_SHORT, PHOTOMETRIC_LINEAR_RAW))  # LinearRaw
    ifd0.append(prep_entry(TAG_STRIP_OFFSETS, T_LONG, 0))  # 占位
    ifd0.append(prep_entry(TAG_ORIENTATION, T_SHORT, 1))
    ifd0.append(prep_entry(TAG_SAMPLES_PER_PIXEL, T_SHORT, 3))
    ifd0.append(prep_entry(TAG_ROWS_PER_STRIP, T_LONG, h))
    ifd0.append(prep_entry(TAG_STRIP_BYTE_COUNTS, T_LONG, len(strip)))
    ifd0.append(prep_entry(TAG_X_RESOLUTION, T_RATIONAL, (72, 1)))
    ifd0.append(prep_entry(TAG_Y_RESOLUTION, T_RATIONAL, (72, 1)))
    ifd0.append(prep_entry(TAG_RESOLUTION_UNIT, T_SHORT, 2))

    for entry in ifd0_extras:
        ifd0.append(entry)

    if exif_entries:
        ifd0.append(prep_entry(TAG_EXIF_IFD, T_LONG, 0))
    if gps_entries:
        ifd0.append(prep_entry(TAG_GPS_IFD, T_LONG, 0))

    # DNG 核心标签
    ifd0.append(prep_entry(DNG_VERSION, T_BYTE, bytes([1, 4, 0, 0])))
    ifd0.append(prep_entry(DNG_BACKWARD_VERSION, T_BYTE, bytes([1, 1, 0, 0])))
    ifd0.append(prep_entry(DNG_UNIQUE_CAMERA_MODEL, T_ASCII, camera_model))
    ifd0.append(prep_entry(DNG_BLACK_LEVEL, T_RATIONAL, [(0, 1), (0, 1), (0, 1)]))
    ifd0.append(prep_entry(DNG_WHITE_LEVEL, T_SHORT, [65535, 65535, 65535]))
    ifd0.append(prep_entry(DNG_DEFAULT_SCALE, T_RATIONAL, [(1, 1), (1, 1)]))
    ifd0.append(prep_entry(DNG_DEFAULT_CROP_ORIGIN, T_RATIONAL, [(0, 1), (0, 1)]))
    ifd0.append(prep_entry(DNG_DEFAULT_CROP_SIZE, T_RATIONAL, [(w, 1), (h, 1)]))
    ifd0.append(prep_entry(DNG_COLOR_MATRIX1, T_SRATIONAL, cm))
    ifd0.append(prep_entry(DNG_ANALOG_BALANCE, T_RATIONAL, [(1, 1), (1, 1), (1, 1)]))
    ifd0.append(prep_entry(DNG_AS_SHOT_NEUTRAL, T_RATIONAL, [(1, 1), (1, 1), (1, 1)]))
    ifd0.append(prep_entry(DNG_BASELINE_EXPOSURE, T_SRATIONAL, (0, 1)))
    ifd0.append(prep_entry(DNG_BASELINE_NOISE, T_RATIONAL, (1, 1)))
    ifd0.append(prep_entry(DNG_BASELINE_SHARPNESS, T_RATIONAL, (1, 1)))
    ifd0.append(prep_entry(DNG_LINEAR_RESPONSE_LIMIT, T_RATIONAL, (1, 1)))
    ifd0.append(prep_entry(DNG_CAL_ILLUMINANT1, T_SHORT, 23))  # D50，与矩阵一致

    # ---- 布局 ----
    header_size = 8
    ifd0_size = 2 + 12 * len(ifd0) + 4
    cursor = header_size + ifd0_size

    strip_off = cursor
    cursor += len(strip)

    off0 = {}
    for _tag, _typ, _cnt, _inline, payload in ifd0:
        if payload is not None:
            cursor = (cursor + 3) & ~3
            off0[id(payload)] = cursor
            cursor += len(payload)

    if exif_entries:
        exif_ifd_off = (cursor + 3) & ~3
        cursor = exif_ifd_off + (2 + 12 * len(exif_entries) + 4)
        off1 = {}
        for _tag, _typ, _cnt, _inline, payload in exif_entries:
            if payload is not None:
                cursor = (cursor + 3) & ~3
                off1[id(payload)] = cursor
                cursor += len(payload)
    else:
        exif_ifd_off = None
        off1 = {}

    if gps_entries:
        gps_ifd_off = (cursor + 3) & ~3
        cursor = gps_ifd_off + (2 + 12 * len(gps_entries) + 4)
        off2 = {}
        for _tag, _typ, _cnt, _inline, payload in gps_entries:
            if payload is not None:
                cursor = (cursor + 3) & ~3
                off2[id(payload)] = cursor
                cursor += len(payload)
    else:
        gps_ifd_off = None
        off2 = {}

    _patch(ifd0, TAG_STRIP_OFFSETS, prep_entry(TAG_STRIP_OFFSETS, T_LONG, strip_off))
    if exif_ifd_off is not None:
        _patch(ifd0, TAG_EXIF_IFD, prep_entry(TAG_EXIF_IFD, T_LONG, exif_ifd_off))
    if gps_ifd_off is not None:
        _patch(ifd0, TAG_GPS_IFD, prep_entry(TAG_GPS_IFD, T_LONG, gps_ifd_off))

    # ---- 写盘 ----
    buf = bytearray(cursor)
    buf[0:8] = b"II" + struct.pack("<H", 42) + struct.pack("<I", 8)
    buf[8:8 + ifd0_size] = build_ifd_bytes(ifd0, off0, 0)
    buf[strip_off:strip_off + len(strip)] = strip
    for _tag, _typ, _cnt, _inline, payload in ifd0:
        if payload is not None:
            buf[off0[id(payload)]:off0[id(payload)] + len(payload)] = payload
    if exif_entries:
        buf[exif_ifd_off:exif_ifd_off + 2 + 12 * len(exif_entries) + 4] = build_ifd_bytes(
            exif_entries, off1, 0
        )
        for _tag, _typ, _cnt, _inline, payload in exif_entries:
            if payload is not None:
                buf[off1[id(payload)]:off1[id(payload)] + len(payload)] = payload
    if gps_entries:
        buf[gps_ifd_off:gps_ifd_off + 2 + 12 * len(gps_entries) + 4] = build_ifd_bytes(
            gps_entries, off2, 0
        )
        for _tag, _typ, _cnt, _inline, payload in gps_entries:
            if payload is not None:
                buf[off2[id(payload)]:off2[id(payload)] + len(payload)] = payload
    return bytes(buf)


def _exif_entries_from_dict(exif_dict, section):
    entries = []
    tags_map = piexif.TAGS.get(section, {})
    for tag, val in exif_dict.get(section, {}).items():
        if section == "Exif" and tag == DNG_IFD_INTEROP:
            continue
        tinfo = tags_map.get(tag)
        if not tinfo:
            continue
        typ = tinfo["type"] if isinstance(tinfo, dict) else tinfo[0]
        try:
            entries.append(prep_entry(tag, typ, val))
        except Exception:
            continue
    return entries


def convert_one(src: Path, out: Path, compression: str):
    hf = pillow_heif.open_heif(str(src))
    img = hf.to_pillow().convert("RGB")

    exif_dict = None
    exif_bytes = hf.info.get("exif")
    if exif_bytes:
        try:
            exif_dict = piexif.load(exif_bytes)
        except Exception:
            exif_dict = None

    orient = 1
    if exif_dict:
        orient = exif_dict.get("0th", {}).get(274, 1)
    if orient != 1:
        from PIL import ImageOps

        img = ImageOps.exif_transpose(img)

    arr8 = np.asarray(img, dtype=np.uint8)
    u16 = display_to_linear_u16(arr8)
    del arr8

    # 基础信息
    ifd0_extras = []
    model = b"Apple iPhone"
    if exif_dict:
        z0 = exif_dict.get("0th", {})
        make = z0.get(271)
        model_raw = z0.get(272)
        dt = z0.get(306)
        sw = z0.get(305)
        if make:
            ifd0_extras.append(prep_entry(TAG_MAKE, T_ASCII, make))
        if model_raw:
            model = model_raw
            ifd0_extras.append(prep_entry(TAG_MODEL, T_ASCII, model))
        if sw:
            ifd0_extras.append(prep_entry(TAG_SOFTWARE, T_ASCII, sw))
        if dt:
            ifd0_extras.append(prep_entry(TAG_DATETIME, T_ASCII, dt))

    # 色彩空间选择
    cs = detect_color_space(hf.info.get("icc_profile"))
    if cs == "p3":
        m_xyz = p3_to_xyz_d50_matrix()
    else:
        m_xyz = srgb_to_xyz_d50_matrix()
    # DNG 规范：ColorMatrix1 存储的是 XYZ -> 相机空间矩阵（ACR 内部求逆用于 cam->XYZ）
    if MATRIX_XYZ_TO_CAM:
        color_matrix = np.linalg.inv(m_xyz)
    else:
        color_matrix = m_xyz

    # UniqueCameraModel 用自定义名，避免 ACR 尝试匹配 iPhone 机型 raw 配置
    camera_model = b"Apple " + model + b" (HEIC Linear)"
    if len(camera_model) > 100:
        camera_model = b"Apple iPhone HEIC Linear"

    exif_entries = _exif_entries_from_dict(exif_dict, "Exif") if exif_dict else []
    gps_entries = _exif_entries_from_dict(exif_dict, "GPS") if exif_dict else []

    data = assemble_dng(u16, ifd0_extras, camera_model, color_matrix,
                         exif_entries, gps_entries, compression)
    with open(out, "wb") as f:
        f.write(data)
    return src.name, True, ""


def collect_files(input_dir: Path):
    files = [p for p in input_dir.iterdir() if p.is_file() and p.suffix.lower() in EXTS]
    return sorted(files)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    ap = argparse.ArgumentParser(description="HEIF/HEIC -> DNG (linear DNG, 16-bit, ACR 兼容)")
    ap.add_argument("--input", required=True, help="HEIF 源文件夹")
    ap.add_argument("--output", default=None, help="输出文件夹（默认：源文件夹同级 DNG 目录）")
    ap.add_argument("--compression", choices=["deflate", "uncompressed"], default="uncompressed",
                    help="压缩方式：uncompressed 兼容性最好（默认，libraw/ACR 均支持）；deflate 体积小但部分第三方读取器不支持")
    ap.add_argument("--force", action="store_true", help="覆盖已存在的 DNG")
    ap.add_argument("--dry-run", action="store_true", help="只统计，不转换")
    ap.add_argument("--jobs", type=int, default=3, help="并行线程数（默认 3）")
    ap.add_argument("--limit", type=int, default=0, help="只处理前 N 个文件（0=全部）")
    args = ap.parse_args()

    input_dir = Path(args.input)
    if not input_dir.is_dir():
        print(f"[错误] 输入文件夹不存在: {input_dir}")
        sys.exit(1)
    out_dir = Path(args.output) if args.output else input_dir.parent / "DNG"

    files = collect_files(input_dir)
    if not files:
        print(f"[提示] 文件夹里没有 {sorted(EXTS)} 文件: {input_dir}")
        return
    if args.limit > 0:
        files = files[:args.limit]

    total_mb = sum(p.stat().st_size for p in files) / (1024 * 1024)
    print(f"找到 {len(files)} 个文件，总大小 {total_mb:.1f} MB")

    if args.dry_run:
        n = min(len(files), 200)
        sample = files[:n]
        est = sum(
            pillow_heif.open_heif(str(p)).size[0] * pillow_heif.open_heif(str(p)).size[1] * 6
            for p in sample
        )
        est = est * (len(files) / n)  # 按比例外推到全部文件
        est = est * 0.35 if args.compression == "deflate" else est
        print(f"[dry-run] 估算输出约 {est / (1024**3):.1f} GB（{args.compression}）")
        return

    out_dir.mkdir(parents=True, exist_ok=True)
    free_mb = shutil.disk_usage(out_dir).free / (1024 * 1024)
    print(f"输出到: {out_dir}  |  压缩: {args.compression}  |  线程: {args.jobs}")

    todo = []
    for src in files:
        out_path = out_dir / (src.stem + ".dng")
        if out_path.exists() and not args.force:
            continue
        todo.append((src, out_path))

    skipped = len(files) - len(todo)
    t0 = time.time()
    ok = 0
    failed = []

    def run(item):
        src, out = item
        t = time.time()
        try:
            name, _, _ = convert_one(src, out, args.compression)
            return src, out, True, "", time.time() - t, name
        except Exception as e:
            return src, out, False, f"{type(e).__name__}: {e}", time.time() - t, src.name

    if args.jobs > 1 and len(todo) > 1:
        with ThreadPoolExecutor(max_workers=args.jobs) as ex:
            futs = {ex.submit(run, item): item for item in todo}
            done = 0
            for fut in as_completed(futs):
                done += 1
                src, out, is_ok, err, dt, name = fut.result()
                if is_ok:
                    ok += 1
                    print(f"[{done}/{len(todo)}] {name} -> {out.name}  ({dt:.1f}s)", flush=True)
                else:
                    failed.append((src.name, err))
                    print(f"[{done}/{len(todo)}] 失败 {name}: {err}", flush=True)
    else:
        for i, item in enumerate(todo, 1):
            src, out, is_ok, err, dt, name = run(item)
            if is_ok:
                ok += 1
                print(f"[{i}/{len(todo)}] {name} -> {out.name}  ({dt:.1f}s)", flush=True)
            else:
                failed.append((src.name, err))
                print(f"[{i}/{len(todo)}] 失败 {name}: {err}", flush=True)

    total = time.time() - t0
    out_size_mb = 0
    dng_count = 0
    for f in out_dir.glob("*.dng"):
        out_size_mb += f.stat().st_size
        dng_count += 1
    out_size_mb /= 1024 * 1024

    print("-" * 60)
    print(f"完成：成功 {ok}，跳过 {skipped}，失败 {len(failed)}，耗时 {total:.0f}s")
    print(f"输出体积：{out_size_mb / 1024:.2f} GB（{dng_count} 个文件）")
    if failed:
        print("失败清单：")
        for name, err in failed:
            print(f"  {name}: {err}")


if __name__ == "__main__":
    main()
