"""문서철 열람기 — 자료를 가리지 않는 단일 HTML 생성기.

    python3 build.py <collection.json> [reader.html]

이 파일은 **자료가 무엇인지 모른다.** collection.json 과 docs.json 만 읽는다.
규격은 SCHEMA.md. 새 문서철을 넣을 때 여기를 고칠 일은 없어야 한다 —
자료마다 다른 것은 각 문서철의 make_docs.py 가 흡수한다.

겉모습은 처음 다룬 자료(극동군 G-3 전문철)의 어법을 그대로 물려받았다 —
전신 용지의 등폭 서체, 기밀등급 도장의 자주색, 마이크로필름의 차가운 회청색.
장식이 아니라 자료가 원래 그렇게 생겼다. 문서철이 바뀌어도 화면을 유지하는 건
읽는 사람이 자료를 옮겨 다닐 때마다 다시 적응하지 않게 하려는 것이다.
"""
import html as H
import json
import os
import sys

if len(sys.argv) < 2:
    sys.exit(__doc__)

argv = sys.argv[1:]

# 배포로 묶을 때만 「돌아가기」 링크를 넣는다. 작업용으로 혼자 열 때는
# 그 링크가 갈 곳이 없어서, 넣어 두면 깨진 링크가 된다.
#   --home <url> <label>
HOME = None
if "--home" in argv:
    i = argv.index("--home")
    HOME = {"url": argv[i + 1], "label": argv[i + 2]}
    del argv[i:i + 3]

# 배포에서는 열람기가 `_site/<문서철>/index.html` 에 놓인다. 작업 폴더에서는
# `reading/reader.html` 이라 스캔이 한 단계 위(`../pages`)에 있지만, 배포에서는
# 열람기와 **같은 자리**에 있다. 그래서 `../` 를 떼어 준다 — 안 떼면 사이트
# 전체의 스캔과 썸네일이 통째로 깨진 링크가 된다.
FLATTEN = "--flat-scans" in argv
if FLATTEN:
    argv.remove("--flat-scans")

CONF = os.path.abspath(argv[0])
BASE = os.path.dirname(CONF)
conf = json.load(open(CONF))

DOCS_PATH = os.path.join(BASE, conf.get("docs", "docs.json"))
OUT = os.path.abspath(argv[1]) if len(argv) > 1 \
    else os.path.join(BASE, "reader.html")

if not os.path.exists(DOCS_PATH):
    sys.exit(f"{DOCS_PATH} 이 없다. 먼저 make_docs.py 를 돌려라.")
docs = json.load(open(DOCS_PATH))
if not docs:
    sys.exit("docs.json 이 비었다.")

for i, d in enumerate(docs):
    if not d.get("id"):
        sys.exit(f"{i}번째 문서에 id 가 없다. id 는 필수다.")
    d.setdefault("order", i)

# 본문 속 용어·상호참조 주석. 사료를 읽다 보면 문서번호(`SWNCC 176/8`)와
# 그 문서 안에서만 통하는 약칭(`제안 「A」`)이 끊임없이 나오는데, 그게 무엇인지
# 모르면 문장이 읽히지 않는다. 낱말에 붙여 두고 손을 얹으면 설명이 뜨게 한다.
#
#   terms.json = { "_": [문서철 전체에 적용], "d238": [이 문서에만] }
#   항목 = {term, alias[], title, body, url, doc}
# 파일을 여럿 적을 수 있다. 사람이 쓴 주석과 자동으로 뽑은 전문번호를 나눠 두고
# 여기서 합친다 — 자동 생성이 사람이 쓴 것을 덮어쓰면 안 된다.
terms_all = {}
_tp = conf.get("terms")
for _one in ([_tp] if isinstance(_tp, str) else (_tp or [])):
    _tf = os.path.join(BASE, _one)
    if not os.path.exists(_tf):
        print(f"  !! {_one} 가 없다 — 건너뛴다")
        continue
    for _scope, _items in json.load(open(_tf)).items():
        terms_all.setdefault(_scope, []).extend(_items)

groups = conf.get("groups") or []
sorts = conf.get("sorts") or []
panes = conf.get("panes") or {}
pages_conf = conf.get("pages")          # None 이면 스캔 기능이 통째로 빠진다
if pages_conf and FLATTEN:
    for k in ("dir", "thumbs"):
        v = pages_conf.get(k)
        if isinstance(v, str) and v.startswith("../"):
            pages_conf[k] = v[3:]

# 용어를 카드 자료와 매칭 규칙으로 나눠 담는다. 긴 낱말부터 찾아야
# `제안 「A」` 가 `A` 하나에 먼저 걸려 잘리지 않는다.
term_cards, term_rules = {}, {}
for scope, items in terms_all.items():
    rules = []
    for i, t in enumerate(items):
        key = f"{scope}:{i}"
        term_cards[key] = {"title": t.get("title"), "sum": t.get("body"),
                           "badge": t.get("badge") or "이 문서철의 주석",
                           "points": t.get("points") or []}
        for w in [t["term"]] + (t.get("alias") or []):
            r = {"w": w, "k": key,
                 "href": t.get("url") or (f"#{t['doc']}" if t.get("doc") else None)}
            if t.get("doc"):
                r["doc"] = t["doc"]     # 자기 자신을 가리키면 링크는 빼고 카드만
            rules.append(r)
    rules.sort(key=lambda r: -len(r["w"]))
    term_rules[scope] = rules

# 늘 떠 있는 연대 바. 문서 하나를 읽을 때 「이건 언제 이야기인가」를 잡아 준다.
# 문서철마다 다르지 않아야 하므로 공용 파일 하나를 쓴다.
_cf = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chrono.json")
chrono = json.load(open(_cf)) if os.path.exists(_cf) else None
if chrono and conf.get("chrono") is False:
    chrono = None

runtime = {
    "pages": pages_conf,
    "chrono": chrono,
    "terms": term_rules,
    "term_cards": term_cards,
    "panes": {"primary": panes.get("primary", "본문"),
              "secondary": panes.get("secondary"),
              "both": panes.get("both", "나란히")},
    "warn": conf.get("warn_text", "판독 신뢰도가 낮다. 원본 대조 필요."),
    "sorts": [s["key"] for s in sorts],
}

payload = json.dumps(docs, ensure_ascii=False).replace("</", "<\\/")

# 호버 카드는 랜딩과 같은 부품을 쓴다. 소스는 나눠 두고 결과만 한 파일로 낸다.
_hc = os.path.dirname(os.path.abspath(__file__))
HC_CSS = open(os.path.join(_hc, "hovercard.css")).read()
HC_JS = open(os.path.join(_hc, "hovercard.js")).read().replace("</", "<\\/")
runtime_js = json.dumps(runtime, ensure_ascii=False)

