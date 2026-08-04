"""복원한 지면을 문서 단위로 자른다.

이 책은 문서마다 머리가 붙는다 — 문서번호, 날짜, 발신·수신, 제목, 발신지와
발·착 시각. 그 머리가 곧 경계다.

    949 昭和20年3月9日  在スウエーデン岡本公使より 重光外務大臣宛（電報）
    連合国側における日本からの和平打診説について
    ストックホルム3月9日發 / 本省3月12日前10時20分着
    第一五九號

성가신 것은 **문서번호의 자릿수**다. 세 자리(949)도 있고 네 자리(1086)도 있는데,
번호 뒤에 판식 기호 한 글자가 더 붙는 일이 있어 949 가 9499 로 읽힌다.
자릿수만 봐서는 가를 수 없다. 다만 **번호는 반드시 1씩 늘어난다** — 그 성질로
앞뒤를 맞춰 자릿수를 정한다.

    python3 segment.py ../text/s03.json ../raw_docs/s03

문서마다 `dNNNN.txt` 한 장. 번역은 이 파일을 읽는다.
"""
import sys, os, json, re

# 날짜 자리에 판독 못 한 글자(□)나 따옴표가 끼는 지면이 있다. 느슨하게 잡는다.
HEAD = re.compile(r"(?P<no>\d{3,5})\D{0,2}昭和(?P<y>\d+)年(?P<m>\d+)月(?P<d>[^日]{0,6})日")


def pick(raw, prev):
    """번호는 1씩 는다. 그 성질로 자릿수를 정한다."""
    if prev is not None:
        for n in (3, 4):
            if len(raw) >= n and int(raw[:n]) == prev + 1:
                return int(raw[:n])
    return int(raw[:4]) if len(raw) >= 4 else int(raw[:3])


def main(argv):
    src, out = argv[1], argv[2]
    pages = json.load(open(src))["pages"]
    docs, cur, prev = [], None, None
    for p in pages:
        for ln in p["text"].split("\n"):
            ms = list(HEAD.finditer(ln))     # 한 줄에 문서 둘이 붙어 나오는 지면이 있다
            if not ms:
                if cur is not None:
                    cur["lines"].append(ln)
                continue
            if cur is not None and ms[0].start() > 0:
                cur["lines"].append(ln[:ms[0].start()])
            for j, m in enumerate(ms):
                no = pick(m.group("no"), prev)
                prev = no
                end = ms[j + 1].start() if j + 1 < len(ms) else len(ln)
                cur = {"no": no, "y": int(m.group("y")), "m": int(m.group("m")),
                       "d": m.group("d"), "page": p["page"],
                       "lines": [ln[m.start():end]]}
                docs.append(cur)
    # 첫 문서는 견줄 앞이 없어 자릿수를 못 정한다. 두 번째로 되짚는다.
    if len(docs) > 1 and docs[0]["no"] != docs[1]["no"] - 1:
        docs[0]["no"] = docs[1]["no"] - 1

    os.makedirs(out, exist_ok=True)
    idx = []
    for d in docs:
        body = "\n".join(d["lines"])
        name = "d%d.txt" % d["no"]
        open(os.path.join(out, name), "w").write(body)
        day = d["d"] if d["d"].isdigit() else None
        date = "19%02d-%02d-%s" % (d["y"] + 25, d["m"], day.zfill(2) if day else "??")
        idx.append({"no": d["no"], "date": date, "page": d["page"],
                    "chars": len(body), "file": name})
        print(f"  d{d['no']}  {date}  {d['page']:2d}면부터  {len(body):6d}자")
    json.dump(idx, open(os.path.join(out, "index.json"), "w"), ensure_ascii=False, indent=1)
    print(f"문서 {len(docs)}건 · {sum(i['chars'] for i in idx)}자 → {out}")


if __name__ == "__main__":
    main(sys.argv)
