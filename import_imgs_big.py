# -*- coding: utf-8 -*-
"""
大目录补图（163MB，14 张表全处理）
=================================
来源：D:\\111A剪辑\\线圈 碳罐 机油阀 阀体 马达 分火线 产品目录（带价格）(2).2026...xlsx
思路：
  - 逐表自适应表头（表头错位的表用内容兜底：哪一列 WL 编码最多就用哪列）
  - 图：xl/drawings/drawingN.xml 的 <xdr:from><xdr:row> 锚点 → 行 → 该行 SKU
  - SKU 到品类的归属查 data.js（不在表里猜），只给「还没有图」的型号补
  - 不覆盖已有图；对不上 SKU 的图进 待人工对应
  - 价格（一级价/二级价/新一级价…）只写 内部价格-不发布\\价格表.csv

用法：python import_imgs_big.py --dry / 真跑
"""

import csv
import io
import json
import os
import re
import sys
import zipfile
from collections import Counter
from xml.etree import ElementTree as ET

import openpyxl
from PIL import Image, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = r"D:\111A剪辑\线圈 碳罐 机油阀 阀体 马达 分火线 产品目录（带价格）(2).20260701165609369.xlsx"
SRC_NAME = os.path.basename(SRC)
DATA_JS = os.path.join(HERE, "data", "data.js")
IMG_ROOT = os.path.join(HERE, "images")
MANUAL_DIR = r"D:\欧鲸鲸\default-workspace\目录图片-待人工对应"
PRICE_DIR = os.path.join(HERE, "内部价格-不发布")
PRICE_CSV = os.path.join(PRICE_DIR, "价格表.csv")
REPORT = os.path.join(HERE, "解析失败清单-大目录补图.txt")

FULL_EDGE, FULL_BYTES, THUMB_EDGE, THUMB_Q = 800, 80 * 1024, 260, 78

S = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
X = "{http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"


def s(v):
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    t = str(v).replace("\u00a0", " ").replace("\u3000", " ")
    t = t.replace("\r", " ").replace("\n", " ")
    return re.sub(r"\s+", " ", t).strip()


CODE_RE = re.compile(r"^(WL\d{2}-?[0-9A-Z]{3,6}|JJ\d{2}-\d{4}[A-Z]?)$", re.I)


def is_code(v):
    return bool(CODE_RE.match(s(v).replace(" ", "")))


def code_key(t):
    c = s(t).upper().replace(" ", "")
    m = re.match(r"^(WL\d{2})-?([0-9A-Z]{3,6})$", c)
    if m:
        return "%s-%s" % (m.group(1), m.group(2))
    m = re.match(r"^(JJ\d{2})-?(\d{4})([A-Z]?)$", c)
    if m:
        return "%s-%s%s" % (m.group(1), m.group(2), m.group(3))
    return c


def norm_code(t):
    return re.sub(r"[^A-Za-z0-9_.-]", "_", s(t))


# ------------------------------------------------------------------ 工作簿
def sheet_list(z):
    wbx = ET.fromstring(z.read("xl/workbook.xml"))
    rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    rmap = {x.get("Id"): x.get("Target") for x in rels}
    return [(sh.get("name"), rmap.get(sh.get(REL + "id")))
            for sh in wbx.find(S + "sheets").findall(S + "sheet")]


def sheet_anchors(z, target):
    """[(excel_row(1-based), 'xl/media/imageN.png')]，同一行只留第一张"""
    rp = "xl/worksheets/_rels/%s.rels" % target.split("/")[-1]
    if rp not in z.namelist():
        return [], 0
    dpath = None
    for x in ET.fromstring(z.read(rp)):
        tg = x.get("Target") or ""
        if (x.get("Type") or "").endswith("/drawing") and tg.endswith(".xml"):
            dpath = "xl/" + tg.replace("../", "")
    if not dpath or dpath not in z.namelist():
        return [], 0
    imap = {}
    relp = dpath.replace("drawings/", "drawings/_rels/") + ".rels"
    if relp in z.namelist():
        for x in ET.fromstring(z.read(relp)):
            imap[x.get("Id")] = x.get("Target")
    out, extra = {}, 0
    for c in ET.fromstring(z.read(dpath)):
        f = c.find(X + "from")
        if f is None:
            continue
        blip = c.find(".//" + A + "blip")
        tgt = imap.get(blip.get(REL + "embed")) if blip is not None else None
        if not tgt:
            continue
        row = int(f.find(X + "row").text) + 1
        if row in out:
            extra += 1
            continue
        out[row] = "xl/" + tgt.replace("../", "")
    return out, extra


