# -*- coding: utf-8 -*-
"""
增强首屏背景图（Real-ESRGAN 4x + 真实纹理回混 + 轻锐化）→ assets/hero/

为什么不能用原来的 2560x1440 直接 cover：
  源图本身是暗光手机实拍，细节少；封面铺满 2x 屏时会被放大，
  再叠 0.93 的深色遮罩，观感就是"糊"。

流程：
  1) realesrgan-ncnn-vulkan（.tools/sr/realesrgan，跑 GPU）4x 超分
  2) 降采样到 3840x2160（4K 够 2x 屏 + 大屏）
  3) 与 Lanczos 放大的原图按 0.72/0.28 混合：保留真实颗粒，避免 AI 塑料感
  4) 轻锐化 UnsharpMask(1.2, 110%, 2)
  5) 输出 webp（桌面 3840 / 移动 1280 小图）

跑法：python 增强首屏图.py
需要：.tools/sr/realesrgan 已解压（--setup 重新下载）
"""
import os
import subprocess
import sys
import urllib.request
import zipfile

from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
WORKSPACE = os.path.dirname(HERE)
SR_DIR = os.path.join(WORKSPACE, ".tools", "sr", "realesrgan")
EXE = os.path.join(SR_DIR, "realesrgan-ncnn-vulkan.exe")
WORK = os.path.join(WORKSPACE, "_tmp", "hero-sr")
SRC = os.path.join(HERE, "_sketches", "hero", "hero-warehouse.jpg")
OUT_DIR = os.path.join(HERE, "assets", "hero")
ZIP_URL = ("https://github.com/xinntao/Real-ESRGAN/releases/download/"
           "v0.2.5.0/realesrgan-ncnn-vulkan-20220424-windows.zip")

# 最终尺寸
DESKTOP = (3840, 2160)
MOBILE = (1280, 720)
BLEND = 0.28            # 真实图回混比例（0 = 纯 AI，1 = 纯放大锐化）
WEBP_Q_DESKTOP = 78
WEBP_Q_MOBILE = 70


def setup():
    """下载并解压 realesrgan-ncnn-vulkan（约 45MB）。"""
    os.makedirs(os.path.dirname(SR_DIR), exist_ok=True)
    zp = os.path.join(os.path.dirname(SR_DIR), "realesrgan.zip")
    print("下载", ZIP_URL, flush=True)
    with urllib.request.urlopen(ZIP_URL, timeout=1800) as r, open(zp, "wb") as f:
        while True:
            b = r.read(1 << 20)
            if not b:
                break
            f.write(b)
    with zipfile.ZipFile(zp) as z:
        z.extractall(SR_DIR)
    print("已解压到", SR_DIR)


def upscale_4x(src, dst):
    os.makedirs(WORK, exist_ok=True)
    cmd = [EXE, "-i", src, "-o", dst, "-n", "realesrgan-x4plus",
           "-s", "4", "-m", "models", "-t", "256", "-g", "0", "-f", "png"]
    print("超分中:", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=SR_DIR, check=True)


def build():
    if not os.path.exists(EXE):
        setup()
    os.makedirs(WORK, exist_ok=True)
    os.makedirs(OUT_DIR, exist_ok=True)

    raw = os.path.join(WORK, "hero-x4.png")
    if not os.path.exists(raw):
        upscale_4x(SRC, raw)

    ai = Image.open(raw).convert("RGB")
    orig = Image.open(SRC).convert("RGB")
    print("超分结果", ai.size, "源图", orig.size)

    out = {}
    for name, size, q in (("hero-warehouse.webp", DESKTOP, WEBP_Q_DESKTOP),
                          ("hero-warehouse-sm.webp", MOBILE, WEBP_Q_MOBILE)):
        a = ai.resize(size, Image.LANCZOS)
        b = orig.resize(size, Image.LANCZOS)
        merged = Image.blend(a, b, BLEND)
        merged = merged.filter(ImageFilter.UnsharpMask(radius=1.2, percent=110, threshold=2))
        path = os.path.join(OUT_DIR, name)
        merged.save(path, "WEBP", quality=q, method=6)
        out[name] = os.path.getsize(path)
    for k, v in out.items():
        print("%s  %d KB" % (k, v // 1024))


if __name__ == "__main__":
    if "--setup" in sys.argv:
        setup()
    build()
