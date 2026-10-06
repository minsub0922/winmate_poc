/**
 * MI 화면 테스트용 API 흉내(page.route) — §9.1 `웹 화면 테스트는 API 목 위에서 문구 · 이동 · 상태를 확인한다`.
 * 실제 mi 서비스로 만들기 어려운 상태(업종 두 갈래 · 분석 중 미리 보기 · 배지 수 · 넘김)를 고정값으로 그린다.
 * 흉내 안 한 mi 경로 중 정적인 것(segments · routing-rules · capabilities)은 실제 서비스로 보낸다.
 */
import type { Page, Route } from '@playwright/test';

export type Handler = (route: Route, url: URL, method: string, body: any) => unknown | Promise<unknown>;

const json = (route: Route, data: unknown, status = 200) => route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(data) });

/** SSE 본문(한 번에 보내고 닫힘). retry 가 길면 다시 연결하지 않는다 */
export function sse(events: Array<{ type: string; data: unknown }>, retryMs = 600_000): string {
  return `retry: ${retryMs}\n\n${events.map((e) => `event: ${e.type}\ndata: ${JSON.stringify(e.data)}\n\n`).join('')}`;
}

/**
 * `routes` 의 키 = `METHOD /v1/...` (경로 조각 `:x` 는 아무 값). 값 = 응답(JSON) 또는 처리 함수.
 * 처리 함수가 undefined 를 돌려주면 그 함수가 직접 fulfill 한 것으로 본다.
 */
export async function mockMi(page: Page, routes: Record<string, unknown | Handler>) {
  const entries = Object.entries(routes).map(([k, v]) => {
    const [method, pat] = k.split(' ');
    const re = new RegExp(`^/api/mi${pat.replace(/:[a-z_]+/g, '[^/]+')}$`);
    return { method, re, v };
  });
  await page.route('**/api/mi/v1/**', async (route) => {
    const req = route.request();
    const url = new URL(req.url());
    const method = req.method();
    const hit = entries.find((e) => e.method === method && e.re.test(url.pathname));
    if (!hit) {
      if (method === 'GET' && /\/v1\/(segments|routing-rules|capabilities)/.test(url.pathname)) return route.fallback();
      return json(route, { error: { code: 'NOT_FOUND', message: `흉내 없음: ${method} ${url.pathname}` } }, 404);
    }
    if (typeof hit.v === 'function') {
      let body: unknown = null;
      try { body = req.postDataJSON(); } catch { body = null; }
      const out = await (hit.v as Handler)(route, url, method, body);
      if (out !== undefined) return json(route, out);
      return undefined;
    }
    return json(route, hit.v);
  });
}

/** jobs 서비스 흉내 — 잡 스냅숏 · SSE · 입력 · 메모 · 취소 */
export async function mockJobs(page: Page, jobs: Record<string, { snapshot: () => unknown; events: () => string; onInput?: (body: any) => void; onCancel?: () => void }>) {
  await page.route('**/api/jobs/v1/jobs/**', async (route) => {
    const url = new URL(route.request().url());
    const m = url.pathname.match(/\/api\/jobs\/v1\/jobs\/([^/]+)(?:\/(events|input|memos|cancel))?$/);
    if (!m || !jobs[m[1]]) return route.fulfill({ status: 404, contentType: 'application/json', body: '{"error":{"code":"NOT_FOUND","message":"없음"}}' });
    const j = jobs[m[1]];
    const tail = m[2];
    if (!tail) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(j.snapshot()) });
    if (tail === 'events') return route.fulfill({ status: 200, contentType: 'text/event-stream', headers: { 'Cache-Control': 'no-cache' }, body: j.events() });
    if (tail === 'input') { j.onInput?.(route.request().postDataJSON()); return route.fulfill({ status: 200, contentType: 'application/json', body: '{"ok":true}' }); }
    if (tail === 'cancel') { j.onCancel?.(); return route.fulfill({ status: 200, contentType: 'application/json', body: '{"ok":true}' }); }
    return route.fulfill({ status: 200, contentType: 'application/json', body: '{"ok":true}' });
  });
}

export const AID = 'mi_01M4E2EMOCK0000000000000AA';

