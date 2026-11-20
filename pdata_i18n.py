# -*- coding: utf-8 -*-
"""
产品数据译名表：适配品牌 / 适配车型 / 备注
============================================
界面文案在 assets/i18n.js 的 T 字典里；产品数据（品牌名、车型里的品牌和方位词、
备注里的固定说法）在这张表里，页面渲染后由 I18N.pd() 逐词替换。

规则（2026-11-20 老板定的口径）：
  1. 有官方译名的用官方译名：Changan → 长安、Toyota → 丰田、BMW → 宝马 …
  2. 查不到官方译名的**保留英文**——这是 fallback，不是漏做。
     西/葡/法/印尼四语因此天然不用写：品牌名在当地也写英文原名。
  3. 车系名（Star / Sunshine / Accord …）只收「有官方中文名」的那批，其余留英文。
  4. 型号代码、OE 号、包装号（YM03-0006、WL10-BC001C）永远不动。

用法：
    python pdata_i18n.py            自检 + 打印统计
    python pdata_i18n.py --write    把表写进 assets/i18n.js 的 PDATA 段
"""

import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
I18N_JS = os.path.join(HERE, "assets", "i18n.js")

# 列顺序：与 i18n.js 的 IDX 一致（en 是原文，不占列）
LANGS = ("zh", "ar", "ru", "fr", "es", "pt", "id", "fa")

