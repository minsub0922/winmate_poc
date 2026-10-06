/**
 * kb 응답 고정 데이터(00-shell §7.2 모양) — 보드 샘플(QM55C/LH55QMCEBGCXKR · MagicINFO · 카페 메뉴보드 · 프랜차이즈 메뉴보드)을 따른다.
 * 이미지 출처 메타데이터는 docs/screens/webapp1/data/image_sources.json(26장)에서 가져온다. 테스트 전용 — 화면 데이터가 아니다.
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const SRC = JSON.parse(fs.readFileSync(path.resolve(here, '../../../../docs/screens/webapp1/data/image_sources.json'), 'utf8')) as {
  images: Array<{ name: string; title: string; kind: string; sourcePage: string; originalUrl: string; original: { w: number; h: number; format: string; bytes: number };
    stored: { w: number; h: number; format: string; bytes: number }; altOnSource: string; collected: string }>;
};
const byName = (n: string) => SRC.images.find((i) => i.name === n)!;

export const COLLECTED = '2026-10-04T02:10:00Z';
export const PDP = 'https://www.samsung.com/sec/business/smart-signage/qmc-series/LH55QMCEBGCXKR/';
export const CS = 'https://www.samsung.com/sec/business/insights/case-study/';
export const fixtureImg = (id: string) => `/api/kb/v1/_fixture/img/${id}.svg`;

const RIGHTS = (kind: string) => (kind === '도입사례' ? 'customer_case' : 'official');
const KIND = (kind: string) => (kind === '도입사례' ? 'case' : kind === '솔루션' ? 'solution' : 'product');
const CASE_TITLE: Record<string, string> = {
  'reference-MCDONALDSsamsong': '맥도날드 고양삼송DT점 도입사례', 'reference-starbucksDT': '스타벅스 의왕청계DT점 도입사례', milky_presso: '밀키프레소 도입사례',
  'reference-coffeebean': '커피빈 학동역 DT점 · 서초역 1번출구점 도입사례', NFT_artgallary: 'NFT아트갤러리 청담 도입사례',
  'reference-smartsignage-solution': 'NH농협은행 도입사례', 'reference-sheraton': '쉐라톤 서울 디큐브시티 도입사례',
};
const CASE_DATE: Record<string, string> = {
  'reference-MCDONALDSsamsong': '2020-11-12', 'reference-starbucksDT': '2020-05-14', milky_presso: '2026-02-06', 'reference-coffeebean': '2018-03-07',
  NFT_artgallary: '2023-01-30', 'reference-smartsignage-solution': '2022-02-25', 'reference-sheraton': '2017-10-19',
};
const slugOf = (url: string) => url.replace(CS, '').replace(/\/$/, '');

/** image_sources.json 한 장 → ImageMeta */
export function metaOf(name: string, id: string, extra: Record<string, unknown> = {}) {
  const s = byName(name);
  const kind = KIND(s.kind);
  const slug = kind === 'case' ? slugOf(s.sourcePage) : '';
  const pathDate = /\/(\d{4})\/(\d{2})\/(\d{2})\//.exec(s.originalUrl);
  return {
    id, kind, title: s.title, alt: s.altOnSource, label: undefined as string | undefined,
    stored_url: fixtureImg(id), thumb_url: fixtureImg(id),
    original: { width: s.original.w, height: s.original.h, format: s.original.format, bytes: s.original.bytes },
    stored: { width: s.stored.w, height: s.stored.h, format: s.stored.format, bytes: s.stored.bytes },
    focal: null, source_domain: 'samsung.com', grade: kind === 'case' ? 'A' : 'C', rights: RIGHTS(s.kind),
    source_page: kind === 'case' ? { url: s.sourcePage, title: CASE_TITLE[slug], label: CASE_TITLE[slug] }
      : kind === 'product' ? { url: s.sourcePage, title: 'QM55C 제품 페이지', label: 'samsung.com · LH55QMCEBGCXKR' }
        : { url: s.sourcePage, title: '사이니지 콘텐츠관리 MagicINFO', label: 'samsung.com · 사이니지 콘텐츠관리 MagicINFO' },
    original_url: s.originalUrl,
    posted: kind === 'case' ? { date: CASE_DATE[slug], basis: 'case_page' } : pathDate ? { date: `${pathDate[1]}-${pathDate[2]}-${pathDate[3]}`, basis: 'file_path' } : null,
    collected_at: COLLECTED,
    source_type_label: kind === 'case' ? '삼성전자 고객 도입사례' : kind === 'solution' ? '삼성전자 공식 · 솔루션 소개 이미지' : '삼성전자 공식 · 제품 갤러리',
    usage_note: kind === 'case' ? '“도입사례 사진” 표기 필수 · 대외 사용 범위 확인 필요' : '삼성전자 저작물 · 대외 사용 범위 확인 필요',
    page_note: kind === 'solution' ? '이해를 돕기 위한 연출 이미지' : null,
    depicts: [], context: null,
    ...extra,
  };
}
export const cardOf = (m: ReturnType<typeof metaOf>) => ({
  id: m.id, kind: m.kind, title: m.title, alt: m.alt, stored_url: m.stored_url, thumb_url: m.thumb_url, original: m.original, focal: m.focal,
  source_domain: m.source_domain, grade: m.grade, rights: m.rights,
});

