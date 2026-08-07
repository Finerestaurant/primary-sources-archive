"""지면 이미지를 줄인다. 문서철마다 제각각인 크기를 하나로 맞춘다.

    python3 열람기/shrink_pages.py --dry        # 얼마나 주는지만 센다
    python3 열람기/shrink_pages.py              # 실제로 줄인다
    python3 열람기/shrink_pages.py 014.1.korea  # 한 문서철만

## 왜 필요한가

같은 종류의 지면인데 문서철마다 면당 크기가 다섯 배까지 벌어져 있었다.
그때그때 다른 도구로 받았기 때문이지 뜻이 있어서가 아니다.

    014.1.korea       1650x2334  JPEG  542KB/면
    MOFA_1945_Shusen  1167x1653  PNG   418KB/면   ← 스캔을 PNG 로 갖고 있다
    CREST_1945        1105x1430  JPEG  159KB/면   ← 맞추려는 기준
    KOREA_1950_53      499x800   PNG   127KB/면

**PNG 는 스캔에 안 맞는다.** 글자와 도형에는 좋은데 종이 결이 있는 지면은
JPEG 이 훨씬 작다. 화면에서 긴 변 1600 을 넘게 볼 일도 없다.

GitHub Pages 산출물 한도가 1GB 인데 스캔이 사이트의 대부분이다. 줄이면
184MB 를 벌어 새 문서철의 지면을 받을 자리가 생긴다.

## 원본을 잃는 것 아닌가

**되받을 수 있다.** NDL 과 CREST 에서 받은 것이고 도구가 저장소에 있다
(`조사/도구/`, `CREST_1945/pipeline/fetch_scans.py`). 나중에 더 좋은 화질이
필요하면 다시 받으면 된다. 지금 필요한 것은 **읽히는 지면**이다.

## 줄지 않는 것은 건너뛴다

이미 이 기준으로 받아 둔 문서철(`CREST_1945`)을 다시 인코딩하면 **오히려
커진다.** 품질 72 로 저장한 것을 75 로 다시 저장하는 셈이라 그렇다.
그래서 표본으로 어림해 보고 줄지 않으면 손대지 않는다.

## 품질을 문서철마다 다르게 잡는 까닭

`014.1.korea` 는 국립국회도서관이 **사진으로 찍은 것**이라 종이 결과 그림자가
있어 낮은 품질에서 눈에 띄게 뭉갠다. 그래서 그것만 80 으로 둔다.
나머지는 마이크로필름이나 인쇄물 스캔이라 75 로 충분하다.
"""
import glob
import json
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

CAP = 1600          # 긴 변. 이보다 크면 줄이고, 작으면 그대로 둔다
Q = 75              # 품질
Q_BY = {"014.1.korea": 80,          # 사진으로 찍은 것은 높게
        "NDL_점령기자료/pid_9850431": 82}   # 펼침면이라 한 쪽이 800px 뿐이다


def page_dirs():
    """지면 폴더를 찾는다. **한 겹 깊은 곳도 본다.**

    처음엔 `*/pages` 만 훑었는데 `NDL_점령기자료/pid_9850431/pages` 가 통째로
    빠졌다. 그 하나가 277MB, 사이트의 사분의 일이었다. 문서철이 한 기관 밑에
    여럿 들어앉는 꼴이 앞으로 더 생기니 두 겹까지 훑는다.

    `_site` 는 뺀다. 지어 낸 것이라 여기서 줄여 봐야 다음 빌드에 덮인다."""
    d = (glob.glob(os.path.join(ROOT, "*", "pages"))
         + glob.glob(os.path.join(ROOT, "*", "*", "pages")))
    return sorted(p for p in d
                  if not os.path.relpath(p, ROOT).startswith(("_", ".")))


def shrink(src, dst, q):
    im = Image.open(src)
    w, h = im.size
    if max(w, h) > CAP:
        r = CAP / max(w, h)
        im = im.resize((int(w * r), int(h * r)), Image.LANCZOS)
    im.convert("RGB").save(dst, "JPEG", quality=q, optimize=True, progressive=True)


def main(only=None, dry=False):
    tot_o = tot_n = 0
    for pd in page_dirs():
        home = os.path.dirname(pd)                       # 문서철 폴더
        coll = os.path.relpath(home, ROOT)               # 두 겹이면 두 겹째까지
        if only and coll not in only:
            continue
        files = sorted(glob.glob(os.path.join(pd, "*")))
        if not files:
            continue
        q = Q_BY.get(coll, Q)
        o = sum(os.path.getsize(f) for f in files)

        # 먼저 표본으로 어림해 본다. 줄지 않으면 손대지 않는다.
        # **앞에서 다섯 장을 뽑으면 안 된다.** 앞머리는 표지와 백지라 가볍고,
        # 그래서 MOFA_1941_Nichibei 를 20.9MB→16.1MB 로 잘못 어림해 헛되이
        # 다시 인코딩했다. 문서철 전체에 고르게 흩어 뽑는다.
        import io
        k = min(9, len(files))
        s = [files[i * (len(files) - 1) // max(k - 1, 1)] for i in range(k)]
        est = 0
        for f in s:
            im = Image.open(f)
            w, h = im.size
            if max(w, h) > CAP:
                r = CAP / max(w, h)
                im = im.resize((int(w * r), int(h * r)), Image.LANCZOS)
            b = io.BytesIO()
            im.convert("RGB").save(b, "JPEG", quality=q, optimize=True,
                                   progressive=True)
            est += len(b.getvalue())
        guess = est / len(s) * len(files)
        if guess >= o * 0.95:
            print(f"  {coll:22} {len(files):>4}면  {o/1e6:>6.1f}MB  건너뛴다"
                  f" (줄지 않는다)")
            tot_o += o
            tot_n += o
            continue

        if dry:
            n = guess
        else:
            for f in files:
                dst = os.path.splitext(f)[0] + ".jpg"
                shrink(f, dst, q)
                if dst != f:
                    os.remove(f)
            n = sum(os.path.getsize(f)
                    for f in glob.glob(os.path.join(pd, "*")))
            # 확장자가 바뀌었으면 규격에도 알려야 한다
            cj = os.path.join(home, "reading", "collection.json")
            if os.path.exists(cj):
                c = json.load(open(cj))
                if (c.get("pages") or {}).get("ext") != "jpg":
                    c["pages"]["ext"] = "jpg"
                    json.dump(c, open(cj, "w"), ensure_ascii=False, indent=1)
        tot_o += o
        tot_n += n
        print(f"  {coll:22} {len(files):>4}면  {o/1e6:>6.1f}MB → {n/1e6:>6.1f}MB"
              f"  (q{q})")
    print(f"\n합계 {tot_o/1e6:.0f}MB → {tot_n/1e6:.0f}MB · {(tot_o-tot_n)/1e6:.0f}MB 절약"
          + ("  (어림)" if dry else ""))
    if not dry:
        print("문서철을 다시 지어라 — make_docs 는 손댈 것이 없고 build.py 만 다시 돌리면 된다.")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    main(only=args or None, dry="--dry" in sys.argv)
