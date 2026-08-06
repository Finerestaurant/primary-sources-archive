"""FRUS 1950·1951·1952-54 에서 「전쟁의 세 해」를 뽑는다.

    python3 frus_fetch.py

앞 문서철 「전쟁이 오기까지」의 frus_fetch.py 를 물려받았다. 다른 점은 하나다 —
**1952-54년 두 권이 해로 갈린다.** v15p1 을 `52-`, v15p2 를 `53-` 로 붙인다.
권이 곧 해가 아니라서 그렇다. 고른 목록과 그 이유는 `raw/pick.json` 에 있다.

    frus1950v07        56건   개전 · 인천 · 38선 · 중공군
    frus1951v07p1      59건   맥아더 해임 · 개성 · 판문점
    frus1952-54v15p1   47건   포로 · 부산 정치 파동 · 재검토
    frus1952-54v15p2   13건   반공포로 석방 · 정전

산출물
    raw/50-dNNN.txt   본문 (각주 포함). 면이 바뀌는 자리에 [448면]
    raw/index.json    문서번호 → 제목·날짜·URL·글자수·권·고른 이유
    raw/pages.json    문서번호 → 스캔 파일 번호 목록
"""
"""FRUS 1948·1949·1950 에서 「전쟁이 오기까지」를 뽑는다.

    python3 frus_fetch.py

앞선 문서철들과 다른 점이 둘 있다.

**세 권에 걸쳐 있다.** 그래서 문서번호에 권을 붙여 `48-d776` 처럼 쓴다.
안 그러면 세 권의 `d1` 이 서로 부딪힌다.

**날짜 창도 장(章)도 아니라 손으로 고른 목록으로 뽑는다.** 세 권의 조선
관련 문서는 402건인데 그 가운데 152건을 골랐다. 짧은 사무 연락과 뒤에
종합본이 있는 것을 쳐냈다. 고른 목록과 그 이유가 `raw/pick.json` 에 있다.

  frus1948v06     Korea                      226건 중 69
  frus1949v07p2   철군과 원조                 118건 중 50
  frus1950v07     개전 전 (1/1 – 6/24)         58건 중 33

이 문서철은 「조선 1943–1948」 주제를 1950년 6월 25일 직전까지 잇는다.
카이로에서 만들어진 「in due course」가 어떻게 끝나는지가 여기 있다.

산출물
    raw/48-dNNN.txt   본문 (각주 포함). 면이 바뀌는 자리에 [448면]
    raw/index.json    문서번호 → 제목·날짜·URL·글자수·권·고른 이유
    raw/pages.json    문서번호 → 스캔 파일 번호 목록
"""
import html
import json
import os
import re
import sys
import urllib.request

VOLS = {"frus1950v07": "50", "frus1951v07p1": "51",
        "frus1952-54v15p1": "52", "frus1952-54v15p2": "53"}
SITE = "https://history.state.gov/historicaldocuments"

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "raw")
os.makedirs(OUT, exist_ok=True)

pick = json.load(open(os.path.join(OUT, "pick.json")))
want = {}
for x in pick:
    want.setdefault(x["v"], {})[x["src"]] = x
print(f"고른 문서 {len(pick)}건")


def to_text(x):
    """TEI 조각 → 읽을 수 있는 텍스트. 쪽 넘김과 각주 참조만 남긴다."""
    x = re.sub(r'<pb[^>]*\bn="(\d+)"[^>]*/>', r" [\1면] ", x)
    x = re.sub(r"<pb[^>]*/>", " ", x)
    x = re.sub(r'<note[^>]*\bn="([^"]+)"[^>]*>', r" [주\1] ", x)
    BLOCK = r"p|div|head|item|list|closer|dateline|opener|signed|table|row"
    x = re.sub(rf"<(?:{BLOCK})\b[^>]*>", "\x00", x)
    x = re.sub(rf"</(?:{BLOCK})>", "\x00", x)
    x = re.sub(r"<lb\b[^>]*/?>", "\x01", x)
    x = re.sub(r"<[^>]+>", "", x)
    x = html.unescape(x)
    x = re.sub(r"[ \t\r\n]+", " ", x)
    x = x.replace("\x01", "\n")
    x = re.sub(r" *\x00[\s\x00]*", "\n\n", x)
    return x.strip()