// ── 제품 이미지(QMC 시리즈 갤러리 8) ───────────────────
const P_NAMES = ['p01_front', 'p02_back', 'p03_side', 'p04_r45', 'p05_r70', 'p06_port_front', 'p07_port_side', 'p08_bottom_side'];
const P_LABEL = ['정면', '후면', '옆면', '우측 45도', '우측 70도', '후면 포트 정면', '후면 포트 측면', '후면 하단 측면'];
export const PRODUCT_IMAGES = P_NAMES.map((n, i) => metaOf(n, i === 0 ? 'img_9ec6148d2e4d9c18' : `img_qmc_${i + 1}`, { label: P_LABEL[i] }));

// ── 사례 이미지 ────────────────────────────────────────
export const IMG = {
  mcd1: metaOf('mcd1_dt', 'img_mcd1'), mcd2: metaOf('mcd2_double', 'img_mcd2'), mcd3: metaOf('mcd3_inside', 'img_0b58832faefa0ff4'),
  sbx1: metaOf('sbx1_drive', 'img_sbx1'), sbx2: metaOf('sbx2_zone', 'img_sbx2'), sbx3: metaOf('sbx3_signage', 'img_sbx3'),
  mlk1: metaOf('mlk1', 'img_mlk1'), mlk2: metaOf('mlk2', 'img_mlk2'), mlk3: metaOf('mlk3', 'img_mlk3'), cbn3: metaOf('cbn3_inside', 'img_cbn3'),
  nft1: metaOf('nft1', 'img_nft1'), nh1: metaOf('nh1', 'img_nh1'), shr7: metaOf('shr7', 'img_shr7'),
  mi1: metaOf('mi_hero', 'img_mi1', { label: '대표 이미지' }), mi2: metaOf('mi_three', 'img_mi2', { label: '콘텐츠 · 디바이스 · 데이터 관리' }),
  mi3: metaOf('mi_author', 'img_mi3', { label: 'Author 제작 기능' }), mi4: metaOf('mi_server', 'img_mi4', { label: 'Server 재생 목록 · 그룹 · 태그' }),
  mi5: metaOf('mi_device', 'img_mi5', { label: '디바이스 관리' }),
};
export const ALL_IMAGES = [...PRODUCT_IMAGES, ...Object.values(IMG)];

/** 이미지 검색 `카페 메뉴보드`(보드 HomeImage: 도입사례 5 + 제품 1) */
export const IMAGE_SEARCH = [IMG.mcd3, IMG.sbx3, IMG.cbn3, IMG.mlk1, IMG.mcd2, PRODUCT_IMAGES[3]];

