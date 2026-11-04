# -*- coding: utf-8 -*-
"""
车型品牌 / 车系词典（给「按品牌浏览」「按车型浏览」落地页用）
================================================================
只做三件事，全部纯字符串处理，不依赖站点其它模块：

  BRANDS            品牌规范名 -> 别名列表（大写）
  brand_hits(text)  适配车型文本里出现哪些品牌（返回规范名列表，去重保序）
  vehicle_tokens(text)  适配车型文本里的车系关键词（全量，不截断，过滤掉噪声词）

品牌页 URL：/brand/<brand_slug>.html
车型页 URL：/vehicle/<token_slug>.html
"""

import re

# 品牌规范名 -> 别名（全部大写；含常见拼错/缩写）。
# 只收汽配目录里真实出现过的写得出来的品牌，宁缺毋滥：认不出的进「无品牌」，不要瞎猜。
BRANDS = {
    "Toyota": ["TOYOTA", "TOYTA"],
    "Lexus": ["LEXUS"],
    "Honda": ["HONDA"],
    "Acura": ["ACURA"],
    "Nissan": ["NISSAN", "NISSIAN"],
    "Infiniti": ["INFINITI"],
    "Mazda": ["MAZDA"],
    "Mitsubishi": ["MITSUBISHI"],
    "Subaru": ["SUBARU"],
    "Suzuki": ["SUZUKI"],
    "Isuzu": ["ISUZU"],
    "Daihatsu": ["DAIHATSU"],
    "Hyundai": ["HYUNDAI", "HYUNDIA"],
    "Kia": ["KIA"],
    "Genesis": ["GENESIS"],
    "Daewoo": ["DAEWOO"],
    "SsangYong": ["SSANGYONG"],
    "Chevrolet": ["CHEVROLET", "CHEVY"],
    "Buick": ["BUICK"],
    "Cadillac": ["CADILLAC"],
    "GMC": ["GMC"],
    "Ford": ["FORD"],
    "Lincoln": ["LINCOLN"],
    "Chrysler": ["CHRYSLER"],
    "Dodge": ["DODGE"],
    "Jeep": ["JEEP"],
    "Ram": ["RAM"],
    "Tesla": ["TESLA"],
    "Volkswagen": ["VOLKSWAGEN", "VW"],
    "Audi": ["AUDI"],
    "BMW": ["BMW"],
    "Mini": ["MINI"],
    "Mercedes-Benz": ["MERCEDES", "BENZ"],
    "Smart": ["SMART"],
    "Porsche": ["PORSCHE"],
    "Opel": ["OPEL"],
    "Peugeot": ["PEUGEOT", "PEUGOET"],
    "Citroen": ["CITROEN"],
    "Renault": ["RENAULT"],
    "Dacia": ["DACIA"],
    "Skoda": ["SKODA"],
    "Seat": ["SEAT"],
    "Volvo": ["VOLVO"],
    "Saab": ["SAAB"],
    "Land Rover": ["LAND ROVER", "LANDROVER", "RANGE ROVER"],
    "Jaguar": ["JAGUAR"],
    "Fiat": ["FIAT"],
    "Alfa Romeo": ["ALFA ROMEO"],
    "Lancia": ["LANCIA"],
    "Chery": ["CHERY"],
    "Geely": ["GEELY"],
    "BYD": ["BYD"],
    "Great Wall": ["GREAT WALL", "GREATWALL", "GWM"],
    "Haval": ["HAVAL"],
    "Changan": ["CHANGAN"],
    "BAIC": ["BAIC"],
    "Dongfeng": ["DONGFENG"],
    "FAW": ["FAW"],
    "JAC": ["JAC"],
    "Lifan": ["LIFAN"],
    "MG": ["MG"],
    "Roewe": ["ROEWE"],
    "Wuling": ["WULING"],
    "Baojun": ["BAOJUN"],
    "Mahindra": ["MAHINDRA"],
    "Tata": ["TATA"],
    "Maruti": ["MARUTI"],
    "Proton": ["PROTON"],
    "Perodua": ["PERODUA"],
    "UAZ": ["UAZ"],
    "Lada": ["LADA"],
    # 中国品牌 / 子品牌（目录里按品牌出现，不是车系，别让它们跑进车型页）
    "Jinbei": ["JINBEI"],
    "Forthing": ["FORTHING"],
    "Foton": ["FOTON"],
    "Soueast": ["SOUEAST"],
    "JMC": ["JMC"],
    "Maxus": ["MAXUS"],
    "Haima": ["HAIMA"],
    "Zotye": ["ZOTYE"],
    "Brilliance": ["BRILLIANCE", "ZHONGHUA"],
    "Trumpchi": ["TRUMPCHI"],
    "Landwind": ["LANDWIND"],
    "Sokon": ["SOKON"],
    "Oushan": ["OUSHAN"],
    "Venucia": ["VENUCIA"],
    "WEY": ["WEY"],
    "Exeed": ["EXEED"],
    "DFSK": ["DFSK"],
    "Beijing": ["BEIJING"],
    "Besturn": ["BESTURN"],
    "Jetour": ["JETOUR"],
    "Hanteng": ["HANTENG"],
    "Borgward": ["BORGWARD"],
    "SWM": ["SWM"],
    "Lynk": ["LYNK"],
    "NETA": ["NETA"],
    "Luxgen": ["LUXGEN"],
    "Hawtai": ["HAWTAI"],
    "Huanghai": ["HUANGHAI"],
    "Iveco": ["IVECO"],
    "Maserati": ["MASERATI"],
    "Karry": ["KARRY"],
    "Senova": ["SENOVA"],
    "Fengguang": ["FENGGUANG"],
    "Leopaard": ["LEOPAARD"],
    "Weiwang": ["WEIWANG"],
}

