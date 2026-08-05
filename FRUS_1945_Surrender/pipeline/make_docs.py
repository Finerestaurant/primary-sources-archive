"""FRUS 1943 자료 → 열람기 규격의 docs.json.

    python3 make_docs.py

이 파일이 이 문서철에서만 통하는 유일한 부분이다. 열람기(../../열람기/build.py)는
자료를 모르고 규격(../../열람기/SCHEMA.md)만 안다.

읽는 것   tr/*.json (번역) · raw/*.txt (정본 영문) · raw/index.json · raw/pages.json
쓰는 것   reading/docs.json
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TR, RAW = os.path.join(ROOT, "tr"), os.path.join(ROOT, "raw")
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "reading", "docs.json")

# 문서 종류를 칩 세 갈래로 묶는다. 자료에 이미 있는 doc_type 값만 쓴다.
GROUP = {"전보": "A",
         "각서": "B", "각서 초안": "B", "보고서": "B", "비망록": "C",
         "회의록": "C", "전화 비망록": "C", "기록": "C",
         "성명": "D", "구술서": "D", "서한": "D"}

index = {d["doc_id"]: d for d in json.load(open(os.path.join(RAW, "index.json")))}
pages = json.load(open(os.path.join(RAW, "pages.json")))

out, missing = [], []
for did in sorted(index, key=lambda x: int(x[1:])):
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

    n = int(did[1:])
    src = index[did]
    body = open(os.path.join(RAW, did + ".txt")).read().split("----- 각주 -----")[0]

    # 회의록은 발신·수신이 없고 참석자가 있다. 있는 것만 표에 올린다.
    who = d.get("participants") or []
    out.append({
        "id": did,
        "order": n,
        "date": d.get("date"),
        "group": GROUP.get(d.get("doc_type"), "X"),
        "eyebrow": f"{did} · {src['title']}",
        "title": d.get("title_ko") or src["title"],
        "badge": d.get("classification"),
        "list_right": f"문서 {n}",
        "meta": [
            {"k": "일자", "v": d.get("date") or d.get("date_note")},
            {"k": "시각", "v": d.get("time")},
            {"k": "장소", "v": d.get("place"), "txt": True},
            {"k": "전문번호", "v": d.get("msg_nr")},
            {"k": "원문출처", "v": d.get("source_note"), "txt": True},
            {"k": "발신", "v": d.get("from"), "txt": True},
            {"k": "수신", "v": d.get("to"), "txt": True},
            {"k": "참석", "v": ", ".join(who) if who else None, "txt": True, "wide": True},
            {"k": "종류", "v": d.get("doc_type")},
        ],
        "links": [{"k": "FRUS", "text": f"문서 {n} 원문", "url": src["url"]}],
        "summary": d.get("subject_ko"),
        "points": d.get("key_points_ko") or [],
        "primary": (d.get("ko") or "").strip(),
        "secondary": body.strip(),
        "notes": d.get("notes_ko") or [],
        "warn": d.get("confidence") != "high",
        "pages": pages.get(did, []),
        "search": " ".join((d.get("people") or []) + who),
    })

os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump(out, open(OUT, "w"), ensure_ascii=False, indent=1)
print(f"문서 {len(out)}건 → {OUT}")
if missing:
    print(f"!! 번역 없음 {len(missing)}건: {' '.join(missing)}")
