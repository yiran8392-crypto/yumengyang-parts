# -*- coding: utf-8 -*-
"""从 assets/i18n.js 提取 T（界面文案）/ C（品类名）/ PD（产品数据译名）成 JSON。

为什么要它：多语种静态化要把「浏览器里用 JS 现翻」改成「生成时就翻好」，
而翻译表只在 i18n.js 里。这里把三张纯数据表抠出来，避免在 Python 里重抄一遍
（重抄就会两头不同步）。

用法：
    python i18n_extract.py            # 提取并写 _tmp/i18n_cache.json + 打印统计
    python i18n_extract.py --check    # 只校验不写文件（自检用）

⚠️ 只认数据表，不执行 i18n.js。改译名一律去 i18n.js / pdata_i18n.py 改。
"""

import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
I18N_JS = os.path.join(HERE, "assets", "i18n.js")
CACHE = os.path.join(HERE, "_tmp", "i18n_cache.json")

# 与 i18n.js 的 IDX 一致（en 是原文，不占列）
LANGS = ("zh", "ar", "ru", "fr", "es", "pt", "id", "fa")


# ------------------------------------------------------------------ 括号扫描
def slice_literal(src, start):
    """从 start（指向 { 或 [）开始，返回配平的整段字面量文本。
    正确处理：单/双引号字符串、转义、行注释、块注释、模板字符串。"""
    open_ch = src[start]
    close_ch = "}" if open_ch == "{" else "]"
    depth = 0
    i = start
    n = len(src)
    while i < n:
        ch = src[i]
        # 注释
        if ch == "/" and i + 1 < n:
            nxt = src[i + 1]
            if nxt == "/":
                j = src.find("\n", i)
                i = n if j < 0 else j + 1
                continue
            if nxt == "*":
                j = src.find("*/", i + 2)
                i = n if j < 0 else j + 2
                continue
        # 字符串
        if ch in ("'", '"', "`"):
            quote = ch
            i += 1
            while i < n:
                c = src[i]
                if c == "\\":
                    i += 2
                    continue
                if c == quote:
                    i += 1
                    break
                i += 1
            continue
        if ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return src[start:i + 1]
        i += 1
    raise ValueError("括号没配平，起始位置 %d" % start)


def find_literal(src, var_name):
    """定位 `var NAME = {`/`var NAME = [` 并把字面量抠出来。"""
    pat = re.compile(r"\bvar\s+%s\s*=\s*" % re.escape(var_name))
    m = pat.search(src)
    if not m:
        raise ValueError("找不到 var %s =" % var_name)
    i = m.end()
    # 跳过空白
    while i < len(src) and src[i] in " \t\r\n":
        i += 1
    if src[i] not in "{[":
        raise ValueError("%s 后面不是 { 或 [，而是 %r" % (var_name, src[i]))
    return slice_literal(src, i)


# ------------------------------------------------------------------ JS -> JSON
def js_to_json(text):
    """把 JS 对象/数组字面量转成合法 JSON 文本。"""
    out = []
    i = 0
    n = len(text)
    # 记录「上一个有效字符是什么」，用来判断这里出现的标识符能不能当键
    last_sig = ""
    while i < n:
        ch = text[i]

        # 注释：直接丢掉
        if ch == "/" and i + 1 < n:
            nxt = text[i + 1]
            if nxt == "/":
                j = text.find("\n", i)
                i = n if j < 0 else j
                continue
            if nxt == "*":
                j = text.find("*/", i + 2)
                i = n if j < 0 else j + 2
                continue

        # 字符串：统一转成 JSON 双引号字符串。
        # 关键点：JS 单引号字符串里的 \' 在 JSON 里非法，必须还原成 '；
        # 反过来裸的 " 要转义成 \"。这两条不做，json.loads 就炸在某个 don\'t 上。
        if ch in ("'", '"', "`"):
            quote = ch
            j = i + 1
            buf = []
            while j < n:
                c = text[j]
                if c == "\\":
                    esc = text[j + 1] if j + 1 < n else ""
                    if esc == "'":
                        buf.append("'")           # JSON 不认 \'
                    elif esc == '"':
                        buf.append('\\"')         # 保留转义双引号
                    elif esc == "/":
                        buf.append("/")           # \/ 没必要，还原成 /
                    else:
                        buf.append("\\" + esc)    # \\ \n \t \r \b \f \uXXXX JSON 都认
                    j += 2
                    continue
                if c == quote:
                    break
                if c == '"':
                    buf.append('\\"')
                else:
                    buf.append(c)
                j += 1
            out.append('"' + "".join(buf) + '"')
            last_sig = '"'
            i = j + 1
            continue

        # 标识符：可能是无引号键
        if ch.isalpha() or ch in "_$":
            j = i
            while j < n and (text[j].isalnum() or text[j] in "_$"):
                j += 1
            word = text[i:j]
            # 向后看（跳过空白）是不是冒号 → 是则是键
            k = j
            while k < n and text[k] in " \t\r\n":
                k += 1
            if k < n and text[k] == ":" and last_sig in ("{", ","):
                out.append('"' + word + '"')
                last_sig = '"'
            else:
                # true/false/null 直接过；其它（不该出现）原样
                out.append(word)
                last_sig = word[-1]
            i = j
            continue

        # 尾逗号：, 后面紧跟 } 或 ]
        if ch == ",":
            k = i + 1
            while k < n and text[k] in " \t\r\n":
                k += 1
            if k < n and text[k] in "}]":
                i += 1          # 丢掉这个逗号
                continue
            out.append(",")
            last_sig = ","
            i += 1
            continue

        out.append(ch)
        if not ch.isspace():
            last_sig = ch
        i += 1

    return "".join(out)


