/**
 * MOCK — 보드(docs/screens/webapp3) 예시 값으로 만든 응답. 화면 테스트 · 스크린샷 비교용(mock.ts 와 함께).
 * 실제 백엔드가 이 경로를 구현해도 이 고정값으로 보드와 같은 화면을 그려 비교한다.
 */
// ── PR1F RFP ──────────────────────────────────────────────
export const rfpDone = {
  status: 'done', job_id: null, error: null,
  files: [{ file_id: 'file_mock_rfp', name: 'A커피_디지털메뉴보드_RFP.pdf', kind_label: 'PDF', pages: 24 }], extra_files: [],
  phases: [{ key: 'read', label: '읽기', status: 'done' }, { key: 'find', label: '항목 찾기', status: 'done' }, { key: 'fill', label: '채우기', status: 'done' }],
  excerpts: [
    { page: 1, page_label: 'p.1 · 표지', parts: [{ text: 'A 커피 프랜차이즈', field_no: 1 }, { text: ' — ' }, { text: '전국 매장 디지털 메뉴보드 전환', field_no: 2 }, { text: ' 제안 요청서' }] },
    { page: 2, page_label: 'p.2 · 사업 개요', parts: [{ text: '당사는 ' }, { text: '커피 전문점', field_no: 3 }, { text: ' 브랜드로 전국 ' }, { text: '320개 직영 · 가맹 매장', field_no: 4 }, { text: '을 운영합니다.' }] },
    { page: 5, page_label: 'p.5 · 요구 사항', parts: [{ text: '본사에서 전 매장 콘텐츠를 일괄 배포', field_no: 5 }, { text: '하고, 프로모션 교체 주기를 줄일 방안을 제안해 주십시오.' }] },
    { page: 11, page_label: 'p.11 · 일정', parts: [{ text: '제안서 제출 ' }, { text: '2026년 10월 15일', field_no: 6 }, { text: ', 제안 설명회 ' }, { text: '10월 22일 (발표 20분)', field_no: 7 }] },
  ],
  fields: [
    ['customer', '고객사', 'A 커피 프랜차이즈', 'p.1', 'found'], ['title', '프로젝트명', '전국 매장 디지털 메뉴보드 전환', 'p.1', 'found'],
    ['industry', '업종', '외식 · 카페 프랜차이즈', 'p.2', 'guess'], ['scale', '규모', '320개 매장 (직영 · 가맹)', 'p.2', 'found'],
    ['requirements', '요구사항', '5건 · 콘텐츠 일괄 배포 외 4', 'p.5–7', 'found'], ['submit_due', '제안 제출일', '2026-10-15', 'p.11', 'found'],
    ['presentation', '제안 설명회', '2026-10-22 · 발표 20분', 'p.11', 'found'], ['budget', '예산 범위', '', '—', 'empty'], ['decision_makers', '의사결정자', '', '—', 'empty'],
  ].map(([key, label, value, src, state], i) => ({
    no: i + 1, key, label, value, source: state === 'empty' ? null : { page: 1, page_label: src }, source_label: src,
    state, state_label: state === 'found' ? '찾음' : state === 'guess' ? '추정' : '비어 있음', edited: false,
  })),
  tally: { found: 6, guess: 1, empty: 2 }, found_count: 7,
  intro: 'RFP를 읽고 고객 · 프로젝트 정보를 채웠어요. 원문에서 찾은 곳에 번호를 달아 두었으니 맞는지 확인해 주세요. 원문에 없는 2개 항목은 비워 두었어요.',
  rq_count: 5, rq_label: '요구사항 5건은 시트 구성 추천과 섹션 작성에 그대로 쓰여요.', rq_ref: null, confirmed: false,
};

// ── PR1L 기존 작업 ─────────────────────────────────────────
const W = [
  ['storyboard', 'Storyboard', 'A 커피 프랜차이즈 매장 리뉴얼', 'Key Message 4 · 어제', '고객 정보 · Value Props', true],
  ['mi', 'Market Intelligence', 'A 커피 프랜차이즈 시장·경쟁사 분석', '분석 완료 · 3일 전', 'MI · Why Samsung', true],
  ['birdseye', '공간 조감도', '강남 플래그십 1층 로비', '존 4 · 지난주', '조감도 · 공간별 제품', true],
  ['scenario', '공간 시나리오', 'A 커피 매장 하루 시나리오', '장면 6 · 지난주', '솔루션 제안', true],
  ['image', '이미지 생성', '카페 매장 메뉴보드 시안', '이미지 4장 · 지난주', '공간별 제품 이미지', false],
  ['spec', 'Spec 시트', 'QMC vs QBC 55" 비교', '시트 1 · 2주 전', '제품 스펙', false],
] as const;
export const relatedWorks = {
  scope: 'customer', customer_name: 'A 커피 프랜차이즈', work_count: 6, on_count: 4,
  intro: 'A 커피 프랜차이즈와 이어진 작업 6건을 찾았어요. 연결하면 고객 정보는 Storyboard에서 채우고, 각 작업 결과는 맞는 섹션에 미리 넣어 둡니다. 연결은 섹션 작성 중에도 바꿀 수 있어요.',
  footer_label: '기존 작업에서 시작 · 작업 4건 연결 · 1 / 6',
  works: W.map(([feature, tool, title, meta, target, on], i) => ({ feature, ref_id: `${feature}_mock_${i}`, title, tool_label: tool, meta, target_label: target, default_on: on, on })),
  preview: {
    customer_from: { feature: 'storyboard', label: 'Storyboard' }, customer_summary: 'A 커피 프랜차이즈 · 외식 · 카페 · 320개 매장 · 요구사항 5건',
    recommended_type: { type: 'standard', name: '표준 제안서', reason: '조감도 · 시나리오가 있어 공간 섹션까지 채울 수 있어요.' },
    sections: [
      ['mi', 'Market Intelligence', 'full', 'MI 작업'], ['vp', 'Value Props', 'full', 'Storyboard'], ['birdseye', '조감도', 'full', '조감도'],
      ['spaceProducts', '공간별 제품', 'partial', '조감도 배치안'], ['solution', '솔루션 제안', 'partial', '시나리오'], ['cases', '유관 사례', 'new', '새로 찾기'],
      ['why', 'Why Samsung', 'partial', 'MI 경쟁사'], ['spec', '제품 스펙', 'new', '새로 작성'],
    ].map(([key, name, state, src]) => ({ key, name, state, state_label: state === 'full' ? '채움' : state === 'partial' ? '일부' : '새로 작성', source_label: src })),
    counts: { full: 3, partial: 3, new: 2 }, counts_label: '채움 3 · 일부 3 · 새로 작성 2',
  },
};