# 品牌 slug（URL 用；手写一遍，避免 slugify 把 "Mercedes-Benz" 拆成两份）
BRAND_SLUG = {
    "Mercedes-Benz": "mercedes-benz", "Land Rover": "land-rover",
    "Alfa Romeo": "alfa-romeo", "Great Wall": "great-wall",
    "SsangYong": "ssangyong", "Volkswagen": "volkswagen", "Daihatsu": "daihatsu",
}

ALIAS = {}
for _canon, _names in BRANDS.items():
    for _n in _names:
        ALIAS[_n] = _canon
# 长别名优先匹配（"LAND ROVER" 先于 "LAND"）
_ALIAS_KEYS = sorted(ALIAS, key=len, reverse=True)

_SQ = re.compile(r"\s+")


def _tidy(text):
    """大写 + 标点变空格 + 压缩空格，两边补空格，方便 \b 之外的整词匹配。"""
    t = re.sub(r"[^A-Za-z ]", " ", (text or "").upper())
    return " " + _SQ.sub(" ", t).strip() + " "


def brand_hits(text):
    """适配车型文本 → 命中的品牌规范名（去重保序）。"""
    t = _tidy(text)
    out = []
    for alias in _ALIAS_KEYS:
        if (" " + alias + " ") in t:
            canon = ALIAS[alias]
            if canon not in out:
                out.append(canon)
    return out


def brand_slug(canon):
    return BRAND_SLUG.get(canon, canon.lower().replace(" ", "-"))


