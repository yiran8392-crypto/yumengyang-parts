# -*- coding: utf-8 -*-
"""
把这批目录表里「还没上站」的型号一次性补齐（增量，不动已有数据）
==================================================================
来源（只读，绝不写回）：
  D:\\111A剪辑\\111资料\\*.xlsx / *.xls（12 个文件）

做了四件事：
  1. 按表逐页解析（每张表硬编码列位，不再靠表头猜），只补站上没有的编码；
     已存在的编码只在缺字段时补 oe / 交叉号 / 车型 / 品牌。
  2. 产品图：从 xlsx 内嵌 drawing 锚点抽「行 → 图」，压成 webp（大图 800px + 缩略图 260px），
     已有图的一律不覆盖。
  3. 价格（进价 / 一级 / 二级 / 限价 / 批价）只写 内部价格-不发布\\价格表.csv，公开数据里没有价格。
  4. 品名清洗：中文品名统一翻成英文（英文站不能出现中文），翻不掉的退回品类默认英文名并记清单。

用法：
    python import_more.py --dry     只看统计，不落盘
    python import_more.py           真跑
"""

import csv
import io
import json
import os
import re
import sys
import time
import zipfile
from xml.etree import ElementTree as ET

sys.path.insert(0, r"D:\欧鲸鲸\default-workspace\.pylibs")
import openpyxl
import xlrd
from PIL import Image, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = r"D:\111A剪辑\111资料"
DATA_JS = os.path.join(HERE, "data", "data.js")
IMG_ROOT = os.path.join(HERE, "images")
PRICE_DIR = os.path.join(HERE, "内部价格-不发布")
PRICE_CSV = os.path.join(PRICE_DIR, "价格表.csv")
REPORT = os.path.join(HERE, "解析失败清单-补录.txt")
NEW_CSV = os.path.join(HERE, "新增型号清单-%s.csv" % time.strftime("%Y%m%d"))

FULL_EDGE, FULL_BYTES, THUMB_EDGE, THUMB_Q = 800, 80 * 1024, 260, 78

S = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
X = "{http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"

# ---------------------------------------------------------------- 品类 → 英文品名
CAT_NAME = {
    "coil": "Ignition Coil", "abs": "ABS Sensor", "wire": "Spark Plug Wire Set",
    "thermo": "Thermostat", "plug": "Spark Plug", "ckp": "Crankshaft Position Sensor",
    "cmp": "Camshaft Position Sensor", "dpfe": "Differential Pressure Sensor",
    "map": "Intake Pressure Sensor (MAP)", "tps": "Throttle Position Sensor",
    "tpms": "TPMS Sensor", "temp": "Temperature Sensor", "o2": "Oxygen Sensor",
    "fuelpump": "Fuel Pump Assembly", "vsv": "Vacuum Solenoid Valve",
    "purge": "Canister Purge Valve", "ocv": "Oil Control Valve",
    "throttle": "Throttle Body", "injector": "Fuel Injector",
    "stepper": "Idle Stepper Motor", "maf": "Mass Air Flow Sensor",
    "fuelpress": "Fuel Pressure Regulator", "njkspark": "NJK Spark Plug",
}

