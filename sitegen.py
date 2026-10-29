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
import re
import time
from urllib.parse import quote

HERE = os.path.dirname(os.path.abspath(__file__))
CFG_FILE = os.path.join(HERE, "站点设置.txt")

DEFAULT_CFG = {
    "site_url": "https://your-domain.com",
    "whatsapp": "8615915859048",
    "company_en": "Guangzhou Yumengyang Auto Parts Co., Ltd.",
    "company_cn": "广州驭盟扬汽车零部件有限公司",
}

# 品牌显示（别在模板里散着写名字，改一处全站生效）
# translate="no" + class="notranslate" 是给浏览器自动翻译看的：Edge / Chrome / iOS Safari
# 翻页面时会跳过这些节点，避免把 Yumengyang 翻成「玉明阳」这种鬼东西。
# 注意：不整页禁译（客户可能想翻译页面），只锁品牌名。
BRAND_EN = "Yumengyang"
BRAND_EN2 = "Auto Parts"
BRAND_CN = "广州驭盟扬汽配"
NOTRANSLATE = 'translate="no"'

# 界面多语言：文案字典在 assets/i18n.js（全站共用一个文件，页面里只放 data-i18n 标记）。
# 这里只负责语言切换器的 HTML 和“首屏防闪”的小脚本。
LANG_OPTIONS = [("en", "English"), ("zh", "简体中文"), ("ar", "العربية"), ("ru", "Русский")]


def lang_sel_html():
    opts = "".join('<option value="%s">%s</option>' % (k, esc(v)) for k, v in LANG_OPTIONS)
    return ('<label class="sr-only" for="langsel">Language</label>'
            '<select id="langsel" class="langsel" aria-label="Language" translate="no">%s</select>' % opts)


LANG_BOOT = ('<script>try{var l=(new URLSearchParams(location.search).get("lang")||'
             'localStorage.getItem("ymy_lang")||"en").toLowerCase();'
             'l=l.indexOf("zh")===0?"zh":l.indexOf("ar")===0?"ar":l.indexOf("ru")===0?"ru":"en";'
             'var d=document.documentElement;d.setAttribute("data-lang",l);'
             'if(l==="ar")d.setAttribute("dir","rtl")}catch(e){}</script>')

# 热销品类排最前，其余按型号数从多到少（首页按钮 / 导航 / 品类总览 / 首页目录块共用）
HOT_ORDER = ["coil", "fuelpump", "o2", "plug"]
NAV_KEYS = []          # build_static 里算好，给 sitehead 用


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
            "电话": "whatsapp",
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


def make_slugs(items):
    """优先 OE 号，其次内部型号；重复的加 -2、-3 后缀。"""
    used, clash = set(), []
    for it in items:
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


# ------------------------------------------------------------------ 页面片段
def head_block(cfg, title, desc, canonical, og_image="", og_type="product", ld_list=None):
    """canonical / og:url / og:image 只在填了真实域名时才输出；
    域名还是占位符时，页面照样能双击打开、能部署，只是没有这些标签（不会指错地方）。"""
    site = has_site(cfg)
    img = ""
    if og_image and site:
        img = '\n<meta property="og:image" content="%s">' % esc(rel_url(cfg, og_image))
    can = ""
    ogurl = ""
    if canonical and site:
        can = '\n<link rel="canonical" href="%s">' % esc(canonical)
        ogurl = '\n<meta property="og:url" content="%s">' % esc(canonical)
    ld = "".join('\n<script type="application/ld+json">%s</script>' % json.dumps(x, ensure_ascii=False)
                 for x in (ld_list or []))
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta name="robots" content="index,follow">{can}
<meta property="og:type" content="{ogtype}">
<meta property="og:site_name" content="Guangzhou Yumengyang Auto Parts">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">{ogurl}{img}
<meta name="twitter:card" content="summary_large_image">
<link rel="stylesheet" href="../assets/style.css">
{langboot}
<script defer src="../assets/i18n.js"></script>{ld}
</head>""".format(title=esc(title), desc=esc(desc), can=can, ogurl=ogurl,
                 ogtype=og_type, img=img, ld=ld, langboot=LANG_BOOT)


def sitehead(cfg, active=""):
    keys = NAV_KEYS or ["coil", "abs", "wire", "thermo", "plug"]
    nav = []
    for key in keys[:5]:
        slug, en, _one, _cn = CAT_META.get(key, (key, key, key, key))
        cls = ' class="on"' if active == key else ""
        nav.append('<a href="../category/%s.html"%s data-cat="%s">%s</a>' % (slug, cls, key, esc(en)))
    return """<header class="sitehead"><div class="wrap">
