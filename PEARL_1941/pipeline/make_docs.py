"""FRUS Japan 1931–1941 II 「진주만으로 가는 열 주」 → 열람기 규격의 docs.json.

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

# 이 문서철은 **회담**이 뼈대다. 헐과 노무라가 마주 앉은 자리의 기록이
# 절반을 넘고, 그 사이사이에 서로 건넨 문면(제안·구두 성명)이 끼어 있다.
# 그래서 「마주 앉아 한 말」과 「건넨 종이」를 가른다 — 이 둘의 차이가
# 11월 26일에 무슨 일이 있었는지를 가르는 자리이기도 하다.
GROUP = {"회담 비망록": "A", "비망록": "A", "대화 비망록": "A", "회의록": "A",
         "제안": "B", "제안 초안": "B", "초안": "B", "구두 성명": "B",
         "각서": "C", "각서 초안": "C", "보고": "C",
         "전보": "D",
         "서한": "E", "친서": "E", "성명": "E", "연설": "E", "결의": "E"}

index = {d["doc_id"]: d for d in json.load(open(os.path.join(RAW, "index.json")))}
pages = json.load(open(os.path.join(RAW, "pages.json")))

out, missing = [], []
for did in sorted(index, key=lambda x: (index[x].get("date",""), int(x[1:]))):
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
        "note": f"번역자 주. {d['notes']}" if d.get("notes") else None,
        "warn": d.get("confidence") != "high",
        "pages": pages.get(did, []),
        "search": " ".join((d.get("people") or []) + who),
    })

os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump(out, open(OUT, "w"), ensure_ascii=False, indent=1)
print(f"문서 {len(out)}건 → {OUT}")
if missing:
    print(f"!! 번역 없음 {len(missing)}건: {' '.join(missing)}")