# 中文品名 → 英文（长词优先，先整名匹配）
NAME_EN = {
    "凸轮轴位置传感器（曲轴箱传感器）": "Camshaft Position Sensor (Crankcase)",
    "凸轮轴位置传感器": "Camshaft Position Sensor", "凸轮轴位传感器": "Camshaft Position Sensor",
    "凸轮轴传感器": "Camshaft Sensor", "曲轴位置传感器": "Crankshaft Position Sensor",
    "曲轴位置传感": "Crankshaft Position Sensor", "节气门位置传感器": "Throttle Position Sensor",
    "节气门阀体总成": "Throttle Body Assembly", "节气门阀体": "Throttle Body",
    "进气压力传感器": "Intake Pressure Sensor (MAP)", "空气流量计": "Mass Air Flow Sensor",
    "空气温度传感器": "Air Temperature Sensor", "室外温度传感器": "Ambient Temperature Sensor",
    "水温传感器": "Coolant Temperature Sensor", "温度传感器": "Temperature Sensor",
    "压差传感器": "Differential Pressure Sensor", "油压传感器": "Oil Pressure Sensor",
    "油压调节器": "Fuel Pressure Regulator", "汽油泵总成": "Fuel Pump Assembly",
    "燃油泵总成": "Fuel Pump Assembly", "燃油泵模块": "Fuel Pump Module",
    "机油控制阀": "Oil Control Valve", "碳罐电磁阀": "Canister Purge Valve",
    "碳罐截止阀": "Canister Purge Valve", "真空电磁阀": "Vacuum Solenoid Valve",
    "步进电机": "Idle Stepper Motor", "怠速马达": "Idle Stepper Motor",
    "火花塞线": "Spark Plug Wire Set", "分火线": "Spark Plug Wire Set",
    "点火线圈": "Ignition Coil", "火花塞套筒": "Spark Plug Socket",
    "火花塞": "Spark Plug", "氧传感器": "Oxygen Sensor", "胎压传感器": "TPMS Sensor",
    "节温器": "Thermostat", "电子调温器": "Electronic Thermostat",
    "ABS传感器": "ABS Sensor", "车速传感器": "Speed Sensor",
    "喷油嘴": "Fuel Injector", "油压报警器": "Oil Pressure Switch",
    "机油压力报警器": "Oil Pressure Switch", "机油压力传感器": "Oil Pressure Sensor",
    "水位传感器": "Coolant Level Sensor", "节温器座": "Thermostat Housing",
    "节温器总成": "Thermostat Assembly", "普通节温器": "Thermostat",
    "腔体调温器": "Thermostat", "普通调温器": "Thermostat",
    "热管理模块/ETM": "Thermal Management Module (ETM)",
    "水泵+ETM总成": "Water Pump + ETM Assembly",
    "进气温度传感器": "Intake Air Temperature Sensor",
    "碳罐电磁阀 带管": "Canister Purge Valve with pipe",
    "碳罐电磁阀带管": "Canister Purge Valve with pipe",
    "凸轮轴位置传感器(变速箱传感器)": "Camshaft Position Sensor (transmission)",
    "机油泵电磁阀": "Oil Pump Solenoid Valve",
    "电子节气门": "Electronic Throttle Body", "机械节气门": "Mechanical Throttle Body",
    "可编程胎压传感器": "Programmable TPMS Sensor", "胎压编程维修设备": "TPMS Programming Tool",
}
NAME_KEYS = sorted(NAME_EN, key=len, reverse=True)

MATERIAL = {"铱铂金": "Iridium Platinum", "依铂金": "Iridium Platinum", "双铱金": "Double Iridium",
            "铱金": "Iridium", "铂金": "Platinum", "镍包铜": "Nickel Copper", "铜芯": "Copper Core"}

BRAND_EN = {"威利": "WEILI", "加加": "JIAJIA", "天博": "TIANBO", "德尔福": "Delphi", "博世": "Bosch",
            "电装": "Denso", "联电": "UAES", "马瑞利": "Magneti Marelli", "玛瑞利": "Magneti Marelli"}

CJK = re.compile(r"[\u4e00-\u9fa5]")


# ---------------------------------------------------------------- 基础工具
def s(v):
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    t = str(v).replace("\u00a0", " ").replace("\u3000", " ")
    t = t.replace("\r", "\n")
    return re.sub(r"[ \t]+", " ", t).strip()


def one_line(v):
    return re.sub(r"\s+", " ", s(v)).strip()


def norm(c):
    return re.sub(r"[^A-Z0-9]", "", s(c).upper())


def img_base(code):
    return re.sub(r"[^A-Za-z0-9_.-]", "_", s(code))


def name_en(raw, cat):
    """品类品名 → 英文。整名命中优先，其次长词替换，最后退回品类默认名。"""
    t = one_line(raw)
    if not t:
        return CAT_NAME.get(cat, cat), False
    if not CJK.search(t):
        return t, False
    if t in NAME_EN:
        return NAME_EN[t], False
    out = t
    for k in NAME_KEYS:
        if k in out:
            out = out.replace(k, " ")
    out = re.sub(r"[\u4e00-\u9fa5]+", " ", out)
    out = re.sub(r"[\s,;/\-（）()]+", " ", out).strip()
    if not out:
        return CAT_NAME.get(cat, cat), True
    return out, False


SPLIT_RE = re.compile(r"[;\n|]+")


def split_codes(text):
    """一格多号 → 列表。支持 ; 换行 | / 和「两个以上空格」，也支持整格是空格的多个号。"""
    t = s(text)
    if not t:
        return []
    out = []
    for p in SPLIT_RE.split(t):
        p = p.strip(" ,，、/=")
        if not p:
            continue
        if "/" in p:
            sub = [x.strip() for x in p.split("/") if x.strip()]
            if len(sub) >= 2 and all(len(x) >= 4 and re.search(r"\d", x) for x in sub):
                out.extend(sub)
                continue
        toks = [x for x in re.split(r"\s{2,}", p) if x]
        if len(toks) == 1 and " " in p:
            w = p.split()
            if len(w) >= 2 and all(len(x) >= 4 and re.search(r"\d", x) for x in w):
                out.extend(w)      # "K5T46685 36162-RFE-005"
                continue
        out.extend(toks)
    res = []
    for x in out:
        x = x.strip(" ,，、/=")
        if len(x) >= 3 and re.search(r"\d", x):
            res.append(x)
    seen, uniq = set(), []
    for x in res:
        k = norm(x)
        if k and k not in seen:
            seen.add(k)
            uniq.append(x)
    return uniq


