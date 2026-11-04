# -*- coding: utf-8 -*-
"""
企业微信 WeDrive「点火线圈/产品图片」→ 型号查询站
====================================================
源：D:\\企业微信\\WXWork\\1688857019246987\\WeDrive\\驭盟扬电喷\\1-电喷产品专业知识\\1-点火线圈\\产品图片\\
    每个型号一个文件夹（03-0139 / WL03—0011 / 2248—AA100 …），里面放该型号的产品图。

规则：
  - 文件夹名 → 站点型号：`03-0139`→`WL03-0139`、`WL03—0011`→`WL03-0011`（全角破折号/空格容错），
    认不出时拿它去撞 OE / 交叉号。
  - 站上没有图 → 补一张（第一张图，800px webp + 260px 缩略图）。
  - 站上已有图 → 只有新图长边比现有大 20% 以上才换（旧图备份 images/_v1/）。
  - 站内查不到的型号 → 只进报告，不自动新增（缺 OE/车型没法建页）。

用法：
    python import_coil_wedrive.py --dry    看会补/换哪些
    python import_coil_wedrive.py          执行
"""

import io
import json
import os
import re
import shutil
import sys
import time

sys.path.insert(0, r"D:\欧鲸鲸\default-workspace\.pylibs")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PIL import Image
import import_1688 as base

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = r"D:\企业微信\WXWork\1688857019246987\WeDrive\驭盟扬电喷\1-电喷产品专业知识\1-点火线圈\产品图片"
DATA_JS = os.path.join(HERE, "data", "data.js")
IMG_ROOT = os.path.join(HERE, "images")
REPORT = os.path.join(HERE, "_selftest", "点火线圈WeDrive补图报告.txt")
CAT = "coil"
UPGRADE_RATIO = 1.2          # 新图长边要比现有大 20% 才换
IMG_EXT = (".jpg", ".jpeg", ".png", ".webp", ".bmp")


def norm(c):
    return re.sub(r"[^A-Z0-9]", "", str(c or "").upper())


def folder_code(name):
    return re.sub(r"[—－–_]+", "-", name).replace(" ", "").strip()


def code_variants(code):
    """文件夹名 → 站点型号候选：03-0139；03-291 补零成 03-0291；WL03—0011 → WL03-0011"""
    out = []

    def add(x):
        if x and x not in out:
            out.append(x)

    add(code)
    m = re.fullmatch(r"(\d{2})-(\d{1,3})", code)
    if m:
        add("%s-%04d" % (m.group(1), int(m.group(2))))
    if re.match(r"^\d{2}-", code):
        add("WL" + code)
        if m:
            add("WL%s-%04d" % (m.group(1), int(m.group(2))))
    return out


def img_key(name):
    """1.jpg、2.jpg、10.jpg 按数字排（字符串排会把 10 排到 2 前面）"""
    m = re.search(r"(\d+)", os.path.splitext(name)[0])
    return (int(m.group(1)) if m else 999, name)


def score_img(p):
    """(白底比例, 红色占比, 深色占比)
    红色 = WEILI 包装盒/角标；深色 = 真产品本体。纯白底产品图：白高、红低、深色适中。"""
    with Image.open(p) as im:
        im = im.convert("RGB").resize((160, 160))
        px = im.load()
    W = H = 160
    tot = W * H
    white = red = dark = 0
    for y in range(H):
        for x in range(W):
            r, g, b = px[x, y]
            if r > 235 and g > 235 and b > 235:
                white += 1
            elif r > 150 and g < 110 and b < 110:
                red += 1
            if (r + g + b) / 3 < 70:
                dark += 1
    return white / tot, red / tot, dark / tot


