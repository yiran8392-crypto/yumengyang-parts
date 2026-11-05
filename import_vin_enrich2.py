# -*- coding: utf-8 -*-
"""
用「机器人群 2026-08-15 至今」的新解析明细补站点年份/排量/发动机号
================================================================
源：03-获客与推广\\微信群分析\\机器人群-解析-0805至今.csv（VIN, 时间, 车型, 品类, SKU）
规则同 import_vin_enrich.py：只补空、≥3 条记录、年份 1980~明年、发动机只认已知系列。
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
SRC = r"D:\欧鲸鲸\default-workspace\03-获客与推广\微信群分析\机器人群-解析-0805至今.csv"
DATA_JS = os.path.join(HERE, "data", "data.js")

YEAR = re.compile(r"(?<!\d)((?:19|20)\d{2})(?!\d)")
DISP = re.compile(r"(?<![\d.])(\d\.\d)\s*(?:L|T)?(?![\d.])")
ENGINE_RE = re.compile(
    r"^(4G\d{2}|4A\d{2}|G4[A-Z]{2}|EA\d{3}|B4[0-8]|N[2-5][0-9]|M[12][0-9]{2}|M2[0-9]{2}|"
    r"BYD4\d{2}\w*|SQR4\d{2}\w*|JL\d{3}Q\w*|HFC4\w*|CA4G\w*|D4\d{2}\w*|L15B\w*|FB\d{0,2}|"
    r"LJ479\w*|HR1[56]\w*|MR\d{2}\w*|DK1[0-9]\w*|BJ4\d{2}\w*|VVT)$")
MIN_VINS = 3
MIN_DISP = 2
MIN_ENGINE = 2
MAX_YEAR_SPAN = 20
YEAR_MAX = time.localtime().tm_year + 1


def norm(c):
    return re.sub(r"[^A-Z0-9]", "", str(c or "").upper())


def parse_desc(desc):
    year = None
    m = YEAR.search(desc or "")
    if m:
        y = int(m.group(1))
        if 1980 <= y <= YEAR_MAX:
            year = y
    disps = []
    for m in DISP.finditer(desc or ""):
        v = float(m.group(1))
        if 0.5 <= v <= 8.0 and v not in disps:
            disps.append(v)
    engine = None
    for m in re.finditer(r"\b[A-Z0-9]{4,10}\b", (desc or "").upper()):
        if ENGINE_RE.match(m.group(0)):
            engine = m.group(0)
            break
    return year, disps, engine


def years_to_ranges(years):
    ys = sorted({y for y in years if 1980 <= y <= YEAR_MAX})
    if not ys:
        return []
    segs, a, b = [], ys[0], ys[0]
    for y in ys[1:]:
        if y == b + 1:
            b = y
            continue
        segs.append([a, b])
        a = b = y
    segs.append([a, b])
    merged = []
    for s in segs:
        if merged and s[0] - merged[-1][1] <= 2:
            merged[-1][1] = s[1]
        else:
            merged.append(s)
    return ["%d" % a if a == b else "%d-%d" % (a, b) for a, b in merged[:3]]


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
    rows = 0
    for r in csv.DictReader(io.open(SRC, encoding="utf-8-sig")):
        rows += 1
        sku = (r.get("SKU") or "").strip().upper()
        if not sku:
            continue
        key = norm("WL" + sku) if re.match(r"^\d{2}-", sku) else norm(sku)
        it = by_model.get(key) or by_model.get(norm(sku))
        if not it:
            continue
        year, disps, engine = parse_desc(r.get("车型") or "")
        p = pool[it["i"]]
        p["n"] += 1
        if year:
            p["years"][year] += 1
        for d in disps:
            p["disps"][d] += 1
        if engine:
            p["engines"][engine] += 1

    stats = Counter()
    plans = []
    for iid, p in pool.items():
        it = next((x for x in items if x["i"] == iid), None)
        if not it or p["n"] < MIN_VINS:
            continue
        add = {}
        if not it.get("y") and p["years"]:
            ys = list(p["years"])
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

    print("明细 %d 行；命中站点型号 %d 个；还缺且能补的型号 %d 个" % (rows, len(pool), len(plans)))
    print("新增补：年份 %d ／ 排量 %d ／ 发动机号 %d" % (stats.get("y", 0), stats.get("d", 0), stats.get("e", 0)))
    for it, add, n in plans[:8]:
        print("  %-10s a=%-38s VIN行=%-4d %s" % (it["m"], (it.get("a") or "")[:38], n, add))
    if dry or not plans:
        print("（试运行/无可补）")
        return 0

    bak = DATA_JS + ".bak-vin2-" + time.strftime("%Y%m%d-%H%M%S")
    shutil.copyfile(DATA_JS, bak)
    for it, add, n in plans:
        for k, v in add.items():
            it[k] = v
    payload["generated"] = time.strftime("%Y-%m-%d %H:%M")
    head = s[:s.find("{")]
    with io.open(DATA_JS, "w", encoding="utf-8", newline="\n") as f:
        f.write(head + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n")
    print("已写入 %d 个型号（备份 %s）" % (len(plans), os.path.basename(bak)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
