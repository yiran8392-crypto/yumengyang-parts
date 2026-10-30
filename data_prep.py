# -*- coding: utf-8 -*-
"""
站点数据后处理（build.py / rerender.py 都会调）
====================================================
1) 清洗中文：品牌（威利→WEILI 等）、适配车型（宝马→BMW、前左→Front LH …）
   —— 原始值全部写进站外的映射表 ../型号查询站-清洗映射/clean_map.json
   —— 清洗完还剩中文的，品牌归 Unspecified、车型只保留英文片段
2) OE 去重：同一 OE 只留「信息最全」的一条
3) 拆包：data/meta.js + data/chunk-XX.js（每片 CHUNK 条），首页只引第 0 片
   其余分片由 assets/catalog.js 用 <script> 动态注入 —— file:// 双击也能跑

用法：
    python data_prep.py             单独跑，清洗 + 拆包
    import data_prep                build.py / rerender.py 里调用
"""
import io
import json
import os
import re
import time

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")
DATA_JS = os.path.join(DATA_DIR, "data.js")
MAP_DIR = os.path.join(os.path.dirname(HERE), "型号查询站-清洗映射")
CHUNK = 240                 # 每个分片多少条
CLEAN_VER = 6               # 字典/规则版本，改了它才会重新清洗

CJK = re.compile(r"[\u4e00-\u9fa5]")

