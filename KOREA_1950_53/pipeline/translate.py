"""FRUS 정본 → 한국어 번역. `pi` CLI로 호출한다.

    python3 pipeline/translate.py            # 남은 것 전부
    python3 pipeline/translate.py 50         # 1950년만
    python3 pipeline/translate.py 50 8       # 1950년 중 여덟 건만

**해마다 끊어서 한다.** PLAN.md 의 원칙이다 — 175건을 다 옮긴 뒤에 한꺼번에
올리지 않는다. 한 해가 끝나면 그 해만으로 문서철을 다시 짓고 배포한다.

**되도록 문서 하나를 통째로 넘긴다.** NDL 문서철은 OCR 면을 조각내 보냈지만
여기는 그럴 이유가 적다 — TEI 정본이라 문서 경계가 이미 정확하고, 회의록은
앞뒤를 같이 봐야 누가 무엇에 답한 것인지가 산다.

**다만 아주 긴 것은 나눈다.** 30,809자짜리 웨이크섬 회담록(`50-d680`)을 통째로
보냈더니 번역이 29,660자에서 잘려 나왔다. 모델의 출력 한도다. `MAX_CHARS` 를
넘으면 빈 줄에서 잘라 나눠 보내고 여기서 다시 붙인다. 자르는 자리는 문단
경계뿐이다 — 문장 중간에서 자르면 두 조각 다 못 쓰게 된다.

조각에는 **앞 조각의 끝 부분을 같이 보낸다.** 회의록에서 「그는 그렇게 보지
않는다고 답했다」의 「그」가 누구인지는 앞을 봐야 안다.

이어달리기 가능 — 이미 옮긴 것은 건너뛴다. 실패한 것만 다시 돌리면 된다.
"""
import json, os, re, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RAW, OUT = os.path.join(ROOT, "raw"), os.path.join(ROOT, "tr")
os.makedirs(OUT, exist_ok=True)

YEAR = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1].isdigit() else None
LIMIT = int(sys.argv[2]) if len(sys.argv) > 2 else None
WORKERS = int(os.environ.get("PI_WORKERS", "4"))
TIMEOUT = int(os.environ.get("PI_TIMEOUT", "1800"))
THINKING = os.environ.get("PI_THINKING", "off")
MAX_CHARS = int(os.environ.get("MAX_CHARS", "12000"))   # 이보다 길면 나눈다
TAIL = 700                                              # 조각에 딸려 보낼 앞 문맥

SPEC = open(os.path.join(HERE, "TRANSLATION_SPEC.md"), encoding="utf-8").read()
BASE = open(os.path.join(ROOT, "..", "KOREA_1948_50", "pipeline",
                         "TRANSLATION_SPEC.md"), encoding="utf-8").read()
STYLE = open(os.path.join(ROOT, "..", "열람기", "STYLE.md"), encoding="utf-8").read()

SYSTEM = f"""You translate US State Department records (FRUS) about the Korean War,
1950-1953, into Korean for a primary-source archive. Output ONE JSON object, nothing else.

The archive's rules follow. They are binding. Read them fully before translating.

===== 이 문서철의 규칙 =====
{SPEC}

===== 물려받은 공통 규칙 =====
{BASE}

===== 말투 =====
{STYLE}

Output the JSON object only. No prose before or after, no code fence."""


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


index = {d["doc_id"]: d for d in json.load(open(os.path.join(RAW, "index.json")))}


def split_body(text, limit):
    """빈 줄에서만 자른다. 한 문단이 limit 을 넘으면 그 문단은 통째로 둔다 —
    문장 중간에서 자르느니 조각 하나가 큰 편이 낫다."""
    if len(text) <= limit:
        return [text]
    parts, cur = [], ""
    for para in text.split("\n\n"):
        if cur and len(cur) + len(para) + 2 > limit:
            parts.append(cur)
            cur = para
        else:
            cur = f"{cur}\n\n{para}" if cur else para
    if cur:
        parts.append(cur)
    return parts


def call_pi(prompt):
    proc = subprocess.run(
        ["pi", "-p", "--no-session", "-nt", "--thinking", THINKING,
         "--system-prompt", SYSTEM, prompt],
        capture_output=True, text=True, timeout=TIMEOUT)
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or "")[-300:] or f"exit {proc.returncode}")
    return extract_json(proc.stdout), proc.stdout


