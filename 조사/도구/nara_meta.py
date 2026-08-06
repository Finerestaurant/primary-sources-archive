"""NARA 카탈로그에서 기록군별 조선 관련 온라인 공개본의 목록과 파일 정보를 모은다.
내려받기 전에 규모부터 잰다 — 한 기술항목에 이미지가 수백 장 붙어 있을 수 있다."""
import json, time, urllib.parse, urllib.request
UA = {"User-Agent": "Mozilla/5.0 (research; primary-sources-archive)",
      "Accept": "application/json"}

def page(rg, offset, limit=100):
    p = {"q": "korea", "recordGroupNumber": str(rg), "availableOnline": "true",
         "limit": limit, "offset": offset}
    u = "https://catalog.archives.gov/proxy/records/search?" + urllib.parse.urlencode(p)
    with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=180) as r:
        return json.loads(r.read().decode())["body"]["hits"]

out = {}
for rg in (226, 242, 407, 65, 319, 554):
    recs, off = [], 0
    while True:
        h = page(rg, off)
        tot = h["total"]["value"]
        for x in h["hits"]:
            r = x["_source"]["record"]
            objs = r.get("digitalObjects") or []
            recs.append({
                "naId": r.get("naId"), "title": (r.get("title") or "")[:160],
                "level": r.get("levelOfDescription"),
                "n_obj": len(objs),
                "bytes": sum(int(o.get("objectFileSize") or 0) for o in objs),
                "types": sorted({(o.get("objectType") or "?") for o in objs}),
            })
        off += len(h["hits"])
        if off >= tot or not h["hits"]:
            break
        time.sleep(0.4)
    out[rg] = recs
    n_obj = sum(r["n_obj"] for r in recs)
    gb = sum(r["bytes"] for r in recs) / 1e9
    print(f"RG {rg:<4} 기술항목 {len(recs):>6,}   디지털 개체 {n_obj:>9,}   {gb:>9.1f} GB", flush=True)

json.dump(out, open("nara_korea_online.json", "w"), ensure_ascii=False)
