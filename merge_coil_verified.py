# -*- coding: utf-8 -*-
"""
把三份「线圈 OE 联网核查结果」合并进 data.js：
  - 只补空的 y（年份）/ d（排量）/ e（发动机号）
  - 车型 a 不改（站点已有英文车型，避免被覆盖成子代理的简写）
  - 核查到的品牌/车系写进备注的一条追溯信息（r 里加 "[verified: ...]"），方便回查
  - 生成核对报告：verified / 查不到 / 补了哪些字段
"""
import io
import json
import os
import shutil
import sys
import time

HERE = r"D:\欧鲸鲸\default-workspace\型号查询站"
DATA_JS = os.path.join(HERE, "data", "data.js")
RESULTS = [os.path.join(HERE, "_selftest", "线圈核查结果-%d.json" % i) for i in (1, 2, 3)]
REPORT = os.path.join(HERE, "_selftest", "线圈OE核查报告-%s.md" % time.strftime("%Y%m%d"))


def norm(c):
    import re
    return re.sub(r"[^A-Z0-9]", "", str(c or "").upper())


def main():
    s = io.open(DATA_JS, encoding="utf-8").read()
    i = s.index("window.SITE_DATA=") + len("window.SITE_DATA=")
    payload = json.loads(s[i:s.rindex(";")])
    items = payload["items"]
    by_norm = {norm(it["m"]): it for it in items}

    got = []
    for p in RESULTS:
        if not os.path.exists(p):
            print("缺结果文件：", p)
            continue
        d = json.load(io.open(p, encoding="utf-8"))
        got += d.get("items") or []
    print("核查结果条目：%d" % len(got))

    n_ok = n_miss = 0
    filled = {"y": 0, "d": 0, "e": 0}
    changed = []
    for r in got:
        it = by_norm.get(norm(r.get("model")))
        if not it:
            continue
        if not r.get("verified"):
            n_miss += 1
            continue
        n_ok += 1
        add = {}
        if not it.get("y") and r.get("years"):
            add["y"] = [str(x) for x in r["years"]][:3]
        if not it.get("d") and r.get("disp"):
            add["d"] = [str(x) for x in r["disp"]][:6]
        if not it.get("e") and r.get("engine"):
            add["e"] = [str(x) for x in r["engine"]][:6]
        if add:
            for k, v in add.items():
                it[k] = v
                filled[k] += 1
            changed.append((it["m"], it.get("oe"), add,
                            (r.get("sources") or [""])[0]))
            note = "OE verified online: %s" % ", ".join(
                filter(None, [", ".join(r.get("brands") or []), ", ".join(r.get("models") or [])]))[:60]
            if note and note not in (it.get("r") or ""):
                it["r"] = ((it.get("r") or "") + " | " + note).strip(" |")

    print("verified %d ／ 查不到 %d ／ 补了字段的型号 %d" % (n_ok, n_miss, len(changed)))
    print("补：年份 %d ／ 排量 %d ／ 发动机号 %d" % (filled["y"], filled["d"], filled["e"]))

    if not changed:
        print("没有可写的。")
        return 0
    bak = DATA_JS + ".bak-oeverify-" + time.strftime("%Y%m%d-%H%M%S")
    shutil.copyfile(DATA_JS, bak)
    payload["generated"] = time.strftime("%Y-%m-%d %H:%M")
    head = s[:s.find("{")]
    with io.open(DATA_JS, "w", encoding="utf-8", newline="\n") as f:
        f.write(head + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n")
    print("已写入（备份 %s）" % os.path.basename(bak))

    with io.open(REPORT, "w", encoding="utf-8", newline="\n") as f:
        f.write("# 点火线圈 OE 联网核查（%s）\n\n" % time.strftime("%Y-%m-%d %H:%M"))
        f.write("核查 %d 个 OE：真实存在 **%d**，查不到 %d；补字段型号 %d\n\n"
                % (len(got), n_ok, n_miss, len(changed)))
        f.write("| 型号 | OE | 补的内容 | 依据 |\n| --- | --- | --- | --- |\n")
        for m, oe, add, src in changed:
            f.write("| %s | %s | %s | %s |\n" % (m, oe, json.dumps(add, ensure_ascii=False), src[:80]))
    print("报告：", REPORT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