# ---------------------------------------------------------------- 词典
# 品牌 / 车系 / 车型 / 位置 / 描述。按长度从长到短替换，避免「五菱宏光」被「五菱」先吃掉。
BRAND = {
    "北京奔驰": "Beijing Benz", "广汽传祺": "GAC Trumpchi", "广汽本田": "GAC Honda",
    "东风本田": "Dongfeng Honda", "东风日产": "Dongfeng Nissan", "东风小康": "Dongfeng Sokon",
    "东风风行": "Dongfeng Forthing", "东风风神": "Dongfeng Aeolus", "东风标致": "Dongfeng Peugeot",
    "东风雪铁龙": "Dongfeng Citroen", "上汽通用": "SAIC-GM", "上汽大众": "SAIC Volkswagen",
    "一汽大众": "FAW-Volkswagen", "一汽奥迪": "FAW Audi", "一汽丰田": "FAW Toyota",
    "一汽奔腾": "FAW Besturn", "一汽红旗": "FAW Hongqi", "一汽马自达": "FAW Mazda",
    "华晨宝马": "Brilliance BMW", "华晨金杯": "Brilliance Jinbei", "长安汽车": "Changan",
    "长安福特": "Changan Ford", "长安马自达": "Changan Mazda", "长城汽车": "Great Wall",
    "江淮汽车": "JAC", "江淮瑞风": "JAC Refine", "奇瑞汽车": "Chery", "吉利汽车": "Geely",
    "上海通用": "Shanghai GM", "上海大众": "Shanghai Volkswagen", "南京依维柯": "Nanjing Iveco",
    "郑州日产": "Zhengzhou Nissan", "江铃汽车": "JMC", "庆铃汽车": "Qingling",
    "斯柯达": "Skoda", "雪佛兰": "Chevrolet",
    "凯迪拉克": "Cadillac", "雷克萨斯": "Lexus", "英菲尼迪": "Infiniti", "玛莎拉蒂": "Maserati",
    "兰博基尼": "Lamborghini", "劳斯莱斯": "Rolls-Royce", "阿斯顿马丁": "Aston Martin",
    "阿尔法罗密欧": "Alfa Romeo", "路虎": "Land Rover", "捷豹": "Jaguar", "保时捷": "Porsche",
    "沃尔沃": "Volvo", "萨博": "Saab", "欧宝": "Opel", "雷诺": "Renault", "标致": "Peugeot",
    "雪铁龙": "Citroen", "菲亚特": "Fiat", "铃木": "Suzuki", "斯巴鲁": "Subaru",
    "三菱": "Mitsubishi", "马自达": "Mazda", "日产": "Nissan", "本田": "Honda",
    "丰田": "Toyota", "现代起亚": "Hyundai/Kia", "现代": "Hyundai",
    "起亚": "Kia", "大宇": "Daewoo", "双龙": "SsangYong", "大发": "Daihatsu",
    "五十铃": "Isuzu", "日野": "Hino", "宝马": "BMW", "奥迪": "Audi", "奔驰": "Mercedes-Benz",
    "大众": "Volkswagen", "别克": "Buick", "福特": "Ford", "克莱斯勒": "Chrysler",
    "道奇": "Dodge", "吉普": "Jeep", "悍马": "Hummer", "林肯": "Lincoln", "水星": "Mercury",
    "特斯拉": "Tesla", "罗孚": "Rover", "迷你": "Mini", "西亚特": "SEAT", "达契亚": "Dacia",
    "拉达": "Lada", "依维柯": "Iveco", "斯堪尼亚": "Scania",
    "比亚迪": "BYD", "奇瑞": "Chery", "瑞琪": "Riich", "开瑞": "Karry", "凯翼": "Cowin",
    "吉利": "Geely", "帝豪": "Emgrand", "全球鹰": "Gleagle", "英伦": "Englon", "领克": "Lynk & Co",
    "长城": "Great Wall", "哈弗": "Haval", "哈佛": "Haval", "魏派": "WEY", "坦克": "Tank",
    "欧拉": "ORA", "长安": "Changan", "江淮": "JAC", "江铃": "JMC", "五菱": "Wuling",
    "宝骏": "Baojun", "荣威": "Roewe", "名爵": "MG", "众泰": "Zotye", "力帆": "Lifan",
    "华泰": "Hawtai", "东南": "Soueast", "海马": "Haima", "中华": "Zhonghua", "金杯": "Jinbei",
    "风行": "Forthing", "东风": "Dongfeng", "一汽": "FAW", "上汽": "SAIC", "北汽": "BAIC",
    "广汽": "GAC", "华晨": "Brilliance", "福田": "Foton", "陆风": "Landwind", "猎豹": "Leopaard",
    "纳智捷": "Luxgen", "启辰": "Venucia", "理念": "Everus", "思铭": "Ciimo", "传祺": "Trumpchi",
    "大通": "Maxus", "上汽大通": "Maxus", "野马": "Yema", "潍柴": "Weichai", "陕汽": "Shacman",
    "中国重汽": "Sinotruk", "红岩": "Hongyan", "解放": "Jiefang",
    "知豆": "Zhidou", "威马": "WM Motor", "蔚来": "NIO", "小鹏": "Xpeng", "理想": "Li Auto",
    "腾势": "Denza", "观致": "Qoros", "宝沃": "Borgward", "比速": "Bisu", "斯威": "SWM",
    "汉腾": "Hanteng", "君马": "Junma", "云度": "Yudo",
    "威利": "WEILI", "加加": "JIAJIA", "德尔福": "Delphi", "博世": "Bosch", "电装": "Denso",
    "联合电子": "UAES", "马瑞利": "Magneti Marelli", "西门子": "Siemens", "摩托罗拉": "Motorola",
    "德尔福款": "Delphi type", "博世款": "Bosch type", "联电款": "UAES type",
}