// ── PR1C · PRU 기존 제안서 활용 ─────────────────────────────
const SECS = [['표지', 1, '#121417'], ['시장', 3, '#1428a0'], ['고객 과제', 3, '#8a3b00'], ['가치 제안', 4, '#0b6e4f'], ['솔루션', 5, '#5b2bb5'], ['사례', 3, '#0e7490'], ['스펙', 2, '#596170'], ['견적 · 일정', 3, '#c2410c']] as const;
const pagesOf = () => {
  const out: any[] = [];
  let no = 1;
  const TITLES = ['표지 · B 베이커리 매장 사이니지 제안', '오프라인 매장, 디지털 전환의 기로', '국내 QSR 디지털 메뉴보드 도입 추이', '경쟁 브랜드 도입 현황', 'B 베이커리 매장 운영 과제 3가지', '점주 인터뷰 요약', '가치 제안: 본사 통제 · 운영 부담 ↓', '기대 효과 Before / After', '솔루션 구성도 MagicINFO', '매장 동선별 사이니지 배치'];
  const ROLES = ['표지', '문제 제기', '시장 변화', '시장 변화', '고객 과제', '고객 과제', '가치 제안', '가치 제안', '솔루션 구성', '솔루션 구성'];
  const EVID = ['—', '근거 p.3 시장 수치', '[출처 없음] · 수치 출처 미기재', '근거 p.3 보강 · 경쟁 5개 브랜드', '근거 p.6 점주 인터뷰', 'p.5의 근거 역할 · 인용 4건', '근거 p.8 기대 효과', '근거 없음 · 수치 출처 없음', '근거 p.17 도입 사례', '역할 후보 2 · 공간 시나리오로 볼 수도'];
  const ST = ['auto', 'ok', 'auto', 'ok', 'edited', 'auto', 'ok', 'auto', 'auto', 'need'];
  for (const [name, n, color] of SECS) {
    for (let i = 0; i < n; i += 1) {
      const k = no - 1;
      out.push({
        no, title: TITLES[k] ?? `${name} ${i + 1}`, section_name: name, section_color: color, flow_role: ROLES[k] ?? (name === '견적 · 일정' ? '견적 · 일정' : name === '사례' ? '도입 사례' : name === '스펙' ? '제품 스펙' : '솔루션 구성'),
        role_state: ST[k] ?? 'auto', role_state_label: ({ auto: '자동', ok: '확인됨', edited: '수정함', need: '확인 필요' } as Record<string, string>)[ST[k] ?? 'auto'],
        role_candidates: k === 9 ? ['솔루션 구성', '공간 시나리오'] : [], evidence: EVID[k] ?? '근거 앞 쪽', evidence_warn: k === 2 || k === 7 || k === 9,
        excluded: name === '견적 · 일정', exclude_reason: name === '견적 · 일정' ? '비복제 · 자동 제외' : null, locked: ST[k] === 'edited',
      });
      no += 1;
    }
  }
  return out;
};
const CRIT = [
  [1, 'structure', '문서 구조', false, '24장 → 섹션 8개 복원 · 표지 · 목차 · 부록 없음 · 견적 3장 분리', 96, 'ok'],
  [2, 'flow', '논리 흐름', true, "시장 변화 → 고객 과제 → 가치 → 솔루션 → 사례 → 스펙 → 견적 · '문제 해결형' · Why Samsung 고리 없음", 82, 'need'],
  [3, 'messages', '핵심 메시지', false, "KM 3개 · '매장별 운영 부담 ↓ · 본사 통제 ↑ · 고객 체류 ↑' · 톤 운영 효율 중심", 88, 'ok'],
  [4, 'context', '고객 · 프로젝트 맥락', true, 'B 베이커리 · 베이커리 프랜차이즈 180개 매장 · 요구사항 4건 → 이번 5건과 겹침 3 · 다름 2', 90, 'need'],
  [5, 'products', '제품 · 솔루션', false, 'QM55B ×2 · QB65B · MagicINFO 8 · 단종 1종(QM55B → QM55C) · 버전 1종(MagicINFO 9)', 93, 'edited'],
  [6, 'data', '데이터 · 수치', false, '시장 수치 2024 기준 3건(오래됨) · 효과 수치 4건 중 출처 없음 2건', 85, 'ok'],
  [7, 'assets', '이미지 · 자산', false, '31개 · 삼성 공식 14 재사용 가능 · B 베이커리 매장 사진 9 사용 불가 · 출처 미상 8', 79, 'need'],
  [8, 'design', '디자인 · 템플릿', false, '21장 Winmate 시트 유형 매핑 · 매핑 실패 3장(견적 · 일정 · 손글씨 도식)', 74, 'need'],
  [9, 'noncopy', '비복제 · 민감 항목', true, '견적 2장 · 일정 1장 · B 베이커리 매출 1건 → 자동 제외', 99, 'ok'],
] as const;
const FLOW = {
  steps: [
    { name: '문제 제기', count: 1 }, { name: '시장 변화', count: 3 }, { name: '고객 과제', count: 3 }, { name: '가치 제안', count: 4 }, { name: '솔루션 구성', count: 5 },
    { name: '도입 사례', count: 3 }, { name: 'Why Samsung · 경쟁 비교', count: 0, dashed: true }, { name: '제품 스펙', count: 2 }, { name: '견적 · 일정', count: 3, excluded: true },
  ],
  pattern: { name: '문제 해결형', en: 'Problem → Solution' }, claims: { linked: 11, total: 14 }, broken: ['p.3 출처 없음', 'p.8 근거 없음', 'Why Samsung 단계 없음'],
  memos: [
    { no: 1, text: 'Why Samsung 단계가 없어 R5 POS 연동의 신뢰 근거가 약해요. 경쟁 비교 시트 2장 추가를 제안해요.', tag: 'R5', action: '시트 구성에 신규 추가' },
    { no: 2, text: 'p.8 기대 효과는 출처가 없어요. 흐름(Before / After)만 가져오고 수치는 이번 고객 기준으로 새로 채워요.', tag: '수치', action: '[00]% 플레이스홀더 · 확정 필요 등록' },
    { no: 3, text: 'p.10을 공간 시나리오로 보면 이번 320개 매장 단계 도입(R4)에 맞아요. 역할을 바꾸면 로드맵 시트와 이어져요.', tag: 'R4', action: '역할 후보 선택 대기' },
  ],
};
const ROW = (row_id: string, group: string, page: number | null, sheet_name: string, verdict: string, note: string, rq_ids: string[] = [], extra: Record<string, unknown> = {}) =>
  ({ row_id, group, page, page_label: page ? `p.${page}` : '신규', sheet_name, verdict, verdict_label: ({ keep: '유지', update: '갱신', rewrite: '재작성', new: '신규', drop: '제외' } as Record<string, string>)[verdict], note, rq_ids, ...extra });
