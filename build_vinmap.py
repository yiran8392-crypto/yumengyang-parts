# -*- coding: utf-8 -*-
"""
重建 VIN 映射（data/vinmap/*.js）：用机器人群最新查询记录，只映射站点还在的型号
=========================================================================
来源：03-获客与推广\\微信群分析\\机器人群-查询对.csv（VIN, 查询部件, 品类, SKU, 位置备注, 交叉/附加, 时间）

产物（与 vin.js 兼容）：
  data/vinmap/<WMI 前3位>.js   window.VINMAPS["LGX"] = {"s":[SKU...], "v":{VIN:[索引...]}, "m":{SKU:slug}}
  data/vinmap_manifest.json    总 VIN 数 / 分片统计

另外输出「站外高频 SKU」清单（站上没有但客户反复查的件，选品参考）：
  _selftest/站外高频SKU-YYYYMMDD.csv
"""

import csv
import io
import json
import os
import re
import shutil
import time
from collections import Counter, defaultdict

HERE = r"D:\欧鲸鲸\default-workspace\型号查询站"
PAIRS = r"D:\欧鲸鲸\default-workspace\03-获客与推广\微信群分析\机器人群-查询对.csv"
PAIRS_NEW = r"D:\欧鲸鲸\default-workspace\03-获客与推广\微信群分析\机器人群-解析-0805至今.csv"
OUTDIR = os.path.join(HERE, "data", "vinmap")
MANIFEST = os.path.join(HERE, "data", "vinmap_manifest.json")
MISSING = os.path.join(HERE, "_selftest", "站外高频SKU-%s.csv" % time.strftime("%Y%m%d"))

VIN_RE = re.compile(r"^[A-HJ-NPR-Z0-9]{17}$")


def norm(c):
    return re.sub(r"[^0-9A-Z]", "", str(c or "").upper())


def main():
    s = io.open(os.path.join(HERE, "data", "data.js"), encoding="utf-8").read()
    i = s.index("window.SITE_DATA=") + len("window.SITE_DATA=")
    items = json.loads(s[i:s.rindex(";")])["items"]
    by_model = {}
    for it in items:
        k = norm(it["m"])
        by_model[k] = it
        if not k.startswith("WL"):
            by_model["WL" + k] = it

    vin_skus = defaultdict(list)      # VIN -> [SKU]（保序去重）
    seen = defaultdict(set)
    sku_count = Counter()
    matched = 0
    rows = 0
    # 两个源合并：新的 8-15 至今明细 + 旧的全历史查询对（同一个 VIN 的 SKU 取并集）
    sources = []
    if os.path.exists(PAIRS_NEW):
        sources.append((PAIRS_NEW, "VIN"))
    if os.path.exists(PAIRS):
        sources.append((PAIRS, "VIN或车型"))
    for src, qcol in sources:
        n_before = len(vin_skus)
        with io.open(src, encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                rows += 1
                q = (r.get(qcol) or "").strip().upper()
                sku = (r.get("SKU") or "").strip().upper()
                if not q or not sku:
                    continue
                sku_count[sku] += 1
                if not VIN_RE.match(q):
                    continue
                if sku not in seen[q]:
                    seen[q].add(sku)
                    vin_skus[q].append(sku)
                k = norm("WL" + sku) if re.match(r"^\d{2}-", sku) else norm(sku)
                if k in by_model or norm(sku) in by_model:
                    matched += 1
        print("  读 %-24s 累计 VIN %d（+%d）" % (os.path.basename(src), len(vin_skus), len(vin_skus) - n_before))

    print("查询对 %d 行；VIN %d 个；独立 SKU %d 个" % (rows, len(vin_skus), len(sku_count)))

    # 分片
    shards = defaultdict(lambda: {"s": [], "v": {}, "m": {}})
    idx_cache = {}
    n_map = 0
    for vin, skus in vin_skus.items():
        wmi = vin[:3]
        sh = shards[wmi]
        ids = []
        for sku in skus:
            dic = sh["s"]
            if sku not in idx_cache.get(wmi, {}):
                idx_cache.setdefault(wmi, {})[sku] = len(dic)
                dic.append(sku)
            ids.append(idx_cache[wmi][sku])
            k = norm("WL" + sku) if re.match(r"^\d{2}-", sku) else norm(sku)
            it = by_model.get(k) or by_model.get(norm(sku))
            if it and sku not in sh["m"]:
                sh["m"][sku] = it.get("s") or ("p" + str(it["i"]))
                n_map += 1
        sh["v"][vin] = ids

    # 清理旧分片
    os.makedirs(OUTDIR, exist_ok=True)
    for fn in os.listdir(OUTDIR):
        if fn.endswith(".js"):
            os.remove(os.path.join(OUTDIR, fn))

    manifest = {"gen": time.strftime("%Y-%m-%d"), "vins": len(vin_skus),
                "skus_mapped": n_map, "low_conf_excluded": 0, "shards": {}}
    for wmi, sh in sorted(shards.items()):
        body = json.dumps(sh, ensure_ascii=False, separators=(",", ":"))
        with io.open(os.path.join(OUTDIR, wmi + ".js"), "w", encoding="utf-8", newline="\n") as f:
            f.write('window.VINMAPS=window.VINMAPS||{};VINMAPS["%s"]=%s;\n' % (wmi, body))
        manifest["shards"][wmi] = [len(sh["v"]), len(body), len(sh["m"])]
    with io.open(MANIFEST, "w", encoding="utf-8", newline="\n") as f:
        json.dump(manifest, f, ensure_ascii=False, separators=(",", ":"))

    print("写分片 %d 个；站点可跳转的 SKU 映射 %d 条" % (len(shards), n_map))

    # 站外高频 SKU（站上没有但被反复查）
    missing = []
    for sku, n in sku_count.most_common():
        k = norm("WL" + sku) if re.match(r"^\d{2}-", sku) else norm(sku)
        if k in by_model or norm(sku) in by_model:
            continue
        missing.append((sku, n))
    with io.open(MISSING, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["SKU（站上没有）", "历史查询次数"])
        for sku, n in missing[:500]:
            w.writerow([sku, n])
    print("站外高频 SKU：%d 个，TOP10 %s" % (len(missing), missing[:10]))
    print("清单：", MISSING)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
