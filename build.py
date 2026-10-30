# -*- coding: utf-8 -*-
"""
型号查询站 - 数据构建脚本
=========================
作用：读取手上的英文版产品 Excel（只读，绝不修改），提取型号/OE/交叉号/车型/备注，
      把内嵌图片抽出来压成 webp，最后生成 data/data.js 和 images/ 目录。

直接双击“更新数据.cmd”即可，不需要懂代码。

设计原则：
  1) 源文件只读，任何情况下都不写回、不移动。
  2) 数据忠于 Excel：解析不了的行不瞎补，统一记到“解析失败清单.txt”。
  3) 图片缓存：源图没变就跳过压缩，第二次更新会很快。
"""

import html
import io
import json
import os
import re
import sys
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from xml.etree import ElementTree as ET

try:
    from PIL import Image, ImageOps
except Exception:  # pragma: no cover
    print("!! 缺少 Pillow 库，无法压缩图片。")
    raise

import openpyxl

# ---------------------------------------------------------------- 路径配置
HERE = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(HERE, "images")
DATA_DIR = os.path.join(HERE, "data")
CACHE_PATH = os.path.join(DATA_DIR, "_images_cache.json")
FAIL_PATH = os.path.join(HERE, "解析失败清单.txt")
DATA_JS = os.path.join(DATA_DIR, "data.js")

WS = r"D:\欧鲸鲸\default-workspace"
SRC = {
    "coil":   r"D:\欧鲸鲸\点火线圈-英文版-Ignition Coil.xlsx",
    "coil_x": r"D:\欧鲸鲸\点火线圈-出口版对照表-驭盟扬.xlsx",
    "coil_img_dir": os.path.join(WS, "点火线圈-图片"),
    "abs":    os.path.join(WS, "新增4类产品", "交付", "ABS传感器-ABS Sensor-English.xlsx"),
    "wire":   os.path.join(WS, "新增4类产品", "交付", "火花塞线-高压点火线-English.xlsx"),
    "thermo": os.path.join(WS, "新增4类产品", "交付", "节温器-Thermostat-English.xlsx"),
    "plug":   os.path.join(WS, "新增4类产品", "交付", "威利火花塞-Spark Plug-English-客户版(已去内部价格).xlsx"),
}

CATS = [
    {"key": "coil",   "name": "点火线圈",   "en": "Ignition Coils",      "dir": "coil"},
    {"key": "abs",    "name": "ABS 传感器", "en": "ABS Sensors",         "dir": "abs"},
    {"key": "wire",   "name": "火花塞线",   "en": "Spark Plug Wire Sets", "dir": "wire"},
    {"key": "thermo", "name": "节温器",     "en": "Thermostats",         "dir": "thermo"},
    {"key": "plug",   "name": "火花塞",     "en": "Spark Plugs",         "dir": "plug"},
]

FULL_EDGE = 800        # 大图长边
FULL_QUALITY = 88      # 大图质量
FULL_MAX_BYTES = 120 * 1024
THUMB_EDGE = 260       # 缩略图长边
THUMB_QUALITY = 80
TARGET_TOTAL_MB = 150  # 图片总体积目标

fails = []   # (品类, 位置, 问题, 原始内容)
warns = []
missing_imgs = {"coil": [], "abs": []}   # 有型号但源文件里找不到图的


# ---------------------------------------------------------------- 小工具
def log(msg):
    print(msg, flush=True)


def s(v):
    """单元格转干净字符串。"""
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    t = str(v).replace("\u00a0", " ").replace("\u3000", " ")
    t = html.unescape(t)          # 源表里有 &#10; &amp; 这类残留实体
    t = re.sub(r"[ \t]+", " ", t)
    return t.strip()


def uniq(seq):
    out, seen = [], set()
    for x in seq:
        k = x.upper()
        if x and k not in seen:
            seen.add(k)
            out.append(x)
    return out