def code_ok(code):
    c = s(code).replace(" ", "")
    if len(c) < 4 or len(c) > 28:
        return False
    if not re.search(r"\d", c):
        return False
    if re.search(r"[\u4e00-\u9fa5]", c):
        return False
    if not re.match(r"^[A-Za-z0-9][A-Za-z0-9\-./]*$", c):
        return False
    return True


# ---------------------------------------------------------------- 表配置
# cols: code / name / brand / oe / app / model / prices（0 基列号）
# hdr: 表头行（1 基），从下一行开始读数据
# brand_fixed: 表里没有品牌列时用这个
# system / stepper / sensor / material / packing: 额外列，写进备注或交叉号
# code_strip: 编码里要去掉的空格
def sp(**kw):
    kw.setdefault("prices", [])
    return kw


def specs():
    new = os.path.join(SRC, "线圈 碳罐 机油阀 阀体 马达 分火线 产品目录（带价格）(2).xlsx")
    absf = os.path.join(SRC, "ABS  凸轮  曲轴  节气门  进气压力传感器目录表(2).xlsx")
    out = []
    # ---- 大目录（2026-11-03 版，含供应商/进价）
    out += [
        sp(file=new, sheet="点火线圈", hdr=2, cat="coil", code=1, name=0, brand=3, oe=4, app=5,
           prices=[6, 7, 8], qty=10, stars=11),
        sp(file=new, sheet="步进电机", hdr=1, cat="stepper", code=1, name=0, oe=2, brand=4, app=5,
           prices=[6, 7], brand_fixed="WEILI", group=0),
        sp(file=new, sheet="室外温度传感器", hdr=1, cat="temp", code=1, name=0, brand=3, oe=4,
           app=5, prices=[6, 7, 8]),
        sp(file=new, sheet="水温传感器", hdr=1, cat="temp", code=1, name=0, brand=3, app=4,
           prices=[5, 6]),
        sp(file=new, sheet="天博水温传感器", hdr=1, cat="temp", code=1, name=0, oe=None, app=4,
           prices=[5, 6], brand_fixed="TIANBO"),
        sp(file=new, sheet="喷油嘴", hdr=1, cat="injector", code=1, name=0, brand=3, app=4,
           prices=[5, 6, 7]),
        sp(file=new, sheet="电子", hdr=1, cat="throttle", code=1, name=None, oe=3, app=4,
           prices=[5, 6, 7], brand_fixed="WEILI"),
        sp(file=new, sheet="机械", hdr=1, cat="throttle", code=1, name=2, oe=4, app=5,
           prices=[9, 10, 11], brand_fixed="WEILI", system=6, stepper=7, sensor=8),
        sp(file=new, sheet="高压线", hdr=1, cat="wire", code=0, name=None, brand=2, app=3,
           prices=[4, 5]),
        sp(file=new, sheet="碳罐电磁阀", hdr=1, cat="purge", code=1, name=0, brand=3, oe=4,
           app=5, prices=[6, 7, 8]),
        sp(file=new, sheet="油压传感器", hdr=1, cat="fuelpress", code=1, name=0, brand=3, app=4,
           prices=[5, 6]),
        sp(file=new, sheet="空气流量计", hdr=1, cat="maf", code=1, name=0, brand=3, app=4,
           prices=[5, 6]),
        sp(file=new, sheet="机油控制阀", hdr=1, cat="ocv", code=1, name=0, oe=3, app=4,
           prices=[5, 6, 7], brand_fixed="WEILI"),
        sp(file=new, sheet="火花塞", hdr=3, cat="plug", code=1, name=None, model=2, app=5,
           prices=[6, 9], brand_fixed="WEILI", material=4, packing=8),
    ]
    # ---- ABS 五大类（336MB）
    out += [
        sp(file=absf, sheet="进气压力传感器", hdr=1, cat="map", code=0, name=1, oe=3, app=4,
           prices=[5, 6], brand_fixed="WEILI"),
        sp(file=absf, sheet="节气门位置传感器", hdr=1, cat="tps", code=1, name=0, brand=3, app=4,
           prices=[5]),
        sp(file=absf, sheet="曲轴位置传感器", hdr=1, cat="ckp", code=0, name=1, brand=3, oe=4,
           app=5, prices=[6, 7]),
        sp(file=absf, sheet="ABS传感器", hdr=1, cat="abs", code=1, name=0, brand=3, oe=4, app=5,
           prices=[6, 7]),
        sp(file=absf, sheet="凸轮轴位置传感器", hdr=1, cat="cmp", code=0, name=1, brand=3, oe=4,
           app=5, prices=[6, 7]),
        sp(file=absf, sheet="压差传感器", hdr=1, cat="dpfe", code=0, name=1, brand=3, oe=4,
           app=5, prices=[6, 7]),
    ]
    # ---- 其余单表
    out += [
        sp(file=os.path.join(SRC, "胎压传感器目录.xlsx"), sheet="Sheet1", hdr=1, cat="tpms",
           code=0, name=1, brand=3, app=4, prices=[5, 6]),
        sp(file=os.path.join(SRC, "油泵价格（含进价）.xls"), sheet="Sheet1", hdr=1, cat="fuelpump",
           code=0, name=1, oe=2, app=3, prices=[4, 5, 6], brand_fixed="WEILI"),
        sp(file=os.path.join(SRC, "油泵价格1.xls"), sheet="Sheet1", hdr=1, cat="fuelpump",
           code=0, name=1, oe=2, app=3, prices=[4, 5], brand_fixed="WEILI"),
        sp(file=os.path.join(SRC, "油泵目录表.xls"), sheet="Sheet1", hdr=1, cat="fuelpump",
           code=0, name=1, oe=2, app=3, prices=[4], brand_fixed="WEILI"),
        sp(file=os.path.join(SRC, "威利火花塞.xlsx"), sheet="商品属性导出表20251223_黎达文_",
           hdr=1, cat="plug", code=1, name=2, app=3, prices=[6, 7], brand_fixed="WEILI",
           material=5, packing=8),
        sp(file=os.path.join(SRC, "NJK火花塞.xlsx"), sheet="商品属性导出表20251223_黎达文_ (1)",
           hdr=1, cat="njkspark", code=1, name=2, app=3, prices=[], brand_fixed="NJK"),
        sp(file=os.path.join(SRC, "真空电磁阀目录1.xlsx"), sheet="Sheet1", hdr=1, cat="vsv",
           code=1, name=0, brand=3, oe=4, app=5, prices=[6, 7]),
        sp(file=os.path.join(SRC, "天博温度传感器与节温器5.31目录表.xlsx"), sheet="Sheet1",
           hdr=1, cat="temp", code=1, name=3, app=4, prices=[5], brand_fixed="TIANBO",
           cat_by_name=True),
        sp(file=os.path.join(SRC, "天博温度传感器与节温器5.31目录表.xlsx"), sheet="Sheet2",
           hdr=3, cat="thermo", code=1, name=None, oe=4, app=3, prices=[5], brand_fixed="TIANBO",
           tbno=2),
        sp(file=os.path.join(SRC, "氧传感器单价.xls"), sheet="红盒包装", hdr=1, cat="o2",
           code=0, name=1, oe=3, app=4, prices=[5, 6], brand_fixed="WEILI"),
        sp(file=os.path.join(SRC, "氧传感器单价.xls"), sheet="白色包装", hdr=1, cat="o2",
           code=0, name=1, oe=3, app=4, prices=[5, 6], brand_fixed="WEILI"),
        sp(file=os.path.join(SRC, "氧传感器单价.xls"), sheet="红色包装01", hdr=1, cat="o2",
           code=0, name=1, oe=3, app=4, prices=[5], brand_fixed="WEILI"),
    ]
    return [x for x in out if os.path.exists(x["file"])]


