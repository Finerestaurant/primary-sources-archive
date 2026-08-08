"""번역문에 괄호로 달아 놓은 OCR 원문을 걷어낸다.

    python3 열람기/원문병기제거.py --dry     # 얼마나 지워지는지만 본다
    python3 열람기/원문병기제거.py           # 실제로 지운다
    python3 열람기/원문병기제거.py CREST_전쟁  # 한 문서철만

## 왜 지우나

에이전트가 뭉갠 대목을 옮길 때마다 원문을 괄호로 달았다. 뜻은 좋았는데
**읽을 수가 없다.**

    …입법부와 행정부의 험한 싸움을 막기 위한 조치를 취할지는 알 수 없다.
    (원문 `that 2 domestic quarrel` / `legisiative- executive battle is net known`)

이런 것이 열여섯 문서철에 **16,000군데**다. 대부분은 도장 문구의 잡음이다.

    (원문 `Approved For Release @ROS/N FLAS iCBACRORER QO#57RO0S 1 PEF 00`)

## 지워도 잃는 것이 없다

**원본 OCR 은 `raw/*.txt` 에 언제나 그대로 있다.** 번역문은 읽으라고 있는
것이고, 원문 대조는 raw 와 `pages/` 의 지면이 맡는다.

## 무엇을 남기나

- `[원문 그대로]` — 숫자를 고치지 않았다는 **표시**다. 잡음이 아니다. 남긴다
- `(원문 「餘程瞠リスル」)` — 한자·가나 원문 인용. 잡음이 아니라 **자료**다. 남긴다
- `[판독 불가]` — 남긴다

곧 **괄호 안에 한자나 가나가 없는 `(원문 …)` 만 지운다.**
"""
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOTE = re.compile(r"\s*\(원문[^()]{0,400}\)")
CJK = re.compile(r"[぀-ヿ一-鿿]")
# **`notes` 는 건드리지 않는다.** 판단이 갈린 자리에 원문을 인용해 두는 것이
# 주석의 일이다. 처음에 여기 넣었다가 79건을 되돌렸다.
FIELDS = ("ko", "en", "title_ko", "subject_ko")


def strip(t):
    """괄호 안에 한자·가나가 없는 `(원문 …)` 만 뺀다."""
    out, n = [], 0
    i = 0
    for m in NOTE.finditer(t):
        if CJK.search(m.group(0)):
            continue
        out.append(t[i:m.start()])
        i = m.end()
        n += 1
    out.append(t[i:])
    s = "".join(out)
    s = re.sub(r"[ \t]{2,}", " ", s)          # 지운 자리에 남은 겹공백
    s = re.sub(r"[ \t]+([,.;:」』】\)])", r"\1", s)   # 문장부호 앞 공백
    s = re.sub(r"\n[ \t]+\n", "\n\n", s)
    return s, n


def main(only, dry):
    tot = files = 0
    for f in sorted(glob.glob(os.path.join(ROOT, "*", "tr", "*.json"))
                    + glob.glob(os.path.join(ROOT, "*", "*", "tr", "*.json"))):
        coll = os.path.relpath(f, ROOT).split(os.sep)[0]
        if only and coll not in only:
            continue
        try:
            d = json.load(open(f))
        except Exception:
            continue
        if not isinstance(d, dict):
            continue
        hit = 0
        for k in FIELDS:
            v = d.get(k)
            if isinstance(v, str) and "(원문" in v:
                s, n = strip(v)
                if n:
                    d[k] = s
                    hit += n
        if hit:
            files += 1
            tot += hit
            if not dry:
                json.dump(d, open(f, "w"), ensure_ascii=False, indent=1)
    print(f"{files}개 문서에서 {tot:,}군데를 뺐다" + ("  (어림)" if dry else ""))
    if not dry:
        print("문서철을 다시 지어라 — 각 pipeline/make_docs.py 그리고 build_site.py")


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    main(a or None, "--dry" in sys.argv)
