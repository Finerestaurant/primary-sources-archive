"""연표 바(chrono.json)와 주제 항목(site.json)의 사건을 하나로 합친다.

    python3 make_events.py [--write]

## 왜

같은 사건이 두 군데에 따로 적혀 있었다.

    열람기 아래 연표 바   chrono.json   47항   date · label · note
    색인 화면 주제 항목   site.json    160항   when · who · what · col · doc

같은 1945년 5월 8일을 바에서는 「독일 항복」이라 적고, 주제에서는 따로 한 줄을
썼다. 둘이 서로를 모른다. 바를 고쳐도 주제는 안 바뀌고, 주제에 문서를 걸어도
바는 여전히 점 하나다. 같은 날짜를 양쪽이 적은 것이 17건이다.

## 합친 뒤의 모양

**사건 하나에 대한 사실은 한 군데에만 둔다.** 날짜·이름·어느 국면인지·문서.
그 위에 **주제마다 자기 문장을 얹는다.**

    chrono.json   사건 (사실)      id · date · label · arc · bar · where · note · docs
    site.json     주제 위의 한 줄   ev · who · what · flag

문장을 주제 쪽에 남기는 이유가 있다. `veday-1945/d235` 한 문서를 「독일의 항복」과
「쓰이지 않은 문서」가 각각 다른 문장으로 적었다 — 하나는 「그날 서명한 것은 그
문서가 아니었다」, 하나는 「끝내 안 썼다」. 그 두 문장이 이 저장소가 파는 물건이라
사건 쪽으로 끌어올려 하나로 만들면 안 된다.

## bar

**연표 바는 성글어야 값이 있다.** 12년에 47개라 눈에 들어온다. 주제의 160항을
다 밀어 넣으면 바가 빗금이 된다. 그래서 저장은 하나로 하되 `bar: true` 인 것만
바에 띄운다. 지금 바에 있던 47개가 그것이다.

## 날짜와 표기

`when` 은 화면에 보이는 글자지 기계가 읽는 날짜가 아니다 — 「08.14 20:05」처럼
해가 없고 시각이 붙은 것이 「일본의 항복」에 열넷 있다. 같은 순간을 가세와 미국이
따로 적은 대목이라 시각이 곧 내용이다. 그래서 기계용 `date` 와 화면용 `disp` 를
따로 둔다. 해가 없는 것은 **같은 주제에서 바로 앞에 나온 온전한 날짜의 해**를
물려받는다 — 항목이 시간순이라 이것으로 맞는다.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
WRITE = "--write" in sys.argv

CH = json.load(open(os.path.join(HERE, "chrono.json"), encoding="utf-8"))
SITE = json.load(open(os.path.join(ROOT, "site.json"), encoding="utf-8"))

# 사건 — 큰 국면. 이벤트마다 하나를 단다.
ARCS = [
    {"key": "wwii", "label": "2차대전", "note": "진주만에서 도쿄만까지"},
    {"key": "korea-div", "label": "조선의 분단",
     "note": "카이로의 「in due course」에서 1950년 6월까지"},
    {"key": "korea-war", "label": "한국전쟁", "note": "개전에서 정전협정까지"},
]


# 국면은 **어느 주제에 실린 줄인지**로 정한다. 날짜로 가르면 1945년 8월 14일
# 20시 05분(가세가 번스 회답을 받은 기록)이 「조선의 분단」으로 넘어간다.
# 같은 날 같은 시각을 두 나라가 적은 대목인데, 그건 일본 항복 이야기다.
THREAD_ARC = {"two-twenty": "wwii", "reims": "wwii", "instrument": "wwii",
              "ten-days": "wwii", "in-due-course": None}   # None 이면 날짜로 가른다


def arc_of(date, label="", thread=None):
    """주제가 국면을 정한다. 조선 주제와 주제에 안 실린 이정표만 날짜로 가른다."""
    fixed = THREAD_ARC.get(thread)
    if fixed:
        return fixed
    if date >= "1950-06-25":
        return "korea-war"
    if thread == "in-due-course":
        return "korea-div"
    # 주제에 실리지 않은 이정표 — 이름과 날짜로 가른다
    if re.search(r"카이로|얄타|신탁|조선|한국|38선|김구|이승만|철수", label):
        return "korea-div"
    if date >= "1948-08-15":          # 대한민국 수립 뒤의 이정표는 조선 쪽이다
        return "korea-div"
    return "wwii"


def norm_date(when, carry):
    """화면 표기 → (기계 날짜, 화면 표기). carry 는 물려받을 해."""
    w = when.strip()
    m = re.match(r"^(\d{4})[.\-](\d{2})[.\-](\d{2})$", w)
    if m:
        return f"{m[1]}-{m[2]}-{m[3]}", None
    m = re.match(r"^(\d{4})[.\-](\d{2})$", w)
    if m:
        return f"{m[1]}-{m[2]}", None
    if re.match(r"^\d{4}$", w):
        return w, None
    # 해가 없다 — 「08.14」 「08.14 20:05」 「08.11 밤」.
    # 뒤에 붙는 것은 시각일 수도 「밤」 같은 말일 수도 있다. 둘 다 표기에 남긴다.
    m = re.match(r"^(\d{2})[.\-](\d{2})(?:\s+(\S.*))?$", w)
    if m and carry:
        return f"{carry}-{m[1]}-{m[2]}", w
    return None, w


# ---------------------------------------------------------------- 사건 모으기
#
# **사건의 단위는 하루가 아니다.** 처음에 날짜로 묶었더니 1945년 8월 14일이 한
# 덩어리가 됐다. 20시 05분(가세)과 20시 10분(미국)은 같은 순간을 양쪽이 따로
# 적은 것인데, 그 둘이 하나가 되면 시각이 곧 내용인 대목에서 시각이 사라진다.
# 1941년 12월 6일도 워싱턴과 도쿄의 다른 책상 다섯이 뭉쳤다.
#
# 그래서 **날짜 · 표기(시각) · 누구 · 문서** 넷이 같아야 같은 사건으로 본다.
# 문서까지 넣는 이유가 있다. 카이로 회담은 같은 달·같은 자리(who)로 두 줄이
# 적혀 있는데 가리키는 문서가 다르다(d307·d308). 셋만으로 묶으면 둘째 줄의
# 문서가 사라진다. 거꾸로 「독일의 항복」과 「쓰이지 않은 문서」가 같은 날
# 같은 자리에서 같은 문서(veday-1945/d235)를 가리키는 것은 하나로 묶인다 —
# 한 사건을 두 주제가 다르게 적은 것이니 그게 맞다.
events, by_key, by_date = {}, {}, {}


def put(date, disp, who, label, doc=None, **kw):
    key = (date, disp or "", who or "", doc or "")
    if key in by_key:
        eid = by_key[key]
    else:
        eid, n = date, 0
        while eid in events:
            n += 1
            eid = f"{date}-{n}"
        by_key[key] = eid
        by_date.setdefault(date, []).append(eid)
    e = events.setdefault(eid, {"id": eid, "date": date})
    if disp:
        e.setdefault("disp", disp)
    if label:
        e.setdefault("label", label)
    for k, v in kw.items():
        if v not in (None, "", [], False):
            e.setdefault(k, v)
    return eid


for e in CH["events"]:
    put(e["date"], None, None, e["label"], arc=arc_of(e["date"], e["label"]),
        bar=True, key=e.get("key", False), where=e.get("where"), note=e.get("note"))

# ---------------------------------------------------------------- 주제 훑기
threads_out = []
unmatched = []
for t in SITE["threads"]:
    carry, out = None, []
    for ev in t["events"]:
        date, disp = norm_date(ev["when"], carry)
        if date and len(date) == 10:
            carry = date[:4]
        if not date:
            unmatched.append((t["slug"], ev["when"]))
            date = ev["when"]
        # 바에 있던 이정표와 잇는 것은 **그날에 주제 항목이 하나뿐일 때만** 한다.
        # 여럿이면 어느 것이 그 이정표인지 기계가 알 수 없다 — 잘못 이으면
        # 서로 다른 책상의 기록이 한 사건으로 뭉친다.
        same_day = [e for e in t["events"]
                    if norm_date(e["when"], carry)[0] == date]
        mark = None
        if len(same_day) == 1:
            mark = next((i for i in by_date.get(date, [])
                         if events[i].get("bar")), None)
        if mark:
            eid = mark
            events[eid]["arc"] = arc_of(date, events[eid].get("label", ""),
                                        thread=t["slug"])
            if disp:
                events[eid].setdefault("disp", disp)
            by_key[(date, disp or "", ev["who"],
                    f'{ev.get("col")}/{ev.get("doc")}' if ev.get("doc") else "")] = eid
        else:
            eid = put(date, disp, ev["who"], None,
                      doc=f'{ev.get("col")}/{ev.get("doc")}' if ev.get("doc") else None,
                      arc=arc_of(date, thread=t["slug"]), bar=False)
        if ev.get("col") and ev.get("doc"):
            docs = events[eid].setdefault("docs", [])
            pair = [ev["col"], ev["doc"]]
            if pair not in docs:
                docs.append(pair)
        line = {"ev": eid, "who": ev["who"], "what": ev["what"]}
        if ev.get("key"):
            line["key"] = True
        if ev.get("flag"):
            line["flag"] = ev["flag"]
        out.append(line)
    threads_out.append((t["slug"], out))

# ---------------------------------------------------------------- 결과
ev_list = sorted(events.values(), key=lambda e: (e["date"], e["id"]))
bar = [e for e in ev_list if e.get("bar")]
withdoc = [e for e in ev_list if e.get("docs")]
multi = [e for e in ev_list if len(e.get("docs") or []) > 1]

print(f"사건 {len(ev_list)}개  (바에 뜨는 것 {len(bar)} · 문서가 걸린 것 {len(withdoc)}"
      f" · 문서 둘 이상 {len(multi)})")
print(f"주제 {len(threads_out)}개 · 항목 {sum(len(o) for o in dict(threads_out).values())}")
import collections
print("국면별:", dict(collections.Counter(e.get("arc") for e in ev_list)))
if unmatched:
    print(f"날짜를 못 읽은 것 {len(unmatched)}: {unmatched[:6]}")
print("\n문서가 둘 이상 걸린 사건:")
for e in multi:
    print(f"  {e['date']}  {e.get('label') or '(이름 없음)'}  {e['docs']}")

if not WRITE:
    print("\n--write 를 붙이면 chrono.json 과 site.json 을 고쳐 쓴다.")
    sys.exit()

out = {"from": CH["from"], "to": CH["to"],
       "note": ("문서철을 가리지 않고 공용으로 쓰는 사건 목록이다. 열람기 아래 연대 "
                "바와 색인 화면의 주제가 이 하나를 함께 읽는다. `bar` 가 참인 것만 "
                "바에 뜬다 — 바는 성글어야 눈에 들어온다. `note` 는 마우스를 올렸을 "
                "때 뜨는 요약이라 두세 문장을 넘기지 마라. 주제의 한 줄(who·what)은 "
                "site.json 에 있다. 같은 사건을 두 주제가 다르게 적을 수 있어서다."),
       "arcs": ARCS, "events": ev_list}
json.dump(out, open(os.path.join(HERE, "chrono.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

tmap = dict(threads_out)
for t in SITE["threads"]:
    t["events"] = tmap[t["slug"]]
json.dump(SITE, open(os.path.join(ROOT, "site.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("\nchrono.json · site.json 을 고쳐 썼다.")
