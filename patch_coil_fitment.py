# -*- coding: utf-8 -*-
"""按联网核查证据，修正 7 个「车型文本与证据冲突」的点火线圈型号（旧文本记到备注）+ 修 OE 笔误"""
import io
import json
import os
import re
import shutil
import time

HERE = r"D:\欧鲸鲸\default-workspace\型号查询站"
DATA_JS = os.path.join(HERE, "data", "data.js")

# 只改这 7 条：三组核查里 note 明确写「清单未证实/不符」的
FIX = {"WL03-0001", "WL03-0254", "WL03-0255", "WL03-0325", "WL03-0356", "WL03-0359", "WL03-0571"}
# OE 笔误：编号末位是数字 0，不是字母 O
OE_FIX = {"27301-08HAO": "27301-08HA0", "FO1R00A188": "F01R00A188"}


def main():
    s = io.open(DATA_JS, encoding="utf-8").read()
    i = s.index("window.SITE_DATA=") + len("window.SITE_DATA=")
    payload = json.loads(s[i:s.rindex(";")])
    items = payload["items"]
    by_model = {it["m"]: it for it in items}

    ev = {}
    for k in (1, 2, 3):
        p = os.path.join(HERE, "_selftest", "线圈核查结果-%d.json" % k)
        if not os.path.exists(p):
            continue
        for x in json.load(io.open(p, encoding="utf-8")).get("items") or []:
            ev[x["model"]] = x

    changed = []
    for m in FIX:
        it = by_model.get(m)
        x = ev.get(m)
        if not it or not x or not x.get("verified"):
            continue
        brands = [b for b in (x.get("brands") or []) if b]
        models = [b for b in (x.get("models") or []) if b]
        if not brands or not models:
            continue
        new_a = "%s %s" % ("/".join(brands[:3]), ", ".join(models[:8]))
        old_a = it.get("a") or ""
        if old_a.strip() == new_a.strip():
            continue
        it["a"] = new_a
        note = "Fitment corrected online (was: %s)" % old_a[:80]
        if note not in (it.get("r") or ""):
            it["r"] = ((it.get("r") or "") + " | " + note).strip(" |")
        changed.append((m, it.get("oe"), old_a, new_a))

    # OE 笔误
    oe_fixed = []
    for it in items:
        oe = (it.get("oe") or "").strip()
        if oe in OE_FIX:
            it["oe"] = OE_FIX[oe]
            it["r"] = ((it.get("r") or "") + " | OE typo fixed: %s" % oe).strip(" |")
            oe_fixed.append((it["m"], oe, OE_FIX[oe]))

    print("车型修正：%d 条；OE 笔误：%d 条" % (len(changed), len(oe_fixed)))
    for x in changed:
        print("  %-10s %-16s %s  →  %s" % (x[0], x[1], x[2][:40], x[3][:60]))
    for x in oe_fixed:
        print("  OE 修正 %-10s %s → %s" % x)
    if not changed and not oe_fixed:
        print("没有要改的。")
        return 0

    bak = DATA_JS + ".bak-fitfix-" + time.strftime("%Y%m%d-%H%M%S")
    shutil.copyfile(DATA_JS, bak)
    payload["generated"] = time.strftime("%Y-%m-%d %H:%M")
    head = s[:s.find("{")]
    with io.open(DATA_JS, "w", encoding="utf-8", newline="\n") as f:
        f.write(head + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n")
    print("已写入（备份 %s）" % os.path.basename(bak))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
