# -*- coding: utf-8 -*-
"""
把 D:\111A剪辑 里的 10 个目录表合并进型号查询站。

硬规矩：
  1. 原始 Excel 只读，绝不写回。
  2. 价格 / 成本 / 限价 / 批价 一律不进公开数据：只写进 内部价格-不发布\价格表.csv。
  3. 同型号（商品编码）与已有条目合并，补交叉号，不重复建页。
  4. 解析不了的整行/整表记进 解析失败清单.txt。
"""
import csv
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = r"D:\111A剪辑"
PRICE_DIR = os.path.join(HERE, "内部价格-不发布")

try:
    import openpyxl
except Exception:
    openpyxl = None

try:
    sys.path.insert(0, r"D:\欧鲸鲸\default-workspace\.pylibs")
    import xlrd
except Exception:
    xlrd = None


# ---------------------------------------------------------------- 新品类
# key: (slug, 英文复数, 英文单数, 中文)
NEW_CATS = {
    "map":     ("intake-pressure-sensors", "Intake Pressure Sensors (MAP)", "Intake Pressure Sensor", "进气压力传感器"),
    "tps":     ("throttle-position-sensors", "Throttle Position Sensors", "Throttle Position Sensor", "节气门位置传感器"),
    "ckp":     ("crankshaft-position-sensors", "Crankshaft Position Sensors", "Crankshaft Position Sensor", "曲轴位置传感器"),
    "cmp":     ("camshaft-position-sensors", "Camshaft Position Sensors", "Camshaft Position Sensor", "凸轮轴位置传感器"),
    "dpfe":    ("differential-pressure-sensors", "Differential Pressure Sensors", "Differential Pressure Sensor", "压差传感器"),
    "tpms":    ("tpms-sensors", "TPMS Sensors", "TPMS Sensor", "胎压传感器"),
    "temp":    ("temperature-sensors", "Temperature Sensors", "Temperature Sensor", "温度传感器"),
    "o2":      ("oxygen-sensors", "Oxygen Sensors", "Oxygen Sensor", "氧传感器"),
    "fuelpump": ("fuel-pumps", "Fuel Pumps", "Fuel Pump", "燃油泵"),
    "vsv":     ("vacuum-solenoid-valves", "Vacuum Solenoid Valves", "Vacuum Solenoid Valve", "真空电磁阀"),
    "purge":   ("canister-purge-valves", "Canister Purge Valves", "Canister Purge Valve", "碳罐电磁阀"),
    "ocv":     ("oil-control-valves", "Oil Control Valves", "Oil Control Valve", "机油控制阀"),
    "throttle": ("throttle-bodies", "Throttle Bodies", "Throttle Body", "节气门阀体"),
    "injector": ("fuel-injectors", "Fuel Injectors", "Fuel Injector", "喷油嘴"),
    "stepper": ("idle-stepper-motors", "Idle Stepper Motors", "Idle Stepper Motor", "怠速马达（步进电机）"),
    "maf":     ("mass-air-flow-sensors", "Mass Air Flow Sensors", "Mass Air Flow Sensor", "空气流量计"),
    "njkspark": ("njk-spark-plugs", "NJK Spark Plugs", "NJK Spark Plug", "NJK 火花塞"),
    "fuelpress": ("fuel-pressure-regulators", "Fuel Pressure Regulators", "Fuel Pressure Regulator", "油压调节器"),
}

CAT_FALLBACK = {
    "throttle": "节气门阀体", "wire": "分火线", "plug": "火花塞", "stepper": "怠速马达",
    "injector": "喷油嘴", "temp": "温度传感器", "fuelpump": "汽油泵总成",
}
PRICE_WORDS = ("价", "价格", "单价", "限价", "批价", "成本", "折扣", "毛价", "底价", "销售价")
CODE_RE = re.compile(r"^(WL\d{2}-[A-Z0-9]+|TB-[\w\-]+|NJK\d+|10-BC\d+C?|\d{2}-BC\d+C?)$", re.I)


def s(v):
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    t = str(v).replace("\u00a0", " ").replace("\u3000", " ")
    t = t.replace("\r", "\n")
    t = re.sub(r"[ \t]+", " ", t)
    return t.strip()


