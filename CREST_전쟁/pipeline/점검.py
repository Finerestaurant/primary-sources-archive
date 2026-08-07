"""번역 결과를 훑어 성한지 본다. **세션을 이어받을 때 맨 먼저 돌려라.**

    python3 CREST_전쟁/pipeline/점검.py           # 본다
    python3 CREST_전쟁/pipeline/점검.py --정리     # 묶인 배정을 푼다

## 왜 있나

에이전트가 한도에 걸려 죽으면 두 가지가 남는다.

    1. 반쪽 파일    ko 가 비었거나, 중간에서 끊겼거나, 영어가 그대로 남았거나
    2. 묶인 배정    `배정.json` 에는 맡겼다고 적혀 있는데 아무도 안 하고 있는 것

둘째가 고약하다. `다음묶음.py` 는 맡긴 것을 다시 내주지 않으므로, 묶인 채로
두면 **그 문서는 영영 배정되지 않는다.** 눈에 띄지도 않는다.

## --정리 는 언제 도는가

**에이전트가 하나도 돌고 있지 않을 때만 돌려라.** 돌고 있는 것까지 풀어
버리면 같은 일을 두 에이전트가 하게 된다. 세션을 새로 여는 첫 순간이 맞다.

## 무엇을 잡아내나

    깨진 JSON      json.load 가 안 된다. 쓰다 만 것이다
    ko 비었다       영문만 채워진 긴 문서(에이전트_지시_긴것.md)면 정상이다
    한글이 적다     ko 칸에 영어가 그대로 들어갔다. 실제로 한 건 있었다
                   병기한 원문 `기밀(CONFIDENTIAL)` 은 빼고 센다
    ko 가 짧다      en 대비 0.38 아래. 중간에서 끊긴 것이다
    칸이 다르다     16칸 스키마를 벗어났다
"""
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BOOK = os.path.join(HERE, "배정.json")
HAN = re.compile(r"[가-힣]")
PAREN = re.compile(r"\([^()가-힣]*\)")   # 괄호 안에 한글이 없는 것 = 병기한 원문
SCHEMA = {"doc_id", "date", "doc_type", "from", "to", "classification",
          "title_en", "title_ko", "subject_ko", "key_points_ko", "en", "ko",
          "redactions", "people", "confidence", "notes"}


def look():
    idx = json.load(open(os.path.join(ROOT, "raw/index.json")))
    done, half, sick = set(), [], []
    for d in idx:
        did = d["doc_id"]
        p = os.path.join(ROOT, "tr", did + ".json")
        if not os.path.exists(p):
            continue
        try:
            j = json.load(open(p))
        except Exception as e:
            sick.append((did, "깨진 JSON", str(e)[:50]))
            continue
        if set(j) != SCHEMA:
            sick.append((did, "칸이 다르다", str(set(j) ^ SCHEMA)[:50]))
        ko, en = (j.get("ko") or ""), (j.get("en") or "")
        if not ko.strip():
            half.append((did, len(en)))
            continue
        # 괄호로 병기한 원문을 빼고 센다. 서식이 많은 문서는 번역문이
        # `기밀(CONFIDENTIAL)` 꼴로 영문을 달고 다녀 한글 비율이 그냥
        # 떨어진다. W126·W131 이 그래서 헛짚혔다. 둘 다 온전한 번역이었다.
        bare = PAREN.sub("", ko)
        if len(bare) > 40 and len(HAN.findall(bare)) / len(bare) < 0.15:
            sick.append((did, "한글이 적다",
                         f"{len(HAN.findall(bare))/len(bare):.2f}"))
        elif en and len(ko) / len(en) < 0.38:
            sick.append((did, "ko 가 짧다", f"{len(ko)/len(en):.2f}"))
        else:
            done.add(did)
    return idx, done, half, sick


def main(argv):
    idx, done, half, sick = look()
    given = set(json.load(open(BOOK))) if os.path.exists(BOOK) else set()
    stuck = sorted(given - done - {h[0] for h in half})

    print(f"전체 {len(idx)}건 · 성한 것 {len(done)}건 · 남은 것 "
          f"{len(idx) - len(done)}건")
    if half:
        print(f"\n영문만 채워진 것 {len(half)}건 — 긴 문서다. 한국어만 쓰면 된다")
        for did, n in half:
            print(f"  {did}  en {n:,}자")
    if sick:
        print(f"\n손봐야 할 것 {len(sick)}건")
        for did, why, how in sick:
            print(f"  {did}  {why}  {how}")
    if stuck:
        print(f"\n맡겼는데 안 끝난 것 {len(stuck)}건")
        print("  " + " ".join(stuck))
        if "--정리" in argv:
            json.dump(sorted(given - set(stuck)), open(BOOK, "w"),
                      ensure_ascii=False, indent=1)
            print(f"  → 배정에서 풀었다. 이제 다음묶음.py 가 다시 내준다")
        else:
            print("  에이전트가 하나도 돌고 있지 않다면 --정리 로 풀어라")
    if not (sick or stuck):
        print("\n성하다")


if __name__ == "__main__":
    main(sys.argv[1:])
