/**
 * IMG e2e 도우미 — 게이트웨이 경유 API(브라우저와 같은 개발 사용자) · 화면 캡처 · 견본 파일(버퍼로 넣는다).
 * 공유 개발 데이터라 목록이 비어 있다고 가정하지 않는다 — 테스트마다 자기 작업을 만든다.
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { expect, type APIRequestContext, type Page } from '@playwright/test';

const FX = fileURLToPath(new URL('./fixtures/', import.meta.url));
export const DESC = '카페 카운터 위에 3연 메뉴보드가 걸린 장면, 낮 시간, 손님 2~3명';
export const QM55C = { family_id: 'fam_G000182628', model_code: 'LH55QMCEBGCXKR', name: 'Smart Signage QM55C', short: 'QM55C', qty: 3, source: 'user' as const };

export const shot = (page: Page, name: string) => page.screenshot({ path: `e2e/image/__screens__/${name}.png` });
export const fixture = (name: string) => ({ name, mimeType: 'image/png', buffer: fs.readFileSync(FX + name) });

/** 내부 전용 API(요청 · 사용 등록)용 토큰 — INTERNAL_TOKEN 또는 data/.internal_token */
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

/** internal = 서비스 간 호출 흉내(내부 토큰 + 호출 서비스 + 지금 사용자) */
export async function api<T = any>(req: APIRequestContext, method: string, p: string, body?: unknown, internal: false | string = false): Promise<T> {
  const headers = internal
    ? { 'X-Internal-Token': internalToken(), 'X-Caller-Service': internal, 'X-User-Id': await myId(req), 'X-User-Name': encodeURIComponent('테스터') }
    : undefined;
  const r = await req.fetch(`/api/image/v1${p}`, { method, data: body === undefined ? undefined : body, headers });
  if (!r.ok()) throw new Error(`${method} ${p} → ${r.status()} ${await r.text()}`);
  return (r.status() === 204 ? null : await r.json()) as T;
}

export async function newWork(req: APIRequestContext, body: Record<string, unknown> = { kind: 'space', description: DESC }) {
  return api(req, 'POST', '/works', body);
}

export async function waitRun(req: APIRequestContext, runId: string, until = ['succeeded', 'failed', 'canceled', 'awaiting_input'], timeout = 90_000) {
  const t0 = Date.now();
  for (;;) {
    const r = await api(req, 'GET', `/runs/${runId}`);
    if (until.includes(r.status)) return r;
    if (Date.now() - t0 > timeout) throw new Error(`run ${runId} 이 ${until.join('/')} 가 되지 않음(${r.status})`);
    await new Promise((res) => setTimeout(res, 700));
  }
}

/** 설명 → prefill → run(count) → 끝날 때까지 */
export async function doneWork(req: APIRequestContext, opts: { desc?: string; count?: 2 | 4 } = {}) {
  const w = await newWork(req, { kind: 'space', description: opts.desc ?? DESC });
  await api(req, 'POST', `/works/${w.id}:prefill`);
  const acc = await api(req, 'POST', `/works/${w.id}/runs`, { kind: 'initial', count: opts.count ?? 2, notify: false });
  const run = await waitRun(req, acc.run_id, ['succeeded', 'failed', 'awaiting_input']);
  expect(run.status).toBe('succeeded');
  return { work: w, run };
}

/** 파일 서비스에 올리기(기밀) */
export async function uploadFixture(req: APIRequestContext, name: string, confidential = true): Promise<string> {
  const r = await req.post('/api/files/v1/files', { multipart: { file: fixture(name), confidential: String(confidential) } });
  if (!r.ok()) throw new Error(`upload → ${r.status()} ${await r.text()}`);
  return (await r.json()).id;
}

export const uniq = () => Date.now().toString(36).slice(-5).toUpperCase();
