"""원본 지면 스캔 받기.

    python3 frus_scans.py

FRUS_1945_Korea 에서는 인쇄 쪽번호와 스캔 파일 번호의 차이(+12)를 직접 재서
맞췄지만, 여기서는 TEI 의 `<pb facs="0460" n="448"/>` 이 짝을 그대로 알려준다.

**파일은 인쇄 쪽번호로 저장한다** — 본문의 [448면] 표시와 파일 이름이 같아야
헷갈리지 않는다. 내려받을 때만 facs 번호로 주소를 만든다.

먼저 `fix_pagemap.py` 를 돌려 raw/pages.json 을 인쇄 쪽번호로 맞춰 두어야 한다.
"""
import json
import os
import re
import sys
import time
import urllib.request

VOL = "frus1945v06"
IMG = f"https://static.history.state.gov/frus/{VOL}/medium/{{}}.png"
UA = {"User-Agent": "Mozilla/5.0 (research; personal use)"}

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RAW = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "raw")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "pages")

os.makedirs(OUT, exist_ok=True)
pages = json.load(open(os.path.join(RAW, "pages.json")))
want = sorted({str(p) for v in pages.values() for p in v}, key=int)

# 인쇄 쪽번호 → 스캔 파일 번호
xml = open(os.path.join(RAW, f"{VOL}.xml"), encoding="utf-8").read()
n2f = {}
for m in re.finditer(r'<pb[^>]*facs="(\d+)"[^>]*n="([^"]+)"', xml):
    if m.group(2).isdigit():
        n2f.setdefault(m.group(2), m.group(1))

print(f"면 {len(want)}장 (문서 {len(pages)}건)")

got = 0
for n in want:
    dst = os.path.join(OUT, f"{n}.png")
    if os.path.exists(dst) and os.path.getsize(dst) > 5000:
        continue
    facs = n2f.get(n)
    if not facs:
        print(f"!! {n}면 — 스캔 번호를 못 찾았다")
        continue
    try:
        req = urllib.request.Request(IMG.format(facs), headers=UA)
        with urllib.request.urlopen(req, timeout=60) as r:
            data = r.read()
    except Exception as e:
        print(f"!! {n} — {e}")
        continue
    open(dst, "wb").write(data)
    got += 1
    print(f"   {n} {len(data)//1024}KB")
    time.sleep(0.3)

have = len([f for f in os.listdir(OUT) if f.endswith(".png")])
size = sum(os.path.getsize(os.path.join(OUT, f)) for f in os.listdir(OUT)) / 1e6
print(f"\n스캔 {have}/{len(want)}장 (이번에 {got}장) · {size:.0f}MB -> {OUT}/")
