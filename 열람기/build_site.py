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

# 문서철을 펴내거나 심사해 올린 기관의 인장. 문서철마다 있는 게 아니라 랜딩
# 전체가 공유하는 자산이라, 문서철별 스캔·썸네일과는 따로 한 번만 복사한다.
_logos_src = os.path.join(HERE, "inst-logos")
_logos_dst = os.path.join(OUT, "inst-logos")
if os.path.isdir(_logos_src):
    os.makedirs(_logos_dst, exist_ok=True)
    for f in os.listdir(_logos_src):
        if f.startswith("_"):
            continue
        sp, dp = os.path.join(_logos_src, f), os.path.join(_logos_dst, f)
        if not os.path.exists(dp) or os.path.getmtime(sp) > os.path.getmtime(dp):
            shutil.copyfile(sp, dp)

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
    dj = os.path.join(reading, "docs.json")
    if os.path.exists(dj):
        c["_docs"] = json.load(open(dj))
    built.append(c)
    print(f"  {c['slug']:12} 열람기 + 썸네일 {c.get('_thumbs',0)}장"
          + ("" if NO_SCANS else f" + 스캔 {c.get('_pages',0)}장"))

if not built:
    sys.exit("모을 문서철이 없다.")

TOTAL = sum(c["n"] for c in built)

# 머리에 적는 기간. **손으로 적어 두었더니 문서철이 늘어도 그대로였다.**
# 1953년까지 자료가 들어왔는데 1948년까지라고 적혀 있었다. 세어서 적는다.
_dates = sorted(d["date"] for c in built for d in c.get("_docs", []) if d.get("date"))
if _dates:
    _a, _b = _dates[0], _dates[-1]
    _y = (int(_b[:4]) - int(_a[:4])) * 12 + int(_b[5:7]) - int(_a[5:7])
    SPAN = (f"{_y // 12}년 반" if 5 <= _y % 12 <= 7 else
            f"{_y // 12}년" if _y % 12 < 5 else f"{_y // 12 + 1}년")
    RANGE = f"{_a[:4]}.{_a[5:7]} – {_b[:4]}.{_b[5:7]}"
else:
    SPAN, RANGE = "", ""

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

# 사건 목록을 여기서 한 번 읽어 둔다. 주제 항목은 `ev` 로 이 목록을 가리키고,
# 날짜와 문서는 거기에만 있다.
_ef = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chrono.json")
EVENTS = {e["id"]: e for e in json.load(open(_ef, encoding="utf-8"))["events"]}

bad = []
ALL_EV = [(t, e) for t in site.get("threads", []) for e in t.get("events", [])]
for _t, e in ALL_EV:
    ev = EVENTS.get(e.get("ev"))
    if ev is None:
        bad.append(f"[{_t['slug']}] 사건 '{e.get('ev')}' 이 chrono.json 에 없음")
        continue
    for col, doc in (ev.get("docs") or []):
        if col not in ids:
            bad.append(f"[{_t['slug']}] {ev['id']} — 문서철 '{col}' 없음")
        elif str(doc) not in ids[col]:
            bad.append(f"[{_t['slug']}] {ev['id']} — {col}/#{doc} 없음")
if bad:
    print("\n!! 연표 링크가 어긋난다:")
    for b in bad:
        print("   " + b)
    sys.exit("site.json 과 열람기/chrono.json 을 맞춰라.")

linked = sum(1 for _t, e in ALL_EV if (EVENTS.get(e.get("ev")) or {}).get("docs"))
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

/* ── 국면 고르기. 주제 위에 한 칸 더 있다 ──
   주제가 여섯이 되면서 진주만(두 달)과 조선(열 해)이 한 줄에 나란히 서게 됐다.
   읽는 사람은 둘이 같은 층위인 줄 알고 누른다. 국면으로 한 번 갈라 준다. */
.arc-tabs{display:flex;flex-wrap:wrap;gap:0;margin:0 0 14px;
  border-bottom:1px solid var(--edge)}
.arc-tab{background:none;border:0;border-bottom:2px solid transparent;
  margin-bottom:-1px;padding:7px 15px 8px;cursor:pointer;font:inherit;
  color:var(--ink-3);font-size:14px;font-weight:600;letter-spacing:-.005em}
