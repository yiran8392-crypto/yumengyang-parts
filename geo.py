# -*- coding: utf-8 -*-
"""
GEO（生成式引擎优化）· 给 AI 搜索看的三个入口
==============================================
传统 SEO 拼的是「人在搜索结果里点进来」；GEO 拼的是「ChatGPT / Perplexity /
Claude / Google AI 概览 / Copilot 直接把咱们这一页当答案引用」。
AI 爬虫要的东西其实很朴素，这里就负责把三件事写出来：

  1. robots.txt
     现在写的是 `User-agent: * / Allow: /`，大部分 AI 爬虫照做；
     但有些平台先找自己那一段，找不到才落到 *。这里逐个写明白 + 写清楚
     该去读哪个文件，省得哪天在别处被默认拦掉还不知道。

  2. llms.txt（根目录，约定见 https://llmstxt.org）
     一份「站点说明书」：公司是谁、多少型号、25 个品类分别多少个、
     哪些指南/故障码页值得读、怎么下单。AI 想深一点又不想翻 11,000 个 HTML 时读它。

  3. llms-full.txt
     全量型号清单，一行一个：SKU | 品名 | OE 号 | 交叉号 | 适配车型 | 页面地址。
     买家在 ChatGPT 里问「90919-02248 有哪些替代号」，这一行就能被直接引用。

另外给了型号页的 Product JSON-LD 两个小补充（产地、质保），见 product_facts()。

不要在生成的 llms*.txt 里手改——它们跟着 rerender.py（更新数据.cmd 的第 2 步）
每次重新生成，改文案请改这个文件。
"""

import re

# ------------------------------------------------------------------ 小工具


def _n(v):
    return "{:,}".format(int(v or 0))


def _clip(s, cap):
    """压成一行、超长在空格处收尾。给 llms-full.txt 省体积用。"""
    s = re.sub(r"\s+", " ", (s or "")).strip(" ,;")
    if len(s) <= cap:
        return s
    cut = s[:cap]
    cut = cut.rsplit(" ", 1)[0] if " " in cut else cut
    return cut.rstrip(" ,;.") + " …"


def _fit_brief(apps, segs=3, cap=80):
    """适配车型压成「前 3 段」，例如 Fiat/Lancia Punto, Palio, Doblo, …
    只按逗号/分号切——车型里的斜杠（Fiat/Lancia）不能切。"""
    parts = [p.strip(" .") for p in re.split(r"[,;|]", apps or "") if p.strip(" .")]
    if not parts:
        return ""
    out = ", ".join(parts[:segs])
    if len(parts) > segs:
        out += ", …"
    return _clip(out, cap)


def _lines(*chunks):
    """拼行：允许传 list 或 str，最后统一成一个以 \n 结尾的文本。"""
    out = []
    for c in chunks:
        if isinstance(c, str):
            out.append(c)
        elif c:
            out.extend(c)
    return "\n".join(out).rstrip("\n") + "\n"


# ------------------------------------------------------------------ 1. robots.txt

# （UA, 说明）——UA 写错就等于没放行，按各家官方文档里的名字抄的，别随手改。
# 说明写英文、文件保持纯 ASCII：robots.txt 没有 charset 声明，老解析器遇到非 ASCII 容易乱。
AI_CRAWLERS = [
    ("GPTBot", "OpenAI - ChatGPT training and browsing"),
    ("OAI-SearchBot", "OpenAI - ChatGPT search index"),
    ("ChatGPT-User", "OpenAI - live fetch when a user asks"),
    ("PerplexityBot", "Perplexity - index"),
    ("Perplexity-User", "Perplexity - live fetch"),
    ("ClaudeBot", "Anthropic - Claude"),
    ("Claude-User", "Anthropic - live fetch"),
    ("Claude-SearchBot", "Anthropic - search index"),
    ("anthropic-ai", "Anthropic - legacy UA"),
    ("Google-Extended", "Google - Gemini / Vertex AI"),
    ("Applebot", "Apple - Spotlight / Siri"),
    ("Applebot-Extended", "Apple - Apple Intelligence"),
    ("Amazonbot", "Amazon - Alexa / Rufus"),
    ("DuckAssistBot", "DuckDuckGo - AI answers"),
    ("MistralAI-User", "Mistral - Le Chat"),
    ("YouBot", "You.com"),
    ("cohere-ai", "Cohere"),
    ("meta-externalagent", "Meta AI"),
    ("Bytespider", "ByteDance / Doubao"),
    ("PetalBot", "Huawei Petal search"),
    ("YandexBot", "Yandex (Russia / CIS)"),
    ("Baiduspider", "Baidu"),
]


