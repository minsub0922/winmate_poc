# 화면 색인 (아티팩트 원본 보드)

오프라인으로 보는 법 · 그린 화면(`_rendered/`)은 [README.md](README.md).

> **조감도(birdseye) 최신안은 `BP*`(2D 조감도 4단계 + 내보내기) · `BR*`(3D 조감도 3단계 + 내보내기)** 다(2026-10-07 아티팩트 기준).
> 옛 `BE1`–`BE6` 흐름은 아티팩트에서 빠졌지만 참고용으로 남겨 둔다 — 새로 만들거나 고칠 때는 BP · BR 을 따른다. `BE0`(작업 목록 · 2D/3D 유형 선택) · `UC_BE` 는 그대로 쓴다.
> 웹앱 ③ 의 PRQ · PRS · PRX · *Layout* 보드와 `Stepper` · `Thumb` 는 이제 각자 `.dc.html` 파일로 있다(전에는 다른 파일 안의 변형).

> **웹앱 ① 은 2026-10-08 에 콘텐츠 흐름을 처음부터 다시 그렸다(Storyboard 중심 · 사전 작업 · 완료 JSON · DSS 신규 · VP 가치 · 고객의 니즈 · 공간 → 시나리오 → 장면).**
> 정본은 `webapp1/`(아티팩트 v58 사본)이고, 규칙은 `docs/scenarios/11-content-flow.md` 가 정본이다. 그 전 웹앱 ① 보드(RQ1~RQ7 · SB1~SB5 · MI1~MI4 · CA1~CA5 · VP1~VP4 · SP1~SP4 등)는
> `_archive/webapp1-v52/` · `_rendered/_archive/webapp1-v52/` 에 참고용으로만 남긴다 — **새로 만들거나 고칠 때는 따르지 않는다.**
> 웹앱 ② 의 SC0~SC5(옛 공간 시나리오)도 새 흐름(웹앱 ① SC0 · SC1 · SC2)으로 대체됐다. 웹앱 ② 의 이미지 · 조감도는 그대로다.