# 车系关键词里明显不是车的词（品牌别名之外还要挡的）
VEHICLE_STOP = {
    # 通用词
    "THE", "AND", "FOR", "WITH", "WITHOUT", "NEW", "OLD", "FROM", "ALL", "SET", "KIT",
    "FRONT", "REAR", "LEFT", "RIGHT", "UPPER", "LOWER", "INNER", "OUTER", "SIDE",
    "AT", "MT", "CVT", "DCT", "DSG", "EFI", "MPI", "GDI", "LPG", "CNG", "TURBO",
    "TSI", "TDCI", "SUV", "MPV", "SEDAN", "HATCHBACK", "COUPE", "WAGON", "PICKUP",
    "VAN", "TRUCK", "BUS", "CAB", "ENG", "ENGINE", "MODEL", "VERSION", "IMPORTED",
    "DOMESTIC", "PRESENT", "YEARS", "YEAR", "EXPORT", "OEM", "OES", "PIN", "WIRE",
    "GEN", "PLUS", "PRO", "MAX", "SPORT", "BASE", "TYPE", "PART", "SERIES",
    "CYL", "CYLINDER", "VALVE", "FAMILY", "SERIES",
    # 目录里的零件/规格词
    "WHEEL", "COIL", "PUMP", "SENSOR", "ASSY", "CONNECTOR", "CABLE", "HOSE", "CLIP",
    "MOTOR", "AUTO", "CAR", "PARTS", "STEEL", "PLASTIC", "METAL", "RUBBER", "COLOR",
    "GREY", "GRAY", "BLACK", "WHITE", "BLUE", "RED", "GREEN", "CHROME",
    # 产地 / 区域
    "USA", "JAPAN", "KOREA", "CHINA", "GERMANY", "FRANCE", "ITALY", "RUSSIA",
    "BRAZIL", "INDIA", "TURKEY", "IRAN", "EGYPT", "EUROPE", "EURO", "ASIA",
    "AFRICA", "MIDDLE", "EAST", "SOUTH", "NORTH", "AMERICA", "LATIN",
    # 常见非车系词
    "CLASS", "STAR", "EURO", "STANDARD", "HIGH", "LOW", "SMALL", "BIG", "LARGE",
    "SINGLE", "DOUBLE", "TRIPLE", "FOUR", "TWO", "THREE", "PIPE", "PIPES",
    "SERIES", "CONDITION", "ORIGINAL", "AFTERMARKET", "QUALITY", "BRAND",
    # 组合品牌的拆词（GREAT WALL / LAND ROVER / RANGE ROVER 已由品牌词典整词识别）
    "GREAT", "WALL", "LAND", "ROVER", "RANGE", "ALFA", "ROMEO",
    # 供应商 / 配套厂（不是车系）
    "BOSCH", "DELPHI", "DENSO", "UAES", "SIEMENS", "BORG", "WARNER", "MOTOROLA",
    "CONTINENTAL", "MAGNETI", "MARELLI", "VALEO", "HELLA", "NGK", "HITACHI",
    "AISIN", "KYB", "MANN", "VISCO", "PCS", "VDO", "SAGEM",
    # 目录噪声
    "EDITION", "STRAIGHT", "SANTA", "KING", "KONG", "XY", "AC", "OE",
    "GAC", "SAIC", "DIESEL", "BENT", "TRIM", "SPEED", "WIRING", "HARNESS",
    "DIAMETER", "POINT", "CROSS", "SERIES", "ENGINEERING",
    "GRAND", "UNIVERSAL", "ZHENGZHOU", "SAME", "MAIN", "MULTI", "VVT", "HEAD",
    "VIEW", "PARK", "LONG", "SHAFT", "PETROL", "CLASSIC", "ELECTRIC", "HYBRID",
    "FACELIFT", "SHORT", "BRAKE", "ENERGY", "FREE", "TREK", "SLS", "CTS", "AMG",
    "CRUISER", "AVENUE", "SON",
}
# 品牌别名也永远不是车系关键词
VEHICLE_STOP |= set(ALIAS)

_WORD = re.compile(r"[A-Za-z][A-Za-z0-9]*")


def vehicle_tokens(text):
    """适配车型文本 → 车系关键词列表（全量、去重保序、纯字母 3–14 个字符）。"""
    out, seen = [], set()
    for w in _WORD.findall(text or ""):
        t = w.upper()
        if len(t) < 3 or len(t) > 14:
            continue
        if not re.fullmatch(r"[A-Z]+", t):
            continue
        if t in VEHICLE_STOP or t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out


def token_slug(t):
    return t.lower().replace(".", "-").replace(" ", "-")
