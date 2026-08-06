"""CREST(아카이브닷오르그 미러)에서 조선 관련 1948–54 문서 목록을 뽑는다.
메타데이터만 받는다 — 본문은 고른 뒤에 받는다."""
import json, time, urllib.parse, urllib.request

UA = {"User-Agent": "Mozilla/5.0 (research)"}
Q = ('identifier:cia-readingroom-document-* AND korea '
     'AND date:[1948-01-01 TO 1954-12-31]')

out, cursor = [], None
while True:
    p = {"q": Q, "fields": "identifier,title,date", "count": 10000}
    if cursor:
        p["cursor"] = cursor
    u = "https://archive.org/services/search/v1/scrape?" + urllib.parse.urlencode(p)
    with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=120) as r:
        d = json.load(r)
    out += d.get("items", [])
    cursor = d.get("cursor")
    print(f"  {len(out)} / {d.get('total')}")
    if not cursor:
        break
    time.sleep(1)

for x in out:
    x["date"] = (x.get("date") or "")[:10]
    # 미러의 제목은 "CIA Reading Room {문서번호}: {원제}" 꼴이다
    t = x.get("title") or ""
    x["docnum"] = x["identifier"].replace("cia-readingroom-document-", "")
    x["title"] = t.split(": ", 1)[1] if ": " in t else t
out.sort(key=lambda x: (x["date"], x["docnum"]))
json.dump(out, open("crest_korea_1948_54.json", "w"), ensure_ascii=False, indent=1)
print("저장", len(out), "건 → crest_korea_1948_54.json")
