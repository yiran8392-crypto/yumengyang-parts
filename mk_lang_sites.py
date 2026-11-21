# -*- coding: utf-8 -*-
"""型号查询站 · 多语种静态化
======================================================================
把「浏览器里用 i18n.js 现翻」变成「生成时就翻好、有独立 URL 的真静态页」。

为什么必须这么做（2026-11-21 诊断结论）：
    线上实测 <html lang="en">、hreflang 只有 x-default、源码里没有任何阿/俄/西内容。
    也就是说 9 语种只存在于浏览器执行 JS 之后 —— 而 Google 抓到的是英文。
    沙特客户搜「ملف إشعال」、俄罗斯客户搜「катушка зажигания」永远搜不到我们。

做什么：
    ar/ ru/ es/ pt/  四个语种目录，镜像「需要被当地语言搜到」的那批页面：
      首页 / products / about / contact / list + category(34) + brand(86)
      + vehicle(258) + codes(48) + guides(11)  ≈ 440 页/语种
    ★ 刻意不做 11,143 个型号页：买家搜的是 OE 号，号码语言无关；
      做了只有代价（4 × 10,300 页 ≈ 800 MB，站点已经 2 GB 了）。

规则来源：完全照 assets/i18n.js 的 apply() / pd()，数据来自 _tmp/i18n_cache.json
（i18n_extract.py 从 i18n.js 提取，已和 Node 版逐字段交叉验证一致）。

用法：
    python mk_lang_sites.py --only category/ignition-coils.html --lang ar   # PoC 单页
    python mk_lang_sites.py --lang ar                                       # 一个语种全量
    python mk_lang_sites.py                                                 # 四个语种全量
    python mk_lang_sites.py --dry                                           # 只算不写
"""

import argparse
import io
import json
import os
import posixpath
import re
import sys
import time

from lxml import etree
from lxml import html as LH

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "_tmp", "i18n_cache.json")

# 要生成的语种（顺序无所谓，输出独立目录）
LANGS = ("ar", "ru", "es", "pt")

# 与 i18n.js 的 IDX 一致（en 是原文，不占列）
IDX = {"zh": 0, "ar": 1, "ru": 2, "fr": 3, "es": 4, "pt": 5, "id": 6, "fa": 7}
RTL = ("ar", "fa")

# 需要镜像的页面：根页面 + 这些目录下的全部 html
ROOT_PAGES = ("index.html", "products.html", "about.html", "contact.html", "list.html")
# ⚠️ codes（48 篇故障码）和 guides（10 篇采购指南）也故意不放进来：
#    它们的正文只在 codes_content.py / guides_content.py 里有英文，
#    i18n.js 的 T 表里没有译文（cd_* 2,500 多个、gd_* 687 个 key）。
#    硬做出来是「阿语界面 + 大段英文正文」的语言混杂页，Google 可能判低质。
#    ★ 以后把正文翻译好，再把 "codes" / "guides" 加回这个元组即可，脚本不用改。
MIRROR_DIRS = ("category", "brand", "vehicle")

DEFAULT_DOMAIN = "https://yumengyangparts.com"


# ------------------------------------------------------------------ 配置
def read_cfg():
    cfg = {}
    p = os.path.join(HERE, "站点设置.txt")
    if not os.path.exists(p):
        return cfg
    for enc in ("utf-8-sig", "utf-8", "gbk"):
        try:
            txt = io.open(p, "r", encoding=enc).read()
            break
        except UnicodeDecodeError:
            continue
    for line in txt.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        cfg[k.strip()] = v.strip()
    return cfg


def load_cache():
    if not os.path.exists(CACHE):
        raise SystemExit(
            "找不到 %s\n先跑：python i18n_extract.py" % CACHE)
    with io.open(CACHE, "r", encoding="utf-8") as f:
        return json.load(f)


# ------------------------------------------------------------------ 产品数据替换（照搬 pd()）
def pd_ant(key):
    head = r"\b" if re.match(r"^[A-Za-z0-9]", key) else ""
    tail = r"\b" if re.search(r"[A-Za-z0-9]$", key) else ""
    return "(?:%s%s%s)" % (head, re.escape(key), tail)


