# -*- coding: utf-8 -*-
"""
用机器人 VIN 查询记录（VIN映射.csv）反哺站点型号的「年份 / 排量 / 发动机号」
==========================================================================
数据来源：03-获客与推广\\微信群分析\\VIN映射.csv
  - 每行是一个真实车架号（或车型）的查询结果：车型描述 + 适配 SKU 列表
  - 车型描述含：品牌 年份 车系 发动机 排量 变速箱 配置 排放 驱动

做法（保守）：
  - 只补站点里**为空**的字段，绝不覆盖已有值；
  - 一个型号至少要命中 ≥3 条 VIN 记录才采纳（避免单条误配）；
  - 年份跨度 > 20 年的不补（说明这个件跨了很多代车型，写区间会误导）；
  - 排量、发动机号只取出现 ≥2 次的（过滤偶发噪声）；
  - 年份写成区间（连续段），最多 3 段。

用法：
    python import_vin_enrich.py --dry
    python import_vin_enrich.py
"""

import csv
import io
import json
import os
import re
import shutil
import sys
import time
from collections import Counter, defaultdict

HERE = r"D:\欧鲸鲸\default-workspace\型号查询站"
VINCSV = r"D:\欧鲸鲸\default-workspace\03-获客与推广\微信群分析\VIN映射.csv"
DATA_JS = os.path.join(HERE, "data", "data.js")
REPORT = os.path.join(HERE, "_selftest", "VIN反哺报告.txt")

YEAR = re.compile(r"(?<!\d)((?:19|20)\d{2})(?!\d)")
DISP = re.compile(r"(?<![\d.])(\d\.\d)\s*(?:L|T)?(?![\d.])")

# 发动机号：只认已知的发动机系列前缀，避免把 V73 / CS35 / E90 这类底盘代号当发动机
ENGINE_RE = re.compile(
    r"^(4G\d{2}|4A\d{2}|G4[A-Z]{2}|EA\d{3}|B4[0-8]|N[2-5][0-9]|M[12][0-9]{2}|M2[0-9]{2}|"
    r"BYD4\d{2}\w*|SQR4\d{2}\w*|JL\d{3}Q\w*|HFC4\w*|CA4G\w*|D4\d{2}\w*|L15B\w*|FB\d{0,2}|"
    r"LJ479\w*|HR1[56]\w*|MR\d{2}\w*|DK1[0-9]\w*|BJ4\d{2}\w*|VVT)$")

MIN_VINS = 3          # 型号至少要命中几条 VIN 记录
MIN_DISP = 2          # 排量出现次数阈值
MIN_ENGINE = 2        # 发动机号出现次数阈值
MAX_YEAR_SPAN = 20
YEAR_MAX = 2027       # 年份上限：明年（车型描述里的未来年不采纳）


def norm(c):
    return re.sub(r"[^A-Z0-9]", "", str(c or "").upper())


def parse_desc(desc):
    year = None
    m = YEAR.search(desc)
    if m:
        y = int(m.group(1))
        if 1980 <= y <= YEAR_MAX:
            year = y
    disps = []
    for m in DISP.finditer(desc):
        v = float(m.group(1))
        if 0.5 <= v <= 8.0 and v not in disps:
            disps.append(v)
    engine = None
    for m in re.finditer(r"\b[A-Z0-9]{4,10}\b", desc.upper()):
        if ENGINE_RE.match(m.group(0)):
            engine = m.group(0)
            break
    return year, disps, engine


def years_to_ranges(years):
    ys = sorted({y for y in years if 1980 <= y <= YEAR_MAX})
    if not ys:
        return []
    segs = []
    a = b = ys[0]
    for y in ys[1:]:
        if y == b + 1:
            b = y
            continue
        segs.append((a, b))
        a = b = y
    segs.append((a, b))
    # 合并间隔 ≤2 年的段，避免 2005,2007 这种碎段
    merged = []
    for seg in segs:
        if merged and seg[0] - merged[-1][1] <= 2:
            merged[-1] = (merged[-1][0], seg[1])
        else:
            merged.append(list(seg))
            merged[-1] = tuple(merged[-1])
    out = []
    for a, b in merged[:3]:
        out.append("%d" % a if a == b else "%d-%d" % (a, b))
    return out


