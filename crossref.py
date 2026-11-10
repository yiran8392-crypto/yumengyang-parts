# -*- coding: utf-8 -*-
"""
交叉号（cross reference / 互替号）工具链 —— 2026-11-10
=====================================================
一条命令，三种活：

    python crossref.py queue                 # 1) 导出"待补交叉号"清单（给数据商 / 自己查）
    python crossref.py check  文件.csv       # 2) 校验拿回来的候选号，出"待审"表
    python crossref.py apply  待审.csv --write   # 3) 把人工确认的并进 data/data.js

设计原则（和奕然 2026-11-10 定的口径一致）：宁缺毋滥。
  · 只补"能校验得住"的号：格式对、不撞自己、不和已有一条打架；
  · 每一条都留来源（source）和判定结论，人工能复核；
  · apply 默认只打印不写；加 --write 才动 data.js，且先备份。

数据约定（data.js 里每个型号一条）：
    m  我方 SKU        oe 原厂号        x  交叉号数组（本工具只写这里）
    a  适配文本        y  年款          d  排量        si 销量星级 0-5
"""
import argparse
import collections
import csv
import io
import json
import os
import re
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_JS = os.path.join(HERE, "data", "data.js")
OUT_DIR = os.path.join(HERE, "_交叉号")          # 中间产物，本机留档（.gitignore 里已挡 *.xls 但没挡这个目录，见文末）
TEMPLATE_COLS = ["我方SKU", "原厂OE", "品类", "候选交叉号", "来源", "备注"]

# ---------------------------------------------------------------- 小工具
SEP = re.compile(r"[\s\-\./]+")


def norm(s):
    """比较用的归一：去分隔符、大写。"""
    return re.sub(r"[^A-Z0-9]", "", str(s or "").upper())


def guess_brand(num):
    """粗判候选号属于谁（只为人工复核时好读，不参与判定）。"""
    n = norm(num)
    if re.fullmatch(r"0\d{9}", n):
        return "Bosch"
    if re.fullmatch(r"F00[A-Z0-9]{6,8}", n):
        return "Bosch/国产贴牌"
    if re.fullmatch(r"\d{5}", n):
        return "Denso(5位)"
    if re.fullmatch(r"CE\d{5,6}", n):
        return "Delphi"
    if re.fullmatch(r"\d{3}\d{4,6}", n):
        return "Denso/电装?"
    if re.fullmatch(r"\d{4}[A-Z]{1,2}\d{2,4}", n):
        return "德尔福/博世?"
    return "未识别"


BAD = {"", "-", "N/A", "NA", "NONE", "NULL", "TBD", "OEM", "OES", "OE", "0", "无", "暂缺"}
MIN_LEN, MAX_LEN = 4, 18          # 去掉分隔符后的长度区间（4 位以下的号大多数是噪音）


def load_items(path=DATA_JS):
    s = io.open(path, encoding="utf-8").read()
    i = s.index("window.SITE_DATA=") + len("window.SITE_DATA=")
    payload = json.loads(s[i:s.rindex(";")])
    return payload, s


def ensure_out():
    if not os.path.isdir(OUT_DIR):
        os.makedirs(OUT_DIR)


# ---------------------------------------------------------------- 1) queue
def cmd_queue(args):
    payload, _ = load_items()
    items = payload["items"]
    cat_name = {c.get("key"): c.get("name") or c.get("key") for c in payload.get("cats") or []}
    cand = [it for it in items if len(it.get("x") or []) <= args.max_existing]
    if args.cat:
        cand = [it for it in cand if it.get("cat") in set(args.cat.split(","))]
    if args.min_si:
        cand = [it for it in cand if (it.get("si") or 0) >= args.min_si]
    cand.sort(key=lambda it: (-(it.get("si") or 0), it.get("cat") or "", it.get("m") or ""))
    if args.limit:
        cand = cand[: args.limit]

    ensure_out()
    out = args.out or os.path.join(OUT_DIR, "待补清单-%s.csv" % time.strftime("%Y%m%d"))
    with io.open(out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["我方SKU", "原厂OE", "品类", "销量星级", "已有交叉号", "适配摘要", "年款"])
        for it in cand:
            w.writerow([it.get("m") or "", it.get("oe") or "", cat_name.get(it.get("cat"), it.get("cat") or ""),
                        it.get("si") or 0, " ".join(it.get("x") or []),
                        (it.get("a") or "")[:120], " ".join(it.get("y") or [])])
    print("待补清单：%d 条 → %s" % (len(cand), out))
    print("统计：全站 %d 条，其中 %d 条没有交叉号、%d 条只有 1 个"
          % (len(items), sum(1 for i in items if not (i.get("x") or [])),
             sum(1 for i in items if len(i.get("x") or []) == 1)))
    return 0