export const planImprove = {
  groups: [
    { name: 'Market Intelligence', count: 3, range: 'p.2–4', rows: [ROW('r2', 'mi', 2, '시장 규모 · 성장', 'update', '2025.11 수치 → 최신 [00] 조사로 갱신'), ROW('r3', 'mi', 3, '고객사 비즈니스', 'update', '매장 280 → 320 · 직영 · 가맹 비율 갱신'), ROW('r4', 'mi', 4, '경쟁 환경', 'keep', '경쟁 구도 변화 없음 · 기준일만 표시')] },
    { name: 'Value Props', count: 3, range: 'p.5–7', rows: [ROW('r5', 'vp', 5, '가치 제안', 'rewrite', '지난 KM 매장 경험 → 이번 본사 통제 · 교체 주기', ['R1', 'R2']), ROW('r6', 'vp', 6, '이해관계자별 가치', 'keep', '본사 · 점주 · 손님 3축 그대로'), ROW('r7', 'vp', 7, '기대 효과', 'rewrite', '효과 수치 기준 바뀜 · 교체 주기 기준으로', ['R2'])] },
    { name: '조감도', count: 1, range: 'p.8', rows: [ROW('r8', 'birdseye', 8, '매장 조감도', 'drop', '매장 구조 달라 새로 생성 · 조감도 작업으로')] },
    { name: '공간별 제품', count: 3, range: 'p.9–11', rows: [ROW('r9', 'sp', 9, '공간 맵', 'keep', '카운터 · 대기 · 픽업 3공간 동일'), ROW('r10', 'sp', 10, '카운터 메뉴보드', 'update', 'QM55B 단종 → QM55C 후속 치환'), ROW('r11', 'sp', 11, '대기 공간', 'keep', '매장 사진 2025 촬영 · 재사용 가능')] },
    { name: '솔루션 제안', count: 2, range: 'p.12–13', rows: [ROW('r12', 'sol', 12, 'MagicINFO 소개', 'update', 'MagicINFO 8 → 9 · 기능 표 갱신'), ROW('r13', 'sol', 13, '구성도', 'rewrite', 'POS 연동 추가 · 본사 배포 경로 다시 그림', ['R5'])] },
    { name: '요구사항 갭에서 추가', count: 2, label: '2장 · 원본에 없음', is_new: true, rows: [ROW('n1', 'new', null, '매장별 가격 차등 운영', 'new', '원본에 없음 → 본사 템플릿 + 매장 변수', ['R3']), ROW('n2', 'new', null, '320개 매장 단계 도입 로드맵', 'new', '원본에 없음 → 권역별 3단계', ['R4'])] },
  ],
  requirement_coverage: [
    { rq_id: 'rq1', code: 'R1', name: '본사 콘텐츠 일괄 배포', state: 'has', state_label: '있음', where: '원본 p.5 가치 제안 · 그대로 이어감' },
    { rq_id: 'rq2', code: 'R2', name: '프로모션 교체 주기 단축', state: 'part', state_label: '일부', where: '원본 p.7 기대 효과 · 수치 기준 다름' },
    { rq_id: 'rq3', code: 'R3', name: '매장별 메뉴 가격 차등', state: 'none', state_label: '없음 → 신규', where: '원본에 없음 → 신규 시트 1장' },
    { rq_id: 'rq4', code: 'R4', name: '320개 매장 단계 도입', state: 'none', state_label: '없음 → 신규', where: '원본에 없음 → 로드맵 신규 1장' },
    { rq_id: 'rq5', code: 'R5', name: '기존 POS 연동', state: 'part', state_label: '일부', where: '원본 p.13 구성도 · 연동 경로 추가' },
  ],
  only_in_source: [{ label: '매장 경험 Key Message · p.5', tag: '제외 제안' }, { label: '2025 프로모션 일정 · p.19', tag: '비복제' }],
  totals: { keep: 5, update: 5, rewrite: 3, new: 2, drop: 6 }, source_total: 21, new_total: 22,
  summary_note: '제외 6장에는 견적 · 일정(비복제) · 조감도가 들어 있어요. 유저가 고친 판정은 다시 분석해도 바뀌지 않아요.',
  shown_label: '12 / 21장 표시 · 나머지 9장 보기', footer_label: '활용 계획 · 원본 21장 → 새 제안서 22장 · 1 / 6',
};
export const planBorrow = {
  rows: [
    { src_step: '문제 제기', src_count: 1, src_range: 'p.2', kind: 'flow', new_label: '표지 · 제안 배경 1장', note: '신규 작성 · 이번 프로젝트 배경으로', rq_ids: [], new_count: 2 },
    { src_step: '시장 변화', src_count: 3, src_range: 'p.3–4', kind: 'flow', new_label: 'Market Intelligence 3장', note: '시장 규모 · 성장 / 고객사 비즈니스 / 경쟁 환경 — 수치는 MI 작업으로 새로 조사', rq_ids: [], new_count: 3 },
    { src_step: '고객 과제', src_count: 3, src_range: 'p.5–6', kind: 'flow', new_label: "Value Props 안 '과제' 1장", note: 'R1 · R2 · R3에서 추출 · 점주 인터뷰 대신 요구사항이 근거', rq_ids: ['R1', 'R2', 'R3'], new_count: 1 },
    { src_step: '가치 제안', src_count: 4, src_range: 'p.7–10', kind: 'flow', new_label: 'Value Props 3장', note: '흐름 유지 · Key Message는 A 커피 톤(본사 통제 · 교체 주기)으로', rq_ids: ['R1', 'R2'], new_count: 3 },
    { src_step: '솔루션 구성', src_count: 5, src_range: 'p.11–15', kind: 'flow', new_label: '솔루션 제안 3장 + 공간별 제품 4장', note: 'MagicINFO 전용 소개 · 구성도 · 공간 시나리오 / 공간 맵 · 카운터 · 대기 · 픽업', rq_ids: ['R1', 'R5'], new_count: 7 },
    { src_step: '도입 사례', src_count: 3, src_range: 'p.16–18', kind: 'flow', new_label: '유관 사례 2장', note: '외식 · 카페 사례로 교체 · B 베이커리 사례 사용 안 함', rq_ids: [], new_count: 2 },
    { src_step: '제품 스펙', src_count: 2, src_range: 'p.19–20', kind: 'flow', new_label: '제품 스펙 1장', note: 'Spec 시트 작업으로 생성 · QM55C · OM46C', rq_ids: [], new_count: 1 },
    { src_step: '견적 · 일정', src_count: 3, src_range: 'p.21–24', kind: 'drop', new_label: '제외', note: '비복제 · 가격 · 견적 · 일정은 가져오지 않아요', rq_ids: [], new_count: 0 },
    { src_step: 'Why Samsung', src_count: 0, kind: 'new', new_label: 'Why Samsung 2장', note: '경쟁 비교 · R5 POS 연동 신뢰 근거', rq_ids: ['R5'], new_count: 2 },
    { src_step: '단계 도입', src_count: 0, kind: 'new', new_label: '단계 도입 로드맵 1장', note: 'R4 320개 매장 · 권역별 3단계', rq_ids: ['R4'], new_count: 1 },
  ],
  take: [{ label: '단계 순서', sub: '8단계 → 8섹션' }, { label: '시트 역할', sub: '24장 역할 태그' }, { label: '주장 → 근거 구조', sub: '11개 연결' }, { label: '템플릿 유형', sub: '매핑 성공 21장' }, { label: '톤', sub: '운영 효율 중심' }],
  not_take: [{ label: '고객 정보', sub: 'B 베이커리 · 180개 매장' }, { label: '매장 사진 9장', sub: '사용 불가' }, { label: '수치', sub: '시장 · 효과 수치 7건' }, { label: '견적 · 일정', sub: '비복제 3장' }, { label: 'B 베이커리 사례', sub: '도입 사례 3장' }, { label: '출처 미상 이미지 8개', sub: '분류 보류' }],
  sections: 8, sheets: 22, counts: { flow: 19, new: 3, drop: 3 }, footer_label: '시트 구성 초안 · 8섹션 · 22시트 · 원본 내용 0줄 사용 · 1 / 6',
};
export function reuseView(over: Record<string, unknown> = {}) {
  const pages = pagesOf();
  return {
    id: 'pru_mock', proposal_id: 'x', job_id: null, job_status: null, status: 'awaiting_confirm', status_label: '분석 완료',
    sources: [{ kind: 'file', file_id: 'file_mock_src', name: 'B베이커리_매장사이니지_제안_v3.pptx', format: 'pptx', pages: 24, author: '김하늘(동료)', doc_date: '2024.09', customer: 'B 베이커리', meta_label: 'PPTX · 24장 · 2024.09 · 김하늘(동료)', phases: [{ key: 'read', label: '읽기', status: 'done' }, { key: 'split', label: '쪽 나누기', status: 'done' }, { key: 'analyze', label: '기준별 분석', status: 'done' }] }],
    phases: [{ key: 'read', label: '읽기', status: 'done' }, { key: 'split', label: '쪽 나누기', status: 'done' }, { key: 'analyze', label: '기준별 분석', status: 'done' }],
    mode_pref: 'auto', mode: null, recommendation: { mode: 'borrow', reason: '다른 고객 제안서라 흐름 차용을 추천해요', badge: '추천 · 다른 고객' },
    pages, source_sections: SECS.map(([name, count, color]) => ({ name, count, color, excluded: name === '견적 · 일정' })),
    criteria: CRIT.map(([no, key, name, must, summary, confidence, state]) => ({ no, key, name, must, summary, confidence, warn: confidence < 80, state, state_label: ({ ok: '확인됨', need: '확인 필요', edited: '수정함' } as Record<string, string>)[state] })),
    flow: FLOW, context: {}, plan_improve: null, plan_borrow: null, must_done: 1, must_total: 3, confirmed_count: 5, can_confirm: false,
    intro: '**B베이커리_매장사이니지_제안_v3.pptx** 24장을 9가지 기준으로 분석했어요. 기준마다 결과를 확인해 주세요 — 필수 확인 3곳(논리 흐름 · 고객 맥락 · 비복제)을 확인하면 활용 방식을 추천해요.',
    footer_label: '분석 결과 확인 · 9개 기준 중 5개 확인 · 필수 확인 1 / 3 마침 · 2곳 남음', excluded_page_count: 3, band_label: '외부 파일 · 섹션 8개', error: null,
    ...over,
  };
}
export function criterion2() {
  return {
    no: 2, key: 'flow', name: '논리 흐름', must: true, state: 'need', state_label: '확인 필요', confidence: 82, summary: CRIT[1][4],
    header_label: '신뢰도 82% · 다음 단계로 가려면 확인이 필요해요',
    intro: '24장 각각이 설득 흐름에서 맡은 역할을 태그했어요. 역할이 틀리면 바꿔 주세요 — **유저가 고친 태그는 다시 분석해도 바뀌지 않아요.** 이 흐름이 이번 제안서 시트 구성의 뼈대가 돼요.',
    detail: {}, pages: pagesOf(), flow: FLOW, footer_label: '논리 흐름 확인 · 24장 중 태그 확인 21 · 수정 1 · 남음 2',
    chips: CRIT.map(([no, , name, , , , state]) => ({ no, name, state })),
  };
}
export const reuseSectionCompare = {
  view: 'compare', mode: 'improve', header_label: '시트 3장 · 유지 2 · 갱신 1', section_key: 'spaceProducts', sheet_id: null, source_label: '원본 · A 커피 2025 p.9–11',
  source_sheet: {
    page: 10, page_label: 'p.10', title_label: '카운터 메뉴보드 · 2025 v4', title: '카운터 메뉴보드 QM55B 2대 · 바닥형 OM46', kind_label: 'cards3img · 이미지 카드 3',
    lines: [{ id: 's1', text: 'QM55B 55형 메뉴보드 2대 · 카운터 상단 가로 배치', mark: 'update' }, { id: 's2', text: '바닥형 스탠드 1대 · 입구 프로모션 안내', mark: 'keep' }, { id: 's3', text: '2025 가을 프로모션 · 월 1회 본사 교체', mark: 'drop' }],
    images_note: '원본 이미지 3개 · 삼성 공식 2(재사용) · 매장 사진 1(2025 촬영 · 재사용 가능)',
  },
  new_sheet: {
    sheet_id: 'sht_m10', title: '카운터 메뉴보드 QM55C 2대 · 바닥형 OM46C', title_label: '원본 대비 모델명 갱신 · 유저가 고침', rq_label: '요구사항 R3 · R1 반영',
    lines: [
      { id: 'n1', text: 'QM55C 55형 메뉴보드 2대 · 카운터 상단 가로 배치', mark: 'update', badge: '갱신 · 모델', source_line_id: 's1', draft_text: 'QM55C 55형 메뉴보드 2대 · 카운터 상단 가로 배치' },
      { id: 'n2', text: '바닥형 스탠드 1대 · 입구 프로모션 안내', mark: 'keep', badge: '유지', source_line_id: 's2' },
      { id: 'n3', text: '매장별 가격 차등 — 본사 템플릿 + 매장 변수', mark: 'new', badge: '신규 · R3 매장별 가격' },
    ],
    note: '원본 p.10 기반 · 갱신 — 이미지 3개는 원본에서 그대로 가져옴',
  },
  section_sheets: [
    { sheet_id: 'sht_m9', sheet_no: 9, page_label: 'p.9', name: '공간 맵', verdict: 'keep', verdict_label: '유지', template_code: 'SM-A' },
    { sheet_id: 'sht_m10', sheet_no: 10, page_label: 'p.10', name: '카운터 메뉴보드', verdict: 'update', verdict_label: '갱신', template_code: 'P3-A' },
    { sheet_id: 'sht_m11', sheet_no: 11, page_label: 'p.11', name: '대기 공간', verdict: 'keep', verdict_label: '유지', template_code: 'P3-B' },
  ],
  tally: { update: 1, keep: 1, new: 1, drop: 1 }, footer_label: '원본 대조 작성 · 바뀐 줄 3 · 유저가 고친 줄 1 · 4 / 6',
};
export const reuseSectionGuide = {
  view: 'guide', mode: 'borrow', header_label: '가치 제안 · 이해관계자별 가치 · 기대 효과', section_key: 'vp', sheet_id: null, source_label: '원본 · B 베이커리 p.7–8 · 역할만 참고',
  compare_disabled_reason: '흐름 차용 모드에선 원본 내용을 보여주지 않아요',
  source_sheet: null,
  new_sheet: {
    sheet_id: 'sht_g5', title: '가치 제안 — 본사가 하루에 바꾸는 320개 매장 메뉴보드',
    lines: [
      { id: 'g1', text: '매장 320곳 프로모션 교체에 평균 [0]일', mark: 'new' }, { id: 'g2', text: 'MagicINFO 9 본사 일괄 배포', mark: 'new' }, { id: 'g3', text: '교체 주기 [0]일 → 당일', mark: 'new' },
      { id: 'g4', text: '매장별 가격 안내 불일치', mark: 'new' }, { id: 'g5', text: '매장 변수 템플릿', mark: 'new' }, { id: 'g6', text: '가격 오류 [00]% ↓', mark: 'new' },
      { id: 'g7', text: '본사-매장 콘텐츠 승인 지연', mark: 'new' }, { id: 'g8', text: '승인 워크플로', mark: 'new' }, { id: 'g9', text: '운영 인력 [0]명 절감', mark: 'new' },
    ],
  },
  guide: [
    { no: 1, title: '가치 제안', status: 'writing', status_label: '작성 중', role: '과제 → 해법 → 효과 한 장', from_source: "'본사 통제 · 운영 부담 ↓'을 말했음", this_time: 'R1 R2 · 톤 운영 효율 · 업종 레이아웃 추천', chips: ['R1', 'R2', '운영 효율 톤', 'VP-FB-A'] },
    { no: 2, title: '이해관계자별 가치', status: 'waiting', status_label: '대기', role: '본사 · 점주 · 손님 3축', from_source: "'점주 인터뷰'가 근거였음", this_time: '근거는 요구사항 R3 매장별 가격 차등', chips: ['R3', '3축 유지', 'VP-FB-B'] },
    { no: 3, title: '기대 효과', status: 'waiting', status_label: '대기', role: 'Before / After', from_source: '출처 없는 수치였음', this_time: '수치 비워 두고 [00]% 플레이스홀더 · 확정 필요 등록', chips: ['플레이스홀더 3곳', 'VP-FB-C'] },
  ],
  guide_label: '원본 역할 3 / 3 반영',
  placeholders: [{ token: '[0]일', label: '교체 소요 · 현재' }, { token: '[00]%', label: '가격 오류 감소' }, { token: '[0]명', label: '운영 인력 절감' }],
  section_sheets: [
    { sheet_id: 'sht_g5', sheet_no: 5, name: '가치 제안', role: '과제 → 해법 → 효과', status: 'writing', status_label: '작성 중', template_code: 'VP-FB-A' },
    { sheet_id: 'sht_g6', sheet_no: 6, name: '이해관계자별 가치', role: '본사 · 점주 · 손님', status: 'waiting', status_label: '대기', template_code: 'VP-FB-B' },
    { sheet_id: 'sht_g7', sheet_no: 7, name: '기대 효과', role: 'Before / After', status: 'waiting', status_label: '대기', template_code: 'VP-FB-C' },
  ],
  tally: { writing: 1, waiting: 2, confirm: 3 }, footer_label: '흐름 가이드 작성 · 원본 역할 3 / 3 반영 · 수치 플레이스홀더 3곳 확정 필요 등록 · 4 / 6',
};
const CI = (id: string, no: string, pre: string, mark: string, post: string, sub: string, tag: string, extra: Record<string, unknown> = {}) => ({
  id, proposal_id: 'x', category: 'fact', tag, sheet_no_label: no, sheet_no: Number(no), text: { pre, mark, post }, sub, status: 'open', status_label: '확정 필요', origin: 'generate', route: '', created_at: '2026-10-07T00:00:00Z', ...extra,
});
export const summary = {
  intro: 'PPTX **22장**을 만들었어요. 원본(A 커피 2025 · 21장)과 비교해 무엇을 그대로 두고, 무엇을 바꾸고, 무엇을 새로 넣었는지 정리했어요. 갱신한 수치 · 모델은 검토 필요 목록에 모았어요.',
  counts: [
    { verdict: 'keep', label: '유지', n: 5, desc: '원본 그대로 · 공간 맵 · 대기 공간 · Why Samsung' }, { verdict: 'update', label: '갱신', n: 5, desc: '모델 · 수치 현행화 · QM55C · MagicINFO 9 · 320곳' },
    { verdict: 'rewrite', label: '재작성', n: 3, desc: '역할만 두고 다시 씀 · 가치 제안 · 기대 효과 · 구성도' }, { verdict: 'new', label: '신규', n: 2, desc: '요구사항 갭 · R3 가격 차등 · R4 단계 도입 로드맵' },
    { verdict: 'drop', label: '제외', n: 6, desc: '견적 · 일정 · 조감도 · 매장 경험 KM · 지난 사례' },
  ],
  mapping: [
    ['표지 · 목차 · 간지', 1, ['자동 5'], 5], ['Market Intelligence', 3, ['갱신 2', '유지 1'], 3], ['Value Props', 3, ['재작성 2', '제외 1'], 2], ['조감도', 1, ['제외 1', '자동 1'], 1],
    ['공간별 제품', 3, ['갱신 2', '유지 1'], 3], ['솔루션 제안', 2, ['갱신 1', '재작성 1'], 2], ['유관 사례', 2, ['유지 1', '제외 1'], 1], ['Why Samsung', 2, ['유지 2'], 2],
    ['제품 스펙', 1, ['자동 1'], 1], ['요구사항 갭 · R3 · R4', 0, ['신규 2'], 2], ['견적 · 일정', 3, ['제외 3'], 0],
  ].map(([section, src_count, chips, new_count]) => ({ section, src_count, chips, new_count })),
  mapping_label: '원본 21장 · A 커피 2025 v4',
  review_items: [
    CI('c10', '10', '카운터 메뉴보드 ', 'QM55B → QM55C', ' 치환 확인', '', '단종 치환'), CI('c12', '12', 'MagicINFO 9 ', '가격 정책', ' · 라이선스 단위가 8과 달라요', '', '정책'),
    CI('c02', '02', '시장 규모 · 성장 ', '2026 조사 반영', ' · 2025.11 수치 교체', '', '수치'), CI('c03', '03', '매장 수 ', '320', ' 전 시트 반영 · 원본 280', '', '값 전파'),
  ],
  review_total: 6, review_more_label: '2곳 더 · 기대 효과 수치 출처 · 유관 사례 공개 범위',
  traces: [
    { title: "새 제안서 각 시트 노트에 '원본 p.N 기반 · 갱신' 기록", sub: '시트 17장 · 되돌리기 가능' },
    { title: "버전 이력에 '2025 제안서 v4에서 파생' 표시", sub: '새 제안서 v1 · 파생 관계가 목록에도 보여요' },
    { title: '원본 제안서는 바뀌지 않음', sub: 'A 커피 2025 v4 · 2025.11.20 제출본 그대로' },
  ],
  changed_count: 11, footer_label: '완료 · 22장 · 원본 대비 변경 11장 · 6 / 6', file_label: 'A커피_디지털메뉴보드_제안_v1.pptx · 22장 · 16:9 · 삼성 B2B 표준 템플릿',
};

