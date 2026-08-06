"""CREST 본문(OCR 전문)을 받는다. 이어달리기 가능 — 이미 받은 것은 건너뛴다.

서버 부담을 줄이려고 동시 요청 5개, 실패는 세 번까지 물러서며 다시 시도한다.
아카이브닷오르그는 이 정도 요청에 관대하지만, 그렇다고 세게 두드릴 이유는 없다.
(국편을 막히게 한 것이 20갈래 동시 요청이었다.)
"""
import json, os, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor

UA = {"User-Agent": "Mozilla/5.0 (research; primary-sources-archive)"}
OUT = "crest_txt"
os.makedirs(OUT, exist_ok=True)
ids = json.load(open("crest_ids.json"))
log = open("crest_fetch_status.tsv", "a")

def one(x):
    p = os.path.join(OUT, x["doc"] + ".txt")
    if os.path.exists(p):
        return "cached"
    url = f'https://archive.org/download/{x["id"]}/{x["doc"]}_djvu.txt'
    for a in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
                b = r.read()
            open(p, "wb").write(b)
            time.sleep(0.1)
            return "ok"
        except urllib.error.HTTPError as e:
            if e.code == 404:                 # OCR 텍스트가 없는 건 (이미지만)
                log.write(f'{x["doc"]}\tno_text\n'); return "no_text"
            time.sleep(2.0 * (a + 1))
        except Exception:
            time.sleep(2.0 * (a + 1))
    log.write(f'{x["doc"]}\tfail\n'); return "fail"

n = {"ok": 0, "cached": 0, "no_text": 0, "fail": 0}
t0 = time.time()
with ThreadPoolExecutor(max_workers=5) as ex:
    for i, s in enumerate(ex.map(one, ids), 1):
        n[s] += 1
        if i % 500 == 0:
            el = time.time() - t0
            print(f"  {i:,}/{len(ids):,}  {n}  {el/60:.1f}분 "
                  f"(남은 예상 {el/i*(len(ids)-i)/60:.0f}분)", flush=True)
print("끝", n, flush=True)