index, pagemap = [], {}
for vol, tag in VOLS.items():
    cache = os.path.join(OUT, f"{vol}.xml")
    if not os.path.exists(cache):
        url = f"https://raw.githubusercontent.com/HistoryAtState/frus/master/volumes/{vol}.xml"
        print(f"  원본 XML 받는 중… {vol}")
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (research)"})
        with urllib.request.urlopen(req, timeout=300) as r:
            open(cache, "wb").write(r.read())
    s = open(cache, encoding="utf-8").read()

    pos = [(m.group(1), m.start()) for m in
           re.finditer(r'<div[^>]*type="document"[^>]*xml:id="(d\d+)"', s)]
    # 마지막 문서의 끝을 파일 끝으로 잡으면 권말 색인을 통째로 삼킨다.
    # 1948년 권의 d931 이 그래서 11만 자였다.
    STRUCT = [m.start() for m in re.finditer(
        r'<div[^>]*type="(?:section|chapter|part|compilation|appendix|index)"', s)]
    span = {}
    for i, (did, st) in enumerate(pos):
        en = pos[i + 1][1] if i + 1 < len(pos) else len(s)
        nxt = [x for x in STRUCT if x > st]
        if nxt:
            en = min(en, nxt[0])
        span[did] = (st, en)

    got = 0
    for did in sorted(want.get(vol, {}), key=lambda d: int(d[1:])):
        if did not in span:
            print(f"  !! {vol}/{did} 없다")
            continue
        st, en = span[did]
        blk = s[st:en]
        key = f"{tag}-{did}"

        h = re.search(r"<head[^>]*>(.*?)</head>", blk, re.S)
        title = re.sub(r"\s+", " ", to_text(h.group(1))) if h else ""
        title = re.sub(r"\[주\d+\]", "", title).strip()

        sm = re.search(r'<note[^>]*type="source"[^>]*>(.*?)</note>', blk, re.S)
        source = re.sub(r"\s+", " ", to_text(sm.group(1))).strip() if sm else ""

        notes = []
        for m in re.finditer(r"<note([^>]*)>(.*?)</note>", blk, re.S):
            if 'type="source"' in m.group(1):
                continue
            n = re.search(r'\bn="([^"]+)"', m.group(1))
            t = re.sub(r"\s+", " ", to_text(m.group(2))).strip()
            if t:
                notes.append(f"[주{n.group(1)}] {t}" if n else t)

        body_xml = re.sub(r'<note[^>]*type="source"[^>]*>.*?</note>', "", blk, flags=re.S)
        body_xml = re.sub(r'<note([^>]*)\bn="([^"]+)"([^>]*)>.*?</note>',
                          lambda m: f" [주{m.group(2)}] ", body_xml, flags=re.S)
        body_xml = re.sub(r"<note[^>]*>.*?</note>", "", body_xml, flags=re.S)
        body_xml = re.sub(r"<head[^>]*>.*?</head>", "", body_xml, count=1, flags=re.S)
        body = to_text(body_xml)

        facs = []
        for m in re.finditer(r'<pb[^>]*\bfacs="(\d+)"', blk):
            if m.group(1) not in facs:
                facs.append(m.group(1))
        pagemap[key] = facs

        open(os.path.join(OUT, key + ".txt"), "w").write(
            body + (("\n\n----- 각주 -----\n" + "\n".join(notes) + "\n") if notes else ""))
        p = want[vol][did]
        index.append({"doc_id": key, "vol": vol, "src_id": did,
                      "date": p["date"], "title": title, "source_note": source,
                      "url": f"{SITE}/{vol}/{did}", "chars": len(body),
                      "tag": p.get("tag"), "why": p.get("why")})
        got += 1
    print(f"  {vol}  {got}건")

# 날짜가 없는 편집자 주는 앞 문서의 날짜를 물려받는다. 안 그러면 시간순에서
# 맨 뒤로 밀려 엉뚱한 데 선다. 물려받았다는 것은 date_guess 로 남긴다.
index.sort(key=lambda d: (d["vol"], int(d["src_id"][1:])))
last = None
for d in index:
    if d["date"]:
        last = d["date"]
    elif last:
        d["date"], d["date_guess"] = last, True

index.sort(key=lambda d: (d["date"] or "9999", d["vol"], int(d["src_id"][1:])))
json.dump(index, open(os.path.join(OUT, "index.json"), "w"), ensure_ascii=False, indent=1)
json.dump(pagemap, open(os.path.join(OUT, "pages.json"), "w"), ensure_ascii=False, indent=1)
print(f"\n문서 {len(index)}건 · {sum(d['chars'] for d in index):,}자 -> {OUT}/")
print(f"  {index[0]['date']} ~ {index[-1]['date']}")