# ---------------------------------------------------------------- 品牌
# 规范名（= brands.py 的 BRANDS 键，页面 data-pd 里也用它）→ 8 语种译名
# 顺序：zh, ar, ru, fr, es, pt, id, fa；空串 = 用英文原文
BRANDS = {
    # ---- 日系
    "Toyota":            ("丰田", "تويوتا", "Тойота", "", "", "", "", "تویوتا"),
    "Lexus":             ("雷克萨斯", "لكزس", "Лексус", "", "", "", "", "لکسوس"),
    "Honda":             ("本田", "هوندا", "Хонда", "", "", "", "", "هوندا"),
    "Acura":             ("讴歌", "أكيورا", "Акура", "", "", "", "", "آکورا"),
    "Nissan":            ("日产", "نيسان", "Ниссан", "", "", "", "", "نیسان"),
    "Infiniti":          ("英菲尼迪", "إنفينيتي", "Инфинити", "", "", "", "", "اینفینیتی"),
    "Mazda":             ("马自达", "مازدا", "Мазда", "", "", "", "", "مزدا"),
    "Mitsubishi":        ("三菱", "ميتسوبيشي", "Мицубиси", "", "", "", "", "میتسوبیشی"),
    "Subaru":            ("斯巴鲁", "سوبارو", "Субару", "", "", "", "", "سوبارو"),
    "Suzuki":            ("铃木", "سوزوكي", "Сузуки", "", "", "", "", "سوزوکی"),
    "Isuzu":             ("五十铃", "إيسوزو", "Исузу", "", "", "", "", "ایسوزو"),
    "Daihatsu":          ("大发", "ديهاتسو", "Дайхацу", "", "", "", "", "دایهاتسو"),
    # ---- 韩系
    "Hyundai":           ("现代", "هيونداي", "Хендай", "", "", "", "", "هیوندای"),
    "Kia":               ("起亚", "كيا", "Киа", "", "", "", "", "کیا"),
    "Genesis":           ("捷尼赛思", "جينيسيس", "Дженезис", "", "", "", "", "جنسیس"),
    "Daewoo":            ("大宇", "دايو", "Дэу", "", "", "", "", "دوو"),
    "SsangYong":         ("双龙", "سانج يونج", "СсангЙонг", "", "", "", "", "سانگیونگ"),
    # ---- 美系
    "Chevrolet":         ("雪佛兰", "شيفروليه", "Шевроле", "", "", "", "", "شورولت"),
    "Buick":             ("别克", "بويك", "Бьюик", "", "", "", "", "بیوک"),
    "Cadillac":          ("凯迪拉克", "كاديلاك", "Кадиллак", "", "", "", "", "کادیلاک"),
    "GMC":               ("GMC", "جي إم سي", "", "", "", "", "", "جی‌ام‌سی"),
    "Ford":              ("福特", "فورد", "Форд", "", "", "", "", "فورد"),
    "Lincoln":           ("林肯", "لينكولن", "Линкольн", "", "", "", "", "لینکلن"),
    "Chrysler":          ("克莱斯勒", "كرايسلر", "Крайслер", "", "", "", "", "کرایسلر"),
    "Dodge":             ("道奇", "دودج", "Додж", "", "", "", "", "دوج"),
    "Jeep":              ("吉普", "جيب", "Джип", "", "", "", "", "جیپ"),
    "Ram":               ("公羊", "رام", "Рам", "", "", "", "", "رم"),
    "Tesla":             ("特斯拉", "تسلا", "Тесла", "", "", "", "", "تسلا"),
    # ---- 德系
    "Volkswagen":        ("大众", "فولكس فاجن", "Фольксваген", "", "", "", "", "فولکس‌واگن"),
    "Audi":              ("奥迪", "أودي", "Ауди", "", "", "", "", "آئودی"),
    "BMW":               ("宝马", "بي إم دبليو", "БМВ", "", "", "", "", "بی‌ام‌و"),
    "Mini":              ("迷你", "ميني", "Мини", "", "", "", "", "مینی"),
    "Mercedes-Benz":     ("奔驰", "مرسيدس", "Мерседес", "", "", "", "", "مرسدس‌بنز"),
    "Smart":             ("斯玛特", "سمارت", "Смарт", "", "", "", "", "اسمارت"),
    "Porsche":           ("保时捷", "بورش", "Порше", "", "", "", "", "پورشه"),
    # ---- 法系
    "Peugeot":           ("标致", "بيجو", "Пежо", "", "", "", "", "پژو"),
    "Citroen":           ("雪铁龙", "سيتروين", "Ситроен", "", "", "", "", "سیتروئن"),
    "Renault":           ("雷诺", "رينو", "Рено", "", "", "", "", "رنو"),
    "Dacia":             ("达契亚", "داسيا", "Дачия", "", "", "", "", "داچیا"),
    # ---- 其他欧系
    "Opel":              ("欧宝", "أوبل", "Опель", "", "", "", "", "اوپل"),
    "Skoda":             ("斯柯达", "سكودا", "Шкода", "", "", "", "", "اشکودا"),
    "Seat":              ("西雅特", "سيات", "Сеат", "", "", "", "", "سیت"),
    "Volvo":             ("沃尔沃", "فولفو", "Вольво", "", "", "", "", "ولوو"),
    "Saab":              ("萨博", "ساب", "Сааб", "", "", "", "", "ساب"),
    "Land Rover":        ("路虎", "لاند روفر", "Ленд Ровер", "", "", "", "", "لندروور"),
    "Jaguar":            ("捷豹", "جاكوار", "Ягуар", "", "", "", "", "جگوار"),
    "Fiat":              ("菲亚特", "فيات", "Фиат", "", "", "", "", "فیات"),
    "Alfa Romeo":        ("阿尔法·罗密欧", "ألفا روميو", "Альфа Ромео", "", "", "", "", "آلفارومئو"),
    "Lancia":            ("蓝旗亚", "لانشيا", "Лянча", "", "", "", "", "لانچیا"),
    "Iveco":             ("依维柯", "إيفيكو", "Ивеко", "", "", "", "", "ایوکو"),
    "Maserati":          ("玛莎拉蒂", "مازيراتي", "Мазерати", "", "", "", "", "مازراتی"),
    "Borgward":          ("宝沃", "بورجوارد", "Боргвард", "", "", "", "", "بورگوارت"),
    # ---- 中国品牌
    "Chery":             ("奇瑞", "شيري", "Чери", "", "", "", "", "چری"),
    "Geely":             ("吉利", "جيلي", "Джили", "", "", "", "", "جیلی"),
    "BYD":               ("比亚迪", "بي واي دي", "БИД", "", "", "", "", "بی‌وای‌دی"),
    "Great Wall":        ("长城", "جريت وول", "Грейт Волл", "", "", "", "", "گریت وال"),
    "Haval":             ("哈弗", "هافال", "Хавал", "", "", "", "", "هاول"),
    "Changan":           ("长安", "شانجان", "Чанган", "", "", "", "", "چانگان"),
    "BAIC":              ("北汽", "بايك", "БАИК", "", "", "", "", "بایک"),
    "Dongfeng":          ("东风", "دونغفنغ", "Дунфэн", "", "", "", "", "دونگ‌فنگ"),
    "FAW":               ("一汽", "فاو", "ФАВ", "", "", "", "", "فاو"),
    "JAC":               ("江淮", "جاك", "Джак", "", "", "", "", "جک"),
    "Lifan":             ("力帆", "ليفان", "Лифан", "", "", "", "", "لیفان"),
    "MG":                ("名爵", "إم جي", "МГ", "", "", "", "", "ام‌جی"),
    "Roewe":             ("荣威", "", "Роуи", "", "", "", "", "رووی"),
    "Wuling":            ("五菱", "وولينغ", "Вулинг", "", "", "", "", "وولینگ"),
    "Baojun":            ("宝骏", "باوجون", "Баоцзюнь", "", "", "", "", "بائوجون"),
    "Jinbei":            ("金杯", "جينبي", "Цзиньбэй", "", "", "", "", "جین‌بی"),
    "Forthing":          ("风行", "فورثينغ", "", "", "", "", "", "فورسینگ"),
    "Foton":             ("福田", "فوتون", "Фотон", "", "", "", "", "فوتون"),
    "Soueast":           ("东南", "ساوإيست", "", "", "", "", "", "سواست"),
    "JMC":               ("江铃", "", "", "", "", "", "", ""),
    "Maxus":             ("大通", "ماكسوس", "Максус", "", "", "", "", "ماکسوس"),
    "Haima":             ("海马", "هايما", "Хайма", "", "", "", "", "هایما"),
    "Zotye":             ("众泰", "زوتي", "", "", "", "", "", "زوتی"),
    "Brilliance":        ("华晨", "بريليانس", "", "", "", "", "", "بریلیانس"),
    "Zhonghua":          ("中华", "", "", "", "", "", "", ""),
    "Trumpchi":          ("传祺", "", "", "", "", "", "", ""),
    "Landwind":          ("陆风", "", "", "", "", "", "", ""),
    "Sokon":             ("小康", "", "", "", "", "", "", ""),
    "Oushan":            ("欧尚", "", "", "", "", "", "", ""),
    "Venucia":           ("启辰", "", "", "", "", "", "", ""),
    "WEY":               ("魏牌", "", "", "", "", "", "", ""),
    "Exeed":             ("星途", "إكسيد", "Эксид", "", "", "", "", "اکسید"),
    "DFSK":              ("东风小康", "", "", "", "", "", "", ""),
    "Beijing":           ("北京", "", "", "", "", "", "", ""),
    "Besturn":           ("奔腾", "", "", "", "", "", "", ""),
    "Jetour":            ("捷途", "جيتور", "Джетур", "", "", "", "", "جتور"),
    "Hanteng":           ("汉腾", "", "", "", "", "", "", ""),
    "SWM":               ("斯威", "", "", "", "", "", "", ""),
    "Lynk":              ("领克", "", "", "", "", "", "", ""),
    "NETA":              ("哪吒", "", "", "", "", "", "", ""),
    "Luxgen":            ("纳智捷", "", "", "", "", "", "", ""),
    "Hawtai":            ("华泰", "", "", "", "", "", "", ""),
    "Huanghai":          ("黄海", "", "", "", "", "", "", ""),
    "Karry":             ("开瑞", "", "", "", "", "", "", ""),
    "Senova":            ("绅宝", "", "", "", "", "", "", ""),
    "Fengguang":         ("风光", "", "", "", "", "", "", ""),
    "Leopaard":          ("猎豹", "", "", "", "", "", "", ""),
    "Weiwang":           ("威旺", "", "", "", "", "", "", ""),
    "Changhe":           ("昌河", "", "", "", "", "", "", ""),
    "Hafei":             ("哈飞", "", "", "", "", "", "", ""),
    "Tianye":            ("田野", "", "", "", "", "", "", ""),
    # ---- 南亚 / 东南亚 / 俄系
    "Mahindra":          ("马恒达", "ماهيندرا", "Махиндра", "", "", "", "", "ماهیندرا"),
    "Tata":              ("塔塔", "تاتا", "Тата", "", "", "", "", "تاتا"),
    "Maruti":            ("马鲁蒂", "ماروتي", "Марути", "", "", "", "", "ماروتی"),
    "Proton":            ("宝腾", "بروتون", "Протон", "", "", "", "", "پروتون"),
    "UAZ":               ("乌阿斯", "أواز", "УАЗ", "", "", "", "", "اوز"),
    "Lada":              ("拉达", "لادا", "Лада", "", "", "", "", "لادا"),
    # ---- 集团 / 合资厂（适配文本里常直接写集团名）
    "SAIC":              ("上汽", "سايك", "", "", "", "", "", "سایک"),
    "GAC":               ("广汽", "", "", "", "", "", "", ""),
    "GM":                ("通用", "جي إم", "", "", "", "", "", "جی‌ام"),
}

