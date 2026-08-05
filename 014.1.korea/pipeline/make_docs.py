"""014.1 Korea 자료 → 열람기 규격의 docs.json.

    python3 make_docs.py

이 파일이 이 문서철에서만 통하는 유일한 부분이다. 열람기(../../열람기/build.py)는
자료를 모르고 규격(../../열람기/SCHEMA.md)만 안다.

읽는 것   tr/<serial>.json (번역) · raw/documents.json (면 배정) ·
          raw/list_of_papers.json (문서철 자체의 공식 색인)
쓰는 것   reading/docs.json
"""
import json
import os
import sys as _sys

# OCR 은 스캔에 찍힌 물리적 줄을 그대로 내놓는다. 한 문단이 예닐곱 조각으로
# 쪼개져 읽을 수가 없어서, 열람기에 넣을 때만 문단으로 합친다.
# 원문(ocr/)은 건드리지 않는다 — 원본 대조는 스캔으로 한다.
_sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "..", "..", "열람기"))
from reflow import reflow
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TR = os.path.join(ROOT, "tr")
RAW = os.path.join(ROOT, "raw")
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "reading", "docs.json")

GROUP = {"서한": "A", "전문": "B",
         "각서": "C", "지령": "C",
         "라우팅 슬립": "D", "첨부물": "D", "기타": "D"}

docs = json.load(open(os.path.join(RAW, "documents.json")))
lop = {x["serial"]: x for x in json.load(open(os.path.join(RAW, "list_of_papers.json")))}


def order_key(s):
    """편철 일련번호(1, 1-A, 2-B, 7-K, 10)를 정렬 가능한 값으로.
    문서철은 역연대순으로 편철돼 있어 편철순이 곧 시간 역순이다."""
    m = re.fullmatch(r"(\d+)(?:-([A-Z]))?", str(s))
    if not m:
        return (999, 99)
    return (int(m.group(1)), ord(m.group(2)) - 64 if m.group(2) else 0)


out, missing = [], []
for i, d in enumerate(sorted(docs, key=lambda x: x["pages"][0])):
    s = d.get("serial")
    if not s:
        continue
    p = os.path.join(TR, f"{s}.json")
    if not os.path.exists(p):
        missing.append(s)
        continue
    try:
        t = json.load(open(p))
    except json.JSONDecodeError as e:
        print(f"!! {s} JSON 깨짐: {e}")
        missing.append(s)
        continue

    idx = lop.get(s, {})
    pages = d["pages"] + d.get("copies", [])
    subj = t.get("subject_ko") or d.get("subject") or s

    meta = [
        {"k": "일자", "v": t.get("date") or t.get("date_note")},
        {"k": "발신", "v": t.get("from"), "txt": True},
        {"k": "수신", "v": t.get("to"), "txt": True},
        {"k": "참조", "v": t.get("info"), "txt": True},
        {"k": "전문번호", "v": t.get("msg_nr")},
        {"k": "종류", "v": t.get("doc_type")},
        {"k": "면", "v": f"{d['pages'][0]}–{d['pages'][-1]} ({len(d['pages'])}면)"
                        + (f" · 사본 {len(d['copies'])}면" if d.get("copies") else "")},
        {"k": "건명", "v": t.get("subject_en"), "txt": True},
    ]
    # 색인은 이 문서철 자체가 갖고 있는 목록이다. 번역과 별개로 붙여 둔다.
    if idx.get("synopsis"):
        meta.append({"k": "색인 요지", "v": idx["synopsis"], "txt": True, "wide": True})

    # 접수 도장·손글씨 결재·회부 기록. 문서당 열 건 안팎이라 메타 표에 한 줄로
    # 밀어 넣으면 뭉개진다. 각주 자리에 한 건씩 놓는다 —
    # 이 문서철은 여백이 값어치의 절반이라 읽히게 두어야 한다.
    notes = [f"[도장·결재] {s}" for s in (t.get("stamps_ko") or [])]
    if d.get("match") and d["match"] != "high":
        notes.append(f"면 배정 신뢰도 {d['match']} — {d.get('match_why') or ''}")
    if d.get("note"):
        notes.append(f"편철 메모 — {d['note']}")

    out.append({
        "id": s,
        "order": order_key(s)[0] * 100 + order_key(s)[1],
        "date": t.get("date"),
        "group": GROUP.get(t.get("doc_type"), "D"),
        "eyebrow": f"편철 {s} · {d['pages'][0]}–{d['pages'][-1]}면",
        "title": subj,
        "badge": t.get("classification"),
        "list_right": f"{s}",
        "meta": meta,
        "summary": t.get("summary_ko"),
        "points": t.get("key_points_ko") or [],
        "primary": (t.get("ko") or "").strip(),
        "secondary": reflow((t.get("en") or "").strip()),
        "notes": notes,
        "warn": t.get("confidence") not in ("high", None),
        "pages": pages,
        "search": " ".join((t.get("people") or []) + [s, idx.get("synopsis") or ""]),
    })

os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump(out, open(OUT, "w"), ensure_ascii=False, indent=1)
print(f"문서 {len(out)}건 → {OUT}")
if missing:
    print(f"!! 번역 없음 {len(missing)}건: {' '.join(missing)}")
