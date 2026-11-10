# -*- coding: utf-8 -*-
"""把备注里残留的旧写法（10-BC001C）改成新写法（WL10-BC001C），只动我们自己的氧传感器料号。"""
import io, json, os, re, shutil, time

HERE = r"D:\欧鲸鲸\default-workspace\型号查询站"
DATA = os.path.join(HERE, "data", "data.js")

s = io.open(DATA, encoding="utf-8").read()
i = s.index("window.SITE_DATA=") + len("window.SITE_DATA=")
payload = json.loads(s[i:s.rindex(";")])
items = payload["items"]

o2_old = {it["m"][2:] for it in items if it.get("c") == "o2" and it["m"].startswith("WL10-")}
# 白盒号多半没有独立页面，也要收进映射
pat = re.compile(r"(?<![A-Z0-9])(10-[A-Z]{1,2}\d{3,4}C?)(?![A-Z0-9])")


def repl(m):
    k = m.group(1)
    if k in o2_old or (k.endswith("C") and k[:-1] in o2_old):
        return "WL" + k
    return k


n = 0
for it in items:
    r = it.get("r") or ""
    if not r:
        continue
    new = pat.sub(repl, r)
    if new != r:
        it["r"] = new
        n += 1

if not n:
    print("没有需要改的")
    raise SystemExit(0)

bak = DATA + ".bak-note-" + time.strftime("%Y%m%d-%H%M%S")
shutil.copyfile(DATA, bak)
payload["generated"] = time.strftime("%Y-%m-%d %H:%M")
head = s[: s.find("{")]
with io.open(DATA, "w", encoding="utf-8", newline="\n") as f:
    f.write(head + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n")
print("改了 %d 条备注里的旧料号写法" % n)
print("备份：%s" % os.path.basename(bak))