// ── 분류 · 시리즈 · 모델 ───────────────────────────────
export const L1 = [
  ['top_display', '사이니지'], ['top_tv_av', 'TV/음향'], ['top_it', 'IT·PC·프린팅'], ['top_mobile', '모바일'], ['top_hvac', '시스템에어컨·공조'],
  ['top_living', '리빙가전'], ['top_kitchen', '주방가전'], ['top_solution', '솔루션'], ['top_service', '서비스'],
].map(([id, name], i) => ({ id, name, level: 1, parent_id: null, order: i + 1, has_children: id === 'top_display', family_count: id === 'top_display' ? 4 : 0 }));
export const L2: Record<string, Array<{ id: string; name: string; level: number; parent_id: string; order: number; has_children: boolean; family_count: number }>> = {
  top_display: [
    { id: 'cat_led-signage', name: '스마트 LED 사이니지', level: 2, parent_id: 'top_display', order: 1, has_children: false, family_count: 2 },
    { id: 'cat_smart-signage', name: '스마트 LCD 사이니지', level: 2, parent_id: 'top_display', order: 2, has_children: false, family_count: 3 },
  ],
};
const fam = (id: string, name: string, series: string | null, count: number, url: string) => ({
  id, name, series_label: series, model_count: count, subcategory: null, is_bundle: false, detail_url: url,
  thumb: cardOf(PRODUCT_IMAGES[0]),
});
export const FAMILIES: Record<string, ReturnType<typeof fam>[]> = {
  'cat_smart-signage': [
    fam('fam_G000182628', '단독형 UHD M 시리즈', 'QMC Series', 7, 'https://www.samsung.com/sec/business/smart-signage/qmc-series/'),
    fam('fam_G000183398', '단독형 UHD M 시리즈 98형', null, 1, 'https://www.samsung.com/sec/business/smart-signage/'),
    fam('fam_G000QBC', '단독형 UHD B 시리즈', 'QBC Series', 2, 'https://www.samsung.com/sec/business/smart-signage/qbc-series/'),
  ],
  'cat_led-signage': [
    fam('fam_IWC', '실내용 The Wall IWC', null, 1, 'https://www.samsung.com/sec/business/led-signage/'),
    fam('fam_IWA', '실내용 The Wall IWA', null, 1, 'https://www.samsung.com/sec/business/led-signage/'),
  ],
};
const FAM_PATH: Record<string, string> = { fam_G000182628: 'cat_smart-signage', fam_G000183398: 'cat_smart-signage', fam_G000QBC: 'cat_smart-signage', fam_IWC: 'cat_led-signage', fam_IWA: 'cat_led-signage' };
export const allFamilies = () => Object.values(FAMILIES).flat();
export const familyById = (id: string) => allFamilies().find((f) => f.id === id);

const CM: Record<number, number> = { 32: 80.1, 43: 107.9, 50: 125.7, 55: 138.7, 65: 163.9, 75: 189.3, 85: 214.6, 98: 247.7 };
function modelRow(code: string, display: string, famId: string, inch: number, nit: number, w: number, h: number, isDefault = false) {
  const f = familyById(famId)!;
  return {
    id: `mdl_${code}`, model_code: code, display_name: display,
    family: { id: f.id, name: f.name, series_label: f.series_label },
    values: {
      size: { display: `${inch}"`, cm: CM[inch] ?? null, inch },
      brightness: { display: `${nit}nit`, nit },
      resolution: { display: w === 3840 ? '4K UHD' : w === 1920 ? 'FHD' : `${w} × ${h}`, w, h },
    },
    thumb: cardOf(PRODUCT_IMAGES[0]), is_family_default: isDefault,
  };
}
export const MODELS = [
  modelRow('LH32QMCEBGCXKR', 'QM32C', 'fam_G000182628', 32, 400, 1920, 1080),
  modelRow('LH43QMCEBGCXKR', 'QM43C', 'fam_G000182628', 43, 500, 3840, 2160),
  modelRow('LH50QMCEBGCXKR', 'QM50C', 'fam_G000182628', 50, 500, 3840, 2160),
  modelRow('LH55QMCEBGCXKR', 'QM55C', 'fam_G000182628', 55, 500, 3840, 2160, true),
  modelRow('LH65QMCEBGCXKR', 'QM65C', 'fam_G000182628', 65, 500, 3840, 2160),
  modelRow('LH75QMCEBGCXKR', 'QM75C', 'fam_G000182628', 75, 500, 3840, 2160),
  modelRow('LH85QMCEBGCXKR', 'QM85C', 'fam_G000182628', 85, 500, 3840, 2160),
  modelRow('LH98QMCEBGCXKR', 'QM98C', 'fam_G000183398', 98, 500, 3840, 2160, true),
  modelRow('LH55QBCEBGCXKR', 'QB55C', 'fam_G000QBC', 55, 350, 3840, 2160, true),
  modelRow('LH65QBCEBGCXKR', 'QB65C', 'fam_G000QBC', 65, 350, 3840, 2160),
  modelRow('IW012C', 'IW012C', 'fam_IWC', 146, 1600, 3840, 2160, true),
  modelRow('IW016A', 'IW016A', 'fam_IWA', 146, 1600, 3840, 2160, true),
];
export const COLUMNS = [{ key: 'size', label: '크기' }, { key: 'brightness', label: '밝기' }, { key: 'resolution', label: '해상도' }];
export const familyCategory = (famId: string) => FAM_PATH[famId];

