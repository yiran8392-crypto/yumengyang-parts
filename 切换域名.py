# -*- coding: utf-8 -*-
"""切换域名：把型号查询站从 github.io 迁到任意自有域名

为什么必须跑这个脚本，而不是手改一行：
  站点里 11.9 万处地方写着 github.io —— canonical、og:url、JSON-LD、
  面包屑、分享文案、sitemap、robots 全靠「站点设置.txt」的「域名=」派生。
  只改 DNS 不改这一行，等于 7000 多个页面的 canonical 还指着旧域名，
  Google 会把权重全记在 github.io 上，新域名白绑。

用法（2026-11-14 改成支持任意域名）：
  切换域名.cmd                          默认 parts.yumengyang.com
  切换域名.cmd yumengyangparts.com      指定域名（裸域或子域都行）
  切换域名.cmd check                    只体检，不改任何文件
  切换域名.cmd check yumengyangparts.com

顺序（DNS 没到位脚本会拒绝写入，这是保护，别绕过）：
  1. 域名已买好、DNS 记录已加好、能解析到 GitHub Pages 的地址
  2. 写 CNAME 文件（GitHub Pages 靠它记住域名）
  3. 改 站点设置.txt 的「域名=」、发布上线.cmd 的 LIVE
  4. 全站替换旧域名 → 新域名（纯字符串替换，不重跑 build，不动图片和 Excel）
  5. 自检：sitemap / 首页 canonical / 残留 github.io 计数

⚠️ 第 2 步不能提前做：CNAME 文件一旦进仓库，GitHub 会立刻把自定义域名
   设成新域名，此时 DNS 还没生效，<user>.github.io 的老地址会被 301 到那个
   还不存在的域名 —— 现网立刻就挂了。所以本脚本默认先验 DNS，验不过就拒绝写入。

DNS 记录（GitHub 官方，2026-11 核对）：
  裸域 yumengyangparts.com：
    A    @   185.199.108.153 / 185.199.109.153 / 185.199.110.153 / 185.199.111.153
    AAAA @   2606:50c0:8000::153 / 8001::153 / 8002::153 / 8003::153（可选）
  www：
    CNAME www → yiran8392-crypto.github.io   ← 只写主机名，不带仓库名
  子域（如 parts.yumengyang.com）：
    CNAME parts → yiran8392-crypto.github.io
"""

import io
import json
import os
import re
import socket
import ssl
import sys
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SETTINGS = os.path.join(HERE, "站点设置.txt")
CNAME = os.path.join(HERE, "CNAME")
PUBLISH = os.path.join(HERE, "发布上线.cmd")

DEFAULT_HOST = "parts.yumengyang.com"
GH_HOST = "yiran8392-crypto.github.io"
GH_IPS = ["185.199.108.153", "185.199.109.153",
          "185.199.110.153", "185.199.111.153"]

# 旧站点地址的两种写法：带仓库名 / 裸主机名
OLD_WITH_PATH = "https://" + GH_HOST + "/yumengyang-parts"

SKIP_DIRS = {".git", ".tmp", "_selftest", "_backup", "__pycache__",
             "images", "_shots", "_sketches", "_shorts"}

HOST_RE = re.compile(
    r"^(?=.{4,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,24}$")

LINE = "=" * 58


def say(msg=""):
    print(msg)
    sys.stdout.flush()


def head(title):
    say()
    say(LINE)
    say("  " + title)
    say(LINE)


def read_text(path, enc="utf-8"):
    with io.open(path, "r", encoding=enc) as f:
        return f.read()


def write_text(path, text, enc="utf-8"):
    tmp = path + ".tmp~"
    with io.open(tmp, "w", encoding=enc, newline="") as f:
        f.write(text)
    os.replace(tmp, path)


# ---------------- 参数 ----------------

def parse_args(argv):
    """返回 (check_only, host)。host 可以是 None（用默认）。"""
    check_only = False
    host = None
    for a in argv:
        s = (a or "").strip()
        if not s:
            continue
        if s.lower() == "check":
            check_only = True
            continue
        if s.startswith("-"):
            continue
        # 允许贴整条网址
        s = s.strip().strip('"').strip("'")
        s = re.sub(r"(?i)^https?://", "", s)
        s = s.split("/")[0].split("?")[0].split(":")[0]
        host = s.lower().rstrip(".")
    return check_only, host


# ---------------- 检查 ----------------

def current_domain():
    if not os.path.exists(SETTINGS):
        return None
    m = re.search(r"(?m)^域名=(.*)$", read_text(SETTINGS))
    return m.group(1).strip() if m else None


def resolve_local(host):
    try:
        infos = socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)
        return sorted({i[4][0] for i in infos})
    except Exception:
        return []


DOH_URLS = [
    # Google：返回干净的 JSON，不需要特殊请求头，国内也基本能通
    "https://dns.google/resolve?%s",
    # Cloudflare：需要 Accept 头
    "https://cloudflare-dns.com/dns-query?%s",
]