def is_price_header(h):
    h = s(h)
    return any(w in h for w in PRICE_WORDS)


def looks_code(v):
    v = s(v)
    return bool(CODE_RE.match(v)) or bool(re.match(r"^[A-Z]{1,4}\d{2}-\w", v))


def split_codes(text):
    """一格里塞多个 OE 号：逗号、分号、斜杠、换行、两个以上空格。"""
    t = s(text)
    if not t:
        return []
    parts = re.split(r"[;\n\r]+", t)
    out = []
    for p in parts:
        p = p.strip(" ,，、/")
        if not p:
            continue
        if "," in p and all(len(x.strip()) >= 4 for x in p.split(",")):
            out.extend(x.strip() for x in p.split(","))
        else:
            out.append(p)
    # 空格分隔的多号（如 "K5T46685 36162-RFE-005 164"）
    res = []
    for p in out:
        toks = p.split(" ")
        if len(toks) > 1 and all(len(x) >= 4 for x in toks):
            res.extend(toks)
        else:
            res.append(p)
    return [x for x in res if len(x) >= 3]


# ---------------------------------------------------------------- 读表
def read_xlsx_sheet(path, sheet):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        ws = wb[sheet]
        rows = [list(r) for r in ws.iter_rows(values_only=True)]
    finally:
        wb.close()
    return rows


def read_xls_sheet(path, sheet):
    bk = xlrd.open_workbook(path)
    sh = bk.sheet_by_name(sheet)
    rows = []
    for r in range(sh.nrows):
        rows.append([sh.cell_value(r, c) for c in range(sh.ncols)])
    return rows


# ---------------------------------------------------------------- 表头/列角色
ROLE_KEYS = [
    ("code", ("编码", "编号", "商品编码", "产品编码", "威利编号", "货号")),
    ("name", ("名称", "品名", "产品名称", "商品名称")),
    ("oe", ("原厂图号", "图号", "OEM", "OE号", "OE", "原厂号")),
    ("app", ("车型", "适用车型", "产品车型", "适配")),
    ("brand", ("品牌",)),
    ("model", ("型号",)),
]


def header_roles(row):
    roles = {}
    for idx, cell in enumerate(row):
        h = s(cell)
        if not h:
            continue
        if is_price_header(h):
            roles.setdefault("price", []).append(idx)
            continue
        for role, keys in ROLE_KEYS:
            if any(k.lower() in h.lower() for k in keys):
                if role not in roles:
                    roles[role] = idx
                break
    return roles


def find_header(rows):
    for i in range(min(6, len(rows))):
        cells = [s(c) for c in rows[i]]
        nonempty = [c for c in cells if c]
        if len(nonempty) < 2:
            continue
        joined = " ".join(nonempty)
        if any(k in joined for k in ("编码", "名称", "图号", "车型", "OE", "价格", "单价")):
            return i, header_roles(rows[i])
    return -1, {}


BRAND_WORDS = ("威利", "WEILI", "天博", "NJK", "博世", "德尔福", "西门子", "电装", "马瑞利", "玛瑞利")


def _col_sample(rows, start, idx, limit=40):
    vals = []
    for r in rows[start:start + limit]:
        if idx < len(r):
            v = s(r[idx])
            if v:
                vals.append(v)
    return vals


def validate_roles(rows, start, roles):
    """表头经常写错/错位，用内容再校验一遍：
    编码列必须真像编码；品牌列里如果全是图号，那就其实是 OE 列。"""
    if "code" in roles:
        vals = _col_sample(rows, start, roles["code"])
        ratio = sum(1 for v in vals if looks_code(v)) / max(1, len(vals))
        if ratio < 0.3:
            ncols = max((len(r) for r in rows), default=0)
            best, best_r = None, 0
            for c in range(ncols):
                vv = _col_sample(rows, start, c)
                rr = sum(1 for v in vv if looks_code(v)) / max(1, len(vv))
                if rr > best_r:
                    best, best_r = c, rr
            if best is not None and best_r >= 0.5:
                roles["code"] = best
    if "name" in roles and roles.get("name") == roles.get("code"):
        roles.pop("name", None)
    if "brand" in roles:
        vals = _col_sample(rows, start, roles["brand"])
        brandish = sum(1 for v in vals if any(w.lower() in v.lower() for w in BRAND_WORDS) or (len(v) <= 6 and re.search(r"[\u4e00-\u9fa5]", v)))
        coder = sum(1 for v in vals if looks_code(v) or re.fullmatch(r"[A-Z0-9/\-\.]{5,}", v))
        if vals and brandish / len(vals) < 0.4 and coder / len(vals) > 0.5 and "oe" not in roles:
            roles["oe"] = roles.pop("brand")
    return roles


