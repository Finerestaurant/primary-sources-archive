"""번역 결과를 열람기 규격으로 바꾼다.

    python3 make_docs.py

이 문서철은 사건(event) 이 1차 단위다. `문서목록.json` 이 사건마다 고른
레퍼런스 코드와 제목·쪽수를 들고 있고, `tr/<코드>.json` 이 그 문서의 번역이다.
사건 여섯 개를 열람기의 `groups`(A~E, X) 여섯 칸에 하나씩 건다.

오른쪽 창에는 `ja`(지면에서 읽은 원문)를 놓는다. **OCR 초벌이 없어서 이
문서철에는 raw/*.txt 도, 교정 전후 두 벌도 없다** — `ja` 자체가 정본이다.
"""
import os
import json
import glob

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "reading", "docs.json")

GROUP = {
    "changtsolin-1928": ("A", "장쭤린 폭살 · 1928"),
    "manchurian-1931": ("B", "만주사변 · 1931"),
    "jehol-1933": ("C", "러허 작전 · 1933"),
    "marcopolo-1937": ("D", "노구교 사건 · 1937"),
    "taiyuan-1937": ("E", "태원작전(산서성) · 1937"),
    "nomonhan-1939": ("X", "노몬한 사건 · 1939"),
}


def main():
    doclist = json.load(open(os.path.join(HERE, "문서목록.json")))
    meta = {}
    for ev in doclist["events"]:
        for d in ev["docs"]:
            meta[d["ref"]] = {"event": ev["key"], "event_title": ev["title"],
                               "archive": ev["archive"], "date": ev.get("date"),
                               "title": d["title"], "pages_planned": d["pages"]}

    docs, missing, order = [], [], 0
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
        pages = sorted(
            os.path.splitext(os.path.basename(p))[0]
            for p in glob.glob(os.path.join(ROOT, "pages", f"{ref}-*.jpg")))
        who = t.get("author") or ""
        docs.append({
            "id": ref,
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
            "links": [{"k": "JACAR", "text": f"{ref} 원문",
                       "url": f"https://www.jacar.archives.go.jp/das/meta/{ref}"}],
            "summary": t.get("subject_ko"),
            "points": t.get("key_points_ko") or [],
            "primary": (t.get("ko") or "").strip(),
            "secondary": (t.get("ja") or "").strip(),
            "notes": [t.get("notes")] if t.get("notes") else [],
            "warn": t.get("confidence") != "high",
            "pages": pages,
            "search": " ".join((t.get("people") or [])),
        })
        if len(pages) != m["pages_planned"]:
            print(f"  ! {ref} 지면 {len(pages)}장 (예정 {m['pages_planned']}장) — 확인할 것")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(docs, open(OUT, "w"), ensure_ascii=False, indent=1)
    print(f"문서 {len(docs)}건 → {OUT}")

    done_refs = {d["id"] for d in docs}
    all_refs = set(meta)
    left = all_refs - done_refs
    if left:
        print(f"아직 번역 안 된 것 {len(left)}건: {' '.join(sorted(left))}")


if __name__ == "__main__":
    main()