/** 부록 B 프로필(LH55QMCEBGCXKR, KB value_raw) */
export const SPEC_GROUPS = [
  { name: '디스플레이', rows: [['대각선', '138.7 cm (55형)'], ['패널', 'VA'], ['해상도', '3,840 x 2,160'], ['픽셀 피치', '0.315 x 0.315 mm'], ['밝기 (Typ)', '500 nit'], ['명암비', '4,000:1'], ['시야각', '178/178'], ['응답속도', '8 ms'], ['헤이즈', '25 %'], ['사용 시간', '24/7']] },
  { name: '전원', rows: [['정격 입력', 'AC 100-240 V 50/60 Hz'], ['소비전력', '154 W · 대기 0.5 W']] },
  { name: '크기 · 무게', rows: [['제품 크기', '1237.9 x 708.8 x 28.5 mm'], ['무게', '15.7 kg · 포장 19.9 kg'], ['VESA', '200 x 200 mm'], ['베젤', '11.5 mm (even)']] },
  { name: '연결성', rows: [['HDMI', '입력 3 · 버전 2 · HDCP 2.2'], ['DP', '입력 1 · 버전 1.2'], ['USB', '2'], ['RS232', '입력 · 출력 있음'], ['네트워크', 'RJ45 · Wi-Fi · Bluetooth'], ['오디오', '출력 Stereo Mini Jack']] },
  { name: '운영 · 환경', rows: [['운영체제', 'Tizen 7.0'], ['저장 공간', '16 GB'], ['동작 온도', '0 ~ 40 ℃'], ['동작 습도', '10 ~ 80 (non-condensing) %']] },
  { name: '인증 · 액세서리', rows: [['KC 인증', 'R-R-SEC-LH55QMCE'], ['안전 규격', '60950-1, 62368-1'], ['EMC', 'Class B'], ['마운트', 'WMN-B50SC'], ['스탠드', 'STN-L4355C']] },
].map((g) => ({ name: g.name, rows: g.rows.map(([label, value]) => ({ label, value, attrs: [] })) }));

export function modelDetail(code: string) {
  const row = MODELS.find((m) => m.model_code === code);
  if (!row) return null;
  const f = familyById(row.family.id)!;
  const cat = FAM_PATH[f.id];
  const l2 = Object.values(L2).flat().find((c) => c.id === cat)!;
  const inch = row.values.size.inch;
  return {
    id: row.id, model_code: code, display_name: row.display_name,
    family: { id: f.id, name: f.name, series_label: f.series_label, detail_url: code === 'LH55QMCEBGCXKR' ? PDP : `${f.detail_url}${code}/` },
    category_path: [{ id: 'top_display', name: '사이니지' }, { id: l2.id, name: l2.name }],
    title_line: `${f.name} ${CM[inch] ?? '?'} cm (${inch}형)`,
    key_chips: [row.values.resolution.display, `${row.values.brightness.nit} nit`, '24/7', '두께 28.5 mm', 'Tizen 7.0'],
    facts: [{ label: '출시', value: '2024년 9월' }, { label: '제조국', value: '베트남' }, { label: '동작', value: '0~40 ℃' }],
    supported_solutions: f.id === 'fam_G000182628' ? [
      { id: 'magicinfo', kb_id: 'sol_magicinfo', name: 'MagicINFO', kind_label: 'CMS', evidence: { text: 'QMC 디스플레이는 MagicINFO와 VXT를 지원합니다.', source_url: PDP } },
      { id: 'vxt', kb_id: 'sol_vxt', name: 'VXT', kind_label: 'CMS', evidence: { text: 'QMC 디스플레이는 MagicINFO와 VXT를 지원합니다.', source_url: PDP } },
    ] : [],
    spec: { profile: 'signage', source_url: code === 'LH55QMCEBGCXKR' ? PDP : null, groups: SPEC_GROUPS },
    documents: null,
    verified_at: COLLECTED,
    counts: { images: f.id === 'fam_G000182628' ? 8 : 0, cases: 3 },
    case_corpus: { count: 198, checked_at: COLLECTED },
  };
}

