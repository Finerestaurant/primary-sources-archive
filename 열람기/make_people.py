"""인물 사전을 만들어 문서철마다 얹는다.

    python3 make_people.py                # people.json 을 만들고 collection.json 에 건다
    python3 make_people.py --check        # 만들지 않고 검사만

## 무엇을 하는가

문서를 옮긴 사람들이 `tr/*.json` 의 `people` 에 등장 인물을 적어 두었다.
그런데 표기가 제각각이다. 같은 도고 시게노리가 이렇게 흩어져 있다.

    東郷茂徳 (도고 시게노리) — 외무대신
    東鄕茂德 도고 시게노리 (외무대신)          ← 구자체
    도고(東郷茂徳, Togo) — 일본 외상
    Shigenori Togo 도고 시게노리 — 외무대신

이것을 한 사람으로 묶고, 짧은 소개를 붙여 `열람기/people.json` 에 모은다.
열람기는 이미 `terms` 라는 주석 장치를 가지고 있으므로, 그 규격에 맞춰
내놓기만 하면 본문에서 이름에 손을 올렸을 때 소개가 뜬다.

## 묶는 규칙

**한자 이름과 로마자 성명만 열쇠로 쓴다. 한글 표기는 열쇠가 아니다.**
한글로 묶으면 `헐`(Cordell Hull, 국무장관)과 `헐`(J. E. Hull, 육군 중장)이
한 사람이 된다. 실제로 처음에 그렇게 만들었다가 1,259개 표기가 한 덩어리로
뭉쳤다. 직위 낱말이 서로 다른 사람들 사이에 다리를 놓은 것이다.

구자체는 신자체로 맞춘다. 안 그러면 東鄕茂德과 東郷茂徳이 갈라진다.
"""
import collections
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(HERE, "people.json")

HAN_NAME = re.compile(r"[一-鿿]{2,5}")
LAT_NAME = re.compile(r"\b([A-Z][a-z]{2,})\b")
ROLE = re.compile(r"(대사|공사|장관|차관|총장|대신|주석|총리|위원|참모|사령|국장|고문|비서|"
                  r"대표|총독|지사|대통령|원수|제독|장군|수상|외상|중장|소장|대령|중령)")
STOP = {"外務", "大臣", "大使", "公使", "次官", "総長", "首相", "総理", "政府", "会議",
        "委員", "長官", "陸軍", "海軍", "米国", "英国", "日本", "帝国", "中国", "支那",
        "独国", "蘇連", "国務", "本省", "夫人", "公爵", "侯爵", "元帥", "中将", "少将",
        "大将", "提督"}
OLD2NEW = str.maketrans("鄕德眞澤學國會發廣鐵爲來條戰淺榮壽藝龍畵",
                        "郷徳真沢学国会発広鉄為来条戦浅栄寿芸竜画")

# 이름으로 쓰기에 너무 짧거나 흔해서 본문에서 오탐이 나는 것들
TOO_COMMON = {"헐", "그루", "딘", "킹", "리", "커크", "빔", "메이"}


def gather():
    raw = collections.Counter()
    where = collections.defaultdict(set)
    for f in sorted(glob.glob(os.path.join(ROOT, "*", "tr", "*.json"))):
        col = f.split(os.sep)[-3]
        try:
            d = json.load(open(f))
        except Exception:
            continue
        if not isinstance(d, dict):
            continue
        for p in (d.get("people") or []):
            if isinstance(p, str) and p.strip():
                raw[p.strip()] += 1
                where[p.strip()].add(col)
    return raw, where


TITLES = ("The", "Mr", "Dr", "Sir", "Prince", "General", "Admiral", "Ambassador",
          "Secretary", "Minister", "President", "Marshal", "Madam", "Madame")


def latin(s):
    head = re.split(r"\s+—\s+|—|:", s)[0]
    return [x for x in LAT_NAME.findall(head) if x not in TITLES]


def keys(s, solo_ok=()):
    """묶는 열쇠. `solo_ok` 에 든 성은 성 하나만으로도 묶는다."""
    head = re.split(r"\s+—\s+|—|:", s)[0]
    ks = set()
    for h in HAN_NAME.findall(head.translate(OLD2NEW)):
        if h not in STOP and not ROLE.search(h) and len(h) >= 2:
            ks.add("H:" + h)
    lat = latin(head)
    if len(lat) >= 2:
        ks.add("L:" + lat[-2] + " " + lat[-1])
        if lat[-1] in solo_ok:
            ks.add("S:" + lat[-1])
    elif len(lat) == 1 and lat[0] in solo_ok:
        ks.add("S:" + lat[0])
    return ks


