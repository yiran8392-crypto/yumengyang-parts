# -*- coding: utf-8 -*-
"""
首页「热销品类」卡片的配图挑选
==============================
每个热销品类从站点现有图片里自动挑一张最适合放大展示的（白底、横向比例、
产品占比适中、分辨率够），做成长边 400×250（16:10）的白底 webp，存到
assets/top/<品类页 slug>.webp。

想人工换图：直接把 assets/top/<slug>.webp 换成你喜欢的图（400×250 最好是
同等比例），站点重建不会覆盖它 —— sitegen 只读不写这个目录。

某个品类站里一张图都没有时（比如氧传感器），生成一张中性的占位图
（浅灰斜纹 + 相机图标，不带文字），等有实拍图了直接替换同名文件即可。

运行：python pick_top.py
"""

import io
import json
import os
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

TOP = os.path.join(HERE, "assets", "top")
DATA_JS = os.path.join(HERE, "data", "data.js")

HOT = ["coil", "fuelpump", "o2", "plug", "abs", "throttle"]
W, H = 400, 250


def load_site():
    raw = io.open(DATA_JS, encoding="utf-8").read()
    k = "window.SITE_DATA="
    i = raw.find(k)
    return json.JSONDecoder().raw_decode(raw[i + len(k):])[0]


def cat_meta():
    import sitegen
    meta = dict(sitegen.CAT_META)
    try:
        import import_catalogs as ic
        meta.update(ic.NEW_CATS)
    except Exception:
        pass
    return meta


