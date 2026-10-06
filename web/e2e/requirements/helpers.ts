/** RQ e2e 도우미 — 견본 파일(버퍼로 넣는다: 이 환경의 Chromium 은 한글 경로 setInputFiles 를 조용히 무시한다) · 화면 캡처 · API. */
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';
import type { APIRequestContext, Page } from '@playwright/test';

const FX = fileURLToPath(new URL('./fixtures/', import.meta.url));
const MIME: Record<string, string> = {
  pptx: 'application/vnd.openxmlformats-officedocument.presentationml.presentation', txt: 'text/plain', pdf: 'application/pdf',
};
export const RQ_ID = /rq_[0-9A-HJKMNP-TV-Z]{26}/;

export function files(...names: string[]) {
  return names.map((name) => ({ name, mimeType: MIME[name.split('.').pop() ?? ''] ?? 'application/octet-stream', buffer: fs.readFileSync(FX + name) }));
}

export async function attach(page: Page, selector: string, payload: ReturnType<typeof files>) {
  await page.locator(selector).setInputFiles(payload);
}

/** 화면 위에 파일을 끄는 것처럼(DataTransfer) — dragenter 만(drop=false) 또는 놓기까지 */
export async function dragFiles(page: Page, names: string[], drop: boolean) {
  const data = names.map((n) => ({ name: n, type: MIME[n.split('.').pop() ?? ''] ?? '', b64: fs.readFileSync(FX + n).toString('base64') }));
  await page.evaluate(({ data, drop }) => {
    const dt = new DataTransfer();
    for (const f of data) {
      const bin = Uint8Array.from(atob(f.b64), (c) => c.charCodeAt(0));
      dt.items.add(new File([bin], f.name, { type: f.type }));
    }
    const target = document.querySelector('.rq-form-section') ?? document.body;
    target.dispatchEvent(new DragEvent('dragenter', { bubbles: true, cancelable: true, dataTransfer: dt }));
    target.dispatchEvent(new DragEvent('dragover', { bubbles: true, cancelable: true, dataTransfer: dt }));
    if (drop) target.dispatchEvent(new DragEvent('drop', { bubbles: true, cancelable: true, dataTransfer: dt }));
  }, { data, drop });
}

export const shot = (page: Page, name: string) => page.screenshot({ path: `e2e/requirements/__screens__/${name}.png` });

export const sum = (xs: number[]) => xs.reduce((a, b) => a + b, 0);

/** 폼의 가중치 막대 값 */
export async function weightsOf(page: Page): Promise<number[]> {
  const raw = await page.locator('.rq-rightcard .rq-wbar').first().getAttribute('data-weights');
  return (raw ?? '').split(',').filter(Boolean).map(Number);
}

export const uniq = () => Date.now().toString(36).toUpperCase();

/** 다른 서비스 자원 id 흉내(`sb_<ULID>` 꼴) */
export function fakeId(prefix: string): string {
  const A = '0123456789ABCDEFGHJKMNPQRSTVWXYZ';
  return `${prefix}_${Array.from({ length: 26 }, (_, i) => A[i === 0 ? 0 : Math.floor(Math.random() * 32)]).join('')}`;
}

/** 게이트웨이 경유 API(브라우저와 같은 세션) */
export async function apiJson<T>(req: APIRequestContext, method: string, path: string, body?: unknown): Promise<T> {
  const r = await req.fetch(`/api/requirements/v1${path}`, { method, data: body === undefined ? undefined : body });
  if (!r.ok()) throw new Error(`${method} ${path} → ${r.status()} ${await r.text()}`);
  return (await r.json()) as T;
}

/** 서비스 직접(internal 경로 — 소비 서비스 대신 링크 등록). 내부 토큰은 저장소 data/.internal_token */
export function internalToken(): string {
  const p = fileURLToPath(new URL('../../../data/.internal_token', import.meta.url));
  return fs.readFileSync(p, 'utf8').trim();
}

export const PPTX = '제안지원요청서_용산 업무시설 재개발.pptx';
export const MEMO = '고객 미팅 메모_11월 4일.txt';
export const PDF = '성수오피스_에너지사용량_2025.pdf';

const wait = (ms: number) => new Promise((res) => setTimeout(res, ms));

/** files 서비스에 견본 파일을 올린다(화면과 같은 기밀 · 용도) → file_id */
export async function uploadFixture(req: APIRequestContext, name: string): Promise<string> {
  const [f] = files(name);
  const r = await req.post('/api/files/v1/files', { multipart: { file: f, confidential: 'true', purpose: 'rq.source' } });
  if (!r.ok()) throw new Error(`upload ${name} → ${r.status()} ${await r.text()}`);
  return ((await r.json()) as { id: string }).id;
}

/** 정의서를 만들고 ops 를 한 번에 넣는다 */
export async function createRq(req: APIRequestContext, ops: Array<Record<string, unknown>> = []): Promise<Rq> {
  const rq = await apiJson<Rq>(req, 'POST', '/requirements', {});
  if (!ops.length) return rq;
  return apiJson<Rq>(req, 'PATCH', `/requirements/${rq.id}/draft`, { base_revision: null, ops });
}

/** 견본 파일로 채우고 끝날 때까지 기다린다 */
export async function fillWith(req: APIRequestContext, id: string, names: string[]): Promise<Rq> {
  const ids = [];
  for (const n of names) ids.push(await uploadFixture(req, n));
  await apiJson(req, 'POST', `/requirements/${id}/files`, { file_ids: ids });
  for (let i = 0; i < 200; i++) {
    const rq = await apiJson<Rq>(req, 'GET', `/requirements/${id}`);
    if (!rq.active_job && !rq.files.some((f) => f.status === 'reading' || f.status === 'uploading')) return rq;
    await wait(300);
  }
  throw new Error(`채우기가 끝나지 않았어요: ${id}`);
}

/** 심층 작성 세션이 분석을 마칠 때까지 */
export async function waitSession(req: APIRequestContext, id: string, sid: string, status = 'ready'): Promise<Session> {
  for (let i = 0; i < 200; i++) {
    const s = await apiJson<Session>(req, 'GET', `/requirements/${id}/deep-sessions/${sid}`);
    if (s.status === status) return s;
    if (s.status === 'failed') throw new Error(`분석 실패: ${sid}`);
    await wait(300);
  }
  throw new Error(`세션이 ${status} 가 되지 않았어요: ${sid}`);
}

export interface Rq {
  id: string; revision: number; version: number; active_job: unknown; list_state: string;
  files: Array<{ file_id: string; status: string; name: string }>;
  form: {
    project_name: { value: string | null }; customer_name: { value: string | null }; final_audience: { value: string | null };
    weights_mode: string;
    keymen: Array<{ id: string; name: string; weight: number | null; items: Array<{ id: string; text: string; code: string }> }>;
  };
}

export interface Session { id: string; status: string; current_index: number; total: number; current_gap_id: string | null }
