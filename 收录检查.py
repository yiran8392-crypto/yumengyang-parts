# -*- coding: utf-8 -*-
"""
型号查询站 · 收录检查
=====================
双击「收录检查.cmd」即可，不用懂代码。跑完会在本文件夹生成一份中文报告：

    收录检查报告-YYYYMMDD-HHMM.md

它检查四件事：
  1. 本地 sitemap.xml：总条数、各类页面数量、最新更新时间
  2. 线上能不能打开：随机抽 20 个页面 + 首页 + privacy.html + returns.html
  3. 搜索引擎收录：Bing / Yandex 的 site: 查询 + 3 个型号页精确查询（尽力而为）
  4. IndexNow 的 key 文件还在不在、内容对不对（32 位十六进制 <key>.txt）

注意：第 3 项受反爬影响很大。Bing / Yandex 经常给机器人返回验证码或者
一堆跟本站毫无关系的结果。脚本会自动识别这种情况，写“未解析”，
不会因此报错退出，也不会编一个假数字给你。

用法（在“型号查询站”文件夹里）：
    python 收录检查.py                  # 正常跑一遍
    python 收录检查.py --sample 10      # 线上抽查 10 条（默认 20）
    python 收录检查.py --no-search      # 跳过搜索引擎那一步（网络不好时用）
    python 收录检查.py --timeout 30     # 单次请求超时秒数（默认 20）

域名优先读 站点设置.txt 的「域名=」，读不到才用下面的兜底值。
"""

import datetime
import gzip
import os
import random
import re
import socket
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
CFG_FILE = os.path.join(HERE, "站点设置.txt")
SITEMAP_FILE = os.path.join(HERE, "sitemap.xml")

# 兜底：配置文件读不到时才用（跟线上实际部署一致）
DEFAULT_SITE = "https://yiran8392-crypto.github.io/yumengyang-parts"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "close",
}

TIMEOUT = 20          # 单次请求超时（秒）
RETRIES = 1           # 失败重试次数（总共最多 2 次）
MAX_BYTES = 3 * 1024 * 1024
HEX32_RE = re.compile(r"^[0-9a-f]{32}$", re.I)

POLICY_NAMES = ("privacy.html", "returns.html", "terms.html", "shipping.html",
                "about.html", "contact.html", "faq.html", "policy.html")


# --------------------------------------------------------------------------
# 小工具
# --------------------------------------------------------------------------
def log(msg=""):
    print(msg, flush=True)


def banner(title):
    log("")
    log("=" * 58)
    log("  " + title)
    log("=" * 58)


def hr(title):
    log("")
    log("-- %s " % title + "-" * max(0, 52 - len(title) * 2))


def read_cfg_site():
    """只读「域名=」，配置文件里别的键一概不碰。"""
    site = DEFAULT_SITE
    if os.path.exists(CFG_FILE):
        raw = ""
        for enc in ("utf-8-sig", "gbk"):
            try:
                with open(CFG_FILE, "r", encoding=enc) as f:
                    raw = f.read()
                break
            except (UnicodeDecodeError, LookupError):
                continue
        for line in raw.splitlines():
            line = line.strip()
            if line.startswith("域名=") or line.lower().startswith("site_url="):
                v = line.split("=", 1)[1].strip().rstrip("/")
                if v.startswith("http"):
                    site = v
    return site.rstrip("/")


def load_sitemap(path):
    if not os.path.exists(path):
        return None, "找不到 sitemap.xml（先双击「重新生成页面.cmd」或跑 rerender.py）"
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        xml = f.read()
    urls = [u.strip() for u in re.findall(r"<loc>\s*(.*?)\s*</loc>", xml, re.S)]
    urls = [u for u in urls if u.startswith("http")]
    lastmods = [x.strip() for x in re.findall(r"<lastmod>\s*(.*?)\s*</lastmod>", xml, re.S)]
    return (urls, lastmods), None


