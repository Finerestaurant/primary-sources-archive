"""글자표를 만든다 — 한 번 읽으면 그 뒤로는 공짜다.

PDF 안의 글자는 익명이지만 **반복된다.** 37면에 33,848자가 있어도
서로 다른 글리프는 1,746종뿐이다. 그러니 글리프마다 한 번씩만 정체를
확인해 두면, 나머지는 표를 찾아 붙이기만 하면 된다. 444면이든 4,440면이든
비용이 늘지 않는다.

  1. 모든 글자를 훑어 글리프 그림을 해시로 묶는다 (같은 그림 = 같은 글자)
  2. 종마다 **지면에서 처음 나온 자리**를 기억해 둔다
  3. 그 자리를 지면에서 오려 낸다 — 눕지 않은, 사람이 읽는 그대로의 모습
  4. ヒラギノ明朝 모양 맞추기로 후보를 하나 달아 둔다

그림 회전을 추측하지 않는 것이 요령이다. 조판기는 글리프를 눕혀 저장했지만
**지면은 바로 서 있다.** 지면에서 오려 내면 방향 문제가 아예 없어진다.

    python3 inventory.py ../raw/taiheiyo3_03.pdf ../glyphs/s03
"""
import sys, os, json, hashlib, glob
import numpy as np, freetype, fitz

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from glyphmap import _feat, _wanted, REF

EM, CAN, X0 = 48, 64, 8
BASE = X0 + int(round(0.88 * EM))
CROP_DPI = 300


def em_draw(face, gid):
    """글리프를 전각 상자 자리 그대로 그린다 (해시용 — 회전은 건드리지 않는다)."""
    face.load_glyph(gid, freetype.FT_LOAD_RENDER)
    b = face.glyph.bitmap
    a = np.zeros((CAN, CAN), np.uint8)
    if b.rows and b.width:
        g = np.array(b.buffer, np.uint8).reshape(b.rows, b.pitch)[:, :b.width]
        y, x = BASE - face.glyph.bitmap_top, X0 + face.glyph.bitmap_left
        y0, x0 = max(0, y), max(0, x)
        y1, x1 = min(CAN, y + b.rows), min(CAN, x + b.width)
        if y1 > y0 and x1 > x0:
            a[y0:y1, x0:x1] = g[y0 - y:y1 - y, x0 - x:x1 - x]
    return a


def uniquify_fonts(path):
    """부분집합 글꼴이 이름을 나눠 쓴다. 이름이 겹치면 엉뚱한 글꼴로 읽게 된다."""
    d = fitz.open(path)
    for x in range(1, d.xref_length()):
        if d.xref_get_key(x, "Type")[1] == "/Font" and d.xref_get_key(x, "BaseFont")[0] != "null":
            d.xref_set_key(x, "BaseFont", "/X%d" % x)
    tmp = "/tmp/_uniq_%s" % os.path.basename(path)
    d.save(tmp)
    return fitz.open(tmp)


def scan(path, store):
    doc = uniquify_fonts(path)
    faces, seen = {}, store["glyphs"]
    tag = os.path.basename(path).replace(".pdf", "")
    for pi in range(len(doc)):
        page = doc[pi]
        for f in page.get_fonts(full=True):
            nm = f[3].split("+")[-1]
            if nm in faces:
                continue
            try:
                _, ext, _, buf = doc.extract_font(f[0], info_only=False)
                fp = "/tmp/_cff_%s_%s.cff" % (tag, nm)
                open(fp, "wb").write(buf)
                fa = freetype.Face(fp)
                fa.set_char_size(EM * 64)
                faces[nm] = fa
            except Exception:
                faces[nm] = None
        for b in page.get_text("rawdict")["blocks"]:
            for l in b.get("lines", []):
                vert = abs(l.get("dir", (1, 0))[1]) > 0.5
                for s in l["spans"]:
                    fa = faces.get(s["font"])
                    if fa is None:
                        continue
                    for c in s["chars"]:
                        code = ord(c["c"])
                        if code >= fa.num_glyphs:
                            continue
                        h = hashlib.md5(em_draw(fa, code).tobytes()).hexdigest()[:16]
                        e = seen.get(h)
                        if e is None:
                            seen[h] = {"n": 1, "pdf": tag, "page": pi, "v": vert,
                                       "bbox": [round(v, 2) for v in c["bbox"]]}
                        else:
                            e["n"] += 1
                        store["codes"].setdefault(tag, {}).setdefault(s["font"], {})[code] = h
    return doc


def crop_samples(store, docs, outdir):
    """종마다 처음 나온 자리를 지면에서 오려 낸다."""
    os.makedirs(outdir, exist_ok=True)
    m = CROP_DPI / 72
    by_page = {}
    for h, e in store["glyphs"].items():
        by_page.setdefault((e["pdf"], e["page"]), []).append((h, e["bbox"], e.get("v")))
    for (tag, pi), items in by_page.items():
        page = docs[tag][pi]
        pix = page.get_pixmap(matrix=fitz.Matrix(m, m))
        img = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width, pix.n)
        for h, bb, vert in items:
            x0, y0, x1, y1 = [int(round(v * m)) for v in bb]
            # 세로줄에서는 글자 칸이 잉크보다 한 뼘 아래로 잡힌다. 올려 준다 —
            # 안 그러면 아래 글자의 윗머리가 들어와 平 을 半 으로 보게 된다.
            if vert:
                dy = int(round((y1 - y0) * 0.14))
                y0 -= dy; y1 -= dy
            # 세로쓰기 자리는 글자 하나보다 길게 잡히는 일이 있다. 길면 정사각으로
            # 가운데를 도려낸다 — 안 그러면 아래 글자를 물고 와서 잘못 읽는다.
            w, hgt = x1 - x0, y1 - y0
            if hgt > w * 1.15:
                cy = (y0 + y1) // 2
                y0, y1 = cy - w // 2, cy + (w + 1) // 2
            elif w > hgt * 1.15:
                cx = (x0 + x1) // 2
                x0, x1 = cx - hgt // 2, cx + (hgt + 1) // 2
            # 안쪽으로 조금 깎는다. 칸이 정확해도 이웃 글자의 윗머리가 아래에
            # 걸쳐 들어와서, 판을 읽을 때 平 을 半 으로 보게 만든다.
            ins = max(1, int(round((x1 - x0) * 0.06)))
            crop = img[y0 + ins:y1 - ins, x0 + ins:x1 - ins, :3]
            if crop.size:
                np.save(os.path.join(outdir, h + ".npy"), crop)


def main(argv):
    pdfs, out = argv[1:-1], argv[-1]
    store = {"glyphs": {}, "codes": {}}
    docs = {}
    for p in pdfs:
        for q in sorted(glob.glob(p)):
            print("  훑는 중", os.path.basename(q), flush=True)
            docs[os.path.basename(q).replace(".pdf", "")] = scan(q, store)
    os.makedirs(out, exist_ok=True)
    crop_samples(store, docs, os.path.join(out, "crops"))
    json.dump(store, open(os.path.join(out, "index.json"), "w"), ensure_ascii=False)
    tot = sum(e["n"] for e in store["glyphs"].values())
    print(f"{tot}자 · 고유 글리프 {len(store['glyphs'])}종 → {out}")


if __name__ == "__main__":
    main(sys.argv)
