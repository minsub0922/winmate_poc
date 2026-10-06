/**
 * 경쟁사 분석 e2e 도우미 — 실제 competitor 서비스(make dev-bg SERVICE=competitor) + 플랫폼(ai-tools mock · kb · jobs · workspace · export)을 게이트웨이로 부른다.
 * 공유 개발 사용자 · 데이터라 목록이 비어 있다고 가정하지 않는다(만든 작업만 id 로 찾는다).
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { expect, test, type APIRequestContext, type Page } from '@playwright/test';

const here = path.dirname(fileURLToPath(import.meta.url));
export const SCREENS = path.join(here, '__screens__');

export async function shot(page: Page, name: string) {
  fs.mkdirSync(SCREENS, { recursive: true });
  await page.waitForTimeout(250);
  await page.screenshot({ path: path.join(SCREENS, `${name}.png`) });
}

export const CA_ID = /ca_[0-9A-HJKMNP-TV-Z]{26}/;
export const uniq = () => Date.now().toString(36).toUpperCase().slice(-5);
export const A_TEXT = 'A 커피 프랜차이즈가 전국 320개 매장의 메뉴보드를 디지털로 바꾸려고 해요. 수도권 직영점부터 시작하고, 55인치 사이니지와 본사에서 콘텐츠를 일괄 배포하는 솔루션이 필요해요.';
export const REAL = ['가나 디스플레이', '다라 사이니지', '마바 클라우드', '사아 키오스크', '자차 디스플레이', '카타 미디어'];

/** competitor 서비스가 꺼져 있으면 이유(건너뛰기용) */
export async function backendDown(request: APIRequestContext): Promise<string | null> {
  const r = await request.get('/api/competitor/v1/info').catch(() => null);
  if (!r || !r.ok()) return 'competitor 서비스가 꺼져 있어요(make dev-bg SERVICE=competitor)';
  return null;
}

/**
 * 시간 예산 — 공유 머신(2 CPU · 7GB)이 다른 세션 일로 바쁘면 page 준비 · 첫 요청만으로 수십 초가 갈 수 있다.
 * 파일 머리 `test.describe.configure({ timeout: SETUP_MS })` 가 준비(fixture · beforeEach) 시간을 잡고,
 * 본문은 `budget(ms)` 로 그 위에 ms 를 더한다(test.setTimeout 은 총량이라 준비에 쓴 시간을 잃는다).
 */
export const SETUP_MS = 120_000;
export function budget(ms: number) {
  test.setTimeout(test.info().timeout + ms);
}

export async function api<T = any>(request: APIRequestContext, method: string, p: string, body?: unknown): Promise<T> {
  // 게이트웨이가 연결 재사용 중 끊긴 연결(RemoteProtocolError)을 500 으로 돌려줄 때가 있어 GET 은 두 번까지 다시 묻는다
  for (let i = 0; ; i++) {
    const r = await request.fetch(`/api/competitor/v1${p}`, { method, data: body === undefined ? undefined : body });
    if (r.ok()) return (r.status() === 204 ? null : await r.json()) as T;
    const text = await r.text();
    if (method === 'GET' && r.status() >= 500 && i < 2) { await new Promise((res) => setTimeout(res, 300)); continue; }
    throw new Error(`${method} ${p} → ${r.status()} ${text}`);
  }
}

export async function waitStatus(request: APIRequestContext, id: string, want: string[], timeout = 90_000): Promise<any> {
  const t0 = Date.now();
  let last: any = null;
  while (Date.now() - t0 < timeout) {
    last = await api(request, 'GET', `/analyses/${id}`);
    if (want.includes(last.status)) return last;
    await new Promise((res) => setTimeout(res, 600));
  }
  throw new Error(`분석 ${id} 상태가 ${want.join('/')} 가 되지 않음 (지금 ${last?.status})`);
}

/** 후보 확인까지 마친 작업(실제 find 잡 · mock 모델) */
export async function seedConfirming(request: APIRequestContext, text = A_TEXT): Promise<any> {
  const a = await api(request, 'POST', '/analyses', { input_mode: 'free', text });
  await api(request, 'POST', `/analyses/${a.id}/find`);
  return waitStatus(request, a.id, ['confirming', 'ask', 'failed'], 60_000);
}

/** 분석까지 마친 작업 */
export async function seedDone(request: APIRequestContext, text = A_TEXT): Promise<any> {
  const a = await seedConfirming(request, text);
  expect(a.status).toBe('confirming');
  await api(request, 'POST', `/analyses/${a.id}/runs`, { mode: 'full' });
  return waitStatus(request, a.id, ['done', 'upd', 'stopped'], 120_000);
}

export async function noRealNames(page: Page, names = REAL) {
  const text = await page.locator('#wm-main').innerText();
  for (const n of names) expect(text, `실명 ${n} 이 보이면 안 된다`).not.toContain(n);
}
