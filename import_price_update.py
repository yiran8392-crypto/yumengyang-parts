# -*- coding: utf-8 -*-
"""
进价表更新（带价格的产品目录 + ABS/凸轮/曲轴/节气门/进气压力传感器目录）

用法（Python 路径见 更新内部数据.cmd 里那把）：
    python import_price_update.py "新的大目录.xlsx" "新的ABS目录.xlsx" --tag 20261112 [--apply]

做三件事：
  1. 按**表头名**认列（不硬编码列位，源表改列顺序也不会错位）：进价/一级价/二级价/单价…
  2. 把 内部价格-不发布/价格表.csv 里这批来源的旧行整批换掉，其它单表（油泵、氧传感器、天博、
     威利火花塞、真空阀、胎压）原样保留
  3. 在 build_internal.py 里会自动更新 PRICE_LABELS（本脚本只打印该改的映射，由人确认）

不加 --apply 就是 dry-run：只打印将要写入的行数与列位映射。
"""
import argparse
import csv
import io
import os
import re
import shutil
import sys
from datetime import datetime

import openpyxl

HERE = os.path.dirname(os.path.abspath(__file__))
PRICE_DIR = os.path.join(HERE, "内部价格-不发布")
PRICE_CSV = os.path.join(PRICE_DIR, "价格表.csv")

CODE_RE = re.compile(r"^[A-Z]{2}\d{1,2}-[0-9A-Z]+$", re.I)
PRICE_KEYS = ("进价", "新进价", "一级价", "二级价", "二级", "价格", "单价", "限价", "批价",
              "新一级价", "新二级价", "之前进价")


def norm_head(s):
    return re.sub(r"[\s\u3000（）()]", "", s or "")


LABEL_RE = re.compile(r"^(新)?(进价|一级价|二级价|二级|单价|价格|限价|批价)(限价|批发价|批发|批价|价)?$")


def price_label(c2):
    """表头（已去空格括号）→ 统一档位名；不像价格列就返回 None。
    源表写法很随意：「一级价 （限价）」「二级价 （批发价）」「新二级价」「二级」都出现过；
    也要躲开「名爵没进过新单价」「银龙报价」这种备注列，所以只认整词（允许尾巴带 限价/批发价）。"""
    if not c2 or "之前" in c2 or "历史" in c2:
        return None
    m = LABEL_RE.match(c2)
    if not m:
        return None
    new, core = m.group(1), m.group(2)
    if core == "二级":
        core = "二级价"
    if new and core in ("进价", "一级价", "二级价"):
        return "新" + core
    return core


