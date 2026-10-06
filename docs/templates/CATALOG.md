# Winmate 시트 템플릿 카탈로그

> 자동 생성 — 직접 고치지 말 것. `uv run python -m winmate_export.templates.build` 로 다시 만든다.
> 원본: `docs/templates/source/<캔버스>/`(Design 캔버스 project 파일 사본) · 기계용: `services/export/src/winmate_export/templates/catalog.json` · API: `GET /api/export/v1/templates`.

## 요약

- 템플릿 **430**종 (출시 381 · 제작 중 48 · 내부용 1)
- 업종판(출시) 131 · 솔루션 전용 54(전용 33 + 업종 버전 21)
- 슬라이드 16:9(13.333 × 7.5 in) · 좌표는 1280 × 720 캔버스 기준 상대값(0..1) · 글꼴 `Noto Sans KR` · 포인트 색 `#1428a0`

| 섹션 | 수 |
|---|---|
| 공통(표지 · 목차 · 간지 · 마무리) (`common`) | 12 |
| Market Intelligence (`mi`) | 68 |
| Value Props (`vp`) | 86 |
| 조감도 (`birdseye`) | 16 |
| 공간별 제품 (`space_products`) | 46 |
| 솔루션 제안 (`solution`) | 82 |
| 공간별 가치 제공 시나리오 (`space_scenario`) | 94 |
| 유관 사례 (`cases`) | 8 |
| Why Samsung (`why`) | 10 |
| 제품 스펙 (`spec`) | 6 |
| 부록 (`appendix`) | 2 |

| 역할 | 이름 | 수 |
|---|---|---|
| `AX` | 부록 | 2 |
| `BM` | 구성 · 수량 | 5 |
| `BV` | 공간 전경 | 4 |
| `CB` | 고객사 비즈니스 | 20 |
| `CD` | 사례 상세 | 4 |
| `CH` | 고객 과제 | 19 |
| `CL` | 사례 모음 | 4 |
| `CLOSING` | 마무리 | 2 |
| `CM` | 경쟁 비교 | 3 |
| `COVER` | 표지 | 5 |
| `CP` | 경쟁 환경 | 3 |
| `DIVIDER` | 섹션 간지 | 3 |
| `EF` | 기대 효과 | 21 |
| `GN` | 생성 시안 | 4 |
| `IM` | MI 시사점 | 2 |
| `IS` | 현장 조사 | 2 |
| `MB` | 디자인 컨셉 | 2 |
| `MS` | 시장 규모 · 성장 | 21 |
| `OP` | 운영 시나리오 | 19 |
| `PI` | 공간 제품 소개 | 36 |
| `SA` | 솔루션 구성도 | 4 |
| `SC` | 스펙 비교 | 3 |
| `SD` | 제품 상세 | 3 |
| `SF` | 솔루션 상세 | 5 |
| `SM` | 공간 맵 | 5 |
| `SS` | 공간 시나리오 | 71 |
| `ST` | 삼성 강점 | 4 |
| `SV` | 지원 체계 | 3 |
| `SXD` | 솔루션 구성도 | 11 |
| `SXI` | 솔루션 소개 | 11 |
| `SXS` | 솔루션 공간 시나리오 | 32 |
| `TOC` | 목차 | 2 |
| `TR` | 산업 트렌드 | 3 |
| `US` | 사용자 분석 | 19 |
| `UX` | 사용 장면 | 3 |
| `VM` | 공간 × 솔루션 맵 | 20 |
| `VP` | 가치 제안 | 46 |
| `ZP` | 존별 포인트 | 4 |

## 원본 캔버스

| 폴더 | 캔버스 | 아티팩트 | 판 |
|---|---|---|---|
| `docs/templates/source/mi/` | Winmate PPT · 01 MI (업종별) | https://claude.ai/artifact/XnbECsMCvmCsHTsJtfeQUV | `1790912699-b660` |
| `docs/templates/source/vp/` | Winmate PPT · 02 Value Props (업종별) | https://claude.ai/artifact/V6bPV1WJhKFyJeHEYjmnhv | `1790920287-e4e0` |
| `docs/templates/source/ss/` | Winmate PPT · 03 공간별 가치 제공 시나리오 (업종별) | https://claude.ai/artifact/7DyZ4i11yq9sjnBP2ztEtr | `1790920956-f124` |
| `docs/templates/source/pi/` | Winmate PPT · 04 공간별 제품 소개 | https://claude.ai/artifact/9mD73MY9hcPFPAavohfA7B | `1791267499-dfd8` |
| `docs/templates/source/common/` | Winmate PPT · 공통 레이아웃 · 솔루션 전용 · 분석 | https://claude.ai/artifact/GFCVoigDttt2414bvFWDvv | `1790925158-2850` |

## 칸(slot) 형식

| type | 값 |
|---|---|
| `text` · `caption` | 문자열 또는 `{ko, en}` |
| `bullets` | 문자열 목록 |
| `number` | 숫자 또는 문자열(`[00]`) |
| `kpi` | `{value, unit?, label?, sub?, delta?, bar?(0–100)}` 또는 문자열 |
| `image` · `logo` | files `file_id` 또는 `{file_id, caption?, credit?, ai_generated?, fit?}` |
| `table` | `{columns:[…], rows:[[…]], highlight_col?, highlight_rows?, group_rows?}` — 칸은 문자열 또는 `{text, bold?, fill?}` |
| `chart` | `{type: bar\|line\|hbar\|stacked\|stacked100\|pie\|doughnut\|radar\|scatter\|bubble, categories:[…], series:[{name, values}], unit?, highlight_last?}` |
| `source` | 문자열 또는 `[{label, url?}]` |
| `card` | 필드 묶음 객체(`fields` 참고). `count` 가 있으면 목록 |

`*` = 필수. 업종 변형은 바탕 템플릿과 같은 칸 · 배치를 쓴다(`base`). 이미지 등급 A 공간+제품 · B 솔루션 화면 · C 제품 컷 · D 도식 · E 아이콘/로고.

## 공통(표지 · 목차 · 간지 · 마무리) (`common`)

| 코드 | 이름 | 역할 | 업종 · 솔루션 | 상태 | 아키타입 | 칸 | 배치 | 원본 보드 |
|---|---|---|---|---|---|---|---|---|
| `C07` | 마무리 · 연락처 | `CLOSING` |  | ready | `closing` | `title*` text · `subtitle` text · `contacts` card{name,role,body}×4 | 본문 64,500–1216,620 · 상자 8 | `common/L_C07.dc.html` |
| `C12` | 마무리 B · 도입 후 모습 (생성 시안) | `CLOSING` |  | ready | `closing_image` | `title*` text · `subtitle` text · `contacts` card{name,role,body}×4 · `image*` image:A | 본문 0,0–1216,720 · 상자 9 | `common/L_C12.dc.html` |
| `C01` | 표지 A · 이미지 분할 | `COVER` |  | ready | `cover_split` | `title*` text · `subtitle` text · `customer` text · `date` text · `presenter` text · `image` image:A | 본문 64,0–1280,720 · 상자 9 | `common/L_C01.dc.html` |
| `C02` | 표지 B · 풀블리드 이미지 | `COVER` |  | ready | `cover_full` | `title*` text · `subtitle` text · `customer` text · `date` text · `presenter` text · `image` image:A | 본문 0,0–1280,624 · 상자 9 | `common/L_C02.dc.html` |
| `C03` | 표지 C · 타이포 중심 | `COVER` |  | ready | `cover_type` | `title*` text · `subtitle` text · `customer` text · `date` text · `presenter` text | 본문 64,584–1216,636 · 상자 8 | `common/L_C03.dc.html` |
| `C08` | 표지 D · 이미지 3컷 콜라주 | `COVER` |  | ready | `cover_collage` | `title*` text · `subtitle` text · `customer` text · `date` text · `presenter` text · `images` image:A×3 · `scope` bullets×3 | 본문 64,24–1256,660 · 상자 11 | `common/L_C08.dc.html` |
| `C09` | 표지 E · 제품 누끼 히어로 | `COVER` |  | ready | `cover_product` | `title*` text · `subtitle` text · `customer` text · `date` text · `presenter` text · `image*` image:C · `kpis` kpi×3 | 본문 64,36–1148,676 · 상자 12 | `common/L_C09.dc.html` |
| `C05` | 섹션 간지 A · 대형 번호 | `DIVIDER` |  | ready | `divider_number` | `no` text · `title*` text · `subtitle` text · `sheets` bullets×6 | 본문 96,150–1184,640 · 상자 5 | `common/L_C05.dc.html` |
| `C06` | 섹션 간지 B · 이미지 분할 + 시트 목록 | `DIVIDER` |  | ready | `divider_image` | `no` text · `title*` text · `subtitle` text · `sheets` bullets×6 · `image` image:A | 본문 0,0–1216,720 · 상자 5 | `common/L_C06.dc.html` |
| `C11` | 간지 C · 풀블리드 사진 + 밴드 | `DIVIDER` |  | ready | `divider_photo` | `no` text · `title*` text · `subtitle` text · `sheets` bullets×6 · `image*` image:A | 본문 0,0–1280,720 · 상자 6 | `common/L_C11.dc.html` |
| `C04` | 목차 | `TOC` |  | ready | `toc` | `title` text · `items*` card{no,title,body}×8 | 본문 64,200–1216,616 · 상자 12 | `common/L_C04.dc.html` |
| `C10` | 목차 B · 섹션 썸네일 | `TOC` |  | ready | `toc_thumbs` | `title` text · `items*` card{no,title,body,image}×6 | 본문 64,136–1216,628 · 상자 10 | `common/L_C10.dc.html` |
## Market Intelligence (`mi`)