CSS = r"""
:root{
  --bg:#eef1f4; --panel:#f7f9fa; --edge:#ccd4da; --edge-soft:#dde4e9;
  --ink:#16202a; --ink-2:#4a5b68; --ink-3:#71828f;
  --stamp:#8c2f39;            /* 기밀등급 도장의 자주색 */
  --link:#2f5d86;
  --a:#4a7c59; --b:#8a6d3b; --c:#3f6d8c; --d:#7a4a6b; --e:#5a6f7d; --x:#8a8f94;
  --term-line:#9db0c2; --term-bg:rgba(47,93,134,.05);
  --term-line-go:#7fa3c4; --term-bg-go:rgba(47,93,134,.10);
  --term-bg-on:rgba(47,93,134,.17);
  --mono:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,monospace;
  --sans:"Apple SD Gothic Neo","Pretendard","Malgun Gothic","Noto Sans KR",
         -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
}
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){
    --bg:#12171c; --panel:#171d23; --edge:#2b353e; --edge-soft:#222a31;
    --ink:#dfe6ec; --ink-2:#a4b2bd; --ink-3:#75858f;
    --stamp:#c9707a; --link:#7fb0da;
    --term-line:#5b7183; --term-bg:rgba(127,176,218,.07);
    --term-line-go:#6d90ad; --term-bg-go:rgba(127,176,218,.13);
    --term-bg-on:rgba(127,176,218,.22);
    --a:#7fae8c; --b:#c0a06a; --c:#79a9c7; --d:#b287a3; --e:#93a6b3; --x:#8a939a;
  }
}
:root[data-theme="dark"]{
  --bg:#12171c; --panel:#171d23; --edge:#2b353e; --edge-soft:#222a31;
  --ink:#dfe6ec; --ink-2:#a4b2bd; --ink-3:#75858f;
  --stamp:#c9707a; --link:#7fb0da;
  --term-line:#5b7183; --term-bg:rgba(127,176,218,.07);
  --term-line-go:#6d90ad; --term-bg-go:rgba(127,176,218,.13);
  --term-bg-on:rgba(127,176,218,.22);
  --a:#7fae8c; --b:#c0a06a; --c:#79a9c7; --d:#b287a3; --e:#93a6b3; --x:#8a939a;
}
*{box-sizing:border-box}
html,body{height:100%}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);
  font-size:15px;line-height:1.7;-webkit-font-smoothing:antialiased}
a{color:var(--link)}

.wrap{display:grid;grid-template-columns:minmax(300px,25%) 1fr;height:100vh}
@media(max-width:900px){
  .wrap{grid-template-columns:1fr;grid-template-rows:auto 1fr}
  .rail{max-height:42vh}
}

/* ── 좌측 목록 ─────────────────────────────── */
.rail{border-right:1px solid var(--edge);background:var(--panel);
  display:flex;flex-direction:column;min-height:0}
.rail-head{padding:14px 14px 10px;border-bottom:1px solid var(--edge-soft);
  display:flex;flex-direction:column;gap:8px}
/* 문서철에 들어오면 나갈 길이 있어야 한다 */
.home{display:inline-flex;align-items:center;gap:5px;text-decoration:none;
  color:var(--link);font-size:11.5px;font-family:var(--mono);
  letter-spacing:.04em;width:fit-content;
  background:var(--term-bg-go);border:1px solid var(--term-line-go);
  border-radius:999px;padding:2px 10px 2px 8px}
.home:hover{background:var(--term-bg-on);border-color:var(--link)}
.home span{font-size:12px;line-height:1}
.brand{font-size:13px;font-weight:700;letter-spacing:.06em;text-transform:uppercase}
.brand small{display:block;font-weight:400;letter-spacing:0;text-transform:none;
  color:var(--ink-3);font-size:11.5px;margin-top:2px}
input[type=search]{width:100%;padding:7px 10px;border:1px solid var(--edge);
  border-radius:3px;background:var(--bg);color:var(--ink);font:inherit;font-size:13px}
input[type=search]:focus,button:focus-visible,.item:focus-visible{outline:2px solid var(--link);outline-offset:1px}
.chips{display:flex;flex-wrap:wrap;gap:4px}
.chip{border:1px solid var(--edge);background:transparent;color:var(--ink-2);
  border-radius:999px;padding:2px 9px;font-size:11.5px;cursor:pointer;font-family:inherit}
.chip[aria-pressed="true"]{background:var(--ink);color:var(--panel);border-color:var(--ink)}
.sortbar{display:flex;gap:10px;font-size:11.5px;color:var(--ink-3);align-items:center}
.sortbar button{background:none;border:none;color:var(--ink-3);cursor:pointer;
  font:inherit;padding:0;border-bottom:1px solid transparent}
.sortbar button[aria-pressed="true"]{color:var(--ink);border-bottom-color:var(--ink)}

.list{overflow-y:auto;flex:1;min-height:0}
.item{display:block;width:100%;text-align:left;background:none;border:0;
  border-bottom:1px solid var(--edge-soft);border-left:3px solid transparent;
  padding:9px 13px;cursor:pointer;font:inherit;color:inherit}
.item:hover{background:var(--bg)}
.item[aria-current="true"]{background:var(--bg);border-left-color:var(--ink)}
.item.tA{border-left-color:var(--a)} .item.tB{border-left-color:var(--b)}
.item.tC{border-left-color:var(--c)} .item.tD{border-left-color:var(--d)}
.item.tE{border-left-color:var(--e)} .item.tX{border-left-color:var(--x)}
.item-top{display:flex;justify-content:space-between;gap:8px;
  font-family:var(--mono);font-size:11px;color:var(--ink-3);font-variant-numeric:tabular-nums}
.item-sum{font-size:12.5px;line-height:1.45;margin-top:2px;
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}

/* ── 우측 본문 ─────────────────────────────── */
.main{overflow-y:auto;min-height:0}
.toolbar{position:sticky;top:0;z-index:5;background:var(--panel);
  border-bottom:1px solid var(--edge);padding:8px 26px;
  display:flex;gap:14px;align-items:center;flex-wrap:wrap;font-size:12px}
.toolbar .grow{flex:1}
.seg{display:flex;border:1px solid var(--edge);border-radius:3px;overflow:hidden}
.seg button{background:none;border:0;padding:4px 11px;cursor:pointer;
  font:inherit;font-size:12px;color:var(--ink-2);border-right:1px solid var(--edge)}
.seg button:last-child{border-right:0}
.seg button[aria-pressed="true"]{background:var(--ink);color:var(--panel)}
.srcline{padding:10px 26px 0;font-size:11px;color:var(--ink-3);line-height:1.5}

/* ── 연대 바 ───────────────────────────────
   5년 반을 한 줄에 욱여넣으면 1945년 8월 열흘은 0.5% 밖에 안 된다. 그래서
   줄을 늘여 놓고 **띠 자체를 움직인다** — 지금 읽는 문서의 날짜가 늘 정중앙이다.
   문서를 옮기면 띠가 미끄러지고, 사건 이름은 겹치지 않게 위아래로 층을 나눈다. */
.chrono{position:fixed;left:50%;bottom:16px;transform:translateX(-50%);
  width:min(940px,calc(100vw - 48px));z-index:20;user-select:none;
  border:1px solid var(--edge);border-radius:8px;
  background:color-mix(in srgb,var(--panel) 92%,transparent);
  backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px);
  box-shadow:0 4px 20px rgba(0,0,0,.10);
  transition:box-shadow .2s ease}
.chrono:hover{box-shadow:0 6px 26px rgba(0,0,0,.18)}
/* 옅어지는 것은 **내용**이지 판이 아니다. 판까지 투명해지면 뒤의 본문이
   비쳐 들어와 글자가 서로를 밟는다. */
.chrono-track{opacity:.5;transition:opacity .2s ease}
.chrono:hover .chrono-track{opacity:1}

/* 띠가 지나가는 창. 손으로도 밀 수 있게 진짜 가로 스크롤을 쓴다 */
.chrono-vp{position:relative;overflow-x:auto;overflow-y:hidden;
  height:var(--chH,92px);border-radius:8px;cursor:grab;
  scrollbar-width:none;-ms-overflow-style:none;overscroll-behavior-x:contain}
.chrono-vp::-webkit-scrollbar{display:none}
.chrono-vp.drag{cursor:grabbing}
/* 안쪽 띠. 양옆 여백은 창의 절반 — 첫 문서도 마지막 문서도 가운데에 설 수 있게 */
.chrono-track{position:relative;height:100%;margin:0 var(--chPad,0px)}
/* 시간 축 — 층의 한가운데 */
.chrono-track::before{content:"";position:absolute;
  left:calc(0px - var(--chPad,0px));right:calc(0px - var(--chPad,0px));
  top:var(--axis,46px);height:1px;background:var(--edge)}

/* 연도 — 해가 바뀌는 자리에 선을 긋고, 그 선부터가 그 해다.
   이름표는 창 왼쪽에 들러붙는다. 1945년 한복판을 보고 있어도 「1945」가 남는다. */
.cy{position:absolute;top:0;bottom:0;
  border-left:1px solid color-mix(in srgb,var(--ink-3) 50%,transparent)}
.cy.alt{background:color-mix(in srgb,var(--ink) 3%,transparent)}
.cy b{position:absolute;bottom:3px;font-family:var(--mono);font-size:11px;
  font-weight:600;color:var(--ink-3);font-variant-numeric:tabular-nums;
  line-height:1;letter-spacing:.06em;white-space:nowrap;
  background:color-mix(in srgb,var(--panel) 80%,transparent);padding:1px 3px}
/* 달·분기 눈금 — 해 안에서 어디쯤인지. 분기는 조금 길게 */
.cq{position:absolute;top:calc(var(--axis,46px) - 1.5px);width:1px;height:4px;
  background:var(--edge);opacity:.7}
.cq.q{top:calc(var(--axis,46px) - 2.5px);height:6px;opacity:1}
.cq[hidden]{display:none}

/* 배율 — 5년 반을 한눈에 볼 때와 8월 열흘을 벌려 볼 때가 같을 수 없다 */
.chrono-zoom{position:absolute;right:6px;top:5px;z-index:3;display:flex;gap:3px;
  opacity:0;transition:opacity .2s ease}
.chrono:hover .chrono-zoom,.chrono-zoom:focus-within{opacity:1}
.chrono-zoom button{width:19px;height:19px;padding:0;line-height:1;
  font-family:var(--mono);font-size:12px;color:var(--ink-2);cursor:pointer;
  background:var(--panel);border:1px solid var(--edge);border-radius:3px}
.chrono-zoom button:hover:not(:disabled){color:var(--link);border-color:var(--link)}
.chrono-zoom button:disabled{opacity:.35;cursor:default}
.chrono-scale{position:absolute;right:6px;bottom:3px;z-index:3;
  font-family:var(--mono);font-size:9.5px;color:var(--ink-3);letter-spacing:.03em;
  background:color-mix(in srgb,var(--panel) 80%,transparent);padding:1px 3px;
  opacity:0;transition:opacity .2s ease}
.chrono:hover .chrono-scale{opacity:1}

/* 사건 점 */
.cm{position:absolute;top:calc(var(--axis,46px) - 3px);width:7px;height:7px;
  margin-left:-3.5px;border-radius:50%;background:var(--ink-3);z-index:1;
  border:1.5px solid var(--panel);cursor:help;
  transition:background .15s ease,transform .15s ease}
.cm.key{background:var(--stamp);width:9px;height:9px;margin-left:-4.5px;
  top:calc(var(--axis,46px) - 4px)}
.cm:hover{background:var(--link);transform:scale(1.45)}

/* 사건 이름 — 층(lane)을 나눠 위아래로 흩는다. 여기서 겹침이 풀린다 */
.cl{position:absolute;transform:translateX(-50%);white-space:nowrap;z-index:1;
  font-family:var(--mono);font-size:10px;line-height:1.1;color:var(--ink-2);
  letter-spacing:.01em;padding:1px 4px;border-radius:2px;cursor:help;
  background:color-mix(in srgb,var(--panel) 70%,transparent)}
.cl.key{color:var(--stamp)}
.cl:hover,.cl:focus-visible{color:var(--link);outline:0;
  background:color-mix(in srgb,var(--link) 12%,var(--panel))}
/* 이름에서 축까지 내려/올려 긋는 실 — 어느 점의 이름인지 알아보게 */
.cl::after{content:"";position:absolute;left:50%;width:1px;background:var(--edge)}
.cl.up::after{top:100%;height:var(--leg,0px)}
.cl.dn::after{bottom:100%;height:var(--leg,0px)}

/* 지금 읽는 문서가 놓인 자리. 문서를 고르면 이 표가 창 한가운데로 온다.
   손으로 띠를 밀면 표는 제 날짜에 남는다 — 표는 시간에 박혀 있지 창에 박혀 있지 않다. */
.chrono-cursor{position:absolute;top:0;bottom:0;width:1px;z-index:2;
  background:var(--stamp);pointer-events:none}
/* 가상 요소는 위의 *{box-sizing:border-box}가 닿지 않는다 — 여기서 직접 잡아 주지
   않으면 테두리 2px 만큼 표시가 축 아래·오른쪽으로 밀려 앉는다. */
.chrono-cursor::before{content:"";position:absolute;box-sizing:border-box;
  left:-6px;top:calc(var(--axis,46px) - 6px);width:13px;height:13px;
  border-radius:50%;background:var(--stamp);border:2px solid var(--panel)}
/* 날짜는 맨 아래, 표 바로 밑에 — 위쪽은 사건 이름 층에 내준다 */
.chrono-date{position:absolute;bottom:2px;transform:translateX(-50%);
  font-family:var(--mono);font-size:10px;color:var(--stamp);
  font-variant-numeric:tabular-nums;background:var(--panel);
  padding:0 5px;border-radius:2px;white-space:nowrap;z-index:2}
.chrono[data-nodate="1"] .chrono-cursor,
.chrono[data-nodate="1"] .chrono-date{display:none}

@media(max-width:900px){.chrono{display:none}}
@media(prefers-reduced-motion:reduce){.chrono-track{transition:none}}

/* 아래쪽 여백은 떠 있는 연대 바가 마지막 문단을 덮지 않을 만큼 */
article{max-width:none;padding:26px 26px 190px}
.doc-head{border-bottom:1px solid var(--edge);padding-bottom:14px;margin-bottom:18px}
h1{font-size:19px;margin:0 0 4px;line-height:1.35;text-wrap:balance;font-weight:650}
.docid{font-family:var(--mono);font-size:11px;color:var(--ink-3);
  letter-spacing:.04em;font-variant-numeric:tabular-nums}
.stamp{display:inline-block;border:1.5px solid var(--stamp);color:var(--stamp);
  font-family:var(--mono);font-size:10px;letter-spacing:.14em;padding:1px 6px;
  border-radius:2px;transform:rotate(-1.2deg);margin-left:8px;vertical-align:2px}
.meta{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));
  gap:3px 20px;margin-top:10px;font-size:12.5px}
.meta div{display:flex;gap:7px}
/* 참석자 명단처럼 긴 값. 좁은 칸에 넣으면 한 글자씩 세로로 눌린다 */
.meta div.wide{grid-column:1/-1}
.meta b{color:var(--ink-3);font-weight:500;min-width:52px;font-size:11.5px}
.meta span{font-family:var(--mono);font-size:12px}
.meta span.txt{font-family:var(--sans);font-size:12.5px}

.points{margin:16px 0;padding:12px 16px;border-left:2px solid var(--edge);
  background:var(--panel);border-radius:0 3px 3px 0}
.points li{margin:3px 0}
.points ul{margin:0;padding-left:18px}

.cols{display:grid;gap:26px}
.cols.two{grid-template-columns:1fr 1fr}
@media(max-width:1100px){.cols.two{grid-template-columns:1fr}}
.pane h2{font-size:11px;letter-spacing:.12em;text-transform:uppercase;
  color:var(--ink-3);margin:0 0 8px;font-weight:600}
.body{white-space:pre-wrap;word-break:break-word}
/* 번역문에 마크다운이 섞여 들어온다 — 긴 문서는 옮긴 쪽이 소제목과 항목으로
   나눠 두어야 읽힌다. 본문은 pre-wrap 이므로 줄 단위로만 풀어 준다. */
.mdh{display:block;font-weight:700;margin:20px 0 6px;letter-spacing:-.01em}
.mdh.h1{font-size:17px} .mdh.h2{font-size:15.5px}
.mdh.h3,.mdh.h4,.mdh.h5,.mdh.h6{font-size:14px;color:var(--ink-2);
  letter-spacing:.04em}
.mdq{display:block;border-left:2px solid var(--edge);padding-left:13px;
  color:var(--ink-2);margin:6px 0}
.mdli{display:block;padding-left:17px;text-indent:-17px;margin:2px 0}
.mdli::before{content:"· ";color:var(--ink-3)}
.mdli[data-n]::before{content:attr(data-n) " ";color:var(--ink-3);
  font-family:var(--mono);font-size:12px}
.mdhr{border:0;border-top:1px solid var(--edge);margin:18px 0}
.body.en{font-family:var(--mono);font-size:12.5px;line-height:1.65;color:var(--ink-2)}
.body del{color:var(--ink-3)}
.body strong{font-weight:650}

.pagemark{display:block;margin:16px 0 6px;font-family:var(--mono);font-size:10.5px;
  color:var(--ink-3);letter-spacing:.06em;border-top:1px dashed var(--edge);padding-top:5px}
.pagemark.hit{cursor:zoom-in;text-decoration:underline;
  text-decoration-style:dotted;text-underline-offset:3px}
.pagemark.hit:hover{color:var(--link)}
.fnref{font-family:var(--mono);font-size:10.5px;color:var(--ink-3);vertical-align:super}

/* 본문 속 용어 주석.
   앞서 --edge 로 밑줄을 그었더니 배경에 묻혀 아예 보이지 않았다.
   옅은 바탕을 깔아 「여기 무언가 있다」를 먼저 알리고, 점선으로 종류를 나눈다.
   다른 문서로 가는 것(a)과 설명만 뜨는 것(span)을 색으로 구분한다. */
.term{color:inherit;text-decoration:none;cursor:help;
  background:var(--term-bg);border-radius:2px;
  padding:0 2px;margin:0 -1px;
  border-bottom:1px dashed var(--term-line);
  box-decoration-break:clone;-webkit-box-decoration-break:clone}
a.term{cursor:pointer;color:var(--link);
  background:var(--term-bg-go);border-bottom-color:var(--term-line-go)}
.term:hover{background:var(--term-bg-on);border-bottom-style:solid;
  border-bottom-color:var(--link);color:var(--link)}
.term:focus-visible{outline:2px solid var(--link);outline-offset:2px}

.fns{margin-top:24px;padding-top:14px;border-top:1px solid var(--edge-soft);
  font-size:12px;color:var(--ink-3);line-height:1.6}
.fns h2,.scans h2{font-size:11px;letter-spacing:.12em;text-transform:uppercase;
  color:var(--ink-3);margin:0 0 9px;font-weight:600}
.fns div{margin:4px 0}
.note{margin-top:14px;font-size:12px;color:var(--ink-3);border-left:2px solid var(--edge);
  padding-left:11px}
.empty{padding:60px 26px;color:var(--ink-3)}
.warn{color:var(--stamp)}

/* ── 스캔 원본 ─────────────────────────────── */
.scans{margin-top:24px;padding-top:14px;border-top:1px solid var(--edge-soft)}
.thumbs{display:flex;flex-wrap:wrap;gap:8px}
.thumb{border:1px solid var(--edge);background:var(--panel);padding:0;cursor:zoom-in;
  border-radius:2px;overflow:hidden;line-height:0;position:relative}
.thumb:hover{border-color:var(--link)}
.thumb img{width:84px;height:110px;object-fit:cover;object-position:top center;
  display:block;background:var(--edge-soft)}
.thumb b{position:absolute;left:0;bottom:0;background:rgba(0,0,0,.62);color:#fff;
  font-family:var(--mono);font-size:9.5px;font-weight:400;padding:1px 4px;
  letter-spacing:.04em;line-height:1.5}

/* ── 확대 뷰어 ─────────────────────────────── */
.lb{position:fixed;inset:0;z-index:50;background:rgba(8,11,14,.94);
  display:none;flex-direction:column}
.lb[open]{display:flex}
.lb-bar{display:flex;align-items:center;gap:14px;padding:9px 16px;color:#c9d3db;
  font-size:12px;border-bottom:1px solid #2a343d;flex:none}
.lb-bar .grow{flex:1}
.lb-bar button{background:none;border:1px solid #3a464f;color:#c9d3db;
  border-radius:3px;padding:3px 11px;font:inherit;font-size:12px;cursor:pointer}
.lb-bar button:hover:not(:disabled){border-color:#7fb0da;color:#fff}
.lb-bar button:disabled{opacity:.35;cursor:default}
.lb-bar .pg{font-family:var(--mono);font-variant-numeric:tabular-nums}
.lb-stage{flex:1;min-height:0;overflow:auto;display:flex;
  align-items:flex-start;justify-content:center;padding:16px}
.lb-stage img{max-width:100%;height:auto;background:#fff;box-shadow:0 2px 24px rgba(0,0,0,.5)}
.lb-stage.fit img{max-height:calc(100vh - 90px);width:auto}
"""

