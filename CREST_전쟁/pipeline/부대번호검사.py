"""번역이 원문에 없는 부대 번호를 만들어 내지 않았는지 본다.

    python3 CREST_전쟁/pipeline/부대번호검사.py [X117 X154 ...]

## 왜 있나

**뭉갠 글자를 숫자로 옮기는 위반이 실제로 났다.** X245 에서 원문의
`h Field Army` 가 `4 Field Army` 로, `l, Field Army` 가 `1 Field Army` 로
바뀌었다. 어느 야전군이 조선에 병력을 보냈는가는 그 문서의 내용 자체다.

**길이 검사로는 안 잡힌다.** 번역은 온전하고 말도 매끄럽다. 원문과 숫자를
맞대 봐야만 드러난다.

## 어떻게 보나

번역문(`en`)에서 `<숫자> Division` 꼴을 뽑아, 그 숫자가 원문(`raw/*.txt`)에
있는지 본다. 없으면 지어낸 것이다.

**헛짚음이 있다.** 원문이 줄바꿈으로 갈라 놓았거나(`194\nDivision`),
`194th` 처럼 접미사가 붙은 경우다. 그래서 숫자만 따로도 찾아본다.
**그래도 남는 것은 사람이 원문을 열어 봐야 한다. 자동으로 고치지 마라.**
"""
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KIND = r"(?:Field Army|Army Group|Division|Div\b|Corps|Regiment)"
UNIT = re.compile(r"(\d{1,3})\s*(?:st|nd|rd|th)?\s+(" + KIND + ")")


def main(only):
    hit = 0
    for f in sorted(glob.glob(os.path.join(ROOT, "tr", "*.json"))):
        did = os.path.basename(f)[:-5]
        if only and did not in only:
            continue
        rp = os.path.join(ROOT, "raw", did + ".txt")
        if not os.path.exists(rp):
            continue
        raw = open(rp, errors="replace").read()
        nums_raw = set(re.findall(r"\d{1,3}", raw))
        en = json.load(open(f)).get("en") or ""
        made = sorted({(n, k) for n, k in UNIT.findall(en) if n not in nums_raw})
        if made:
            hit += 1
            print(f"{did}  " + " · ".join(f"{n} {k}" for n, k in made))
    print(f"\n원문에 그 숫자가 아예 없는 것 {hit}건 — 열어서 확인해라")


if __name__ == "__main__":
    main([a for a in sys.argv[1:] if not a.startswith("--")])