| 코드 | 이름 | 역할 | 업종 · 솔루션 | 상태 | 아키타입 | 칸 | 배치 | 원본 보드 |
|---|---|---|---|---|---|---|---|---|
| `CB-A` | 한 줄 요약 + 3단 | `CB` |  | ready | `summary_3col` | `title*` text · `summary*` text · `columns*` card{tag,title,bullets,kpi}×3 | 본문 64,188–1216,648 · 상자 10 | `mi/L_MI03.dc.html` |
| `CB-B` | 전략 목표 → 과제 | `CB` |  | ready | `tree` | `title*` text · `headers` text×3 · `root*` card{tag,title,kpi,note} · `branches*` card{no,title,body}×3 · `leaves*` card{title,body,tag}×5 | 본문 64,136–1216,648 · 상자 28 | `mi/L_CB_B.dc.html` |
| `CB-C` | 운영 흐름 속 문제 | `CB` |  | ready | `process_pains` | `title*` text · `subtitle` text · `steps*` card{no,title,owner,days}×5 · `pains*` card{no,title,body}×3 · `totals` kpi×3 · `totals_label` text | 본문 64,176–1216,630 · 상자 26 | `mi/L_CB_C.dc.html` |
| `CB-D` | SWOT | `CB` |  | ready | `swot` | `title*` text · `quadrants*` card{letter,title,bullets}×4 · `axes` text×4 · `message` text | 본문 64,139–1216,636 · 상자 15 | `mi/L_CB_D.dc.html` |
| `MI-AD-B` | 옥외 광고 · 고객 비즈니스 · 운영 과제 | `CB` | AD 옥외 광고 | ready | `biz_ops` | `title*` text · `subtitle` text · `chain*` card{no,title,body,kpi}×5 · `issues*` card{tag,title,body,kpi}×6 · `chain_label` text · `issues_label` text | 본문 64,160–1216,648 · 상자 23 | `mi/L_MI_AD_B.dc.html` |
| `MI-ED-B` | 교육 · 캠퍼스 · 고객 비즈니스 · 운영 과제 | `CB` | ED 교육 · 캠퍼스 | ready | `biz_ops` | `title*` text · `subtitle` text · `chain*` card{no,title,body,kpi}×5 · `issues*` card{tag,title,body,kpi}×6 · `chain_label` text · `issues_label` text | 본문 64,160–1216,648 · 상자 23 | `mi/L_MI_ED_B.dc.html` |
| `MI-FB-B` | 외식 · 카페 · 고객 비즈니스 · 운영 과제 | `CB` | FB 외식 · 카페 | ready | `biz_ops` | `title*` text · `subtitle` text · `chain*` card{no,title,body,kpi}×5 · `issues*` card{tag,title,body,kpi}×6 · `chain_label` text · `issues_label` text | 본문 64,160–1216,648 · 상자 23 | `mi/L_MI_FB_B.dc.html` |
| `MI-FN-B` | 금융 · 고객 비즈니스 · 운영 과제 | `CB` | FN 금융 | ready | `biz_ops` | `title*` text · `subtitle` text · `chain*` card{no,title,body,kpi}×5 · `issues*` card{tag,title,body,kpi}×6 · `chain_label` text · `issues_label` text | 본문 64,160–1216,648 · 상자 23 | `mi/L_MI_FN_B.dc.html` |
| `MI-HT-B` | 호텔 · 리조트 · 고객 비즈니스 · 운영 과제 | `CB` | HT 호텔 · 리조트 | ready | `biz_ops` | `title*` text · `subtitle` text · `chain*` card{no,title,body,kpi}×5 · `issues*` card{tag,title,body,kpi}×6 · `chain_label` text · `issues_label` text | 본문 64,160–1216,648 · 상자 23 | `mi/L_MI_HT_B.dc.html` |
| `MI-ID-B` | 인테리어 · 빌트인 · 고객 비즈니스 · 운영 과제 | `CB` | ID 인테리어 · 빌트인 | ready | `biz_ops` | `title*` text · `subtitle` text · `chain*` card{no,title,body,kpi}×5 · `issues*` card{tag,title,body,kpi}×6 · `chain_label` text · `issues_label` text | 본문 64,160–1216,648 · 상자 23 | `mi/L_MI_ID_B.dc.html` |
| `MI-MD-B` | 의료 · 요양 · 고객 비즈니스 · 운영 과제 | `CB` | MD 의료 · 요양 | ready | `biz_ops` | `title*` text · `subtitle` text · `chain*` card{no,title,body,kpi}×5 · `issues*` card{tag,title,body,kpi}×6 · `chain_label` text · `issues_label` text | 본문 64,160–1216,648 · 상자 23 | `mi/L_MI_MD_B.dc.html` |
| `MI-MF-B` | 제조 · 물류 · 현장 · 고객 비즈니스 · 운영 과제 | `CB` | MF 제조 · 물류 · 현장 | ready | `biz_ops` | `title*` text · `subtitle` text · `chain*` card{no,title,body,kpi}×5 · `issues*` card{tag,title,body,kpi}×6 · `chain_label` text · `issues_label` text | 본문 64,160–1216,648 · 상자 23 | `mi/L_MI_MF_B.dc.html` |
| `MI-OE-B` | 파트너 전용 단말 · 고객 비즈니스 · 운영 과제 | `CB` | OE 파트너 전용 단말 | ready | `biz_ops` | `title*` text · `subtitle` text · `chain*` card{no,title,body,kpi}×5 · `issues*` card{tag,title,body,kpi}×6 · `chain_label` text · `issues_label` text | 본문 64,160–1216,648 · 상자 23 | `mi/L_MI_OE_B.dc.html` |
| `MI-OF-B` | 오피스 · 고객 비즈니스 · 운영 과제 | `CB` | OF 오피스 | ready | `biz_ops` | `title*` text · `subtitle` text · `chain*` card{no,title,body,kpi}×5 · `issues*` card{tag,title,body,kpi}×6 · `chain_label` text · `issues_label` text | 본문 64,160–1216,648 · 상자 23 | `mi/L_MI_OF_B.dc.html` |
| `MI-PB-B` | 공공 · 교통 · 고객 비즈니스 · 운영 과제 | `CB` | PB 공공 · 교통 | ready | `biz_ops` | `title*` text · `subtitle` text · `chain*` card{no,title,body,kpi}×5 · `issues*` card{tag,title,body,kpi}×6 · `chain_label` text · `issues_label` text | 본문 64,160–1216,648 · 상자 23 | `mi/L_MI_PB_B.dc.html` |
| `MI-RS-B` | 주거 분양 · 고객 비즈니스 · 운영 과제 | `CB` | RS 주거 분양 | ready | `biz_ops` | `title*` text · `subtitle` text · `chain*` card{no,title,body,kpi}×5 · `issues*` card{tag,title,body,kpi}×6 · `chain_label` text · `issues_label` text | 본문 64,160–1216,648 · 상자 23 | `mi/L_MI_RS_B.dc.html` |
| `MI-RT-B` | 리테일 · 플래그십 · 고객 비즈니스 · 운영 과제 | `CB` | RT 리테일 · 플래그십 | ready | `biz_ops` | `title*` text · `subtitle` text · `chain*` card{no,title,body,kpi}×5 · `issues*` card{tag,title,body,kpi}×6 · `chain_label` text · `issues_label` text | 본문 64,160–1216,648 · 상자 23 | `mi/L_MI_RT_B.dc.html` |
| `MI-SV-B` | 생활 편의 · 무인 매장 · 고객 비즈니스 · 운영 과제 | `CB` | SV 생활 편의 · 무인 매장 | ready | `biz_ops` | `title*` text · `subtitle` text · `chain*` card{no,title,body,kpi}×5 · `issues*` card{tag,title,body,kpi}×6 · `chain_label` text · `issues_label` text | 본문 64,160–1216,648 · 상자 23 | `mi/L_MI_SV_B.dc.html` |
| `MI-TP-B` | 테마파크 · 전시 · 고객 비즈니스 · 운영 과제 | `CB` | TP 테마파크 · 전시 | ready | `biz_ops` | `title*` text · `subtitle` text · `chain*` card{no,title,body,kpi}×5 · `issues*` card{tag,title,body,kpi}×6 · `chain_label` text · `issues_label` text | 본문 64,160–1216,648 · 상자 23 | `mi/L_MI_TP_B.dc.html` |
| `MI-VN-B` | 공연장 · 경기장 · 고객 비즈니스 · 운영 과제 | `CB` | VN 공연장 · 경기장 | ready | `biz_ops` | `title*` text · `subtitle` text · `chain*` card{no,title,body,kpi}×5 · `issues*` card{tag,title,body,kpi}×6 · `chain_label` text · `issues_label` text | 본문 64,160–1216,648 · 상자 23 | `mi/L_MI_VN_B.dc.html` |
| `CP-A` | 비교표 | `CP` |  | ready | `table` | `title*` text · `subtitle` text · `table*` table · `message` text | 본문 64,160–1216,636 · 상자 9 | `mi/L_MI04.dc.html` |
| `CP-B` | 포지셔닝 맵 | `CP` |  | ready | `plot_insights` | `title*` text · `subtitle` text · `points*` card{title,x,y,size,tag}×6 · `axis_x` text · `axis_y` text · `insights*` card{no,title,body}×3 | 본문 72,160–1216,648 · 상자 13 | `mi/L_CP_B.dc.html` |
| `CP-C` | 점유율 + 추이 | `CP` |  | ready | `stacked_table` | `title*` text · `chart*` chart · `table*` table | 본문 84,136–1216,648 · 상자 8 | `mi/L_CP_C.dc.html` |
| `IM-A` | 발견 → 시사점 → 방향 | `IM` |  | ready | `funnel` | `title*` text · `headers` text×3 · `findings*` card{tag,title}×4 · `implications*` card{tag,title,body,chips}×2 · `direction*` card{tag,title,bullets} | 본문 64,136–1216,648 · 상자 18 | `mi/L_IM_A.dc.html` |
| `IM-B` | 4분면 요약 + 결론 | `IM` |  | ready | `quad_center` | `title*` text · `quadrants*` card{tag,title,body,bullets,kpi}×4 · `conclusion*` text | 본문 64,136–1216,648 · 상자 10 | `mi/L_IM_B.dc.html` |
| `MS-A` | 핵심 수치 4 | `MS` |  | ready | `kpi_band` | `title*` text · `subtitle` text · `kpis*` kpi×4 · `message` text · `bullets` bullets×3 | 본문 64,176–1216,634 · 상자 13 | `mi/L_MI01.dc.html` |
| `MS-B` | 성장 추이 | `MS` |  | ready | `chart_insights` | `title*` text · `subtitle` text · `chart*` chart · `chart_title` text · `insights*` card{no,title,body,kpi}×3 | 본문 88,160–1216,648 · 상자 12 | `mi/L_MI02.dc.html` |
| `MS-C` | TAM · SAM · SOM | `MS` |  | ready | `circles_rows` | `title*` text · `subtitle` text · `tiers*` kpi×3 · `rows*` card{label,title,body}×3 · `message` text | 본문 84,160–1216,640 · 상자 14 | `mi/L_MS_C.dc.html` |
| `MS-D` | 세그먼트 규모 × 성장률 | `MS` |  | ready | `plot_insights` | `title*` text · `subtitle` text · `points*` card{title,x,y,size,tag}×5 · `axis_x` text · `axis_y` text · `insights*` card{no,title,body}×3 | 본문 72,160–1216,648 · 상자 13 | `mi/L_MS_D.dc.html` |
| `MS-E` | 성장 동인 → 전망 | `MS` |  | ready | `drivers_outlook` | `title*` text · `drivers*` card{no,title,body,kpi}×3 · `outlook_title` text · `outlook` kpi×2 · `outlook_body` text | 본문 64,136–1188,648 · 상자 13 | `mi/L_MS_E.dc.html` |
| `MI-AD-A` | 옥외 광고 · 시장 · 트렌드 | `MS` | AD 옥외 광고 | ready | `market_trend` | `title*` text · `subtitle` text · `chart*` chart · `chart_title` text · `chart_note` text · `kpis` kpi×3 · `headers` text×2 · `trends*` card{no,title,body,so,kpi}×4 | 본문 80,160–1216,648 · 상자 27 | `mi/L_MI_AD_A.dc.html` |
| `MI-ED-A` | 교육 · 캠퍼스 · 시장 · 트렌드 | `MS` | ED 교육 · 캠퍼스 | ready | `market_trend` | `title*` text · `subtitle` text · `chart*` chart · `chart_title` text · `chart_note` text · `kpis` kpi×3 · `headers` text×2 · `trends*` card{no,title,body,so,kpi}×4 | 본문 80,160–1216,648 · 상자 27 | `mi/L_MI_ED_A.dc.html` |
| `MI-FB-A` | 외식 · 카페 · 시장 · 트렌드 | `MS` | FB 외식 · 카페 | ready | `market_trend` | `title*` text · `subtitle` text · `chart*` chart · `chart_title` text · `chart_note` text · `kpis` kpi×3 · `headers` text×2 · `trends*` card{no,title,body,so,kpi}×4 | 본문 80,160–1216,648 · 상자 27 | `mi/L_MI_FB_A.dc.html` |
| `MI-FN-A` | 금융 · 시장 · 트렌드 | `MS` | FN 금융 | ready | `market_trend` | `title*` text · `subtitle` text · `chart*` chart · `chart_title` text · `chart_note` text · `kpis` kpi×3 · `headers` text×2 · `trends*` card{no,title,body,so,kpi}×4 | 본문 80,160–1216,648 · 상자 27 | `mi/L_MI_FN_A.dc.html` |
| `MI-HT-A` | 호텔 · 리조트 · 시장 · 트렌드 | `MS` | HT 호텔 · 리조트 | ready | `market_trend` | `title*` text · `subtitle` text · `chart*` chart · `chart_title` text · `chart_note` text · `kpis` kpi×3 · `headers` text×2 · `trends*` card{no,title,body,so,kpi}×4 | 본문 80,160–1216,648 · 상자 27 | `mi/L_MI_HT_A.dc.html` |
| `MI-ID-A` | 인테리어 · 빌트인 · 시장 · 트렌드 | `MS` | ID 인테리어 · 빌트인 | ready | `market_trend` | `title*` text · `subtitle` text · `chart*` chart · `chart_title` text · `chart_note` text · `kpis` kpi×3 · `headers` text×2 · `trends*` card{no,title,body,so,kpi}×4 | 본문 80,160–1216,648 · 상자 27 | `mi/L_MI_ID_A.dc.html` |
| `MI-MD-A` | 의료 · 요양 · 시장 · 트렌드 | `MS` | MD 의료 · 요양 | ready | `market_trend` | `title*` text · `subtitle` text · `chart*` chart · `chart_title` text · `chart_note` text · `kpis` kpi×3 · `headers` text×2 · `trends*` card{no,title,body,so,kpi}×4 | 본문 80,160–1216,648 · 상자 27 | `mi/L_MI_MD_A.dc.html` |
| `MI-MF-A` | 제조 · 물류 · 현장 · 시장 · 트렌드 | `MS` | MF 제조 · 물류 · 현장 | ready | `market_trend` | `title*` text · `subtitle` text · `chart*` chart · `chart_title` text · `chart_note` text · `kpis` kpi×3 · `headers` text×2 · `trends*` card{no,title,body,so,kpi}×4 | 본문 80,160–1216,648 · 상자 27 | `mi/L_MI_MF_A.dc.html` |
| `MI-OE-A` | 파트너 전용 단말 · 시장 · 트렌드 | `MS` | OE 파트너 전용 단말 | ready | `market_trend` | `title*` text · `subtitle` text · `chart*` chart · `chart_title` text · `chart_note` text · `kpis` kpi×3 · `headers` text×2 · `trends*` card{no,title,body,so,kpi}×4 | 본문 80,160–1216,648 · 상자 27 | `mi/L_MI_OE_A.dc.html` |
| `MI-OF-A` | 오피스 · 시장 · 트렌드 | `MS` | OF 오피스 | ready | `market_trend` | `title*` text · `subtitle` text · `chart*` chart · `chart_title` text · `chart_note` text · `kpis` kpi×3 · `headers` text×2 · `trends*` card{no,title,body,so,kpi}×4 | 본문 80,160–1216,648 · 상자 27 | `mi/L_MI_OF_A.dc.html` |
| `MI-PB-A` | 공공 · 교통 · 시장 · 트렌드 | `MS` | PB 공공 · 교통 | ready | `market_trend` | `title*` text · `subtitle` text · `chart*` chart · `chart_title` text · `chart_note` text · `kpis` kpi×3 · `headers` text×2 · `trends*` card{no,title,body,so,kpi}×4 | 본문 80,160–1216,648 · 상자 27 | `mi/L_MI_PB_A.dc.html` |
| `MI-RS-A` | 주거 분양 · 시장 · 트렌드 | `MS` | RS 주거 분양 | ready | `market_trend` | `title*` text · `subtitle` text · `chart*` chart · `chart_title` text · `chart_note` text · `kpis` kpi×3 · `headers` text×2 · `trends*` card{no,title,body,so,kpi}×4 | 본문 80,160–1216,648 · 상자 27 | `mi/L_MI_RS_A.dc.html` |
| `MI-RT-A` | 리테일 · 플래그십 · 시장 · 트렌드 | `MS` | RT 리테일 · 플래그십 | ready | `market_trend` | `title*` text · `subtitle` text · `chart*` chart · `chart_title` text · `chart_note` text · `kpis` kpi×3 · `headers` text×2 · `trends*` card{no,title,body,so,kpi}×4 | 본문 80,160–1216,648 · 상자 27 | `mi/L_MI_RT_A.dc.html` |
| `MI-SV-A` | 생활 편의 · 무인 매장 · 시장 · 트렌드 | `MS` | SV 생활 편의 · 무인 매장 | ready | `market_trend` | `title*` text · `subtitle` text · `chart*` chart · `chart_title` text · `chart_note` text · `kpis` kpi×3 · `headers` text×2 · `trends*` card{no,title,body,so,kpi}×4 | 본문 80,160–1216,648 · 상자 27 | `mi/L_MI_SV_A.dc.html` |
| `MI-TP-A` | 테마파크 · 전시 · 시장 · 트렌드 | `MS` | TP 테마파크 · 전시 | ready | `market_trend` | `title*` text · `subtitle` text · `chart*` chart · `chart_title` text · `chart_note` text · `kpis` kpi×3 · `headers` text×2 · `trends*` card{no,title,body,so,kpi}×4 | 본문 80,160–1216,648 · 상자 27 | `mi/L_MI_TP_A.dc.html` |
| `MI-VN-A` | 공연장 · 경기장 · 시장 · 트렌드 | `MS` | VN 공연장 · 경기장 | ready | `market_trend` | `title*` text · `subtitle` text · `chart*` chart · `chart_title` text · `chart_note` text · `kpis` kpi×3 · `headers` text×2 · `trends*` card{no,title,body,so,kpi}×4 | 본문 80,160–1216,648 · 상자 27 | `mi/L_MI_VN_A.dc.html` |
| `TR-A` | 흐름 타임라인 | `TR` |  | ready | `timeline` | `title*` text · `steps*` card{when,title,body,tag}×4 · `message` text · `message_label` text | 본문 64,208–1216,632 · 상자 17 | `mi/L_MI06.dc.html` |
| `TR-B` | 트렌드 → 고객 시사점 | `TR` |  | ready | `trend_cards` | `title*` text · `trends*` card{no,title,body,bullets,so}×3 · `so_label` text | 본문 64,136–1216,648 · 상자 14 | `mi/L_TR_B.dc.html` |
| `TR-C` | 영향도 × 시급성 | `TR` |  | ready | `plot_insights` | `title*` text · `points*` card{title,x,y,size,tag}×6 · `axis_x` text · `axis_y` text · `quadrants` text×4 · `insights*` card{no,title,body}×3 | 본문 72,136–1216,648 · 상자 12 | `mi/L_TR_C.dc.html` |
| `US-A` | 페르소나 3 | `US` |  | ready | `personas` | `title*` text · `people*` card{role,name,body,bullets,quote,kpi}×3 | 본문 64,136–1216,648 · 상자 8 | `mi/L_MI05.dc.html` |
| `US-B` | 고객 여정 맵 | `US` |  | ready | `journey` | `title*` text · `stages*` card{title,action,touchpoint,emotion,pain,opportunity}×5 · `row_labels` text×5 | 본문 64,136–1216,648 · 상자 31 | `mi/L_US_B.dc.html` |
| `US-C` | 사용자 구성 + 니즈 | `US` |  | ready | `donut_needs` | `title*` text · `subtitle` text · `chart*` chart · `segments*` card{title,share,need,so}×4 · `headers` text×4 | 본문 84,160–1216,648 · 상자 28 | `mi/L_US_C.dc.html` |
| `MI-AD-C` | 옥외 광고 · 사용자 여정 | `US` | AD 옥외 광고 | ready | `user_journey` | `title*` text · `subtitle` text · `segments*` card{title,share,body}×3 · `segments_label` text · `stages*` card{title,action,pain,opportunity}×5 · `row_labels` text×3 | 본문 82,160–1216,648 · 상자 34 | `mi/L_MI_AD_C.dc.html` |
| `MI-ED-C` | 교육 · 캠퍼스 · 사용자 여정 | `US` | ED 교육 · 캠퍼스 | ready | `user_journey` | `title*` text · `subtitle` text · `segments*` card{title,share,body}×3 · `segments_label` text · `stages*` card{title,action,pain,opportunity}×5 · `row_labels` text×3 | 본문 82,160–1216,648 · 상자 34 | `mi/L_MI_ED_C.dc.html` |
| `MI-FB-C` | 외식 · 카페 · 사용자 여정 | `US` | FB 외식 · 카페 | ready | `user_journey` | `title*` text · `subtitle` text · `segments*` card{title,share,body}×3 · `segments_label` text · `stages*` card{title,action,pain,opportunity}×5 · `row_labels` text×3 | 본문 82,160–1216,648 · 상자 34 | `mi/L_MI_FB_C.dc.html` |
| `MI-FN-C` | 금융 · 사용자 여정 | `US` | FN 금융 | ready | `user_journey` | `title*` text · `subtitle` text · `segments*` card{title,share,body}×3 · `segments_label` text · `stages*` card{title,action,pain,opportunity}×5 · `row_labels` text×3 | 본문 82,160–1216,648 · 상자 34 | `mi/L_MI_FN_C.dc.html` |
| `MI-HT-C` | 호텔 · 리조트 · 사용자 여정 | `US` | HT 호텔 · 리조트 | ready | `user_journey` | `title*` text · `subtitle` text · `segments*` card{title,share,body}×3 · `segments_label` text · `stages*` card{title,action,pain,opportunity}×5 · `row_labels` text×3 | 본문 82,160–1216,648 · 상자 34 | `mi/L_MI_HT_C.dc.html` |
| `MI-ID-C` | 인테리어 · 빌트인 · 사용자 여정 | `US` | ID 인테리어 · 빌트인 | ready | `user_journey` | `title*` text · `subtitle` text · `segments*` card{title,share,body}×3 · `segments_label` text · `stages*` card{title,action,pain,opportunity}×5 · `row_labels` text×3 | 본문 82,160–1216,648 · 상자 34 | `mi/L_MI_ID_C.dc.html` |
| `MI-MD-C` | 의료 · 요양 · 사용자 여정 | `US` | MD 의료 · 요양 | ready | `user_journey` | `title*` text · `subtitle` text · `segments*` card{title,share,body}×3 · `segments_label` text · `stages*` card{title,action,pain,opportunity}×5 · `row_labels` text×3 | 본문 82,160–1216,648 · 상자 34 | `mi/L_MI_MD_C.dc.html` |
| `MI-MF-C` | 제조 · 물류 · 현장 · 사용자 여정 | `US` | MF 제조 · 물류 · 현장 | ready | `user_journey` | `title*` text · `subtitle` text · `segments*` card{title,share,body}×3 · `segments_label` text · `stages*` card{title,action,pain,opportunity}×5 · `row_labels` text×3 | 본문 82,160–1216,648 · 상자 34 | `mi/L_MI_MF_C.dc.html` |
| `MI-OE-C` | 파트너 전용 단말 · 사용자 여정 | `US` | OE 파트너 전용 단말 | ready | `user_journey` | `title*` text · `subtitle` text · `segments*` card{title,share,body}×3 · `segments_label` text · `stages*` card{title,action,pain,opportunity}×5 · `row_labels` text×3 | 본문 82,160–1216,648 · 상자 34 | `mi/L_MI_OE_C.dc.html` |
| `MI-OF-C` | 오피스 · 사용자 여정 | `US` | OF 오피스 | ready | `user_journey` | `title*` text · `subtitle` text · `segments*` card{title,share,body}×3 · `segments_label` text · `stages*` card{title,action,pain,opportunity}×5 · `row_labels` text×3 | 본문 82,160–1216,648 · 상자 34 | `mi/L_MI_OF_C.dc.html` |
| `MI-PB-C` | 공공 · 교통 · 사용자 여정 | `US` | PB 공공 · 교통 | ready | `user_journey` | `title*` text · `subtitle` text · `segments*` card{title,share,body}×3 · `segments_label` text · `stages*` card{title,action,pain,opportunity}×5 · `row_labels` text×3 | 본문 82,160–1216,648 · 상자 34 | `mi/L_MI_PB_C.dc.html` |
| `MI-RS-C` | 주거 분양 · 사용자 여정 | `US` | RS 주거 분양 | ready | `user_journey` | `title*` text · `subtitle` text · `segments*` card{title,share,body}×3 · `segments_label` text · `stages*` card{title,action,pain,opportunity}×5 · `row_labels` text×3 | 본문 82,160–1216,648 · 상자 34 | `mi/L_MI_RS_C.dc.html` |
| `MI-RT-C` | 리테일 · 플래그십 · 사용자 여정 | `US` | RT 리테일 · 플래그십 | ready | `user_journey` | `title*` text · `subtitle` text · `segments*` card{title,share,body}×3 · `segments_label` text · `stages*` card{title,action,pain,opportunity}×5 · `row_labels` text×3 | 본문 82,160–1216,648 · 상자 34 | `mi/L_MI_RT_C.dc.html` |
| `MI-SV-C` | 생활 편의 · 무인 매장 · 사용자 여정 | `US` | SV 생활 편의 · 무인 매장 | ready | `user_journey` | `title*` text · `subtitle` text · `segments*` card{title,share,body}×3 · `segments_label` text · `stages*` card{title,action,pain,opportunity}×5 · `row_labels` text×3 | 본문 82,160–1216,648 · 상자 34 | `mi/L_MI_SV_C.dc.html` |
| `MI-TP-C` | 테마파크 · 전시 · 사용자 여정 | `US` | TP 테마파크 · 전시 | ready | `user_journey` | `title*` text · `subtitle` text · `segments*` card{title,share,body}×3 · `segments_label` text · `stages*` card{title,action,pain,opportunity}×5 · `row_labels` text×3 | 본문 82,160–1216,648 · 상자 34 | `mi/L_MI_TP_C.dc.html` |
| `MI-VN-C` | 공연장 · 경기장 · 사용자 여정 | `US` | VN 공연장 · 경기장 | ready | `user_journey` | `title*` text · `subtitle` text · `segments*` card{title,share,body}×3 · `segments_label` text · `stages*` card{title,action,pain,opportunity}×5 · `row_labels` text×3 | 본문 82,160–1216,648 · 상자 34 | `mi/L_MI_VN_C.dc.html` |
## Value Props (`vp`)

