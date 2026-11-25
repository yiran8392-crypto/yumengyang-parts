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
import glob
import io
import json
import os
import re
import shutil
import time
from collections import Counter, defaultdict

HERE = r"D:\欧鲸鲸\default-workspace\型号查询站"
PAIRS = r"D:\欧鲸鲸\default-workspace\03-获客与推广\微信群分析\机器人群-查询对.csv"
PAIRS_OLD = r"D:\欧鲸鲸\default-workspace\03-获客与推广\微信群分析\机器人群-解析-0805至今.csv"
# 最新一轮「群聊全量解析」明细优先（_parse5.py 产出），没有就退回 0805 旧明细
_cand = sorted(glob.glob(os.path.join(os.path.dirname(PAIRS), "机器人群-解析-全量-*.csv")))
PAIRS_NEW = _cand[-1] if _cand else PAIRS_OLD
OUTDIR = os.path.join(HERE, "data", "vinmap")
MANIFEST = os.path.join(HERE, "data", "vinmap_manifest.json")
MISSING = os.path.join(HERE, "_selftest", "站外高频SKU-%s.csv" % time.strftime("%Y%m%d"))

VIN_RE = re.compile(r"^[A-HJ-NPR-Z0-9]{17}$")


PREFIX = re.compile(r"^([A-Z]{2})(\d{2}-)")


def norm(c):
    return re.sub(r"[^0-9A-Z]", "", str(c or "").upper())


def base_key(c):
    """去掉两位品牌前缀：YM03-0001 / WL03-0001 / SL10-DZ046C → 030001 / 10DZ046C。
    站点 2026-11-20 起是多品牌编码（YM/WL/SL/TB/DF/NJ/YY），群机器人只报裸料号，
    所以两边都按「去掉前缀」的口径对。返回 None 表示没有前缀。
    注意 norm() 会把 "-" 一起去掉，所以前缀要在原始字符串上剥。"""
    s = str(c or "").strip().upper()
    m = PREFIX.match(s)
    if not m:
        return None
    return norm(s[m.end(1):])


def lookup_keys(sku):
    """一个 SKU 可能命中的 by_model 键，按优先级返回。"""
    out = []
    b = base_key(sku)
    if b:
        out.append(b)
    out.append(norm(sku))
    return out


def main():
    s = io.open(os.path.join(HERE, "data", "data.js"), encoding="utf-8").read()
    i = s.index("window.SITE_DATA=") + len("window.SITE_DATA=")
    items = json.loads(s[i:s.rindex(";")])["items"]
    by_model = {}
    by_base = {}           # 裸料号 -> item；同号跨品类时留 None（不链，防跳错件）
    _prefix = {"WL": 0, "YM": 1, "YY": 2, "SL": 3, "TB": 4, "DF": 5, "NJ": 6}
    _groups = defaultdict(list)
    for it in items:
        k = norm(it["m"])
        by_model[k] = it
        b = base_key(it["m"])    # 裸料号也建一份，群里只报 03-0001 这种
        if b:
            _groups[b].append(it)
    n_amb = 0
    for b, lst in _groups.items():
        cats = {str(x.get("c") or "").strip().lower() for x in lst}
        if len(cats) > 1:        # 同号不同品类 = 真不同件，宁可不链
            by_base[b] = None
            n_amb += 1
            continue
        lst.sort(key=lambda x: _prefix.get(str(x.get("m") or "")[:2].upper(), 9))
        by_base[b] = lst[0]

    def find(sku):
        """精确 -> 带前缀去前缀 -> 裸料号直接查（群机器人报的就是裸号）"""
        k = norm(sku)
        if k in by_model:
            return by_model[k]
        b = base_key(sku)
        if b:
            return by_base.get(b)
        return by_base.get(k)

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
                if find(sku):
                    matched += 1
        print("  读 %-24s 累计 VIN %d（+%d）" % (os.path.basename(src), len(vin_skus), len(vin_skus) - n_before))

    print("查询对 %d 行；VIN %d 个；独立 SKU %d 个" % (rows, len(vin_skus), len(sku_count)))
    print("裸号（去品牌前缀）可用 %d 个，其中同号跨品类不链 %d 个" % (len(by_base) - n_amb, n_amb))

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
            it = find(sku)
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
        if find(sku):
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