def num(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(",", "").replace("￥", "").replace("元", "").replace(" ", "")
    if not s:
        return None
    try:
        return float(s)
    except Exception:
        return None


def clean_code(raw):
    """料号清洗：WL29-3811/90083 → WL29-3811（斜杠后面是 OE/装箱号，不是料号的一部分）"""
    s = ("" if raw is None else str(raw)).strip().upper()
    s = re.sub(r"[\s\u3000]+", "", s)
    if "/" in s:
        s = s.split("/")[0]
    return s


def is_code(s):
    return bool(CODE_RE.match(s or ""))


def parse_sheet(ws):
    """表头名驱动 + 数据形态校准编码列。返回 dict 或 None。"""
    cells = None
    head_row = None
    for r, row in enumerate(ws.iter_rows(min_row=1, max_row=min(ws.max_row or 0, 8), max_col=20,
                                         values_only=True), 1):
        cc = [("" if v is None else str(v).strip()) for v in row]
        norm = [norm_head(c) for c in cc]
        if any("进价" in c for c in norm) or sum(1 for c in norm if c in PRICE_KEYS) >= 2:
            head_row, cells = r, cc
            break
    if not head_row:
        return None

    sample = list(ws.iter_rows(min_row=head_row + 1, max_row=head_row + 15, max_col=20, values_only=True))

    def shape_score(col):
        n = 0
        for row in sample:
            if len(row) >= col:
                if is_code(clean_code(row[col - 1])):
                    n += 1
        return n

    named = [i for i, c in enumerate(cells, 1) if ("编码" in c) or ("编号" in c)]
    pool = named or list(range(1, 7))
    code_col = max(pool, key=shape_score)
    if shape_score(code_col) == 0:
        code_col = max(range(1, min(7, (ws.max_column or 7)) + 1), key=shape_score)
    if shape_score(code_col) == 0:
        return None

    name_col = None
    for i, c in enumerate(cells, 1):
        if i != code_col and ("名称" in c or c == "型号"):
            name_col = i
            break

    # 列号 → 档位名（归一成 build_internal 认的写法；「之前进价」是历史价，不收）
    price_map = {}
    for i, c in enumerate(cells, 1):
        if i == code_col:
            continue
        lab = price_label(norm_head(c))
        if lab:
            price_map[i] = lab

    maxc = max([code_col, name_col or 0] + list(price_map))
    rows, seen = [], set()
    for r, row in enumerate(ws.iter_rows(min_row=head_row + 1, max_row=ws.max_row, max_col=maxc,
                                         values_only=True), head_row + 1):
        code = clean_code(row[code_col - 1]) if len(row) >= code_col else ""
        if not is_code(code):
            continue
        nm = ""
        if name_col and len(row) >= name_col and row[name_col - 1] is not None:
            nm = str(row[name_col - 1]).strip().replace("\n", " ")
        vals = {}
        for col in price_map:
            if len(row) >= col:
                v = num(row[col - 1])
                if v is not None and v != 0:
                    vals[col] = v
        if not vals:
            continue
        if code in seen:      # 同料号重复行：保留第一行（有价的那行通常在上面）
            continue
        seen.add(code)
        rows.append((r, code, nm, vals))
    return {"header": head_row, "code_col": code_col, "name_col": name_col,
            "price_map": price_map, "rows": rows}


def fmt(v):
    """写进 CSV 的数值：保留 6 位小数再掐零。
    源表里有 44.0005681818182 这种（进价按公式算出来的），保留 4 位就会变成 44.0006，
    所以这里多留两位；110.199999999999 这类浮点尾巴仍然会被掐成 110.2。"""
    s = ("%.6f" % v).rstrip("0").rstrip(".")
    return s if s else "0"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("big")
    ap.add_argument("abs_file")
    ap.add_argument("--tag", required=True, help="版本标签，写进「来源文件」列，如 20261112")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    big_name = "产品目录-带价格-%s.xlsx" % a.tag
    abs_name = "ABS等传感器目录-%s.xlsx" % a.tag

    payload = []          # (来源文件名, 工作表, 行号, 料号, 名称, {列号: 值})
    label_out = {}
    for path, fname in ((a.big, big_name), (a.abs_file, abs_name)):
        if not os.path.exists(path):
            sys.exit("找不到源表：%s" % path)
        print("读取 %s" % path)
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        for sn in wb.sheetnames:
            ws = wb[sn]
            p = parse_sheet(ws)
            if not p:
                print("  - %-16s 跳过（没有价格表头）" % sn)
                continue
            print("  - %-16s 表头r%-2d 编码列%d  %d 行  %s"
                  % (sn, p["header"], p["code_col"], len(p["rows"]),
                     ", ".join("%d=%s" % (c, l) for c, l in sorted(p["price_map"].items()))))
            label_out[(fname, sn)] = dict(sorted(p["price_map"].items()))
            for r, code, nm, vals in p["rows"]:
                payload.append((fname, sn, r, code, nm, vals))
        wb.close()

    print("\n新表合计 %d 行（%d 个料号）" % (len(payload), len(set(x[3] for x in payload))))

    # ---- 读旧价格表，剔掉这批来源
    old_rows = []
    fields_old = []
    with io.open(PRICE_CSV, encoding="utf-8-sig", newline="") as f:
        rd = csv.DictReader(f)
        fields_old = list(rd.fieldnames or [])
        for r in rd:
            old_rows.append(r)

    def is_replaced(f):
        # 新旧两种来源名都要认，否则第二次跑会把上次写入的行当成“别人的”留下来，价格表越跑越重
        return (f.startswith("线圈 碳罐") or f.startswith("产品目录-带价格")
                or f.startswith("ABS等传感器") or f.startswith("ABS"))

    keep = [r for r in old_rows if not is_replaced(r.get("来源文件") or "")]
    dropped = len(old_rows) - len(keep)
    print("旧价格表：%d 行，替换掉 %d 行，保留 %d 行" % (len(old_rows), dropped, len(keep)))

    # ---- 组装新表
    maxcol = max([int(k.replace("价格col", "")) for k in fields_old if k and k.startswith("价格col")] +
                 [max(v) for v in [x[5] for x in payload] if v] or [5])
    fields = ["来源文件", "工作表", "行号", "商品编码", "名称"] + ["价格col%d" % c for c in range(5, maxcol + 1)]

    def row_of(src, sheet, line, code, nm, vals):
        d = {"来源文件": src, "工作表": sheet, "行号": str(line), "商品编码": code, "名称": nm}
        for c in range(5, maxcol + 1):
            if c in vals:
                d["价格col%d" % c] = fmt(vals[c])
        return d

    new_rows = [row_of(*x) for x in payload]

    print("写入后：%d 行（含占位列到 价格col%d）" % (len(keep) + len(new_rows), maxcol))

    print("\n---- build_internal.py 的 PRICE_LABELS 应该改成 ----")
    for (f, s), m in label_out.items():
        print('    (%r, %r): {%s},' % (f, s, ", ".join("%d: %r" % (c, l) for c, l in m.items())))

    if not a.apply:
        print("\n[dry-run] 没有写文件。确认后加 --apply。")
        return

    bak = os.path.join(PRICE_DIR, "价格表.before-%s.csv" % a.tag)
    if not os.path.exists(bak):
        shutil.copy2(PRICE_CSV, bak)
        print("\n备份：%s" % bak)
    tmp = PRICE_CSV + ".tmp"
    with io.open(tmp, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in keep:
            w.writerow(r)
        for r in new_rows:
            w.writerow(r)
    os.replace(tmp, PRICE_CSV)
    print("已写入：%s（%d 行）" % (PRICE_CSV, len(keep) + len(new_rows)))


if __name__ == "__main__":
    main()
