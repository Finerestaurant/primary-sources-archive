"""번역(tr/*.json)을 열람기 규격의 docs.json 으로 묶는다.

    python3 make_docs.py

이 문서철만의 사정이 둘 있다.

**영문 창은 교정본이다.** 앞 FRUS 문서철들은 raw/ 의 정본 영문을 그대로 둘째
창에 넣었다. 여기 raw/ 는 기계가 스캔에서 읽어 낸 OCR 원본이라 뭉개져 있어서,
둘째 창에는 번역자가 교정한 영문(tr 의 `en`)을 넣는다. raw/ 의 OCR 은 대조용으로
디스크에만 남는다.

**칩은 내용으로 가른다.** 일곱 건뿐이라 doc_type(각서·서한)으로는 갈리는 것이
없다. 무엇에 관한 왕복인가로 세 갈래를 둔다.

읽는 것   tr/*.json (번역·교정 영문) · raw/index.json (날짜·원제·CREST 번호·주소)
쓰는 것   reading/docs.json
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TR, RAW = os.path.join(ROOT, "tr"), os.path.join(ROOT, "raw")
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "reading", "docs.json")

# 내용으로 세 갈래. 현지 정세 판단 / 자료·접촉선 송부 / 종전 뒤 평시 첩보.
GROUP = {"L01": "A", "L02": "A",
         "L03": "B", "L04": "B", "L05": "B", "L06": "B",
         "L07": "C"}

index = {d["doc_id"]: d for d in json.load(open(os.path.join(RAW, "index.json")))}
order = sorted(index, key=lambda i: (index[i]["date"], i))  # 날짜순, 같은 날이면 번호순

out, missing = [], []
for n, did in enumerate(order, 1):
    src = index[did]
    p = os.path.join(TR, did + ".json")
    if not os.path.exists(p):
        missing.append(did)
        continue
    try:
        d = json.load(open(p))
    except json.JSONDecodeError as e:
        print(f"!! {did} JSON 깨짐: {e}")
        missing.append(did)
        continue
    if not (d.get("ko") or "").strip():
        print(f"!! {did} 본문이 비었다")
        missing.append(did)
        continue

    out.append({
        "id": did,
        "order": n,
        "date": d.get("date") or src["date"],
        "group": GROUP.get(did, "X"),
        "eyebrow": f"{did} · {src['title']}",
        "title": d.get("title_ko") or src["title"],
        "badge": d.get("classification"),
        "meta": [
            {"k": "일자", "v": d.get("date") or src["date"]},
            {"k": "종류", "v": d.get("doc_type")},
            {"k": "발신", "v": d.get("from"), "txt": True},
            {"k": "수신", "v": d.get("to"), "txt": True},
            {"k": "CREST 번호", "v": src.get("crest")},
        ],
        "links": [{"k": "CREST", "text": "archive.org 스캔", "url": src["url"]}],
        "summary": d.get("subject_ko"),
        "points": d.get("key_points_ko") or [],
        "primary": (d.get("ko") or "").strip(),
        "secondary": (d.get("en") or "").strip(),
        "notes": d.get("notes") or [],
        "warn": d.get("confidence") != "high",
        "search": " ".join((d.get("people") or []) + (d.get("redactions") or [])
                           + [d.get("title_en") or ""]),
    })

os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump(out, open(OUT, "w"), ensure_ascii=False, indent=1)
print(f"문서 {len(out)}건 → {OUT}")
if missing:
    print(f"!! 빠짐 {len(missing)}건: {' '.join(missing)}")