<a class="brand notranslate" %s href="../index.html">%s<em %s>%s</em></a>
<nav>%s<a href="../category/index.html" data-i18n="nav_all" data-v-n="%d">All %d categories</a></nav>
<div class="tools">%s<a class="wapush" href="%s" target="_blank" rel="noopener" data-i18n="wa">WhatsApp Us</a></div>
</div></header>""" % (NOTRANSLATE, BRAND_EN, NOTRANSLATE, BRAND_EN2,
                       "".join(nav), len(CAT_META), len(CAT_META), lang_sel_html(),
                       esc(wa_link(cfg, "Hi, I have an inquiry about auto parts.")))


def sitefoot(cfg):
    return """<footer class="sitefoot"><div class="wrap">
<div><b class="notranslate" %s>%s</b> · <span class="notranslate" %s>%s</span></div>
<div><a href="../index.html" data-i18n="lookup">OE / cross-reference lookup</a> · <a href="../sitemap.xml" data-i18n="sitemap">Sitemap</a></div>
</div></footer>""" % (NOTRANSLATE, esc(BRAND_CN), NOTRANSLATE, esc(cfg["company_en"]))


SPEC_LABELS = [("spec_oe", "OE number"), ("spec_xref", "Cross-reference"), ("spec_brand", "Brand"),
               ("spec_fit", "Vehicle fitment"), ("spec_notes", "Notes"), ("our_sku", "Our SKU")]


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
    if it.get("r"):
        rows.append(("spec_notes", esc(it["r"])))
    rows.append(("our_sku", esc(it["m"])))
    label = dict(SPEC_LABELS)
    return "".join('<tr><th data-i18n="%s">%s</th><td>%s</td></tr>' % (k, label.get(k, k), v)
                   for k, v in rows)


def page_model(cfg, it, cat, related):
    one = type_name(cat)
    primary = it.get("oe") or it.get("m")
    hint = fitment_hint(it.get("a"), it.get("b"))
    head = "%s %s" % (primary, one)
    title = head + ((" for " + hint) if hint else "")
    suffix = " | Guangzhou Yumengyang Auto Parts"
    if len(title) + len(suffix) > 78:
        suffix = " | Yumengyang Auto Parts"
    if len(title) + len(suffix) > 78:
        title = head
    title += suffix

    apps = clean_text(it.get("a"))
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
    if len(desc) > 160:
        desc = desc[:155].rsplit(" ", 1)[0].rstrip(" ,.;") + tail

    slug = it["s"]
    page_path = "c/%s.html" % slug
    canonical = rel_url(cfg, page_path)

    ld = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": "%s %s" % (one, primary),
        "sku": it.get("m", ""),
        "mpn": it.get("m", ""),
        "brand": {"@type": "Brand", "name": it.get("b") or "WEILI"},
        "category": CAT_META[cat][1],
        "description": clean_text(desc),
    }
    if has_site(cfg):
        ld["url"] = canonical
    if it.get("p"):
        ld["image"] = [rel_url(cfg, it["p"])]
    props = []
    if it.get("oe"):
        props.append({"@type": "PropertyValue", "name": "OE Number", "value": it["oe"]})
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

    rel_html = ""
    if related:
        rel_html = ('<section class="pdp-block"><h2><span data-i18n="more">More</span> '
                    '<span data-cat="%s">%s</span></h2><ul class="rel">%s</ul></section>' % (
                        cat, esc(CAT_META[cat][1]),
                        "".join('<li><a href="../c/%s.html">%s</a></li>'
                                % (esc(r["s"]), esc(r.get("oe") or r["m"])) for r in related)))

    total_txt = "{:,}".format(cfg.get("_total", 0))
    body = """<body class="pdp">
