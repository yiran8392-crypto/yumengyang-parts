# -*- coding: utf-8 -*-
"""
型号查询站 · 静态页生成（SEO 用）
================================
在 build.py 跑完数据和图片之后调用，生成：

  c/<slug>.html              每个型号一个独立页（3500+）
  category/<slug>.html       5 个品类页，列出该品类全部型号
  sitemap.xml / robots.txt
  404.html
  assets/style.css           共用样式（如果不存在就写一份）
  首页 index.html            注入可被搜索引擎抓取的型号链接

所有页面都用相对路径，双击 index.html（file://）也能互相跳转。
站点域名和 WhatsApp 号写在 站点设置.txt，改完重跑“更新数据.cmd”即可。
"""

import html
import json
import os
import random
import re
import time
from urllib.parse import quote

try:
    import guides_content
except Exception:                      # 指南模块缺失时站点照常生成，只是没有 guides/
    guides_content = None

try:
    import codes_content              # 故障码诊断页正文（codes/），缺了就跳过这一层
except Exception:
    codes_content = None

try:
    import brands as brandlib          # 品牌 / 车系词典（/brand/、/vehicle/ 落地页用）
except Exception:
    brandlib = None

# 二维码里解出来的「加好友」链接（2026-11-11 用 zxing-cpp 解 qr-wecom.webp / qr-whatsapp.webp 得到）。
# 页脚和联系页二维码下面的按钮直接指向它们：手机点一下 = 打开微信添加页 / 拉起 WhatsApp 对话。
# 换二维码后必须同步改这里（解一下新二维码就行）。
QR_LINK_WECOM = ("https://work.weixin.qq.com/u/vc7fdb77fb9d4687fc"
                 "?v=5.0.13.84802&bb=cd29c15e19")
QR_LINK_WHATSAPP = "https://wa.me/message/AH6U2Q2P7BKZH1"

# 站点自己的号码（分享按钮不强制发给某个号，先让客户自己选人）
SHARE_ICON = ('<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2a10 10 0 00-8.5 15.2L2 22l4.9-1.4A10 '
              '10 0 1012 2zm0 2a8 8 0 016.9 12l-.3.5 1 3-3.1-.9-.5.3A8 8 0 1112 4z"/></svg>')
COPY_ICON = ('<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9.5 14.5l5-5M8 13.2l-1.6 1.6a3.6 3.6 0 005 5'
             'l1.7-1.7M16 10.8l1.6-1.6a3.6 3.6 0 00-5-5l-1.7 1.7" fill="none" stroke="currentColor" '
             'stroke-width="1.9" stroke-linecap="round"/></svg>')

HERE = os.path.dirname(os.path.abspath(__file__))
CFG_FILE = os.path.join(HERE, "站点设置.txt")

DEFAULT_CFG = {
    "site_url": "https://your-domain.com",
    "whatsapp": "8615915859048",
    "company_en": "Guangzhou Yumengyang Auto Parts Co., Ltd.",
    "company_cn": "广州驭盟扬汽车零部件有限公司",
    # 邮箱：sales@yumengyang.com 待开通（开通后改 站点设置.txt 里的 邮箱= 一行即可；
    # 页面上只显示地址本身，不写任何"待开通 / 占位"字样）
    "email": "sales@yumengyang.com",
    # 地址：英文站 / 阿语站 / 俄语站用 address_en，中文站用 address_cn
    "address_en": "E05, Yiyou (Guangyuan East) Auto Parts City, Baiyun District, Guangzhou, China",
    "address_cn": "广州市白云区益友（广元东）汽配城 E05 档",
    # Organization JSON-LD 里的结构化地址（站点设置.txt 可覆盖，不填用这里的默认值）
    "street": "E05, Yiyou (Guangyuan East) Auto Parts City",
    "locality": "Baiyun District, Guangzhou",
    "region": "Guangdong",
    "country": "CN",
    "hours": "Mon–Sat 09:00–18:00 (GMT+8)",
    # 访问统计：空 = 关闭；写法见 assets/analytics.js 顶部注释和《站点设置.txt》
    "analytics": "",
    # 是否把买家搜的词（型号/OE 号）一起记下来：1 = 记，空 = 不记
    "analytics_q": "",
}

# 首页信任条 / 产品页条款块用的口径。
# 只放公司能给的说法：质保区间、退货率、电喷件覆盖率、支持小批量。
# 价格、库存、MOQ 具体数量、交期天数一律不写死（见《怎么用.md》：内部数据不对外）。
TRUST = [
    ("12–24 mo", "trust_warranty", "Warranty on every part"),
    ("0.03%", "trust_return", "Return rate"),
    ("≈95%", "trust_cover", "EFI parts covered"),
    ("Small batch", "trust_moq", "Orders accepted"),
]
# 信任条里需要跟着语种变的“数值短语”（键 → i18n 键）
TRUST_V = {"trust_warranty": "trust_v_warranty", "trust_moq": "trust_v_moq"}

# 品牌显示（别在模板里散着写名字，改一处全站生效）
# translate="no" + class="notranslate" 是给浏览器自动翻译看的：Edge / Chrome / iOS Safari
# 翻页面时会跳过这些节点，避免把 Yumengyang 翻成「玉明阳」这种鬼东西。
# 注意：不整页禁译（客户可能想翻译页面），只锁品牌名。
BRAND_EN = "Yumengyang"
BRAND_EN2 = "Auto Parts"
BRAND_CN = "广州驭盟扬汽配"
NOTRANSLATE = 'translate="no"'

# 内联 SVG favicon：省掉每个页面一次 /favicon.ico 404 请求（3G 上有用）
FAVICON = ('<link rel="icon" href="data:image/svg+xml,'
           "%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E"
           "%3Crect width='32' height='32' rx='7' fill='%230d2233'/%3E"
           "%3Ccircle cx='16' cy='16' r='7' fill='%23e8622a'/%3E%3C/svg%3E\">")

# 界面多语言：文案字典在 assets/i18n.js（全站共用一个文件，页面里只放 data-i18n 标记）。
# 这里只负责语言切换器的 HTML 和“首屏防闪”的小脚本。
LANG_OPTIONS = [("en", "English"), ("zh", "简体中文"), ("ar", "العربية"), ("ru", "Русский"),
                ("fr", "Français"), ("es", "Español"), ("pt", "Português"), ("id", "Bahasa Indonesia"),
                ("fa", "فارسی")]


def lang_sel_html():
    opts = "".join('<option value="%s">%s</option>' % (k, esc(v)) for k, v in LANG_OPTIONS)
    return ('<label class="sr-only" for="langsel">Language</label>'
            '<select id="langsel" class="langsel" aria-label="Language" translate="no">%s</select>' % opts)


LANG_BOOT = ('<script>try{var l=(new URLSearchParams(location.search).get("lang")||'
             'localStorage.getItem("ymy_lang")||"en").toLowerCase();'
             'l=l.indexOf("zh")===0?"zh":l.indexOf("ar")===0?"ar":l.indexOf("ru")===0?"ru"'
             ':l.indexOf("fr")===0?"fr":l.indexOf("es")===0?"es":l.indexOf("pt")===0?"pt"'
             ':l.indexOf("id")===0?"id":l.indexOf("fa")===0?"fa":"en";'
             'var d=document.documentElement;d.setAttribute("data-lang",l);'
             'if(l==="ar"||l==="fa")d.setAttribute("dir","rtl");'
             # 非英语界面锁住浏览器的「自动翻译」：否则 Chrome/Edge 会把我们的
             # 印尼语/波斯语页面当成外语再翻成访客的母语，翻出一堆乱码。
             'if(l!=="en")d.setAttribute("translate","no")}catch(e){}</script>')

# 热销品类排最前，其余按型号数从多到少（首页按钮 / 导航 / 品类总览 / 首页目录块共用）
HOT_ORDER = ["coil", "fuelpump", "o2", "plug"]
NAV_KEYS = []          # build_static 里算好，给 sitehead 用
LIVE_N = 0             # 有型号的品类数（0 型号的品类不进出入口）


def order_cats(cats):
    """热销四类固定在前，后面按型号数倒序。"""
    def k(c):
        key = c.get("key")
        i = HOT_ORDER.index(key) if key in HOT_ORDER else len(HOT_ORDER)
        return (i, -(c.get("n") or 0), key or "")
    return sorted(cats, key=k)

# 品类元信息：key -> (目录 slug, 英文复名, 英文单数, 中文)
CAT_META = {
    "coil": ("ignition-coils", "Ignition Coils", "Ignition Coil", "点火线圈"),
    "abs": ("abs-sensors", "ABS Sensors", "ABS Sensor", "ABS 传感器"),
    "wire": ("spark-plug-wires", "Spark Plug Wire Sets", "Spark Plug Wire Set", "火花塞线"),
    "thermo": ("thermostats", "Thermostats", "Thermostat", "节温器"),
    "plug": ("spark-plugs", "Spark Plugs", "Spark Plug", "火花塞"),
}

POS_WORDS = {
    "front", "rear", "left", "right", "lh", "rh", "wheel", "axle",
    "new", "old", "abs", "sensor", "-", "=", "&",
}

PER_PAGE = 700          # 品类页每页列多少个型号（ABS 2065 个拆成 3 页，避免单页过大）
ANALYTICS_V = "20261110b"   # 改 assets/analytics.js 之后把这个版本号一起改，浏览器才会重新拉
CSS_V = "20261111g"          # 改 assets/style.css 之后改这里，等于给全站换个缓存键
I18N_V = "20261112i18n1"     # 改 assets/i18n.js（加语种/改文案）之后改这里，老访客才不会用缓存里的旧字典


# ------------------------------------------------------------------ 配置
def load_cfg():
    cfg = dict(DEFAULT_CFG)
    if os.path.exists(CFG_FILE):
        try:
            raw = open(CFG_FILE, "r", encoding="utf-8-sig").read()
        except UnicodeDecodeError:
            raw = open(CFG_FILE, "r", encoding="gbk", errors="ignore").read()
        alias = {
            "域名": "site_url", "site_url": "site_url", "网址": "site_url",
            "whatsapp": "whatsapp", "whatsapp号": "whatsapp", "号码": "whatsapp",
            "电话": "whatsapp", "邮箱": "email", "email": "email",
            "地址": "address_en", "address": "address_en", "英文地址": "address_en",
            "中文地址": "address_cn", "address_cn": "address_cn",
            "街道": "street", "street": "street",
            "城市": "locality", "locality": "locality",
            "省份": "region", "region": "region",
            "国家": "country", "country": "country",
            "工作时间": "hours", "hours": "hours",
            "统计": "analytics", "分析": "analytics", "统计代码": "analytics",
            "analytics": "analytics",
            "统计查询词": "analytics_q", "analytics_q": "analytics_q",
        }
        for line in raw.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = alias.get(k.strip().lower(), alias.get(k.strip(), k.strip()))
            v = v.strip()
            if k in cfg and v:
                cfg[k] = v
    cfg["site_url"] = cfg["site_url"].rstrip("/")
    cfg["whatsapp"] = re.sub(r"[^0-9]", "", cfg["whatsapp"]) or DEFAULT_CFG["whatsapp"]
    return cfg


# ------------------------------------------------------------------ 小工具
def esc(t):
    return html.escape(str(t or ""), quote=True)


def clean_text(t):
    """源表里残留的 &#10; 之类实体，统一还原成正常文字。"""
    t = html.unescape(str(t or ""))
    t = t.replace("\u00a0", " ").replace("\u3000", " ")
    return re.sub(r"\s+", " ", t).strip()


def slugify(t):
    t = clean_text(t).lower()
    t = t.replace("&", " and ").replace("+", " plus ")
    t = re.sub(r"[\s/\\|,;:]+", "-", t)
    t = re.sub(r"[^a-z0-9-]+", "", t)
    t = re.sub(r"-{2,}", "-", t).strip("-")
    return t[:70]


def make_slugs(items, keep_existing=False):
    """优先 OE 号，其次内部型号；重复的加 -2、-3 后缀。
    keep_existing=True：已经有 s 的条目一律不动（补 OE 字段时不会让老 URL 变地址）。"""
    used, clash = set(), []
    if keep_existing:
        for it in items:
            s = (it.get("s") or "").strip()
            if s:
                used.add(s)
    for it in items:
        if keep_existing and (it.get("s") or "").strip():
            continue
        base = slugify(it.get("oe") or "") or slugify(it.get("m") or "") or ("part-%d" % it["i"])
        slug = base
        n = 2
        while slug in used:
            slug = "%s-%d" % (base, n)
            n += 1
        if slug != base:
            clash.append((base, slug, it.get("m")))
        used.add(slug)
        it["s"] = slug
    return clash


def fitment_hint(app, brand=""):
    """从适配车型里挑一个短的车系名，用在 title 里，比如 “Toyota Camry”。"""
    text = clean_text(app)
    if not text:
        b = clean_text(brand).split(",")[0].strip()[:32]
        return "" if re.search(r"[\u4e00-\u9fa5]", b) else b
    for seg in re.split(r"[;|,]", text):
        had_slash = "/" in seg
        seg = seg.replace("/", " ").replace("=", " ")
        toks, out = seg.split(), []
        for tok in toks:
            t = tok.strip("()[],.")
            if not t:
                continue
            low = t.lower()
            if not out and low in POS_WORDS:
                continue
            if re.fullmatch(r"[0-9.,\-+]+", t):
                continue
            if re.fullmatch(r"\d+(\.\d+)?\s*(l|t|v|cc|kw|hp|at|mt)?", t, re.I):
                continue          # 排量/功率这类参数别放进标题
            if re.search(r"[\u4e00-\u9fa5]", t):
                # 中文车型段：只挑里面的拉丁词，挑不到就跳过（标题保持英文）
                latin = re.findall(r"[A-Za-z][A-Za-z0-9\.\-]*", tok)
                if latin and not out:
                    out.extend(latin[:2])
                continue
            out.append(t)
            if len(out) >= 2:
                break
        hint = " ".join(out[:1] if had_slash else out)[:34].strip(" -,")
        if hint and len(hint) > 2:
            return hint
    return ""


def type_name(cat):
    return CAT_META.get(cat, (cat, cat, cat, cat))[2]


def cat_slug(cat):
    return CAT_META.get(cat, (cat, cat, cat, cat))[0]


def wa_link(cfg, text):
    return "https://wa.me/%s?text=%s" % (cfg["whatsapp"], quote(text, safe=""))


def has_site(cfg):
    u = (cfg.get("site_url") or "").strip()
    return bool(u) and "your-domain.com" not in u


def rel_url(cfg, path):
    path = path.lstrip("/")
    if not path or path == "index.html":
        return cfg["site_url"] + "/"
    return cfg["site_url"] + "/" + path


def money_free_note():
    return "Price and MOQ on request."


def wa_display(num):
    """8615915859048 -> +86 159 1585 9048（页脚用，看得懂的形式）"""
    num = num or ""
    if len(num) == 13 and num.startswith("86"):
        return "+86 %s %s %s" % (num[2:5], num[5:9], num[9:])
    return "+" + num


# ------------------------------------------------------------------ 结构化数据
def org_ld(cfg):
    """Organization：公司名 / logo / 地址 / 联系方式 / 语言。全站每页都带。"""
    base = cfg["site_url"] + "/"
    ld = {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": cfg["company_en"],
        "alternateName": cfg["company_cn"],
        "url": base,
        "logo": rel_url(cfg, "assets/og/ignition-coils.jpg"),
        "description": ("Chinese manufacturer and exporter of electronic fuel injection parts: ignition coils, "
                        "fuel pumps, oxygen sensors, ABS sensors, spark plugs and sensors."),
        "address": {"@type": "PostalAddress",
                    "streetAddress": cfg["street"],
                    "addressLocality": cfg["locality"],
                    "addressRegion": cfg["region"],
                    "addressCountry": cfg["country"]},
        "contactPoint": [{
            "@type": "ContactPoint",
            "contactType": "sales",
            "telephone": "+" + cfg["whatsapp"],
            "email": cfg["email"],
            "areaServed": "Worldwide",
            "availableLanguage": ["en", "zh", "ar", "ru", "fr", "es", "pt", "id", "fa"],
        }],
    }
    return ld


def website_ld(cfg, total):
    """WebSite + SearchAction：站内搜索框指向首页 ?q=。"""
    base = cfg["site_url"] + "/"
    return {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": "%s · OE / cross-reference lookup" % cfg["company_en"].split(" Co.")[0],
        "alternateName": BRAND_CN,
        "url": base,
        "inLanguage": ["en", "zh", "ar", "ru", "fr", "es", "pt", "id", "fa"],
        "potentialAction": {
            "@type": "SearchAction",
            "target": {"@type": "EntryPoint", "urlTemplate": base + "?q={search_term_string}"},
            "query-input": "required name=search_term_string",
        },
        "publisher": {"@type": "Organization", "name": cfg["company_en"], "url": base},
    }


def site_ld(cfg):
    """全站（型号页 / 品类页 / 首页）都要带的 Organization + WebSite。"""
    if not has_site(cfg):
        return []
    return [org_ld(cfg), website_ld(cfg, cfg.get("_total", 0))]


# ------------------------------------------------------------------ 首页内容块
# 文案：英文原文写在 HTML 里（data-i18n 兜底），zh / ar / ru 在 assets/i18n.js。
FAQ_ITEMS = [
    ("faq_q1", "What is your MOQ?",
     "faq_a1", "MOQ depends on the part and the packing. Send us the models and quantities you need "
               "and we confirm the MOQ line by line."),
    ("faq_q2", "How long does delivery take?",
     "faq_a2", "Stock items leave our Guangzhou warehouse within days. Production orders depend on "
               "quantity — we confirm the exact shipping date in the quotation."),
    ("faq_q3", "What warranty do you give?",
     "faq_a3", "12 to 24 months depending on the part type. The exact term is written on the quotation "
               "and the invoice, so it is the same for you and for us."),
    ("faq_q4", "Can I return or exchange a part?",
     "faq_a4", "Yes. Send photos of the problem and we replace or credit the faulty parts. Our return "
               "rate is 0.03%, so it is rare."),
    ("faq_q5", "Can I get samples for testing?",
     "faq_a5", "Yes. Samples are available on request before a bulk order; the buyer covers the freight."),
    ("faq_q6", "How do I pay?",
     "faq_a6", "Bank transfer (T/T) is standard: 30% deposit, balance before shipment. L/C at sight is "
               "accepted on orders above USD 20,000. Terms are confirmed on the proforma invoice."),
]

WHY = [
    ("why_q_t", "OE-grade quality", "why_q_v",
     "Built to OE specification for the electrics and sensors we supply, under our own brand WEILI.",
     '<path d="M12 3 5 6v5.4c0 4.4 3 8.2 7 9.6 4-1.4 7-5.2 7-9.6V6l-7-3z"/><path d="m9 12.2 2.1 2.1 4.2-4.2"/>'),
    ("why_p_t", "About 1/3 of OEM price", "why_p_v",
     "Factory-direct pricing, no importer and no distributor in between.",
     '<path d="M20.6 13.4 13.4 20.6a2 2 0 0 1-2.8 0L3 13V3h10l7.6 7.6a2 2 0 0 1 0 2.8z"/><path d="M7.6 7.6h.01"/>'),
    ("why_r_t", "24-hour quotation", "why_r_v",
     "Send the OE number or a photo with quantity — a priced offer comes back within one working day.",
     '<circle cx="12" cy="12" r="9"/><path d="M12 7.4V12l3.3 2.1"/>'),
    ("why_s_t", "Worldwide shipping", "why_s_v",
     "Guangzhou port to your door, with packing matched to the part so nothing is damaged on the way.",
     '<circle cx="12" cy="12" r="9"/><path d="M3.2 9h17.6M3.2 15h17.6"/>'
     '<path d="M12 3c2.2 2.4 3.3 5.7 3.3 9s-1.1 6.6-3.3 9c-2.2-2.4-3.3-5.7-3.3-9S9.8 5.4 12 3z"/>'),
]


def trust_html(cfg):
    # 13–24 mo / Small batch 这类静态英文在非英语页很扎眼，能翻的值也挂上 data-i18n
    cells = "".join(
        '<div class="tb-cell"><b%s>%s</b><span data-i18n="%s">%s</span></div>'
        % (' data-i18n="%s"' % TRUST_V[k] if k in TRUST_V else "", esc(v), k, esc(lbl))
        for v, k, lbl in TRUST)
    return ('<section class="trustbar" aria-label="Company facts"><div class="wrap tb-wrap">%s</div></section>'
            % cells)


def why_html(cfg):
    cards = "".join(
        '<div class="wh"><span class="whi"><svg viewBox="0 0 24 24" aria-hidden="true">%s</svg></span>'
        '<b data-i18n="%s">%s</b><p data-i18n="%s">%s</p></div>'
        % (svg, kt, esc(t), kv, esc(v)) for kt, t, kv, v, svg in WHY)
    return ('<section class="whyus" id="why">'
            '<h2><span data-i18n="why_h">Why buyers overseas order from us</span>'
            '<span class="zh-extra"> 为什么选我们</span></h2>'
            '<p class="lead" data-i18n="why_lead">Own brand WEILI at importer-free pricing: the same part '
            'numbers, inspected batch by batch, at a fraction of the OEM price.</p>'
            '<div class="whgrid">%s</div></section>' % cards)


SALES_RE = re.compile(r"Sales index:\s*(\*+)")

# 内部备注段：销量打分、质检修正、OE 校验、同款互指、错字修正 —— 一律不给买家看
INTERNAL_NOTE_RE = re.compile(
    r"(sales\s*index|corrected\s+online|verified\s+online|oe\s+typo\s+fixed|also\s+listed\s+as)",
    re.I,
)


def _sales_rank(it):
    si = it.get("si")
    if si:
        return int(si)
    m = SALES_RE.search(it.get("r") or "")
    return len(m.group(1)) if m else 0


def public_notes(t):
    """对外显示的备注：去掉内部段（销量指数 / 质检修正 / OE 校验 / 同款互指 / 错字修正），
    其余段（Qty/vehicle 每车用量、Packing、Material…）照常保留。"""
    segs = [s.strip() for s in re.split(r"[|｜]", t or "") if s.strip()]
    return " | ".join(s for s in segs if not INTERNAL_NOTE_RE.search(s))