def classify(url, site):
    """返回 (类别, 相对路径)。"""
    path = url[len(site):] if url.startswith(site) else urllib.parse.urlsplit(url).path
    path = path.split("#")[0].split("?")[0]
    low = path.lower()
    if low in ("", "/", "/index.html"):
        return "首页", path
    if low.startswith("/category/"):
        return "品类页", path
    if low.startswith("/c/"):
        return "型号页", path
    name = low.rsplit("/", 1)[-1]
    if name in POLICY_NAMES or "policy" in low or "privacy" in low:
        return "政策页", path
    return "其他", path


def _decode_body(raw, headers):
    enc = (headers.get("Content-Encoding") or "").lower()
    try:
        if "gzip" in enc:
            raw = gzip.decompress(raw)
        elif "deflate" in enc:
            try:
                raw = zlib.decompress(raw)
            except zlib.error:
                raw = zlib.decompress(raw, -zlib.MAX_WBITS)
    except Exception:
        pass  # 压缩头不对就别解了，后面按乱码处理也不会崩
    charset = "utf-8"
    ctype = headers.get("Content-Type") or ""
    m = re.search(r"charset=([\w\-]+)", ctype, re.I)
    if m:
        charset = m.group(1)
    else:
        m = re.search(rb"<meta[^>]+charset=[\"']?([\w\-]+)", raw[:4096], re.I)
        if m:
            charset = m.group(1).decode("ascii", "ignore")
    try:
        return raw.decode(charset, "replace")
    except (LookupError, UnicodeDecodeError):
        return raw.decode("utf-8", "replace")


def http_get(url, timeout=None, retries=None):
    """GET 一次（失败自动重试）。永远不抛异常，返回 dict。"""
    timeout = TIMEOUT if timeout is None else timeout
    retries = RETRIES if retries is None else retries
    last = {"code": 0, "body": "", "err": "", "sec": 0.0, "size": 0, "url": url}
    for attempt in range(retries + 1):
        t0 = time.time()
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read(MAX_BYTES)
                body = _decode_body(raw, resp.headers)
                return {"code": resp.status, "body": body, "err": "",
                        "sec": time.time() - t0, "size": len(raw), "url": url}
        except urllib.error.HTTPError as e:
            raw = b""
            try:
                raw = e.read(MAX_BYTES)
            except Exception:
                pass
            body = _decode_body(raw, dict(e.headers or {}))
            last = {"code": e.code, "body": body, "err": "HTTP %s %s" % (e.code, e.reason),
                    "sec": time.time() - t0, "size": len(raw), "url": url}
            if e.code not in (408, 429, 500, 502, 503, 504):
                return last          # 4xx 重试也没用
        except socket.timeout:
            last = {"code": 0, "body": "", "err": "超时（%d 秒没响应）" % timeout,
                    "sec": time.time() - t0, "size": 0, "url": url}
        except urllib.error.URLError as e:
            reason = getattr(e, "reason", e)
            last = {"code": 0, "body": "", "err": "连不上：%s" % reason,
                    "sec": time.time() - t0, "size": 0, "url": url}
        except ssl.SSLError as e:
            last = {"code": 0, "body": "", "err": "证书/加密握手失败：%s" % e,
                    "sec": time.time() - t0, "size": 0, "url": url}
        except Exception as e:                      # 兜底：任何意外都不让脚本崩
            last = {"code": 0, "body": "", "err": "%s: %s" % (type(e).__name__, e),
                    "sec": time.time() - t0, "size": 0, "url": url}
        if attempt < retries:
            time.sleep(1.5)
    return last


# --------------------------------------------------------------------------
# 1. 本地 sitemap
# --------------------------------------------------------------------------
def check_sitemap(site):
    log("[1/4] 读本地 sitemap.xml ……")
    data, err = load_sitemap(SITEMAP_FILE)
    if err:
        log("      [失败] " + err)
        return None
    urls, lastmods = data
    if not urls:
        log("      [失败] sitemap 里一个 <loc> 都没解析到。")
        return None

    counts = {}
    paths = {}
    for u in urls:
        kind, p = classify(u, site)
        counts[kind] = counts.get(kind, 0) + 1
        paths.setdefault(kind, []).append(p)

    newest = ""
    if lastmods:
        newest = max(lastmods)        # ISO 8601 字符串可以直接比大小

    order = ["首页", "品类页", "型号页", "政策页", "其他"]
    log("      sitemap 总条数：%d" % len(urls))
    for k in order:
        if k in counts:
            log("      %-4s %5d 条" % (k, counts[k]))
    log("      lastmod 最新：%s" % (newest or "（没有 lastmod）"))
    return {"total": len(urls), "counts": counts, "newest": newest, "urls": urls}


