"""번역 결과를 열람기 규격으로 바꾼다.

    python3 make_docs.py

이 문서철에는 **스캔이 없다.** 원본이 HTML 로 공개된 자료라 지면 이미지가 없고,
그래서 `collection.json` 에 `pages` 를 두지 않았다 — 열람기는 그러면 썸네일과
확대 뷰어를 통째로 뺀다. 오른쪽 창에는 영문 원문이 그대로 붙는다.

한 가지 사정이 있다. 심문조서와 작전 보고는 **한 편의 긴 글**이라 문서 단위가
따로 없다. 그래서 뜻이 끊기지 않는 자리에서 잘라 놓았고(`extract.py`),
여기서는 그 차례를 잃지 않도록 `order` 를 손으로 매긴다.
"""
import os, json, glob, re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = {"toyoda": ("A", "도요다 소에무 심문조서 · USSBS Nav-75", "1945-11-13"),
       "tf58":   ("B", "제58기동부대 작전 보고 · 미처 중장", "1945-06-18")}

# 목록은 시간순이 기본이다. 그런데 작전 보고는 **낸 날짜가 하나**라서, 그대로
# 두면 3월의 작전과 5월의 작전이 6월 18일 한 자리에 뭉친다. 그래서 각 장이
# **다루는 기간의 첫날**을 문서 날짜로 쓴다 — 보고서를 낸 날이 아니라 그 장이
# 서 있는 시점이다. 낸 날짜는 `meta` 에 따로 남긴다.
COVERS = {
    "tf58-0": "1945-03-14", "tf58-1": "1945-03-14", "tf58-2": "1945-03-17",
    "tf58-3": "1945-03-21", "tf58-4": "1945-04-11", "tf58-5": "1945-05-11",
}


def main():
    idx = {d["id"]: d for d in json.load(open(os.path.join(ROOT, "raw_docs/index.json")))}
    order = {d: i for i, d in enumerate(idx)}
    docs = []
    for path in sorted(glob.glob(os.path.join(ROOT, "tr", "*.json"))):
        t = json.load(open(path))
        did = t.get("doc_id") or os.path.basename(path)[:-5]
        meta = idx.get(did)
        if not meta:
            print("  건너뜀 (원문 없음):", did); continue
        grp, label, date = SRC[meta["src"]]
        shown = COVERS.get(did) or t.get("date") or date
        raw = open(os.path.join(ROOT, "raw_docs", did + ".txt")).read()
        docs.append({
            "id": did,
            "order": order.get(did, 999),
            "date": shown,
            "group": grp,
            "eyebrow": label,
            "title": t.get("title_ko") or t.get("title_en") or did,
            "list_right": meta["kind"],
            "meta": [m for m in (
                {"k": "다루는 시점", "v": shown},
                {"k": "문서 일자", "v": t.get("date") or date},
                {"k": "성격", "v": meta["kind"], "txt": True},
                {"k": "원제", "v": t.get("title_en"), "txt": True},
            ) if m.get("v")],
            "summary": t.get("subject_ko"),
            "points": t.get("key_points_ko") or [],
            "primary": t.get("ko") or "",
            "secondary": raw,
            "warn": t.get("confidence") not in (None, "high"),
            "search": " ".join(filter(None, [t.get("title_en"),
                                             " ".join(t.get("people") or [])])),
        })
    docs.sort(key=lambda d: (d["date"], d["order"]))   # 파일도 시간순으로 둔다
    out = os.path.join(ROOT, "reading", "docs.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(docs, open(out, "w"), ensure_ascii=False, indent=1)
    print(f"{len(docs)}건 → {out}  (확신 낮음 {sum(1 for d in docs if d['warn'])}건)")


if __name__ == "__main__":
    main()