JS = r"""
const DOCS = JSON.parse(document.getElementById('data').textContent);
const CONF = JSON.parse(document.getElementById('conf').textContent);
const PG = CONF.pages;   // null 이면 스캔 기능이 없는 자료다

let state = {q:'', groups:new Set(),
             sort:(CONF.sorts && CONF.sorts[0]) || null,
             view:'primary', cur:null};

const $ = s => document.querySelector(s);
const esc = s => (s==null?'':String(s)).replace(/[&<>]/g,
  c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));

/* 본문에서 특별 취급하는 것은 두 가지뿐이다.
   [1050면] → 원본 지면 구분선(스캔이 있으면 눌러서 열린다), [주74] → 각주 참조.
   d777처럼 편집 이력을 취소선·굵게로 복원한 문서가 있어 인라인 서식도 함께 푼다. */
function marks(t){
  const cls = PG ? 'pagemark hit' : 'pagemark';
  const tail = PG ? '면 · 원본 보기' : '면';
  return esc(t)
    .replace(/\[(\d+)면\]/g, `<span class="${cls}" data-pg="$1">$1${tail}</span>`)
    .replace(/\[주(\d+)\]/g, '<span class="fnref">$1</span>')
    .replace(/~~([^~]+)~~/g, '<del>$1</del>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
}

/* 줄머리의 마크다운. 번역이 길어지면 옮긴 쪽이 `## 소제목` 과 `- 항목` 으로
   나눠 두는데, 그대로 두면 우물정자와 붙임표가 본문에 그냥 찍힌다.
   본문 상자가 pre-wrap 이라 문단을 다시 짜지 않고 줄 단위로만 푼다. */
function blocks(t){
  const out = [];
  for (const line of String(t == null ? '' : t).split('\n')){
    let m;
    if ((m = /^(#{1,6})\s+(.*)$/.exec(line)))
      out.push(`<b class="mdh h${m[1].length}">${marks(m[2])}</b>`);
    else if (/^\s*(-{3,}|\*{3,}|_{3,})\s*$/.test(line))
      out.push('<hr class="mdhr">');
    else if ((m = /^\s*>\s?(.*)$/.exec(line)))
      out.push(`<span class="mdq">${marks(m[1])}</span>`);
    else if ((m = /^\s*(\d+)[.)]\s+(.*)$/.exec(line)))
      out.push(`<span class="mdli" data-n="${esc(m[1])}.">${marks(m[2])}</span>`);
    else if ((m = /^\s*[-*+]\s+(.*)$/.exec(line)))
      out.push(`<span class="mdli">${marks(m[1])}</span>`);
    else
      out.push(marks(line) + '\n');
  }
  return out.join('').replace(/\n$/, '');
}

const haystack = d => [d.id, d.date, d.title, d.eyebrow, d.summary, d.search,
    (d.points||[]).join(' '), (d.meta||[]).map(m=>m.v).join(' '),
    (d.notes||[]).join(' '), d.note, d.primary, d.secondary]
  .join(' ').toLowerCase();

function visible(){
  const q = state.q.trim().toLowerCase();
  let out = DOCS.filter(d => {
    if (state.groups.size && !state.groups.has(d.group)) return false;
    return !q || haystack(d).includes(q);
  });
  if (state.sort === 'date')
    out.sort((a,b) => (a.date||'9999').localeCompare(b.date||'9999') || a.order - b.order);
  else if (state.sort)
    out.sort((a,b) => a.order - b.order);
  return out;
}

function renderList(){
  const items = visible();
  $('#count').textContent = `${items.length}건`;
  $('#list').innerHTML = items.map(d => `
    <button class="item t${d.group||'X'}" data-id="${esc(d.id)}"
            aria-current="${state.cur===d.id}">
      <div class="item-top"><span>${esc(d.date||'날짜미상')}</span>
        <span>${esc(d.list_right||'')}</span></div>
      <div class="item-sum">${esc(d.title||d.id)}</div>
    </button>`).join('') ||
    '<div class="empty">해당하는 문서가 없다.</div>';
}

function pane(kind){
  const d = DOCS.find(x => x.id === state.cur);
  const txt = kind==='primary' ? d.primary : d.secondary;
  if (!txt) return '';
  const cls = kind==='primary' ? 'body' : 'body en';
  return `<div class="pane"><h2>${esc(CONF.panes[kind])}</h2>
    <div class="${cls}">${blocks(txt)}</div></div>`;
}

function renderDoc(){
  const d = DOCS.find(x => x.id === state.cur);
  if (!d){ $('#main').innerHTML =
    '<div class="empty">왼쪽에서 문서를 고르세요.</div>'; return; }

  const meta = (d.meta||[]).filter(m => m && m.v).map(m =>
    `<div class="${m.wide?'wide':''}"><b>${esc(m.k)}</b>` +
    `<span class="${m.txt?'txt':''}">${esc(m.v)}</span></div>`).join('')
    + (d.links||[]).filter(l => l && l.url).map(l =>
    `<div><b>${esc(l.k)}</b><span class="txt"><a href="${esc(l.url)}" target="_blank"
       rel="noopener">${esc(l.text||l.url)}</a></span></div>`).join('');

  const pts = (d.points||[]).length
    ? `<div class="points"><ul>${d.points.map(p=>`<li>${esc(p)}</li>`).join('')}</ul></div>` : '';

  const cols = state.view==='both'
      ? `<div class="cols two">${pane('primary')}${pane('secondary')}</div>`
      : `<div class="cols">${pane(state.view)}</div>`;

  const fns = (d.notes||[]).length
    ? `<div class="fns"><h2>각주</h2>${d.notes.map(n=>`<div>${marks(n)}</div>`).join('')}</div>` : '';

  // 목록에는 작은 사본을 쓴다. 원본은 확대해 볼 때만 받는다 —
  // 84×110 으로 찍으면서 883KB 를 내려받던 것을 고친 것이다.
  const thumb = p => PG.thumbs
    ? `${PG.thumbs}/${p}.${PG.thumb_ext||'jpg'}` : `${PG.dir}/${p}.${PG.ext}`;
  const scans = (PG && (d.pages||[]).length)
    ? `<div class="scans"><h2>${esc(PG.label||'원본 지면')} ${d.pages.length}면</h2>
        <div class="thumbs">${d.pages.map(p=>
          `<button class="thumb" data-pg="${p}" title="${p}면 크게 보기">
             <img loading="lazy" src="${thumb(p)}" alt="${p}면 원본"><b>${p}</b>
           </button>`).join('')}</div></div>` : '';

  $('#main').innerHTML = `<article>
    <div class="doc-head">
      ${d.eyebrow?`<div class="docid">${esc(d.eyebrow)}</div>`:''}
      <h1>${esc(d.title||d.id)}
        ${d.badge?`<span class="stamp">${esc(d.badge)}</span>`:''}</h1>
      ${meta?`<div class="meta">${meta}</div>`:''}
    </div>
    ${d.summary?`<div class="points">${esc(d.summary)}</div>`:''}
    ${pts}${cols}${fns}${scans}
    ${d.note?`<div class="note">${esc(d.note)}</div>`:''}
    ${d.warn?`<div class="note warn">${esc(CONF.warn)}</div>`:''}
  </article>`;
  $('#main').scrollTop = 0;
  markTerms(d.id);
  markNow(d.date);
}

/* 본문 속 용어에 주석을 붙인다.
   HTML 문자열을 치환하면 이미 만들어 둔 태그(면 표시·각주·굵게) 안을 건드려
   깨진다. 그래서 다 그린 뒤 **텍스트 노드만** 훑는다. */
function markTerms(scope){
  const rules = (CONF.terms||{});
  const list = [].concat(rules['_']||[], rules[scope]||[]);
  if (!list.length) return;
  const roots = document.querySelectorAll('#main .body');
  roots.forEach(root => {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode(n){
        // 이미 링크·주석·코드 안이면 건드리지 않는다
        if (n.parentElement.closest('a,.term,.pagemark,.fnref,code,del'))
          return NodeFilter.FILTER_REJECT;
        return n.nodeValue.trim() ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
      }
    });
    const targets = [];
    while (walker.nextNode()) targets.push(walker.currentNode);
    targets.forEach(node => {
      let html = null, rest = node.nodeValue;
      for (const r of list){
        const i = rest.indexOf(r.w);
        if (i < 0) continue;
        html = html || document.createDocumentFragment();
        break;
      }
      if (!html) return;
      // 가장 먼저 나오는 것부터 차례로 잘라 붙인다
      const frag = document.createDocumentFragment();
      let s = node.nodeValue;
      let guard = 0;
      while (s && guard++ < 200){
        let best = null;
        for (const r of list){
          const i = s.indexOf(r.w);
          if (i >= 0 && (!best || i < best.i || (i === best.i && r.w.length > best.r.w.length)))
            best = {i, r};
        }
        if (!best){ frag.appendChild(document.createTextNode(s)); break; }
        if (best.i) frag.appendChild(document.createTextNode(s.slice(0, best.i)));
        // 지금 보고 있는 문서를 가리키는 번호는 링크로 만들지 않는다 — 제자리걸음이다
        const self = best.r.doc && best.r.doc === scope;
        const el = document.createElement(best.r.href && !self ? 'a' : 'span');
        el.className = 'term';
        el.textContent = best.r.w;
        el.dataset.card = best.r.k;
        if (best.r.href && !self) el.setAttribute('href', best.r.href);
        frag.appendChild(el);
        s = s.slice(best.i + best.r.w.length);
      }
      node.parentNode.replaceChild(frag, node);
    });
  });
  if (window.HoverCard) HoverCard.init(CONF.term_cards || {}, document.getElementById('main'));
}

/* ── 연대 바 ───────────────────────────────
   문서를 하나씩 읽다 보면 「얄타가 언제였더라」를 매번 놓친다.
   5년 반을 한 화면에 눌러 담으면 1945년 8월 열흘이 0.5%로 뭉개져 이름이 겹친다.
   그래서 셋으로 나눠 푼다.
     (1) 축을 길게 늘여 놓고 띠를 민다 — 지금 문서의 날짜가 늘 정중앙.
         띠는 진짜 가로 스크롤이라 손으로도 밀 수 있다.
     (2) 그래도 남는 겹침은 이름을 위아래 층으로 흩어 푼다.
     (3) 해가 바뀌는 자리에 선을 긋고, 이름표는 창 왼쪽에 들러붙인다 —
         1945년 한복판을 보고 있어도 「1945」가 떠나지 않는다.
   덕분에 사건 이름을 하나도 숨기지 않는다.

   자리는 전부 날짜에서 다시 계산한다. 그래야 배율을 바꿔도(줌) 같은 코드로
   다시 그릴 수 있다. 화면에 박아 둔 좌표는 없다. */
const CH = CONF.chrono;
const CH_STEPS = [0.6, 1.2, 2.5, 4, 8, 16, 32];  // 하루 몇 px
const CH_LANE = 14;    // 이름 한 층의 높이
const CH_GAP  = 5;     // 같은 층에서 이름끼리 띄울 최소 간격
let CH_PXD = 4;        // 기본 배율 — 창 하나에 대략 여덟 달
let chFrom=0, chEndT=0, chMarks=[], chBands=[], chTicks=[];
const chX = t => ((t - chFrom) / 86400000) * CH_PXD;

function initChrono(){
  const box = $('#chrono');
  if (!CH || !box){ if (box) box.hidden = true; return; }
  chFrom = Date.parse(CH.from);
  chEndT = Date.parse(CH.to);
  const track = $('#chronoTrack');

  // 연도는 「선」이다. 이 선부터 1944, 저 선부터 1945.
  // 한 해를 띠(band)로 잡아 두면 이름표를 그 띠 안에서 움직일 수 있다.
  const y0 = new Date(chFrom).getFullYear(), y1 = new Date(chEndT).getFullYear();
  for (let y = y0; y <= y1; y++){
    const el = document.createElement('div');
    el.className = 'cy' + (y % 2 ? ' alt' : '');
    el.innerHTML = '<b>' + y + '</b>';
    track.appendChild(el);
    chBands.push({el, tag: el.firstChild,
                  t0: Math.max(chFrom, Date.parse(y + '-01-01')),
                  t1: Math.min(chEndT,  Date.parse((y + 1) + '-01-01'))});

    ['02','03','04','05','06','07','08','09','10','11','12'].forEach(m => {
      const t = Date.parse(y + '-' + m + '-01');
      if (t < chFrom || t > chEndT) return;
      const q = document.createElement('div');
      q.className = 'cq' + (m === '04' || m === '07' || m === '10' ? ' q' : '');
      track.appendChild(q);
      chTicks.push({el: q, t});
    });
  }

  // 점과 이름을 한꺼번에 놓는다.
  // 점·이름 어느 쪽에 머물러도 그 사건이 무엇이었는지 카드로 뜬다 —
  // 이름 넉 자로는 「38선 획정」이 무슨 문서에서 어떻게 갈렸는지 알 수 없다.
  const cards = {};
  chMarks = CH.events.map(e => {
    const t = Date.parse(e.date), key = 'ch:' + e.date;
    cards[key] = {title: e.label, date: e.date, route: e.where || '',
                  sum: e.note || '', go: false};

    const dot = document.createElement('div');
    dot.className = 'cm' + (e.key ? ' key' : '');
    dot.dataset.card = key;
    track.appendChild(dot);

    const lab = document.createElement('div');
    lab.className = 'cl' + (e.key ? ' key' : '');
    lab.textContent = e.label;
    lab.dataset.card = key;
    lab.tabIndex = 0;
    track.appendChild(lab);
    return {t, dot, lab};
  });

  renderChrono();
  if (window.HoverCard) HoverCard.init(cards, track);
  // 글꼴이 늦게 오면 아까 잰 이름 너비가 틀린다 — 오고 나서 한 번 더 잰다
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(renderChrono);
}

/* 배율이 바뀔 때마다 날짜에서 자리를 다시 뽑는다 */
function renderChrono(){
  const track = $('#chronoTrack');
  if (!track || !chMarks.length) return;
  track.style.width = chX(chEndT) + 'px';
  chBands.forEach(b => {
    b.x0 = chX(b.t0); b.x1 = chX(b.t1);
    b.el.style.left  = b.x0 + 'px';
    b.el.style.width = (b.x1 - b.x0) + 'px';
  });
  // 달 눈금은 넉넉히 벌어졌을 때만. 좁을 때는 빗금처럼 보여 축을 더럽힌다
  chTicks.forEach(k => {
    k.el.style.left = chX(k.t) + 'px';
    k.el.hidden = !k.el.classList.contains('q') && CH_PXD < 4;
  });
  chMarks.forEach(m => {
    m.x = chX(m.t);
    m.dot.style.left = m.x + 'px';
    m.lab.style.left = m.x + 'px';
  });
  chMarks.sort((a, b) => a.x - b.x);
  layoutChrono();
  const t = Date.parse(chCur || '');
  if (!isNaN(t)){
    $('#chronoCursor').style.left = chX(t) + 'px';
    $('#chronoDate').style.left = chX(t) + 'px';
  }
  stickYears();

  // 지금 창에 얼마만큼의 시간이 들어와 있는지. 배율을 바꿀 때 유일한 길잡이다
  const vp = $('#chronoVp'), sc = $('#chronoScale');
  if (vp && sc){
    const d = vp.clientWidth / CH_PXD;
    sc.textContent = d >= 400 ? '창 폭 ' + (d / 365).toFixed(1) + '년'
                   : d >= 55  ? '창 폭 ' + Math.round(d / 30) + '달'
                              : '창 폭 ' + Math.round(d) + '일';
  }
  const z = $('#chronoZoom'), i = CH_STEPS.indexOf(CH_PXD);
  if (z){
    z.querySelector('[data-z="-1"]').disabled = i <= 0;
    z.querySelector('[data-z="1"]').disabled  = i >= CH_STEPS.length - 1;
  }
}

/* 줌. 창 안의 한 지점을 붙들어 두고 그 둘레를 늘이거나 줄인다 —
   붙들지 않으면 배율을 바꿀 때마다 보던 자리를 잃는다. */
function chZoom(dir, holdPx){
  const vp = $('#chronoVp');
  if (!vp) return;
  const i = CH_STEPS.indexOf(CH_PXD);
  const j = Math.max(0, Math.min(CH_STEPS.length - 1, i + dir));
  if (j === i) return;
  const pad = parseFloat(getComputedStyle(vp).getPropertyValue('--chPad')) || 0;
  const px = holdPx == null ? vp.clientWidth / 2 : holdPx;
  const hold = chFrom + ((vp.scrollLeft - pad + px) / CH_PXD) * 86400000;
  CH_PXD = CH_STEPS[j];
  renderChrono();
  vp.scrollLeft = pad + chX(hold) - px;
  stickYears();
}

function layoutChrono(){
  const box = $('#chrono'), items = chMarks;
  if (!box || !items.length) return;

  // 층 배정 — 왼쪽부터, 그 층의 마지막 이름과 안 겹치는 첫 층에 얹는다.
  // 층 0,1,2… 를 위·아래로 번갈아 내보내면 축을 사이에 두고 고르게 흩어진다.
  const ends = [];
  let lanes = 0;
  items.forEach(it => {
    const half = it.lab.offsetWidth / 2;
    let k = 0;
    while (k < ends.length && ends[k] > it.x - half) k++;
    ends[k] = it.x + half + CH_GAP;
    it.lane = k;
    lanes = Math.max(lanes, k + 1);
  });

  // 층 수가 정해져야 바 높이와 축의 자리가 나온다
  const up = Math.ceil(lanes / 2), dn = lanes - up;   // 위쪽이 한 층 더
  const axis = 12 + up * CH_LANE;                     // 위 여백 + 위층들
  const H    = axis + dn * CH_LANE + 26;              // 아래층들 + 연도·날짜 자리
  box.style.setProperty('--chH', H + 'px');
  box.style.setProperty('--axis', axis + 'px');

  items.forEach(it => {
    const side = it.lane % 2 === 0 ? 'up' : 'dn';     // 0,2,4…는 위 / 1,3,5…는 아래
    const row  = Math.floor(it.lane / 2);             // 축에서 몇 번째 층인가
    it.lab.classList.remove('up', 'dn');
    it.lab.classList.add(side);
    if (side === 'up'){
      it.lab.style.top = (axis - 8 - (row + 1) * CH_LANE) + 'px';
      it.lab.style.setProperty('--leg', (CH_LANE * row + 8) + 'px');
    } else {
      it.lab.style.top = (axis + 8 + row * CH_LANE) + 'px';
      it.lab.style.setProperty('--leg', (CH_LANE * row + 8) + 'px');
    }
  });
}

/* 연도 이름표를 창 왼쪽에 들러붙인다. 그 해의 띠가 창에 걸쳐 있는 동안은
   이름표가 띠를 벗어나지 않는 선에서 왼쪽 끝을 따라다닌다. */
function stickYears(){
  const vp = $('#chronoVp');
  if (!vp || !chBands.length) return;
  const pad = parseFloat(getComputedStyle(vp).getPropertyValue('--chPad')) || 0;
  const L = vp.scrollLeft - pad;                 // 창 왼쪽이 띠 좌표계에서 어디인가
  chBands.forEach(b => {
    const w = b.tag.offsetWidth;
    const x = Math.max(0, Math.min(L + 6 - b.x0, b.x1 - b.x0 - w - 2));
    b.tag.style.left = x + 'px';
  });
}

let chCur = null, chJump = null;
function markNow(date){
  const box = $('#chrono'), vp = $('#chronoVp');
  if (!CH || !box || !vp) return;
  chCur = date;
  const t = Date.parse(date || '');
  if (!date || isNaN(t)){ box.dataset.nodate = '1'; return; }
  delete box.dataset.nodate;

  // 창 절반만큼 양옆에 여백을 둬야 첫 문서도 마지막 문서도 가운데에 설 수 있다.
  // 양 끝을 붙잡지 않는다 — 붙잡으면 「가운데가 곧 지금」이라는 약속이 깨진다.
  const vpW = vp.clientWidth;
  box.style.setProperty('--chPad', (vpW / 2) + 'px');
  $('#chronoCursor').style.left = chX(t) + 'px';
  const dl = $('#chronoDate');
  dl.style.left = chX(t) + 'px';
  dl.textContent = date;

  // 곧바로 옮긴다. 부드럽게 미는 길(scrollTo behavior:'smooth' 도, CSS 의
  // scroll-behavior 도) 은 브라우저 설정에 따라 통째로 무시돼서, 띠가 아예
  // 안 움직인 적이 있다. 움직이지 않는 띠보다 툭 옮겨지는 띠가 낫다.
  clearTimeout(chJump);
  chJump = setTimeout(() => { vp.scrollLeft = chX(t); stickYears(); }, 0);
}

/* 손으로도 민다 — 세로 휠은 가로로 바꿔 주고, 끌어서도 옮길 수 있게 */
function initChronoScroll(){
  const vp = $('#chronoVp');
  if (!vp) return;
  vp.addEventListener('scroll', stickYears, {passive: true});
  vp.addEventListener('wheel', e => {
    // ⌘/Ctrl 을 누른 채 굴리면 배율. 손가락 아래 날짜를 붙들고 늘인다
    if (e.ctrlKey || e.metaKey){
      e.preventDefault();
      chZoom(e.deltaY < 0 ? 1 : -1, e.clientX - vp.getBoundingClientRect().left);
      return;
    }
    const d = Math.abs(e.deltaX) > Math.abs(e.deltaY) ? e.deltaX : e.deltaY;
    if (!d) return;
    e.preventDefault();
    vp.scrollLeft += d;
  }, {passive: false});

  const z = $('#chronoZoom');
  if (z) z.addEventListener('click', e => {
    const b = e.target.closest('button[data-z]');
    if (b) chZoom(+b.dataset.z, null);
  });

  let down = false, x0 = 0, s0 = 0, moved = false;
  vp.addEventListener('pointerdown', e => {
    down = true; moved = false; x0 = e.clientX; s0 = vp.scrollLeft;
    vp.classList.add('drag');
  });
  vp.addEventListener('pointermove', e => {
    if (!down) return;
    if (Math.abs(e.clientX - x0) > 3){ moved = true; vp.setPointerCapture(e.pointerId); }
    if (moved) vp.scrollLeft = s0 - (e.clientX - x0);
  });
  const up = () => { down = false; vp.classList.remove('drag'); };
  vp.addEventListener('pointerup', up);
  vp.addEventListener('pointercancel', up);
}

function select(id){ state.cur=id; renderList(); renderDoc();
  history.replaceState(null,'','#'+id); }

$('#q').addEventListener('input', e => { state.q=e.target.value; renderList(); });
$('#list').addEventListener('click', e => {
  const b = e.target.closest('.item'); if (b) select(b.dataset.id); });
document.querySelectorAll('.chip[data-group]').forEach(c => c.addEventListener('click', () => {
  const k=c.dataset.group;
  state.groups.has(k)?state.groups.delete(k):state.groups.add(k);
  c.setAttribute('aria-pressed', state.groups.has(k));
  renderList();
}));
document.querySelectorAll('[data-sort]').forEach(b => b.addEventListener('click', () => {
  state.sort=b.dataset.sort;
  document.querySelectorAll('[data-sort]').forEach(x=>x.setAttribute('aria-pressed',x===b));
  renderList();
}));
document.querySelectorAll('[data-view]').forEach(b => b.addEventListener('click', () => {
  state.view=b.dataset.view;
  document.querySelectorAll('[data-view]').forEach(x=>x.setAttribute('aria-pressed',x===b));
  renderDoc();
}));
$('#themeBtn').addEventListener('click', () => {
  const r=document.documentElement;
  const dark=(r.getAttribute('data-theme')||
    (matchMedia('(prefers-color-scheme:dark)').matches?'dark':'light'))==='dark';
  r.setAttribute('data-theme', dark?'light':'dark');
});

// ── 확대 뷰어 ─── 스캔이 없는 자료에서는 통째로 건너뛴다
if (PG){
  let lbPages = [], lbAt = 0;
  const lb = $('#lb'), lbImg = $('#lbImg'), lbStage = $('#lbStage');
  const src = p => `${PG.dir}/${p}.${PG.ext}`;

  function lbShow(){
    const p = lbPages[lbAt];
    lbImg.src = src(p);
    lbImg.alt = `${p}면 원본`;
    $('#lbPg').textContent = `${p}면  (${lbAt+1}/${lbPages.length})`;
    $('#lbPrev').disabled = lbAt === 0;
    $('#lbNext').disabled = lbAt === lbPages.length - 1;
    $('#lbOpen').href = src(p);
    lbStage.scrollTop = 0;
  }
  function lbOpen(pg){
    const d = DOCS.find(x => x.id === state.cur);
    lbPages = (d && d.pages || []).slice();
    // 면 번호는 숫자일 수도 "0003" 같은 문자열일 수도 있다. 문자열로 맞춰 찾는다.
    lbAt = lbPages.map(String).indexOf(String(pg));
    if (lbAt < 0){ lbPages = [pg]; lbAt = 0; }
    lb.setAttribute('open',''); lbShow();
  }
  function lbClose(){ lb.removeAttribute('open'); lbImg.removeAttribute('src'); }
  function lbStep(n){
    const i = lbAt + n;
    if (i >= 0 && i < lbPages.length){ lbAt = i; lbShow(); }
  }

  $('#main').addEventListener('click', e => {
    const t = e.target.closest('.thumb,.pagemark.hit');
    if (t) lbOpen(t.dataset.pg);
  });
  $('#lbPrev').addEventListener('click', () => lbStep(-1));
  $('#lbNext').addEventListener('click', () => lbStep(1));
  $('#lbClose').addEventListener('click', lbClose);
  lb.addEventListener('click', e => { if (e.target === lb || e.target === lbStage) lbClose(); });
  $('#lbFit').addEventListener('click', e => {
    const fit = lbStage.classList.toggle('fit');
    e.target.setAttribute('aria-pressed', fit);
    e.target.textContent = fit ? '실제 크기' : '화면 맞춤';
  });
  addEventListener('keydown', e => {
    if (!lb.hasAttribute('open')) return;
    if (e.key === 'Escape') lbClose();
    else if (e.key === 'ArrowLeft') lbStep(-1);
    else if (e.key === 'ArrowRight') lbStep(1);
  });
}

state.cur = decodeURIComponent((location.hash||'').slice(1)) ||
            visible()[0]?.id || DOCS[0]?.id;
if (!DOCS.some(d => d.id === state.cur)) state.cur = DOCS[0].id;
initChrono(); initChronoScroll();
addEventListener('resize', () => { renderChrono(); markNow(chCur); });
renderList(); renderDoc();
"""