def smart_split(text):
    """把 “主号 = 交叉号” 这种单元格拆成 (主号, [其它号])。
    只有拆出来的每一段都像编号（>=4 个字符）才拆，否则原样保留，避免把
    “022905100N/K/G/D/A” 这种拆成一堆单字母。"""
    t = s(text)
    if not t:
        return "", []
    parts = [p.strip(" ,，、/=") for p in re.split(r"[;=\n\r|/]+", t)]
    parts = [p for p in parts if p]
    if len(parts) >= 2 and all(len(p) >= 4 for p in parts):
        return parts[0], uniq(parts[1:])
    return display_text(t).strip(" ,;，;、"), []


def display_text(t):
    """展示用：换行变空格，多个空格压成一个。"""
    return re.sub(r"\s+", " ", str(t).replace("\u00a0", " ")).strip()


def clean_codes(seq):
    """过滤掉拆分产生的碎片（"/"、"K"、"036" 这种），只留像编号的。"""
    out = []
    for x in seq:
        x = s(x).strip("/=;,- ")
        if len(x) >= 4 and re.search(r"\d", x):
            out.append(x)
    return uniq(out)


def split_nums(text):
    """把一个单元格里的多个编号拆开。支持 ; 、换行、/ 和较长的空格间隔。"""
    if not text:
        return []
    parts = re.split(r"[;\n\r|]+", text)
    out = []
    for p in parts:
        p = p.strip(" ,，、")
        if not p:
            continue
        toks = [t for t in re.split(r"\s{2,}", p) if t.strip()]
        if len(toks) == 1:
            # 单个编号内部可能是 Bosch 那种 "F 000 ZS0 103" 的写法，别拆
            single = p
            if " " in single:
                words = single.split()
                if all(len(w) >= 4 for w in words) and len(words) <= 4 and re.search(r"\d", single):
                    out.extend(words)
                    continue
                if len(words) > 4:
                    out.extend(words)
                    continue
            out.append(single)
        else:
            for t in toks:
                out.extend(split_nums(t))
    return uniq(out)


def norm_code(code):
    """图片文件名安全化。"""
    return re.sub(r"[^A-Za-z0-9_.-]", "_", code)


def rowfail(cat, row, why, raw=""):
    fails.append((cat, row, why, s(raw)[:160]))


# ---------------------------------------------------------------- 数据源读取
def read_coil():
    """点火线圈：英文版主表 + 出口版对照表（补交叉号/车型）。"""
    items = []
    path = SRC["coil"]
    if not os.path.exists(path):
        warns.append("找不到点火线圈英文版：%s" % path)
        return items

    cross = {}
    xp = SRC["coil_x"]
    if os.path.exists(xp):
        wb = openpyxl.load_workbook(xp, read_only=True, data_only=True)
        ws = wb.worksheets[0]
        for i, row in enumerate(ws.iter_rows(min_row=3, max_col=15, values_only=True), 3):
            code = s(row[0])
            if not code:
                continue
            cross[code.upper()] = {
                "x": split_nums(s(row[4])),
                "app": s(row[9]) or s(row[8]),
            }
        wb.close()
    else:
        warns.append("找不到出口版对照表（交叉号会缺）：%s" % xp)

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb["Sheet1"] if "Sheet1" in wb.sheetnames else wb.worksheets[0]
    for i, row in enumerate(ws.iter_rows(min_row=3, max_col=8, values_only=True), 3):
        name = s(row[0])
        code = s(row[1])
        brand = s(row[3])
        oem = s(row[4])
        app = s(row[5])
        qty = s(row[6])
        sales = s(row[7])
        if not code and not oem:
            continue                      # 源文件大量空行，正常跳过，不算失败
        if not code:
            rowfail("点火线圈", i, "没有我方型号（Item Code）", oem)
            continue
        sup = cross.get(code.upper(), {})
        oe, xs = smart_split(oem)
        xs = clean_codes(xs + sup.get("x", []))
        if not app:
            app = sup.get("app", "")
        remark = []
        if qty:
            remark.append("Qty/vehicle: %s" % qty)
        if sales:
            remark.append("Sales index: %s" % sales)
        items.append({
            "cat": "coil", "m": code, "n": name or "Ignition Coil", "b": brand,
            "oe": oe, "x": xs, "a": app, "r": " | ".join(remark),
            "img": ("dir", os.path.join(SRC["coil_img_dir"], code)),
        })
    wb.close()
    return items


