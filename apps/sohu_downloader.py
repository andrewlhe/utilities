#!/usr/bin/env python3
"""Sohu Video Downloader - standalone program (GUI by default, CLI with args).

Download videos from Sohu TV (tv.sohu.com) by page URL or numeric video ID.

Usage:
    python apps/sohu_downloader.py                        # GUI (default)
    python apps/sohu_downloader.py <url-or-vid> [-o <dir>] [-q <ver>]
    python apps/sohu_downloader.py url1 url2 ... -o <dir>

Quality codes: 51=超清 35=高清 31=标清 21=流畅 1=默认 (auto picks best available).
"""
from __future__ import annotations

import argparse
import os
import sys
import tkinter as tk
from tkinter import ttk

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils_lib import sohu_downloader  # noqa: E402
from utils_lib.gui_common import (  # noqa: E402
    make_field,
    make_output,
    make_window,
    run_async,
    set_output,
)

QUALITY_LABELS = {
    "auto": "自动(最高可用)",
    "51": "超清 51",
    "35": "高清 35",
    "31": "标清 31",
    "21": "流畅 21",
    "1": "默认 1",
}


def run_cli(args: argparse.Namespace) -> int:
    def _log(msg: str) -> None:
        print(msg)

    results = sohu_downloader.download_many(
        args.targets, args.output or ".", args.quality, log=_log
    )
    failed = [r for r in results if "error" in r]
    if failed:
        print(f"\n{len(failed)} 个视频下载失败")
        return 1
    print(f"\n全部完成，共 {len(results)} 个视频")
    return 0


class SohuPanel(ttk.Frame):
    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master)
        self._build()

    def _build(self) -> None:
        top = ttk.Frame(self)
        top.pack(side="top", fill="x")

        # URL / vid input: multi-line so several can be pasted at once
        lbl = ttk.Label(top, text="视频链接 / vid\n(每行一个):")
        lbl.pack(side="left")
        self.url_text = tk.Text(top, width=55, height=4, font=("Consolas", 10))
        self.url_text.pack(side="left", fill="x", expand=True, padx=4)

        # Output directory
        _, self.dir_var = make_field(self, "保存到:", "dir")
        self.dir_var.set("")  # empty = current directory

        # Quality
        qfrm = ttk.Frame(self)
        qfrm.pack(side="top", fill="x", pady=2)
        ttk.Label(qfrm, text="清晰度:", width=18).pack(side="left")
        self.quality_var = tk.StringVar(value="auto")
        box = ttk.Combobox(
            qfrm,
            textvariable=self.quality_var,
            values=list(QUALITY_LABELS.keys()),
            width=12,
            state="readonly",
        )
        box.pack(side="left")
        ttk.Label(qfrm, text="  " + QUALITY_LABELS[self.quality_var.get()]).pack(side="left")
        self.quality_var.trace_add("write", lambda *_: self._update_quality_hint())

        # Run button
        bfrm = ttk.Frame(self)
        bfrm.pack(side="top", fill="x", pady=4)
        ttk.Button(bfrm, text="下载", command=self._on_run).pack(side="left")

        self.text = make_output(self)
        set_output(
            self.text,
            "搜狐视频下载工具\n"
            "================\n"
            "下载 tv.sohu.com 上的视频（按页面链接或视频 ID）。\n\n"
            "使用方法:\n"
            "  1. 在“视频链接 / vid”框粘贴一个或多个链接（每行一个），\n"
            "     也可以直接填数字形式的视频 ID。\n"
            "  2. “保存到”选择输出文件夹（留空 = 当前目录）。\n"
            "  3. 选择清晰度（自动默认）。\n"
            "  4. 点“下载”，日志会显示解析和下载进度。\n\n"
            "说明: 付费/会员视频或已下架内容会明确报错；下载支持断点续传。",
        )

    def _update_quality_hint(self) -> None:
        pass  # (hint label kept simple)

    def _on_run(self) -> None:
        raw = self.url_text.get("1.0", "end").strip()
        targets = [t.strip() for t in re_split_targets(raw)]
        targets = [t for t in targets if t]
        if not targets:
            set_output(self.text, "请先粘贴一个或多个视频链接 / vid。")
            return
        out_dir = self.dir_var.get().strip() or "."
        quality = None if self.quality_var.get() == "auto" else self.quality_var.get()

        def worker(log) -> None:
            sohu_downloader.download_many(targets, out_dir, quality, log=log)

        set_output(self.text, "开始下载 ...\n")
        run_async(self.text, worker, on_done=lambda: None)


def re_split_targets(raw: str):
    # URLs or vids separated by newlines / commas / spaces
    import re
    return re.split(r"[\s,;]+", raw)


def run_gui() -> int:
    root = make_window("搜狐视频下载工具", 780, 560)
    SohuPanel(root).pack(fill="both", expand=True)
    root.mainloop()
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="搜狐视频下载工具：按页面链接或视频 ID 下载 tv.sohu.com 的视频"
    )
    p.add_argument("targets", nargs="*", help="搜狐视频页面链接或视频 ID（可多个）")
    p.add_argument("-o", "--output", default="", help="输出目录（默认当前目录）")
    p.add_argument("-q", "--quality", default=None,
                   help="清晰度 ver 值: 51/35/31/21/1（默认自动选择最高可用）")
    args = p.parse_args(argv)
    if not args.targets:
        return run_gui()
    return run_cli(args)


if __name__ == "__main__":
    sys.exit(main())
