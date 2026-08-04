"""macOS Vision OCR로 스캔 페이지 → 텍스트.

완전 로컬·무료·오프라인. 페이지당 약 1.4초.

Vision은 인식 블록을 순서 없이 돌려주므로, 정규화 좌표로 줄을 재구성한다.
원점은 좌하단이라 y가 클수록 위쪽이다.

출력은 LLM 교정·번역 단계의 입력이 된다. 오탈자를 여기서 고치려 하지 말 것 —
그건 다음 단계의 일이고, 원본 OCR을 그대로 남겨야 대조가 가능하다.
"""
import json, os, sys, time, glob
from ocrmac import ocrmac

SRC = sys.argv[1] if len(sys.argv) > 1 else "ndl_9850431"
OUT = sys.argv[2] if len(sys.argv) > 2 else "ocr_9850431"
LINE_TOL = 0.012          # 같은 줄로 볼 y 허용오차 (페이지 높이 비율)
MIN_CONF = 0.30           # 이보다 낮은 블록은 버린다

os.makedirs(OUT, exist_ok=True)


def to_lines(blocks):
    """인식 블록들을 읽기 순서(위→아래, 좌→우)의 줄로 묶는다."""
    items = [(t, c, b) for t, c, b in blocks if c >= MIN_CONF and t.strip()]
    items.sort(key=lambda r: -r[2][1])

    lines, cur, cur_y = [], [], None
    for text, conf, box in items:
        y = box[1]
        if cur_y is None or abs(y - cur_y) <= LINE_TOL:
            cur.append((box[0], text, conf))
            cur_y = y if cur_y is None else (cur_y + y) / 2.0
        else:
            cur.sort()
            lines.append(cur)
            cur, cur_y = [(box[0], text, conf)], y
    if cur:
        cur.sort()
        lines.append(cur)
    return lines


files = sorted(glob.glob(os.path.join(SRC, "*.jpg")))
print(f"{len(files)} pages")

index = []
t0 = time.time()
for i, path in enumerate(files, 1):
    stem = os.path.splitext(os.path.basename(path))[0]
    txt_path = os.path.join(OUT, f"{stem}.txt")
    if os.path.exists(txt_path):
        continue

    blocks = ocrmac.OCR(path, language_preference=["en-US"]).recognize()
    lines = to_lines(blocks)

    text = "\n".join(" ".join(t for _, t, _ in ln) for ln in lines)
    confs = [c for ln in lines for _, _, c in ln]
    mean_conf = sum(confs) / len(confs) if confs else 0.0

    open(txt_path, "w").write(text)
    index.append({
        "page": stem,
        "chars": len(text),
        "lines": len(lines),
        "mean_conf": round(mean_conf, 3),
    })

    if i % 25 == 0:
        print(f"  {i}/{len(files)}  ({time.time()-t0:.0f}s)")

json.dump(index, open(os.path.join(OUT, "_index.json"), "w"),
          ensure_ascii=False, indent=1)

if index:
    empty = [r["page"] for r in index if r["chars"] < 40]
    print(f"\ndone in {time.time()-t0:.0f}s")
    print(f"mean chars/page: {sum(r['chars'] for r in index)//len(index)}")
    print(f"mean confidence: {sum(r['mean_conf'] for r in index)/len(index):.3f}")
    print(f"near-empty pages ({len(empty)}): {empty[:15]}")
