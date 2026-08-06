"""RG 319 부관감 문서철(1949.6–1950.1)의 앞부분을 표본으로 받는다.
한 장 28MB짜리 원본 TIFF뿐이라 전량(48.7GB)은 먼저 재 보고 결정한다."""
import json, os, sys, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
UA={"User-Agent":"Mozilla/5.0 (research; primary-sources-archive)","Accept":"application/json"}
N=int(sys.argv[1]) if len(sys.argv)>1 else 60
OUT="nara_rg319_ago"; os.makedirs(OUT,exist_ok=True)

u="https://catalog.archives.gov/proxy/records/search?"+urllib.parse.urlencode(
   {"q":"korea","recordGroupNumber":"319","availableOnline":"true","limit":100})
with urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=180) as r:
    hits=json.loads(r.read().decode())["body"]["hits"]["hits"]
rec=next(x["_source"]["record"] for x in hits
         if "Adjutant General" in (x["_source"]["record"].get("title") or ""))
objs=rec["digitalObjects"]
json.dump({"naId":rec["naId"],"title":rec["title"],"n":len(objs),"objects":objs},
          open(os.path.join(OUT,"_manifest.json"),"w"))
print(f'{rec["title"]}  전체 {len(objs):,}장 — 앞 {N}장을 받는다')

def get(o):
    p=os.path.join(OUT,o["objectFilename"])
    if os.path.exists(p) and os.path.getsize(p)>10000: return "cached"
    for a in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(
                    o["objectUrl"],headers={"User-Agent":UA["User-Agent"]}),timeout=300) as r:
                open(p,"wb").write(r.read())
            time.sleep(0.2); return "ok"
        except Exception: time.sleep(3*(a+1))
    return "fail"
with ThreadPoolExecutor(3) as ex:
    from collections import Counter
    c=Counter(ex.map(get,objs[:N]))
print(dict(c), f'{sum(os.path.getsize(os.path.join(OUT,f)) for f in os.listdir(OUT))/1e9:.2f}GB')