def read_abs():
    """ABS 传感器：英文版，图片按锚点行号对应。"""
    items = []
    path = SRC["abs"]
    if not os.path.exists(path):
        warns.append("找不到 ABS 传感器英文版：%s" % path)
        return items
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb["ABS Sensors"] if "ABS Sensors" in wb.sheetnames else wb.worksheets[0]
    for i, row in enumerate(ws.iter_rows(min_row=2, max_col=6, values_only=True), 2):
        name, code, _photo, brand, oem, app = [s(c) for c in row]
        if not code and not oem:
            continue
        if not code:
            rowfail("ABS 传感器", i, "没有我方型号（Item Code）", oem or app)
            continue
        nums = smart_split(oem)
        oe, xs = nums[0], clean_codes(nums[1])
        items.append({
            "cat": "abs", "m": code, "n": name or "ABS Sensor", "b": brand,
            "oe": oe, "x": xs, "a": app, "r": "",
            "img": ("zip_row", path, i),
        })
    wb.close()
    return items


def read_wire():
    """火花塞线：Part / OEM / Brand，OEM 列就是型号。"""
    items = []
    path = SRC["wire"]
    if not os.path.exists(path):
        warns.append("找不到火花塞线英文版：%s" % path)
        return items
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.worksheets[0]
    for i, row in enumerate(ws.iter_rows(min_row=2, max_col=3, values_only=True), 2):
        part, oem, brand = [s(c) for c in row]
        if not oem and not brand:
            continue
        if not oem:
            rowfail("火花塞线", i, "没有型号（OEM 列是空的）", brand)
            continue
        items.append({
            "cat": "wire", "m": oem, "n": part or "Spark Plug Wire Set", "b": brand,
            "oe": "", "x": [], "a": "", "r": "", "img": None,
        })
    wb.close()
    return items


def read_thermo():
    """节温器：无表头，5 列 = 序号 / 型号 / OEM / 品名 / 车型。"""
    items = []
    path = SRC["thermo"]
    if not os.path.exists(path):
        warns.append("找不到节温器英文版：%s" % path)
        return items
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.worksheets[0]
    for i, row in enumerate(ws.iter_rows(min_row=1, max_col=5, values_only=True), 1):
        a, code, oem, name, app = [s(c) for c in (list(row) + [None] * 5)[:5]]
        if not code and not oem:
            continue
        if a.lower() in ("no.", "no", "序号"):
            continue
        if not code:
            rowfail("节温器", i, "没有型号", oem or app)
            continue
        oe, xs = smart_split(oem)
        items.append({
            "cat": "thermo", "m": code, "n": name or "Thermostat", "b": "",
            "oe": oe, "x": clean_codes(xs), "a": app, "r": "", "img": None,
        })
    wb.close()
    return items


def read_plug():
    """火花塞：No. / Item Code / Product Name / Application / Unit / Remark / Pcs/Box。"""
    items = []
    path = SRC["plug"]
    if not os.path.exists(path):
        warns.append("找不到火花塞英文版：%s" % path)
        return items
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.worksheets[0]
    for i, row in enumerate(ws.iter_rows(min_row=2, max_col=7, values_only=True), 2):
        _no, code, name, app, unit, remark, pcs = [s(c) for c in (list(row) + [None] * 7)[:7]]
        if not code and not app:
            continue
        if not code:
            rowfail("火花塞", i, "没有型号（Item Code）", app)
            continue
        remark_parts = [p for p in (remark, ("%s pcs/box" % pcs) if pcs else "", ("Unit: %s" % unit) if unit else "") if p]
        items.append({
            "cat": "plug", "m": code, "n": name or "Spark Plug", "b": "",
            "oe": "", "x": [], "a": app, "r": " | ".join(remark_parts), "img": None,
        })
    wb.close()
    return items


