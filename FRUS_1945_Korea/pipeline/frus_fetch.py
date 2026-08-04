"""FRUS 문서를 받아 텍스트로 바꾼다.

    python frus_fetch.py frus1945v06 756 785 ../raw

FRUS(Foreign Relations of the United States)는 미국 국무부 공식 외교문서집이고
전문이 공개돼 있다. 스캔이 아니라 이미 텍스트라 OCR 단계가 필요 없다.

산출물
    raw/d756.txt … 본문 (각주 포함)
    raw/index.json … 문서번호 → 제목·날짜·출처표시
"""
import html
import json
import os
import re
import sys
import time
import urllib.request

VOL = sys.argv[1] if len(sys.argv) > 1 else "frus1945v06"
LO = int(sys.argv[2]) if len(sys.argv) > 2 else 756
HI = int(sys.argv[3]) if len(sys.argv) > 3 else 785
OUT = sys.argv[4] if len(sys.argv) > 4 else "../raw"

BASE = f"https://history.state.gov/historicaldocuments/{VOL}"
UA = {"User-Agent": "Mozilla/5.0 (research; personal use)"}


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", "replace")


def strip_tags(s):
    """블록 요소는 줄바꿈으로, 나머지는 제거."""
    s = re.sub(r"<a[^>]*class=\"[^\"]*tei-pb1[^\"]*\"[^>]*>\s*\[Page (\d+)\]\s*</a>",
               r" [\1면] ", s)
    s = re.sub(r"<a[^>]*rel=\"footnote\"[^>]*>(\d+)</a>", r"[주\1]", s)
    # 문단 경계는 블록 태그가 정한다. HTML 안의 줄바꿈과 들여쓰기는 소스를 보기 좋게
    # 정렬한 것일 뿐이라, 그대로 살리면 한 문장이 예닐곱 조각으로 쪼개져 읽을 수 없다.
    # <br> 만 진짜 줄바꿈으로 남긴다.
    BLOCK = r"p|div|h[1-6]|li|ul|ol|table|tr|blockquote"
    s = re.sub(rf"<(?:{BLOCK})\b[^>]*>", "\x00", s)
    s = re.sub(rf"</(?:{BLOCK})>", "\x00", s)
    s = re.sub(r"<br\b[^>]*/?>", "\x01", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s)
    s = re.sub(r"[ \t\r\n]+", " ", s)
    s = s.replace("\x01", "\n")
    s = re.sub(r" *\x00[\s\x00]*", "\n\n", s)
    return s.strip()


def extract(page, did):
    """해당 문서 div만 잘라낸다. div 중첩을 세어 정확히 닫는다."""
    m = re.search(r'<div class="tei-div3" id="%s">' % did, page)
    if not m:
        return None, None
    i, depth, j = m.end(), 1, m.end()
    for t in re.finditer(r"<(/?)div\b[^>]*>", page[i:]):
        depth += -1 if t.group(1) else 1
        if depth == 0:
            j = i + t.start()
            break
    body = page[i:j]

    head = re.search(r'<h4[^>]*class="tei-head7"[^>]*>(.*?)</h4>', body, re.S)
    title = strip_tags(head.group(1)).replace("\n", " ") if head else ""
    title = re.sub(r"\[주\d+\]", "", title).strip()

    # 각주는 본문 뒤에 따로 붙인다.
    # 각주 목록(<li id="fn:XXX">)에는 번호가 없다 — 번호는 본문 쪽 참조
    # (<a rel="footnote">48</a>)에만 있고, 둘은 id로 이어진다. 그 대응을 복원해야
    # 본문의 [주48]과 각주가 맞물린다.
    num = {m.group(1): m.group(2) for m in re.finditer(
        r'<span id="fnref:([^"]+)"><a [^>]*rel="footnote">(\d+)</a>', page)}
    notes = []
    for n in re.finditer(r'<li[^>]*id="fn:([^"]+)"[^>]*>(.*?)</li>', page, re.S):
        t = strip_tags(n.group(2)).replace("\n", " ").rstrip("↩ ").strip()
        notes.append(f"[주{num[n.group(1)]}] {t}" if n.group(1) in num else t)
    return title, (strip_tags(body), notes)


def main():
    os.makedirs(OUT, exist_ok=True)
    index = []
    for n in range(LO, HI + 1):
        did = f"d{n}"
        dst = os.path.join(OUT, did + ".txt")
        if os.path.exists(dst) and os.path.getsize(dst) > 200:
            print(f"  {did} 이미 있음")
            continue
        title, res = extract(get(f"{BASE}/{did}"), did)
        if res is None:
            print(f"!! {did} 본문 없음 — 건너뜀")
            continue
        body, notes = res
        with open(dst, "w") as f:
            f.write(body)
            if notes:
                f.write("\n\n----- 각주 -----\n" + "\n".join(notes) + "\n")
        print(f"  {did} {len(body):6d}자  {title[:60]}")
        time.sleep(0.4)
        index.append({"doc_id": did, "title": title,
                      "url": f"{BASE}/{did}", "chars": len(body)})

    if index:
        p = os.path.join(OUT, "index.json")
        old = json.load(open(p)) if os.path.exists(p) else []
        seen = {d["doc_id"] for d in index}
        index += [d for d in old if d["doc_id"] not in seen]
        index.sort(key=lambda d: int(d["doc_id"][1:]))
        json.dump(index, open(p, "w"), ensure_ascii=False, indent=1)

    print(f"\n-> {OUT}/")


if __name__ == "__main__":
    main()