def hot_html(cfg, cats, by_cat, per_cat=2, keys=None):
    """最新/热门型号横条：按数据里的 Sales index（*–*****）取，跨品类，带图带 OE。
    无星级也不强凑：每个品类取前 per_cat 个有图的，按星级降序、再按下标稳定排序。"""
    keys = keys or TOP_KEYS
    picked = []
    for key in keys:
        items = [it for it in (by_cat.get(key) or []) if it.get("p")]
        if not items:
            continue
        items = sorted(items, key=lambda it: (-_sales_rank(it), it["i"]))
        picked.extend(items[:per_cat])
    if not picked:
        return ""
    cards = []
    for it in picked:
        key = it["cat"]
        slug, en, one, cn = CAT_META.get(key, (key, key, key, key))
        img = it.get("t") or it.get("p")
        oe = it.get("oe") or it["m"]
        cards.append(
            '<a class="hotcard" href="c/%s.html">'
            '<span class="hotimg"><img src="%s" width="160" height="160" loading="lazy" decoding="async" '
            'alt="%s"></span>'
            '<b>%s</b><span class="hotoe">OE %s</span><span class="hotcat" data-cat="%s">%s</span></a>'
            % (esc(it["s"]), esc(img), esc("%s %s" % (one, oe)), esc(it["m"]), esc(oe), key, esc(en)))
    return ('<section class="hotstrip" id="hot">'
            '<div class="hs-head"><h2><span data-i18n="hot_h">Popular part numbers</span>'
            '<span class="zh-extra"> 热门型号</span></h2>'
            '<a class="hs-all" href="category/index.html"><span data-i18n="hot_all">All categories</span> →</a></div>'
            '<p class="hs-sub" data-i18n="hot_sub">Best-selling models this season — every card opens the '
            'fitment list, photos and a WhatsApp quote button.</p>'
            '<div class="hotgrid">%s</div></section>' % "".join(cards))


def faq_html(cfg):
    items = "".join(
        '<details class="fq"%s><summary><span data-i18n="%s">%s</span></summary>'
        '<div class="fqa" data-i18n="%s">%s</div></details>'
        % (" open" if i == 0 else "", qk, esc(q), ak, esc(a))
        for i, (qk, q, ak, a) in enumerate(FAQ_ITEMS))
    return ('<section class="faq" id="faq">'
            '<h2><span data-i18n="faq_h">Frequently asked questions</span>'
            '<span class="zh-extra"> 常见问题</span></h2>'
            '<p class="lead" data-i18n="faq_lead">Six things buyers ask before the first order. '
            'Anything else — send it on WhatsApp, we answer in one working day.</p>'
            '%s</section>' % items)


def faq_ld(cfg):
    """FAQPage：跟上面 FAQ_ITEMS 同一份文案，避免正文和结构化数据对不上。"""
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [{"@type": "Question", "name": q,
                        "acceptedAnswer": {"@type": "Answer", "text": a}}
                       for _qk, q, _ak, a in FAQ_ITEMS],
    }


def addr_span(cfg, cls=""):
    """地址节点：英文页显示英文地址，中文页显示中文地址（data-v-cn 由 i18n.js 填）。
    en / ar / ru 走 foot_addr 字典；en 没字典时回退节点原文（就是英文地址）。"""
    c = ' class="%s"' % cls if cls else ""
    return ('<span%s data-i18n="foot_addr" data-v-en="%s" data-v-cn="%s">%s</span>'
            % (c, esc(cfg["address_en"]), esc(cfg["address_cn"]), esc(cfg["address_en"])))


POLICY_LINKS_EN = [("foot_privacy", "Privacy Policy", "privacy.html"),
                   ("foot_returns", "Refund & returns", "returns.html")]


def homefoot_html(cfg, total):
    wa = wa_link(cfg, "Hi, I would like a quotation for auto parts.")
    pol = "".join('<p><a href="%s" data-i18n="%s">%s</a></p>' % (href, k, esc(t))
                  for k, t, href in POLICY_LINKS_EN)
    return """<footer class="homefoot"><div class="wrap fgrid">
<section class="fcol">
  <b class="notranslate" %(nt)s>%(cn)s</b>
  <p class="notranslate" %(nt)s>%(en)s</p>
  <p>%(addr)s</p>
  <p><a href="about.html" data-i18n="foot_about">About us</a></p>
</section>
<section class="fcol">
  <h3 data-i18n="foot_contact">Contact</h3>
  <p><a href="%(wa)s" target="_blank" rel="noopener">WhatsApp %(wanum)s</a></p>
  <p><span data-i18n="foot_email">Email</span>: <a href="mailto:%(mail)s">%(mail)s</a></p>
  <p><span data-i18n="foot_hours">Working hours</span>: %(hours)s</p>
</section>
<section class="fcol">
  <h3 data-i18n="foot_links">Find a part</h3>
  <p><a href="index.html" data-i18n="lookup">OE / cross-reference lookup</a></p>
  <p><a href="category/index.html" data-i18n="all_cat_h1">All product categories</a></p>
  <p><a href="guides/index.html" data-i18n="guides_link">Buying guides</a></p>
  <p><a href="sitemap.xml" data-i18n="sitemap">Sitemap</a></p>
</section>
<section class="fcol">
  <h3 data-i18n="foot_legal">Policies</h3>
  %(pol)s
</section>
</div>
<div class="wrap fbot">
  <span data-i18n="foot_parts">Part numbers · real photos · fitment data</span>
  <span id="gen"></span>
</div></footer>""" % {
        "nt": NOTRANSLATE, "cn": esc(BRAND_CN), "en": esc(cfg["company_en"]),
        "addr": addr_span(cfg), "pol": pol,
        "wa": esc(wa), "wanum": esc(wa_display(cfg["whatsapp"])),
        "mail": esc(cfg["email"]), "hours": esc(cfg["hours"]),
    }


# ------------------------------------------------------------------ 页面片段
def head_block(cfg, title, desc, canonical, og_image="", og_type="product", ld_list=None, noindex=False,
               base="../", extra_scripts=""):
    """canonical / og:url / og:image 只在填了真实域名时才输出；
    域名还是占位符时，页面照样能双击打开、能部署，只是没有这些标签（不会指错地方）。
    base 是到站点根目录的相对前缀：c/ 和 category/ 里的页面是 "../"，根目录页面（政策页）是 ""。"""
    # 搜索结果摘要一般显示 155–160 字符，更长的会被截掉；统一压到 158 以内，优先在句号处收尾。
    if len(desc) > 158:
        cut = desc[:158]
        if ". " in cut:
            cut = cut[:cut.rfind(". ") + 1]
        else:
            cut = cut.rsplit(" ", 1)[0]
        desc = cut.rstrip(" ,;")
    site = has_site(cfg)
    robots = "noindex,follow" if noindex else "index,follow"
    img = ""
    if og_image and site:
        img = '\n<meta property="og:image" content="%s">' % esc(rel_url(cfg, og_image))
    can = ""
    ogurl = ""
    if canonical and site:
        can = '\n<link rel="canonical" href="%s">' % esc(canonical)
        # 四语共用一个 URL（JS 切换），所以只声明 x-default 指回本页英文版
        can += '\n<link rel="alternate" hreflang="x-default" href="%s">' % esc(canonical)
        ogurl = '\n<meta property="og:url" content="%s">' % esc(canonical)
    ld = "".join('\n<script type="application/ld+json">%s</script>' % json.dumps(x, ensure_ascii=False)
                 for x in (site_ld(cfg) + (ld_list or [])))
    an_cfg = (cfg.get("analytics") or "").strip()
    an = ""
    if an_cfg:
        an = '\n<meta name="ymy-analytics" content="%s">' % esc(an_cfg)
        if (cfg.get("analytics_q") or "").strip() in ("1", "yes", "true", "on"):
            an += '\n<meta name="ymy-analytics-q" content="1">'
    an += '\n<script defer src="%sassets/analytics.js?v=%s"></script>' % (base, ANALYTICS_V)
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta name="robots" content="{robots}">{can}
<meta property="og:type" content="{ogtype}">
<meta property="og:site_name" content="Guangzhou Yumengyang Auto Parts">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">{ogurl}{img}
<meta name="twitter:card" content="summary_large_image">
{favicon}
<link rel="stylesheet" href="{base}assets/style.css?v={cssv}">
{langboot}
<script defer src="{base}assets/i18n.js?v={i18nv}"></script>{an}{extra}{ld}
</head>""".format(title=esc(title), desc=esc(desc), can=can, ogurl=ogurl, robots=robots,
                 ogtype=og_type, img=img, ld=ld, langboot=LANG_BOOT, favicon=FAVICON, base=base,
                 an=an, extra=extra_scripts, cssv=CSS_V, i18nv=I18N_V)



# 联系信息（2026-11 奕然确认）：WhatsApp 走站点设置，销售电话单独一条
PHONE_SALES = "+86 195 7786 3139"
CONTACT_EMAIL = "yumengyangkefu@yumengyang.com"

def sitehead(cfg, active="", base="../"):
    keys = NAV_KEYS or ["coil", "abs", "wire", "thermo", "plug"]
    nav = []
    for key in keys[:5]:
        slug, en, _one, _cn = CAT_META.get(key, (key, key, key, key))
        cls = ' class="on"' if active == key else ""
        nav.append('<a href="%scategory/%s.html"%s data-cat="%s">%s</a>'
                   % (base, slug, cls, key, esc(en)))
    # 主导航：官网化以后产品排第二，About / Contact 都要真的能跳
    main = ('<nav class="mainnav">'
            '<a href="%sindex.html"%s data-i18n="nav_home">Home</a>'
            '<a href="%scategory/index.html"%s data-i18n="nav_products">Products</a>'
            '<a href="%scodes/index.html"%s data-i18n="nav_codes">Fault codes</a>'
            '<a href="%sabout.html"%s data-i18n="nav_about">About us</a>'
            '<a href="%scontact.html"%s data-i18n="nav_contact">Contact</a>'
            '</nav>') % (base, ' class="on"' if active == "home" else "",
                         base, ' class="on"' if active == "products" else "",
                         base, ' class="on"' if active == "codes" else "",
                         base, ' class="on"' if active == "about" else "",
                         base, ' class="on"' if active == "contact" else "")
    return """<a class="skip" href="#main">Skip to content</a>
<header class="sitehead"><div class="wrap">
<a class="brand notranslate" %s href="%sindex.html">%s<em %s>%s</em></a>
%s
<nav>%s<a href="%scategory/index.html" data-i18n="nav_all" data-v-n="%d">All %d categories</a></nav>
<div class="tools">%s<a class="wapush" href="%s" target="_blank" rel="noopener" data-i18n="wa">WhatsApp Us</a></div>
</div></header>""" % (NOTRANSLATE, base, BRAND_EN, NOTRANSLATE, BRAND_EN2,
                       main,
                       "".join(nav), base, LIVE_N or len(CAT_META), LIVE_N or len(CAT_META),
                       lang_sel_html(),
                       esc(wa_link(cfg, "Hi, I have an inquiry about auto parts.")))


def sitefoot(cfg, base="../"):
    """深色页脚：二维码 + 双号码 + 邮箱 + 地址 + 产品列表（全站共用）。"""
    wa = wa_link(cfg, "Hi, I would like a quotation for auto parts.")
    pol = " · ".join('<a href="%s%s" data-i18n="%s">%s</a>' % (base, href, k, esc(t))
                     for k, t, href in POLICY_LINKS_EN)
    prods = [("coil", "Ignition coils"), ("abs", "ABS sensors"), ("fuelpump", "Fuel pumps"),
             ("o2", "Oxygen sensors"), ("throttle", "Throttle bodies")]
    plist = "".join('<li><a href="%scategory/%s.html" data-cat="%s">%s</a></li>'
                    % (base, CAT_META.get(k, (k,))[0], k, esc(t)) for k, t in prods)
    return """<footer class="sf2">
<div class="in">
  <div>
    <div class="qrs">
      <div class="qr"><div class="box"><img src="%(base)sassets/hero/qr-wecom.webp" alt="WeCom QR" loading="lazy"></div>
        <a class="qrbtn qrbtn-wecom" href="%(qrwecom)s" target="_blank" rel="noopener" data-i18n="foot_qr_wecom">WeCom</a></div>
      <div class="qr"><div class="box"><img src="%(base)sassets/hero/qr-whatsapp.webp" alt="WhatsApp QR" loading="lazy"></div>
        <a class="qrbtn qrbtn-wa" href="%(qrwa)s" target="_blank" rel="noopener">WhatsApp</a></div>
    </div>
  </div>
  <div>
    <p class="fh" data-i18n="foot_hotline">Sales hotline</p>
    <p class="hot">%(wanum)s</p>
    <div class="line"><i>&#9742;</i><span><span data-i18n="foot_sales">Sales office</span>:
      <a href="tel:+8619577863139">%(phone)s</a></span></div>
    <div class="line"><i>&#9993;</i><span><span data-i18n="foot_email">Email</span>:
      <a href="mailto:%(mail)s">%(mail)s</a></span></div>
    <div class="line"><i>&#9873;</i><span>%(addr)s</span></div>
    <div class="line"><i>&#8632;</i><span><span data-i18n="foot_hours">Working hours</span>: %(hours)s</span></div>
  </div>
  <div>
    <p class="fh" data-i18n="foot_products">Our products</p>
    <ul class="plist">%(plist)s
      <li><a href="%(base)scategory/index.html" data-i18n="all_cat_h1">All product categories</a></li>
    </ul>
  </div>
</div>
<div class="copy">&copy; 2026 <span class="notranslate" %(nt)s>%(en)s</span>
  <a href="%(base)sindex.html" data-i18n="lookup">OE lookup</a>
  <a href="%(base)sabout.html" data-i18n="foot_about">About us</a>
  %(pol)s · <a href="%(base)ssitemap.xml" data-i18n="sitemap">Sitemap</a></div>