def unambiguous_surnames(raw):
    """성 하나만 적힌 표기가 많다(`Winant 위넌트`). 그것도 묶어야 하는데,
    성만으로 묶으면 Cordell Hull 과 J. E. Hull 이 한 사람이 된다.

    그래서 **그 성에 딸린 이름이 한 가지뿐인 성만** 성으로 묶는다.
    Hull 은 Cordell 과 Edwin 둘이 붙으므로 빠지고, Winant 는 John 뿐이라 들어간다."""
    given = collections.defaultdict(set)
    for s in raw:
        lat = latin(s)
        if len(lat) >= 2:
            given[lat[-1]].add(" ".join(lat[:-1]))
    return {sur for sur, gs in given.items() if len(gs) == 1}


def cluster(raw):
    par = {}

    def find(x):
        par.setdefault(x, x)
        while par[x] != x:
            par[x] = par[par[x]]
            x = par[x]
        return x

    solo = unambiguous_surnames(raw)
    k2s = collections.defaultdict(list)
    for s in raw:
        for k in keys(s, solo):
            k2s[k].append(s)
    for _, ss in k2s.items():
        for s in ss[1:]:
            par[find(s)] = find(ss[0])

    g = collections.defaultdict(list)
    for s in raw:
        g[find(s)].append(s)
    return sorted(g.values(), key=lambda v: -sum(raw[x] for x in v))


def main(argv):
    raw, where = gather()
    groups = cluster(raw)
    print(f"표기 {len(raw):,}가지 → 인물 {len(groups):,}명")
    for th in (10, 5, 3):
        print(f"  {th}회 이상 {sum(1 for v in groups if sum(raw[x] for x in v) >= th)}명")

    bio_dir = os.path.join(HERE, "people_bio")
    bios = {}
    for f in sorted(glob.glob(os.path.join(bio_dir, "*.json"))):
        for x in json.load(open(f)):
            if x.get("term"):
                bios[x["term"]] = x
    print(f"  소개가 쓰인 인물 {len(bios)}명 ({bio_dir}/)")

    if "--check" in argv:
        return

    # 열람기 규격으로 내놓는다. 소개가 없는 사람은 싣지 않는다 — 이름만 뜨는
    # 손말이는 없는 것만 못하다.
    items, skipped, done = [], 0, set()
    for v in groups:
        n = sum(raw[x] for x in v)
        if n < 3:
            continue
        forms = sorted(v, key=lambda x: -raw[x])
        bio = None
        for f in forms:
            for t, b in bios.items():
                if t in f or any(a in f for a in (b.get("alias") or [])):
                    bio = b
                    break
            if bio:
                break
        # `mixed` 는 「이 묶음에 다른 사람이 섞였다」는 표시다. 그렇다고 통째로
        # 버리면 아깝다. 장제스 묶음에 부인 쑹메이링이 하나 섞였다고 장제스를
        # 빼는 것은 과하다. **소개가 쓰였으면 싣되, 섞인 사실을 주에 남긴다.**
        # 정말 두 사람이 반씩 뭉친 것이라면 소개를 쓴 쪽이 term 을 안 정했을
        # 테니 그때는 아래 `not bio` 에서 걸린다.
        if not bio:
            skipped += 1
            continue
        if bio.get("mixed") and bio.get("notes"):
            bio = dict(bio, points=(bio.get("points") or []) + [bio["notes"]])
        # 묶기가 완벽하지 않아 같은 사람이 여러 묶음으로 남는다(성만 적힌 표기가
        # 따로 떨어진다). 해롭지는 않다 — 본문에서 잡아내는 것은 alias 가 하고,
        # 소개는 term 으로 하나만 실으면 된다.
        if bio["term"] in done:
            continue
        done.add(bio["term"])
        items.append({k: bio[k] for k in ("term", "alias", "title", "body", "points")
                      if bio.get(k)})

    json.dump({"_": items}, open(OUT, "w"), ensure_ascii=False, indent=1)
    print(f"\n인물 {len(items)}명 → {OUT}  (소개 없음·섞임 {skipped}명은 뺐다)")

    # collection.json 에 건다. 이미 있는 terms 파일을 덮지 않고 뒤에 더한다.
    rel = os.path.join("..", "..", "열람기", "people.json")
    n = 0
    for f in sorted(glob.glob(os.path.join(ROOT, "*", "reading", "collection.json"))):
        c = json.load(open(f))
        t = c.get("terms")
        cur = [t] if isinstance(t, str) else list(t or [])
        if rel in cur:
            continue
        c["terms"] = cur + [rel]
        json.dump(c, open(f, "w"), ensure_ascii=False, indent=1)
        n += 1
    print(f"문서철 {n}개의 collection.json 에 걸었다")


if __name__ == "__main__":
    main(sys.argv[1:])