# ---------------------------------------------------------------- 조판
chips = "".join(
    f'\n        <button class="chip" data-group="{H.escape(g["key"])}" '
    f'aria-pressed="false">{H.escape(g["label"])}</button>' for g in groups)
chips_block = f'<div class="chips">{chips}\n      </div>' if groups else ""

sort_btns = "".join(
    f'\n        <button data-sort="{H.escape(s["key"])}" '
    f'aria-pressed="{"true" if i == 0 else "false"}">{H.escape(s["label"])}</button>'
    for i, s in enumerate(sorts))

views = [("primary", runtime["panes"]["primary"])]
if runtime["panes"]["secondary"]:
    views += [("both", runtime["panes"]["both"]), ("secondary", runtime["panes"]["secondary"])]
view_btns = "".join(
    f'\n        <button data-view="{k}" aria-pressed="{"true" if i == 0 else "false"}">'
    f'{H.escape(v)}</button>' for i, (k, v) in enumerate(views))
view_block = f'<div class="seg">{view_btns}\n      </div>' if len(views) > 1 else ""

# 여러 문서철을 한 사이트로 묶었을 때 첫 화면으로 돌아가는 링크.
# collection.json 에 `home` 이 없으면 안 나온다 — 문서철 하나만 따로 쓸 때도
# 깨진 링크가 생기지 않게.
_home = HOME or conf.get("home")
home_link = ""
if _home:
    home_link = (f'<a class="home" href="{H.escape(_home.get("url", "../"))}">'
                 f'<span>←</span>{H.escape(_home.get("label", "전체 목록"))}</a>')

