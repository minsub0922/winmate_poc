# 수집 스크립트 (브라우저 콘솔용)

samsung.com/business 는 목록·스펙·특장점을 자바스크립트와 XHR 로 그린다. 컨테이너에서는 사이트에 직접 접속할 수 없어서(프록시 정책),
브라우저에서 `https://www.samsung.com/sec/business/` 아무 페이지를 연 상태로 아래 스크립트를 순서대로 실행해 같은 출처(same-origin)
API 를 호출하고, 결과를 `window.__*` 변수에 모았다. 실행 순서와 결과 변수:

| 순서 | 파일 | 하는 일 | 결과 변수 → raw 파일 |
|---|---|---|---|
| 1 | `01_categories.js` | 카테고리 목록 페이지 43개에서 분류 번호(dispClsfNo)·제목·상품 수 | `window.__cats` |
| 2 | `02_products_specs.js` | 상품 목록 API(`cxhr/pf/goodsList`), 필터별 소속, 옵션(모델), 스펙 API(`xhr/goods/getGoodsSpecList`), PDP 특장점(v1) | `window.__wkb` → `wkb_products.json`, `wkb_specs.json` |
| 3 | `05_extra_categories.js` | 업종 페이지가 링크하지만 1번 목록에 없던 솔루션 목록 8개(사이니지·시스템에어컨·TV/음향·모바일·프린팅 솔루션, 하만, 크롬북, XR) | `window.__wkb` 에 합침 |
| 4 | `06_filter_meta.js` | 목록 페이지 필터 패널의 공식 그룹명·라벨, 목록별 소속 상품 | `window.__fmeta` → `wkb_filter_meta.json` |
| 5 | `07_pdp_features_v2.js` | PDP 특장점 컴포넌트 파서 v2(지연 로딩 이미지 `data-src`, PC/MO 묶기, 제목·본문·면책 문구 분리, 캐러셀 항목) | `window.__feat2` → `wkb_features.json` |
| 6 | `03_page_queue.js` | 업종 17·솔루션/서비스 17·랜딩 9·도입사례·US 업종 페이지 목록 | `window.__pagesQueue` |
| 7 | `04_pages_v2.js` | 페이지 HTML 을 순서대로 펴서(h/p/a/img 블록) 저장 | `window.__pages2` → `wkb_pages_v2.json` |
| 8 | `08_transfer_gzip_b64.js` | 결과를 gzip+base64 로 묶는 헬퍼(브라우저 → 빌드 환경 전송용) | — |

요청 간격은 150~400 ms 로 두었다. robots.txt 가 막은 `samsung.aiibook.net`(e-카탈로그 뷰어)과 로그인 뒤 콘텐츠는 수집하지 않았다.
수집 시각: 2026-10-04 (KST 15:51~17:20).
