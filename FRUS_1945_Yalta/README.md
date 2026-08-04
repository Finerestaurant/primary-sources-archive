# FRUS 1945 몰타·얄타 — 신탁통치 구두 양해

*Foreign Relations of the United States: Diplomatic Papers,
The Conferences at Malta and Yalta, 1945*

| 항목 | 값 |
|---|---|
| 전체 | 512건 |
| **조선 관련** | **4건** |
| 기간 | 1945.1 ~ 2 |
| 분량 | 약 28,000자 · 원본 지면 14면 |
| 출처 | https://history.state.gov/historicaldocuments/frus1945Malta |
| 이용 조건 | **미국 정부 저작물 — 퍼블릭 도메인** |

---

## 왜 이 4건인가

이미 번역해 둔 1945년 문서(`../FRUS_1945_Korea`, d771)에서 국무부가 이렇게 쓴다.

> 유일한 국제 양해는 **얄타에서 4개국 신탁통치에 관해 이루어진 구두 양해**뿐이다.

**그 구두 양해의 현장 기록이 여기 d393이다.** 문서로 서명된 협정이 아니라
루스벨트와 스탈린이 나눈 대화이고, 그래서 이후 3년 내내 「구두 양해」라고만 불린다.

| 문서 | 면 | 내용 |
|---|---|---|
| **d247** 브리핑북 | 358–361 | **`POST-WAR STATUS OF KOREA`** — 원본 지면에 절 제목이 따로 붙은 **조선 전용 문서**. 군사 점령과 잠정 국제 행정·신탁통치에 어느 나라가 참여할지 (Korea 46회) |
| **d393** 볼렌 회의록 | 766–771 | **루스벨트가 스탈린에게 조선 신탁통치를 꺼내는 자리.** 필리핀 사례를 들어 기간을 말하고, 스탈린이 외국 군대 주둔 여부를 묻는다 |
| d246 브리핑북 | 356–358 | 대중국 정책. 중국의 조선 지배·정치적 통제에는 반대한다는 대목 |
| d477 전보 | 952–953 | 헐리·장제스 회담 의제에 조선·만주 관련 소련–중국 관계 포함 |

**d247(회담 전 준비) → d393(회담 중 대화)** 의 순서를 이룬다.
얄타 이전에 이미 국무부가 조선의 점령과 신탁통치를 문서로 준비하고 있었다.

### 고르는 기준

원본 TEI XML에서 **`Korea`가 한 번이라도 나오는 문서 전부**다. 512건 중 5건이었는데
그중 **d512는 뺐다** — 130,664자가 전부 `Korea, postwar status, 358-361` 같은
쪽수 나열인 **권말 색인**이다.

---

## 파이프라인

`../FRUS_1943_Cairo`와 같다. 같은 TEI 방식이라 스크립트를 그대로 옮겨 왔고,
바꾼 것은 권 이름과 문서 목록뿐이다.

```
pipeline/frus_fetch.py        ① 원본 TEI XML → raw/dNNN.txt
pipeline/fix_pagemap.py       ② 면 번호를 인쇄 쪽번호로 맞춤
pipeline/frus_scans.py        ③ 원본 지면 → pages/
pipeline/TRANSLATION_SPEC.md  ④ 번역 규칙 (서브에이전트가 읽는다)
pipeline/make_docs.py         ⑤ → reading/docs.json
../열람기/build.py            ⑥ 화면 — 공용
```

```bash
cd pipeline
python3 frus_fetch.py
python3 fix_pagemap.py      # ← 반드시 scans 보다 먼저
python3 frus_scans.py
# ④ 번역은 서브에이전트에 위임 — TRANSLATION_SPEC.md 를 프롬프트로 준다
python3 make_docs.py
python3 "../../열람기/build.py" ../reading/collection.json
```

**순서 주의.** `frus_scans.py`는 `raw/pages.json`이 인쇄 쪽번호로 맞춰져 있어야
올바른 지면을 받는다. `frus_fetch.py`를 다시 돌리면 `pages.json`이 스캔 번호로
되돌아가므로, 그 뒤에는 반드시 `fix_pagemap.py`를 다시 돌려야 한다.

**화면은 공용이다.** 이 README 기준으로 `../열람기/`. 규격은 `../열람기/SCHEMA.md`.

---

## 이어지는 자료

```
FRUS 1943 Cairo      1943.11 ~ 12       "in due course" 가 만들어진다
FRUS 1945 Yalta      1945.01 ~ 02       ← 이 폴더. 신탁통치 구두 양해
FRUS 1945 v06        1945.02 ~ 09.26    그 양해를 근거로 정책이 짜인다
014.1.korea.pdf      1945.09 ~ 1947.01  군정 (미처리)
NDL pid_9850431      1946.11 ~ 1948.04  철군과 한국군 창설
```

카이로에서 만들어진 `in due course`가 얄타에서 **구체적인 신탁통치 구상**이 되고,
그것이 1945년 9월 이후 실제 정책의 근거가 된다. 세 문서철이 한 줄기다.

## ⚠️ 검증

한국어는 기계 번역이다. **인용 전에 반드시 원문과 대조할 것** —
열람기의 각 문서에 FRUS 원문 링크, 영문 정본, 원본 지면 스캔을 달아 두었다.

**차별적 표현을 다듬지 않았다.** 조선인의 자치 능력을 낮춰 보는 서술이 나오면
그대로 옮기고 각 문서의 `notes`에 표기 사실을 적었다.
사료를 다듬는 것은 사료를 없애는 것이다.