# ---------------------------------------------------------------- 2) check
def read_rows(path):
    with io.open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    # 允许用户用英文表头
    alias = {"sku": "我方SKU", "oe": "原厂OE", "candidate": "候选交叉号", "source": "来源", "note": "备注"}
    fixed = []
    for r in rows:
        fixed.append({alias.get((k or "").strip().lower(), (k or "").strip()): (v or "").strip()
                      for k, v in r.items()})
    return fixed


def getv(row, prefix):
    """按列名前缀取值：表头可能写成「人工确认(y/空)」这种。"""
    for k, v in row.items():
        if k and k.strip().startswith(prefix):
            return (v or "").strip()
    return ""


def cmd_check(args):
    payload, _ = load_items()
    items = payload["items"]
    by_sku = {norm(it.get("m")): it for it in items if it.get("m")}
    by_oe = {norm(it.get("oe")): it for it in items if it.get("oe")}
    known_x = collections.Counter(norm(x) for it in items for x in (it.get("x") or []))

    rows = read_rows(args.file)
    results, tally = [], collections.Counter()
    claimed = collections.defaultdict(list)     # 候选号 -> 被哪些 SKU 认领（同一个号给两个不同件 = 警示）

    for r in rows:
        sku = r.get("我方SKU", "")
        it = by_sku.get(norm(sku))
        cand = r.get("候选交叉号", "")
        src = r.get("来源", "")
        note = r.get("备注", "")
        if it is None:                            # SKU 对不上 → 退一步用 OE 找
            it = by_oe.get(norm(r.get("原厂OE", "")))
        if it is None:
            results.append([sku, r.get("原厂OE", ""), "", cand, src, note, "驳回", "SKU/OE 在库里找不到"])
            tally["驳回:找不到型号"] += 1
            continue

        n = norm(cand)
        if cand in BAD or n in {norm(x) for x in BAD}:
            verdict, why = "驳回", "空值/占位符"
        elif not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 .\-/]{1,26}", cand):
            verdict, why = "驳回", "含非法字符"
        elif not (MIN_LEN <= len(n) <= MAX_LEN):
            verdict, why = "驳回", "长度不对（%d 位，要求 %d–%d）" % (len(n), MIN_LEN, MAX_LEN)
        elif n == norm(it.get("oe")):
            verdict, why = "驳回", "和本条目自己的 OE 一样"
        elif n == norm(it.get("m")):
            verdict, why = "驳回", "和本条目自己的 SKU 一样"
        elif n in {norm(x) for x in (it.get("x") or [])}:
            verdict, why = "通过", "已存在，重复（不入库）"
        else:
            verdict, why = "通过", "格式通过（品牌猜测：%s）" % guess_brand(cand)

        if verdict == "通过" and why.startswith("格式"):
            other = by_oe.get(n)
            if other is not None and (other.get("i") != it.get("i")):
                # 候选号恰好是库里另一条的原厂号：这是好事（说明互为替代），但要人工确认不是错行
                verdict, why = "待审", "命中了库内另一条的 OE（%s / %s），需人工确认" % (other.get("m"), other.get("oe"))
        if verdict == "通过":
            claimed[n].append(it.get("m"))
        results.append([sku, it.get("oe") or "", it.get("cat") or "", cand, src, note, verdict, why])
        tally[verdict + ":" + why.split("（")[0]] += 1

    # 同一个候选号被两个不同 SKU 认领：提示
    dup_claim = {k: v for k, v in claimed.items() if len(set(v)) > 1}
    if dup_claim:
        for row in results:
            n = norm(row[3])
            if n in dup_claim and row[6] == "通过":
                row[6] = "待审"
                row[7] += "；同一个号被多个 SKU 认领（%s）" % "、".join(sorted(set(dup_claim[n])))

    # 结论重算：上面的二次改判要反映到统计里
    tally = collections.Counter()
    for row in results:
        tally[row[6] + ":" + row[7].split("（")[0].split("；")[0]] += 1

    ensure_out()
    out = args.out or (os.path.splitext(args.file)[0] + "-待审.csv")
    with io.open(out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(TEMPLATE_COLS + ["结论", "理由", "人工确认(y/空)"])
        for sku, oe, cat, cand, src, note, verdict, why in results:
            w.writerow([sku, oe, cat, cand, src, note, verdict, why, ""])
    print("校验 %d 行 → %s" % (len(results), out))
    for k, v in tally.most_common():
        print("  %-28s %d" % (k, v))
    print("下一步：打开待审表，把确认要用的行『人工确认』列填 y，再跑 apply。")
    return 0


# ---------------------------------------------------------------- 3) apply
def cmd_apply(args):
    rows = read_rows(args.file)
    payload, raw = load_items()
    items = payload["items"]
    by_sku = {norm(it.get("m")): it for it in items if it.get("m")}
    by_oe = {norm(it.get("oe")): it for it in items if it.get("oe")}

    planned, skipped = [], collections.Counter()
    for r in rows:
        if getv(r, "结论") != "通过":
            skipped["结论不是通过"] += 1
            continue
        if getv(r, "人工确认").lower() not in ("y", "yes", "1", "是", "✓"):
            skipped["没人工确认"] += 1
            continue
        it = by_sku.get(norm(getv(r, "我方SKU"))) or by_oe.get(norm(getv(r, "原厂OE")))
        if it is None:
            skipped["型号找不到"] += 1
            continue
        cand = getv(r, "候选交叉号")
        if not cand:
            skipped["空号"] += 1
            continue
        it.setdefault("x", [])
        if norm(cand) in {norm(x) for x in it["x"]}:
            skipped["重复"] += 1
            continue
        it["x"].append(cand)
        planned.append((it.get("m"), it.get("oe"), cand, getv(r, "来源")[:40]))

    print("计划写入 %d 条" % len(planned))
    for k, v in skipped.most_common():
        print("  跳过 %-12s %d" % (k, v))
    if not planned:
        print("没有可写的。")
        return 0
    if not args.write:
        print("（dry-run，没写文件；确认无误后加 --write）")
        for row in planned[:10]:
            print("   ", " | ".join(x or "" for x in row))
        return 0

    bak = DATA_JS + ".bak-cross-" + time.strftime("%Y%m%d-%H%M%S")
    shutil.copyfile(DATA_JS, bak)
    payload["generated"] = time.strftime("%Y-%m-%d %H:%M")
    head = raw[: raw.find("{")]
    with io.open(DATA_JS, "w", encoding="utf-8", newline="\n") as f:
        f.write(head + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n")
    print("已写入 data.js（备份 %s）" % os.path.basename(bak))
    print("接着跑：python rerender.py  →  抽查几个型号页 →  发布上线")
    return 0


def main():
    ap = argparse.ArgumentParser(description="交叉号：导出清单 / 校验候选 / 合并入库")
    sub = ap.add_subparsers(dest="cmd", required=True)

    q = sub.add_parser("queue", help="导出待补交叉号清单")
    q.add_argument("--cat", default="", help="只导出这些品类（逗号分隔的 key，如 coil,fuelpump）")
    q.add_argument("--min-si", type=int, default=0, help="只看销量星级 ≥ N 的（0-5）")
    q.add_argument("--max-existing", type=int, default=0, help="已有交叉号 ≤ N 条的才算待补（默认 0 = 完全没有）")
    q.add_argument("--limit", type=int, default=0, help="最多导出多少条")
    q.add_argument("--out", default="")
    q.set_defaults(func=cmd_queue)

    c = sub.add_parser("check", help="校验候选交叉号，生成待审表")
    c.add_argument("file")
    c.add_argument("--out", default="")
    c.set_defaults(func=cmd_check)

    a = sub.add_parser("apply", help="把人工确认过的号并进 data.js")
    a.add_argument("file")
    a.add_argument("--write", action="store_true", help="真的写；不加只演练")
    a.set_defaults(func=cmd_apply)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
