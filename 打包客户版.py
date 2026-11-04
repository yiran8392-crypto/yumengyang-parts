# -*- coding: utf-8 -*-
"""
打包「型号查询站-客户版.zip」——直接发给客户、离线双击就能用的那一份。
========================================================================
只收公开文件，内部的东西一个都不进去：
  收：index.html / 404.html / privacy.html / returns.html / robots.txt / sitemap.xml
      START-HERE.txt / assets/ data/ images/ category/ c/ guides/
  不收：内部价格-不发布/ _selftest/ _backup/ 推广物料/ 任何 .py .md .xls .xlsx .csv .cmd

用法：python 打包客户版.py
"""
import os
import sys
import time
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "型号查询站-客户版.zip")
ROOT = "型号查询站-客户版"

FILES = ["index.html", "404.html", "privacy.html", "returns.html", "robots.txt",
         "sitemap.xml", "START-HERE.txt"]
DIRS = ["assets", "data", "images", "category", "c", "guides"]
SKIP_EXT = (".py", ".md", ".txt", ".csv", ".xls", ".xlsx", ".cmd", ".zip", ".orig", ".bak")
SKIP_NAME = ("catalog.js.bak", "data.js.before-more", ".DS_Store")


def main():
    t0 = time.time()
    if os.path.exists(OUT):
        os.remove(OUT)
    n = 0
    total = 0
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for fn in FILES:
            p = os.path.join(HERE, fn)
            if os.path.exists(p):
                z.write(p, "%s/%s" % (ROOT, fn))
                n += 1
                total += os.path.getsize(p)
        for d in DIRS:
            base = os.path.join(HERE, d)
            if not os.path.isdir(base):
                continue
            for r, _dirs, files in os.walk(base):
                for f in files:
                    if f.startswith(".") or f in SKIP_NAME:
                        continue
                    if f.lower().endswith(SKIP_EXT) and not f.lower().endswith(".txt"):
                        continue
                    p = os.path.join(r, f)
                    rel = os.path.relpath(p, HERE).replace("\\", "/")
                    z.write(p, "%s/%s" % (ROOT, rel))
                    n += 1
                    total += os.path.getsize(p)
    mb_src = total / 1048576.0
    mb_zip = os.path.getsize(OUT) / 1048576.0
    print("打包完成：%d 个文件，原始 %.1f MB → 压缩后 %.1f MB（%.1f 秒）"
          % (n, mb_src, mb_zip, time.time() - t0))
    print("文件：%s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
