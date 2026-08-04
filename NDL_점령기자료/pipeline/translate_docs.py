"""2단계: 문서 단위 교정 + 번역. `pi` CLI로 호출한다.

1단계(segment.py)가 잡은 문서 경계를 쓴다. 페이지 단위로 부르지 않는 이유:
  6면짜리 전문의 4번째 면만 떼어 보내면 모델은 무슨 건인지 모른다. SUBJECT 줄은
  1면에만 있기 때문이다. 문서째로 보내면 문맥이 붙고, 호출 수도 351 → 90 안팎으로 준다.

큰 문서는 나눈다. 133면짜리 계획서는 한 번에 못 보내므로 APPENDIX/ANNEX 경계를
우선해 조각내고, 조각마다 문서 메타데이터와 '몇 번째 조각인지'를 같이 넘긴다.

    python translate_docs.py documents.json ocr tr_docs [처리할 조각 수]

이어달리기 가능 — 이미 처리된 조각은 건너뛴다.
"""
import glob, json, os, re, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor

DOCS = sys.argv[1] if len(sys.argv) > 1 else "documents.json"
SRC = sys.argv[2] if len(sys.argv) > 2 else "ocr"
OUT = sys.argv[3] if len(sys.argv) > 3 else "tr_docs"
LIMIT = int(sys.argv[4]) if len(sys.argv) > 4 else None

WORKERS = int(os.environ.get("PI_WORKERS", "4"))
TIMEOUT = int(os.environ.get("PI_TIMEOUT", "900"))
THINKING = os.environ.get("PI_THINKING", "off")
MAX_PAGES = int(os.environ.get("MAX_PAGES", "4"))    # 조각당 최대 면 수

os.makedirs(OUT, exist_ok=True)

SYSTEM = """You process OCR output from declassified US military records about Korea, 1945-1950.

SOURCE: Records of General Headquarters Far East Command (GHQ/FEC), Assistant Chief of
Staff G-3. TOP SECRET radio/cable messages on teletype forms, staff memoranda, studies
with appendices, and T/O&E tables. Held by the National Diet Library of Japan (public domain).

This file is about one thing: building a South Korean army while planning US withdrawal,
Nov 1947 – Apr 1948.

Your job is CORRECTION and TRANSLATION, not reading. The OCR already read the pages.

## Task 1 — correct the English

Fix obvious OCR errors. Common confusions in this corpus:
  1s->is  1n->in  11st->list  or->of  ot->of  tor->for  Kores->Korea  Ary->Army
  INPO->INFO  CINCPE->CINCFE  rrom->from  adviseble->advisable  JOS->JCS
  USAPIK->USAFIK  Comnis-sion->Commission  0<->O and l/1/I and 5/S confusion

**Do not "correct" digit strings** — message numbers, declassification authority
numbers (NND…), dates, quantities, T/O&E numbers. Copy them exactly as the OCR gave
them, even when they look wrong. A wrong digit you invent is worse than one you preserve.

Preserve the document's physical structure: header block, FROM/TO/INFO/NR lines, numbered
paragraphs, signature blocks, stamps, table columns. Keep line breaks where they carry
meaning. Preserve original spelling of proper nouns even when archaic ("Chosen", "Keijo",
"Jap"). Do NOT modernize, summarize, paraphrase, or fix the author's grammar.

Where the OCR is too garbled to recover, write [illegible] — never invent text.
Discard scanning artifacts: the photographic ruler ("SEKISUI JUSHI", stray "200cm",
loose tick numbers) is not part of the document.

## Glossary (leave as-is; do not expand inline)

CINCFE  Commander in Chief, Far East        CG USAFIK  CG, US Army Forces in Korea
GHQ/FEC General HQ, Far East Command        SCAP  Supreme Commander Allied Powers
XXIV Corps  US corps in Korea               DA / WD  Dept of the Army / War Dept
JCS     Joint Chiefs of Staff               T/O&E  Table of Organization and Equipment
G-1/2/3/4  staff sections                   TOO  time of origin
MCN     message control number              NR  message number
UNTCOK  UN Temporary Commission on Korea    KMAG  Korean Military Advisory Group
WX, W, WARX  Washington cable prefixes      ZGCT, ZOCG  USAFIK cable prefixes

Place names appear in Japanese reading. Keep them; give the Korean name in the Korean
translation only: Keijo(경성) Jinsen(인천) Fusan(부산) Taikyu(대구) Koshu(광주)
Genzan(원산) Kanko(함흥) Seishin(청진) Heijo(평양) Kaijo(개성) Chosen(조선)

## Task 2 — translate to Korean

Natural Korean for a reader who knows the period. Keep military abbreviations in Latin
script with a Korean gloss in parentheses on first use. Render dates as written. Formal,
documentary register — this is an archival record, not prose. Mark [판독불가] where the
English has [illegible].

### Dense numeric tables — do not translate row by row

T/O&E and supply tables run to dozens of rows of stock numbers and quantities.
Transcribe them in full in "en", but in "ko" translate only the table title, the column
headers, and any rows carrying narrative content (remarks, totals, footnotes). For the
numeric body write one line stating how many rows there are and which item numbers they
span, e.g. "[품목 1~67, 총 67행 — 수치는 영문 원문 참조]". Repeating stock numbers in
Korean adds nothing and risks the response being truncated mid-output.

## Output

Return ONLY a JSON object. No prose before or after, no markdown fence.

{
  "doc_type": "cable|memorandum|study|annex|table|routing_slip|cover|other",
  "date": "YYYY-MM-DD or null",
  "from": "string or null",
  "to": "string or null",
  "info": "string or null",
  "msg_nr": "string or null",
  "classification": "TOP SECRET|SECRET|CONFIDENTIAL|RESTRICTED|null",
  "subject": "one-line English summary of THIS chunk",
  "subject_ko": "이 조각의 한 줄 한국어 요약",
  "en": "corrected English, with [[page NNNN]] markers kept where they appear",
  "ko": "한국어 번역, [[면 NNNN]] 표기로 면 경계 유지",
  "entities": {"people": [], "places": [], "units": []},
  "key_points_ko": ["이 조각의 핵심 논점 1~4개, 각 한 문장"],
  "confidence": "high|medium|low",
  "notes": "재구성했거나 불확실한 부분. 없으면 빈 문자열"
}

If the chunk is a cover sheet, ruler-only page, or unreadable, say so via doc_type and
confidence "low". Do not fabricate content."""