// ── 사례 ───────────────────────────────────────────────
const caseCard = (id: string, slug: string, title: string, vertical: [string, string], detail: string | null, summary: string, products: string[], terms: string[], photos: Array<ReturnType<typeof metaOf>>, count?: number) => ({
  id, title, date: CASE_DATE[slug] ?? null, url: `${CS}${slug}/`, url_display: `samsung.com/sec/business/insights/case-study/${slug}`,
  vertical: { id: vertical[0], name: vertical[1] }, tag_detail: detail, summary,
  products: products.map((label) => ({ label, ref: null, tier: 'T2' })),
  photos: { count: count ?? photos.length, items: photos.map(cardOf) },
  match: { score: 0.8, breakdown: { vertical: 1, space: 0.5, product: 0.4, text: 0.6 }, terms }, source_tier: 'official',
});
export const CASES = [
  caseCard('dep_1490', 'reference-MCDONALDSsamsong', '맥도날드 고양삼송DT점 – 삼성 스마트 사이니지', ['kr_retail_fnb', '유통/요식'], 'DT',
    '드라이브스루 실외 메뉴판과 매장 전면 양면형 사이니지로 종이 메뉴판을 없앤 매장. 신제품 · 프로모션 소재는 MagicINFO Player로 원격 교체합니다.',
    ['실외용 OMN-D 시리즈', 'MagicINFO Player'], ['메뉴보드', '프랜차이즈'], [IMG.mcd1, IMG.mcd2, IMG.mcd3]),
  caseCard('dep_1312', 'reference-starbucksDT', '스타벅스 의왕청계DT점 – 삼성 스마트 사이니지', ['kr_retail_fnb', '유통/요식'], 'DT',
    '차량이 들어오면 메뉴 화면을 바꿔 보여 주고, 주문 내역은 별도 사이니지로 확인하는 드라이브스루. 직사광선 · 비바람을 견디는 실외용 모델을 썼습니다.',
    ['실외용 OMD-W · OM75D-W'], ['메뉴보드', '프랜차이즈'], [IMG.sbx2, IMG.sbx1, IMG.sbx3]),
  caseCard('dep_2601', 'milky_presso', '밀키프레소 - 삼성 VXT 솔루션 + 스마트 사이니지', ['kr_retail_fnb', '유통/요식'], '카페',
    '가맹점 사이니지 콘텐츠를 본사에서 VXT로 원격 통합 관리하고, 시간대별 재생 목록으로 프로모션을 운영하는 프랜차이즈 카페입니다.',
    ['Samsung VXT', '스마트 사이니지'], ['프랜차이즈', '본사 일괄 관리'], [IMG.mlk1, IMG.mlk2, IMG.mlk3]),
];
export const HOTEL_CASE = caseCard('dep_33', 'reference-sheraton', '쉐라톤 서울 디큐브시티 호텔 – 삼성 스마트 사이니지(홍보용), 매직인포(MagicINFO) 솔루션', ['kr_hotel', '호텔'], '로비',
  '로비부터 고층부까지 사이니지 콘텐츠를 웹으로 원격 수정하고, 연회 · 웨딩 일정에 맞춰 이벤트 스케줄로 미리 예약합니다.', ['스마트 사이니지', 'MagicINFO'], ['호텔'], [IMG.shr7, IMG.shr7, IMG.shr7]);

