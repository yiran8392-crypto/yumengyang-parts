# -*- coding: utf-8 -*-
"""
1688 网业图库 → 型号查询站：补缺图 + 升级低清图
================================================
来源（只读，绝不写回）：
  D:\\111A剪辑\\111资料\\0.1688网业\\<类目>\\**\\*.jpg|png

做了两件事：
  1. 站上没有图的型号 → 按文件名里的型号/OE 配一张主图（800px webp + 260px 缩略图）。
  2. 站上已有图但宽度 < 1200px 的 → 用图库同型号的高清图替换（源图至少比现在宽 10% 才换），
     旧图备份到 images/_v1/<品类>/。

文件名规律（1688 商品图）：
  WL 型号常省前缀：03-0114(1).jpg = WL03-0114；28-0001 (2).jpg = WL28-0001
  也有直接用 OE 号的：19500-B1050(1).jpg、04861959AD(2).jpg
  末尾 (1)(2)(3) 是多角度序号，取 (1) 或第一张。

用法：
    python import_1688.py --dry     只看统计
    python import_1688.py           真跑（补图/换图 + 改 data.js）
    python import_1688.py --no-upgrade   只补缺图，不动已有图
"""

import io
import json
import os
import re
import sys
import time
import shutil
from collections import deque

sys.path.insert(0, r"D:\欧鲸鲸\default-workspace\.pylibs")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
from PIL import Image, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = r"D:\111A剪辑\111资料\0.1688网业"
DATA_JS = os.path.join(HERE, "data", "data.js")
IMG_ROOT = os.path.join(HERE, "images")
REPORT = os.path.join(HERE, "_selftest", "1688补图报告.txt")

FOLDERS = {
    "火花塞": "plug",
    "机油控制阀": "ocv",
    "节气门阀体总成": "throttle",
    "汽油泵总成": "fuelpump",
    "曲轴位置传感器": "ckp",
    "燃油泵模块": "fuelpump",
    "氧传感器": "o2",
    "蒸发探测器": "purge",
    "点火线圈": "coil",
    "分火线": "wire",
    # 2026-11-13 加：实拍/供应商高清图的归档目录（文件夹不存在时 collect() 返回空，无副作用）
    "ABS传感器": "abs",
    "ABS 传感器": "abs",
    "温度传感器": "temp",
    "凸轮轴位置传感器": "cmp",
    "喷油嘴": "injector",
}
SKIP_DIRS = {"海报", "详情图", "定制"}
SKIP_WORDS = ("图片文字修改", "框", "英文", "海报", "详情", "logo")
IMG_EXT = (".jpg", ".jpeg", ".png", ".webp")

FULL_EDGE, FULL_BYTES, THUMB_EDGE, THUMB_Q = 1200, 200 * 1024, 260, 78
UPGRADE_UNDER = 1200     # 宽度小于这个就算低清，可用图库替换（2026-11-13 从 400 提到 1200）
EDGE_MIN = 0.80          # 图片四边白色比例下限：1688 宣传海报整张有底色，四边几乎没白色
WHITE_MIN = 0.25         # 整体白色占比下限


def img_quality(path):
    """(白底占比, 四边白色占比)。用来筛掉带大字的海报图，只留白底产品图。"""
    with Image.open(path) as im:
        im = im.convert("RGB").resize((160, 160))
        px = im.load()
    tot = 0
    w = 0
    for y in range(160):
        for x in range(160):
            r, g, b = px[x, y]
            tot += 1
            if r > 235 and g > 235 and b > 235:
                w += 1
    edge = []
    for x in range(160):
        for y in (0, 1, 2, 3, 156, 157, 158, 159):
            edge.append(px[x, y])
    for y in range(160):
        for x in (0, 1, 2, 3, 156, 157, 158, 159):
            edge.append(px[x, y])
    ew = sum(1 for r, g, b in edge if r > 235 and g > 235 and b > 235) / float(len(edge))
    return w / float(tot), ew


def norm(c):
    return re.sub(r"[^A-Z0-9]", "", str(c or "").upper())


def img_base(code):
    return re.sub(r"[^A-Za-z0-9_.-]", "_", str(code or ""))


def code_from_name(fn):
    stem = os.path.splitext(fn)[0]
    return re.sub(r"\s*[（(]\s*\d+\s*[)）]\s*$", "", stem).strip()