# ---------------------------------------------------------------- 读表
def read_xlsx(path, sheet):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        if sheet not in wb.sheetnames:
            return None
        ws = wb[sheet]
        return [list(r) for r in ws.iter_rows(values_only=True)]
    finally:
        wb.close()


def read_xls(path, sheet):
    bk = xlrd.open_workbook(path)
    if sheet not in bk.sheet_names():
        return None
    sh = bk.sheet_by_name(sheet)
    return [[sh.cell_value(r, c) for c in range(sh.ncols)] for r in range(sh.nrows)]


def read_any(path, sheet):
    return read_xls(path, sheet) if path.lower().endswith(".xls") else read_xlsx(path, sheet)


# ---------------------------------------------------------------- 图片锚点
def sheet_list(z):
    wbx = ET.fromstring(z.read("xl/workbook.xml"))
    rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    rmap = {x.get("Id"): x.get("Target") for x in rels}
    return {sh.get("name"): rmap.get(sh.get(REL + "id"))
            for sh in wbx.find(S + "sheets").findall(S + "sheet")}


def sheet_anchors(z, target):
    """{excel_row(1基): 'xl/media/imageN.png'}，同一行只留第一张。"""
    if not target:
        return {}
    rp = "xl/worksheets/_rels/%s.rels" % target.split("/")[-1]
    if rp not in z.namelist():
        return {}
    dpath = None
    for x in ET.fromstring(z.read(rp)):
        tg = x.get("Target") or ""
        if (x.get("Type") or "").endswith("/drawing") and tg.endswith(".xml"):
            dpath = "xl/" + tg.replace("../", "")
    if not dpath or dpath not in z.namelist():
        return {}
    imap = {}
    relp = dpath.replace("drawings/", "drawings/_rels/") + ".rels"
    if relp in z.namelist():
        for x in ET.fromstring(z.read(relp)):
            imap[x.get("Id")] = x.get("Target")
    out = {}
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
            continue
        out[row] = "xl/" + tgt.replace("../", "")
    return out


