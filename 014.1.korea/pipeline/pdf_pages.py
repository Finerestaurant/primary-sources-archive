"""PDF → 면별 이미지.

    python3 pdf_pages.py ../014.1.korea.pdf ../pages

NDL 자료는 IIIF에서 면을 낱장으로 받았지만(`ndl_download.py`) 이 자료는 손에 PDF만
있다. 그 자리만 바꿔 끼우는 것이고, 다음 단계(OCR·분할·번역)는 NDL과 같다.

원본이 1658×2339(약 200dpi)라 그대로 뽑는다. NDL에서 폭 1600으로 줄여도 타자기
문서가 충분히 읽혔으므로 더 키울 이유가 없다.
"""
import os
import sys

import fitz

SRC = sys.argv[1] if len(sys.argv) > 1 else "../014.1.korea.pdf"
OUT = sys.argv[2] if len(sys.argv) > 2 else "../pages"

os.makedirs(OUT, exist_ok=True)
doc = fitz.open(SRC)

done = 0
for i, page in enumerate(doc, 1):
    dst = os.path.join(OUT, f"{i:04d}.jpg")
    if os.path.exists(dst) and os.path.getsize(dst) > 5000:
        continue
    # 200dpi 로 굳힌다. 면마다 원본 해상도가 다를 수 있어 배율이 아니라 dpi 로 준다.
    pix = page.get_pixmap(dpi=200)
    pix.save(dst, jpg_quality=88)
    done += 1
    if done % 20 == 0:
        print(f"  {i}/{len(doc)}면")

have = len([f for f in os.listdir(OUT) if f.endswith(".jpg")])
size = sum(os.path.getsize(os.path.join(OUT, f)) for f in os.listdir(OUT)) / 1e6
print(f"{have}/{len(doc)}면 (이번에 {done}장) · {size:.0f}MB -> {OUT}/")