def trim_white(im):
    g = im.convert("L").point(lambda p: 255 if p < 244 else 0)
    box = g.getbbox()
    if box:
        pad = 2
        im = im.crop((max(0, box[0] - pad), max(0, box[1] - pad),
                      min(im.width, box[2] + pad), min(im.height, box[3] + pad)))
    return im


def to_square(im):
    w, h = im.size
    if w == h:
        return im
    side = max(w, h)
    bg = Image.new("RGB", (side, side), (255, 255, 255))
    bg.paste(im, ((side - w) // 2, (side - h) // 2))
    return bg


def fit(im, edge):
    w, h = im.size
    if max(w, h) <= edge:
        return im
    if w >= h:
        return im.resize((edge, max(1, round(h * edge / w))), Image.LANCZOS)
    return im.resize((max(1, round(w * edge / h)), edge), Image.LANCZOS)


def save_webp(im, path, quality, max_bytes=None):
    q = quality
    while True:
        buf = io.BytesIO()
        im.save(buf, "WEBP", quality=q, method=4)
        data = buf.getvalue()
        if max_bytes is None or len(data) <= max_bytes or q <= 40:
            with open(path, "wb") as f:
                f.write(data)
            return len(data)
        q -= 8


def prep_img(path):
    im = Image.open(path)
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        bg = Image.new("RGB", im.size, (255, 255, 255))
        bg.paste(im, mask=im.split()[-1])
        im = bg
    im = ImageOps.exif_transpose(im.convert("RGB"))
    return fit(to_square(trim_white(im)), FULL_EDGE)


def _edge_blocks(im, small=200, max_area=0.16):
    """在缩略图上找「贴边的非白连通域」（店铺角标 / 中文水印块），返回 bbox 列表。"""
    thumb = im.convert("RGB").resize((small, small))
    a = np.asarray(thumb).astype(np.int16)
    mask = ~((a[:, :, 0] > 238) & (a[:, :, 1] > 238) & (a[:, :, 2] > 238))
    seen = np.zeros_like(mask, dtype=bool)
    blocks = []
    for y0 in range(small):
        for x0 in range(small):
            if not mask[y0, x0] or seen[y0, x0]:
                continue
            q = deque([(x0, y0)])
            seen[y0, x0] = True
            pix = []
            while q:
                x, y = q.popleft()
                pix.append((x, y))
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < small and 0 <= ny < small and mask[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        q.append((nx, ny))
            if len(pix) / float(small * small) > max_area:
                continue                      # 太大 = 产品主体
            xs = [p[0] for p in pix]
            ys = [p[1] for p in pix]
            bx0, bx1, by0, by1 = min(xs), max(xs), min(ys), max(ys)
            w, h = bx1 - bx0, by1 - by0
            cx, cy = (bx0 + bx1) / 2.0, (by0 + by1) / 2.0
            touches = bx0 <= 2 or by0 <= 2 or bx1 >= small - 3 or by1 >= small - 3
            in_corner = ((cx < small * 0.40 or cx > small * 0.60) and
                         (cy < small * 0.32 or cy > small * 0.68))
            flat = w > h * 1.4 and h < small * 0.22
            if not (touches or (in_corner and flat)):
                continue
            if w > small * 0.8 or h > small * 0.5:
                continue
            blocks.append((bx0, by0, bx1, by1))
    return blocks, small


def clean_badge(im):
    """抹掉 1688 图上的店铺角标（Drivefar / 中文「全系车型」）。
    用非白像素减少量保护：填掉超过 22% 就判定误伤产品，回退原图。"""
    blocks, small = _edge_blocks(im)
    if not blocks:
        return im, "none"
    W, H = im.size
    sx, sy = W / float(small), H / float(small)
    work = im.copy()
    px = work.load()

    def nonwhite(step=4):
        n = 0
        for y in range(0, H, step):
            for x in range(0, W, step):
                r, g, b = px[x, y]
                if not (r > 235 and g > 235 and b > 235):
                    n += 1
        return n

    before = nonwhite()
    pad = small * 0.02
    for bx0, by0, bx1, by1 in blocks:
        x0 = max(0, int((bx0 - pad) * sx))
        x1 = min(W - 1, int((bx1 + pad) * sx))
        y0 = max(0, int((by0 - pad) * sy))
        y1 = min(H - 1, int((by1 + pad) * sy))
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                px[x, y] = (255, 255, 255)
    after = nonwhite()
    if before and (before - after) / float(before) > 0.22:
        return im, "revert"
    return work, "cleaned:%d" % len(blocks)


def prep_img_restore(im):
    """回退用：把被填白区域还原成原图（简单做法是重新读原图，见 write_shot）"""
    return im


def prep_img_restore(im):
    """回退用：把被填白区域还原成原图（简单做法是重新读原图，见 write_shot）"""
    return im


def load_data():
    raw = io.open(DATA_JS, encoding="utf-8").read()
    k = "window.SITE_DATA="
    idx = raw.find(k)
    payload, _ = json.JSONDecoder().raw_decode(raw[idx + len(k):])
    return raw, payload


def collect(folder):
    root = os.path.join(BASE, folder)
    out = []
    if not os.path.isdir(root):
        return out
    for r, dirs, fns in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fn in fns:
            if fn.lower().endswith(IMG_EXT) and not any(w.lower() in fn.lower() for w in SKIP_WORDS):
                out.append(os.path.join(r, fn))
    # 同一型号多张图时优先 (1)，其次按路径排序
    out.sort(key=lambda p: (0 if re.search(r"[（(]\s*1\s*[)）]", p) else 1, p))
    return out


def main():
    dry = "--dry" in sys.argv
    no_upgrade = "--no-upgrade" in sys.argv
    t0 = time.time()
    raw, payload = load_data()
    items = payload["items"]
    by_cat = {}
    for it in items:
        by_cat.setdefault(it["c"], []).append(it)

    # 现有图宽度
    dims = {}
    for it in items:
        p = it.get("p") or ""
        if not p:
            continue
        fp = os.path.join(HERE, p)
        if os.path.exists(fp):
            try:
                with Image.open(fp) as im:
                    dims[it["i"]] = im.size[0]
            except Exception:
                pass

    # 同一型号多张图：只留「最像白底产品图」的一张（海报图整张有底色，四边没白）
    fill, upgrade, unknown = {}, {}, {}
    up_src = {}          # iid -> 图库源图长边（写报告用）
    per_folder = []
    skipped_poster = 0
    for folder, cat in FOLDERS.items():
        files = collect(folder)
        by_model, by_alias = {}, {}
        for it in by_cat.get(cat, []):
            by_model.setdefault(norm(it["m"]), it)
            for a in [it.get("oe") or ""] + list(it.get("x") or []):
                k = norm(a)
                if len(k) >= 4:
                    by_alias.setdefault(k, it)

        def lookup(code):
            cands = [code]
            if re.fullmatch(r"\d{2}-[A-Za-z0-9.-]+", code):
                cands.append("WL" + code)
            for c in cands:
                k = norm(c)
                if len(k) < 4:
                    continue
                t = by_model.get(k) or by_alias.get(k)
                if t is not None:
                    return t
            k = norm(code)
            if len(k) >= 4:
                hits = [it for m, it in by_model.items() if m.startswith(k)]
                if len(hits) == 1:
                    return hits[0]
            return None

        best = {}      # iid -> (score, path, kind, 源图长边)
        for p in files:
            code = code_from_name(os.path.basename(p))
            if len(norm(code)) < 4:
                continue
            it = lookup(code)
            if it is None:
                continue
            cur = dims.get(it["i"])
            if cur is not None:
                if cur >= UPGRADE_UNDER or no_upgrade:
                    continue
                kind = "upgrade"
            else:
                kind = "fill"
            try:
                with Image.open(p) as _im:
                    sedge = max(_im.size)
            except Exception:
                continue
            # 只换「真变大」的：源图至少比现在宽 10% 才换，否则会把清图换成更糊的图
            if kind == "upgrade" and sedge < cur * 1.10:
                continue
            try:
                wr, ew = img_quality(p)
            except Exception:
                continue
            if ew < EDGE_MIN or wr < WHITE_MIN:
                skipped_poster += 1
                continue
            score = wr + ew * 0.5
            old = best.get(it["i"])
            if old is None or score > old[0]:
                best[it["i"]] = (score, p, kind, sedge)
        nf = nu = 0
        for iid, (sc, p, kind, sedge) in best.items():
            if kind == "fill":
                fill[iid] = p
                nf += 1
            else:
                upgrade[iid] = p
                up_src[iid] = sedge
                nu += 1
        per_folder.append((folder, cat, len(files), nf, nu))
        print("%-12s → %-9s 图=%-5d 补缺=%-4d 升级=%d" % (folder, cat, len(files), nf, nu))

    print("\n合计：补缺 %d / 升级 %d；筛掉疑似海报 %d 张（用时 %.1fs）"
          % (len(fill), len(upgrade), skipped_poster, time.time() - t0))
    if dry:
        print("（试运行，未写任何文件）")
        return 0
    if not fill and not upgrade:
        print("没有可做的，退出。")
        return 0

    # 备份 data.js
    stamp = time.strftime("%Y%m%d-%H%M%S")
    shutil.copyfile(DATA_JS, DATA_JS + ".bak-1688-" + stamp)

    by_i = {it["i"]: it for it in items}
    n_img, fails = 0, []
    badge_stats = {"cleaned": 0, "none": 0, "revert": 0}
    v1dir = os.path.join(IMG_ROOT, "_v1")

    def write_shot(it, src, replace):
        cat = it["c"]
        base = img_base(it["m"])
        d = os.path.join(IMG_ROOT, cat)
        os.makedirs(os.path.join(d, "t"), exist_ok=True)
        full = os.path.join(d, base + ".webp")
        thumb = os.path.join(d, "t", base + ".webp")
        if replace and os.path.exists(full):
            os.makedirs(os.path.join(v1dir, cat), exist_ok=True)
            try:
                shutil.copyfile(full, os.path.join(v1dir, cat, base + ".webp"))
            except Exception:
                pass
        im = prep_img(src)
        im, state = clean_badge(im)
        badge_stats[state.split(":")[0]] = badge_stats.get(state.split(":")[0], 0) + 1
        save_webp(im, full, 82, FULL_BYTES)
        save_webp(fit(im, THUMB_EDGE), thumb, THUMB_Q)
        it["p"] = "images/%s/%s.webp" % (cat, base)
        it["t"] = "images/%s/t/%s.webp" % (cat, base)

    for i, (iid, src) in enumerate(sorted(fill.items()), 1):
        it = by_i.get(iid)
        if not it:
            continue
        try:
            write_shot(it, src, False)
            n_img += 1
        except Exception as e:
            fails.append((it["m"], "fill", str(e)[:60]))
        if i % 50 == 0:
            print("  补图 %d/%d" % (i, len(fill)))

    for i, (iid, src) in enumerate(sorted(upgrade.items()), 1):
        it = by_i.get(iid)
        if not it:
            continue
        try:
            write_shot(it, src, True)
            n_img += 1
        except Exception as e:
            fails.append((it["m"], "upgrade", str(e)[:60]))
        if i % 50 == 0:
            print("  换图 %d/%d" % (i, len(upgrade)))

    # 写回 data.js
    payload["generated"] = time.strftime("%Y-%m-%d %H:%M")
    head = raw[:raw.find("{")]
    with io.open(DATA_JS, "w", encoding="utf-8", newline="\n") as f:
        f.write(head + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n")
    print("data.js 已更新（%d 条）" % len(items))

    # 报告
    lines = ["1688 网业图库 → 型号查询站（%s）" % time.strftime("%Y-%m-%d %H:%M:%S"), "=" * 60,
             "逐类目："]
    for f, c, n, nf, nu in per_folder:
        lines.append("   %-12s %-9s 图=%-5d 补缺=%-4d 升级=%d" % (f, c, n, nf, nu))
    lines += ["", "合计：写图 %d 张（补缺 %d / 升级 %d），失败 %d" % (n_img, len(fill), len(upgrade), len(fails)),
              "角标处理：清掉 %d / 没检测到 %d / 误伤回退 %d"
              % (badge_stats.get("cleaned", 0), badge_stats.get("none", 0), badge_stats.get("revert", 0))]
    if fails:
        lines.append("失败：")
        for x in fails[:30]:
            lines.append("   %s %s %s" % x)
    lines.append("")
    lines.append("低清图判定：宽度 < %dpx；升级前的旧图备份在 images\\_v1\\<品类>\\" % UPGRADE_UNDER)
    lines.append("补缺明细：")
    for iid in sorted(fill, key=lambda x: by_i[x]["m"]):
        it = by_i[iid]
        lines.append("   %-10s %-9s %s" % (it["m"], it["c"], os.path.relpath(fill[iid], BASE)))
    lines.append("")
    lines.append("升级明细：")
    for iid in sorted(upgrade, key=lambda x: by_i[x]["m"]):
        it = by_i[iid]
        lines.append("   %-10s %-9s 原宽 %dpx → 源图 %dpx  %s" % (it["m"], it["c"], dims.get(iid, 0),
                                                            up_src.get(iid, 0),
                                                            os.path.relpath(upgrade[iid], BASE)))
    with io.open(REPORT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print("报告：%s" % REPORT)
    print("完成，用时 %.1f 秒" % (time.time() - t0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
