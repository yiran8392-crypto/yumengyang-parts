# -*- coding: utf-8 -*-
"""
从「适配车型」文本里解析出结构化字段
====================================
输出到 data.js 新字段：
  y = years        年份（"2014-2018"、"2019-"、"1998-2006"）
  d = displacement 排量（"2.0T"、"1.6L"、"1.5"）
  e = engine       发动机号（"4G63"、"EA888"、"B48"、"G4FC"）

只做「从已有文本里提取」，绝不编造：文本里没写的就留空。
"""
import io
import json
import os
import re
import shutil
import sys
import time
from collections import Counter

HERE = r"D:\欧鲸鲸\default-workspace\型号查询站"
DATA_JS = os.path.join(HERE, "data", "data.js")

# ---- 年份 --------------------------------------------------------------
# 1998-2006 / 01-05 / 2019- / 2019- -present / 14年 / 2017—
Y_RANGE = re.compile(
    r"(?<![\d.])((?:19|20)\d{2})\s*[-–~—至到]\s*((?:19|20)\d{2}|present|now|current|(?=款))?",
    re.I)
Y_SHORT_RANGE = re.compile(r"(?<![\d.])(\d{2})\s*[-–~]\s*(\d{2})(?![\d])")
Y_SINGLE = re.compile(r"(?<![\d.])((?:19|20)\d{2})(?!\d)")

# ---- 排量 --------------------------------------------------------------
D_LT = re.compile(r"(?<![\d.])(\d{1}\.\d{1})\s*([LTlt])\b")
D_T = re.compile(r"(?<![\d.])(\d{1}\.\d{1})\s*T\b")
D_L = re.compile(r"(?<![\d.])(\d{1}\.\d{1})\s*L\b")

# ---- 发动机号：只认确定是发动机的系列，宁可漏也不乱认（E60/W204/CS35 是底盘/车型号）----
ENGINE_PAT = [
    r"\b4G\d{2}[A-Z]?\b", r"\b4A\d{2}\b", r"\bG4[A-Z]{2}\b", r"\bGDI\b",
    r"\bEA\d{3}\b", r"\bB4[0-9]\b", r"\bN[2-5][0-9][A-Z]{0,2}\b", r"\bM2\d{2}\b",
    r"\bM1[0-9]{2}\b", r"\bCA4G[A-Z0-9]*\b", r"\bJL\d{3}Q[A-Z]?\b", r"\bHFC4[A-Z0-9]*\b",
    r"\bD4\d{2}[A-Z]?\b", r"\bL15B[A-Z]?\b", r"\bFB\d?\b", r"\bLJ479\b", r"\bBYD4\d{2}\w*\b",
    r"\b1GD\b", r"\bVVT\b",
]
ENGINE_RE = re.compile("|".join(ENGINE_PAT))


def norm_years(a):
    out = []
    for m in Y_RANGE.finditer(a):
        y1 = int(m.group(1))
        y2raw = (m.group(2) or "").strip().lower()
        if y2raw.isdigit():
            y2 = int(y2raw)
            if y2 < y1:                       # 1998-06 这种
                y2 += 2000 if y2 < 100 else 0
            out.append("%d-%d" % (y1, y2))
        elif y2raw in ("present", "now", "current"):
            out.append("%d-" % y1)
        elif m.group(2) is None:
            out.append("%d-" % y1)            # "2019-  -present" 之类
    if not out:
        for m in Y_SHORT_RANGE.finditer(a):
            a1, a2 = int(m.group(1)), int(m.group(2))
            if a1 > a2:
                continue
            base = 2000 if a1 < 90 else 1900
            out.append("%d-%d" % (base + a1, base + a2))
    if not out:
        for m in Y_SINGLE.finditer(a):
            out.append(m.group(1))
    seen, uniq = set(), []
    for x in out:
        if x not in seen:
            seen.add(x)
            uniq.append(x)
    return uniq[:3]


def norm_displ(a):
    out = []
    for m in D_T.finditer(a):
        out.append(m.group(1) + "T")
    for m in D_L.finditer(a):
        out.append(m.group(1) + "L")
    seen, uniq = set(), []
    for x in out:
        k = x.upper()
        if k not in seen:
            seen.add(k)
            uniq.append(x)
    return uniq[:4]


def norm_engine(a):
    out = []
    for m in ENGINE_RE.finditer(a.upper()):
        t = m.group(0)
        if t == "VVT":                       # 可变气门，不是发动机号
            continue
        if t not in out:
            out.append(t)
    return out[:4]


def main():
    raw = io.open(DATA_JS, encoding="utf-8").read()
    k = "window.SITE_DATA="
    idx = raw.find(k)
    payload, _ = json.JSONDecoder().raw_decode(raw[idx + len(k):])
    items = payload["items"]

    ny = nd = ne = 0
    yl, dl, el = Counter(), Counter(), Counter()
    for it in items:
        a = it.get("a") or ""
        y = norm_years(a)
        d = norm_displ(a)
        e = norm_engine(a)
        it["y"] = y
        it["d"] = d
        it["e"] = e
        if y:
            ny += 1
            for x in y:
                yl[x] += 1
        if d:
            nd += 1
            for x in d:
                dl[x] += 1
        if e:
            ne += 1
            for x in e:
                el[x] += 1

    n = len(items)
    print("型号 %d；年份 %d（%.0f%%）／排量 %d（%.0f%%）／发动机号 %d（%.0f%%）"
          % (n, ny, 100.0 * ny / n, nd, 100.0 * nd / n, ne, 100.0 * ne / n))
    print("\n年份 top10:", yl.most_common(10))
    print("排量 top10:", dl.most_common(10))
    print("发动机 top15:", el.most_common(15))

    bak = DATA_JS + ".bak-fit-" + time.strftime("%Y%m%d-%H%M%S")
    shutil.copyfile(DATA_JS, bak)
    payload["generated"] = time.strftime("%Y-%m-%d %H:%M")
    head = raw[:raw.find("{")]
    with io.open(DATA_JS, "w", encoding="utf-8", newline="\n") as f:
        f.write(head + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n")
    print("\n已写入 data.js（备份 %s）" % os.path.basename(bak))
    return 0


if __name__ == "__main__":
    sys.exit(main())
