"""번역 결과를 열람기 규격으로 바꾼다.

    python3 make_docs.py

이 문서철에는 **스캔이 없다.** CREST 원본은 아카이브닷오르그에 스캔이 있으나
저장소에 넣지 않았다(`조사/README.md` 참조). 그래서 `collection.json` 에
`pages` 를 두지 않는다 — 열람기는 그러면 썸네일과 확대 뷰어를 통째로 뺀다.

**오른쪽 창에 무엇을 놓을 것인가.** 이 문서철에는 텍스트가 셋이다.

    raw/<번호>.txt   기계가 읽어 낸 것. 뭉개져 있다
    tr/…["en"]       사람이 고친 영문
    tr/…["ko"]       번역

오른쪽에는 **교정본(`en`)** 을 놓는다. 뭉갠 원문을 그대로 붙이면 대조에 쓸 수가
없기 때문이다. 다만 교정도 판단이므로, 무엇을 고쳤는지는 `notes` 에 남고
원본은 `raw/` 에 그대로 있다. 원본 주소는 문서마다 `meta` 에 건다.
"""
import os, json, glob

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# 두 계열이다. 성격이 다르므로 묶음을 가른다.
GROUP = {"L": ("A", "1945 뉴욕 · OSS 외국인 전문가 조사"),
         "M": ("B", "1946 만주·북조선 · 현장 첩보보고"),
         "N": ("C", "1947 북조선 · 중앙정보단·중앙정보국 보고"),
         "P": ("D", "1948 두 정부 · 중앙정보국 보고")}


def main():
    idx = {d["doc_id"]: d for d in json.load(open(os.path.join(ROOT, "raw/index.json")))}
    order = {d: i for i, d in enumerate(idx)}
    docs, missing = [], []
    for path in sorted(glob.glob(os.path.join(ROOT, "tr", "*.json"))):
        try:
            t = json.load(open(path))
        except json.JSONDecodeError as e:
            print(f"!! {os.path.basename(path)} JSON 깨짐: {e}")
            continue
        did = t.get("doc_id") or os.path.basename(path)[:-5]
        meta = idx.get(did)
        if not meta:
            print("  건너뜀 (원문 없음):", did)
            continue
        if not (t.get("ko") or "").strip():
            print(f"!! {did} 본문이 비었다")
            continue
        grp, label = GROUP[did[0]]
        # 삭제·공개 표시는 각주로 올린다. **이 문서철에서는 그것이 내용이다** —
        # 누가 지워졌는지가 자료의 일부라서 본문에만 두고 넘기지 않는다.
        notes = [f"[삭제·공개 표시] {r}" for r in (t.get("redactions") or [])]
        docs.append({
            "id": did,
            "order": order.get(did, 999),
            "date": t.get("date") or meta["date"],
            "group": grp,
            "eyebrow": label,
            "title": t.get("title_ko") or t.get("title_en") or did,
            "badge": t.get("classification"),
            "list_right": t.get("doc_type"),
            "meta": [m for m in (
                {"k": "일자", "v": t.get("date") or meta["date"]},
                {"k": "발신", "v": t.get("from"), "txt": True},
                {"k": "수신", "v": t.get("to"), "txt": True},
                {"k": "종류", "v": t.get("doc_type")},
                {"k": "원제", "v": t.get("title_en"), "txt": True},
                {"k": "CREST 번호", "v": meta["crest"]},
            ) if m.get("v")],
            "links": [{"k": "CREST", "text": "아카이브닷오르그 원본",
                       "url": meta["url"]}],
            "summary": t.get("subject_ko"),
            "points": t.get("key_points_ko") or [],
            "primary": t.get("ko") or "",
            "secondary": t.get("en") or "",
            "notes": notes,
            "note": t.get("notes"),
            "warn": t.get("confidence") == "low",
            # 지워진 자리의 표시(`(b)(6)`, `25X1X6`)로도 찾아지게 한다.
            # 이 문서철에서는 **무엇이 가려졌는가가 곧 찾을 거리**다.
            "search": " ".join((t.get("people") or []) + (t.get("redactions") or [])
                               + [t.get("title_en") or ""]),
        })
    missing = [d for d in idx if d not in {x["id"] for x in docs}]
    docs.sort(key=lambda d: (d["date"], d["order"]))
    out = os.path.join(ROOT, "reading", "docs.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(docs, open(out, "w"), ensure_ascii=False, indent=1)
    print(f"문서 {len(docs)}건 → {out}")
    if missing:
        print(f"!! 빠짐 {len(missing)}건: {' '.join(missing)}")


if __name__ == "__main__":
    main()