# ---------------------------------------------------------------- 方位 / 结构词
# 适配文本里反复出现的方位词和描述词，按「长的先匹配」规则替换
TERMS = {
    "Front":      ("前", "أمامي", "Передний", "Avant", "Delantero", "Dianteiro", "Depan", "جلو"),
    "Rear":       ("后", "خلفي", "Задний", "Arrière", "Trasero", "Traseiro", "Belakang", "عقب"),
    "Left":       ("左", "يسار", "Левый", "Gauche", "Izquierdo", "Esquerdo", "Kiri", "چپ"),
    "Right":      ("右", "يمين", "Правый", "Droit", "Derecho", "Direito", "Kanan", "راست"),
    "LH":         ("左", "يسار", "Лев.", "G", "Izq.", "Esq.", "Kiri", "چپ"),
    "RH":         ("右", "يمين", "Прав.", "D", "Der.", "Dir.", "Kanan", "راست"),
    "LH/RH":      ("左右", "يمين/يسار", "Лев./прав.", "G/D", "Izq./Der.", "Esq./Dir.", "Kiri/kanan", "چپ/راست"),
    "Upper":      ("上", "علوي", "Верхний", "Supérieur", "Superior", "Superior", "Atas", "بالا"),
    "Lower":      ("下", "سفلي", "Нижний", "Inférieur", "Inferior", "Inferior", "Bawah", "پایین"),
    "Inner":      ("内", "داخلي", "Внутренний", "Intérieur", "Interior", "Interno", "Dalam", "داخلی"),
    "Outer":      ("外", "خارجي", "Внешний", "Extérieur", "Exterior", "Externo", "Luar", "بیرونی"),
    "New":        ("新", "جديد", "Новый", "Neuf", "Nuevo", "Novo", "Baru", "نو"),
    "Old":        ("旧", "قديم", "Старый", "Ancien", "Usado", "Usado", "Lama", "قدیمی"),
    "Imported":   ("进口", "مستورد", "Импортный", "Importé", "Importado", "Importado", "Impor", "وارداتی"),
    "Without":    ("无", "بدون", "Без", "Sans", "Sin", "Sem", "Tanpa", "بدون"),
    "With":       ("带", "مع", "С", "Avec", "Con", "Com", "Dengan", "با"),
    "Pickup":     ("皮卡", "بيك أب", "Пикап", "Pick-up", "Pickup", "Picape", "Pikap", "وانت"),
    "Truck":      ("货车", "شاحنة", "Грузовик", "Camion", "Camión", "Caminhão", "Truk", "کامیون"),
    "Van":        ("面包车", "فان", "Фургон", "Fourgon", "Furgoneta", "Van", "Van", "ون"),
    "Sedan":      ("轿车", "سيدان", "Седан", "Berline", "Sedán", "Sedã", "Sedan", "سدان"),
    "Diesel":     ("柴油", "ديزل", "Дизель", "Diesel", "Diésel", "Diesel", "Diesel", "دیزل"),
    "Petrol":     ("汽油", "بنزين", "Бензин", "Essence", "Gasolina", "Gasolina", "Bensin", "بنزین"),
    "Straight":   ("直", "مستقيم", "Прямой", "Droit", "Recto", "Reto", "Lurus", "مستقیم"),
    "Bent":       ("弯", "منحني", "Изогнутый", "Coudé", "Curvo", "Curvo", "Bengkok", "خم"),
    "Engine":     ("发动机", "محرك", "Двигатель", "Moteur", "Motor", "Motor", "Mesin", "موتور"),
    "Connector":  ("插头", "موصل", "Разъём", "Connecteur", "Conector", "Conector", "Konektor", "اتصال"),
    "Valve":      ("阀", "صمام", "Клапан", "Soupape", "Válvula", "Válvula", "Katup", "سوپاپ"),
    "Series":     ("系", "سلسلة", "Серия", "Série", "Serie", "Série", "Seri", "سری"),
    "Present":    ("至今", "حتى الآن", "н.в.", "actuel", "actual", "atual", "sekarang", "تاکنون"),
}

