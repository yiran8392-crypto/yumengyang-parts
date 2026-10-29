# -*- coding: utf-8 -*-
"""
3333 版目录（带价格）导入器
============================
把「线圈 碳罐 机油阀 阀体 马达 分火线 产品目录（带价格）3333.xlsx」并进站点：

  1. 逐表自适应解析：表头优先，表头错位/缺失时按内容（WL 编码列）兜底
  2. 图片：读 drawing 锚点 → 行 → SKU；裁白边、白底方形、长边≤800px、webp≤80KB，
     存 images/<品类>/<型号>.webp 和 260px 缩略图（t/），已存在的不覆盖
  3. 合并 data/data.js：老 SKU 只补空字段（OE/车型/备注/图），新 SKU 追加并分配稳定 slug
  4. 价格全部写进 内部价格-不发布/价格表.csv（公开数据里一个价格都不写）
  5. 对不上的图 / 解析不了的行 → 解析失败清单-3333.txt

用法：
    python import_3333.py --dry     # 只解析，看统计，不写任何文件
    python import_3333.py           # 真跑
"""

import csv
import io
import json
import os
import re
import sys
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from xml.etree import ElementTree as ET

import openpyxl
from PIL import Image, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = r"D:\xwechat_files\wxid_cg3ddv5d0i7z22_4bfc\msg\file\2026-10\线圈 碳罐 机油阀 阀体 马达 分火线 产品目录（带价格）3333.xlsx"
SRC_NAME = os.path.basename(SRC)
DATA_JS = os.path.join(HERE, "data", "data.js")
IMG_DIR = os.path.join(HERE, "images")
PRICE_DIR = os.path.join(HERE, "内部价格-不发布")
PRICE_CSV = os.path.join(PRICE_DIR, "价格表.csv")
FAIL_PATH = os.path.join(HERE, "解析失败清单-3333.txt")

S = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
X = "{http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"

FULL_EDGE, FULL_BYTES, THUMB_EDGE, THUMB_Q = 800, 80 * 1024, 260, 78

SHEET_CAT = {
    "点火线圈": "coil", "分火线": "wire", "高压线": "wire",
    "步进电机": "stepper", "怠速马达": "stepper",
    "室外温度传感器": "temp", "水温传感器": "temp", "天博水温传感器": "temp",
    "机油温度传感器": "temp", "温度传感器": "temp",
    "喷油嘴": "injector", "电子": "throttle", "机械": "throttle",
    "节气门阀体": "throttle", "碳罐电磁阀": "purge",
    "油压传感器": "fuelpress", "油压调节器": "fuelpress",
    "空气流量计": "maf", "机油控制阀": "ocv", "火花塞": "plug",
    "节温器": "thermo", "氧传感器": "o2", "ABS传感器": "abs",
}

CN_EN = {
    "点火线圈": "Ignition Coil", "分火线": "Spark Plug Wire Set", "高压线": "Spark Plug Wire Set",
    "步进电机": "Idle Stepper Motor", "怠速马达": "Idle Stepper Motor",
    "水温传感器": "Coolant Temperature Sensor", "空气温度传感器": "Air Temperature Sensor",
    "室外温度传感器": "Ambient Temperature Sensor", "机油温度传感器": "Oil Temperature Sensor",
    "喷油嘴": "Fuel Injector", "电子": "Electronic Throttle Body", "机械": "Throttle Body",
    "节气门阀体总成": "Throttle Body Assembly", "节气门阀体": "Throttle Body",
    "碳罐电磁阀": "Canister Purge Valve", "油压调节器": "Fuel Pressure Regulator",
    "空气流量计": "Mass Air Flow Sensor", "机油控制阀": "Oil Control Valve",
    "火花塞": "Spark Plug", "火花塞套筒": "Spark Plug Socket", "节温器": "Thermostat",
}


def s(v):
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    t = str(v).replace("\u00a0", " ").replace("\u3000", " ")
    t = t.replace("\r", " ").replace("\n", " ")
    return re.sub(r"\s+", " ", t).strip()