# --------------------------------------------------------------------------
# 2. 线上可达
# --------------------------------------------------------------------------
def check_online(site, urls, sample_n):
    log("[2/4] 抽查线上能否打开（%d 条随机 + 首页 + privacy + returns）……" % sample_n)
    pool = [u for u in urls if u.startswith(site)]
    pick = random.sample(pool, min(sample_n, len(pool))) if pool else []
    fixed = [site + "/", site + "/privacy.html", site + "/returns.html"]
    targets, seen = [], set()
    for u in fixed + pick:
        if u not in seen:
            seen.add(u)
            targets.append(u)

    results = []
    # 串行但很短：Github Pages 很快，不折腾线程，失败时更好读日志
    for i, u in enumerate(targets, 1):
        r = http_get(u)
        r["stamp"] = "首页" if u.rstrip("/") == site else ("固定页" if u in fixed else "随机")
        results.append(r)
        flag = "OK  " if r["code"] == 200 else "X   "
        log("      %s %3d/%d  %-4s HTTP %-4s %5.2fs %s"
            % (flag, i, len(targets), r["stamp"], r["code"] or "-", r["sec"],
               u[len(site):] or "/"))

    ok = [r for r in results if r["code"] == 200]
    fails = [r for r in results if r["code"] != 200]
    ratio = 100.0 * len(ok) / len(results) if results else 0.0
    log("      200 比例：%d/%d = %.0f%%" % (len(ok), len(results), ratio))
    for f in fails:
        log("      失败：%s → %s" % (f["url"], f["err"] or ("HTTP %s" % f["code"])))
    return {"targets": len(results), "ok": len(ok), "ratio": ratio, "fails": fails}


# --------------------------------------------------------------------------
# 3. 搜索引擎（尽力而为）
# --------------------------------------------------------------------------
CAPTCHA_HINTS = ("captcha", "not a robot", "are you a robot", "人机验证",
                 "verify you are human", "challenge-platform", "cf-challenge")


def looks_like_captcha(body):
    low = (body or "").lower()
    return any(h in low for h in CAPTCHA_HINTS)


def bing_result_blocks(body):
    return re.findall(r'<li class="b_algo".*?</li>', body, re.S)


def parse_count(body):
    """从搜索结果页里抠“约 N 条结果 / About N results”。抠不到返回 None。"""
    # Bing
    m = re.search(r'sb_count[^>]*>\s*(.{0,80}?)</span>', body, re.I | re.S)
    if m:
        n = re.search(r"([\d][\d,\.\s]*)", m.group(1))
        if n:
            return n.group(1).strip().rstrip(".,")
    # 通用英文 / 中文
    for pat in (r"[Aa]bout\s+([\d][\d,\.\s]*)\s+results?",
                r"([\d][\d,\.\s]*)\s+results?\s+(?:for|found)",
                r"约\s*([\d][\d,\.\s]*)\s*条结果"):
        m = re.search(pat, body)
        if m:
            return m.group(1).strip().rstrip(".,")
    # Yandex 俄语
    m = re.search(r"Результатов[^0-9]{0,20}([\d\s]+)", body)
    if m:
        return m.group(1).strip()
    return None


def to_int(s):
    if not s:
        return None
    digits = re.sub(r"[^\d]", "", s)
    return int(digits) if digits else None


