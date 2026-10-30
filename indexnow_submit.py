# -*- coding: utf-8 -*-
"""
IndexNow 提交（Bing / Yandex / Seznam 共用，不需要任何账号）
============================================================
IndexNow 的玩法：站点根目录放一个验证文件 <key>.txt，内容就是 key；
然后向 https://api.indexnow.org/indexnow POST 一个 JSON，里面写 URL 列表。
搜索引擎收到后自己去抓，返回 200 / 202 就表示"已接收"（不等于已收录）。

用法（在“型号查询站”文件夹里）：

    python indexnow_submit.py                  # 提交 sitemap.xml 里的全部 URL
    python indexnow_submit.py --limit 20       # 只提交前 20 条（试水）
    python indexnow_submit.py https://.../privacy.html https://.../returns.html
                                               # 只提交指定 URL（以后发新页面用这个）
    python indexnow_submit.py --dry-run        # 不真发，只打印会发什么
    python indexnow_submit.py --sitemap 其他.xml

返回码含义：
    200 OK       已接收，URL 交给了索引队列
    202 Accepted 已接收，但还在校验（正常，等几分钟会处理）
    400          请求格式不对（URL 跟 host 不匹配之类）
    403          验证失败：key 文件打不开 / 内容和 key 不一致 → 先修 key 文件再重试
    422          URL 和 key 不匹配，或超过了单次上限
    429          太频繁，被限流，隔一会儿再发

配置来源：
    站点域名  读 站点设置.txt 的「域名=」，读不到就用文件内 DEFAULTS
    key       自动在站点根目录找唯一的 32 位十六进制 <key>.txt，找不到就用 DEFAULTS 里的 key
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CFG_FILE = os.path.join(HERE, "站点设置.txt")

# 兜底：配置文件读不到时用这组（跟站点里实际部署的一致）
DEFAULTS = {
    "site_url": "https://yiran8392-crypto.github.io/yumengyang-parts",
    "key": "8b3e2eebe992aa73225a4c7073fa6554",
}

ENDPOINT = "https://api.indexnow.org/indexnow"
MAX_BATCH = 10000          # IndexNow 单次上限
KEY_RE = re.compile(r"^[0-9a-f]{8,128}$", re.I)
HEX32_RE = re.compile(r"^[0-9a-f]{32}$", re.I)


def log(msg=""):
    print(msg, flush=True)


def read_cfg():
    """只读「域名=」，别的一概不碰（配置文件里还有别的键）。"""
    site = DEFAULTS["site_url"]
    if os.path.exists(CFG_FILE):
        try:
            raw = open(CFG_FILE, "r", encoding="utf-8-sig").read()
        except UnicodeDecodeError:
            raw = open(CFG_FILE, "r", encoding="gbk", errors="ignore").read()
        for line in raw.splitlines():
            line = line.strip()
            if line.startswith("域名=") or line.lower().startswith("site_url="):
                v = line.split("=", 1)[1].strip().rstrip("/")
                if v.startswith("http"):
                    site = v
    return site


def find_key(site_root):
    """站点根目录里唯一的 32 位十六进制 .txt 就是 key 文件。"""
    cands = []
    for name in os.listdir(site_root):
        if name.lower().endswith(".txt") and HEX32_RE.match(name[:-4]):
            cands.append(name[:-4].lower())
    if len(cands) == 1:
        return cands[0]
    return DEFAULTS["key"] if not cands else sorted(cands)[0]


def load_sitemap(path):
    if not os.path.exists(path):
        raise SystemExit("找不到 sitemap：%s（先跑一次 rerender.py）" % path)
    xml = open(path, encoding="utf-8").read()
    urls = re.findall(r"<loc>\s*(.*?)\s*</loc>", xml)
    return [u for u in (x.strip() for x in urls) if u.startswith("http")]


def chunk(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def post_once(payload, timeout):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        ENDPOINT, data=body, method="POST",
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "ymy-parts-indexnow/1.0",
        })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:                     # 网络断了 / DNS / 超时
        return 0, "%s: %s" % (type(e).__name__, e)


def hint_for(code):
    return {
        200: "已接收。搜索引擎开始排队抓取（≠已经收录）。",
        202: "已接收，还在校验。等几分钟，之后会正常处理。",
        400: "请求格式不对：多半是 URL 的域名和 host 不一致。",
        403: "验证失败：key 文件打不开或内容和 key 不一致。"
             "先确认 keyLocation 能打开、里面就是那串 key，再重试。",
        422: "URL 与 key 不匹配，或一次提交超上限（>10000）。",
        429: "提交太频繁被限流，隔几小时再试。",
    }.get(code, "未预期的状态码，把响应体贴给开发看。")


def main(argv=None):
    ap = argparse.ArgumentParser(description="提交 URL 到 IndexNow（Bing / Yandex / Seznam）")
    ap.add_argument("urls", nargs="*", help="只提交这些 URL；不给就读 sitemap")
    ap.add_argument("--sitemap", default=os.path.join(HERE, "sitemap.xml"))
    ap.add_argument("--limit", type=int, default=0, help="只提交前 N 条")
    ap.add_argument("--batch", type=int, default=MAX_BATCH, help="每批多少条（上限 10000）")
    ap.add_argument("--timeout", type=int, default=90, help="单次请求超时秒数")
    ap.add_argument("--retries", type=int, default=3, help="失败重试次数")
    ap.add_argument("--key", default="", help="手动指定 key（默认自动找根目录的 <32hex>.txt）")
    ap.add_argument("--dry-run", action="store_true", help="只打印，不真发")
    a = ap.parse_args(argv)

    site = read_cfg()
    host = re.sub(r"^https?://", "", site).split("/")[0]
    key = (a.key or find_key(HERE)).strip()
    key_loc = "%s/%s.txt" % (site, key)

    if not KEY_RE.match(key):
        log("[错误] key 不像 32 位十六进制：%r" % key)
        return 2
    key_file = os.path.join(HERE, key + ".txt")
    if os.path.exists(key_file):
        inside = open(key_file, encoding="utf-8").read().strip()
        if inside != key:
            log("[警告] 本地 %s.txt 的内容和 key 不一致（文件里是 %r）" % (key, inside[:40]))
    else:
        log("[警告] 本地没有 %s.txt，只有线上有也能提交，但最好补上" % key)

    urls = [u.strip() for u in a.urls if u.strip()] or load_sitemap(a.sitemap)
    urls = [u for u in urls if u.startswith(site)]
    if a.limit:
        urls = urls[:a.limit]
    if not urls:
        log("[错误] 没有可提交的 URL（sitemap 里的域名和「域名=」对不上？）")
        return 2

    log("站点      %s" % site)
    log("host      %s" % host)
    log("key       %s" % key)
    log("keyLocation %s" % key_loc)
    log("URL 数    %d" % len(urls))
    log("接口      %s" % ENDPOINT)
    log("")

    batches = list(chunk(urls, min(a.batch, MAX_BATCH)))
    ok = 0
    for i, batch in enumerate(batches, 1):
        payload = {"host": host, "key": key, "keyLocation": key_loc, "urlList": batch}
        size = len(json.dumps(payload))
        log("--- 第 %d/%d 批：%d 条（%.0f KB）" % (i, len(batches), len(batch), size / 1024.0))
        if a.dry_run:
            log("    [dry-run] 只打印，没真发。前 3 条：%s" % ", ".join(batch[:3]))
            ok += 1
            continue
        code, body = 0, ""
        for attempt in range(1, a.retries + 1):
            t0 = time.time()
            code, body = post_once(payload, a.timeout)
            log("    尝试 %d：HTTP %s（%.1f 秒）%s"
                % (attempt, code or "无响应", time.time() - t0, ("　响应体：" + body[:400]) if body else ""))
            if code in (200, 202):
                break
            if code in (400, 403, 422):        # 重试也没用，直接停
                break
            time.sleep(3 * attempt)            # 0 / 429 / 5xx：等一会儿再来
        if code in (200, 202):
            log("    结果：%s" % hint_for(code))
            ok += 1
        else:
            log("    结果：失败 —— %s" % hint_for(code))
            return 1

    log("")
    log("完成：%d/%d 批被接收，共 %d 条 URL。" % (ok, len(batches), len(urls)))
    log("提醒：200/202 只表示“已接收”，不代表马上被收录；通常几天到两周在 Bing 里能看到，"
        "Google 得等它自己发现 sitemap。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