</footer>""" % {"nt": NOTRANSLATE, "en": esc(cfg["company_en"]),
               "addr": addr_span(cfg), "hours": esc(cfg["hours"]), "pol": pol,
               "wa": esc(wa), "wanum": esc(wa_display(cfg["whatsapp"])),
               "phone": esc(PHONE_SALES), "plist": plist,
               "mail": esc(cfg["email"]), "base": base,
               "qrwecom": esc(QR_LINK_WECOM), "qrwa": esc(QR_LINK_WHATSAPP)}


SPEC_LABELS = [("spec_oe", "OE number"), ("spec_xref", "Cross-reference"), ("spec_brand", "Brand"),
               ("spec_fit", "Vehicle fitment"), ("spec_fit_brands", "Fits brands"),
               ("spec_years", "Years"), ("spec_displ", "Displacement"), ("spec_engine", "Engine code"),
               ("spec_notes", "Notes"), ("our_sku", "Our SKU")]


LIVE_BRAND_SLUGS = set()      # 真正生成了品牌页的 slug（型号页只链这些，避免死链）


def spec_rows(it):
    rows = []
    if it.get("oe"):
        rows.append(("spec_oe", '<span style="font-variant-numeric:tabular-nums">%s</span>' % esc(it["oe"])))
    if it.get("x"):
        tags = "".join("<span>%s</span>" % esc(x) for x in it["x"][:24])
        rows.append(("spec_xref", '<div class="tags">%s</div>' % tags))
    if it.get("b"):
        rows.append(("spec_brand", esc(it["b"])))
    if it.get("a"):
        rows.append(("spec_fit", esc(it["a"])))
    else:
        rows.append(("spec_fit", '<span class="dash">&mdash;</span>'))
    if it.get("_brands") and brandlib is not None:
        bl = [b for b in it["_brands"] if brandlib.brand_slug(b) in LIVE_BRAND_SLUGS][:4]
        if bl:
            rows.append(("spec_fit_brands", '<div class="tags">%s</div>' % "".join(
                '<a href="../brand/%s.html">%s</a>' % (brandlib.brand_slug(b), esc(b)) for b in bl)))
    # 结构化适配信息（从适配车型文本里解析出来的，没解析到就不显示）
    if it.get("y"):
        rows.append(("spec_years", '<span style="font-variant-numeric:tabular-nums">%s</span>'
                     % esc(", ".join(it["y"]))))
    if it.get("d"):
        rows.append(("spec_displ", '<div class="tags">%s</div>'
                     % "".join("<span>%s</span>" % esc(x) for x in it["d"])))
    if it.get("e"):
        rows.append(("spec_engine", '<div class="tags">%s</div>'
                     % "".join("<span>%s</span>" % esc(x) for x in it["e"])))
    notes = public_notes(it.get("r"))
    if notes:
        rows.append(("spec_notes", esc(notes)))
    rows.append(("our_sku", esc(it["m"])))
    label = dict(SPEC_LABELS)
    return "".join('<tr><th data-i18n="%s">%s</th><td>%s</td></tr>' % (k, label.get(k, k), v)
                   for k, v in rows)


# ==================================================================== 内链网络
# 两块：① 同 OE / 同交叉号的其他型号  ② 同车型的热门件（不同品类、带图）
# 全部在生成时算好、写死成 <a>，页面里没有 JS 参与。每页 8–12 条，目标 10 条。
LINK_CAP = 12                 # 每页内链总数上限（需求 8–12）
BLOCK_MIN = 4                 # 单块最少 4 条（不够就逐级兜底）
LINK_TARGET = 10              # 常规每页 10 条，留 2 个空位给孤立页补齐
LINK_MIN = 8                  # 低于这个数就从同品类里补齐
LINK_EACH = 6                 # 单块最多 6 条
TOKEN_SCAN = 240              # 每个关键词最多扫多少个候选（按热度预排过）
WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9.]*")
TOKEN_STOP = {
    "THE", "AND", "FOR", "WITH", "WITHOUT", "NEW", "OLD", "FROM", "ALL", "SET", "KIT",
    "FRONT", "REAR", "LEFT", "RIGHT", "LH", "RH", "UPPER", "LOWER", "INNER", "OUTER",
    "AT", "MT", "CVT", "DCT", "DSG", "EFI", "MPI", "GDI", "LPG", "CNG", "TURBO", "TDI",
    "TSI", "TDCI", "SUV", "MPV", "SEDAN", "HATCHBACK", "COUPE", "WAGON", "PICKUP",
    "VAN", "TRUCK", "BUS", "CAB", "ENG", "ENGINE", "MODEL", "VERSION", "IMPORTED",
    "DOMESTIC", "PRESENT", "YEARS", "YEAR", "EXPORT", "OEM", "OES", "PIN", "WIRE",
    "GEN", "GEN1", "GEN2", "GEN3", "GEN4", "GEN5", "GEN6", "PLUS", "PRO", "MAX",
    "SPORT", "BASE", "TYPE", "PART", "SERIES", "CYL", "CYLINDER", "VALVE",
}


def norm_code(s):
    """OE / 交叉号归一：去掉空格、连字符、点、括号等，全部大写。"""
    return re.sub(r"[^0-9A-Z]", "", (s or "").upper())


def fit_tokens(text, limit=8):
    """从适配车型里抽品牌 / 车系关键词（Toyota、Camry、Hilux、JAC、Wuling…）。"""
    out, seen = [], set()
    for w in WORD_RE.findall(text or ""):
        t = w.upper().strip(".")
        if len(t) < 3 or len(t) > 14 or t in TOKEN_STOP or t in seen:
            continue
        seen.add(t)
        out.append(t)
        if len(out) >= limit:
            break
    return out


def build_link_index(items):
    """建两张倒排表：归一码 -> 型号；车型关键词 -> 型号（按热度预排，方便只扫前几十个）。"""
    token_map = {}
    code_map = {}
    by_i = {}
    for it in items:
        by_i[it["i"]] = it
        codes = set()
        for c in [it.get("oe")] + list(it.get("x") or []):
            n = norm_code(c)
            if len(n) >= 4:
                codes.add(n)
        it["_codes"] = codes
        for n in codes:
            code_map.setdefault(n, []).append(it["i"])
        toks = fit_tokens(it.get("a"))
        it["_toks"] = toks
        for t in toks:
            token_map.setdefault(t, []).append(it["i"])
    # 每个关键词的候选按「销量星数降序 + 编号升序」预排，扫描时只取前 120 个，够用且快
    for t, lst in token_map.items():
        lst.sort(key=lambda i: (-_sales_rank(by_i[i]), i))
    return by_i, code_map, token_map


def _rank_pick(cands, it, limit):
    """排序：同品类优先 → 销量星数高 → 编号小；去重、去掉自己。"""
    seen, out = {it["i"]}, []
    for x in cands:
        if x["i"] in seen:
            continue
        seen.add(x["i"])
        out.append(x)
    out.sort(key=lambda x: (x["cat"] != it["cat"], -_sales_rank(x), x["i"]))
    return out[:limit]


def pick_same_code(it, by_i, code_map, limit=LINK_EACH):
    """同 OE / 同交叉号的其他型号。"""
    cands = []
    for n in it["_codes"]:
        for j in code_map.get(n, ())[:300]:
            if j != it["i"]:
                cands.append(by_i[j])
    return _rank_pick(cands, it, limit)


def pick_same_cat_token(it, by_i, token_map, limit=LINK_EACH, exclude=()):
    """兜底：同品类 + 有共同车型关键词。"""
    score = {}
    for t in it["_toks"]:
        for j in token_map.get(t, ())[:TOKEN_SCAN]:
            if j == it["i"] or j in exclude:
                continue
            if by_i[j]["cat"] != it["cat"]:
                continue
            score[j] = score.get(j, 0) + 1
    cands = [by_i[j] for j in score]
    cands.sort(key=lambda x: (-score[x["i"]], -_sales_rank(x), x["i"]))
    pool = cands[:60]
    random.Random(it["i"] * 31 + 7).shuffle(pool)      # 同分里打散，入链才会摊到全站
    pool.sort(key=lambda x: -score[x["i"]])
    return pool[:limit]


def pick_same_vehicle(it, by_i, token_map, limit=LINK_EACH, exclude=()):
    """同车型的热门件：不同品类、带图、按共享关键词数 + 热度排。"""
    score = {}
    for t in it["_toks"]:
        for j in token_map.get(t, ())[:TOKEN_SCAN]:
            if j == it["i"] or j in exclude:
                continue
            x = by_i[j]
            if x["cat"] == it["cat"] or not (x.get("p") or x.get("t")):
                continue
            score[j] = score.get(j, 0) + 1
    cands = [by_i[j] for j in score]
    cands.sort(key=lambda x: (-score[x["i"]], -_sales_rank(x), x["i"]))
    pool = cands[:60]
    random.Random(it["i"] * 17 + 3).shuffle(pool)
    pool.sort(key=lambda x: -score[x["i"]])
    return pool[:limit]


def pick_links(it, by_i, code_map, token_map):
    """算出这页的两块内链。
    目标：A 块（同 OE / 同交叉号）4–6 条、B 块（同车型热门件）4–6 条，总数 8–12；
    两块都不足 4 条时按「同品类 / 不同品类」逐级兜底，保证配比稳定、不重复、不含自己。"""
    rnd = random.Random(it["i"] * 101 + 13)
    mine = {it["i"]}

    # ---- A：同 OE / 同交叉号 → 同品类+同车型关键词 → 同品类随机
    a = pick_same_code(it, by_i, code_map)
    # 只有真的按 OE/交叉号命中时，这一块的标题才配叫 "Same OE"；退化成同品类兜底时改名
    it["_lnk_oe_exact"] = bool(a)
    if len(a) < BLOCK_MIN:
        have = {x["i"] for x in a}
        a += [x for x in pick_same_cat_token(it, by_i, token_map, exclude=have, limit=LINK_EACH)
              if x["i"] not in have]
    if len(a) < BLOCK_MIN:
        have = {x["i"] for x in a}
        pool = [by_i[j] for j in by_i
                if by_i[j]["cat"] == it["cat"] and j not in have and j not in mine]
        pool.sort(key=lambda x: (-_sales_rank(x), x["i"]))
        head = pool[:60]
        rnd.shuffle(head)
        a += head
    a = a[:LINK_EACH]

    # ---- B：同车型热门件（不同品类、带图）→ 不同品类随机（带图的优先）
    used = {x["i"] for x in a} | mine
    b = pick_same_vehicle(it, by_i, token_map, exclude=used)
    if len(b) < BLOCK_MIN:
        have = used | {x["i"] for x in b}
        pool = [by_i[j] for j in by_i if by_i[j]["cat"] != it["cat"] and j not in have]
        withpic = [x for x in pool if x.get("p") or x.get("t")]
        pool = withpic or pool
        pool.sort(key=lambda x: (-_sales_rank(x), x["i"]))
        head = pool[:80]
        rnd.shuffle(head)
        b += head
    b = b[:LINK_EACH]

    # 总数压到 10 条（两块仍各 ≥4），给后面「孤立页补齐」留 2 个空位
    while len(a) + len(b) > LINK_TARGET and (len(a) > BLOCK_MIN or len(b) > BLOCK_MIN):
        if len(a) >= len(b) and len(a) > BLOCK_MIN:
            a.pop()
        elif len(b) > BLOCK_MIN:
            b.pop()
        else:
            break
    return a, b


def repair_orphans(items):
    """覆盖补齐：算完全站后，把「没人链」的页挂到同品类里有空位的页上（每页仍 ≤12 条、每块 ≤6 条）。
    这样每个型号页至少被 1 个其他页链到，孤立页降到 0。"""
    indeg = {}
    for it in items:
        for x in it["_lnk_oe"] + it["_lnk_veh"]:
            indeg[x["i"]] = indeg.get(x["i"], 0) + 1
    by_cat = {}
    for it in items:
        by_cat.setdefault(it["cat"], []).append(it)
    orphans = [it for it in items if indeg.get(it["i"], 0) == 0]
    fixed = 0
    for o in orphans:
        best = None
        for h in by_cat.get(o["cat"], ()):
            if h["i"] == o["i"]:
                continue
            na, nb = len(h["_lnk_oe"]), len(h["_lnk_veh"])
            if na + nb >= LINK_CAP:
                continue
            if any(x["i"] == o["i"] for x in h["_lnk_oe"] + h["_lnk_veh"]):
                continue
            if na < LINK_EACH and na <= nb:
                slot = h["_lnk_oe"]
            elif nb < LINK_EACH:
                slot = h["_lnk_veh"]
            elif na < LINK_EACH:
                slot = h["_lnk_oe"]
            else:
                continue
            key = (na + nb, h["i"])
            if best is None or key < best[0]:
                best = (key, slot)
        if best is None:
            continue
        best[1].append(o)
        indeg[o["i"]] = 1
        fixed += 1
    return len(orphans), fixed


def _fit_summary(it, n=44):
    """一句适配摘要：截到 n 个字符左右，尽量在词边界断。"""
    t = clean_text(it.get("a"))
    if not t:
        return (it.get("b") or "")[:n]
    if len(t) > n:
        cut = t[:n].rsplit(" ", 1)[0].rstrip(" ,;()/-")
        t = cut + "…"
    return t


def _link_card(x):
    """一张内链卡：小图（可选）+ 料号 + OE + 一句适配。纯 <a>，无 JS。"""
    img = x.get("t") or x.get("p")
    pic = ('<span class="lkimg"><img src="../%s" alt="" width="56" height="56" loading="lazy" '
           'decoding="async"></span>' % esc(img)) if img else '<span class="lkimg none" aria-hidden="true"></span>'
    oe = x.get("oe")
    oe_html = '<span class="lkoe">OE %s</span>' % esc(oe) if oe else ""
    return ('<a class="lk" href="../c/%s.html">%s<b>%s</b><span class="lkf">%s</span>%s</a>'
            % (esc(x["s"]), pic, esc(x["m"]), esc(_fit_summary(x)), oe_html))


def link_blocks_html(it):
    a = it.get("_lnk_oe") or []
    b = it.get("_lnk_veh") or []
    if not a and not b:
        return ""
    out = ['<section class="pdp-block linknet" aria-labelledby="lnk1">']
    if a:
        if it.get("_lnk_oe_exact"):
            out.append('<h2 id="lnk1"><span data-i18n="lk_oe_t">Same OE / cross-reference</span></h2>')
        else:
            out.append('<h2 id="lnk1"><span data-i18n="lk_rel_t">More from this category</span></h2>')
        out.append('<div class="lkgrid">%s</div>' % "".join(_link_card(x) for x in a))
    if b:
        out.append('<h2 id="lnk2" class="lk2h"><span data-i18n="lk_veh_t">Popular for the same vehicle</span>'
                   '</h2>')
        out.append('<div class="lkgrid">%s</div>' % "".join(_link_card(x) for x in b))
    out.append("</section>")
    return "".join(out)


SHARE_BRAND_WORDS = ("bosch", "delphi", "delco", "denso", "marelli", "magneti", "siemens", "motorola", "uaes",
                     "continental", "vdo", "sagem", "bremi", "ngk", "valeo", "hitachi", "huco", "beru",
                     "champion", "motorcraft", "acdelco", "weili", "standard", "era", "facelift")

# 剥掉品牌词之后剩下的残渣（「Siemens gen」→「gen」这种），不能当成车型写进标题
HINT_JUNK = {"gen", "new", "old", "model", "models", "type", "single", "multi", "point", "points",
             "car", "cars", "etc", "engine", "diesel", "petrol", "series", "all", "set",
             "euro", "efi", "mpi", "gdi", "obd", "at", "mt"}

# 词级清洗表：品牌 + 空壳词一起，剥开头连续命中的词
LEAD_DROP = set(SHARE_BRAND_WORDS) | HINT_JUNK | {"multi-point", "single-point", "new-model"}


def _clean_lead(text):
    """把开头连着的供应商品牌词、空壳词（gen / new / multi-point / engine …）和裸数字全部剥掉，
    这样 "Delphi gen, Wuling, Refine" → "Wuling, Refine"、"7 gen Accord" → "Accord"。"""
    words = (text or "").split()
    while words:
        w = words[0].strip(".,()[]:;/")
        low = w.lower()
        if not w:
            words.pop(0)
            continue
        parts = [p for p in re.split(r"[/\-–—]", low) if p]
        if low in LEAD_DROP or (parts and parts[0] in LEAD_DROP):
            words.pop(0)          # 品牌名 / 空壳词（含 "Siemens/VDO"、"multi-point" 这种连写）
            continue
        if re.fullmatch(r"[:\-–—/]+", w):
            words.pop(0)
            continue
        if re.fullmatch(r"[0-9]+", w):
            words.pop(0)          # 开头的裸数字（"7 gen Accord" 的 7）对车型没意义
            continue
        break
    return " ".join(words)


def _ok_hint(h):
    """兜底：剥完品牌后只剩 gen / new 之类的残渣时，宁可不写这句，也别写出 "for gen"。"""
    h = (h or "").strip()
    if len(h) < 3:
        return ""
    if re.search(r"[:|;]", h):
        return ""
    words = [w.strip(".,()") for w in h.split()]
    if words and all(w.lower() in HINT_JUNK for w in words):
        return ""
    # 去掉紧挨着的重复词（"Mazda Mazda CX-5" → "Mazda CX-5"、"Kia Kia" → "Kia"）
    dedup = []
    for w in words:
        if dedup and dedup[-1].lower() == w.lower():
            continue
        dedup.append(w)
    return " ".join(dedup)


def share_fit(it):
    """分享文案 / 页面标题里的那句适配。
    规则：① 剥掉开头的供应商品牌和空壳词；② 没有适配数据时**不拿我方品牌当车型**
    （否则会写出 "for WEILI" 这种没人看得懂的话）；③ 只剩一个光秃秃的品牌名时，
    往后找一段「品牌+车型」的，读起来更像一条真正的适配说明。"""
    apps = clean_text(it.get("a"))
    segs = [s.strip() for s in re.split(r"[;|,]", apps) if s.strip()]
    # 注意第二个参数传空串：不要退回 it["b"]（那是我方 WEILI）
    hint = _ok_hint(fitment_hint(_clean_lead(apps), ""))
    if hint and len(hint.split()) >= 2:
        return hint
    if hint and len(segs) >= 2:
        for seg in segs[1:6]:
            alt = _ok_hint(fitment_hint(_clean_lead(seg), ""))
            if alt and len(alt.split()) >= 2:
                return alt
    if hint:
        return hint
    # 整段剥完没东西了（例如整段只有 "Bosch"），退到后面几段再试一次
    if len(segs) >= 2:
        return _ok_hint(fitment_hint(_clean_lead(", ".join(segs[1:])), ""))
    return ""


def share_payload(cfg, it, cat):
    """型号页的分享文案：料号 + OE + 一句适配 + 页面 URL（服务端先渲染英文版，
    切到 zh / ar / ru 时 assets/share.js 就地重写 href 和按钮文字）。"""
    sku = it.get("m") or ""
    oe = (" (OE %s)" % it["oe"]) if it.get("oe") else ""
    fit = share_fit(it)
    page = "c/%s.html" % it["s"]
    url = rel_url(cfg, page) if has_site(cfg) else page
    text = "Check this part: %s%s. " % (sku, oe)
    if fit:
        text += "Fits %s. " % fit
    text += "OE-grade replacement - price and MOQ on WhatsApp: %s" % url
    return text, url, sku, it.get("oe") or "", fit


def share_bar_html(cfg, it, cat):
    """WhatsApp 分享 + 复制链接，两个小按钮，摆在原有 CTA 右边（同一条 flex 行，不另起一块）。"""
    text, url, sku, oe, fit = share_payload(cfg, it, cat)
    href = "https://wa.me/?text=" + quote(text, safe="")
    return """<div class="sharebar" data-sharebar>
  <a class="btn-share js-share" href="%s" target="_blank" rel="noopener nofollow"
     data-url="%s" data-sku="%s" data-oe="%s" data-fit="%s"
     title="Share on WhatsApp" aria-label="Share on WhatsApp">%s<span class="sbt">Share on WhatsApp</span></a>
  <button type="button" class="btn-copy js-copy" data-url="%s" title="Copy link" aria-label="Copy link">%s<span class="sbt">Copy link</span></button>
</div>""" % (esc(href), esc(url), esc(sku), esc(oe), esc(fit), SHARE_ICON, esc(url), COPY_ICON)


def page_model(cfg, it, cat, related=None):
    one = type_name(cat)
    primary = it.get("oe") or it.get("m")
    # share_fit 会跳过「Bosch / Delphi」这类供应商开头的段，避免写出 "... for Bosch Safe" 这种标题
    hint = share_fit(it)
    head = "%s %s" % (primary, one)
    tail_part = (" for " + hint) if hint else ""
    # 搜索结果大约 60 字符就截断，这里按「车型+全称后缀 → 车型+短后缀 → 只留车型 → 只留品名」逐级降。
    # 优先保车型关键词（买家最关心），品牌后缀放最后考虑。
    title = None
    for _tp, _sfx in ((tail_part, " | Yumengyang Auto Parts"), (tail_part, " | Yumengyang"),
                      (tail_part, ""), ("", " | Yumengyang"), ("", "")):
        _cand = head + _tp + _sfx
        if len(_cand) <= 62:
            title = _cand
            break
    if title is None:
        title = head

    apps = clean_text(it.get("a"))
    # 适配文本里的中文（如「长城H6」）不进英文站的 meta description，否则会在搜索结果摘要里露出中文
    apps = re.sub(r"[\u4e00-\u9fa5]+", " ", apps)
    apps = re.sub(r"\s{2,}", " ", apps).strip(" ,;")
    fits = apps[:120].rstrip(" ,;") if apps else ""
    tail = ". Factory-direct, ask price and MOQ on WhatsApp."
    desc = "%s %s" % (one, ("OE " + it["oe"]) if it.get("oe") else ("part " + it["m"]))
    if it.get("oe") and it.get("m"):
        desc += " (our SKU %s)" % it["m"]
    if it.get("x"):
        desc += ". Cross-reference: %s" % ", ".join(it["x"][:3])
    room = 158 - len(desc) - len(tail) - 8
    if fits and room >= 25:
        piece = fits[:room].rsplit(" ", 1)[0].rstrip(" ,;")
        if piece:
            desc += ". Fits " + piece
    desc += tail
    # 总长压到 158 以内（之前截断后又把 47 字符的 tail 接回去，最长到 202，Google 摘要会截掉后半句）
    if len(desc) > 158:
        keep = 158 - len(tail)
        cut = desc[:keep]
        desc = (cut.rsplit(" ", 1)[0] if " " in cut else cut).rstrip(" ,.;") + tail

    slug = it["s"]
    page_path = "c/%s.html" % slug
    canonical = rel_url(cfg, page_path)

    # Product schema 必备四件套：brand / sku / mpn(=OE 号) / image（没实拍图就退回品类分享图）
    ld = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": "%s %s" % (one, primary),
        "sku": it.get("m", ""),
        "mpn": it.get("oe") or it.get("m", ""),
        "brand": {"@type": "Brand", "name": it.get("b") or "WEILI"},
        "category": CAT_META[cat][1],
        "description": clean_text(desc),
        "image": [rel_url(cfg, it.get("p") or ("assets/og/%s.jpg" % cat_slug(cat)))],
        "manufacturer": {"@type": "Organization", "name": cfg["company_en"]},
    }
    if has_site(cfg):
        ld["url"] = canonical
    props = []
    if it.get("oe"):
        props.append({"@type": "PropertyValue", "name": "OE Number", "value": it["oe"]})
    if it.get("m"):
        props.append({"@type": "PropertyValue", "name": "Our SKU", "value": it["m"]})
    if it.get("b"):
        props.append({"@type": "PropertyValue", "name": "Brand", "value": it["b"]})
    for x in (it.get("x") or [])[:8]:
        props.append({"@type": "PropertyValue", "name": "Cross Reference", "value": x})
    if props:
        ld["additionalProperty"] = props

    _items = [
        {"@type": "ListItem", "position": 1, "name": "Home"},
        {"@type": "ListItem", "position": 2, "name": CAT_META[cat][1]},
        {"@type": "ListItem", "position": 3, "name": primary},
    ]
    if has_site(cfg):
        _items[0]["item"] = rel_url(cfg, "")
        _items[1]["item"] = rel_url(cfg, "category/%s.html" % cat_slug(cat))
    crumbs = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": _items}

    pic = ('<img src="../%s" alt="%s" loading="eager" decoding="async">' % (esc(it["p"]), esc("%s %s" % (one, primary)))
           if it.get("p") else
           '<div class="nopic"><span data-i18n="nopic">No photo available for this part</span><br>'
           '<span style="font-size:12px" data-i18n="nopic_sub">Ask us on WhatsApp for a real picture</span></div>')

    app_html = ('<p>%s</p>' % esc(apps)) if apps else \
        '<p data-i18n="app_fallback">Please contact us with your vehicle model and we will confirm the fitment.</p>'

    wa_text = "Hi, I am interested in %s%s. Please send me the price, MOQ and delivery time." % (
        it.get("m"), (" (OE %s)" % it["oe"]) if it.get("oe") else "")
    wa = wa_link(cfg, wa_text)

    # ---------------- 内链两块（服务端渲染的纯 <a>，爬虫不走 JS 也能爬）
    rel_html = link_blocks_html(it)

    terms = """<section class="pdp-block terms">
<h2 data-i18n="block_terms">Warranty, lead time, MOQ &amp; samples</h2>
<div class="tgrid">
  <div class="tc"><b data-i18n="t_warranty">Warranty</b>
    <span data-i18n="t_warranty_v">12–24 months depending on the part type. The exact term is written on the quotation and the invoice.</span></div>
  <div class="tc"><b data-i18n="t_lead">Lead time</b>
    <span data-i18n="t_lead_v">Stock items leave our Guangzhou warehouse in days; production depends on quantity. We confirm the date per order.</span></div>
  <div class="tc"><b data-i18n="t_moq">MOQ</b>
    <span data-i18n="t_moq_v">Set per model and packing. Send your list and we confirm the MOQ line by line — small first orders are fine.</span></div>
  <div class="tc"><b data-i18n="t_sample">Samples</b>
    <span data-i18n="t_sample_v">Available on request before a bulk order for testing; the buyer covers the freight.</span></div>
</div>
</section>"""

    terms = terms.replace('</div>\n</section>', pay_card_html() + '</div>\n</section>')

    cta_text = ("Hi, please quote %s%s. Quantity: ____. Vehicle / year: ____. Ship to: ____."
                % (it.get("m"), (" (OE %s)" % it["oe"]) if it.get("oe") else ""))
    big_cta = """<section class="pdp-cta">
<div class="pcta-t"><b data-i18n="cta_h">Need a price for this part?</b>
<span data-i18n="cta_p">Send the model and the OE number on WhatsApp — we reply with the price, MOQ and packing within one working day.</span></div>
<a class="btn-wa big" href="%s" target="_blank" rel="noopener">
  <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2a10 10 0 00-8.5 15.2L2 22l4.9-1.4A10 10 0 1012 2zm0 2a8 8 0 016.9 12l-.3.5 1 3-3.1-.9-.5.3A8 8 0 1112 4z"/></svg>
  <span data-i18n="cta_btn" data-v-n="%s">WhatsApp: %s</span></a>
</section>""" % (esc(wa_link(cfg, cta_text)), esc(it["m"]), esc(it["m"]))

    total_txt = "{:,}".format(cfg.get("_total", 0))
    body = """<body class="pdp">
%s
<main id="main" tabindex="-1" class="pdp-main">
<nav class="crumbs"><a href="../index.html" data-i18n="home">Home</a> &rsaquo; <a href="../category/%s.html" data-cat="%s">%s</a> &rsaquo; <span>%s</span></nav>
<div class="pdp-grid">
  <figure class="pdp-pic">%s</figure>
  <div class="pdp-info">
    <div class="kicker" data-cat="%s">%s</div>
    <h1><span class="sr-only">%s </span>%s</h1>
    <p class="sub2"><span data-i18n="our_sku">Our SKU</span> <b>%s</b>%s</p>
    <p class="langnote" data-i18n="langnote">Product data is shown in English</p>
    <table class="spec">%s</table>
    <div class="cta">
      <a class="btn-wa" href="%s" target="_blank" rel="noopener">
        <svg viewBox="0 0 24 24"><path d="M12 2a10 10 0 00-8.5 15.2L2 22l4.9-1.4A10 10 0 1012 2zm0 2a8 8 0 016.9 12l-.3.5 1 3-3.1-.9-.5.3A8 8 0 1112 4z"/></svg>
        <span data-i18n="btn_wa">WhatsApp for price &amp; MOQ</span>
      </a>
      <a class="btn-ghost" href="../index.html?q=%s" data-i18n="btn_search_all" data-v-n="%s">Search all %s parts</a>
      %s
    </div>
  </div>
</div>
%s
<section class="pdp-block"><h2 data-i18n="block_app">Vehicle application</h2>%s</section>
%s
<section class="pdp-block"><h2 data-i18n="block_buy">Buying this part</h2><p data-i18n="buy_text" data-v-company="%s" data-v-brand="%s">%s supplies these parts under our own brand %s. Send us the OE number on WhatsApp and we will confirm availability, price, MOQ and packing. Samples for testing are available on request.</p></section>
%s
</main>
%s
</body></html>
""" % (sitehead(cfg, cat), cat_slug(cat), cat, esc(CAT_META[cat][1]), esc(primary), pic,
       cat, esc(CAT_META[cat][1]), esc(one), esc(primary), esc(it["m"]),
       (" · <span data-i18n=\"spec_brand\">Brand</span> " + esc(it["b"])) if it.get("b") else "",
       spec_rows(it), esc(wa), quote(it.get("oe") or it["m"], safe=""),
       total_txt, total_txt, share_bar_html(cfg, it, cat),
       terms, app_html, rel_html,
       esc(cfg["company_en"]), esc(it.get("b") or "WEILI"),
       esc(cfg["company_en"]), esc(it.get("b") or "WEILI"),
       big_cta, sitefoot(cfg))

    og_img = it.get("p") or ("assets/og/%s.jpg" % cat_slug(cat))
    return head_block(cfg, title, desc, canonical, og_img, "website", [ld, crumbs],
                      extra_scripts='\n<script defer src="../assets/share.js"></script>') + "\n" + body


def load_pricing():
    """读 品类定价.txt：key|moq|币种|最低价|最高价|备注"""
    path = os.path.join(HERE, "品类定价.txt")
    out = {}
    if not os.path.exists(path):
        return out
    with open(path, encoding="utf-8") as fh:
        lines = fh.readlines()
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "|" not in line:
            continue
        p = [x.strip() for x in line.split("|")]
        if len(p) < 5:
            continue
        def num(x):
            try:
                return float(x)
            except Exception:
                return None
        out[p[0]] = {"moq": p[1], "cur": p[2] or "USD", "lo": num(p[3]), "hi": num(p[4])}
    return out


PRICING = {}


def price_html(key):
    d = PRICING.get(key)
    if not d or not d.get("moq"):
        return ""
    if d.get("lo") is not None and d.get("hi") is not None:
        lo, hi = ("%g" % d["lo"]), ("%g" % d["hi"])
        return ('<div class="priceline"><b data-i18n="price_range" data-v-moq="%s" data-v-cur="%s" '
                'data-v-lo="%s" data-v-hi="%s">MOQ %s pcs · %s %s–%s / pc · FOB Guangzhou</b>'
                '<span data-i18n="price_note">Final price depends on quantity and packing — '
                'we confirm it in the quotation.</span></div>'
                % (d["moq"], d["cur"], lo, hi, d["moq"], d["cur"], lo, hi))
    return ('<div class="priceline"><b data-i18n="price_req" data-v-moq="%s">MOQ %s pcs · Price on quotation</b>'
            '<span data-i18n="price_note">Final price depends on quantity and packing — '
            'we confirm it in the quotation.</span></div>' % (d["moq"], d["moq"]))


def page_category(cfg, cat, all_items, page_items, page_no, total_pages):
    slug, en, one, cn = CAT_META[cat]
    fname = "%s.html" % slug if page_no == 1 else "%s-%d.html" % (slug, page_no)
    if total_pages > 1:
        title = "%s — page %d of %d (%d models) | Guangzhou Yumengyang Auto Parts" % (
            en, page_no, total_pages, len(all_items))
    else:
        title = "%s — %d models with OE numbers | Guangzhou Yumengyang Auto Parts" % (en, len(all_items))
    desc = "Browse all %d %s. Each part links to its OE number, cross-reference and vehicle fitment. Guangzhou Yumengyang Auto Parts." % (len(all_items), en.lower())
    canonical = rel_url(cfg, "category/%s" % fname)
    lis = "".join(
        '<li><a href="../c/%s.html"><b>%s</b><span>%s</span></a></li>' % (
            esc(it["s"]), esc(it.get("oe") or it["m"]),
            esc(it["m"]) if it.get("oe") else "")
        for it in page_items)

    pager = ""
    if total_pages > 1:
        links = []
        for p in range(1, total_pages + 1):
            href = "%s.html" % slug if p == 1 else "%s-%d.html" % (slug, p)
            if p == page_no:
                links.append('<b>%d</b>' % p)
            else:
                links.append('<a href="%s">%d</a>' % (href, p))
        pager = ('<div class="pager"><span data-i18n="page_of" data-v-p="%d" data-v-t="%d">Page %d / %d</span> %s</div>'
                 % (page_no, total_pages, page_no, total_pages, " ".join(links)))

    if total_pages > 1:
        a = (page_no - 1) * 700 + 1
        b = (page_no - 1) * 700 + len(page_items)
        modh = ('<span data-i18n="models_range" data-v-a="%d" data-v-b="%d" data-v-n="%d">Models %d–%d of %d</span>'
                % (a, b, len(all_items), a, b, len(all_items)))
    else:
        modh = '<span data-i18n="all_models" data-v-n="%d">All models (%d)</span>' % (len(all_items), len(all_items))

    # 品类页 → 故障码页的入链（反向映射从 codes_content 的 parts 算，双向内链加速收录）
    code_hint = ""
    _cl = [c["code"] for c in _code_list()
           if any(k == cat for k, _n in (c.get("parts") or []))]
    if _cl:
        code_hint = ' &middot; <span data-i18n="codes_h">Fault codes</span>: ' + " ".join(
            '<a href="../codes/%s.html">%s</a>' % (esc(x.lower()), esc(x)) for x in _cl[:10])

    body = """<body>
