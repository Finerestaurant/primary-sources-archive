"""글자표를 눈으로 읽을 수 있게 판으로 펴 놓는다.

`inventory.py` 가 오려 낸 글리프 그림을 10×10 격자로 붙여 큰 그림 한 장을 만든다.
칸마다 번호를 달아 두므로, 읽은 결과를 `번호: 글자` 로 받아 적으면 그대로 표가 된다.

  판 하나 = 100자. 1,746종이면 18장. 444면 3,654종이면 37장.
  이걸 한 번 읽으면 376,831자가 풀린다.

잦은 것부터 앞에 놓는다. 앞 판 몇 장만 읽어도 본문 대부분이 살아난다.

    python3 sheets.py ../glyphs/s03 ../glyphs/s03/sheets
"""
import sys, os, json
import numpy as np
from PIL import Image, ImageDraw, ImageFont

COLS, ROWS = 10, 10
CELL, LABEL, PAD = 96, 22, 6
MONO = "/System/Library/Fonts/Menlo.ttc"


def fit(arr, box):
    """오려 낸 그림을 칸에 맞춘다. 비율은 지킨다 — 찌그러지면 못 읽는다."""
    im = Image.fromarray(arr).convert("L")
    w, h = im.size
    s = min(box / max(1, w), box / max(1, h))
    im = im.resize((max(1, int(w * s)), max(1, int(h * s))), Image.LANCZOS)
    c = Image.new("L", (box, box), 255)
    c.paste(im, ((box - im.width) // 2, (box - im.height) // 2))
    return c


def main(argv):
    src, out = argv[1], argv[2]
    idx = json.load(open(os.path.join(src, "index.json")))
    items = sorted(idx["glyphs"].items(), key=lambda kv: -kv[1]["n"])
    # --new: 이미 읽어 둔 글자는 건너뛴다. 절이 늘어도 새 글자만 읽으면 된다
    if "--new" in argv:
        known = json.load(open(argv[argv.index("--new") + 1]))
        items = [kv for kv in items if kv[0] not in known]
    os.makedirs(out, exist_ok=True)
    try:
        font = ImageFont.truetype(MONO, 13)
    except Exception:
        font = ImageFont.load_default()

    per = COLS * ROWS
    order = []
    for n in range(0, len(items), per):
        chunk = items[n:n + per]
        W = COLS * (CELL + PAD) + PAD
        H = ROWS * (CELL + LABEL + PAD) + PAD + 24
        sheet = Image.new("L", (W, H), 255)
        dr = ImageDraw.Draw(sheet)
        dr.text((PAD, 6), f"sheet {n // per:02d}   #{n:04d}-{n + len(chunk) - 1:04d}",
                fill=90, font=font)
        for i, (h, e) in enumerate(chunk):
            r, c = divmod(i, COLS)
            x = PAD + c * (CELL + PAD)
            y = 24 + PAD + r * (CELL + LABEL + PAD)
            p = os.path.join(src, "crops", h + ".npy")
            if os.path.exists(p):
                sheet.paste(fit(np.load(p), CELL), (x, y))
            dr.rectangle([x - 1, y - 1, x + CELL, y + CELL], outline=205)
            dr.text((x + 2, y + CELL + 4), "%04d" % (n + i), fill=60, font=font)
            order.append(h)
        sheet.save(os.path.join(out, "sheet%02d.png" % (n // per)))
    json.dump(order, open(os.path.join(out, "order.json"), "w"))
    print(f"{len(items)}종 → 판 {(len(items) + per - 1) // per}장  {out}")


if __name__ == "__main__":
    main(sys.argv)
