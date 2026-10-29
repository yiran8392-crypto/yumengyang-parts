# -*- coding: utf-8 -*-
"""
只重渲染静态页（改文案/模板之后用这个）
=====================================
和 build.py 的区别：
  build.py      读 Excel → 抽图压缩 → 写 data/data.js → 生成所有 HTML（慢，会动图片）
  rerender.py   直接读 data/data.js → 只生成 HTML（快，不碰 data.js、不碰 images/）

改完 sitegen.py 里的文案（品牌、表格标题之类）之后：

    python rerender.py        （或者双击 重新生成页面.cmd）

会重写：c/*.html（7418 个型号页）、category/*.html（品类页）、404.html、
        sitemap.xml、robots.txt，以及 index.html 里的“按品类浏览”区块。
不会动：data/、images/、Excel、内部价格-不发布。
"""

import io
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_JS = os.path.join(HERE, "data", "data.js")

sys.path.insert(0, HERE)
import sitegen  # noqa: E402


def load_payload(path=DATA_JS):
    if not os.path.exists(path):
        raise SystemExit("找不到 %s，请先跑一次 build.py（更新数据.cmd）。" % path)
    raw = io.open(path, encoding="utf-8").read()
    key = "window.SITE_DATA="
    idx = raw.find(key)
    if idx < 0:
        raise SystemExit("data.js 格式不对：没找到 window.SITE_DATA=")
    payload, _end = json.JSONDecoder().raw_decode(raw[idx + len(key):])
    return payload


def to_items(payload):
    """data.js 的行 → sitegen 要的结构（cat/i/m/n/b/oe/x/a/r/p/t）。"""
    items = []
    for row in payload.get("items") or []:
        items.append({
            "i": row["i"],
            "cat": row["c"],
            "m": row.get("m") or "",
            "n": row.get("n") or "",
            "b": row.get("b") or "",
            "oe": row.get("oe") or "",
            "x": row.get("x") or [],
            "a": row.get("a") or "",
            "r": row.get("r") or "",
            "p": row.get("p") or "",
            "t": row.get("t") or "",
        })
    return items


def register_extra_cats(cats):
    """data.js 里没有新品类的 slug/单数英文，从 import_catalogs.NEW_CATS 补回来，
    保证品类页文件名和标题跟第一次 build 完全一致。"""
    try:
        import import_catalogs as ic
        extra = ic.NEW_CATS
    except Exception:
        extra = {}
    n = 0
    for c in cats:
        key = c["key"]
        if key in sitegen.CAT_META:
            continue          # 原有的 5 类已经写在 CAT_META 里了
        pair = extra.get(key)
        if pair:
            sitegen.register_cats([{"key": key, "slug": pair[0], "en": pair[1],
                                    "one": pair[2], "name": pair[3]}])
        else:
            sitegen.register_cats([{"key": key, "en": c.get("en") or key,
                                    "one": c.get("en") or key, "name": c.get("name") or key}])
        n += 1
    return n


def main():
    t0 = time.time()
    payload = load_payload()
    items = to_items(payload)
    cats = [{"key": c["key"], "name": c.get("name") or c["key"],
             "en": c.get("en") or c["key"], "n": c.get("n") or 0}
            for c in (payload.get("cats") or [])]
    if not items:
        raise SystemExit("data.js 里一条 data 都没有，停下。")
    extra = register_extra_cats(cats)
    print("  读 data.js：%d 个型号 / %d 个品类（其中 %d 个新品类补了 slug）"
          % (len(items), len(cats), extra), flush=True)
    print("  品类页：%d 个（含 index）" % (len(cats) + 1), flush=True)

    res = sitegen.build_static(items, cats, log=lambda m: print(m, flush=True))
    print("  完成：%d 个型号页，用时 %.1f 秒" % (res["pages"], time.time() - t0), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