# ---------------------------------------------------------------- 车系（只收有官方中文名的）
# 车系名不做逐语翻译：别的语种就写英文原名，只有中文有官方名。
MODELS_ZH = {
    # 丰田 / 雷克萨斯
    "Camry": "凯美瑞", "Corolla": "卡罗拉", "Crown": "皇冠", "Highlander": "汉兰达",
    "Levin": "雷凌", "Prado": "普拉多", "Prius": "普锐斯", "Reiz": "锐志",
    "Vios": "威驰", "Yaris": "雅力士",
    # 本田
    "Accord": "雅阁", "City": "锋范", "Civic": "思域", "Crider": "凌派",
    "Crosstour": "歌诗图", "Odyssey": "奥德赛", "Spirior": "思铂睿", "Vezel": "缤智",
    # 日产 / 马自达 / 三菱
    "Bluebird": "蓝鸟", "Livina": "骊威", "Murano": "楼兰", "Qashqai": "逍客",
    "Sunny": "阳光", "Sylphy": "轩逸", "Teana": "天籁", "Tiida": "骐达",
    "Atenza": "阿特兹", "Axela": "昂克赛拉",
    "Asx": "劲炫", "Delica": "得利卡", "Lancer": "蓝瑟", "Outlander": "欧蓝德",
    "Pajero": "帕杰罗",
    # 斯巴鲁 / 铃木
    "Forester": "森林人", "Legacy": "力狮", "Outback": "傲虎",
    "Alto": "奥拓", "Liana": "利亚纳", "Vitara": "维特拉",
    # 现代 / 起亚
    "Accent": "雅绅特", "Elantra": "伊兰特", "Sonata": "索纳塔", "Tucson": "途胜",
    "Verna": "瑞纳", "Cerato": "赛拉图", "Rio": "锐欧", "Sorento": "索兰托",
    "Sportage": "狮跑",
    # 雪佛兰
    "Aveo": "乐骋", "Captiva": "科帕奇", "Cavalier": "科沃兹", "Cruze": "科鲁兹",
    "Epica": "景程", "Lova": "乐风", "Malibu": "迈锐宝", "Monza": "科鲁泽",
    "Sail": "赛欧", "Spark": "乐驰", "Trax": "创酷",
    # 别克
    "Enclave": "昂科雷", "Encore": "昂科拉", "Envision": "昂科威", "Excelle": "凯越",
    "Lacrosse": "君越", "Regal": "君威", "Verano": "威朗",
    # 福特 / 吉普 / 道奇
    "Ecosport": "翼搏", "Edge": "锐界", "Fiesta": "嘉年华", "Focus": "福克斯",
    "Kuga": "翼虎", "Mondeo": "蒙迪欧", "Taurus": "金牛座", "Transit": "全顺",
    "Cherokee": "自由光", "Compass": "指南者", "Patriot": "自由客", "Wrangler": "牧马人",
    "Journey": "酷威",
    # 大众 / 斯柯达
    "Beetle": "甲壳虫", "Bora": "宝来", "Golf": "高尔夫", "Jetta": "捷达",
    "Lavida": "朗逸", "Magotan": "迈腾", "Passat": "帕萨特", "Sagitar": "速腾",
    "Santana": "桑塔纳", "Tiguan": "途观", "Touareg": "途锐", "Touran": "途安",
    "Fabia": "晶锐", "Octavia": "明锐", "Superb": "昊锐",
    # 标致 / 雪铁龙
    "Elysee": "爱丽舍", "Triomphe": "凯旋",
    # 路虎
    "Discovery": "发现", "Evoque": "极光", "Range Rover": "揽胜",
    # 长安
    "AlSvin": "悦翔", "Benben": "奔奔", "Eado": "逸动", "Ono": "欧诺",
    "Raeton": "睿骋", "Xingka": "星卡",
    # 奇瑞
    "Arrizo": "艾瑞泽", "Fulwin": "风云", "Oriental": "东方之子", "Tiggo": "瑞虎",
    # 吉利
    "Binyue": "缤越", "Borui": "博瑞", "Boyue": "博越", "Emgrand": "帝豪",
    "Vision": "远景", "Xingyue": "星越",
    # 比亚迪
    "Qin": "秦", "Song": "宋", "Yuan": "元",
    # 五菱 / 宝骏
    "Hongguang": "宏光", "Hongtu": "鸿途", "Rongguang": "荣光", "Zhiguang": "之光",
    # 江淮 / 长城 / 东风 / 北汽
    "Heyue": "和悦", "Refine": "瑞风", "Sehol": "思皓",
    "Coolbear": "酷熊", "Florid": "炫丽", "Voleex": "腾翼", "Wingle": "风骏",
    "Heijingang": "黑金刚", "Leopaul": "猎豹", "Junjie": "骏捷",
    "Jingyi": "景逸", "Lingzhi": "菱智", "Huansu": "幻速", "Zhanqi": "战旗",
    "Senia": "森雅", "Weizhi": "威志", "Haise": "海狮",
    # 江铃
    "Baodian": "宝典", "Vigus": "域虎",
    # 东风风神
    "Aeolus": "风神",
    # 凯翼
    "Cowin": "凯翼",
}

