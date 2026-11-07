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

# ---------------------------------------------------------------
# 车系归属：这个车系「属于」哪个品牌
# ---------------------------------------------------------------
# 为什么必须显式写一张表，而不能按文本投票：
#   适配文本里一个型号常写好几个车系，跨品牌共通件是真实存在的
#   （90919-05059 这个丰田线圈也装长安逸动）。只按共现次数投票，
#   会把 CROWN / HIGHLANDER / PRIUS 这类「丰田-雷克萨斯共线」的车系
#   投给雷克萨斯，把 PASSAT 投给奥迪。所以归属写死，不猜。
#   表里没有的车系 = 归属不明，只进品牌页的「也适用这些车系」，
#   绝不冒充「本品牌车型」。
MODEL_OWNER = {
    # 日系
    "CAMRY": "Toyota", "COROLLA": "Toyota", "CROWN": "Toyota", "HIGHLANDER": "Toyota",
    "LEVIN": "Toyota", "PRADO": "Toyota", "PRIUS": "Toyota", "REIZ": "Toyota",
    "VIOS": "Toyota", "YARIS": "Toyota",
    "ACCORD": "Honda", "CITY": "Honda", "CIVIC": "Honda", "CRIDER": "Honda",
    "CROSSTOUR": "Honda", "CRV": "Honda", "FIT": "Honda", "ODYSSEY": "Honda",
    "SPIRIOR": "Honda", "VEZEL": "Honda",
    "BLUEBIRD": "Nissan", "LIVINA": "Nissan", "MURANO": "Nissan", "QASHQAI": "Nissan",
    "SUNNY": "Nissan", "SYLPHY": "Nissan", "TEANA": "Nissan", "TIIDA": "Nissan",
    "ATENZA": "Mazda", "AXELA": "Mazda", "FAMILIA": "Mazda", "PREMACY": "Mazda",
    "ASX": "Mitsubishi", "DELICA": "Mitsubishi", "LANCER": "Mitsubishi",
    "LIONCEL": "Mitsubishi", "OUTLANDER": "Mitsubishi", "PAJERO": "Mitsubishi",
    "FORESTER": "Subaru", "LEGACY": "Subaru", "OUTBACK": "Subaru",
    "ALTO": "Suzuki", "LIANA": "Suzuki", "VITARA": "Suzuki",
    # 韩系
    "ACCENT": "Hyundai", "ELANTRA": "Hyundai", "SONATA": "Hyundai",
    "TUCSON": "Hyundai", "VERNA": "Hyundai",
    "CERATO": "Kia", "OPTIMA": "Kia", "RIO": "Kia", "SORENTO": "Kia", "SPORTAGE": "Kia",
    # 美系
    "AVEO": "Chevrolet", "CAPTIVA": "Chevrolet", "CAVALIER": "Chevrolet",
    "CRUZE": "Chevrolet", "EPICA": "Chevrolet", "LOVA": "Chevrolet",
    "MALIBU": "Chevrolet", "MONZA": "Chevrolet", "SAIL": "Chevrolet",
    "SPARK": "Chevrolet", "TRAX": "Chevrolet",
    "ENCLAVE": "Buick", "ENCORE": "Buick", "ENVISION": "Buick", "EXCELLE": "Buick",
    "LACROSSE": "Buick", "REGAL": "Buick", "VERANO": "Buick",
    "ECOSPORT": "Ford", "EDGE": "Ford", "FIESTA": "Ford", "FOCUS": "Ford",
    "KUGA": "Ford", "MONDEO": "Ford", "TAURUS": "Ford", "TRANSIT": "Ford",
    "SRX": "Cadillac", "XTS": "Cadillac",
    "CHEROKEE": "Jeep", "COMPASS": "Jeep", "PATRIOT": "Jeep", "WRANGLER": "Jeep",
    "JOURNEY": "Dodge", "VOYAGER": "Chrysler",
    # 德系
    "BEETLE": "Volkswagen", "BORA": "Volkswagen", "GOLF": "Volkswagen",
    "JETTA": "Volkswagen", "LAVIDA": "Volkswagen", "MAGOTAN": "Volkswagen",
    "PASSAT": "Volkswagen", "POLO": "Volkswagen", "SAGITAR": "Volkswagen",
    "SANTANA": "Volkswagen", "TIGUAN": "Volkswagen", "TOUAREG": "Volkswagen",
    "TOURAN": "Volkswagen",
    "FABIA": "Skoda", "OCTAVIA": "Skoda", "SUPERB": "Skoda", "YETI": "Skoda",
    "CLS": "Mercedes-Benz", "GLC": "Mercedes-Benz", "GLK": "Mercedes-Benz",
    "VIANO": "Mercedes-Benz", "VITO": "Mercedes-Benz",
    # 法系 / 欧系
    "ELYSEE": "Citroen", "QUATRE": "Citroen", "TRIOMPHE": "Citroen",
    "PANDA": "Fiat",
    "DISCOVERY": "Land Rover", "EVOQUE": "Land Rover",
    # 中国品牌
    "ALSVIN": "Changan", "BENBEN": "Changan", "EADO": "Changan", "ONO": "Changan",
    "RAETON": "Changan", "UNI": "Changan", "XINGKA": "Changan",
    "ARRIZO": "Chery", "COWIN": "Chery", "FULWIN": "Chery",
    "ORIENTAL": "Chery", "TIGGO": "Chery",
    "BINYUE": "Geely", "BORUI": "Geely", "BOYUE": "Geely", "EMGRAND": "Geely",
    "VISION": "Geely", "XINGYUE": "Geely",
    "QIN": "BYD", "SONG": "BYD", "YUAN": "BYD",
    "HONGGUANG": "Wuling", "HONGTU": "Wuling", "RONGGUANG": "Wuling", "ZHIGUANG": "Wuling",
    "HEYUE": "JAC", "REFINE": "JAC", "SEHOL": "JAC",
    "COOLBEAR": "Great Wall", "FLORID": "Great Wall", "VOLEEX": "Great Wall",
    "WINGLE": "Great Wall",
    "HEIJINGANG": "Leopaard", "LEOPAUL": "Leopaard",
    "JUNJIE": "Brilliance",
    "JINGYI": "Forthing", "LINGZHI": "Forthing",
    "HUANSU": "BAIC", "ZHANQI": "BAIC",
    "SENIA": "FAW", "WEIZHI": "FAW",
    "FEITENG": "Besturn",
    "HAISE": "Jinbei",
    "BAODIAN": "JMC", "RUIMAI": "JMC", "VIGUS": "JMC", "YUHU": "JMC", "YUSHENG": "JMC",
    "AEOLUS": "Dongfeng",
}