def robots_txt(cfg):
    """全站 robots.txt：搜索爬虫 + AI 爬虫一起放行，并指明 llms.txt 在哪。
    整个文件保持纯 ASCII（没有 charset 声明，杂字符容易在老的解析器里出问题）。"""
    base = cfg["site_url"].rstrip("/")
    out = [
        "# %s/robots.txt" % base,
        "# Everything here is public: part numbers, OE cross-references, fitment.",
        "# Search engines and AI answer engines are both welcome - being quoted is the point.",
        "#",
        "# AI crawlers: start at %s/llms.txt (short, curated)." % base,
        "#              %s/llms-full.txt is the whole catalogue, one line per part." % base,
        "#",
        "",
        "User-agent: *",
        "Allow: /",
        "",
        "# ---------------------------------------------------------------------------",
        "# AI / LLM crawlers, listed one by one on purpose: a platform that only looks for",
        "# its own token would otherwise fall through to its own defaults.",
        "# ---------------------------------------------------------------------------",
    ]
    for ua, who in AI_CRAWLERS:
        out.append("")
        out.append("# %s" % who)
        out.append("User-agent: %s" % ua)
    out.append("Allow: /")
    out += [
        "",
        "# ---------------------------------------------------------------------------",
        "# Machine-readable index for LLMs (llmstxt.org)",
        "#   /llms.txt       who we are + every category, guide, fault code and index page",
        "#   /llms-full.txt  every part number with OE, cross-reference and fitment",
        "# ---------------------------------------------------------------------------",
        "",
        "",
        "Sitemap: %s/sitemap.xml" % base,
        "",
    ]
    return "\n".join(out)


# ------------------------------------------------------------------ 2. llms.txt

