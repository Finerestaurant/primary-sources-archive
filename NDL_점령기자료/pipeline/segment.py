"""1단계: OCR 텍스트만으로 면 → 문서 → 건명(SUBJECT) 구조를 잡는다.

비용 0. 모델을 부르지 않는다. 규칙과 문자열 유사도만 쓴다.

왜 필요한가:
  이 문서철은 351면이지만 문서는 그보다 훨씬 적고, 한 문서가 최대 9면까지 이어진다.
  6면짜리 문서의 4번째 면만 떼어 번역하면 모델은 무슨 건에 대한 문서인지 모른다 —
  SUBJECT 줄은 1면에만 있기 때문이다. 그래서 번역 전에 먼저 묶어야 한다.

건명 11개는 NDL이 서지에 매긴 것(dcndl:alternative)을 그대로 쓴다.

    python segment.py ocr documents.json
"""
import glob, json, os, re, sys
from collections import Counter, defaultdict

SRC = sys.argv[1] if len(sys.argv) > 1 else "ocr"
OUT = sys.argv[2] if len(sys.argv) > 2 else "documents.json"

# NDL 서지의 dcndl:alternative — 이 문서철의 건명 목록
SUBJECTS = [
    ("A1", "1947-11-04", "Arming of South Korean Constabulary", "경비대"),
    ("A2", "1948-04-14", "T/O&E's for Security Forces in South Korea", "경비대"),
    ("A3", "1948-04-16", "Brief of JCS 1483/51, Augmentation and Equipping of South Korean Constabulary", "경비대"),
    # NDL 서지에는 없으나 본문에서 독립 건명으로 반복되는 것. 왕복이 가장 잦다.
    ("A4", None, "Augmentation of South Korean Constabulary", "경비대"),
    ("B1", "1947-11-17", "Preliminary Aspects Concerning Proposed Plans for Training a South Korean Army", "한국군"),
    ("B2", "1947-11-19", "Training of the South Korean Army", "한국군"),
    ("B3", "1947-12-01", "Notes on South Korean Army For Trip to Korea", "한국군"),
    ("B4", "1947-12-05", "Establishment of a South Korean Army", "한국군"),
    ("C1", "1948-03-01", "Logistic Requirements for the Korean Army", "병참"),
    ("D1", "1947-11-25", "Views and Comments for the Determination of Future Korea Policy", "정책"),
    ("D2", "1947-12-01", "Future Policy in Korea", "정책"),
    ("D3", "1948-01-26", "Withdrawal from Korea", "정책"),
]

THEMES = {"경비대": "A. 조선경비대 무장·증강", "한국군": "B. 한국군 창설·훈련",
          "병참": "C. 병참·편제", "정책": "D. 장래 정책·철군"}

# OCR이 자주 뭉개는 글자쌍. 정규화해서 비교한다.
OCR_MAP = str.maketrans("018|", "olbl")
STOP = {"the", "for", "and", "of", "a", "an", "in", "on", "to", "s", "from", "with"}

# 건명 매칭 기준.
#   이 문서철에서 army(49%) from(47%) korean(43%)은 거의 모든 면에 나와 변별력이 없고,
#   withdrawal(11%) arming(1.1%) trip(0.6%)이 실제 신호다. 그래서 단순 일치율 대신
#   IDF로 가중하고, "희귀어가 최소 하나는 맞아야 한다"는 조건을 건다.
#   이 조건이 없으면 'Withdrawal from Korea'가 korea+from만으로 37건에 오탐된다.
RARE_DF = 0.15      # 이 비율 미만으로 등장하는 낱말을 '희귀어'로 본다
MIN_SCORE = 0.50    # IDF 가중 일치율 하한


def norm(s):
    s = s.lower().translate(OCR_MAP)
    return re.sub(r"[^a-z ]", " ", s)


def toks(s):
    return {w for w in norm(s).split() if len(w) > 3 and w not in STOP}


def near(w, vocab):
    """편집거리 1 이내면 같은 낱말로 본다 (OCR 한 글자 오류 흡수)."""
    if w in vocab:
        return True
    for v in vocab:
        if abs(len(v) - len(w)) > 1:
            continue
        if len(v) == len(w):
            if sum(a != b for a, b in zip(v, w)) <= 1:
                return True
        else:
            lo, hi = (w, v) if len(w) < len(v) else (v, w)
            for i in range(len(hi)):
                if hi[:i] + hi[i + 1:] == lo:
                    return True
    return False


# ---------------------------------------------------------------- 적재

pages = []
for f in sorted(glob.glob(os.path.join(SRC, "*.txt"))):
    pg = os.path.splitext(os.path.basename(f))[0]
    raw = open(f).read()
    pages.append({"page": pg, "raw": raw, "vocab": toks(raw), "chars": len(raw.strip())})

# ---------------------------------------------------------------- 경계 판정

