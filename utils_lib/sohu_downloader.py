"""Sohu video downloader - core logic (no GUI).

Resolves a Sohu TV video (page URL or numeric vid) to its real CDN MP4 URL
and downloads it. Mirrors the official web player's request flow:

    1. page  ->  vid
    2. hot.vrs.sohu.com/vrs_pc_play.action  (MD5-signed) -> mp4PlayUrl
    3. data.vod.itc.cn/ip                   -> real CDN mp4 address
    4. download (with progress, resume via Range)
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import re
import time
import urllib.parse
import urllib.request
from typing import Callable, Dict, List, Optional

APP_KEY = "n2YmPA4f5HJeL8uB"           # player's built-in signing key
PCPLAYER_VER = "202609031547"           # player build version (pcPlayerVer)
PLAY_API = "https://hot.vrs.sohu.com/vrs_pc_play.action"
IP_API = "https://data.vod.itc.cn/ip"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
REFERER = "https://tv.sohu.com/"
# Quality codes used by the Sohu player (51=超清 35=高清 31=标清 21=流畅 1=默认)
QUALITY_PRIORITY: List[str] = ["51", "35", "31", "21", "1"]

Log = Callable[[str], None]
_SILENT: Log = lambda _msg: None


def _md5_upper(s: str) -> str:
    return hashlib.md5(s.encode("utf-8")).hexdigest().upper()


def gen_fuid() -> str:
    """Generate a fuid the same way the player does: millis timestamp + random tail."""
    t = 10001000
    e = random.random()
    if e < 0.1:
        e += 0.1
    i = int(1000 + e * t)
    return str(int(time.time() * 1000)) + str(i)


def build_sign(params: Dict[str, object], path: str):
    """Return (timestamp, svsign) matching the player's _l() helper.

    svsign = MD5(sorted "k=v" pairs + "&app_key=...").upper()
    """
    merged: Dict[str, object] = {
        "timestamp": int(time.time() * 1000),
        "path": path,
        "platform_source": "pc",
    }
    merged.update(params)
    parts = []
    for k in sorted(merged.keys()):
        v = merged[k]
        if v != "" and v is not None:
            parts.append(f"{k}={v}")
    parts.append(f"app_key={APP_KEY}")
    return merged["timestamp"], _md5_upper("&".join(parts))


def http_get_json(url: str, headers: Optional[Dict[str, str]] = None, timeout: int = 30):
    req = urllib.request.Request(url, headers=headers or {"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def fetch_page(url: str) -> str:
    """Fetch a Sohu video page and return its text (handles GBK/UTF-8)."""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read()
    for enc in ("utf-8", "gbk", "gb18030"):
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("utf-8", errors="replace")


def extract_vid(page: str) -> Optional[str]:
    m = re.search(r'var\s+vid\s*=\s*"(\d+)"', page)
    return m.group(1) if m else None


def get_play_url(vid: str, ver: str, uid: str) -> dict:
    """Call vrs_pc_play.action and return the raw JSON."""
    params = {
        "vid": vid,
        "ver": ver,
        "uid": uid,
        "ssl": "1",
        "pflag": "pch5",
        "prod": "h5n",
        "pcPlayerVer": PCPLAYER_VER,
        "plat": "99",
        "sver": "10.1.1",
        "platform_source": "pc",
    }
    sign_params = {k: v for k, v in params.items() if k != "platform_source"}
    ts, sign = build_sign(sign_params, "vrs_pc_play.action")
    url = PLAY_API + "?" + urllib.parse.urlencode(params)
    data = http_get_json(url, headers={
        "User-Agent": UA,
        "Referer": REFERER,
        "timestamp": str(ts),
        "svsign": sign,
    })
    if data.get("status") != 1:
        raise RuntimeError(
            f"取流接口返回异常: status={data.get('status')} msg={data.get('msg', '')}"
        )
    return data


def resolve_cdn(play_path: str) -> str:
    """Turn an mp4PlayUrl (//data.vod.itc.cn/ip?... ) into the real CDN URL."""
    if play_path.startswith("//"):
        play_path = "https:" + play_path
    j = http_get_json(play_path, headers={"User-Agent": UA, "Referer": REFERER})
    servers = j.get("servers") or []
    if not servers or not servers[0].get("url"):
        raise RuntimeError("无法解析 CDN 地址: " + json.dumps(j, ensure_ascii=False)[:200])
    return servers[0]["url"]


def sanitize_filename(name: str) -> str:
    name = re.sub(r'[\\/:*?"<>|\r\n\t]', "_", name).strip()
    return name[:120] or "sohu_video"


def download_file(url: str, out_path: str, referer: str = REFERER, log: Log = _SILENT) -> int:
    """Download *url* to *out_path* with progress logging; resumes partial files."""
    existed = os.path.getsize(out_path) if os.path.exists(out_path) else 0
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": referer})
    if existed:
        req.add_header("Range", f"bytes={existed}-")

    with urllib.request.urlopen(req, timeout=60) as resp:
        total = int(resp.headers.get("Content-Length") or 0)
        mode = "ab"
        if resp.status == 206:
            total += existed
        elif existed:
            existed = 0
            mode = "wb"  # server ignored the Range request
        if existed:
            log(f"  总大小: {total / 1024 / 1024:.1f} MB (已存在 {existed / 1024 / 1024:.1f} MB)")
        else:
            log(f"  总大小: {total / 1024 / 1024:.1f} MB")

        with open(out_path, mode) as f:
            downloaded = existed
            last_log = time.time()
            while True:
                chunk = resp.read(1024 * 256)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                now = time.time()
                if now - last_log > 1.0:
                    pct = downloaded / total * 100 if total else 0
                    log(f"\r  进度: {downloaded / 1024 / 1024:.1f} / {total / 1024 / 1024:.1f} MB ({pct:.1f}%)")
                    last_log = now
            log("\r  进度: 100.0%")
    return total


def _first_play_url(vid: str, uid: str, quality: Optional[str], log: Log):
    """Try quality codes in order; return (play_data, ver_used)."""
    candidates = [quality] if quality else QUALITY_PRIORITY
    last_err: Optional[Exception] = None
    for ver in candidates:
        try:
            log(f"  请求取流接口 (vid={vid}, ver={ver}) ...")
            data = get_play_url(vid, ver, uid)
            d = data.get("data") or {}
            if d.get("mp4PlayUrl"):
                return data, ver
            last_err = RuntimeError("接口未返回播放地址")
        except Exception as e:  # noqa: BLE001
            last_err = e
            log(f"      ver={ver} 失败: {e}")
    raise RuntimeError(f"未能获取播放地址{('：' + str(last_err)) if last_err else ''}（视频可能已下架或需会员）")


def download(target: str, out_dir: str = ".", quality: Optional[str] = None,
             log: Log = _SILENT) -> Dict[str, object]:
    """Download one Sohu video (page URL or vid).

    Returns a dict with title / path / size / duration / width / height.
    """
    os.makedirs(out_dir, exist_ok=True)
    uid = gen_fuid()

    target = target.strip()
    if re.fullmatch(r"\d+", target):
        vid = target
    else:
        log(f"[1/4] 抓取页面: {target}")
        page = fetch_page(target)
        vid = extract_vid(page)
        if not vid:
            raise RuntimeError("未在页面中找到 vid，请直接提供视频 ID")
        log(f"      视频 ID: {vid}")

    play_data, _ver = _first_play_url(vid, uid, quality, log)
    d = play_data.get("data") or {}
    title = d.get("tvName") or f"sohu_{vid}"
    total_bytes = d.get("totalBytes") or 0
    total_dur = d.get("totalDuration") or 0
    width, height = d.get("width", 0), d.get("height", 0)
    play_path = d["mp4PlayUrl"][0]
    log(f"      标题: {title}")
    log(f"      时长: {int(total_dur // 60)}分{int(total_dur % 60)}秒  分辨率: {width}x{height}  "
        f"大小: {total_bytes / 1024 / 1024:.1f} MB")

    log("[3/4] 解析 CDN 下载地址 ...")
    cdn_url = resolve_cdn(play_path)

    out_path = os.path.join(out_dir, sanitize_filename(title) + ".mp4")
    log(f"[4/4] 开始下载 -> {out_path}")
    size = download_file(cdn_url, out_path, log=log)
    log(f"完成: {out_path} ({size / 1024 / 1024:.1f} MB)")
    return {
        "title": title,
        "path": out_path,
        "size": size,
        "duration": total_dur,
        "width": width,
        "height": height,
    }


def download_many(targets: List[str], out_dir: str = ".",
                  quality: Optional[str] = None, log: Log = _SILENT) -> List[Dict[str, object]]:
    """Download several videos; each target is a page URL or vid."""
    results = []
    for i, target in enumerate(targets, 1):
        log(f"\n===== [{i}/{len(targets)}] {target} =====")
        try:
            results.append(download(target, out_dir, quality, log))
        except Exception as e:  # noqa: BLE001
            log(f"错误: {e}")
            results.append({"target": target, "error": str(e)})
    return results
