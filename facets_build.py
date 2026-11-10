# -*- coding: utf-8 -*-
"""
构建 data/facets.js —— 首页「品牌 → 车型 → 年款 → 排量」级联筛选用。
=====================================================================
规则（和数据一起走，页面不再自己猜）：

  · 品牌：brands.brand_hits()（词典 + 别名，整词匹配）
  · 车型：brands.vehicle_tokens() 里
        - 词典登记过归属的（MODEL_OWNER / MODEL_EXTRA）→ 归给它登记的品牌；
        - 没登记的，只有整条文本里只出现一个品牌时才归给这个品牌；
        - 代号（T31 / J32 / HR16）、方位词、零件词、供应商名一律不要。
  · 年款：item.y（结构化）；开口区间 2019- 算到今年
  · 排量：item.d

输出给浏览器的是紧凑数组，省流量：
  window.YMY_FACETS={g, aliases:{NISSAN:"Nissan",...}, models:{SUNNY:"Nissan",...},
    brands:[["Nissan",177,[["SUNNY","Sunny",6,2007,2024,[1.2,1.5,1.6,2.0]], ...]], ...]}
"""
import io
import json
import os
import re
import sys
import collections
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import brands  # noqa: E402

NOW = datetime.now().year
WORD = re.compile(r"[A-Za-z][A-Za-z0-9]*(?:-[A-Za-z0-9]+)*")
EXTRA_STOP = {"AWD", "FWD", "4WD", "2WD", "INJECTOR", "SENSOR", "PUMP", "COIL",
              "FRONT", "REAR", "LEFT", "RIGHT", "IMPORTED", "DOMESTIC", "PIECE",
              "BEARING", "HUB", "SHAFT", "BOX", "GEAR", "VALVE", "MOTOR", "KIT"}
