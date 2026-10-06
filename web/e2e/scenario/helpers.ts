/**
 * SC e2e 도우미 — 게이트웨이 경유 API(브라우저와 같은 개발 사용자) · 화면 캡처 · 잡 기다리기.
 * 공유 개발 데이터라 목록이 비어 있다고 가정하지 않는다 — 테스트마다 자기 시나리오를 만든다.
 */
import fs from 'node:fs';
import path from 'node:path';
import { expect, type APIRequestContext, type Page } from '@playwright/test';

export const RAW = [
  '07:00 점장이 매장을 오픈한다. 메뉴보드가 아침 메뉴로 켜져 있어야 한다.',
  '11:30 점심 피크. 주문 줄이 길어지고 프로모션 음료가 잘 팔린다.',
  '14:00 본사 마케팅팀이 전국 320개 매장에 오후 프로모션을 배포한다.',
  '21:00 마감. 메뉴보드가 자동으로 꺼지고 전력 사용량이 집계된다.',
].join('\n');
export const QM55C = { ref: 'kb:model:mdl_LH55QMCEBGCXKR', family_id: 'fam_G000182628', model_code: 'LH55QMCEBGCXKR', label: 'Smart Signage QM55C', short: 'QM55C', qty: 3 };
export const KM24C = { ref: 'custom:Kiosk KM24C', label: 'Kiosk KM24C', short: 'KM24C' };

export const shot = (page: Page, name: string) => page.screenshot({ path: `e2e/scenario/__screens__/${name}.png` });

function internalToken(): string {
  if (process.env.INTERNAL_TOKEN) return process.env.INTERNAL_TOKEN;
  const p = path.resolve(process.cwd(), '..', 'data', '.internal_token');
  return fs.existsSync(p) ? fs.readFileSync(p, 'utf8').trim() : '';
}
let meId: string | null = null;
async function myId(req: APIRequestContext): Promise<string> {
  if (!meId) meId = ((await (await req.get('/api/workspace/v1/me')).json()) as { user_id: string }).user_id;
  return meId;
}

/** scenario API. internal = 서비스 간 호출 흉내(내부 토큰 + 호출 서비스 + 지금 사용자) */
export async function api<T = any>(req: APIRequestContext, method: string, p: string, body?: unknown, internal: false | string = false): Promise<T> {
  const headers = internal
    ? { 'X-Internal-Token': internalToken(), 'X-Caller-Service': internal, 'X-User-Id': await myId(req), 'X-User-Name': encodeURIComponent('테스터') }
    : undefined;
  const r = await req.fetch(`/api/scenario/v1${p}`, { method, data: body === undefined ? undefined : body, headers });
  if (!r.ok()) throw new Error(`${method} ${p} → ${r.status()} ${await r.text()}`);
  return (r.status() === 204 ? null : await r.json()) as T;
}

export async function waitJob(req: APIRequestContext, jobId: string, timeout = 90_000) {
  const t0 = Date.now();
  for (;;) {
    const j = await (await req.get(`/api/jobs/v1/jobs/${jobId}`)).json();
    if (['succeeded', 'failed', 'canceled'].includes(j.status)) return j;
    if (Date.now() - t0 > timeout) throw new Error(`job ${jobId} 이 끝나지 않음(${j.status})`);
    await new Promise((res) => setTimeout(res, 500));
  }
}

/** API 로 보드 예 시나리오를 원하는 단계까지 만든다 */
export async function makeScenario(req: APIRequestContext, opts: { type?: 'with' | 'without'; until?: 'parsed' | 'picked' | 'done'; solutions?: string[]; title?: string } = {}) {
  const sc = await api(req, 'POST', '/scenarios', { type: opts.type ?? 'with', title: opts.title });
  const acc = await api(req, 'POST', `/scenarios/${sc.id}/input:parse`, { raw_text: RAW, characters: ['점장', '손님', '본사 마케팅 담당자'] });
  expect((await waitJob(req, acc.job_id)).status).toBe('succeeded');
  if (opts.until === 'parsed') return sc.id as string;
  if ((opts.type ?? 'with') === 'with') await api(req, 'PUT', `/scenarios/${sc.id}/solutions`, { items: (opts.solutions ?? ['magicinfo', 'smartthings_pro']).map((s) => ({ solution_id: s })) });
  await api(req, 'PUT', `/scenarios/${sc.id}/products`, { items: [QM55C, KM24C] });
  if (opts.until === 'picked') return sc.id as string;
  const rg = await api(req, 'POST', `/scenarios/${sc.id}:route-generate`);
  expect(rg.next).toBe('SC4G');
  const g = await api(req, 'POST', `/scenarios/${sc.id}/generate`, { scope: 'all' });
  expect((await waitJob(req, g.job_id)).status).toBe('succeeded');
  return sc.id as string;
}
