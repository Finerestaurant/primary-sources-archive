"""문서철들을 묶어 배포용 정적 사이트를 만든다.

    python3 build_site.py <site.json> [--out ../_site] [--no-scans]

랜딩 페이지를 만들고, 각 문서철의 열람기·썸네일·원본 스캔을 한곳에 모은다.
결과는 정적 파일뿐이라 GitHub Pages·Cloudflare Pages 어디든 그대로 올라간다.

    _site/
      index.html          연표와 문서철 목록
      cairo-1943/
        index.html        열람기 (reader.html 을 이름만 바꿔 놓는다)
        pages/  thumbs/
      …

겉모습은 열람기와 같은 언어를 쓴다 — 전신 용지의 등폭 서체, 기밀등급 도장의
자주색, 마이크로필름의 차가운 회청색. 랜딩만 다르게 생기면 같은 자료로 안 보인다.

랜딩의 주인공은 연표다. 이 묶음은 문서 169건이기 이전에 **문구 하나가 만들어져서
번역되고 배신으로 받아들여지기까지의 기록**이고, 첫 화면이 그걸 말해야 한다.
"""
import html as H
import json
import os
import re
import shutil
import subprocess
import sys
from urllib.parse import quote as urlquote

if len(sys.argv) < 2:
    sys.exit(__doc__)

CONF = os.path.abspath(sys.argv[1])
BASE = os.path.dirname(CONF)
OUT = os.path.abspath(sys.argv[sys.argv.index("--out") + 1]) \
    if "--out" in sys.argv else os.path.join(BASE, "_site")
NO_SCANS = "--no-scans" in sys.argv

site = json.load(open(CONF))
HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------- 모으기
os.makedirs(OUT, exist_ok=True)
built = []
for c in site["collections"]:
    src = os.path.join(BASE, c["src"])
    dst = os.path.join(OUT, c["slug"])
    reading = os.path.join(src, "reading")
    cjson = os.path.join(reading, "collection.json")
    if not os.path.exists(cjson):
        print(f"!! {c['slug']} — collection.json 이 없다")
        continue
    os.makedirs(dst, exist_ok=True)

    # 열람기를 **여기로 직접 다시 만든다.** 작업용 reader.html 을 복사해 오지 않는
    # 이유는 「돌아가기」 링크 때문이다 — 그 링크는 사이트로 묶였을 때만 갈 곳이
    # 있어서, 작업용 파일에 넣어 두면 혼자 열었을 때 깨진 링크가 된다.
    # 주소가 /cairo-1943/ 로 끝나게 index.html 로 놓는다.
    # 스캔은 열람기와 **같은 자리**로 복사한다. 그래서 `--flat-scans` 로 `../` 를
    # 떼어 준다 — 작업 폴더에서는 `reading/reader.html` 이라 한 단계 위가 맞지만
    # 여기서는 아니다. 이걸 빠뜨려서 사이트의 스캔이 통째로 깨져 있었다.
    r = subprocess.run(
        [sys.executable, os.path.join(HERE, "build.py"), cjson,
         os.path.join(dst, "index.html"), "--flat-scans",
         "--home", "../", site["title"]],
        capture_output=True, text=True)
    if r.returncode:
        print(f"!! {c['slug']} 열람기 생성 실패\n{r.stdout}{r.stderr}")
        continue

    for kind in (["thumbs"] if NO_SCANS else ["thumbs", "pages"]):
        s = os.path.join(src, kind)
        if not os.path.isdir(s):
            continue
        d = os.path.join(dst, kind)
        os.makedirs(d, exist_ok=True)
        n = 0
        for f in os.listdir(s):
            sp, dp = os.path.join(s, f), os.path.join(d, f)
            if not os.path.exists(dp) or os.path.getmtime(sp) > os.path.getmtime(dp):
                shutil.copyfile(sp, dp)
            n += 1
        c[f"_{kind}"] = n
    built.append(c)
    print(f"  {c['slug']:12} 열람기 + 썸네일 {c.get('_thumbs',0)}장"
          + ("" if NO_SCANS else f" + 스캔 {c.get('_pages',0)}장"))

if not built:
    sys.exit("모을 문서철이 없다.")