%s
<main class="pdp-main">
<nav class="crumbs"><a href="../index.html" data-i18n="home">Home</a> &rsaquo; <a href="../category/%s.html" data-cat="%s">%s</a> &rsaquo; <span>%s</span></nav>
<div class="pdp-grid">
  <figure class="pdp-pic">%s</figure>
  <div class="pdp-info">
    <div class="kicker" data-cat="%s">%s</div>
    <h1>%s</h1>
    <p class="sub2"><span data-i18n="our_sku">Our SKU</span> <b>%s</b>%s</p>
    <p class="langnote" data-i18n="langnote">Product data is shown in English</p>
    <table class="spec">%s</table>
    <div class="cta">
      <a class="btn-wa" href="%s" target="_blank" rel="noopener">
        <svg viewBox="0 0 24 24"><path d="M12 2a10 10 0 00-8.5 15.2L2 22l4.9-1.4A10 10 0 1012 2zm0 2a8 8 0 016.9 12l-.3.5 1 3-3.1-.9-.5.3A8 8 0 1112 4z"/></svg>
        <span data-i18n="btn_wa">WhatsApp for price &amp; MOQ</span>
      </a>
      <a class="btn-ghost" href="../index.html?q=%s" data-i18n="btn_search_all" data-v-n="%s">Search all %s parts</a>
    </div>
  </div>
</div>
<section class="pdp-block"><h2 data-i18n="block_app">Vehicle application</h2>%s</section>
%s
<section class="pdp-block"><h2 data-i18n="block_buy">Buying this part</h2><p data-i18n="buy_text" data-v-company="%s" data-v-brand="%s">%s supplies these parts under our own brand %s. Send us the OE number on WhatsApp and we will confirm availability, price, MOQ and packing. Samples for testing are available on request.</p></section>
</main>
%s
</body></html>
""" % (sitehead(cfg, cat), cat_slug(cat), cat, esc(CAT_META[cat][1]), esc(primary), pic,
       cat, esc(CAT_META[cat][1]), esc(primary), esc(it["m"]),
       (" · brand " + esc(it["b"])) if it.get("b") else "",
       spec_rows(it), esc(wa), quote(it.get("oe") or it["m"], safe=""),
       total_txt, total_txt, app_html,
       rel_html, esc(cfg["company_en"]), esc(it.get("b") or "WEILI"),
       esc(cfg["company_en"]), esc(it.get("b") or "WEILI"),
       sitefoot(cfg))

    og_img = it.get("p") or ("assets/og/%s.jpg" % cat_slug(cat))
    return head_block(cfg, title, desc, canonical, og_img, "product", [ld, crumbs]) + "\n" + body


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

    body = """<body>
%s
<main class="cat-main">
<nav class="crumbs"><a href="../index.html" data-i18n="home">Home</a> &rsaquo; <span data-cat="%s">%s</span></nav>
<div class="cat-head">
  <h1><span data-cat="%s">%s</span> <span class="h1sub zh-extra">%s</span></h1>
  <p data-i18n="cat_lead">Every %s we stock, with OE number and cross-reference. Click a part number to see fitment, photos and a WhatsApp quote button.</p>
  <div class="stat"><span data-i18n="models_n" data-v-n="%d">%d models</span> · <a href="../index.html" data-i18n="search_oe">search by OE number</a> · <a href="../index.html?cat=%s" data-i18n="filter_search">filter on the search page</a></div>
</div>
<div class="modlist"><h2>%s</h2><ul class="modgrid">%s</ul>%s</div>
</main>
%s
</body></html>
""" % (sitehead(cfg, cat), cat, esc(en), cat, esc(en), esc(cn), esc(one),
       len(all_items), len(all_items), cat, modh, lis, pager, sitefoot(cfg))
    return head_block(cfg, title, desc, canonical, "assets/og/%s.jpg" % slug, "website") + "\n" + body


def page_cat_index(cfg, cats, by_cat):
    total = sum(len(by_cat.get(c["key"], [])) for c in cats)
    title = "All %d product categories — %d part numbers | Guangzhou Yumengyang Auto Parts" % (len(cats), total)
    desc = ("Ignition coils, ABS sensors, oxygen sensors, fuel pumps, TPMS, throttle bodies and more — "
            "%d part numbers with OE cross-reference." % total)
    cards = []
    for c in order_cats(cats):
        key = c["key"]
        slug, en, one, cn = CAT_META.get(key, (key, key, key, key))
        n = len(by_cat.get(key, []))
        cards.append('<a class="catcard" href="%s.html"><b data-cat="%s">%s</b><span class="zh-extra">%s</span>'
                     '<em data-i18n="cat_arrow" data-v-n="%d">%d models →</em></a>'
                     % (slug, key, esc(en), esc(cn), n, n))
    body = """<body>