| 코드 | 이름 | 역할 | 업종 · 솔루션 | 상태 | 아키타입 | 칸 | 배치 | 원본 보드 |
|---|---|---|---|---|---|---|---|---|
| `CH-A` | 과제 3 + 영향 | `CH` |  | ready | `challenge_cards` | `title*` text · `items*` card{no,tag,title,body,quote,who,kpi}×3 | 본문 64,136–1216,648 · 상자 8 | `vp/L_CH_A.dc.html` |
| `CH-B` | 지금 → 바라는 모습 | `CH` |  | ready | `rows_arrow` | `title*` text · `subtitle` text · `rows*` card{label,left,right}×4 · `headers` text×3 | 본문 64,172–1204,648 · 상자 30 | `vp/L_CH_B.dc.html` |
| `CH-C` | 문제 → 근본 원인 | `CH` |  | ready | `tree` | `title*` text · `subtitle` text · `headers` text×3 · `root*` card{tag,title,kpi,note} · `branches*` card{no,title,body}×3 · `leaves*` card{title,body,tag}×3 | 본문 64,160–1216,648 · 상자 25 | `vp/L_CH_C.dc.html` |
| `VP-AD-A` | 옥외 광고 · 과제 → 해법 → 효과 | `CH` | AD 옥외 광고 | in_production | `chain_rows` | `title*` text · `rows*` card{left,mid,right,kpi,left_sub}×3 · `headers` text×3 | 본문 64,136–1216,648 · 상자 23 | `vp/—` |
| `VP-ED-A` | 교육 · 캠퍼스 · 과제 → 해법 → 효과 | `CH` | ED 교육 · 캠퍼스 | in_production | `chain_rows` | `title*` text · `rows*` card{left,mid,right,kpi,left_sub}×3 · `headers` text×3 | 본문 64,136–1216,648 · 상자 23 | `vp/—` |
| `VP-FB-A` | 외식 · 카페 · 과제 → 해법 → 효과 | `CH` | FB 외식 · 카페 | in_production | `chain_rows` | `title*` text · `rows*` card{left,mid,right,kpi,left_sub}×3 · `headers` text×3 | 본문 64,136–1216,648 · 상자 23 | `vp/—` |
| `VP-FN-A` | 금융 · 과제 → 해법 → 효과 | `CH` | FN 금융 | in_production | `chain_rows` | `title*` text · `rows*` card{left,mid,right,kpi,left_sub}×3 · `headers` text×3 | 본문 64,136–1216,648 · 상자 23 | `vp/—` |
| `VP-HT-A` | 호텔 · 리조트 · 과제 → 해법 → 효과 | `CH` | HT 호텔 · 리조트 | in_production | `chain_rows` | `title*` text · `rows*` card{left,mid,right,kpi,left_sub}×3 · `headers` text×3 | 본문 64,136–1216,648 · 상자 23 | `vp/—` |
| `VP-ID-A` | 인테리어 · 빌트인 · 과제 → 해법 → 효과 | `CH` | ID 인테리어 · 빌트인 | in_production | `chain_rows` | `title*` text · `rows*` card{left,mid,right,kpi,left_sub}×3 · `headers` text×3 | 본문 64,136–1216,648 · 상자 23 | `vp/—` |
| `VP-MD-A` | 의료 · 요양 · 과제 → 해법 → 효과 | `CH` | MD 의료 · 요양 | in_production | `chain_rows` | `title*` text · `rows*` card{left,mid,right,kpi,left_sub}×3 · `headers` text×3 | 본문 64,136–1216,648 · 상자 23 | `vp/—` |
| `VP-MF-A` | 제조 · 물류 · 현장 · 과제 → 해법 → 효과 | `CH` | MF 제조 · 물류 · 현장 | in_production | `chain_rows` | `title*` text · `rows*` card{left,mid,right,kpi,left_sub}×3 · `headers` text×3 | 본문 64,136–1216,648 · 상자 23 | `vp/—` |
| `VP-OE-A` | 파트너 전용 단말 · 과제 → 해법 → 효과 | `CH` | OE 파트너 전용 단말 | in_production | `chain_rows` | `title*` text · `rows*` card{left,mid,right,kpi,left_sub}×3 · `headers` text×3 | 본문 64,136–1216,648 · 상자 23 | `vp/—` |
| `VP-OF-A` | 오피스 · 과제 → 해법 → 효과 | `CH` | OF 오피스 | in_production | `chain_rows` | `title*` text · `rows*` card{left,mid,right,kpi,left_sub}×3 · `headers` text×3 | 본문 64,136–1216,648 · 상자 23 | `vp/—` |
| `VP-PB-A` | 공공 · 교통 · 과제 → 해법 → 효과 | `CH` | PB 공공 · 교통 | in_production | `chain_rows` | `title*` text · `rows*` card{left,mid,right,kpi,left_sub}×3 · `headers` text×3 | 본문 64,136–1216,648 · 상자 23 | `vp/—` |
| `VP-RS-A` | 주거 분양 · 과제 → 해법 → 효과 | `CH` | RS 주거 분양 | in_production | `chain_rows` | `title*` text · `rows*` card{left,mid,right,kpi,left_sub}×3 · `headers` text×3 | 본문 64,136–1216,648 · 상자 23 | `vp/—` |
| `VP-RT-A` | 리테일 · 플래그십 · 과제 → 해법 → 효과 | `CH` | RT 리테일 · 플래그십 | in_production | `chain_rows` | `title*` text · `rows*` card{left,mid,right,kpi,left_sub}×3 · `headers` text×3 | 본문 64,136–1216,648 · 상자 23 | `vp/—` |
| `VP-SV-A` | 생활 편의 · 무인 매장 · 과제 → 해법 → 효과 | `CH` | SV 생활 편의 · 무인 매장 | in_production | `chain_rows` | `title*` text · `rows*` card{left,mid,right,kpi,left_sub}×3 · `headers` text×3 | 본문 64,136–1216,648 · 상자 23 | `vp/—` |
| `VP-TP-A` | 테마파크 · 전시 · 과제 → 해법 → 효과 | `CH` | TP 테마파크 · 전시 | in_production | `chain_rows` | `title*` text · `rows*` card{left,mid,right,kpi,left_sub}×3 · `headers` text×3 | 본문 64,136–1216,648 · 상자 23 | `vp/—` |
| `VP-VN-A` | 공연장 · 경기장 · 과제 → 해법 → 효과 | `CH` | VN 공연장 · 경기장 | in_production | `chain_rows` | `title*` text · `rows*` card{left,mid,right,kpi,left_sub}×3 · `headers` text×3 | 본문 64,136–1216,648 · 상자 23 | `vp/—` |
| `EF-A` | KPI 전 → 후 | `EF` |  | ready | `kpi_rows` | `title*` text · `subtitle` text · `rows*` card{title,body,before,after,change}×4 · `headers` text×4 | 본문 64,168–1216,624 · 상자 34 | `vp/L_EF_A.dc.html` |
| `EF-B` | 투자 회수 | `EF` |  | ready | `roi` | `title*` text · `subtitle` text · `chart*` chart · `chart_title` text · `stats` kpi×3 · `assumptions` caption | 본문 88,168–1216,640 · 상자 13 | `vp/L_EF_B.dc.html` |
| `EF-C` | 정량 + 정성 효과 | `EF` |  | ready | `quant_qual` | `title*` text · `headers` text×2 · `kpis` kpi×4 · `feels*` card{no,title,body,who}×4 | 본문 64,136–1216,648 · 상자 15 | `vp/L_EF_C.dc.html` |
| `EF-D` | 제품별 기대 효과 | `EF` |  | ready | `pillars` | `title*` text · `pillars*` card{no,tag,title,body,kpi,image}×3 | 본문 64,136–1216,648 · 상자 8 | `vp/L_EF_D.dc.html` |
| `EF-E` | 기대 효과 + 매달 확인할 실제 화면 | `EF` |  | ready | `pillars` | `title*` text · `pillars*` card{no,tag,title,body,kpi,image}×3 | 본문 64,136–1216,648 · 상자 8 | `vp/L_EF_E.dc.html` |
| `VP-AD-C` | 옥외 광고 · 기대 효과 | `EF` | AD 옥외 광고 | in_production | `kpi_rows` | `title*` text · `subtitle` text · `rows*` card{title,body,before,after,change}×4 · `headers` text×4 | 본문 64,168–1216,624 · 상자 34 | `vp/—` |
| `VP-ED-C` | 교육 · 캠퍼스 · 기대 효과 | `EF` | ED 교육 · 캠퍼스 | in_production | `kpi_rows` | `title*` text · `subtitle` text · `rows*` card{title,body,before,after,change}×4 · `headers` text×4 | 본문 64,168–1216,624 · 상자 34 | `vp/—` |
| `VP-FB-C` | 외식 · 카페 · 기대 효과 | `EF` | FB 외식 · 카페 | in_production | `kpi_rows` | `title*` text · `subtitle` text · `rows*` card{title,body,before,after,change}×4 · `headers` text×4 | 본문 64,168–1216,624 · 상자 34 | `vp/—` |
| `VP-FN-C` | 금융 · 기대 효과 | `EF` | FN 금융 | in_production | `kpi_rows` | `title*` text · `subtitle` text · `rows*` card{title,body,before,after,change}×4 · `headers` text×4 | 본문 64,168–1216,624 · 상자 34 | `vp/—` |
| `VP-HT-C` | 호텔 · 리조트 · 기대 효과 | `EF` | HT 호텔 · 리조트 | in_production | `kpi_rows` | `title*` text · `subtitle` text · `rows*` card{title,body,before,after,change}×4 · `headers` text×4 | 본문 64,168–1216,624 · 상자 34 | `vp/—` |
| `VP-ID-C` | 인테리어 · 빌트인 · 기대 효과 | `EF` | ID 인테리어 · 빌트인 | in_production | `kpi_rows` | `title*` text · `subtitle` text · `rows*` card{title,body,before,after,change}×4 · `headers` text×4 | 본문 64,168–1216,624 · 상자 34 | `vp/—` |
| `VP-MD-C` | 의료 · 요양 · 기대 효과 | `EF` | MD 의료 · 요양 | in_production | `kpi_rows` | `title*` text · `subtitle` text · `rows*` card{title,body,before,after,change}×4 · `headers` text×4 | 본문 64,168–1216,624 · 상자 34 | `vp/—` |
| `VP-MF-C` | 제조 · 물류 · 현장 · 기대 효과 | `EF` | MF 제조 · 물류 · 현장 | in_production | `kpi_rows` | `title*` text · `subtitle` text · `rows*` card{title,body,before,after,change}×4 · `headers` text×4 | 본문 64,168–1216,624 · 상자 34 | `vp/—` |
| `VP-OE-C` | 파트너 전용 단말 · 기대 효과 | `EF` | OE 파트너 전용 단말 | in_production | `kpi_rows` | `title*` text · `subtitle` text · `rows*` card{title,body,before,after,change}×4 · `headers` text×4 | 본문 64,168–1216,624 · 상자 34 | `vp/—` |
| `VP-OF-C` | 오피스 · 기대 효과 | `EF` | OF 오피스 | in_production | `kpi_rows` | `title*` text · `subtitle` text · `rows*` card{title,body,before,after,change}×4 · `headers` text×4 | 본문 64,168–1216,624 · 상자 34 | `vp/—` |
| `VP-PB-C` | 공공 · 교통 · 기대 효과 | `EF` | PB 공공 · 교통 | in_production | `kpi_rows` | `title*` text · `subtitle` text · `rows*` card{title,body,before,after,change}×4 · `headers` text×4 | 본문 64,168–1216,624 · 상자 34 | `vp/—` |
| `VP-RS-C` | 주거 분양 · 기대 효과 | `EF` | RS 주거 분양 | in_production | `kpi_rows` | `title*` text · `subtitle` text · `rows*` card{title,body,before,after,change}×4 · `headers` text×4 | 본문 64,168–1216,624 · 상자 34 | `vp/—` |
| `VP-RT-C` | 리테일 · 플래그십 · 기대 효과 | `EF` | RT 리테일 · 플래그십 | in_production | `kpi_rows` | `title*` text · `subtitle` text · `rows*` card{title,body,before,after,change}×4 · `headers` text×4 | 본문 64,168–1216,624 · 상자 34 | `vp/—` |
| `VP-SV-C` | 생활 편의 · 무인 매장 · 기대 효과 | `EF` | SV 생활 편의 · 무인 매장 | in_production | `kpi_rows` | `title*` text · `subtitle` text · `rows*` card{title,body,before,after,change}×4 · `headers` text×4 | 본문 64,168–1216,624 · 상자 34 | `vp/—` |
| `VP-TP-C` | 테마파크 · 전시 · 기대 효과 | `EF` | TP 테마파크 · 전시 | in_production | `kpi_rows` | `title*` text · `subtitle` text · `rows*` card{title,body,before,after,change}×4 · `headers` text×4 | 본문 64,168–1216,624 · 상자 34 | `vp/—` |
| `VP-VN-C` | 공연장 · 경기장 · 기대 효과 | `EF` | VN 공연장 · 경기장 | in_production | `kpi_rows` | `title*` text · `subtitle` text · `rows*` card{title,body,before,after,change}×4 · `headers` text×4 | 본문 64,168–1216,624 · 상자 34 | `vp/—` |
| `VP-A` | 과제 ↔ 해결 1:1 | `VP` |  | ready | `rows_arrow` | `title*` text · `rows*` card{label,left,right}×3 · `headers` text×3 | 본문 64,148–1204,648 · 상자 24 | `vp/L_VP01.dc.html` |
| `VP-B2` | 가치 기둥 2 | `VP` |  | ready | `pillars` | `title*` text · `pillars*` card{no,tag,title,body,kpi}×2 | 본문 64,136–1216,648 · 상자 7 | `vp/L_VP02.dc.html` |
| `VP-B3` | 가치 기둥 3 | `VP` |  | ready | `pillars` | `title*` text · `pillars*` card{no,tag,title,body,kpi}×3 | 본문 64,136–1216,648 · 상자 8 | `vp/L_VP03.dc.html` |
| `VP-B4` | 가치 기둥 4 | `VP` |  | ready | `pillars` | `title*` text · `pillars*` card{no,tag,title,body,kpi}×4 | 본문 64,136–1216,648 · 상자 9 | `vp/L_VP04.dc.html` |
| `VP-C` | 한 문장 + 근거 3 | `VP` |  | ready | `statement` | `title*` text · `message*` text · `message_sub` text · `proofs*` card{kpi,title,body}×3 | 본문 64,156–1216,648 · 상자 10 | `vp/L_VP05.dc.html` |
| `VP-D` | 이해관계자별 가치 | `VP` |  | ready | `personas` | `title*` text · `people*` card{role,name,body,bullets,quote,kpi}×3 · `message` text | 본문 64,138–1216,648 · 상자 9 | `vp/L_VP_D.dc.html` |
| `VP-E` | 과제 → 제품 → 가치 | `VP` |  | ready | `chain_rows` | `title*` text · `rows*` card{left,mid,right,kpi,image,left_sub}×3 · `headers` text×3 | 본문 64,136–1216,648 · 상자 26 | `vp/L_VP_E.dc.html` |
| `VP-F2` | 가치 기둥 × 제품 · 2개 | `VP` |  | ready | `pillars` | `title*` text · `pillars*` card{no,tag,title,body,kpi,image}×2 | 본문 64,136–1216,648 · 상자 7 | `vp/L_VP_F2.dc.html` |
| `VP-F3` | 가치 기둥 × 제품 · 3개 (기둥 수 n으로 2 · 3 · 4) | `VP` |  | ready | `pillars` | `title*` text · `pillars*` card{no,tag,title,body,kpi,image}×3 | 본문 64,136–1216,648 · 상자 8 | `vp/L_VP_F.dc.html` |
| `VP-F4` | 가치 기둥 × 제품 · 4개 (2×2) | `VP` |  | ready | `pillars` | `title*` text · `pillars*` card{no,tag,title,body,kpi,image}×4 | 본문 64,136–1216,648 · 상자 9 | `vp/L_VP_F4.dc.html` |
| `VP-G` | 한 문장 + 제품 히어로 | `VP` |  | ready | `statement` | `title*` text · `message*` text · `message_sub` text · `proofs*` card{kpi,title,body}×3 · `image*` image:C · `products` card{title,image}×3 | 본문 64,114–1216,648 · 상자 15 | `vp/L_VP_G.dc.html` |
| `VP-H` | 이해관계자 × 만나는 화면 | `VP` |  | ready | `personas` | `title*` text · `people*` card{role,name,body,bullets,quote,kpi,image}×4 · `message` text | 본문 64,138–1216,648 · 상자 10 | `vp/L_VP_H.dc.html` |
| `VP-I` | 제품 콜아웃 | `VP` |  | ready | `image_pins` | `title*` text · `image*` image:C · `pins*` card{no,title,body,tag,x,y}×4 | 본문 64,136–1216,648 · 상자 11 | `vp/L_VP_I.dc.html` |
| `VP-J` | 솔루션 화면 + 연결 제품 | `VP` |  | ready | `image_pins` | `title*` text · `image*` image:B · `pins*` card{no,title,body,tag,x,y}×4 | 본문 64,136–1216,648 · 상자 11 | `vp/L_VP_J.dc.html` |
| `VP-K` | 공간 속 제품 | `VP` |  | ready | `image_pins_wide` | `title*` text · `image*` image:A · `pins*` card{no,title,body,x,y}×5 | 본문 64,128–1216,648 · 상자 16 | `vp/L_VP_K.dc.html` |
| `VP-L` | 도입 전 → 후 | `VP` |  | ready | `two_images` | `title*` text · `sides*` card{tag,title,body,bullets,image}×2 · `labels` text×2 · `message` text · `message_label` text | 본문 64,136–1216,638 · 상자 15 | `vp/L_VP_L.dc.html` |
| `VP-M` | 제품 × 가치 매트릭스 | `VP` |  | ready | `matrix` | `title*` text · `table*` table | 본문 64,136–1216,648 · 상자 6 | `vp/L_VP_M.dc.html` |
| `VP-N` | 실사 히어로 + 가치 3 | `VP` |  | ready | `hero_panel` | `title*` text · `image*` image:A · `image_caption` caption · `message` text · `items*` card{no,tag,title,body,kpi,image}×3 | 본문 0,0–1216,720 · 상자 11 | `vp/L_VP_N.dc.html` |
| `VP-O` | 제품 라인업 실사 | `VP` |  | ready | `pillars` | `title*` text · `pillars*` card{no,tag,title,body,kpi,image}×4 | 본문 64,136–1216,648 · 상자 9 | `vp/L_VP_O.dc.html` |
| `VP-P` | 솔루션 실제 화면 + 주석 | `VP` |  | ready | `image_pins` | `title*` text · `image*` image:B · `pins*` card{no,title,body,tag,x,y}×3 | 본문 64,136–1216,648 · 상자 10 | `vp/L_VP_P.dc.html` |
| `VP-Q` | 레퍼런스 사례 | `VP` |  | ready | `hero_panel` | `title*` text · `image*` image:A · `image_caption` caption · `message` text · `items*` card{no,tag,title,body,kpi,image}×3 | 본문 64,136–1216,648 · 상자 11 | `vp/L_VP_Q.dc.html` |
| `VP-R` | 실사 동선 투어 | `VP` |  | ready | `path_strip` | `title*` text · `steps*` card{no,title,body,chips,image}×4 · `message` text | 본문 64,136–1216,638 · 상자 14 | `vp/L_VP_R.dc.html` |
| `VP-S` | 고객 매장 사진 → 도입 후 실사 (VP-L의 실사판) | `VP` |  | ready | `two_images` | `title*` text · `sides*` card{tag,title,body,bullets,image}×2 · `labels` text×2 · `message` text · `message_label` text | 본문 64,136–1216,638 · 상자 15 | `vp/L_VP_S.dc.html` |
| `VP-T` | 제품 실사 + 공식 연출 + 근거 스펙 (VP-I의 실사판) | `VP` |  | ready | `hero_panel` | `title*` text · `image*` image:C · `image_caption` caption · `message` text · `items*` card{no,tag,title,body,kpi,image}×3 | 본문 64,136–1216,648 · 상자 11 | `vp/L_VP_T.dc.html` |
| `VP-U` | 현장 질문 → 제품 · 솔루션 → 핵심 가치 + 키워드 | `VP` |  | ready | `chain_rows` | `title*` text · `rows*` card{left,mid,right,kpi,image,chips,left_sub}×3 · `headers` text×3 | 본문 64,136–1216,648 · 상자 26 | `vp/L_VP_U.dc.html` |
| `VP-UC` | 현장 질문 · 열형 | `VP` |  | ready | `pillars` | `title*` text · `pillars*` card{no,tag,title,body,kpi,image}×3 | 본문 64,136–1216,648 · 상자 8 | `vp/L_VP_UC.dc.html` |
| `VP-US` | 매장 실사 위 질문 핀 | `VP` |  | ready | `image_pins` | `title*` text · `image*` image:A · `pins*` card{no,title,body,tag,x,y}×3 | 본문 64,136–1216,648 · 상자 10 | `vp/L_VP_US.dc.html` |
| `VP-AD-B` | 옥외 광고 · 이해관계자별 가치 | `VP` | AD 옥외 광고 | in_production | `personas` | `title*` text · `people*` card{role,name,body,bullets,quote,kpi}×3 · `message` text | 본문 64,138–1216,648 · 상자 9 | `vp/—` |
| `VP-ED-B` | 교육 · 캠퍼스 · 이해관계자별 가치 | `VP` | ED 교육 · 캠퍼스 | in_production | `personas` | `title*` text · `people*` card{role,name,body,bullets,quote,kpi}×3 · `message` text | 본문 64,138–1216,648 · 상자 9 | `vp/—` |
| `VP-FB-B` | 외식 · 카페 · 이해관계자별 가치 | `VP` | FB 외식 · 카페 | in_production | `personas` | `title*` text · `people*` card{role,name,body,bullets,quote,kpi}×3 · `message` text | 본문 64,138–1216,648 · 상자 9 | `vp/—` |
| `VP-FN-B` | 금융 · 이해관계자별 가치 | `VP` | FN 금융 | in_production | `personas` | `title*` text · `people*` card{role,name,body,bullets,quote,kpi}×3 · `message` text | 본문 64,138–1216,648 · 상자 9 | `vp/—` |
| `VP-HT-B` | 호텔 · 리조트 · 이해관계자별 가치 | `VP` | HT 호텔 · 리조트 | in_production | `personas` | `title*` text · `people*` card{role,name,body,bullets,quote,kpi}×3 · `message` text | 본문 64,138–1216,648 · 상자 9 | `vp/—` |
| `VP-ID-B` | 인테리어 · 빌트인 · 이해관계자별 가치 | `VP` | ID 인테리어 · 빌트인 | in_production | `personas` | `title*` text · `people*` card{role,name,body,bullets,quote,kpi}×3 · `message` text | 본문 64,138–1216,648 · 상자 9 | `vp/—` |
| `VP-MD-B` | 의료 · 요양 · 이해관계자별 가치 | `VP` | MD 의료 · 요양 | in_production | `personas` | `title*` text · `people*` card{role,name,body,bullets,quote,kpi}×3 · `message` text | 본문 64,138–1216,648 · 상자 9 | `vp/—` |
| `VP-MF-B` | 제조 · 물류 · 현장 · 이해관계자별 가치 | `VP` | MF 제조 · 물류 · 현장 | in_production | `personas` | `title*` text · `people*` card{role,name,body,bullets,quote,kpi}×3 · `message` text | 본문 64,138–1216,648 · 상자 9 | `vp/—` |
| `VP-OE-B` | 파트너 전용 단말 · 이해관계자별 가치 | `VP` | OE 파트너 전용 단말 | in_production | `personas` | `title*` text · `people*` card{role,name,body,bullets,quote,kpi}×3 · `message` text | 본문 64,138–1216,648 · 상자 9 | `vp/—` |
| `VP-OF-B` | 오피스 · 이해관계자별 가치 | `VP` | OF 오피스 | in_production | `personas` | `title*` text · `people*` card{role,name,body,bullets,quote,kpi}×3 · `message` text | 본문 64,138–1216,648 · 상자 9 | `vp/—` |
| `VP-PB-B` | 공공 · 교통 · 이해관계자별 가치 | `VP` | PB 공공 · 교통 | in_production | `personas` | `title*` text · `people*` card{role,name,body,bullets,quote,kpi}×3 · `message` text | 본문 64,138–1216,648 · 상자 9 | `vp/—` |
| `VP-RS-B` | 주거 분양 · 이해관계자별 가치 | `VP` | RS 주거 분양 | in_production | `personas` | `title*` text · `people*` card{role,name,body,bullets,quote,kpi}×3 · `message` text | 본문 64,138–1216,648 · 상자 9 | `vp/—` |
| `VP-RT-B` | 리테일 · 플래그십 · 이해관계자별 가치 | `VP` | RT 리테일 · 플래그십 | in_production | `personas` | `title*` text · `people*` card{role,name,body,bullets,quote,kpi}×3 · `message` text | 본문 64,138–1216,648 · 상자 9 | `vp/—` |
| `VP-SV-B` | 생활 편의 · 무인 매장 · 이해관계자별 가치 | `VP` | SV 생활 편의 · 무인 매장 | in_production | `personas` | `title*` text · `people*` card{role,name,body,bullets,quote,kpi}×3 · `message` text | 본문 64,138–1216,648 · 상자 9 | `vp/—` |
| `VP-TP-B` | 테마파크 · 전시 · 이해관계자별 가치 | `VP` | TP 테마파크 · 전시 | in_production | `personas` | `title*` text · `people*` card{role,name,body,bullets,quote,kpi}×3 · `message` text | 본문 64,138–1216,648 · 상자 9 | `vp/—` |
| `VP-U-HT` | 현장 질문 → 제품 · 솔루션 → 핵심 가치 + 키워드 · 호텔 · 리조트 | `VP` | HT 호텔 · 리조트 | ready | `chain_rows` | `title*` text · `rows*` card{left,mid,right,kpi,image,chips,left_sub}×3 · `headers` text×3 | 본문 64,136–1216,648 · 상자 26 | `vp/L_VP_U_HT.dc.html` |
| `VP-U-MD` | 현장 질문 → 제품 · 솔루션 → 핵심 가치 + 키워드 · 의료 · 요양 | `VP` | MD 의료 · 요양 | ready | `chain_rows` | `title*` text · `rows*` card{left,mid,right,kpi,image,chips,left_sub}×3 · `headers` text×3 | 본문 64,136–1216,648 · 상자 26 | `vp/L_VP_U_MD.dc.html` |
| `VP-UC-RT` | 현장 질문 · 열형 · 리테일 · 플래그십 | `VP` | RT 리테일 · 플래그십 | ready | `pillars` | `title*` text · `pillars*` card{no,tag,title,body,kpi,image}×3 | 본문 64,136–1216,648 · 상자 8 | `vp/L_VP_UC_RT.dc.html` |
| `VP-VN-B` | 공연장 · 경기장 · 이해관계자별 가치 | `VP` | VN 공연장 · 경기장 | in_production | `personas` | `title*` text · `people*` card{role,name,body,bullets,quote,kpi}×3 · `message` text | 본문 64,138–1216,648 · 상자 9 | `vp/—` |
## 조감도 (`birdseye`)