// ── PR7Q 확정 필요 ─────────────────────────────────────────
export function confirmList() {
  const items = [
    CI('q01', '01', '2028년 국내 디지털 메뉴보드 시장 ', '[00]억 원', '', '시장 규모 · 성장 · MI 작업의 추정치 — 출처 확인 필요', '수치', { action: { kind: 'link', label: 'MI에서 확인', target: { route: '/mi' } } }),
    CI('q09', '09', '전국 ', '[00]개', ' 매장 × 카운터 3대', '카운터 · 메뉴보드 · 매장 수를 아직 받지 못했어요', '고객 확인', {
      action: { kind: 'link', label: '시트에서 보기', target: { route: null } },
      fix: { sentence: [{ text: '카운터마다 메뉴보드 3대씩, 전국' }, { input: 'stores', label: '매장 수' }, { text: '개 매장에 설치합니다.' }], formula: '합계 = 매장 수 × 3대', linked_sheets: [{ sheet_id: 's08', sheet_no: 8, name: '공간 맵' }, { sheet_id: 's09', sheet_no: 9, name: '카운터 · 메뉴보드' }, { sheet_id: 's11', sheet_no: 11, name: '주문 · 대기 공간' }] },
    }),
    CI('q19', '19', '고객사명 · 성과 수치 ', '공개 가능 여부', '', '사례 · 커피 프랜차이즈 · 사례 자료가 내부용으로 표시돼 있어요', '공개 여부', { action: { kind: 'button', label: '익명으로 바꾸기', target: { op: 'anonymize' } } }),
    CI('q21', '21', '유지보수 응답 시간 ', '[00]시간', ' · 삼성 · 경쟁사 A · B', '경쟁 비교 · 방금 추가한 행 — 공개 자료를 찾지 못했어요', '수치', { action: { kind: 'link', label: '시트에서 보기', target: { route: null } } }),
    CI('q23', '23', 'OH55C 밝기 ', '[00] nit', ' — Spec 시트와 다름', '스펙 비교 · 제안서 값과 Spec 시트 작업의 값이 달라요', '값 불일치', { action: { kind: 'link', label: 'Spec 시트에서 보기', target: { route: '/spec' } } }),
    CI('q03', '03', '경쟁 환경 ', '공개 자료 링크 첨부', '', '경쟁 환경', '수치', { status: 'confirmed', status_label: '확정' }),
    CI('q22', '22', '삼성 강점 ', '사내 자료로 확정', '', '삼성 강점', '수치', { status: 'confirmed', status_label: '확정' }),
  ];
  return {
    items, counts: { open: 5, confirmed: 2, total: 7 }, header_label: '확정 필요 7곳', progress_label: '2곳 확정 · 5곳 남음',
    intro: '제안서 24시트에서 사실 확인이 필요한 곳 7곳을 모았어요. 값을 넣거나 근거를 붙이면 그 값이 쓰인 시트에 모두 반영되고, 확정하지 않은 곳은 내보낼 때 표시를 남길 수 있어요.',
    confirmed_summary: '03 경쟁 환경 · 공개 자료 링크 첨부 · 22 삼성 강점 · 사내 자료로 확정', footer_label: '확정 필요 · 5곳 남음 · 확정한 값은 버전 기록에 남아요', sheets_total: 24,
  };
}

