# 배포

정적 파일뿐이라 어디든 올라간다. 여기서는 GitHub Pages를 전제로 적는다.

```bash
# 1. 문서철마다 열람기 다시 만들기 (번역이 바뀌었을 때만)
for c in FRUS_1943_Cairo FRUS_1945_Yalta FRUS_1945_Korea 014.1.korea; do
  (cd $c && python3 pipeline/make_docs.py && python3 "../열람기/build.py" reading/collection.json)
done
(cd NDL_점령기자료 && python3 pipeline/make_docs.py \
   && python3 "../열람기/build.py" pid_9850431/reading/collection.json)

# 2. 썸네일 (면이 늘었을 때만)
for p in FRUS_1943_Cairo FRUS_1945_Yalta FRUS_1945_Korea 014.1.korea; do
  python3 "열람기/make_thumbs.py" $p/reading/collection.json
done
python3 "열람기/make_thumbs.py" NDL_점령기자료/pid_9850431/reading/collection.json

# 3. 사이트 조립
python3 "열람기/build_site.py" site.json --out _site
```

`_site/` 를 통째로 올리면 끝이다.

## 용량

| | |
|---|---|
| 열람기 + 썸네일 | **16MB** — 첫 화면과 목록에 필요한 전부 |
| 원본 지면 스캔 | 392MB — 확대해 볼 때만 받는다 |
| 합계 | **408MB** |

GitHub Pages 권장 한도는 저장소 1GB, 파일당 100MB다. 가장 큰 파일이 1MB 남짓이라
여유가 있다. 대역폭은 월 100GB 소프트 리밋.

**스캔 없이 가볍게 올리려면** `--no-scans` 를 붙인다. 16MB가 되고,
썸네일과 번역·영문 원문은 그대로 다 보인다. 확대 뷰어만 깨진다.

```bash
python3 "열람기/build_site.py" site.json --out _site --no-scans
```

## GitHub Pages

```bash
cd _site
git init && git add -A && git commit -m "조선 1943-1948"
git branch -M gh-pages
git remote add origin git@github.com:<계정>/<저장소>.git
git push -u origin gh-pages
```

저장소 Settings → Pages → Source 를 `gh-pages` 브랜치 루트로 지정한다.

`.nojekyll` 은 `build_site.py` 가 자동으로 넣는다 — 없으면 GitHub이 `_` 로 시작하는
폴더를 지워 버린다.

### 저장소를 아카이브로도 쓰려면

`_site/` 만 올리면 결과물만 남는다. **스크립트와 원자료까지 같이 올리는 편을 권한다** —
번역이 기계 번역이라 검증 가능성이 곧 신뢰도다. 그럴 때는 `_site` 를 서브모듈이나
별도 브랜치로 두고 본체는 `main` 에 둔다.

올리지 말아야 할 것:

```gitignore
_site/
**/pages/          # 스캔 원본은 용량이 커서 별도 관리
**/ocr/            # 재생성 가능
*.pdf              # 원본 PDF (46MB, 265MB)
**/raw/*.xml       # FRUS TEI 원본 (7~8MB, 다시 받으면 된다)
```

`thumbs/` 는 올려도 된다 (9MB, 재생성에 시간이 걸린다).

## 다른 곳

| | |
|---|---|
| **Cloudflare Pages** | 무료, 파일당 25MB. 대역폭 무제한이라 스캔까지 올릴 때 유리하다 |
| **Netlify** | 무료 100GB/월. 설정이 가장 단순하다 |
| **직접 호스팅** | `python3 -m http.server` 로도 그대로 돈다. 특별한 서버 설정이 없다 |

## 올리기 전에

- [ ] `site.json` 의 `repo` 와 `contact` 을 실제 값으로 고쳤는가
- [ ] **NDL IIIF 이용 안내**를 확인했는가 — https://dl.ndl.go.jp/ja/help_iiif
      NDL 계열 두 문서철(`014.1.korea`, `NDL_점령기자료`)의 스캔을 올리는 문제다
- [ ] 각 문서철 화면 위쪽의 출처 표시가 맞는가
- [ ] 랜딩 꼬리말의 소장기관 표시(`国立国会図書館 National Diet Library, JAPAN`)가 들어갔는가

마지막 두 개는 `build_site.py` 가 `site.json` 의 `rights` 항목에서 만든다.
문서철을 추가하면 그 항목도 채워야 한다.
