"""원본 지면 스캔 받기.

    python3 frus_scans.py

`frus_fetch.py` 는 pages.json 에 **스캔 파일 번호(facs)** 를 적어 둔다. 그런데
본문에는 `[448면]` 처럼 **인쇄 쪽번호**가 찍힌다. 둘이 다르면 읽는 사람이
"448면을 보라"는 각주를 따라갔을 때 엉뚱한 장이 열린다.

그래서 여기서 두 가지를 한꺼번에 한다.

  1. pages.json 을 인쇄 쪽번호로 바꾼다 (TEI 의 `<pb facs="0460" n="448"/>` 가 짝)
  2. 내려받을 때만 facs 번호로 주소를 만들고, **파일은 인쇄 쪽번호로 저장한다**

인쇄 쪽번호가 없는 면(로마숫자 앞머리 등)은 건너뛴다 — 이름 붙일 수가 없다.
"""
import json
import os
import re
import sys
import time
import urllib.request

VOL = "frus1945v03"
IMG = f"https://static.history.state.gov/frus/{VOL}/medium/{{}}.png"
UA = {"User-Agent": "Mozilla/5.0 (research; personal use)"}

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RAW = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "raw")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "pages")

os.makedirs(OUT, exist_ok=True)

# facs ↔ 인쇄 쪽번호
xml = open(os.path.join(RAW, f"{VOL}.xml"), encoding="utf-8").read()
f2n, n2f = {}, {}
for m in re.finditer(r'<pb[^>]*facs="(\d+)"[^>]*n="([^"]+)"', xml):
    facs, n = m.group(1), m.group(2)
    if n.isdigit():
        f2n.setdefault(facs, n)
        n2f.setdefault(n, facs)
print(f"짝 {len(f2n)}쌍")

# pages.json 을 인쇄 쪽번호로 바꾼다
pages = json.load(open(os.path.join(RAW, "pages.json")))
fixed, lost = {}, 0
for did, facs in pages.items():
    out = []
    for f in facs:
        n = f2n.get(str(f).zfill(4)) or f2n.get(str(f))
        if n:
            if n not in out:
                out.append(n)
        else:
            lost += 1
    fixed[did] = out
json.dump(fixed, open(os.path.join(RAW, "pages.json"), "w"),
          ensure_ascii=False, indent=1)
print(f"pages.json 을 인쇄 쪽번호로 바꿨다 · 짝 못 찾은 면 {lost}장")

want = sorted({p for v in fixed.values() for p in v}, key=int)
print(f"면 {len(want)}장 (문서 {len(fixed)}건)")

got = skip = fail = 0
for i, n in enumerate(want, 1):
    dst = os.path.join(OUT, f"{n}.png")
    if os.path.exists(dst) and os.path.getsize(dst) > 5000:
        skip += 1
        continue
    facs = n2f.get(n)
    if not facs:
        fail += 1
        continue
    url = IMG.format(facs.zfill(4))
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=120) as r:
            open(dst, "wb").write(r.read())
        got += 1
        if got % 25 == 0:
            print(f"  {i}/{len(want)} … {n}면")
        time.sleep(0.25)          # 남의 서버다. 몰아치지 않는다
    except Exception as e:
        fail += 1
        print(f"  ! {n}면 (facs {facs}) {e}")

print(f"\n받음 {got} · 건너뜀 {skip} · 실패 {fail} -> {OUT}/")