// ── 딸깍 ─────────────────────────────────────────────────
const OC_STEPS = [
  ['mi', 'Market Intelligence', '직접 작성 · 3시트', 'confirmed'], ['vp', 'Value Props', '직접 작성 · 2시트', 'confirmed'], ['birdseye', '조감도', '작성 중이던 내용 + 조감도 작업으로 완성', 'inferred_done'],
  ['spaceProducts', '공간별 제품', '조감도 배치안 · 요구사항에서 제품 추론', 'running'], ['solution', '솔루션 제안', '연결된 솔루션 2개 · 시나리오로 작성', 'waiting'], ['cases', '유관 사례', '유사도 상위 사례 자동 선택', 'waiting'],
  ['why', 'Why Samsung', 'MI 경쟁사 분석으로 비교표 작성', 'waiting'], ['spec', '제품 스펙', '공간별 제품 모델로 비교표 생성', 'waiting'], ['design', '디자인 템플릿', '삼성 B2B 표준 (기본값)', 'waiting'], ['assemble', 'PPTX 조립', '표지 · 목차 · 섹션 구분 포함', 'waiting'],
] as const;
const ST_L: Record<string, string> = { confirmed: '확정', inferred_done: '추론 완료', running: '생성 중', waiting: '대기' };
export function oneClickRunning(jobId: string) {
  return {
    job_id: jobId, status: 'running', from_stage: 'sections', from_section_key: 'birdseye', options: { mark_inferred: true, collect_reviews: true },
    steps: OC_STEPS.map(([key, label, note, status]) => ({ key, label, note, status, status_label: ST_L[status] })), memos: [],
    auto_from_step: 4, header: '딸깍 · 조감도부터 나머지 자동 완성', intro: '남은 6개 섹션과 템플릿을 추론해 제안서를 만들고 있어요. 확정해 두신 MI · Value Props는 그대로 쓰고, 추론으로 채운 시트에는 표시와 근거 노트를 남깁니다.',
    pct: 45, eta_label: '약 1분 남음', type_label: '표준 제안서', slides_label: '21장',
  };
}
export function oneClickDone(jobId: string, sheetId?: string) {
  const T = ['01 표지', '02 목차', '03 MI · 시장', '04 MI · 고객사', '05 MI · 경쟁', '06 VP · 과제', '07 VP · 가치', '08 조감도'];
  return {
    ...oneClickRunning(jobId), status: 'succeeded', pct: 100, eta_label: '',
    steps: OC_STEPS.map(([key, label, note, status]) => ({ key, label, note, status: status === 'confirmed' ? status : 'inferred_done', status_label: status === 'confirmed' ? '확정' : '추론 완료' })),
    done_intro: '딸깍으로 제안서를 완성했습니다. 21장 중 16장을 추론으로 채웠고, 그 시트에는 **추론** 표시와 근거 노트를 남겼어요. 먼저 확인이 필요한 3곳을 모았습니다.',
    file: { name: 'A커피_디지털메뉴보드_제안서_v1.pptx', meta: '표준 제안서 · 21장', pptx_file_id: null, pdf_file_id: null, pptx_url: null },
    counts: { confirmed: 5, inferred: 16, review: 3 },
    thumbs: T.map((label, i) => ({ slide_no: i + 1, label: label.slice(3), thumb_url: null, inferred: [0, 1, 7].includes(i), sheet_id: i >= 2 ? sheetId ?? null : null, kind: i === 0 ? 'cover' : i === 1 ? 'toc' : 'table' })),
    rest_label: '09–21 조감도 포인트 · 공간별 제품 4 · 솔루션 제안 2 · 유관 사례 2 · Why Samsung 2 · 제품 스펙 2 — 모두 추론',
    review_header: '검토가 필요한 곳 3',
    review_items: [
      { ...CI('r1', '13', '', '', '', '', '검토 필요'), category: 'review', where: '공간별 제품 · 주문 · 대기 공간', why: '매장당 1대로 수량을 가정했어요 — 실제 매장 도면과 맞는지 확인', section_key: 'spaceProducts', text: { mark: '공간별 제품 · 주문 · 대기 공간' } },
      { ...CI('r2', '21', '', '', '', '', '검토 필요'), category: 'review', where: 'Why Samsung · 경쟁사 비교', why: '경쟁사 수치를 찾지 못해 [확정 필요]로 두었어요', section_key: 'why', text: { mark: 'Why Samsung · 경쟁사 비교' } },
      { ...CI('r3', '18', '', '', '', '', '검토 필요'), category: 'review', where: '유관 사례 · 사례 2건', why: '유사도 순으로 자동 선택 — 고객사에 공개 가능한 사례인지 확인', section_key: 'cases', text: { mark: '유관 사례 · 사례 2건' } },
    ],
  };
}

