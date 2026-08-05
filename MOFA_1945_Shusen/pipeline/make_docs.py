"""번역 결과를 열람기 규격으로 바꾼다 — 이 문서철만의 사정을 여기서 흡수한다.

    python3 make_docs.py

읽는 것
    tr/dNNNN.json          번역 (TRANSLATION_SPEC 스키마)
    raw_docs/{s03,s06}/    복원한 일본어 원문 — 오른쪽 창에 그대로 붙는다
    raw_docs/*/index.json  문서가 어느 지면에서 시작하는지
    reading_pagemap.json   PDF 면 → 책의 인쇄 면 번호 (1696…1942)

쓰는 것
    reading/docs.json

이 문서철의 사정 세 가지.

  1. **두 절이 한 벌이다.** 「중립국 경유 화평 타진」과 「포츠담 선언의 수락」은
     같은 통로(스위스·스웨덴 공사관)의 앞뒤라 갈라 놓으면 이야기가 끊긴다.
     문서번호가 949~966 과 1074~1104 로 떨어져 있어도 한 목록에 시간순으로 놓는다.
  2. **오른쪽 창이 영문이 아니라 일본어다.** 미국 문서를 다루는 문서철은
     영문이 정본이었지만, 여기서는 구자체 가타카나 원문이 정본이다.
  3. **면 번호는 책의 것을 쓴다.** 절마다 1면부터 다시 세면 스캔 파일 이름이
     부딪힌다. 인쇄된 면 번호(1696…1942)는 책 전체에서 유일하다.
"""
import os, json, glob, re
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

SEC = {"s03": "二 中立国を通じた和平打診", "s06": "四 ポツダム宣言の受諾"}

# 새 줄로 시작하는 것들 — 앞줄이 꽉 찼더라도 여기서는 잇지 않는다
BREAK = re.compile(
    r"^(?:[一二三四五六七八九十]+、"          # 一、二、三、
    r"|（[イロハニホヘトチリヌ]）"             # （イ）（ロ）
    r"|（[0-9０-９]+）"                        # （1）（2）
    r"|[0-9０-９]+[、.]"
    r"|第[一二三四五六七八九十百千0-9]+[號号]"
    r"|別電|付記|附記|〔編注〕|編注|追而|尙|右)")


def _flow(lines):
    """꽉 찬 줄은 이어진 것, 짧은 줄은 문단이 끝난 것."""
    body = [len(l) for l in lines if len(l) >= 12]
    if not body:
        return [l for l in lines if l.strip()]
    keep = Counter(body).most_common(1)[0][0] - 2
    out, buf = [], ""
    for l in lines:
        if not l.strip():
            if buf:
                out.append(buf); buf = ""
            continue
        if buf and not BREAK.match(l):
            buf += l
        else:
            if buf:
                out.append(buf)
            buf = l
        if len(l) < keep:
            out.append(buf); buf = ""
    if buf:
        out.append(buf)
    return [x for x in out if x.strip()]


# 전보가 시작하는 자리 — 여기부터가 본문이고, 앞은 편자가 붙인 머리다.
BODY = re.compile(r"(本省|[ぁ-ヿ一-龥ー]{2,10})?\d+月\d+日(前|後|午前|午後)?[\d時分]*(發|着)$"
                  r"|^合?第[一二三四五六七八九十百千0-9]+[號号]")