lightbox = """
<div class="lb" id="lb" role="dialog" aria-modal="true" aria-label="원본 지면">
  <div class="lb-bar">
    <span class="pg" id="lbPg"></span>
    <button id="lbPrev">◀ 이전</button>
    <button id="lbNext">다음 ▶</button>
    <button id="lbFit" aria-pressed="false">화면 맞춤</button>
    <div class="grow"></div>
    <a id="lbOpen" href="#" target="_blank" rel="noopener">새 탭</a>
    <button id="lbClose">닫기 (Esc)</button>
  </div>
  <div class="lb-stage" id="lbStage"><img id="lbImg" alt=""></div>
</div>""" if pages_conf else ""

page = f"""<!doctype html>
<html lang="ko"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{H.escape(conf.get("title", "열람기"))} — 열람기</title>
<style>{CSS}
{HC_CSS}</style>
</head><body>
<div class="wrap">
  <aside class="rail">
    <div class="rail-head">
      {home_link}
      <div class="brand">{H.escape(conf.get("title", ""))}
        <small>{H.escape(conf.get("subtitle", ""))}</small></div>
      <input id="q" type="search"
        placeholder="{H.escape(conf.get("search_hint", "검색"))}" aria-label="검색">
      {chips_block}
      <div class="sortbar">
        <span id="count"></span>{sort_btns}
      </div>
    </div>
    <div class="list" id="list"></div>
  </aside>

  <div class="main">
    <div class="toolbar">
      {view_block}
      <div class="grow"></div>
      <button class="chip" id="themeBtn">명암 전환</button>
    </div>
    <div class="srcline">{H.escape(conf.get("source", ""))}</div>
    <div id="main"></div>
  </div>
</div>
<div class="chrono" id="chrono">
  <div class="chrono-vp" id="chronoVp">
    <div class="chrono-track" id="chronoTrack">
      <div class="chrono-cursor" id="chronoCursor"></div>
      <div class="chrono-date" id="chronoDate"></div>
    </div>
  </div>
  <div class="chrono-zoom" id="chronoZoom">
    <button type="button" data-z="-1" title="넓게 보기 (⌘/Ctrl+휠)" aria-label="넓게 보기">−</button>
    <button type="button" data-z="1" title="벌려 보기 (⌘/Ctrl+휠)" aria-label="벌려 보기">+</button>
  </div>
  <div class="chrono-scale" id="chronoScale"></div>
</div>
{lightbox}
<script id="data" type="application/json">{payload}</script>
<script id="conf" type="application/json">{runtime_js}</script>
<script>{HC_JS}</script>
<script>{JS}</script>
</body></html>
"""