# ---------------------------------------------------------------- 清洗图片
def trim_white(im):
    g = im.convert("L").point(lambda p: 255 if p < 244 else 0)
    box = g.getbbox()
    if box:
        pad = 2
        im = im.crop((max(0, box[0] - pad), max(0, box[1] - pad),
                      min(im.width, box[2] + pad), min(im.height, box[3] + pad)))
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


def prep_img(raw):
    im = Image.open(io.BytesIO(raw))
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        bg = Image.new("RGB", im.size, (255, 255, 255))
        bg.paste(im, mask=im.split()[-1])
        im = bg
    im = ImageOps.exif_transpose(im.convert("RGB"))
    return fit(to_square(trim_white(im)), FULL_EDGE)


# ---------------------------------------------------------------- 解析
def cell(row, idx):
    if idx is None or idx < 0 or idx >= len(row):
        return ""
    return s(row[idx])


def parse_spec(spec, rows, known=None):
    """→ (items, prices, fails)"""
    items, prices, fails = [], [], []
    hdr = spec["hdr"]
    cat = spec["cat"]
    for rn in range(hdr, len(rows)):
        row = rows[rn]
        if not any(s(c) for c in row):
            continue
        code = cell(row, spec["code"]).replace(" ", "")
        pack_x = []
        # 「10-DZ002C(10-0008)」= 本站型号 + 括号里的旧号
        m_br = re.match(r"^([A-Za-z0-9][A-Za-z0-9\-./]*?)[(（]([A-Za-z0-9\-]+)[)）]$", code)
        if m_br and code_ok(m_br.group(1)):
            code = m_br.group(1)
            pack_x = [m_br.group(2)]
        if not code_ok(code):
            if code and not CJK.search(code):
                fails.append((spec["sheet"], rn + 1, "编码不像编码：%s" % code[:40]))
            continue
        # 「WL29-3811/90083」这种一码双写的：第一个当本站型号，其余进交叉号
        # （如果整串本来就是站上的型号，比如 NJK3811/ 90083，就不拆）
        if "/" in code and (known is None or norm(code) not in known):
            parts_ = [x for x in code.split("/") if x]
            if len(parts_) >= 2 and all(code_ok(x) for x in parts_):
                code, pack_x = parts_[0], parts_[1:] + pack_x
        name_raw = cell(row, spec.get("name"))
        if not name_raw and spec.get("group") is not None:
            name_raw = cell(row, spec["group"])
        app = cell(row, spec.get("app"))
        oe_raw = cell(row, spec.get("oe"))
        brand = spec.get("brand_fixed") or cell(row, spec.get("brand")) or "WEILI"
        brand = BRAND_EN.get(brand.strip(), brand.strip())
        oe_list = split_codes(oe_raw)
        xs = list(pack_x) + oe_list[1:]

        remark = []
        model_raw = cell(row, spec.get("model"))
        if model_raw:
            if CJK.search(model_raw):
                if not name_raw:
                    name_raw = model_raw
            elif code_ok(model_raw) and len(model_raw) <= 20:
                xs.append(model_raw)
                remark.append("Type: %s" % model_raw)
        if "不备货" in app:
            remark.append("Not kept in stock")

        if spec.get("sensor"):
            extra = cell(row, spec["sensor"])
            for x in split_codes(extra):
                if norm(x) not in [norm(v) for v in xs]:
                    xs.append(x)
        if spec.get("stepper"):
            v = one_line(cell(row, spec["stepper"]))
            if v:
                remark.append("Stepper: %s" % v)
        if spec.get("system"):
            v = one_line(cell(row, spec["system"]))
            if v and not CJK.search(v):
                remark.append("System: %s" % v)
        if spec.get("qty"):
            v = one_line(cell(row, spec["qty"]))
            if v and re.search(r"\d", v):
                remark.append("Qty/vehicle: %s" % v)
        if spec.get("stars"):
            v = one_line(cell(row, spec["stars"]))
            if v:
                remark.append("Sales index: %s" % v)
        if spec.get("material"):
            v = one_line(cell(row, spec["material"]))
            en = MATERIAL.get(v)
            if en:
                remark.append("Material: %s" % en)
        if spec.get("packing"):
            v = one_line(cell(row, spec["packing"]))
            if v:
                remark.append("Packing: %s" % v)
        if spec.get("tbno"):
            v = cell(row, spec["tbno"])
            if v:
                xs.insert(0, v)

        nm, fallback = name_en(name_raw, cat)
        cat_use = cat
        if spec.get("cat_by_name") and ("节温器" in name_raw or "调温器" in name_raw):
            cat_use = "thermo"
        items.append({
            "cat": cat_use, "m": code, "n": nm, "n_fallback": fallback, "n_raw": name_raw,
            "b": one_line(brand), "oe": oe_list[0] if oe_list else "", "x": xs,
            "a": one_line(app), "r": " | ".join(remark), "row": rn + 1,
        })
        pr = {}
        for c in spec.get("prices", []):
            v = cell(row, c)
            if re.fullmatch(r"-?\d+(\.\d+)?", v):
                pr["col%d" % (c + 1)] = v
        if pr:
            prices.append({"code": code, "name": one_line(name_raw), "prices": pr,
                           "sheet": spec["sheet"], "row": rn + 1,
                           "file": os.path.basename(spec["file"])})
    return items, prices, fails


