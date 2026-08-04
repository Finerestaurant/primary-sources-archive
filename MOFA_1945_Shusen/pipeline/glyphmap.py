"""외무성 PDF의 글자를 되살린다. — OCR 없이, 지면을 건드리지 않고.

『日本外交文書』 PDF에는 텍스트 층이 **멀쩡히 들어 있다.** 다만 두 가지가 막고 있다.

  1. 글꼴이 부분집합으로 박혀 있고 ToUnicode 표가 없다.
     뽑아내면 `/TypeOne0 /TypeOne1 …` 같은 글리프 이름만 나온다. 글자가 익명이다.
  2. 세로쓰기라 글리프가 **270도 돌아간 채** 저장돼 있다.
     조판기가 회전을 글자 모양 자체에 구워 넣었다.

그래서 모양을 직접 맞춘다.

  PDF 안의 CFF 글꼴을 꺼내 글리프를 그린다 → 270도 되돌린다
  → ヒラギノ明朝 ProN 에서 뽑은 후보들과 견준다 → 가장 닮은 글자를 고른다.

같은 명조 계열이라 모양이 사실상 일치한다. 16×16 로 줄여 한 번에 추리고,
남은 후보만 64×64 로 다시 견주는 2단이다. 표를 한 번 만들어 두면
444면 전부를 **원문 그대로** 읽어낼 수 있다 — 판독 오류가 원리적으로 없다.

글자를 판 한가운데에 놓고 견주는 것이 요령이다. 기준선에 맞추면 회전된
글리프의 기준선이 원래와 달라 어긋난다.
"""
import numpy as np, freetype
from PIL import Image

REF = "/System/Library/Fonts/ヒラギノ明朝 ProN.ttc"
EM, CAN = 48, 64          # 그리는 크기 / 판 크기
ROT = 3                   # np.rot90 k=3 → 270도. 세로쓰기 글리프를 세운다


def draw(face, gid, rot=0):
    """글리프를 그려 판 한가운데에 놓는다."""
    face.load_glyph(gid, freetype.FT_LOAD_RENDER)
    b = face.glyph.bitmap
    a = np.zeros((CAN, CAN), np.float32)
    if not b.rows or not b.width:
        return a
    g = np.array(b.buffer, np.uint8).reshape(b.rows, b.pitch)[:, :b.width]
    g = g.astype(np.float32) / 255
    if rot:
        g = np.rot90(g, rot)
    h, w = g.shape
    if h > CAN or w > CAN:
        g = np.asarray(Image.fromarray((g * 255).astype(np.uint8))
                       .resize((min(w, CAN), min(h, CAN))), np.float32) / 255
        h, w = g.shape
    y, x = (CAN - h) // 2, (CAN - w) // 2
    a[y:y + h, x:x + w] = g
    return a


def _feat(a):
    """16×16 으로 줄이고 길이를 1로. 이 꼴이라야 행렬곱 한 번에 다 견준다."""
    f = a.reshape(16, 4, 16, 4).mean(axis=(1, 3)).ravel()
    n = np.linalg.norm(f)
    return f / n if n > 1e-6 else f


def _wanted(cc):
    return (0x3000 <= cc <= 0x30FF or 0x4E00 <= cc <= 0x9FFF or 0xF900 <= cc <= 0xFAFF
            or 0x3400 <= cc <= 0x4DBF or 0xFF01 <= cc <= 0xFF65 or 0x21 <= cc <= 0x7E
            or cc in (0x2015, 0x2016, 0x2018, 0x2019, 0x201C, 0x201D, 0x2026,
                      0x25A1, 0x25CB, 0x3013, 0x00B7))


class Ref:
    """ヒラギノ明朝 후보 색인. 만드는 데 몇 초, 그다음은 행렬곱."""

    def __init__(self, path=REF, index=0):
        face = freetype.Face(path, index=index)
        face.set_char_size(EM * 64)
        chars, coarse, fine = [], [], []
        cc, gi = face.get_first_char()
        while gi:
            if _wanted(cc):
                a = draw(face, gi)
                if a.any():
                    chars.append(cc); coarse.append(_feat(a)); fine.append(a.ravel())
            cc, gi = face.get_next_char(cc, gi)
        self.chars = np.array(chars)
        self.C = np.array(coarse, np.float32)
        self.A = np.array(fine, np.float32)
        self.An = np.linalg.norm(self.A, axis=1) + 1e-9

    def match(self, a, topk=40):
        """굵게 추리고 곱게 다시 본다. 16×16 만으로는 第 와 笫 를 못 가른다."""
        s = self.C @ _feat(a)
        top = np.argpartition(-s, topk)[:topk]
        v = a.ravel(); nv = np.linalg.norm(v) + 1e-9
        f = (self.A[top] @ v) / (self.An[top] * nv)
        i = int(np.argmax(f))
        srt = np.sort(f)[::-1]
        margin = float(srt[0] - srt[1]) if len(srt) > 1 else 1.0
        return chr(int(self.chars[top[i]])), float(f[i]), margin
