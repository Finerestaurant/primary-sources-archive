"""NDL 자료 → 열람기 규격의 docs.json.

    python3 make_docs.py

읽는 것   reading/docs.json        assemble_docs.py 가 만든 이 문서철용 구조
쓰는 것   reading/reader_docs.json 공용 열람기가 읽는 규격

**두 파일을 따로 둔다.** 같은 자리에 덮어쓰면 assemble_docs.py 를 다시 돌릴 때
규격 파일이 날아간다.

열람기(../../열람기/build.py)는 자료를 모르고 규격(../../열람기/SCHEMA.md)만 안다.
이 파일이 그 사이를 메운다 — 이 문서철에서만 통하는 유일한 부분이다.
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
READING = os.path.join(os.path.dirname(HERE), "pid_9850431", "reading")

SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(READING, "docs.json")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(READING, "reader_docs.json")

THEME = {"A. 조선경비대 무장·증강": "A", "B. 한국군 창설·훈련": "B",
         "C. 병참·편제": "C", "D. 장래 정책·철군": "D"}

src = json.load(open(SRC))
if src and "primary" in src[0]:
    sys.exit("이미 규격에 맞춘 파일이다. assemble_docs.py 의 출력을 넘겨라.")


def pagemarks(t):
    """[[page 0003]] / [[면 0003]] → 규격의 [0003면]."""
    return re.sub(r"\[\[(?:page|면)\s*(\d+)\]\]", r"[\1면]", t or "")


out = []
for i, d in enumerate(sorted(src, key=lambda x: x["page_start"])):
    title = d.get("subject_ko") or d.get("subject_en") or d["doc_id"]
    part = (not d.get("translated")) and d.get("done")
    out.append({
        "id": d["doc_id"],
        "order": i,
        "date": d.get("date"),
        "group": THEME.get(d.get("theme"), "X"),
        "eyebrow": f"{d['doc_id']}" + (f" · {d['theme']}" if d.get("theme") else ""),
        "title": title,
        "badge": d.get("classification"),
        "list_right": f"{d['page_start']}–{d['page_end']}",
        "meta": [
            {"k": "발신", "v": d.get("from"), "txt": True},
            {"k": "수신", "v": d.get("to"), "txt": True},
            {"k": "참조", "v": d.get("info"), "txt": True},
            {"k": "전문번호", "v": d.get("msg_nr")},
            {"k": "종류", "v": d.get("doc_type")},
            {"k": "면", "v": f"{d['page_start']}–{d['page_end']} ({d['n_pages']}면)"},
            {"k": "건명", "v": d.get("subject_title"), "txt": True},
        ],
        "summary": d.get("subject_en") if d.get("subject_ko") else None,
        "points": d.get("key_points_ko") or [],
        "primary": pagemarks(d.get("ko")),
        "secondary": reflow(pagemarks(d.get("en"))),
        "notes": [],
        "warn": d.get("confidence") == "low",
        "pages": d.get("pages") or [],
    })

json.dump(out, open(OUT, "w"), ensure_ascii=False, indent=1)
print(f"문서 {len(out)}건 → {OUT}")
