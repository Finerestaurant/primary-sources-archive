"""지면 → 원문 텍스트. 국립국회도서관 NDLOCR-Lite 로 뽑는다.

    python3 ndlocr.py ../pages/nichibei2_05_050.png [...]      # 낱장
    python3 ndlocr.py --all                                    # 아직 안 뽑은 것 전부

이 자료는 스캔 이미지뿐이라 PDF 안에 글자가 없다. 텍스트 층도 폰트도 0이고
한 면에 그림 하나씩이다. 그래서 『종전사록』에 썼던 글자표(글꼴의 벡터 윤곽을
ヒラギノ明朝 와 견주는 방식)가 통하지 않는다 — 견줄 윤곽 자체가 없다.

tesseract `jpn_vert` 는 82% 에서 막힌다. Apple Vision 은 세로 본문을 통째로
건너뛴다. NDLOCR-Lite 는 국립국회도서관이 일본 근대 자료의 세로쓰기를 위해
만든 것이라 이 지면에서 **97~99%** 가 나온다. 한 쪽 1.2초.

틀리는 자리에 성격이 있다 — 본문 글자는 거의 안 틀리고 **괄호 안 항목 번호**
（三）→(二), （五）→(ロ) 가 틀린다. 그래서 뽑은 뒤 항목 번호가 차례대로
가는지 따로 본다. 어긋나면 표시해 두고 사람이 지면을 확인한다.

**이것은 초벌이지 정본이 아니다.** 번역하는 사람이 지면과 대조해 고친 것이
정본이 된다.
"""
import os
import re
import subprocess
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PAGES = os.path.join(ROOT, "pages")
OUT = os.path.join(ROOT, "raw", "ocr")

# 도구가 놓인 자리. 없으면 받는 법을 알려 준다.
TOOL = os.environ.get("NDLOCR_DIR",
                      "/Users/anthonypark/.claude/jobs/d7faacd4/tmp/ndlocr-lite")
PY_ = os.path.join(TOOL, ".venv", "bin", "python")
SRC = os.path.join(TOOL, "src")

ITEM = re.compile(r"[（(]\s*([一二三四五六七八九十イロハニホヘト])\s*[）)]")
NUM = "一二三四五六七八九十"


def check_items(text):
    """괄호 안 항목 번호가 차례대로 가는지 본다. OCR 이 가장 잘 틀리는 자리다."""
    seen = [m.group(1) for m in ITEM.finditer(text)]
    bad, prev = [], None
    for s in seen:
        if s in NUM:
            i = NUM.index(s)
            if prev is not None and i != prev + 1 and i != 0:
                bad.append(f"（{s}）")
            prev = i
        else:
            bad.append(f"（{s}）")      # イロハ 가 섞이면 오독일 공산이 크다
            prev = None
    return bad


def run(imgs):
    if not os.path.exists(PY_):
        sys.exit(f"NDLOCR-Lite 가 없다: {TOOL}\n"
                 "  git clone https://github.com/ndl-lab/ndlocr-lite\n"
                 "  cd ndlocr-lite && python3 -m venv .venv\n"
                 "  .venv/bin/pip install -r requirements.txt\n"
                 "  (모델은 저장소에 들어 있다)")
    os.makedirs(OUT, exist_ok=True)
    for p in imgs:
        # 도구를 제 폴더에서 돌리므로(cwd=SRC) 상대 경로는 엉뚱한 곳을 가리킨다.
        p = os.path.abspath(p)
        tag = os.path.basename(p).replace(".png", "")
        dst = os.path.join(OUT, tag + ".txt")
        if os.path.exists(dst):
            print(f"  {tag} 그대로")
            continue
        r = subprocess.run([PY_, "ocr.py", "--sourceimg", p, "--output", OUT],
                           cwd=SRC, capture_output=True)
        if not os.path.exists(dst):
            print(f"  !! {tag} 실패\n{r.stderr.decode()[:300]}")
            continue
        t = open(dst).read()
        bad = check_items(t)
        print(f"  {tag} {len(t.strip()):5,}자"
              + (f"  !! 항목 번호 확인: {' '.join(bad)}" if bad else ""))


if __name__ == "__main__":
    a = sys.argv[1:]
    if a == ["--all"]:
        done = {f[:-4] for f in os.listdir(OUT)} if os.path.isdir(OUT) else set()
        a = [os.path.join(PAGES, f) for f in sorted(os.listdir(PAGES))
             if f.endswith(".png") and f[:-4] not in done]
    if not a:
        sys.exit(__doc__)
    run(a)