TOTAL = sum(c["n"] for c in built)

# ---------------------------------------------------------------- 앵커 검사
# 연표가 가리키는 문서가 실제로 있는지 본다. 틀린 앵커는 화면에서 조용히
# 첫 문서로 넘어가 버려서, 눌러 보기 전에는 잘못된 줄 모른다.
ids, docmap = {}, {}
for c in built:
    cj = json.load(open(os.path.join(BASE, c["src"], "reading", "collection.json")))
    dj = os.path.join(BASE, c["src"], "reading", cj.get("docs", "docs.json"))
    dd = json.load(open(dj))
    ids[c["slug"]] = {str(x["id"]) for x in dd}
    docmap[c["slug"]] = {str(x["id"]): x for x in dd}

bad = []
ALL_EV = [(t, e) for t in site.get("threads", []) for e in t.get("events", [])]
for _t, e in ALL_EV:
    col, doc = e.get("col"), e.get("doc")
    if not doc:
        continue
    if col not in ids:
        bad.append(f"[{_t['slug']}] {e['when']} — 문서철 '{col}' 없음")
    elif str(doc) not in ids[col]:
        bad.append(f"[{_t['slug']}] {e['when']} — {col}/#{doc} 없음")
if bad:
    print("\n!! 연표 링크가 어긋난다:")
    for b in bad:
        print("   " + b)
    sys.exit("site.json 의 timeline 을 고쳐라.")

linked = sum(1 for _t, e in ALL_EV if e.get("doc"))
print(f"  주제 {len(site.get('threads', []))}개 · 연표 {len(ALL_EV)}항 · "
      f"문서까지 연결 {linked}항")