RE_PAGEOF = re.compile(r"\bPage\s+(\d+)\s+of\s+(\d+)", re.I)
RE_FROM = re.compile(r"\bFROM\s*[:.]", re.I)
RE_TO = re.compile(r"\bTO\s*[:.]", re.I)
RE_NR = re.compile(r"\bNR\s*[:.]\s*([A-Z]{1,4}\s?\d{3,6})", re.I)
RE_SUBJ = re.compile(r"^\s*SUBJECT\s*[:.]\s*(.{6,110})", re.I | re.M)
RE_MEMO = re.compile(r"\bMEMORANDUM\b|\bM/R\b", re.I)
# 전문이 여러 면에 걸치면 각 면에 머리를 되풀이하고 CONTINUED를 붙인다.
# 이걸 새 문서로 보면 하나의 전문이 조각난다.
RE_CONT = re.compile(r"\bCONTINUED\b|\bCONT\s*['\u2019]?D\b", re.I)
RE_DATE = re.compile(r"\b(\d{1,2})\s*(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s*(4[5-9])\b", re.I)
MON = dict(zip("jan feb mar apr may jun jul aug sep oct nov dec".split(), range(1, 13)))


def dates_in(t):
    out = []
    for m in RE_DATE.finditer(t):
        d, mo, y = int(m.group(1)), MON[m.group(2).lower()[:3]], 1900 + int(m.group(3))
        if 1 <= d <= 31:
            out.append(f"{y}-{mo:02d}-{d:02d}")
    return sorted(set(out))


for p in pages:
    t = p["raw"]
    m = RE_PAGEOF.search(t)
    p["page_of"] = (int(m.group(1)), int(m.group(2))) if m else None
    p["has_hdr"] = bool(RE_FROM.search(t) and RE_TO.search(t))
    nr = RE_NR.search(t)
    p["nr"] = re.sub(r"\s+", " ", nr.group(1)).strip() if nr else None
    sj = RE_SUBJ.search(t)
    p["subj_raw"] = re.sub(r"\s+", " ", sj.group(1)).strip(" .:_-") if sj else None
    p["memo"] = bool(RE_MEMO.search(t))
    p["continued"] = bool(RE_CONT.search(t[:400]))
    p["dates"] = dates_in(t)

    # 자 눈금·비밀해제 도장만 있는 면은 실질 내용이 없다
    body = re.sub(r"DECLASSIFIED|Authority\s+\S+|SEKISUI\s+JUSHI|\d+", " ", t, flags=re.I)
    p["thin"] = len(re.sub(r"[^A-Za-z]", "", body)) < 60


def starts_doc(p, prev):
    if p["page_of"]:
        return p["page_of"][0] == 1, f"page 1 of {p['page_of'][1]}"
    if p["thin"]:
        return False, "thin (ruler/stamp only)"
    if p["continued"] and prev is not None:
        return False, "CONTINUED"
    if p["has_hdr"] or p["nr"]:
        return True, "cable header"
    if p["subj_raw"] and p["memo"]:
        return True, "memo header"
    if prev is None:
        return True, "first page"
    return False, "continuation"


docs, cur = [], None
for i, p in enumerate(pages):
    prev = pages[i - 1] if i else None
    new, why = starts_doc(p, prev)
    if new or cur is None:
        cur = {"pages": [], "signals": []}
        docs.append(cur)
    cur["pages"].append(p)
    cur["signals"].append(why)

# ---------------------------------------------------------------- 부록·별지 구조

# 대형 계획서는 APPENDIX / ANNEX 로 내부가 나뉜다. PART·TAB·SECTION 은
# "DEPARTMENT"→"PART MENT", "TABLE"→"TAB LE" 같은 오탐이 많아 쓰지 않는다.
RE_SECT = re.compile(r"^\s*(APPENDIX|ANNEX)\s*[#No.]*\s*([A-H]|\d{1,2})\b\s*[-–—:.]?\s*(.{0,70})",
                     re.I | re.M)

for p in pages:
    ms = RE_SECT.findall(p["raw"])
    # 한 면에 넷 이상 나오면 절 시작이 아니라 그 계획서의 목차 면이다.
    p["is_toc"] = len(ms) >= 4
    p["sections"] = [] if p["is_toc"] else [
        {"label": f"{k.upper()} {n.upper()}", "title": re.sub(r"\s+", " ", t).strip(" -–—:.")}
        for k, n, t in ms[:2]
    ]
    p["toc_entries"] = [
        {"label": f"{k.upper()} {n.upper()}", "title": re.sub(r"\s+", " ", t).strip(" -–—:.")}
        for k, n, t in ms
    ] if p["is_toc"] else []

# ---------------------------------------------------------------- 건명 배정

import math

N = len(pages)
df = Counter()
for p in pages:
    df.update(p["vocab"])


def weight(w):
    return math.log(N / max(df.get(w, 0), 1) + 1)


SIG = [(sid, date, title, theme, toks(title)) for sid, date, title, theme in SUBJECTS]