# ---------------------------------------------------------------- 备注里的固定说法
# 备注是「段」拼起来的（Qty/vehicle: 2 | 1*4 pcs/box | Unit: pc），逐段替换固定词，
# 数字和包装号原样保留。
PHRASES = {
    "Qty/vehicle":        ("每车用量", "الكمية لكل سيارة", "Кол-во на авто", "Qté/véhicule", "Cant./vehículo", "Qtd./veículo", "Jumlah/kendaraan", "تعداد در خودرو"),
    "pcs/box":            ("件/盒", "قطعة/علبة", "шт./кор.", "pcs/boîte", "uds./caja", "un./caixa", "pcs/kotak", "عدد/جعبه"),
    "Unit: pc":           ("单位：件", "الوحدة: قطعة", "Ед.: шт.", "Unité : pc", "Unidad: ud", "Unidade: un", "Satuan: pcs", "واحد: عدد"),
    "Also packed as":     ("另有包装号", "معبأ أيضاً كـ", "Также фасуется как", "Aussi conditionné en", "También envasado como", "Também embalado como", "Juga dikemas sebagai", "همچنین بسته‌بندی به‌صورت"),
    "Material:":          ("材质：", "المادة:", "Материал:", "Matière :", "Material:", "Material:", "Bahan:", "جنس:"),
    "Packing:":           ("包装：", "التعبئة:", "Упаковка:", "Conditionnement :", "Empaque:", "Embalagem:", "Kemasan:", "بسته‌بندی:"),
    "Stepper:":           ("步进马达：", "محرك خطوة:", "Шаговый мотор:", "Moteur pas-à-pas :", "Motor paso a paso:", "Motor de passo:", "Motor stepper:", "موتور پله‌ای:"),
    "Not kept in stock":  ("不备货", "غير متوفر بالمخزون", "Нет на складе", "Non stocké", "Sin stock", "Sem estoque", "Tidak ada stok", "موجود نیست"),
    "Discontinued - no reorder": ("已停产，不再补货", "متوقف - لا إعادة طلب", "Снято с производства", "Arrêté - pas de réassort", "Descontinuado", "Descontinuado", "Tidak diproduksi lagi", "توقف تولید"),
    "Iridium-Platinum":   ("铱铂金", "إيريديوم-بلاتين", "Иридий-платина", "Iridium-Platine", "Iridio-Platino", "Irídio-Platina", "Iridium-Platinum", "ایریدیم-پلاتین"),
    "Double Iridium":     ("双铱金", "إيريديوم مزدوج", "Двойной иридий", "Double iridium", "Doble iridio", "Irídio duplo", "Iridium ganda", "ایریدیم دوتایی"),
    "Double Platinum":    ("双铂金", "بلاتين مزدوج", "Двойная платина", "Double platine", "Doble platino", "Platina dupla", "Platinum ganda", "پلاتین دوتایی"),
    "Iridium":            ("铱金", "إيريديوم", "Иридий", "Iridium", "Iridio", "Irídio", "Iridium", "ایریدیم"),
    "Platinum":           ("铂金", "بلاتين", "Платина", "Platine", "Platino", "Platina", "Platinum", "پلاتین"),
    "Nickel-Copper":      ("镍铜", "نيكل-نحاس", "Никель-медь", "Nickel-cuivre", "Níquel-Cobre", "Níquel-Cobre", "Nikel-Tembaga", "نیکل-مس"),
    "Nickel":             ("镍", "نيكل", "Никель", "Nickel", "Níquel", "Níquel", "Nikel", "نیکل"),
    "electrode":          ("电极", "قطب", "электрод", "électrode", "electrodo", "eletrodo", "elektroda", "الکترود"),
}