CODEY = re.compile(r"^(?:[A-Za-z]{1,3}\d|\d)")
# 带数字/连字符但确实是车系的，登记在这里（奕然确认要加）
MODEL_EXTRA = {
    # Nissan
    "370Z": "Nissan", "350Z": "Nissan", "GTR": "Nissan", "NAVARA": "Nissan",
    "XTERRA": "Nissan", "NV200": "Nissan", "NV300": "Nissan", "URVAN": "Nissan",
    # Toyota / Lexus
    "86": "Toyota", "SUPRA": "Toyota", "LCS": "Lexus", "CT200H": "Lexus",
    # Honda
    "CRV": "Honda", "HRV": "Honda", "XRV": "Honda", "URV": "Honda", "BRV": "Honda",
    # VW / Audi / Skoda
    "GOLF": "Volkswagen", "POLO": "Volkswagen", "PASSAT": "Volkswagen", "SANTANA": "Volkswagen",
    "LAVIDA": "Volkswagen", "BORA": "Volkswagen", "JETTA": "Volkswagen", "TIGUAN": "Volkswagen",
    "TOUAREG": "Volkswagen", "MAGOTAN": "Volkswagen", "SAGITAR": "Volkswagen",
    "A4L": "Audi", "A6L": "Audi", "Q5L": "Audi", "Q7": "Audi", "A3": "Audi",
    "A4": "Audi", "A6": "Audi", "A8": "Audi", "Q3": "Audi", "Q5": "Audi",
    "OCTAVIA": "Skoda", "SUPERB": "Skoda", "KODIAQ": "Skoda",
    # BMW / Mercedes
    "X1": "BMW", "X3": "BMW", "X5": "BMW", "X6": "BMW", "320": "BMW", "325": "BMW",
    "520": "BMW", "525": "BMW", "730": "BMW", "740": "BMW",
    "C200": "Mercedes-Benz", "E200": "Mercedes-Benz", "E260": "Mercedes-Benz",
    "S350": "Mercedes-Benz", "GLC": "Mercedes-Benz", "GLE": "Mercedes-Benz",
    # Peugeot / Citroen / Renault
    "206": "Peugeot", "207": "Peugeot", "208": "Peugeot", "301": "Peugeot",
    "307": "Peugeot", "308": "Peugeot", "408": "Peugeot", "508": "Peugeot",
    "2008": "Peugeot", "3008": "Peugeot", "4008": "Peugeot", "5008": "Peugeot",
    "C3": "Citroen", "C4": "Citroen", "C5": "Citroen", "C6": "Citroen",
    # Ford / GM
    "F150": "Ford", "FOCUS": "Ford", "FIESTA": "Ford", "MONDEO": "Ford", "KUGA": "Ford",
    "ECOSPORT": "Ford", "EDGE": "Ford", "EXPLORER": "Ford", "RANGER": "Ford",
    "GL8": "Buick", "EXCELLE": "Buick", "REGAL": "Buick", "LACROSSE": "Buick",
    "ENVISION": "Buick", "ENCLAVE": "Buick", "ENCORE": "Buick", "VERANO": "Buick",
    "CRUZE": "Chevrolet", "SAIL": "Chevrolet", "MALIBU": "Chevrolet", "CAPTIVA": "Chevrolet",
    "SPARK": "Chevrolet", "AVEO": "Chevrolet", "TRAX": "Chevrolet", "EQUINOX": "Chevrolet",
    # Hyundai / Kia
    "IX35": "Hyundai", "IX25": "Hyundai", "TUCSON": "Hyundai", "ELANTRA": "Hyundai",
    "SONATA": "Hyundai", "ACCENT": "Hyundai", "VERNA": "Hyundai", "MISTRA": "Hyundai",
    "K2": "Kia", "K3": "Kia", "K5": "Kia", "KX3": "Kia", "KX5": "Kia", "K4": "Kia",
    "SPORTAGE": "Kia", "SORENTO": "Kia", "CERATO": "Kia", "RIO": "Kia", "OPTIMA": "Kia",
    "CARNIVAL": "Kia", "CARENS": "Kia", "SELTOS": "Kia", "STONIC": "Kia", "MOHAVE": "Kia",
    "CRETA": "Hyundai", "I10": "Hyundai", "I20": "Hyundai", "I30": "Hyundai",
    "STAREX": "Hyundai", "PALISADE": "Hyundai",
    # Chinese
    "H2": "Haval", "H6": "Haval", "H9": "Haval", "F7": "Haval",
    "CS35": "Changan", "CS55": "Changan", "CS75": "Changan", "CS95": "Changan",
    "EC7": "Geely", "EC8": "Geely", "GX7": "Geely", "B70": "Besturn", "B50": "Besturn",
    "F3": "BYD", "F6": "BYD", "S6": "BYD", "S7": "BYD", "G6": "BYD", "L3": "BYD",
    "T600": "Zotye", "T700": "Zotye",
    # Mitsubishi / Subaru / Suzuki
    "ASX": "Mitsubishi", "L200": "Mitsubishi", "V73": "Mitsubishi", "V93": "Mitsubishi",
    "XV": "Subaru", "BRZ": "Subaru", "WRX": "Subaru",
    "SWIFT": "Suzuki", "VITARA": "Suzuki", "SX4": "Suzuki", "JIMNY": "Suzuki",
}
OWNER = dict(brands.MODEL_OWNER)
OWNER.update(MODEL_EXTRA)

DISPLAY = {"CRV": "CR-V", "XTRAIL": "X-Trail", "CHR": "C-HR", "XRV": "XR-V",
           "URV": "UR-V", "BRV": "BR-V", "HRV": "HR-V", "NV200": "NV200",
           "370Z": "370Z", "350Z": "350Z", "300C": "300C", "GTR": "GT-R",
           "CT200H": "CT200h", "A4L": "A4L", "A6L": "A6L", "Q5L": "Q5L",
           "IX35": "ix35", "IX25": "ix25", "SX4": "SX4", "T600": "T600"}
ALIASES = {a.upper(): canon for a, canon in brands.ALIAS.items()}
ALIAS_NORM = {re.sub(r"[^A-Z0-9]", "", k) for k in ALIASES}


def norm(t):
    return re.sub(r"[^A-Za-z0-9]", "", t or "").upper()


