/**
 * MOCK — 제안서 화면 테스트용 API 흉내(page.route). 백엔드가 아직 501 이거나 실제로 만들기 어려운 상태
 * (RFP 추출 · 기존 작업 · 기존 제안서 분석 · 딸깍 · 확정 필요 · 검토 · 버전 · 내보내기)를 보드 값으로 고정해 그린다.
 * 흉내 안 한 경로는 실제 서비스로 보낸다(route.fallback) — 제안서 자체(GET /proposals/{id})는 실제 데이터.
 */
import type { Page, Route } from '@playwright/test';

export type Handler = (route: Route, url: URL, method: string, body: any) => unknown | Promise<unknown>;
const json = (route: Route, data: unknown, status = 200) => route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(data) });

/** SSE 본문(한 번에 보내고 닫힘). retry 가 길면 다시 연결하지 않는다 */
export function sse(events: Array<{ type: string; data: unknown }>, retryMs = 600_000): string {
  return `retry: ${retryMs}\n\n${events.map((e) => `event: ${e.type}\ndata: ${JSON.stringify(e.data)}\n\n`).join('')}`;
}

/** `METHOD /v1/...`(`:x` = 아무 조각) → 응답(JSON) 또는 처리 함수. 처리 함수가 undefined 면 직접 fulfill 한 것 */
export async function mockApi(page: Page, svc: string, routes: Record<string, unknown | Handler>) {
  const entries = Object.entries(routes).map(([k, v]) => {
    const [method, pat] = k.split(' ');
    const re = new RegExp(`^/api/${svc}${pat.replace(/[.*+?^${}()|[\]\\]/g, (c) => (c === ':' ? c : `\\${c}`)).replace(/:[a-z_]+/g, '[^/]+')}$`);
    return { method, re, v };
  });
  await page.route(`**/api/${svc}/v1/**`, async (route) => {
    const req = route.request();
    const url = new URL(req.url());
    const method = req.method();
    const hit = entries.find((e) => e.method === method && e.re.test(url.pathname));
    if (!hit) return route.fallback();
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
export const mockProposal = (page: Page, routes: Record<string, unknown | Handler>) => mockApi(page, 'proposal', routes);
export const fail = (status: number, code: string, message: string, details: Record<string, unknown> = {}): Handler =>
  (route) => { void route.fulfill({ status, contentType: 'application/json', body: JSON.stringify({ error: { code, message, details } }) }); return undefined; };

/** jobs 서비스 흉내 — 잡 스냅숏 · SSE · 메모 · 취소 */
export async function mockJobs(page: Page, jobs: Record<string, { snapshot: () => unknown; events: () => string; onMemo?: (body: any) => void; onCancel?: () => void }>) {
  await page.route('**/api/jobs/v1/jobs/**', async (route) => {
    const url = new URL(route.request().url());
    const m = url.pathname.match(/\/api\/jobs\/v1\/jobs\/([^/]+)(?:\/(events|input|memos|cancel))?$/);
    if (!m || !jobs[m[1]]) return route.fallback();
    const j = jobs[m[1]];
    const tail = m[2];
    if (!tail) return json(route, j.snapshot());
    if (tail === 'events') return route.fulfill({ status: 200, contentType: 'text/event-stream', headers: { 'Cache-Control': 'no-cache' }, body: j.events() });
    if (tail === 'memos') { j.onMemo?.(route.request().postDataJSON()); return json(route, { ok: true }); }
    if (tail === 'cancel') { j.onCancel?.(); return json(route, { ok: true }); }
    return json(route, { ok: true });
  });
}
/** 진행 중인 채로 멈춰 있는 잡(이벤트 한 번) */
export const runningJob = (id: string, progress = 45, steps: Array<{ step: string; status: string }> = []) => ({
  snapshot: () => ({ id, status: 'running', progress, kind: 'x', created_at: new Date().toISOString() }),
  events: () => sse([{ type: 'progress', data: { progress, message: '진행 중' } }, ...steps.map((s) => ({ type: 'step', data: s }))]),
});
/** 바로 끝나는 잡 */
export const doneJob = (id: string, result: Record<string, unknown> = {}) => ({
  snapshot: () => ({ id, status: 'succeeded', progress: 100, result }),
  events: () => sse([{ type: 'progress', data: { progress: 100 } }, { type: 'done', data: { status: 'succeeded', result } }]),
});