# ---------------------------------------------------------------- 图片处理
def open_image(data):
    im = Image.open(io.BytesIO(data))
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        bg = Image.new("RGB", im.size, (255, 255, 255))
        bg.paste(im, mask=im.split()[-1])
        im = bg
    else:
        im = im.convert("RGB")
    return ImageOps.exif_transpose(im)


def resize(im, edge):
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


def load_cache():
    try:
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_cache(cache):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False)


def abs_row_map(xlsx_path):
    """从 xlsx 的 drawing 锚点算出“行号 -> 压缩包里的图片名”。"""
    z = zipfile.ZipFile(xlsx_path)
    S = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    X = "{http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing}"
    A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
    R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed"

    sheet = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
    heights, default_h = {}, 53.1
    fmt = sheet.find(S + "sheetFormatPr")
    if fmt is not None and fmt.get("defaultRowHeight"):
        default_h = float(fmt.get("defaultRowHeight"))
    for r in sheet.find(S + "sheetData").findall(S + "row"):
        heights[int(r.get("r"))] = float(r.get("ht") or default_h)
    maxrow = max(heights) if heights else 1

    tops, acc = {}, 0.0
    for i in range(1, maxrow + 2):
        tops[i] = acc
        acc += heights.get(i, default_h) * 12700.0

    draw = ET.fromstring(z.read("xl/drawings/drawing1.xml"))
    rels = ET.fromstring(z.read("xl/drawings/_rels/drawing1.xml.rels"))
    rmap = {x.get("Id"): x.get("Target") for x in rels}

    anchors = []
    for anch in draw:
        f = anch.find(X + "from")
        t = anch.find(X + "to")
        if f is None:
            continue
        r1, o1 = int(f.find(X + "row").text), int(f.find(X + "rowOff").text)
        r2 = int(t.find(X + "row").text) if t is not None else r1
        o2 = int(t.find(X + "rowOff").text) if t is not None else 0
        y1 = tops.get(r1 + 1, 0.0) + o1
        y2 = tops.get(r2 + 1, 0.0) + o2
        blip = anch.find(".//" + A + "blip")
        if blip is None:
            continue
        tgt = rmap.get(blip.get(R))
        if not tgt:
            continue
        anchors.append(((y1 + y2) / 2.0, r1, tgt))
    z.close()

    centers = [(i, (tops[i] + tops[i + 1]) / 2.0) for i in range(1, maxrow + 1)]
    mapping, used = {}, set()
    for cy, r1, tgt in sorted(anchors):
        best, bestd = None, None
        for row, c in centers:
            d = abs(c - cy)
            if bestd is None or d < bestd:
                best, bestd = row, d
        if best is None:
            continue
        if best in mapping:
            warns.append("ABS 第 %d 行有 2 张图，只保留第一张" % best)
            continue
        mapping[best] = tgt
        used.add(tgt)
    return mapping, used