def pick_image(folder_path):
    """一个型号文件夹里挑一张最适合做商品主图的。"""
    files = sorted((x for x in os.listdir(folder_path)
                    if x.lower().endswith(IMG_EXT) and not x.startswith(".")), key=img_key)
    if not files:
        return None, None
    scored = []
    for fn in files:
        p = os.path.join(folder_path, fn)
        try:
            w, r, d = score_img(p)
        except Exception:
            continue
        scored.append((fn, p, w, r, d))
    if not scored:
        return None, None
    strong = [x for x in scored if x[3] <= 0.015 and x[4] >= 0.02]   # 白底 + 产品本体对比足
    clean = [x for x in scored if x[3] <= 0.015 and x[4] >= 0.005]   # 退一步：至少不是包装/气垫箱
    pool = strong or clean
    if pool:
        best = max(pool, key=lambda x: x[2])
    else:
        best = min(scored, key=lambda x: (x[3], -x[2]))
    return best[1], best[0]


def make_preview(picks, out_path):
    """把每个型号选中的图拼成一张总览，方便人工过一眼。"""
    from PIL import ImageDraw
    cell, pad, label = 200, 6, 18
    cols = 5
    rows = (len(picks) + cols - 1) // cols
    W = cols * (cell + pad) + pad
    H = rows * (cell + label + pad) + pad
    canvas = Image.new("RGB", (W, H), (245, 245, 245))
    dr = ImageDraw.Draw(canvas)
    for i, (folder, chosen, path) in enumerate(picks):
        r, c = divmod(i, cols)
        x = pad + c * (cell + pad)
        y = pad + r * (cell + label + pad)
        try:
            with Image.open(path) as im:
                im = im.convert("RGB")
                im.thumbnail((cell, cell), Image.LANCZOS)
                canvas.paste(im, (x + (cell - im.width) // 2, y + (cell - im.height) // 2))
        except Exception:
            pass
        dr.rectangle([x, y, x + cell, y + cell], outline=(200, 200, 200))
        dr.text((x + 2, y + cell + 2), "%s  [%s]" % (folder, chosen), fill=(20, 20, 20))
    canvas.save(out_path)
    print("预览图：", out_path)


def main():
    dry = "--dry" in sys.argv
    if not os.path.isdir(SRC):
        print("目录不存在：", SRC)
        return 1

    raw = io.open(DATA_JS, encoding="utf-8").read()
    k = "window.SITE_DATA="
    idx = raw.find(k)
    payload, _ = json.JSONDecoder().raw_decode(raw[idx + len(k):])
    items = payload["items"]
    by_model = {}
    by_alias = {}
    for it in items:            # 全站索引：WL28—0097 这种放在线圈目录、其实属机油控制阀的也能对上
        by_model.setdefault(norm(it["m"]), it)
        for a in [it.get("oe") or ""] + list(it.get("x") or []):
            kk = norm(a)
            if len(kk) >= 4:
                by_alias.setdefault(kk, it)

    folders = sorted(d for d in os.listdir(SRC) if os.path.isdir(os.path.join(SRC, d)))
    print("型号文件夹：%d 个" % len(folders))

    fill, upgrade, unknown = [], [], []
    picks = []
    for f in folders:
        p = os.path.join(SRC, f)
        src, chosen = pick_image(p)
        if src is None:
            unknown.append((f, "文件夹里没有已下载的图片"))
            continue
        picks.append((f, chosen, src))
        keys = [norm(x) for x in code_variants(folder_code(f))]
        it = None
        for kk in keys:
            it = by_model.get(kk) or by_alias.get(kk)
            if it:
                break
        if it is None:
            unknown.append((f, "站内没有这个型号（%s）" % chosen))
            continue
        try:
            with Image.open(src) as im:
                new_edge = max(im.size)
        except Exception as e:
            unknown.append((f, "图片打不开：%s" % e))
            continue
        cur = it.get("p") or ""
        if not cur:
            fill.append((it, src, new_edge))
        else:
            fp = os.path.join(HERE, cur)
            old_edge = 0
            if os.path.exists(fp):
                try:
                    with Image.open(fp) as im:
                        old_edge = max(im.size)
                except Exception:
                    old_edge = 0
            if new_edge >= old_edge * UPGRADE_RATIO:
                upgrade.append((it, src, new_edge, old_edge))

    print("可补缺图：%d ／ 可升级：%d ／ 没结果：%d" % (len(fill), len(upgrade), len(unknown)))
    for it, src, e in fill:
        print("  补 %-10s ← %s (%dpx)" % (it["m"], os.path.basename(src), e))
    for it, src, e, o in upgrade:
        print("  换 %-10s ← %s (%dpx → %dpx)" % (it["m"], os.path.basename(src), o, e))
    for f, why in unknown:
        print("  跳过 %-18s %s" % (f, why))
    if "--preview" in sys.argv:
        make_preview(picks, os.path.join(HERE, "_selftest", "coil_pick_preview.png"))
        return 0
    if dry:
        print("（试运行，未写文件）")
        return 0
    if not fill and not upgrade:
        print("没有可做的。")
        return 0

    stamp = time.strftime("%Y%m%d-%H%M%S")
    shutil.copyfile(DATA_JS, DATA_JS + ".bak-wedrive-" + stamp)
    v1 = os.path.join(IMG_ROOT, "_v1")
    n = 0
    fails = []
    for it, src, e in fill:
        try:
            cat = it["c"]
            b = base.img_base(it["m"])
            d = os.path.join(IMG_ROOT, cat)
            os.makedirs(os.path.join(d, "t"), exist_ok=True)
            im = base.prep_img(src)
            im, _st = base.clean_badge(im)
            base.save_webp(im, os.path.join(d, b + ".webp"), 82, base.FULL_BYTES)
            base.save_webp(base.fit(im, base.THUMB_EDGE), os.path.join(d, "t", b + ".webp"), base.THUMB_Q)
            it["p"] = "images/%s/%s.webp" % (cat, b)
            it["t"] = "images/%s/t/%s.webp" % (cat, b)
            n += 1
        except Exception as ex:
            fails.append((it["m"], str(ex)[:60]))
    for it, src, e, o in upgrade:
        try:
            cat = it["c"]
            b = base.img_base(it["m"])
            d = os.path.join(IMG_ROOT, cat)
            os.makedirs(os.path.join(v1, cat), exist_ok=True)
            oldf = os.path.join(d, b + ".webp")
            if os.path.exists(oldf):
                shutil.copyfile(oldf, os.path.join(v1, cat, b + ".webp"))
            im = base.prep_img(src)
            im, _st = base.clean_badge(im)
            base.save_webp(im, os.path.join(d, b + ".webp"), 82, base.FULL_BYTES)
            base.save_webp(base.fit(im, base.THUMB_EDGE), os.path.join(d, "t", b + ".webp"), base.THUMB_Q)
            it["p"] = "images/%s/%s.webp" % (cat, b)
            it["t"] = "images/%s/t/%s.webp" % (cat, b)
            n += 1
        except Exception as ex:
            fails.append((it["m"], str(ex)[:60]))

    payload["generated"] = time.strftime("%Y-%m-%d %H:%M")
    head = raw[:raw.find("{")]
    with io.open(DATA_JS, "w", encoding="utf-8", newline="\n") as f:
        f.write(head + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n")

    with io.open(REPORT, "w", encoding="utf-8", newline="\n") as f:
        f.write("企业微信 WeDrive 点火线圈补图（%s）\n" % time.strftime("%Y-%m-%d %H:%M:%S"))
        f.write("写图 %d 张（补缺 %d / 升级 %d），失败 %d\n" % (n, len(fill), len(upgrade), len(fails)))
        for it, src, e in fill:
            f.write("  补 %-10s ← %s\n" % (it["m"], os.path.relpath(src, SRC)))
        for it, src, e, o in upgrade:
            f.write("  换 %-10s ← %s (%d → %d px)\n" % (it["m"], os.path.relpath(src, SRC), o, e))
        for x in fails:
            f.write("  失败 %s：%s\n" % x)
        f.write("\n站内没有的文件夹：\n")
        for f_, why in unknown:
            f.write("  %s\t%s\n" % (f_, why))
    print("写完：%d 张，失败 %d；报告 %s" % (n, len(fails), REPORT))
    print("接着跑一遍 rerender.py 让页面换图。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