%s
<main id="main" tabindex="-1" class="cat-main">
<nav class="crumbs"><a href="../index.html" data-i18n="home">Home</a> &rsaquo; <span data-cat="%s">%s</span></nav>
<div class="cat-head">
  <h1><span data-cat="%s">%s</span> <span class="h1sub zh-extra">%s</span></h1>
  <p data-i18n="cat_lead">Every %s we stock, with OE number and cross-reference. Click a part number to see fitment, photos and a WhatsApp quote button.</p>
  <div class="stat"><span data-i18n="models_n" data-v-n="%d">%d models</span> · <a href="../index.html" data-i18n="search_oe">search by OE number</a> · <a href="../index.html?cat=%s" data-i18n="filter_search">filter on the search page</a>%s</div>
  %s
</div>
<div class="modlist"><h2>%s</h2><ul class="modgrid">%s</ul>%s</div>
</main>
%s
</body></html>
""" % (sitehead(cfg, cat), cat, esc(en), cat, esc(en), esc(cn), esc(one),
       len(all_items), len(all_items), cat, code_hint, price_html(cat), modh, lis, pager, sitefoot(cfg))
    return head_block(cfg, title, desc, canonical, "assets/og/%s.jpg" % slug, "website",
                      noindex=not all_items) + "\n" + body


def page_cat_index(cfg, cats, by_cat):
    live = [c for c in order_cats(cats) if by_cat.get(c["key"])]   # 0 型号的品类不摆入口
    total = sum(len(by_cat.get(c["key"], [])) for c in live)
    title = "All %d product categories — %d part numbers | Guangzhou Yumengyang Auto Parts" % (len(live), total)
    desc = ("Ignition coils, ABS sensors, oxygen sensors, fuel pumps, TPMS, throttle bodies and more — "
            "%d part numbers with OE cross-reference." % total)
    cards = []
    for c in live:
        key = c["key"]
        slug, en, one, cn = CAT_META.get(key, (key, key, key, key))
        n = len(by_cat.get(key, []))
        cards.append('<a class="catcard" href="%s.html"><b data-cat="%s">%s</b><span class="zh-extra">%s</span>'
                     '<em data-i18n="cat_arrow" data-v-n="%d">%d models →</em></a>'
                     % (slug, key, esc(en), esc(cn), n, n))
    body = """<body>
%s
<main id="main" tabindex="-1" class="cat-main">
<nav class="crumbs"><a href="../index.html" data-i18n="home">Home</a> &rsaquo; <span data-i18n="all_cat_h1">All categories</span></nav>
<div class="cat-head">
  <h1><span data-i18n="all_cat_h1">All product categories</span> <span class="h1sub zh-extra">全部品类</span></h1>
  <p data-i18n="all_cat_lead" data-v-c="%d" data-v-n="%d">%d categories, %d part numbers. Pick a category to see every model with its OE number, cross-reference and fitment.</p>
  <div class="stat"><a href="../index.html" data-i18n="search_oe_btn">Search by OE number</a></div>
</div>
<div class="catcards">%s</div>
</main>
%s
</body></html>
""" % (sitehead(cfg), len(live), total, len(live), total, "".join(cards), sitefoot(cfg))
    return head_block(cfg, title, desc, rel_url(cfg, "category/index.html"), "", "website") + "\n" + body


# ------------------------------------------------------------------ 品牌页 / 车型页（长尾落地页）
def _cat_groups(items):
    """按品类分组，型号多的品类排前面。"""
    g = {}
    for it in items:
        g.setdefault(it["cat"], []).append(it)
    return [(k, g[k]) for k in sorted(g, key=lambda c: (-len(g[c]), c))]


def _model_grid(lst, per_cat=40):
    """型号网格（和品类页同一个 modgrid 样式）。"""
    lis = "".join(
        '<li><a href="../c/%s.html"><b>%s</b><span>%s</span></a></li>' % (
            esc(it["s"]), esc(it.get("oe") or it["m"]),
            esc(it["m"]) if it.get("oe") else "")
        for it in lst[:per_cat])
    return '<ul class="modgrid">%s</ul>' % lis


def _cat_blocks(items, per_cat=40):
    blocks = []
    for cat, lst in _cat_groups(items):
        slug, en, _one, _cn = CAT_META.get(cat, (cat, cat, cat, cat))
        more = ""
        if len(lst) > per_cat:
            more = ('<p class="stat"><a href="../category/%s.html">'
                    '<span data-i18n="see_all_cat" data-v-n="%d" data-v-cat="%s" data-v-cat-en="%s">'
                    'See all %d %s</span></a></p>'
                    % (slug, len(lst), cat, esc(en.lower()), len(lst), esc(en.lower())))
        blocks.append('<div class="modlist"><h2><a href="../category/%s.html" data-cat="%s">%s</a> '
                      '<em>(%d)</em></h2>%s%s</div>'
                      % (slug, cat, esc(en), len(lst), _model_grid(lst, per_cat), more))
    return "".join(blocks)


def _chips(links):
    """一排小链接（车型 / 品牌跳转）。"""
    if not links:
        return ""
    return ('<p class="stat">%s</p>' % " · ".join(
        '<a href="%s">%s</a>' % (esc(h), esc(t)) for h, t in links))


def _itemlist_ld(name, cfg, items, path_prefix):
    return {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": name,
        "numberOfItems": len(items),
        "itemListElement": [
            {"@type": "ListItem", "position": n + 1,
             "url": rel_url(cfg, "%s/%s.html" % (path_prefix, it["s"])),
             "name": it.get("oe") or it["m"]}
            for n, it in enumerate(items[:50])],
    }


def _crumbs_ld(cfg, trail):
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": name,
             **({"item": rel_url(cfg, path)} if has_site(cfg) and path is not None else {})}
            for i, (name, path) in enumerate(trail)],
    }


def page_brands_index(cfg, entries, cover):
    total = cover
    title = "Vehicle brands — %d brand pages, %d part numbers | Yumengyang Auto Parts" % (len(entries), total)
    desc = ("Browse our part numbers by vehicle brand: Toyota, Hyundai, Kia, BMW, Ford, Volkswagen and %d more. "
            "OE numbers, cross-references and photos on every part." % max(0, len(entries) - 5))
    cards = "".join(
        '<a class="catcard" href="%s.html"><b>%s</b>'
        '<em data-i18n="cat_arrow" data-v-n="%d">%d models →</em></a>' % (
            esc(e["slug"]), esc(e["canon"]), e["n"], e["n"])
        for e in entries)
    body = """<body>
%(head)s
<main id="main" tabindex="-1" class="cat-main">
<nav class="crumbs"><a href="../index.html" data-i18n="home">Home</a> &rsaquo;
<span data-i18n="brands_crumb">Brands</span></nav>
<div class="cat-head">
  <h1 data-i18n="brand_idx_h1">Browse by vehicle brand</h1>
  <p data-i18n="brand_idx_lead" data-v-b="%(nb)d" data-v-n="%(n)d">Parts are grouped by the brand they fit.
  %(nb)d brands, %(n)d part numbers — each part links to its OE number,
  cross-reference, photos and a WhatsApp quote button.</p>
  <div class="stat"><a href="../index.html" data-i18n="search_oe_btn">Search by OE number</a> ·
  <a href="../vehicle/index.html" data-i18n="browse_vehicle">Browse by vehicle</a> ·
  <a href="../category/index.html" data-i18n="all_cat_h1">All categories</a></div>
</div>
<div class="catcards">%(cards)s</div>
</main>
%(foot)s
</body></html>
""" % dict(head=sitehead(cfg, base="../"), nb=len(entries), n=total, cards=cards, foot=sitefoot(cfg))
    return head_block(cfg, title, desc, rel_url(cfg, "brand/index.html"), "", "website",
                      [_crumbs_ld(cfg, [("Home", ""), ("Brands", "brand/index.html")])]) + "\n" + body


def page_brand(cfg, e):
    canon, slug, items = e["canon"], e["slug"], e["items"]
    n = e["n"]
    cats = _cat_groups(items)
    cat_txt = ", ".join(CAT_META.get(k, (k, k))[1] for k, _ in cats[:4])
    title = "%s parts — %d part numbers with OE numbers | Yumengyang" % (canon, n)
    desc = ("%s: %d part numbers — %s. Every part lists its OE number, cross-reference and photo. "
            "Ask for a price and MOQ on WhatsApp." % (canon, n, cat_txt))
    trail = [("Home", ""), ("Brands", "brand/index.html"), (canon, None)]
    model_links = [("../vehicle/%s.html" % brandlib.token_slug(t), t) for t, _n in e["tokens"][:14]]
    xfit_links = [("../vehicle/%s.html" % brandlib.token_slug(t), t) for t, _n in (e.get("xfit") or [])[:14]]
    # 「本品牌车型」只列归属确凿的；一个都没有就整块不出现，不留空标题。
    # 英文原文里直接写品牌名（en 走页面兜底），其它语种由 i18n.js 的 {b} 占位符填。
    models_block = ""
    if model_links:
        models_block = ('<div class="modlist"><h2 data-i18n="brand_models_h2" data-v-b="%s">%s models</h2>%s</div>'
                        % (esc(canon), esc(canon), _chips(model_links)))
    # 跨品牌共通件单独一块，措辞诚实：这些车型也用这些件，但不是本品牌车型。
    xfit_block = ""
    if xfit_links:
        xfit_block = ('<div class="modlist"><h2 data-i18n="brand_xfit_h2">Cross-compatible models</h2>%s</div>'
                      % _chips(xfit_links))
    others = [("../brand/%s.html" % o["slug"], o["canon"]) for o in e["others"][:18]]
    body = """<body>
%(head)s
<main id="main" tabindex="-1" class="cat-main">
<nav class="crumbs"><a href="../index.html" data-i18n="home">Home</a> &rsaquo;
<a href="index.html" data-i18n="brands_crumb">Brands</a> &rsaquo; <span>%(brand)s</span></nav>
<div class="cat-head">
  <h1><span data-i18n="brand_parts_h1" data-v-b="%(brand)s">%(brand)s parts</span>
  <span class="stat"><span data-i18n="parts_n_paren" data-v-n="%(n)d">(%(n)d part numbers)</span></span></h1>
  <p data-i18n="brand_lead" data-v-b="%(brand)s">Ignition coils, sensors, fuel pumps and other parts for %(brand)s.
  Each part links to its OE number, cross-reference, fitment and photos.
  Send us the OE number on WhatsApp for price, MOQ and packing.</p>
  <div class="stat"><a href="../index.html?q=%(brand)s" data-i18n="brand_search_oe" data-v-b="%(brand)s">Search %(brand)s parts by OE number</a> ·
  <a href="../category/index.html" data-i18n="all_cat_h1">All categories</a></div>
</div>
%(cats)s
%(models_block)s%(xfit_block)s
<div class="modlist"><h2 data-i18n="brand_others_h2">Other brands</h2>%(others)s</div>
</main>
%(foot)s
</body></html>
""" % dict(head=sitehead(cfg, base="../"), brand=esc(canon), n=n, cats=_cat_blocks(items),
           models_block=models_block, xfit_block=xfit_block, others=_chips(others), foot=sitefoot(cfg))
    ld = [_crumbs_ld(cfg, trail), _itemlist_ld("%s parts" % canon, cfg, items, "c")]
    return head_block(cfg, title, desc, rel_url(cfg, "brand/%s.html" % slug), "", "website", ld) + "\n" + body


def page_vehicles_index(cfg, entries, cover):
    total = cover
    title = "Vehicle fitment — %d models covered, %d part numbers | Yumengyang Auto Parts" % (len(entries), total)
    desc = ("Find parts by vehicle: %d models and generations, %d part numbers with OE numbers and "
            "cross-references." % (len(entries), total))
    chips = " · ".join(
        '<a href="%s.html">%s <em>(%d)</em></a>' % (esc(e["slug"]), esc(e["token"]), e["n"])
        for e in entries)
    body = """<body>
%(head)s
<main id="main" tabindex="-1" class="cat-main">
<nav class="crumbs"><a href="../index.html" data-i18n="home">Home</a> &rsaquo;
<span data-i18n="vehicles_crumb">Vehicles</span></nav>
<div class="cat-head">
  <h1 data-i18n="browse_vehicle">Browse by vehicle</h1>
  <p data-i18n="veh_idx_lead" data-v-v="%(nv)d" data-v-n="%(n)d">Model names taken from our fitment data.
  %(nv)d vehicles, %(n)d part numbers. Pick a vehicle to see every compatible part with its OE number.</p>
  <div class="stat"><a href="../index.html" data-i18n="search_oe_btn">Search by OE number</a> ·
  <a href="../brand/index.html" data-i18n="browse_brand">Browse by brand</a> ·
  <a href="../category/index.html" data-i18n="all_cat_h1">All categories</a></div>
</div>
<div class="modlist"><h2><span data-i18n="all_veh_h2" data-v-n="%(nv)d">All vehicles (%(nv)d)</span></h2>
<p class="vehiclechips">%(chips)s</p></div>
</main>
%(foot)s
</body></html>
""" % dict(head=sitehead(cfg, base="../"), nv=len(entries), n=total, chips=chips, foot=sitefoot(cfg))
    return head_block(cfg, title, desc, rel_url(cfg, "vehicle/index.html"), "", "website",
                      [_crumbs_ld(cfg, [("Home", ""), ("Vehicles", "vehicle/index.html")])]) + "\n" + body


def page_vehicle(cfg, e):
    token, slug, items = e["token"], e["slug"], e["items"]
    n = e["n"]
    cats = _cat_groups(items)
    cat_txt = ", ".join(CAT_META.get(k, (k, k))[1] for k, _ in cats[:4])
    title = "%s parts — %d part numbers by OE number | Yumengyang" % (token.title(), n)
    desc = ("Parts for %s: %d part numbers — %s. OE numbers, cross-references and photos; "
            "quote on WhatsApp." % (token.title(), n, cat_txt))
    trail = [("Home", ""), ("Vehicles", "vehicle/index.html"), (token.title(), None)]
    brand_chips = [("../brand/%s.html" % b["slug"], b["canon"])
                   for b in e["brands"] if b["slug"] in LIVE_BRAND_SLUGS][:6]
    others = [("../vehicle/%s.html" % o["slug"], o["token"]) for o in e["others"][:16]]
    body = """<body>
%(head)s
<main id="main" tabindex="-1" class="cat-main">
<nav class="crumbs"><a href="../index.html" data-i18n="home">Home</a> &rsaquo;
<a href="index.html" data-i18n="vehicles_crumb">Vehicles</a> &rsaquo; <span>%(veh)s</span></nav>
<div class="cat-head">
  <h1><span data-i18n="brand_parts_h1" data-v-b="%(veh)s">%(veh)s parts</span>
  <span class="stat"><span data-i18n="parts_n_paren" data-v-n="%(n)d">(%(n)d part numbers)</span></span></h1>
  <p data-i18n="veh_lead" data-v-v="%(veh)s">Parts that fit the %(veh)s. Each part lists its OE number,
  cross-reference, fitment and photos. Send us the OE number on WhatsApp for price, MOQ and packing.</p>
  <div class="stat"><a href="../index.html?q=%(tok)s" data-i18n="search_oe_btn">Search by OE number</a> ·
  <a href="../category/index.html" data-i18n="all_cat_h1">All categories</a></div>