class Pd:
    """某个语种的产品数据逐词替换器（等价于 i18n.js 的 pdBuild + pd()）"""

    def __init__(self, pd_rows, lang):
        self.lang = lang
        o = IDX[lang] + 1
        m = {}
        src = []
        for row in pd_rows:
            if o >= len(row):
                continue
            v = row[o]
            if not v:
                continue
            m[row[0].upper()] = v
            src.append(row[0])
        src.sort(key=len, reverse=True)          # 长的先匹配
        self.map = m
        self.rx = re.compile("|".join(pd_ant(k) for k in src), re.I) if src else None

    def __call__(self, text, kind=""):
        t = "" if text is None else str(text)
        if not t or self.lang == "en":
            return t
        if self.rx is not None:
            t = self.rx.sub(lambda mo: self.map.get(mo.group(0).upper(), mo.group(0)), t)
        t = pd_sep(t)
        if kind == "years":
            t = re.sub(r"(\d{4})\s*[-\u2013\u2014]\s*(\d{4})", r"\1/\2", t)
        return t


def pd_sep(s):
    """逗号改斜杠（千分位先保护）—— 与 i18n.js 的 pdSep 一致"""
    s = re.sub(r"(\d),(\d{3})(?!\d)", "\\1\u0001\\2", s)
    s = re.sub(r"\s*[,\uff0c]\s*", " / ", s)
    return s.replace("\u0001", ",")


# ------------------------------------------------------------------ 界面文案
def fill(s, vars_):
    return re.sub(r"\{(\w+)\}",
                  lambda m: str(vars_.get(m.group(1), m.group(0))) if m.group(1) in vars_ else m.group(0),
                  s)


def dom_vars(el, cat_table, idx, pdx=None):
    """data-v-xxx 属性 -> 占位符；data-v-cat 换成当前语种品类名。

    ★ data-v-b 这类参数值是「品牌 / 车型名」（品牌页 h1 就是 "{b} parts"），
      光塞英文原文进去，阿语页会写成「قطع Toyota」。所以每个变量值都要再过一遍
      PD 表（pdx）—— 型号代码 / 纯数字不在 PD 表里，过一遍也不会有副作用。
    """
    v = {}
    for name, val in el.attrib.items():
        if name.startswith("data-v-"):
            v[name[len("data-v-"):]] = pdx(val) if pdx is not None else val
    if "data-v-cat" in el.attrib:
        key = el.get("data-v-cat")
        arr = cat_table.get(key) or []
        if idx < len(arr) and arr[idx]:
            v["cat"] = arr[idx]
        else:
            v["cat"] = el.get("data-v-cat-en") or ""
    return v


def _set_text(el, text):
    """等价于 JS 的 textContent = text（清掉子元素）"""
    for ch in list(el):
        el.remove(ch)
    el.text = text


# ------------------------------------------------------------------ 链接改写
def norm_rel(cur_rel, href):
    """把当前页里的 href 解析成「相对站点根」的路径；解析不了返回 None"""
    if not href:
        return None
    h = href.strip()
    if h.startswith(("#", "mailto:", "tel:", "javascript:", "data:")):
        return None
    if h.startswith(("http://", "https://", "//")):
        return None
    # 去掉 query / fragment，记住它们
    frag = ""
    for sep in ("#", "?"):
        if sep in h:
            h, tail = h.split(sep, 1)
            frag = sep + tail + frag
    if not h:
        return None
    base = posixpath.dirname(cur_rel)
    path = posixpath.normpath(posixpath.join(base, h))
    if path.startswith(".."):
        return None
    return path + frag