| 코드 | 이름 | 역할 | 업종 · 솔루션 | 상태 | 아키타입 | 칸 | 배치 | 원본 보드 |
|---|---|---|---|---|---|---|---|---|
| `BV-A` | 풀폭 전경 | `BV` |  | ready | `full_image` | `title*` text · `image*` image:A · `caption` text · `details` text · `legend` bullets×3 | 본문 64,128–1216,636 · 상자 9 | `common/L_BE01.dc.html` |
| `BV-B` | 두 시점 비교 | `BV` |  | ready | `two_images` | `title*` text · `sides*` card{tag,title,body,bullets,image}×2 · `labels` text×2 | 본문 64,136–1216,648 · 상자 12 | `common/L_BE03.dc.html` |
| `BV-C` | 전경 + 한 장 요약 | `BV` |  | ready | `hero_panel` | `title*` text · `image*` image:A · `image_caption` caption · `message` text · `items*` card{no,tag,title,body,kpi,image}×3 | 본문 64,136–1216,648 · 상자 11 | `common/L_BV_C.dc.html` |
| `BV-D` | 시점 투어 · 평면도 + 렌더 4 | `BV` |  | ready | `plan_grid` | `title*` text · `subtitle` text · `image*` image:D · `zones*` card{no,title,body,image,chips,x,y}×4 | 본문 64,160–1216,648 · 상자 12 | `common/L_BV_D.dc.html` |
| `GN-A` | 배치 시안 3안 | `GN` |  | ready | `options3` | `title*` text · `subtitle` text · `options*` card{tag,title,body,bullets,kpi,image}×3 · `recommended` number | 본문 64,160–1216,648 · 상자 9 | `common/L_GN_A.dc.html` |
| `GN-B` | 현재 ↔ 시안 와이프 | `GN` |  | ready | `two_images` | `title*` text · `sides*` card{tag,title,body,bullets,image}×2 · `labels` text×2 · `message` text · `message_label` text | 본문 64,136–1216,638 · 상자 15 | `common/L_GN_B.dc.html` |
| `GN-C` | 공간별 지금 → 제안 시안 | `GN` |  | ready | `rows_images` | `title*` text · `subtitle` text · `rows*` card{title,left,right,body,chips}×3 · `headers` text×2 | 본문 64,160–1216,648 · 상자 23 | `common/L_GN_C.dc.html` |
| `GN-D` | 화면 콘텐츠 시안 3 | `GN` |  | ready | `options3` | `title*` text · `subtitle` text · `options*` card{tag,title,body,bullets,kpi,image}×3 · `recommended` number | 본문 64,160–1216,648 · 상자 9 | `common/L_GN_D.dc.html` |
| `IS-A` | 현장 조사 · 사진 모자이크 | `IS` |  | ready | `image_grid` | `title*` text · `subtitle` text · `items*` card{image,title,body,chips,tag}×6 | 본문 64,160–1216,648 · 상자 12 | `common/L_IS_A.dc.html` |
| `IS-B` | 실측 오버레이 · 설치 조건 | `IS` |  | ready | `image_pins` | `title*` text · `subtitle` text · `image*` image:A · `pins*` card{no,title,body,tag,x,y}×4 | 본문 64,160–1216,648 · 상자 12 | `common/L_IS_B.dc.html` |
| `MB-A` | 무드보드 · 공간 톤 | `MB` |  | ready | `moodboard` | `title*` text · `subtitle` text · `images` image:A×5 · `swatches` text×5 · `points*` card{no,title,body}×3 | 본문 64,160–1216,648 · 상자 19 | `common/L_MB_A.dc.html` |
| `MB-B` | 마감 · 소재 매칭 | `MB` |  | ready | `rows_images` | `title*` text · `subtitle` text · `rows*` card{title,left,right,body,chips}×3 · `headers` text×2 | 본문 64,160–1216,648 · 상자 23 | `common/L_MB_B.dc.html` |
| `ZP-A` | 번호 콜아웃 | `ZP` |  | ready | `image_pins` | `title*` text · `subtitle` text · `image*` image:A · `pins*` card{no,title,body,tag,x,y}×4 | 본문 64,160–1216,648 · 상자 12 | `common/L_BE02.dc.html` |
| `ZP-B` | 존 확대 컷 | `ZP` |  | ready | `plan_grid` | `title*` text · `subtitle` text · `image*` image:D · `zones*` card{no,title,body,image,chips,x,y}×4 | 본문 64,160–1216,648 · 상자 12 | `common/L_ZP_B.dc.html` |
| `ZP-C` | 고객 동선 따라가기 | `ZP` |  | ready | `image_pins_wide` | `title*` text · `subtitle` text · `image*` image:A · `pins*` card{no,title,body,x,y}×4 | 본문 64,152–1216,648 · 상자 15 | `common/L_ZP_C.dc.html` |
| `ZP-D` | 실사 핫스팟 · 제품 카드 | `ZP` |  | ready | `image_pins` | `title*` text · `image*` image:A · `pins*` card{no,title,body,tag,x,y}×4 | 본문 64,136–1216,648 · 상자 11 | `common/L_ZP_D.dc.html` |
## 공간별 제품 (`space_products`)

| 코드 | 이름 | 역할 | 업종 · 솔루션 | 상태 | 아키타입 | 칸 | 배치 | 원본 보드 |
|---|---|---|---|---|---|---|---|---|
| `BM-A` | 전체 구성표 | `BM` |  | ready | `table` | `title*` text · `subtitle` text · `table*` table · `message` text | 본문 64,160–1216,636 · 상자 9 | `pi/L_BM_A.dc.html` |
| `BM-B` | 매장 유형별 구성 | `BM` |  | ready | `types_cols` | `title*` text · `types*` card{tag,title,body,bullets,kpi,note}×3 · `total` text | 본문 64,136–1216,636 · 상자 10 | `pi/L_BM_B.dc.html` |
| `BM-C` | 반복 유닛 + 공용부 | `BM` |  | ready | `unit_kit` | `title*` text · `kit*` card{title,body,bullets,image} · `multiplier` kpi · `common` card{title,body,bullets} · `table*` table | 본문 64,136–1216,648 · 상자 10 | `pi/L_BM_C.dc.html` |
| `BM-D` | 단계별 도입 물량 | `BM` |  | ready | `timeline` | `title*` text · `subtitle` text · `steps*` card{when,title,body,tag}×3 · `message` text · `message_label` text | 본문 64,232–1216,632 · 상자 16 | `pi/L_BM_D.dc.html` |
| `BM-E` | 지역별 물량 | `BM` |  | ready | `map_table` | `title*` text · `subtitle` text · `image` image:D · `regions` card{title,kpi}×6 · `table*` table | 본문 64,160–1216,608 · 상자 9 | `pi/L_BM_E.dc.html` |
| `P-E` | 정면 입면도 · 치수 | `PI` |  | ready | `drawing` | `title*` text · `subtitle` text · `image*` image:D · `table*` table · `kpis` kpi×3 | 본문 84,160–1216,648 · 상자 12 | `pi/L_P_E.dc.html` |
| `P-F` | 시야 거리 단면 | `PI` |  | ready | `drawing` | `title*` text · `subtitle` text · `image*` image:D · `table*` table · `kpis` kpi×3 | 본문 84,160–1216,648 · 상자 12 | `pi/L_P_F.dc.html` |
| `P-G` | 설치 방식 옵션 | `PI` |  | ready | `options3` | `title*` text · `subtitle` text · `options*` card{tag,title,body,bullets,kpi,image}×3 · `recommended` number | 본문 64,160–1216,648 · 상자 9 | `pi/L_P_G.dc.html` |
| `P-H` | 커버리지 평면 | `PI` |  | ready | `image_pins` | `title*` text · `subtitle` text · `image*` image:D · `pins*` card{no,title,body,tag,x,y}×4 | 본문 64,160–1216,648 · 상자 12 | `pi/L_P_H.dc.html` |
| `P-I` | 무드 컷 · 풀블리드 | `PI` |  | ready | `mood_full` | `title*` text · `subtitle` text · `image*` image:A · `products` card{title,body}×3 | 본문 0,0–1280,720 · 상자 9 | `pi/L_P_I.dc.html` |
| `P-J` | 제품 디테일 콜아웃 | `PI` |  | ready | `image_pins` | `title*` text · `subtitle` text · `image*` image:C · `pins*` card{no,title,body,tag,x,y}×4 | 본문 64,160–1216,648 · 상자 12 | `pi/L_P_J.dc.html` |
| `P-K` | 공간 조건 → 대응 사양 | `PI` |  | ready | `rows_arrow` | `title*` text · `subtitle` text · `rows*` card{label,left,right}×4 · `headers` text×3 | 본문 64,172–1204,648 · 상자 30 | `pi/L_P_K.dc.html` |
| `P-L` | 비디오월 · LED 구성 | `PI` |  | ready | `drawing` | `title*` text · `subtitle` text · `image*` image:D · `table*` table · `kpis` kpi×3 | 본문 84,160–1216,648 · 상자 12 | `pi/L_P_L.dc.html` |
| `P-M` | 수량 · 용량 산정 근거 | `PI` |  | ready | `table` | `title*` text · `subtitle` text · `table*` table · `message` text | 본문 64,160–1216,636 · 상자 9 | `pi/L_P_M.dc.html` |
| `P-N` | 기존 장비 → 교체 매핑 | `PI` |  | ready | `rows_arrow` | `title*` text · `subtitle` text · `rows*` card{label,left,right,image}×4 · `headers` text×3 | 본문 64,172–1204,648 · 상자 34 | `pi/L_P_N.dc.html` |
| `P-O` | 구성 3안 (기본 · 권장 · 확장) | `PI` |  | ready | `options3` | `title*` text · `subtitle` text · `options*` card{tag,title,body,bullets,kpi}×3 · `recommended` number | 본문 64,160–1216,648 · 상자 9 | `pi/L_P_O.dc.html` |
| `P-P` | 사용자별 접점 | `PI` |  | ready | `personas` | `title*` text · `people*` card{role,name,body,bullets,quote,kpi,image}×3 | 본문 64,136–1216,648 · 상자 8 | `pi/L_P_P.dc.html` |
| `P-Q` | 직무별 기기 키트 | `PI` |  | ready | `personas` | `title*` text · `people*` card{role,name,body,bullets,quote,kpi,image}×4 | 본문 64,136–1216,648 · 상자 9 | `pi/L_P_Q.dc.html` |
| `P-R` | 유닛 패키지 | `PI` |  | ready | `unit_kit` | `title*` text · `kit*` card{title,body,bullets,image} · `multiplier` kpi · `common` card{title,body,bullets} · `table*` table | 본문 64,136–1216,648 · 상자 10 | `pi/L_P_R.dc.html` |
| `P-S` | 한 제품 · 여러 공간 | `PI` |  | ready | `hero_panel` | `title*` text · `image*` image:C · `image_caption` caption · `message` text · `items*` card{no,tag,title,body,kpi,image}×4 | 본문 64,136–1216,648 · 상자 12 | `pi/L_P_S.dc.html` |
| `P-T` | 카탈로그 6~8개 | `PI` |  | ready | `image_grid` | `title*` text · `subtitle` text · `items*` card{image,title,body,chips,tag}×8 | 본문 64,160–1216,648 · 상자 14 | `pi/L_P_T.dc.html` |
| `P1-A` | 제품 1개 · 제품 이미지 중심 | `PI` |  | ready | `products` | `title*` text · `products*` card{tag,title,model,body,qty,bullets,kpi,image,x,y}×1 · `message` text | 본문 84,136–1216,648 · 상자 9 | `pi/L_P1A.dc.html` |
| `P1-B` | 제품 1개 · 공간 · 설치 중심 | `PI` |  | ready | `products` | `title*` text · `products*` card{tag,title,model,body,qty,bullets,kpi,image,x,y}×1 · `space_image*` image:A | 본문 64,128–1216,648 · 상자 7 | `pi/L_P1B.dc.html` |
| `P1-C` | 제품 1개 · 스펙 · 비교 중심 | `PI` |  | ready | `products` | `title*` text · `subtitle` text · `products*` card{tag,title,model,body,qty,bullets,kpi,image,x,y}×1 · `table*` table | 본문 64,160–1216,648 · 상자 8 | `pi/L_P1C.dc.html` |
| `P1-D` | 제품 1개 · 메시지 강조 | `PI` |  | ready | `products` | `title*` text · `products*` card{tag,title,model,body,qty,bullets,kpi,image,x,y}×1 · `message` text | 본문 64,156–1196,648 · 상자 9 | `pi/L_P1D.dc.html` |
| `P2-A` | 제품 2개 · 제품 이미지 중심 | `PI` |  | ready | `products` | `title*` text · `products*` card{tag,title,model,body,qty,bullets,kpi,image,x,y}×2 | 본문 64,136–1216,648 · 상자 7 | `pi/L_P2A.dc.html` |
| `P2-B` | 제품 2개 · 공간 · 설치 중심 | `PI` |  | ready | `products` | `title*` text · `products*` card{tag,title,model,body,qty,bullets,kpi,image,x,y}×2 · `space_image*` image:A | 본문 64,128–1216,648 · 상자 9 | `pi/L_P2B.dc.html` |
| `P2-C` | 제품 2개 · 스펙 · 비교 중심 | `PI` |  | ready | `products` | `title*` text · `subtitle` text · `products*` card{tag,title,model,body,qty,bullets,kpi,image,x,y}×2 · `table*` table | 본문 64,160–1216,648 · 상자 9 | `pi/L_P2C.dc.html` |
| `P2-D` | 제품 2개 · 강조형 | `PI` |  | ready | `products` | `title*` text · `products*` card{tag,title,model,body,qty,bullets,kpi,image,x,y}×2 | 본문 64,136–1216,648 · 상자 7 | `pi/L_P2D.dc.html` |
| `P3-A` | 제품 3개 · 제품 이미지 중심 | `PI` |  | ready | `products` | `title*` text · `products*` card{tag,title,model,body,qty,bullets,kpi,image,x,y}×3 | 본문 64,136–1216,648 · 상자 8 | `pi/L_P3A.dc.html` |
| `P3-B` | 제품 3개 · 공간 · 설치 중심 | `PI` |  | ready | `products` | `title*` text · `products*` card{tag,title,model,body,qty,bullets,kpi,image,x,y}×3 · `space_image*` image:A | 본문 64,136–1216,648 · 상자 10 | `pi/L_P3B.dc.html` |
| `P3-C` | 제품 3개 · 스펙 · 비교 중심 | `PI` |  | ready | `products` | `title*` text · `products*` card{tag,title,model,body,qty,bullets,kpi,image,x,y}×3 · `table*` table | 본문 64,146–1216,648 · 상자 10 | `pi/L_P3C.dc.html` |
| `P3-D` | 제품 3개 · 강조형 | `PI` |  | ready | `products` | `title*` text · `products*` card{tag,title,model,body,qty,bullets,kpi,image,x,y}×3 | 본문 64,136–1216,648 · 상자 8 | `pi/L_P3D.dc.html` |
| `P4-A` | 제품 4개 · 제품 이미지 중심 | `PI` |  | ready | `products` | `title*` text · `products*` card{tag,title,model,body,qty,bullets,kpi,image,x,y}×4 | 본문 64,136–1216,648 · 상자 9 | `pi/L_P4A.dc.html` |
| `P4-B` | 제품 4개 · 공간 · 설치 중심 | `PI` |  | ready | `products` | `title*` text · `products*` card{tag,title,model,body,qty,bullets,kpi,image,x,y}×4 · `space_image*` image:A | 본문 64,128–1216,648 · 상자 11 | `pi/L_P4B.dc.html` |
| `P4-C` | 제품 4개 · 스펙 · 비교 중심 | `PI` |  | ready | `products` | `title*` text · `products*` card{tag,title,model,body,qty,bullets,kpi,image,x,y}×4 | 본문 64,136–1216,648 · 상자 9 | `pi/L_P4C.dc.html` |
| `P4-D` | 제품 4개 · 강조형 | `PI` |  | ready | `products` | `title*` text · `products*` card{tag,title,model,body,qty,bullets,kpi,image,x,y}×4 | 본문 64,136–1216,648 · 상자 9 | `pi/L_P4D.dc.html` |
| `P5-A` | 제품 5개 · 제품 이미지 중심 | `PI` |  | ready | `products` | `title*` text · `products*` card{tag,title,model,body,qty,bullets,kpi,image,x,y}×5 | 본문 64,136–1216,648 · 상자 10 | `pi/L_P5A.dc.html` |
| `P5-B` | 제품 5개 · 공간 · 설치 중심 | `PI` |  | ready | `products` | `title*` text · `products*` card{tag,title,model,body,qty,bullets,kpi,image,x,y}×5 · `space_image*` image:A | 본문 64,128–1216,648 · 상자 12 | `pi/L_P5B.dc.html` |
| `P5-C` | 제품 5개 · 스펙 · 비교 중심 | `PI` |  | ready | `products` | `title*` text · `table*` table | 본문 64,136–1216,648 · 상자 6 | `pi/L_P5C.dc.html` |
| `P5-D` | 제품 5개 · 강조형 | `PI` |  | ready | `products` | `title*` text · `products*` card{tag,title,model,body,qty,bullets,kpi,image,x,y}×5 | 본문 64,136–1216,648 · 상자 10 | `pi/L_P5D.dc.html` |
| `SM-A` | 존 맵 + 목록 | `SM` |  | ready | `space_map` | `title*` text · `subtitle` text · `image` image:A · `spaces*` card{no,title,chips,body,x,y}×3 | 본문 64,160–1216,648 · 상자 11 | `pi/L_SP00.dc.html` |
| `SM-B` | 공간 × 제품 수량표 | `SM` |  | ready | `matrix` | `title*` text · `subtitle` text · `table*` table | 본문 64,160–1216,648 · 상자 7 | `pi/L_SM_B.dc.html` |
| `SM-C` | 동선 스트립 | `SM` |  | ready | `path_strip` | `title*` text · `subtitle` text · `steps*` card{no,title,body,chips,image}×5 · `message` text | 본문 64,160–1216,638 · 상자 17 | `pi/L_SM_C.dc.html` |
| `SM-D` | 층별 단면 | `SM` |  | ready | `floors` | `title*` text · `floors*` card{tag,title,chips,body}×6 · `message` text | 본문 64,136–1216,640 · 상자 13 | `pi/L_SM_D.dc.html` |
| `SM-E` | 공간 사진 카드 | `SM` |  | ready | `image_grid` | `title*` text · `subtitle` text · `items*` card{image,title,body,chips,tag}×6 | 본문 64,160–1216,648 · 상자 12 | `pi/L_SM_E.dc.html` |
## 솔루션 제안 (`solution`)

