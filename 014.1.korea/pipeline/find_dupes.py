"""같은 문서의 사본을 찾는다.

    python3 find_dupes.py ../ocr ../raw/dupes.json

이 문서철에는 **같은 문서가 여러 벌 편철돼 있다.** 부관부가 배포처마다 사본을
남겼기 때문이다. 예를 들어 「Conditions in Korea」 9월 13일자는 사본이 다섯 벌,
9월 24일자는 세 벌 들어 있다.

그대로 번역하면 같은 글을 여덟 번 옮기게 된다. 먼저 사본을 찾아 한 벌만 남긴다.

낱말 집합의 자카드 유사도로 잰다. OCR 오차가 있어 완전 일치를 볼 수는 없고,
경험상 0.55 를 넘으면 같은 문서의 사본이었다 (다른 문서끼리는 0.2 를 넘지 않는다).
"""
import glob
import json
import os
import re
import sys

SRC = sys.argv[1] if len(sys.argv) > 1 else "../ocr"
OUT = sys.argv[2] if len(sys.argv) > 2 else "../raw/dupes.json"
TH = float(sys.argv[3]) if len(sys.argv) > 3 else 0.55
MIN_WORDS = 40          # 이보다 짧은 면은 견주지 않는다 (표지·백지)

pages = {}
for f in sorted(glob.glob(os.path.join(SRC, "*.txt"))):
    p = os.path.basename(f)[:-4]
    w = set(re.sub(r"[^a-z ]", " ", open(f).read().lower()).split())
    w = {x for x in w if len(x) > 2}
    pages[p] = w

keys = sorted(pages)
short = [p for p in keys if len(pages[p]) < MIN_WORDS]


def sim(a, b):
    A, B = pages[a], pages[b]
    if not A or not B:
        return 0.0
    return len(A & B) / len(A | B)


# 이어붙이기(union-find)로 사본 무리를 만든다
parent = {p: p for p in keys}


def find(x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x


pairs = 0
for i, a in enumerate(keys):
    if a in short:
        continue
    for b in keys[i + 1:]:
        if b in short:
            continue
        if sim(a, b) >= TH:
            parent[find(a)] = find(b)
            pairs += 1

groups = {}
for p in keys:
    groups.setdefault(find(p), []).append(p)
dupes = {k: v for k, v in groups.items() if len(v) > 1}

out = []
for g in sorted(dupes.values(), key=lambda v: v[0]):
    out.append({"keep": g[0], "copies": g[1:], "n": len(g)})

os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
json.dump(out, open(OUT, "w"), ensure_ascii=False, indent=1)

dup_pages = sum(len(x["copies"]) for x in out)
print(f"면 {len(keys)}개 · 짧아서 건너뛴 면 {len(short)}개")
print(f"사본 무리 {len(out)}개 · 겹치는 면 {dup_pages}개 "
      f"→ 실제로 읽을 면 {len(keys) - dup_pages}개")
print()
for x in out[:20]:
    print(f"  {x['keep']} ← {' '.join(x['copies'])}  ({x['n']}벌)")
if len(out) > 20:
    print(f"  … 그 밖 {len(out)-20}무리")