# ---------------------------------------------------------------- 랜딩
CSS = r"""
:root{
  --bg:#eef1f4; --panel:#f7f9fa; --edge:#ccd4da; --edge-soft:#dde4e9;
  --ink:#16202a; --ink-2:#4a5b68; --ink-3:#71828f;
  --stamp:#8c2f39; --link:#2f5d86;
  --term-bg:rgba(47,93,134,.06); --term-bg-on:rgba(47,93,134,.14);
  --term-line:#9db0c2;
  --mono:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,monospace;
  --sans:"Apple SD Gothic Neo","Pretendard","Malgun Gothic","Noto Sans KR",
         -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
}
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){
    --bg:#12171c; --panel:#171d23; --edge:#2b353e; --edge-soft:#222a31;
    --ink:#dfe6ec; --ink-2:#a4b2bd; --ink-3:#75858f;
    --stamp:#c9707a; --link:#7fb0da;
    --term-bg:rgba(127,176,218,.08); --term-bg-on:rgba(127,176,218,.18);
    --term-line:#5b7183;
  }
}
:root[data-theme="dark"]{
  --bg:#12171c; --panel:#171d23; --edge:#2b353e; --edge-soft:#222a31;
  --ink:#dfe6ec; --ink-2:#a4b2bd; --ink-3:#75858f;
  --stamp:#c9707a; --link:#7fb0da;
  --term-bg:rgba(127,176,218,.08); --term-bg-on:rgba(127,176,218,.18);
  --term-line:#5b7183;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);
  font-size:16px;line-height:1.75;-webkit-font-smoothing:antialiased}
a{color:var(--link)}
.wrap{max-width:980px;margin:0 auto;padding:0 22px}

/* ── 머리 ── */
header{border-bottom:1px solid var(--edge);background:var(--panel)}
header .wrap{padding-top:34px;padding-bottom:26px}
.kicker{font-family:var(--mono);font-size:11.5px;letter-spacing:.16em;
  text-transform:uppercase;color:var(--ink-3);margin:0 0 14px}
h1{font-size:clamp(21px,2.6vw,27px);line-height:1.2;margin:0 0 5px;
  font-weight:660;letter-spacing:-.005em;text-wrap:balance}
.tagline{font-size:14.5px;color:var(--ink-3);margin:0 0 16px}
.lead{max-width:64ch;color:var(--ink-2);font-size:14.5px;margin:0}

/* ── 주제가 이 페이지의 주인공이다 ── */
.th-hero{margin:0 0 20px}
.th-hero .kicker{margin:0 0 9px}
.th-h{font-size:clamp(28px,4.4vw,40px);line-height:1.14;margin:0 0 8px;
  font-weight:680;letter-spacing:-.012em;text-wrap:balance;
  color:var(--ink);font-family:var(--sans);text-transform:none}
.th-tag{font-size:clamp(15px,2vw,18px);color:var(--ink-2);margin:0 0 16px}
.th-lead{max-width:62ch;color:var(--ink-2);font-size:15.5px;margin:0}
.counts{display:flex;flex-wrap:wrap;gap:10px 24px;margin-top:18px;
  font-family:var(--mono);font-size:12px;color:var(--ink-3);
  font-variant-numeric:tabular-nums}
.counts b{color:var(--ink);font-size:20px;font-weight:650;margin-right:5px}
#themeBtn{position:absolute;top:18px;right:22px;background:transparent;
  border:1px solid var(--edge);color:var(--ink-2);border-radius:999px;
  padding:4px 12px;font:inherit;font-size:12px;cursor:pointer}

/* ── 주제 고르기 ── */
.th-tabs{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 26px}
.th-tab{display:flex;flex-direction:column;gap:1px;align-items:flex-start;
  background:var(--panel);border:1px solid var(--edge);border-radius:5px;
  padding:9px 15px;cursor:pointer;font:inherit;color:var(--ink-2);
  text-align:left;transition:background .12s ease,border-color .12s ease}
.th-tab b{font-size:14.5px;font-weight:640;color:var(--ink)}
.th-tab span{font-family:var(--mono);font-size:10.5px;letter-spacing:.06em;
  color:var(--ink-3);font-variant-numeric:tabular-nums}
.th-tab:hover{border-color:var(--link)}
.th-tab[aria-pressed="true"]{background:var(--term-bg-on);
  border-color:var(--link);box-shadow:inset 3px 0 0 var(--link)}
.th-tab[aria-pressed="true"] b{color:var(--link)}
.th-pane[hidden]{display:none}

/* ── 연표 ── */
section{padding:56px 0}
section.threads{padding-top:34px}
h2{font-size:13px;font-family:var(--mono);letter-spacing:.14em;
  text-transform:uppercase;color:var(--ink-3);margin:0 0 6px;font-weight:600}
.sec-lead{color:var(--ink-2);margin:0 0 30px;max-width:62ch;font-size:15px}
/* 조작 안내는 내용이 아니라 거들기다. 한 톤 물러나게 둔다 */
.sec-lead .hint{color:var(--ink-3);font-size:13.5px}

.tl{position:relative;padding-left:0}
.tl::before{content:"";position:absolute;left:104px;top:6px;bottom:6px;
  width:1px;background:var(--edge)}
.ev{display:grid;grid-template-columns:92px 1fr;gap:0 30px;
  padding:9px 0;position:relative}
.ev time{font-family:var(--mono);font-size:12px;color:var(--ink-3);
  text-align:right;padding-top:3px;font-variant-numeric:tabular-nums;
  white-space:nowrap}
.ev::before{content:"";position:absolute;left:101px;top:16px;width:7px;height:7px;
  border-radius:50%;background:var(--edge);border:1px solid var(--bg)}
.ev.key::before{background:var(--stamp);width:9px;height:9px;left:100px}
.ev .who{font-family:var(--mono);font-size:11px;letter-spacing:.07em;
  text-transform:uppercase;color:var(--ink-3);display:flex;align-items:center;
  gap:6px;margin-bottom:1px}
/* 어느 쪽이 남긴 기록인지 한눈에 갈리게. 작게, 옅게 — 읽는 것을 방해하지 않는다 */
.ev .flag{flex:0 0 auto;border:.5px solid var(--edge);border-radius:1px;
  opacity:.85;display:block}
.ev p{margin:0;font-size:15px;color:var(--ink-2)}
.ev.key p{color:var(--ink)}
.ev strong{font-weight:640;color:var(--ink)}
.ev code{font-family:var(--mono);font-size:.88em;background:var(--panel);
  border:1px solid var(--edge-soft);border-radius:3px;padding:0 4px}
/* 연표 항목은 통째로 링크다. 색을 바꾸면 본문이 시끄러워지니
   왼쪽에 얇은 띠를 두고, 손을 얹으면 바탕이 들어온다 */
.ev a{color:inherit;text-decoration:none;display:block;
  margin:-6px -12px;padding:6px 12px;border-radius:4px;
  border-left:2px solid var(--term-line);padding-left:12px;
  transition:background .12s ease}
.ev a:hover{background:var(--term-bg-on);border-left-color:var(--link)}
.ev a:hover .body{color:var(--ink)}
.ev a:focus-visible{outline:2px solid var(--link);outline-offset:1px}
.ev.key a{border-left-color:var(--stamp)}

/* ── 문서철 ── */
.cols{display:grid;gap:14px}
.col{display:block;border:1px solid var(--edge);border-radius:4px;
  background:var(--panel);padding:20px 22px;text-decoration:none;color:inherit}
.col:hover{border-color:var(--link)}
.col-top{display:flex;justify-content:space-between;align-items:baseline;
  gap:14px;flex-wrap:wrap;margin-bottom:5px}
.col h3{margin:0;font-size:18px;font-weight:650}
.col .n{font-family:var(--mono);font-size:12px;color:var(--ink-3);
  font-variant-numeric:tabular-nums;white-space:nowrap}
.col .period{font-family:var(--mono);font-size:12px;color:var(--ink-3);
  margin-bottom:9px}
.col .blurb{margin:0 0 11px;font-size:14.5px;color:var(--ink-2);max-width:66ch}
.col .hl{margin:0;font-size:13.5px;color:var(--stamp);
  border-left:2px solid var(--stamp);padding-left:11px}
.col .src{margin:12px 0 0;font-size:11.5px;color:var(--ink-3);
  font-family:var(--mono);line-height:1.6}

/* ── 방법 ── */
.method{display:grid;gap:2px;border:1px solid var(--edge);border-radius:4px;
  overflow:hidden;background:var(--edge)}
.method div{background:var(--panel);padding:15px 20px;
  display:grid;grid-template-columns:120px 1fr;gap:20px}
.method b{font-size:13.5px;font-weight:620}
.method span{font-size:14px;color:var(--ink-2)}

/* ── 주의·꼬리 ── */
.warn{border:1px solid var(--stamp);border-radius:4px;padding:18px 22px;
  background:var(--panel)}
.warn h3{margin:0 0 8px;font-size:14px;color:var(--stamp);
  font-family:var(--mono);letter-spacing:.08em;text-transform:uppercase}
.warn p{margin:0 0 9px;font-size:14.5px;color:var(--ink-2);max-width:66ch}
.warn p:last-child{margin-bottom:0}
footer{border-top:1px solid var(--edge);margin-top:40px;background:var(--panel)}
footer .wrap{padding:30px 22px 46px;font-size:12.5px;color:var(--ink-3)}
footer p{margin:0 0 8px;max-width:70ch}
footer a{color:var(--ink-3)}

@media(max-width:640px){
  .tl::before{left:0}
  .ev{grid-template-columns:1fr;gap:0;padding-left:20px}
  .ev::before{left:-3px;top:14px}
  .ev.key::before{left:-4px}
  .ev time{text-align:left;padding-top:0;display:block;margin-bottom:2px}
  .method div{grid-template-columns:1fr;gap:4px}
  header .wrap{padding-top:40px}
}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
"""


