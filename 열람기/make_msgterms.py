"""전문번호에서 용어집을 자동으로 만든다.

    python3 make_msgterms.py <collection.json> [terms_msg.json]

## 왜

이 자료는 문서끼리 전문번호로 서로를 부른다. 「귀 WX 61967에 관하여」,
「TFGCG 285에 대한 회신」— 그런데 그 번호가 무슨 문서인지는 목록을 뒤져야 안다.
읽는 흐름이 매번 끊긴다.

문서마다 `msg_nr` 가 이미 있으니, 그것을 모아 「이 번호는 이 문서다」로 이어 준다.
본문에서 번호를 누르면 그 문서로 간다.

## 무엇을 뽑고 무엇을 버리나

**접두어가 붙은 번호만 쓴다.** `WX 97877`, `TFGCG 334`, `J.C.S. 1483/24` 같은 것.
`329`, `040805` 처럼 숫자만 있는 것은 버린다 — 본문의 쪽수·부대번호·날짜와
구별되지 않아 엉뚱한 곳에 주석이 붙는다.

산출물은 수동으로 쓴 `terms.json` 과 **별개 파일**이다. 자동 생성이 사람이 쓴
주석을 덮어쓰면 안 된다. collection.json 에서 둘을 나란히 적는다.

    "terms": ["terms.json", "terms_msg.json"]
"""
import json
import os
import re
import sys

if len(sys.argv) < 2:
    sys.exit(__doc__)

CONF = os.path.abspath(sys.argv[1])
BASE = os.path.dirname(CONF)
conf = json.load(open(CONF))
OUT = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 \
    else os.path.join(BASE, "terms_msg.json")

docs = json.load(open(os.path.join(BASE, conf.get("docs", "docs.json"))))

# 접두어 + 숫자. 접두어는 대문자 2~8자(점 허용), 숫자는 2자리 이상.
NR = re.compile(r"\b([A-Z][A-Z.]{0,7})\s*[-–]?\s*(\d{2,6}(?:/\d{1,3})?)\b")
# 접두어처럼 보여도 전문번호가 아닌 것들.
# AG 는 부관부 편철 파일번호(`AG 014.12`)라서, 이걸 넣으면 문서철 번호와 겹쳐
# 본문 곳곳에 엉뚱한 주석이 붙는다.
SKIP = {"NO", "NO.", "APO", "RG", "BOX", "PAGE", "P.", "PP", "VOL", "AM", "PM",
        "AG", "A.G.", "ENTRY", "FILE", "COPY", "INCL", "ENCL"}


def variants(pre, num):
    """본문 표기가 흔들린다. 같은 번호로 볼 만한 꼴을 함께 둔다."""
    bare = pre.replace(".", "")
    out = {f"{pre} {num}", f"{pre}{num}", f"{bare} {num}", f"{bare}{num}"}
    if len(bare) > 1:                       # J.C.S. → JCS, 그 반대도
        out.add(f"{'.'.join(bare)}. {num}")
    return {x for x in out if x}


found, seen = {}, {}
for d in docs:
    raw = ""
    for m in (d.get("meta") or []):
        if m.get("k") == "전문번호" and m.get("v"):
            raw = str(m["v"])
            break
    if not raw:
        continue
    # 「TFXAG 381 · 배서 …」 처럼 설명이 붙기도 한다. 번호만 걷어낸다.
    for pre, num in NR.findall(raw):
        if pre.upper().rstrip(".") in SKIP:
            continue
        key = f"{pre} {num}"
        if key in seen:                     # 같은 번호가 여러 문서에 (사본 등)
            seen[key].append(d["id"])
            continue
        seen[key] = [d["id"]]
        found[key] = {
            "term": key,
            "alias": sorted(variants(pre, num) - {key}),
            "title": f"{key} — {d.get('title') or d['id']}",
            "body": d.get("summary") or "",
            "badge": "이 문서철의 전문",
            "doc": d["id"],
        }

# 여러 문서가 같은 번호를 쓰면 그 사실을 적어 둔다
for key, ids in seen.items():
    if len(ids) > 1 and key in found:
        found[key]["points"] = [f"같은 번호가 붙은 문서: {' · '.join(ids)}"]

data = {"_": sorted(found.values(), key=lambda t: t["term"])}
json.dump(data, open(OUT, "w"), ensure_ascii=False, indent=1)

print(f"{conf.get('title','')} — 전문번호 {len(found)}개 → {OUT}")
dup = {k: v for k, v in seen.items() if len(v) > 1}
if dup:
    print(f"  같은 번호를 쓰는 문서 {len(dup)}쌍: "
          + ", ".join(f"{k}({len(v)})" for k, v in list(dup.items())[:5]))
skipped = sum(1 for d in docs
              if any(m.get("k") == "전문번호" and m.get("v") for m in (d.get("meta") or []))) \
    - len(seen)
if skipped > 0:
    print(f"  접두어가 없어 건너뛴 문서 약 {skipped}건 (숫자만 있는 번호)")