def check_engine(label, url, host, count_expected=True):
    """跑一次 site: 查询并判断结果可不可信。永远不抛异常。"""
    log("      %s 查询中 ……" % label)
    r = http_get(url, timeout=TIMEOUT, retries=RETRIES)
    info = {"label": label, "code": r["code"], "count": None, "count_text": "",
            "hits": 0, "trusted": False, "note": "", "url": url, "body": ""}

    if r["code"] != 200:
        info["note"] = "请求失败（HTTP %s%s）" % (
            r["code"] or "无响应", ("，" + r["err"]) if r["err"] else "")
        log("         → " + info["note"])
        return info

    body = r["body"]
    info["body"] = body
    if looks_like_captcha(body):
        info["note"] = "未解析（搜索引擎要人机验证，反爬了）"
        log("         → " + info["note"])
        return info

    host_low = host.lower()
    blocks = bing_result_blocks(body) if "bing.com" in url else []
    hits = 0
    for blk in blocks:
        flat = re.sub(r"<[^>]+>", " ", blk).lower()
        if host_low in flat:
            hits += 1
    if not blocks:      # 非 bing：退回整页里找域名
        hits = body.lower().count(host_low)

    ctext = parse_count(body)
    info["count_text"] = ctext or ""
    info["count"] = to_int(ctext)
    info["hits"] = hits

    # 可信度：有结果块、且结果块里出现本域名，才算真收录数字
    if blocks:
        if hits > 0:
            info["trusted"] = True
        else:
            info["trusted"] = False
            if ctext:
                info["note"] = ("页面声称 %s，但抓到的结果里一个本域名都没有 → "
                                "疑似反爬/代理给了假结果，按未解析处理" % ctext)
            else:
                info["note"] = ("抓到的结果里一个本域名都没有，也没解析到数字 → "
                                "疑似反爬/代理给了假结果，按未解析处理")
    else:
        if hits > 0:
            info["trusted"] = True
        elif ctext:
            info["note"] = "未解析（有数字 %s，但页面里找不到本域名，可能确实没收录）" % ctext
        else:
            info["note"] = "未解析（可能被反爬或尚未收录）"

    if info["trusted"]:
        log("         → 约 %s 条结果（页面里命中本域名 %d 次）" % (ctext or "?", hits))
    else:
        log("         → " + info["note"])
    return info


def check_model_queries(site, urls):
    """抽 3 个型号页做 site:域名 型号 的精确查询。"""
    models = [u for u in urls if "/c/" in u and u.endswith(".html")]
    if not models:
        return []
    picks = random.sample(models, min(3, len(models)))
    host = re.sub(r"^https?://", "", site).split("/")[0]
    out = []
    for u in picks:
        slug = u.rsplit("/", 1)[-1][:-5]
        q = urllib.parse.quote('site:%s %s' % (host, slug))
        label = "型号 %s（/c/%s.html）" % (slug, slug)
        info = check_engine(label, "https://www.bing.com/search?q=%s" % q, host)
        flat = (info.get("body") or "").lower()
        # 精确判定：结果页里出现 /c/<slug>.html 才算真的搜到了这个型号页
        info["found"] = ("/c/%s.html" % slug.lower()) in flat
        info["slug"] = slug
        info["page"] = u
        if info["found"]:
            log("         命中：结果页里出现了这个型号页")
        elif info["trusted"] or info["code"] == 200:
            log("         未见：结果里没有这个型号页（未收录或还没爬）")
        out.append(info)
        time.sleep(1.2)
    return out


# --------------------------------------------------------------------------
# 4. IndexNow key 复查
# --------------------------------------------------------------------------
def find_key_files():
    names = []
    try:
        for name in sorted(os.listdir(HERE)):
            if name.lower().endswith(".txt") and HEX32_RE.match(name[:-4]):
                names.append(name)
    except OSError:
        pass
    return names


