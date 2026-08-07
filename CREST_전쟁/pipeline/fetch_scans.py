"""아카이브닷오르그에서 면 이미지를 받는다.

    python3 fetch_scans.py            # 안 받은 것만 이어서 받는다
    python3 fetch_scans.py --dry      # 무엇을 받을지만 세어 본다

읽는 것   raw/index.json
쓰는 것   pages/<번호>-01.jpg …   본문 (130dpi · 품질 72)
          thumbs/<번호>-01.jpg …  목록용 (40dpi)
          pipeline/scans.json     문서마다 몇 면인지

## 왜 PDF 를 받아 여기서 쪼개나

아카이브닷오르그는 면마다 이미지를 내주는 길도 있는데, 그러면 **문서 하나에
요청이 면 수만큼 간다.** 항목마다 `Image Container PDF` 가 이미 만들어져 있어
그것 하나만 받으면 되고, 쪼개는 일은 이쪽에서 한다. 309건이면 요청도 309번이다.

## 같은 문서가 두 벌 있다. 그것이 이 도구의 핵심이다

아카이브닷오르그에 CIA 문서가 **두 계열로 들어와 있다.**

    CIA-RDP82-00457R000100370010-3                              그 자체가 항목 이름
    cia-readingroom-document-cia-rdp82-00457r000100370010-3      같은 문서의 다른 벌

**두 벌이 다른 저장 노드에 놓여 있다.** 그래서 한쪽이 503 을 내도 다른 쪽은
멀쩡한 일이 잦다. 실제로 처음 스무 건에서 여덟 건이 앞의 길로 실패했는데
뒤의 길로는 모두 받아졌다. **한 길만 쓰면 못 받는 것이 생긴다.**

파일 이름 규칙이 계열마다 다르다.

    항목 CIA-RDP82-...          파일 CIA-RDP82-....pdf        (대문자)
    항목 cia-readingroom-...    파일 cia-rdp82-....pdf        (소문자, 앞머리 없이)
    항목 cia-readingroom-...    파일 0005657579.pdf           (숫자 번호는 이 길뿐)

**항목 이름으로 파일을 부르면 404 다.** 항목 이름과 파일 이름은 다른 것이다.

## 그 밖에 알아 둘 것

**식별자는 대문자다.** 소문자로 부르면 404 다. 본문(`_djvu.txt`)은 소문자로도
받아지기 때문에 이 함정이 늦게 드러난다.

**503 은 우리가 막힌 것이 아니다.** `download.php` 의 `quickFileRedir` 가
`exit_service_unavailable` 로 죽는 것이고, **문서마다 갈린다.** 같은 시각에
어떤 문서는 200 이고 어떤 문서는 503 이다. 기다려도 안 살아나므로 오래 매달리지
말고 다음 주소로 넘긴다.

**`www.cia.gov/readingroom` 은 쓸 수 없다.** 자동 요청을 첫 화면으로 돌려보낸다.
"""
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

import fitz
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PAGES = os.path.join(ROOT, "pages")
THUMBS = os.path.join(ROOT, "thumbs")
STATE = os.path.join(HERE, "scans.json")

DPI, Q = 130, 72          # 면당 100KB 안팎. 타자기 글씨가 읽힌다
THUMB_DPI, THUMB_Q = 40, 70
PAUSE = 3.0               # 한 건 받고 쉬는 시간. 503 이 잦아 넉넉히 둔다
MAX_PAGES = 60            # 한 문서에서 이보다 많으면 앞부분만. 지금은 걸리는 것이 없다


def get(url, tries=2):
    """빈 응답과 503 을 견딘다. **오래 매달리지 않는다** — 노드가 죽은 것은
    기다려도 안 살아나므로, 짧게 두 번 보고 다음 주소로 넘긴다."""
    wait = 4
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=90) as r:
                b = r.read()
            if b:
                return b
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None          # 없는 것은 기다려도 안 생긴다
        except Exception:
            pass
        time.sleep(wait)
        wait *= 2
    return None


def pdf_urls(crest):
    """받을 주소를 **차례대로** 내놓는다. 앞의 것이 안 되면 뒤의 것으로 간다.

    같은 문서가 아카이브닷오르그에 두 벌 있다. 하나는 CREST 번호가 그대로
    항목 이름인 것이고, 다른 하나는 `cia-readingroom-document-` 가 붙은 것이다.
    **두 벌이 다른 저장 노드에 놓여 있어서**, 한쪽이 죽어 있어도 다른 쪽은 산다.
    실제로 그런 일이 잦다.
    """
    low = crest.lower()
    if re.fullmatch(r"\d+", crest):
        # CIA 열람실 계열은 이 한 길뿐이다
        return [f"https://archive.org/download/cia-readingroom-document-{crest}/{crest}.pdf"]
    return [
        f"https://archive.org/download/{crest.upper()}/{crest.upper()}.pdf",
        f"https://archive.org/download/cia-readingroom-document-{low}/{low}.pdf",
    ]


def jpeg(page, dpi, q):
    pix = page.get_pixmap(dpi=dpi)
    im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    b = io.BytesIO()
    im.save(b, "JPEG", quality=q, optimize=True, progressive=True)
    return b.getvalue()


def main(dry=False):
    idx = json.load(open(os.path.join(ROOT, "raw/index.json")))
    state = json.load(open(STATE)) if os.path.exists(STATE) else {}
    todo = [d for d in idx if d["doc_id"] not in state]
    print(f"문서 {len(idx)}건 · 이미 받은 것 {len(state)}건 · 받을 것 {len(todo)}건")
    if dry:
        return
    os.makedirs(PAGES, exist_ok=True)
    os.makedirs(THUMBS, exist_ok=True)

    ok = fail = 0
    for n, d in enumerate(todo, 1):
        did = d["doc_id"]
        pdf = None
        for u in pdf_urls(d["crest"]):
            pdf = get(u)
            if pdf:
                break
        if not pdf:
            print(f"  [{n}/{len(todo)}] {did}  못 받았다  {d['crest']}")
            fail += 1
            time.sleep(PAUSE)
            continue
        try:
            doc = fitz.open(stream=pdf, filetype="pdf")
        except Exception as e:
            print(f"  [{n}/{len(todo)}] {did}  PDF 가 아니다: {e}")
            fail += 1
            time.sleep(PAUSE)
            continue
        kb = 0
        cnt = min(doc.page_count, MAX_PAGES)
        for i in range(cnt):
            p = doc[i]
            name = f"{did}-{i + 1:02d}.jpg"
            big = jpeg(p, DPI, Q)
            open(os.path.join(PAGES, name), "wb").write(big)
            open(os.path.join(THUMBS, name), "wb").write(jpeg(p, THUMB_DPI, THUMB_Q))
            kb += len(big) // 1024
        state[did] = cnt
        json.dump(state, open(STATE, "w"), ensure_ascii=False, indent=1)
        ok += 1
        print(f"  [{n}/{len(todo)}] {did}  {cnt}면  {kb}KB")
        time.sleep(PAUSE)

    tot = sum(state.values())
    print(f"\n받은 문서 {len(state)}건 · 면 {tot}장 · 실패 {fail}건")


if __name__ == "__main__":
    main(dry="--dry" in sys.argv)
