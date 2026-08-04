"""HyperWar 의 HTML 을 문서 단위 평문으로 뽑는다.

    python3 extract.py

이 문서철은 판독할 것이 없다. 미국 정부가 남긴 영문 평문이고 HTML 로 공개돼
있어서, 지금까지처럼 OCR 도 글자표도 필요 없다. 여기서 하는 일은 **자르는 것**뿐이다.

두 자료의 결이 다르다.

  심문조서   개요 한 덩이 + 문답 수십 쌍. 문답 한 쌍은 절대 가르지 않는다 —
             물음과 답이 갈리면 둘 다 뜻을 잃는다.
  작전 보고  번호 문단이 이어지는 보고서. 문단 경계에서만 자른다.

한 문서가 너무 길면 읽는 쪽도 옮기는 쪽도 감당이 안 되므로 9,000자 안팎으로
끊되, **뜻이 끊기는 자리에서는 자르지 않는다.**
"""
import os, re, json, html

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CHUNK = 9000


def plain(path):
    s = open(path, encoding="latin-1").read()
    s = re.sub(r"(?is)<(script|style).*?</\1>", " ", s)
    s = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</tr>|</h[1-6]>", "\n", s)
    s = re.sub(r"(?i)<p[^>]*>|<h[1-6][^>]*>", "\n", s)
    s = html.unescape(re.sub(r"[ \t]+", " ", re.sub("<[^>]+>", "", s)))
    out, prev = [], ""
    for l in s.split("\n"):
        l = l.strip()
        if l and l != prev:
            out.append(l)
        prev = l
    return out


def pack(units, limit=CHUNK):
    """뜻이 끊기지 않는 덩이들을 붙여 나가다 한도를 넘으면 새 묶음."""
    parts, cur, n = [], [], 0
    for u in units:
        if cur and n + len(u) > limit:
            parts.append("\n\n".join(cur)); cur, n = [], 0
        cur.append(u); n += len(u)
    if cur:
        parts.append("\n\n".join(cur))
    return parts


def toyoda():
    """도요다 심문조서 — 개요와 문답을 갈라 담는다."""
    lines = plain(os.path.join(ROOT, "raw/ussbs/IJO-75.html"))
    body = "\n".join(lines)
    i = body.find("SUMMARY")
    j = body.find("TRANSCRIPT")
    head = body[:i].strip()
    summary = body[i + 7:j].strip()
    tr = body[j + 10:].strip()
    # 문답 한 쌍을 한 덩이로. 「Q」 로 시작하는 줄에서 새 쌍이 열린다.
    units, cur = [], []
    for l in tr.split("\n"):
        if re.match(r"^Q[\s.:]", l) and cur:
            units.append("\n".join(cur)); cur = []
        cur.append(l)
    if cur:
        units.append("\n".join(cur))
    print(f"  도요다 · 개요 {len(summary):,}자 · 문답 {len(units)}쌍")
    docs = [{"id": "toyoda-0", "kind": "요약", "text": head + "\n\n" + summary}]
    for k, p in enumerate(pack(units), 1):
        docs.append({"id": f"toyoda-{k}", "kind": "문답", "text": p})
    return docs


def tf58():
    """제58기동부대 작전 보고 — 문단 경계에서만 자른다."""
    lines = plain(os.path.join(ROOT, "raw/usn/okinawa-tf58.html"))
    # 짧은 줄이 이어지는 머리(수신·참조·첨부)는 한 덩이로 묶어 둔다
    cut = next((i for i, l in enumerate(lines) if l.strip().upper() == "GENERAL"), 30)
    head = "\n".join(lines[:cut])
    units, cur = [], []
    for l in lines[cut:]:
        if re.match(r"^\d{1,2}\.\s+[A-Z]", l) and cur:
            units.append("\n".join(cur)); cur = []
        cur.append(l)
    if cur:
        units.append("\n".join(cur))
    # 번호 문단이 몇 개뿐이라 덩이가 너무 크면 빈 줄 단위로 다시 쪼갠다
    fine = []
    for u in units:
        if len(u) <= CHUNK * 1.6:
            fine.append(u); continue
        buf, n = [], 0
        for l in u.split("\n"):
            if buf and n + len(l) > CHUNK:
                fine.append("\n".join(buf)); buf, n = [], 0
            buf.append(l); n += len(l)
        if buf:
            fine.append("\n".join(buf))
    print(f"  TF58 · 머리 {len(head):,}자 · 본문 덩이 {len(fine)}개")
    docs = [{"id": "tf58-0", "kind": "표제", "text": head}]
    for k, p in enumerate(pack(fine), 1):
        docs.append({"id": f"tf58-{k}", "kind": "본문", "text": p})
    return docs


def main():
    out = os.path.join(ROOT, "raw_docs")
    os.makedirs(out, exist_ok=True)
    idx = []
    for src, docs in (("toyoda", toyoda()), ("tf58", tf58())):
        for d in docs:
            open(os.path.join(out, d["id"] + ".txt"), "w").write(d["text"])
            idx.append({"id": d["id"], "src": src, "kind": d["kind"],
                        "chars": len(d["text"])})
    json.dump(idx, open(os.path.join(out, "index.json"), "w"),
              ensure_ascii=False, indent=1)
    print(f"\n{len(idx)}건 · {sum(i['chars'] for i in idx):,}자 → {out}")
    for i in idx:
        print(f"  {i['id']:10} {i['kind']:4} {i['chars']:7,}자")


if __name__ == "__main__":
    main()