def check_indexnow(site):
    log("[4/4] IndexNow key 复查 ……")
    keys = find_key_files()
    if not keys:
        log("      [注意] 根目录没有 32 位十六进制的 .txt，IndexNow 验证会失败。")
        return {"keys": [], "results": [], "ok": False}

    results = []
    for name in keys:
        local_content = ""
        try:
            with open(os.path.join(HERE, name), "r", encoding="utf-8",
                      errors="replace") as f:
                local_content = f.read().strip()
        except OSError:
            local_content = ""
        url = "%s/%s" % (site, name)
        r = http_get(url)
        online = (r["body"] or "").strip()
        match = bool(online) and online == local_content and online.lower() == name[:-4].lower()
        results.append({"name": name, "key": name[:-4], "url": url, "code": r["code"],
                        "err": r["err"], "online": online[:80], "match": match,
                        "local": local_content})
        log("      %s → HTTP %s%s" % (name, r["code"] or "无响应",
                                     ("（" + r["err"] + "）") if r["err"] else ""))
        if r["code"] == 200:
            if match:
                log("         内容 = key，验证没问题。")
            else:
                log("         [警告] 内容对不上！线上是 %r，本地是 %r"
                    % (online[:60], local_content[:60]))
    return {"keys": keys, "results": results,
            "ok": all(x["code"] == 200 and x["match"] for x in results)}


# --------------------------------------------------------------------------
# 5. 出报告
# --------------------------------------------------------------------------
def fmt_num(n):
    if n is None:
        return "?"
    return "{:,}".format(n) if n >= 1000 else str(n)


def build_conclusion(sm, online, engine, models, idx):
    total = sm["total"]
    bits = []
    if online["ratio"] >= 100:
        bits.append("线上 %d 个抽查页全部返回 200，站点是活的" % online["targets"])
    elif online["ratio"] >= 90:
        bits.append("线上抽查 %d/%d 可访问，有零星失败" % (online["ok"], online["targets"]))
    else:
        bits.append("线上抽查只有 %d/%d 可访问，先修可达性" % (online["ok"], online["targets"]))

    bing = engine.get("bing")
    if bing and bing["trusted"] and bing["count"]:
        pct = 100.0 * bing["count"] / total if total else 0
        bits.append("Bing 侧抓到的数字约 %s 条（≈sitemap 的 %.1f%%）" % (fmt_num(bing["count"]), pct))
    elif engine:
        bits.append("Bing / Yandex 的收录数字这次没拿到（反爬或查询被拦，属正常）")
    else:
        bits.append("这次跳过了搜索引擎收录检查")

    hits = [m for m in models if m.get("found")]
    if models:
        bits.append("3 个型号页精确查询命中 %d 个" % len(hits))

    if idx["keys"]:
        if idx["ok"]:
            bits.append("IndexNow 的 key 文件线上可访问且内容正确")
        else:
            bits.append("IndexNow 的 key 文件有问题，需要修")
    else:
        bits.append("没找到 key 文件，IndexNow 会验证失败")

    return "结论：" + "；".join(bits) + "。"


def build_next_step(site, sm, online, engine, models, idx):
    total = sm["total"]
    if online["ratio"] < 100:
        f = online["fails"][0]["url"] if online["fails"] else ""
        return ("下一步建议：先打开失败的那个页面确认是不是文件没上传/路径写错（%s），"
                "修完再跑一次本检查，然后再去 IndexNow 提交。" % f)

    if idx["keys"] and not idx["ok"]:
        return ("下一步建议：打开 %s 确认返回 200 且正文就只有那串 32 位 key，"
                "改好后重新双击「提交收录.cmd」。" % (idx["results"][0]["url"] if idx["results"] else "key 文件"))

    if not engine:
        return ("下一步建议：这次跳过了搜索引擎检查（--no-search），想看收录数字就"
                "再双击一次「收录检查.cmd」，别带这个参数。")

    bing = engine.get("bing")
    if bing and bing["trusted"] and bing["count"] is not None:
        if bing["count"] < total * 0.05:
            return ("下一步建议：已收录占比还很小，继续每周双击「提交收录.cmd」提交新增/改动页面，"
                    "并给 26 个品类页和首页多加指向型号页的内链，等 1～2 周再看这个数字。")
        return ("下一步建议：收录已经铺开，接下来盯“命中率”——每周复查一次，"
                "把这次没被搜到的型号页挑出来，补标题描述或在内链报告里加指向。")

    return ("下一步建议：这次搜索引擎数字拿不到（Bing 给了一堆不相关的结果、Yandex 弹了验证码），"
            "属正常反爬。隔 3～5 天用浏览器手动打开 https://www.bing.com/ 搜 "
            "'site:%s' 看一眼；同时保持每周双击一次「提交收录.cmd」，并给品类页补内链。"
            % re.sub(r"^https?://", "", site).split("/")[0])


