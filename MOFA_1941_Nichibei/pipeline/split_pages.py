"""펼침면 PDF → 한 쪽씩 이미지.

    python3 split_pages.py ../raw/nichibei2_05.pdf ../pages

이 자료는 **스캔 이미지**다. 『종전사록』처럼 글꼴이 박혀 있지 않아 글자표가
통하지 않고, tesseract 세로쓰기 모델은 82%에서 막힌다. 그래서 지면을 그대로
읽히는 길로 간다 — 그러려면 사람이 읽는 단위, 곧 **한 쪽씩** 잘라야 한다.

일본어 책은 오른쪽에서 왼쪽으로 읽는다. 펼침면의 오른쪽이 먼저다.
파일 이름의 번호가 곧 읽는 순서가 되게 붙인다.
"""
import sys, os, fitz

src, out = sys.argv[1], sys.argv[2]
DPI = int(sys.argv[3]) if len(sys.argv) > 3 else 300
tag = os.path.basename(src).replace(".pdf", "")
os.makedirs(out, exist_ok=True)

doc = fitz.open(src)
n = 0
for i, pg in enumerate(doc):
    pix = pg.get_pixmap(dpi=DPI)
    w, h = pix.width, pix.height
    if w > h * 1.25:                      # 펼침면이면 가른다
        for half, x0 in (("R", w // 2), ("L", 0)):   # 오른쪽이 먼저
            n += 1
            clip = fitz.Rect(x0 * 72 / DPI, 0, (x0 + w // 2) * 72 / DPI, h * 72 / DPI)
            pg.get_pixmap(dpi=DPI, clip=clip).save(
                os.path.join(out, f"{tag}_{n:03d}.png"))
    else:
        n += 1
        pix.save(os.path.join(out, f"{tag}_{n:03d}.png"))
print(f"{doc.page_count}면 → {n}쪽  {out}/{tag}_*.png")