def md(s):
    """랜딩에서 쓰는 최소 표기 — **굵게** 와 `등폭`."""
    s = H.escape(s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    return s


by_slug = {c["slug"]: c for c in built}

# 연표에서 그 문서로 바로 간다. `doc` 이 있으면 열람기의 #앵커까지,
# 없으면 문서철 첫 화면까지. 앵커 값은 열람기의 문서 id(= docs.json 의 id)다.
# 링크에 머물면 호버 카드가 뜨도록 요약도 함께 뽑아 둔다.
def card_of(slug, did):
    d = docmap[slug][did]
    route = " → ".join(
        m["v"] for m in (d.get("meta") or [])
        if m.get("k") in ("발신", "수신") and m.get("v"))
    return {
        "title": d.get("title"),
        "date": d.get("date"),
        "badge": d.get("badge") or by_slug[slug]["title"],
        "route": route or None,
        "sum": d.get("summary"),
        "points": (d.get("points") or [])[:2],
        "pages": len(d.get("pages") or []) or None,
    }


# 1945년의 깃발. 15×10 으로 줄이면 세부는 뭉개지니 알아볼 최소한만 남긴다 —
# 성조기는 줄무늬와 청색 칸, 일장기는 붉은 동그라미, 소련기는 붉은 바탕에 금별,
# 유니언잭은 붉은 십자, 중화민국기는 청천백일, 교황청기는 노랑과 흰색.
FLAGS = {
 "us": '<rect width="15" height="10" fill="#f2f3f4"/>'
       '<g fill="#b32134">'
       '<rect y="0" width="15" height="1.1"/><rect y="2.2" width="15" height="1.1"/>'
       '<rect y="4.4" width="15" height="1.1"/><rect y="6.6" width="15" height="1.1"/>'
       '<rect y="8.8" width="15" height="1.1"/></g>'
       '<rect width="6.4" height="5.5" fill="#2a3560"/>'
       '<g fill="#f2f3f4"><circle cx="1.6" cy="1.4" r=".5"/><circle cx="3.2" cy="1.4" r=".5"/>'
       '<circle cx="4.8" cy="1.4" r=".5"/><circle cx="2.4" cy="2.8" r=".5"/>'
       '<circle cx="4" cy="2.8" r=".5"/><circle cx="1.6" cy="4.1" r=".5"/>'
       '<circle cx="3.2" cy="4.1" r=".5"/><circle cx="4.8" cy="4.1" r=".5"/></g>',
 "jp": '<rect width="15" height="10" fill="#f2f3f4"/>'
       '<circle cx="7.5" cy="5" r="3" fill="#bc002d"/>',
 "su": '<rect width="15" height="10" fill="#b32134"/>'
       '<path d="M3.4 1.6 4 3.3 5.8 3.3 4.4 4.4 4.9 6.1 3.4 5.1 2 6.1 2.5 4.4 1.1 3.3 '
       '2.9 3.3Z" fill="#e8c34a"/>',
 "uk": '<rect width="15" height="10" fill="#22346b"/>'
       '<path d="M0 0 15 10M15 0 0 10" stroke="#f2f3f4" stroke-width="2"/>'
       '<path d="M7.5 0v10M0 5h15" stroke="#f2f3f4" stroke-width="3.4"/>'
       '<path d="M7.5 0v10M0 5h15" stroke="#b32134" stroke-width="1.9"/>',
 "cn": '<rect width="15" height="10" fill="#b32134"/>'
       '<rect width="7.5" height="5" fill="#22346b"/>'
       '<circle cx="3.75" cy="2.5" r="1.5" fill="#f2f3f4"/>',
 "va": '<rect width="15" height="10" fill="#f2f3f4"/>'
       '<rect width="7.5" height="10" fill="#e8c34a"/>',
}


def flag_of(e):
    """깃발은 문서철에서 정한다 — 일본 외무성 자료면 일장기, 나머지는 성조기.
    소련·영국처럼 다른 쪽이 말하는 자리는 항목에 `flag` 를 적어 덮어쓴다."""
    f = e.get("flag") or ("jp" if e.get("col") == "mofa-1945" else "us")
    svg = FLAGS.get(f)
    if not svg:
        return ""
    return (f'<svg class="flag" viewBox="0 0 15 10" width="15" height="10" '
            f'aria-hidden="true">{svg}</svg>')


def render_events(events, cards):
    out = []
    for e in events:
        inner = (f'<span class="who">{H.escape(e["who"])}{flag_of(e)}</span>'
                 f'<p class="body">{md(e["what"])}</p>')
        if e.get("col") in by_slug:
            href = e["col"] + "/"
            attr = ""
            if e.get("doc"):
                did = str(e["doc"])
                href += "#" + urlquote(did, safe="")
                key = f'{e["col"]}:{did}'
                cards[key] = card_of(e["col"], did)
                attr = f' data-card="{H.escape(key)}"'
            inner = f'<a href="{H.escape(href)}"{attr}>{inner}</a>'
        out.append(f'<div class="ev{" key" if e.get("key") else ""}">'
                   f'<time>{H.escape(e["when"])}</time><div>{inner}</div></div>')
    return "".join(out)


cards = {}
threads = site.get("threads", [])
th_tabs, th_panes = [], []
for _i, _t in enumerate(threads):
    _on = "true" if _i == 0 else "false"
    th_tabs.append(f'<button class="th-tab" data-th="{H.escape(_t["slug"])}" '
                   f'aria-pressed="{_on}"><b>{H.escape(_t["title"])}</b>'
                   f'<span>{H.escape(_t.get("kicker",""))}</span></button>')
    _hint = (f' <span class="hint">{H.escape(_t["hint"])}</span>'
             if _t.get("hint") else "")
    _n = len(_t.get("events", []))
    th_panes.append(
        f'<div class="th-pane" data-th="{H.escape(_t["slug"])}"'
        f'{"" if _i == 0 else " hidden"}>'
        f'<div class="th-hero">'
        f'<p class="kicker">{H.escape(_t.get("kicker",""))} · 연표 {_n}항</p>'
        f'<h2 class="th-h">{H.escape(_t.get("headline") or _t["title"])}</h2>'
        + (f'<p class="th-tag">{H.escape(_t["tagline"])}</p>'
           if _t.get("tagline") else "")
        + (f'<p class="th-lead">{H.escape(_t["lead"])}</p>'
           if _t.get("lead") else "")
        + f'</div>'
        f'<p class="sec-lead">{H.escape(_t.get("sub",""))}{_hint}</p>'
        f'<div class="tl">{render_events(_t.get("events", []), cards)}</div></div>')

# 호버 카드는 따로 만든 부품이다. 소스는 나눠 두되 결과는 한 파일로 낸다 —
# 랜딩도 열람기처럼 그 자체로 완결돼야 옮기기 쉽다.
HC_CSS = open(os.path.join(HERE, "hovercard.css")).read()
# 스크립트 안에 </script> 가 들어 있으면 HTML 파서가 거기서 끊는다.
# 주석에 예시로 적어 둔 것 하나 때문에 통째로 죽은 적이 있어 넣어 둔 방어다.
HC_JS = open(os.path.join(HERE, "hovercard.js")).read().replace("</", "<\\/")
cards_js = json.dumps(cards, ensure_ascii=False).replace("</", "<\\/")

cols = []
for c in built:
    scans = "" if NO_SCANS else f" · 원본 지면 {c.get('_pages', 0)}면"
    cols.append(f"""<a class="col" href="{c['slug']}/">
      <div class="col-top"><h3>{H.escape(c['title'])}</h3>
        <span class="n">{c['n']}건{scans}</span></div>
      <div class="period">{H.escape(c['period'])}</div>
      <p class="blurb">{H.escape(c['blurb'])}</p>
      <p class="hl">{md(c['highlight'])}</p>
      <p class="src">{H.escape(c['source'])}<br>{H.escape(c['rights'])}</p>
    </a>""")

method = "".join(f"<div><b>{H.escape(a)}</b><span>{H.escape(b)}</span></div>"
                 for a, b in site["method"])

repo = site.get("repo")
contact = site.get("contact")

# 섹션 제목·설명은 site.json 에 둔다. 문구를 고치려고 이 스크립트를 열게 하면 안 된다.
S = site.get("sections", {})


def sec(key, dflt_h, dflt_lead):
    s = S.get(key, {})
    h = H.escape(s.get("h", dflt_h))
    lead = H.escape(s.get("lead", dflt_lead))
    hint = s.get("hint")
    tail = f' <span class="hint">{H.escape(hint)}</span>' if hint else ""
    return f'<h2>{h}</h2><p class="sec-lead">{lead}{tail}</p>'


warn = S.get("warn", {})
warn_items = warn.get("items") or []
warn_html = "".join(f"<p><strong>{H.escape(a)}</strong> {H.escape(b)}</p>"
                    for a, b in warn_items)

page = f"""<!doctype html>
<html lang="ko"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{H.escape(site['title'])} — {H.escape(site['tagline'])}</title>
<meta name="description" content="{H.escape(site['tagline'])}. 1차 사료 {TOTAL}건을 원문과 나란히 옮겼다.">
<style>{CSS}
{HC_CSS}</style>
</head><body>
<header style="position:relative">
  <button id="themeBtn">명암 전환</button>
  <div class="wrap">
    <p class="kicker">1차 사료 열람 · 원문 대조</p>
    <h1>{H.escape(site['title'])}</h1>
    <p class="tagline">{H.escape(site['tagline'])}</p>
    <p class="lead">{H.escape(site['lead'])}</p>
    <div class="counts">
      <span><b>{TOTAL}</b>건</span>
      <span><b>{len(built)}</b>개 문서철</span>
      <span><b>4년 반</b>1943.11 – 1948.04</span>
    </div>
  </div>
</header>

<div class="wrap">
  <section class="threads">
    <div class="th-tabs">{''.join(th_tabs)}</div>
    {''.join(th_panes)}
  </section>

  <section>
    {sec("collections", "문서철", "")}
    <div class="cols">{''.join(cols)}</div>
  </section>

  <section>
    {sec("method", "어떻게 만들었나", "")}
    <div class="method">{method}</div>
  </section>

  <section>
    <div class="warn">
      <h3>{H.escape(warn.get("h", "읽기 전에"))}</h3>
      {warn_html}
    </div>
  </section>
</div>

<footer><div class="wrap">
  <p><strong>출처와 이용 조건</strong>은 문서철마다 다르다. FRUS 세 종은 미국 정부
    저작물로 퍼블릭 도메인이다. NDL 계열 두 종은 일본 국립국회도서관이 촬영·공개한
    것으로, 소장 표시는 <span style="font-family:var(--mono)">国立国会図書館
    National Diet Library, JAPAN</span> 이다. 각 문서철 화면 위쪽에 원 출처를
    적어 두었다.</p>
  <p>권리에 관해 문제 제기할 것이 있으면
    {'<a href="mailto:' + H.escape(contact) + '">' + H.escape(contact) + '</a> 로 알려주기 바란다. 확인하고 내리겠다.' if contact else '연락 바란다.'}</p>
  {'<p>스크립트와 원자료: <a href="' + H.escape(repo) + '">' + H.escape(repo) + '</a></p>' if repo else ''}
</div></footer>

<script>{HC_JS}</script>
<script>
HoverCard.init({cards_js});

// 주제 전환. 주소에 #thread=... 를 남겨 링크로 공유할 수 있게 한다.
const tabs = [...document.querySelectorAll('.th-tab')];
const panes = [...document.querySelectorAll('.th-pane')];
function showThread(slug, push){{
  const hit = tabs.find(t => t.dataset.th === slug) || tabs[0];
  if (!hit) return;
  tabs.forEach(t => t.setAttribute('aria-pressed', t === hit));
  panes.forEach(p => p.hidden = p.dataset.th !== hit.dataset.th);
  if (push) history.replaceState(null, '', '#thread=' + hit.dataset.th);
}}
tabs.forEach(t => t.addEventListener('click', () => showThread(t.dataset.th, true)));
const m = (location.hash || '').match(/thread=([\w-]+)/);
if (m) showThread(m[1], false);
document.getElementById('themeBtn').addEventListener('click',()=>{{
  const r=document.documentElement;
  const dark=(r.getAttribute('data-theme')||
    (matchMedia('(prefers-color-scheme:dark)').matches?'dark':'light'))==='dark';
  r.setAttribute('data-theme',dark?'light':'dark');
}});
</script>
</body></html>
"""

open(os.path.join(OUT, "index.html"), "w").write(page)
open(os.path.join(OUT, ".nojekyll"), "w").write("")   # GitHub Pages 가 _ 폴더를 안 지우게

total = 0
for r, d, f in os.walk(OUT):
    for x in f:
        total += os.path.getsize(os.path.join(r, x))
print(f"\n{site['title']} — 문서철 {len(built)}개 · {TOTAL}건 → {OUT}")
print(f"  전체 {total/1e6:.0f}MB" + ("  (스캔 제외)" if NO_SCANS else ""))