def pi_args():
    return ["pi", "-p", "--no-session", "-nt", "--thinking", THINKING,
            "--system-prompt", SYSTEM]


def extract_json(raw):
    s = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.M).strip()
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass
    start = s.find("{")
    if start < 0:
        raise ValueError("no JSON object in output")
    depth, in_str, esc = 0, False, False
    for i, ch in enumerate(s[start:], start):
        if in_str:
            esc = (ch == "\\") and not esc
            if ch == '"' and not esc:
                in_str = False
        elif ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return json.loads(s[start:i + 1])
    raise ValueError("unbalanced JSON object")


# ---------------------------------------------------------------- 조각 만들기

docs = json.load(open(DOCS))
sect_at = {}
for d in docs:
    for s in d.get("sections", []):
        sect_at.setdefault(s["page"], s["label"])

PLAN = os.path.join(OUT, "_chunks.json")


def build_plan():
    plan = []
    for d in docs:
        pages = d["pages"]
        if len(pages) <= MAX_PAGES:
            parts = [pages]
        else:
            # 부록·별지 경계에서 우선 끊고, 그래도 길면 MAX_PAGES로 자른다.
            parts, cur = [], []
            for pg in pages:
                if cur and (pg in sect_at or len(cur) >= MAX_PAGES):
                    parts.append(cur)
                    cur = []
                cur.append(pg)
            if cur:
                parts.append(cur)
        for i, part in enumerate(parts, 1):
            plan.append({"doc_id": d["doc_id"], "idx": i, "of": len(parts),
                         "pages": part, "section": sect_at.get(part[0])})
    return plan


# 조각 계획은 한 번 만들면 파일로 고정한다.
#   MAX_PAGES를 도중에 바꾸면 경계가 이동해, 이미 끝난 조각과 새 조각이 같은 면을
#   중복해서 덮는다. 계획을 저장해 두면 환경변수를 바꿔도 흔들리지 않는다.
#   의도적으로 다시 짜려면 _chunks.json을 지우고 출력물도 함께 비울 것.
if os.path.exists(PLAN):
    plan = json.load(open(PLAN))
else:
    plan = build_plan()
    json.dump(plan, open(PLAN, "w"), ensure_ascii=False, indent=1)
    print(f"조각 계획 생성: {len(plan)}개 (MAX_PAGES={MAX_PAGES}) → {PLAN}")

by_id = {d["doc_id"]: d for d in docs}
chunks = [dict(c, doc=by_id[c["doc_id"]]) for c in plan]

# 계획과 어긋나는 기존 출력물을 찾아낸다 (계획 변경 전에 만들어진 것)
stale = []
for c in chunks:
    f = os.path.join(OUT, f"{c['doc_id']}_{c['idx']:02d}.json")
    if os.path.exists(f):
        try:
            if json.load(open(f)).get("pages") != c["pages"]:
                stale.append(f)
        except Exception:
            stale.append(f)
