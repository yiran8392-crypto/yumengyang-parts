# -*- coding: utf-8 -*-
"""
下架「只有我方 SKU、没有 OE 号」的型号
====================================
判定规则（写进报告）：
  1. 型号本身必须是我方自编号：WL\d{2}- / JJ\d{2}- / \d{2}-[A-Z]{2,4}\d{3,4}（如 10-BC001）；
     型号本身是 OEM/品牌号的（55226249、TB-1808、NJK91217…）一律不动。
  2. OE 字段为空，或 OE 本身就是自编号；并且交叉号 x 全为空或全是自编号。
  3. 适配车型里没有任何「长度≥6 且含≥2 个数字」的编号串（防 OE 被错填进车型栏）——
     有的话保守保留，不下架。

用法：python delist_nooe.py --dry / 真跑
"""

import csv
import io
import json
import os
import re
import shutil
import sys
import time
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_JS = os.path.join(HERE, "data", "data.js")
BACKUP_ROOT = os.path.join(HERE, "_backup")
CSV_OUT = os.path.join(HERE, "下架清单.csv")
MD_OUT = os.path.join(HERE, "下架清单.md")

OURS = re.compile(r"^(WL\d{2}[-\s]|JJ\d{2}[-\s]|\d{2}-[A-Z]{2,4}\d{3,4})", re.I)
TOK = re.compile(r"[0-9A-Za-z][0-9A-Za-z\-_.]{5,}")


def ours(t):
    return bool(OURS.match(re.sub(r"\s+", "", str(t or "").upper())))


def blank(t):
    return not str(t or "").strip()


def has_codeish(a):
    for m in TOK.finditer(a or ""):
        if sum(c.isdigit() for c in m.group(0)) >= 2:
            return True
    return False


def load_site():
    raw = io.open(DATA_JS, encoding="utf-8").read()
    k = "window.SITE_DATA="
    i = raw.find(k)
    return json.JSONDecoder().raw_decode(raw[i + len(k):])[0], raw


def should_delist(it):
    if not ours(it["m"]):
        return False, ""
    oe = it.get("oe") or ""
    xs = [x for x in (it.get("x") or []) if str(x).strip()]
    if not (blank(oe) or ours(oe)):
        return False, "有真 OE"
    if not all(ours(x) for x in xs):
        return False, "有真交叉号"
    if has_codeish(it.get("a")):
        return False, "车型栏里有编号"
    return True, "只有我方型号，无 OE/交叉号"


def main():
    dry = "--dry" in sys.argv
    site, raw = load_site()
    items = site["items"]
    cats = {c["key"]: c for c in site["cats"]}

    hit, kept_exc = [], Counter()
    for it in items:
        ok, why = should_delist(it)
        if ok:
            hit.append(it)
        elif why == "车型栏里有编号":
            kept_exc[it["c"]] += 1
    print("待下架 %d 个（占 %.1f%%）" % (len(hit), 100.0 * len(hit) / len(items)))
    print("按品类：", dict(Counter(it["c"] for it in hit).most_common()))
    print("因车型栏里有编号而保守保留：%d" % sum(kept_exc.values()))

    if dry:
        import random
        random.seed(2)
        for it in random.sample(hit, min(10, len(hit))):
            print("  %-8s %-11s oe=%-8s a=%s" % (it["c"], it["m"], it.get("oe") or "(空)", (it.get("a") or "")[:34]))
        return 0

    ts = time.strftime("%Y%m%d-%H%M%S")
    bdir = os.path.join(BACKUP_ROOT, "下架前-%s" % ts)
    os.makedirs(bdir, exist_ok=True)
    for f in ("data/data.js", "sitegen.py", "sitemap.xml"):
        src = os.path.join(HERE, f.replace("/", os.sep))
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(bdir, os.path.basename(f)))
    print("备份 → %s" % bdir)

    # 清单
    rows = []
    for it in hit:
        rows.append({
            "品类": it["c"],
            "我方料号": it["m"],
            "名称": it.get("n") or "",
            "原OE字段": it.get("oe") or "",
            "适配车型": (it.get("a") or "").replace("\n", " "),
            "原图片路径": it.get("p") or "",
            "slug": it.get("s") or "",
        })
    with open(CSV_OUT, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["品类", "我方料号", "名称", "原OE字段", "适配车型", "原图片路径", "slug"])
        w.writeheader()
        for r in rows:
            w.writerow(r)

    bycat = {}
    for r in rows:
        bycat.setdefault(r["品类"], []).append(r)
    md = ["# 下架清单（只有我方 SKU、没有 OE 号）", "",
          "生成时间：%s" % time.strftime("%Y-%m-%d %H:%M:%S"),
          "合计 **%d** 个型号。" % len(rows), "",
          "> 恢复办法：双击 `恢复下架.cmd`，会从 `_backup\\下架前-%s\\` 还原 data.js 并重渲染。" % ts, ""]
    for k in sorted(bycat, key=lambda x: -len(bycat[x])):
        cn = cats.get(k, {}).get("name") or k
        md.append("## %s %s（%d 个）" % (k, cn, len(bycat[k])))
        md.append("")
        md.append("| 我方料号 | 名称 | 原OE | 适配车型 |")
        md.append("|---|---|---|---|")
        for r in bycat[k][:80]:
            md.append("| %s | %s | %s | %s |" % (r["我方料号"], r["名称"][:18],
                                                  r["原OE字段"] or "（空）", r["适配车型"][:46]))
        if len(bycat[k]) > 80:
            md.append("| … | 还有 %d 个，见 CSV | | |" % (len(bycat[k]) - 80))
        md.append("")
    open(MD_OUT, "w", encoding="utf-8", newline="\n").write("\n".join(md) + "\n")

    # 执行
    keep = [it for it in items if it not in hit]
    gone_slugs = [it.get("s") for it in hit if it.get("s")]
    payload = dict(site)
    payload["items"] = keep
    cnt = Counter(it["c"] for it in keep)
    payload["cats"] = [dict(c, n=cnt.get(c["key"], 0)) for c in site["cats"]]
    payload["generated"] = time.strftime("%Y-%m-%d %H:%M")
    with open(DATA_JS, "w", encoding="utf-8", newline="\n") as f:
        f.write("/* 型号查询站数据文件 —— 由 build.py 自动生成，别手改。 */\n")
        f.write("/* 字段：i=编号 c=品类 m=型号 n=品名 b=品牌 oe=主OE号 x=交叉号数组 a=适配车型 r=备注 p=大图 t=缩略图 */\n")
        f.write("window.SITE_DATA=")
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";\n")
    print("data.js：%d → %d（删了 %d）" % (len(items), len(keep), len(items) - len(keep)))

    removed = 0
    for s in gone_slugs:
        p = os.path.join(HERE, "c", s + ".html")
        if os.path.exists(p):
            os.remove(p)
            removed += 1
    print("删掉型号页 %d 个（其余由 rerender 重建目录时清掉）" % removed)

    with open(os.path.join(bdir, "下架记录.json"), "w", encoding="utf-8") as f:
        json.dump({"time": ts, "count": len(rows), "by_cat": {k: len(v) for k, v in bycat.items()},
                   "slugs": gone_slugs}, f, ensure_ascii=False)
    print("完成：清单 %s / %s" % (CSV_OUT, MD_OUT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