MODEL = {
    "兰德酷路泽": "Land Cruiser", "普拉多": "Prado", "凯美瑞": "Camry", "卡罗拉": "Corolla",
    "雅力士": "Yaris", "威驰": "Vios", "花冠": "Corolla EX", "汉兰达": "Highlander",
    "逸致": "Verso", "普锐斯": "Prius", "锐志": "Reiz", "皇冠": "Crown", "特锐": "Terios",
    "帕萨特": "Passat", "迈腾": "Magotan", "速腾": "Sagitar", "宝来": "Bora", "朗逸": "Lavida",
    "桑塔纳": "Santana", "捷达": "Jetta", "高尔夫": "Golf", "途观": "Tiguan", "途安": "Touran",
    "途锐": "Touareg", "辉腾": "Phaeton", "波罗劲情": "Polo", "波罗": "Polo", "晶锐": "Fabia",
    "明锐": "Octavia", "昊锐": "Superb", "速派": "Superb", "野帝": "Yeti", "甲壳虫": "Beetle",
    "开迪": "Caddy", "凌渡": "Lamando", "蔚领": "C-Trek", "嘉旅": "Sportsvan", "迈特威": "Multivan",
    "凯越": "Excelle", "君威": "Regal", "君越": "LaCrosse", "英朗": "Excelle GT", "威朗": "Verano",
    "科鲁兹": "Cruze", "迈锐宝": "Malibu", "赛欧": "Sail", "乐风": "Lova", "乐骋": "Aveo",
    "景程": "Epica", "爱唯欧": "Aveo", "创酷": "Trax", "昂科拉": "Encore", "昂科威": "Envision",
    "昂科雷": "Enclave", "林荫大道": "Park Avenue", "赛威": "SLS",
    "蒙迪欧": "Mondeo", "福克斯": "Focus", "嘉年华": "Fiesta", "致胜": "Mondeo", "翼虎": "Kuga",
    "锐界": "Edge", "翼博": "EcoSport", "全顺": "Transit", "经典全顺": "Transit",
    "索纳塔": "Sonata", "伊兰特": "Elantra", "途胜": "Tucson", "雅绅特": "Accent", "名驭": "Sonata",
    "领动": "Elantra", "悦动": "Elantra", "瑞纳": "Verna", "胜达": "Santa Fe",
    "智跑": "Sportage", "狮跑": "Sportage", "赛拉图": "Cerato", "福瑞迪": "Forte",
    "轩逸": "Sylphy", "天籁": "Teana", "阳光": "Sunny", "骐达": "Tiida", "颐达": "Tiida",
    "逍客": "Qashqai", "奇骏": "X-Trail", "蓝鸟": "Bluebird", "骊威": "Livina", "楼兰": "Murano",
    "雅阁": "Accord", "思域": "Civic", "飞度": "Fit", "锋范": "City", "凌派": "Crider",
    "奥德赛": "Odyssey", "歌诗图": "Crosstour", "思铂睿": "Spirior", "缤智": "Vezel",
    "马自达6": "Mazda 6", "马自达3": "Mazda 3", "马自达8": "Mazda 8", "马自达2": "Mazda 2",
    "昂克赛拉": "Axela", "阿特兹": "Atenza", "睿翼": "Mazda 6", "星骋": "Mazda 3",
    "瑞虎": "Tiggo", "风云": "Fulwin", "旗云": "Cowin", "东方之子": "Oriental Son",
    "艾瑞泽": "Arrizo", "威麟": "Rely", "威志": "Weizhi",
    "远景": "Vision", "博瑞": "Borui", "博越": "Boyue", "金刚": "King Kong", "海景": "SC7",
    "熊猫": "Panda", "自由舰": "Free Cruiser", "豪情": "Haoqing", "美日": "Merrie",
    "荣光": "Rongguang", "宏光": "Hongguang", "之光": "Zhiguang", "鸿途": "Hongtu",
    "乐驰": "Spark", "征程": "Zhengcheng", "长安之星": "Changan Star", "奔奔": "Benben",
    "悦翔": "Alsvin", "逸动": "Eado", "欧诺": "Ono", "欧尚": "Oushan", "睿骋": "Raeton",
    "风骏": "Wingle", "炫丽": "Florid", "腾翼": "Voleex", "精灵": "Peri", "酷熊": "Coolbear",
    "嘉誉": "Cowin", "威霆": "Vito", "唯雅诺": "Viano", "凌特": "Sprinter",
    "凯旋": "C-Triomphe", "世嘉": "C-Quatre", "爱丽舍": "Elysee", "毕加索": "Picasso",
    "自由光": "Cherokee", "指南者": "Compass", "大切诺基": "Grand Cherokee", "牧马人": "Wrangler",
    "挑战者": "Challenger", "凯领": "Caravan", "大捷龙": "Grand Voyager", "酷威": "Journey",
    "锐欧": "Rio", "凯绅": "K5",
    "揽胜极光": "Range Rover Evoque", "揽胜运动": "Range Rover Sport", "揽胜星脉": "Range Rover Velar",
    "揽胜": "Range Rover", "发现神行": "Discovery Sport", "发现": "Discovery", "卫士": "Defender",
    "科帕奇": "Captiva", "科雷傲": "Koleos", "科雷嘉": "Kadjar", "科迈罗": "Camaro",
    "桑塔纳2000": "Santana 2000", "桑塔纳3000": "Santana 3000", "桑塔纳志俊": "Santana Vista",
    "帕萨特领驭": "Passat Lingyu", "新领驭": "New Lingyu", "桑塔纳浩纳": "Santana Gran Santana",
    "福美来": "Familia", "普力马": "Premacy", "海福星": "Haima 3", "欢动": "Haima 3",
    "丘比特": "Haima 2", "骑士": "S7", "福仕达": "Fstar", "爱尚": "Aishang",
    "悦悦": "Yueyue", "同悦": "Tongyue", "和悦": "Heyue", "瑞风": "Refine", "瑞鹰": "Rein",
    "星锐": "Sunray", "帅铃": "Shuailing", "骏铃": "Junling", "康铃": "Kangling",
    "奥铃": "Aoling", "欧马可": "Aumark", "风景": "View", "蒙派克": "MP-X",
    "萨普": "Sap", "拓陆者": "Tunland", "驭胜": "Yusheng", "域虎": "Yuhu", "宝典": "Baodian",
    "特顺": "Transit", "凯运": "Kaiyun", "顺达": "Shunda",
    "威旺": "Weiwang", "幻速": "Huansu", "绅宝": "Senova", "勇士": "Warrior", "战旗": "Zhanqi",
    "角斗士": "Raider", "陆霸": "Luba", "路霸": "Luba",
    "猎鹰": "Falcon", "御风": "Yufeng", "御轩": "Yuxuan", "嘉华": "Carnival", "佳乐": "Carens",
    "索兰托": "Sorento", "霸锐": "Borrego", "欧菲莱斯": "Opirus",
    "爱腾": "Actyon", "享御": "Kyron", "雷斯特": "Rexton", "柯兰多": "Korando",
    "主席": "Chairman", "路帝": "Rodius",
    "玛驰": "March", "俊风": "Junfeng",
    "赛马": "Saima", "赛豹": "Saibao", "路宝": "Lobo", "中意": "Zhongyi",
    "民意": "Minyi", "小霸王": "Xiaobawang", "威虎": "Weihu", "傲龙": "Aolong",
    "猎豹奇兵": "Leopaard Qibing", "飞腾": "Feiteng", "黑金刚": "Heijingang",
    "斯帕可": "Spark", "景逸": "Jingyi", "菱智": "Lingzhi", "菱悦": "Lingyue", "菱绅": "Soveran",
    "菱帅": "Lioncel", "蓝瑟": "Lancer", "翼神": "Lancer EX", "戈蓝": "Galant", "欧蓝德": "Outlander",
    "劲炫": "ASX", "帕杰罗": "Pajero", "劲畅": "Montero Sport", "得利卡": "Delica",
    "风迪思": "Fortis", "君阁": "Zinger",
}