// ── PR7C 검토 ─────────────────────────────────────────────
export function reviewView(sheets: Array<{ id: string; sheet_no: number; title: string }>, cur: { id: string; sheet_no: number; title: string }) {
  const grid = sheets.map((s, i) => ({ sheet_no: s.sheet_no, sheet_id: s.id, title: s.title, state: s.id === cur.id ? 'open' : i % 7 === 3 ? 'todo' : 'ok' }));
  return {
    review: { id: 'rvw_mock', version: 2, status: 'in_review', status_label: '진행 중', message: '1차 제출본입니다. Why Samsung 수치 위주로 봐주세요.', due_date: '2026-10-08', requested_at: new Date().toISOString(), sent_label: '오늘 11:00 보냄 · 마감 10월 8일 (수)', requester_name: '최민섭' },
    reviewers: [
      { user_id: 'u_park', name: '박준호', initial: '박', role: '솔루션 컨설턴트', status: 'approved', status_label: '승인' },
      { user_id: 'u_lee', name: '이서연', initial: '이', role: '디자인', status: 'changes_requested', status_label: '수정 요청' },
      { user_id: 'u_kim', name: '김지훈', initial: '김', role: '영업팀장', status: 'pending', status_label: '대기 중' },
    ],
    approvals: { done: 1, total: 3, label: '승인 1 / 3' },
    comment_sheets: [{ sheet_no: cur.sheet_no, sheet_id: cur.id, name: cur.title, open: 2, resolved: 1 }],
    comments_open: 4, comments_resolved: 2, check_grid: grid, check_label: `시트 확인 ${grid.filter((g) => g.state === 'ok').length} / ${grid.length}`,
    my_turn: false, can_decide: false, suggest_text: '열린 코멘트 4건을 반영한 수정안을 만들 수 있어요. 새 버전으로 저장하고 바뀐 곳을 비교해 드릴게요.',
    version_label: 'v2 · 검토 중', comment_target: 'proposal:mock-review', share_permission_label: '팀 내부 · 코멘트 가능',
  };
}
export function comments(proposalId: string, sheetId: string) {
  const now = new Date();
  const at = (h: number, m: number) => new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate(), h - 9, m)).toISOString();
  const base = { target: 'proposal:mock-review', updated_at: at(13, 10) };
  return [
    { ...base, id: 'cmt1', body: '경쟁사 B 유지보수 응답 값은 출처가 있나요? 없으면 노트로 옮겨 주세요.', anchor: { proposal_id: proposalId, version: 2, sheet_id: sheetId, x: 0.85, y: 0.74 }, parent_id: null, author: 'u_kim', author_name: '김지훈', resolved: false, created_at: at(11, 40) },
    { ...base, id: 'cmt1r', body: 'MI에서 다시 찾아볼게요. 못 찾으면 노트로 옮길게요.', anchor: null, parent_id: 'cmt1', author: 'u_dev', author_name: '최민섭', resolved: false, created_at: at(11, 52) },
    { ...base, id: 'cmt2', body: '삼성 열 머리글이 검정이에요. 표준 마스터의 블루로 맞춰 주세요.', anchor: { proposal_id: proposalId, version: 2, sheet_id: sheetId, x: 0.42, y: 0.28 }, parent_id: null, author: 'u_lee', author_name: '이서연', resolved: false, created_at: at(13, 5) },
    { ...base, id: 'cmt3', body: '유지보수 항목 추가 요청 — v2에 반영', anchor: { proposal_id: proposalId, version: 1, sheet_id: sheetId, x: 0.12, y: 0.62 }, parent_id: null, author: 'u_park', author_name: '박준호', resolved: true, created_at: at(9, 0) },
  ];
}