def build_images(items):
    """给每条数据配图并压缩。返回统计。"""
    os.makedirs(IMG_DIR, exist_ok=True)
    cache = load_cache()
    new_cache = {}
    stats = {"full": 0, "bytes": 0, "thumb_bytes": 0, "noimg": 0, "err": 0}

    # 预取 ABS 的行->图片名映射
    abs_map, abs_used = {}, set()
    if any(it["img"] and it["img"][0] == "zip_row" for it in items):
        try:
            abs_map, abs_used = abs_row_map(SRC["abs"])
            log("  ABS 图片锚点：%d 张已定位" % len(abs_map))
        except Exception as e:
            warns.append("ABS 图片锚点解析失败：%s" % e)
            abs_map = {}

    coil_dir = SRC["coil_img_dir"]
    coil_files = {}
    if os.path.isdir(coil_dir):
        for fn in os.listdir(coil_dir):
            stem, ext = os.path.splitext(fn)
            if ext.lower() in (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"):
                if stem.endswith("_2"):
                    continue          # 同名补拍的备用图，跳过
                coil_files.setdefault(stem.upper(), os.path.join(coil_dir, fn))

    zip_local = {}   # 每个线程一个 ZipFile 句柄

    def get_zip():
        t = __import__("threading").get_ident()
        if t not in zip_local:
            zip_local[t] = zipfile.ZipFile(SRC["abs"])
        return zip_local[t]

    def src_bytes(spec):
        kind = spec[0]
        if kind == "dir":
            stem = os.path.basename(spec[1])
            path = coil_files.get(stem.upper())
            if not path:
                return None
            with open(path, "rb") as f:
                return f.read(), str(os.path.getsize(path)), os.path.basename(path)
        if kind == "zip_row":
            row = spec[2]
            tgt = abs_map.get(row)
            if not tgt:
                return None
            name = "xl/" + tgt.replace("../", "")
            return get_zip().read(name), "row%d" % row, os.path.basename(name)
        return None

    jobs = []
    for idx, it in enumerate(items):
        spec = it.get("img")
        if not spec:
            stats["noimg"] += 1
            continue
        base = norm_code(it["m"])
        catdir = it["cat"]
        jobs.append((idx, spec, base, catdir))

    def work(job):
        idx, spec, base, catdir = job
        try:
            got = src_bytes(spec)
        except Exception as e:
            return idx, "err", "读源图失败：%s" % e
        if not got:
            return idx, "noimg", items[idx]["m"]
        data, sig, fname = got
        sig = "%s|%d|%d|%d" % (sig, FULL_EDGE, FULL_QUALITY, THUMB_EDGE)
        out_dir = os.path.join(IMG_DIR, catdir)
        thumb_dir = os.path.join(out_dir, "t")
        os.makedirs(thumb_dir, exist_ok=True)
        full_p = os.path.join(out_dir, base + ".webp")
        thumb_p = os.path.join(thumb_dir, base + ".webp")
        key = "%s/%s" % (catdir, base)
        ck = cache.get(key)
        if (ck and ck.get("sig") == sig and os.path.exists(full_p) and os.path.exists(thumb_p)):
            return idx, "ok", ck
        try:
            im = open_image(data)
            full = resize(im, FULL_EDGE)
            n1 = save_webp(full, full_p, FULL_QUALITY, FULL_MAX_BYTES)
            thumb = resize(im, THUMB_EDGE)
            n2 = save_webp(thumb, thumb_p, THUMB_QUALITY)
            return idx, "ok", {"sig": sig, "full": n1, "thumb": n2}
        except Exception as e:
            return idx, "err", "压缩失败：%s" % e

    total = len(jobs)
    done = 0
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=8) as ex:
        for idx, status, payload in ex.map(work, jobs):
            it = items[idx]
            done += 1
            if done % 200 == 0 or done == total:
                log("  图片 %d/%d  （%.1fs）" % (done, total, time.time() - t0))
            if status == "ok":
                sig, n1, n2 = payload["sig"], payload["full"], payload["thumb"]
                base = norm_code(it["m"])
                it["p"] = "images/%s/%s.webp" % (it["cat"], base)
                it["t"] = "images/%s/t/%s.webp" % (it["cat"], base)
                stats["full"] += 1
                stats["bytes"] += n1
                stats["thumb_bytes"] += n2
                new_cache["%s/%s" % (it["cat"], base)] = {"sig": sig, "full": n1, "thumb": n2}
            elif status == "noimg":
                it["p"] = it["t"] = ""
                stats["noimg"] += 1
                if it["cat"] in missing_imgs:
                    missing_imgs[it["cat"]].append(it["m"])
            else:
                it["p"] = it["t"] = ""
                stats["err"] += 1
                rowfail(it["cat"], it["m"], payload, "")
    save_cache(new_cache)
    for z in zip_local.values():
        z.close()
    return stats


