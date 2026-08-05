# FRUS 1945 v06 「미국의 대한정책」 번역 규칙

## 자료 성격

미국 국무부 공식 외교문서집 *Foreign Relations of the United States, 1945, Volume VI*
제10장 1절 "Policies of the United States toward Korea" (문서 756–785, 1945.2.5 ~ 9.26).

**스캔 OCR이 아니라 이미 교정된 텍스트다.** 판독 오류를 고칠 필요가 없다.
원문 그대로가 정본이니 영문을 임의로 다듬지 말 것.

## 작업

`raw/dNNN.txt` 한 건을 읽고 `tr/dNNN.json` 한 건을 쓴다. 파일 하나에 문서 하나.

## 출력 스키마

```json
{
  "doc_id": "d771",
  "date": "1945-08-24",
  "date_note": "원문 표기 그대로. 날짜가 undated면 null, 추정이면 여기에 근거를 적는다",
  "doc_type": "각서 | 전보 | 서한 | 대화비망록 | 포고문 | 보고서",
  "classification": "Top Secret",
  "from": "국무·육군·해군 3부조정위원회(SWNCC)",
  "to": "합동참모본부(JCS)",
  "place": "Washington",
  "source_note": "원문 첫머리의 출처 표시 (예: Records of the State-War-Navy Coordinating Committee, Lot 52-M45)",
  "title_en": "Draft Memorandum to the Joint Chiefs of Staff",
  "title_ko": "합동참모본부 앞 각서 초안",
  "subject_ko": "한 문장 요지",
  "key_points_ko": ["핵심 논점 3~6개"],
  "ko": "본문 한국어 번역 (마크다운)",
  "notes_ko": ["각주 번역. 원문 각주 번호를 [주48] 형태로 앞에 붙인다"],
  "people": ["문서에 등장하는 실인물 — 원어와 한국어 병기: Syngman Rhee 이승만"],
  "confidence": "high | medium | low",
  "notes": "번역자 주 — 애매했던 대목, 판단 근거. 없으면 빈 문자열"
}
```

## 번역 규칙

1. **영문은 손대지 않는다.** `en` 필드를 만들지 마라 — 원문은 `raw/`에 그대로 있고,
   읽기 화면에서 그 파일을 직접 붙인다. 중복 저장하지 않는다.
2. **의역하지 말고 직역에 가깝게.** 외교문서는 낱말 선택 자체가 사료다.
   "it would be politically advisable"을 "정치적으로 바람직할 것"으로 옮기되
   "~해야 한다"로 강화하지 마라.
3. **본문의 `[1038면]` 표시는 그대로 둔다.** 원본 책 쪽수라 인용에 필요하다.
4. **각주 참조 `[주48]`도 본문 안에 그대로 둔다.**
5. **고유명사**
   - 인물: 첫 등장에 `이승만(Syngman Rhee)` 식으로 병기, 이후 한국어만
   - 기구: `국무·육군·해군 3부조정위원회(SWNCC)`, `합동참모본부(JCS)`,
     `태평양미육군총사령부(AFPAC)`, `주한미군사령부(USAFIK)`
   - 대한민국임시정부는 `대한민국임시정부(Korean Provisional Government)`
   - 지명은 당대 표기를 살리되 한국어를 우선: `경성(Seoul)`, `인천(Jinsen/Inchon)`
6. **전보 머리(FROM/TO/NR 등)는 번역하지 말고 `from`/`to`/`msg_nr` 필드로 뽑는다.**
   본문에 다시 적지 마라.
7. **추측 금지.** 원문에 없는 배경 설명을 본문에 섞지 마라.
   설명이 꼭 필요하면 `notes`에 적는다.
8. 읽을 수 없거나 원문이 잘린 대목은 `[원문 결락]`으로 표시한다. 지어내지 마라.

## 주의

이 자료는 게임 시나리오의 고증 자료로 쓴다. **정확도가 매끄러움보다 중요하다.**
확신이 없으면 `confidence`를 낮추고 `notes`에 이유를 적어라 — 그게 나중에
원문 대조 대상 목록이 된다.

---

## 말투

`subject_ko`·`key_points_ko`·`notes` 의 말투는 `열람기/STYLE.md` 를 따른다.
**줄표(—)와 「자리」를 쓰지 마라.** 번역 본문(`ko`)과 원문(`ja`)에는 적용하지 않는다.