# ------------------------------------------------------------------ 主转换
def translate_doc(tree, rel, lang, i18n, mirror_set, domain, stats):
    """把一棵英文 DOM 就地翻成 lang。rel = 相对站点根的路径"""
    root = tree.getroot()
    T = i18n["T"].get(lang, {})
    C = i18n["C"]
    idx = IDX[lang]
    pdx = Pd(i18n["PD"], lang)

    # --- 1. <html> 属性
    root.set("lang", "zh-CN" if lang == "zh" else lang)
    root.set("dir", "rtl" if lang in RTL else "ltr")
    root.set("data-lang", lang)
    root.set("translate", "no")          # 别让浏览器再机翻一遍

    # --- 2. data-i18n（文案）
    for el in tree.xpath("//*[@data-i18n]"):
        key = el.get("data-i18n")
        s = T.get(key)
        if s is None:
            stats["i18n_miss"] += 1
            continue
        src = el.get("data-i18n-src")
        if src is None:
            src = el.text or ""
            el.set("data-i18n-src", src)      # 留英文原文，切回英文能还原
        _set_text(el, fill(s, dom_vars(el, C, idx, pdx)))
        stats["i18n"] += 1

    # --- 3. data-i18n-ph（输入框 placeholder）
    for el in tree.xpath("//*[@data-i18n-ph]"):
        key = el.get("data-i18n-ph")
        s = T.get(key)
        if s is None:
            continue
        if el.get("data-i18n-ph-src") is None:
            el.set("data-i18n-ph-src", el.get("placeholder") or "")
        el.set("placeholder", fill(s, dom_vars(el, C, idx, pdx)))
        stats["ph"] += 1

    # --- 4. data-i18n-html（带行内标签的段落）
    for el in tree.xpath("//*[@data-i18n-html]"):
        key = el.get("data-i18n-html")
        s = T.get(key)
        if s is None:
            continue
        if el.get("data-i18n-html-src") is None:
            el.set("data-i18n-html-src", el.text or "")
        inner = LH.fragment_fromstring(s, create_parent="span")
        for ch in list(el):
            el.remove(ch)
        _set_text(el, inner.text)
        for ch in inner:
            el.append(ch)
        stats["html"] += 1

    # --- 5. data-cat（品类名）
    for el in tree.xpath("//*[@data-cat]"):
        key = el.get("data-cat")
        arr = C.get(key) or []
        src = el.get("data-cat-src")
        if src is None:
            src = el.text or ""
            el.set("data-cat-src", src)
        if idx < len(arr) and arr[idx]:
            _set_text(el, arr[idx])
            stats["cat"] += 1

    # --- 6. data-pd（品牌 / 车型 / 备注，逐词替换）
    for el in tree.xpath("//*[@data-pd]"):
        kind = el.get("data-pd")
        src = el.get("data-pd-src")
        if src is None:
            src = el.text or ""
            el.set("data-pd-src", src)
        _set_text(el, pdx(src, kind if kind != "text" else ""))
        stats["pd"] += 1

    # --- 7. 站内链接：镜像过的走本语种目录，没镜像的回英文页
    for a in tree.xpath("//a[@href]"):
        target = norm_rel(rel, a.get("href"))
        if target is None:
            continue
        bare = target.split("#")[0].split("?")[0]
        suffix = target[len(bare):]
        if bare in mirror_set:
            a.set("href", "/%s/%s%s" % (lang, bare, suffix))
        else:
            a.set("href", "/%s%s" % (bare, suffix))
        stats["link"] += 1

    # --- 7b. 静态资源（css / js / 图片）统一改成站点绝对路径。
    #     ⚠️ 这一条是必须的：它们在 ar/ 下**没有副本**，相对路径 ../assets/style.css
    #     在 /ar/category/x.html 里会解析成 /ar/assets/style.css → 404，整页样式全丢。
    def _abs(url):
        if not url or url.startswith(("http://", "https://", "//", "data:", "#")):
            return url
        if url.startswith("/"):
            return url
        t = norm_rel(rel, url)
        return url if t is None else "/" + t

    for el in tree.xpath("//script[@src] | //img[@src] | //source[@src] | //video[@src] | //audio[@src]"):
        el.set("src", _abs(el.get("src")))
        stats["asset"] += 1
    for el in tree.xpath("//link[@href]"):
        rtype = (el.get("rel") or "").lower()
        if rtype in ("canonical", "alternate"):
            continue                       # 这两个已经是绝对 URL
        el.set("href", _abs(el.get("href")))
        stats["asset"] += 1
    for el in tree.xpath("//img[@srcset] | //source[@srcset]"):
        parts = []
        for item in (el.get("srcset") or "").split(","):
            item = item.strip()
            if not item:
                continue
            bits = item.split()
            bits[0] = _abs(bits[0])
            parts.append(" ".join(bits))
        el.set("srcset", ", ".join(parts))

    # --- 8. canonical 指向本语种自己
    for l in tree.xpath('//link[@rel="canonical"]'):
        l.set("href", "%s/%s/%s" % (domain, lang, rel))
        stats["canonical"] += 1

    # --- 9. hreflang 互指（en + 4 语种 + x-default）
    head = tree.xpath("//head")
    if head:
        head = head[0]
        for l in tree.xpath("//link[@hreflang]"):
            l.getparent().remove(l)
        for code in ("en",) + LANGS:
            le = etree.SubElement(head, "link")
            le.set("rel", "alternate")
            le.set("hreflang", code)
            if code == "en":
                le.set("href", "%s/%s" % (domain, rel))
            else:
                le.set("href", "%s/%s/%s" % (domain, code, rel))
        le = etree.SubElement(head, "link")
        le.set("rel", "alternate")
        le.set("hreflang", "x-default")
        le.set("href", "%s/%s" % (domain, rel))
        stats["hreflang"] += 1

        # --- 10. 语言锁定：i18n.js 会读 localStorage 的 ymy_lang 再 apply 一次。
        #     如果用户上次选过 ar、现在打开 /ru/ 页，它会把俄语页当场翻成阿语（URL 说俄语、内容是阿语）。
        #     所以进到静态语种页先把这个键写成当前语种 —— 它 apply 的也是同一语种，无害。
        #     必须放在 <head> 最前，抢在 i18n.js 之前执行。
        lock = etree.Element("script")
        lock.text = ("try{localStorage.setItem('ymy_lang','%s')}catch(e){};"
                     "document.documentElement.setAttribute('data-lang','%s');" % (lang, lang))
        head.insert(0, lock)

        # --- 11. 语言切换改成「跳 URL」而不是「就地 JS 翻译」。
        #     用 capture 阶段抢在 i18n.js 的 change 监听之前，再 stopImmediatePropagation 掐掉它。
        sw = etree.SubElement(head, "script")
        sw.text = (
            "(function(){document.addEventListener('change',function(e){"
            "var el=e.target;if(!el||!el.classList||!el.classList.contains('langsel'))return;"
            "e.stopImmediatePropagation();var v=el.value||'en';var p=location.pathname;"
            "var m=p.match(/^\\/(ar|ru|es|pt)(\\/.*)$/);var base=m?m[2]:p;"
            "location.href=(v==='en')?base:('/'+v+base);},true);})();"
        )

    return tree