def has_cn(t):
    return bool(re.search(r"[\u4e00-\u9fa5]", t or ""))


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


BRAND_EN = {"威利": "WEILI", "加加": "JJ", "天博": "TIANBO", "博世": "BOSCH", "德尔菲": "DELPHI",
            "德尔福": "DELPHI", "西门子": "SIEMENS", "电装": "DENSO", "马瑞利": "MAGNETI MARELLI",
            "玛瑞利": "MAGNETI MARELLI", "联电": "UAES", "摩托罗拉": "MOTOROLA"}


def brand_en(b):
    b = s(b)
    if not b:
        return ""
    if b in BRAND_EN:
        return BRAND_EN[b]
    return b if not has_cn(b) else ""


def norm_code(t):
    return re.sub(r"[^A-Za-z0-9_.-]", "_", s(t))


def clean_code(t):
    """OE 里常带（不带管）/弯头 这类中文备注，去掉中文和括号，只留号。"""
    t = s(t)
    if not t:
        return ""
    t = re.sub(r"[（(][^）)]*[）)]", " ", t)
    t = re.sub(r"[\u4e00-\u9fa5]+", " ", t)
    t = re.sub(r"\s+", " ", t).strip(" ,;")
    return t if re.search(r"[0-9]", t) else ""


def split_nums(text):
    t = s(text)
    if not t:
        return "", []
    parts = [p.strip(" ,，、/;|=") for p in re.split(r"[,，;；/|]+", t)]
    parts = [p for p in parts if p and re.search(r"[0-9]", p)]
    if len(parts) <= 1:
        return (parts[0] if parts else t), []
    return parts[0], [p for p in parts[1:] if len(p) >= 4]


# ------------------------------------------------------------------ 工作簿
def sheet_list(z):
    wbx = ET.fromstring(z.read("xl/workbook.xml"))
    rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    rmap = {x.get("Id"): x.get("Target") for x in rels}
    return [(sh.get("name"), rmap.get(sh.get(REL + "id")))
            for sh in wbx.find(S + "sheets").findall(S + "sheet")]


def sheet_anchors(z, target):
    rp = "xl/worksheets/_rels/%s.rels" % target.split("/")[-1]
    if rp not in z.namelist():
        return []
    dpath = None
    for x in ET.fromstring(z.read(rp)):
        tg = x.get("Target") or ""
        if (x.get("Type") or "").endswith("/drawing") and tg.endswith(".xml"):
            dpath = "xl/" + tg.replace("../", "")
    if not dpath or dpath not in z.namelist():
        return []
    imap = {}
    relp = dpath.replace("drawings/", "drawings/_rels/") + ".rels"
    if relp in z.namelist():
        for x in ET.fromstring(z.read(relp)):
            imap[x.get("Id")] = x.get("Target")
    out = []
    for c in ET.fromstring(z.read(dpath)):
        f = c.find(X + "from")
        if f is None:
            continue
        blip = c.find(".//" + A + "blip")
        tgt = imap.get(blip.get(REL + "embed")) if blip is not None else None
        if tgt:
            out.append((int(f.find(X + "row").text) + 1, "xl/" + tgt.replace("../", "")))
    return out


# ------------------------------------------------------------------ 表头
HDR_CODE = ["商品编码", "产品编码", "物料编码", "编码", "料号", "威利编号", "产品型号", "型号"]
HDR_NAME = ["名称", "品名", "产品名称", "商品名称", "型号"]
HDR_OE = ["原厂图号", "OE", "OEM", "原厂号", "图号", "原厂编号"]
HDR_APP = ["适用车型", "产品车型", "车型", "应用车型"]
HDR_BRAND = ["品牌"]
HDR_IMG = ["图片", "商品图片", "产品图片"]
HDR_PRICE = ["价", "单价", "调价", "费用"]
HDR_SKIP = ["序号", "材质", "盒", "支", "用量", "指数", "系统", "步进电机", "传感器"]


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
            if any(any(n.lower() in h.lower() for n in g)
                   for g in (HDR_CODE, HDR_NAME, HDR_OE, HDR_APP, HDR_PRICE, HDR_BRAND, HDR_IMG)):
                hit += 1
        if hit > best[0]:
            best = (hit, r, cols)
    return best[1], best[2]