def llms_txt(cfg, items, cats, cat_meta, brand_entries=None, vehicle_entries=None,
             guides=None, codes=None, terms=None, moq_range=None):
    """根目录 llms.txt：两三屏读完的「站点说明书」。

    items        产品行（sitegen 的 it 结构）
    cats         [{"key","name","en","n"}]，按站点顺序
    cat_meta     sitegen.CAT_META：key -> (slug, 英文复名, 英文单数, 中文)
    brand_entries / vehicle_entries  /brand/、/vehicle/ 落地页（可空）
    guides       guides_content.GUIDES（可空）
    codes        codes_content.CODES（可空）
    terms        付款与装运.txt 读出来的 dict（可空：空就不写那几行）
    """
    base = cfg["site_url"].rstrip("/")

    def url(path=""):
        return "%s/%s" % (base, path) if path else base + "/"

    n_total = len(items)
    n_oe = sum(1 for it in items if (it.get("oe") or "").strip())
    n_img = sum(1 for it in items if it.get("p"))
    n_x = sum(1 for it in items if it.get("x"))
    live_cats = [c for c in cats if c.get("n")]
    terms = terms or {}

    t = cfg.get("company_en") or "Guangzhou Yumengyang Auto Parts Co., Ltd."
    t_cn = cfg.get("company_cn") or ""

    L = []
    L.append("# %s%s" % (t, (" (%s)" % t_cn) if t_cn else ""))
    L.append("")
    L.append(
        "> Guangzhou-based manufacturer and exporter of ignition and electronic "
        "fuel-injection parts for Asian, European and American vehicles: ignition coils, "
        "ABS wheel-speed sensors, fuel pumps, oxygen sensors, camshaft/crankshaft position "
        "sensors, throttle bodies, injectors, spark plugs, thermostats and related sensors. "
        "%s part numbers with OE number, cross-reference and vehicle fitment, in %d categories. "
        "Wholesale only — prices, MOQ and packing are confirmed on WhatsApp within one working day."
        % (_n(n_total), len(live_cats))
    )
    L.append("")
    L.append("This site is public on purpose. Quoting it, summarising it and linking to it is welcome; "
             "cite the page URL you used.")
    L.append("")

    # ---------------- 关键事实
    L.append("## Key facts")
    L.append("")
    L.append("- Legal name: %s%s" % (t, (" · %s" % t_cn) if t_cn else ""))
    L.append("- Business: manufacturer and exporter (own brands WEILI 威力, Standout 胜路, "
             "Drivefar 卓凡, Yumengyang 驭扬)")
    if cfg.get("address_en"):
        L.append("- Address: %s" % cfg["address_en"])
    contact = []
    if cfg.get("whatsapp"):
        contact.append("WhatsApp +" + cfg["whatsapp"])
    if cfg.get("email"):
        contact.append(cfg["email"])
    if cfg.get("hours"):
        contact.append(cfg["hours"])
    if contact:
        L.append("- Contact: " + " · ".join(contact))
    L.append("- Catalogue: %s part numbers · %d categories · %s with an OE number · "
             "%s with our own photos · %s with cross-references"
             % (_n(n_total), len(live_cats), _n(n_oe), _n(n_img), _n(n_x)))
    if moq_range and moq_range[0]:
        lo, hi = moq_range
        if lo == hi:
            L.append("- MOQ: %d pcs for most part types (each part page states its own MOQ)" % lo)
        else:
            L.append("- MOQ: %d–%d pcs depending on the part type (each part page states its own MOQ)"
                     % (lo, hi))
    L.append("- Warranty: 12–24 months depending on the part type, written on the quotation and invoice")
    if terms.get("t_t"):
        L.append("- Payment: %s" % terms["t_t"])
    if terms.get("l_c"):
        L.append("- Letter of credit: %s" % terms["l_c"])
    if terms.get("terms"):
        L.append("- Incoterms: %s" % terms["terms"])
    if terms.get("lead_time"):
        L.append("- Lead time: %s" % terms["lead_time"])
    L.append("- Markets served: Middle East, Africa, Latin America, Russia / CIS, Southeast Asia")
    L.append("- Site languages: English, 简体中文, العربية, Русский, Français, Español, "
             "Português, Bahasa Indonesia, فارسی (same URL, language switch by JS)")
    L.append("")

    # ---------------- 品类
    L.append("## Product categories")
    L.append("")
    L.append("Every category page lists all the part numbers we stock in that group; "
             "every part page carries its OE number, cross-reference list and vehicle fitment.")
    L.append("")
    for c in sorted(live_cats, key=lambda x: (-(x.get("n") or 0), x.get("key") or "")):
        key = c["key"]
        meta = cat_meta.get(key) or (key, c.get("en") or key, c.get("en") or key, c.get("name") or key)
        slug, en, one, cn = meta
        L.append("- [%s](%s): %s part numbers." % (en, url("category/%s.html" % slug), _n(c["n"])))
    L.append("")
    L.append("Index pages: [all products](%s) · [all %d categories](%s) · "
             "[bulk OE lookup](%s) · [fault codes](%s)"
             % (url("products.html"), len(live_cats), url("category/index.html"),
                url("list.html"), url("codes/index.html")))
    L.append("")

    # ---------------- 指南
    if guides:
        L.append("## Buying guides (long-form, free to quote)")
        L.append("")
        for g in guides:
            L.append("- [%s](%s): %s" % (g["title"], url("guides/%s.html" % g["slug"]),
                                         _clip(g.get("desc") or "", 200)))
        L.append("")

    # ---------------- 故障码
    if codes:
        L.append("## Fault-code diagnostics")
        L.append("")
        L.append("Symptom-first pages: what the code means, how to test before replacing, "
                 "and which part numbers on this site it points to.")
        L.append("")
        L.append("- [All fault codes](%s)" % url("codes/index.html"))
        for c in codes[:60]:
            L.append("- [%s](%s): %s" % (c["code"], url("codes/%s.html" % c["code"].lower()),
                                         _clip(c.get("name") or "", 90)))
        L.append("")

    # ---------------- 品牌 / 车型
    if brand_entries:
        top = brand_entries[:20]
        L.append("## Vehicle brands covered")
        L.append("")
        L.append("- [All brands](%s)" % url("brand/index.html"))
        for e in top:
            L.append("- [%s](%s): %s part numbers" % (e["canon"], url("brand/%s.html" % e["slug"]),
                                                      _n(e.get("n") or 0)))
        L.append("")
    if vehicle_entries:
        top = vehicle_entries[:20]
        L.append("## Most covered models")
        L.append("")
        L.append("- [All models](%s)" % url("vehicle/index.html"))
        for e in top:
            L.append("- [%s](%s): %s part numbers" % (e["token"], url("vehicle/%s.html" % e["slug"]),
                                                      _n(e.get("n") or 0)))
        L.append("")

    # ---------------- 公司页
    L.append("## Company and terms")
    L.append("")
    L.append("- [About us](%s): what we make, how we check it, what we do not do" % url("about.html"))
    L.append("- [Contact and how to order](%s): WhatsApp, email, address, payment and shipping terms"
             % url("contact.html"))
    L.append("- [Returns and warranty](%s) · [Privacy](%s)"
             % (url("returns.html"), url("privacy.html")))
    L.append("")

    # ---------------- OpenAPI/可选
    L.append("## Optional")
    L.append("")
    L.append("- [llms-full.txt](%s): the whole catalogue as plain text, one line per part number "
             "(SKU | part type | OE number | cross-references | fitment | page URL). "
             "Use this instead of crawling %s pages." % (url("llms-full.txt"), _n(n_total)))
    L.append("- [sitemap.xml](%s)" % url("sitemap.xml"))
    L.append("")
    return _lines(L)


