# -*- coding: utf-8 -*-
"""切换域名：把型号查询站从 github.io 迁到自有子域 parts.yumengyang.com

为什么必须跑这个脚本，而不是手改一行：
  站点里 11.9 万处地方写着 github.io —— canonical、og:url、JSON-LD、
  面包屑、分享文案、sitemap、robots 全靠「站点设置.txt」的「域名=」派生。
  只改 DNS 不改这一行，等于 7000 多个页面的 canonical 还指着旧域名，
  Google 会把权重全记在 github.io 上，新域名白绑。

顺序（脚本会自己检查，不能反过来）：
  1. DNS 记录已经加好：parts.yumengyang.com → CNAME → yiran8392-crypto.github.io（灰云）
  2. 写 CNAME 文件（GitHub Pages 靠它记住域名）
  3. 改 站点设置.txt 的「域名=」
  4. 重跑 update_all.py 重新生成全站
  5. 全站扫残留 github.io，报数

⚠️ 第 2 步不能提前做：CNAME 文件一旦进仓库，GitHub 会立刻把自定义域名
   设成 parts.yumengyang.com，此时 DNS 还没生效，<user>.github.io 的老地址
   会被 301 到那个还不存在的域名 —— 现网立刻就挂了。所以本脚本默认
   先验 DNS，验不过就拒绝写入。

用法：
  双击 切换域名.cmd            真跑
  切换域名.cmd check           只体检，不改任何文件
"""

import io
import os
import re
import socket
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SETTINGS = os.path.join(HERE, "站点设置.txt")
CNAME = os.path.join(HERE, "CNAME")
PUBLISH = os.path.join(HERE, "发布上线.cmd")

NEW_DOMAIN = "https://parts.yumengyang.com"
NEW_HOST = "parts.yumengyang.com"
GH_HOST = "yiran8392-crypto.github.io"
OLD_RE = re.compile(r"https://yiran8392-crypto\.github\.io/yumengyang-parts/?")

SKIP_DIRS = {".git", ".tmp", "_selftest", "_backup", "__pycache__", "images", "_shots"}

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


# ---------- 检查 ----------

def current_domain():
    if not os.path.exists(SETTINGS):
        return None
    m = re.search(r"(?m)^域名=(.*)$", read_text(SETTINGS))
    return m.group(1).strip() if m else None


def resolve(host):
    try:
        infos = socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)
        return sorted({i[4][0] for i in infos})
    except Exception:
        return []


def dns_ok():
    """返回 (ok, 说明)。既要能解析，也要和 github.io 落到同一批地址。"""
    new_ips = resolve(NEW_HOST)
    if not new_ips:
        return False, "解析不到 %s（记录还没加，或者还没生效，通常 1-10 分钟）" % NEW_HOST
    gh_ips = resolve(GH_HOST)
    if gh_ips and not (set(new_ips) & set(gh_ips)):
        return False, (
            "能解析，但地址和 github.io 对不上。\n"
            "      %s -> %s\n"
            "      %s -> %s\n"
            "      多半是记录填错，或者开成了橙色小云（必须「仅 DNS」灰云）。"
            % (NEW_HOST, ", ".join(new_ips[:3]), GH_HOST, ", ".join(gh_ips[:3]))
        )
    return True, "%s -> %s（与 github.io 一致）" % (NEW_HOST, ", ".join(new_ips[:2]))


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


def scan_sitemap():
    path = os.path.join(HERE, "sitemap.xml")
    if not os.path.exists(path):
        return None
    s = read_text(path)
    return s.count("github.io"), s.count(NEW_HOST)


# ---------- 改动 ----------

def write_cname():
    write_text(CNAME, NEW_HOST + "\n")


def patch_settings():
    s = read_text(SETTINGS)
    new, n = re.subn(r"(?m)^域名=.*$", "域名=" + NEW_DOMAIN, s)
    if n != 1:
        raise RuntimeError("没在 站点设置.txt 里找到唯一一行「域名=」，先人工看一眼。")
    write_text(SETTINGS, new)