export function analysis(over: Record<string, unknown> = {}) {
  return {
    id: AID, owner_id: 'u', owner_name: '최민섭', project_id: null, title: 'H 호텔 로비 라운지 카페 분석', topic: '시장 · 경쟁사', customer_name: 'H 호텔',
    requirements_text: '로비 라운지 카페 메뉴보드', requirements: [], files: [], links: {}, segment: { code: 'HT', mode: 'ask', confidence: 0.58,
      candidates: [{ code: 'HT', confidence: 0.58 }, { code: 'FB', confidence: 0.55 }], clues: [], mix: null, inherited_from: null, llm_failed: false },
    usage: { value: 'standard', mode: 'auto', reason: '' }, scope: { areas: ['market', 'customer', 'user', 'competitor'], mode: 'auto', reasons: {}, reduced: [] },
    anonymize: true, naming_mode: 'letter', internal: { kb_case_count: 40, included_file_ids: [], excluded_file_ids: [], mode: null, summary: '호텔 17 + 외식 23건' },
    depth: { target_sources: 30, eta_s: 180 }, status: 'ask', status_label: '작성 중', version: 0, current_job_id: null, design_job_id: 'job_ask', design_status: 'ask',
    last_screen: 'design/industry', memos: [], competitors: [], criteria: [], samsung_products: [], preset: null, req_summary: '', scope_desc: {}, input_kind: '회의록',
    one_line_memo: false, route: `/mi/${AID}/design/industry`, eta_s: 180, run_label: '분석 시작 (약 3분)', created_at: '2026-10-06T00:00:00Z',
    updated_at: '2026-10-06T00:00:00Z', analyzed_at: null, next_recheck_at: null, edited_after_analysis: false, result: null, ...over,
  };
}

/** MI1Q 보드 그대로의 묻기 데이터(AC-MI-04: HT 0.58 · FB 0.55 · 차이 0.03 · MIX 0.57) */
export const ASK = {
  kind: 'segment_choice', question: '어느 업종 관점으로 분석할까요?',
  agent_text: '회의록을 읽어 보니 업종이 두 갈래로 읽혀요. 업종에 따라 시장 · 비즈니스 · 사용자 레이아웃이 통째로 달라져서, 이것 하나만 여쭤볼게요.',
  diff: 0.03, gap_rule: '기준 0.10 미만',
  clues: [{ t: '로비', code: 'HT' }, { t: '투숙객', code: 'HT' }, { t: '객실 320실', code: 'HT' }, { t: '라운지 카페', code: 'FB' }, { t: '메뉴보드', code: 'FB' }, { t: '음료 피크타임', code: 'FB' }],
  options: [
    { key: 'HT', segment: 'HT', name: '호텔 · 리조트', desc: '호텔 운영 관점 — 로비 · 객실 경험, 투숙객 여정, 호텔 매출 구조. 사례 17건', score: 0.58, codes: 'MI-HT-A · B · C', recommended: true, thumbs: ['barline', 'process', 'journey'] },
    { key: 'FB', segment: 'FB', name: '외식 · 카페', desc: '매장 운영 관점 — 메뉴 · 피크 주문, 손님 체류, 가맹 구조. 사례 23건', score: 0.55, codes: 'MI-FB-A · B · C', recommended: false, thumbs: ['barline', 'process', 'journey'] },
    { key: 'MIX', segment: 'MIX', name: '섞어서 보기', desc: '시장 · 비즈니스는 호텔로, 사용자 여정은 라운지 카페 손님으로', score: 0.57, codes: 'MI-HT-A · B + MI-FB-C', recommended: false, mix: { a: 'HT', b: 'HT', c: 'FB' }, thumbs: ['barline', 'process', 'journey'] },
  ],
  default: 'HT', default_text: '답이 없으면 추천(호텔 · 리조트)으로 진행하고, 결과 화면의 업종 칩에서 언제든 바꿀 수 있어요.',
  done: ['쓰임 · 표준 MI 3시트', '범위 · 4개 영역', '경쟁사 · 익명 A · B · C', '사내 자료 · 호텔 17 + 외식 23건'],
  footer: '업종 확인 · 선택 필요 1 · 나머지 6개는 자동으로 정했어요', hint: null,
};

export function designView(over: Record<string, unknown> = {}) {
  return { status: 'ask', job_id: 'job_ask', decisions: [], tally: { auto: 5, check: 1, ask: 1 }, sheets_preview: [], sheets_head: '', usage_label: '', ask: ASK,
    run_label: '분석 시작 (약 3분)', error: null, ...over };
}

const AREAS = [['market', '시장조사'], ['customer', '고객사 · 비즈니스'], ['user', '사용자'], ['competitor', '경쟁사 → 삼성 강점']] as const;