DESC = {
    "不带阀": "without valve", "带阀": "with valve", "不带管": "without pipe", "带管": "with pipe",
    "手动挡": "MT", "自动挡": "AT", "自动波": "AT", "手动波": "MT", "手动": "MT", "自动": "AT",
    "电喷": "EFI", "化油器": "carburettor", "柴油": "diesel", "汽油": "petrol",
    "国六": "Euro 6", "国五": "Euro 5", "国四": "Euro 4", "国三": "Euro 3",
    "前左": "Front LH", "前右": "Front RH", "后左": "Rear LH", "后右": "Rear RH",
    "左前": "Front LH", "右前": "Front RH", "左后": "Rear LH", "右后": "Rear RH",
    "前后": "front rear", "左右": "LH/RH", "进口": "Imported", "国产": "Domestic",
    "原厂": "OEM", "副厂": "aftermarket", "拆车": "used", "全新": "new", "新款": "new model",
    "老款": "old model", "旧款": "old model", "改款": "facelift", "经典": "classic",
    "至今": "present", "现在": "present", "目前": "present", "以后": "onwards",
    "发动机": "engine", "排量": "displacement", "口径": "diameter", "孔距": "hole pitch",
    "安装孔距": "mounting hole pitch", "进气孔径": "inlet diameter", "插头": "connector",
    "直头": "straight connector", "弯头": "bent connector", "三线": "3-wire",
    "四线": "4-wire", "两线": "2-wire", "单线": "1-wire", "带线": "with wire",
    "不带线": "without wire", "长线": "long wire", "短线": "short wire", "主泵": "main pump",
    "副泵": "secondary pump", "半总成": "semi-assembly", "总成": "assembly",
    "驱动": "drive", "传感": "sensing", "总线": "CAN bus", "单点": "single-point",
    "多点": "multi-point", "汽缸": "cylinder", "缸": "cyl", "排": "series",
    "不分": "", "同款": "same type", "通用": "universal", "专用": "dedicated",
    "两驱": "2WD", "四驱": "4WD", "四轮": "4-wheel", "前轮": "front wheel", "后轮": "rear wheel",
    "全车件": "", "全车": "", "皮卡": "pickup", "面包车": "van", "货车": "truck",
    "客车": "bus", "微面": "microvan", "旅行车": "wagon",
    "电动": "electric", "轴头": "shaft head", "两厢": "hatchback", "三厢": "sedan",
    "涡轮增压": "turbo", "自然吸气": "naturally aspirated", "分电器": "distributor",
    "高压线": "ignition wire", "火花塞": "spark plug", "线圈": "coil", "传感器": "sensor",
    "电磁阀": "solenoid valve", "节气门": "throttle body", "喷油嘴": "injector",
    "油泵": "fuel pump", "水泵": "water pump", "壳体": "housing", "支架": "bracket",
    "螺丝": "screw", "孔位": "mounting holes", "带涡轮": "turbo", "不带涡轮": "non-turbo",
    # 单字兜底：中文里出现最多的几个，翻出来比直接删可读性好
    "款": "", "价": "", "新": "new", "氧": "O2", "后": "rear", "前": "front",
    "代": "gen", "系": "series", "国": "Euro", "级": "class", "年": "year",
    "号": "no.", "型": "type", "机": "engine", "车": "car", "位": "",
    "版": "edition", "第": "gen ",
    "胜": "", "揽": "", "科": "", "利": "", "达": "", "现": "", "行": "",
    "星": "", "瑞": "", "风": "", "光": "", "海": "", "桑": "", "尼": "", "一": "",
    "二": "", "三": "", "斯": "",
}

