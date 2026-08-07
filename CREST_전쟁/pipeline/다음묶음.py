"""다음에 맡길 묶음을 내놓는다. **이미 맡긴 것을 다시 맡기지 않으려고 둔다.**

    python3 다음묶음.py 4          # 네 묶음을 내놓고 배정에 적는다
    python3 다음묶음.py --남은것    # 얼마나 남았는지만 본다
    python3 다음묶음.py --풀기 W049 W050   # 실패한 것을 배정에서 뺀다

## 왜 이것이 있나

에이전트를 물결로 나눠 돌리다 보면 **돌고 있는 것을 빼는 걸 잊는다.** 실제로
W049–W052 가 두 에이전트에 갔다. 둘 다 온전한 번역을 냈으니 망가지지는
않았지만, 같은 일을 두 번 시킨 것이고 한쪽이 다른 쪽을 덮었다.

그래서 **맡긴 것을 파일에 적는다.** 끝났는지(`tr/` 에 파일이 있는지)와
맡겼는지(여기 적혀 있는지)는 다른 것이다. 세션이 끊겨도 남는다.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BOOK = os.path.join(HERE, "배정.json")
BUD = 26000        # 묶음 하나의 글자 수
BIG = 20000        # 이보다 크면 홀로 맡긴다


def state():
    idx = json.load(open(os.path.join(ROOT, "raw/index.json")))
    done = set()
    for d in idx:
        p = os.path.join(ROOT, "tr", d["doc_id"] + ".json")
        if os.path.exists(p):
            try:
                if (json.load(open(p)).get("ko") or "").strip():
                    done.add(d["doc_id"])
            except Exception:
                pass
    given = set(json.load(open(BOOK))) if os.path.exists(BOOK) else set()
    return idx, done, given


def main(argv):
    idx, done, given = state()
    if "--풀기" in argv:
        given -= set(argv[argv.index("--풀기") + 1:])
        json.dump(sorted(given), open(BOOK, "w"), ensure_ascii=False, indent=1)
        print(f"배정에서 뺐다. 지금 맡긴 것 {len(given)}건")
        return
    todo = [d for d in idx if d["doc_id"] not in done and d["doc_id"] not in given]
    if "--남은것" in argv:
        print(f"전체 {len(idx)}건 · 끝난 것 {len(done)}건 · 맡긴 것 {len(given)}건 "
              f"· 아직 안 맡긴 것 {len(todo)}건 ({sum(x['chars'] for x in todo):,}자)")
        return

    want = int(argv[0]) if argv and argv[0].isdigit() else 4
    lots, cur, c = [], [], 0
    for x in todo:
        if x["chars"] > BIG:
            if cur:
                lots.append(cur)
                cur, c = [], 0
            lots.append([x["doc_id"]])
            continue
        if cur and c + x["chars"] > BUD:
            lots.append(cur)
            cur, c = [], 0
        cur.append(x["doc_id"])
        c += x["chars"]
    if cur:
        lots.append(cur)

    out = lots[:want]
    for l in out:
        given |= set(l)
    json.dump(sorted(given), open(BOOK, "w"), ensure_ascii=False, indent=1)
    for l in out:
        print(" ".join(l))
    print(f"# 맡긴 것 {len(given)}건 · 아직 안 맡긴 것 "
          f"{len(todo) - sum(len(l) for l in out)}건", file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1:])
