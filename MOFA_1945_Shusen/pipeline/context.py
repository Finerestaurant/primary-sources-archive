"""아직 모르는 글리프를 **앞뒤 글자와 함께** 오려 판으로 만든다.

글자 하나만 떼어 보면 判 인지 剃 인지 못 가른다. 그런데 「大量輸送」 처럼
앞뒤가 붙어 있으면 한눈에 읽힌다. 그래서 세로줄에서 위아래 두 글자씩,
다섯 글자 띠를 오려 낸다. 가운데가 찾는 글자다.

    python3 context.py ../glyphs/s03 ../glyphs/s03/ctx
"""
import sys, os, json, hashlib
import numpy as np, freetype, fitz
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from inventory import em_draw, uniquify_fonts, EM

DPI, N = 260, 2          # 위아래로 몇 글자까지 함께 볼 것인가
COLS, ROWS = 8, 4


def main(argv):
    src, out = argv[1], argv[2]
    idx = json.load(open(os.path.join(src, "index.json")))
    tbl = json.load(open(os.path.join(src, "table.json")))
    order = json.load(open(os.path.join(src, "sheets", "order.json")))
    want = [(i, h) for i, h in enumerate(order) if h not in tbl]
    pdf = "../raw/%s.pdf" % list(idx["codes"])[0]
    doc = uniquify_fonts(pdf)
    faces = {}
    m = DPI / 72

    # 어느 글자가 어느 자리에 있는지 다시 훑어, 찾는 글리프의 이웃까지 잡는다
    spots = {}
    for pi in range(len(doc)):
        page = doc[pi]
        for f in page.get_fonts(full=True):
            nm = f[3].split("+")[-1]
            if nm not in faces:
                _, e, _, buf = doc.extract_font(f[0], info_only=False)
                fp = "/tmp/ctx_%s.cff" % nm
                open(fp, "wb").write(buf)
                fa = freetype.Face(fp); fa.set_char_size(EM * 64); faces[nm] = fa
        for b in page.get_text("rawdict")["blocks"]:
            for l in b.get("lines", []):
                for s in l["spans"]:
                    fa = faces.get(s["font"])
                    if fa is None: continue
                    cs = s["chars"]
                    for k, c in enumerate(cs):
                        code = ord(c["c"])
                        if code >= fa.num_glyphs: continue
                        h = hashlib.md5(em_draw(fa, code).tobytes()).hexdigest()[:16]
                        if h in tbl or h in spots: continue
                        lo, hi = max(0, k - N), min(len(cs), k + N + 1)
                        bb = [min(cs[j]["bbox"][0] for j in range(lo, hi)),
                              min(cs[j]["bbox"][1] for j in range(lo, hi)),
                              max(cs[j]["bbox"][2] for j in range(lo, hi)),
                              max(cs[j]["bbox"][3] for j in range(lo, hi))]
                        spots[h] = (pi, bb, c["bbox"])

    os.makedirs(out, exist_ok=True)
    try: font = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 13)
    except Exception: font = ImageFont.load_default()
    CW, CH = 120, 200
    per = COLS * ROWS
    kept = [(i, h) for i, h in want if h in spots]
    for n in range(0, len(kept), per):
        chunk = kept[n:n + per]
        W = COLS * (CW + 8) + 8
        Hh = ROWS * (CH + 20) + 30
        sh = Image.new("RGB", (W, Hh), "white")
        dr = ImageDraw.Draw(sh)
        dr.text((8, 8), "ctx %02d" % (n // per), fill=(90, 90, 90), font=font)
        for j, (i, h) in enumerate(chunk):
            r, c = divmod(j, COLS)
            x = 8 + c * (CW + 8); y = 30 + r * (CH + 20)
            pi, bb, tb = spots[h]
            pix = doc[pi].get_pixmap(clip=fitz.Rect(*bb), matrix=fitz.Matrix(m, m))
            im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            s = min(CW / im.width, CH / im.height)
            im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))))
            ox, oy = x + (CW - im.width) // 2, y + (CH - im.height) // 2
            sh.paste(im, (ox, oy))
            # 찾는 글자에 테두리
            rx0 = ox + (tb[0] - bb[0]) * m * s; ry0 = oy + (tb[1] - bb[1]) * m * s
            rx1 = ox + (tb[2] - bb[0]) * m * s; ry1 = oy + (tb[3] - bb[1]) * m * s
            dr.rectangle([rx0, ry0, rx1, ry1], outline=(210, 60, 60), width=2)
            dr.text((x + 2, y + CH + 3), "%04d" % i, fill=(60, 60, 60), font=font)
        sh.save(os.path.join(out, "ctx%02d.png" % (n // per)))
    json.dump([i for i, h in kept], open(os.path.join(out, "order.json"), "w"))
    print(f"모르는 {len(want)}종 중 {len(kept)}종 → 판 {(len(kept)+per-1)//per}장")


if __name__ == "__main__":
    main(sys.argv)