</div>
%(cats)s
<div class="modlist"><h2 data-i18n="veh_brands_h2">Fits vehicles from</h2>%(brands)s</div>
<div class="modlist"><h2 data-i18n="veh_others_h2">Other vehicles</h2>%(others)s</div>
</main>
%(foot)s
</body></html>
""" % dict(head=sitehead(cfg, base="../"), veh=esc(token.title()), tok=esc(token), n=n,
           cats=_cat_blocks(items), brands=_chips(brand_chips), others=_chips(others),
           foot=sitefoot(cfg))
    ld = [_crumbs_ld(cfg, trail), _itemlist_ld("%s parts" % token.title(), cfg, items, "c")]
    return head_block(cfg, title, desc, rel_url(cfg, "vehicle/%s.html" % slug), "", "website", ld) + "\n" + body


# ------------------------------------------------------------------ 政策页（英文为主 + 底部中文摘要）
POLICY_DATE = "2026-11-10"
POLICY_DATE_TXT = "10 November 2026"   # 改这里要同步 i18n.js 的 policy_date（各语种当地写法）

PRIVACY_SECTIONS = [
    ("priv_s1_h", "What this policy covers",
     ("priv_s1_p",
      "This policy explains what data we handle when you use our part-number lookup site and when you "
      "contact us about a part. It does not cover other companies' sites that we link to.")),
    ("priv_s2_h", "Information you give us",
     ("priv_s2_p",
      "We only receive what you send us: your name, company and country, the part numbers and quantities "
      "you ask about, vehicle details, order information and any photos or documents you attach. You can "
      "send this by WhatsApp, email or any other channel you choose.")),
    ("priv_s3_h", "Information collected automatically",
     ("priv_s3_p",
      "Our hosting provider keeps standard web-server logs (IP address, browser, page requested, time) to "
      "run the site and block abuse. The site also remembers your language choice in your own browser "
      "(local storage key <code>ymy_lang</code>); that value stays on your device and is not sent to us.")),
    ("priv_s4_h", "Cookies & statistics",
     ("priv_s4_p1",
      "We set no cookies at all — not for advertising, not for statistics. The language preference is stored "
      "in your browser as local storage, not as a cookie, and clearing your browser data removes it."),
     ("priv_s4_p2",
      "Page views are counted in aggregate with a cookieless counter (GoatCounter): it receives the page path, "
      "the referring page and your browser language. It sets no cookie and keeps no identifier that would let "
      "us recognise you, so what we see is &quot;this page was opened N times from this country&quot;, not who "
      "opened it. Search terms typed into the part-number lookup may be recorded as part numbers only. If your "
      "browser sends the Do Not Track signal, the counter stays off.")),
    ("priv_s5_h", "How we use your information",
     ("priv_s5_p",
      "To answer your inquiry, prepare a quotation, arrange production and shipping, keep the records our "
      "accounting and export paperwork require, and to find and fix faults on the site. We do not use your "
      "inquiry to build advertising profiles.")),
    ("priv_s6_h", "Who we share it with",
     ("priv_s6_p",
      "We share data only where it is needed to serve you: our hosting provider (GitHub Pages) processes "
      "access logs; WhatsApp (Meta) handles messages you choose to send us there; freight forwarders, "
      "couriers and customs authorities receive the shipping details required for delivery. "
      "We do not sell or rent your data, and we do not pass your customer list to other buyers.")),
    ("priv_s7_h", "How long we keep it",
     ("priv_s7_p",
      "Inquiry and order records are kept for as long as we need them to serve you and to meet legal, tax "
      "and export requirements. Marketing messages stop as soon as you ask us to stop.")),
    ("priv_s8_h", "Your choices",
     ("priv_s8_p",
      "You can ask us for a copy of the information you sent, ask us to correct it, or ask us to delete it. "
      "Write to the email address below and we will act on the request. Deleting an inquiry record may end "
      "our ability to quote or support that order.")),
    ("priv_s9_h", "Security",
     ("priv_s9_p",
      "We keep inquiry data on access-controlled systems and limit it to the staff who deal with your order. "
      "No system is perfectly secure, and messages sent over WhatsApp or ordinary email are not end-to-end "
      "encrypted by us.")),
    ("priv_s10_h", "Children",
     ("priv_s10_p",
      "This site is a business-to-business parts catalogue. It is not directed at children and we do not "
      "knowingly collect their data.")),
    ("priv_s11_h", "Changes to this policy",
     ("priv_s11_p",
      "If we change how we handle data, we update this page and the date above. The version published here "
      "is the one that applies.")),
]
PRIVACY_ZH = [
    "本政策说明：使用本站型号查询、或通过 WhatsApp / 邮件联系我们时，我们处理哪些数据。",
    "你主动提供的：姓名、公司、国家、询价型号与数量、车型信息、订单信息，以及你附上的照片或文件。",
    "自动记录的：托管方的服务器日志（IP、浏览器、访问页面、时间）；语言偏好存在你自己浏览器的 "
    "localStorage（键名 ymy_lang），不上传给我们。",
    "Cookie：本站不设置任何 Cookie；语言偏好用 localStorage 保存，清浏览器数据即可清除。页面浏览用无 Cookie 的 "
    "GoatCounter 做汇总计数，只记页面路径、来源页和浏览器语言，不存标识、认不出是谁；首页搜索框里输入的型号/OE 号"
    "可能被记下来（只记号码）。浏览器发 Do Not Track 时不统计。",
    "用途：回复询盘、报价、安排生产与发货、保存报关与财务所需的记录、修复站点故障。",
    "共享范围：托管方（GitHub Pages）处理访问日志；你主动使用的 WhatsApp 由 Meta 处理；货代、快递与海关"
    "只拿到发货必需的信息。我们不出售、不出租你的数据，也不会把你的客户名单给别的买家。",
    "你的权利：可以要求查看、更正或删除你发来的信息，发邮件到下方邮箱即可。",
    "安全：询盘数据放在有访问控制的系统里，只给处理你订单的同事看；WhatsApp 和普通邮件本身不是端到端加密。",
    "本页不面向未成年人；政策有变化时更新本页与上方日期。",
]

RETURNS_SECTIONS = [
    ("ret_s1_h", "Overview",
     ("ret_s1_p",
      "We want the part to fit and to work. If something is wrong, contact us first — before you send "
      "anything back — so we can confirm the case and give you a return authorization (RMA) number. "
      "Parts sent back without an RMA number may be refused or delayed at customs.")),
    ("ret_s2_h", "What the warranty covers",
     ("ret_s2_p",
      "Our parts carry a warranty of 12 to 24 months depending on the part type. The exact term for your "
      "order is written on the quotation and on the invoice, so the same number applies to both sides. "
      "The warranty covers manufacturing defects that appear under normal use on the vehicle the part is "
      "listed for.")),
    ("ret_s3_h", "What is not covered",
     ("ret_s3_p",
      "The warranty does not cover: damage from an accident, collision or fire; wrong installation or "
      "installation with damaged wiring, connectors or voltage problems; misuse, neglect, water ingress or "
      "unauthorized repair and modification; normal wear; a part ordered for the wrong vehicle because the "
      "OE number or cross-reference was not checked; and transit damage that is not reported to us with the "
      "carrier's record.")),
    ("ret_s4_h", "How to make a claim",
     ("ret_s4_p",
      "1) Send us the invoice or order number and the part number. 2) Send photos or a short video of the "
      "part and, where possible, of the vehicle and the fault code. 3) Tell us the vehicle model, year and "
      "engine, and what the part is doing wrong. 4) We review the case — each case is judged on its own "
      "evidence, and we may ask for the part to be tested. 5) If the claim is accepted we issue an RMA "
      "number and agree with you whether the part is replaced, credited or refunded.")),
    ("ret_s5_h", "Shipping and timing",
     ("ret_s5_p",
      "Return freight is paid by the buyer unless the fault is ours (wrong part sent, part not as "
      "described, or a defect confirmed by us). We confirm who pays in writing before the return ships. "
      "Inspection and the replacement or credit are handled case by case; we give you the expected timing "
      "in writing with the RMA number rather than promising a fixed number of days here.")),
    ("ret_s6_h", "Replacements and refunds",
     ("ret_s6_p",
      "Where a claim is accepted we replace the part, issue a credit note against your next order, or refund "
      "the invoice value — whichever we agree in writing. Refunds go back through the original payment "
      "channel where that is possible.")),
    ("ret_s7_h", "Contact",
     ("ret_s7_p",
      "Send claims and questions to the WhatsApp number or email address below. Please include the order "
      "number so we can find your file quickly.")),
]
RETURNS_ZH = [
    "先把问题告诉我们，再寄回：没有 RMA 号的退货可能被拒收或在海关卡住。",
    "质保范围：按品类 12–24 个月，具体年限写在报价单和发票上；保的是正常使用下出现的制造缺陷。",
    "不保：事故/碰撞/火烧、装错或线路与电压问题导致的损坏、误用与私拆改装、正常磨损、"
    "没核对 OE 号买错车型、以及没有当场向承运方登记的运输破损。",
    "流程：提供发票或订单号 + 型号 → 拍照片/短视频（含车型与故障码更好）→ 说明车型年款与故障现象 → "
    "我们逐案评估（可能要寄回检测）→ 通过后给 RMA 号，并确认换货、冲抵还是退款。",
    "运费与时限：非我方责任由买家承担回运运费，谁付在寄回前书面确认；检测与换补时间逐案给出，"
    "我们按 RMA 号书面告知预计时间，不在页面上写死天数。",
    "换补与退款：按书面确认的方式换货、开冲抵单或退发票金额；能原路退回就原路退回。",
    "联系：把订单号一起发到下方 WhatsApp 或邮箱，我们好尽快找到你的档案。",
]


def _sections_html(secs):
    """政策页正文：每节 = (标题 key, 英文标题, [(段落 key, 英文段落 html), ...])。"""
    out = []
    for hk, hen, *paras in secs:
        body = "".join('<p data-i18n-html="%s">%s</p>' % (pk, ph) for pk, ph in paras)
        out.append('<section class="dsec"><h2 data-i18n="%s">%s</h2>%s</section>'
                   % (hk, esc(hen), body))
    return "".join(out)


def page_policy(cfg, kind):
    """kind = 'privacy' | 'returns'。英文正文 + 底部 <details> 中文摘要，同站同头同脚。"""
    if kind == "privacy":
        title = "Privacy Policy | Guangzhou Yumengyang Auto Parts"
        desc = ("What data Guangzhou Yumengyang Auto Parts handles when you use the OE number lookup or "
                "send an inquiry, why we keep it, and who we share it with.")
        h1 = "Privacy Policy"
        secs, zh, fname = PRIVACY_SECTIONS, PRIVACY_ZH, "privacy.html"
        hkey, lkey = "priv_h1", "priv_lead"
        lead = ("We keep this short and specific: what we receive, why we keep it, and how to have it "
                "removed.")
    else:
        title = "Refund & Returns Policy | Guangzhou Yumengyang Auto Parts"
        desc = ("Warranty, returns and claims for Guangzhou Yumengyang Auto Parts: what is covered, what "
                "is not, how to get an RMA number, and who pays the freight.")
        h1 = "Refund & Returns"
        secs, zh, fname = RETURNS_SECTIONS, RETURNS_ZH, "returns.html"
        hkey, lkey = "ret_h1", "ret_lead"
        lead = ("Contact us before you ship anything back. Below is what the warranty covers, what it does "
                "not, and how a claim is handled.")

    zh_html = "".join("<li>%s</li>" % esc(x) for x in zh)
    canon = rel_url(cfg, fname)
    ld = {"@context": "https://schema.org", "@type": "WebPage",
          "name": h1, "description": clean_text(desc), "dateModified": POLICY_DATE,
          "inLanguage": "en", "isPartOf": {"@type": "WebSite", "url": cfg["site_url"] + "/"}}
    if has_site(cfg):
        ld["url"] = canon

    wa = wa_link(cfg, "Hi, I have a question about %s." % h1.lower())
    body = """<body class="docpage">
%(head)s
<main id="main" tabindex="-1" class="policy">
<nav class="crumbs"><a href="index.html" data-i18n="home">Home</a> &rsaquo; <span data-i18n="%(hkey)s">%(h1)s</span></nav>
<article class="doc">
  <h1 data-i18n="%(hkey)s">%(h1)s</h1>
  <p class="docmeta"><span data-i18n="policy_upd">Last updated</span> <span data-i18n="policy_date">%(d)s</span> · <span data-i18n="doc_ref">English version is the reference</span></p>
  <p class="doclead" data-i18n="%(lkey)s">%(lead)s</p>
  %(secs)s
  <details class="doczh"><summary>中文摘要 · Chinese summary</summary><ul>%(zh)s</ul></details>
  <section class="doccontact">
    <h2 data-i18n="foot_contact">Contact</h2>
    <p class="docorg"><b class="notranslate" %(nt)s>%(brandcn)s</b> · <span class="notranslate" %(nt)s>%(company)s</span></p>
    <p class="docaddr">%(addr)s</p>
    <p><span data-i18n="foot_hours">Working hours</span>: %(hours)s</p>
    <p data-i18n="foot_contact_via">Questions about this page? WhatsApp or email us — we answer within one working day.</p>
    <p><a class="btn-wa" href="%(wa)s" target="_blank" rel="noopener">%(walabel)s</a>
       <a class="btn-ghost" href="index.html" data-i18n="nf_back">Back to the lookup home</a></p>
  </section>
</article>
</main>
%(foot)s
<script>(function(){function f(){try{var d=document.querySelector('.doczh');if(d&&window.I18N&&window.I18N.lang==='zh')d.open=true;}catch(e){}}
document.addEventListener('DOMContentLoaded',f);document.addEventListener('i18n:change',f);
try{if(document.documentElement.getAttribute('data-lang')==='zh')document.querySelector('.doczh').open=true;}catch(e){}})();</script>
</body></html>
""" % dict(head=sitehead(cfg, "", base=""), hkey=hkey, h1=esc(h1), lkey=lkey,
           d=POLICY_DATE_TXT, lead=esc(lead), secs=_sections_html(secs), zh=zh_html,
           nt=NOTRANSLATE, brandcn=esc(BRAND_CN), company=esc(cfg["company_en"]),
           addr=addr_span(cfg), hours=esc(cfg["hours"]), wa=esc(wa),
           walabel=esc("WhatsApp " + wa_display(cfg["whatsapp"])), foot=sitefoot(cfg, base=""))
    return head_block(cfg, title, desc, canon, "assets/og/og-default.webp", "website",
                      [ld], base="") + "\n" + body


# ------------------------------------------------------------------ 公司介绍页

# About 页的「最后更新」：改内容时手动改这一行，别用生成时间，否则每次构建都自称刚更新过
ABOUT_DATE_TXT = "7 November 2026"   # 改这里要同步 i18n.js 的 about_date



def _about_body(parts):
    """About 页正文：("key", "英文原文") = 一段；列表 = <ul>；("raw", html) = 原样插入。"""
    out = []
    for p in parts:
        if isinstance(p, list):
            out.append("<ul>%s</ul>" % "".join(
                '<li data-i18n="%s">%s</li>' % (k, esc(v)) for k, v in p))
        elif p[0] == "raw":
            out.append(p[1])
        else:
            out.append('<p data-i18n="%s">%s</p>' % (p[0], esc(p[1])))
    return "".join(out)


def page_about(cfg):
    """公司介绍页：说真话的那种。
    目标读者是中东 / 非洲 / 拉美的采购：他们被"我们是工厂"骗过太多次，
    所以这一页明说"我们不是工厂"，然后把能证明的东西列出来。"""
    title = "About us — who you are buying from | Guangzhou Yumengyang Auto Parts"
    desc = ("Guangzhou Yumengyang Auto Parts Co., Ltd: trading auto electrical parts since 2002, own brand WEILI. "
            "What we do, how the parts are made, where we are, and what we can prove before you order.")
    h1 = "About us"
    canon = rel_url(cfg, "about.html")
    wa = wa_link(cfg, "Hi, I would like to know more about your company and your production.")
    n_total = cfg.get("_total") or 6819
    n_txt = "{:,}".format(n_total)


    secs = [
        ("about_s1_h", "What we do",
         ("about_s1_p1",
          "Guangzhou Yumengyang Auto Parts Co., Ltd has been trading auto electrical parts since 2002. "
          "We are headquartered in Baiyun District, Guangzhou, we own two brands — WEILI and STANDOUT — "
          "and we supply 23 categories of parts: ignition coils, ABS sensors, fuel pumps, oxygen sensors, "
          "throttle bodies, thermostats and more."),
         ("about_s1_p2",
          "Every part we sell is listed on this site with its OE number, cross-references and fitment. "
          "That list is the product: if we cannot name the OE number a part replaces, we do not list it.")),
        ("about_s2_h", "How the parts are made",
         ("about_s2_p1",
          "We are a trading company with our own brand, and we say so plainly. Parts sold under WEILI are "
          "produced for us by long-term manufacturing partners — the same arrangement most aftermarket brands "
          "you already buy work with."),
         ("about_s2_p2",
          "What we control is everything around the part: the OE and cross-reference list, the specification, "
          "incoming inspection, packing and the warranty. We know which batch came from which line, and if you "
          "ask us which factory made a specific SKU, we will tell you.")),
        ("about_s3_h", "Where we are",
         ("about_s3_p1",
          "Our office is in Baiyun District, Guangzhou, the trading district the whole Chinese aftermarket "
          "buys from. Stock ships within days and export goes out through Guangzhou port — we will confirm the "
          "exact port and terms in the quotation."),
         ("raw", addr_span(cfg))),
        ("about_s4_h", "What we can send you before you order",
         [("about_s4_li1", "Our business licence, stamped"),
          ("about_s4_li2", "The ISO 9001 and IATF 16949 certificates held by our production partners"),
          ("about_s4_li3", "Real photos of the part, the inner packing and the carton marking"),
          ("about_s4_li4", "The test report for the batch we are quoting"),
          ("about_s4_li5", "Buyers in your region who agreed to be a reference")],
         ("about_s4_p",
          "Ask on WhatsApp and we send what we have the same working day. If we do not have a document, "
          "we say so rather than sending something that looks like it.")),
        ("about_s5_h", "What we are not",
         ("about_s5_p", "We would rather lose an order than mislead a buyer:"),
         [("about_s5_li1", "We do not run our own stamping or winding plant, and we will not claim to."),
          ("about_s5_li2", "We are not the cheapest source for a single piece. Our pricing pays off on mixed orders."),
          ("about_s5_li3", "We do not stock every body panel. Our catalogue is electrics and sensors — that is where "
                           "our knowledge is.")]),
        ("about_s6_h", "Why this lookup site exists",
         ("about_s6_p",
          "The first question every buyer asks is “do you have my number?” — usually with a photo of a sticker "
          "on a broken part. Instead of answering that one part at a time, we put %s part numbers online with "
          "their OE numbers and cross-references, in nine languages, so a mechanic in Lagos or a counter in "
          "Dubai can check it themselves at 2 a.m." % n_txt)),
    ]

    def render(pairs):
        out = []
        for sec in pairs:
            out.append('<section class="dsec"><h2 data-i18n="%s">%s</h2>%s</section>'
                       % (sec[0], esc(sec[1]), _about_body(sec[2:])))
        return "".join(out)

    zh = [
        "2002 年成立，总部在广州白云区，自有品牌 WEILI 与 STANDOUT，供 23 个品类、%s 个型号。" % n_txt,
        "我们是工贸一体、自有品牌，不假装自己是工厂：WEILI 的货由长期合作工厂代工，我们负责 OE 清单、"
        "规格、来料检验、包装和质保。哪批货出自哪条线，你问了我们说。",
        "广州办公与仓库，现货几天内发出，出口走广州港。",
        "下单前可以给我们索取：营业执照、合作工厂的 ISO 9001 / IATF 16949 证书、实物与包装实拍、批次检测报告、"
        "同区域客户推荐。有就给，没有就说没有。",
        "我们不做的：不假装有冲压绕线车间；单件不是最便宜；车身覆盖件不齐——我们的强项是电器件和传感器。",
        "这个查询站的由来：每个买家第一句话都是「这个号你有没有」，我们干脆把 %s 个型号和 OE 号全部放上网。" % n_txt,
    ]
    zh_html = "".join("<li>%s</li>" % esc(x) for x in zh)

    ld = {"@context": "https://schema.org", "@type": "AboutPage",
          "name": "About %s" % cfg["company_en"], "description": clean_text(desc),
          "inLanguage": "en", "isPartOf": {"@type": "WebSite", "url": cfg["site_url"] + "/"}}
    if has_site(cfg):
        ld["url"] = canon

    body = """<body class="docpage">
%s
<main id="main" tabindex="-1" class="policy">
<nav class="crumbs"><a href="index.html" data-i18n="home">Home</a> &rsaquo; <span data-i18n="foot_about">About us</span></nav>
<article class="doc">
  <h1 data-i18n="about_h1">%s</h1>
  <p class="docmeta"><span data-i18n="about_upd">Last updated</span> <span data-i18n="about_date">%s</span> · <span data-i18n="doc_ref">English version is the reference</span></p>
  <p class="doclead" data-i18n="about_lead">We buy, brand and ship auto electrical parts for the aftermarket. We are not a factory,
  and this page does not pretend that we are — it explains what we actually do, so you can judge whether
  we are the right supplier for your market.</p>
  %s
  <details class="doczh"><summary>中文摘要 · Chinese summary</summary><ul>%s</ul></details>
  <section class="doccontact">
    <h2 data-i18n="foot_contact">Contact</h2>
    <p class="docorg"><b class="notranslate" %s>%s</b> · <span class="notranslate" %s>%s</span></p>
    <p class="docaddr">%s</p>
    <p><span data-i18n="foot_hours">Working hours</span>: %s</p>
    <p data-i18n="foot_contact_via">Questions about this page? WhatsApp or email us — we answer within one working day.</p>
    <p><a class="btn-wa" href="%s" target="_blank" rel="noopener">%s</a>
       <a class="btn-ghost" href="index.html" data-i18n="nf_back">Back to the lookup home</a></p>
  </section>
</article>
</main>
%s
<script>(function(){function f(){try{var d=document.querySelector('.doczh');if(d&&window.I18N&&window.I18N.lang==='zh')d.open=true;}catch(e){}}
document.addEventListener('DOMContentLoaded',f);document.addEventListener('i18n:change',f);
try{if(document.documentElement.getAttribute('data-lang')==='zh')document.querySelector('.doczh').open=true;}catch(e){}})();</script>
</body></html>
""" % (sitehead(cfg, "", base=""), esc(h1), ABOUT_DATE_TXT,
       render(secs), zh_html,
       NOTRANSLATE, esc(BRAND_CN), NOTRANSLATE, esc(cfg["company_en"]),
       addr_span(cfg), esc(cfg["hours"]),
       esc(wa), esc("WhatsApp " + wa_display(cfg["whatsapp"])),
       sitefoot(cfg, base=""))
    return head_block(cfg, title, desc, canon, "assets/og/og-default.webp", "website",
                      [ld], base="") + "\n" + body


def make_og_default(cfg):
    """全站默认分享卡 assets/og/og-default.webp（1200×630）：首页 / 政策页 / 指南页都用它。
    型号页仍然用它自己的产品图（head_block 里按 it["p"] 传进去）。"""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception:
        return ""
    outdir = os.path.join(HERE, "assets", "og")
    os.makedirs(outdir, exist_ok=True)

    def font(size, bold=True):
        names = ["segoeuib.ttf", "arialbd.ttf"] if bold else ["segoeui.ttf", "arial.ttf"]
        for n in names:
            p = os.path.join(r"C:\Windows\Fonts", n)
            if os.path.exists(p):
                try:
                    return ImageFont.truetype(p, size)
                except Exception:
                    pass
        try:
            return ImageFont.load_default(size)
        except Exception:
            return ImageFont.load_default()

    W, H = 1200, 630
    img = Image.new("RGB", (W, H), (13, 34, 51))
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / float(H)
        d.line([(0, y), (W, y)], fill=(int(13 + 12 * t), int(34 + 34 * t), int(51 + 46 * t)))
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse([W - 300, -180, W + 160, 280], fill=(232, 98, 42, 58))
    gd.ellipse([-160, H - 120, 260, H + 220], fill=(37, 211, 102, 26))
    img = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")
    d = ImageDraw.Draw(img)

    d.text((72, 74), "YUMENGYANG  ·  AUTO PARTS", font=font(24), fill=(232, 98, 42))
    total = cfg.get("_total") or 0
    head = "{:,}+ OE part numbers".format(total - (total % 100))
    d.text((72, 176), head, font=font(78), fill=(255, 255, 255))
    d.text((72, 288), "OE-grade  ·  1/3 of OEM price", font=font(42), fill=(159, 192, 214))
    d.text((72, 356), "Ignition coils · ABS sensors · fuel pumps · oxygen sensors",
           font=font(27, False), fill=(139, 166, 186))
    d.line([(72, 442), (W - 72, 442)], fill=(40, 82, 112), width=2)
    d.text((72, 474), "Guangzhou Yumengyang Auto Parts Co., Ltd.", font=font(28, False), fill=(207, 224, 236))
    site = (cfg.get("site_url") or "").replace("https://", "").replace("http://", "").rstrip("/")
    d.text((72, 524), site, font=font(30), fill=(255, 255, 255))
    wa = cfg["whatsapp"]
    wa_pretty = ("+%s %s %s %s" % (wa[:2], wa[2:5], wa[5:9], wa[9:])) if len(wa) == 13 and wa.startswith("86") else ("+" + wa)
    d.text((72, 570), "WhatsApp %s  ·  reply within one working day" % wa_pretty,
           font=font(24, False), fill=(139, 166, 186))
    path = os.path.join(outdir, "og-default.webp")
    img.save(path, "WEBP", quality=88, method=6)
    return path


# ------------------------------------------------------------------ 采购指南（SEO 内容页）
GUIDE_LINK_RE = re.compile(r"\[\[L:([^|\]]+)\|([^\]]+)\]\]")


def _norm_key(t):
    return re.sub(r"[^a-z0-9]", "", (t or "").lower())


def make_guide_resolver(items):
    """[[L:...]] → 相对链接。找不到的型号退回首页搜索，绝不写出死链。"""
    oe_map = {}
    for it in items:
        key = _norm_key(it.get("oe"))
        if key and key not in oe_map:
            oe_map[key] = it["s"]
    code_slugs = {c["code"].lower() for c in _code_list()}

    def resolve(target):
        t = (target or "").strip()
        low = t.lower()
        if low.startswith("cat/"):
            key = t[4:]
            return "../category/%s.html" % cat_slug(key) if key in CAT_META else "../category/index.html"
        if low.startswith("part/"):
            oe = t[5:].strip()
            slug = oe_map.get(_norm_key(oe))
            return "../c/%s.html" % slug if slug else "../index.html?q=%s" % quote(oe, safe="")
        if low.startswith("guides/"):
            return "./" + t[7:]
        if low.startswith("code/"):
            slug = t[5:].strip().lower()
            return ("./%s.html" % slug) if slug in code_slugs else "./index.html"
        if low.startswith("codes/"):
            return "./" + t[6:]
        if low in ("home", "index.html", "/", ""):
            return "../index.html"
        return "../index.html"

    return resolve


def _guide_text(raw, resolve):
    def rep(m):
        target, label = m.group(1), m.group(2)
        extra = ""
        if target.lower().startswith("cat/"):
            key = target[4:]
            if key in CAT_META:
                extra = ' data-cat="%s"' % key      # 品类名跟着界面语种走（C 字典）
        return '<a href="%s"%s>%s</a>' % (esc(resolve(target)), extra, esc(label))
    return GUIDE_LINK_RE.sub(rep, raw or "")


def _i18n_attr(raw, pfx, *parts):
    """有前缀才挂钩子；块里有 [[L:...]] 链接就用 innerHTML 版本，否则用纯文本版本。"""
    if not pfx:
        return ""
    key = "_".join((pfx,) + tuple(str(p) for p in parts))
    if "[[" in (raw or ""):
        return ' data-i18n-html="%s"' % key
    return ' data-i18n="%s"' % key


def guide_blocks_html(blocks, resolve, pfx=""):
    """块状正文 → HTML。h2 开一段 .dsec（沿用政策页的排版）。
    pfx 给了（如 cd_p0301）就给每块挂 data-i18n；字典里没有对应键时前端保持英文。"""
    out, open_sec = [], False
    for i, b in enumerate(blocks):
        kind = b[0]
        if kind == "h2":
            if open_sec:
                out.append("</section>")
            out.append('<section class="dsec"><h2%s>%s</h2>'
                       % (_i18n_attr(b[1], pfx, "b", i), _guide_text(b[1], resolve)))
            open_sec = True
            continue
        if not open_sec:
            out.append('<section class="dsec">')
            open_sec = True
        if kind in ("p", "tip"):
            out.append('<p class="%s"%s>%s</p>'
                       % ("gtip" if kind == "tip" else "gp",
                          _i18n_attr(b[1], pfx, "b", i), _guide_text(b[1], resolve)))
        elif kind in ("ul", "ol"):
            out.append("<%s>%s</%s>" % (
                kind,
                "".join("<li%s>%s</li>" % (_i18n_attr(x, pfx, "b", i, "l", j),
                                           _guide_text(x, resolve))
                        for j, x in enumerate(b[1])), kind))
        elif kind == "table":
            head = "".join("<th%s>%s</th>" % (_i18n_attr(h, pfx, "b", i, "h", j),
                                              _guide_text(h, resolve))
                           for j, h in enumerate(b[1]))
            rows = []
            for r, row in enumerate(b[2]):
                rows.append("<tr>%s</tr>" % "".join(
                    "<td%s>%s</td>" % (_i18n_attr(c, pfx, "b", i, "c", r, ci),
                                       _guide_text(c, resolve))
                    for ci, c in enumerate(row)))
            out.append('<div class="gtable"><table><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>'
                       % (head, "".join(rows)))
    if open_sec:
        out.append("</section>")
    return "".join(out)


def guide_url(cfg, slug):
    return rel_url(cfg, "guides/%s.html" % slug)


def page_guide(cfg, g, resolve):
    slug = g["slug"]
    canonical = guide_url(cfg, slug)
    og = "assets/og/og-default.webp"
    ld = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": g["title"],
        "description": clean_text(g["desc"]),
        "datePublished": g["date"],
        "dateModified": g["date"],
        "inLanguage": "en",
        "articleSection": "Buying guides",
        "author": {"@type": "Organization", "name": cfg["company_en"], "url": cfg["site_url"] + "/"},
        "publisher": {"@type": "Organization", "name": cfg["company_en"],
                      "logo": {"@type": "ImageObject", "url": rel_url(cfg, og)}},
        "image": [rel_url(cfg, og)],
        "mainEntityOfPage": {"@type": "WebPage", "@id": canonical},
    }
    if has_site(cfg):
        ld["url"] = canonical
    crumbs = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Home", "item": rel_url(cfg, "")},
        {"@type": "ListItem", "position": 2, "name": "Buying guides", "item": rel_url(cfg, "guides/index.html")},
        {"@type": "ListItem", "position": 3, "name": g["h1"]},
    ]}
    others = [x for x in guides_content.GUIDES if x["slug"] != slug]
    more = "".join('<a href="./%s.html">%s</a>' % (esc(x["slug"]), esc(x["nav"])) for x in others)
    wa = wa_link(cfg, "Hi, I read your guide. I have a question about a part number.")
    body = """<body class="docpage">