def years_of(it):
    spans = []
    for s in it.get("y") or []:
        s = str(s).strip()
        m = re.fullmatch(r"((?:19|20)\d{2})(?:\s*[-–]\s*((?:19|20)\d{2})?)?", s)
        if not m:
            continue
        a = int(m.group(1))
        b = int(m.group(2)) if m.group(2) else a
        if s.endswith("-"):
            b = NOW
        b = min(b, NOW)
        if 1970 <= a <= NOW:
            spans.append((a, b))
    if not spans:
        return (0, 0)
    return (min(a for a, _ in spans), max(b for _, b in spans))


def disps_of(it):
    out = set()
    for s in it.get("d") or []:
        m = re.match(r"(\d(?:\.\d)?)\s*[LT]?", str(s).strip(), re.I)
        if not m:
            continue
        v = float(m.group(1))
        if 0.5 <= v <= 8.0:
            out.add(round(v, 1))
    return sorted(out)


def models_of(a, bs):
    """返回 {brand: [key]}：词典登记的车系 + 品牌名后面 1–2 个词里的词形车系。"""
    out = collections.defaultdict(list)
    seen = set()
    text = a or ""

    def ok(key, b):
        if not (3 <= len(key) <= 14):
            return False
        if key in ALIAS_NORM or key in brands.VEHICLE_STOP or key in EXTRA_STOP:
            return False
        if CODEY.match(key):
            return False
        owner = OWNER.get(key)
        if owner and owner != b:     # 别的品牌的登记车系，不能抢过来
            return False
        return True

    # 1) 词典登记的车系
    for w in WORD.findall(text):
        key = norm(w)
        owner = OWNER.get(key)
        if owner and owner in bs and key not in seen:
            seen.add(key)
            out[owner].append(key)

    # 2) 品牌名后面 1–2 个词（Patrol / March 这类没登记的，靠位置收）
    for b in bs:
        for name in brands.BRANDS.get(b, [b]):
            for m in re.finditer(r"\b" + re.escape(name) + r"\b", text, re.I):
                tail = text[m.end(): m.end() + 32]
                for w in WORD.findall(tail)[:2]:
                    key = norm(w)
                    if key in seen or not ok(key, b):
                        continue
                    seen.add(key)
                    out[b].append(key)
    return out


def build(payload, log=print):
    items = payload.get("items") or []
    agg = collections.defaultdict(lambda: collections.defaultdict(
        lambda: {"n": 0, "y0": 0, "y1": 0, "d": set()}))
    stats = {"items": 0, "branded": 0, "models": 0}
    for it in items:
        a = it.get("a") or ""
        bs = brands.brand_hits(a)
        if not bs:
            continue
        stats["branded"] += 1
        y0, y1 = years_of(it)
        ds = disps_of(it)
        for b, keys in models_of(a, bs).items():
            for k in dict.fromkeys(keys):
                rec = agg[b][k]
                rec["n"] += 1
                if y0:
                    rec["y0"] = min(rec["y0"] or y0, y0)
                    rec["y1"] = max(rec["y1"] or y1, y1)
                rec["d"].update(ds)
                stats["models"] += 1

    brands_out = []
    for b in sorted(agg, key=lambda x: -sum(r["n"] for r in agg[x].values())):
        models = []
        for k, r in sorted(agg[b].items(), key=lambda kv: -kv[1]["n"]):
            disp = DISPLAY.get(k) or (k.title() if k.isupper() else k)
            models.append([k, disp, r["n"], r["y0"], r["y1"], sorted(r["d"])])
        brands_out.append([b, sum(m[2] for m in models), models])

    data = {"g": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "aliases": ALIASES, "models": OWNER,
            "stop": sorted(brands.VEHICLE_STOP | EXTRA_STOP),
            "brands": brands_out}
    out = os.path.join(HERE, "data", "facets.js")
    body = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    tmp = out + ".tmp"
    with io.open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write("/* 级联筛选数据 —— 由 facets_build.py 自动生成，别手改。 */\n")
        f.write("window.YMY_FACETS=")
        f.write(body)
        f.write(";\n")
    os.replace(tmp, out)
    log("  级联数据：%d 个品牌 / %d 条品牌-车型（%.0f KB）"
        % (len(brands_out), stats["models"], os.path.getsize(out) / 1024.0))
    return data


def main():
    import data_prep
    payload, _ = data_prep.prepare(write=False, log=lambda m: None)
    build(payload)


if __name__ == "__main__":
    main()
