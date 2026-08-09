"""JACAR(아시아역사자료센터)에서 낱장 문서(件名) 단위로 PDF를 받아 지면 이미지로 쪼갠다.

    python3 jacar_fetch.py <레퍼런스코드> [<레퍼런스코드> ...]
    python3 jacar_fetch.py --list 문서목록.json          # 목록에 있는 것 전부
    python3 jacar_fetch.py --expand <簿冊 레퍼런스코드>    # 묶음의 하위 항목 코드만 뽑아 보여준다

산출물
    raw/<코드>.pdf         원본 PDF (JACAR가 지면을 낱장 PNG를 이어붙여 만든 것)
    pages/<코드>-01.jpg    지면 이미지. CREST_전쟁과 같은 이름 규칙(문서번호-쪽번호)

## 어떻게 주소를 얻는가

JACAR는 `/das/meta/<코드>` (목록·서지사항)와 `/das/image/<코드>` (PDF.js 뷰어)
가 따로 있다. **메타 페이지는 SPA 껍데기만 오고 실 데이터가 없다.** 뷰어
페이지 쪽 HTML 안에 실제 PDF 경로가 JSON 문자열로 이미 박혀 있다 — 브라우저
없이 `curl` 수준으로 받을 수 있다는 뜻이다. (예: content/item/aj12/
C200007804400/raw/C11110925000.c0947120001.....pdf)

묶음(簿冊) 페이지에는 하위 항목의 레퍼런스 코드가 체크박스 `value="aj11/C코드"`
형태로 들어 있다 — `--expand` 가 이걸 긁어 목록을 만든다. **다만 페이지가
넘어가면(20건 초과) 다음 페이지 코드는 못 가져온다** — JACAR 목록이 자바스크립트
페이지네이션이라, 넘는 분은 `--expand` 결과를 보고 사람이 다음 페이지를 열어
손으로 보태야 한다.
"""
import json
import os
import re
import sys
import time
import subprocess
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (research; personal use; primary-sources-archive)"}
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RAW = os.path.join(ROOT, "raw")
PAGES = os.path.join(ROOT, "pages")
os.makedirs(RAW, exist_ok=True)
os.makedirs(PAGES, exist_ok=True)


def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def pdf_url_of(refcode):
    """뷰어 페이지(/das/image/)에서 실제 PDF 경로를 뽑는다. 못 찾으면 None.

    메타 페이지(/das/meta/)는 SPA 껍데기만 오고 실제 데이터가 없다 — 반드시
    뷰어 페이지 쪽이라야 PDF.js 에 넘길 경로가 HTML 안에 박혀 있다."""
    html = fetch(f"https://www.jacar.archives.go.jp/das/image/{refcode}#1").decode("utf-8", "ignore")
    m = re.search(
        r'\\/content\\/item\\/(aj\d+)\\/(\w+)\\/raw\\/([^"\\]+\.pdf)', html)
    if not m:
        m = re.search(
            r'/content/item/(aj\d+)/(\w+)/raw/([^"\']+\.pdf)', html)
    if not m:
        return None
    aj, itemid, fname = m.groups()
    return f"https://www.jacar.archives.go.jp/content/item/{aj}/{itemid}/raw/{fname}"


def expand_bundle(refcode):
    """簿冊 코드의 하위 件名 코드를 뽑는다. 20건 넘으면 1페이지만 나온다."""
    html = fetch(f"https://www.jacar.archives.go.jp/das/meta/{refcode}").decode("utf-8", "ignore")
    ids = re.findall(r'name="id" value="aj\d+/([A-Za-z0-9]+)"', html)
    seen, out = set(), []
    for i in ids:
        if i not in seen and i != refcode:
            seen.add(i)
            out.append(i)
    return out


def fetch_one(refcode):
    dst_pdf = os.path.join(RAW, f"{refcode}.pdf")
    if not os.path.exists(dst_pdf):
        url = pdf_url_of(refcode)
        if not url:
            print(f"  ! {refcode} — PDF 경로를 못 찾았다")
            return False
        data = fetch(url)
        open(dst_pdf, "wb").write(data)
        time.sleep(0.5)  # 남의 서버다
    # 이미 지면이 있으면 건너뛴다
    if os.path.exists(os.path.join(PAGES, f"{refcode}-01.jpg")):
        print(f"  = {refcode} (이미 있음)")
        return True
    out_prefix = os.path.join(PAGES, f"{refcode}-")
    subprocess.run(
        ["pdftoppm", "-jpeg", "-r", "200", dst_pdf, out_prefix.rstrip("-") + "-tmp"],
        check=True)
    # pdftoppm 은 -01, -1 등 자릿수가 페이지 수에 따라 달라진다. 두 자리로 통일한다.
    made = sorted(f for f in os.listdir(PAGES) if f.startswith(f"{refcode}-tmp"))
    for i, f in enumerate(made, 1):
        os.rename(os.path.join(PAGES, f), os.path.join(PAGES, f"{refcode}-{i:02d}.jpg"))
    print(f"  + {refcode} — {len(made)}면")
    return True


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    if args[0] == "--expand":
        for code in expand_bundle(args[1]):
            print(code)
        sys.exit(0)
    if args[0] == "--list":
        doclist = json.load(open(args[1]))
        codes = [d["ref"] for event in doclist["events"] for d in event["docs"]]
    else:
        codes = args
    print(f"{len(codes)}건 받는다")
    ok = 0
    for c in codes:
        if fetch_one(c):
            ok += 1
    print(f"\n{ok}/{len(codes)}건 완료 -> {PAGES}/")
