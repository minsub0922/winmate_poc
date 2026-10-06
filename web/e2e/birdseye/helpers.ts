/**
 * BE e2e 도우미 — 게이트웨이 경유 API(브라우저와 같은 개발 사용자) · 화면 캡처 · 잡 기다리기.
 * 공유 개발 데이터라 목록이 비어 있다고 가정하지 않는다 — 테스트마다 자기 조감도를 만든다.
 */
import path from 'node:path';
import { expect, type APIRequestContext, type Page } from '@playwright/test';

export const DESC = '강남 플래그십 스토어 1층 로비. 약 120평, 층고 4.5m, 정면이 전면 유리창이라 낮에는 밝고 저녁엔 외부에서 내부가 잘 보임. 중앙에 기둥 2개.';
export const FIX = (name: string) => path.resolve('e2e/birdseye/fixtures', name);   // playwright 는 web/ 에서 돈다
export const shot = (page: Page, name: string) => page.screenshot({ path: `e2e/birdseye/__screens__/${name}.png` });

export async function api<T = any>(req: APIRequestContext, method: string, p: string, body?: unknown): Promise<T> {
  const r = await req.fetch(`/api/birdseye/v1${p}`, { method, data: body === undefined ? undefined : body });
  if (!r.ok()) throw new Error(`${method} ${p} → ${r.status()} ${await r.text()}`);
  return (r.status() === 204 ? null : await r.json()) as T;
}

export async function waitJob(req: APIRequestContext, jobId: string, timeout = 120_000) {
  const t0 = Date.now();
  for (;;) {
    const j = await (await req.get(`/api/jobs/v1/jobs/${jobId}`)).json();
    if (['succeeded', 'failed', 'canceled'].includes(j.status)) return j;
    if (Date.now() - t0 > timeout) throw new Error(`job ${jobId} 이 끝나지 않음(${j.status})`);
    await new Promise((res) => setTimeout(res, 500));
  }
}

/** API 로 공간 분석 · 제품(실제 KB) · 가구 · 배치까지 만든다 */
export async function makeLayout(req: APIRequestContext, title = `e2e 조감도 ${Date.now()}`): Promise<string> {
  const b = await api(req, 'POST', '/birdseyes', { title, description: DESC });
  const a = await api(req, 'POST', `/birdseyes/${b.id}/space:analyze`);
  expect((await waitJob(req, a.job_id)).status).toBe('succeeded');
  const items = [];
  for (const q of ['OH55', 'Flip Pro', 'The Wall']) {
    const s = await api(req, 'GET', `/product-search?q=${encodeURIComponent(q)}&limit=1`);
    items.push({ ref: s.items[0].ref, family_id: s.items[0].family_id, model_code: s.items[0].model_code });
  }
  await api(req, 'PUT', `/birdseyes/${b.id}/products`, { items });
  const f = await api(req, 'POST', `/birdseyes/${b.id}/furniture:recommend`, { exclude: [] });
  expect((await waitJob(req, f.job_id)).status).toBe('succeeded');
  const g = await api(req, 'POST', `/birdseyes/${b.id}/layout:generate`, { none: false });
  expect((await waitJob(req, g.job_id)).status).toBe('succeeded');
  return b.id as string;
}

/** 주 컷까지 만든다(렌더는 image 서비스 mock) */
export async function makeResult(req: APIRequestContext, title?: string): Promise<{ id: string; cutId: string }> {
  const id = await makeLayout(req, title);
  const acc = await api(req, 'POST', `/birdseyes/${id}/cuts`, { views: [{ preset: 'aerial45' }], lights: ['day'], primary: true, auto_extra: false, before: false });
  expect((await waitJob(req, acc.job_id, 180_000)).status).toBe('succeeded');
  return { id, cutId: acc.cut_ids[0] };
}