MARK_BEGIN = "  /* ===== PDATA:BEGIN 由 pdata_i18n.py 生成，别手改这一段（改译名请改 pdata_i18n.py） ===== */"
MARK_END = "  /* ===== PDATA:END ===== */"


def rows():
    """合并成一张表：[(英文原文, {lang: 译文}), ...]，只保留有译文的。"""
    out, seen = [], {}
    for src_dict in (BRANDS, TERMS, MODELS_ZH, PHRASES):
        for src, val in src_dict.items():
            key = src.strip().upper()
            if not key:
                continue
            if key in seen:
                raise SystemExit("译名表里重复的原词：%r（%s / %s）" % (src, seen[key], src))
            seen[key] = src
            if isinstance(val, str):
                d = {"zh": val}
            else:
                d = {LANGS[i]: v for i, v in enumerate(val) if v}
            if d:
                out.append((src, d))
    out.sort(key=lambda r: (r[0].lower(), r[0]))
    return out


def build_js():
    """生成 PDATA 段的 JS 文本（每行 [原文, zh, ar, ru, fr, es, pt, id, fa]）。"""
    lines = [MARK_BEGIN,
             "  /* 产品数据译名：英语原文在前；空串 = 这种语言就用英文原名 */",
             "  var PD = ["]
    for src, d in rows():
        cells = [src] + [d.get(l, "") for l in LANGS]
        lines.append("    " + json.dumps(cells, ensure_ascii=False) + ",")
    lines.append("  ];")
    lines.append(MARK_END)
    return "\n".join(lines)


