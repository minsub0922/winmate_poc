/** Spec(SP) e2e 도우미 — API 로 준비 · 스크린숏 · 파일 버퍼 업로드(한글 경로 우회) */
import fs from 'node:fs';
import path from 'node:path';
import { expect, type APIRequestContext, type Page } from '@playwright/test';

export const QM55C = 'LH55QMCEBGCXKR';
export const QB55C = 'LH55QBCEBGCXKR';
export const QH55C = 'LH55QHCEBGCXKR';
export const QM65C = 'LH65QMCEBGCXKR';
export const QM55R = 'LH55QMREBGCXKR';

const HERE = path.dirname(new URL(import.meta.url).pathname);
export const FIXTURES = path.join(HERE, 'fixtures');
const SCREENS = path.join(HERE, '__screens__');

export async function shot(page: Page, name: string) {
  fs.mkdirSync(SCREENS, { recursive: true });
  await page.waitForTimeout(250);
  await page.screenshot({ path: path.join(SCREENS, `${name}.png`) });
}

/** setInputFiles 에 한글 경로를 넘기면 Chromium 이 무시하므로 버퍼로 넘긴다 */
export function fileBuffer(name: string, mimeType: string) {
  return { name, mimeType, buffer: fs.readFileSync(path.join(FIXTURES, name)) };
}

const API = '/api/spec/v1';

export async function api<T = any>(request: APIRequestContext, method: 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE', url: string, data?: unknown): Promise<T> {
  const r = await request.fetch(`${API}${url}`, { method, data: data as never, headers: data ? { 'Content-Type': 'application/json' } : undefined });
  const text = await r.text();
  expect(r.ok(), `${method} ${url} → ${r.status()} ${text.slice(0, 300)}`).toBeTruthy();
  return (text ? JSON.parse(text) : undefined) as T;
}

/** 작업 만들기(모델 코드) */
export async function createSheet(request: APIRequestContext, models: string[], extra: Record<string, unknown> = {}) {
  const s = await api(request, 'POST', '/sheets', { start: 'model', products: models, ...extra });
  return s as { id: string; title: string };
}

/** 생성 잡이 끝날 때까지 */
export async function waitIdle(request: APIRequestContext, id: string, timeout = 40_000) {
  const t0 = Date.now();
  for (;;) {
    const s = await api(request, 'GET', `/sheets/${id}`);
    if (!s.active_job || !['queued', 'running'].includes(s.active_job.status)) return s;
    if (Date.now() - t0 > timeout) throw new Error(`생성이 끝나지 않음: ${JSON.stringify(s.active_job)}`);
    await new Promise((r) => setTimeout(r, 500));
  }
}

/** 항목 → 생성 → (값 확인은 [확정 필요]로) → 완료된 시트 */
export async function generatedSheet(request: APIRequestContext, models: string[], opts: { items?: string[]; deferChecks?: boolean } = {}) {
  const { id } = await createSheet(request, models);
  await api(request, 'PATCH', `/sheets/${id}`, { step: 2 });
  if (opts.items) await api(request, 'PUT', `/sheets/${id}/items`, { items: opts.items.map((key) => ({ key, checked: true })) });
  await api(request, 'POST', `/sheets/${id}/generate`, { mode: 'full' });
  await waitIdle(request, id);
  if (opts.deferChecks !== false) {
    await api(request, 'POST', `/sheets/${id}/checks:defer-all`);
    await api(request, 'POST', `/sheets/${id}/checks:apply`, { answers: [] });
  }
  return api(request, 'GET', `/sheets/${id}`);
}

/** 셸 상단 · 스텝바가 그려질 때까지 */
export async function ready(page: Page) {
  await expect(page.getByRole('region', { name: '입력 도크' })).toBeVisible();
}