| 웹앱 | 보드 | 제목 | 페이지 | 기능(서비스) |
|---|---|---|---|---|
| webapp1 | `Main` | 홈 |  | shell |
| webapp1 | `HomeProduct` | 홈 — 제품 탐색 (디렉토리 탐색기) |  | shell |
| webapp1 | `HomeSolution` | 홈 — 솔루션 탐색 |  | shell |
| webapp1 | `HomeImage` | 홈 — 이미지 검색 |  | shell |
| webapp1 | `HomeCase` | 홈 — 유관 사례 검색 |  | shell |
| webapp1 | `ProductInput` | 공통 제품 입력 컴포넌트 |  | shell |
| webapp1 | `Sidebar` | 컴포넌트 · 사이드바 |  | shell |
| webapp1 | `TopBar` | 컴포넌트 · 상단 액션바 (팝오버 4종 내장) |  | shell |
| webapp1 | `Stepper` | 컴포넌트 · 스텝바 |  | shell |
| webapp1 | `HomeGrid` | 컴포넌트 · 홈 그리드 |  | shell |
| webapp1 | `Thumb` | 컴포넌트 · 템플릿 썸네일 (kind · n) |  | shell |
| webapp1 | `Guide` | Winmate 캔버스 안내 | 웹앱 · 홈 · 공통 컴포넌트 | shell |
| webapp1 | `HomeProductDetail` | 상세 보기 — QM55C 스펙 · 공식 자료 | 웹앱 · 홈 · 공통 컴포넌트 | shell |
| webapp1 | `HomeProductImages` | 상세 보기 — QM55C 이미지 8 · 출처 메타데이터 | 웹앱 · 홈 · 공통 컴포넌트 | shell |
| webapp1 | `HomeProductCases` | 상세 보기 — QM55C 활용 사례 (용도 일치) | 웹앱 · 홈 · 공통 컴포넌트 | shell |
| webapp1 | `HomeSolutionDetail` | 상세 보기 — MagicINFO 개요 · 구성 | 웹앱 · 홈 · 공통 컴포넌트 | shell |
| webapp1 | `HomeSolutionImages` | 상세 보기 — MagicINFO 이미지 9 · 출처 메타데이터 | 웹앱 · 홈 · 공통 컴포넌트 | shell |
| webapp1 | `HomeSolutionCases` | 상세 보기 — MagicINFO 활용 사례 17 | 웹앱 · 홈 · 공통 컴포넌트 | shell |
| webapp1 | `ProductDetail` | 컴포넌트 · 제품 상세 시트 (tab: spec · images · cases) | 웹앱 · 홈 · 공통 컴포넌트 | shell |
| webapp1 | `SolutionDetail` | 컴포넌트 · 솔루션 상세 시트 (tab: overview · images · cases) | 웹앱 · 홈 · 공통 컴포넌트 | shell |
| webapp1 | `SBBar` | 컴포넌트 · 연결된 Storyboard 바 |  | shell(공통 흐름) |
| webapp1 | `SBPopup` | 컴포넌트 · Storyboard 요약 팝업 |  | shell(공통 흐름) |
| webapp1 | `Gate` | 컴포넌트 · 사전 작업 Storyboard 고르기 (content) |  | shell(공통 흐름) |
| webapp1 | `Done` | 컴포넌트 · 완료 · Storyboard 갱신 · 후속 작업 (content) |  | shell(공통 흐름) |
| webapp1 | `List` | 컴포넌트 · 콘텐츠 목록 (content) |  | shell(공통 흐름) |
| webapp1 | `RQ0` | 요구사항 · 목록 | 웹앱 · 고객 요구사항 | requirements |
| webapp1 | `RQ1` | 요구사항 · 입력 | 웹앱 · 고객 요구사항 | requirements |
| webapp1 | `RQ1_AI` | 요구사항 · AI 심층 질의 (추가기능) | 웹앱 · 고객 요구사항 | requirements |
| webapp1 | `RQ_Done` | 요구사항 · 완료 · Storyboard 자동 생성 · 후속 DSS | 웹앱 · 고객 요구사항 | requirements |
| webapp1 | `FlowRule` | 콘텐츠 흐름 규칙 | 웹앱 · 전략 수립 Storyboard | storyboard |
| webapp1 | `SB0` | Storyboard 목록 · 어디까지 입력됐나 | 웹앱 · 전략 수립 Storyboard | storyboard |
| webapp1 | `SB1` | Storyboard · 연결 콘텐츠 · 요약본 md | 웹앱 · 전략 수립 Storyboard | storyboard |
| webapp1 | `SB1_Json` | Storyboard · 전체 흐름 JSON | 웹앱 · 전략 수립 Storyboard | storyboard |
| webapp1 | `DS0` | DSS · 목록 | 웹앱 · 공간별 제품 매칭 DSS | dss(신규) |
| webapp1 | `DS1` | DSS · 사전 작업 · Storyboard 고르기 | 웹앱 · 공간별 제품 매칭 DSS | dss(신규) |
| webapp1 | `DS2` | DSS · 공간 · 제품 (업종 · 공간 · 공간별 제품 한 화면) | 웹앱 · 공간별 제품 매칭 DSS | dss(신규) |
| webapp1 | `DS4` | DSS · 솔루션 (0개 이상) | 웹앱 · 공간별 제품 매칭 DSS | dss(신규) |
| webapp1 | `DS_Done` | DSS · 완료 · 후속 시나리오 · Spec | 웹앱 · 공간별 제품 매칭 DSS | dss(신규) |
| webapp1 | `DS2_AI` | DSS · AI 업종 추론 · 공간 추천 · 제품 자동 매칭 | 웹앱 · 공간별 제품 매칭 DSS | dss(신규) |
| webapp1 | `DS4_AI` | DSS · AI 솔루션 추천 | 웹앱 · 공간별 제품 매칭 DSS | dss(신규) |
| webapp1 | `MI0` | MI · 목록 | 웹앱 · Market Intelligence | mi |
| webapp1 | `MI1` | MI · 사전 작업 · 이미 있으면 수정 | 웹앱 · Market Intelligence | mi |
| webapp1 | `MI2` | MI · 검색 (AI가 Storyboard 분석 후 표시) | 웹앱 · Market Intelligence | mi |
| webapp1 | `MI3` | MI · 정제 | 웹앱 · Market Intelligence | mi |
| webapp1 | `MI_Done` | MI · 완료 | 웹앱 · Market Intelligence | mi |
| webapp1 | `MI1_Branch` | MI · 사전 작업 · 복제본(분기) 고르기 | 웹앱 · Market Intelligence | mi |
| webapp1 | `CA0` | 경쟁사 분석 · 목록 | 웹앱 · 경쟁사 분석 | competitor |
| webapp1 | `CA1` | 경쟁사 분석 · 사전 작업 | 웹앱 · 경쟁사 분석 | competitor |
| webapp1 | `CA2` | 경쟁사 분석 · 리스트업 · 제안 기준 비교 (스펙 · 가격 · 사례 · ESG · 브랜드) | 웹앱 · 경쟁사 분석 | competitor |
| webapp1 | `CA_Done` | 경쟁사 분석 · 완료 | 웹앱 · 경쟁사 분석 | competitor |
| webapp1 | `CA2_AI` | 경쟁사 분석 · AI 후보군 웹 탐색 · 후보 비교 | 웹앱 · 경쟁사 분석 | competitor |
| webapp1 | `VP0` | VP · 목록 | 웹앱 · Value Proposition | vp |
| webapp1 | `VP1` | VP · 사전 작업 | 웹앱 · Value Proposition | vp |
| webapp1 | `VP2` | VP · 제품 · 솔루션별 가치 여러 개 · 고객의 니즈 | 웹앱 · Value Proposition | vp |
| webapp1 | `VP_Done` | VP · 완료 | 웹앱 · Value Proposition | vp |
| webapp1 | `VP2_AI` | VP · AI 가치 매칭 추천 · 니즈 추론 (점선 → 수락) | 웹앱 · Value Proposition | vp |
| webapp1 | `SP0` | Spec 시트 · 목록 | 웹앱 · Spec 시트 생성 | spec |
| webapp1 | `SP1` | Spec 시트 · 사전 작업 | 웹앱 · Spec 시트 생성 | spec |
| webapp1 | `SP2` | Spec 시트 · 시트 작성 | 웹앱 · Spec 시트 생성 | spec |
| webapp1 | `SP_Done` | Spec 시트 · 완료 | 웹앱 · Spec 시트 생성 | spec |
| webapp1 | `SC0` | 공간 시나리오 · 목록 | 웹앱 · 공간 시나리오 생성 | scenario |
| webapp1 | `SC1` | 공간 시나리오 · 사전 작업 | 웹앱 · 공간 시나리오 생성 | scenario |
| webapp1 | `SC2` | 공간 시나리오 · 공간 → 시나리오 → 장면 · 공간 / 시나리오별 제품 · 솔루션 | 웹앱 · 공간 시나리오 생성 | scenario |
| webapp1 | `SC_Done` | 공간 시나리오 · 완료 | 웹앱 · 공간 시나리오 생성 | scenario |
| webapp1 | `SC2_AI` | 공간 시나리오 · AI 3안 (후보를 시나리오 목록에 · 수락) | 웹앱 · 공간 시나리오 생성 | scenario |
| webapp1 | `ContentPopup` | 컴포넌트 · 연결된 콘텐츠 보기 팝업 (refId) |  | shell(공통 흐름) |
| webapp1 | `SB1_View` | Storyboard · 연결 콘텐츠 보기 팝업 (페이지 이동 없음) | 웹앱 · 전략 수립 Storyboard | storyboard |
| webapp1 | `SB1_Strat` | Storyboard · 전략 수립 팝업 (페이지 이동 없음) | 웹앱 · 전략 수립 Storyboard | storyboard |
| webapp1 | `SB1_StratAI` | Storyboard · 전략 수립 팝업 · AI 후보 3안 | 웹앱 · 전략 수립 Storyboard | storyboard |
| webapp1 | `StrategyPopup` | 컴포넌트 · 전략 수립 팝업 (ai) |  | shell(공통 흐름) |
| webapp1 | `MI2_Loading` | MI · Storyboard 고른 뒤 AI 분석 로딩 | 웹앱 · Market Intelligence | mi |
| webapp1 | `MI_DoneJson` | MI · 완료 · flow.json 전체 (출처 · 정리 내용 포함) | 웹앱 · Market Intelligence | mi |
| webapp1 | `JsonPopup` | 컴포넌트 · flow.json 전체 보기 팝업 |  | shell(공통 흐름) |
| webapp1 | `CA2_Info` | 경쟁사 분석 · 개요 탭 · 위키 메타 · 선별 기준 | 웹앱 · 경쟁사 분석 | competitor |
| webapp1 | `CA2_Pc` | 경쟁사 분석 · 장단점 탭 · 삼성 대비 · 주장 포인트 | 웹앱 · 경쟁사 분석 | competitor |
| webapp1 | `CA_DoneJson` | 경쟁사 분석 · 완료 · flow.json 전체 (메타 · 비교 · 장단점 포함) | 웹앱 · 경쟁사 분석 | competitor |
| webapp1 | `VP2_Pick` | VP · 제품 · 솔루션 고르기 팝업 | 웹앱 · Value Proposition | vp |
| webapp1 | `VP2_Detail` | VP · 연결된 가치 전체 보기 팝업 (이 제안 + 다른 제안) | 웹앱 · Value Proposition | vp |
| webapp1 | `VP_DoneJson` | VP · 완료 · flow.json 전체 (가치 · 니즈) | 웹앱 · Value Proposition | vp |
| webapp1 | `SC2_Pick` | 공간 시나리오 · 공간 제품 · 솔루션 고르기 (1개 이상) | 웹앱 · 공간 시나리오 생성 | scenario |
| webapp1 | `SC2_Empty` | 공간 시나리오 · 시나리오 없는 공간 (주차장) | 웹앱 · 공간 시나리오 생성 | scenario |
| webapp1 | `SC_DoneJson` | 공간 시나리오 · 완료 · flow.json 전체 | 웹앱 · 공간 시나리오 생성 | scenario |
| webapp1 | `ProdPicker` | 컴포넌트 · 제품 · 솔루션 고르기 팝업 (picked · min) |  | shell(공통 흐름) |
| webapp1 | `VpDetail` | 컴포넌트 · VP 연결된 가치 전체 팝업 |  | vp |
| webapp2 | `UC_BE` | 조감도 · 유스케이스 맵 | 웹앱 · 공간 조감도 생성 | birdseye |
| webapp2 | `BE0` | 조감도 · 작업 목록 | 웹앱 · 공간 조감도 생성 | birdseye |
| webapp2 | `BE1` | 조감도 1/5 · 공간 입력 | 웹앱 · 공간 조감도 생성 | birdseye |
| webapp2 | `BE2` | 조감도 2/5 · 배치될 제품 | 웹앱 · 공간 조감도 생성 | birdseye |
| webapp2 | `BE3` | 조감도 3/5 · 가구 추천 | 웹앱 · 공간 조감도 생성 | birdseye |
| webapp2 | `BE4` | 조감도 4/5 · 배치·인테리어 컨펌 | 웹앱 · 공간 조감도 생성 | birdseye |
| webapp2 | `BE5` | 조감도 5/5 · 3D 조감도 생성 | 웹앱 · 공간 조감도 생성 | birdseye |
| webapp2 | `BE1D` | 조감도 · 도면 인식 확인 | 웹앱 · 공간 조감도 생성 | birdseye |
| webapp2 | `BE1P` | 조감도 · 현장 사진으로 입력 | 웹앱 · 공간 조감도 생성 | birdseye |
| webapp2 | `BE5G` | 조감도 · 생성 중 | 웹앱 · 공간 조감도 생성 | birdseye |
| webapp2 | `BE4E` | 조감도 · 배치 직접 수정 | 웹앱 · 공간 조감도 생성 | birdseye |
| webapp2 | `BE5V` | 조감도 · 시점 · 조명 바꾸기 | 웹앱 · 공간 조감도 생성 | birdseye |
| webapp2 | `BE5Z` | 조감도 · 존 포인트 지정 | 웹앱 · 공간 조감도 생성 | birdseye |
| webapp2 | `BE6` | 조감도 · 내보내기 · 보내기 | 웹앱 · 공간 조감도 생성 | birdseye |
| webapp2 | `BP1` | 2D 조감도 1/4 · 공간 · 치수 | 웹앱 · 공간 조감도 생성 (2D · 3D) | birdseye |
| webapp2 | `BP2` | 2D 조감도 2/4 · 제품 · 수량 | 웹앱 · 공간 조감도 생성 (2D · 3D) | birdseye |
| webapp2 | `BP3` | 2D 조감도 3/4 · 배치 · 동선 | 웹앱 · 공간 조감도 생성 (2D · 3D) | birdseye |
| webapp2 | `BP4` | 2D 조감도 4/4 · 완성 | 웹앱 · 공간 조감도 생성 (2D · 3D) | birdseye |
| webapp2 | `BP5` | 2D 조감도 · 내보내기 · 보내기 | 웹앱 · 공간 조감도 생성 (2D · 3D) | birdseye |
| webapp2 | `BP1D` | 2D 조감도 · 도면 인식 확인 | 웹앱 · 공간 조감도 생성 (2D · 3D) | birdseye |
| webapp2 | `BP3Z` | 2D 조감도 · 존 구획 · 동선 순서 | 웹앱 · 공간 조감도 생성 (2D · 3D) | birdseye |
| webapp2 | `BR1` | 3D 조감도 1/3 · 요구사항 | 웹앱 · 공간 조감도 생성 (2D · 3D) | birdseye |
| webapp2 | `BR2` | 3D 조감도 2/3 · AI 구성 · 렌더링 | 웹앱 · 공간 조감도 생성 (2D · 3D) | birdseye |
| webapp2 | `BR3` | 3D 조감도 3/3 · 결과 | 웹앱 · 공간 조감도 생성 (2D · 3D) | birdseye |
| webapp2 | `BR4` | 3D 조감도 · 내보내기 · 보내기 | 웹앱 · 공간 조감도 생성 (2D · 3D) | birdseye |
| webapp2 | `BR1P` | 3D 조감도 · 현장 사진으로 | 웹앱 · 공간 조감도 생성 (2D · 3D) | birdseye |
| webapp2 | `BR3V` | 3D 조감도 · 시점 · 조명 컷 | 웹앱 · 공간 조감도 생성 (2D · 3D) | birdseye |
| webapp2 | `UC_IMG` | 이미지 생성 · 유스케이스 맵 | 웹앱 · 이미지 생성 | image |
| webapp2 | `IMG0` | 이미지 생성 · 작업 목록 · 갤러리 | 웹앱 · 이미지 생성 | image |
| webapp2 | `IMG1` | 이미지 생성 1/3 · 이미지 유형 | 웹앱 · 이미지 생성 | image |
| webapp2 | `IMG2` | 이미지 생성 2/3 · 상세 조건 | 웹앱 · 이미지 생성 | image |
| webapp2 | `IMG3` | 이미지 생성 3/3 · 생성 결과 | 웹앱 · 이미지 생성 | image |
| webapp2 | `IMG2R` | 이미지 생성 · 참조 이미지 고르기 | 웹앱 · 이미지 생성 | image |
| webapp2 | `IMG2P` | 이미지 생성 · 현장 사진 제품 합성 | 웹앱 · 이미지 생성 | image |
| webapp2 | `IMG3G` | 이미지 생성 · 생성 중 | 웹앱 · 이미지 생성 | image |
| webapp2 | `IMG3X` | 이미지 생성 · 생성 실패 · 제한 안내 | 웹앱 · 이미지 생성 | image |
| webapp2 | `IMG3E` | 이미지 생성 · 부분 수정 | 웹앱 · 이미지 생성 | image |
| webapp2 | `IMG3V` | 이미지 생성 · 변형 · 비율 · 해상도 | 웹앱 · 이미지 생성 | image |
| webapp2 | `IMG4` | 이미지 생성 · 내보내기 · 제안서에 넣기 | 웹앱 · 이미지 생성 | image |
| webapp2 | `UC_SC` | 시나리오 · 유스케이스 맵 | 웹앱 · 공간 시나리오 생성 | scenario |
| webapp2 | `SC0` | 시나리오 · 작업 목록 | 웹앱 · 공간 시나리오 생성 | scenario |
| webapp2 | `SC1` | 시나리오 1/4 · 유형 선택 (with/without 솔루션) | 웹앱 · 공간 시나리오 생성 | scenario |
| webapp2 | `SC2` | 시나리오 2/4 · 공간 시나리오 입력 | 웹앱 · 공간 시나리오 생성 | scenario |
| webapp2 | `SC3` | 시나리오 3/4 · 솔루션·제품 입력 | 웹앱 · 공간 시나리오 생성 | scenario |
| webapp2 | `SC4` | 시나리오 4/4 · 시나리오 생성 | 웹앱 · 공간 시나리오 생성 | scenario |
| webapp2 | `SC1T` | 시나리오 · 업종 템플릿에서 시작 | 웹앱 · 공간 시나리오 생성 | scenario |
| webapp2 | `SC1B` | 시나리오 · 조감도에서 이어 만들기 | 웹앱 · 공간 시나리오 생성 | scenario |
| webapp2 | `SC3R` | 시나리오 · 장면별 솔루션 추천 | 웹앱 · 공간 시나리오 생성 | scenario |
| webapp2 | `SC4G` | 시나리오 · 생성 중 | 웹앱 · 공간 시나리오 생성 | scenario |
| webapp2 | `SC2E` | 시나리오 · 타임라인 · 페르소나 편집 | 웹앱 · 공간 시나리오 생성 | scenario |
| webapp2 | `SC4E` | 시나리오 · 장면 편집 | 웹앱 · 공간 시나리오 생성 | scenario |
| webapp2 | `SC5` | 시나리오 · 제안서로 보내기 · 내보내기 | 웹앱 · 공간 시나리오 생성 | scenario |
| webapp2 | `Sidebar` | 컴포넌트 · 사이드바 | 공통 컴포넌트 (웹앱 ①과 같은 파일) | shell |
| webapp2 | `Stepper` | 컴포넌트 · 스텝바 | 공통 컴포넌트 (웹앱 ①과 같은 파일) | shell |
| webapp2 | `TopBar` | 컴포넌트 · 상단 액션바 (팝오버 4종 내장) | 공통 컴포넌트 (웹앱 ①과 같은 파일) | shell |
| webapp2 | `Guide` | Winmate 캔버스 안내 | 안내 · 캔버스 8개 | shell |
| webapp3 | `UC_PR` | B2B 제안서 · 유스케이스 맵 | 제안서 · 시작 · 기본 흐름 · 섹션 작성 | proposal |
| webapp3 | `PR0` | B2B 제안서 · 제안서 목록 | 제안서 · 시작 · 기본 흐름 · 섹션 작성 | proposal |
| webapp3 | `PR1F` | B2B 제안서 · RFP로 시작 | 제안서 · 시작 · 기본 흐름 · 섹션 작성 | proposal |
| webapp3 | `PR1L` | B2B 제안서 · 기존 작업에서 시작 | 제안서 · 시작 · 기본 흐름 · 섹션 작성 | proposal |
| webapp3 | `PR1C` | B2B 제안서 · 기존 제안서로 시작 (목록 · PPTX · PDF) | 제안서 · 시작 · 기본 흐름 · 섹션 작성 | proposal |
| webapp3 | `PR3I` | B2B 제안서 · 업종 레이아웃 적용 | 제안서 · 시작 · 기본 흐름 · 섹션 작성 | proposal |
| webapp3 | `PR1` | 제안서 1/6 · 고객·프로젝트 정보 | 제안서 · 시작 · 기본 흐름 · 섹션 작성 | proposal |
| webapp3 | `PR2` | 제안서 2/6 · 제안서 유형 (표준 · 퀵윈 · Solution형) | 제안서 · 시작 · 기본 흐름 · 섹션 작성 | proposal |
| webapp3 | `PR3` | 제안서 3/6 · 시트 구성 — 표준 (MI 펼침) | 제안서 · 시작 · 기본 흐름 · 섹션 작성 | proposal |
| webapp3 | `PR3SolOpen` | 제안서 3/6 · 시트 구성 — 표준 · 솔루션 제안 펼침 (솔루션별 전용 3장) | 제안서 · 시작 · 기본 흐름 · 섹션 작성 | proposal |
| webapp3 | `PR3Quick` | 제안서 3/6 · 시트 구성 — 퀵윈(제품) | 제안서 · 시작 · 기본 흐름 · 섹션 작성 | proposal |
| webapp3 | `PR3Solution` | 제안서 3/6 · 시트 구성 — Solution형 | 제안서 · 시작 · 기본 흐름 · 섹션 작성 | proposal |
| webapp3 | `PR6` | 제안서 5/6 · 디자인 템플릿 | 제안서 · 시작 · 기본 흐름 · 섹션 작성 | proposal |
| webapp3 | `PR7` | 제안서 6/6 · PPTX 생성 | 제안서 · 시작 · 기본 흐름 · 섹션 작성 | proposal |
| webapp3 | `PRS1` | 표준 1/8 · Market Intelligence (선택) | 제안서 · 시작 · 기본 흐름 · 섹션 작성 | proposal |
| webapp3 | `PRS2` | 표준 2/8 · Value Props | 제안서 · 시작 · 기본 흐름 · 섹션 작성 | proposal |
| webapp3 | `PRS3` | 표준 3/8 · 조감도 | 제안서 · 시작 · 기본 흐름 · 섹션 작성 | proposal |
| webapp3 | `PRS4` | 표준 4/8 · 공간별 제품 | 제안서 · 시작 · 기본 흐름 · 섹션 작성 | proposal |
| webapp3 | `PRS5` | 표준 5/8 · 솔루션 제안 (선택) | 제안서 · 시작 · 기본 흐름 · 섹션 작성 | proposal |
| webapp3 | `PRS6` | 표준 6/8 · 유관 사례 | 제안서 · 시작 · 기본 흐름 · 섹션 작성 | proposal |
| webapp3 | `PRS7` | 표준 7/8 · Why Samsung | 제안서 · 시작 · 기본 흐름 · 섹션 작성 | proposal |
| webapp3 | `PRS8` | 표준 8/8 · 제품 스펙 | 제안서 · 시작 · 기본 흐름 · 섹션 작성 | proposal |
| webapp3 | `PRQ1` | 퀵윈 1/5 · Value Props | 제안서 · 시작 · 기본 흐름 · 섹션 작성 | proposal |
| webapp3 | `PRQ2` | 퀵윈 2/5 · 공간별 제품 | 제안서 · 시작 · 기본 흐름 · 섹션 작성 | proposal |
| webapp3 | `PRQ3` | 퀵윈 3/5 · 솔루션 제안 (선택) | 제안서 · 시작 · 기본 흐름 · 섹션 작성 | proposal |
| webapp3 | `PRQ4` | 퀵윈 4/5 · 유관 사례 | 제안서 · 시작 · 기본 흐름 · 섹션 작성 | proposal |
| webapp3 | `PRQ5` | 퀵윈 5/5 · 제품 스펙 | 제안서 · 시작 · 기본 흐름 · 섹션 작성 | proposal |
| webapp3 | `PRX1` | Solution형 1/5 · 대규모 MI | 제안서 · 시작 · 기본 흐름 · 섹션 작성 | proposal |
| webapp3 | `PRX2` | Solution형 2/5 · Value Props (선택) | 제안서 · 시작 · 기본 흐름 · 섹션 작성 | proposal |
| webapp3 | `PRX3` | Solution형 3/5 · 공간별 가치 제공 시나리오 | 제안서 · 시작 · 기본 흐름 · 섹션 작성 | proposal |
| webapp3 | `PRX4` | Solution형 4/5 · 유관 사례 | 제안서 · 시작 · 기본 흐름 · 섹션 작성 | proposal |
| webapp3 | `PRX5` | Solution형 5/5 · Why Samsung | 제안서 · 시작 · 기본 흐름 · 섹션 작성 | proposal |
| webapp3 | `PRU2` | 기존 제안서 · 기준별 분석 결과 (9기준 · 필수 확인 3) | 제안서 · 시작 · 기본 흐름 · 섹션 작성 | proposal |
| webapp3 | `PRU2F` | 기존 제안서 · 기준 상세 — 논리 흐름 · 시트별 역할 태깅 · 유저 확인 | 제안서 · 시작 · 기본 흐름 · 섹션 작성 | proposal |
| webapp3 | `PRU3A` | 활용 계획 · 기반으로 개선 · 수정 (같은 고객 · 시트별 유지 · 갱신 · 재작성 · 신규 · 제외) | 제안서 · 시작 · 기본 흐름 · 섹션 작성 | proposal |
| webapp3 | `PRU3B` | 활용 계획 · 논리 흐름만 차용 (다른 고객 · 흐름 → 시트 구성) | 제안서 · 시작 · 기본 흐름 · 섹션 작성 | proposal |
| webapp3 | `PRU4` | 섹션 작성 · 원본 대조 — 공간별 제품 (개선 · 수정 모드) | 제안서 · 시작 · 기본 흐름 · 섹션 작성 | proposal |
| webapp3 | `PRU4B` | 섹션 작성 · 흐름 가이드 — Value Props (흐름 차용 모드) | 제안서 · 시작 · 기본 흐름 · 섹션 작성 | proposal |
| webapp3 | `PRU5` | 완성 · 원본 대비 변경 요약 · 검토 필요 · 흔적 | 제안서 · 시작 · 기본 흐름 · 섹션 작성 | proposal |
| webapp3 | `DnD_MISidebar` | DnD · 사이드바 MI 작업 → MI 섹션 | 제안서 · DnD · 딸깍 · 템플릿 고르기 · 생성 후 | proposal |
| webapp3 | `DnD_MIExtract` | DnD · 놓은 뒤 — 추출 결과 확인 (시트별 매핑) | 제안서 · DnD · 딸깍 · 템플릿 고르기 · 생성 후 | proposal |
| webapp3 | `DnD_Product` | DnD · 제품 팝업 → 공간별 제품 | 제안서 · DnD · 딸깍 · 템플릿 고르기 · 생성 후 | proposal |
| webapp3 | `DnD_ProductDropped` | DnD · 놓은 뒤 — 추가됨 · 시트 업데이트 · 실행 취소 | 제안서 · DnD · 딸깍 · 템플릿 고르기 · 생성 후 | proposal |
| webapp3 | `DnD_Case` | DnD · 유관 사례 팝업 → 유관 사례 | 제안서 · DnD · 딸깍 · 템플릿 고르기 · 생성 후 | proposal |
| webapp3 | `DnD_Solution` | DnD · 솔루션 팝업 → 공간별 가치 제공 시나리오 | 제안서 · DnD · 딸깍 · 템플릿 고르기 · 생성 후 | proposal |
| webapp3 | `OneClickEarly` | 딸깍 · 유형 선택 전에 누름 — 유형부터 추론 | 제안서 · DnD · 딸깍 · 템플릿 고르기 · 생성 후 | proposal |
| webapp3 | `OneClickConfirm` | 딸깍 · 섹션 작성 중에 누름 — 확정/추론 확인 | 제안서 · DnD · 딸깍 · 템플릿 고르기 · 생성 후 | proposal |
| webapp3 | `OneClickGen` | 딸깍 · 생성 중 (중지 · 방향 메모 가능) | 제안서 · DnD · 딸깍 · 템플릿 고르기 · 생성 후 | proposal |
| webapp3 | `OneClickDone` | 딸깍 · 완성 — 추론 표시 · 검토 필요 3곳 | 제안서 · DnD · 딸깍 · 템플릿 고르기 · 생성 후 | proposal |
| webapp3 | `PRS1Layout` | 템플릿 고르기 · 시장 규모 · 성장 — 자동 추천 (MS-B) | 제안서 · DnD · 딸깍 · 템플릿 고르기 · 생성 후 | proposal |
| webapp3 | `PRS4Layout` | 템플릿 고르기 · 공간 제품 소개 — 제품 3개 · 직접 선택 (P3-C) | 제안서 · DnD · 딸깍 · 템플릿 고르기 · 생성 후 | proposal |
| webapp3 | `PRS5Layout` | 템플릿 고르기 · MagicINFO 구성도 — 전용 템플릿 자동 추천 (MGI-D) | 제안서 · DnD · 딸깍 · 템플릿 고르기 · 생성 후 | proposal |
| webapp3 | `PRS7Layout` | 템플릿 고르기 · 경쟁 비교 — 직접 선택 (CM-B) | 제안서 · DnD · 딸깍 · 템플릿 고르기 · 생성 후 | proposal |
| webapp3 | `PRS5LayoutInd` | 템플릿 고르기 · SmartThings Pro 공간 시나리오 — 업종별 버전 직접 선택 (STP-S-HT) | 제안서 · DnD · 딸깍 · 템플릿 고르기 · 생성 후 | proposal |
| webapp3 | `PRS1LayoutInd` | 템플릿 고르기 · 고객사 비즈니스 — 업종 레이아웃 직접 선택 (MI-FB-B 외식 · 카페) | 제안서 · DnD · 딸깍 · 템플릿 고르기 · 생성 후 | proposal |
| webapp3 | `PRS2LayoutInd` | 템플릿 고르기 · 가치 제안 — 업종 레이아웃 직접 선택 (VP-FB-A) | 제안서 · DnD · 딸깍 · 템플릿 고르기 · 생성 후 | proposal |
| webapp3 | `PRX3LayoutInd` | 템플릿 고르기 · 공간 × 솔루션 맵 — 업종 레이아웃 직접 선택 (SS-FB-A) | 제안서 · DnD · 딸깍 · 템플릿 고르기 · 생성 후 | proposal |
| webapp3 | `PR7P` | B2B 제안서 · 미리보기 · 시트 편집 | 제안서 · DnD · 딸깍 · 템플릿 고르기 · 생성 후 | proposal |
| webapp3 | `PR7Q` | B2B 제안서 · 확정 필요 목록 | 제안서 · DnD · 딸깍 · 템플릿 고르기 · 생성 후 | proposal |
| webapp3 | `PR7C` | B2B 제안서 · 검토 · 코멘트 · 승인 | 제안서 · DnD · 딸깍 · 템플릿 고르기 · 생성 후 | proposal |
| webapp3 | `PR7V` | B2B 제안서 · 버전 · 변경 이력 | 제안서 · DnD · 딸깍 · 템플릿 고르기 · 생성 후 | proposal |
| webapp3 | `PR7X` | B2B 제안서 · 내보내기 옵션 | 제안서 · DnD · 딸깍 · 템플릿 고르기 · 생성 후 | proposal |
| webapp3 | `Sidebar` | 컴포넌트 · 사이드바 | 공통 컴포넌트 (웹앱 ①과 같은 파일) | shell |
| webapp3 | `TopBar` | 컴포넌트 · 상단 액션바 (팝오버 4종 내장) | 공통 컴포넌트 (웹앱 ①과 같은 파일) | shell |
| webapp3 | `Stepper` | 컴포넌트 · 스텝바 | 공통 컴포넌트 (웹앱 ①과 같은 파일) | shell |
| webapp3 | `SectionStep` | 컴포넌트 · 제안서 섹션 작성 (type · idx · mode) | 공통 컴포넌트 (웹앱 ①과 같은 파일) | proposal |
| webapp3 | `Thumb` | 컴포넌트 · 템플릿 썸네일 (kind · n) | 공통 컴포넌트 (웹앱 ①과 같은 파일) | shell |
| webapp3 | `Guide` | Winmate 캔버스 안내 | 안내 · 캔버스 8개 | shell |

기능별 보드 수: birdseye 27, competitor 8, dss(신규) 7, image 12, mi 8, proposal 63, requirements 4, scenario 21, shell 29, shell(공통 흐름) 9, spec 4, storyboard 7, vp 9