def write_report(site, sm, online, engine, models, idx, elapsed, sample_n):
    now = datetime.datetime.now()
    stamp_file = now.strftime("%Y%m%d-%H%M")
    path = os.path.join(HERE, "收录检查报告-%s.md" % stamp_file)

    total = sm["total"]
    counts = sm["counts"]
    order = ["首页", "品类页", "型号页", "政策页", "其他"]
    L = []
    L.append("# 型号查询站 · 收录检查报告")
    L.append("")
    L.append("- 生成时间：%s" % now.strftime("%Y-%m-%d %H:%M:%S"))
    L.append("- 站点：%s" % site)
    L.append("- sitemap：%s（共 %s 条）" % (os.path.basename(SITEMAP_FILE), fmt_num(total)))
    L.append("- 本报告耗时：%.1f 秒" % elapsed)
    L.append("")

    L.append("## 一、本地 sitemap")
    L.append("")
    L.append("| 类型 | 条数 |")
    L.append("| --- | ---: |")
    for k in order:
        if k in counts:
            L.append("| %s | %s |" % (k, fmt_num(counts[k])))
    L.append("| **合计** | **%s** |" % fmt_num(total))
    L.append("")
    L.append("- lastmod 最新时间：**%s**" % (sm["newest"] or "（sitemap 里没有 lastmod）"))
    L.append("")

    L.append("## 二、线上可达")
    L.append("")
    L.append("- 抽查方式：随机抽 %d 条型号/品类页 + 首页 + privacy.html + returns.html，共 %d 条"
             % (sample_n, online["targets"]))
    L.append("- **200 比例：%d/%d = %.0f%%**" % (online["ok"], online["targets"], online["ratio"]))
    L.append("")
    if online["fails"]:
        L.append("失败清单：")
        L.append("")
        L.append("| URL | 状态 | 原因 |")
        L.append("| --- | --- | --- |")
        for f in online["fails"]:
            L.append("| %s | %s | %s |" % (f["url"], f["code"] or "无响应", f["err"] or "-"))
        L.append("")
    else:
        L.append("失败清单：无。全部返回 200。")
        L.append("")

    L.append("## 三、搜索引擎收录（尽力而为）")
    L.append("")
    L.append("| 引擎 | 查询 | HTTP | 数字 | 判断 |")
    L.append("| --- | --- | --- | --- | --- |")
    for key in ("bing", "yandex"):
        e = engine.get(key)
        if not e:
            continue
        if e["trusted"]:
            verdict = "约 %s 条，结果里命中本域名 %d 次" % (e["count_text"] or "?", e["hits"])
            num = e["count_text"] or "—"
        else:
            verdict = e["note"] or "未解析（可能被反爬或尚未收录）"
            num = ("%s（不可信）" % e["count_text"]) if e["count_text"] else "—"
        L.append("| %s | site: | %s | %s | %s |"
                 % (e["label"], e["code"] or "无响应", num, verdict))
    if not engine:
        L.append("| — | — | — | — | 本次跳过了搜索引擎检查（--no-search） |")
    L.append("")
    if models:
        L.append("型号页精确查询（`site:域名 型号`，Bing）：")
        L.append("")
        L.append("| 型号页 | 是否出现 | 说明 |")
        L.append("| --- | --- | --- |")
        for m in models:
            if m["found"]:
                note = "结果页里搜到了这个页面"
            elif not m["trusted"]:
                note = "Bing 这次给的结果不可信，判断不了（不代表没收录）"
            else:
                note = "结果里没有这个页面（未收录或还没爬）"
            L.append("| %s（/c/%s.html） | %s | %s |"
                     % (m["slug"], m["slug"], "出现" if m["found"] else "未见", note))
        L.append("")
    L.append("> 说明：Bing / Yandex 经常给机器人返回验证码或一堆跟本站无关的结果，"
             "脚本会识别这种情况并写“未解析”，不会编数字。想看真数，浏览器里手动查一次最准。")
    L.append("")

    L.append("## 四、IndexNow 复查")
    L.append("")
    if idx["keys"]:
        L.append("根目录找到 key 文件：%s" % "、".join(idx["keys"]))
        L.append("")
        L.append("| 文件 | 线上 URL | HTTP | 内容校验 |")
        L.append("| --- | --- | --- | --- |")
        for r in idx["results"]:
            L.append("| %s | %s | %s | %s |"
                     % (r["name"], r["url"], r["code"] or "无响应",
                        "内容 = key，正常" if r["match"] else "**对不上**"))
        L.append("")
    else:
        L.append("**没找到 32 位十六进制的 `<key>.txt`**，IndexNow 验证会失败，需要补一个。")
        L.append("")

    L.append("## 结论")
    L.append("")
    L.append(build_conclusion(sm, online, engine, models, idx))
    L.append("")
    L.append(build_next_step(site, sm, online, engine, models, idx))
    L.append("")
    L.append("---")
    L.append("由《收录检查.cmd》自动生成，想再看一遍就再双击它。")
    L.append("")

    text = "\n".join(L)
    with open(path, "w", encoding="utf-8-sig") as f:      # 带 BOM，记事本打开不会乱码
        f.write(text)
    return path, text


