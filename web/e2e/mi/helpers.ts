/**
 * MI e2e 도우미 — 실제 mi 서비스(make dev-bg SERVICE=mi) + 플랫폼(ai-tools mock · kb · jobs · workspace · export)을 게이트웨이로 부른다.
 * 공유 개발 사용자 · 데이터라 목록이 비어 있다고 가정하지 않는다(만든 작업만 id 로 찾는다).
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { expect, type APIRequestContext, type Page } from '@playwright/test';

const here = path.dirname(fileURLToPath(import.meta.url));
export const SCREENS = path.join(here, '__screens__');

export async function shot(page: Page, name: string) {
  fs.mkdirSync(SCREENS, { recursive: true });
  await page.waitForTimeout(200);
  await page.screenshot({ path: path.join(SCREENS, `${name}.png`) });
}

export const MI_ID = /mi_[0-9A-HJKMNP-TV-Z]{26}/;
export const uniq = () => Date.now().toString(36).toUpperCase().slice(-5);

/** mi 서비스가 꺼져 있으면 이유(건너뛰기용) */
export async function backendDown(request: APIRequestContext): Promise<string | null> {
  const r = await request.get('/api/mi/v1/info').catch(() => null);
  if (!r || !r.ok()) return 'mi 서비스가 꺼져 있어요(make dev-bg SERVICE=mi)';
  return null;
}

export async function api<T = any>(request: APIRequestContext, method: string, p: string, body?: unknown): Promise<T> {
  const r = await request.fetch(`/api/mi/v1${p}`, { method, data: body === undefined ? undefined : body });
  if (!r.ok()) throw new Error(`${method} ${p} → ${r.status()} ${await r.text()}`);
  return (r.status() === 204 ? null : await r.json()) as T;
}

export async function waitStatus(request: APIRequestContext, id: string, want: string[], timeout = 90_000): Promise<any> {
  const t0 = Date.now();
  let last: any = null;
  while (Date.now() - t0 < timeout) {
    last = await api(request, 'GET', `/analyses/${id}`);
    if (want.includes(last.status)) return last;
    await new Promise((res) => setTimeout(res, 700));
  }
  throw new Error(`분석 ${id} 상태가 ${want.join('/')} 가 되지 않음 (지금 ${last?.status})`);
}

export async function waitDesign(request: APIRequestContext, id: string, timeout = 60_000): Promise<any> {
  const t0 = Date.now();
  let last: any = null;
  while (Date.now() - t0 < timeout) {
    last = await api(request, 'GET', `/analyses/${id}/design`);
    if (['done', 'ask', 'failed'].includes(last.status)) return last;
    await new Promise((res) => setTimeout(res, 600));
  }
  throw new Error(`설계가 끝나지 않음 (${last?.status})`);
}

export const CUSTOMER = 'A 커피';
export const REQ = 'A 커피 프랜차이즈 320개 매장 디지털 메뉴보드 교체 — 본사 일괄 관리, 전기료 절감, 경쟁사 대비 강점, 주문 대기 줄이기';

/** 설계까지 마친 작업(실제 잡) */
export async function seedDesigned(request: APIRequestContext, customer = `${CUSTOMER} ${uniq()}`, extra: Record<string, unknown> = {}): Promise<any> {
  const a = await api(request, 'POST', '/analyses', { customer_name: customer, requirements_text: REQ, ...extra });
  await api(request, 'POST', `/analyses/${a.id}/design`);
  const d = await waitDesign(request, a.id);
  expect(d.status).toBe('done');
  return a;
}

/** 분석까지 마친 작업(실제 잡 · mock 모델) */
export async function seedDone(request: APIRequestContext, customer?: string, extra: Record<string, unknown> = {}): Promise<any> {
  const a = await seedDesigned(request, customer, extra);
  await api(request, 'POST', `/analyses/${a.id}/runs`, { mode: 'full' });
  return waitStatus(request, a.id, ['done', 'upd'], 150_000);
}
