"""문서별 면 범위를 복원하고 원본 스캔을 받는다.

    python frus_scans.py ../raw ../pages

FRUS 본문의 [1019면] 표시는 **면이 넘어가는 지점**만 찍혀 있다. 문서가 시작하는
면에는 표시가 없다. 그래서 첫 문서의 시작 면 하나만 알면 나머지는 이어서 센다 —
어떤 문서의 마지막 면이 다음 문서의 첫 면이다(한 면에 여러 문서가 실린다).

스캔 파일 이름은 인쇄 쪽번호가 아니라 물리적 장 번호다. 앞머리(로마숫자)만큼
어긋나 있어 OFFSET 으로 맞춘다. 다른 권을 받을 때는 이 값을 다시 재야 한다.

산출물
    pages/1019.png …      인쇄 쪽번호로 저장한다 (본문 표시와 같은 번호)
    raw/pages.json        문서번호 → 면 목록
"""
import json
import os
import re
import sys
import time
import urllib.request

RAW = sys.argv[1] if len(sys.argv) > 1 else "../raw"
OUT = sys.argv[2] if len(sys.argv) > 2 else "../pages"

VOL = "frus1945v06"
FIRST_PAGE = 1018          # 제10장 1절이 시작하는 인쇄 쪽. d756 의 첫 마커가 1019다.
OFFSET = 12                # 인쇄 쪽번호 + OFFSET = 스캔 파일 번호
IMG = f"https://static.history.state.gov/frus/{VOL}/medium/{{}}.png"
UA = {"User-Agent": "Mozilla/5.0 (research; personal use)"}

os.makedirs(OUT, exist_ok=True)

index = json.load(open(os.path.join(RAW, "index.json")))
index.sort(key=lambda d: int(d["doc_id"][1:]))

# ---- 면 범위 복원 ----
pages, cur = {}, FIRST_PAGE
for d in index:
    did = d["doc_id"]
    body = open(os.path.join(RAW, did + ".txt")).read().split("----- 각주 -----")[0]
    marks = [int(m) for m in re.findall(r"\[(\d+)면\]", body)]
    # 마커를 그대로 쓰면 안 된다. 통째로 각주나 표만 실린 면에는 전환 표시가
    # 안 찍히는 일이 있어 중간이 빈다. 시작 면부터 마지막 마커까지 연속으로 센다.
    end = max(marks) if marks else cur
    pages[did] = list(range(cur, end + 1))
    cur = end

covered = sorted({x for v in pages.values() for x in v})
gaps = [n for n in range(covered[0], covered[-1] + 1) if n not in covered]
print(f"면 {covered[0]}–{covered[-1]} · {len(covered)}면"
      + (f" · !! 빠진 면 {gaps}" if gaps else " · 빠진 면 없음"))

json.dump(pages, open(os.path.join(RAW, "pages.json"), "w"),
          ensure_ascii=False, indent=1)

# ---- 스캔 받기 ----
got = 0
for n in covered:
    dst = os.path.join(OUT, f"{n}.png")
    if os.path.exists(dst) and os.path.getsize(dst) > 5000:
        continue
    url = IMG.format(n + OFFSET)
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=60) as r:
            data = r.read()
    except Exception as e:
        print(f"!! {n}면 ({url}) — {e}")
        continue
    open(dst, "wb").write(data)
    got += 1
    print(f"   {n}면 {len(data)//1024}KB")
    time.sleep(0.3)

have = len([f for f in os.listdir(OUT) if f.endswith(".png")])
print(f"\n스캔 {have}/{len(covered)}면 (이번에 {got}장) -> {OUT}/")