os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
open(OUT, "w").write(page)
print(f"{conf.get('title','')} — 문서 {len(docs)}건 → {OUT}  "
      f"({os.path.getsize(OUT)/1e6:.2f} MB)")
if pages_conf:
    # 개수만 세면 안 된다. 면 번호와 파일 이름 규칙이 어긋나 있어도 개수는 맞을 수
    # 있어서, 썸네일이 전부 깨진 채로 통과한 적이 있다. 파일 하나하나를 확인한다.
    d = os.path.normpath(os.path.join(os.path.dirname(OUT), pages_conf["dir"]))
    want = sorted({str(p) for x in docs for p in (x.get("pages") or [])})
    miss = [p for p in want
            if not os.path.exists(os.path.join(d, f"{p}.{pages_conf['ext']}"))]
    print(f"  스캔 {len(want) - len(miss)}/{len(want)}면 · {pages_conf['dir']}")
    if miss:
        print(f"  !! 파일이 없는 면 {len(miss)}개: {' '.join(miss[:10])}"
              f"{' …' if len(miss) > 10 else ''}")
        print("     썸네일과 확대 뷰어가 깨진 채로 나온다.")

    if pages_conf.get("thumbs"):
        td = os.path.normpath(os.path.join(os.path.dirname(OUT), pages_conf["thumbs"]))
        tx = pages_conf.get("thumb_ext", "jpg")
        tm = [p for p in want if not os.path.exists(os.path.join(td, f"{p}.{tx}"))]
        print(f"  썸네일 {len(want) - len(tm)}/{len(want)}면 · {pages_conf['thumbs']}")
        if tm:
            print(f"  !! 썸네일이 없는 면 {len(tm)}개 — make_thumbs.py 를 돌려라")
    else:
        print("  썸네일 없음 — 목록이 원본을 그대로 받는다. make_thumbs.py 를 권한다")
