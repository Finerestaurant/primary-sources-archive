"""고를 거리를 뽑는다. **본문은 아직 받지 않는다.**

    python3 frus_scan.py

전쟁 세 해의 조선 관계 문서는 900건이 넘는다. 전부 옮기는 것은 될 일이
아니고, 무엇을 옮길지 사람이 정해야 한다. 그런데 900건의 본문을 다 읽고
정할 수도 없다. 그래서 **날짜·제목·분량·어느 장에 속하는지만** 뽑아
목록을 만든다. 고르는 사람은 이 목록을 보고 정한다.

권을 넷 쓴다.

    frus1950v07        6월 25일 이후          개전과 인천, 중공군 개입
    frus1951v07p1      1951년 전부           휴전 회담 시작
    frus1952-54v15p1   묶음 I~VI            1952년 1월 – 1953년 6월 8일
    frus1952-54v15p2   묶음 VII             1953년 6월 8일 – 7월 27일

`frus1951v07p2` 는 중국 편이라 뺀다. `v15p2` 의 묶음 VIII 이후는 정전 뒤라 뺀다.

문서번호에 권을 붙인다 — `50-d123`, `51-d45`, `52-d200`, `53-d80`.
1952-54 권은 두 부로 갈리므로 앞부분을 `52`, 뒷부분을 `53` 으로 적는다.
같은 권의 두 부에서 문서번호가 겹치지 않는지 확인한다.

산출물
    raw/cand.json   고를 거리 (본문 없음)
"""
import html
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RAW = os.path.join(ROOT, "raw")

LO, HI = "1950-06-25", "1953-07-27"
VOLS = [
    ("frus1950v07", "50", None),
    ("frus1951v07p1", "51", None),
    ("frus1952-54v15p1", "52", None),
    ("frus1952-54v15p2", "53", "VII."),      # 묶음 VII 만
]
STRUCT = r'<div[^>]*type="(?:section|chapter|part|compilation|appendix|index)"'


def txt(x):
    x = re.sub(r"<[^>]+>", " ", x)
    return re.sub(r"\s+", " ", html.unescape(x)).strip()


out = []
for vol, tag, only in VOLS:
    s = open(os.path.join(RAW, vol + ".xml"), encoding="utf-8").read()

    # 묶음(compilation) 경계를 잡아 둔다. `only` 가 있으면 그 묶음 안의 문서만 쓴다.
    comp = []
    for m in re.finditer(r'<div[^>]*type="compilation"[^>]*>\s*<head[^>]*>(.*?)</head>',
                         s, re.S):
        comp.append((m.start(), txt(m.group(1))))
    comp.sort()

    def which(pos):
        cur = ""
        for st, name in comp:
            if st < pos:
                cur = name
            else:
                break
        return cur

    pos = [(m.group(1), m.start()) for m in
           re.finditer(r'<div[^>]*type="document"[^>]*xml:id="(d\d+)"', s)]
    ends = [m.start() for m in re.finditer(STRUCT, s)]

    n = 0
    for i, (did, st) in enumerate(pos):
        en = pos[i + 1][1] if i + 1 < len(pos) else len(s)
        nxt = [x for x in ends if x > st]
        if nxt:
            en = min(en, nxt[0])
        blk = s[st:en]

        c = which(st)
        if only and not c.startswith(only):
            continue

        m = re.search(r'when="(\d{4}-\d{2}-\d{2})"', blk)
        date = m.group(1) if m else None
        if not date or not (LO <= date <= HI):
            continue

        h = re.search(r"<head[^>]*>(.*?)</head>", blk, re.S)
        title = re.sub(r"\[?주?\d*\]?", "", txt(h.group(1))) if h else ""
        title = re.sub(r"\s+", " ", title).strip()

        body = re.sub(r"<note[^>]*>.*?</note>", "", blk, flags=re.S)
        body = re.sub(r"<head[^>]*>.*?</head>", "", body, count=1, flags=re.S)

        out.append({"id": f"{tag}-{did}", "v": vol, "src": did, "date": date,
                    "title": title[:180], "chars": len(txt(body)), "comp": c[:60]})
        n += 1
    print(f"{vol:20} {n:4}건")

out.sort(key=lambda d: (d["date"], d["id"]))
json.dump(out, open(os.path.join(RAW, "cand.json"), "w"), ensure_ascii=False, indent=1)
print(f"\n고를 거리 {len(out)}건 · {sum(d['chars'] for d in out):,}자")
print(f"  {out[0]['date']} ~ {out[-1]['date']}")