def row_values(row, roles, ncols):
    out = {k: "" for k in ("code", "name", "oe", "app", "brand", "model")}
    prices = {}
    for role, idx in roles.items():
        if role == "price":
            continue
        if idx < len(row):
            out[role] = s(row[idx])
    for idx in roles.get("price", []):
        if idx < len(row):
            v = s(row[idx])
            if v:
                prices["col%d" % (idx + 1)] = v
    return out, prices


def guess_roles_by_content(rows, start, roles):
    """表头不可靠时，按列内容猜：编码列、价格列、OE 列。"""
    ncols = max((len(r) for r in rows), default=0)
    sample = [r for r in rows[start:start + 40] if any(s(c) for c in r)]
    guesses = {}
    for c in range(ncols):
        vals = [s(r[c]) if c < len(r) else "" for r in sample]
        vals = [v for v in vals if v]
        if not vals:
            continue
        code_ratio = sum(1 for v in vals if looks_code(v)) / len(vals)
        num_ratio = sum(1 for v in vals if re.fullmatch(r"\d+(\.\d+)?", v)) / len(vals)
        cn_ratio = sum(1 for v in vals if re.search(r"[\u4e00-\u9fa5]", v)) / len(vals)
        if code_ratio > 0.5:
            guesses[c] = "code"
        elif num_ratio > 0.7:
            guesses[c] = "price"
        elif cn_ratio > 0.5:
            guesses.setdefault("app", c)
    return guesses


# ---------------------------------------------------------------- 单表解析
def parse_sheet(rows, cat, fixed=None, remark=""):
    """返回 (items, prices, fails)。items 里绝不含价格。"""
    items, prices, fails = [], [], []
    if fixed:
        start = 0
        roles = {"code": fixed["code"], "name": fixed.get("name"), "oe": fixed.get("oe"),
                 "app": fixed.get("app"), "price": fixed.get("price", [])}
        roles = {k: v for k, v in roles.items() if v is not None}
    else:
        start, roles = find_header(rows)
        if start < 0:
            return [], [], ["表头识别失败：%s" % remark]
        start += 1
        roles = validate_roles(rows, start, roles)
        if "code" not in roles:
            guesses = guess_roles_by_content(rows, start, roles)
            for c, role in guesses.items():
                if role == "code" and "code" not in roles:
                    roles["code"] = c
            extra_prices = [c for c, r in guesses.items() if r == "price" and c not in roles.get("price", [])]
            roles.setdefault("price", [])
            roles["price"] = list(roles["price"]) + extra_prices
        if "code" not in roles:
            return [], [], ["找不到商品编码列：%s" % remark]

    for rn in range(start, len(rows)):
        row = rows[rn]
        if not any(s(c) for c in row):
            continue
        vals, pr = row_values(row, roles, len(row))
        code = vals["code"]
        if not looks_code(code):
            # 允许以数字开头的编码，或整行是分组标题 → 跳过
            if code and not re.search(r"\d", code):
                continue
            if not code:
                continue
        if pr:
            prices.append({"code": code, "name": vals["name"], "prices": pr,
                           "sheet": remark, "row": rn + 1})
        oe_list = split_codes(vals["oe"])
        # “型号”这一列有时装的是车型（NJK 表就是这样），长文本或带斜杠的当适配车型
        if not vals["app"] and vals["model"] and (len(vals["model"]) >= 8 or "/" in vals["model"]):
            vals["app"] = vals["model"]
            vals["model"] = ""
        items.append({
            "cat": cat, "m": code, "n": vals["name"], "b": vals["brand"],
            "oe": oe_list[0] if oe_list else "", "x": oe_list[1:],
            "a": vals["app"], "r": vals["model"], "img": None, "src": remark,
        })
    return items, prices, fails