.arc-tab:hover{color:var(--ink-2)}
.arc-tab[aria-pressed="true"]{color:var(--link);border-bottom-color:var(--link)}
.arc-tab i{font-style:normal;font-family:var(--mono);font-size:10.5px;
  color:var(--ink-3);margin-left:6px;font-variant-numeric:tabular-nums}
.th-tab[hidden]{display:none}

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
/* 덜 된 문서철임을 카드에서 바로 알 수 있게. 읽는 사람이 빈 곳을 만나기 전에 알아야 한다 */
.wip{margin:8px 0 0;font-size:12px;color:var(--ink-3);font-family:var(--mono);
  border-left:2px solid var(--stamp);padding-left:8px;line-height:1.45}
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
/* 점은 세로줄 한가운데(104.5px)와 첫 글줄에 맞춘다. 자리를 좌표로 적지 않고
   한 점을 잡아 옮기는 까닭은, 굵은 점이 2px 크기 때문이다. 좌표로 적으면
   크기를 고칠 때마다 두 벌을 같이 고쳐야 하고 실제로 1px 어긋나 있었다 */
.ev::before{content:"";position:absolute;left:104.5px;top:18.5px;
  transform:translate(-50%,-50%);width:7px;height:7px;
  border-radius:50%;background:var(--edge);border:1px solid var(--bg)}
.ev.key::before{background:var(--stamp);width:9px;height:9px}
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
/* 아직 옮기지 않아 문서가 걸리지 않은 항목. 링크가 없다고 왼쪽 띠까지 없으면
   줄이 들쭉날쭉해 고장난 것으로 보인다. 점선으로 자리를 지키고, 옅게 둔다 */
.ev.pending>div{border-left:2px dashed var(--edge);padding-left:12px;
  margin-left:-12px}
.ev.pending p{color:var(--ink-3)}
.ev.pending strong{color:var(--ink-2);font-weight:600}

/* ── 문서철 ── */
/* 문서철이 열여섯 개로 늘면서 한 줄로 나열하면 흐려진다. 두 시기로 갈라
   각각에 소개를 붙인다 — 주제(threads) 탭의 「국면」과 같은 생각이다 */
.col-group{margin:0 0 40px}
.col-group:last-child{margin-bottom:0}
.col-group h3{margin:0 0 6px;font-size:16.5px;font-weight:650;color:var(--ink)}
.col-group>p{margin:0 0 18px;font-size:14px;color:var(--ink-2);max-width:62ch}
.cols{display:grid;gap:14px}
.col{display:block;border:1px solid var(--edge);border-radius:4px;
  background:var(--panel);padding:20px 22px;text-decoration:none;color:inherit}
.col:hover{border-color:var(--link)}
.col-top{display:flex;justify-content:space-between;align-items:baseline;
  gap:14px;flex-wrap:wrap;margin-bottom:5px}
.col h3{margin:0;font-size:18px;font-weight:650;display:flex;align-items:center;gap:8px}
/* 제목 옆의 국기. 자랑이 아니라 표시이니 작고 조용하게 둔다 */
.col-fl{display:inline-flex;gap:3px;align-items:center}
.col-fl svg{display:block;border:.5px solid var(--edge);border-radius:1px;
  box-shadow:0 0 0 .5px rgba(0,0,0,.04)}
.col .n{font-family:var(--mono);font-size:12px;color:var(--ink-3);
  font-variant-numeric:tabular-nums;white-space:nowrap}
.col .period{font-family:var(--mono);font-size:12px;color:var(--ink-3);
  margin-bottom:9px}
.col .blurb{margin:0 0 11px;font-size:14.5px;color:var(--ink-2);max-width:66ch}
.col .hl{margin:0;font-size:13.5px;color:var(--stamp);
  border-left:2px solid var(--stamp);padding-left:11px}
.col .src{margin:0;font-size:11.5px;color:var(--ink-3);
  font-family:var(--mono);line-height:1.6}
/* 출처 줄과 발행 기관 낙관을 한 줄에 놓는다. 카드가 좁아지면 낙관이
   먼저 아래로 떨어져 우하단에 남는다 */
.col-foot{display:flex;flex-wrap:wrap;align-items:flex-end;
  gap:8px 14px;margin-top:12px}
/* 실물 인장이라 색이 짙다. 옅게 죽여 두고 손을 얹으면 살아나게 한다 —
   국기와 같은 자리에 앉지만, 국기보다 한 걸음 물러나 있어야 한다 */