def parse_var(src, name):
    lit = find_literal(src, name)
    return json.loads(js_to_json(lit))


# ------------------------------------------------------------------ 主流程
def build():
    if not os.path.exists(I18N_JS):
        raise SystemExit("找不到 %s" % I18N_JS)
    src = io.open(I18N_JS, "r", encoding="utf-8-sig").read()

    T = parse_var(src, "T")
    C = parse_var(src, "C")
    PD = parse_var(src, "PD")

    data = {
        "_source": "assets/i18n.js",
        "_langs": list(LANGS),
        "T": T,
        "C": C,
        "PD": PD,
    }
    return data, src


def main():
    check_only = "--check" in sys.argv
    data, src = build()

    T, C, PD = data["T"], data["C"], data["PD"]

    print("=" * 64)
    print("  i18n.js 提取结果")
    print("=" * 64)
    print("  T  语种数 : %d   -> %s" % (len(T), ", ".join("%s:%d" % (k, len(v)) for k, v in sorted(T.items()))))
    print("  C  品类键 : %d" % len(C))
    print("  PD 词条   : %d" % len(PD))

    # --- 自检 1：每行 PD 必须是 9 元素
    bad = [(i, len(r)) for i, r in enumerate(PD) if len(r) != 9]
    print("  PD 行长度不是 9 的 : %d %s" % (len(bad), bad[:5]))

    # --- 自检 2：C 每行必须 8 元素
    badc = [(k, len(v)) for k, v in C.items() if len(v) != 8]
    print("  C  行长度不是 8 的 : %d %s" % (len(badc), badc[:5]))

    # --- 自检 3：T 的每个语种 key 集合应一致
    keysets = {k: set(v.keys()) for k, v in T.items()}
    if keysets:
        base = keysets.get("zh") or next(iter(keysets.values()))
        print()
        print("  各语种 key 数与 zh 的差：")
        for k, ks in sorted(keysets.items()):
            print("    %-4s  keys=%-5d  少 %-3d 多 %-3d" % (
                k, len(ks), len(base - ks), len(ks - base)))

    # --- 自检 4：抽查
    print()
    print("  抽查 T['ar']['wa']      = %r" % (T.get("ar", {}).get("wa"),))
    print("  抽查 T['ru']['nav_guides'] = %r" % (T.get("ru", {}).get("nav_guides"),))
    print("  抽查 C['coil']          = %r" % (C.get("coil"),))
    print("  抽查 PD[0]              = %r" % (PD[0] if PD else None,))

    # --- 自检 5：有多少 key 是 ar/ru/es/pt 四语都齐的（决定能静态化多少）
    print()
    tgt = ("ar", "ru", "es", "pt")
    both = 0
    partial = 0
    none_ = 0
    for key in T.get("zh", {}):
        have = [l for l in tgt if T.get(l, {}).get(key)]
        if len(have) == 4:
            both += 1
        elif have:
            partial += 1
        else:
            none_ += 1
    print("  T 表覆盖（对 ar/ru/es/pt 四语）：")
    print("    四语都齐 : %d" % both)
    print("    部分有   : %d" % partial)
    print("    四语全无 : %d  ← 这些静态化后会退回英文" % none_)

    # 品类名覆盖
    cfull = sum(1 for v in C.values() if all(v[i] for i in (1, 2, 4, 5)))
    print("  品类名四语全齐 : %d / %d" % (cfull, len(C)))

    if check_only:
        print()
        print("[check] 不写缓存文件。")
        return 0

    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    with io.open(CACHE, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=0, sort_keys=False)
    size = os.path.getsize(CACHE)
    print()
    print("[OK] 已写 %s  (%.1f KB)" % (os.path.relpath(CACHE, HERE), size / 1024.0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