%s
<main id="main" tabindex="-1" class="policy">
<nav class="crumbs"><a href="../index.html" data-i18n="home">Home</a> &rsaquo;
<a href="./index.html" data-i18n="guides_h">Buying guides</a> &rsaquo; <span>%s</span></nav>
<article class="doc guide">
  <h1 data-i18n="%s">%s</h1>
  <p class="docmeta">%s · %d min read · <span data-i18n="doc_ref">English version is the reference</span></p>
  <p class="doclead" data-i18n="%s">%s</p>
  %s
  <nav class="gmore"><b data-i18n="guides_more">More guides</b><a href="./index.html" data-i18n="guides_h">Buying guides</a>%s</nav>
  <section class="doccontact">
    <h2 data-i18n="foot_contact">Contact</h2>
    <p class="docorg"><b class="notranslate" %s>%s</b> · <span class="notranslate" %s>%s</span></p>
    <p class="docaddr">%s</p>
    <p><a class="btn-wa" href="%s" target="_blank" rel="noopener">%s</a>
       <a class="btn-ghost" href="../index.html" data-i18n="lookup">OE / cross-reference lookup</a></p>
  </section>
</article>
</main>
%s
</body></html>
""" % (sitehead(cfg, "", base="../"), esc(g["h1"]),
       "gd_%s_h1" % slug.replace("-", "_"), esc(g["h1"]),
       "Published " + g["date"], g.get("minutes", 6),
       "gd_%s_lead" % slug.replace("-", "_"), esc(g["lead"]),
       guide_blocks_html(g["body"], resolve, "gd_%s" % slug.replace("-", "_")), more,
       NOTRANSLATE, esc(BRAND_CN), NOTRANSLATE, esc(cfg["company_en"]), addr_span(cfg),
       esc(wa), esc("WhatsApp " + wa_display(cfg["whatsapp"])), sitefoot(cfg, base="../"))
    return head_block(cfg, g["title"] + " | Yumengyang Auto Parts", g["desc"], canonical, og, "article",
                      [ld, crumbs], base="../") + "\n" + body


def page_guides_index(cfg):
    cards = []
    for g in guides_content.GUIDES:
        cards.append(
            '<a class="guidecard" href="./%s.html"><b>%s</b><span>%s</span>'
            '<em>%d min read →</em></a>' % (esc(g["slug"]), esc(g["h1"]), esc(g["desc"]),
                                            g.get("minutes", 6)))
    total_txt = "{:,}".format(cfg.get("_total", 0))
    title = "Buying guides: OE numbers, VIN and ABS sensors | Yumengyang Auto Parts"
    desc = ("Three practical guides for mechanics and parts buyers: find an ignition coil by OE number, "
            "read a VIN, and diagnose an ABS sensor before ordering.")
    body = """<body class="docpage">
%s
<main id="main" tabindex="-1" class="policy">
<nav class="crumbs"><a href="../index.html" data-i18n="home">Home</a> &rsaquo; <span data-i18n="guides_h">Buying guides</span></nav>
<article class="doc guide">
  <h1 data-i18n="guides_h">Buying guides</h1>
  <p class="doclead" data-i18n="guides_lead">Short, practical notes from our workshop and export desk: how to read a part number, how to place a car from its VIN, and how to diagnose before you order. Product data stays in English; the interface follows your language.</p>
  <div class="guidecards">%s</div>
  <section class="dsec">
    <h2 data-i18n="guides_use">What you can do next</h2>
    <ul>
      <li><a href="../index.html" data-i18n="lookup">OE / cross-reference lookup</a> — %s part numbers by OE, cross-reference or vehicle.</li>
      <li><a href="../category/index.html" data-i18n="all_cat_h1">All product categories</a> — browse the full catalogue.</li>
      <li><a href="../codes/index.html" data-i18n="codes_h">Fault codes</a> — the OBD codes our own catalogue can fix, with the order we check parts in.</li>
    </ul>  </section>
</article>
</main>
%s
</body></html>
""" % (sitehead(cfg, "", base="../"), "".join(cards), esc(total_txt), sitefoot(cfg, base="../"))
    return head_block(cfg, title, desc, rel_url(cfg, "guides/index.html"), "assets/og/og-default.webp",
                      "website", base="../") + "\n" + body


CODES_DATE = "2026-11-10"     # 故障码页正文的维护日期（改了 CODES 就改这个）


def _code_list():
    return list(getattr(codes_content, "CODES", None) or []) if codes_content else []


def _code_sys_list():
    return list(getattr(codes_content, "SYSTEMS", None) or []) if codes_content else []


def _codes_by_system():
    out = {}
    for c in _code_list():
        out.setdefault(c["system"], []).append(c)
    return out


def code_url(cfg, slug):
    return rel_url(cfg, "codes/%s.html" % slug)


def _code_lead_part(c):
    """码卡片右下角那句：取第一个品类的英文名，让买家一眼知道要动什么件。"""
    for key, _note in (c.get("parts") or []):
        if key in CAT_META:
            return CAT_META[key][1]
    return "Diagnosis"


def page_codes_index(cfg):
    """故障码总目录：按系统分组。故意不列"全部 OBD 码"——我们只收录我们的件能修的码。"""
    by_sys = _codes_by_system()
    sections = []
    for key, en, span in _code_sys_list():
        lst = by_sys.get(key) or []
        if not lst:
            continue
        cards = "".join(
            '<a class="guidecard" href="./%s.html"><b class="notranslate" translate="no">%s</b>'
            '<span>%s</span><em>%s &rarr;</em></a>'
            % (esc(c["code"].lower()), esc(c["code"]), esc(c["name"]), esc(_code_lead_part(c)))
            for c in sorted(lst, key=lambda x: x["code"]))
        sections.append('<section class="dsec"><h2>%s <code>%s</code></h2>'
                        '<div class="guidecards">%s</div></section>' % (esc(en), esc(span), cards))
    n = len(_code_list())
    title = "OBD fault code diagnosis: what to check, what to replace | Yumengyang"
    desc = ("%d OBD-II fault codes explained the way an export desk explains them: what the code means, "
            "the order we check parts in, the mistake that costs the most, and the parts we actually "
            "stock for each one." % n)
    wa = wa_link(cfg, "Hi, my car shows a fault code. Can you help me pick the part?")
    body = """<body class="docpage">
%s
<main id="main" tabindex="-1" class="policy">
<nav class="crumbs"><a href="../index.html" data-i18n="home">Home</a> &rsaquo; <span data-i18n="codes_h">Fault codes</span></nav>
<article class="doc guide">
  <h1 data-i18n="codes_h">Fault codes</h1>
  <p class="docmeta">%d codes &middot; updated %s &middot; <span data-i18n="doc_ref">English version is the reference</span></p>
  <p class="doclead">A code tells you which system failed, not which part. These pages are the ones we use
  at the desk when a customer sends a photo of the scanner: what the code actually means, the order we
  check parts in, the mistake that costs the most money, and the part numbers we hold for it.</p>
  <p class="doclead" style="border:0;padding-bottom:0;margin-bottom:0">We do not list all 12,000 OBD codes.
  We list the ones our own catalogue can fix &mdash; if your code is here, we very likely have the part.</p>
  %s
  <section class="dsec">
    <h2 data-i18n="codes_next">What you can do next</h2>
    <ul>
      <li><a href="../index.html" data-i18n="lookup">OE / cross-reference lookup</a> &mdash; search the catalogue by OE, cross-reference or vehicle.</li>
      <li><a href="../vehicle/index.html" data-i18n="nav_vehicles">Browse by vehicle</a> &mdash; pick the car, then the part.</li>
      <li><a href="../guides/index.html" data-i18n="guides_h">Buying guides</a> &mdash; how to read an OE number and place a car from its VIN.</li>
    </ul>
  </section>
  <section class="doccontact">
    <h2 data-i18n="foot_contact">Contact</h2>
    <p class="docorg"><b class="notranslate" %s>%s</b> &middot; <span class="notranslate" %s>%s</span></p>
    <p class="docaddr">%s</p>
    <p>Send us the code and the car &mdash; year, engine, and a photo of the scanner if you have one. We will
    tell you which of our numbers fits before you order.</p>
    <p><a class="btn-wa" href="%s" target="_blank" rel="noopener">%s</a>
       <a class="btn-ghost" href="../index.html" data-i18n="lookup">OE / cross-reference lookup</a></p>
  </section>
</article>
</main>
%s
</body></html>
""" % (sitehead(cfg, "codes", base="../"), n, CODES_DATE, "".join(sections),
       NOTRANSLATE, esc(BRAND_CN), NOTRANSLATE, esc(cfg["company_en"]), addr_span(cfg),
       esc(wa), esc("WhatsApp " + wa_display(cfg["whatsapp"])), sitefoot(cfg, base="../"))
    return head_block(cfg, title, desc, rel_url(cfg, "codes/index.html"), "assets/og/og-default.webp",
                      "website", base="../") + "\n" + body


def page_code(cfg, c, resolve, cat_counts):
    """单个故障码页。正文来自 codes_content，品类表由模板按 parts 自动生成。"""
    code = c["code"]
    slug = code.lower()
    canonical = code_url(cfg, slug)
    og = "assets/og/og-default.webp"
    sys_name = ""
    for key, en, _span in _code_sys_list():
        if key == c["system"]:
            # 系统名（misfire / air / abs …）跟着界面语种走
            sys_name = '<span data-i18n="csys_%s">%s</span>' % (esc(key), esc(en))
            break
    # 标题压到 70 字符内（之前最长 114 字符，Google 摘要里会被截掉一半）
    _suffix = " | Yumengyang"
    _mid = " — causes, tests & parts"
    _room = 70 - len(_suffix) - len(_mid) - len(code) - 1
    _name = c["name"]
    if len(_name) > _room:
        _name = _name[:max(_room - 1, 12)].rsplit(" ", 1)[0] + "…"
    title = "%s %s%s%s" % (code, _name, _mid, _suffix)
    ld = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": "%s: %s" % (code, c["name"]),
        "description": clean_text(c["desc"]),
        "datePublished": CODES_DATE,
        "dateModified": CODES_DATE,
        "inLanguage": "en",
        "articleSection": "Fault codes",
        "author": {"@type": "Organization", "name": cfg["company_en"], "url": cfg["site_url"] + "/"},
        "publisher": {"@type": "Organization", "name": cfg["company_en"],
                      "logo": {"@type": "ImageObject", "url": rel_url(cfg, og)}},
        "image": [rel_url(cfg, og)],
        "mainEntityOfPage": {"@type": "WebPage", "@id": canonical},
    }
    if has_site(cfg):
        ld["url"] = canonical
    crumbs = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Home", "item": rel_url(cfg, "")},
        {"@type": "ListItem", "position": 2, "name": "Fault codes", "item": rel_url(cfg, "codes/index.html")},
        {"@type": "ListItem", "position": 3, "name": code},
    ]}
    ld_list = [ld, crumbs]
    if c.get("qa"):
        ld_list.append({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": clean_text(q),
             "acceptedAnswer": {"@type": "Answer", "text": clean_text(a)}}
            for q, a in c["qa"]]})

    # 我们手上的件：品类 + 型号数 + 什么时候换。数字取本次生成的真实计数。
    prows = []
    for key, note in (c.get("parts") or []):
        meta = CAT_META.get(key)
        if not meta:
            continue
        prows.append('<tr><td><a href="../category/%s.html" data-cat="%s">%s</a></td>'
                     '<td>%s</td><td data-i18n="%s_pn_%d">%s</td></tr>'
                     % (esc(meta[0]), esc(key), esc(meta[1]),
                        "{:,}".format(cat_counts.get(key, 0)),
                        "cd_%s" % slug.replace("-", "_"), len(prows), esc(note)))
    parts_block = ""
    if prows:
        parts_block = ('<section class="dsec"><h2 data-i18n="cdx_parts_h" data-v-c="%s">'
                       'Parts we stock for a %s</h2>'
                       '<p class="gp" data-i18n="cdx_parts_p">Stocked numbers and fitment for these categories '
                       'are in the catalogue; message us with the car details and we will pick the right one.</p>'
                       '<div class="gtable"><table><thead><tr>'
                       '<th data-i18n="cdx_parts_th1">Our category</th>'
                       '<th data-i18n="cdx_parts_th2">Part numbers</th>'
                       '<th data-i18n="cdx_parts_th3">When</th>'
                       '</tr></thead><tbody>%s</tbody></table></div></section>'
                       % (esc(code), esc(code), "".join(prows)))

    faq_block = ""
    if c.get("qa"):
        pfx_qa = "cd_%s" % slug.replace("-", "_")
        items = []
        for qi, (q, a) in enumerate(c["qa"]):
            items.append('<details class="fq"><summary data-i18n="%s_qa_q%d">%s</summary>'
                         '<div class="fqa" data-i18n="%s_qa_a%d">%s</div></details>'
                         % (pfx_qa, qi, esc(q), pfx_qa, qi, esc(a)))
        faq_block = ('<section class="dsec"><h2 data-i18n="cdx_faq_h">Questions we get</h2>%s</section>'
                     % "".join(items))

    have = {x["code"].lower() for x in _code_list()}
    rel = "".join('<a href="./%s.html">%s</a>' % (esc(x.lower()), esc(x))
                  for x in (c.get("related") or []) if x.lower() in have)
    wa = wa_link(cfg, "Hi, my car shows %s (%s). What part do you recommend?" % (code, c["name"]))
    body = """<body class="docpage">
%s
<main id="main" tabindex="-1" class="policy">
<nav class="crumbs"><a href="../index.html" data-i18n="home">Home</a> &rsaquo;
<a href="./index.html" data-i18n="codes_h">Fault codes</a> &rsaquo; <span class="notranslate" translate="no">%s</span></nav>
<article class="doc guide">
  <h1><span class="notranslate" translate="no">%s</span> &mdash; <span data-i18n="%s">%s</span></h1>
  <p class="docmeta"><span data-i18n="cdx_obd">OBD-II fault code</span> &middot; %s &middot;
     <span data-i18n="cdx_updated">updated</span> %s &middot;
     <span data-i18n="doc_ref">English version is the reference</span></p>
  <p class="doclead" data-i18n="%s">%s</p>
  %s
  %s
  %s
  <nav class="gmore"><b data-i18n="codes_more">More codes</b><a href="./index.html" data-i18n="codes_all">All codes we cover</a>%s</nav>
  <section class="doccontact">
    <h2 data-i18n="foot_contact">Contact</h2>
    <p class="docorg"><b class="notranslate" %s>%s</b> &middot; <span class="notranslate" %s>%s</span></p>
    <p class="docaddr">%s</p>
    <p data-i18n="cdx_contact_p">Send us the code, the car and the year. If this page points at several parts,
    we will tell you which one to change first &mdash; and which one not to change.</p>
    <p><a class="btn-wa" href="%s" target="_blank" rel="noopener">%s</a>
       <a class="btn-ghost" href="../index.html" data-i18n="lookup">OE / cross-reference lookup</a></p>
  </section>
</article>
</main>
%s
</body></html>
""" % (sitehead(cfg, "codes", base="../"), esc(code), esc(code),
       "cd_%s_name" % slug.replace("-", "_"), esc(c["name"]),
       sys_name, CODES_DATE,
       "cd_%s_lead" % slug.replace("-", "_"), esc(c["lead"]),
       guide_blocks_html(c["body"], resolve, "cd_%s" % slug.replace("-", "_")), parts_block, faq_block,
       rel, NOTRANSLATE, esc(BRAND_CN), NOTRANSLATE, esc(cfg["company_en"]), addr_span(cfg),
       esc(wa), esc("WhatsApp " + wa_display(cfg["whatsapp"])), sitefoot(cfg, base="../"))
    return head_block(cfg, title, c["desc"], canonical, og, "article",
                      ld_list, base="../") + "\n" + body


def page_404(cfg):
    # 404 页总在站点根目录：用相对路径，本地双击预览时也能加载到本机 assets/i18n.js
    # （以前用绝对域名，本地预览会去拉线上旧字典，改文案后测不出效果）
    home = "index.html"
    js = "assets/i18n.js"
    js += "?v=" + I18N_V
    sel = lang_sel_html().replace('class="langsel"', 'class="langsel dark"')
    an = ""
    if (cfg.get("analytics") or "").strip():
        an = '\n<meta name="ymy-analytics" content="%s">' % esc(cfg["analytics"].strip())
        if (cfg.get("analytics_q") or "").strip() in ("1", "yes", "true", "on"):
            an += '\n<meta name="ymy-analytics-q" content="1">'
        an += '\n<script defer src="assets/analytics.js?v=%s"></script>' % ANALYTICS_V
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Page not found | Guangzhou Yumengyang Auto Parts</title>
<meta name="robots" content="noindex,follow">
{FAVICON}
{LANG_BOOT}
<script defer src="{js}"></script>{an}
<style>
*{{box-sizing:border-box}}
body{{margin:0;font-family:Inter,"Segoe UI",system-ui,Arial,"Microsoft YaHei",sans-serif;background:#f6f8fa;color:#16232e;
display:flex;min-height:100vh;align-items:center;justify-content:center;padding:24px}}
.box{{max-width:600px;text-align:center}}
.top{{display:flex;justify-content:center;margin-bottom:18px}}
.code{{font-size:72px;font-weight:700;color:#dbe6ee;line-height:1}}
h1{{font-size:24px;margin:12px 0 10px;font-weight:700}}
p{{color:#5d7186;font-size:15px;line-height:1.7;margin:0 0 24px}}
a.btn{{display:inline-flex;align-items:center;justify-content:center;min-height:48px;background:#0d2233;color:#fff;text-decoration:none;padding:0 24px;border-radius:12px;font-weight:600;font-size:15px}}
a.wa{{display:inline-flex;align-items:center;justify-content:center;min-height:48px;background:#25d366;color:#062b16;text-decoration:none;padding:0 24px;border-radius:12px;font-weight:700;font-size:15px;margin-inline-start:10px}}
form.nf{{display:flex;gap:8px;max-width:540px;margin:0 auto 16px}}
form.nf input{{flex:1;min-width:0;height:48px;border:1px solid #cfdae4;border-radius:12px;padding:0 14px;font:inherit;font-size:15px;background:#fff}}
form.nf button{{height:48px;border:0;border-radius:12px;background:#e8622a;color:#fff;font:inherit;font-weight:700;padding:0 18px;cursor:pointer;white-space:nowrap}}
.nfquick{{font-size:14px;margin:0 0 22px}}
.nfquick a{{color:#c2491f;text-decoration:none;font-weight:600}}
html[dir="rtl"] form.nf{{flex-direction:row-reverse}}
small{{display:block;margin-top:28px;color:#8698a9;font-size:12.5px}}
.langsel{{-webkit-appearance:none;appearance:none;height:42px;min-width:130px;padding:0 34px 0 14px;border-radius:10px;
font:inherit;font-size:14px;font-weight:600;color:#16232e;background:#fff url("data:image/svg+xml;charset=utf-8,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 12 8'%3E%3Cpath d='M1 1.5 6 6.5l5-5' fill='none' stroke='%235d7186' stroke-width='1.8' stroke-linecap='round'/%3E%3C/svg%3E") no-repeat right 12px center/12px 8px;
border:1px solid #cfdae4;cursor:pointer}}
html[dir="rtl"] .langsel{{padding:0 14px 0 34px;background-position:left 12px center}}
</style>
</head>
<body>
<div class="box">
  <div class="top">{sel}</div>
  <div class="code">404</div>
  <h1 data-i18n="nf_h1">Page not found</h1>
  <p data-i18n="nf_p">The part may have moved. Search by OE number below, or message us on WhatsApp.</p>
  <form class="nf" action="products.html" method="get" role="search">
    <input type="search" name="q" data-i18n-ph="home_ph" placeholder="OE number / cross-reference / SKU / model" aria-label="Search parts">
    <button type="submit" data-i18n="search_oe_btn">Search by OE number</button>
  </form>
  <p class="nfquick"><a href="category/index.html" data-i18n="all_cat_h1">All product categories</a>
    · <a href="products.html" data-i18n="nav_products">Products</a>
    · <a href="list.html" data-i18n="bulk_check">Bulk check</a>
    · <a href="about.html" data-i18n="nav_about">About us</a></p>
  <a class="btn" href="{home}" data-i18n="nf_back">Back to the lookup home</a>
  <a class="wa" href="{wa}" target="_blank" rel="noopener">WhatsApp</a>
  <small><span class="notranslate" translate="no">{cn}</span> · <span class="notranslate" translate="no">{en}</span></small>
</div>
</body>
</html>
""".format(LANG_BOOT=LANG_BOOT, js=esc(js), sel=sel, home=esc(home),
           wa=esc(wa_link(cfg, "Hi, I could not find a part on your website.")),
           cn=esc(BRAND_CN), en=esc(cfg["company_en"]), FAVICON=FAVICON, an=an)