.col-inst{flex:0 0 auto;margin-left:auto;width:30px;height:30px;
  object-fit:contain;border:1px solid var(--edge);border-radius:3px;
  background:#fff;padding:3px;filter:grayscale(1);opacity:.55;
  transition:filter .15s ease,opacity .15s ease}
.col:hover .col-inst{filter:grayscale(0);opacity:1}

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
  .ev::before{left:.5px;top:19.5px}   /* 여기선 날짜가 본문 위로 올라온다 */
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
 "se": '<rect width="15" height="10" fill="#2a5f9e"/>'
       '<path d="M4.9 0v10M0 5h15" stroke="#e8c34a" stroke-width="2.2"/>',
 "fr": '<rect width="15" height="10" fill="#f2f3f4"/>'
       '<rect width="5" height="10" fill="#22346b"/>'
       '<rect x="10" width="5" height="10" fill="#b32134"/>',
 "ch": '<rect width="15" height="10" fill="#b32134"/>'
       '<path d="M7.5 2.4v5.2M4.9 5h5.2" stroke="#f2f3f4" stroke-width="1.7"/>',
 "de": '<rect y="0" width="15" height="3.34" fill="#1a1a1a"/>'
       '<rect y="3.33" width="15" height="3.34" fill="#b32134"/>'
       '<rect y="6.66" width="15" height="3.34" fill="#e8c34a"/>',
}


def flag_of(e):
    """깃발은 문서철에서 정한다 — 일본 외무성 자료면 일장기, 나머지는 성조기.
    소련·영국처럼 다른 쪽이 말하는 대목은 항목에 `flag` 를 적어 덮어쓴다.

    **문서가 걸리지 않은 항목에는 깃발을 달지 않는다.** 깃발은 「이것을 누가
    적었는가」를 가리키는데, 아직 옮기지 않아 문서가 없는 항목은 적은 사람이
    없다. 성조기를 달아 두면 「중공군」이나 「판문점」 옆에 성조기가 붙는다."""
    if not e.get("col"):
        return ""
    f = e.get("flag") or ("jp" if e.get("col") == "mofa-1945" else "us")
    svg = FLAGS.get(f)
    if not svg:
        return ""
    return (f'<svg class="flag" viewBox="0 0 15 10" width="15" height="10" '
            f'aria-hidden="true">{svg}</svg>')


def render_events(events, cards):
    out = []
    for e in events:
        # 날짜와 문서는 사건 목록(열람기/chrono.json)에 있다. 주제가 가진 것은
        # 자기 문장뿐이다 — 같은 사건을 두 주제가 다르게 적을 수 있어서다.
        ev = EVENTS.get(e.get("ev")) or {}
        # 저장은 ISO(1943-11)로 하고 화면에는 점(1943.11)으로 찍는다. 이 화면이
        # 줄곧 써 온 표기다. disp 가 있으면 그것이 우선 — 「08.14 20:05」처럼
        # 해가 없고 시각이 붙은 것은 그 글자 자체가 내용이다.
        when = ev.get("disp") or (ev.get("date") or "").replace("-", ".")
        docs = [d for d in (ev.get("docs") or []) if d[0] in by_slug]
        inner = (f'<span class="who">{H.escape(e["who"])}{flag_of(e)}</span>'
                 f'<p class="body">{md(e["what"])}</p>')
        if docs:
            col, did = docs[0][0], str(docs[0][1])
            href = col + "/#" + urlquote(did, safe="")
            key = f"{col}:{did}"
            cards[key] = card_of(col, did)
            inner = (f'<a href="{H.escape(href)}" '
                     f'data-card="{H.escape(key)}">{inner}</a>')
        out.append(f'<div class="ev{" key" if e.get("key") else ""}'
                   f'{"" if docs else " pending"}">'
                   f'<time>{H.escape(when)}</time><div>{inner}</div></div>')
    return "".join(out)


cards = {}
threads = site.get("threads", [])