out = []
for n, d in enumerate(docs, 1):
    subj0 = next((p["subj_raw"] for p in d["pages"] if p["subj_raw"]), None)

    # 무엇에 대고 매칭할 것인가가 핵심이다.
    #   문서 전체 면의 낱말을 합치면 133면짜리 계획서는 모든 낱말을 갖게 되어
    #   어느 건명에나 걸린다. 문서의 정체는 SUBJECT 줄과 첫 면에 있으므로
    #   SUBJECT가 있으면 그것만, 없으면 앞 두 면만 본다.
    if subj0:
        vocab, basis = toks(subj0), "subject line"
    else:
        vocab = set().union(*(p["vocab"] for p in d["pages"][:2]))
        basis = "first pages"

    scores = []
    for sid, date, title, theme, kw in SIG:
        matched = [w for w in kw if near(w, vocab)]
        wsum = sum(weight(w) for w in kw)
        got = sum(weight(w) for w in matched)
        # 희귀어가 하나도 안 맞으면 흔한 낱말만 겹친 것이므로 매칭으로 치지 않는다.
        has_rare = any(df.get(w, 0) / N < RARE_DF for w in matched)
        scores.append(((got / wsum if wsum else 0.0) * (1 if has_rare else 0.0),
                       sid, date, title, theme))
    scores.sort(reverse=True)
    best = scores[0]

    all_dates = sorted(set(x for p in d["pages"] for x in p["dates"]))
    subj = subj0
    nr = next((p["nr"] for p in d["pages"] if p["nr"]), None)

    ok = best[0] >= MIN_SCORE
    sections = [dict(s, page=p["page"]) for p in d["pages"] for s in p["sections"]]
    toc = [dict(t, page=p["page"]) for p in d["pages"] for t in p["toc_entries"]]

    out.append({
        "doc_id": f"D{n:03d}",
        "page_start": d["pages"][0]["page"],
        "page_end": d["pages"][-1]["page"],
        "n_pages": len(d["pages"]),
        "pages": [p["page"] for p in d["pages"]],
        "start_signal": d["signals"][0],
        "msg_nr": nr,
        "subject_raw": subj,
        "subject_id": best[1] if ok else None,
        "subject_title": best[3] if ok else None,
        "theme": THEMES[best[4]] if ok else None,
        "match_score": round(best[0], 2),
        "match_basis": basis,
        "dates": all_dates,
        "date": all_dates[0] if all_dates else None,
        "chars": sum(p["chars"] for p in d["pages"]),
        "toc_page": toc[0]["page"] if toc else None,
        "toc": toc,
        "sections": sections,
    })

json.dump(out, open(OUT, "w"), ensure_ascii=False, indent=1)

# ---------------------------------------------------------------- 검증용 요약

print(f"351면 → 문서 {len(out)}건\n")
print("문서당 면 수:", dict(sorted(Counter(d["n_pages"] for d in out).items())))
print("경계 신호   :", dict(Counter(d["start_signal"] for d in out).most_common()))

matched = [d for d in out if d["subject_id"]]
print(f"\n건명 배정: {len(matched)}/{len(out)}건 ({len(matched)/len(out):.0%})")
by_theme = defaultdict(list)
for d in matched:
    by_theme[d["theme"]].append(d)
for th in sorted(by_theme):
    ds = by_theme[th]
    print(f"\n{th}  — {len(ds)}건 / {sum(x['n_pages'] for x in ds)}면")
    for sid in sorted({x["subject_id"] for x in ds}):
        sub = [x for x in ds if x["subject_id"] == sid]
        title = sub[0]["subject_title"]
        pgs = sum(x["n_pages"] for x in sub)
        print(f"   {sid}  {len(sub):2d}건 {pgs:3d}면  {title[:62]}")

un = [d for d in out if not d["subject_id"]]
print(f"\n미배정 {len(un)}건 / {sum(d['n_pages'] for d in un)}면")
print("  ", [f"{d['doc_id']}({d['page_start']},{d['n_pages']}p)" for d in un[:18]])

big = [d for d in out if d["toc"] or len(d["sections"]) >= 2]
if big:
    print("\n=== 내부 절 구조가 있는 문서 ===")
    for d in big:
        print(f"\n{d['doc_id']}  {d['page_start']}-{d['page_end']} ({d['n_pages']}면)"
              f"  {d['subject_title'] or d['subject_raw'] or ''}")
        if d["toc"]:
            print(f"  목차 면 {d['toc_page']}:")
            for t in d["toc"]:
                print(f"    {t['label']:12} {t['title'][:58]}")
        seen = set()
        body = [s for s in d["sections"]
                if not (s["label"] in seen or seen.add(s["label"]))]
        if body:
            print("  본문 절 시작 면:", ", ".join(f"{s['label']}@{s['page']}" for s in body[:14]))

print(f"\n-> {OUT}")
