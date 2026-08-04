# GHQ/SCAP 014.1 Korea — 번역 규칙

## 자료 성격

**GHQ/SCAP Records (RG 331), Box AG-1, Folder 014.1 Korea, 1945.9 ~ 1947.1.**
연합국최고사령관총사령부 부관부(AG)가 편철한 조선 관계 문서철. 일본 국립국회도서관
헌정자료실 촬영본. 표지에 `TOP SECRET`.

**이건 외교문서가 아니라 군 지휘계통의 서류다.** 워싱턴(육군부·합참) ↔ 도쿄(맥아더)
↔ 경성(하지)이 주고받은 서한·전문·각서·지령이고, 원본 타자지에 접수 도장과
손글씨 결재가 그대로 남아 있다.

이미 번역해 둔 `../FRUS_1945_Korea`(국무부 외교문서)와 **같은 사건의 군 라인**이다.
예를 들어 FRUS d783은 여기 `2-B`(9월 24일자)와 **같은 문서**다 — 저쪽은 활자 정서본,
여기는 하지의 사령부에서 실제로 타자해 보낸 종이다.

## 작업

문서 하나를 읽고 `tr/<serial>.json` 하나를 쓴다. 어느 면이 어느 문서인지는
`raw/documents.json`에 이미 배정돼 있다.

## 출력 스키마

```json
{
  "serial": "2-B",
  "date": "1945-09-24",
  "date_note": "원문 표기 그대로. 미상이면 null",
  "doc_type": "서한 | 전문 | 각서 | 지령 | 라우팅 슬립 | 첨부물",
  "classification": "Top Secret",
  "from": "주한미군사령부(HQ USAFIK), APO 235",
  "to": "태평양미육군총사령관(CINCAFPAC)",
  "info": "참조 수신처. 없으면 null",
  "msg_nr": "CA 52443 · 없으면 null",
  "subject_en": "Conditions in Korea",
  "subject_ko": "조선의 정세",
  "summary_ko": "한 문장 요지",
  "key_points_ko": ["핵심 논점 3~10개"],
  "ko": "본문 한국어 번역 (마크다운)",
  "en": "OCR을 교정한 영문",
  "stamps_ko": ["접수 도장·손글씨 결재·회부 표시를 읽은 것"],
  "people": ["등장 실인물 — 원어와 한국어 병기"],
  "confidence": "high | medium | low",
  "notes": "번역자 주. 없으면 빈 문자열"
}
```

## OCR 교정

`ocr/NNNN.txt`는 macOS Vision 결과(평균 신뢰도 0.955)다. 본문은 대체로 정확하고
오류는 전형적인 OCR 혼동이다.

```
1s→is   1n→in   or→of   ot→of   tor→for   rnay→may
Kores→Korea   Ary→Army   INPO→INFO   CINCPE→CINCFE
SINGC/SWINCO→SWNCC   TROGG/CTGGG→TFGCG
```

**고칠 것과 고치지 말 것을 구분하라.**

- **고친다** — 위 같은 판독 오류.
- **고치지 않는다** — 원저자의 오타와 시대 표기. `WAROCS`(=WARCOS), `Summery`,
  `Affaris`, `emports` 같은 것. 그대로 두고 `notes`에 적어라.
- **숫자열은 '고치지' 마라.** 전문번호·문서번호·날짜·부대번호를 그럴듯하게
  바로잡으려 들지 마라. 읽은 그대로 두고 의심되면 `notes`에.
- 읽을 수 없는 대목은 영문 `[illegible]` / 한국어 `[판독불가]`. **지어내지 마라.
  아카이브 작업에서 가장 중요한 규칙이다.**

판단이 안 서면 `pages/NNNN.jpg` 원본 스캔을 직접 봐라.

## 번역 규칙

1. **직역에 가깝게.** 군 문서는 낱말 선택이 곧 지휘 의도다.
   `will`(~할 것) / `should`(~해야) / `may`(~해도 좋다)를 뭉개지 마라.
2. **본문의 쪽번호(`- 2 -`)는 옮기지 마라.** 면 구분은 열람기가 따로 한다.
3. **전문 머리(FROM/TO/INFO/NR/TOO/MCN)는 번역하지 말고 필드로 뽑아라.**
   본문에 다시 적지 마라.
4. **약어·기관**
   - `CINCAFPAC` 태평양미육군총사령관 · `SCAP` 연합국최고사령관
   - `CG USAFIK` 주한미군사령관(하지) · `CG XXIV CORPS` 제24군단장
   - `WARCOS` 육군참모총장 · `AGWAR` 육군부 부관감 · `WD` 육군부
   - `JCS` 합동참모본부 · `SWNCC` 국무·육군·해군 3부조정위원회
   - `AFPAC` 태평양미육군 · `APO 235` 군사우편번호 235
   - 문서번호(`JCS 1483/15`, `SWNCC 176/8`)는 **번역하지 말고 그대로.**
5. **지명은 한국어를 앞에, 원문 표기를 괄호에.**
   `경성(Keijo/Seoul)`, `인천(Jinsen)`, `부산(Fusan)`, `제주(Saishu)`
   원문이 일본식 음독을 쓴 것 자체가 사료다.
6. **인물** 첫 등장에 `하지(John R. Hodge)` 식 병기, 이후 한국어만.
7. **`trusteeship` 신탁통치 / `tutelage` 후견 / `military government` 군정 /
   `civil affairs` 민사** — 뒤섞지 마라.
8. **차별적 표현을 부드럽게 만들지 마라.** 이 문서철에는 `Japs` 같은 멸칭과
   조선인의 자치 능력을 낮춰 보는 서술이 나온다. 그대로 옮기고 `notes`에
   표기 사실을 적어라. **사료를 다듬는 것은 사료를 없애는 것이다.**
9. **추측 금지.** 원문에 없는 배경을 본문에 섞지 마라. 필요하면 `notes`에.

## 도장과 손글씨

이 자료의 값어치 절반은 여백에 있다. 본문 밖의 표시를 `stamps_ko`에 옮겨라.

```
GHQ AGO RECORDS 28 SEP 1945   → 접수 도장
Noted by CinC & C/S            → 총사령관·참모장 열람 표시
Returned to AG Records, 3 Oct 45 → 회부 기록
```

읽히지 않으면 `[판독불가]`. **없는 것을 지어내지 마라.**

## 라우팅 슬립·쪽지

본문 없이 회부 경로만 적힌 종이가 섞여 있다. 짧아도 버리지 말고
`doc_type: "라우팅 슬립"`으로 남겨라 — 누가 언제 봤는지가 기록이다.

## 주의

정확도가 매끄러움보다 중요하다. 확신이 없으면 `confidence`를 낮추고 `notes`에
이유를 적어라 — 그게 나중에 원본 대조 대상 목록이 된다.