def cjk_name_col(rows, used):
    """没有品名列时，找「短中文名词」最多的一列（车型那种长句不算）。"""
    best, score = None, 0
    for c in range(1, 10):
        if c in used:
            continue
        tot = hit = 0
        for r, row in rows:
            v = s(row[c - 1]) if c <= len(row) else ""
            if v:
                tot += 1
                if has_cn(v) and len(v) <= 10:
                    hit += 1
        if tot >= 5 and hit >= 5 and hit > score:
            best, score = c, hit
    return best


def content_code_col(rows):
    score = {}
    for r, row in rows:
        for i, v in enumerate(row[:12], 1):
            if is_code(v):
                score[i] = score.get(i, 0) + 1
    return max(score, key=score.get) if score else None


def parse_sheet(ws, name, fails):
    header_row, cols = find_header(ws)
    rows = [(r, list(row)) for r, row in
            enumerate(ws.iter_rows(min_row=1, max_row=ws.max_row, max_col=16, values_only=True), 1)]
    data = [(r, row) for r, row in rows if r > header_row]

    code_col = pick(cols, HDR_CODE)
    if not code_col or sum(1 for r, row in data if code_col <= len(row) and is_code(row[code_col - 1])) < 5:
        cc = content_code_col(data)
        if cc:
            code_col = cc
    if not code_col:
        fails.append((name, header_row, "找不到型号列", ""))
        return []

    # 先认 OE / 车型 / 品牌，最后才处理品名（有的表没有品名列，别把「适用车型」抢走）
    used = {code_col}
    oe_col = pick(cols, HDR_OE, exclude=used)
    if oe_col:
        used.add(oe_col)
    app_col = pick(cols, HDR_APP, exclude=used)
    if app_col:
        used.add(app_col)
    brand_col = pick(cols, HDR_BRAND, exclude=used)
    if brand_col:
        used.add(brand_col)
    name_col = pick(cols, HDR_NAME, exclude=used)
    if name_col:
        used.add(name_col)
    else:
        name_col = cjk_name_col(data, used)
        if name_col:
            used.add(name_col)

    price_cols = {}
    for c, h in sorted(cols.items()):
        if c in used:
            continue
        if any(n in h for n in HDR_PRICE) and not any(k in h for k in HDR_SKIP):
            price_cols[c] = h

    # 品牌列其实是 OE 号（机油控制阀那种）
    if brand_col and not oe_col:
        vals = [s(row[brand_col - 1]) for r, row in data if brand_col <= len(row) and s(row[brand_col - 1])]
        codelike = [v for v in vals if re.search(r"[0-9]", v) and not has_cn(v)]
        if vals and len(codelike) >= max(3, int(len(vals) * 0.6)):
            oe_col, brand_col = brand_col, None

    if not price_cols:
        for c in sorted(cols):
            if c in used or c in (oe_col,):
                continue
            tot = num = 0
            for r, row in data:
                if c <= len(row) and s(row[c - 1]):
                    tot += 1
                    if re.fullmatch(r"-?\d+(\.\d+)?", s(row[c - 1])):
                        num += 1
            if tot >= 5 and num >= tot * 0.7:
                price_cols[c] = cols[c]

    def cell(row, c):
        return s(row[c - 1]) if c and c <= len(row) else ""

    recs, bad = [], 0
    for r, row in data:
        code = cell(row, code_col)
        if not code:
            continue
        extra = []
        if not is_code(code) and "/" in code:
            head, tail = code.split("/", 1)
            if is_code(head):
                code = head
                extra = [x.strip() for x in tail.split("/") if x.strip() and len(x.strip()) >= 4]
        if not is_code(code):
            bad += 1
            fails.append((name, r, "型号列不是标准 WL/JJ 型号", code[:30]))
            continue
        prices = {}
        for c in price_cols:
            v = cell(row, c)
            if re.fullmatch(r"-?\d+(\.\d+)?", v):
                prices[c] = v
        nm = cell(row, name_col)
        xs = list(extra)
        if nm and not has_cn(nm) and re.search(r"[0-9]|-", nm) and len(nm) >= 4:
            xs.append(nm)          # 「型号」列其实是火花塞型号之类的编号
            nm = ""
        oe, ox = split_nums(cell(row, oe_col)) if oe_col else ("", [])
        oe = clean_code(oe)
        xs = [clean_code(x) for x in (ox + xs)]
        xs = [x for x in xs if x and x.upper() != oe.upper()]
        recs.append({"row": r, "code": code, "key": code_key(code), "name": nm,
                     "brand": cell(row, brand_col) if brand_col else "",
                     "oe": oe, "x": xs, "app": cell(row, app_col),
                     "prices": prices, "sheet": name})
    return recs


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
            with open(path, "wb") as f:
                f.write(data)
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