// ── PR7V 버전 ─────────────────────────────────────────────
export function versionsView() {
  const today = new Date();
  const iso = (dDay: number, h: number, m: number) => new Date(Date.UTC(today.getUTCFullYear(), today.getUTCMonth(), today.getUTCDate() + dDay, h - 9, m)).toISOString();
  return {
    current: 3, current_label: 'v3 · 현재', header_label: '버전 3 · 변경 기록 9', change_count: 9, next_save_label: '지금 상태를 v4로 저장', retention_note: '자동 저장 기록은 30일 동안 남아요',
    versions: [
      { n: 3, label: 'v3', kind: 'manual', desc: '검토 코멘트 반영', author_label: '최민섭', created_at: iso(0, 14, 20), time_label: '오늘 14:20', current: true,
        changes: [{ change_id: 'chg_a', t: '14:18', text: '21 머리글 색 → 표준 블루' }, { change_id: 'chg_b', t: '14:12', text: '21 경쟁사 B 값 → 노트로' }, { change_id: 'chg_c', t: '14:06', text: '21 제목 다듬기 · W' }, { change_id: 'chg_d', t: '13:30', text: '09 매장 수 확정 · 08 · 11 반영' }] },
      { n: 2, label: 'v2', kind: 'review', desc: '유지보수 행 추가 · 수치 2곳 확정', author_label: '최민섭', created_at: iso(0, 10, 55), time_label: '오늘 10:55',
        changes: [{ change_id: 'chg_e', t: '10:52', text: '21 유지보수 응답 시간 행 추가' }, { change_id: 'chg_f', t: '10:40', text: '03 · 22 수치 확정 · 사내 자료' }] },
      { n: 1, label: 'v1', kind: 'generate', desc: '표준 제안서 24시트 처음 생성', author_label: 'W', created_at: iso(-1, 18, 30), time_label: '어제 18:30', changes: [] },
    ],
    events: [{ at: iso(0, 11, 0), text: '검토 요청 · 오늘 11:00 · 3명에게', kind: 'review' }],
  };
}
/** PR7V 보드의 21 경쟁 비교 — v2(A) · v3(B) 시트 display(CompareSide.display) */
function cmDisplay(v: 2 | 3) {
  const C = (text: string, mark: 'full' | 'half' | 'none' | null = null) => ({ text, mark });
  const rows: Array<[string, ReturnType<typeof C>[]]> = [
    ['원격 콘텐츠 배포', [C('본사 일괄 배포', 'full'), C('일괄 배포', 'full'), C('매장별 등록', 'half')]],
    ['POS 가격 연동', [C('자동 반영', 'full'), C('수동 업로드', 'half'), C('미지원', 'none')]],
    ['사내 서버 · 보안', [C('설치형 · 사내망', 'full'), C('클라우드 전용', 'none'), C('별도 구축', 'half')]],
    ['매장 에너지 관리', [C('SmartThings Pro', 'full'), C('미지원', 'none'), C('미지원', 'none')]],
    ['전국 설치 · A/S', [C('직영 서비스망', 'full'), C('협력사 위탁', 'half'), C('협력사 위탁', 'half')]],
    ['유지보수 응답 시간', [C('[00]시간 이내'), C('[00]시간'), C(v === 2 ? '[00]시간' : '공개 자료 없음')]],
  ];
  return {
    eyebrow: 'WHY SAMSUNG', title: v === 2 ? '운영 · 지원에서 앞서는 삼성' : '매장 운영 · 지원, 경쟁사보다 앞섭니다', subtitle: 'A 커피 요구사항 6개 기준 · 출처 MI 경쟁사 분석',
    slots: { table: { columns: ['비교 항목', '삼성 제안', '경쟁사 A', '경쟁사 B'], rows: rows.map(([label, cells], i) => ({ id: `r${i + 1}`, label, cells })) } },
  };
}