def work(d):
    did = d["doc_id"]
    dst = os.path.join(OUT, did + ".json")
    if os.path.exists(dst):
        return ("cached", did)
    body = open(os.path.join(RAW, did + ".txt"), encoding="utf-8").read()

    ctx = [f"document id {did}", f"date {d.get('date')}",
           f"title as printed: {d.get('title')}", f"FRUS volume {d.get('vol')}"]
    if d.get("source_note"):
        ctx.append(f"source note: {d['source_note']}")
    if d.get("why"):
        # 고른 이유는 참고일 뿐이다. 여기 적힌 판단을 번역에 옮겨 심지 마라.
        ctx.append(f"why this document was selected (context only, do NOT let this "
                   f"colour the translation): {d['why']}")

    chunks = split_body(body, MAX_CHARS)
    out, raw_out = None, ""
    for attempt in range(3):
        try:
            parts = []
            for i, chunk in enumerate(chunks, 1):
                c = list(ctx)
                if len(chunks) > 1:
                    c.append(f"this is part {i} of {len(chunks)} of the document; "
                             f"translate ONLY the text between the --- markers. "
                             f"Put the running translation in \"ko\". "
                             + ("Fill every metadata field from the document head."
                                if i == 1 else
                                "Metadata fields (doc_type, from, to, msg_nr, "
                                "classification, source_note, title_en, title_ko, "
                                "subject_ko) may be null — part 1 already carries them."))
                    if i > 1:
                        c.append("preceding text, for reference only, already "
                                 "translated, do NOT translate again: "
                                 + chunks[i - 2][-TAIL:].replace("\n", " "))
                p = ("CONTEXT: " + "; ".join(c) + "\n\nFRUS text (authoritative, do "
                     "not correct):\n\n---\n" + chunk + "\n---")
                r, raw_out = call_pi(p)
                if not (r.get("ko") or "").strip():
                    raise ValueError(f"{i}번째 조각의 ko 가 비었다")
                parts.append(r)

            out = parts[0]
            if len(parts) > 1:
                out["ko"] = "\n\n".join(p["ko"].strip() for p in parts)
                for k in ("key_points_ko", "notes_ko", "people"):
                    seen, merged = set(), []
                    for p in parts:
                        for v in (p.get(k) or []):
                            if v not in seen:
                                seen.add(v)
                                merged.append(v)
                    out[k] = merged
                out["confidence"] = min((p.get("confidence") or "low" for p in parts),
                                        key=lambda x: {"high": 0, "medium": 1}.get(x, 2))
                out["notes"] = " / ".join(p["notes"] for p in parts if p.get("notes"))
                out["parts"] = len(parts)
            out["doc_id"] = did
            out.setdefault("date", d.get("date"))
            json.dump(out, open(dst, "w"), ensure_ascii=False, indent=1)
            return ("ok" if len(chunks) == 1 else f"ok({len(chunks)}조각)", did)
        except subprocess.TimeoutExpired:
            if attempt == 2:
                return ("timeout", did)
            time.sleep(5)
        except Exception as e:
            if attempt == 2:
                open(os.path.join(OUT, did + ".error.txt"), "w").write(
                    f"{type(e).__name__}: {e}\n\n--- stdout ---\n" + raw_out)
                return (f"fail:{type(e).__name__}", did)
            time.sleep(3 * (attempt + 1))


docs = [d for d in index.values() if not YEAR or d["doc_id"].startswith(YEAR + "-")]
docs.sort(key=lambda d: (d.get("date") or "", d["doc_id"]))
todo = [d for d in docs if not os.path.exists(os.path.join(OUT, d["doc_id"] + ".json"))]
batch = todo[:LIMIT] if LIMIT else todo

chars = sum(d.get("chars", 0) for d in batch)
print(f"대상 {len(docs)}건 · 남은 {len(todo)}건 · 이번에 {len(batch)}건 "
      f"({chars:,}자) · workers={WORKERS}", flush=True)
if not batch:
    sys.exit("옮길 것이 없다.")

stats, fails = {}, []
t0 = time.time()
with ThreadPoolExecutor(max_workers=WORKERS) as ex:
    for n, (status, did) in enumerate(ex.map(work, batch), 1):
        stats[status] = stats.get(status, 0) + 1
        if not status.startswith("ok"):
            fails.append((did, status))
        print(f"  {n}/{len(batch)}  {did:<12} {status:<16} "
              f"({time.time()-t0:.0f}초)", flush=True)

print(f"\n{time.time()-t0:.0f}초  {stats}")
if fails:
    print(f"실패 {len(fails)}: {fails[:10]}  — 다시 실행하면 실패분만 재시도")
