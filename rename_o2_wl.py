# -*- coding: utf-8 -*-
"""氧传感器料号统一加 WL 品牌前缀：10-BC001 → WL10-BC001（白盒 C 版就是 WL10-BC001C）。

同时把别的条目里引用到这些料号的地方（交叉号 x、备注 r 的 "Also packed as"）一起改，
不然页面上还会显示老写法。
"""
import io, json, os, re, shutil, time

HERE = r"D:\欧鲸鲸\default-workspace\型号查询站"
DATA = os.path.join(HERE, "data", "data.js")

s = io.open(DATA, encoding="utf-8").read()
i = s.index("window.SITE_DATA=") + len("window.SITE_DATA=")
payload = json.loads(s[i:s.rindex(";")])
items = payload["items"]

# 1) 先算出改名表
rename = {}
for it in items:
    m = it.get("m") or ""
    if re.match(r"^\d{2}-", m):
        rename[m] = "WL" + m

if not rename:
    print("没有需要改名的料号")
    raise SystemExit(0)

# 2) 改 m
for it in items:
    if it.get("m") in rename:
        it["m"] = rename[it["m"]]

# 3) 改引用：x 数组逐项、r 备注按整词替换
pat = re.compile(r"(?<![A-Z0-9])(\d{2}-[A-Z0-9]+[A-Z]?)(?![A-Z0-9])")
n_x = n_r = 0
for it in items:
    if it.get("x"):
        newx = []
        for v in it["x"]:
            if v in rename:
                newx.append(rename[v]); n_x += 1
            else:
                newx.append(v)
        it["x"] = newx
    r = it.get("r") or ""
    if r:
        def rep(m):
            global n_r
            k = m.group(1)
            if k in rename:
                n_r += 1
                return rename[k]
            return k
        it["r"] = pat.sub(rep, r)

# 4) 唯一性检查
seen = {}
for it in items:
    m = it.get("m")
    if m in seen:
        raise SystemExit("改名后出现重复料号：%s" % m)
    seen[m] = 1

bak = DATA + ".bak-wl10-" + time.strftime("%Y%m%d-%H%M%S")
shutil.copyfile(DATA, bak)
payload["generated"] = time.strftime("%Y-%m-%d %H:%M")
head = s[: s.find("{")]
with io.open(DATA, "w", encoding="utf-8", newline="\n") as f:
    f.write(head + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n")

print("改名 %d 条（10-* → WL10-*）" % len(rename))
print("顺带改了交叉号引用 %d 处、备注引用 %d 处" % (n_x, n_r))
print("备份：%s" % os.path.basename(bak))
sample = [k for k in rename if k.endswith("C")][:3]
for k in sample:
    print("  例：%s → %s" % (k, rename[k]))