export const MODEL_CASES = {
  corpus: { count: 198, checked_at: COLLECTED }, counts: { model: 0, series: 0, usage: 3 }, usage_label: '매장 메뉴보드',
  items: [
    { ...CASES[0], summary: '매장 안쪽 메뉴보드는 세부 메뉴 정보를 보여 주고, 전면 양면형 사이니지가 밖의 고객을 맞습니다. 소재 교체는 MagicINFO Player로 원격 처리.', match_type: 'usage', used_products_line: '실외용 OMN-D 시리즈(양면형) · MagicINFO Player', photos: { count: 3, items: [cardOf(IMG.mcd3)] } },
    { ...caseCard('dep_1101', 'reference-coffeebean', '커피빈 학동역 DT점, 서초역 1번출구점 – 삼성 스마트 사이니지', ['kr_retail_fnb', '유통/요식'], '카페', '서초역점은 카운터에 슬림 베젤 메뉴보드를 원목 인테리어에 맞춰 걸었고, 학동 DT점은 실외용 사이니지를 세로로 돌려 메뉴판으로 씁니다.', [], [], [IMG.cbn3]), match_type: 'usage', used_products_line: '실외용 OMD-K 시리즈 · 메뉴보드 사이니지 · 시스템에어컨 360' },
    { ...CASES[2], summary: '카운터 상단 메뉴보드 콘텐츠를 본사가 VXT로 관리하고, 시간대별 고객층에 맞춰 재생 목록을 바꿔 프로모션을 돌립니다.', match_type: 'usage', used_products_line: '스마트 사이니지 · Samsung VXT' },
  ],
};

// ── 솔루션 11(§5.4.2) ─────────────────────────────────
export const SOLUTIONS = [
  ['magicinfo', 'MagicINFO', '디스플레이', '디스플레이 · 설치형 사이니지 CMS · 콘텐츠 · 스케줄 · 데이터 연동', 'MGI', 'sol_magicinfo', ['retail', 'hospitality', 'education', 'healthcare', 'office']],
  ['vxt', 'Samsung VXT', '디스플레이', '디스플레이 · 클라우드 사이니지 CMS · Canvas · 원격 관리', 'VXT', 'sol_vxt', ['retail', 'office']],
  ['smartthings_pro', 'SmartThings Pro', '공간 · 에너지', '공간 · 에너지 · 여러 사업장 IoT · 에너지 대시보드', 'STP', 'sol_smartthings_pro', ['retail', 'office']],
  ['biot', 'b.IoT', '공간 · 에너지', '공간 · 에너지 · 공조 중심 빌딩 관리', 'BIT', 'sol_biot', ['office']],
  ['lynk_cloud', 'LYNK Cloud', '호스피탈리티', '호스피탈리티 · 호텔 객실 TV · 투숙객 서비스', 'LYN', 'sol_lynk_cloud', ['hospitality']],
  ['knox_suite', 'Knox Suite', '모바일', '모바일 · 업무용 갤럭시 등록 · 관리 · 보안', 'KNX', 'sol_knox', ['retail', 'office', 'education', 'healthcare']],
  ['knox_capture', 'Knox Capture', '모바일', '모바일 · 갤럭시 카메라로 바코드 스캔', 'KCP', null, ['retail']],
  ['dex', 'Samsung DeX', '모바일', '모바일 · 휴대폰을 모니터에 연결해 PC처럼', 'DEX', null, ['office', 'education']],
  ['cold_chain', '삼성 콜드체인', '공조', '공조 · 냉장 · 냉동 쇼케이스 · 저장고 + 에어컨 통합 관리', 'CCH', null, ['retail']],
  ['hvac_integrated', '삼성 통합공조', '공조', '공조 · 개별공조 + 중앙공조 + b.IoT 통합', 'HVC', null, ['office', 'hospitality']],
  ['sac_control', 'SAC 제어 시스템', '공조', '공조 · 리모컨부터 DMS · BMS 연동 · 전력량 분배', 'SAC', null, ['office']],
].map(([id, name, domain, desc, template_code, kb_id, industries]) => ({ id, name, domain, desc, icon: null, template_code, kb_id, industries }));

