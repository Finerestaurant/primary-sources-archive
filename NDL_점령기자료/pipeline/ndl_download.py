"""NDL 디지털컬렉션 IIIF 다운로더.

PDM(퍼블릭 도메인) 자료만 대상으로 한다.
IIIF Image API로 축소본을 받는다 — 원본은 3967x5467이라 351장이면 1GB에 육박하고,
타자기로 친 1940년대 문서는 폭 1600px면 충분히 읽힌다.

서버 부담을 줄이려고 동시 요청은 4개로 제한한다.
"""
import json, os, sys, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor

PID = sys.argv[1] if len(sys.argv) > 1 else "9850431"
WIDTH = 1600
OUT = f"ndl_{PID}"
UA = {"User-Agent": "Mozilla/5.0 (research; single-document download)"}

os.makedirs(OUT, exist_ok=True)

man_path = os.path.join(OUT, "manifest.json")
if not os.path.exists(man_path):
    req = urllib.request.Request(
        f"https://dl.ndl.go.jp/api/iiif/{PID}/manifest.json", headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        open(man_path, "wb").write(r.read())

man = json.load(open(man_path))
canvases = man["sequences"][0]["canvases"]
label = man["label"]

restrictions = next((m["value"] for m in man.get("metadata", [])
                     if m["label"] == "Access Restrictions"), "?")
print(f"{label}")
print(f"  frames={len(canvases)}  access={restrictions}")
if restrictions != "PDM":
    print("  !! PDM이 아니다. 이용 조건을 먼저 확인할 것.")
    sys.exit(1)

def fetch(i_canvas):
    i, canvas = i_canvas
    svc = canvas["images"][0]["resource"]["service"]["@id"]
    url = f"{svc}/full/{WIDTH},/0/default.jpg"
    path = os.path.join(OUT, f"{i+1:04d}.jpg")
    if os.path.exists(path) and os.path.getsize(path) > 1000:
        return "cached"
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=120) as r:
                data = r.read()
            open(path, "wb").write(data)
            time.sleep(0.15)          # 요청 간격
            return "ok"
        except Exception as e:
            if attempt == 2:
                return f"fail:{type(e).__name__}"
            time.sleep(2.0 * (attempt + 1))

done = {"ok": 0, "cached": 0}
fails = []
with ThreadPoolExecutor(max_workers=4) as ex:
    for n, status in enumerate(ex.map(fetch, enumerate(canvases)), 1):
        if status in done:
            done[status] += 1
        else:
            fails.append((n, status))
        if n % 50 == 0:
            print(f"  {n}/{len(canvases)}")

total = sum(os.path.getsize(os.path.join(OUT, f))
            for f in os.listdir(OUT) if f.endswith(".jpg"))
print(f"downloaded={done['ok']} cached={done['cached']} failed={len(fails)}")
if fails:
    print("  실패:", fails[:10])
print(f"total {total/1e6:.1f} MB → {OUT}/")
