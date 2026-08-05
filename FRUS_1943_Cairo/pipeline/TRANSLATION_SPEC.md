# FRUS 1943 카이로·테헤란 회담 — 조선 관련 12건 번역 규칙

## 자료 성격

*Foreign Relations of the United States: Diplomatic Papers, The Conferences at
Cairo and Tehran, 1943*. 전체 576건 중 **조선이 나오는 12건**을 골랐다.

**스캔 OCR이 아니라 원본 TEI에서 뽑은 정본이다.** 판독 오류를 고칠 필요가 없다.
원문 그대로가 정본이니 영문을 임의로 다듬지 마라.

## 이 묶음의 핵심

카이로 선언의 **`in due course`**(적절한 절차를 거쳐)라는 문구가 만들어지는 과정이
초안째로 남아 있다.

| 문서 | 문안 |
|---|---|
| d307 미국 초안 | `at the earliest possible moment after the downfall of Japan` |
| d308 미국 수정안 | `at the proper moment after the downfall of Japan` |
| d309 영국 초안 (처칠 필적) | **`in due course`** |
| d343 최종 코뮈니케 | **`in due course`** |

**이 네 건은 문구 대조가 전부다.** 번역이 매끄러워지려고 표현을 통일해 버리면
자료의 값어치가 사라진다. 각각을 다르게, 원문 강도 그대로 옮겨라.

- `at the earliest possible moment` → **가능한 한 가장 이른 시점에**
- `at the proper moment` → **적절한 시점에**
- `in due course` → **적절한 절차를 거쳐** (관례역 「머지않아」로 눌러 쓰지 말 것.
  이 문구가 모호했다는 것 자체가 사건이다. `notes`에 원문을 반드시 병기하라.)

## 작업

`raw/dNNN.txt` 한 건을 읽고 `tr/dNNN.json` 한 건을 쓴다. 파일 하나에 문서 하나.

## 출력 스키마

```json
{
  "doc_id": "d309",
  "date": "1943-11-25",
  "date_note": "원문 표기 그대로. 미상이면 null, 추정이면 근거를 적는다",
  "doc_type": "코뮈니케 초안 | 회의록 | 각서 | 비망록 | 기록",
  "classification": "Secret 등. 없으면 null",
  "place": "Cairo | Tehran | Washington | 10 Downing Street …",
  "from": "작성자·발신",
  "to": "수신. 회의록이면 null",
  "participants": ["회의록일 때 참석자 — 원어와 한국어 병기"],
  "title_en": "British Draft of the Communiqué",
  "title_ko": "영국 측 코뮈니케 초안",
  "subject_ko": "한 문장 요지",
  "key_points_ko": ["핵심 논점 3~8개"],
  "ko": "본문 한국어 번역 (마크다운)",
  "notes_ko": ["각주 번역. 원문 번호를 [주1] 형태로 앞에 붙인다"],
  "people": ["등장 실인물 — 원어와 한국어 병기: Chiang Kai-shek 장제스"],
  "confidence": "high | medium | low",
  "notes": "번역자 주 — 애매했던 대목, 판단 근거. 없으면 빈 문자열"
}
```

## 번역 규칙

1. **영문은 손대지 않는다.** `en` 필드를 만들지 마라 — 원문은 `raw/`에 그대로 있고
   열람기가 그 파일을 직접 붙인다. 중복 저장하지 않는다.
2. **원문의 오탈자를 고치지 마라.** 예를 들어 d309(처칠 필적 초안)에는
   `ad greed`(= and greed), `in harmony with the United Nations` 같은 대목이 있다.
   **그대로 두고 `notes`에 적어라.** 초안이라는 증거다.
3. **직역에 가깝게.** 외교문서는 낱말 선택 자체가 사료다.
   "is determined that"을 "결의한다"로 옮기되 "약속한다"로 강화하지 마라.
4. **본문의 `[449면]` 표시는 그대로 둔다.** 원본 책 쪽수라 인용에 필요하다.
5. **각주 참조 `[주1]`도 본문 안에 그대로 둔다.**
6. **고유명사**
   - 인물: 첫 등장에 `장제스(Chiang Kai-shek)` 식으로 병기, 이후 한국어만.
     `Roosevelt 루스벨트`, `Churchill 처칠`, `Stalin 스탈린`, `Hopkins 홉킨스`,
     `Marshall 마셜`, `Harriman 해리먼`, `Bohlen 볼렌`, `Hurley 헐리`,
     `Madame Chiang 장 부인(쑹메이링)`
   - 기구: `합동참모본부(JCS)`, `연합참모본부(CCS)`, `태평양전쟁위원회(Pacific War Council)`
   - `trusteeship` → **신탁통치**, `tutelage` → **후견**. 둘을 뒤섞지 마라 —
     원문이 구분해 쓴다.
   - 지명: `Formosa 타이완(포모사)`, `Pescadores 펑후 제도`, `Manchuria 만주`
7. **회의록의 발언은 발언자를 살려서 옮긴다.** "대통령은 …라고 말했다" 형식을
   임의로 평서문으로 바꾸지 마라.
8. **추측 금지.** 원문에 없는 배경 설명을 본문에 섞지 마라. 필요하면 `notes`에.
9. 원문이 잘렸거나 읽을 수 없는 대목은 `[원문 결락]`. 지어내지 마라.
10. **차별적 표현을 부드럽게 만들지 마라.** 이 시대 문서에는 `Japs` 같은 멸칭과
    "조선인은 아직 자치 능력이 없다"(d545)는 서술이 나온다. 그대로 옮기고
    `notes`에 표기 사실을 적어라. 사료를 다듬는 것은 사료를 없애는 것이다.

## 긴 회의록 다루기

d238(35,000자)·d263(12,900자)은 회담 전체 회의록이고 조선은 그중 한 대목이다.
**그래도 전문을 번역한다** — 조선 대목만 떼면 그게 어떤 자리에서 나온 말인지
알 수 없게 된다. 다만 `key_points_ko`는 **조선·신탁통치·전후 처리에 관한 것을
앞에 놓아라.** 나머지(상륙작전 일정, 선박 배정 등)는 뒤로.

## 주의

정확도가 매끄러움보다 중요하다. 확신이 없으면 `confidence`를 낮추고 `notes`에
이유를 적어라 — 그게 나중에 원문 대조 대상 목록이 된다.

---

## 말투

`subject_ko`·`key_points_ko`·`notes` 의 말투는 `열람기/STYLE.md` 를 따른다.
**줄표(—)와 「자리」를 쓰지 마라.** 번역 본문(`ko`)과 원문(`ja`)에는 적용하지 않는다.