def make_og_images(cfg, cats):
    """给没照片的型号页做分享缩略图：每个品类一张 1200x630 的品牌卡片。"""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception:
        return
    ogdir = os.path.join(HERE, "assets", "og")
    os.makedirs(ogdir, exist_ok=True)

    def font(size, bold=True):
        names = ["arialbd.ttf", "segoeuib.ttf"] if bold else ["arial.ttf", "segoeui.ttf"]
        for n in names:
            p = os.path.join(r"C:\Windows\Fonts", n)
            if os.path.exists(p):
                try:
                    return ImageFont.truetype(p, size)
                except Exception:
                    pass
        try:
            return ImageFont.load_default(size)
        except Exception:
            return ImageFont.load_default()

    W, H = 1200, 630
    for c in cats:
        slug = cat_slug(c["key"])
        en = CAT_META[c["key"]][1]
        img = Image.new("RGB", (W, H), (14, 36, 56))
        d = ImageDraw.Draw(img)
        for y in range(H):
            t = y / float(H)
            d.line([(0, y), (W, y)], fill=(int(14 + 14 * t), int(36 + 38 * t), int(56 + 51 * t)))
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        gd.ellipse([W - 320, -170, W + 140, 290], fill=(232, 98, 42, 55))
        img = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")
        d = ImageDraw.Draw(img)
        d.text((72, 84), "YUMENGYANG  ·  WEILI", font=font(22), fill=(232, 98, 42))
        d.text((72, 190), en, font=font(80), fill=(255, 255, 255))
        d.text((72, 300), "OE number & cross-reference lookup", font=font(30), fill=(159, 192, 214))
        d.text((72, 372), "{:,} part numbers, fitment and photos".format(c["n"]), font=font(26), fill=(159, 192, 214))
        d.line([(72, 470), (W - 72, 470)], fill=(40, 82, 112), width=2)
        d.text((72, 500), "Guangzhou Yumengyang Auto Parts Co., Ltd.", font=font(26, False), fill=(207, 224, 236))
        wa = cfg["whatsapp"]
        wa_pretty = ("+%s %s %s %s" % (wa[:2], wa[2:5], wa[5:9], wa[9:])) if len(wa) == 13 and wa.startswith("86") else ("+" + wa)
        d.text((72, 540), "Guangzhou, China  ·  WhatsApp %s" % wa_pretty, font=font(24, False), fill=(139, 166, 186))
        img.save(os.path.join(ogdir, slug + ".jpg"), "JPEG", quality=84, optimize=True)


def register_cats(cats):
    """把新品类登记进 CAT_META（slug, 复数英文, 单数英文, 中文）。"""
    for c in cats or []:
        CAT_META[c["key"]] = (c.get("slug") or c["key"], c.get("en") or c["key"],
                              c.get("one") or c.get("en") or c["key"], c.get("name") or c["key"])


# ------------------------------------------------------------------ 首页注入
# 首页「热销品类」六宫格：顺序写死，数量从数据实时算，图优先用 assets/top/<slug>.webp
# （想换封面直接替换那个文件，sitegen 只读不写；没有就用该品类第一张实拍图）
TOP_KEYS = ["coil", "fuelpump", "o2", "plug", "abs", "throttle"]


def top_cards(cfg, cats, by_cat):
    cards = []
    for key in TOP_KEYS:
        items = by_cat.get(key) or []
        if not items:
            continue
        slug, en, one, cn = CAT_META.get(key, (key, key, key, key))
        n = len(items)
        img = "assets/top/%s.webp" % slug
        if not os.path.exists(os.path.join(HERE, img)):
            img = ""
            for it in items:
                if it.get("t"):
                    img = it["t"]
                    break
        if not img:
            continue
        cards.append(
            '<a class="tscard" href="category/%s.html">'
            '<span class="tsimg"><img src="%s" width="400" height="250" loading="lazy" '
            'decoding="async" alt="%s"></span>'
            '<span class="tsbd"><b data-cat="%s">%s</b>'
            '<em class="zh-extra">%s</em>'
            '<span class="tsn" data-i18n="models_n" data-v-n="%d">%d models</span></span></a>'
            % (slug, esc(img), esc(en), key, esc(en), esc(cn), n, n))
    return "".join(cards)


def _origin_key(it):
    """型号 -> (区域名次, 区域代码)。一个件同时适配丰田和长安就算日系。"""
    if brandlib is None:
        return (99, "OTHER")
    br = it.get("_brands")
    if br is None:
        br = brandlib.brand_hits(it.get("a"))
    o = brandlib.origin_of_brands(br)
    return (brandlib.ORIGIN_RANK.get(o, 99), o)


def home_links(cfg, cats, by_cat, limit=100):
    rows = []
    total = 0
    for c in order_cats(cats):
        key = c["key"]
        items = by_cat.get(key, [])
        if not items:
            continue          # 0 型号的品类不摆入口（页面留着，但不从这里链出去）
        total += len(items)
        slug, en, one, cn = CAT_META.get(key, (key, key, key, key))
        # 按品牌国籍重排：日系 -> 德系 -> 韩系 -> 其余，同组内保持原顺序（稳定）
        ranked = sorted(enumerate(items), key=lambda p: (_origin_key(p[1])[0], p[0]))
        by_origin = {}
        for _, it in ranked:
            by_origin.setdefault(_origin_key(it)[1], []).append(it)
        # 按配额取，而不是「先切前 100 再分组」：
        # 那样日系会把 100 个名额吃光，德系韩系根本露不出来。
        quota = {"JP": 45, "DE": 25, "KR": 15, "US": 8}
        picked = []
        for o in (brandlib.ORIGIN_ORDER if brandlib is not None else ["OTHER"]):
            picked.extend(by_origin.get(o, [])[:quota.get(o, 7)])
        picked = picked[:limit]
        picked = [(it, _origin_key(it)[1]) for it in picked]
        # 再按国籍分组 —— 排序结果要让买家一眼看出来，而不是藏在代码里
        groups = []
        for o in (brandlib.ORIGIN_ORDER if brandlib is not None else ["OTHER"]):
            g = [it for it, oo in picked if oo == o]
            if not g:
                continue
            links = "".join('<a href="c/%s.html" title="%s">%s</a>' % (
                esc(it["s"]), esc(it.get("a", "")[:60]), esc(it.get("oe") or it["m"]))
                for it in g)
            label = brandlib.ORIGIN_LABEL.get(o, o) if brandlib is not None else o
            groups.append('<div class="ogr" data-og="%s"><span class="og">%s</span>'
                          '<div class="lst">%s</div></div>' % (o.lower(), esc(label), links))
        rows.append(
            '<div class="catrow"><div class="cath"><b data-cat="%s">%s</b>'
            '<span class="zh-extra">%s · </span>'
            '<span data-i18n="models_n" data-v-n="%d">%d models</span>'
            '<a class="all" href="category/%s.html"><span data-i18n="view_all">View all</span>'
            '<span class="zh-extra"> 查看全部</span> →</a></div>'
            '<div class="ogroups">%s</div></div>'
            % (key, esc(en), esc(cn), len(items), len(items), slug, "".join(groups)))
    return ('<h2><span data-i18n="cat_h2">Browse all models by category</span>'
            '<span class="zh-extra"> 按品类浏览全部型号</span></h2>'
            '<p class="lead" data-i18n="cat_home_lead">Each category lists its first 100 models, grouped by '
            'where the car comes from: Japanese, German and Korean applications first — those are the cars your '
            'counter actually services. Click View all for the whole list.</p>'
            '<details class="catbox"><summary><span data-i18n="catbox_open" data-v-c="%d" data-v-n="%d">'
            'Expand / collapse: %d categories · %d models</span></summary>%s</details>'
            % (len(cats), total, len(cats), total, "".join(rows)))


def _ld_block(items):
    return "".join('\n<script type="application/ld+json">%s</script>' % json.dumps(x, ensure_ascii=False)
                   for x in items)


def home_brands_html(cfg, entries):
    """首页「按品牌浏览」区块（品牌页的首页入口）。"""
    if not entries:
        return ""
    chips = "".join(
        '<a href="brand/%s.html">%s <em>%d</em></a>' % (esc(e["slug"]), esc(e["canon"]), e["n"])
        for e in entries)
    return ('<h2><span data-i18n="brand_h2">Browse parts by vehicle brand</span>'
            '<span class="zh-extra"> 按品牌浏览</span></h2>'
            '<p class="lead" data-i18n="brand_home_lead">Parts grouped by the vehicle brand they fit — '
            'Toyota, Hyundai, Kia, BMW, Ford, Volkswagen and more. Every brand page lists all its part numbers '
            'with OE numbers and cross-references.</p>'
            '<p class="lst">%s</p>' % chips)


def _put_block(text, name, block, label="index.html"):
    """把 <!-- NAME_START --> 与 <!-- NAME_END --> 之间换成 block。
    标记不存在就原样返回并提示——不猜位置、不往别的区块里硬塞。"""
    pat = r"(<!-- %s_START -->)(.*?)(<!-- %s_END -->)" % (name, name)
    new, n = re.subn(pat, lambda m: m.group(1) + "\n" + block + "\n" + m.group(3),
                     text, count=1, flags=re.S)
    if not n:
        print("  [warn] %s 缺少标记 %s_START/END，跳过" % (label, name), flush=True)
        return text
    return new


def inject_home(cfg, cats, by_cat, brand_entries=None):
    """首页 = 公司页。

    ⚠ 落地页拆分（1d9f94710）之后，产品列表面 —— TOP_CARDS / HOME_HOT /
    HOME_BRANDS / HOME_LINKS —— 已经搬到 products.html（见 inject_products）。
    别再往首页找这四块：模板里没有标记，找到了也会把产品网格塞回公司页，
    造成和 products.html 重复的内容。HOME_TRUST 同理已并入公司介绍块。
    """
    path = os.path.join(HERE, "index.html")
    if not os.path.exists(path):
        return
    h = open(path, encoding="utf-8").read()
    total = sum(len(v) for v in by_cat.values())

    h = _put_block(h, "HOME_COMPANY", home_company_html(cfg, total, len(cats)))
    h = _put_block(h, "HOME_CORE", home_core_html(cfg, by_cat))
    h = _put_block(h, "HOME_CONTACT", home_contact_html(cfg))
    h = _put_block(h, "HOME_WHY", why_html(cfg))
    h = _put_block(h, "HOME_FAQ", faq_html(cfg))
    h = _put_block(h, "HOME_FOOT", sitefoot(cfg, base=""))  # 首页也用它，保持全站一致
    # 首页 head 里的 SITE_LD 已经由 head_block() 输出（site_ld + faq_ld），
    # 这里不再往 body 写第二份——否则 Organization/WebSite/FAQPage 各重复一次。

    h = h.replace("https://your-domain.com", cfg["site_url"])
    h = h.replace("8615915859048", cfg["whatsapp"])
    # 语言选择器：首页手写部分里也有一份，选项列表跟着 LANG_OPTIONS 走，每次同步（幂等）
    opts = "".join('<option value="%s">%s</option>' % (k, esc(v)) for k, v in LANG_OPTIONS)
    h = re.sub(r'(<select id="langsel"[^>]*>).*?(</select>)',
               lambda m: m.group(1) + opts + m.group(2), h, count=1, flags=re.S)
    if not has_site(cfg):
        # 没有真实域名：去掉会指错地方的 canonical / og:url / og:image
        h = re.sub(r'\n<link rel="canonical"[^>]*>', "", h)
        h = re.sub(r'\n<meta property="og:url"[^>]*>', "", h)
        h = re.sub(r'\n<meta property="og:image"[^>]*>', "", h)
    open(path, "w", encoding="utf-8", newline="\n").write(h)


def inject_products(cfg, cats, by_cat, brand_entries=None):
    """products.html = 产品目录页：热销品类 / 热门型号 / 按品类浏览全部型号 / 按品牌浏览。

    这一页是落地页拆分时新增的，模板里只有空容器和标记，内容全靠这里填。
    全部写成静态 HTML（不靠 JS 拉），爬虫和 file:// 双击都能看到型号页入口。
    不放 faq_ld：页面正文里没有 FAQ 区块，结构化数据和可见内容对不上会被判无效。
    """
    path = os.path.join(HERE, "products.html")
    if not os.path.exists(path):
        print("  [warn] 没有 products.html，跳过产品目录页注入", flush=True)
        return
    h = open(path, encoding="utf-8").read()
    n_before = h.count('href="c/')
    h = _put_block(h, "TOP_CARDS", top_cards(cfg, cats, by_cat), "products.html")
    h = _put_block(h, "HOME_HOT", hot_html(cfg, cats, by_cat), "products.html")
    if brand_entries:
        h = _put_block(h, "HOME_BRANDS", home_brands_html(cfg, brand_entries), "products.html")
    h = _put_block(h, "HOME_LINKS", home_links(cfg, cats, by_cat), "products.html")
    h = _put_block(h, "SITE_LD", _ld_block(site_ld(cfg)), "products.html")
    h = _put_block(h, "HOME_FOOT", sitefoot(cfg, base=""), "products.html")
    h = h.replace("https://your-domain.com", cfg["site_url"])
    h = h.replace("8615915859048", cfg["whatsapp"])
    if not has_site(cfg):
        h = re.sub(r'\n<link rel="canonical"[^>]*>', "", h)
        h = re.sub(r'\n<meta property="og:url"[^>]*>', "", h)
        h = re.sub(r'\n<meta property="og:image"[^>]*>', "", h)
    open(path, "w", encoding="utf-8", newline="\n").write(h)
    print("  产品目录页：型号页入口 %d -> %d 条" % (n_before, h.count('href="c/')), flush=True)



def home_company_html(cfg, total, n_cats):
    """首页「我们是谁」：公司介绍 + 市场标签 + 四个数字。"""
    return """<section class="sect">
<div class="hco">
  <div>
    <span class="kick" data-i18n="about_kick">Who you are buying from</span>
    <h2 data-i18n="about_h2">A Guangzhou parts house with its own brands</h2>
    <p data-i18n="about_p1">We are Guangzhou Yumengyang Auto Parts Co., Ltd — founded in 2002 in
    Baiyun District, Guangzhou, with 4 subsidiaries and two own brands: WEILI
    (ignition, sensors, fuel system) and STANDOUT.</p>
    <p data-i18n="about_p2">Parts are stocked and shipped from a 10,000+ m² warehouse in Guangzhou.
    WEILI parts are produced by long-term manufacturing partners certified to ISO 9001 and IATF 16949;
    we control the OE list, incoming inspection, packing and the warranty.</p>
    <p data-i18n="about_p3">We currently supply distributors and workshops in 25+ countries —
    including Peru, Bolivia, South Africa, Iraq, Iran, Syria and Egypt.</p>
    <div class="markets"><span>Peru</span><span>Bolivia</span><span>South Africa</span><span>Iraq</span>
      <span>Iran</span><span>Syria</span><span>Egypt</span><span>+ 18 more</span></div>
    <div class="stats">
      <div class="st"><b>2002</b><em data-i18n="st_founded">Founded</em></div>
      <div class="st"><b>%(nt)s</b><em data-i18n="st_parts">Part numbers online</em></div>
      <div class="st"><b>%(nc)d</b><em data-i18n="st_cats">Product categories</em></div>
      <div class="st"><b>10,000+ m²</b><em data-i18n="st_wh">Warehouse in Guangzhou</em></div>
    </div>
  </div>
  <img src="assets/hero/about-warehouse.webp" alt="Guangzhou warehouse" loading="lazy">
</div>
</section>""" % {"nt": "{:,}".format(total), "nc": n_cats}


CORE = [("coil", "prod-coil.webp", "Ignition coils", "Ignition Coils"),
        ("abs", "prod-abs.webp", "ABS sensors", "ABS Sensors"),
        ("fuelpump", "prod-fuelpump.webp", "Fuel pumps", "Fuel Pumps")]


def home_core_html(cfg, by_cat):
    """首页「三条主营线」：用目录里的真实产品图。"""
    cards = []
    for key, img, label, en in CORE:
        slug = CAT_META.get(key, (key,))[0]
        n = len(by_cat.get(key) or [])
        cards.append(
            '<a href="category/%s.html">'
            '<img src="assets/hero/%s" alt="%s" loading="lazy">'
            '<div class="tx"><b data-cat="%s">%s</b>'
            '<span data-i18n="models_n" data-v-n="%d">%d models</span>'
            '<em><span data-i18n="view_range">View range</span> &rarr;</em></div></a>'
            % (slug, img, esc(en), key, esc(en), n, n))
    return ('<section class="sect"><div class="head">'
            '<h2 data-i18n="core_h2">Three lines we ship every week</h2>'
            '<b data-i18n="core_sub">from 23 categories</b>'
            '<a href="category/index.html" data-i18n="core_all">All products</a></div>'
            '<div class="hcore">%s</div></section>' % "".join(cards))


def home_contact_html(cfg):
    """首页联系条：WhatsApp / 销售电话 / 邮箱 / 地址（手机端也要一眼看到）。"""
    wa = wa_link(cfg, "Hi, I would like a quotation for auto parts.")
    return """<section class="hct"><div class="in">
  <div class="ci"><i>&#9990;</i><div><b>WhatsApp</b><span>%s</span></div></div>
  <div class="ci"><i>&#9742;</i><div><b data-i18n="foot_sales">Sales office</b><span>%s</span></div></div>
  <div class="ci"><i>&#9993;</i><div><b data-i18n="foot_email">Email</b><span><a href="mailto:%s">%s</a></span></div></div>
  <div class="ci"><i>&#9873;</i><div><b data-i18n="foot_addr_h">Address</b><span>%s</span></div></div>
</div></section>""" % (esc(wa_display(cfg["whatsapp"])), esc(PHONE_SALES),
                      esc(cfg["email"]), esc(cfg["email"]), addr_span(cfg))


def load_terms():
    """读 付款与装运.txt：英文键 = 值"""
    path = os.path.join(HERE, "付款与装运.txt")
    out = {}
    if not os.path.exists(path):
        return out
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
            elif ":" in line:
                k, v = line.split(":", 1)
            else:
                continue
            out[k.strip()] = v.strip()
    return out


TERMS = {}


def _prow(label_key, label_en, main, note="", val_key="", note_key=""):
    """一行条款。val_key / note_key 是「值」和「小字」的 i18n 键：
    英文仍然以 付款与装运.txt 为准（data-i18n-src 兜底），翻译在 i18n.js 里。"""
    if not main:
        return ""
    if note:
        note_html = '<em><span%s>%s</span></em>' % (
            (' data-i18n="%s"' % note_key) if note_key else "", esc(note))
    else:
        note_html = ""
    main_html = ('<span data-i18n="%s">%s</span>' % (val_key, esc(main))) if val_key else esc(main)
    return ('<div class="prow"><b data-i18n="%s">%s</b><span>%s%s</span></div>'
            % (label_key, esc(label_en), main_html, note_html))


def pay_card_html():
    """型号页那一张卡。"""
    t = TERMS
    rows = _prow("pay_t", "Bank transfer (T/T)", t.get("t_t", ""), val_key="payv_t")
    rows += _prow("pay_lc", "Letter of credit", t.get("l_c", ""), val_key="payv_lc")
    if not rows:
        return ""
    return ('<div class="tc"><b data-i18n="t_pay">Payment</b><span>%s'
            '<a class="paymore" href="../contact.html" data-i18n="pay_more">Payment &amp; shipping terms</a>'
            '</span></div>' % rows)


def pay_block_html():
    """联系页那一整块。"""
    t = TERMS
    pay = (_prow("pay_t", "Bank transfer (T/T)", t.get("t_t", ""), t.get("t_t_note", ""),
                 "payv_t", "payv_t_note") +
           _prow("pay_lc", "Letter of credit", t.get("l_c", ""), t.get("l_c_note", ""),
                 "payv_lc", "payv_lc_note") +
           _prow("pay_sample", "Samples / small orders", t.get("sample_pay", ""),
                 t.get("sample_pay_note", ""), "payv_sample", "payv_sample_note") +
           _prow("pay_cur", "Currency", t.get("currency", ""), t.get("currency_note", ""),
                 "payv_cur", "payv_cur_note"))
    ship = (_prow("pay_terms", "Shipping terms", t.get("terms", ""), t.get("terms_note", ""),
                  "payv_terms", "payv_terms_note") +
            _prow("t_lead", "Lead time", t.get("lead_time", ""), t.get("lead_time_note", ""),
                  "payv_lead", "payv_lead_note"))
    docs = _prow("pay_docs", "Documents", t.get("docs", ""), t.get("docs_note", ""),
                 "payv_docs", "payv_docs_note")
    if not (pay or ship or docs):
        return ""
    return ("""<section class="payblock">
<h2 data-i18n="pay_h">Payment, shipping &amp; documents</h2>
<div class="paygrid">
  <div class="paycol"><h3 data-i18n="pay_payment">Payment</h3>%s</div>
  <div class="paycol"><h3 data-i18n="pay_shipping">Shipping</h3>%s</div>
  <div class="paycol"><h3 data-i18n="pay_docs_h">Documents</h3>%s</div>
</div>
<p class="payfoot" data-i18n="pay_foot">Nothing here matches your requirement? Send us your terms — most buyers'
terms can be accommodated on repeat orders.</p>
</section>""" % (pay, ship, docs))


