"""OCR로 뽑은 영문의 줄바꿈을 문단으로 되돌린다.

    from reflow import reflow
    text = reflow(ocr_text)

## 왜 필요한가

OCR은 스캔에 찍힌 **물리적 줄**을 그대로 내놓는다. 타자기 문서는 한 줄이 60자쯤
이라, 한 문단이 예닐곱 조각으로 쪼개진 채 화면에 나온다. 읽을 수가 없다.

원문 자체를 고치지는 않는다 — `ocr/` 는 그대로 두고, 열람기에 넣을 때만 합친다.
원본 대조가 필요하면 스캔을 보면 된다.

## 무엇을 합치고 무엇을 남기나

합치면 안 되는 줄이 있다. 전문 머리(`FROM:` `TO:` `NR:`), 번호 항목, 서명,
대문자 머리말, 표. 이런 것은 줄바꿈 자체가 정보다.

판단 기준은 하나다 — **앞줄이 문장으로 끝났는가.** 끝나지 않았고 다음 줄이
독립 항목이 아니면 이어진 문장으로 본다. 타자기 문서는 오른쪽 끝까지 쓰다가
넘어가므로 이 규칙이 잘 맞는다.
"""
import re

# 문장이 끝난 것으로 보는 자리
END = re.compile(r'[.!?:;”"’\)\]]\s*$')

# 언제나 그 자체로 한 줄인 것 — 도장·기관명·쪽표시. 이어질 일이 없다.
ALONE = re.compile(r"""^\s*(
      \[\d+면\]
    | \[[^\]]{0,40}\]\s*$                    # [Excerpt] 같은 편집자 표시
    | \.\s*\.\s*\.                           # 편집자 생략
    | /s/
    | [A-Z][A-Z0-9 ./&'"()\-]{2,}\s*$        # TOP SECRET, HEADQUARTERS (쉼표 없는 대문자)
)""", re.X)

# 새 항목이 시작되는 자리 — 앞은 끊되, 뒷줄이 이어질 수는 있다.
KEEP = re.compile(r"""^\s*(
      (SUBJECT|TO|FROM|INFO|NR|REF|DATE|TOO|MCN|CITE|CM|PRIORITY
       |MEMORANDUM(\s+\w+)?|SECTION|ANNEX|INCL|ENCL)\b\s*[:.]
    | [0-9]{1,3}\s*[.)]\s                    # 1.  2)
    | [a-z]\s*[.)]\s                         # a.  b)
    | \(\s*[a-z0-9]{1,3}\s*\)                # (a) (1)
    | [-–—*•]\s
)""", re.X)

# 짧고 마침표로 끝나면 그 자체로 한 줄 (서명, 직함, 날짜)
SHORT = 46


def reflow(text, short=SHORT):
    if not text:
        return text
    raw = [l.rstrip() for l in text.split("\n")]
    out, buf = [], []

    def flush():
        if buf:
            out.append(" ".join(buf))
            buf.clear()

    for i, ln in enumerate(raw):
        s = ln.strip()
        if not s:
            # 빈 줄이 문단 구분인지, 물리적 줄 사이 여백인지 본다.
            nxt = next((x.strip() for x in raw[i + 1:] if x.strip()), "")
            if buf and nxt and not END.search(buf[-1]) \
               and not KEEP.match(nxt) and not ALONE.match(nxt):
                continue                      # 문장이 이어진다 — 빈 줄을 무시
            flush()
            if out and out[-1] != "":
                out.append("")
            continue

        if ALONE.match(s):
            flush()
            out.append(s)
            continue

        if KEEP.match(s):
            # 새 항목이 시작된다. 앞은 끊되, 이 줄이 문장으로 끝나지 않았으면
            # 뒷줄이 이어질 수 있다 — `SUBJECT: Notes on … (For Trip to` / `Korea).`
            flush()
            if END.search(s):
                out.append(s)
            else:
                buf.append(s)
            continue

        if buf and buf[-1].endswith("-"):     # 낱말이 줄 끝에서 잘렸다
            buf[-1] = buf[-1][:-1] + s
            continue

        buf.append(s)
        if END.search(s) and len(s) < short:
            flush()

    flush()
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()


if __name__ == "__main__":
    import json
    import statistics as st
    import sys

    src = sys.argv[1]
    d = json.load(open(src))
    key = sys.argv[2] if len(sys.argv) > 2 else "secondary"
    b = [len(x) for y in d for x in (y.get(key) or "").split("\n") if x.strip()]
    a = [len(x) for y in d for x in reflow(y.get(key) or "").split("\n") if x.strip()]
    print(f"줄 {len(b)} → {len(a)} · 평균 {st.mean(b):.0f}자 → {st.mean(a):.0f}자")
