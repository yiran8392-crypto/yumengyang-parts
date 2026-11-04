# -*- coding: utf-8 -*-
"""
一键更新数据（双击 更新数据.cmd 走的就是这里）
==============================================
做两件事，中间任何一步出错都会停下来，不会把站上的数据弄丢：

  1. import_more.py —— 读 D:\\111A剪辑\\111资料 里的目录表，把站上没有的型号补进去
     （已在的只补交叉号/车型/品牌；价格只进 内部价格-不发布\\价格表.csv）
  2. rerender.py   —— 重新生成 c\\*.html、category\\*.html、index.html 品类块、sitemap

先备份：data\\data.js.bak-YYYYMMDD-HHMM，出了问题可以还原。
"""

import io
import os
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, r"D:\欧鲸鲸\default-workspace\.pylibs")

DATA_JS = os.path.join(HERE, "data", "data.js")


def count_items(path):
    try:
        raw = io.open(path, encoding="utf-8").read()
        key = "window.SITE_DATA="
        i = raw.find(key)
        if i < 0:
            return -1
        import json
        payload, _ = json.JSONDecoder().raw_decode(raw[i + len(key):])
        return len(payload.get("items") or [])
    except Exception:
        return -1


def main():
    t0 = time.time()
    before = count_items(DATA_JS)
    print("=" * 56)
    print(" 型号查询站 · 一键更新")
    print("=" * 56)
    print(" 现有型号：%s 条" % (before if before >= 0 else "?"))

    if os.path.exists(DATA_JS):
        bak = DATA_JS + time.strftime(".bak-%Y%m%d-%H%M")
        shutil.copyfile(DATA_JS, bak)
        print(" 已备份：%s" % os.path.basename(bak))

    print("\n[1/2] 读目录表，补新型号 …")
    import import_more
    rc = import_more.main()
    if rc:
        print("!! 第 1 步失败，站点数据没有继续生成。")
        return 1
    after = count_items(DATA_JS)
    if before >= 1000 and after < before:
        print("!! 型号数从 %d 掉到 %d，停下来，请用 data.js.bak-* 还原。" % (before, after))
        return 1

    print("\n[2/2] 重新生成页面 …")
    import rerender
    rc = rerender.main()
    if rc:
        print("!! 第 2 步失败。数据已经写进 data.js，页面没重生成。")
        return 1

    print("\n合计用时 %.1f 秒。双击 index.html 就能看到新数据。" % (time.time() - t0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