| 코드 | 이름 | 역할 | 업종 · 솔루션 | 상태 | 아키타입 | 칸 | 배치 | 원본 보드 |
|---|---|---|---|---|---|---|---|---|
| `OP-A` | 단계 타임라인 | `OP` |  | ready | `timeline` | `title*` text · `steps*` card{when,title,body,tag}×5 · `message` text · `message_label` text | 본문 64,208–1216,632 · 상자 19 | `common/L_SOL02.dc.html` |
| `OP-B` | 역할별 스윔레인 | `OP` |  | ready | `swimlane` | `title*` text · `subtitle` text · `lanes*` table | 본문 64,160–1216,648 · 상자 7 | `common/L_OP_B.dc.html` |
| `OP-C` | 도입 전 → 후 업무 | `OP` |  | ready | `steps_compare` | `title*` text · `subtitle` text · `labels` text×2 · `before*` card{title,days}×5 · `after` card{title,days}×5 · `summary` kpi×2 · `summary_title` text | 본문 84,178–1194,568 · 상자 24 | `common/L_OP_C.dc.html` |
| `SS-AD-C` | 옥외 광고 · 하루 · 동선 | `OP` | AD 옥외 광고 | ready | `swimlane` | `title*` text · `subtitle` text · `lanes*` table | 본문 64,160–1216,648 · 상자 7 | `ss/L_SS_AD_C.dc.html` |
| `SS-ED-C` | 교육 · 캠퍼스 · 하루 · 동선 | `OP` | ED 교육 · 캠퍼스 | ready | `swimlane` | `title*` text · `subtitle` text · `lanes*` table | 본문 64,160–1216,648 · 상자 7 | `ss/L_SS_ED_C.dc.html` |
| `SS-FB-C` | 외식 · 카페 · 하루 · 동선 | `OP` | FB 외식 · 카페 | ready | `swimlane` | `title*` text · `subtitle` text · `lanes*` table | 본문 64,160–1216,648 · 상자 7 | `ss/L_SS_FB_C.dc.html` |
| `SS-FN-C` | 금융 · 하루 · 동선 | `OP` | FN 금융 | ready | `swimlane` | `title*` text · `subtitle` text · `lanes*` table | 본문 64,160–1216,648 · 상자 7 | `ss/L_SS_FN_C.dc.html` |
| `SS-HT-C` | 호텔 · 리조트 · 하루 · 동선 | `OP` | HT 호텔 · 리조트 | ready | `swimlane` | `title*` text · `subtitle` text · `lanes*` table | 본문 64,160–1216,648 · 상자 7 | `ss/L_SS_HT_C.dc.html` |
| `SS-ID-C` | 인테리어 · 빌트인 · 하루 · 동선 | `OP` | ID 인테리어 · 빌트인 | ready | `swimlane` | `title*` text · `subtitle` text · `lanes*` table | 본문 64,160–1216,648 · 상자 7 | `ss/L_SS_ID_C.dc.html` |
| `SS-MD-C` | 의료 · 요양 · 하루 · 동선 | `OP` | MD 의료 · 요양 | ready | `swimlane` | `title*` text · `subtitle` text · `lanes*` table | 본문 64,160–1216,648 · 상자 7 | `ss/L_SS_MD_C.dc.html` |
| `SS-MF-C` | 제조 · 물류 · 현장 · 하루 · 동선 | `OP` | MF 제조 · 물류 · 현장 | ready | `swimlane` | `title*` text · `subtitle` text · `lanes*` table | 본문 64,160–1216,648 · 상자 7 | `ss/L_SS_MF_C.dc.html` |
| `SS-OE-C` | 파트너 전용 단말 · 하루 · 동선 | `OP` | OE 파트너 전용 단말 | ready | `swimlane` | `title*` text · `subtitle` text · `lanes*` table | 본문 64,160–1216,648 · 상자 7 | `ss/L_SS_OE_C.dc.html` |
| `SS-OF-C` | 오피스 · 하루 · 동선 | `OP` | OF 오피스 | ready | `swimlane` | `title*` text · `subtitle` text · `lanes*` table | 본문 64,160–1216,648 · 상자 7 | `ss/L_SS_OF_C.dc.html` |
| `SS-PB-C` | 공공 · 교통 · 하루 · 동선 | `OP` | PB 공공 · 교통 | ready | `swimlane` | `title*` text · `subtitle` text · `lanes*` table | 본문 64,160–1216,648 · 상자 7 | `ss/L_SS_PB_C.dc.html` |
| `SS-RS-C` | 주거 분양 · 하루 · 동선 | `OP` | RS 주거 분양 | ready | `swimlane` | `title*` text · `subtitle` text · `lanes*` table | 본문 64,160–1216,648 · 상자 7 | `ss/L_SS_RS_C.dc.html` |
| `SS-RT-C` | 리테일 · 플래그십 · 하루 · 동선 | `OP` | RT 리테일 · 플래그십 | ready | `swimlane` | `title*` text · `subtitle` text · `lanes*` table | 본문 64,160–1216,648 · 상자 7 | `ss/L_SS_RT_C.dc.html` |
| `SS-SV-C` | 생활 편의 · 무인 매장 · 하루 · 동선 | `OP` | SV 생활 편의 · 무인 매장 | ready | `swimlane` | `title*` text · `subtitle` text · `lanes*` table | 본문 64,160–1216,648 · 상자 7 | `ss/L_SS_SV_C.dc.html` |
| `SS-TP-C` | 테마파크 · 전시 · 하루 · 동선 | `OP` | TP 테마파크 · 전시 | ready | `swimlane` | `title*` text · `subtitle` text · `lanes*` table | 본문 64,160–1216,648 · 상자 7 | `ss/L_SS_TP_C.dc.html` |
| `SS-VN-C` | 공연장 · 경기장 · 하루 · 동선 | `OP` | VN 공연장 · 경기장 | ready | `swimlane` | `title*` text · `subtitle` text · `lanes*` table | 본문 64,160–1216,648 · 상자 7 | `ss/L_SS_VN_C.dc.html` |
| `SA-A` | 계층형 | `SA` |  | ready | `tiers` | `title*` text · `subtitle` text · `layers*` card{tag,title,body,chips}×3 · `notes` card{no,title,body}×3 | 본문 64,160–1216,648 · 상자 14 | `common/L_SOL01.dc.html` |
| `SA-B` | 허브형 | `SA` |  | ready | `hub` | `title*` text · `subtitle` text · `center*` card{tag,title,body} · `nodes*` card{title,body,image}×6 | 본문 170,208–1110,600 · 상자 19 | `common/L_SA_B.dc.html` |
| `SA-C` | 레이어 스택 | `SA` |  | ready | `tiers` | `title*` text · `subtitle` text · `layers*` card{tag,title,body,chips}×4 | 본문 64,160–1216,648 · 상자 13 | `common/L_SA_C.dc.html` |
| `SA-D` | 화면 → 현장 | `SA` |  | ready | `hero_panel` | `title*` text · `image*` image:B · `image_caption` caption · `message` text · `items*` card{no,tag,title,body,kpi,image}×3 | 본문 64,136–1216,648 · 상자 11 | `common/L_SA_D.dc.html` |
| `SF-A` | 솔루션 + 함께 쓰는 제품 | `SF` |  | ready | `hero_panel` | `title*` text · `image*` image:B · `image_caption` caption · `message` text · `items*` card{no,tag,title,body,kpi,image}×3 | 본문 64,136–1216,648 · 상자 11 | `common/L_SOL03.dc.html` |
| `SF-B` | 기능 → 고객 효과 | `SF` |  | ready | `rows_arrow` | `title*` text · `subtitle` text · `rows*` card{label,left,right}×4 · `headers` text×3 | 본문 64,172–1204,648 · 상자 30 | `common/L_SF_B.dc.html` |
| `SF-C` | 솔루션 KV 히어로 + 함께 쓰는 기기 | `SF` |  | ready | `hero_panel` | `title*` text · `image*` image:B · `image_caption` caption · `message` text · `items*` card{no,tag,title,body,kpi,image}×3 | 본문 64,136–1216,648 · 상자 11 | `common/L_SF_C.dc.html` |
| `SF-D` | 실제 화면 투어 · 확대 3 | `SF` |  | ready | `image_pins` | `title*` text · `subtitle` text · `image*` image:B · `pins*` card{no,title,body,tag,x,y}×3 | 본문 64,160–1216,648 · 상자 11 | `common/L_SF_D.dc.html` |
| `SF-E` | 솔루션 포트폴리오 타일 | `SF` |  | ready | `image_grid` | `title*` text · `subtitle` text · `items*` card{image,title,body,chips,tag}×8 | 본문 64,160–1216,648 · 상자 14 | `common/L_SF_E.dc.html` |
| `BIT-D` | b.IoT 전용 구성도 | `SXD` | BIT | ready | `sol_diagram` | `title*` text · `subtitle` text · `layers*` card{tag,title,body,chips}×3 · `notes` card{no,title,body}×3 | 본문 64,160–1216,648 · 상자 14 | `common/L_BIT_D.dc.html` |
| `CCH-D` | 삼성 콜드체인 전용 구성도 | `SXD` | CCH | ready | `sol_diagram` | `title*` text · `subtitle` text · `layers*` card{tag,title,body,chips}×3 · `notes` card{no,title,body}×3 | 본문 64,160–1216,648 · 상자 14 | `common/L_CCH_D.dc.html` |
| `DEX-D` | Samsung DeX 전용 구성도 | `SXD` | DEX | ready | `sol_diagram` | `title*` text · `subtitle` text · `layers*` card{tag,title,body,chips}×3 · `notes` card{no,title,body}×3 | 본문 64,160–1216,648 · 상자 14 | `common/L_DEX_D.dc.html` |
| `HVC-D` | 삼성 통합공조 전용 구성도 | `SXD` | HVC | ready | `sol_diagram` | `title*` text · `subtitle` text · `layers*` card{tag,title,body,chips}×3 · `notes` card{no,title,body}×3 | 본문 64,160–1216,648 · 상자 14 | `common/L_HVC_D.dc.html` |
| `KCP-D` | Knox Capture 전용 구성도 | `SXD` | KCP | ready | `sol_diagram` | `title*` text · `subtitle` text · `layers*` card{tag,title,body,chips}×3 · `notes` card{no,title,body}×3 | 본문 64,160–1216,648 · 상자 14 | `common/L_KCP_D.dc.html` |
| `KNX-D` | Knox Suite 전용 구성도 | `SXD` | KNX | ready | `sol_diagram` | `title*` text · `subtitle` text · `layers*` card{tag,title,body,chips}×3 · `notes` card{no,title,body}×3 | 본문 64,160–1216,648 · 상자 14 | `common/L_KNX_D.dc.html` |
| `LYN-D` | LYNK Cloud 전용 구성도 | `SXD` | LYN | ready | `sol_diagram` | `title*` text · `subtitle` text · `layers*` card{tag,title,body,chips}×3 · `notes` card{no,title,body}×3 | 본문 64,160–1216,648 · 상자 14 | `common/L_LYN_D.dc.html` |
| `MGI-D` | MagicINFO 전용 구성도 | `SXD` | MGI | ready | `sol_diagram` | `title*` text · `subtitle` text · `layers*` card{tag,title,body,chips}×3 · `notes` card{no,title,body}×3 | 본문 64,160–1216,648 · 상자 14 | `common/L_MGI_D.dc.html` |
| `SAC-D` | SAC 제어 시스템 전용 구성도 | `SXD` | SAC | ready | `sol_diagram` | `title*` text · `subtitle` text · `layers*` card{tag,title,body,chips}×3 · `notes` card{no,title,body}×3 | 본문 64,160–1216,648 · 상자 14 | `common/L_SAC_D.dc.html` |
| `STP-D` | SmartThings Pro 전용 구성도 | `SXD` | STP | ready | `sol_diagram` | `title*` text · `subtitle` text · `layers*` card{tag,title,body,chips}×3 · `notes` card{no,title,body}×3 | 본문 64,160–1216,648 · 상자 14 | `common/L_STP_D.dc.html` |
| `VXT-D` | Samsung VXT 전용 구성도 | `SXD` | VXT | ready | `sol_diagram` | `title*` text · `subtitle` text · `layers*` card{tag,title,body,chips}×3 · `notes` card{no,title,body}×3 | 본문 64,160–1216,648 · 상자 14 | `common/L_VXT_D.dc.html` |
| `BIT-I` | b.IoT 전용 소개 | `SXI` | BIT | ready | `sol_intro` | `title*` text · `solution_name*` text · `one_liner` text · `image` image:B · `logo_solution` image:E · `features*` card{no,title,body}×4 · `devices` bullets×6 · `when` text | 본문 64,136–1216,648 · 상자 15 | `common/L_BIT_I.dc.html` |
| `CCH-I` | 삼성 콜드체인 전용 소개 | `SXI` | CCH | ready | `sol_intro` | `title*` text · `solution_name*` text · `one_liner` text · `image` image:B · `logo_solution` image:E · `features*` card{no,title,body}×4 · `devices` bullets×6 · `when` text | 본문 64,136–1216,648 · 상자 15 | `common/L_CCH_I.dc.html` |
| `DEX-I` | Samsung DeX 전용 소개 | `SXI` | DEX | ready | `sol_intro` | `title*` text · `solution_name*` text · `one_liner` text · `image` image:B · `logo_solution` image:E · `features*` card{no,title,body}×4 · `devices` bullets×6 · `when` text | 본문 64,136–1216,648 · 상자 15 | `common/L_DEX_I.dc.html` |
| `HVC-I` | 삼성 통합공조 전용 소개 | `SXI` | HVC | ready | `sol_intro` | `title*` text · `solution_name*` text · `one_liner` text · `image` image:B · `logo_solution` image:E · `features*` card{no,title,body}×4 · `devices` bullets×6 · `when` text | 본문 64,136–1216,648 · 상자 15 | `common/L_HVC_I.dc.html` |
| `KCP-I` | Knox Capture 전용 소개 | `SXI` | KCP | ready | `sol_intro` | `title*` text · `solution_name*` text · `one_liner` text · `image` image:B · `logo_solution` image:E · `features*` card{no,title,body}×4 · `devices` bullets×6 · `when` text | 본문 64,136–1216,648 · 상자 15 | `common/L_KCP_I.dc.html` |
| `KNX-I` | Knox Suite 전용 소개 | `SXI` | KNX | ready | `sol_intro` | `title*` text · `solution_name*` text · `one_liner` text · `image` image:B · `logo_solution` image:E · `features*` card{no,title,body}×4 · `devices` bullets×6 · `when` text | 본문 64,136–1216,648 · 상자 15 | `common/L_KNX_I.dc.html` |
| `LYN-I` | LYNK Cloud 전용 소개 | `SXI` | LYN | ready | `sol_intro` | `title*` text · `solution_name*` text · `one_liner` text · `image` image:B · `logo_solution` image:E · `features*` card{no,title,body}×4 · `devices` bullets×6 · `when` text | 본문 64,136–1216,648 · 상자 15 | `common/L_LYN_I.dc.html` |
| `MGI-I` | MagicINFO 전용 소개 | `SXI` | MGI | ready | `sol_intro` | `title*` text · `solution_name*` text · `one_liner` text · `image` image:B · `logo_solution` image:E · `features*` card{no,title,body}×4 · `devices` bullets×6 · `when` text | 본문 64,136–1216,648 · 상자 15 | `common/L_MGI_I.dc.html` |
| `SAC-I` | SAC 제어 시스템 전용 소개 | `SXI` | SAC | ready | `sol_intro` | `title*` text · `solution_name*` text · `one_liner` text · `image` image:B · `logo_solution` image:E · `features*` card{no,title,body}×4 · `devices` bullets×6 · `when` text | 본문 64,136–1216,648 · 상자 15 | `common/L_SAC_I.dc.html` |
| `STP-I` | SmartThings Pro 전용 소개 | `SXI` | STP | ready | `sol_intro` | `title*` text · `solution_name*` text · `one_liner` text · `image` image:B · `logo_solution` image:E · `features*` card{no,title,body}×4 · `devices` bullets×6 · `when` text | 본문 64,136–1216,648 · 상자 15 | `common/L_STP_I.dc.html` |
| `VXT-I` | Samsung VXT 전용 소개 | `SXI` | VXT | ready | `sol_intro` | `title*` text · `solution_name*` text · `one_liner` text · `image` image:B · `logo_solution` image:E · `features*` card{no,title,body}×4 · `devices` bullets×6 · `when` text | 본문 64,136–1216,648 · 상자 15 | `common/L_VXT_I.dc.html` |
| `BIT-S` | b.IoT 전용 공간 시나리오 | `SXS` | BIT | ready | `sol_scene` | `title*` text · `subtitle` text · `image*` image:A · `space` text · `steps*` card{time,title,body,chips}×4 · `kpis` kpi×3 | 본문 64,160–1216,648 · 상자 20 | `common/L_BIT_S.dc.html` |
| `CCH-S` | 삼성 콜드체인 전용 공간 시나리오 | `SXS` | CCH | ready | `sol_scene` | `title*` text · `subtitle` text · `image*` image:A · `space` text · `steps*` card{time,title,body,chips}×4 · `kpis` kpi×3 | 본문 64,160–1216,648 · 상자 20 | `common/L_CCH_S.dc.html` |
| `DEX-S` | Samsung DeX 전용 공간 시나리오 | `SXS` | DEX | ready | `sol_scene` | `title*` text · `subtitle` text · `image*` image:A · `space` text · `steps*` card{time,title,body,chips}×4 · `kpis` kpi×3 | 본문 64,160–1216,648 · 상자 20 | `common/L_DEX_S.dc.html` |
| `HVC-S` | 삼성 통합공조 전용 공간 시나리오 | `SXS` | HVC | ready | `sol_scene` | `title*` text · `subtitle` text · `image*` image:A · `space` text · `steps*` card{time,title,body,chips}×4 · `kpis` kpi×3 | 본문 64,160–1216,648 · 상자 20 | `common/L_HVC_S.dc.html` |
| `KCP-S` | Knox Capture 전용 공간 시나리오 | `SXS` | KCP | ready | `sol_scene` | `title*` text · `subtitle` text · `image*` image:A · `space` text · `steps*` card{time,title,body,chips}×4 · `kpis` kpi×3 | 본문 64,160–1216,648 · 상자 20 | `common/L_KCP_S.dc.html` |
| `KNX-S` | Knox Suite 전용 공간 시나리오 | `SXS` | KNX | ready | `sol_scene` | `title*` text · `subtitle` text · `image*` image:A · `space` text · `steps*` card{time,title,body,chips}×4 · `kpis` kpi×3 | 본문 64,160–1216,648 · 상자 20 | `common/L_KNX_S.dc.html` |
| `LYN-S` | LYNK Cloud 전용 공간 시나리오 | `SXS` | LYN | ready | `sol_scene` | `title*` text · `subtitle` text · `image*` image:A · `space` text · `steps*` card{time,title,body,chips}×4 · `kpis` kpi×3 | 본문 64,160–1216,648 · 상자 20 | `common/L_LYN_S.dc.html` |
| `MGI-S` | MagicINFO 전용 공간 시나리오 | `SXS` | MGI | ready | `sol_scene` | `title*` text · `subtitle` text · `image*` image:A · `space` text · `steps*` card{time,title,body,chips}×4 · `kpis` kpi×3 | 본문 64,160–1216,648 · 상자 20 | `common/L_MGI_S.dc.html` |
| `SAC-S` | SAC 제어 시스템 전용 공간 시나리오 | `SXS` | SAC | ready | `sol_scene` | `title*` text · `subtitle` text · `image*` image:A · `space` text · `steps*` card{time,title,body,chips}×4 · `kpis` kpi×3 | 본문 64,160–1216,648 · 상자 20 | `common/L_SAC_S.dc.html` |
| `STP-S` | SmartThings Pro 전용 공간 시나리오 | `SXS` | STP | ready | `sol_scene` | `title*` text · `subtitle` text · `image*` image:A · `space` text · `steps*` card{time,title,body,chips}×4 · `kpis` kpi×3 | 본문 64,160–1216,648 · 상자 20 | `common/L_STP_S.dc.html` |
| `VXT-S` | Samsung VXT 전용 공간 시나리오 | `SXS` | VXT | ready | `sol_scene` | `title*` text · `subtitle` text · `image*` image:A · `space` text · `steps*` card{time,title,body,chips}×4 · `kpis` kpi×3 | 본문 64,160–1216,648 · 상자 20 | `common/L_VXT_S.dc.html` |
| `BIT-S-HT` | b.IoT 공간 시나리오 · 비즈니스 호텔 업종 버전 | `SXS` | HT 비즈니스 호텔 | ready | `sol_scene` | `title*` text · `subtitle` text · `image*` image:A · `space` text · `steps*` card{time,title,body,chips}×4 · `kpis` kpi×3 | 본문 64,160–1216,648 · 상자 20 | `common/L_BIT_S_HT.dc.html` |
| `BIT-S-RT` | b.IoT 공간 시나리오 · 매장 업종 버전 | `SXS` | RT 매장 | ready | `sol_scene` | `title*` text · `subtitle` text · `image*` image:A · `space` text · `steps*` card{time,title,body,chips}×4 · `kpis` kpi×3 | 본문 64,160–1216,648 · 상자 20 | `common/L_BIT_S_RT.dc.html` |
| `CCH-S-RT` | 삼성 콜드체인 공간 시나리오 · 매장 업종 버전 | `SXS` | RT 매장 | ready | `sol_scene` | `title*` text · `subtitle` text · `image*` image:A · `space` text · `steps*` card{time,title,body,chips}×4 · `kpis` kpi×3 | 본문 64,160–1216,648 · 상자 20 | `common/L_CCH_S_RT.dc.html` |
| `CCH-S-WH` | 삼성 콜드체인 공간 시나리오 · 저온 저장시설 업종 버전 | `SXS` | WH 저온 저장시설 | ready | `sol_scene` | `title*` text · `subtitle` text · `image*` image:A · `space` text · `steps*` card{time,title,body,chips}×4 · `kpis` kpi×3 | 본문 64,160–1216,648 · 상자 20 | `common/L_CCH_S_WH.dc.html` |
| `DEX-S-FD` | Samsung DeX 공간 시나리오 · 제조 현장 업종 버전 | `SXS` | FD 제조 현장 | ready | `sol_scene` | `title*` text · `subtitle` text · `image*` image:A · `space` text · `steps*` card{time,title,body,chips}×4 · `kpis` kpi×3 | 본문 64,160–1216,648 · 상자 20 | `common/L_DEX_S_FD.dc.html` |
| `DEX-S-OF` | Samsung DeX 공간 시나리오 · 오피스 업종 버전 | `SXS` | OF 오피스 | ready | `sol_scene` | `title*` text · `subtitle` text · `image*` image:A · `space` text · `steps*` card{time,title,body,chips}×4 · `kpis` kpi×3 | 본문 64,160–1216,648 · 상자 20 | `common/L_DEX_S_OF.dc.html` |
| `HVC-S-HT` | 삼성 통합공조 공간 시나리오 · 비즈니스 호텔 업종 버전 | `SXS` | HT 비즈니스 호텔 | ready | `sol_scene` | `title*` text · `subtitle` text · `image*` image:A · `space` text · `steps*` card{time,title,body,chips}×4 · `kpis` kpi×3 | 본문 64,160–1216,648 · 상자 20 | `common/L_HVC_S_HT.dc.html` |
| `HVC-S-OF` | 삼성 통합공조 공간 시나리오 · 오피스 업종 버전 | `SXS` | OF 오피스 | ready | `sol_scene` | `title*` text · `subtitle` text · `image*` image:A · `space` text · `steps*` card{time,title,body,chips}×4 · `kpis` kpi×3 | 본문 64,160–1216,648 · 상자 20 | `common/L_HVC_S_OF.dc.html` |
| `KCP-S-LG` | Knox Capture 공간 시나리오 · 물류센터 업종 버전 | `SXS` | LG 물류센터 | ready | `sol_scene` | `title*` text · `subtitle` text · `image*` image:A · `space` text · `steps*` card{time,title,body,chips}×4 · `kpis` kpi×3 | 본문 64,160–1216,648 · 상자 20 | `common/L_KCP_S_LG.dc.html` |
| `KNX-S-AC` | Knox Suite 공간 시나리오 · 학원 업종 버전 | `SXS` | AC 학원 | ready | `sol_scene` | `title*` text · `subtitle` text · `image*` image:A · `space` text · `steps*` card{time,title,body,chips}×4 · `kpis` kpi×3 | 본문 64,160–1216,648 · 상자 20 | `common/L_KNX_S_AC.dc.html` |
| `KNX-S-FD` | Knox Suite 공간 시나리오 · 제조 현장 업종 버전 | `SXS` | FD 제조 현장 | ready | `sol_scene` | `title*` text · `subtitle` text · `image*` image:A · `space` text · `steps*` card{time,title,body,chips}×4 · `kpis` kpi×3 | 본문 64,160–1216,648 · 상자 20 | `common/L_KNX_S_FD.dc.html` |
| `LYN-S-HT` | LYNK Cloud 공간 시나리오 · 비즈니스 호텔 업종 버전 | `SXS` | HT 비즈니스 호텔 | ready | `sol_scene` | `title*` text · `subtitle` text · `image*` image:A · `space` text · `steps*` card{time,title,body,chips}×4 · `kpis` kpi×3 | 본문 64,160–1216,648 · 상자 20 | `common/L_LYN_S_HT.dc.html` |
| `MGI-S-HT` | MagicINFO 공간 시나리오 · 비즈니스 호텔 업종 버전 | `SXS` | HT 비즈니스 호텔 | ready | `sol_scene` | `title*` text · `subtitle` text · `image*` image:A · `space` text · `steps*` card{time,title,body,chips}×4 · `kpis` kpi×3 | 본문 64,160–1216,648 · 상자 20 | `common/L_MGI_S_HT.dc.html` |
| `MGI-S-RT` | MagicINFO 공간 시나리오 · 매장 업종 버전 | `SXS` | RT 매장 | ready | `sol_scene` | `title*` text · `subtitle` text · `image*` image:A · `space` text · `steps*` card{time,title,body,chips}×4 · `kpis` kpi×3 | 본문 64,160–1216,648 · 상자 20 | `common/L_MGI_S_RT.dc.html` |
| `SAC-S-AC` | SAC 제어 시스템 공간 시나리오 · 학원 업종 버전 | `SXS` | AC 학원 | ready | `sol_scene` | `title*` text · `subtitle` text · `image*` image:A · `space` text · `steps*` card{time,title,body,chips}×4 · `kpis` kpi×3 | 본문 64,160–1216,648 · 상자 20 | `common/L_SAC_S_AC.dc.html` |
| `SAC-S-GF` | SAC 제어 시스템 공간 시나리오 · 스크린골프장 업종 버전 | `SXS` | GF 스크린골프장 | ready | `sol_scene` | `title*` text · `subtitle` text · `image*` image:A · `space` text · `steps*` card{time,title,body,chips}×4 · `kpis` kpi×3 | 본문 64,160–1216,648 · 상자 20 | `common/L_SAC_S_GF.dc.html` |
| `STP-S-GF` | SmartThings Pro 공간 시나리오 · 스크린골프장 업종 버전 | `SXS` | GF 스크린골프장 | ready | `sol_scene` | `title*` text · `subtitle` text · `image*` image:A · `space` text · `steps*` card{time,title,body,chips}×4 · `kpis` kpi×3 | 본문 64,160–1216,648 · 상자 20 | `common/L_STP_S_GF.dc.html` |
| `STP-S-HT` | SmartThings Pro 공간 시나리오 · 비즈니스 호텔 업종 버전 | `SXS` | HT 비즈니스 호텔 | ready | `sol_scene` | `title*` text · `subtitle` text · `image*` image:A · `space` text · `steps*` card{time,title,body,chips}×4 · `kpis` kpi×3 | 본문 64,160–1216,648 · 상자 20 | `common/L_STP_S_HT.dc.html` |
| `STP-S-OF` | SmartThings Pro 공간 시나리오 · 오피스 업종 버전 | `SXS` | OF 오피스 | ready | `sol_scene` | `title*` text · `subtitle` text · `image*` image:A · `space` text · `steps*` card{time,title,body,chips}×4 · `kpis` kpi×3 | 본문 64,160–1216,648 · 상자 20 | `common/L_STP_S_OF.dc.html` |
| `VXT-S-GF` | Samsung VXT 공간 시나리오 · 스크린골프장 업종 버전 | `SXS` | GF 스크린골프장 | ready | `sol_scene` | `title*` text · `subtitle` text · `image*` image:A · `space` text · `steps*` card{time,title,body,chips}×4 · `kpis` kpi×3 | 본문 64,160–1216,648 · 상자 20 | `common/L_VXT_S_GF.dc.html` |
| `VXT-S-RT` | Samsung VXT 공간 시나리오 · 매장 업종 버전 | `SXS` | RT 매장 | ready | `sol_scene` | `title*` text · `subtitle` text · `image*` image:A · `space` text · `steps*` card{time,title,body,chips}×4 · `kpis` kpi×3 | 본문 64,160–1216,648 · 상자 20 | `common/L_VXT_S_RT.dc.html` |
## 공간별 가치 제공 시나리오 (`space_scenario`)