%s
<main class="cat-main">
<nav class="crumbs"><a href="../index.html" data-i18n="home">Home</a> &rsaquo; <span data-i18n="all_cat_h1">All categories</span></nav>
<div class="cat-head">
  <h1><span data-i18n="all_cat_h1">All product categories</span> <span class="h1sub zh-extra">全部品类</span></h1>
  <p data-i18n="all_cat_lead" data-v-c="%d" data-v-n="%d">%d categories, %d part numbers. Pick a category to see every model with its OE number, cross-reference and fitment.</p>
  <div class="stat"><a href="../index.html" data-i18n="search_oe">Search by OE number</a></div>
</div>
<div class="catcards">%s</div>
</main>
%s
</body></html>
""" % (sitehead(cfg), len(cats), total, len(cats), total, "".join(cards), sitefoot(cfg))
    return head_block(cfg, title, desc, rel_url(cfg, "category/index.html"), "", "website") + "\n" + body


def page_404(cfg):
    home = rel_url(cfg, "") if has_site(cfg) else "index.html"
    js = rel_url(cfg, "assets/i18n.js") if has_site(cfg) else "assets/i18n.js"
    sel = lang_sel_html().replace('class="langsel"', 'class="langsel dark"')
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Page not found | Guangzhou Yumengyang Auto Parts</title>
<meta name="robots" content="noindex,follow">
{LANG_BOOT}
<script defer src="{js}"></script>
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
  <p data-i18n="nf_p">The part may have moved. Search by OE number on the home page, or message us on WhatsApp.</p>
  <a class="btn" href="{home}" data-i18n="nf_back">Back to the lookup home</a>
  <a class="wa" href="{wa}" target="_blank" rel="noopener">WhatsApp</a>
  <small><span class="notranslate" translate="no">{cn}</span> · <span class="notranslate" translate="no">{en}</span></small>
</div>
</body>
</html>
""".format(LANG_BOOT=LANG_BOOT, js=esc(js), sel=sel, home=esc(home),
           wa=esc(wa_link(cfg, "Hi, I could not find a part on your website.")),
           cn=esc(BRAND_CN), en=esc(cfg["company_en"]))


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


def home_links(cfg, cats, by_cat, limit=100):
    rows = []
    total = 0
    for c in order_cats(cats):
        key = c["key"]
        items = by_cat.get(key, [])
        total += len(items)
        slug, en, one, cn = CAT_META.get(key, (key, key, key, key))
        links = "".join('<a href="c/%s.html" title="%s">%s</a>' % (
            esc(it["s"]), esc(it.get("a", "")[:60]), esc(it.get("oe") or it["m"]))
            for it in items[:limit])
        rows.append(
            '<div class="catrow"><div class="cath"><b data-cat="%s">%s</b>'
            '<span class="zh-extra">%s · </span>'
            '<span data-i18n="models_n" data-v-n="%d">%d models</span>'
            '<a class="all" href="category/%s.html"><span data-i18n="view_all">View all</span>'
            '<span class="zh-extra"> 查看全部</span> →</a></div>'
            '<div class="lst">%s</div></div>'
            % (key, esc(en), esc(cn), len(items), len(items), slug, links))
    return ('<h2><span data-i18n="cat_h2">Browse all models by category</span>'
            '<span class="zh-extra"> 按品类浏览全部型号</span></h2>'
            '<p class="lead" data-i18n="cat_home_lead">Each category lists its first 100 models — click View all '
            'for the whole list. The block collapses and scrolls on its own.</p>'
            '<details class="catbox"><summary><span data-i18n="catbox_open" data-v-c="%d" data-v-n="%d">'
            'Expand / collapse: %d categories · %d models</span></summary>%s</details>'
            % (len(cats), total, len(cats), total, "".join(rows)))