export const MAGICINFO = {
  id: 'magicinfo', name: 'MagicINFO', version_label: 'MagicINFO™ 8', category_path: ['디스플레이 솔루션', '사이니지 CMS'],
  subtitle: '삼성 스마트 사이니지 콘텐츠 관리 솔루션 (CMS)', key_chips: ['Author · Server · Player', '설치형', '클라우드형 (월 구독)'],
  purchase: { site_code: 'BW-MIP70PA', label: '별도 구매 · 견적 문의 (BW-MIP70PA) · 라이선스 단가 [견적 확인]' },
  quote_url: 'https://www.samsung.com/sec/business/display-solution/display-solution-bwmip70pa/BW-MIP70PA/',
  intro_url: 'https://www.samsung.com/sec/business/display-solutions/magicinfo/',
  supported_devices: { label: '삼성 스마트 사이니지', example: { family_id: 'fam_G000182628', series_label: 'QMC Series', model_code: 'LH55QMCEBGCXKR', display_name: 'QM55C' } },
  profile: {
    intro: '콘텐츠를 만들고 예약해 배포하는 일, 사이니지 기기를 원격으로 살피는 일, 외부 데이터를 화면에 연결하는 일을 한 서버에서 하는 삼성 사이니지 CMS입니다.',
    pillars: [{ name: '콘텐츠 관리', items: ['제작', '스케줄링', '배포'] }, { name: '디바이스 관리', items: ['모니터링', '제어', '알림'] }, { name: '데이터 관리', items: ['자동화', '분석', '시각화'] }],
    parts: [
      { name: 'MagicINFO Author', does: '템플릿 · 클립아트 · 시각 효과를 조합해 콘텐츠를 만들고, HTML · CSS · JS 요소도 코딩 없이 넣습니다.' },
      { name: 'MagicINFO Server', does: '재생 목록에 담아 날짜 · 시간별로 예약 배포하고, 연결된 기기를 실시간 모니터링 · 원격 제어하며 통계를 봅니다.' },
      { name: 'MagicINFO Player', does: '8K 화질과 멀티스크린 동시 재생을 지원하고, 거의 모든 웹 표준 콘텐츠를 재생합니다.' },
      { name: 'MagicINFO Datalink', does: '외부 데이터를 콘텐츠에 연결하는 기능 (공식 기능 목록 기준).' },
    ],
    deploy: [
      { name: '설치형 — 고객사 서버', desc: '웹으로 MagicINFO 서버에 접속해 네트워크의 모든 디스플레이를 원격 관리합니다.', evidence: { deployment_id: 'dep_33', title: '쉐라톤 서울 디큐브시티 사례', date: '2017-10-19' } },
      { name: '클라우드형 — 월 구독', desc: '별도 서버 구축 없이 월 구독으로 씁니다. 일반 기업 첫 도입 사례로 소개됨.', evidence: { deployment_id: 'dep_2129', title: 'NH농협은행 사례', date: '2022-02-25' } },
    ],
    device_functions: ['보안 제어', '원격 펌웨어 업데이트', '기기 상태', '메일 알림'],
    source_note: '출처 · samsung.com MagicINFO 소개 페이지 · 견적 페이지 · 도입사례 2건 (2026-10-02 확인) · 설명은 원문을 줄여 쓴 것',
  },
  messages: [], verified_at: COLLECTED, counts: { images: 9, cases: 17 },
};
export const solutionDetail = (id: string) => {
  if (id === 'magicinfo') return MAGICINFO;
  const s = SOLUTIONS.find((x) => x.id === id);
  if (!s) return null;
  return {
    id: s.id, name: s.name, version_label: null, category_path: [s.domain as string], subtitle: null, key_chips: [], purchase: null,
    quote_url: null, intro_url: null, supported_devices: null, profile: null,
    messages: id === 'knox_capture' ? [] : [{ level: 'value_prop', text: `${s.name} 메시지(고정 데이터)`, children: [] }], verified_at: COLLECTED, counts: { images: 0, cases: 0 },
  };
};
export const MAGICINFO_IMAGES = {
  groups: [
    { key: 'official', label: '공식 소개 이미지', source_label: 'samsung.com MagicINFO 소개', items: [IMG.mi1, IMG.mi2, IMG.mi3, IMG.mi4, IMG.mi5] },
    { key: 'case', label: '도입사례 사진', source_label: 'samsung.com 고객 도입사례', items: [IMG.nft1, IMG.nh1, IMG.shr7, IMG.mcd3] },
  ],
  total: 9,
};
const mention = (id: string, title: string, date: string, slug: string) => ({ id, title, date, url: `${CS}${slug}/` });
export const MAGICINFO_CASES = {
  corpus: { count: 198, checked_at: COLLECTED }, total: 17,
  title_explicit: [
    caseCard('dep_2549', 'NFT_artgallary', 'NFT아트갤러리 청담 – 스마트 사이니지 + MagicINFO 솔루션', ['kr_culture', '문화/여가'], null, '수십 대의 LCD 사이니지를 MagicINFO로 한 번에 원격 관리하고, 스케줄링으로 작품 송출 순서 · 시간 · 반복 주기를 미리 정해 둡니다.', [], [], [IMG.nft1]),
    caseCard('dep_2129', 'reference-smartsignage-solution', 'NH농협은행 - 스마트 LED 사이니지 + MagicINFO솔루션', ['kr_finance', '금융'], null, '본사 로비 LED 사이니지에 홍보 콘텐츠를 반복 노출합니다. 별도 서버가 필요 없는 월 구독형 MagicINFO 클라우드형을 도입했습니다.', [], [], [IMG.nh1]),
    caseCard('dep_33', 'reference-sheraton', '쉐라톤 서울 디큐브시티 호텔 – 삼성 스마트 사이니지(홍보용), 매직인포(MagicINFO) 솔루션', ['kr_hotel', '호텔'], null, '로비부터 고층부까지 사이니지 콘텐츠를 웹으로 원격 수정하고, 연회 · 웨딩 일정에 맞춰 이벤트 스케줄로 미리 예약합니다.', [], [], [IMG.shr7]),
  ],
  body_mentions: [
    mention('dep_1490', '맥도날드 고양삼송DT점 – 삼성 스마트 사이니지', '2020-11-12', 'reference-MCDONALDSsamsong'), mention('dep_m2', '팩토리얼 성수 - AI 오피스', '2024-12-02', 'factorial_seongsu'),
    mention('dep_m3', '이트너스 - AI 오피스', '2024-09-26', 'etners_ai_office'), mention('dep_m4', '룰루레몬 파르나스몰 스토어', '2022-01-10', 'Lululemon-parnasmall_Signage'),
    mention('dep_m5', '에버랜드 – 스마트 LED 사이니지', '2021-05-25', 'reference-EverlandSmartLED1'), mention('dep_m6', 'SKT - 삼성 스마트 사이니지', '2020-04-09', 'reference-SKT'),
    mention('dep_1101', '커피빈 학동역 DT점, 서초역 1번출구점 – 삼성 스마트 사이니지', '2018-03-07', 'reference-coffeebean'), mention('dep_m8', '이가자헤어비스', '2017-11-27', 'reference-leekaja'),
    mention('dep_m9', '현대백화점 판교점', '2017-11-27', 'hyundai-pankyo'), mention('dep_m10', '한국IBM', '2017-11-27', 'korea-ibm'),
    mention('dep_m11', '말리커피', '2017-11-27', 'marley-coffee'), mention('dep_m12', '제주 유민 미술관', '2017-10-25', 'reference-yumin'),
    mention('dep_m13', '인천SK행복드림구장', '2017-10-12', 'reference-incheonsk-bigboard'), mention('dep_m14', '크라운 파크 호텔 서울', '2017-09-28', 'crownparkhotel'),
  ],
};

export const VERTICALS = [
  { id: 'kr_retail_fnb', name: '유통/요식', parent_id: null }, { id: 'kr_retail', name: '유통', parent_id: 'kr_retail_fnb' }, { id: 'kr_fnb', name: '외식', parent_id: 'kr_retail_fnb' },
  { id: 'kr_hotel', name: '호텔', parent_id: null }, { id: 'kr_office', name: '오피스', parent_id: null }, { id: 'kr_small_office', name: '소규모 오피스', parent_id: 'kr_office' },
  { id: 'kr_school', name: '교육', parent_id: null }, { id: 'kr_academy', name: '학원', parent_id: 'kr_school' },
  { id: 'kr_hospital', name: '병원', parent_id: null }, { id: 'kr_clinic', name: '의원', parent_id: 'kr_hospital' },
];

/** 기간별 코퍼스 수(고정 데이터) */
export const CORPUS_BY_PERIOD: Record<string, number> = { all: 198, '5y': 83, '3y': 41, '1y': 12 };
export const TODAY = '2026-10-06';

export const PRODUCT_SEARCH: Record<string, unknown[]> = {};