def score(im):
    """白底多、横向比例、产品占比适中、分辨率够、边缘锐利 → 分高。"""
    from PIL import ImageChops, ImageFilter, ImageStat
    # 先按内容裁掉大白边，再看「真正挨着产品」的那圈底色（有的图是白边+蓝底）
    g0 = im.convert("L").point(lambda p: 255 if p < 246 else 0)
    box0 = g0.getbbox()
    if box0 and (box0[2] - box0[0]) > 40:
        im = im.crop(box0)
    w, h = im.size
    g = im.convert("L")
    # 只看最外一圈的底色（整图白度会被「白底+蓝底」这种图骗过）
    bw = max(3, int(min(w, h) * 0.07))
    ring = []
    rgb = im.load()
    for x in range(0, w, max(1, w // 60)):
        for y in list(range(0, bw)) + list(range(h - bw, h)):
            ring.append(rgb[x, y])
    for y in range(0, h, max(1, h // 60)):
        for x in list(range(0, bw)) + list(range(w - bw, w)):
            ring.append(rgb[x, y])
    white_ratio = (sum(1 for (r_, g_, b_) in ring if min(r_, g_, b_) > 235) /
                   float(max(1, len(ring))))
    mask = g.point(lambda p: 0 if p > 244 else 255)
    bbox = mask.getbbox()
    fill = 0.0
    if bbox:
        ink = sum(1 for px in mask.getdata() if px) / float(w * h)
        fill = ink
    aspect = w / float(h)
    s_white = min(1.0, max(0.0, (white_ratio - 0.15) / 0.55))
    s_aspect = 1.0 - min(1.0, abs(aspect - 1.45) / 0.9)
    s_fill = 1.0 - min(1.0, abs(fill - 0.40) / 0.40)
    s_res = min(1.0, max(w, h) / 800.0)
    edge = g.filter(ImageFilter.FIND_EDGES)
    s_sharp = min(1.0, ImageStat.Stat(edge).mean[0] / 12.0)
    return (0.34 * s_white + 0.22 * s_aspect + 0.20 * s_fill +
            0.12 * s_res + 0.12 * s_sharp), white_ratio


def make_card(src_path, out_path):
    im = Image.open(src_path).convert("RGB")
    g = im.convert("L").point(lambda p: 255 if p < 246 else 0)
    box = g.getbbox()
    if box and (box[2] - box[0]) > 40:
        pad = 2
        im = im.crop((max(0, box[0] - pad), max(0, box[1] - pad),
                      min(im.width, box[2] + pad), min(im.height, box[3] + pad)))
    scale = min(W / float(im.width), H / float(im.height))
    nw, nh = max(1, int(im.width * scale)), max(1, int(im.height * scale))
    im = im.resize((nw, nh), Image.LANCZOS)
    canvas = Image.new("RGB", (W, H), (255, 255, 255))
    canvas.paste(im, ((W - nw) // 2, (H - nh) // 2))
    q = 84
    while True:
        buf = io.BytesIO()
        canvas.save(buf, "WEBP", quality=q, method=4)
        data = buf.getvalue()
        if len(data) <= 60 * 1024 or q <= 50:
            open(out_path, "wb").write(data)
            return len(data)
        q -= 6


def make_placeholder(out_path):
    """浅灰斜纹 + 相机轮廓，中性占位图（不带任何文字，四语都能用）。"""
    im = Image.new("RGB", (W, H), (245, 247, 249))
    d = ImageDraw.Draw(im)
    for x in range(-H, W + H, 18):
        d.line([(x, H), (x + H, 0)], fill=(236, 240, 244), width=9)
    cx, cy = W // 2, H // 2 - 6
    d.rounded_rectangle([cx - 52, cy - 34, cx + 52, cy + 34], radius=8,
                        outline=(196, 208, 219), width=3)
    d.ellipse([cx - 20, cy - 20, cx + 20, cy + 20], outline=(196, 208, 219), width=3)
    d.rounded_rectangle([cx - 16, cy - 46, cx + 16, cy - 32], radius=4,
                        outline=(196, 208, 219), width=3)
    d.rounded_rectangle([0, 0, W - 1, H - 1], radius=0, outline=(226, 232, 238), width=2)
    buf = io.BytesIO()
    im.save(buf, "WEBP", quality=86, method=4)
    open(out_path, "wb").write(buf.getvalue())
    return len(buf.getvalue())


def main():
    site = load_site()
    meta = cat_meta()
    items = site["items"]
    os.makedirs(TOP, exist_ok=True)
    manifest = {}
    for key in HOT:
        m = meta.get(key)
        slug = m[0] if m else key
        en = m[1] if m else key
        out = os.path.join(TOP, slug + ".webp")
        cands = []
        for it in items:
            if it["c"] != key or not it.get("p"):
                continue
            p = os.path.join(HERE, it["p"])
            if not os.path.exists(p):
                continue
            try:
                im = Image.open(p)
                if max(im.size) < 240:
                    continue
                sc, wr = score(im.convert("RGB"))
                cands.append((sc, wr, it, p, im.size))
            except Exception:
                continue
            if len(cands) >= 90:
                break
        if not cands:
            n = make_placeholder(out)
            manifest[slug] = {"cat": key, "en": en, "sku": None, "src": None,
                              "placeholder": True}
            print("  %-9s → %s  （站里没有实拍图，用中性占位图 %dKB）"
                  % (key, os.path.basename(out), n // 1024))
            continue
        cands.sort(key=lambda x: -x[0])
        # 尽量要白底的（卡片是白底），没有白底的再退而求其次
        whites = [c for c in cands if c[1] >= 0.30]
        sc, wr, it, p, size = whites[0] if whites else cands[0]
        n = make_card(p, out)
        manifest[slug] = {"cat": key, "en": en, "sku": it["m"], "src": it["p"],
                          "score": round(sc, 3), "srcSize": list(size),
                          "placeholder": False}
        print("  %-9s → %s  (SKU %s, %.2f 分, 白底%.0f%%, %dx%d, %dKB)"
              % (key, os.path.basename(out), it["m"], sc, wr * 100, size[0], size[1], n // 1024))
    with open(os.path.join(TOP, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    print("写好 %d 张封面 → assets/top/" % len(manifest))


if __name__ == "__main__":
    main()
