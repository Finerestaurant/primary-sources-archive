"""원본 지면 → 썸네일. 문서철을 가리지 않는다.

    python3 make_thumbs.py <collection.json> [--width 240] [--force]

## 왜 필요한가

열람기는 썸네일을 84×110 으로 보여주면서 원본을 그대로 내려받고 있었다.
NDL 자료는 한 장이 883KB 라서, 문서 하나를 열면 썸네일만 12MB 를 받는다.
화면에 찍히는 것은 그 60분의 1 도 안 되는 크기다.

작은 사본을 따로 만들어 두면 목록은 가볍게 뜨고, 원본은 확대해 볼 때만 받는다.

## 설정

collection.json 의 `pages` 에 `thumbs` 를 적으면 열람기가 그쪽을 쓴다.

    "pages": {
      "dir": "../pages", "ext": "jpg",
      "thumbs": "../thumbs", "thumb_ext": "jpg",
      "label": "원본 지면"
    }

`thumbs` 가 없으면 지금까지처럼 원본을 그대로 쓴다 — 썸네일을 안 만든 문서철도
그대로 돌아간다.
"""
import json
import os
import sys

from PIL import Image

if len(sys.argv) < 2:
    sys.exit(__doc__)

CONF = os.path.abspath(sys.argv[1])
BASE = os.path.dirname(CONF)
WIDTH = 240
FORCE = "--force" in sys.argv
if "--width" in sys.argv:
    WIDTH = int(sys.argv[sys.argv.index("--width") + 1])

conf = json.load(open(CONF))
pc = conf.get("pages")
if not pc:
    sys.exit("이 문서철은 스캔이 없다 (collection.json 에 pages 항목 없음).")

src = os.path.normpath(os.path.join(BASE, pc["dir"]))
dst = os.path.normpath(os.path.join(BASE, pc.get("thumbs") or (pc["dir"] + "/../thumbs")))
ext = pc["ext"]
text = pc.get("thumb_ext", "jpg")

if not os.path.isdir(src):
    sys.exit(f"{src} 가 없다.")
os.makedirs(dst, exist_ok=True)

names = sorted(f for f in os.listdir(src) if f.lower().endswith("." + ext))
made, skip, before, after = 0, 0, 0, 0

for n in names:
    sp = os.path.join(src, n)
    dp = os.path.join(dst, os.path.splitext(n)[0] + "." + text)
    before += os.path.getsize(sp)
    if os.path.exists(dp) and not FORCE:
        skip += 1
        after += os.path.getsize(dp)
        continue
    im = Image.open(sp)
    if im.mode not in ("RGB", "L"):
        im = im.convert("RGB")
    # 목록에서는 위쪽만 보이므로 세로는 넉넉히 두고 폭만 맞춘다.
    im.thumbnail((WIDTH, WIDTH * 4), Image.LANCZOS)
    if text in ("jpg", "jpeg"):
        im.save(dp, quality=78, optimize=True, progressive=True)
    else:
        im.save(dp, optimize=True)
    made += 1
    after += os.path.getsize(dp)
    if made % 50 == 0:
        print(f"  {made}장…")

print(f"{conf.get('title','')} — 썸네일 {len(names)}장 "
      f"(새로 {made}, 그대로 {skip}) 폭 {WIDTH}px")
print(f"  원본 {before/1e6:.0f}MB → 썸네일 {after/1e6:.1f}MB "
      f"({before/max(after,1):.0f}분의 1)  -> {dst}/")
if not pc.get("thumbs"):
    print("  !! collection.json 의 pages 에 \"thumbs\" 를 적어야 열람기가 쓴다.")
