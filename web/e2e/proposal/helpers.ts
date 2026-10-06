/**
 * 제안서(PR) e2e 도우미 — 실제 proposal 서비스(게이트웨이 경유) + 플랫폼(jobs · workspace · export · files · ai-tools mock).
 * 공유 개발 사용자 · 데이터라 목록이 비어 있다고 가정하지 않는다 — 테스트가 만든 제안서만 id 로 찾고, 끝나면 지운다.
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { expect, type APIRequestContext, type Page } from '@playwright/test';

const here = path.dirname(fileURLToPath(import.meta.url));
export const SCREENS = path.join(here, '__screens__');

export async function shot(page: Page, name: string) {
  fs.mkdirSync(SCREENS, { recursive: true });
  await page.waitForTimeout(250);
  await page.screenshot({ path: path.join(SCREENS, `${name}.png`) });
}

export const PR_ID = /pr_[0-9A-HJKMNP-TV-Z]{26}/;
export const uniq = () => Date.now().toString(36).toUpperCase().slice(-5);
export const CUSTOMER = 'A 커피 프랜차이즈';

/** proposal 서비스가 꺼져 있으면 이유(건너뛰기용) */
export async function backendDown(request: APIRequestContext): Promise<string | null> {
  const r = await request.get('/api/proposal/v1/info').catch(() => null);
  if (!r || !r.ok()) return 'proposal 서비스가 꺼져 있어요(make dev-bg SERVICE=proposal)';
  return null;
}

/** 그 경로가 아직 501(NOT_IMPLEMENTED)이면 이유 */
export async function notImplemented(request: APIRequestContext, method: string, p: string, body?: unknown): Promise<string | null> {
  const r = await request.fetch(`/api/proposal/v1${p}`, { method, data: body === undefined ? undefined : body }).catch(() => null);
  if (!r) return 'proposal 서비스에 닿지 않아요';
  if (r.status() === 501) return `백엔드 미구현: ${method} ${p} (501)`;
  return null;
}

export async function api<T = any>(request: APIRequestContext, method: string, p: string, body?: unknown, headers?: Record<string, string>): Promise<T> {
  const r = await request.fetch(`/api/proposal/v1${p}`, { method, data: body === undefined ? undefined : body, headers });
  if (!r.ok()) throw new Error(`${method} ${p} → ${r.status()} ${await r.text()}`);
  return (r.status() === 204 ? null : await r.json()) as T;
}

export async function waitJob(request: APIRequestContext, jobId: string, timeout = 120_000): Promise<any> {
  const t0 = Date.now();
  let last: any = null;
  while (Date.now() - t0 < timeout) {
    const r = await request.get(`/api/jobs/v1/jobs/${jobId}`);
    if (r.ok()) {
      last = await r.json();
      if (['succeeded', 'failed', 'canceled', 'awaiting_input'].includes(last.status)) return last;
    }
    await new Promise((res) => setTimeout(res, 700));
  }
  throw new Error(`잡 ${jobId} 이 끝나지 않음 (지금 ${last?.status})`);
}

/** 빈 제안서(고객 정보까지) — 끝나면 removeProposal */
export async function seedProposal(request: APIRequestContext, extra: Record<string, unknown> = {}): Promise<any> {
  return api(request, 'POST', '/proposals', {
    start_mode: 'blank', title: `[e2e] 전국 매장 디지털 메뉴보드 전환 ${uniq()}`,
    customer: { name: CUSTOMER, industry_chip: '리테일 · F&B', scale_text: '320개 매장' }, ...extra,
  });
}
/** 유형 · 시트 구성 · 업종 레이아웃까지 정한 제안서 */
export async function seedComposed(request: APIRequestContext, type: 'standard' | 'quickwin' | 'solution' = 'standard'): Promise<any> {
  const p = await seedProposal(request);
  await api(request, 'PUT', `/proposals/${p.id}/type`, { type });
  await api(request, 'POST', `/proposals/${p.id}/composition:start`);
  await api(request, 'PUT', `/proposals/${p.id}/industry`, { decided: true }).catch(() => null);
  return api(request, 'GET', `/proposals/${p.id}`);
}
/** PPTX 까지 만든 제안서(실제 generate 잡 · mock 모델) */
export async function seedGenerated(request: APIRequestContext): Promise<any> {
  const p = await seedComposed(request);
  const j = await api(request, 'POST', `/proposals/${p.id}:generate`, { scope: 'all', infer_empty: true });
  const done = await waitJob(request, j.job_id, 150_000);
  expect(done.status).toBe('succeeded');
  return api(request, 'GET', `/proposals/${p.id}`);
}
export async function removeProposal(request: APIRequestContext, id: string | undefined | null) {
  if (!id) return;
  await request.delete(`/api/proposal/v1/proposals/${id}`).catch(() => null);
}

/** 셸이 뜰 때까지 기다리며 연다(첫 진입은 Vite 가 모듈을 처음 변환해 느릴 수 있다) */
export async function open(page: Page, url: string) {
  await page.goto(url);
  await page.locator('.pr-page, .pr-res, .pr-list').first().waitFor({ timeout: 60_000 });
}

/**
 * 같은 작업 트리에서 다른 세션이 기능 모듈을 고치는 중이라 그 모듈이 Vite 에서 500(가져올 파일 없음)이면,
 * 셸 등록(import.meta.glob eager) 전체가 깨진다. 시험 하네스에서만 그 모듈을 빈 모듈로 바꿔 이 기능 화면만 돌린다(제품 동작은 그대로).
 */
export async function isolateBrokenFeatures(page: Page) {
  await page.route(/\/src\/features\/(?!proposal\/)[^/]+\/index\.tsx(\?.*)?$/, async (route) => {
    const resp = await route.fetch().catch(() => null);
    if (resp && resp.status() < 500) return route.fulfill({ response: resp });
    return route.fulfill({ status: 200, contentType: 'application/javascript', body: 'export default null;\n' });
  });
}

/**
 * 공유 PC 메모리가 모자라면 커널(cgroup OOM)이 백엔드 잡이 도는 동안 브라우저 탭(oom_score_adj 300)을 먼저 죽인다.
 * 긴 잡을 기다리는 테스트는 탭이 죽었는지 지켜보다가, 죽었으면 새 탭을 열어 화면 확인을 이어 간다.
 */
export function watchCrash(page: Page) {
  const st = { crashed: false };
  page.on('crash', () => { st.crashed = true; });
  return {
    get crashed() { return st.crashed; },
    async alive(): Promise<Page> {
      if (!st.crashed) return page;
      const p2 = await page.context().newPage();
      await isolateBrokenFeatures(p2);
      return p2;
    },
  };
}
