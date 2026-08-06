import json,os,sys,time,urllib.request
from concurrent.futures import ThreadPoolExecutor
PID=sys.argv[1]; A=int(sys.argv[2]); B=int(sys.argv[3])
UA={"User-Agent":"Mozilla/5.0 (research; single-document download)"}
OUT=f"ndl_{PID}"; os.makedirs(OUT,exist_ok=True)
mp=os.path.join(OUT,"manifest.json")
if not os.path.exists(mp):
    with urllib.request.urlopen(urllib.request.Request(f"https://dl.ndl.go.jp/api/iiif/{PID}/manifest.json",headers=UA),timeout=60) as r:
        open(mp,'wb').write(r.read())
man=json.load(open(mp)); cvs=man["sequences"][0]["canvases"]
def fetch(i):
    p=os.path.join(OUT,f"{i+1:04d}.jpg")
    if os.path.exists(p) and os.path.getsize(p)>1000: return "cached"
    svc=cvs[i]["images"][0]["resource"]["service"]["@id"]
    for a in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(f"{svc}/full/1200,/0/default.jpg",headers=UA),timeout=120) as r:
                open(p,'wb').write(r.read())
            time.sleep(0.15); return "ok"
        except Exception as e:
            time.sleep(1.5*(a+1))
    return "fail"
idx=[i for i in range(A-1,min(B,len(cvs)))]
with ThreadPoolExecutor(4) as ex:
    print(PID, len(cvs),"frames;", sum(1 for s in ex.map(fetch,idx) if s in("ok","cached")),"got")