def model_owner(token):
    """车系 -> 品牌规范名；没收录的返回 None（归属不明，不猜）。"""
    return MODEL_OWNER.get((token or "").upper())


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

# ------------------------------------------------------------------ 品牌国籍
# 首页「按品类浏览全部型号」那个列表的排序用：日系 -> 德系 -> 韩系 -> 其余。
# 目标市场（中东 / 非洲 / 拉美 / 独联体）修的绝大多数是这几系；国产车系排后面，
# 免得买家一滑下去满屏长安之星、五菱宏光，觉得「这网站不是给我的」。
BRAND_ORIGIN = {
    "JP": ["Toyota", "Lexus", "Honda", "Acura", "Nissan", "Infiniti", "Mazda",
           "Mitsubishi", "Subaru", "Suzuki", "Isuzu", "Daihatsu"],
    # Skoda / Seat 归在德系里，因为买家是按大众集团找件的
    "DE": ["Volkswagen", "Audi", "BMW", "Mini", "Mercedes-Benz", "Smart", "Porsche",
           "Opel", "Skoda", "Seat"],
    "KR": ["Hyundai", "Kia", "Genesis", "Daewoo", "SsangYong"],
    "US": ["Chevrolet", "Buick", "Cadillac", "GMC", "Ford", "Lincoln", "Chrysler",
           "Dodge", "Jeep", "Ram", "Tesla"],
    "FR": ["Peugeot", "Citroen", "Renault", "Dacia"],
    "IT": ["Fiat", "Alfa Romeo", "Lancia", "Maserati", "Iveco"],
    "SE": ["Volvo", "Saab"],
    "UK": ["Land Rover", "Jaguar"],
}

# 中国自主品牌（列表里排最后）
CHINA_BRANDS = {
    "Chery", "Geely", "BYD", "Great Wall", "Haval", "Changan", "BAIC", "Dongfeng", "FAW",
    "JAC", "Lifan", "MG", "Roewe", "Wuling", "Baojun", "Jinbei", "Forthing", "Foton",
    "Soueast", "JMC", "Maxus", "Haima", "Zotye", "Brilliance", "Trumpchi", "Landwind",
    "Sokon", "Oushan", "Venucia", "WEY", "Exeed", "DFSK", "Beijing", "Besturn", "Jetour",
    "Hanteng", "Borgward", "SWM", "Lynk", "NETA", "Luxgen", "Hawtai", "Huanghai",
    "Karry", "Senova", "Fengguang", "Leopaard", "Weiwang",
}

ORIGIN_ORDER = ["JP", "DE", "KR", "US", "FR", "IT", "SE", "UK", "CN", "OTHER"]
ORIGIN_RANK = {o: i for i, o in enumerate(ORIGIN_ORDER)}
ORIGIN_LABEL = {"JP": "Japan", "DE": "Germany", "KR": "Korea", "US": "USA", "FR": "France",
                "IT": "Italy", "SE": "Sweden", "UK": "UK", "CN": "China", "OTHER": "Other"}

_BRAND_ORIGIN = {b: o for o, bs in BRAND_ORIGIN.items() for b in bs}


def brand_origin(brand):
    """品牌规范名 -> 区域代码。"""
    if brand in _BRAND_ORIGIN:
        return _BRAND_ORIGIN[brand]
    return "CN" if brand in CHINA_BRANDS else "OTHER"


def origin_of_brands(brands):
    """一组品牌 -> 最靠前的区域（一个件同时适配丰田和长安，就算日系）。"""
    best = "OTHER"
    for b in brands or ():
        o = brand_origin(b)
        if ORIGIN_RANK[o] < ORIGIN_RANK[best]:
            best = o
    return best
