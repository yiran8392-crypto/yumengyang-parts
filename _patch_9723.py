# -*- coding: utf-8 -*-
"""
补录：威利火花塞 WL29-9723 的 OEM 号与适配明细
==============================================
站点上原来只有型号 WL29-9723（交叉号 SILZKR7B11），oe 字段是空的，
所以客户拿 OE 号 18846-11070 搜不到这一条。

这个脚本只改 data.js 里那一行（oe / x / a / y / d / e / r），
然后重新拆包（data/meta.js + chunk-XX.js），再重渲染静态页。

来源（2026-11-05 核对）：
  · NGK SILZKR7B11，短号 9723，OE Hyundai/Kia 18846-11070
    M12x1.25、螺纹长 26.5mm、六角 16mm、间隙 1.1mm、NGK 热值 7、5kΩ
    https://mosautoshina.ru/catalog/tov/ngk-silzkr7b11-svecha-zazhiganiya-5115703/
  · 适配（TecDoc 关联）：Hyundai Elantra MD / i30 / i40 / ix35 / Tucson /
    Sonata / Santa Fe / Genesis，Kia 同平台车型，1.8-2.4L
用法：python _patch_9723.py   （改完自动重渲染）
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, r"D:\欧鲸鲸\default-workspace\.pylibs")

import data_prep  # noqa: E402

OE = "18846-11070"
XADD = ["9723", "SILZKR7B11", "1884611070"]
APP = ("Hyundai: Elantra (MD) / i30 / i40 / ix35 / Tucson / Sonata / Santa Fe / Genesis; "
       "Kia: K3 Forte / K5 Optima / Sportage / Sorento / Soul")
REMARK = ("Iridium Laser | OEM 18846-11070 | M12x1.25, thread 26.5mm, hex 16mm, gap 1.1mm | "
          "1*4 pcs/box | Unit: pc")


def main():
    payload = data_prep.load_payload()
    items = payload.get("items") or []
    hit = []
    for it in items:
        m = (it.get("m") or "").upper()
        s = (it.get("s") or "").lower()
        if m == "WL29-9723" or s == "wl29-9723":
            hit.append(it)
    if not hit:
        print("!! data.js 里找不到 WL29-9723，先确认型号（是不是已经被清洗成别的编号了）")
        return 1

    for it in hit:
        print("改前：%s" % it)
        it["oe"] = OE
        xs = [x for x in (it.get("x") or []) if x]
        for code in XADD:
            if code.upper() not in [y.upper() for y in xs]:
                xs.append(code)
        it["x"] = xs
        it["a"] = APP
        it["y"] = ["2010-2019"]
        it["d"] = ["1.8L", "2L", "2.4L"]
        it["e"] = ["G4NB", "G4NC", "G4KD", "G4KE"]
        it["r"] = REMARK
        print("改后：%s" % it)

    data_prep.write_data_js(payload)
    info = data_prep.write_chunks(payload)
    print("已写回 data.js · 拆包 %d 片 · 合计 %.1f KB" % (info["chunks"], info["total_kb"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
