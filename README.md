# 다카야마 질점 가스가점 재고 (한국어)

[高山質店 販売春日店 재고](https://takayama78online.jp/shop/pages/b03_zaiko.aspx)를 한국어로 요약해 보여주는 GitHub Pages 사이트.

- `scrape.py` — 7개 카테고리(남성/여성 시계, 가방, 지갑, 소품, 주얼리, 악기)를 전부 수집 → `docs/data.json`
- `dict_ja_ko.json` — 일본어→한국어 용어 사전. 어색한 번역은 여기에 단어를 추가하면 다음 갱신부터 반영. 사전에 없는 가타카나는 자동 음역.
- `.github/workflows/update.yml` — 3시간마다 자동 갱신 (Actions 탭에서 수동 실행 가능)
- `docs/index.html` — 열 때마다 최신 `data.json`을 받아 카테고리 탭·검색·가격 정렬로 표시

로컬 실행: `python scrape.py` 후 `python -m http.server -d docs` → http://localhost:8000

Pages 설정: Settings → Pages → Branch `main`, 폴더 `/docs`.