def inject_home(cfg, cats, by_cat):
    path = os.path.join(HERE, "index.html")
    if not os.path.exists(path):
        return
    h = open(path, encoding="utf-8").read()
    block = home_links(cfg, cats, by_cat)
    h2, n = re.subn(r"(<!-- HOME_LINKS_START -->)(.*?)(<!-- HOME_LINKS_END -->)",
                    lambda m: m.group(1) + "\n" + block + "\n" + m.group(3),
                    h, count=1, flags=re.S)
    if not n:
        return
    cards = top_cards(cfg, cats, by_cat)
    h2 = re.sub(r"(<!-- TOP_CARDS_START -->)(.*?)(<!-- TOP_CARDS_END -->)",
                lambda m: m.group(1) + "\n" + cards + "\n" + m.group(3),
                h2, count=1, flags=re.S)
    h2 = h2.replace("https://your-domain.com", cfg["site_url"])
    h2 = h2.replace("8615915859048", cfg["whatsapp"])
    if not has_site(cfg):
        # 没有真实域名：去掉会指错地方的 canonical / og:url / og:image
        h2 = re.sub(r'\n<link rel="canonical"[^>]*>', "", h2)
        h2 = re.sub(r'\n<meta property="og:url"[^>]*>', "", h2)
        h2 = re.sub(r'\n<meta property="og:image"[^>]*>', "", h2)
        h2 = re.sub(r'\n?<script type="application/ld\+json">\{"@context":"https://schema\.org","@type":"WebSite".*?</script>', "", h2, flags=re.S)
    open(path, "w", encoding="utf-8", newline="\n").write(h2)


# ------------------------------------------------------------------ 主入口
def build_static(items, cats, log=print):
    cfg = load_cfg()
    cfg["_total"] = len(items)
    t0 = time.time()
    clash = make_slugs(items)

    by_cat = {}
    for it in items:
        by_cat.setdefault(it["cat"], []).append(it)

    # 导航条上放“热销 4 类 + 型号最多的 1 类”，顺序按 order_cats
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
    for idx, it in enumerate(items):
        cat = it["cat"]
        siblings = by_cat.get(cat, [])
        pos = None
        for k, s in enumerate(siblings):
            if s["i"] == it["i"]:
                pos = k
                break
        rel = []
        if pos is not None:
            for d in (1, 2, 3, -1, -2, -3):
                j = pos + d
                if 0 <= j < len(siblings):
                    rel.append(siblings[j])
        htmltext = page_model(cfg, it, cat, rel)
        with open(os.path.join(cdir, it["s"] + ".html"), "w", encoding="utf-8", newline="\n") as f:
            f.write(htmltext)
        counts[cat] = counts.get(cat, 0) + 1

    make_og_images(cfg, cats)

    cat_files = []
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

    with open(os.path.join(catdir, "index.html"), "w", encoding="utf-8", newline="\n") as f:
        f.write(page_cat_index(cfg, cats, by_cat))

    # sitemap
    today = time.strftime("%Y-%m-%d")
    urls = ['<url><loc>%s</loc><lastmod>%s</lastmod><changefreq>weekly</changefreq><priority>0.9</priority></url>'
            % (esc(cfg["site_url"] + "/"), today)]
    urls.append('<url><loc>%s</loc><lastmod>%s</lastmod><changefreq>weekly</changefreq><priority>0.8</priority></url>'
                % (esc(rel_url(cfg, "category/index.html")), today))
    for fname in cat_files:
        urls.append('<url><loc>%s</loc><lastmod>%s</lastmod><changefreq>weekly</changefreq><priority>0.7</priority></url>'
                    % (esc(rel_url(cfg, "category/" + fname)), today))
    for it in items:
        urls.append('<url><loc>%s</loc><lastmod>%s</lastmod><changefreq>monthly</changefreq><priority>0.6</priority></url>'
                    % (esc(rel_url(cfg, "c/%s.html" % it["s"])), today))
    sm = ('<?xml version="1.0" encoding="UTF-8"?>\n'
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
          + "\n".join(urls) + "\n</urlset>\n")
    open(os.path.join(HERE, "sitemap.xml"), "w", encoding="utf-8", newline="\n").write(sm)

    robots = ("User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n" % cfg["site_url"])
    open(os.path.join(HERE, "robots.txt"), "w", encoding="utf-8", newline="\n").write(robots)

    open(os.path.join(HERE, "404.html"), "w", encoding="utf-8", newline="\n").write(page_404(cfg))

    inject_home(cfg, cats, by_cat)

    log("  型号页 %d 个（slug 冲突加后缀 %d 个）" % (len(items), len(clash)))
    log("  品类页 %d 个（%d 条/页）· sitemap %d 条 URL" % (len(cat_files), PER_PAGE, len(urls)))
    log("  域名：%s　WhatsApp：%s" % (cfg["site_url"], cfg["whatsapp"]))
    log("  分享图：assets/og/ 共 %d 张" % len(cats))
    log("  静态页用时：%.1f 秒" % (time.time() - t0))
    return {"pages": len(items), "clash": clash, "urls": len(urls), "cfg": cfg, "cat_files": len(cat_files)}
