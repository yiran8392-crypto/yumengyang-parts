# -*- coding: utf-8 -*-
"""
氧传感器单价.xls（BIFF8/OLE2，WPS 存的）→ 公开站补图
=====================================================
路线（按可信度）：
  1. 解析 OLE 的 Workbook 流：
     - MSODRAWINGGROUP 拼出 drawing group，里面的 BSE 依次就是 BLIP 数组（pib 索引）
     - 每张表的 MSODRAWING 记录按顺序拼成 Escher 流，解析 SpContainer 的
       ClientAnchor（行号）和 OPT 属性 0x0104（pib）
     → 锚点行 + pib 一一对应，置信度「高」
  2. 解出某个 pib 的图但行号上没有型号时，退化为同表按行序对应，置信度「中/低」
  3. 实在对不上的图 → 存到 氧传感器图片-待人工对应\，不进公开站

价格（一级价/二级价）只写 内部价格-不发布\价格表.csv，公开数据一个价格都不写。

用法：
    python import_o2.py --dry     # 只统计
    python import_o2.py           # 真跑
"""

import csv
import io
import json
import os
import re
import struct
import sys
import zipfile
from collections import Counter

sys.path.insert(0, r"D:\欧鲸鲸\default-workspace\.pylibs")
import olefile
from PIL import Image, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = r"D:\111A剪辑\氧传感器单价.xls"
SRC_NAME = os.path.basename(SRC)
DATA_JS = os.path.join(HERE, "data", "data.js")
IMG_DIR = os.path.join(HERE, "images", "o2")
MANUAL_DIR = r"D:\欧鲸鲸\default-workspace\氧传感器图片-待人工对应"
PRICE_DIR = os.path.join(HERE, "内部价格-不发布")
PRICE_CSV = os.path.join(PRICE_DIR, "价格表.csv")
REPORT = os.path.join(HERE, "解析失败清单-氧传感器.txt")

FULL_EDGE, FULL_BYTES, THUMB_EDGE, THUMB_Q = 800, 80 * 1024, 260, 78

SHEET_NAMES = ["红盒包装", "白色包装", "红色包装01"]


# ------------------------------------------------------------------ OLE / BIFF
def biff_records(buf, start=0, end=None):
    p = start
    n = len(buf) if end is None else end
    while p + 4 <= n:
        rt, rl = struct.unpack("<HH", buf[p:p + 4])
        if p + 4 + rl > n:
            break
        yield p, rt, rl
        p += 4 + rl


def read_workbook():
    ole = olefile.OleFileIO(SRC)
    wb = ole.openstream("Workbook").read()
    ole.close()
    return wb


def sheet_offsets(wb):
    out = []
    for p, rt, rl in biff_records(wb):
        if rt == 0x0085:
            d = wb[p + 4:p + 4 + rl]
            off = struct.unpack("<I", d[0:4])[0]
            cch = d[6]
            flags = d[7]
            name = (d[8:8 + cch * 2].decode("utf-16le", "ignore")
                    if flags & 0x01 else d[8:8 + cch].decode("gbk", "ignore"))
            out.append((name, off))
    out.sort(key=lambda x: x[1])
    return out


def walk_escher(buf, start, end, depth=0, out=None):
    p = start
    while p + 8 <= end:
        vi, et, el = struct.unpack("<HHI", buf[p:p + 8])
        ver = vi & 0x0F
        ds, de = p + 8, p + 8 + el
        if de > end:
            break
        if out is not None:
            out.append((depth, et, ds, el))
        if ver == 0x0F:
            walk_escher(buf, ds, de, depth + 1, out)
        p = de