# ------------------------------------------------------------------ 表头
HDR_CODE = ["商品编码", "产品编码", "物料编码", "编码", "料号", "威利编号", "产品型号", "型号"]
HDR_PRICE = ["价", "单价", "调价", "费用"]
HDR_SKIP = ["序号", "材质", "盒", "支", "用量", "指数", "系统", "步进电机", "传感器", "备注"]


def pick(cols, names, exclude=()):
    for n in names:
        for c in sorted(cols):
            if c in exclude:
                continue
            if n.lower() in cols[c].lower():
                return c
    return None


def find_header(ws):
    best = (0, 1, {})
    for r, row in enumerate(ws.iter_rows(min_row=1, max_row=8, max_col=16, values_only=True), 1):
        cols, hit = {}, 0
        for i, v in enumerate(row, 1):
            h = s(v)
            if not h:
                continue
            cols[i] = h
            if any(n.lower() in h.lower() for n in HDR_CODE + HDR_PRICE):
                hit += 1
        if hit > best[0]:
            best = (hit, r, cols)
    return best[1], best[2]


def content_code_col(rows):
    score = {}
    for r, row in rows:
        for i, v in enumerate(row[:12], 1):
            if is_code(v):
                score[i] = score.get(i, 0) + 1
    return max(score, key=score.get) if score else None


# ------------------------------------------------------------------ 图片
def trim_white(im):
    g = im.convert("L").point(lambda p: 255 if p < 244 else 0)
    box = g.getbbox()
    if box:
        p = 2
        im = im.crop((max(0, box[0] - p), max(0, box[1] - p),
                      min(im.width, box[2] + p), min(im.height, box[3] + p)))
    return im


