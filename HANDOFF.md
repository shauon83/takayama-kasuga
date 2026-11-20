# HANDOFF — takayama-kasuga (2026-11-20)

## 개요
高山質店 販売春日店(supplier=b03) 재고를 한국어로 요약해 보여주는 GitHub Pages 사이트.
- 사이트: https://shauon83.github.io/takayama-kasuga/
- 저장소: https://github.com/shauon83/takayama-kasuga (public, `main`, Pages = `/docs`)
- 로컬: `H:\Claude\takayama`

## 구조
| 파일 | 역할 |
|---|---|
| `scrape.py` | 7개 카테고리(tree 10,20,30,40,50,60,b0) 검색결과(ps=50, 페이지 반복) 수집 → 한국어 변환 → 환율·신품가 추가 → `docs/data.json`. `python scrape.py --test` = 자체 테스트만 |
| `dict_ja_ko.json` | 일본어→한국어 용어 사전(긴 단어부터 치환). 사전에 없는 가타카나는 `kata_to_hangul()` 음역 |
| `docs/index.html` | 정적 페이지. 열 때마다 `data.json?t=…` no-store 로 로드. 카테고리 탭·검색·가격 정렬·원화·신품가 % |
| `.github/workflows/update.yml` | 3시간마다(UTC cron) + 수동 실행. 변경 시 `docs/data.json`, `price_cache.json` 커밋 |
| `price_cache.json` | (키 등록 후 생성) 네이버 조회 캐시, 7일 후 재조회 |

`data.json`: `{updated:"YYYY-MM-DD HH:MM"(JST), jpykrw, count, items:[{code,title,brand,model,model_ko,ref,spec_ko,rank,price(JPY),img,new,soldout,cat,new_krw?,new_q?}]}`

## 결정 사항
- 원 사이트는 CORS 때문에 브라우저에서 직접 못 읽음 → Actions 주기 수집 방식 (실시간 아님, 최대 3시간 지연)
- 번역: Google 무료 엔드포인트는 차단, 비공식 번역 토큰은 사용 안 함 → 사전 + 음역 (외부 API 없음)
- 환율: Frankfurter(ECB) 키 불필요, 실패 시 직전 값 유지
- 신품가: 구글 검색 스크래핑은 약관 위반 → 네이버쇼핑 검색 API. productType 1~3(신품)이면서 제목에 정규화 품번 포함된 결과의 **중간값**. 품번 4자 미만은 생략. 실행당 조회 상한 3000

## 상태
- ✅ 수집·번역·원화 표시 배포 완료, Actions 실행 성공(GitHub 러너에서 원 사이트 접속 OK)
- ⏳ 네이버 신품가 비교: 코드 배포됨, **Secrets 미등록이라 비활성**. 목업 테스트만 통과, 실제 응답 검증 안 됨

## 다음 할 일
1. developers.naver.com 에서 앱 등록(검색 API) → `gh secret set NAVER_CLIENT_ID` / `gh secret set NAVER_CLIENT_SECRET` (`-R shauon83/takayama-kasuga`)
2. `gh workflow run update-inventory -R shauon83/takayama-kasuga` → 로그의 `naver 조회 N건`, 매칭 건수·오매칭 샘플 확인
3. 어색한 번역은 `dict_ja_ko.json` 에 단어 추가

## 주의
- 원 사이트 HTML(`StyleT_Item_`, `name1_0x_`, `price_ prc_`) 바뀌면 수집 깨짐. 0건이면 data.json 덮어쓰지 않고 실패 종료
- 로컬에서 push 전 `git pull --rebase` 필요(봇이 3시간마다 커밋)
- 등급(S~D) 설명은 일반적 의미, 원 사이트 공식 정의 미확인