DICT = {}
for d in (BRAND, MODEL, DESC):
    DICT.update(d)
_KEYS = sorted(DICT, key=len, reverse=True)
_RE = re.compile("|".join(re.escape(k) for k in _KEYS))


def _tidy(s):
    s = re.sub(r"[\\/]+", " / ", s)
    s = re.sub(r"[、；;，]+", ", ", s)
    s = re.sub(r"\s*,\s*", ", ", s)
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"(,\s*){2,}", ", ", s)
    s = re.sub(r"\s*/\s*/\s*", " / ", s)
    s = re.sub(r"[:：]\s*[:：]+", ":", s)
    s = re.sub(r"\(\s*\)", " ", s)
    s = re.sub(r"\s{2,}", " ", s)
    s = re.sub(r"^[\s,;/\-:]+|[\s,;/\-:]+$", "", s)
    return s.strip()


def translate(text):
    """中文 → 英文。返回 (新值, 是否还有中文, 剩余中文片段列表)"""
    if not text or not CJK.search(text):
        return text or "", False, []
    out = _RE.sub(lambda m: " " + DICT[m.group(0)] + " ", text)
    left = CJK.findall(out)
    out = re.sub(r"[\u4e00-\u9fa5]+", " ", out)
    return _tidy(out), bool(left), left