def _doh_once(url, host, rtype):
    """查一家。返回 (是否查成功, A/AAAA 地址列表)。
    查成功但没记录 = 域名没配/没注册（权威结论，不能拿本机缓存覆盖）。"""
    q = urllib.parse.urlencode({"name": host, "type": rtype})
    req = urllib.request.Request(
        url % q, headers={"Accept": "application/dns-json", "User-Agent": "dsh-ymy"})
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
        j = json.loads(r.read().decode("utf-8", "replace"))
    ips = []
    for ans in j.get("Answer") or []:
        if ans.get("type") in (1, 28):          # A / AAAA
            ips.append(ans.get("data", ""))
    return True, sorted({x for x in ips if x})


def resolve_doh(host):
    """返回 (是否查成功, IPv4 列表)。任何一家 DoH 通了就用它的结论。"""
    for url in DOH_URLS:
        try:
            ok, ips = _doh_once(url, host, "A")
            if ok:
                return True, [ip for ip in ips if ":" not in ip]
        except Exception:
            continue
    return False, []


def resolve_any(host):
    """DoH 优先（绕开本机缓存/强制门户）。DoH 全挂了才退回本机解析。"""
    ok, ips = resolve_doh(host)
    if ok:
        return ips
    return [ip for ip in resolve_local(host) if ":" not in ip]


def dns_ok(host):
    """返回 (ok, 说明)。要能解析，且落到 GitHub Pages 的地址上。"""
    ips = resolve_any(host)
    if not ips:
        return False, (
            "解析不到 %s。\n"
            "      记录还没加，或者还没生效（通常 1–10 分钟，最长 24 小时）。" % host)
    hit = sorted(set(ips) & set(GH_IPS))
    if not hit:
        return False, (
            "能解析，但地址不是 GitHub Pages 的。\n"
            "      %s -> %s\n"
            "      应该包含 %s 中的任意一个。\n"
            "      多半是记录填错，或者云服务商开了「代理/橙云」（必须「仅 DNS」灰云）。"
            % (host, ", ".join(ips[:4]), GH_IPS[0]))
    return True, "%s -> %s（含 GitHub Pages 地址 %s）" % (
        host, ", ".join(ips[:4]), ", ".join(hit[:2]))


def scan_residual():
    files = total = 0
    samples = []
    for dirpath, dirnames, filenames in os.walk(HERE):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if not name.endswith(".html"):
                continue
            path = os.path.join(dirpath, name)
            try:
                s = read_text(path)
            except Exception:
                continue
            if "github.io" in s:
                n = s.count("github.io")
                files += 1
                total += n
                if len(samples) < 5:
                    samples.append((os.path.relpath(path, HERE), n))
    return files, total, samples


def scan_sitemap(host):
    path = os.path.join(HERE, "sitemap.xml")
    if not os.path.exists(path):
        return None
    s = read_text(path)
    return s.count("github.io"), s.count(host)


# ---------------- 改动 ----------------

def write_cname(host):
    write_text(CNAME, host + "\n")


def patch_settings(host):
    s = read_text(SETTINGS)
    new, n = re.subn(r"(?m)^域名=.*$", "域名=https://" + host, s)
    if n != 1:
        raise RuntimeError("没在 站点设置.txt 里找到唯一一行「域名=」，先人工看一眼。")
    write_text(SETTINGS, new)


def patch_publish_cmd(host):
    """发布上线.cmd 里有个 LIVE= 常量，是 GBK 编码。"""
    if not os.path.exists(PUBLISH):
        return "跳过（没有 发布上线.cmd）"
    s = read_text(PUBLISH, enc="gbk")
    new = re.sub(r'(?m)^set "LIVE=.*$', 'set "LIVE=https://%s/"' % host, s)
    if new == s:
        return "已经是新域名"
    write_text(PUBLISH, new, enc="gbk")
    return "已改 LIVE"


def swap_domain(host):
    """全站把旧域名换成新域名。返回 (改了几个文件, 改了多少处)。"""
    files = hits = 0
    targets = (".html", ".xml", ".txt", ".js", ".json", ".md")
    for dirpath, dirnames, filenames in os.walk(HERE):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if not name.endswith(targets):
                continue
            path = os.path.join(dirpath, name)
            if os.path.abspath(path) == os.path.abspath(SETTINGS):
                continue                     # 上面单独改过
            if name == os.path.basename(PUBLISH):
                continue                     # GBK，单独改过
            try:
                b = open(path, "rb").read()
            except Exception:
                continue
            old = b
            n = 0
            # 先换带仓库名的长串，再换剩下的裸主机名，顺序不能反
            for src, dst in ((OLD_WITH_PATH, "https://" + host), (GH_HOST, host)):
                sb, db = src.encode("utf-8"), dst.encode("utf-8")
                n += b.count(sb)
                b = b.replace(sb, db)
            if b != old:
                open(path, "wb").write(b)
                files += 1
                hits += n
    return files, hits


