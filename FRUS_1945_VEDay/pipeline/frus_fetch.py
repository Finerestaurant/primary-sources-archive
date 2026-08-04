"""FRUS 1945 제3권에서 「독일 항복의 열이틀」을 뽑는다.

    python3 frus_fetch.py

기존 도구(FRUS_1945_Surrender)와 뼈대가 같다. 다른 것은 **고르는 방식**뿐이다.
저쪽은 조선이 나오는 문서를 손으로 골라 문서번호를 적어 두었지만, 여기서는
**날짜 창**으로 고른다 — 이 문서철의 주제가 낱말이 아니라 **시간**이기 때문이다.

1945년 4월 25일부터 5월 12일까지 열여드레. 그 사이에 히틀러가 죽고, 랭스에서
독일이 항복문서에 서명하고, 스탈린이 그 서명을 인정하지 않아 베를린에서 다시
서명하고, 그동안 워싱턴·런던·모스크바가 **언제 발표할 것인가**를 두고 다툰다.
하루에 여덟아홉 통씩 오간다. 순서가 곧 내용이다.

산출물
    raw/dNNN.txt    본문 (각주 포함). 면이 바뀌는 자리에 [448면]
    raw/index.json  문서번호 → 제목·날짜·URL·글자수
    raw/pages.json  문서번호 → 스캔 파일 번호 목록
"""
import html
import json
import os
import re
import sys
import urllib.request

VOL = "frus1945v03"
XML = f"https://raw.githubusercontent.com/HistoryAtState/frus/master/volumes/{VOL}.xml"
SITE = f"https://history.state.gov/historicaldocuments/{VOL}"

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(HERE), "raw")

# 날짜 창. 앞뒤를 조금 넉넉히 잡아 히틀러 자살 직전부터 발표 뒤 뒷정리까지 담는다.
FROM, TO = "1945-04-25", "1945-05-12"

os.makedirs(OUT, exist_ok=True)
cache = os.path.join(OUT, f"{VOL}.xml")

if not os.path.exists(cache):
    print(f"원본 XML 받는 중… {XML}")
    req = urllib.request.Request(XML, headers={"User-Agent": "Mozilla/5.0 (research)"})
    with urllib.request.urlopen(req, timeout=180) as r:
        open(cache, "wb").write(r.read())
s = open(cache, encoding="utf-8").read()
print(f"원본 {len(s)//1024}KB")


def to_text(x):
    """TEI 조각 → 읽을 수 있는 텍스트. 쪽 넘김과 각주 참조만 남긴다."""
    # <pb n="448"/> → [448면].  n 이 [I] 처럼 로마숫자인 앞머리는 버린다.
    x = re.sub(r'<pb[^>]*\bn="(\d+)"[^>]*/>', r" [\1면] ", x)
    x = re.sub(r"<pb[^>]*/>", " ", x)
    x = re.sub(r'<note[^>]*\bn="([^"]+)"[^>]*>', r" [주\1] ", x)  # 본문 속 각주 표시
    # 문단 경계는 블록 태그가 정한다. TEI 안의 줄바꿈과 들여쓰기는 XML 을 보기 좋게
    # 정렬한 것일 뿐이라, 그대로 살리면 한 문장이 예닐곱 조각으로 쪼개져 읽을 수 없다.
    # 명시적 줄바꿈(<lb/>)만 줄로 남긴다.
    BLOCK = r"p|div|head|item|list|closer|dateline|opener|signed|table|row"
    x = re.sub(rf"<(?:{BLOCK})\b[^>]*>", "\x00", x)
    x = re.sub(rf"</(?:{BLOCK})>", "\x00", x)
    x = re.sub(r"<lb\b[^>]*/?>", "\x01", x)
    x = re.sub(r"<[^>]+>", "", x)
    x = html.unescape(x)
    x = re.sub(r"[ \t\r\n]+", " ", x)          # 나머지 공백은 전부 하나로
    x = x.replace("\x01", "\n")
    x = re.sub(r" *\x00[\s\x00]*", "\n\n", x)
    return x.strip()