orphan = [f for f in glob.glob(os.path.join(OUT, "D*_*.json"))
          if os.path.basename(f)[:-5] not in
          {f"{c['doc_id']}_{c['idx']:02d}" for c in chunks}]
if stale or orphan:
    print(f"!! 계획과 어긋나는 출력물 {len(stale)+len(orphan)}개 — 지우고 다시 만들 것:")
    for f in (stale + orphan)[:10]:
        print("   ", f)
    sys.exit(1)


def work(c):
    d = c["doc"]
    cid = f"{d['doc_id']}_{c['idx']:02d}"
    dst = os.path.join(OUT, f"{cid}.json")
    if os.path.exists(dst):
        return ("cached", cid)

    body = []
    for pg in c["pages"]:
        t = open(os.path.join(SRC, f"{pg}.txt")).read().strip()
        body.append(f"[[page {pg}]]\n{t}")
    text = "\n\n".join(body)
    if len(text) < 40:
        json.dump({"doc_id": d["doc_id"], "chunk": c["idx"], "pages": c["pages"],
                   "doc_type": "other", "en": text, "ko": "", "confidence": "low",
                   "subject": "", "subject_ko": "", "key_points_ko": [],
                   "notes": "OCR 결과가 거의 없음"}, open(dst, "w"),
                  ensure_ascii=False, indent=1)
        return ("empty", cid)

    ctx = [f"Document {d['doc_id']}, pages {c['pages'][0]}–{c['pages'][-1]}"]
    if c["of"] > 1:
        ctx.append(f"chunk {c['idx']} of {c['of']} of this document")
    if c["section"]:
        ctx.append(f"begins at {c['section']}")
    if d.get("subject_title"):
        ctx.append(f"file subject: {d['subject_title']}")
    if d.get("subject_raw"):
        ctx.append(f"SUBJECT line as OCR'd: {d['subject_raw']}")
    if d.get("date"):
        ctx.append(f"date seen on page: {d['date']}")
    if d.get("msg_nr"):
        ctx.append(f"message nr: {d['msg_nr']}")

    prompt = "CONTEXT: " + "; ".join(ctx) + "\n\nOCR output:\n\n---\n" + text + "\n---"

    for attempt in range(3):
        proc = None
        try:
            proc = subprocess.run(pi_args() + [prompt], capture_output=True,
                                  text=True, timeout=TIMEOUT)
            if proc.returncode != 0:
                raise RuntimeError((proc.stderr or "")[-200:] or f"exit {proc.returncode}")
            r = extract_json(proc.stdout)
            r.update({"doc_id": d["doc_id"], "chunk": c["idx"], "of": c["of"],
                      "pages": c["pages"], "section": c["section"],
                      "subject_id": d.get("subject_id"), "theme": d.get("theme")})
            json.dump(r, open(dst, "w"), ensure_ascii=False, indent=1)
            return ("ok", cid)
        except subprocess.TimeoutExpired:
            if attempt == 2:
                return ("timeout", cid)
            time.sleep(5)
        except Exception as e:
            if attempt == 2:
                open(os.path.join(OUT, f"{cid}.error.txt"), "w").write(
                    f"{type(e).__name__}: {e}\n\n--- stdout ---\n"
                    + (proc.stdout if proc else ""))
                return (f"fail:{type(e).__name__}", cid)
            time.sleep(3 * (attempt + 1))


todo = [c for c in chunks
        if not os.path.exists(os.path.join(OUT, f"{c['doc']['doc_id']}_{c['idx']:02d}.json"))]
batch = todo[:LIMIT] if LIMIT else todo

print(f"문서 {len(docs)}건 → 조각 {len(chunks)}개 · 남은 {len(todo)} · 이번에 {len(batch)}"
      f"  ·  workers={WORKERS} max_pages={MAX_PAGES}")
if not batch:
    sys.exit("처리할 조각이 없다.")

stats, fails = {}, []
t0 = time.time()
with ThreadPoolExecutor(max_workers=WORKERS) as ex:
    for n, (status, cid) in enumerate(ex.map(work, batch), 1):
        stats[status] = stats.get(status, 0) + 1
        if status not in ("ok", "cached", "empty"):
            fails.append((cid, status))
        if n % 10 == 0 and len(batch) > 10:
            print(f"  {n}/{len(batch)}  {stats}  ({time.time()-t0:.0f}s)")

print(f"\n{time.time()-t0:.0f}초  {stats}")
if fails:
    print(f"실패 {len(fails)}: {fails[:8]}  — 다시 실행하면 실패분만 재시도")
