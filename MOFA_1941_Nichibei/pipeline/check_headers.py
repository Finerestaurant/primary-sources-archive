"""초벌 OCR 의 머리글을 검사하고, 수상한 자리의 지면 조각을 잘라 둔다.

    python3 check_headers.py                 # 제八편 전부
    python3 check_headers.py 031 040         # 쪽 범위

## 왜 필요한가

NDLOCR-Lite 는 본문 글자를 97~99% 로 읽는다. 그런데 **머리글은 거의 못 읽는다.**
실측된 오독이다.

    문서번호   446              → 14
    날짜       昭和16年12月3日   → 昭和10年1月3日
    발신착신   ワシントン 12月3日 → ワシントン112月3日

굵은 아라비아 숫자와 큰 고딕 표제가 세로 본문용 모델에 안 맞는 것으로 보인다.
확대해 다시 돌려도 안 된다 — 네 번 돌려 네 번 다 다른 값이 나왔다.

그래서 **기계는 잡아내기만 하고, 고치는 것은 사람이 지면을 보고 한다.**
앞이 445니 446이겠지 하는 추론은 지어내는 것이다. 445호가 둘로 갈릴 수도 있고
날짜가 정말 예외일 수도 있다.

## 무엇을 잡는가

  1. 문서번호가 차례를 벗어난다
  2. 날짜가 이 편의 범위(1941년 11~12월) 밖이다
  3. 발신·착신 표기에 숫자가 겹친다 (`ワシントン112月`)
  4. 시각 기재가 반쪽으로 남는다 (`後7時20分発` → `後7時 分発`)
  5. 괄호 안 항목 번호가 차례가 아니다

## 무엇을 내놓는가

    raw/ocr/_headers.json     쪽마다 잡힌 것
    raw/ocr/hdr/<쪽>.png      수상한 쪽의 **머리글 조각만** 잘라 키운 그림

지면 한 장은 3,800토큰쯤 든다. 머리글 조각은 600~900이다. 옮기는 사람은
표시된 쪽의 조각만 열면 되니, 지면 전체를 여는 일이 없어진다.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OCR = os.path.join(ROOT, "raw", "ocr")
CROP = os.path.join(OCR, "hdr")
PAGES = os.path.join(ROOT, "pages")

TAG = "nichibei2_05"
YEAR_OK = ("昭和16年",)
MONTH_OK = ("11月", "12月")

DOCNO = re.compile(r"^\s*(\d{1,4})\s*(?=昭和|$)")
DATE = re.compile(r"(昭和\s*\d{1,2}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日|昭和\s*\d{1,2}\s*月\s*\d{1,2}\s*日)")
SENDRECV = re.compile(r"(ワシントン|本\s*省|伯林|ベルリン|羅馬)\s*([^\n]{0,24}?)(前発|後発|前着|後着|発|着)")
ITEM = re.compile(r"[（(]\s*([一二三四五六七八九十イロハニホヘト])\s*[）)]")
NUM = "一二三四五六七八九十"


def check(page, text):
    bad = []
    # 한 쪽에 문서가 여럿 실리므로 머리글도 여럿이다. 앞 14줄만 보다가
    # 36행에 있던 「本省12月7日後7時 分発」(20分 이 통째로 사라진 것)을 놓쳤다.
    # **쪽 전체를 본다.** 본문에는 이런 꼴이 거의 나오지 않아 오탐이 적다.
    head = text

    for m in DATE.finditer(head):
        d = m.group(1).replace(" ", "")
        if not d.startswith(YEAR_OK):
            bad.append(f"날짜 연도 「{d}」")
        elif not any(x in d for x in MONTH_OK):
            bad.append(f"날짜 월 「{d}」")

    for m in SENDRECV.finditer(head):
        mid = m.group(2)
        if re.search(r"\d{3,}", mid) or re.search(r"(\d)\1", mid):
            bad.append(f"발신착신 「{m.group(0).strip()}」")

    # 시각 기재가 반쪽으로 남는 일이 있다. 「後7時20分発」에서 「20分」이 통째로
    # 사라져 「後7時 分発」이 된 것을 실제로 놓쳤다. 「時」가 있는데 그 뒤의
    # 「分」 앞이 비어 있으면 숫자가 먹힌 것이다.
    for m in re.finditer(r"(前|後)\s*(\d{1,2})\s*時\s*(\d{0,2})\s*分", head):
        if not m.group(3):
            bad.append(f"시각 「{m.group(0).strip()}」")
    # 「時」나 「分」이 홀로 뜬 것도 잡는다
    for m in re.finditer(r"(?<![\d])時\s*\d{0,2}\s*分|(?<![\d時])\s\d{1,2}\s*分発", head):
        bad.append(f"시각 「{m.group(0).strip()}」")

    for line in head.split("\n"):
        m = DOCNO.match(line)
        if m:
            n = int(m.group(1))
            if not (380 <= n <= 480):            # 이 편의 문서번호 범위
                bad.append(f"문서번호 「{m.group(1)}」")

    seen = [m.group(1) for m in ITEM.finditer(text)]
    prev = None
    for s in seen:
        if s in NUM:
            i = NUM.index(s)
            if prev is not None and i not in (prev + 1, 0):
                bad.append(f"항목 번호 「（{s}）」")
            prev = i
        else:
            bad.append(f"항목 번호 「（{s}）」")
            prev = None
    return bad


def crop(page):
    """세로쓰기라 머리글은 오른쪽 위에 몰려 있다. 그 대목만 잘라 키운다."""
    from PIL import Image
    src = os.path.join(PAGES, page + ".png")
    if not os.path.exists(src):
        return None
    im = Image.open(src)
    w, h = im.size
    # 세로쓰기라 머리글은 오른쪽에 몰려 있다. **키우지 않는다.**
    # 확대하면 화소만 늘어 토큰이 지면 전체보다 오히려 많아진다.
    # 읽는 쪽은 어차피 긴 변 1568 로 줄여 보므로, 잘라 내는 것만으로 족하다.
    #
    # 처음에는 위쪽 46% 만 잘랐다가 **아래 단의 머리글을 놓쳤다.** 한 쪽이
    # 가로줄로 위아래 두 단으로 갈리고 문서가 둘 실리면 아래 단에도 머리글이 있다.
    # 그래서 높이는 전부 담고 폭만 줄인다.
    c = im.crop((int(w * 0.40), 0, w, h))
    os.makedirs(CROP, exist_ok=True)
    dst = os.path.join(CROP, page + ".png")
    c.save(dst)
    return dst


def main(argv):
    lo, hi = (int(argv[0]), int(argv[1])) if len(argv) == 2 else (1, 999)
    out, n_bad = {}, 0
    for f in sorted(os.listdir(OCR)):
        if not (f.startswith(TAG) and f.endswith(".txt")):
            continue
        page = f[:-4]
        if not (lo <= int(page[-3:]) <= hi):
            continue
        bad = check(page, open(os.path.join(OCR, f)).read())
        if bad:
            out[page] = bad
            crop(page)
            n_bad += 1
            print(f"  {page}  {' · '.join(bad[:4])}")
    os.makedirs(OCR, exist_ok=True)
    json.dump(out, open(os.path.join(OCR, "_headers.json"), "w"),
              ensure_ascii=False, indent=1)
    print(f"\n수상한 쪽 {n_bad}개 → raw/ocr/_headers.json · 조각 raw/ocr/hdr/")


if __name__ == "__main__":
    main(sys.argv[1:])
