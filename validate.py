# -*- coding: utf-8 -*-
"""
发布前数据体检（validate.py）
=============================
只做"能自动判断对错"的检查，不猜业务意图。两个级别：

  FATAL  明确的坏数据，会直接挡住发布（exit 1）
        - data.js 读不出来 / 没有型号
        - 有记录缺型号、缺 slug，或 slug 含非法字符
        - slug 重复（会让两个型号抢同一个 URL）
  WARN   已知的历史欠账，只提醒、不挡（谁在变多谁在变少，一眼能看出来）
        - 型号没有 OE 号（按品类给数量）
        - 没有缩略图 / 图片文件不存在
        - 适配车型为空、或含中文
        - OE 重复的组数
        - c\\*.html 页面数和数据条数对不上

用法：
    python validate.py             正常跑，写报告到 _selftest\\校验报告-*.md
    python validate.py --quiet     只在 FATAL 时输出（给更新流程用）

退出码：0 = 可以发布；1 = 有 FATAL，别发。
"""

import collections
import io
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_JS = os.path.join(HERE, "data", "data.js")
C_DIR = os.path.join(HERE, "c")
REPORT_DIR = os.path.join(HERE, "_selftest")

CJK = re.compile(r"[\u4e00-\u9fa5]")
SLUG_OK = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def load_payload():
    raw = io.open(DATA_JS, encoding="utf-8").read()
    key = "window.SITE_DATA="
    i = raw.find(key)
    if i < 0:
        raise ValueError("data.js 里没有 window.SITE_DATA=")
    payload, _ = json.JSONDecoder().raw_decode(raw[i + len(key):])
    return payload


def check(payload):
    items = payload.get("items") or []
    fatal, warn = [], []

    if not items:
        fatal.append("data.js 里一条型号都没有")
        return items, fatal, warn

    # ---- FATAL：型号 / slug
    no_model = [it for it in items if not (it.get("m") or "").strip()]
    if no_model:
        fatal.append("缺型号（m 为空）：%d 条，例如 %s" % (
            len(no_model), ", ".join(str(it.get("i")) for it in no_model[:5])))

    no_slug = [it for it in items if not (it.get("s") or "").strip()]
    if no_slug:
        fatal.append("缺 slug（s 为空）：%d 条，例如 %s" % (
            len(no_slug), ", ".join((it.get("m") or "?") for it in no_slug[:5])))

    bad_slug = [it for it in items if (it.get("s") or "").strip() and not SLUG_OK.match(it["s"])]
    if bad_slug:
        fatal.append("slug 含非法字符：%d 条，例如 %s" % (
            len(bad_slug), ", ".join(it["s"] for it in bad_slug[:5])))

    seen = collections.Counter(it.get("s") for it in items if (it.get("s") or "").strip())
    dups = [(s, n) for s, n in seen.items() if n > 1]
    if dups:
        fatal.append("slug 重复：%d 组（同一条型号会有两个页面抢 URL），例如 %s" % (
            len(dups), ", ".join("%s x%d" % (s, n) for s, n in dups[:5])))

    # ---- WARN：OE
    no_oe = collections.Counter(it.get("c") for it in items if not (it.get("oe") or "").strip())
    total_no_oe = sum(no_oe.values())
    if total_no_oe:
        top = "、".join("%s %d" % (k, v) for k, v in no_oe.most_common(6))
        warn.append("没有 OE 号：%d 条（%s）" % (total_no_oe, top))

    oekey = collections.Counter(
        re.sub(r"[^0-9A-Z]", "", (it.get("oe") or "").upper())
        for it in items if len(re.sub(r"[^0-9A-Z]", "", (it.get("oe") or "").upper())) >= 4)
    dup_oe = [k for k, n in oekey.items() if n > 1]
    if dup_oe:
        warn.append("OE 号重复：%d 组，例如 %s" % (len(dup_oe), ", ".join(dup_oe[:5])))

    # ---- WARN：适配
    empty_fit = sum(1 for it in items if not (it.get("a") or "").strip())
    if empty_fit:
        warn.append("适配车型为空：%d 条" % empty_fit)
    cjk_fit = sum(1 for it in items if CJK.search(it.get("a") or ""))
    if cjk_fit:
        warn.append("适配车型里还有中文：%d 条（英文站会露出来）" % cjk_fit)

    # ---- WARN：图片
    no_thumb = sum(1 for it in items if not (it.get("t") or "").strip())
    missing_file, checked = 0, 0
    for it in items:
        p = (it.get("t") or "").strip()
        if not p:
            continue
        checked += 1
        if not os.path.exists(os.path.join(HERE, p.lstrip("/"))):
            missing_file += 1
    if no_thumb:
        warn.append("没有缩略图：%d 条" % no_thumb)
    if missing_file:
        warn.append("缩略图文件不存在：%d 条（数据里有路径、磁盘上没有）" % missing_file)

    # ---- WARN：页面数
    if os.path.isdir(C_DIR):
        pages = len([f for f in os.listdir(C_DIR) if f.endswith(".html")])
        if pages != len(items):
            warn.append("页面数 %d 和数据条数 %d 对不上（先跑一次 rerender.py）" % (pages, len(items)))

    return items, fatal, warn


def write_report(items, fatal, warn):
    try:
        os.makedirs(REPORT_DIR, exist_ok=True)
    except Exception:
        return ""
    path = os.path.join(REPORT_DIR, "校验报告-%s.md" % time.strftime("%Y%m%d-%H%M"))
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("# 数据体检报告 %s\n\n" % time.strftime("%Y-%m-%d %H:%M"))
        f.write("- 型号：%d 条\n- 结论：%s\n\n" % (
            len(items), "有 FATAL，不能发布" if fatal else "可以发布"))
        f.write("## FATAL\n")
        f.write("\n".join("- " + x for x in fatal) or "- 无\n")
        f.write("\n## WARN\n")
        f.write("\n".join("- " + x for x in warn) or "- 无\n")
        f.write("\n> 这个文件在 _selftest/ 里，已 gitignore，不会发布到线上。\n")
    return path


def main(argv=None):
    argv = argv or sys.argv[1:]
    quiet = "--quiet" in argv
    try:
        payload = load_payload()
    except Exception as e:
        print("[FATAL] 读不了 data/data.js：%s" % e)
        return 1

    items, fatal, warn = check(payload)
    if not quiet:
        print("[体检] 型号 %d 条" % len(items))
        for x in fatal:
            print("  [FATAL] %s" % x)
        for x in warn:
            print("  [WARN ] %s" % x)
        if not fatal:
            print("  结论：可以发布（WARN 是历史欠账，不挡发布）")
    else:
        for x in fatal:
            print("[FATAL] %s" % x)

    if fatal:
        path = write_report(items, fatal, warn)
        if path:
            print("  报告：%s" % os.path.relpath(path, HERE))
        return 1

    if not quiet:
        path = write_report(items, fatal, warn)
        if path:
            print("  报告：%s" % os.path.relpath(path, HERE))
    return 0


if __name__ == "__main__":
    sys.exit(main())
