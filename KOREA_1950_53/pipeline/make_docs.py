"""번역과 정본을 열람기 규격의 docs.json 으로 묶는다.

    python3 make_docs.py

다른 문서철의 같은 이름 파일과 다른 점이 둘 있다.

**세 권이 섞여 있다.** 문서번호가 `48-d776` 처럼 권을 달고 있어서 `int(did[1:])`
로 정렬할 수 없다. 권과 번호를 갈라서 잡는다. 그런데 권 순서로 세우면 1948년
권의 12월 문서가 1949년 권의 1월 문서보다 뒤에 오는 일이 생긴다. 이 문서철은
세 해가 이어지는 것을 보여 주는 것이 목적이므로 **날짜순으로 세운다.**

**칩을 고를 때 붙인 태그로 나눈다.** 다른 문서철은 doc_type(전보·각서·서한)으로
갈랐는데, 여기서는 그것이 아무 말도 해 주지 않는다. 152건 가운데 대다수가
전보다. 무엇에 관한 전보인지가 갈라야 할 것이라, `pick.json` 에 적어 둔 태그를
쓴다. 여덟 갈래를 여섯으로 묶었다 — 칩이 여덟이면 고르는 것이 일이 된다.

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

# pick.json 의 태그 여덟 갈래를 여섯으로 묶는다.
GROUP = {"전황": "A", "결정": "B", "정책": "C", "정세판단": "D",
         "회담": "E", "동맹국": "E", "휴전회담": "E",
         "이승만": "F", "포로": "F"}
VOLNAME = {"frus1950v07": "1950 VII", "frus1951v07p1": "1951 VII-1",
           "frus1952-54v15p1": "1952-54 XV-1", "frus1952-54v15p2": "1952-54 XV-2"}

index = json.load(open(os.path.join(RAW, "index.json")))
pages = json.load(open(os.path.join(RAW, "pages.json"))) \
    if os.path.exists(os.path.join(RAW, "pages.json")) else {}

# 날짜순. 같은 날이면 권 순서, 그 다음 문서번호 순이다.
index.sort(key=lambda d: (d["date"] or "9999", d["vol"], int(d["src_id"][1:])))

out, missing = [], []
for n, src in enumerate(index, 1):
    did = src["doc_id"]
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

    body = open(os.path.join(RAW, did + ".txt")).read().split("----- 각주 -----")[0]

    out.append({
        "id": did,
        "order": n,
        "date": d.get("date") or src["date"],
        "group": GROUP.get(src.get("tag"), "X"),
        "eyebrow": f"{did} · {src['title']}",
        "title": d.get("title_ko") or src["title"],
        "badge": d.get("classification"),
        "list_right": VOLNAME.get(src["vol"], ""),
        "meta": [
            # 날짜가 없는 편집자 주는 앞 문서의 날짜를 물려받았다. 물려받은
            # 것을 확정된 날짜인 양 보이면 안 되므로 그렇다고 적어 둔다.
            {"k": "일자", "v": (d.get("date") or src["date"]) +
                ("  (앞 문서에서 물려받음)" if src.get("date_guess") else "")},
            {"k": "시각", "v": d.get("time")},
            {"k": "발신", "v": d.get("from"), "txt": True},
            {"k": "수신", "v": d.get("to"), "txt": True},
            {"k": "장소", "v": d.get("place")},
            {"k": "전문번호", "v": d.get("msg_nr")},
            {"k": "종류", "v": d.get("doc_type")},
            {"k": "원문출처", "v": d.get("source_note") or src.get("source_note"),
             "txt": True},
        ],
        "links": [{"k": "FRUS", "text": f"{VOLNAME.get(src['vol'], '')} 원문",
                   "url": src["url"]}],
        "summary": d.get("subject_ko"),
        "points": d.get("key_points_ko") or [],
        "primary": (d.get("ko") or "").strip(),
        "secondary": body.strip(),
        "notes": d.get("notes_ko") or [],
        "warn": d.get("confidence") != "high",
        "pages": pages.get(did, []),
        "search": " ".join(d.get("people") or []),
    })

os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump(out, open(OUT, "w"), ensure_ascii=False, indent=1)
print(f"문서 {len(out)}건 → {OUT}")
if missing:
    print(f"!! 빠짐 {len(missing)}건: {' '.join(missing)}")