def reflow(text):
    """세로쓰기 단을 문단으로 잇는다.

    조판이 한 줄 25자 안팎으로 꽉 채워 짜여 있어서, 복원한 텍스트는 스물다섯 자마다
    낱말 한복판에서 끊긴다. 그대로 두면 읽을 수가 없다.

    꽉 찬 줄은 뒷줄과 이어진 것이고, 짧은 줄은 거기서 문단이 끝난 것이다 —
    조판된 글을 되살리는 오래된 요령이다. 다만 항목 번호로 시작하는 줄은
    앞줄이 꽉 찼더라도 새로 시작한다.

    머리와 본문은 **단 폭이 다르다.** 편자가 붙인 머리(문서번호·발신·수신·제목,
    그리고 별전과 부기의 목록)는 좁은 단에 짜여 있어서, 본문 폭으로 재면
    제목이 발신자에 달라붙는다. 그래서 둘로 갈라 각자의 폭으로 잇는다.
    """
    lines = [l.rstrip() for l in text.split("\n")]
    cut = 0
    for i, l in enumerate(lines):
        if BODY.search(l):
            cut = i
            break
    head = _flow(lines[:cut]) if cut else []
    return "\n\n".join(head + _flow(lines[cut:]))


ASCII_RUN = re.compile("[A-Za-z][A-Za-z0-9 ,.\\-'\"();:/&\u25a1\u201c\u201d\u2019]{24,}")


def _letters(s):
    return re.sub(r"[^a-z]", "", s.lower())


def respace(raw, ko):
    """원문 쪽 영문을 번역본의 영문으로 갈아 끼운다.

    영문은 낱말 사이가 글자가 아니라 **자리**로 조판돼 있어, 텍스트 층에서 뽑으면
    띄어쓰기가 통째로 사라진다 — `Declarationdoesnotcomprise`. 게다가 로마자
    부분집합의 글리프까지 어긋나 `1945` 가 `19x5` 로, 숫자가 `□` 로 나온다.

    그런데 **번역본에 제대로 된 영문이 이미 있다.** 규칙상 영문은 번역하지 않고
    지면대로 옮겨 적게 했고, 옮긴 쪽이 지면과 한 글자씩 대조했기 때문이다.
    그러니 고쳐 쓸 것 없이 그쪽을 가져다 붙인다. 글자마저 어긋나 있으므로
    정확히 맞추려 하지 말고 **닮은 정도**로 짝을 찾는다.
    """
    from difflib import SequenceMatcher
    cand = []
    for m in ASCII_RUN.finditer(ko):
        seg = m.group(0).strip()
        if " " in seg:
            cand.append((_letters(seg), seg))
    if not cand:
        return raw

    def fix(m):
        run = m.group(0)
        if " " in run:
            return run
        key = _letters(run)
        if len(key) < 20:
            return run
        pos = [j for j, ch in enumerate(run) if ch.isalpha()]

        # 번역본 조각을 하나씩, 긴 것부터 원문 덩어리 안에서 찾아 갈아 끼운다.
        # 왼쪽부터 차례로 맞추려 들면 덩어리가 문장 한복판에서 시작할 때 첫 판이
        # 어긋나 통째로 실패한다. 그래서 자리를 찾아 끼우는 쪽으로 간다.
        edits = []
        for k, seg in sorted(cand, key=lambda x: -len(x[0])):
            if len(k) < 30:          # 짧은 조각은 엉뚱한 자리에 잘못 걸린다
                continue
            sm = SequenceMatcher(None, key, k, autojunk=False)
            blocks = [b for b in sm.get_matching_blocks() if b.size]
            if not blocks:
                continue
            covered = sum(b.size for b in blocks)
            if covered < len(k) * 0.8:
                continue
            lo = blocks[0].a
            hi = blocks[-1].a + blocks[-1].size
            if hi - lo > len(k) * 1.3:       # 너무 넓게 퍼져 맞으면 우연이다
                continue
            if any(not (hi <= s0 or e0 <= lo) for s0, e0, _ in edits):
                continue                      # 이미 갈아 끼운 자리와 겹친다
            edits.append((lo, hi, seg))
        if not edits:
            return run

        edits.sort()
        out, at = [], 0
        for lo, hi, seg in edits:
            out.append(run[at:pos[lo]])
            out.append(seg)
            at = pos[hi - 1] + 1
        out.append(run[at:])
        joined = " ".join(x.strip() for x in out if x.strip())
        # 이어 붙인 자리에서 문장부호가 겹친다 — `following: :` 같은 것
        return re.sub(r"([:.,;])\s+\1", r"\1", joined)

    return ASCII_RUN.sub(fix, raw)