# ---------------------------------------------------------------- 数据源配置
def sources():
    f1 = os.path.join(SRC_DIR, "ABS  凸轮  曲轴  节气门  进气压力传感器目录表(2).xlsx")
    f2 = os.path.join(SRC_DIR, "NJK火花塞.xlsx")
    f3 = os.path.join(SRC_DIR, "胎压传感器目录.xlsx")
    f4 = os.path.join(SRC_DIR, "天博温度传感器与节温器5.31目录表.xlsx")
    f5 = os.path.join(SRC_DIR, "威利火花塞.xlsx")
    f6 = os.path.join(SRC_DIR, "线圈 碳罐 机油阀 阀体 马达 分火线 产品目录（带价格）(2).20260701165609369.xlsx")
    f7 = os.path.join(SRC_DIR, "氧传感器单价.xls")
    f8 = os.path.join(SRC_DIR, "油泵价格1.xls")
    f9 = os.path.join(SRC_DIR, "油泵目录表.xls")
    f10 = os.path.join(SRC_DIR, "真空电磁阀目录1.xlsx")
    return [
        ("xlsx", f1, [
            ("进气压力传感器", "map"), ("节气门位置传感器", "tps"), ("曲轴位置传感器", "ckp"),
            ("凸轮轴位置传感器", "cmp"), ("压差传感器", "dpfe"), ("ABS传感器", "abs"),
            # Sheet1 / Sheet2 是上面两张表的重复版本（价格不同），跳过
        ]),
        ("xlsx", f2, [("商品属性导出表20251223_黎达文_ (1)", "njkspark")]),
        ("xlsx", f3, [("Sheet1", "tpms")]),
        ("xlsx", f4, [("Sheet1", "temp")]),
        ("xlsx", f5, [("商品属性导出表20251223_黎达文_", "plug")]),
        ("xlsx", f6, [
            ("点火线圈", "coil"), ("步进电机", "stepper"), ("室外温度传感器", "temp"),
            ("水温传感器", "temp"), ("天博水温传感器", "temp"), ("喷油嘴", "injector"),
            ("电子", "throttle"), ("机械", "throttle"), ("高压线", "wire"),
            ("碳罐电磁阀", "purge"), ("油压传感器", "fuelpress"), ("空气流量计", "maf"),
            ("机油控制阀", "ocv"), ("火花塞", "plug"),
        ]),
        ("xls", f7, [("红盒包装", "o2"), ("白色包装", "o2")]),
        ("xls", f8, [("Sheet1", "fuelpump")]),
        ("xls", f9, [("Sheet1", "fuelpump")]),
        ("xlsx", f10, [("Sheet1", "vsv")]),
    ]


# 两个油泵表没有规范表头，用固定列位
FIXED = {
    "油泵价格1.xls": {"code": 0, "name": 1, "oe": 2, "app": 3, "price": [4, 5]},
    "油泵目录表.xls": {"code": 0, "name": 1, "oe": 2, "app": 3, "price": [4]},
}


def load_all(log=print):
    """读全部文件 → (items, price_rows, fails, used_files)"""
    items, price_rows, fails, used = [], [], [], []
    for kind, path, sheets in sources():
        name = os.path.basename(path)
        if not os.path.exists(path):
            fails.append("%s：文件不存在，跳过" % name)
            continue
        used.append(name)
        for sheet, cat in sheets:
            remark = "%s / %s" % (name, sheet)
            try:
                rows = read_xlsx_sheet(path, sheet) if kind == "xlsx" else read_xls_sheet(path, sheet)
            except Exception as e:
                fails.append("%s：读取失败 %s" % (remark, e))
                continue
            fixed = FIXED.get(name) if sheet == "Sheet1" else None
            got, pr, fl = parse_sheet(rows, cat, fixed=fixed, remark=remark)
            fails.extend(fl)
            items.extend(got)
            for p in pr:
                p["file"] = name
                p["sheet"] = sheet
            price_rows.extend(pr)
            log("    %-46s %-12s %4d 条%s" % (sheet[:46], cat, len(got), ("  (价格行 %d)" % len(pr)) if pr else ""))
    return items, price_rows, fails, used