| 코드 | 이름 | 역할 | 업종 · 솔루션 | 상태 | 아키타입 | 칸 | 배치 | 원본 보드 |
|---|---|---|---|---|---|---|---|---|
| `SS-A` | 한 공간의 장면 3 | `SS` |  | ready | `hero_panel` | `title*` text · `image*` image:A · `image_caption` caption · `items*` card{no,tag,title,body,kpi,image}×3 | 본문 64,136–1216,648 · 상자 10 | `ss/L_VS02.dc.html` |
| `SS-B` | 솔루션 → 제품 → 가치 | `SS` |  | ready | `chain_cols` | `title*` text · `image` image:A · `space` text · `headers` text×3 · `solutions*` card{letter,title,body}×2 · `products*` card{title,body,image}×3 · `values*` card{no,title,kpi}×2 | 본문 64,136–1216,648 · 상자 18 | `ss/L_SS_B.dc.html` |
| `SS-C` | 이 공간 전 → 후 | `SS` |  | ready | `two_images` | `title*` text · `sides*` card{tag,title,body,bullets,image,chips}×2 · `labels` text×2 · `message` text · `message_label` text | 본문 64,136–1216,638 · 상자 15 | `ss/L_SS_C.dc.html` |
| `VC-11A` | 한 공간 · 한 솔루션 | `SS` |  | ready | `hero_panel` | `title*` text · `image*` image:A · `image_caption` caption · `message` text · `items*` card{no,tag,title,body,kpi,image}×3 | 본문 64,136–1216,648 · 상자 11 | `ss/L_VC_11A.dc.html` |
| `VC-11B` | 한 공간 · 한 솔루션 | `SS` |  | ready | `pillars` | `title*` text · `pillars*` card{no,tag,title,body,kpi,image}×3 | 본문 64,136–1216,648 · 상자 8 | `ss/L_VC_11B.dc.html` |
| `VC-12` | 한 공간 · 솔루션 2개 | `SS` |  | ready | `split2` | `title*` text · `subtitle` text · `image` image:A · `sides*` card{tag,title,body,bullets,kpi}×2 | 본문 64,160–1216,648 · 상자 9 | `ss/L_VC_12.dc.html` |
| `VC-13` | 한 공간 · 솔루션 3개 | `SS` |  | ready | `tiers` | `title*` text · `subtitle` text · `layers*` card{tag,title,body,chips}×3 · `notes` card{no,title,body}×3 | 본문 64,160–1216,648 · 상자 14 | `ss/L_VC_13.dc.html` |
| `VC-14` | 한 공간 · 솔루션 4개 | `SS` |  | ready | `hub` | `title*` text · `subtitle` text · `center*` card{tag,title,body} · `nodes*` card{title,body,image}×4 | 본문 170,258–1110,550 · 상자 15 | `ss/L_VC_14.dc.html` |
| `VC-1Z` | 한 공간 · 존 분할 (플래그십 스토어 1층 × 존 4) | `SS` |  | ready | `space_map` | `title*` text · `subtitle` text · `image` image:A · `spaces*` card{no,title,chips,body,x,y}×4 | 본문 64,160–1216,648 · 상자 12 | `ss/L_VC_1Z.dc.html` |
| `VC-21` | 두 공간 · 한 솔루션 | `SS` |  | ready | `two_images` | `title*` text · `sides*` card{tag,title,body,bullets,image}×2 · `labels` text×2 · `message` text · `message_label` text | 본문 64,136–1216,638 · 상자 15 | `ss/L_VC_21.dc.html` |
| `VC-22` | 두 공간 · 솔루션 2개 | `SS` |  | ready | `two_images` | `title*` text · `sides*` card{tag,title,body,bullets,image,chips}×2 · `labels` text×2 · `message` text · `message_label` text | 본문 64,136–1216,638 · 상자 15 | `ss/L_VC_22.dc.html` |
| `VC-23` | 두 공간 · 솔루션 3개 | `SS` |  | ready | `split2` | `title*` text · `subtitle` text · `image` image:A · `sides*` card{tag,title,body,bullets,kpi}×2 · `message` text | 본문 64,160–1216,638 · 상자 11 | `ss/L_VC_23.dc.html` |
| `VC-24` | 두 공간 · 솔루션 4개 | `SS` |  | ready | `matrix` | `title*` text · `subtitle` text · `table*` table | 본문 64,160–1216,648 · 상자 7 | `ss/L_VC_24.dc.html` |
| `VC-31` | 세 공간 · 한 솔루션 | `SS` |  | ready | `path_strip` | `title*` text · `subtitle` text · `steps*` card{no,title,body,chips,image}×3 · `message` text | 본문 64,160–1216,638 · 상자 13 | `ss/L_VC_31.dc.html` |
| `VC-32` | 세 공간 · 솔루션 2개 | `SS` |  | ready | `pillars` | `title*` text · `pillars*` card{no,tag,title,body,kpi,image}×3 · `message` text | 본문 64,148–1216,648 · 상자 10 | `ss/L_VC_32.dc.html` |
| `VC-33` | 세 공간 · 솔루션 3개 | `SS` |  | ready | `pillars` | `title*` text · `pillars*` card{no,tag,title,body,kpi,image}×3 | 본문 64,136–1216,648 · 상자 8 | `ss/L_VC_33.dc.html` |
| `VC-34` | 세 공간 · 솔루션 4개 | `SS` |  | ready | `pillars` | `title*` text · `pillars*` card{no,tag,title,body,kpi,image}×3 · `message` text | 본문 64,148–1216,648 · 상자 10 | `ss/L_VC_34.dc.html` |
| `VC-42` | 네 공간 · 솔루션 2개 | `SS` |  | ready | `quad_center` | `title*` text · `subtitle` text · `quadrants*` card{tag,title,body,bullets,kpi}×4 | 본문 64,160–1216,648 · 상자 10 | `ss/L_VC_42.dc.html` |
| `VC-43` | 네 공간 · 솔루션 3개 | `SS` |  | ready | `space_map` | `title*` text · `subtitle` text · `image` image:D · `spaces*` card{no,title,chips,body,x,y}×4 | 본문 64,160–1216,648 · 상자 12 | `ss/L_VC_43.dc.html` |
| `VC-64` | 여섯 공간 · 솔루션 4개 | `SS` |  | ready | `matrix` | `title*` text · `subtitle` text · `table*` table | 본문 64,160–1216,648 · 상자 7 | `ss/L_VC_64.dc.html` |
| `VC-J` | 공간 동선 × 솔루션 레인 (멀티플렉스 영화관) | `SS` |  | ready | `swimlane` | `title*` text · `subtitle` text · `lanes*` table | 본문 64,160–1216,648 · 상자 7 | `ss/L_VC_J.dc.html` |
| `VC-MAP` | 조합 지도 | `SS` |  | internal | `matrix` | `title*` text · `subtitle` text · `table*` table | 본문 64,160–1216,648 · 상자 7 | `ss/L_VC_MAP.dc.html` |
| `VC-N` | 지점 여러 곳 | `SS` |  | ready | `tiers` | `title*` text · `subtitle` text · `layers*` card{tag,title,body,chips}×3 · `notes` card{no,title,body}×3 | 본문 64,160–1216,648 · 상자 14 | `ss/L_VC_N.dc.html` |
| `SS-AD-B` | 옥외 광고 · 대표 공간 장면 | `SS` | AD 옥외 광고 | ready | `hero_panel` | `title*` text · `image*` image:A · `image_caption` caption · `message` text · `items*` card{no,tag,title,body,kpi,image}×4 | 본문 64,136–1216,648 · 상자 12 | `ss/L_SS_AD_B.dc.html` |
| `SS-AD-D` | 옥외 광고 · 공간 시나리오 · 지하철 환승통로 | `SS` | AD 옥외 광고 | ready | `form_phases` | `title*` text · `subtitle` text · `steps*` card{when,title,body,tag}×3 · `message` text · `message_label` text | 본문 64,232–1216,632 · 상자 16 | `ss/L_SS_AD_D.dc.html` |
| `SS-AD-E` | 옥외 광고 · 공간 시나리오 · 거리 미디어폴 | `SS` | AD 옥외 광고 | ready | `form_users` | `title*` text · `subtitle` text · `image` image:A · `people*` card{role,name,body,bullets,kpi}×3 | 본문 64,160–1216,648 · 상자 10 | `ss/L_SS_AD_E.dc.html` |
| `SS-ED-B` | 교육 · 캠퍼스 · 대표 공간 장면 | `SS` | ED 교육 · 캠퍼스 | ready | `hero_panel` | `title*` text · `image*` image:A · `image_caption` caption · `message` text · `items*` card{no,tag,title,body,kpi,image}×4 | 본문 64,136–1216,648 · 상자 12 | `ss/L_SS_ED_B.dc.html` |
| `SS-ED-D` | 교육 · 캠퍼스 · 공간 시나리오 · 중앙도서관 · 라운지 | `SS` | ED 교육 · 캠퍼스 | ready | `form_path` | `title*` text · `subtitle` text · `image` image:A · `spaces*` card{no,title,chips,body,x,y}×5 | 본문 64,160–1216,648 · 상자 13 | `ss/L_SS_ED_D.dc.html` |
| `SS-ED-E` | 교육 · 캠퍼스 · 공간 시나리오 · 기숙사 · 생활관 | `SS` | ED 교육 · 캠퍼스 | ready | `form_phases` | `title*` text · `subtitle` text · `steps*` card{when,title,body,tag}×3 · `message` text · `message_label` text | 본문 64,232–1216,632 · 상자 16 | `ss/L_SS_ED_E.dc.html` |
| `SS-FB-B` | 외식 · 카페 · 대표 공간 장면 | `SS` | FB 외식 · 카페 | ready | `hero_panel` | `title*` text · `image*` image:A · `image_caption` caption · `message` text · `items*` card{no,tag,title,body,kpi,image}×4 | 본문 64,136–1216,648 · 상자 12 | `ss/L_SS_FB_B.dc.html` |
| `SS-FB-D` | 외식 · 카페 · 공간 시나리오 · 매장 외부 · 대기 | `SS` | FB 외식 · 카페 | ready | `form_modes` | `title*` text · `sides*` card{tag,title,body,bullets,image}×2 · `labels` text×2 · `message` text · `message_label` text | 본문 64,136–1216,638 · 상자 15 | `ss/L_SS_FB_D.dc.html` |
| `SS-FB-E` | 외식 · 카페 · 공간 시나리오 · 주방 + 냉장 · 냉동 보관 | `SS` | FB 외식 · 카페 | ready | `form_problems` | `title*` text · `subtitle` text · `image` image:A · `rows*` card{label,left,right,change}×3 · `headers` text×2 | 본문 64,160–1216,648 · 상자 21 | `ss/L_SS_FB_E.dc.html` |
| `SS-FN-B` | 금융 · 대표 공간 장면 | `SS` | FN 금융 | ready | `hero_panel` | `title*` text · `image*` image:A · `image_caption` caption · `message` text · `items*` card{no,tag,title,body,kpi,image}×4 | 본문 64,136–1216,648 · 상자 12 | `ss/L_SS_FN_B.dc.html` |
| `SS-FN-D` | 금융 · 공간 시나리오 · 본점 대강당 | `SS` | FN 금융 | ready | `form_modes` | `title*` text · `sides*` card{tag,title,body,bullets,image}×2 · `labels` text×2 · `message` text · `message_label` text | 본문 64,136–1216,638 · 상자 15 | `ss/L_SS_FN_D.dc.html` |
| `SS-FN-E` | 금융 · 공간 시나리오 · 방문 상담 · 현장 영업 | `SS` | FN 금융 | ready | `form_phases` | `title*` text · `subtitle` text · `steps*` card{when,title,body,tag}×3 · `message` text · `message_label` text | 본문 64,232–1216,632 · 상자 16 | `ss/L_SS_FN_E.dc.html` |
| `SS-HT-B` | 호텔 · 리조트 · 대표 공간 장면 | `SS` | HT 호텔 · 리조트 | ready | `hero_panel` | `title*` text · `image*` image:A · `image_caption` caption · `message` text · `items*` card{no,tag,title,body,kpi,image}×4 | 본문 64,136–1216,648 · 상자 12 | `ss/L_SS_HT_B.dc.html` |
| `SS-HT-D` | 호텔 · 리조트 · 공간 시나리오 · 연회장 · 회의실 | `SS` | HT 호텔 · 리조트 | ready | `form_modes` | `title*` text · `sides*` card{tag,title,body,bullets,image}×2 · `labels` text×2 · `message` text · `message_label` text | 본문 64,136–1216,638 · 상자 15 | `ss/L_SS_HT_D.dc.html` |
| `SS-HT-E` | 호텔 · 리조트 · 공간 시나리오 · 로비 · 리셉션 | `SS` | HT 호텔 · 리조트 | ready | `form_users` | `title*` text · `subtitle` text · `image` image:A · `people*` card{role,name,body,bullets,kpi}×3 | 본문 64,160–1216,648 · 상자 10 | `ss/L_SS_HT_E.dc.html` |
| `SS-ID-B` | 인테리어 · 빌트인 · 대표 공간 장면 | `SS` | ID 인테리어 · 빌트인 | ready | `hero_panel` | `title*` text · `image*` image:A · `image_caption` caption · `message` text · `items*` card{no,tag,title,body,kpi,image}×4 | 본문 64,136–1216,648 · 상자 12 | `ss/L_SS_ID_B.dc.html` |
| `SS-ID-D` | 인테리어 · 빌트인 · 공간 시나리오 · 입구 · 상담 라운지 | `SS` | ID 인테리어 · 빌트인 | ready | `form_users` | `title*` text · `subtitle` text · `image` image:A · `people*` card{role,name,body,bullets,kpi}×3 | 본문 64,160–1216,648 · 상자 10 | `ss/L_SS_ID_D.dc.html` |
| `SS-ID-E` | 인테리어 · 빌트인 · 공간 시나리오 · 거실 · 홈시네마 | `SS` | ID 인테리어 · 빌트인 | ready | `form_modes` | `title*` text · `sides*` card{tag,title,body,bullets,image}×2 · `labels` text×2 · `message` text · `message_label` text | 본문 64,136–1216,638 · 상자 15 | `ss/L_SS_ID_E.dc.html` |
| `SS-MD-B` | 의료 · 요양 · 대표 공간 장면 | `SS` | MD 의료 · 요양 | ready | `hero_panel` | `title*` text · `image*` image:A · `image_caption` caption · `message` text · `items*` card{no,tag,title,body,kpi,image}×4 | 본문 64,136–1216,648 · 상자 12 | `ss/L_SS_MD_B.dc.html` |
| `SS-MD-D` | 의료 · 요양 · 공간 시나리오 · 로비 · 원무 · 접수 | `SS` | MD 의료 · 요양 | ready | `form_modes` | `title*` text · `sides*` card{tag,title,body,bullets,image}×2 · `labels` text×2 · `message` text · `message_label` text | 본문 64,136–1216,638 · 상자 15 | `ss/L_SS_MD_D.dc.html` |
| `SS-MD-E` | 의료 · 요양 · 공간 시나리오 · 재활치료센터 · 프로그램실 | `SS` | MD 의료 · 요양 | ready | `form_problems` | `title*` text · `subtitle` text · `image` image:A · `rows*` card{label,left,right,change}×3 · `headers` text×2 | 본문 64,160–1216,648 · 상자 21 | `ss/L_SS_MD_E.dc.html` |
| `SS-MF-B` | 제조 · 물류 · 현장 · 대표 공간 장면 | `SS` | MF 제조 · 물류 · 현장 | ready | `hero_panel` | `title*` text · `image*` image:A · `image_caption` caption · `message` text · `items*` card{no,tag,title,body,kpi,image}×4 | 본문 64,136–1216,648 · 상자 12 | `ss/L_SS_MF_B.dc.html` |
| `SS-MF-D` | 제조 · 물류 · 현장 · 공간 시나리오 · 창고 · 물류 야드 · 배송 | `SS` | MF 제조 · 물류 · 현장 | ready | `form_path` | `title*` text · `subtitle` text · `image` image:A · `spaces*` card{no,title,chips,body,x,y}×5 | 본문 64,160–1216,648 · 상자 13 | `ss/L_SS_MF_D.dc.html` |
| `SS-MF-E` | 제조 · 물류 · 현장 · 공간 시나리오 · 야외 작업장 · 설비 구역 | `SS` | MF 제조 · 물류 · 현장 | ready | `form_users` | `title*` text · `subtitle` text · `image` image:A · `people*` card{role,name,body,bullets,kpi}×3 | 본문 64,160–1216,648 · 상자 10 | `ss/L_SS_MF_E.dc.html` |
| `SS-OE-B` | 파트너 전용 단말 · 대표 공간 장면 | `SS` | OE 파트너 전용 단말 | ready | `hero_panel` | `title*` text · `image*` image:A · `image_caption` caption · `message` text · `items*` card{no,tag,title,body,kpi,image}×4 | 본문 64,136–1216,648 · 상자 12 | `ss/L_SS_OE_B.dc.html` |
| `SS-OE-D` | 파트너 전용 단말 · 공간 시나리오 · 매장 · 개통 카운터 | `SS` | OE 파트너 전용 단말 | ready | `form_problems` | `title*` text · `subtitle` text · `image` image:A · `rows*` card{label,left,right,change}×3 · `headers` text×2 | 본문 64,160–1216,648 · 상자 21 | `ss/L_SS_OE_D.dc.html` |
| `SS-OE-E` | 파트너 전용 단말 · 공간 시나리오 · 학교 · 학원 | `SS` | OE 파트너 전용 단말 | ready | `form_modes` | `title*` text · `sides*` card{tag,title,body,bullets,image}×2 · `labels` text×2 · `message` text · `message_label` text | 본문 64,136–1216,638 · 상자 15 | `ss/L_SS_OE_E.dc.html` |
| `SS-OF-B` | 오피스 · 대표 공간 장면 | `SS` | OF 오피스 | ready | `hero_panel` | `title*` text · `image*` image:A · `image_caption` caption · `message` text · `items*` card{no,tag,title,body,kpi,image}×4 | 본문 64,136–1216,648 · 상자 12 | `ss/L_SS_OF_B.dc.html` |
| `SS-OF-D` | 오피스 · 공간 시나리오 · 로비 · 외벽 | `SS` | OF 오피스 | ready | `form_path` | `title*` text · `subtitle` text · `image` image:A · `spaces*` card{no,title,chips,body,x,y}×5 | 본문 64,160–1216,648 · 상자 13 | `ss/L_SS_OF_D.dc.html` |
| `SS-OF-E` | 오피스 · 공간 시나리오 · 입주사 업무층 | `SS` | OF 오피스 | ready | `form_users` | `title*` text · `subtitle` text · `image` image:A · `people*` card{role,name,body,bullets,kpi}×3 | 본문 64,160–1216,648 · 상자 10 | `ss/L_SS_OF_E.dc.html` |
| `SS-PB-B` | 공공 · 교통 · 대표 공간 장면 | `SS` | PB 공공 · 교통 | ready | `hero_panel` | `title*` text · `image*` image:A · `image_caption` caption · `message` text · `items*` card{no,tag,title,body,kpi,image}×4 | 본문 64,136–1216,648 · 상자 12 | `ss/L_SS_PB_B.dc.html` |
| `SS-PB-D` | 공공 · 교통 · 공간 시나리오 · 역사 · 정류장 | `SS` | PB 공공 · 교통 | ready | `form_problems` | `title*` text · `subtitle` text · `image` image:A · `rows*` card{label,left,right,change}×3 · `headers` text×2 | 본문 64,160–1216,648 · 상자 21 | `ss/L_SS_PB_D.dc.html` |
| `SS-PB-E` | 공공 · 교통 · 공간 시나리오 · 공원 · 탐방로 | `SS` | PB 공공 · 교통 | ready | `form_users` | `title*` text · `subtitle` text · `image` image:A · `people*` card{role,name,body,bullets,kpi}×3 | 본문 64,160–1216,648 · 상자 10 | `ss/L_SS_PB_E.dc.html` |
| `SS-RS-B` | 주거 분양 · 대표 공간 장면 | `SS` | RS 주거 분양 | ready | `hero_panel` | `title*` text · `image*` image:A · `image_caption` caption · `message` text · `items*` card{no,tag,title,body,kpi,image}×4 | 본문 64,136–1216,648 · 상자 12 | `ss/L_SS_RS_B.dc.html` |
| `SS-RS-D` | 주거 분양 · 공간 시나리오 · 세탁실 · 드레스룸 | `SS` | RS 주거 분양 | ready | `form_problems` | `title*` text · `subtitle` text · `image` image:A · `rows*` card{label,left,right,change}×3 · `headers` text×2 | 본문 64,160–1216,648 · 상자 21 | `ss/L_SS_RS_D.dc.html` |
| `SS-RS-E` | 주거 분양 · 공간 시나리오 · 모델하우스 | `SS` | RS 주거 분양 | ready | `form_path` | `title*` text · `subtitle` text · `image` image:A · `spaces*` card{no,title,chips,body,x,y}×5 | 본문 64,160–1216,648 · 상자 13 | `ss/L_SS_RS_E.dc.html` |
| `SS-RT-B` | 리테일 · 플래그십 · 대표 공간 장면 | `SS` | RT 리테일 · 플래그십 | ready | `hero_panel` | `title*` text · `image*` image:A · `image_caption` caption · `message` text · `items*` card{no,tag,title,body,kpi,image}×4 | 본문 64,136–1216,648 · 상자 12 | `ss/L_SS_RT_B.dc.html` |
| `SS-RT-D` | 리테일 · 플래그십 · 공간 시나리오 · B1 식품관 | `SS` | RT 리테일 · 플래그십 | ready | `form_path` | `title*` text · `subtitle` text · `image` image:A · `spaces*` card{no,title,chips,body,x,y}×5 | 본문 64,160–1216,648 · 상자 13 | `ss/L_SS_RT_D.dc.html` |
| `SS-RT-E` | 리테일 · 플래그십 · 공간 시나리오 · VIP 라운지 | `SS` | RT 리테일 · 플래그십 | ready | `form_users` | `title*` text · `subtitle` text · `image` image:A · `people*` card{role,name,body,bullets,kpi}×3 | 본문 64,160–1216,648 · 상자 10 | `ss/L_SS_RT_E.dc.html` |
| `SS-SV-B` | 생활 편의 · 무인 매장 · 대표 공간 장면 | `SS` | SV 생활 편의 · 무인 매장 | ready | `hero_panel` | `title*` text · `image*` image:A · `image_caption` caption · `message` text · `items*` card{no,tag,title,body,kpi,image}×4 | 본문 64,136–1216,648 · 상자 12 | `ss/L_SS_SV_B.dc.html` |
| `SS-SV-D` | 생활 편의 · 무인 매장 · 공간 시나리오 · 출력 코너 | `SS` | SV 생활 편의 · 무인 매장 | ready | `form_phases` | `title*` text · `subtitle` text · `steps*` card{when,title,body,tag}×3 · `message` text · `message_label` text | 본문 64,232–1216,632 · 상자 16 | `ss/L_SS_SV_D.dc.html` |
| `SS-SV-E` | 생활 편의 · 무인 매장 · 공간 시나리오 · 입구 · 좌석 키오스크 | `SS` | SV 생활 편의 · 무인 매장 | ready | `form_modes` | `title*` text · `sides*` card{tag,title,body,bullets,image}×2 · `labels` text×2 · `message` text · `message_label` text | 본문 64,136–1216,638 · 상자 15 | `ss/L_SS_SV_E.dc.html` |
| `SS-TP-B` | 테마파크 · 전시 · 대표 공간 장면 | `SS` | TP 테마파크 · 전시 | ready | `hero_panel` | `title*` text · `image*` image:A · `image_caption` caption · `message` text · `items*` card{no,tag,title,body,kpi,image}×4 | 본문 64,136–1216,648 · 상자 12 | `ss/L_SS_TP_B.dc.html` |
| `SS-TP-D` | 테마파크 · 전시 · 공간 시나리오 · 야외 공연 무대 | `SS` | TP 테마파크 · 전시 | ready | `form_modes` | `title*` text · `sides*` card{tag,title,body,bullets,image}×2 · `labels` text×2 · `message` text · `message_label` text | 본문 64,136–1216,638 · 상자 15 | `ss/L_SS_TP_D.dc.html` |
| `SS-TP-E` | 테마파크 · 전시 · 공간 시나리오 · 키즈 실내 놀이존 | `SS` | TP 테마파크 · 전시 | ready | `form_problems` | `title*` text · `subtitle` text · `image` image:A · `rows*` card{label,left,right,change}×3 · `headers` text×2 | 본문 64,160–1216,648 · 상자 21 | `ss/L_SS_TP_E.dc.html` |
| `SS-VN-B` | 공연장 · 경기장 · 대표 공간 장면 | `SS` | VN 공연장 · 경기장 | ready | `hero_panel` | `title*` text · `image*` image:A · `image_caption` caption · `message` text · `items*` card{no,tag,title,body,kpi,image}×4 | 본문 64,136–1216,648 · 상자 12 | `ss/L_SS_VN_B.dc.html` |
| `SS-VN-D` | 공연장 · 경기장 · 공간 시나리오 · 라커룸 · 체력단련실 | `SS` | VN 공연장 · 경기장 | ready | `form_problems` | `title*` text · `subtitle` text · `image` image:A · `rows*` card{label,left,right,change}×3 · `headers` text×2 | 본문 64,160–1216,648 · 상자 21 | `ss/L_SS_VN_D.dc.html` |
| `SS-VN-E` | 공연장 · 경기장 · 공간 시나리오 · 컨코스 · 매점 | `SS` | VN 공연장 · 경기장 | ready | `form_path` | `title*` text · `subtitle` text · `image` image:A · `spaces*` card{no,title,chips,body,x,y}×5 | 본문 64,160–1216,648 · 상자 13 | `ss/L_SS_VN_E.dc.html` |
| `UX-A` | 이용자 여정 포토 스트립 | `UX` |  | ready | `path_strip` | `title*` text · `subtitle` text · `steps*` card{no,title,body,chips,image}×5 · `message` text | 본문 64,160–1216,638 · 상자 17 | `common/L_UX_A.dc.html` |
| `UX-B` | 한 장면 + 한 마디 | `UX` |  | ready | `hero_panel` | `title*` text · `image*` image:A · `image_caption` caption · `message` text · `items*` card{no,tag,title,body,kpi,image}×1 | 본문 64,136–1216,648 · 상자 9 | `common/L_UX_B.dc.html` |
| `UX-C` | 시간대별 장면 4 | `UX` |  | ready | `image_grid` | `title*` text · `subtitle` text · `items*` card{image,title,body,chips,tag}×4 | 본문 64,160–1216,648 · 상자 10 | `common/L_UX_C.dc.html` |
| `VM-A` | 공간 × 솔루션 매트릭스 | `VM` |  | ready | `matrix` | `title*` text · `subtitle` text · `table*` table | 본문 64,160–1216,648 · 상자 7 | `ss/L_VS01.dc.html` |
| `VM-B` | 공간 3개 한 장 | `VM` |  | ready | `pillars` | `title*` text · `pillars*` card{no,tag,title,body,kpi,image}×3 | 본문 64,136–1216,648 · 상자 8 | `ss/L_VS03.dc.html` |
| `VM-C` | 조감도 위 솔루션 핀 | `VM` |  | ready | `image_pins` | `title*` text · `subtitle` text · `image*` image:A · `pins*` card{no,title,body,tag,x,y}×5 · `legend` card{letter,title,body}×2 | 본문 64,160–1216,648 · 상자 15 | `ss/L_VM_C.dc.html` |
| `VM-D` | 하루 타임라인 × 공간 | `VM` |  | ready | `swimlane` | `title*` text · `subtitle` text · `lanes*` table | 본문 64,160–1216,648 · 상자 7 | `ss/L_VM_D.dc.html` |
| `SS-AD-A` | 옥외 광고 · 공간 맵 | `VM` | AD 옥외 광고 | ready | `space_map` | `title*` text · `subtitle` text · `image` image:A · `spaces*` card{no,title,chips,body,x,y}×7 | 본문 64,160–1216,648 · 상자 15 | `ss/L_SS_AD_A.dc.html` |
| `SS-ED-A` | 교육 · 캠퍼스 · 공간 맵 | `VM` | ED 교육 · 캠퍼스 | ready | `space_map` | `title*` text · `subtitle` text · `image` image:A · `spaces*` card{no,title,chips,body,x,y}×7 | 본문 64,160–1216,648 · 상자 15 | `ss/L_SS_ED_A.dc.html` |
| `SS-FB-A` | 외식 · 카페 · 공간 맵 | `VM` | FB 외식 · 카페 | ready | `space_map` | `title*` text · `subtitle` text · `image` image:A · `spaces*` card{no,title,chips,body,x,y}×7 | 본문 64,160–1216,648 · 상자 15 | `ss/L_SS_FB_A.dc.html` |
| `SS-FN-A` | 금융 · 공간 맵 | `VM` | FN 금융 | ready | `space_map` | `title*` text · `subtitle` text · `image` image:A · `spaces*` card{no,title,chips,body,x,y}×7 | 본문 64,160–1216,648 · 상자 15 | `ss/L_SS_FN_A.dc.html` |
| `SS-HT-A` | 호텔 · 리조트 · 공간 맵 | `VM` | HT 호텔 · 리조트 | ready | `space_map` | `title*` text · `subtitle` text · `image` image:A · `spaces*` card{no,title,chips,body,x,y}×7 | 본문 64,160–1216,648 · 상자 15 | `ss/L_SS_HT_A.dc.html` |
| `SS-ID-A` | 인테리어 · 빌트인 · 공간 맵 | `VM` | ID 인테리어 · 빌트인 | ready | `space_map` | `title*` text · `subtitle` text · `image` image:A · `spaces*` card{no,title,chips,body,x,y}×7 | 본문 64,160–1216,648 · 상자 15 | `ss/L_SS_ID_A.dc.html` |
| `SS-MD-A` | 의료 · 요양 · 공간 맵 | `VM` | MD 의료 · 요양 | ready | `space_map` | `title*` text · `subtitle` text · `image` image:A · `spaces*` card{no,title,chips,body,x,y}×7 | 본문 64,160–1216,648 · 상자 15 | `ss/L_SS_MD_A.dc.html` |
| `SS-MF-A` | 제조 · 물류 · 현장 · 공간 맵 | `VM` | MF 제조 · 물류 · 현장 | ready | `space_map` | `title*` text · `subtitle` text · `image` image:A · `spaces*` card{no,title,chips,body,x,y}×7 | 본문 64,160–1216,648 · 상자 15 | `ss/L_SS_MF_A.dc.html` |
| `SS-OE-A` | 파트너 전용 단말 · 공간 맵 | `VM` | OE 파트너 전용 단말 | ready | `space_map` | `title*` text · `subtitle` text · `image` image:A · `spaces*` card{no,title,chips,body,x,y}×7 | 본문 64,160–1216,648 · 상자 15 | `ss/L_SS_OE_A.dc.html` |
| `SS-OF-A` | 오피스 · 공간 맵 | `VM` | OF 오피스 | ready | `space_map` | `title*` text · `subtitle` text · `image` image:A · `spaces*` card{no,title,chips,body,x,y}×7 | 본문 64,160–1216,648 · 상자 15 | `ss/L_SS_OF_A.dc.html` |
| `SS-PB-A` | 공공 · 교통 · 공간 맵 | `VM` | PB 공공 · 교통 | ready | `space_map` | `title*` text · `subtitle` text · `image` image:A · `spaces*` card{no,title,chips,body,x,y}×7 | 본문 64,160–1216,648 · 상자 15 | `ss/L_SS_PB_A.dc.html` |
| `SS-RS-A` | 주거 분양 · 공간 맵 | `VM` | RS 주거 분양 | ready | `space_map` | `title*` text · `subtitle` text · `image` image:A · `spaces*` card{no,title,chips,body,x,y}×7 | 본문 64,160–1216,648 · 상자 15 | `ss/L_SS_RS_A.dc.html` |
| `SS-RT-A` | 리테일 · 플래그십 · 공간 맵 | `VM` | RT 리테일 · 플래그십 | ready | `space_map` | `title*` text · `subtitle` text · `image` image:A · `spaces*` card{no,title,chips,body,x,y}×7 | 본문 64,160–1216,648 · 상자 15 | `ss/L_SS_RT_A.dc.html` |
| `SS-SV-A` | 생활 편의 · 무인 매장 · 공간 맵 | `VM` | SV 생활 편의 · 무인 매장 | ready | `space_map` | `title*` text · `subtitle` text · `image` image:A · `spaces*` card{no,title,chips,body,x,y}×7 | 본문 64,160–1216,648 · 상자 15 | `ss/L_SS_SV_A.dc.html` |
| `SS-TP-A` | 테마파크 · 전시 · 공간 맵 | `VM` | TP 테마파크 · 전시 | ready | `space_map` | `title*` text · `subtitle` text · `image` image:A · `spaces*` card{no,title,chips,body,x,y}×7 | 본문 64,160–1216,648 · 상자 15 | `ss/L_SS_TP_A.dc.html` |
| `SS-VN-A` | 공연장 · 경기장 · 공간 맵 | `VM` | VN 공연장 · 경기장 | ready | `space_map` | `title*` text · `subtitle` text · `image` image:A · `spaces*` card{no,title,chips,body,x,y}×7 | 본문 64,160–1216,648 · 상자 15 | `ss/L_SS_VN_A.dc.html` |
## 유관 사례 (`cases`)