/** MI3G 스냅숏(AC-MI-20 · 22: 검색 완료 · 영역 2/4 정리 · 작성 0 → 58%) */
export function runSnapshot() {
  return {
    stage: 'organize', stage_status: 'run', stage_note: '영역 2 / 4 정리됨',
    stages: [{ stage: 'search', name: '검색', status: 'done', note: '출처 31곳 확인 · 완료' }, { stage: 'organize', name: '정리', status: 'run', note: '영역 2 / 4 정리됨' },
      { stage: 'write', name: '작성', status: 'wait', note: '결과 · 비교표 · 삼성 강점' }],
    areas: [
      { area: 'market', name: '시장조사', status: 'done', note: '출처 9 · F&B 사이니지 도입 트렌드 · 규제' },
      { area: 'customer', name: '고객사 · 비즈니스', status: 'done', note: '출처 7 · 매장 전략 · 확장 계획 · 운영 구조' },
      { area: 'user', name: '사용자', status: 'run', note: '점장 · 본사 운영자 · 손님 페르소나 정리 중' },
      { area: 'competitor', name: '경쟁사 → 삼성 강점', status: 'wait', note: '경쟁사 3 × 기준 5 · 출처 9곳 확인됨' }],
    sources: { total: 31, used: 18, checking: 9, excluded: 4 },
    recent_sources: [{ kind: '사내', name: '외식 · 카페 도입사례 23건 (사례 DB)', state: '사용' }, { kind: '공개', name: 'A 커피 사업보고서 [연도]', state: '사용' },
      { kind: '공개', name: '경쟁사 A 제품 페이지 · CMS 사양', state: '확인 중' }, { kind: '공개', name: '업계 기사 (2019)', state: '제외 · 오래됨' }],
    previewable: ['market', 'customer'],
  };
}

export function claimRef(id: string, text: string, status = 'matched', ns = [1]) {
  return { id, text, status, label: status === 'matched' ? '원문 일치' : '확인 필요 1', ns, inferred: false, unverified_numbers: status !== 'matched' };
}

/** MI3 결과(미리 보기면 시장 · 고객만 done) */
export function result(preview = false) {
  const tabs = AREAS.map(([area, label], i) => ({ area, label, status: preview && i >= 2 ? 'running' : 'done', needs_check: [3, 1, 0, 2][i] }));
  const foot = (t: string) => ({ sources: 3, by_kind: { public: 2, kb_case: 1 }, unverified: true, text: t });
  return {
    analysis_id: AID, version: preview ? 0 : 1, kind: 'full', created_at: '2026-10-06T00:00:00Z', stopped: false, preview, is_latest: true,
    analysis_status: preview ? 'running' : 'done', tabs,
    market: { size_series: [{ year: 2024, value: 5800, unit: '억 원', claim: claimRef('clm_m1', '2024년 시장 규모는 5,800억 원이에요.', 'needs_check') }],
      size_unit: '억 원', size_label: '국내 F&B 디지털 사이니지 시장', cagr: null,
      trends: [{ title: '디지털 메뉴보드 확산', when: '2023~2025', claim: claimRef('clm_m2', '디지털 메뉴보드를 쓰는 매장이 최근 3년간 42% 늘었습니다.'), implication: '그래서 전 매장 동시 전환이 유리해요' }],
      regulations: [], kb_trend: null },
    customer: { summary: claimRef('clm_c1', 'H 호텔은 로비 라운지 카페 메뉴를 본사에서 관리해요.', 'needs_check', [1]), strategy: [], expansion: [], structure: [], ops_challenges: [], reduced: false },
    user: preview ? null : { personas: [{ role: '투숙객', goal: '빨리 주문', pain: '메뉴 찾기', context: '체크인 직후', claims: [] }], journey: [], composition: [] },
    competitor: preview ? null : {
      table: { columns: [{ key: 'cmp_a', label: '경쟁사 A', sub: '가나 디스플레이', samsung: false }, { key: 'samsung', label: '삼성', sub: '', samsung: true }],
        rows: [{ criterion_id: 'crt_1', name: '본사 원격 통합 관리', weight: 5, cells: {
          cmp_a: { text: '자체 CMS', claim_ids: ['clm_k1'], ns: [1], placeholder: false, status: 'needs_check', verdict: 'samsung_better' },
          samsung: { text: 'MagicINFO 클라우드', claim_ids: ['clm_k2'], ns: [2], placeholder: false, status: 'matched', verdict: null } } }] },
      strengths: [{ id: 'str_1', title: '서버 없는 통합 관리', note: '320개 매장 규모에서 인프라 비용 우위', criterion_ids: ['crt_1'], claims: [] }], samsung_products: [] },
    footers: { market: foot('출처 3건 · 사내 사례 DB 1 · 공개 자료 2 · [수치는 검증 후 확정]'), customer: foot('출처 1건 · 공개 자료 1'),
      ...(preview ? {} : { user: foot('출처 1건 · 공개 자료 1'), competitor: foot('출처 2건 · 공개 자료 1 · 사내 스펙 1') }) },
    check_chips: [], web_unavailable: false, upd: null,
    agent_text: preview ? '먼저 정리된 영역부터 보여 드려요. 나머지 탭은 정리 중이에요.' : '분석이 끝났습니다. 4개 영역의 결과를 탭으로 정리했고, 각 항목은 출처와 함께 제안서에 인용할 수 있습니다.',
    needs_check_total: 6, failed_areas: [], implications: null,
  };
}