# ---------------------------------------------------------------- 合并
def norm_code(c):
    return re.sub(r"[^A-Z0-9]", "", s(c).upper())


def note_key(it):
    return norm_code(it.get("m"))


def merge(existing, new_items, log=print):
    """existing: 站点现有 items（会被就地补充）；new_items: 新读的。
    先按商品编码合并，再按 OE 号补一次。返回 (新增条数, 合并条数, 新品类集合)"""
    by_code = {}
    for it in existing:
        by_code.setdefault(norm_code(it.get("m")), it)
    by_oe = {}
    for it in existing:
        for o in [it.get("oe", "")] + list(it.get("x") or []):
            k = norm_code(o)
            if len(k) >= 5:
                by_oe.setdefault(k, it)

    added, merged = 0, 0
    used_cats = set()
    for it in new_items:
        k = norm_code(it.get("m"))
        if not k:
            continue
        old = by_code.get(k)
        if old is None:
            # 同 OE 同品类的也算同一件
            cand = None
            for o in [it.get("oe")] + list(it.get("x") or []):
                ok = by_oe.get(norm_code(o))
                if ok and ok["cat"] == it["cat"]:
                    cand = ok
                    break
            if cand is not None:
                old = cand
        if old is not None:
            xs = list(old.get("x") or [])
            for o in [it.get("oe")] + list(it.get("x") or []):
                if o and norm_code(o) != norm_code(old.get("oe")) and o not in xs:
                    xs.append(o)
            # 同一个 OE 的不同包装/不同编码：把编码也挂上去，搜得到
            if norm_code(it["m"]) != norm_code(old.get("m")):
                if it["m"] not in xs:
                    xs.append(it["m"])
                note = "Also packed as %s" % it["m"]
                if note not in (old.get("r") or ""):
                    old["r"] = ((old.get("r") or "") + " | " + note).strip(" |")
            old["x"] = xs
            if not old.get("a") and it.get("a"):
                old["a"] = it["a"]
            if not old.get("b") and it.get("b"):
                old["b"] = it["b"]
            if not old.get("n") and it.get("n"):
                old["n"] = it["n"]
            merged += 1
            continue
        # 全新条目
        new = {
            "cat": it["cat"], "m": it["m"], "n": it.get("n") or CAT_FALLBACK.get(it["cat"], ""), "b": it.get("b") or "WEILI",
            "oe": it.get("oe") or "", "x": list(it.get("x") or []), "a": it.get("a") or "",
            "r": it.get("r") or "", "img": None,
        }
        existing.append(new)
        by_code[k] = new
        for o in [new["oe"]] + new["x"]:
            if len(norm_code(o)) >= 5:
                by_oe.setdefault(norm_code(o), new)
        added += 1
        used_cats.add(it["cat"])
    return added, merged, used_cats


def write_prices(price_rows):
    os.makedirs(PRICE_DIR, exist_ok=True)
    p = os.path.join(PRICE_DIR, "价格表.csv")
    heads = []
    for r in price_rows:
        for k in r["prices"]:
            if k not in heads:
                heads.append(k)
    with open(p, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["来源文件", "工作表", "行号", "商品编码", "名称"] + ["价格" + h for h in heads])
        for r in price_rows:
            w.writerow([r.get("file", ""), r.get("sheet", ""), r.get("row", ""), r["code"], r["name"]] +
                       [r["prices"].get(h, "") for h in heads])
    readme = os.path.join(PRICE_DIR, "说明.txt")
    with open(readme, "w", encoding="utf-8") as f:
        f.write(
            "内部价格表（不要发布、不要上传）\n"
            "===============================\n"
            "这里是合并目录表时抽出来的价格，只放在本机，网页和 GitHub 上都没有这些数字。\n"
            "价格表.csv 用 Excel 打开即可。\n"
            "生成时间：%s\n" % __import__("time").strftime("%Y-%m-%d %H:%M")
        )
    return p, len(price_rows)
