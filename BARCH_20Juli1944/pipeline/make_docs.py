"""번역 결과를 열람기 규격으로 바꾼다.

    python3 make_docs.py

JACAR_독단전행과 같은 방식이다. 사건(event)이 1차 단위이고, `문서목록.json`이
사건마다 고른 레퍼런스 코드와 제목·쪽수를 들고, `tr/<코드-슬러그>.json`이 그
문서의 번역이다. 이 문서철은 사건이 하나(7월 20일)뿐이라 그룹도 하나(A)다.

오른쪽 창에는 `de`(지면에서 읽은 원문, 독일어)를 놓는다. JACAR의 `ja` 자리를
그대로 옮긴 것 — 필드 이름만 원문 언어에 맞게 바꿨다.

레퍼런스 코드("NS 6/2")에는 공백·슬래시가 있어 파일명에 못 쓴다. 지면 파일과
tr/*.json 파일명은 슬러그(`NS6-2`)를 쓴다.
"""
import os
import json
import glob
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "reading", "docs.json")

GROUP = {
    "attentat-20juli-1944": ("A", "7월 20일 히틀러 암살 미수 · 1944"),
}


def slug(ref):
    return re.sub(r"[ /]", lambda m: "-" if m.group() == "/" else "", ref).replace(" ", "")


def main():
    doclist = json.load(open(os.path.join(HERE, "문서목록.json")))
    meta = {}
    for ev in doclist["events"]:
        for d in ev["docs"]:
            meta[d["ref"]] = {"event": ev["key"], "event_title": ev["title"],
                               "archive": ev["archive"], "date": ev.get("date"),
                               "title": d["title"], "pages_planned": d["pages"]}

    docs, order = [], 0
    for path in sorted(glob.glob(os.path.join(ROOT, "tr", "*.json"))):
        try:
            t = json.load(open(path))
        except json.JSONDecodeError as e:
            print(f"!! {os.path.basename(path)} JSON 깨짐: {e}")
            continue
        ref = t.get("ref") or os.path.basename(path)[:-5]
        m = meta.get(ref)
        if not m:
            print("  건너뜀 (문서목록.json에 없음):", ref)
            continue
        if not (t.get("ko") or "").strip():
            print(f"!! {ref} 본문이 비었다")
            continue
        grp, glabel = GROUP[m["event"]]
        order += 1
        s = slug(ref)
        pages = sorted(
            os.path.splitext(os.path.basename(p))[0]
            for p in glob.glob(os.path.join(ROOT, "pages", f"{s}-*.jpg")))
        who = t.get("author") or ""
        docs.append({
            "id": s,
            "order": order,
            "date": t.get("date") or m["date"],
            "group": grp,
            "eyebrow": f"{m['event_title']} · {ref} · {m['archive']}",
            "title": t.get("title_ko") or m["title"],
            "badge": t.get("doc_type"),
            "list_right": grp,
            "meta": [
                {"k": "사건", "v": m["event_title"]},
                {"k": "일자", "v": t.get("date_src") or t.get("date")},
                {"k": "작성", "v": who, "txt": True},
                {"k": "소장", "v": m["archive"]},
                {"k": "분류", "v": t.get("doc_type")},
            ],
            "links": [],
            "summary": t.get("subject_ko"),
            "points": t.get("key_points_ko") or [],
            "primary": (t.get("ko") or "").strip(),
            "secondary": (t.get("de") or "").strip(),
            "notes": [t.get("notes")] if t.get("notes") else [],
            "warn": t.get("confidence") != "high",
            "pages": pages,
            "search": " ".join((t.get("people") or [])),
        })
        if pages and len(pages) != m["pages_planned"]:
            print(f"  ! {ref} 지면 {len(pages)}장 (전체 {m['pages_planned']}장 중 일부만 옮김 — 부분 번역이면 정상)")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(docs, open(OUT, "w"), ensure_ascii=False, indent=1)
    print(f"문서 {len(docs)}건 → {OUT}")

    done_refs = {t.get("ref") for p in glob.glob(os.path.join(ROOT, "tr", "*.json"))
                 for t in [json.load(open(p))] if (t.get("ko") or "").strip()}
    left = set(meta) - done_refs
    if left:
        print(f"아직 번역 안 된 것 {len(left)}건: {' '.join(sorted(left))}")


if __name__ == "__main__":
    main()