# 주제가 어느 국면에 속하는지는 **여기서 계산한다.** 사건에 적어 두면 규칙이
# 바뀔 때마다 196개를 다시 써야 하고, 국면은 탭을 가르는 데만 쓰이며 탭은 주제
# 단위다. 저장할 것이 아니다.
#
# 조선 이야기는 카이로에서 「in due course」가 만들어지고 얄타에서 신탁통치
# 기간이 입에 오르고 일반명령 제1호가 38도선을 긋는 데까지가 전쟁의 뒤처리다.
# 하지가 상륙한 1945년 9월부터는 다른 이야기가 시작된다.
ARCS = json.load(open(_ef, encoding="utf-8")).get("arcs", [])
KOREA_IN_WWII = "1945-08-31"
KOREA_THREADS = {"in-due-course", "korea", "chinese-intervention"}


def arc_of(thread_slug, date):
    if thread_slug not in KOREA_THREADS:
        return "wwii"
    return "wwii" if date <= KOREA_IN_WWII else "korea-war"


for _t in threads:
    cnt = {}
    for e in _t.get("events", []):
        ev = EVENTS.get(e.get("ev"))
        if not ev:
            continue
        a = arc_of(_t["slug"], ev["date"])
        cnt[a] = cnt.get(a, 0) + 1
    tot = sum(cnt.values()) or 1
    # 한 국면이 2할을 넘으면 그 국면에 세운다. 「조선」만 둘 다에 선다 —
    # 신탁통치에서 전쟁으로 이어지는 등뼈라 한쪽에 가둘 수 없다.
    _t["_arcs"] = sorted((a for a, n in cnt.items() if n / tot >= 0.2),
                         key=lambda a: -cnt[a])

# 첫 화면에 열리는 국면은 **첫 주제가 속한 국면**이다. 순서대로 첫 국면을 눌러 두면
# HTML 이 켜 둔 것과 JS 가 여는 것이 어긋나 한 번 깜빡인다.
_first_arc = (threads[0]["_arcs"] or [None])[0] if threads else None

arc_tabs = []
for _a in ARCS:
    _n = sum(1 for _t in threads if _a["key"] in _t["_arcs"])
    if not _n:
        continue
    arc_tabs.append(
        f'<button class="arc-tab" data-arc="{H.escape(_a["key"])}" '
        f'aria-pressed="{"true" if _a["key"] == _first_arc else "false"}">'
        f'{H.escape(_a["label"])}<i>{_n}</i></button>')