def self_check(verbose=True):
    rs = rows()
    bad = 0
    for src, d in rs:
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9 ./&:\-]*", src):
            print("  [!] 原词里有可疑字符：%r" % src)
            bad += 1
        if len(src) < 2:
            print("  [!] 太短，容易误替换：%r" % src)
            bad += 1
    if verbose:
        by_lang = {l: sum(1 for _, d in rs if d.get(l)) for l in LANGS}
        print("译名条目：%d（品牌 %d / 方位词 %d / 车系 %d / 备注 %d）"
              % (len(rs), len(BRANDS), len(TERMS), len(MODELS_ZH), len(PHRASES)))
        print("每个语种实际有译文的条目：" +
              ", ".join("%s=%d" % (l, by_lang[l]) for l in LANGS))
        for src in ("Changan", "Toyota", "BMW", "Great Wall", "Qty/vehicle", "Camry"):
            hit = [d for s, d in rs if s == src]
            print("  %-12s → %s" % (src, hit[0] if hit else "（不在表里！）"))
    return bad


def write_js():
    src = io.open(I18N_JS, encoding="utf-8").read()
    block = build_js()
    if MARK_BEGIN in src and MARK_END in src:
        i = src.index(MARK_BEGIN)
        j = src.index(MARK_END) + len(MARK_END)
        new = src[:i] + block + src[j:]
    else:
        # 第一次：插在 var lang = DEF; 之前
        anchor = "  var lang = DEF;"
        if anchor not in src:
            raise SystemExit("i18n.js 里找不到插入位置（var lang = DEF;）")
        new = src.replace(anchor, block + "\n\n" + anchor, 1)
    io.open(I18N_JS, "w", encoding="utf-8", newline="\n").write(new)
    return len(new) - len(src)


def main(argv):
    bad = self_check()
    if "--write" in argv:
        delta = write_js()
        print("已写入 %s（%+d 字节）" % (os.path.basename(I18N_JS), delta))
    else:
        print("（只自检，没写文件。要写请加 --write）")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