# Contact 页的询价表单：纯前端拼消息，不上传任何东西。
# 这一段必须留在模板里 —— 只改 contact.html 的话，下一次 rerender 会被覆盖掉。
RFQ_HTML = """  <section class="rfq" id="quote">
    <h2 data-i18n="rfq_h">Request a quotation</h2>
    <p class="rfqlead" data-i18n="rfq_lead">Fill the four fields and add your part list, then send it on WhatsApp — or by email if you prefer.
    Nothing is uploaded: the button opens WhatsApp (or your mail app) with the text already filled in.
    <span class="zh-extra">填好四栏、贴上型号和数量，点 WhatsApp 直接发给我们（也可以发邮件）。</span></p>
    <form id="rfq" novalidate>
      <div class="rfqgrid">
        <label for="rfq-name"><span data-i18n="rfq_name">Name / company</span>
          <input id="rfq-name" type="text" autocomplete="organization" placeholder="ACME Auto Parts"></label>
        <label for="rfq-country"><span data-i18n="rfq_country">Country</span>
          <input id="rfq-country" type="text" autocomplete="country-name" placeholder="Iraq"></label>
        <label for="rfq-contact"><span data-i18n="rfq_contact">Email or WhatsApp</span>
          <input id="rfq-contact" type="text" autocomplete="email" placeholder="buyer@example.com"></label>
        <label for="rfq-parts"><span data-i18n="rfq_parts">Parts &amp; quantity</span>
          <textarea id="rfq-parts" rows="5" placeholder="WL03-0004 x 200&#10;90919-02248 x 100"></textarea></label>
      </div>
      <div class="rfqbtns">
        <button type="button" class="btn-wa" id="rfq-wa">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2a10 10 0 00-8.5 15.2L2 22l4.9-1.4A10 10 0 1012 2zm0 2a8 8 0 016.9 12l-.3.5 1 3-3.1-.9-.5.3A8 8 0 1112 4z"/></svg>
          <span data-i18n="rfq_wa">Send on WhatsApp</span></button>
        <button type="submit" class="btn-ghost">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 5h18v14H3z" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="M3 6l9 7 9-7" fill="none" stroke="currentColor" stroke-width="1.8"/></svg>
          <span data-i18n="rfq_mail">Send by email</span></button>
      </div>
      <p class="rfqnote" data-i18n="rfq_note">We answer within one working day, Mon–Sat 09:00–18:00 (GMT+8).</p>
    </form>
  </section>
"""

RFQ_SCRIPT = """<script>
(function(){
  var f = document.getElementById('rfq');
  if(!f) return;
  function v(id){ var e = document.getElementById(id); return e ? (e.value || '').trim() : ''; }
  function body(){
    return 'Name / company: ' + (v('rfq-name') || '-') + '\\n' +
           'Country: ' + (v('rfq-country') || '-') + '\\n' +
           'Email / WhatsApp: ' + (v('rfq-contact') || '-') + '\\n' +
           '\\nParts & quantity:\\n' + (v('rfq-parts') || '-') + '\\n' +
           '\\n-- sent from ' + location.href;
  }
  f.addEventListener('submit', function(e){
    e.preventDefault();
    var country = v('rfq-country');
    var subject = 'Quotation request' + (country ? ' - ' + country : '');
    location.href = 'mailto:%s?subject=' + encodeURIComponent(subject) +
                    '&body=' + encodeURIComponent(body());
  });
  var w = document.getElementById('rfq-wa');
  if(w) w.addEventListener('click', function(){
    var text = 'Hi, I would like a quotation.\\n\\n' + body();
    window.open('https://wa.me/%s?text=' + encodeURIComponent(text), '_blank', 'noopener');
  });
})();
</script>
"""


def page_contact(cfg):
    """独立的 Contact 页：导航里那个 Contact 要真的能跳。"""
    title = "Contact us — Guangzhou Yumengyang Auto Parts"
    desc = ("Contact Guangzhou Yumengyang Auto Parts: WhatsApp, sales phone, email and warehouse address. "
            "We answer within one working day.")
    canon = rel_url(cfg, "contact.html")
    wa = wa_link(cfg, "Hi, I would like a quotation for auto parts.")
    body = """<body class="docpage">
%s
<main id="main" tabindex="-1" class="policy">
<nav class="crumbs"><a href="index.html" data-i18n="home">Home</a> &rsaquo;
  <span data-i18n="nav_contact">Contact</span></nav>
<article class="doc">
  <h1 data-i18n="nav_contact">Contact</h1>
  <p class="doclead" data-i18n="contact_lead">Send the OE number, a photo or your list — we reply with
  price, MOQ and packing within one working day.</p>
  <section class="doccontact">
    <p class="docorg"><b class="notranslate" %s>%s</b> · <span class="notranslate" %s>%s</span></p>
    <p><b>WhatsApp</b>: <a href="%s" target="_blank" rel="noopener">%s</a></p>
    <p><b data-i18n="foot_sales">Sales office</b>: <a href="tel:+8619577863139">%s</a></p>
    <p><b data-i18n="foot_email">Email</b>: <a href="mailto:%s">%s</a></p>
    <p class="docaddr">%s</p>
    <p><span data-i18n="foot_hours">Working hours</span>: %s</p>
    <div style="display:flex;gap:18px;flex-wrap:wrap;margin-top:12px">
      <div style="text-align:center"><img src="assets/hero/qr-wecom.webp" alt="WeCom QR"
        style="width:132px;height:132px;background:#fff;border:1px solid #e6edf2;border-radius:10px;padding:5px">
        <div><a class="qrbtn qrbtn-wecom" href="%s" target="_blank" rel="noopener" data-i18n="foot_qr_wecom">WeCom</a></div></div>
      <div style="text-align:center"><img src="assets/hero/qr-whatsapp.webp" alt="WhatsApp QR"
        style="width:132px;height:132px;background:#fff;border:1px solid #e6edf2;border-radius:10px;padding:5px">
        <div><a class="qrbtn qrbtn-wa" href="%s" target="_blank" rel="noopener">WhatsApp</a></div></div>
    </div>
    <p><a class="btn-wa" href="%s" target="_blank" rel="noopener">%s</a>
       <a class="btn-ghost" href="index.html" data-i18n="nf_back">Back to the lookup home</a></p>
  </section>
</article>
</main>
%s
</body></html>""" % (sitehead(cfg, "contact", base=""), NOTRANSLATE, esc(BRAND_CN), NOTRANSLATE,
                      esc(cfg["company_en"]), esc(wa), esc(wa_display(cfg["whatsapp"])),
                      esc(PHONE_SALES), esc(cfg["email"]), esc(cfg["email"]), addr_span(cfg),
                      esc(cfg["hours"]), esc(QR_LINK_WECOM), esc(QR_LINK_WHATSAPP),
                      esc(wa), esc("WhatsApp " + wa_display(cfg["whatsapp"])),
                      sitefoot(cfg, base=""))
    body = body.replace('<section class="doccontact">',
                        RFQ_HTML + '<section class="doccontact">', 1)
    body = body.replace('<section class="doccontact">', pay_block_html() + '<section class="doccontact">', 1)
    body = body.replace('</body></html>',
                        RFQ_SCRIPT % (esc(cfg["email"]), esc(cfg["whatsapp"])) + '</body></html>', 1)
    return head_block(cfg, title, desc, canon, "assets/og/og-default.webp", "website",
                      [{"@context": "https://schema.org", "@type": "ContactPage",
                        "name": "Contact — " + cfg["company_en"],
                        "inLanguage": "en", "isPartOf": {"@type": "WebSite",
                                                          "url": cfg["site_url"] + "/"}}],
                      base="") + "\n" + body



# ------------------------------------------------------------------ 主入口
def build_static(items, cats, log=print):
    cfg = load_cfg()
    global PRICING, TERMS
    PRICING = load_pricing()
    TERMS = load_terms()
    log("  品类定价：%d 个品类有配置" % len(PRICING))
    cfg["_total"] = len(items)
    t0 = time.time()
    clash = make_slugs(items, keep_existing=True)

    by_cat = {}
    for it in items:
        by_cat.setdefault(it["cat"], []).append(it)

    # 导航条上放“热销 4 类 + 型号最多的 1 类”，顺序按 order_cats；0 型号的品类不进任何入口
    global LIVE_N
    LIVE_N = len([c for c in cats if by_cat.get(c["key"])])
    NAV_KEYS[:] = [c["key"] for c in order_cats(
        [{"key": c["key"], "n": len(by_cat.get(c["key"], []))} for c in cats])]

    cdir = os.path.join(HERE, "c")
    catdir = os.path.join(HERE, "category")
    os.makedirs(cdir, exist_ok=True)
    os.makedirs(catdir, exist_ok=True)
    # 先清掉上一轮生成的 html，避免品类改名/型号下架后留下孤儿页
    for d in (cdir, catdir):
        for fn in os.listdir(d):
            if fn.endswith(".html"):
                try:
                    os.remove(os.path.join(d, fn))
                except OSError:
                    pass

    counts = {}
    # 内链：先建两张倒排表，再给每个型号算好两块链接（写死在 HTML 里，不靠 JS）
    t_link = time.time()
    by_i, code_map, token_map = build_link_index(items)
    for it in items:
        it["_lnk_oe"], it["_lnk_veh"] = pick_links(it, by_i, code_map, token_map)
    n_orphan, n_fixed = repair_orphans(items)
    log("  内链：孤立页 %d 个，补齐 %d 个" % (n_orphan, n_fixed))
    log("  内链索引：%d 个归一码 / %d 个车型关键词（%.1f 秒）"
        % (len(code_map), len(token_map), time.time() - t_link))

    # 品牌识别：型号页里要显示「Fits brands」并链到 /brand/（品牌页的入链主要靠这一行）
    global LIVE_BRAND_SLUGS
    if brandlib is not None:
        for it in items:
            it["_brands"] = brandlib.brand_hits(it.get("a"))
        _bc = {}
        for it in items:
            for b in it["_brands"]:
                _bc[b] = _bc.get(b, 0) + 1
        LIVE_BRAND_SLUGS = {brandlib.brand_slug(b) for b, n in _bc.items() if n >= 8}
    else:
        LIVE_BRAND_SLUGS = set()

    for idx, it in enumerate(items):
        cat = it["cat"]
        htmltext = page_model(cfg, it, cat)
        with open(os.path.join(cdir, it["s"] + ".html"), "w", encoding="utf-8", newline="\n") as f:
            f.write(htmltext)
        counts[cat] = counts.get(cat, 0) + 1

    make_og_images(cfg, cats)
    try:
        make_og_default(cfg)                        # assets/og/og-default.webp（首页/政策页/指南页）
    except Exception as e:
        log("  [warn] 默认分享图没生成：%s" % e)

    cat_files = []          # 全部品类页（含 0 型号的）
    live_cat_files = []     # 只进 sitemap 的那批
    for c in cats:
        key = c["key"]
        all_items = by_cat.get(key, [])
        total_pages = max(1, (len(all_items) + PER_PAGE - 1) // PER_PAGE)
        for p in range(1, total_pages + 1):
            chunk = all_items[(p - 1) * PER_PAGE: p * PER_PAGE]
            text = page_category(cfg, key, all_items, chunk, p, total_pages)
            fname = "%s.html" % cat_slug(key) if p == 1 else "%s-%d.html" % (cat_slug(key), p)
            with open(os.path.join(catdir, fname), "w", encoding="utf-8", newline="\n") as f:
                f.write(text)
            cat_files.append(fname)
            if all_items:
                live_cat_files.append(fname)

    with open(os.path.join(catdir, "index.html"), "w", encoding="utf-8", newline="\n") as f:
        f.write(page_cat_index(cfg, cats, by_cat))

    # ---- 品牌页 / 车型页（从适配车型数据自动分组的长尾落地页）
    brand_files, vehicle_files = [], []
    bentries = []
    if brandlib is not None:
        # 先算车型页（品牌页的「热门车型」chips 只链已经生成出来的页，不产生死链）
        vmap = {}
        for it in items:
            for t in brandlib.vehicle_tokens(it.get("a")):
                vmap.setdefault(t, []).append(it)
        ventries = []
        for tok in sorted(vmap, key=lambda t: (-len(vmap[t]), t)):
            lst = vmap[tok]
            if len(lst) < 8:
                continue
            bcnt = {}
            for it in lst:
                for b in it.get("_brands") or ():
                    bcnt[b] = bcnt.get(b, 0) + 1
            ventries.append({"token": tok, "slug": brandlib.token_slug(tok), "items": lst, "n": len(lst),
                             "brands": [{"canon": b, "slug": brandlib.brand_slug(b)}
                                        for b in sorted(bcnt, key=lambda x: (-bcnt[x], x))]})
        for e in ventries:
            e["others"] = [x for x in ventries if x["slug"] != e["slug"]]
        live_tokens = {e["token"] for e in ventries}

        bmap = {}
        for it in items:
            for b in it.get("_brands") or ():
                bmap.setdefault(b, []).append(it)
        bentries = []
        for canon in sorted(bmap, key=lambda c: (-len(bmap[c]), c)):
            lst = bmap[canon]
            if len(lst) < 8:
                continue
            toks, xfit = {}, {}
            for it in lst:
                for t in brandlib.vehicle_tokens(it.get("a")):
                    if t in live_tokens:
                        # 归属写死过（MODEL_OWNER）才算「本品牌车型」；
                        # 其余是跨品牌共通件（丰田线圈也装长安逸动这种），
                        # 单独列在「也适用这些车型」，绝不冒充本品牌车型。
                        d = toks if brandlib.model_owner(t) == canon else xfit
                        d[t] = d.get(t, 0) + 1
            bentries.append({"canon": canon, "slug": brandlib.brand_slug(canon), "items": lst, "n": len(lst),
                             "tokens": sorted(toks.items(), key=lambda kv: (-kv[1], kv[0])),
                             "xfit": sorted(xfit.items(), key=lambda kv: (-kv[1], kv[0]))})
        for e in bentries:
            e["others"] = [x for x in bentries if x["slug"] != e["slug"]]

        bdir = os.path.join(HERE, "brand")
        os.makedirs(bdir, exist_ok=True)
        for fn in os.listdir(bdir):
            if fn.endswith(".html"):
                try:
                    os.remove(os.path.join(bdir, fn))
                except OSError:
                    pass
        for e in bentries:
            with open(os.path.join(bdir, e["slug"] + ".html"), "w", encoding="utf-8", newline="\n") as f:
                f.write(page_brand(cfg, e))
            brand_files.append(e["slug"] + ".html")
        with open(os.path.join(bdir, "index.html"), "w", encoding="utf-8", newline="\n") as f:
            f.write(page_brands_index(cfg, bentries, len({it["i"] for it in items if it.get("_brands")})))

        vdir = os.path.join(HERE, "vehicle")
        os.makedirs(vdir, exist_ok=True)
        for fn in os.listdir(vdir):
            if fn.endswith(".html"):
                try:
                    os.remove(os.path.join(vdir, fn))
                except OSError:
                    pass
        for e in ventries:
            with open(os.path.join(vdir, e["slug"] + ".html"), "w", encoding="utf-8", newline="\n") as f:
                f.write(page_vehicle(cfg, e))
            vehicle_files.append(e["slug"] + ".html")
        with open(os.path.join(vdir, "index.html"), "w", encoding="utf-8", newline="\n") as f:
            f.write(page_vehicles_index(cfg, ventries,
                                        len({it["i"] for t, lst in vmap.items() if len(lst) >= 8 for it in lst})))
        log("  品牌页 %d 个 / 车型页 %d 个" % (len(bentries), len(ventries)))

    # 政策页（根目录）：privacy.html / returns.html
    policy_files = []
    for kind in ("privacy", "returns"):
        fname = "%s.html" % kind
        with open(os.path.join(HERE, fname), "w", encoding="utf-8", newline="\n") as f:
            f.write(page_policy(cfg, kind))
        policy_files.append(fname)

    # 公司介绍页：about.html（说真话版本，含中文摘要）
    with open(os.path.join(HERE, "about.html"), "w", encoding="utf-8", newline="\n") as f:
        f.write(page_about(cfg))
    with open(os.path.join(HERE, "contact.html"), "w", encoding="utf-8", newline="\n") as f:
        f.write(page_contact(cfg))

    # 采购指南（guides/）：正文在 guides_content.py，这里只负责套模板 + 解析内链
    guide_files = []
    if guides_content is not None and getattr(guides_content, "GUIDES", None):
        gdir = os.path.join(HERE, "guides")
        os.makedirs(gdir, exist_ok=True)
        resolve = make_guide_resolver(items)
        with open(os.path.join(gdir, "index.html"), "w", encoding="utf-8", newline="\n") as f:
            f.write(page_guides_index(cfg))
        guide_files.append("index.html")
        for g in guides_content.GUIDES:
            with open(os.path.join(gdir, g["slug"] + ".html"), "w", encoding="utf-8", newline="\n") as f:
                f.write(page_guide(cfg, g, resolve))
            guide_files.append(g["slug"] + ".html")
        log("  采购指南：%d 篇 + 目录页" % (len(guides_content.GUIDES)))

    # 故障码诊断页（codes/）：正文在 codes_content.py。定位是"码 → 我们的件"，
    # 不是全量字典，所以数量少、每页厚。
    code_files = []
    if _code_list():
        codir = os.path.join(HERE, "codes")
        os.makedirs(codir, exist_ok=True)
        for fn in os.listdir(codir):
            if fn.endswith(".html"):
                try:
                    os.remove(os.path.join(codir, fn))
                except OSError:
                    pass
        cresolve = make_guide_resolver(items)
        cat_counts = {k: len(v) for k, v in by_cat.items()}
        with open(os.path.join(codir, "index.html"), "w", encoding="utf-8", newline="\n") as f:
            f.write(page_codes_index(cfg))
        code_files.append("index.html")
        for c in _code_list():
            with open(os.path.join(codir, c["code"].lower() + ".html"), "w",
                      encoding="utf-8", newline="\n") as f:
                f.write(page_code(cfg, c, cresolve, cat_counts))
            code_files.append(c["code"].lower() + ".html")
        log("  故障码页：%d 个 + 目录页" % len(_code_list()))

    # sitemap：lastmod 用本次生成的时间戳（带时区），内容是每页都变了，别再用「今天」糊过去
    today = __import__("datetime").datetime.now().astimezone().replace(microsecond=0).isoformat()
    urls = ['<url><loc>%s</loc><lastmod>%s</lastmod><changefreq>weekly</changefreq><priority>0.9</priority></url>'
            % (esc(cfg["site_url"] + "/"), today)]
    urls.append('<url><loc>%s</loc><lastmod>%s</lastmod><changefreq>weekly</changefreq><priority>0.8</priority></url>'
                % (esc(rel_url(cfg, "category/index.html")), today))
    for fname in live_cat_files:
        urls.append('<url><loc>%s</loc><lastmod>%s</lastmod><changefreq>weekly</changefreq><priority>0.7</priority></url>'
                    % (esc(rel_url(cfg, "category/" + fname)), today))
    # 品牌页 / 车型页（长尾入口）
    if brand_files or vehicle_files:
        urls.append('<url><loc>%s</loc><lastmod>%s</lastmod><changefreq>weekly</changefreq><priority>0.8</priority></url>'
                    % (esc(rel_url(cfg, "brand/index.html")), today))
        for fname in brand_files:
            urls.append('<url><loc>%s</loc><lastmod>%s</lastmod><changefreq>weekly</changefreq><priority>0.7</priority></url>'
                        % (esc(rel_url(cfg, "brand/" + fname)), today))
        urls.append('<url><loc>%s</loc><lastmod>%s</lastmod><changefreq>weekly</changefreq><priority>0.7</priority></url>'
                    % (esc(rel_url(cfg, "vehicle/index.html")), today))
        for fname in vehicle_files:
            urls.append('<url><loc>%s</loc><lastmod>%s</lastmod><changefreq>monthly</changefreq><priority>0.6</priority></url>'
                        % (esc(rel_url(cfg, "vehicle/" + fname)), today))
    for it in items:
        urls.append('<url><loc>%s</loc><lastmod>%s</lastmod><changefreq>monthly</changefreq><priority>0.6</priority></url>'
                    % (esc(rel_url(cfg, "c/%s.html" % it["s"])), today))
    # 采购指南：内容页 priority 与品类页看齐，目录页略低
    for fname in guide_files:
        pr = "0.6" if fname == "index.html" else "0.7"
        urls.append('<url><loc>%s</loc><lastmod>%s</lastmod><changefreq>monthly</changefreq><priority>%s</priority></url>'
                    % (esc(rel_url(cfg, "guides/" + fname)), today, pr))
    # 故障码诊断页
    for fname in code_files:
        pr = "0.6" if fname == "index.html" else "0.7"
        urls.append('<url><loc>%s</loc><lastmod>%s</lastmod><changefreq>monthly</changefreq><priority>%s</priority></url>'
                    % (esc(rel_url(cfg, "codes/" + fname)), today, pr))
    for fname in policy_files:
        urls.append('<url><loc>%s</loc><lastmod>%s</lastmod><changefreq>yearly</changefreq><priority>0.3</priority></url>'
                    % (esc(rel_url(cfg, fname)), POLICY_DATE))
    # 公司介绍页：优先级与品类页看齐 —— 它是买家判断「能不能汇款」的那一页
    urls.append('<url><loc>%s</loc><lastmod>%s</lastmod><changefreq>monthly</changefreq><priority>0.7</priority></url>'
                % (esc(rel_url(cfg, "about.html")), today))
    urls.append('<url><loc>%s</loc><lastmod>%s</lastmod><changefreq>monthly</changefreq><priority>0.7</priority></url>'
                % (esc(rel_url(cfg, "contact.html")), today))
    # 产品目录页（2026-11-10 从首页拆出来）：全站型号的总入口，优先级高于品类索引
    urls.append('<url><loc>%s</loc><lastmod>%s</lastmod><changefreq>weekly</changefreq><priority>0.8</priority></url>'
                % (esc(rel_url(cfg, "products.html")), today))
    # 批量查价页：工具体验页，买家经常从导航进来，之前漏在 sitemap 外
    urls.append('<url><loc>%s</loc><lastmod>%s</lastmod><changefreq>monthly</changefreq><priority>0.5</priority></url>'
                % (esc(rel_url(cfg, "list.html")), today))
    sm = ('<?xml version="1.0" encoding="UTF-8"?>\n'
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
          + "\n".join(urls) + "\n</urlset>\n")
    open(os.path.join(HERE, "sitemap.xml"), "w", encoding="utf-8", newline="\n").write(sm)

    robots = ("User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n" % cfg["site_url"])
    open(os.path.join(HERE, "robots.txt"), "w", encoding="utf-8", newline="\n").write(robots)

    open(os.path.join(HERE, "404.html"), "w", encoding="utf-8", newline="\n").write(page_404(cfg))

    inject_home(cfg, cats, by_cat, bentries or None)
    inject_products(cfg, cats, by_cat, bentries or None)

    log("  型号页 %d 个（slug 冲突加后缀 %d 个）" % (len(items), len(clash)))
    log("  品类页 %d 个（%d 条/页）· sitemap %d 条 URL" % (len(cat_files), PER_PAGE, len(urls)))
    log("  域名：%s　WhatsApp：%s" % (cfg["site_url"], cfg["whatsapp"]))
    log("  分享图：assets/og/ 共 %d 张" % len(cats))
    log("  静态页用时：%.1f 秒" % (time.time() - t0))
    return {"pages": len(items), "clash": clash, "urls": len(urls), "cfg": cfg, "cat_files": len(cat_files)}
