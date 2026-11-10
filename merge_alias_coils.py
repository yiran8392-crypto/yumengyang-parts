# -*- coding: utf-8 -*-
"""把产品目录里的 9 个 WL 料号，作为「同款包装号」挂到站上已存在的型号备注里。

背景：这 9 个号的 OE 在站上都已经有页，只是料号不同（同款不同包装号）。
做法：在匹配到的型号 r（备注）后面追加 "Also packed as WLxx-xxxx"，
      站内搜索会把备注里的号当索引键（index.html prep / list.html buildIndex），
      客户拿旧号来搜就能落到对应型号。
"""
import io, json, os, shutil, time

HERE = r"D:\欧鲸鲸\default-workspace\型号查询站"
DATA = os.path.join(HERE, "data", "data.js")

# (目录里的 WL 料号, 站上已有型号)  —— 来自 6.27 产品目录 + data.js 对账
PAIRS = [
    ("WL03-0117", "WL03-0116"),
    ("WL03-0352", "WL03-0346"),
    ("WL03-0469", "WL03-0458"),
    ("WL03-0136", "WL03-0043"),
    ("WL03-0295", "WL03-0294"),
    ("WL03-0362", "WL03-0349"),
    ("WL03-0576", "WL03-0574"),
    ("WL03-0155", "WL03-0101"),
    ("WL03-0491", "WL03-0470"),
    # ABS：来自《ABS 凸轮 曲轴 节气门 进气压力传感器目录表》，OE 与站上现有一致
    ("WL18-BK052", "WL18-BK051"),
    ("WL18-CA044", "WL18-CA043"),
    ("WL18-BZ004", "WL18-BZ003"),
    ("WL18-QY011", "WL18-QY009"),
    ("WL18-DZ022", "WL18-DZ021"),
    ("WL18-GC345", "WL18-CC045"),
]

s = io.open(DATA, encoding="utf-8").read()
i = s.index("window.SITE_DATA=") + len("window.SITE_DATA=")
payload = json.loads(s[i:s.rindex(";")])
items = payload["items"]
by_m = {}
for it in items:
    by_m.setdefault(it.get("m"), []).append(it)

done, skipped = [], []
for new, old in PAIRS:
    tgt = by_m.get(old)
    if not tgt:
        skipped.append((new, old, "站上没有 %s" % old))
        continue
    it = tgt[0]
    note = it.get("r") or ""
    if new in note:
        skipped.append((new, old, "备注里已经有了"))
        continue
    it["r"] = (note + " | Also packed as %s" % new).strip(" |")
    done.append((new, old))

print("写入 %d 条，跳过 %d 条" % (len(done), len(skipped)))
for d in done:
    print("  %-10s → %s（已加备注）" % d)
for x in skipped:
    print("  跳过 %-10s → %s：%s" % x)

if done:
    bak = DATA + ".bak-alias-" + time.strftime("%Y%m%d-%H%M%S")
    shutil.copyfile(DATA, bak)
    payload["generated"] = time.strftime("%Y-%m-%d %H:%M")
    head = s[: s.find("{")]
    with io.open(DATA, "w", encoding="utf-8", newline="\n") as f:
        f.write(head + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n")
    print("已写入 data.js（备份 %s）" % os.path.basename(bak))