# ---------------------------------------------------------------- 输出
def write_data_js(items, cats):
    os.makedirs(DATA_DIR, exist_ok=True)
    rows = []
    for i, it in enumerate(items, 1):
        rows.append({
            "i": i, "c": it["cat"], "m": it["m"], "n": it["n"], "b": it.get("b", ""),
            "oe": it.get("oe", ""), "x": it.get("x", []), "a": it.get("a", ""),
            "r": it.get("r", ""), "p": it.get("p", ""), "t": it.get("t", ""),
            "s": it.get("s", ""),
        })
    # 中文清洗 + OE 去重（词典在 data_prep.py）；清洗后重新算 slug，保证和 data.js 一致
    try:
        import data_prep
        holder = {"items": rows}
        data_prep.clean_payload(holder, log=print)
        rows = holder["items"]
        sitegen.make_slugs(rows)
    except Exception as e:
        print("  数据清洗失败（用原始数据）：%s" % e)
    payload = {
        "generated": time.strftime("%Y-%m-%d %H:%M"),
        "company": "Guangzhou Yumengyang Auto Parts Co., Ltd.",
        "cats": cats,
        "items": rows,
    }
    with open(DATA_JS, "w", encoding="utf-8") as f:
        f.write("/* 型号查询站数据文件 —— 由 build.py 自动生成，别手改。 */\n")
        f.write("/* 字段：i=编号 c=品类 m=型号 n=品名 b=品牌 oe=主OE号 x=交叉号数组 a=适配车型 r=备注 p=大图 t=缩略图 */\n")
        f.write("window.SITE_DATA=")
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";\n")
    return os.path.getsize(DATA_JS)