def render(tree):
    return LH.tostring(tree, encoding="unicode", method="html", doctype="<!DOCTYPE html>")


# ------------------------------------------------------------------ sitemap
def update_sitemap(domain):
    """把 ar/ru/es/pt 下实际存在的页面追加进 sitemap.xml。

    幂等：先剔掉上一次追加的多语条目再重加，跑几遍都不会重复。
    sitegen.py 里也加了同样一段（重建时自动带），这里是为了**不重建**就能立刻生效。
    """
    import datetime

    p = os.path.join(HERE, "sitemap.xml")
    if not os.path.exists(p):
        return 0, 0
    with io.open(p, "r", encoding="utf-8") as f:
        sm = f.read()

    pat = re.compile(r'[ \t]*<url><loc>%s/(?:%s)/[^<]*</loc>[^\n]*\r?\n?'
                     % (re.escape(domain), "|".join(LANGS)))
    sm2, removed = pat.subn("", sm)

    today = datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()
    add = []
    for lc in LANGS:
        d = os.path.join(HERE, lc)
        if not os.path.isdir(d):
            continue
        found = []
        for root, _dirs, files in os.walk(d):
            for name in files:
                if name.lower().endswith(".html"):
                    found.append(os.path.join(root, name))
        for full in sorted(found):
            relp = os.path.relpath(full, HERE).replace("\\", "/")
            add.append('<url><loc>%s/%s</loc><lastmod>%s</lastmod>'
                       '<changefreq>monthly</changefreq><priority>0.5</priority></url>'
                       % (domain, relp, today))

    if "</urlset>" not in sm2:
        return 0, removed
    sm2 = sm2.replace("</urlset>", "\n".join(add) + "\n</urlset>")
    with io.open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(sm2)
    return len(add), removed


# ------------------------------------------------------------------ 英文原页补 hreflang
def inject_en_hreflang(rel, domain):
    """给英文原页补 hreflang 互指。

    为什么必须做：hreflang 是**双向**协议 —— 阿语页指向英文页，英文页也必须指回阿语页，
    否则 Google 只认单边、等于没写，还可能把几个语言版本判成重复内容。

    做法：正则做最小侵入（只替换 <link hreflang> 那几行），**不重新序列化整页**，
    git diff 才干净、也不会动到别的东西。
    """
    path = os.path.join(HERE, rel)
    if not os.path.exists(path):
        return False
    with io.open(path, "r", encoding="utf-8") as f:
        h = f.read()
    # 先摘掉旧的 hreflang link（原来是 1 条 x-default）
    h2 = re.sub(r'[ \t]*<link[^>]+hreflang="[^"]*"[^>]*>[ \t]*\r?\n?', "", h)
    lines = []
    for code in ("en",) + LANGS:
        url = ("%s/%s" % (domain, rel)) if code == "en" else ("%s/%s/%s" % (domain, code, rel))
        lines.append('<link rel="alternate" hreflang="%s" href="%s">' % (code, url))
    lines.append('<link rel="alternate" hreflang="x-default" href="%s/%s">' % (domain, rel))
    if "</head>" not in h2:
        return False
    h2 = h2.replace("</head>", "\n" + "\n".join(lines) + "\n</head>", 1)
    if h2 == h:
        return False
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(h2)
    return True


