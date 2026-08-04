# NDL 「연합군 점령기 자료」 컬렉션에서 받은 자료

출처: 국립국회도서관(일본) 디지털컬렉션 — **Materials on the Allied Occupation of Japan**
컬렉션 URL: https://dl.ndl.go.jp/collections/A00016

---

## 컬렉션 개요

일본 국립국회도서관 헌정자료실이 공개한, 전후 일본 점령 관계 **미국 공문서** 자료군.

| 구분 | 건수 |
|---|---|
| 전체 | **157,246** |
| 로그인 없이 열람 가능 | **129,236** |
| 도서관·개인 송신 | 14 |
| 관내 한정 | 27,996 |

### 하위 자료군
- **RG331** — 연합국최고사령관총사령부(GHQ/SCAP) 문서
- **RG554** — 극동군사령부(GHQ/FEC) 문서
- **RG260** — 류큐열도 미국민정부 문서
- **RG243** — 미국 전략폭격조사단 문서
- 미국 국무부 문서
- 기타

### 조선 관련
키워드 `Korea` 검색 → **2,757건** (그중 **2,193건이 로그인 없이 열람 가능**)

극동군사령부 참모3부(G-3)의 조선 파일이 연속 편철되어 있다:
- `091 : File 1 Korea, Nov 1946 – 26 Apr 1948` (Entry44, Box 53, Folder 1) ← **아래에서 받음**
- `091 : File 2 Korea, 28 Apr 1948 – 31 Dec 1948` (Box 53, Folder 2)
- `091 : Korea, No. 15` (Box 6, Folder 1) — 1949.07~1950.02

---

## 받은 자료

### `pid_9850431/` — 091 : File 1 Korea, Nov 1946 – 26 Apr 1948

| 항목 | 값 |
|---|---|
| Persistent ID | `info:ndljp/pid/9850431` |
| URL | https://dl.ndl.go.jp/pid/9850431 |
| 문서군 | Records of General Headquarters Far East Command (극동군총사령부문서) |
| 부서 | Assistant Chief of Staff, G-3 (참모 제3부) |
| 편철 | Entry44 · Box 53 · Folder 1 |
| 수록 기간 | 1945.11 ~ 1948.04 |
| 분량 | **351 프레임** |
| **이용 조건** | **PDM (Public Domain Mark)** |
| 소장 표시 | 国立国会図書館 National Diet Library, JAPAN |

**파일**

| 경로 | 내용 |
|---|---|
| `091_File1_Korea_1946-11_1948-04.pdf` | 351쪽 스캔, 277MB |
| `pages/0001.jpg … 0351.jpg` | 페이지별 이미지 (폭 1600px, 265MB) — 번역 대조용 |
| `ocr/0001.txt … 0351.txt` | macOS Vision OCR 결과 (평균 신뢰도 0.931) |
| `documents.json` | 면 → 문서 경계 (66건) |
| `tr_docs/*.json` | 교정 영문 + 한국어 번역 + 메타데이터 (조각 단위) |
| `reading/reader.html` | **열람기** — 여기서 읽는다 |
| `manifest.json` | IIIF 매니페스트 (원본 메타데이터) |

**351면 = 66건이다.** 한 전문이 세 면에 걸치고 한 면에 두 문서가 실린다.
문서 경계는 NDL 메타데이터의 `dcndl:alternative`(NDL이 매긴 수록 문서 목록)를
근거로 찾았다. 자세한 것은 `pipeline/README.md`.

### 열람기

`pid_9850431/reading/reader.html`. 좌측 목록에서 건명·시기로 걸러내고,
한국어 번역과 영문 원문을 나란히 놓고 읽는다. 썸네일이나 본문의 면 표시를 누르면
스캔 원본이 열린다.

**화면은 공용이다** — `../열람기/`에 있고 FRUS 문서철과 같은 것을 쓴다.
새 문서철을 넣을 때 화면을 새로 만들지 않는다. 규격은 `../열람기/SCHEMA.md`.

`pages/`는 PDF와 내용이 같다. 번역문을 원본과 나란히 대조할 때 낱장이 편해서 함께 둔 것이며,
용량이 부담되면 지워도 된다 — `pipeline/ndl_download.py 9850431`로 다시 받을 수 있다.

**내용 성격**
표지에 `091. KOREA / NOVEMBER 1946 THRU 26 APRIL 1948`, `G-3 FILE Administration`, `TOP SECRET` 도장.
분홍색 전문 용지의 `INCOMING MESSAGE` 다수 — 발신·수신·전문번호 체계가 **기존 폴더의 `014.1.korea.pdf`와 동일한 계통**이다.

확인된 예 (프레임 3):
> `FAR EAST COMMAND / GENERAL HEADQUARTERS, U.S. ARMY FORCES, PACIFIC`
> `ADJUTANT GENERAL'S OFFICE · RADIO AND CABLE CENTER`
> **INCOMING MESSAGE** · TOP SECRET PRIORITY · **19 Mar 48**
> `FROM: CSGPO / TO: CINCFE / INFO: CG USAFIK / NR: WX 97877`
>
> "Shipment of dependents to Korea being terminated after 25 Mar sailing…
> **In light of United Nations Temporary Commission on Korea having taken action in regard to observing of a general election on 9 May** looking to the formation of a government for Korea and eventual troop withdrawal it has been deemed advisable to terminate further dispatch of dependents to Korea owing to **indeterminate future status of occupation forces** as a result of UN action."

즉 **기존 자료(1945.9~1946.4)가 끝나는 지점부터 이어지는 시기**를 덮는다.
`CG USAFIK`(하지)가 수신처로 계속 등장한다.

---

## 다운로드 방법

`ndl_download.py` — IIIF Image API 다운로더.

```bash
pip install img2pdf
python ndl_download.py <PID>
```

- **PDM 자료만 받는다.** 매니페스트의 `Access Restrictions`가 PDM이 아니면 중단한다.
- 원본은 3967×5467이라 351장이면 1GB에 육박한다. 폭 **1600px**로 축소해 받는다 — 타자기 문서는 이 정도면 충분히 읽힌다.
- 서버 부담을 줄이려고 **동시 요청 4개, 요청 간 0.15초** 간격을 둔다.

IIIF 매니페스트: `https://dl.ndl.go.jp/api/iiif/{PID}/manifest.json`

---

## ⚠️ 이용 조건

- 이 자료는 **PDM(퍼블릭 도메인)** 표시가 붙어 있다.
- 다만 NDL은 IIIF API 이용에 관한 별도 안내를 두고 있다:
  https://dl.ndl.go.jp/ja/help_iiif
- **상업적 배포(스팀 출시물 포함) 전에는 위 안내와 각 자료의 표시를 다시 확인할 것.**
- 소장기관 표시: `国立国会図書館 National Diet Library, JAPAN`
