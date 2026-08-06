"""긴 문서의 뼈대를 짓는다 — 영문은 기계로, 한국어는 비워 둔다.

    python3 mkskel.py P01 P08 P12 P43

## 왜 이것이 있나

**2만 자를 넘는 문서에서 에이전트가 중단된다.** 「Output blocked by content
filtering policy」다. 영문 전문을 통째로 다시 뱉는 대목에서 걸리고, 1만 자
아래에서는 걸리지 않는다.

그래서 그런 문서만 **영문과 한국어를 갈라 만든다.** 영문은 여기서 기계로
채우고, 에이전트에게는 한국어만 맡긴다. 번역은 옮기는 일이라 걸리지 않는다.

## 무엇을 하는가

    줄 끝 하이픈으로 잘린 낱말을 잇는다      interpreta-\ntion → interpretation
    문단을 되돌린다                          ../../열람기/reflow.py

**그뿐이다. 낱말을 고치지 않는다.** 그래서 이 방법은 **OCR 이 깨끗할 때만
쓴다.** 판단서(ORE)처럼 인쇄된 문서는 깨끗하고, 타자기로 쳐서 마이크로필름으로
뜬 현장 첩보보고는 그렇지 않다. 뭉갠 문서에 쓰면 교정 안 된 영문이 그대로
올라간다.

교정하지 않았다는 사실은 각 문서의 `notes` 에 적힌다. 읽는 사람이 알아야 한다.
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "..", "열람기"))
from reflow import reflow

NOTE = ("이 문서는 영문(en)을 손으로 교정하지 않았다. 원본 OCR 이 깨끗해서 줄 끝 "
        "하이픈으로 잘린 낱말을 잇고 문단을 되돌리는 기계 처리만 했다"
        "(pipeline/mkskel.py). 뭉갠 글자는 원문 그대로 남아 있다. "
        "원본 OCR 은 raw/{did}.txt 에 있다.")


def english(raw):
    """줄 끝 하이픈을 잇고 문단을 되돌린다."""
    return reflow(re.sub(r'(?<=[a-z])-[ \t]*\n[ \t]*(?=[a-z])', '', raw))


def main(ids):
    idx = {d["doc_id"]: d for d in json.load(open(os.path.join(ROOT, "raw/index.json")))}
    for did in ids:
        meta = idx[did]
        en = english(open(os.path.join(ROOT, "raw", did + ".txt")).read())
        out = os.path.join(ROOT, "tr", did + ".json")
        if os.path.exists(out):
            print(f"  이미 있다, 건너뛴다: {did}")
            continue
        json.dump({
            "doc_id": did, "date": meta["date"], "doc_type": "정세 판단서",
            "from": None, "to": None, "classification": None,
            "title_en": meta["title"], "title_ko": "", "subject_ko": "",
            "key_points_ko": [], "en": en, "ko": "",
            "redactions": [], "people": [], "confidence": "medium",
            "notes": NOTE.format(did=did),
        }, open(out, "w"), ensure_ascii=False, indent=1)
        print(f"  {did}  영문 {len(en):,}자 → {out}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1:])
