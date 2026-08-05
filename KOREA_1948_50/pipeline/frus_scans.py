"""원본 지면 스캔 받기. 세 권에 걸쳐 있다.

    python3 frus_scans.py

`frus_fetch.py` 는 pages.json 에 **스캔 파일 번호(facs)** 를 적어 둔다.
그런데 본문에는 `[448면]` 처럼 **인쇄 쪽번호**가 찍힌다. 둘이 다르면
읽는 사람이 각주를 따라갔을 때 엉뚱한 장이 열린다.

그래서 두 가지를 한꺼번에 한다.

  1. pages.json 을 인쇄 쪽번호로 바꾼다 (`<pb facs="0460" n="448"/>` 이 짝)
  2. 내려받을 때만 facs 로 주소를 만들고, **파일은 인쇄 쪽번호로 저장한다**

세 권이 섞여 있으므로 파일 이름에 권을 붙인다 — `48-448.png`. 안 그러면
1948년 권의 448면과 1950년 권의 448면이 서로를 덮어쓴다.
"""
import json
import os
import re
import sys
import time
import urllib.request

VOLS = {"48": "frus1948v06", "49": "frus1949v07p2", "50": "frus1950v07"}
IMG = "https://static.history.state.gov/frus/{vol}/medium/{facs}.png"
UA = {"User-Agent": "Mozilla/5.0 (research; personal use)"}

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RAW = os.path.join(ROOT, "raw")
OUT = os.path.join(ROOT, "pages")
os.makedirs(OUT, exist_ok=True)

pages = json.load(open(os.path.join(RAW, "pages.json")))
fixed = {}
got = skip = fail = 0

for tag, vol in VOLS.items():
    xml = open(os.path.join(RAW, f"{vol}.xml"), encoding="utf-8").read()
    f2n, n2f = {}, {}
    for m in re.finditer(r'<pb[^>]*facs="(\d+)"[^>]*n="([^"]+)"', xml):
        facs, n = m.group(1), m.group(2)
        if n.isdigit():
            f2n.setdefault(facs, n)
            n2f.setdefault(n, facs)
    print(f"{vol}  짝 {len(f2n)}쌍")

    want = set()
    for did, facs in pages.items():
        if not did.startswith(tag + "-"):
            continue
        out = []
        for f in facs:
            n = f2n.get(str(f).zfill(4)) or f2n.get(str(f))
            if n and n not in out:
                out.append(f"{tag}-{n}")
                want.add(n)
        fixed[did] = out

    for n in sorted(want, key=int):
        dst = os.path.join(OUT, f"{tag}-{n}.png")
        if os.path.exists(dst) and os.path.getsize(dst) > 5000:
            skip += 1
            continue
        facs = n2f.get(n)
        if not facs:
            fail += 1
            continue
        try:
            req = urllib.request.Request(
                IMG.format(vol=vol, facs=facs.zfill(4)), headers=UA)
            with urllib.request.urlopen(req, timeout=120) as r:
                open(dst, "wb").write(r.read())
            got += 1
            if got % 25 == 0:
                print(f"  … {got}장")
            time.sleep(0.25)          # 남의 서버다. 몰아치지 않는다
        except Exception as e:
            fail += 1
            print(f"  ! {tag}-{n} {e}")

json.dump(fixed, open(os.path.join(RAW, "pages.json"), "w"),
          ensure_ascii=False, indent=1)
print(f"\n받음 {got} · 건너뜀 {skip} · 실패 {fail} -> {OUT}/")