export function compareView(sheetId: string) {
  return {
    a: { n: 2, label: 'A v2', meta: '오늘 10:55 · 검토 요청한 버전', png_url: null, sheet_id: sheetId, display: cmDisplay(2) },
    b: { n: 3, label: 'B v3', meta: '오늘 14:20 · 현재', png_url: null, sheet_id: sheetId, display: cmDisplay(3) },
    changed_sheets: [{ sheet_no: 21, sheet_id: sheetId, name: '경쟁 비교', count: 3 }, { sheet_no: 9, sheet_id: 'sht_x9', name: '카운터 · 메뉴보드', count: 1 }, { sheet_no: 8, sheet_id: 'sht_x8', name: '공간 맵', count: 1 }, { sheet_no: 11, sheet_id: 'sht_x11', name: '주문 · 대기 공간', count: 1 }],
    diffs: [
      { n: 1, change_id: 'chg_c', sheet_id: sheetId, sheet_no: 21, where: '제목', kind: '텍스트', from: '운영 · 지원에서 앞서는 삼성', to: '매장 운영 · 지원, 경쟁사보다 앞섭니다', why: 'W 다듬기 · 최민섭 요청', bbox: { x: 0.04, y: 0.1, w: 0.4, h: 0.08 }, revertable: true },
      { n: 2, change_id: 'chg_a', sheet_id: sheetId, sheet_no: 21, where: '머리글 · 삼성 열', kind: '서식', from: '검정 배경', to: '표준 블루', from_swatch: '#121417', to_swatch: '#1428A0', why: '이서연 코멘트 반영', bbox: { x: 0.31, y: 0.27, w: 0.25, h: 0.08 }, revertable: true },
      { n: 3, change_id: 'chg_b', sheet_id: sheetId, sheet_no: 21, where: '6행 · 경쟁사 B', kind: '텍스트 · 노트', from: '[00]시간', to: '공개 자료 없음', why: '김지훈 코멘트 반영', bbox: { x: 0.74, y: 0.78, w: 0.2, h: 0.08 }, revertable: true },
    ],
    header_label: '바뀐 시트 4 · 바뀐 곳 6', sheet_id: sheetId, footer_note: '되돌려도 v3는 이력에 남아요. 언제든 다시 돌아올 수 있어요.',
  };
}