| 코드 | 이름 | 역할 | 업종 · 솔루션 | 상태 | 아키타입 | 칸 | 배치 | 원본 보드 |
|---|---|---|---|---|---|---|---|---|
| `CD-A` | 과제 · 해결 · 성과 | `CD` |  | ready | `case_story` | `title*` text · `subtitle` text · `image*` image:A · `customer` text · `parts*` card{tag,title,body}×3 · `kpis` kpi×3 | 본문 64,160–1216,648 · 상자 14 | `common/L_CS01.dc.html` |
| `CD-B` | 도입 전 → 후 사진 | `CD` |  | ready | `two_images` | `title*` text · `sides*` card{tag,title,body,bullets,image}×2 · `labels` text×2 · `kpis` kpi×3 | 본문 64,136–1216,640 · 상자 15 | `common/L_CD_B.dc.html` |
| `CD-C` | 성과 수치 + 코멘트 | `CD` |  | ready | `case_numbers` | `title*` text · `customer` text · `kpis*` kpi×3 · `quote` text · `who` text · `image` image:A | 본문 64,136–1216,648 · 상자 13 | `common/L_CD_C.dc.html` |
| `CD-D` | 사례 포토 에세이 · 원문 링크 | `CD` |  | ready | `hero_panel` | `title*` text · `image*` image:A · `image_caption` caption · `message` text · `items*` card{no,tag,title,body,kpi,image}×3 | 본문 64,136–1216,648 · 상자 11 | `common/L_CD_D.dc.html` |
| `CL-A` | 2건 비교 | `CL` |  | ready | `pillars` | `title*` text · `pillars*` card{no,tag,title,body,kpi,image}×2 | 본문 64,136–1216,648 · 상자 7 | `common/L_CS02.dc.html` |
| `CL-B` | 3건 요약 | `CL` |  | ready | `pillars` | `title*` text · `pillars*` card{no,tag,title,body,kpi,image}×3 | 본문 64,136–1216,648 · 상자 8 | `common/L_CS03.dc.html` |
| `CL-C` | 레퍼런스 월 | `CL` |  | ready | `logo_wall` | `title*` text · `subtitle` text · `count*` kpi · `logos*` card{title,tag,image}×12 | 본문 64,160–1214,648 · 상자 19 | `common/L_CL_C.dc.html` |
| `CL-D` | 사례 사진 카드 6 | `CL` |  | ready | `image_grid` | `title*` text · `subtitle` text · `items*` card{image,title,body,chips,tag}×6 | 본문 64,160–1216,648 · 상자 12 | `common/L_CL_D.dc.html` |
## Why Samsung (`why`)