def verify(host):
    """把关键点抽出来看一眼，返回 (ok, 明细行)。"""
    rows = []
    ok = True

    sm = scan_sitemap(host)
    if sm:
        rows.append("sitemap.xml：旧域名 %d 处 / 新域名 %d 处" % sm)
        if sm[0] != 0:
            ok = False

    idx = os.path.join(HERE, "index.html")
    if os.path.exists(idx):
        s = read_text(idx)
        m = re.search(r'rel="canonical" href="([^"]+)"', s)
        v = m.group(1) if m else "(找不到 canonical)"
        rows.append("首页 canonical：%s" % v)
        if "https://" + host not in v:
            ok = False

    used = resolve_any(host)
    if used:
        rows.append("DNS 复核：%s" % ", ".join(used[:4]))
    return ok, rows


# ---------------- 主流程 ----------------

def main():
    check_only, host_arg = parse_args(sys.argv[1:])
    nl = chr(10)

    if host_arg and not HOST_RE.match(host_arg):
        head("域名格式不对")
        say("  你给的是：%s" % host_arg)
        say("  应该长这样：yumengyangparts.com / parts.yumengyang.com")
        say("  不要带 https://、不要带斜杠、不要带 :端口")
        say()
        return 2

    host = host_arg or DEFAULT_HOST
    new_domain = "https://" + host

    head("型号查询站 · 切换正式域名")
    say("  目标域名：%s" % new_domain)
    say("  当前域名：%s" % (current_domain() or "（读不到 站点设置.txt）"))
    say()

    if current_domain() in (new_domain, new_domain + "/") and not check_only:
        head("已经是这个域名了")
        say("  站点设置.txt 里已经写着 %s。" % new_domain)
        say("  你是要换到别的域名的话，带上域名再跑一次：")
        say("      切换域名.cmd 新域名.com")
        say()
        return 0

    ok, why = dns_ok(host)
    say("  [1] DNS 检查（走 DoH，绕开本机缓存）：" + ("通过" if ok else "没通过"))
    say("      " + why)
    if not ok:
        say()
        if check_only:
            head("体检到此为止（可以提前看到要改多少）")
        else:
            head("先别继续")
            say("  DNS 没到位就写 CNAME，会把现在的线上站搞挂：")
            say("  GitHub 一把域名设成 %s，老地址" % host)
            say("  %s 就会被 301 过去，" % GH_HOST)
            say("  而这个域名现在还不通 —— 已经发出去的链接全打不开。")
            say()
            say("  去域名商后台加这几条，再回来双击一次：")
            say("      A     @   " + " / ".join(GH_IPS))
            say("      CNAME www -> %s" % GH_HOST)
            say()
            return 1

    if not check_only:
        files, hits = swap_domain(host)
        say("  [2] 全站替换旧域名 …… %d 个文件、%d 处" % (files, hits))
        write_cname(host)
        say("  [3] 写 CNAME 文件 …… %s" % host)
        patch_settings(host)
        say("  [4] 改 站点设置.txt …… 域名=%s" % new_domain)
        say("  [5] 修 发布上线.cmd …… %s" % patch_publish_cmd(host))

    files2, total2, samples2 = scan_residual()
    say("  [6] 全站 HTML 残留 github.io：%d 个文件、%d 处" % (files2, total2))
    for name, n in samples2:
        say("      %s（%d 处）" % (name, n))

    vok, rows = verify(host)
    for r in rows:
        say("      " + r)

    if check_only:
        head("体检完成（没改任何文件）")
        say("  去掉 check 参数双击，才会真的动手。")
        say()
        return 0

    head("结果")
    if vok and total2 == 0:
        say("  干净，全站已经没有旧域名了。")
    else:
        say("  还有残留，先别发布，把上面的明细发人看一眼：")
        for name, n in samples2:
            say("      %s（%d 处）" % (name, n))
        say()
        return 1

    head("你还要手点的两下（我点不了）")
    say("  1. 双击 发布上线.cmd 把这次改动推上去")
    say()
    say("  2. 推完之后等 1–10 分钟，打开 https://%s/" % host)
    say("     地址栏有小锁就成了；没小锁去 GitHub 仓库 Settings > Pages：")
    say("       - Custom domain 应该已经自动填好 %s" % host)
    say("       - 勾上 Enforce HTTPS（勾不动就等 10 分钟再勾）")
    say()
    say("  别忘了：推广话术、二维码、名片上的旧链接也要一起换。")
    say()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        say("\n  被中断了，什么也没提交。")
        sys.exit(1)
    except Exception as exc:
        say()
        say("  [失败] %s" % exc)
        say()
        sys.exit(1)