def write_fails(items):
    lines = []
    lines.append("解析失败 / 需要留意清单")
    lines.append("生成时间：%s" % time.strftime("%Y-%m-%d %H:%M:%S"))
    lines.append("=" * 60)
    if fails:
        lines.append("一、解析失败的行（这些行没进站点）")
        for cat, pos, why, raw in fails:
            lines.append("  [%s] %s  ->  %s   （原始内容：%s）" % (cat, pos, why, raw))
    else:
        lines.append("一、解析失败的行：没有，全部解析成功。")
    lines.append("")
    lines.append("二、图片相关提示")
    if missing_imgs["coil"]:
        lines.append("  - 点火线圈有 %d 个型号在“点火线圈-图片”文件夹里找不到图：%s"
                     % (len(missing_imgs["coil"]), "、".join(missing_imgs["coil"][:40])))
    if missing_imgs["abs"]:
        rows = missing_imgs["abs"]
        lines.append("  - ABS 传感器有 %d 个型号在源表里没有配图：%s"
                     % (len(rows), "、".join(rows[:40]) + ("…" if len(rows) > 40 else "")))
    if warns:
        for w in uniq(warns):
            lines.append("  - %s" % w)
    if not missing_imgs["coil"] and not missing_imgs["abs"] and not warns:
        lines.append("  - 无")
    lines.append("")
    lines.append("三、各品类条数")
    cnt = {}
    for it in items:
        cnt[it["cat"]] = cnt.get(it["cat"], 0) + 1
    for c in CATS:
        lines.append("  %-10s %s：%d 条" % (c["name"], c["en"], cnt.get(c["key"], 0)))
    lines.append("")
    lines.append("四、本次构建时间：%s" % time.strftime("%Y-%m-%d %H:%M:%S"))
    with open(FAIL_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main():
    t0 = time.time()
    log("=" * 56)
    log(" 型号查询站 · 数据更新")
    log("=" * 56)
    missing = []
    for k in ("coil", "abs", "wire", "thermo", "plug"):
        if not os.path.exists(SRC[k]):
            missing.append(SRC[k])
    if len(missing) == 5:
        log("!! 5 个 Excel 全都找不到，请确认挪动过文件。")
        for m in missing:
            log("   缺：%s" % m)
        return 1
    for m in missing:
        log("?? 找不到（已跳过）：%s" % m)

    log("\n[1/3] 读取 Excel …")
    readers = [("点火线圈", read_coil), ("ABS 传感器", read_abs), ("火花塞线", read_wire),
               ("节温器", read_thermo), ("火花塞", read_plug)]
    items = []
    for label, fn in readers:
        try:
            got = fn()
        except Exception as e:
            warns.append("%s 读取失败：%s" % (label, e))
            log("  %s 读取失败：%s" % (label, e))
            continue
        log("  %-10s %d 条" % (label, len(got)))
        items.extend(got)

    if not items:
        log("!! 一条数据都没读到，停止。请检查 Excel 是否还在原位置。")
        return 1

    for idx, it in enumerate(items, 1):
        it["i"] = idx

    # ---- 合并 D:\111A剪辑 里的 10 个目录表（价格只写进 内部价格-不发布）----
    extra_cats = []
    try:
        import import_catalogs as ic
        if os.path.isdir(ic.SRC_DIR):
            log("\n[1b/4] 合并 111A剪辑 目录表 …")
            extra, price_rows, cfails, used = ic.load_all(log=log)
            added, merged, used_cats = ic.merge(items, extra, log=log)
            csv_path, nprice = ic.write_prices(price_rows)
            log("  新增 %d 条，合并进已有 %d 条；价格 %d 行已单独存放（不进网页）" % (added, merged, nprice))
            old_keys = {c["key"] for c in CATS}
            for key in sorted(used_cats):
                if key in old_keys:
                    continue
                slug, en, one, cn = ic.NEW_CATS.get(key, (key, key, key, key))
                extra_cats.append({"key": key, "name": cn, "en": en, "one": one, "slug": slug})
            if cfails:
                warns.extend(cfails)
        else:
            warns.append("没找到 D:\\111A剪辑 目录表目录，本次只更新原有 5 类")
    except Exception as e:
        warns.append("合并 111A剪辑 目录表失败：%s" % e)
        log("  !! 合并失败：%s" % e)

    for idx, it in enumerate(items, 1):
        it["i"] = idx

    log("\n[2/4] 抽图 + 压缩 …")
    stats = build_images(items)

    log("\n[3/4] 生成 data.js 与清单 …")
    cats = []
    for c in CATS:
        n = sum(1 for it in items if it["cat"] == c["key"])
        if n:
            cats.append({"key": c["key"], "name": c["name"], "en": c["en"], "n": n})
    for c in extra_cats:
        n = sum(1 for it in items if it["cat"] == c["key"])
        if n:
            cats.append({"key": c["key"], "name": c["name"], "en": c["en"], "n": n})
    try:
        import sitegen
        sitegen.make_slugs(items)
        sitegen.register_cats(extra_cats)
    except Exception as e:
        warns.append("生成 slug 失败：%s" % e)
    size = write_data_js(items, cats)
    write_fails(items)

    log("\n[4/4] 生成型号页 / 品类页 / sitemap …")
    res = sitegen.build_static(items, cats, log=log)
    if res.get("clash"):
        warns.append("%d 个型号的 slug 重名，已自动加 -2/-3 后缀：%s"
                     % (len(res["clash"]), "、".join("%s→%s" % (b, s) for b, s, _m in res["clash"][:10])))
        write_fails(items)

    total_img = stats["bytes"] + stats["thumb_bytes"]
    log("")
    log("-" * 56)
    log(" 型号合计：%d 个" % len(items))
    log(" 图片：%d 张（大图+缩略图存了 %d 个文件）" % (stats["full"], stats["full"] * 2))
    log(" 图片体积：%.1f MB" % (total_img / 1048576.0))
    log(" data.js：%.2f MB" % (size / 1048576.0))
    if stats["noimg"]:
        log(" 没有配图：%d 条（正常，源文件里就没图）" % stats["noimg"])
    if stats["err"]:
        log(" 图片出错：%d 条，详见 解析失败清单.txt" % stats["err"])
    log(" 用时：%.1f 秒" % (time.time() - t0))
    log("-" * 56)
    if total_img > TARGET_TOTAL_MB * 1048576:
        log("?? 图片总体积超过 %d MB 的预算，可以再压。" % TARGET_TOTAL_MB)
    log(" 好了，双击 index.html 就能用。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
