# -*- coding: utf-8 -*-
"""
一键更新数据（双击 更新数据.cmd 走的就是这里）
==============================================
做三件事，中间任何一步出错都会停下来，不会把站上的数据弄丢：

  1. import_more.py —— 读 D:\\111A剪辑\\111资料 里的目录表，把站上没有的型号补进去
     （已在的只补交叉号/车型/品牌；价格只进 内部价格-不发布\\价格表.csv）
  2. rerender.py   —— 重新生成 c\\*.html、category\\*.html、index.html 品类块、sitemap
  3. validate.py   —— 数据体检：slug 重复 / 缺型号 / 缺 slug 这类明确坏数据直接报错，
     无图、无 OE、中文适配这些历史欠账只提醒（报告写进 _selftest\\）
  4. 内部版重建（可选）—— 找到 02-型号查询站\\内部版 就用刚生成的数据刷一遍，
     找不到或失败只提示，不影响公开站

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

    print("\n[1/3] 读目录表，补新型号 …")
    import import_more
    rc = import_more.main()
    if rc:
        print("!! 第 1 步失败，站点数据没有继续生成。")
        return 1
    after = count_items(DATA_JS)
    if before >= 1000 and after < before:
        print("!! 型号数从 %d 掉到 %d，停下来，请用 data.js.bak-* 还原。" % (before, after))
        return 1

    print("\n[2/4] 重新生成页面 …")
    import rerender
    rc = rerender.main()
    if rc:
        print("!! 第 2 步失败。数据已经写进 data.js，页面没重生成。")
        return 1

    print("\n[3/4] 数据体检 …")
    import validate
    rc = validate.main([])
    if rc:
        print("!! 体检没过（上面列的是 FATAL），这次的数据不能发布。")
        print("   报告在 _selftest\\校验报告-*.md；改好再双击一次。")
        return 1

    print("\n[4/4] 顺带刷新内部报价查询站 …")
    if not refresh_internal():
        print("   [提示] 内部版没刷新成功（不影响公开站）。需要时到内部版双击一次“更新内部数据.cmd”。")

    print("\n合计用时 %.1f 秒。双击 index.html 就能看到新数据。" % (time.time() - t0))
    return 0


# 内部报价查询站在哪儿：按顺序找，找到就用
INTERNAL_CANDIDATES = [
    os.path.join(os.path.dirname(HERE), "02-型号查询站", "内部版"),
    os.path.join(os.path.dirname(HERE), "型号查询站-内部版"),
    os.path.join(os.path.dirname(HERE), "内部版"),
]


def refresh_internal():
    """用刚生成好的 data.js 重建内部版（价格仍在 内部价格-不发布\\价格表.csv）。
    找不到内部版 / 跑失败都只提示，不影响公开站。"""
    import subprocess
    for d in INTERNAL_CANDIDATES:
        script = os.path.join(d, "build_internal.py")
        if not os.path.exists(script):
            continue
        print("   找到内部版：%s" % d)
        try:
            r = subprocess.run([sys.executable, script], cwd=d, timeout=600)
        except Exception as e:
            print("   内部版构建出错：%s" % e)
            return False
        if r.returncode != 0:
            print("   内部版构建返回 %d，没刷新成功。" % r.returncode)
            return False
        return True
    print("   没找到内部版目录（找过：%s）。" % "、".join(os.path.basename(x) for x in INTERNAL_CANDIDATES))
    return False


if __name__ == "__main__":
    sys.exit(main())
