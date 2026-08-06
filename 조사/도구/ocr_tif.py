"""TIFF 표본 → 텍스트. Vision 이 TIFF 를 못 읽으면 sips 로 JPEG 를 거친다."""
import glob, os, subprocess
from ocrmac import ocrmac
SRC, OUT, TMP = "nara_rg319_ago", "nara_rg319_ago_ocr", "nara_rg319_ago_jpg"
os.makedirs(OUT, exist_ok=True); os.makedirs(TMP, exist_ok=True)
for p in sorted(glob.glob(os.path.join(SRC, "*.tif"))):
    stem = os.path.splitext(os.path.basename(p))[0]
    t = os.path.join(OUT, stem + ".txt")
    if os.path.exists(t): continue
    j = os.path.join(TMP, stem + ".jpg")
    if not os.path.exists(j):
        subprocess.run(["sips", "-s", "format", "jpeg", "-Z", "3000", p, "--out", j],
                       capture_output=True)
    try:
        b = ocrmac.OCR(j, language_preference=["en-US"]).recognize()
    except Exception as e:
        open(t, "w").write(""); print(stem, "실패", e); continue
    items = sorted([(bb[1], bb[0], tx) for tx, c, bb in b if c >= 0.3 and tx.strip()],
                   key=lambda r: (-r[0], r[1]))
    open(t, "w").write("\n".join(x[2] for x in items))
print("끝", len(glob.glob(os.path.join(OUT, "*.txt"))), "장")
