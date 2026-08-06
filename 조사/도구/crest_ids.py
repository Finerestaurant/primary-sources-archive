"""CREST 미러에서 조선 관련 문서의 문서번호를 모은다. 본문은 다음 단계."""
import json, time, urllib.parse, urllib.request
UA = {"User-Agent": "Mozilla/5.0 (research; primary-sources-archive)"}
B = 'identifier:cia-readingroom-document-*'
TERMS = {"korea": "korea", "korean": "korean", "chosen": "chosen", "seoul": "seoul",
         "pyongyang": "pyongyang OR phyongyang", "panmunjom": "panmunjom",
         "rhee": "rhee", "parallel38": '"38th parallel"'}

items = {}
for tag, term in TERMS.items():
    cur, got = None, 0
    while True:
        p = {"q": f"{B} AND ({term})", "fields": "identifier,title,date", "count": 10000}
        if cur: p["cursor"] = cur
        u = "https://archive.org/services/search/v1/scrape?" + urllib.parse.urlencode(p)
        with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=180) as r:
            d = json.load(r)
        for x in d.get("items", []):
            e = items.setdefault(x["identifier"], {**x, "hit": []})
            e["hit"].append(tag)
        got += len(d.get("items", []))
        cur = d.get("cursor")
        if not cur: break
        time.sleep(1)
    print(f"  {tag:12s} {got:>7,}  (누계 {len(items):,})", flush=True)

out = []
for k, v in items.items():
    t = v.get("title") or ""
    out.append({"id": k, "doc": k.replace("cia-readingroom-document-", ""),
                "date": (v.get("date") or "")[:10],
                "title": t.split(": ", 1)[1] if ": " in t else t,
                "hit": sorted(set(v["hit"]))})
out.sort(key=lambda x: (x["date"], x["doc"]))
json.dump(out, open("crest_ids.json", "w"), ensure_ascii=False, indent=1)
print(f"\n합계 {len(out):,}건 → crest_ids.json")
