# -*- coding: utf-8 -*-
"""
通用合并：把 _selftest\核查结果-*.json（子代理联网核查产物）合并进 data.js
  - 只补空的 y / d / e
  - 记录来源与核查结论到备注（OE verified online: ...）
  - 生成报告 + "车型冲突待确认"清单（不自动改 a，除 note 明确写清单错）
"""
import glob
import io
import json
import os
import re
import shutil
import sys
import time

HERE = r"D:\欧鲸鲸\default-workspace\型号查询站"
DATA_JS = os.path.join(HERE, "data", "data.js")
REPORT = os.path.join(HERE, "_selftest", "联网核查合并报告-%s.md" % time.strftime("%Y%m%d"))


def norm(c):
    return re.sub(r"[^A-Z0-9]", "", str(c or "").upper())


def main():
    s = io.open(DATA_JS, encoding="utf-8").read()
    i = s.index("window.SITE_DATA=") + len("window.SITE_DATA=")
    payload = json.loads(s[i:s.rindex(";")])
    items = payload["items"]
    by_model = {norm(it["m"]): it for it in items}

    results = sorted(glob.glob(os.path.join(HERE, "_selftest", "核查结果-*.json")))
    got = []
    for p in results:
        try:
            got += json.load(io.open(p, encoding="utf-8")).get("items") or []
        except Exception as e:
            print("读失败", os.path.basename(p), e)
    print("结果文件 %d 个，条目 %d" % (len(results), len(got)))

    n_ok = n_miss = 0
    filled = {"y": 0, "d": 0, "e": 0}
    changed, conflicts = [], []
    for r in got:
        it = by_model.get(norm(r.get("model")))
        if not it:
            continue
        note = r.get("note") or ""
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
            changed.append((it["m"], it.get("oe"), add, (r.get("sources") or [""])[0]))
        tag = "OE verified online: %s" % ", ".join(
            filter(None, [", ".join(r.get("brands") or []), ", ".join((r.get("models") or [])[:3])]))[:60]
        if tag.strip() and tag not in (it.get("r") or ""):
            it["r"] = ((it.get("r") or "") + " | " + tag).strip(" |")
        if re.search("冲突|不符|写错|无据|未证实|笔误|完全不符", note):
            conflicts.append((it["m"], it.get("oe"), (it.get("a") or "")[:60], note[:120],
                              "/".join(r.get("brands") or []), ", ".join((r.get("models") or [])[:6])))

    print("verified %d ／ 查不到 %d ／ 补字段型号 %d（y %d / d %d / e %d）"
          % (n_ok, n_miss, len(changed), filled["y"], filled["d"], filled["e"]))
    print("发现车型冲突 %d 条" % len(conflicts))

    if not changed and not conflicts:
        print("没有可写的。")
        return 0
    if changed:
        bak = DATA_JS + ".bak-merge2-" + time.strftime("%Y%m%d-%H%M%S")
        shutil.copyfile(DATA_JS, bak)
        payload["generated"] = time.strftime("%Y-%m-%d %H:%M")
        head = s[:s.find("{")]
        with io.open(DATA_JS, "w", encoding="utf-8", newline="\n") as f:
            f.write(head + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n")
        print("已写入（备份 %s）" % os.path.basename(bak))

    with io.open(REPORT, "w", encoding="utf-8", newline="\n") as f:
        f.write("# 联网核查合并报告（%s）\n\n" % time.strftime("%Y-%m-%d %H:%M"))
        f.write("核查 %d 条：真实 %d ／ 查不到 %d；补字段型号 %d（年份 %d / 排量 %d / 发动机号 %d）\n\n"
                % (len(got), n_ok, n_miss, len(changed), filled["y"], filled["d"], filled["e"]))
        f.write("## 补充明细\n\n| 型号 | OE | 补的内容 | 依据 |\n| --- | --- | --- | --- |\n")
        for m, oe, add, src in changed:
            f.write("| %s | %s | %s | %s |\n" % (m, oe, json.dumps(add, ensure_ascii=False), (src or "")[:70]))
        f.write("\n## 车型冲突待确认（未自动改）\n\n| 型号 | OE | 现有车型 | 证据品牌/车系 | 说明 |\n| --- | --- | --- | --- | --- |\n")
        for m, oe, a, note, br, md in conflicts:
            f.write("| %s | %s | %s | %s %s | %s |\n" % (m, oe, a, br, md, note))
    print("报告：", REPORT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
