"""면별 머리 정보를 한 파일로 모은다 — 문서 경계를 잡기 위한 보조 자료.

    python3 page_digest.py ../ocr ../raw/page_digest.txt

이 문서철은 편철이 시간순이 아니다. 1945년 11월 문서 다음에 1946년 3월 문서가
오고, 한 문서가 여러 면에 걸친다. 색인(LIST OF PAPERS)이 있긴 하지만 본문 면에
일련번호가 찍혀 있지 않아 자동으로 짝지을 수가 없다.

그래서 면마다 「문서가 여기서 시작하는가」를 판단할 근거만 추려 낸다 —
날짜·발신·수신·전문번호·건명, 그리고 첫 몇 줄. 사람(또는 에이전트)이 이걸
순서대로 읽으면서 경계를 정한다. NDL 자료에서 쓴 자동 분할(segment.py)은
전문 용지가 규칙적이어서 통했지만, 여기는 서한·각서·전문이 섞여 있어 안 통한다.
"""
import glob
import os
import re
import sys

SRC = sys.argv[1] if len(sys.argv) > 1 else "../ocr"
OUT = sys.argv[2] if len(sys.argv) > 2 else "../raw/page_digest.txt"

MONTH = (r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*")
DATE = re.compile(rf"\b(\d{{1,2}}\s+{MONTH}\.?\s+(?:19)?4[5-7])\b")
DATE2 = re.compile(rf"\b({MONTH}\.?\s+\d{{1,2}},?\s+(?:19)?4[5-7])\b")
NR = re.compile(r"\b((?:CAX|CA|WX|W|TFGCG|TFYCG|SCAP|WARX)\s*[#]?\s*\d{3,6})\b")
JCS = re.compile(r"\b(?:JCS|SWNCC|SINCC|SWINCC)\s*\d+(?:/\d+)?", re.I)
FROM = re.compile(r"^\s*FROM\s*:\s*(.+)$", re.M)
TO = re.compile(r"^\s*TO\s*:\s*(.+)$", re.M)
SUBJ = re.compile(r"SUBJECT\s*:\s*(.+)")
PG = re.compile(r"^\s*-\s*(\d{1,2})\s*-\s*$", re.M)


def head(t, n=6):
    """머리글로 쓸 만한 첫 몇 줄. 도장·잡음 줄은 건너뛴다."""
    out = []
    for ln in (l.strip() for l in t.splitlines()):
        if len(ln) < 3 or re.fullmatch(r"[-—_. ]+", ln):
            continue
        if re.fullmatch(r"(?:TOP\s+)?SECRET\b.*", ln, re.I) and len(ln) < 20:
            continue
        out.append(ln)
        if len(out) >= n:
            break
    return out


rows = []
for f in sorted(glob.glob(os.path.join(SRC, "*.txt"))):
    p = os.path.basename(f)[:-4]
    t = open(f).read()
    d = DATE.search(t) or DATE2.search(t)
    rows.append({
        "page": p,
        "date": d.group(1) if d else "",
        "from": (FROM.search(t).group(1).strip()[:34] if FROM.search(t) else ""),
        "to": (TO.search(t).group(1).strip()[:34] if TO.search(t) else ""),
        "subj": (SUBJ.search(t).group(1).strip()[:60] if SUBJ.search(t) else ""),
        "nr": " ".join(sorted({m.group(1) for m in NR.finditer(t)})[:3]),
        "ref": " ".join(sorted({m.group(0) for m in JCS.finditer(t)})[:2]),
        "pgno": (PG.search(t).group(1) if PG.search(t) else ""),
        "hq": "HQ" if re.search(r"HEADQUARTERS", t) else "",
        "msg": "MSG" if re.search(r"(?:INCOMING|OUTGOING)\s+MESSAGE", t, re.I) else "",
        "chars": len(t),
        "head": head(t),
    })

os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
with open(OUT, "w") as f:
    f.write("면별 머리 정보 — 문서 경계를 잡기 위한 보조 자료\n")
    f.write("pgno 는 그 면에 찍힌 쪽번호다. 1 이면 문서가 거기서 시작할 가능성이 높다.\n")
    f.write("=" * 96 + "\n\n")
    for r in rows:
        tags = " ".join(x for x in (r["hq"], r["msg"],
                                    f"p.{r['pgno']}" if r["pgno"] else "") if x)
        f.write(f"[{r['page']}] {r['date'] or '(날짜 없음)':<22} {tags}\n")
        for k, label in (("from", "발신"), ("to", "수신"), ("subj", "건명"),
                         ("nr", "전문번호"), ("ref", "참조")):
            if r[k]:
                f.write(f"    {label}: {r[k]}\n")
        for ln in r["head"]:
            f.write(f"    | {ln[:88]}\n")
        f.write("\n")

start = sum(1 for r in rows if r["pgno"] == "1")
print(f"면 {len(rows)}개 -> {OUT}")
print(f"  날짜 잡힌 면 {sum(1 for r in rows if r['date'])}개 · "
      f"쪽번호 1 인 면 {start}개 · 건명 있는 면 {sum(1 for r in rows if r['subj'])}개")
