"""『日本外交文書 日米交渉―1941年― 下巻』 → 열람기 규격의 docs.json.

    python3 make_docs.py

다른 문서철과 다른 점이 하나 있다. **정본 원문이 파일로 따로 없다.**
FRUS 는 TEI 정본을 raw/ 에 두고 열람기가 그것을 붙이지만, 이 자료는
스캔 이미지뿐이라 사람이 지면을 보고 옮긴 것이 곧 정본이다. 그래서
번역 파일의 `ja` 를 원문 칸에 놓는다.

읽는 것   tr/*.json (원문 + 번역) · pages/*.png (지면)
쓰는 것   reading/docs.json
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TR = os.path.join(ROOT, "tr")
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "reading", "docs.json")

def group_of(d):
    """종류로 나누면 뜻이 없다 — 이 문서철은 거의 전부 전보다.
    **어디서 어디로 갔는가**로 나눈다. 그래야 노무라의 보고만, 또는 도고의
    훈령만 따라 읽을 수 있다."""
    frm = (d.get("from") or "")
    to = (d.get("to") or "")
    both = frm + " " + to
    if "各" in to or "公館長" in to:            # 회람
        return "E"
    if "独" in both or "伊" in both or "大島" in both:   # 베를린·로마
        return "C"
    if "中国" in both or "日高" in both or "汪" in both:  # 난징
        return "D"
    if "野村" in frm or "来栖" in frm:          # 워싱턴 → 도쿄
        return "A"
    if "東郷" in frm:                           # 도쿄 → 워싱턴
        return "B"
    return "X"

out, skipped = [], []
for f in sorted(os.listdir(TR)):
    if not f.endswith(".json"):
        continue
    try:
        d = json.load(open(os.path.join(TR, f)))
    except json.JSONDecodeError as e:
        print(f"!! {f} JSON 깨짐: {e}")
        continue

    ja = (d.get("ja") or "").strip()
    ko = (d.get("ko") or "").strip()
    # 조립하다 만 파일을 실으면 반쪽짜리 사료가 된다. 이어붙이기용 표지가
    # 남아 있거나 한쪽이 비어 있으면 싣지 않고 이름을 남긴다.
    # 길이로는 거르지 않는다 — 한 줄짜리 전보도 사료다.
    if "<<" in ja or "<<" in ko or not ja or not ko:
        skipped.append(f[:-5]); continue

    no = d.get("doc_no") or f[:-5]
    pages = d.get("pages") or []
    m = re.search(r"(\d+)$", str(no))
    order = int(m.group(1)) if m else 9999

    out.append({
        "id": str(no),
        "order": order,
        "date": d.get("date"),
        "group": group_of(d),
        "eyebrow": f"문서 {no} · {d.get('title_ja') or ''}",
        "title": d.get("title_ko") or d.get("title_ja") or str(no),
        "list_right": f"문서 {no}",
        "meta": [
            {"k": "일자", "v": d.get("date")},
            {"k": "원문 표기", "v": d.get("date_src")},
            {"k": "전보번호", "v": d.get("msg_nr")},
            {"k": "발신", "v": d.get("from"), "txt": True},
            {"k": "수신", "v": d.get("to"), "txt": True},
            {"k": "발신·착신", "v": d.get("sent_recv"), "txt": True, "wide": True},
            {"k": "종류", "v": d.get("doc_type")},
            {"k": "표제", "v": d.get("title_ja"), "txt": True, "wide": True},
        ],
        "summary": d.get("subject_ko"),
        "points": d.get("key_points_ko") or [],
        "primary": ko,
        "secondary": ja,
        "notes": d.get("notes_ko") or [],
        "warn": d.get("confidence") != "high",
        "pages": pages,
        "search": " ".join(d.get("people") or []),
    })

out.sort(key=lambda x: (x.get("date") or "9999", x["order"]))
os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump(out, open(OUT, "w"), ensure_ascii=False, indent=1)
print(f"문서 {len(out)}건 → {OUT}")
if skipped:
    print(f"!! 아직 덜 된 것 {len(skipped)}건: {' '.join(skipped)}")