def _score(it):
    """信息完整度打分：用来在重复 OE 里挑最全的一条。"""
    s = 0
    if it.get("p"):
        s += 4
    if (it.get("a") or "").strip():
        s += 3
    if (it.get("r") or "").strip():
        s += 2
    s += min(len(it.get("x") or []), 6)
    if (it.get("b") or "").strip():
        s += 1
    s += min(len(it.get("a") or "") // 60, 3)
    return s


def clean_payload(payload, log=print):
    """清洗 + 去重。原地改 payload，返回统计。"""
    items = payload.get("items") or []
    stats = {"brand": 0, "fit": 0, "unresolved": {}, "unspecified": 0,
             "fit_empty": 0, "dup_removed": 0, "dedupe": [], "mapping": {}}
    for it in items:
        orig = {}

        b = it.get("b") or ""
        nb, left, _ = translate(b)
        if nb != b:
            orig["b"] = b
            stats["brand"] += 1
        if b.strip() and not nb.strip():
            nb = "Unspecified"
            stats["unspecified"] += 1
        it["b"] = nb.strip()

        a = it.get("a") or ""
        na, _left, leftover = translate(a)
        if na != a:
            orig["a"] = a
            stats["fit"] += 1
        for k in leftover:
            stats["unresolved"][k] = stats["unresolved"].get(k, 0) + 1
        if a.strip() and not na.strip():
            stats["fit_empty"] += 1
        it["a"] = na.strip()

        for k in ("m", "oe"):
            v = it.get(k) or ""
            if CJK.search(v):
                orig[k] = v
                it[k] = _tidy(re.sub(r"[\u4e00-\u9fa5]+", " ", v))
        xs = it.get("x") or []
        if any(CJK.search(x or "") for x in xs):
            orig["x"] = list(xs)
            it["x"] = [x for x in (_tidy(re.sub(r"[\u4e00-\u9fa5]+", " ", y or "")) for y in xs) if x]
        if orig:
            stats["mapping"][str(it["i"])] = orig

    # OE 去重：同 OE（忽略大小写和分隔符）只留信息最全的一条
    def oekey(v):
        return re.sub(r"[^0-9A-Z]", "", (v or "").upper())

    best = {}
    for it in items:
        k = oekey(it.get("oe"))
        if len(k) < 4:
            continue
        cur = best.get(k)
        if cur is None or _score(it) > _score(cur):
            best[k] = it
    keep_ids = set(id(x) for x in best.values())
    out = []
    for it in items:
        k = oekey(it.get("oe"))
        if len(k) >= 4 and id(it) not in keep_ids:
            stats["dedupe"].append({"oe": it.get("oe"), "drop": it.get("m"),
                                    "keep": best[k].get("m")})
            stats["dup_removed"] += 1
            continue
        out.append(it)
    payload["items"] = out
    payload["_clean"] = CLEAN_VER
    payload["_clean_stats"] = {k: v for k, v in stats.items() if k != "mapping"}
    log("  清洗：品牌 %d 条、适配 %d 条、归 Unspecified %d、适配洗空 %d；OE 去重 -%d 条 → %d 条"
        % (stats["brand"], stats["fit"], stats["unspecified"], stats["fit_empty"],
           stats["dup_removed"], len(out)))
    return stats


def write_map(stats):
    os.makedirs(MAP_DIR, exist_ok=True)
    p = os.path.join(MAP_DIR, "clean_map.json")
    old = {}
    if os.path.exists(p):
        try:
            old = json.load(io.open(p, encoding="utf-8"))
        except Exception:
            old = {}
    old.update(stats["mapping"])
    io.open(p, "w", encoding="utf-8").write(json.dumps(old, ensure_ascii=False, indent=1))
    top = sorted(stats["unresolved"].items(), key=lambda x: -x[1])[:20]
    io.open(os.path.join(MAP_DIR, "unresolved_top20.txt"), "w", encoding="utf-8").write(
        "清洗后仍然无法处理的中文片段（按出现次数，前 20）\n" +
        "\n".join("%-14s %d" % (k, v) for k, v in top) + "\n")
    io.open(os.path.join(MAP_DIR, "dedupe_oe.csv"), "w", encoding="utf-8").write(
        "重复OE,丢掉,保留\n" + "\n".join('%s,%s,%s' % (d["oe"], d["drop"], d["keep"])
                                       for d in stats["dedupe"]) + "\n")
    return p, top


def write_data_js(payload):
    if os.path.exists(DATA_JS):
        bak = DATA_JS + ".bak"
        try:
            if not os.path.exists(bak):
                with io.open(DATA_JS, "rb") as f:
                    io.open(bak, "wb").write(f.read())
        except Exception:
            pass
    with io.open(DATA_JS, "w", encoding="utf-8", newline="\n") as f:
        f.write("/* 型号查询站数据文件 —— 由 build.py / data_prep.py 自动生成，别手改。 */\n")
        f.write("/* 字段：i=编号 c=品类 m=型号 n=品名 b=品牌 oe=主OE号 x=交叉号数组 a=适配车型 r=备注 p=大图 t=缩略图 s=slug */\n")
        f.write("window.SITE_DATA=")
        f.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
        f.write(";\n")


def write_chunks(payload):
    """拆成 data/meta.js + data/chunk-XX.js，首页只引第 0 片。"""
    items = payload.get("items") or []
    for fn in os.listdir(DATA_DIR):
        if fn.startswith("chunk-") and fn.endswith(".js"):
            try:
                os.remove(os.path.join(DATA_DIR, fn))
            except OSError:
                pass
    n = max(1, (len(items) + CHUNK - 1) // CHUNK)
    for k in range(n):
        part = items[k * CHUNK:(k + 1) * CHUNK]
        body = "(window.YMY_CHUNKS=window.YMY_CHUNKS||{})[%d]=%s;\n" % (
            k, json.dumps(part, ensure_ascii=False, separators=(",", ":")))
        io.open(os.path.join(DATA_DIR, "chunk-%02d.js" % k), "w", encoding="utf-8", newline="\n").write(body)
    meta = {
        "generated": payload.get("generated") or "",
        "company": payload.get("company") or "",
        "total": len(items),
        "photos": sum(1 for it in items if it.get("p")),
        "size": CHUNK,
        "chunks": n,
        "cats": payload.get("cats") or [],
        "clean": CLEAN_VER,
    }
    io.open(os.path.join(DATA_DIR, "meta.js"), "w", encoding="utf-8", newline="\n").write(
        "window.YMY_META=%s;\n" % json.dumps(meta, ensure_ascii=False, separators=(",", ":")))
    sizes = [os.path.getsize(os.path.join(DATA_DIR, "chunk-%02d.js" % k)) for k in range(n)]
    return {"chunks": n, "first_kb": round(sizes[0] / 1024.0, 1),
            "total_kb": round(sum(sizes) / 1024.0, 1)}


def load_payload(path=DATA_JS):
    raw = io.open(path, encoding="utf-8").read()
    key = "window.SITE_DATA="
    i = raw.find(key)
    if i < 0:
        raise SystemExit("data.js 格式不对：没有 window.SITE_DATA=")
    payload, _ = json.JSONDecoder().raw_decode(raw[i + len(key):])
    return payload


def prepare(write=True, log=print):
    """读 data.js → 清洗去重 → 写回 + 拆包。返回 (payload, stats)。"""
    payload = load_payload()
    if payload.get("_clean") != CLEAN_VER:
        stats = clean_payload(payload, log=log)
        if write:
            write_map(stats)
            write_data_js(payload)
        info = write_chunks(payload) if write else {}
    else:
        stats = {"mapping": {}, "unresolved": {}, "dedupe": [], "brand": 0, "fit": 0,
                 "unspecified": 0, "fit_empty": 0, "dup_removed": 0}
        info = write_chunks(payload) if write else {}
        log("  数据已清洗过（v%d），直接拆包" % CLEAN_VER)
    if info:
        log("  拆包：%d 片 · 第 0 片 %.1f KB · 合计 %.1f KB" % (
            info["chunks"], info["first_kb"], info["total_kb"]))
    return payload, stats


if __name__ == "__main__":
    t0 = time.time()
    prepare(log=lambda m: print(m, flush=True))
    print("  用时 %.1f 秒" % (time.time() - t0))
