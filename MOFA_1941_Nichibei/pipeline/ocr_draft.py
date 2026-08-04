"""초벌 OCR — 정본이 아니라 **참고용**이다.

    python3 ocr_draft.py ../pages ../raw/draft

tesseract 세로쓰기 모델은 이 자료에서 82% 언저리에 머문다(`ニ→=`, `〇→O`,
`諸→諾`, `於→砂`). 그대로 실을 수 없다. 그래서 지면을 직접 읽는 쪽으로 가되,
이 초벌을 곁에 놓아 **문서 번호와 날짜, 대략의 얼개**를 먼저 잡게 한다.

지면이 가로줄로 위아래 단(段)으로 갈리므로 단을 먼저 가른다. 안 가르면
두 단의 글줄이 섞여 읽힌다.
"""
import sys, os, glob, subprocess
import numpy as np
from PIL import Image

src, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)

def bands(im):
    """가로줄(단 구분선)을 잉크의 가로 투영으로 찾아 끊을 자리를 낸다."""
    a = np.array(im.convert("L"))
    wide = (a < 128).sum(axis=1) > im.width * 0.55
    ys = [i for i, v in enumerate(wide) if v]
    cuts, s = [], None
    for i, y in enumerate(ys):
        if s is None: s = y
        elif y - ys[i-1] > 3: cuts.append((s + ys[i-1]) // 2); s = y
    if s is not None: cuts.append((s + ys[-1]) // 2)
    return [0] + cuts + [im.height]

def tess(im):
    im.save("/tmp/_ocr.png")
    r = subprocess.run(["tesseract", "/tmp/_ocr.png", "-", "-l", "jpn_vert",
                        "--psm", "5", "--dpi", "300"], capture_output=True)
    return r.stdout.decode("utf-8", "replace")

for p in sorted(glob.glob(os.path.join(src, "*.png"))):
    im = Image.open(p)
    cs = bands(im)
    parts = []
    for i in range(len(cs) - 1):
        y0, y1 = cs[i], cs[i+1]
        if y1 - y0 < 120: continue
        parts.append(tess(im.crop((0, y0, im.width, y1))).strip())
    open(os.path.join(out, os.path.basename(p).replace(".png", ".txt")), "w").write(
        "\n\n--- 단 ---\n\n".join(parts))
    print("  ", os.path.basename(p), sum(len(x) for x in parts), "자", flush=True)
