"""글자표로 지면을 원문 텍스트로 되살린다.

    python3 decode.py ../raw/taiheiyo3_03.pdf ../glyphs/s03 ../text/s03.json

`inventory.py` 가 만든 글리프 표를 붙이기만 하면 되므로 판독이 아니라 조회다.
남은 일은 **읽는 순서**뿐이다. 세로쓰기 지면이라 세 겹으로 정렬한다.

    단(段) → 세로줄 → 글자

한 면이 가운데 가로줄로 위아래 두 단으로 갈리는 곳이 있다. 그 줄은 글자가
아니라 그림이라, 글자 좌표만 봐서는 안 보인다. 그래서 지면의 도형에서
가로줄을 찾아 단을 가른다 — 못 찾으면 한 단으로 본다.

표에 없는 글리프는 `□` 로 남긴다. 틀린 글자를 채워 넣는 것보다 낫다.
"""
import sys, os, json, hashlib
import numpy as np, freetype, fitz

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from inventory import em_draw, uniquify_fonts, EM

MISS = "□"


def _spaces(chars, horiz):
    """띄어쓰기 자리를 찾는다.

    영문의 낱말 사이가 **아주 좁은 글리프**로 들어 있다. 글꼴 부분집합마다
    그 글리프가 따로라 표로 잡을 수가 없고, 모양으로 맞추면 획이 없어 아무거나
    걸린다. 그대로 뽑으면 `Declarationdoesnotcomprise` 가 된다.

    그래서 **폭으로 가른다.** 한 줄 안에서 글자 하나가 차지하는 자리를 재어,
    그 절반에도 못 미치는 것은 띄어쓰기로 본다. 세로줄에서는 위아래 길이를,
    가로줄에서는 좌우 길이를 잰다."""
    a, b = (0, 2) if horiz else (1, 3)
    adv = sorted(c["bbox"][b] - c["bbox"][a] for c in chars)
    if not adv:
        return set()
    unit = adv[len(adv) // 2]
    if unit <= 0:
        return set()
    return {i for i, c in enumerate(chars)
            if c["bbox"][b] - c["bbox"][a] < unit * 0.5}


class Decoder:
    def __init__(self, pdf, glyphdir):
        self.doc = uniquify_fonts(pdf)
        self.tbl = json.load(open(os.path.join(glyphdir, "table.json")))
        self.faces = {}
        self.miss = 0
        self.total = 0

    def _face(self, page, nm):
        if nm not in self.faces:
            self.faces[nm] = None
            for f in page.get_fonts(full=True):
                if f[3].split("+")[-1] == nm:
                    _, ext, _, buf = self.doc.extract_font(f[0], info_only=False)
                    p = "/tmp/_dec_%s.cff" % nm
                    open(p, "wb").write(buf)
                    fa = freetype.Face(p)
                    fa.set_char_size(EM * 64)
                    self.faces[nm] = fa
                    break
        return self.faces[nm]

    def _bands(self, page, spans):
        """가운데 가로줄을 찾아 위아래 단을 가른다."""
        cuts = []
        for d in page.get_drawings():
            r = d["rect"]
            if r.width > page.rect.width * 0.5 and r.height < 3:
                cuts.append(r.y0)
        h = page.rect.height
        cuts = sorted(c for c in cuts if h * 0.2 < c < h * 0.8)
        if not cuts:
            return [spans]
        c = cuts[len(cuts) // 2]
        return [[s for s in spans if s["y"] < c], [s for s in spans if s["y"] >= c]]

    @staticmethod
    def _columns(spans, gap=5.0):
        """세로줄을 묶는다. 행간에 끼워 넣은 글자는 본줄보다 0.7pt 쯤 왼쪽에
        앉는데, 자리를 반올림으로 나누면 그 글자만 딴 줄로 떨어져 나간다 —
        「日本擊滅ニ邁進」 이 「日本滅ニ邁」 와 「擊進」 으로 갈라졌다.
        그래서 반올림하지 말고 가까운 것끼리 모은다."""
        cols, cur = {}, []
        for s in sorted(spans, key=lambda s: s["x"]):
            if cur and s["x"] - cur[-1]["x"] > gap:
                cols[sum(t["x"] for t in cur) / len(cur)] = cur
                cur = []
            cur.append(s)
        if cur:
            cols[sum(t["x"] for t in cur) / len(cur)] = cur
        return cols

    def page(self, i):
        p = self.doc[i]
        spans = []
        for b in p.get_text("rawdict")["blocks"]:
            for l in b.get("lines", []):
                horiz = abs(l.get("dir", (1, 0))[0]) > 0.5
                for s in l["spans"]:
                    # 쪽머리와 쪽번호만 걷어낸다. 크기로 자르면 안 된다 —
                    # 발신·수신·발착 시각이 8pt 라서 문서의 머리가 통째로 날아간다.
                    y0, y1 = s["bbox"][1], s["bbox"][3]
                    if horiz and (y0 < 46 or y1 > p.rect.height - 50):
                        continue
                    spans.append({"x": s["bbox"][0], "y": s["bbox"][1],
                                  "f": s["font"], "c": [ord(c["c"]) for c in s["chars"]],
                                  "g": _spaces(s["chars"], horiz)})
        if not spans:
            return ""
        out = []
        for band in self._bands(p, spans):
            cols = self._columns(band)
            for x in sorted(cols, reverse=True):           # 오른쪽 줄부터
                buf = ""
                for s in sorted(cols[x], key=lambda s: s["y"]):
                    fa = self._face(p, s["f"])
                    for i, code in enumerate(s["c"]):
                        self.total += 1
                        if i in s["g"]:              # 폭이 좁으면 띄어쓰기다
                            if not buf.endswith(" "):
                                buf += " "
                            continue
                        if fa is None or code >= fa.num_glyphs:
                            buf += MISS; self.miss += 1; continue
                        h = hashlib.md5(em_draw(fa, code).tobytes()).hexdigest()[:16]
                        ch = self.tbl.get(h)
                        if ch is None:
                            buf += MISS; self.miss += 1
                        else:
                            buf += ch
                if buf.strip():
                    out.append(buf)
        return "\n".join(out)


def main(argv):
    pdf, gdir, out = argv[1], argv[2], argv[3]
    d = Decoder(pdf, gdir)
    pages = [{"page": i + 1, "text": d.page(i)} for i in range(len(d.doc))]
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    json.dump({"pdf": os.path.basename(pdf), "pages": pages}, open(out, "w"),
              ensure_ascii=False, indent=1)
    print(f"{len(pages)}면 · {d.total}자 · 모르는 글자 {d.miss} "
          f"({d.miss / max(1, d.total) * 100:.2f}%) → {out}")


if __name__ == "__main__":
    main(sys.argv)