# --------------------------------------------------------------------------
def main(argv):
    sample_n, do_search, timeout = 20, True, 20
    args = list(argv[1:])
    while args:
        a = args.pop(0)
        if a == "--sample" and args:
            try:
                sample_n = max(1, int(args.pop(0)))
            except ValueError:
                pass
        elif a == "--timeout" and args:
            try:
                timeout = max(5, int(args.pop(0)))
            except ValueError:
                pass
        elif a == "--no-search":
            do_search = False
    global TIMEOUT
    TIMEOUT = timeout
    random.seed()                                    # 真随机，每次抽的不一样

    banner("型号查询站 · 收录检查")
    site = read_cfg_site()
    log("  站点      %s" % site)
    log("  sitemap   %s" % os.path.basename(SITEMAP_FILE))
    log("  超时      %d 秒（失败重试 %d 次）" % (TIMEOUT, RETRIES))
    log("  域名来源  %s" % ("站点设置.txt 的「域名=」" if os.path.exists(CFG_FILE) else "默认值（没有配置文件）"))

    t_start = time.time()
    sm = check_sitemap(site)
    if not sm:
        log("")
        log("[中止] sitemap 读不出来，后面的检查没意义。先双击「重新生成页面.cmd」。")
        return 1

    online = check_online(site, sm["urls"], sample_n)

    engine = {}
    models = []
    if do_search:
        log("[3/4] 搜索引擎收录（尽力而为，失败不影响报告）……")
        host = re.sub(r"^https?://", "", site).split("/")[0]
        sq = urllib.parse.quote("site:%s" % site)
        engine["bing"] = check_engine(
            "Bing", "https://www.bing.com/search?q=%s&count=50" % sq, host)
        time.sleep(1.5)
        engine["yandex"] = check_engine(
            "Yandex", "https://yandex.com/search/?text=%s" % sq, host)
        time.sleep(1.5)
        models = check_model_queries(site, sm["urls"])
    else:
        log("[3/4] 已跳过搜索引擎检查（--no-search）")

    idx = check_indexnow(site)

    elapsed = time.time() - t_start
    path, text = write_report(site, sm, online, engine, models, idx, elapsed, sample_n)

    log("")
    log("=" * 58)
    log("  检查完成，报告已生成：")
    log("  " + os.path.basename(path))
    log("=" * 58)
    log("")
    log(text)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except KeyboardInterrupt:
        log("")
        log("已取消。")
        sys.exit(130)