def group_of(t):
    """칩 넷. 누가 누구에게 보냈는가로 가른다 — 그게 이 묶음의 결이다."""
    ty = (t.get("doc_type") or "")
    frm = (t.get("from") or "")
    to = (t.get("to") or "")
    if "조서" in ty or "詔書" in (t.get("title_ja") or "") or "성명" in ty:
        return "D"
    if "검토" in ty or "부기" in ty or "조약국" in frm:
        return "C"
    if "외무대신" in frm or "외상" in frm or "本省" in (t.get("place") or ""):
        return "B"          # 도쿄에서 나간 것
    return "A"              # 재외공관에서 들어온 것


def main():
    # 문서가 어느 지면에서 시작하는지 + 인쇄 면 번호
    pmap = json.load(open(os.path.join(ROOT, "reading_pagemap.json")))
    start, ends, sec_of, raw_of = {}, {}, {}, {}
    for tag in ("s03", "s06"):
        idx = json.load(open(os.path.join(ROOT, "raw_docs", tag, "index.json")))
        last = max(int(k) for k in pmap[tag])
        for i, e in enumerate(idx):
            no = e["no"]
            sec_of[no] = tag
            raw_of[no] = os.path.join(ROOT, "raw_docs", tag, e["file"])
            start[no] = pmap[tag][str(e["page"])]
            # 다음 문서가 시작하는 면까지가 이 문서의 자리다. 한 면에 두 문서가
            # 앉는 일이 있어 겹치는 면이 생기는데, 그 면은 양쪽 다에 넣는다.
            nxt = idx[i + 1]["page"] if i + 1 < len(idx) else last
            ends[no] = pmap[tag][str(nxt)]

    docs = []
    for path in sorted(glob.glob(os.path.join(ROOT, "tr", "d*.json"))):
        t = json.load(open(path))
        no = t.get("no") or int(re.sub(r"\D", "", os.path.basename(path)))
        tag = sec_of.get(no)
        if tag is None:
            print("  건너뜀 (원문 없음):", os.path.basename(path))
            continue
        a, b = start[no], max(start[no], ends.get(no, start[no]))
        pages = list(range(a, b + 1))

        meta = []
        for k, v in (("일자", t.get("date")), ("발신", t.get("from")), ("수신", t.get("to")),
                     ("발착", t.get("time")), ("장소", t.get("place")),
                     ("전보번호", t.get("msg_nr")), ("종류", t.get("doc_type"))):
            if v:
                meta.append({"k": k, "v": v, "txt": k in ("발신", "수신", "종류")})

        raw = respace(reflow(open(raw_of[no]).read()), t.get("ko") or "")
        low = t.get("confidence") not in (None, "high")

        docs.append({
            "id": "d%d" % no,
            "order": no,
            "date": t.get("date"),
            "group": group_of(t),
            "eyebrow": "문서 %d · %s" % (no, SEC[tag]),
            "title": t.get("title_ko") or t.get("title_ja") or "",
            "badge": t.get("msg_nr") or None,
            "list_right": "문서 %d" % no,
            "meta": meta,
            "summary": t.get("subject_ko"),
            "points": t.get("key_points_ko") or [],
            "primary": t.get("ko") or "",
            "secondary": raw,
            "notes": t.get("notes_ko") or [],
            "warn": bool(low),
            "pages": pages,
            "search": " ".join(filter(None, [t.get("title_ja"), " ".join(t.get("people") or [])])),
        })

    docs.sort(key=lambda d: (d["date"] or "", d["order"]))
    out = os.path.join(ROOT, "reading", "docs.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(docs, open(out, "w"), ensure_ascii=False, indent=1)
    n_low = sum(1 for d in docs if d["warn"])
    print(f"{len(docs)}건 → {out}  (확신 낮음 {n_low}건)")


if __name__ == "__main__":
    main()