def main():
    dry = "--dry" in sys.argv
    s = io.open(DATA_JS, encoding="utf-8").read()
    i = s.index("window.SITE_DATA=") + len("window.SITE_DATA=")
    payload = json.loads(s[i:s.rindex(";")])
    items = payload["items"]
    by_model = {}
    for it in items:
        k = norm(it["m"])
        by_model[k] = it
        if not k.startswith("WL"):
            by_model["WL" + k] = it

    pool = defaultdict(lambda: {"n": 0, "years": Counter(), "disps": Counter(), "engines": Counter()})
    rows = list(csv.DictReader(io.open(VINCSV, encoding="utf-8-sig")))
    unmatched = Counter()
    for r in rows:
        desc = (r.get("车型描述") or "").strip()
        skus = (r.get("SKU列表") or "").split()
        if not skus:
            continue
        year, disps, engine = parse_desc(desc)
        for sku in skus:
            key = norm("WL" + sku) if re.match(r"^\d{2}-", sku) else norm(sku)
            it = by_model.get(key) or by_model.get(norm(sku))
            if not it:
                unmatched[sku] += 1
                continue
            p = pool[it["i"]]
            p["n"] += 1
            if year:
                p["years"][year] += 1
            for d in disps:
                p["disps"][d] += 1
            if engine:
                p["engines"][engine] += 1

    stats = Counter()
    samples = []
    plans = []
    for iid, p in pool.items():
        it = next((x for x in items if x["i"] == iid), None)
        if not it or p["n"] < MIN_VINS:
            continue
        add = {}
        if not it.get("y") and p["years"]:
            ys = [y for y, _c in p["years"].items()]
            if max(ys) - min(ys) <= MAX_YEAR_SPAN:
                rg = years_to_ranges(ys)
                if rg:
                    add["y"] = rg
        if not it.get("d"):
            ds = [d for d, c in p["disps"].items() if c >= MIN_DISP]
            if ds:
                add["d"] = ["%sL" % (("%.1f" % d).rstrip("0").rstrip(".")) for d in sorted(ds)[:6]]
        if not it.get("e"):
            es = [e for e, c in p["engines"].items() if c >= MIN_ENGINE]
            if es:
                add["e"] = sorted(es)[:6]
        if add:
            plans.append((it, add, p["n"]))
            for k in add:
                stats[k] += 1
            if len(samples) < 10:
                samples.append((it["m"], (it.get("a") or "")[:38], p["n"], add))

    print("VIN 记录 %d 行；命中站点型号 %d 个；其中达标（≥%d 条）可补的 %d 个"
          % (len(rows), len(pool), MIN_VINS, len(plans)))
    print("可补：年份 %d ／ 排量 %d ／ 发动机号 %d" % (stats.get("y", 0), stats.get("d", 0), stats.get("e", 0)))
    print("对不上站点的 SKU（前 10）：", unmatched.most_common(10))
    print("\n样例：")
    for m, a, n, add in samples:
        print("  %-10s a=%-40s VIN %-4d → %s" % (m, a, n, add))
    if dry:
        print("\n（试运行，未写文件）")
        return 0
    if not plans:
        print("没有可补的。")
        return 0

    bak = DATA_JS + ".bak-vin-" + time.strftime("%Y%m%d-%H%M%S")
    shutil.copyfile(DATA_JS, bak)
    for it, add, n in plans:
        for k, v in add.items():
            it[k] = v
    payload["generated"] = time.strftime("%Y-%m-%d %H:%M")
    head = s[:s.find("{")]
    with io.open(DATA_JS, "w", encoding="utf-8", newline="\n") as f:
        f.write(head + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n")

    with io.open(REPORT, "w", encoding="utf-8", newline="\n") as f:
        f.write("VIN 反哺（%s）\n" % time.strftime("%Y-%m-%d %H:%M:%S"))
        f.write("来源：%s（%d 行）\n" % (VINCSV, len(rows)))
        f.write("可补：年份 %d / 排量 %d / 发动机号 %d\n\n" % (stats.get("y", 0), stats.get("d", 0), stats.get("e", 0)))
        for it, add, n in plans:
            f.write("%-10s VIN=%-4d %s\n" % (it["m"], n, json.dumps(add, ensure_ascii=False)))
        f.write("\n对不上站点的 SKU（前 30）：\n")
        for k, v in unmatched.most_common(30):
            f.write("%s\t%d\n" % (k, v))
    print("已写入 %d 个型号（备份 %s）" % (len(plans), os.path.basename(bak)))
    print("报告：", REPORT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