# ------------------------------------------------------------------ 页面清单
def collect_pages(only=None):
    pages = []
    if only:
        return [only]
    for p in ROOT_PAGES:
        if os.path.exists(os.path.join(HERE, p)):
            pages.append(p)
    for d in MIRROR_DIRS:
        dd = os.path.join(HERE, d)
        if not os.path.isdir(dd):
            continue
        for name in sorted(os.listdir(dd)):
            if name.lower().endswith(".html"):
                pages.append(d + "/" + name)
    return pages


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", default="", help="只做某个语种：ar / ru / es / pt")
    ap.add_argument("--only", default="", help="只做某一页（相对站点根，PoC 用）")
    ap.add_argument("--dry", action="store_true", help="只解析不写文件")
    ap.add_argument("--out", default="", help="输出目录（默认站点根）")
    ap.add_argument("--en", action="store_true",
                    help="给英文原页补 hreflang 互指（生成完多语页之后跑这一步）")
    ap.add_argument("--sitemap", action="store_true",
                    help="把多语页面追加进 sitemap.xml（幂等，不重建站点也能用）")
    args = ap.parse_args()

    cfg = read_cfg()
    domain = (cfg.get("域名") or DEFAULT_DOMAIN).rstrip("/")
    i18n = load_cache()
    langs = (args.lang,) if args.lang else LANGS
    for l in langs:
        if l not in IDX:
            raise SystemExit("不认识的语种 %r，可选 %s" % (l, ", ".join(LANGS)))

    pages = collect_pages(args.only or None)
    mirror_set = set(collect_pages(None))

    if args.sitemap:
        add, removed = update_sitemap(domain)
        print("  sitemap：追加 %d 条多语 URL（先剔掉旧的 %d 条）" % (add, removed))
        return 0

    if args.en:
        n = 0
        for rel in pages:
            if inject_en_hreflang(rel, domain):
                n += 1
        print("  英文原页补 hreflang：%d / %d 个文件已更新" % (n, len(pages)))
        return 0

    print("=" * 66)
    print("  多语种静态化")
    print("=" * 66)
    print("  域名      : %s" % domain)
    print("  语种      : %s" % ", ".join(langs))
    print("  镜像页面  : %d 个（型号页刻意不做）" % len(pages))
    print("  预计产出  : %d 页" % (len(pages) * len(langs)))
    print()

    out_root = args.out or HERE
    t0 = time.time()
    grand = {}
    for lang in langs:
        stats = {"i18n": 0, "i18n_miss": 0, "ph": 0, "html": 0, "cat": 0,
                 "pd": 0, "link": 0, "asset": 0, "canonical": 0, "hreflang": 0, "pages": 0}
        fail = []
        for rel in pages:
            src = os.path.join(HERE, rel)
            dst = os.path.join(out_root, lang, rel)
            try:
                parser = LH.HTMLParser(encoding="utf-8", remove_comments=False)
                with io.open(src, "rb") as f:
                    tree = LH.parse(f, parser)
                translate_doc(tree, rel, lang, i18n, mirror_set, domain, stats)
                html = render(tree)
                if not args.dry:
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    with io.open(dst, "w", encoding="utf-8", newline="\n") as f:
                        f.write(html)
                stats["pages"] += 1
            except Exception as e:  # noqa: BLE001
                fail.append((rel, repr(e)[:160]))
        grand[lang] = stats
        dt = time.time() - t0
        print("  [%s] 页 %d  文案 %d  品类 %d  产品数据 %d  链接 %d  失败 %d   %.1fs" % (
            lang, stats["pages"], stats["i18n"], stats["cat"], stats["pd"],
            stats["link"], len(fail), dt))
        if stats["i18n_miss"]:
            print("       ⚠ 文案缺译（退回原文）%d 处" % stats["i18n_miss"])
        for rel, err in fail[:5]:
            print("       ✗ %s -> %s" % (rel, err))

    print()
    total = sum(s["pages"] for s in grand.values())
    print("  完成：%d 页%s" % (total, "（dry run，没写文件）" if args.dry else ""))
    return 0 if all(s["pages"] for s in grand.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
