"""3단계: 번역 조각 → 읽을 수 있는 문서.

번역이 끝나기 전에도 돌아간다. 아직 안 된 조각은 '미번역'으로 표시하므로
진행 상황을 눈으로 확인하는 용도로도 쓴다.

    python assemble_docs.py documents.json tr_docs reading

산출물
    reading/index.md   건명별 → 시간순 목차
    reading/read.md    본문 (한국어 우선, 영문 접이식)
    reading/docs.json  질의용 구조화 데이터
"""
import glob, json, os, sys
from collections import defaultdict

DOCS = sys.argv[1] if len(sys.argv) > 1 else "documents.json"
TR = sys.argv[2] if len(sys.argv) > 2 else "tr_docs"
OUT = sys.argv[3] if len(sys.argv) > 3 else "reading"

TITLE = "091 : File 1 Korea, Nov 1946 – 26 Apr 1948"
SOURCE = ("국립국회도서관 디지털컬렉션 PID 9850431 · Records of General Headquarters "
          "Far East Command, Assistant Chief of Staff G-3 · Entry44 Box 53 Folder 1 · PDM")
THEME_ORDER = ["A. 조선경비대 무장·증강", "B. 한국군 창설·훈련",
               "C. 병참·편제", "D. 장래 정책·철군"]

os.makedirs(OUT, exist_ok=True)

docs = {d["doc_id"]: d for d in json.load(open(DOCS))}
chunks = defaultdict(list)
for f in sorted(glob.glob(os.path.join(TR, "D*_*.json"))):
    c = json.load(open(f))
    chunks[c["doc_id"]].append(c)
for v in chunks.values():
    v.sort(key=lambda c: c.get("chunk", 0))

# ---- 문서 단위로 합치기 ----
merged = []
for did, d in docs.items():
    cs = chunks.get(did, [])
    head = cs[0] if cs else {}
    planned = sum(1 for _ in range(head.get("of", 1))) if cs else None
    merged.append({
        "doc_id": did,
        "pages": d["pages"],
        "page_start": d["page_start"],
        "page_end": d["page_end"],
        "n_pages": d["n_pages"],
        "theme": d.get("theme"),
        "subject_id": d.get("subject_id"),
        "subject_title": d.get("subject_title"),
        "date": head.get("date") or d.get("date"),
        "doc_type": head.get("doc_type"),
        "classification": head.get("classification"),
        "from": head.get("from"), "to": head.get("to"), "info": head.get("info"),
        "msg_nr": head.get("msg_nr") or d.get("msg_nr"),
        "subject_ko": head.get("subject_ko") or "",
        "subject_en": head.get("subject") or "",
        "key_points_ko": [k for c in cs for k in (c.get("key_points_ko") or [])],
        "confidence": min((c.get("confidence") or "low" for c in cs),
                          key=lambda x: {"high": 0, "medium": 1, "low": 2}.get(x, 3),
                          default=None) if cs else None,
        "notes": " / ".join(c["notes"] for c in cs if c.get("notes")),
        "ko": "\n\n".join(c.get("ko") or "" for c in cs).strip(),
        "en": "\n\n".join(c.get("en") or "" for c in cs).strip(),
        "done": len(cs),
        "of": head.get("of", 1) if cs else None,
        "translated": bool(cs) and len(cs) == head.get("of", 1),
    })

merged.sort(key=lambda m: m["page_start"])
json.dump(merged, open(os.path.join(OUT, "docs.json"), "w"),
          ensure_ascii=False, indent=1)

done = [m for m in merged if m["translated"]]
part = [m for m in merged if m["done"] and not m["translated"]]
todo = [m for m in merged if not m["done"]]


def scan_link(m):
    return " ".join(f"[{p}](../pages/{p}.jpg)" for p in m["pages"][:6]) + \
           (" …" if m["n_pages"] > 6 else "")


# ---------------------------------------------------------------- index.md
by_theme = defaultdict(list)
for m in merged:
    by_theme[m["theme"] or "— 미분류 (기타 왕복문서)"].append(m)