# ------------------------------------------------------------------ 3. llms-full.txt

def llms_full_txt(cfg, items, cats, cat_meta):
    """全量型号清单。一行一个型号，按品类分组，纯文本好解析也好 grep。"""
    base = cfg["site_url"].rstrip("/")
    n_total = len(items)
    L = []
    L.append("# %s — complete catalogue" % (cfg.get("company_en") or "Guangzhou Yumengyang"))
    L.append("#")
    L.append("# %s part numbers. One line per part:" % _n(n_total))
    L.append("#   SKU | part type | OE number | cross-references | vehicle fitment | page URL")
    L.append("# Cross-references are capped at 5, fitment at 3 groups; the page has the full lists.")
    L.append("# Everything listed here is for wholesale — quotation on WhatsApp, not a webshop.")
    L.append("")

    by_cat = {}
    for it in items:
        by_cat.setdefault(it.get("cat"), []).append(it)

    for c in cats:
        key = c["key"]
        lst = by_cat.get(key) or []
        if not lst:
            continue
        meta = cat_meta.get(key) or (key, c.get("en") or key, c.get("en") or key, c.get("name") or key)
        slug, en, one, cn = meta
        L.append("## %s — %s parts" % (en, _n(len(lst))))
        L.append("# %s/category/%s.html" % (base, slug))
        for it in sorted(lst, key=lambda x: (x.get("oe") or "zzzz", x.get("m") or "")):
            sku = it.get("m") or ""
            oe = it.get("oe") or "-"
            x = ", ".join((it.get("x") or [])[:5]) or "-"
            fits = _fit_brief(it.get("a") or "") or "-"
            L.append("- %s | %s | OE %s | %s | %s | %s/c/%s.html"
                     % (sku, one, oe, x, fits, base, it.get("s") or ""))
        L.append("")
    return _lines(L)


# ------------------------------------------------------------------ 4. 型号页 JSON-LD 补两条

def product_facts():
    """Product JSON-LD 里补两个买家/AI 一定会问、我们又答得出来的字段。"""
    return {
        "countryOfOrigin": {"@type": "Country", "name": "China"},
    }


def warranty_prop():
    return {"@type": "PropertyValue", "name": "Warranty", "value": "12–24 months depending on part type"}