def patch_publish_cmd():
    """发布上线.cmd 里有个 LIVE= 常量，是 GBK 编码。"""
    if not os.path.exists(PUBLISH):
        return "跳过（没有 发布上线.cmd）"
    s = read_text(PUBLISH, enc="gbk")
    new, n = OLD_RE.subn(NEW_DOMAIN + "/", s)
    if n == 0:
        return "已经是新域名或没有 LIVE"
    write_text(PUBLISH, new, enc="gbk")
    return "已改 %d 处" % n


def regen():
    say("  正在重新生成全站（约 1-3 分钟，别关窗口）……")
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    p = subprocess.run(
        [sys.executable, os.path.join(HERE, "update_all.py")],
        cwd=HERE, env=env,
    )
    if p.returncode != 0:
        raise RuntimeError("update_all.py 失败，退出码 %s" % p.returncode)


# ---------- 主流程 ----------

def main():
    check_only = len(sys.argv) > 1 and sys.argv[1].lower() == "check"

    head("型号查询站 · 切换正式域名")
    say("  目标域名：%s" % NEW_DOMAIN)
    cur = current_domain()
    say("  当前域名：%s" % (cur or "（读不到 站点设置.txt）"))
    say()

    ok, why = dns_ok()
    say("  [1] DNS 检查：" + ("通过" if ok else "没通过"))
    say("      " + why)
    if not ok and not check_only:
        head("先别继续")
        say("  DNS 没到位就写 CNAME，会把现在的线上站搞挂：")
        say("  GitHub 一把域名设成 %s，老地址 %s" % (NEW_HOST, GH_HOST))
        say("  就会被 301 过去，而这个域名现在还不通 —— 已经发出去的链接全打不开。")
        say()
        say("  等 DNS 记录加好、能解析了，再双击一次 切换域名.cmd 就行。")
        say()
        return 1

    sitemap_hit = scan_sitemap()
    if sitemap_hit:
        say("  [2] sitemap.xml：旧域名 %d 处 / 新域名 %d 处" % sitemap_hit)
    files, total, samples = scan_residual()
    say("  [3] 全站 HTML 残留 github.io：%d 个文件、%d 处" % (files, total))
    for name, n in samples:
        say("      %s（%d 处）" % (name, n))

    if check_only:
        head("体检完成（没改任何文件）")
        say("  去掉 check 参数双击，才会真的动手。")
        say()
        return 0

    head("开始切换")
    say("  [1/4] 写 CNAME 文件 …… %s" % (NEW_HOST + " 记下了"))
    write_cname()
    say("  [2/4] 改 站点设置.txt …… 域名=%s" % NEW_DOMAIN)
    patch_settings()
    say("  [3/4] 修 发布上线.cmd 里的线上地址 …… %s" % patch_publish_cmd())
    say("  [4/4] 重新生成全站")
    regen()

    files2, total2, samples2 = scan_residual()
    head("结果")
    say("  重新生成后残留 github.io：%d 个文件、%d 处" % (files2, total2))
    if total2:
        say("  （这几处通常是历史文章/备份页，列出来：" + "、".join(n for n, _ in samples2) + "）")
    else:
        say("  干净，全站已经没有旧域名了。")

    head("你还要手点的两下（我点不了）")
    say("  1. GitHub 仓库 Settings > Pages > Custom domain")
    say("     填 %s ，Save，等 1-10 分钟证书签发" % NEW_HOST)
    say("     然后勾上 Enforce HTTPS")
    say()
    say("  2. 双击 发布上线.cmd 把这次改动推上去")
    say()
    say("  推完之后，parts.yumengyang.com 就是正式门面了。")
    say("  再进 Cloudflare 把这条记录从灰云改成橙云（Proxied），")
    say("  SSL/TLS 模式选 Full (strict)，中东非洲拉美就走 Cloudflare 节点了。")
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