def to_square(im):
    w, h = im.size
    if w == h:
        return im
    side = max(w, h)
    bg = Image.new("RGB", (side, side), (255, 255, 255))
    bg.paste(im, ((side - w) // 2, (side - h) // 2))
    return bg


def fit(im, edge):
    w, h = im.size
    if max(w, h) <= edge:
        return im
    if w >= h:
        return im.resize((edge, max(1, round(h * edge / w))), Image.LANCZOS)
    return im.resize((max(1, round(w * edge / h)), edge), Image.LANCZOS)


def save_webp(im, path, quality, max_bytes=None):
    q = quality
    while True:
        buf = io.BytesIO()
        im.save(buf, "WEBP", quality=q, method=4)
        data = buf.getvalue()
        if max_bytes is None or len(data) <= max_bytes or q <= 40:
            open(path, "wb").write(data)
            return len(data)
        q -= 8


def prep(raw):
    im = Image.open(io.BytesIO(raw))
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        bg = Image.new("RGB", im.size, (255, 255, 255))
        bg.paste(im, mask=im.split()[-1])
        im = bg
    im = ImageOps.exif_transpose(im.convert("RGB"))
    im = trim_white(im)
    im = to_square(im)
    return fit(im, FULL_EDGE)


def load_site():
    raw = io.open(DATA_JS, encoding="utf-8").read()
    k = "window.SITE_DATA="
    i = raw.find(k)
    return json.JSONDecoder().raw_decode(raw[i + len(k):])[0]


def main():
    dry = "--dry" in sys.argv
    import time
    t0 = time.time()
    site = load_site()
    items = site["items"]
    by_code = {}
    for it in items:
        by_code[re.sub(r"\s+", "", it["m"].upper())] = it
    print("站里型号 %d 个（%d 个已有图）" % (len(items), sum(1 for it in items if it.get("p"))))

    z = zipfile.ZipFile(SRC)
    wb = openpyxl.load_workbook(SRC, read_only=True, data_only=True)
    per_sheet, recs = [], []
    fails = []
    for name, tgt in sheet_list(z):
        if name not in wb.sheetnames:
            fails.append((name, 0, "openpyxl 打不开这张表"))
            continue
        ws = wb[name]
        rows = [(r, list(row)) for r, row in
                enumerate(ws.iter_rows(min_row=1, max_row=ws.max_row, max_col=16, values_only=True), 1)]
        header_row, cols = find_header(ws)
        data_rows = [(r, row) for r, row in rows if r > header_row]
        code_col = pick(cols, HDR_CODE)
        if not code_col or sum(1 for r, row in data_rows
                               if code_col <= len(row) and is_code(row[code_col - 1])) < 5:
            cc = content_code_col(data_rows)
            if cc:
                code_col = cc
        anchors, extra = sheet_anchors(z, tgt)
        if not code_col:
            fails.append((name, header_row, "找不到型号列"))
            per_sheet.append((name, len(data_rows), len(anchors), 0, 0, 0))
            continue
        price_cols = {}
        for c, h in sorted(cols.items()):
            if c == code_col:
                continue
            if any(n in h for n in HDR_PRICE) and not any(k in h for k in HDR_SKIP):
                price_cols[c] = h

        sheet_recs = []
        for r, row in data_rows:
            code = s(row[code_col - 1]) if code_col <= len(row) else ""
            if not is_code(code):
                continue
            key = code_key(code)
            it = by_code.get(key)
            if it is None and re.match(r"^(WL\d{2}-[0-9]+)[BTHYA]$", key):
                it = by_code.get(re.match(r"^(WL\d{2}-[0-9]+)[BTHYA]$", key).group(1))
            prices = {}
            for c in price_cols:
                v = s(row[c - 1]) if c <= len(row) else ""
                if re.fullmatch(r"-?\d+(\.\d+)?", v):
                    prices[c] = v
            rec = {"sheet": name, "row": r, "code": code, "key": key, "item": it,
                   "img": anchors.get(r), "prices": prices}
            sheet_recs.append(rec)
            recs.append(rec)
        per_sheet.append((name, len(data_rows), len(anchors), extra,
                          sum(1 for x in sheet_recs if x["img"]),
                          sum(1 for x in sheet_recs if x["img"] and x["item"])))
        print("  [%-10s] 行=%-5d 图表=%-4d 有码=%-4d 对上=%-4d"
              % (name, len(data_rows), len(anchors),
                 sum(1 for x in sheet_recs if x["img"]),
                 sum(1 for x in sheet_recs if x["img"] and x["item"])))
    wb.close()

    # ---- 汇总
    with_img = [r for r in recs if r["img"]]
    matched = [r for r in with_img if r["item"]]
    need = [r for r in matched if not r["item"].get("p")]
    print("\n锚点图 %d 个 → 对上站里型号 %d 个（%.1f%%），其中还没有图的 %d 个"
          % (len(with_img), len(matched), 100.0 * len(matched) / max(1, len(with_img)), len(need)))

    # ---- 逐表清单（报告用）
    table = []
    for name, rows_n, anc, extra, has_img, ok in per_sheet:
        rate = (100.0 * ok / has_img) if has_img else 0.0
        table.append((name, rows_n, anc, extra, has_img, ok, rate))
    for t in table:
        print("  %-12s 行=%-5d 锚点=%-4d 同行多图=%-3d 有图行=%-4d 匹配=%-4d 匹配率=%.1f%%" % t)

    if dry:
        print("\n（试运行，用时 %.1f 秒）" % (time.time() - t0))
        return 0

    # ---------------------------------------------------------- 写图
    todo, dup = {}, []
    for r in matched:
        key = re.sub(r"\s+", "", r["item"]["m"].upper())
        if r["item"].get("p"):
            continue
        if key in todo:
            dup.append(r["code"])
            continue
        todo[key] = r
    print("\n需要补图的型号 %d 个（重复 %d）" % (len(todo), len(dup)))

    z2 = zipfile.ZipFile(SRC)
    written = 0
    fail_rows = []
    for key, r in todo.items():
        it = r["item"]
        cat = it["c"]
        base = norm_code(it["m"])
        d = os.path.join(IMG_ROOT, cat)
        os.makedirs(os.path.join(d, "t"), exist_ok=True)
        full = os.path.join(d, base + ".webp")
        thumb = os.path.join(d, "t", base + ".webp")
        if os.path.exists(full):
            continue
        try:
            im = prep(z2.read(r["img"]))
            save_webp(im, full, 82, FULL_BYTES)
            save_webp(fit(im, THUMB_EDGE), thumb, THUMB_Q)
            written += 1
            r["p"] = "images/%s/%s.webp" % (cat, base)
            r["t"] = "images/%s/t/%s.webp" % (cat, base)
        except Exception as e:
            fail_rows.append((r["sheet"], r["row"], r["code"], str(e)[:60]))
    print("新写图片 %d 张" % written)

    # ---------------------------------------------------------- 合并 data.js
    filled = 0
    for key, r in todo.items():
        if r.get("p") and not r["item"].get("p"):
            r["item"]["p"] = r["p"]
            r["item"]["t"] = r["t"]
            filled += 1
    payload = dict(site)
    payload["generated"] = time.strftime("%Y-%m-%d %H:%M")
    with open(DATA_JS, "w", encoding="utf-8", newline="\n") as f:
        f.write("/* 型号查询站数据文件 —— 由 build.py 自动生成，别手改。 */\n")
        f.write("/* 字段：i=编号 c=品类 m=型号 n=品名 b=品牌 oe=主OE号 x=交叉号数组 a=适配车型 r=备注 p=大图 t=缩略图 */\n")
        f.write("window.SITE_DATA=")
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";\n")
    print("data.js：补了 %d 个型号的图字段" % filled)

    # ---------------------------------------------------------- 价格
    base_fields = ["来源文件", "工作表", "行号", "商品编码", "名称"]
    rows_csv = []
    if os.path.exists(PRICE_CSV):
        with open(PRICE_CSV, encoding="utf-8-sig", newline="") as f:
            rows_csv = list(csv.DictReader(f))
    fields = set(base_fields)
    for r in rows_csv:
        fields.update(r.keys())
    idx = {(r.get("来源文件", ""), r.get("工作表", ""), r.get("商品编码", "")): i for i, r in enumerate(rows_csv)}
    added = updated = 0
    for r in recs:
        if not r["prices"]:
            continue
        row = {"来源文件": SRC_NAME, "工作表": r["sheet"], "行号": str(r["row"]), "商品编码": r["code"], "名称": ""}
        for c, v in r["prices"].items():
            row["价格col%d" % c] = v
            fields.add("价格col%d" % c)
        k = (SRC_NAME, r["sheet"], r["code"])
        if k in idx:
            rows_csv[idx[k]].update(row)
            updated += 1
        else:
            idx[k] = len(rows_csv)
            rows_csv.append(row)
            added += 1
    pc = sorted([f for f in fields if re.fullmatch(r"价格col\d+", f)], key=lambda x: int(x.replace("价格col", "")))
    fieldnames = base_fields + pc + sorted([f for f in fields if f not in base_fields and not re.fullmatch(r"价格col\d+", f)])
    os.makedirs(PRICE_DIR, exist_ok=True)
    with open(PRICE_CSV, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, restval="")
        w.writeheader()
        for r in rows_csv:
            w.writerow({k: r.get(k, "") for k in fieldnames})
    print("价格：新增 %d 行 / 更新 %d 行（共 %d 行）" % (added, updated, len(rows_csv)))

    # ---------------------------------------------------------- 待人工对应
    os.makedirs(MANUAL_DIR, exist_ok=True)
    man = [r for r in recs if r["img"] and not r["item"]]
    n_man = 0
    lines_man = ["表名, 行号, 编码, 原因"]
    for r in man[:200]:
        try:
            im = prep(z2.read(r["img"]))
            save_webp(im, os.path.join(MANUAL_DIR, "P%s_%d.webp" % (norm_code(r["code"] or "x"), r["row"])), 82, FULL_BYTES)
            n_man += 1
        except Exception:
            pass
        lines_man.append("%s, %d, %s, 站里没有这个编码" % (r["sheet"], r["row"], r["code"]))
    with open(os.path.join(MANUAL_DIR, "对应清单.csv"), "w", encoding="utf-8-sig", newline="") as f:
        f.write("\n".join(lines_man) + "\n")
    z2.close()

    # ---------------------------------------------------------- 报告
    reps = ["大目录补图报告",
            "来源：%s" % SRC_NAME,
            "时间：%s" % time.strftime("%Y-%m-%d %H:%M:%S"),
            "=" * 66,
            "一、逐表清单",
            "   %-12s %6s %6s %6s %6s %6s %7s" % ("表名", "行数", "锚点", "多图", "有图行", "匹配", "匹配率")]
    for t in table:
        reps.append("   %-12s %6d %6d %6d %6d %6d %6.1f%%" % t)
    reps.append("")
    reps.append("二、结果")
    reps.append("   锚点图 %d 个，对上站里型号 %d 个" % (len(with_img), len(matched)))
    reps.append("   本轮新补图 %d 张（其余型号上一轮已有图，按规则不覆盖）" % written)
    reps.append("   同行多图只取第一张：%d 处" % sum(t[3] for t in table))
    reps.append("   待人工对应：%d 张 → %s" % (n_man, MANUAL_DIR))
    reps.append("")
    reps.append("三、价格")
    reps.append("   价格表新增 %d 行 / 更新 %d 行；公开站不写价格" % (added, updated))
    reps.append("")
    reps.append("四、失败")
    for x in fail_rows[:30]:
        reps.append("   %s 第%d行 %s：%s" % x)
    if not fail_rows:
        reps.append("   无")
    with open(REPORT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(reps) + "\n")
    print("报告：%s" % REPORT)
    print("完成，用时 %.1f 秒" % (time.time() - t0))
    return 0


if __name__ == "__main__":
    sys.exit(main())