with open(os.path.join(OUT, "index.md"), "w") as f:
    f.write(f"# {TITLE} — 목차\n\n출처: {SOURCE}\n\n")
    f.write(f"문서 {len(merged)}건 / {sum(m['n_pages'] for m in merged)}면 · "
            f"번역 완료 **{len(done)}건**, 진행 중 {len(part)}건, 대기 {len(todo)}건\n\n")
    f.write("> 이 문서철은 한 가지 주제다 — **철군하려면 대신할 군대가 필요하다.**\n"
            "> 1947년 11월 경비대 무장 논의로 시작해 1948년 4월 편제표와 병참으로 끝난다.\n\n---\n\n")

    order = THEME_ORDER + [k for k in by_theme if k not in THEME_ORDER]
    for th in order:
        ms = by_theme.get(th)
        if not ms:
            continue
        f.write(f"## {th}\n\n{len(ms)}건 / {sum(m['n_pages'] for m in ms)}면\n\n")
        f.write("| 날짜 | 문서 | 면 | 발신 → 수신 | 전문번호 | 요지 |\n|---|---|---|---|---|---|\n")
        for m in sorted(ms, key=lambda x: (x["date"] or "9999", x["page_start"])):
            route = " → ".join(x for x in (m["from"], m["to"]) if x) or "—"
            summ = m["subject_ko"] or ("*(미번역)*" if not m["done"] else "*(진행 중)*")
            f.write("| {d} | [{i}](read.md#{i}) | {a}–{b} | {r} | {n} | {s} |\n".format(
                d=m["date"] or "—", i=m["doc_id"],
                a=m["page_start"], b=m["page_end"],
                r=route.replace("|", "/")[:38], n=m["msg_nr"] or "—",
                s=summ.replace("|", "/")[:88]))
        f.write("\n")

    low = [m for m in done if m["confidence"] == "low"]
    if low:
        f.write(f"## ⚠️ 판독 신뢰도 낮음 ({len(low)}건)\n\n원본 스캔 대조가 필요하다.\n\n")
        f.write(", ".join(f"[{m['doc_id']}](read.md#{m['doc_id']})" for m in low) + "\n")

# ---------------------------------------------------------------- read.md
with open(os.path.join(OUT, "read.md"), "w") as f:
    f.write(f"# {TITLE}\n\n출처: {SOURCE}\n\n")
    f.write("한국어는 기계 번역이고 영문은 OCR을 교정한 것이다. "
            "인용하기 전에 반드시 원본 스캔과 대조할 것 — 각 문서에 스캔 링크를 달아 두었다.\n\n---\n\n")

    for m in merged:
        if not m["done"]:
            continue
        f.write(f'<a id="{m["doc_id"]}"></a>\n\n### {m["doc_id"]} · {m["page_start"]}–{m["page_end"]}면')
        if m["date"]:
            f.write(f" · {m['date']}")
        if m["classification"]:
            f.write(f" · `{m['classification']}`")
        f.write("\n\n")

        meta = [(k, m.get(v)) for k, v in
                (("발신", "from"), ("수신", "to"), ("참조", "info"), ("전문번호", "msg_nr"))]
        meta = [f"**{k}** {v}" for k, v in meta if v]
        if m["subject_title"]:
            meta.append(f"**건명** {m['subject_title']}")
        if meta:
            f.write(" · ".join(meta) + "\n\n")
        if m["subject_ko"]:
            f.write(f"> {m['subject_ko']}\n\n")
        for kp in m["key_points_ko"]:
            f.write(f"- {kp}\n")
        if m["key_points_ko"]:
            f.write("\n")
        f.write(f"<sub>스캔: {scan_link(m)}</sub>\n\n")

        if not m["translated"]:
            f.write(f"*⚠️ 이 문서는 {m['of']}조각 중 {m['done']}조각만 번역됨*\n\n")
        if m["ko"]:
            f.write(m["ko"] + "\n\n")
        if m["en"]:
            f.write("<details><summary>영문 원문 (OCR 교정본)</summary>\n\n```\n"
                    + m["en"] + "\n```\n\n</details>\n\n")
        if m["notes"]:
            f.write(f"*참고: {m['notes']}*\n\n")
        f.write("---\n\n")

print(f"문서 {len(merged)}건 · 완료 {len(done)} · 진행중 {len(part)} · 대기 {len(todo)}")
for th in THEME_ORDER + ["— 미분류 (기타 왕복문서)"]:
    ms = by_theme.get(th)
    if ms:
        d = sum(1 for m in ms if m["translated"])
        print(f"  {th:22} {d:2d}/{len(ms):2d}건 완료")
print(f"\n-> {OUT}/index.md, {OUT}/read.md, {OUT}/docs.json")
