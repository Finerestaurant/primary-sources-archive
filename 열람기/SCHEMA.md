# 열람기 데이터 규격

열람기(`build.py`)는 **자료가 무엇인지 모른다.** 아래 두 파일만 읽는다.

```
collection.json   문서철 한 벌의 설명 — 제목·출처·칩·창 이름·스캔 위치
docs.json         정규화된 문서 목록
```

새 문서철을 넣을 때 열람기는 건드리지 않는다. 자료마다 다른 것은 **어댑터**
(`make_docs.py`)가 흡수해서 이 규격으로 바꿔 준다.

---

## collection.json

```json
{
  "title": "미국의 대한정책",
  "subtitle": "1945년 2월 5일 – 9월 26일 · FRUS 1945 VI 문서 756–785",
  "source": "출처 한 줄. 화면 위에 작게 깔린다",
  "search_hint": "한국어·영문·인물·기관 검색",

  "groups": [
    {"key": "A", "label": "각서·훈령"},
    {"key": "B", "label": "전보"}
  ],

  "panes": {
    "primary": "한국어 번역",
    "secondary": "영문 원문 · FRUS 정본",
    "both": "나란히"
  },

  "sorts": [
    {"key": "date", "label": "시간순"},
    {"key": "order", "label": "문서번호순"}
  ],

  "pages": {"dir": "../pages", "ext": "png", "label": "원본 지면",
            "thumbs": "../thumbs", "thumb_ext": "jpg"},

  "home": {"url": "../", "label": "조선 1943–1948"},

  "warn_text": "판독 신뢰도가 낮다. 원본 대조 필요."
}
```

| 항목 | 없으면 |
|---|---|
| `groups` | 칩 줄이 사라진다 |
| `panes.secondary` | 한국어/영문 전환 단추가 사라진다 |
| `pages` | **썸네일과 확대 뷰어가 통째로 빠진다.** 스캔이 없는 자료도 그대로 쓸 수 있다 |
| `pages.thumbs` | 목록이 원본을 그대로 받는다 — 느려진다. `make_thumbs.py` 참조 |
| `sorts` | 정렬 단추가 사라진다 (입력 순서 유지) |
| `home` | 좌측 위 「← 돌아가기」 링크가 사라진다. 문서철 하나만 따로 쓸 때 |

`groups[].key`는 `A`~`E`, `X` 중에서 고른다. 좌측 목록의 색 띠가 이 값에 붙어 있다.

---

## docs.json

문서 하나가 객체 하나. **`id` 말고는 전부 없어도 된다** — 없는 항목은 화면에서
그 줄이 통째로 빠진다. 자료에 없는 값을 지어내지 말고 그냥 비워 둘 것.

```json
[{
  "id": "d781",
  "order": 781,
  "date": "1945-09-15",
  "group": "E",

  "eyebrow": "d781 · The Political Adviser in Korea (Benninghoff) to the Secretary of State",
  "title": "주한 정치고문(베닝호프)이 국무장관에게, 제1호",
  "badge": "Top Secret",
  "list_right": "문서 781",

  "meta": [
    {"k": "일자", "v": "1945-09-15"},
    {"k": "발신", "v": "주한 정치고문 베닝호프", "txt": true},
    {"k": "참석", "v": "루스벨트, 스탈린, …", "txt": true, "wide": true}
  ],
  "links": [{"k": "FRUS", "text": "문서 781 원문", "url": "https://..."}],

  "summary": "한 문장 요지. 본문 위 상자에 들어간다",
  "points": ["핵심 논점", "…"],

  "primary": "한국어 본문",
  "secondary": "영문 원문",

  "notes": ["[주74] 각주 …"],
  "note": "번역자 주 한 줄",
  "warn": false,

  "pages": [1048, 1049, 1050],
  "search": "검색에만 걸리고 화면에는 안 나오는 말들"
}]
```

### 항목 뜻

| 이름 | 쓰임 |
|---|---|
| `id` | **필수.** 주소창 `#id`로 그 문서가 열린다 |
| `order` | 정렬용 숫자. 없으면 입력 순서 |
| `group` | `collection.json`의 칩 `key` |
| `eyebrow` | 제목 위 작은 등폭 글씨. 원제나 편철 위치 |
| `badge` | 제목 옆 도장. 기밀등급처럼 눈에 띄어야 하는 한 낱말 |
| `list_right` | 좌측 목록의 오른쪽 끝 (`문서 781`, `12–19면`) |
| `meta` | 표 형태. `txt: true`면 등폭이 아니라 본문 서체로, `wide: true`면 한 줄을 통째로 쓴다 (참석자 명단처럼 긴 값) |
| `links` | `meta` 아래에 링크로 붙는다 |
| `primary` / `secondary` | 두 창의 본문. 마크다운은 `**굵게**` `~~취소선~~`만 |
| `warn` | 참이면 `warn_text`가 빨갛게 붙는다 |
| `pages` | 썸네일·확대 뷰어에 쓸 면 번호. 파일 이름은 `{dir}/{면}.{ext}` |

### 본문 안 표시

두 가지가 특별 취급된다. 나머지는 그대로 나온다.

| 쓰는 법 | 결과 |
|---|---|
| `[1050면]` | 눌러서 그 면의 원본을 여는 구분선 |
| `[주74]` | 각주 참조 위첨자 |

`pages`가 없는 자료에서는 `[1050면]`이 그냥 구분선으로만 남는다.

---

## 새 문서철 넣기

```
새자료/
  pipeline/make_docs.py     ← 이것만 새로 쓴다
  reading/collection.json
  reading/docs.json         ← make_docs.py 가 만든다
  pages/                    ← 스캔이 있으면
```

```bash
python3 pipeline/make_docs.py                       # 자료 → docs.json
python3 ../열람기/build.py reading/collection.json  # → reading/reader.html
```