# ---------------------------------------------------------------- 主流程
def main():
    dry = "--dry" in sys.argv
    t0 = time.time()
    raw = io.open(DATA_JS, encoding="utf-8").read()
    k = "window.SITE_DATA="
    payload, _ = json.JSONDecoder().raw_decode(raw[raw.find(k) + len(k):])
    items = payload["items"]
    print("站上现有 %d 条" % len(items))

    by_code, by_oe = {}, {}
    for it in items:
        by_code.setdefault(norm(it.get("m")), it)
        for o in [it.get("oe")] + list(it.get("x") or []):
            if len(norm(o)) >= 5:
                by_oe.setdefault(norm(o), it)

    all_items, all_prices, all_fails, per_sheet = [], [], [], []
    known = set(by_code)
    zips = {}
    for spec in specs():
        path = spec["file"]
        rows = read_any(path, spec["sheet"])
        if rows is None:
            all_fails.append((os.path.basename(path), spec["sheet"], "表不存在", 0))
            continue
        got, pr, fl = parse_spec(spec, rows, known)
        all_prices.extend(pr)
        all_fails.extend((os.path.basename(path), x[0], x[2], x[1]) for x in fl)
        per_sheet.append((os.path.basename(path)[:18], spec["sheet"], len(rows), len(got)))
        for g in got:
            g["file"] = os.path.basename(path)
            g["sheet"] = spec["sheet"]
        all_items.extend(got)

    # ---- 判重 + 合并
    added, merged, dup_exact = [], 0, 0
    seen_new = {}
    for g in all_items:
        key = norm(g["m"])
        if key in seen_new:
            dup_exact += 1
            old = seen_new[key]
            for o in [g["oe"]] + g["x"]:
                if o and norm(o) not in [norm(v) for v in [old["oe"]] + old["x"]]:
                    old["x"].append(o)
            if not old["a"] and g["a"]:
                old["a"] = g["a"]
            continue
        seen_new[key] = g
        it = by_code.get(key)
        pack_of = ""
        if it is None:
            m2 = re.match(r"^(WL\d{2}-\d+)[BTHYA]$", g["m"], re.I)
            if m2:
                par = by_code.get(norm(m2.group(1)))
                if par is not None and (par.get("c") or par.get("cat")) == g["cat"]:
                    it, pack_of = par, g["m"]
        if it is None:
            cand = None
            for o in [g["oe"]] + g["x"]:
                ok = by_oe.get(norm(o))
                if ok and (ok.get("c") or ok.get("cat")) == g["cat"]:
                    cand = ok
                    break
            it = cand
        if it is not None:
            changed = False
            if pack_of:
                it.setdefault("x", [])
                if pack_of not in it["x"]:
                    it["x"].append(pack_of)
                    changed = True
                note = "Also packed as %s" % pack_of
                old_r = it.get("r") or ""
                if note not in old_r:
                    it["r"] = (old_r + " | " + note).strip(" |")
                    changed = True
            for o in [g["oe"]] + g["x"]:
                if o and norm(o) != norm(it.get("oe")) and o not in it.get("x", []):
                    it.setdefault("x", []).append(o)
                    changed = True
            for fld, src in (("a", "a"), ("b", "b")):
                if not (it.get(fld) or "").strip() and g.get(src):
                    it[fld] = g[src]
                    changed = True
            if changed:
                merged += 1
            continue
        added.append(g)

    print("\n逐表解析（表名 / 行数 / 有效编码）：")
    for f, sh, n, got in per_sheet:
        print("  %-20s %-14s 行=%-5d 编码=%-4d" % (f, sh[:14], n, got))
    print("\n新增 %d 条；合并进已有（补交叉号/车型/品牌）%d 条；表内重复 %d 条"
          % (len(added), merged, dup_exact))

    cnt = {}
    for g in added:
        cnt[g["cat"]] = cnt.get(g["cat"], 0) + 1
    print("新增品类分布：", json.dumps(cnt, ensure_ascii=False, sort_keys=True))
    fb = [g for g in added if g["n_fallback"]]
    print("品名翻不出来、退回品类默认名：%d 条" % len(fb))

    # ---- 图片
    todo_img = {}
    for g in added:
        todo_img.setdefault(norm(g["m"]), g)
    img_plan = {}
    for spec in specs():
        path = spec["file"]
        if not path.lower().endswith(".xlsx"):
            continue
        try:
            if path not in zips:
                zips[path] = zipfile.ZipFile(path)
            z = zips[path]
            tgt = sheet_list(z).get(spec["sheet"])
            if not tgt:
                continue
            anc = sheet_anchors(z, tgt)
        except Exception as e:
            print("  !! 锚点读取失败 %s/%s：%r" % (os.path.basename(path), spec["sheet"], e))
            continue
        rows = read_any(path, spec["sheet"]) or []
        for rn, media in anc.items():
            if not (1 <= rn <= len(rows)):
                continue
            code = cell(rows[rn - 1], spec["code"]).replace(" ", "")
            g = todo_img.get(norm(code))
            if g is not None and norm(code) not in img_plan:
                img_plan[norm(code)] = (path, media, g)
    print("能配图的新型号：%d 个" % len(img_plan))

    # ---- 品名清洗（全站中文品名）
    renamed = 0
    leftover = {}
    for it in items:
        nm = it.get("n") or ""
        if CJK.search(nm):
            new_n, fallback = name_en(nm, it["c"])
            if fallback:
                leftover[nm] = leftover.get(nm, 0) + 1
            if new_n != nm:
                it["n"] = new_n
                renamed += 1
    print("顺手把站上 %d 条中文品名翻成英文" % renamed)

    if dry:
        with io.open(os.path.join(HERE, "_dry_new.txt"), "w", encoding="utf-8") as f:
            f.write("品类 / 型号 / 品名 / 品牌 / 主OE / 交叉号 / 适配车型 / 备注\n")
            for g in sorted(added, key=lambda x: (x["cat"], x["m"])):
                f.write("%-9s | %-14s | %-30s | %-7s | %-24s | x%d | %-46s | %s\n" % (
                    g["cat"], g["m"], g["n"][:30], g["b"][:7], (g["oe"] or "")[:24],
                    len(g["x"]), g["a"][:46], g["r"][:40]))
        print("\n（试运行，未写任何文件，用时 %.1f 秒；样例见 _dry_new.txt）" % (time.time() - t0))
        return 0

    # ---- 写图
    n_img, img_fail = 0, []
    t1 = time.time()
    for i, (key, (path, media, g)) in enumerate(img_plan.items(), 1):
        z = zips.get(path) or zipfile.ZipFile(path)
        zips[path] = z
        cat = g["cat"]
        base = img_base(g["m"])
        d = os.path.join(IMG_ROOT, cat)
        os.makedirs(os.path.join(d, "t"), exist_ok=True)
        full = os.path.join(d, base + ".webp")
        thumb = os.path.join(d, "t", base + ".webp")
        if os.path.exists(full):
            g["p"] = "images/%s/%s.webp" % (cat, base)
            g["t"] = "images/%s/t/%s.webp" % (cat, base)
            continue
        try:
            im = prep_img(z.read(media))
            save_webp(im, full, 82, FULL_BYTES)
            save_webp(fit(im, THUMB_EDGE), thumb, THUMB_Q)
            g["p"] = "images/%s/%s.webp" % (cat, base)
            g["t"] = "images/%s/t/%s.webp" % (cat, base)
            n_img += 1
        except Exception as e:
            img_fail.append((g["m"], str(e)[:60]))
        if i % 50 == 0:
            print("  图片 %d/%d（%.1fs）" % (i, len(img_plan), time.time() - t1))
    print("新写产品图 %d 张，失败 %d" % (n_img, len(img_fail)))

    # ---- 合并进 data.js
    base_i = max(it["i"] for it in items) if items else 0
    for g in added:
        base_i += 1
        items.append({
            "i": base_i, "c": g["cat"], "m": g["m"], "n": g["n"], "b": g["b"],
            "oe": g["oe"], "x": g["x"], "a": g["a"], "r": g["r"],
            "p": g.get("p", ""), "t": g.get("t", ""), "s": "",
        })
    cnt2 = {}
    for it in items:
        cnt2[it["c"]] = cnt2.get(it["c"], 0) + 1
    cats = []
    for c in payload.get("cats") or []:
        cats.append({"key": c["key"], "name": c["name"], "en": c["en"], "n": cnt2.get(c["key"], 0)})
    known = {c["key"] for c in cats}
    sys.path.insert(0, HERE)
    try:
        import import_catalogs as ic
        NEWC = ic.NEW_CATS
    except Exception:
        NEWC = {}
    for key, n in sorted(cnt2.items()):
        if key in known:
            continue
        info = NEWC.get(key)
        if info:
            cats.append({"key": key, "name": info[3], "en": info[1], "n": n})
        else:
            cats.append({"key": key, "name": key, "en": CAT_NAME.get(key, key), "n": n})
    payload["cats"] = cats
    payload["generated"] = time.strftime("%Y-%m-%d %H:%M")
    with io.open(DATA_JS, "w", encoding="utf-8", newline="\n") as f:
        f.write("/* 型号查询站数据文件 —— 由 build.py 自动生成，别手改。 */\n")
        f.write("/* 字段：i=编号 c=品类 m=型号 n=品名 b=品牌 oe=主OE号 x=交叉号数组 a=适配车型 r=备注 p=大图 t=缩略图 s=slug */\n")
        f.write("window.SITE_DATA=")
        f.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
        f.write(";\n")
    print("data.js 已更新：%d 条" % len(items))

    # ---- 价格
    os.makedirs(PRICE_DIR, exist_ok=True)
    rows_csv = []
    if os.path.exists(PRICE_CSV):
        with open(PRICE_CSV, encoding="utf-8-sig", newline="") as f:
            rows_csv = list(csv.DictReader(f))
    fields = set(["来源文件", "工作表", "行号", "商品编码", "名称"])
    for r in rows_csv:
        fields.update(r.keys())
    idx = {(r.get("来源文件", ""), r.get("工作表", ""), r.get("商品编码", "")): i
           for i, r in enumerate(rows_csv)}
    p_add = p_upd = 0
    for r in all_prices:
        row = {"来源文件": r["file"], "工作表": r["sheet"], "行号": str(r["row"]),
               "商品编码": r["code"], "名称": r["name"]}
        for c, v in r["prices"].items():
            row["价格" + c] = v
            fields.add("价格" + c)
        kk = (r["file"], r["sheet"], r["code"])
        if kk in idx:
            rows_csv[idx[kk]].update(row)
            p_upd += 1
        else:
            idx[kk] = len(rows_csv)
            rows_csv.append(row)
            p_add += 1
    pc = sorted([f for f in fields if re.fullmatch(r"价格col\d+", f)],
                key=lambda x: int(x.replace("价格col", "")))
    fieldnames = ["来源文件", "工作表", "行号", "商品编码", "名称"] + pc + \
                 sorted([f for f in fields if f not in ("来源文件", "工作表", "行号", "商品编码", "名称") and f not in pc])
    with open(PRICE_CSV, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, restval="")
        w.writeheader()
        for r in rows_csv:
            w.writerow({k: r.get(k, "") for k in fieldnames})
    print("价格表：新增 %d 行 / 更新 %d 行（共 %d 行，只在本地）" % (p_add, p_upd, len(rows_csv)))

    # ---- 新增清单（给奕然核对）
    with open(NEW_CSV, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["品类", "本站型号", "品名", "品牌", "主OE", "交叉号", "适配车型", "备注",
                    "有图", "来源文件", "来源工作表", "来源行号", "原始品名"])
        for g in sorted(added, key=lambda x: (x["cat"], x["m"])):
            w.writerow([g["cat"], g["m"], g["n"], g["b"], g["oe"], ";".join(g["x"]), g["a"],
                        g["r"], "有" if g.get("p") else "", g["file"], g["sheet"], g["row"],
                        g["n_raw"]])
    print("新增清单：%s" % NEW_CSV)

    # ---- 报告
    lines = ["补录报告（111资料 12 个目录表 → 型号查询站）",
             "时间：%s" % time.strftime("%Y-%m-%d %H:%M:%S"), "=" * 66,
             "一、逐表解析"]
    for f, sh, n, got in per_sheet:
        lines.append("   %-20s %-14s 行=%-5d 编码=%-4d" % (f, sh[:14], n, got))
    lines.append("")
    lines.append("二、结果")
    lines.append("   新增 %d 条 / 合并补字段 %d 条 / 表内重复 %d 条" % (len(added), merged, dup_exact))
    lines.append("   新增分布：" + json.dumps(cnt, ensure_ascii=False, sort_keys=True))
    lines.append("   新写产品图 %d 张；配图失败 %d 个" % (n_img, len(img_fail)))
    lines.append("   站上中文品名翻英文 %d 条；翻不掉退回品类默认名 %d 条" % (renamed, len(fb)))
    lines.append("   最终站上 %d 条" % len(items))
    lines.append("")
    lines.append("三、价格")
    lines.append("   价格表新增 %d 行 / 更新 %d 行；公开数据里没有价格字段" % (p_add, p_upd))
    lines.append("")
    lines.append("四、需要留意")
    if leftover:
        for k2, v2 in sorted(leftover.items(), key=lambda x: -x[1])[:20]:
            lines.append("   品名翻不出来（已用品类默认名）：%s × %d" % (k2, v2))
    for x in all_fails[:40]:
        lines.append("   %s / %s 第%s行：%s" % (x[0], x[1], x[3], x[2]))
    for x in img_fail[:20]:
        lines.append("   图片失败 %s：%s" % x)
    if not (leftover or all_fails or img_fail):
        lines.append("   无")
    with io.open(REPORT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print("报告：%s" % REPORT)
    for z in zips.values():
        z.close()
    print("完成，用时 %.1f 秒" % (time.time() - t0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