# 문서 경계를 먼저 잡는다 (TEI 는 문서가 평평하게 이어져 있다)
pos = [(m.group(1), m.start()) for m in
       re.finditer(r'<div[^>]*type="document"[^>]*xml:id="(d\d+)"', s)]
span = {}
for i, (did, st) in enumerate(pos):
    span[did] = (st, pos[i + 1][1] if i + 1 < len(pos) else len(s))

# 날짜로 고른다. TEI 의 <dateline> 이나 문서 머리의 when 속성을 본다.
WANT, dates = [], {}
for did, (st, en) in span.items():
    m = re.search(r'when="(\d{4}-\d{2}-\d{2})', s[st:en])
    if m and FROM <= m.group(1) <= TO:
        WANT.append(did); dates[did] = m.group(1)
WANT.sort(key=lambda d: (dates[d], int(re.sub(r"\D", "", d))))
print(f"날짜 창 {FROM} ~ {TO} · {len(WANT)}건")

index, pagemap = [], {}
for did in WANT:
    st, en = span[did]
    blk = s[st:en]

    h = re.search(r"<head[^>]*>(.*?)</head>", blk, re.S)
    title = re.sub(r"\s+", " ", to_text(h.group(1))) if h else ""
    title = re.sub(r"\[주\d+\]", "", title).strip()

    # 편철 위치를 적은 note (type="source") 는 각주가 아니라 출처 표시다.
    # FRUS 1945 자료에서 `원문출처` 로 뽑은 것과 같은 것이라 따로 담는다.
    sm = re.search(r'<note[^>]*type="source"[^>]*>(.*?)</note>', blk, re.S)
    source = re.sub(r"\s+", " ", to_text(sm.group(1))).strip() if sm else ""

    # 각주. 번호가 숫자가 아닌 것(`n="*"`)도 있다 — 이걸 놓치면 각주가 통째로 사라진다.
    notes = []
    for m in re.finditer(r'<note([^>]*)>(.*?)</note>', blk, re.S):
        if 'type="source"' in m.group(1):
            continue
        n = re.search(r'\bn="([^"]+)"', m.group(1))
        t = re.sub(r"\s+", " ", to_text(m.group(2))).strip()
        if t:
            notes.append(f"[주{n.group(1)}] {t}" if n else t)

    # 본문에서는 각주 내용을 빼되 참조 표시([주3])는 남긴다.
    # 통째로 지우면 각주가 본문 어느 대목에 붙는지 알 수 없게 된다.
    body_xml = re.sub(r'<note[^>]*type="source"[^>]*>.*?</note>', "", blk, flags=re.S)
    body_xml = re.sub(r'<note([^>]*)\bn="([^"]+)"([^>]*)>.*?</note>',
                      lambda m: f" [주{m.group(2)}] ", body_xml, flags=re.S)
    body_xml = re.sub(r"<note[^>]*>.*?</note>", "", body_xml, flags=re.S)
    body_xml = re.sub(r"<head[^>]*>.*?</head>", "", body_xml, count=1, flags=re.S)
    body = to_text(body_xml)

    # 이 문서가 걸친 스캔 면 (facs = 스캔 파일 번호)
    facs = []
    for m in re.finditer(r'<pb[^>]*\bfacs="(\d+)"', blk):
        if m.group(1) not in facs:
            facs.append(m.group(1))
    pagemap[did] = facs

    open(os.path.join(OUT, did + ".txt"), "w").write(
        body + (("\n\n----- 각주 -----\n" + "\n".join(notes) + "\n") if notes else ""))
    index.append({"doc_id": did, "date": dates[did], "title": title,
                  "source_note": source, "url": f"{SITE}/{did}", "chars": len(body)})
    print(f"  {did} {dates[did]} {len(body):6,}자  면 {len(facs)}장  {title[:52]}")

json.dump(index, open(os.path.join(OUT, "index.json"), "w"),
          ensure_ascii=False, indent=1)
json.dump(pagemap, open(os.path.join(OUT, "pages.json"), "w"),
          ensure_ascii=False, indent=1)
print(f"\n문서 {len(index)}건 · {sum(d['chars'] for d in index):,}자 -> {OUT}/")
