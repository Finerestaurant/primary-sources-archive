"""이미 받아 둔 raw/*.txt 의 각주 절만 번호를 붙여 다시 쓴다.

첫 수집 때 각주 번호를 빠뜨렸다. 본문의 [주48]과 각주 목록이 대응되지 않으면
인용할 때 어느 주석인지 알 수 없다.

**본문은 건드리지 않는다.** 번역 작업이 본문을 기준으로 돌고 있어서,
본문이 바뀌면 이미 끝난 번역과 어긋난다. 각주 절만 교체한다.

    python fix_footnotes.py ../raw
"""
import os
import re
import sys
import time

RAW = sys.argv[1] if len(sys.argv) > 1 else "../raw"
VOL = sys.argv[2] if len(sys.argv) > 2 else "frus1945v06"

# frus_fetch 는 모듈을 읽는 시점에 argv 를 본다. 우리 인자를 그대로 두면
# 권종(VOL)을 "../raw" 로 잘못 읽는다.
sys.argv = [sys.argv[0], VOL]
from frus_fetch import BASE, extract, get   # noqa: E402  — 같은 추출 규칙을 쓴다
SEP = "\n\n----- 각주 -----\n"

for fn in sorted(os.listdir(RAW)):
    m = re.fullmatch(r"(d\d+)\.txt", fn)
    if not m:
        continue
    did = m.group(1)
    p = os.path.join(RAW, fn)
    body = open(p).read().split(SEP.strip())[0].rstrip()

    _, res = extract(get(f"{BASE}/{did}"), did)
    if res is None:
        print(f"!! {did} 다시 못 받음 — 그대로 둠")
        continue
    notes = res[1]
    if not notes:
        print(f"   {did} 각주 없음")
        continue
    numbered = sum(1 for n in notes if n.startswith("[주"))
    open(p, "w").write(body + SEP + "\n".join(notes) + "\n")
    print(f"   {did} 각주 {len(notes)}개 (번호 복원 {numbered}개)")
    time.sleep(0.4)