def main():
    dry = "--dry" in sys.argv
    t0 = time.time()
    print("=" * 68)
    print(" 3333 目录导入%s" % ("（试运行，不写文件）" if dry else ""))
    print("=" * 68)

    raw = io.open(DATA_JS, encoding="utf-8").read()
    i = raw.find("window.SITE_DATA=")
    site, _ = json.JSONDecoder().raw_decode(raw[i + len("window.SITE_DATA="):])
    items = site["items"]
    cat_list = site["cats"]
    cat_meta = {}
    try:
        sys.path.insert(0, HERE)
        import sitegen
        for k, v in sitegen.CAT_META.items():
            cat_meta[k] = v
        import import_catalogs as ic
        for k, v in ic.NEW_CATS.items():
            cat_meta[k] = v          # (slug, 英文复名, 英文单数, 中文)
    except Exception as e:
        print("  !! 读品类元信息失败：%s" % e)
    for c in cat_list:
        cat_meta.setdefault(c["key"], (c["key"], c.get("en"), c.get("en"), c.get("name")))

    by_key = {}
    for it in items:
        by_key.setdefault(code_key(it["m"]), it)
    print("现有：%d 型号 / %d 品类" % (len(items), len(cat_list)))

    z = zipfile.ZipFile(SRC)
    wb = openpyxl.load_workbook(SRC, read_only=True, data_only=True)
    fails = []
    recs_all = []
    sheet_info = []
    for name, tgt in sheet_list(z):
        if name not in wb.sheetnames:
            fails.append((name, 0, "工作簿里没有这张表", ""))
            continue
        anch = {}
        for row, media in sheet_anchors(z, tgt):
            anch.setdefault(row, media)
        recs = parse_sheet(wb[name], name, fails)
        votes = {}
        for r in recs:
            it = by_key.get(r["key"])
            if it:
                votes[it["c"]] = votes.get(it["c"], 0) + 1
        cat = max(votes, key=votes.get) if votes else SHEET_CAT.get(name)
        if not cat:
            pref = recs[0]["key"].split("-")[0] if recs else ""
            votes2 = {}
            for it in items:
                if it["m"].upper().startswith(pref + "-"):
                    votes2[it["c"]] = votes2.get(it["c"], 0) + 1
            cat = max(votes2, key=votes2.get) if votes2 else None
        if not cat:
            fails.append((name, 0, "认不出这个表属于哪个品类", ""))
            continue
        for r in recs:
            r["cat"] = cat
            r["anchors"] = anch
        recs_all.extend(recs)
        sheet_info.append((name, len(recs), len(anch), cat))
        print("  [%-12s] 行=%-4d 图锚点=%-4d 品类=%s" % (name, len(recs), len(anch), cat))
    wb.close()

    # 去重
    seen, uniq = set(), []
    for r in recs_all:
        if r["key"] in seen:
            fails.append((r["sheet"], r["row"], "同一型号重复出现，保留第一行", r["code"]))
            continue
        seen.add(r["key"])
        uniq.append(r)
    recs_all = uniq
    rec_by_key = {r["key"]: r for r in recs_all}

    # ---- 锚点 → 型号
    img_for = {}          # key -> media path
    img_dup = 0
    for r in recs_all:
        anch = r["anchors"]
        media = anch.get(r["row"])
        if not media:
            for d in (-1, 1, -2, 2):
                if anch.get(r["row"] + d) and not any(
                        rr["anchors"].get(r["row"] + d) == anch[r["row"] + d] and rr is not r
                        for rr in recs_all if rr["sheet"] == r["sheet"]):
                    media = anch.get(r["row"] + d)
                    break
        if not media:
            continue
        if r["key"] in img_for:
            img_dup += 1
            continue
        img_for[r["key"]] = media
        # 变体（B/T/Y…）的图，主型号也补一张
        m = re.match(r"^(WL\d{2}-[0-9]+)([BTHYA])$", r["key"])
        if m and m.group(1) in rec_by_key and m.group(1) not in img_for:
            img_for[m.group(1)] = media

    used_media = {}
    for k, v in img_for.items():
        used_media[v] = used_media.get(v, 0) + 1
    unused = sum(1 for name, tgt in sheet_list(z) for row, media in sheet_anchors(z, tgt)
                 if media not in used_media)
    print("\n图片：锚点 %d → 对上型号 %d 个（其中同图多用 %d）" % (
        sum(len(sheet_anchors(z, t)) for _, t in sheet_list(z)), len(img_for), img_dup))

    fixed = [r for r in recs_all if r["key"] in by_key]
    new = [r for r in recs_all if r["key"] not in by_key]
    from collections import Counter
    print("记录 %d：已有 %d / 新增 %d" % (len(recs_all), len(fixed), len(new)))
    print("  新增：", dict(Counter(r["cat"] for r in new)))
    print("  已有：", dict(Counter(r["cat"] for r in fixed)))
    print("  有图的记录 %d（其中新增 %d）" % (
        len(img_for), sum(1 for r in new if r["key"] in img_for)))

    if dry:
        print("\n（试运行，用时 %.1f 秒）失败/留意 %d 条" % (time.time() - t0, len(fails)))
        for f in fails[:12]:
            print("   ", f)
        z.close()
        return 0

    # ---------------------------------------------------------- 1. 图片落盘
    import threading
    stats = {"write": 0, "exists": 0, "thumb": 0, "err": 0}
    zlocal = {}

    def zf():
        t = threading.get_ident()
        if t not in zlocal:
            zlocal[t] = zipfile.ZipFile(SRC)
        return zlocal[t]

    def work(key):
        rec = rec_by_key[key]
        cat, base = rec["cat"], norm_code(rec["code"])
        full = os.path.join(IMG_DIR, cat, base + ".webp")
        thumb = os.path.join(IMG_DIR, cat, "t", base + ".webp")
        try:
            os.makedirs(os.path.dirname(thumb), exist_ok=True)
            if os.path.exists(full):
                if not os.path.exists(thumb):
                    im = Image.open(full).convert("RGB")
                    save_webp(fit(im, THUMB_EDGE), thumb, THUMB_Q)
                    return key, "thumb"
                return key, "exists"
            im = prep(zf().read(img_for[key]))
            save_webp(im, full, 82, FULL_BYTES)
            save_webp(fit(im, THUMB_EDGE), thumb, THUMB_Q)
            return key, "write"
        except Exception as e:
            return key, "err:" + str(e)[:70]

    keys = list(img_for.keys())
    done = 0
    print("\n图片处理 %d 张 …" % len(keys))
    with ThreadPoolExecutor(max_workers=8) as ex:
        for key, st in ex.map(work, keys):
            done += 1
            if done % 200 == 0:
                print("   %d/%d" % (done, len(keys)))
            if st == "write":
                stats["write"] += 1
            elif st in ("exists", "thumb"):
                stats["exists" if st == "exists" else "thumb"] += 1
            else:
                stats["err"] += 1
                fails.append((rec_by_key[key]["sheet"], rec_by_key[key]["row"],
                              "图片处理失败 " + st[4:], rec_by_key[key]["code"]))
            if st in ("write", "exists", "thumb"):
                rec = rec_by_key[key]
                cat, base = rec["cat"], norm_code(rec["code"])
                rec["p"] = "images/%s/%s.webp" % (cat, base)
                rec["t"] = "images/%s/t/%s.webp" % (cat, base)
    for zz in zlocal.values():
        zz.close()
    print("   新写 %d / 已存在 %d / 只补缩略图 %d / 失败 %d"
          % (stats["write"], stats["exists"], stats["thumb"], stats["err"]))

    # ---------------------------------------------------------- 2. 合并 data.js
    sg = sys.modules.get("sitegen")
    filled = {"oe": 0, "app": 0, "app_better": 0, "brand": 0, "x": 0, "p": 0}
    for r in fixed:
        it = by_key[r["key"]]
        if r.get("p") and not it.get("p"):
            it["p"], it["t"] = r["p"], r["t"]
            filled["p"] += 1
        if r["oe"] and not it.get("oe"):
            it["oe"] = r["oe"]
            filled["oe"] += 1
        if r["x"] and not it.get("x"):
            it["x"] = r["x"][:12]
            filled["x"] += 1
        if r["app"]:
            old = it.get("a") or ""
            if not old:
                it["a"] = r["app"]
                filled["app"] += 1
            elif len(r["app"]) >= len(old) * 1.5 and len(r["app"]) >= 20:
                it["a"] = r["app"]
                filled["app_better"] += 1
        if r["brand"] and not it.get("b"):
            b = brand_en(r["brand"])
            if b:
                it["b"] = b
                filled["brand"] += 1

    # 新 SKU
    used_slugs = set(it.get("s") for it in items if it.get("s"))
    next_i = max((it["i"] for it in items), default=0) + 1
    cat_one = {k: (v[2] if len(v) > 2 else v[1]) for k, v in cat_meta.items()}
    added = []
    for r in new:
        base = sg.slugify(r["oe"] or r["code"]) if sg else re.sub(r"[^a-z0-9-]", "", (r["oe"] or r["code"]).lower())
        base = base or ("part-%d" % next_i)
        slug, n = base, 2
        while slug in used_slugs:
            slug = "%s-%d" % (base, n)
            n += 1
        used_slugs.add(slug)
        nm = r["name"] if (r["name"] and not has_cn(r["name"])) else CN_EN.get(r["name"] or "", "")
        if not nm:
            nm = cat_one.get(r["cat"]) or "Auto Part"
        it = {"i": next_i, "c": r["cat"], "m": r["code"], "n": nm,
              "b": brand_en(r["brand"]) or "WEILI", "oe": r["oe"], "x": r["x"][:12],
              "a": r["app"], "r": "", "p": r.get("p", ""), "t": r.get("t", ""), "s": slug}
        items.append(it)
        by_key[r["key"]] = it
        added.append(it)
        next_i += 1
    print("\n合并：老型号补字段 %s" % filled)
    print("      新增型号 %d 个" % len(added))

    # 品类统计
    cnt = {}
    for it in items:
        cnt[it["c"]] = cnt.get(it["c"], 0) + 1
    cats_out = []
    seen_cat = set()
    for c in cat_list:
        k = c["key"]
        if k in cnt:
            cats_out.append({"key": k, "name": c.get("name") or k, "en": c.get("en") or k, "n": cnt[k]})
            seen_cat.add(k)
    new_cats = []
    for k in sorted(cnt):
        if k in seen_cat:
            continue
        meta = cat_meta.get(k, (k, k, k, k))
        cats_out.append({"key": k, "name": meta[3] if len(meta) > 3 else k,
                         "en": meta[1], "n": cnt[k]})
        new_cats.append(k)

    payload = {"generated": time.strftime("%Y-%m-%d %H:%M"),
               "company": site.get("company") or "Guangzhou Yumengyang Auto Parts Co., Ltd.",
               "cats": cats_out, "items": items}
    with open(DATA_JS, "w", encoding="utf-8", newline="\n") as f:
        f.write("/* 型号查询站数据文件 —— 由 build.py 自动生成，别手改。 */\n")
        f.write("/* 字段：i=编号 c=品类 m=型号 n=品名 b=品牌 oe=主OE号 x=交叉号数组 a=适配车型 r=备注 p=大图 t=缩略图 */\n")
        f.write("window.SITE_DATA=")
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";\n")
    print("data.js 写好：%d 型号 / %d 品类%s" % (len(items), len(cats_out),
                                             ("，新品类 " + ",".join(new_cats)) if new_cats else ""))

    # ---------------------------------------------------------- 3. 价格表
    base_fields = ["来源文件", "工作表", "行号", "商品编码", "名称"]
    rows = []
    if os.path.exists(PRICE_CSV):
        with open(PRICE_CSV, encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
    fields = set(base_fields)
    for r in rows:
        fields.update(r.keys())
    idx = {(r.get("来源文件", ""), r.get("工作表", ""), r.get("商品编码", "")): i for i, r in enumerate(rows)}
    p_added = p_updated = 0
    for r in recs_all:
        if not r["prices"]:
            continue
        row = {"来源文件": SRC_NAME, "工作表": r["sheet"], "行号": str(r["row"]),
               "商品编码": r["code"], "名称": r["name"]}
        for c, v in r["prices"].items():
            row["价格col%d" % c] = v
            fields.add("价格col%d" % c)
        k = (SRC_NAME, r["sheet"], r["code"])
        if k in idx:
            rows[idx[k]].update(row)
            p_updated += 1
        else:
            idx[k] = len(rows)
            rows.append(row)
            p_added += 1
    pc = sorted([f for f in fields if re.fullmatch(r"价格col\d+", f)], key=lambda x: int(x.replace("价格col", "")))
    fieldnames = base_fields + pc + sorted([f for f in fields if f not in base_fields and not f.startswith("价格col")])
    os.makedirs(PRICE_DIR, exist_ok=True)
    with open(PRICE_CSV, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, restval="")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})
    print("价格表：新增 %d 行 / 更新 %d 行（共 %d 行，只在 内部价格-不发布）" % (p_added, p_updated, len(rows)))

    # ---------------------------------------------------------- 4. 失败清单
    lines = ["3333 版目录（带价格）解析清单",
             "来源文件：%s" % SRC_NAME,
             "生成时间：%s" % time.strftime("%Y-%m-%d %H:%M:%S"),
             "=" * 64,
             "一、解析不了 / 对不上的行（没有硬编，原样记下来）"]
    if fails:
        for sheet, row, why, raw in fails:
            lines.append("   [%s] 第 %s 行  -> %s   （原内容：%s）" % (sheet, row, why, raw))
    else:
        lines.append("   没有。")
    lines.append("")
    lines.append("二、各表统计")
    for name, n, anc, cat in sheet_info:
        lines.append("   %-12s 解析 %-4d 行 · 图锚点 %-4d · 品类 %s" % (name, n, anc, cat))
    lines.append("")
    lines.append("三、图片")
    lines.append("   锚点合计 1976，对上型号 %d 张；新写 %d，已存在跳过 %d，失败 %d"
                 % (len(keys), stats["write"], stats["exists"] + stats["thumb"], stats["err"]))
    lines.append("")
    lines.append("四、合并结果")
    lines.append("   老型号补字段：%s" % filled)
    lines.append("   新增型号 %d 个，价格新增 %d 行 / 更新 %d 行" % (len(added), p_added, p_updated))
    with open(FAIL_PATH, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print("清单：%s" % FAIL_PATH)
    z.close()
    print("\n完成，用时 %.1f 秒" % (time.time() - t0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