| 코드 | 이름 | 역할 | 업종 · 솔루션 | 상태 | 아키타입 | 칸 | 배치 | 원본 보드 |
|---|---|---|---|---|---|---|---|---|
| `CM-A` | 비교표 (삼성 강조) | `CM` |  | ready | `table` | `title*` text · `subtitle` text · `table*` table · `message` text | 본문 64,160–1216,636 · 상자 9 | `common/L_WS01.dc.html` |
| `CM-B` | 요구사항별 충족도 | `CM` |  | ready | `chart_insights` | `title*` text · `subtitle` text · `chart*` chart · `chart_title` text · `insights*` card{no,title,body,kpi}×3 | 본문 88,160–1216,648 · 상자 12 | `common/L_CM_B.dc.html` |
| `CM-C` | 레이더 종합 비교 | `CM` |  | ready | `chart_insights` | `title*` text · `subtitle` text · `chart*` chart · `chart_title` text · `insights*` card{no,title,body,kpi}×3 | 본문 88,160–1216,648 · 상자 12 | `common/L_CM_C.dc.html` |
| `ST-A` | 강점 3 | `ST` |  | ready | `pillars` | `title*` text · `pillars*` card{no,tag,title,body,kpi}×3 | 본문 64,136–1216,648 · 상자 8 | `common/L_WS02.dc.html` |
| `ST-B` | 요구 ↔ 강점 2×2 | `ST` |  | ready | `quad_center` | `title*` text · `quadrants*` card{tag,title,body,bullets,kpi}×4 | 본문 64,136–1216,648 · 상자 9 | `common/L_WS03.dc.html` |
| `ST-C` | 강점 + 증거 수치 | `ST` |  | ready | `pillars` | `title*` text · `pillars*` card{no,tag,title,body,kpi}×3 | 본문 64,136–1216,648 · 상자 8 | `common/L_WS04.dc.html` |
| `ST-D` | 강점 × 증거 사진 | `ST` |  | ready | `pillars` | `title*` text · `pillars*` card{no,tag,title,body,kpi,image}×3 | 본문 64,136–1216,648 · 상자 8 | `common/L_ST_D.dc.html` |
| `SV-A` | 도입 로드맵 | `SV` |  | ready | `gantt` | `title*` text · `subtitle` text · `periods` text×6 · `phases*` card{title,start,end,owner,body}×5 · `milestones` card{title,x}×3 | 본문 64,160–1216,648 · 상자 7 | `common/L_SV_A.dc.html` |
| `SV-B` | 서비스 커버리지 + SLA | `SV` |  | ready | `map_table` | `title*` text · `subtitle` text · `image` image:D · `regions` card{title,kpi}×6 · `table*` table | 본문 64,160–1216,608 · 상자 9 | `common/L_SV_B.dc.html` |
| `SV-C` | 서비스 현장 4단계 | `SV` |  | ready | `path_strip` | `title*` text · `subtitle` text · `steps*` card{no,title,body,chips,image}×4 · `message` text | 본문 64,160–1216,638 · 상자 15 | `common/L_SV_C.dc.html` |
## 제품 스펙 (`spec`)

| 코드 | 이름 | 역할 | 업종 · 솔루션 | 상태 | 아키타입 | 칸 | 배치 | 원본 보드 |
|---|---|---|---|---|---|---|---|---|
| `SC-A` | 사양 비교표 2~5개 | `SC` |  | ready | `table` | `title*` text · `subtitle` text · `table*` table | 본문 64,160–1216,648 · 상자 7 | `common/L_SPEC3.dc.html` |
| `SC-B` | 요구사항 대응표 | `SC` |  | ready | `table` | `title*` text · `subtitle` text · `table*` table | 본문 64,160–1216,648 · 상자 7 | `common/L_SC_B.dc.html` |
| `SC-C` | 카드형 라인업 비교 | `SC` |  | ready | `pillars` | `title*` text · `pillars*` card{no,tag,title,body,kpi,image}×4 | 본문 64,136–1216,648 · 상자 9 | `common/L_SC_C.dc.html` |
| `SD-A` | 그룹별 상세 사양 | `SD` |  | ready | `spec_groups` | `title*` text · `subtitle` text · `product*` card{title,body,image,tag} · `table*` table | 본문 64,160–1216,648 · 상자 8 | `common/L_SPEC1.dc.html` |
| `SD-B` | 치수 · 설치 정보 | `SD` |  | ready | `drawing` | `title*` text · `subtitle` text · `image*` image:D · `table*` table · `kpis` kpi×3 | 본문 84,160–1216,648 · 상자 12 | `common/L_SD_B.dc.html` |
| `SD-C` | 제품 히어로 + 다각도 | `SD` |  | ready | `hero_panel` | `title*` text · `image*` image:C · `image_caption` caption · `message` text · `items*` card{no,tag,title,body,kpi,image}×3 · `kpis` kpi×3 | 본문 64,136–1216,648 · 상자 14 | `common/L_SD_C.dc.html` |
## 부록 (`appendix`)

| 코드 | 이름 | 역할 | 업종 · 솔루션 | 상태 | 아키타입 | 칸 | 배치 | 원본 보드 |
|---|---|---|---|---|---|---|---|---|
| `AX-A` | 이미지 출처 · 사용 조건 | `AX` |  | ready | `sources_table` | `title*` text · `subtitle` text · `summary` bullets×5 · `table*` table | 본문 64,110–1216,626 · 상자 8 | `common/L_AX_A.dc.html` |
| `AX-B` | 현장 사진 갤러리 | `AX` |  | ready | `image_grid` | `title*` text · `subtitle` text · `items*` card{image,title,body,chips,tag}×12 | 본문 64,160–1216,648 · 상자 18 | `common/L_AX_B.dc.html` |

## 참고 보드(템플릿 아님)

| 캔버스 | 보드 | 제목 |
|---|---|---|
| common | `Guide.dc.html` | Winmate 캔버스 안내 |
| common | `Img.dc.html` | 컴포넌트 · 이미지 슬롯 (pid · kind · origin · hint · w · h · credit) |
| common | `Img_Lib.dc.html` | Img 실사 카탈로그 30종 — pid로 넣는 실제 이미지 |
| common | `L_IA1.dc.html` | IA-1 업종 분류 — 도입사례 198건 · 16개 업종 — 도입사례 198건, 16개 업종 — 업종마다 쓰는 제품 · 솔루션이 다릅니다 |
| common | `L_IA2.dc.html` | IA-2 업종 × 제품 — 어느 업종이 어떤 삼성 제품을 썼나 — 시스템에어컨은 14개 업종, 사이니지 · 모바일 · 가전은 업종을 탑니다 |
| common | `L_IA3.dc.html` | IA-3 업종 × 솔루션 — 어느 업종이 어떤 솔루션 · 서비스를 썼나 — 솔루션은 업종을 탑니다 — 그리고 5건 중 2건은 제품만 도입 |
| common | `L_IMG_MAP.dc.html` | IMG-MAP 이미지 중심 템플릿 지도 — 필요한 이미지 종류 × 개수 |
| common | `L_IMG_SYS.dc.html` | IMG-SYS 이미지 슬롯 규격 — 종류 9 · 출처 5 · 채우는 순서 |
| common | `L_MAP.dc.html` | 시트 · 템플릿 지도 — 시트 유형 29 · 템플릿 152 (솔루션 전용 33 · 업종별 21) |
| common | `L_REQ1.dc.html` | REQ 1 제안 콘텐츠 커버리지 — 198건 중 24%만 지금 템플릿으로 완결 |
| common | `L_REQ2.dc.html` | REQ 2 업종 · 제품별 빈칸 — 건설 · 공공 · 제조 · 교육이 약함 |
| common | `L_REQ3.dc.html` | REQ 3 채워야 할 시트 10종 — 사례 수 순서 |
| common | `L_SYS.dc.html` | 레이아웃 시스템 — 시트는 역할, 템플릿은 표현 · 자동 추천 규칙 |
| mi | `Guide.dc.html` | Winmate 캔버스 안내 |
| pi | `Guide.dc.html` | Winmate 캔버스 안내 |
| pi | `L_PI_MAP.dc.html` | PI-MAP 공간별 제품 템플릿 지도 — 같은 목적, 다른 표현 46장 |
| ss | `Guide.dc.html` | Winmate 캔버스 안내 |
| vp | `Guide.dc.html` | Winmate 캔버스 안내 |
| vp | `Photo.dc.html` | 컴포넌트 · 실사 이미지 슬롯 (pid · w · h · fit · pos · credit) |
| vp | `Photo_Lib.dc.html` | 실사 이미지 30종 — 삼성 공식 제품 컷 · 설치 사례 · 공식 연출 · 솔루션 화면 |
| vp | `Prod.dc.html` | 컴포넌트 · 제품 이미지 슬롯 (kind · w · h · zoom · bg) |
| vp | `Prod_Lib.dc.html` | 제품 · 솔루션 이미지 슬롯 13종 — 모든 이미지판이 함께 씀 |