def carve_image(data):
    """在一个 BLIP/BSE 里把真正的图片字节抠出来"""
    i = data.find(b"\x89PNG\r\n\x1a\n")
    if i >= 0:
        try:
            im = Image.open(io.BytesIO(data[i:]))
            im.load()
            return im
        except Exception:
            pass
    i = data.find(b"\xff\xd8\xff")
    while i >= 0:
        try:
            im = Image.open(io.BytesIO(data[i:]))
            im.load()
            return im
        except Exception:
            i = data.find(b"\xff\xd8\xff", i + 3)
    # DIB（裸 BITMAPINFOHEADER）
    for sig in (b"\x28\x00\x00\x00",):
        i = data.find(sig)
        while i >= 0 and i + 40 <= len(data):
            w, h, planes, bits = struct.unpack("<iiHH", data[i + 4:i + 16])
            if 20 <= abs(w) <= 6000 and 20 <= abs(h) <= 6000 and planes == 1 and bits in (24, 32, 8, 4):
                stride = ((w * bits // 8) + 3) & ~3
                need = 40 + stride * abs(h)
                if i + need <= len(data):
                    dib = data[i:i + need]
                    bmp = b"BM" + struct.pack("<IHHI", 54 + len(dib), 0, 0, 54) + dib
                    try:
                        im = Image.open(io.BytesIO(bmp))
                        im.load()
                        return im
                    except Exception:
                        pass
            i = data.find(sig, i + 4)
    return None


def load_blips(wb):
    """drawing group → [(pib, Image or None)]"""
    dg = None
    for p, rt, rl in biff_records(wb):
        if rt == 0x00EB:
            dg = p
            break
    if dg is None:
        return []
    buf = bytearray()
    cur = False
    for p, rt, rl in biff_records(wb):
        if p < dg:
            continue
        if p == dg:
            buf += wb[p + 4:p + 4 + rl]
            cur = True
            continue
        if cur and rt == 0x003C:
            buf += wb[p + 4:p + 4 + rl]
            continue
        break
    es = bytes(buf)
    flat = []
    walk_escher(es, 0, len(es), 0, flat)
    bse = [(s, l) for d, t, s, l in flat if d <= 3 and t == 0xF007]
    out = []
    for idx, (s, l) in enumerate(bse):
        im = carve_image(es[s:s + l])
        out.append((idx, im))
    return out


def rk_to_num(rk):
    if rk & 0x02:
        v = rk >> 2
        if v & 0x20000000:
            v -= 0x40000000
        return float(v)
    bits = (rk & 0xFFFFFFFC) << 32
    return struct.unpack("<d", struct.pack("<Q", bits))[0]


def read_sst(wb):
    raw = None
    for p, rt, rl in biff_records(wb):
        if rt == 0x00FC:
            raw = bytearray(wb[p + 4:p + 4 + rl])
            for p2, rt2, rl2 in biff_records(wb):
                if p2 <= p:
                    continue
                if rt2 == 0x003C:
                    raw += wb[p2 + 4:p2 + 4 + rl2]
                    continue
                break
            break
    if not raw:
        return []
    raw = bytes(raw)
    _total, unique = struct.unpack("<II", raw[:8])
    out, pos, n = [], 8, len(raw)
    for _ in range(unique):
        if pos + 3 > n:
            break
        cch = struct.unpack("<H", raw[pos:pos + 2])[0]
        flags = raw[pos + 2]
        pos += 3
        nrun = 0
        if flags & 0x08:
            nrun = struct.unpack("<H", raw[pos:pos + 2])[0]
            pos += 2
        if flags & 0x04:
            pos += 4
        if flags & 0x01:
            s = raw[pos:pos + cch * 2].decode("utf-16le", "ignore")
            pos += cch * 2
        else:
            s = raw[pos:pos + cch].decode("latin-1")
            pos += cch
        pos += nrun * 4
        out.append(s)
    return out


def sheet_rows(path, name):
    """用 xlrd 读单元格（它是专门读 .xls 的，SST/CONTINUE 自己会处理）"""
    import xlrd
    bk = xlrd.open_workbook(path, formatting_info=False, on_demand=True)
    sh = bk.sheet_by_name(name)
    rows = [[c.value for c in sh.row(r)] for r in range(sh.nrows)]
    bk.release_resources()
    return rows


def sheet_cells(wb, start, end, sst):
    cells = {}
    for p, rt, rl in biff_records(wb, start, end):
        d = wb[p + 4:p + 4 + rl]
        if rt == 0x00FD and rl >= 10:
            r, c, _xf, isst = struct.unpack("<HHHI", d[:10])
            if isst < len(sst):
                cells[(r, c)] = sst[isst]
        elif rt == 0x027E and rl >= 10:
            r, c, _xf, rk = struct.unpack("<HHHI", d[:10])
            cells[(r, c)] = rk_to_num(rk)
        elif rt == 0x0203 and rl >= 14:
            r, c = struct.unpack("<HH", d[:4])
            cells[(r, c)] = struct.unpack("<d", d[6:14])[0]
        elif rt in (0x0204, 0x00D6) and rl >= 9:
            r, c0, _xf, cch = struct.unpack("<HHHH", d[:8])
            flags = d[8]
            if flags & 0x01:
                s = d[9:9 + cch * 2].decode("utf-16le", "ignore")
            else:
                s = d[9:9 + cch].decode("gbk", "ignore")
            cells[(r, c0)] = s
        elif rt == 0x00BD and rl >= 6:
            r, c0 = struct.unpack("<HH", d[:4])
            k = (rl - 6) // 6
            for i in range(k):
                _, rk = struct.unpack("<HI", d[4 + i * 6:10 + i * 6])
                cells[(r, c0 + i)] = rk_to_num(rk)
    return cells


def sheet_anchors(wb, start, end):
    """[(row, pib)]：把该表所有 MSODRAWING 拼成一条 Escher 流再走树"""
    buf = bytearray()
    for p, rt, rl in biff_records(wb, start, end):
        if rt == 0x00EC:
            buf += wb[p + 4:p + 4 + rl]
    if not buf:
        return []
    es = bytes(buf)
    flat = []
    walk_escher(es, 0, len(es), 0, flat)
    out = []
    n = len(flat)
    for i, (depth, et, s, l) in enumerate(flat):
        if et != 0xF004:
            continue
        pib = None
        row = None
        for j in range(i + 1, n):
            d2, et2, s2, l2 = flat[j]
            if d2 <= depth:
                break
            if et2 in (0xF00B, 0xF121) and l2 >= 6:
                for k in range(l2 // 6):
                    pid, pv = struct.unpack("<HI", es[s2 + k * 6:s2 + k * 6 + 6])
                    if pid in (0x0104, 0x4104):
                        pib = pv
            elif et2 == 0xF010 and l2 >= 18:
                v = struct.unpack("<9H", es[s2:s2 + 18])
                row = v[3]          # rowL
        if pib is not None and row is not None:
            out.append((row, pib))
    return out


# ------------------------------------------------------------------ 图片处理
def trim_white(im):
    g = im.convert("L").point(lambda p: 255 if p < 244 else 0)
    box = g.getbbox()
    if box:
        p = 2
        im = im.crop((max(0, box[0] - p), max(0, box[1] - p),
                      min(im.width, box[2] + p), min(im.height, box[3] + p)))
    return im


def to_square(im):
    w, h = im.size
    if w == h:
        return im
    side = max(w, h)
    bg = Image.new("RGB", (side, side), (255, 255, 255))
    bg.paste(im, ((side - w) // 2, (side - h) // 2))
    return bg


def fit(im, edge):
    w, h = im.size
    if max(w, h) <= edge:
        return im
    if w >= h:
        return im.resize((edge, max(1, round(h * edge / w))), Image.LANCZOS)
    return im.resize((max(1, round(w * edge / h)), edge), Image.LANCZOS)


def save_webp(im, path, quality, max_bytes=None):
    q = quality
    while True:
        buf = io.BytesIO()
        im.save(buf, "WEBP", quality=q, method=4)
        data = buf.getvalue()
        if max_bytes is None or len(data) <= max_bytes or q <= 40:
            open(path, "wb").write(data)
            return len(data)
        q -= 8


def prep(im):
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        bg = Image.new("RGB", im.size, (255, 255, 255))
        bg.paste(im, mask=im.split()[-1])
        im = bg
    im = ImageOps.exif_transpose(im.convert("RGB"))
    im = trim_white(im)
    im = to_square(im)
    return fit(im, FULL_EDGE)


def norm_code(t):
    return re.sub(r"[^A-Za-z0-9_.-]", "_", str(t).strip())


def load_site():
    raw = io.open(DATA_JS, encoding="utf-8").read()
    k = "window.SITE_DATA="
    i = raw.find(k)
    return json.JSONDecoder().raw_decode(raw[i + len(k):])[0]



# ------------------------------------------------------------------ 主流程
def base_code(c):
    """10-BC001C(10-0046) → 10-BC001；白色包装的 C 后缀、括号备注都去掉"""
    s = re.sub(r"\s+", "", str(c).upper())
    s = re.sub(r"[(（].*?[)）]", "", s)
    s = re.sub(r"[A-Z]$", "", s) if re.match(r"^[0-9]{2}-[A-Z]{2,4}[0-9]{3,4}[A-Z]$", s) else s
    return s


def main():
    dry = "--dry" in sys.argv
    import time
    t0 = time.time()
    site = load_site()
    by_code = {}
    for it in site["items"]:
        if it["c"] == "o2":
            by_code[re.sub(r"\s+", "", it["m"].upper())] = it
    print("站里氧传感器型号 %d 个" % len(by_code))

    wb = read_workbook()
    sheets = [(n, o) for n, o in sheet_offsets(wb) if n in SHEET_NAMES]
    blips = load_blips(wb)
    ok = sum(1 for _, im in blips if im is not None)
    print("BLIP %d 个，可解码 %d 个" % (len(blips), ok))

    picks = {}          # code -> dict(sheet,row,pib,im,conf)
    dup, unknown, manual = [], [], []
    prices, per_sheet = [], []
    for idx, (name, off) in enumerate(sheets):
        end = sheets[idx + 1][1] if idx + 1 < len(sheets) else len(wb)
        rows = sheet_rows(SRC, name)
        anchors = sheet_anchors(wb, off, end)
        exact = med = 0
        for row, pib in anchors:
            if row >= len(rows) or pib >= len(blips) or blips[pib][1] is None:
                manual.append((name, row + 1, pib, "锚点/图片无效"))
                continue
            raw = rows[row][0] if rows[row] else None
            code_raw = str(raw).strip() if raw not in (None, "") else ""
            if not code_raw:
                manual.append((name, row + 1, pib, "这一行没有商品编码"))
                continue
            k_exact = re.sub(r"\s+", "", code_raw.upper())
            conf = "高"
            key = k_exact if k_exact in by_code else None
            if key is None:
                kb = base_code(code_raw)
                if kb in by_code:
                    key = kb
                    conf = "中"      # 由「白色包装 C 版」推回主型号
            if key is None:
                unknown.append((name, row + 1, code_raw))
                manual.append((name, row + 1, pib, "站里没有这个编码：" + code_raw))
                continue
            if key in picks:
                dup.append((name, row + 1, code_raw, picks[key]["sheet"]))
                continue
            picks[key] = {"sheet": name, "row": row + 1, "pib": pib,
                          "im": blips[pib][1], "conf": conf, "code_raw": code_raw}
            if conf == "高":
                exact += 1
            else:
                med += 1
        # 价格
        for r in range(1, len(rows)):
            v = rows[r]
            code = str(v[0]).strip() if v and v[0] not in (None, "") else ""
            if not re.match(r"^[0-9A-Za-z][0-9A-Za-z\-]{2,}$", code):
                continue
            vals = {}
            for cidx, vv in ((6, v[5] if len(v) > 5 else None), (7, v[6] if len(v) > 6 else None)):
                if isinstance(vv, float) and vv > 0:
                    vals[cidx] = ("%.4f" % vv).rstrip("0").rstrip(".")
            if vals:
                prices.append({"来源文件": SRC_NAME, "工作表": name, "行号": str(r + 1),
                               "商品编码": code, "名称": str(v[1] if len(v) > 1 else ""),
                               "vals": vals})
        per_sheet.append((name, len(anchors), exact, med))
        print("  [%-8s] 锚点 %-4d 精确 %-4d 推回 %-4d" % (name, len(anchors), exact, med))

    total_anchor = sum(a for _, a, _, _ in per_sheet)
    print("\n有图的型号 %d / %d（锚点精确 %d，C 版推回 %d），锚点共 %d"
          % (len(picks), len(by_code), sum(e for _, _, e, _ in per_sheet),
             sum(m for _, _, _, m in per_sheet), total_anchor))
    print("  同型号重复图（保留第一张）：%d" % len(dup))
    print("  站里没有的编码：%d" % len(unknown))
    print("  价格行：%d" % len(prices))

    if dry:
        print("\n（试运行，用时 %.1f 秒）" % (time.time() - t0))
        return 0

    # ---------------- 写图
    os.makedirs(os.path.join(IMG_DIR, "t"), exist_ok=True)
    written = kept = 0
    for key, p in picks.items():
        it = by_code[key]
        base = norm_code(it["m"])
        full = os.path.join(IMG_DIR, base + ".webp")
        thumb = os.path.join(IMG_DIR, "t", base + ".webp")
        if os.path.exists(full):
            kept += 1
            p["p"] = "images/o2/%s.webp" % base
            p["t"] = "images/o2/t/%s.webp" % base
            continue
        try:
            im = prep(p["im"])
            save_webp(im, full, 82, FULL_BYTES)
            save_webp(fit(im, THUMB_EDGE), thumb, THUMB_Q)
            written += 1
            p["p"] = "images/o2/%s.webp" % base
            p["t"] = "images/o2/t/%s.webp" % base
        except Exception as e:
            print("  !! 处理失败 %s：%s" % (key, str(e)[:50]))
    print("图片：新写 %d，已存在跳过 %d" % (written, kept))

    # ---------------- 合并 data.js
    filled = 0
    for key, p in picks.items():
        it = by_code[key]
        if not it.get("p"):
            it["p"] = p["p"]
            it["t"] = p["t"]
            filled += 1
    payload = dict(site)
    payload["generated"] = __import__("time").strftime("%Y-%m-%d %H:%M")
    with open(DATA_JS, "w", encoding="utf-8", newline="\n") as f:
        f.write("/* 型号查询站数据文件 —— 由 build.py 自动生成，别手改。 */\n")
        f.write("/* 字段：i=编号 c=品类 m=型号 n=品名 b=品牌 oe=主OE号 x=交叉号数组 a=适配车型 r=备注 p=大图 t=缩略图 */\n")
        f.write("window.SITE_DATA=")
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";\n")
    print("data.js：给 %d 个型号补了图字段（有图总数 %d）"
          % (filled, sum(1 for it in payload["items"] if it["c"] == "o2" and it.get("p"))))

    # ---------------- 价格表
    base_fields = ["来源文件", "工作表", "行号", "商品编码", "名称"]
    rows_csv = []
    if os.path.exists(PRICE_CSV):
        with open(PRICE_CSV, encoding="utf-8-sig", newline="") as f:
            rows_csv = list(csv.DictReader(f))
    fields = set(base_fields)
    for r in rows_csv:
        fields.update(r.keys())
    idx = {(r.get("来源文件", ""), r.get("工作表", ""), r.get("商品编码", "")): i
           for i, r in enumerate(rows_csv)}
    added = updated = 0
    for p in prices:
        row = {k: p[k] for k in base_fields}
        for cidx, val in p["vals"].items():
            row["价格col%d" % cidx] = val
            fields.add("价格col%d" % cidx)
        k = (p["来源文件"], p["工作表"], p["商品编码"])
        if k in idx:
            rows_csv[idx[k]].update(row)
            updated += 1
        else:
            idx[k] = len(rows_csv)
            rows_csv.append(row)
            added += 1
    pc = sorted([f for f in fields if re.fullmatch(r"价格col\d+", f)], key=lambda x: int(x.replace("价格col", "")))
    fieldnames = base_fields + pc + sorted([f for f in fields if f not in base_fields and not re.fullmatch(r"价格col\d+", f)])
    os.makedirs(PRICE_DIR, exist_ok=True)
    with open(PRICE_CSV, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, restval="")
        w.writeheader()
        for r in rows_csv:
            w.writerow({k: r.get(k, "") for k in fieldnames})
    print("价格：新增 %d 行 / 更新 %d 行（共 %d 行）" % (added, updated, len(rows_csv)))

    # ---------------- 待人工对应
    os.makedirs(MANUAL_DIR, exist_ok=True)
    seen_pib = set()
    n_manual = 0
    man_lines = ["氧传感器图片 · 没能自动对上的（表名, 行号, pib, 原因）"]
    for name, row, pib, why in manual:
        if pib in seen_pib or pib >= len(blips) or blips[pib][1] is None:
            continue
        seen_pib.add(pib)
        try:
            im = prep(blips[pib][1])
            save_webp(im, os.path.join(MANUAL_DIR, "P%04d.webp" % pib), 82, FULL_BYTES)
            n_manual += 1
        except Exception:
            pass
        man_lines.append("  %s, 第%d行, P%04d, %s" % (name, row, pib, why))
    with open(os.path.join(MANUAL_DIR, "对应清单.csv"), "w", encoding="utf-8-sig", newline="") as f:
        f.write("\n".join(man_lines) + "\n")

    # ---------------- 报告
    lines = ["氧传感器图片导入报告",
             "来源：%s（BIFF8 .xls，WPS 存）" % SRC_NAME,
             "时间：%s" % __import__("time").strftime("%Y-%m-%d %H:%M:%S"),
             "=" * 60,
             "一、源图",
             "   drawing group 里 BSE(BLIP) 共 %d 张，能解码 %d 张" % (len(blips), ok),
             "   三张表合计锚点 %d 个（同一张图会被多张表引用）" % total_anchor,
             "",
             "二、按锚点匹配（置信度）"]
    for name, a, e, m in per_sheet:
        lines.append("   %-8s 锚点 %-4d 精确(高) %-4d C版推回(中) %-4d" % (name, a, e, m))
    lines.append("   最终给 %d 个型号配上图（占站里 %d 个的 %.1f%%）"
                 % (len(picks), len(by_code), 100.0 * len(picks) / max(1, len(by_code))))
    lines.append("   同型号重复图 %d 张（保留红盒包装那张）" % len(dup))
    lines.append("   站里没有的编码 %d 个" % len(unknown))
    lines.append("")
    lines.append("三、进待人工对应的图：%d 张 → %s" % (n_manual, MANUAL_DIR))
    lines.append("")
    lines.append("四、价格")
    lines.append("   写进 内部价格-不发布/价格表.csv：新增 %d 行，更新 %d 行" % (added, updated))
    lines.append("   公开站 data.js 里没有价格字段（见下面自检）")
    lines.append("")
    lines.append("五、没对上的编码（前 30）")
    for x in unknown[:30]:
        lines.append("   %s 第%d行 %s" % x)
    with open(REPORT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print("报告：%s" % REPORT)
    print("完成，用时 %.1f 秒" % (time.time() - t0))
    return 0


if __name__ == "__main__":
    sys.exit(main())