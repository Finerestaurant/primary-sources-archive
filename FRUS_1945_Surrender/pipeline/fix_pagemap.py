"""스캔 파일 이름을 인쇄 쪽번호로 맞춘다.

    python3 fix_pagemap.py

처음에는 스캔을 TEI 의 facs 번호(0460.png)로 저장했다. 그런데 본문의 면 표시는
인쇄 쪽번호([449면])다. 둘이 어긋나면 본문에서 면 표시를 눌러도 그림이 안 열린다.

FRUS_1945_Korea 는 인쇄 쪽번호로 저장했으니 그쪽에 맞춘다 —
**본문에 보이는 번호와 파일 이름이 같아야** 나중에 헷갈리지 않는다.

raw/*.txt 는 건드리지 않는다. 번역 작업이 그 파일을 기준으로 돌고 있다.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RAW = os.path.join(ROOT, "raw")
PAGES = os.path.join(ROOT, "pages")
XML = os.path.join(RAW, "frus1945v06.xml")

os.makedirs(PAGES, exist_ok=True)   # 스캔을 받기 전에 돌려도 되게 한다
s = open(XML, encoding="utf-8").read()

# <pb facs="0460" n="448"/> → 스캔번호와 인쇄 쪽번호의 짝.
# n 이 [I] 처럼 로마숫자인 앞머리는 건너뛴다 (본문에 안 나온다).
f2n, n2f = {}, {}
for m in re.finditer(r'<pb[^>]*facs="(\d+)"[^>]*n="([^"]+)"', s):
    facs, n = m.group(1), m.group(2)
    if n.isdigit():
        f2n[facs] = n
        n2f.setdefault(n, facs)

pos = [(m.group(1), m.start()) for m in
       re.finditer(r'<div[^>]*type="document"[^>]*xml:id="(d\d+)"', s)]
span = {d: (st, pos[i + 1][1] if i + 1 < len(pos) else len(s))
        for i, (d, st) in enumerate(pos)}

# `<pb n="405"/>` 는 **거기서 405면이 시작된다**는 표시다. 문서 안의 pb 만 모으면
# 그 문서가 시작된 면을 놓친다 — 문서 본문 끝에 pb 하나만 있으면 그건 다음 문서가
# 시작되는 면이라, 엉뚱한 지면이 열린다.
# 그래서 권 전체의 pb 를 순서대로 훑어 '지금 몇 면인지'를 따라간다.
marks = [(m.start(), m.group(1)) for m in
         re.finditer(r'<pb[^>]*\bn="(\d+)"', s)]

old = json.load(open(os.path.join(RAW, "pages.json")))
new, renames = {}, {}
for did in old:
    st, en = span[did]
    before = [n for p, n in marks if p < st]
    inside = [n for p, n in marks if st <= p < en]
    start = before[-1] if before else (inside[0] if inside else None)
    if start is None:
        print(f"   {did} 인쇄 쪽번호 없음 — 면 목록이 빈다")
        new[did] = []
        continue
    last = inside[-1] if inside else start
    seen = [str(x) for x in range(int(start), int(last) + 1)]
    new[did] = seen
    for x in seen:
        if x in n2f:
            renames[n2f[x]] = x

# 파일 이름 바꾸기
done = 0
for facs, n in sorted(renames.items()):
    src, dst = os.path.join(PAGES, f"{facs}.png"), os.path.join(PAGES, f"{n}.png")
    if os.path.exists(src) and not os.path.exists(dst):
        os.rename(src, dst)
        done += 1

json.dump(new, open(os.path.join(RAW, "pages.json"), "w"),
          ensure_ascii=False, indent=1)

left = [f for f in os.listdir(PAGES) if f.endswith(".png") and f[:-4].startswith("0")]
print(f"이름 바꾼 파일 {done}장")
if left:
    print(f"!! 짝을 못 찾은 스캔 {len(left)}장: {' '.join(sorted(left)[:8])}")
want = sorted({p for v in new.values() for p in v}, key=int)
have = [f[:-4] for f in os.listdir(PAGES) if f.endswith(".png")]
print(f"면 {len(want)}개 · 파일 {len(have)}장 · 빠짐 {sorted(set(want)-set(have), key=int) or '없음'}")