th_tabs, th_panes = [], []
for _i, _t in enumerate(threads):
    _on = "true" if _i == 0 else "false"
    # 다른 국면의 주제는 처음부터 접어 둔다. JS 가 켜기 전에 여섯이 다 보이면
    # 화면이 한 번 접혔다 펴진다.
    _hide = "" if _first_arc in _t["_arcs"] else " hidden"
    th_tabs.append(f'<button class="th-tab" data-th="{H.escape(_t["slug"])}" '
                   f'data-arcs="{H.escape(" ".join(_t["_arcs"]))}" '
                   f'aria-pressed="{_on}"{_hide}><b>{H.escape(_t["title"])}</b>'
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
        + (f'<p class="th-lead">{md(_t["lead"])}</p>'
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

# 문서철을 실제로 펴내거나 심사해 올린 기관의 낙관(落款) 같은 표시.
# 사진 로고를 그대로 쓰지 않는다 — 국기와 같은 원칙이다. 실물 인장을 흉내
# 내지 않고, 등폭 서체로 짧게 줄인 이름만 얇은 테두리 안에 둔다.
INST = {
    "frus": ("frus.svg", "미국 국무부 역사관실 — Foreign Relations of the United States"),
    "crest": ("crest.svg", "미국 중앙정보국 — CIA Records Search Tool(CREST)"),
    "nara": ("nara.svg", "미국 국립문서기록관리청 — 원본 기록군(Record Group)"),
    "mofa-jp": ("mofa-jp.svg", "일본 정부 문장(오동꽃) · 외무성 외교사료관 — 日本外交文書"),
}


def col_card(c):
    scans = "" if NO_SCANS else f" · 원본 지면 {c.get('_pages', 0)}면"
    # 그 문서를 쓴 쪽의 국기를 제목 옆에 단다. 문서철을 고를 때
    # 「누가 남긴 기록인가」가 제목 다음으로 먼저 알아야 할 것이다.
    fl = "".join(
        f'<svg viewBox="0 0 15 10" width="15" height="10" aria-hidden="true">{FLAGS[k]}</svg>'
        for k in (c.get("flags") or []) if k in FLAGS)
    inst = INST.get(c.get("group"))
    badge = (f'<img class="col-inst" src="inst-logos/{inst[0]}" alt="" '
             f'title="{H.escape(inst[1])}" loading="lazy">'
             if inst else '')
    return f"""<a class="col" href="{c['slug']}/">
      <div class="col-top"><h3>{H.escape(c['title'])}{f'<span class="col-fl">{fl}</span>' if fl else ''}</h3>
        <span class="n">{c['n']}건{scans}</span></div>
      <div class="period">{H.escape(c['period'])}</div>
      <p class="blurb">{H.escape(c['blurb'])}</p>
      <p class="hl">{md(c['highlight'])}</p>
      {f'<p class="wip">아직 옮기는 중 — {H.escape(c["wip"])}</p>' if c.get("wip") else ''}
      <div class="col-foot">
        <p class="src">{H.escape(c['source'])}<br>{H.escape(c['rights'])}</p>
        {badge}
      </div>
    </a>"""


# 문서철이 늘면서 한 줄로 죽 나열하면 무엇이 무엇인지 흐려진다. 주제(threads)
# 탭이 쓰는 「국면」과 같은 생각으로, 문서철도 두 시기로 갈라 각각에 소개를
# 붙인다. `collection_groups` 에 없는 문서철은 묶이지 않고 마지막에 그냥 붙는다.
GROUPS = site.get("collection_groups", [])
_grouped_slugs = set()
col_groups_html = []
for g in GROUPS:
    members = [c for c in built if c.get("group") == g["key"]]
    if not members:
        continue
    _grouped_slugs.update(c["slug"] for c in members)
    col_groups_html.append(f"""<div class="col-group">
      <h3>{H.escape(g['label'])}</h3>
      <p>{H.escape(g.get('lead',''))}</p>
      <div class="cols">{''.join(col_card(c) for c in members)}</div>
    </div>""")
_rest = [c for c in built if c["slug"] not in _grouped_slugs]
if _rest:
    col_groups_html.append(f'<div class="cols">{"".join(col_card(c) for c in _rest)}</div>')
cols_html = "".join(col_groups_html)

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
      <span><b>{SPAN}</b>{RANGE}</span>
    </div>
  </div>
</header>

<div class="wrap">
  <section class="threads">
    <div class="arc-tabs">{''.join(arc_tabs)}</div>
    <div class="th-tabs">{''.join(th_tabs)}</div>
    {''.join(th_panes)}
  </section>

  <section>
    {sec("collections", "문서철", "")}
    {cols_html}
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
// 위 칸은 국면이다. 국면을 고르면 그 아래 주제만 남고, 첫 주제가 열린다.
const tabs = [...document.querySelectorAll('.th-tab')];
const panes = [...document.querySelectorAll('.th-pane')];
const arcs = [...document.querySelectorAll('.arc-tab')];
const arcOf = t => (t.dataset.arcs || '').split(' ').filter(Boolean);

function showArc(key){{
  arcs.forEach(a => a.setAttribute('aria-pressed', a.dataset.arc === key));
  tabs.forEach(t => t.hidden = !arcOf(t).includes(key));
}}
function showThread(slug, push){{
  const hit = tabs.find(t => t.dataset.th === slug) || tabs[0];
  if (!hit) return;
  // 국면을 건너뛰고 주제 주소로 바로 들어올 수 있다. 그때는 그 주제가 속한
  // 국면을 대신 골라 준다. 안 그러면 열린 주제의 탭이 숨어 있게 된다.
  const cur = arcs.find(a => a.getAttribute('aria-pressed') === 'true');
  if (!cur || !arcOf(hit).includes(cur.dataset.arc)) showArc(arcOf(hit)[0]);
  tabs.forEach(t => t.setAttribute('aria-pressed', t === hit));
  panes.forEach(p => p.hidden = p.dataset.th !== hit.dataset.th);
  if (push) history.replaceState(null, '', '#thread=' + hit.dataset.th);
}}
arcs.forEach(a => a.addEventListener('click', () => {{
  showArc(a.dataset.arc);
  const first = tabs.find(t => !t.hidden);
  if (first) showThread(first.dataset.th, true);
}}));
tabs.forEach(t => t.addEventListener('click', () => showThread(t.dataset.th, true)));
const m = (location.hash || '').match(/thread=([\w-]+)/);
showThread(m ? m[1] : (tabs[0] && tabs[0].dataset.th), false);
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
