/**
 * 통합(integration) e2e 도우미 — 실제 스택(게이트웨이 5000 · 기능 서비스 10 + 워커 · 플랫폼, MODEL_MODE=mock)만 쓴다(page.route 흉내 없음).
 * 공유 개발 사용자 · 데이터라 목록이 비어 있다고 가정하지 않는다: 테스트가 만든 자원은 id 로 찾고, 지울 수 있는 것은 끝에 지운다.
 *
 * 실행: cd web && PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers WM_E2E_SUITE=integration WM_E2E_DEV=1 WM_E2E_PORT=5299 \
 *        npx playwright test e2e/integration --workers=1
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { expect, test, type APIRequestContext, type Locator, type Page } from '@playwright/test';

const here = path.dirname(fileURLToPath(import.meta.url));
export const SCREENS = path.join(here, '__screens__');
export const E2E = path.resolve(here, '..');

export async function shot(page: Page, name: string) {
  fs.mkdirSync(SCREENS, { recursive: true });
  await page.waitForTimeout(250);
  await page.screenshot({ path: path.join(SCREENS, `${name}.png`) });
}

/** 테스트마다 붙이는 꼬리표(제목 · 이름) */
export const tag = () => Date.now().toString(36).toUpperCase().slice(-5);
export const ID = (prefix: string) => new RegExp(`${prefix}_[0-9A-HJKMNP-TV-Z]{26}`);

/** 공유 PC(2 CPU)라 준비 · 잡 기다림을 넉넉히 — 본문 시간은 budget 으로 더한다 */
export function budget(ms: number) {
  test.setTimeout(test.info().timeout + ms);
}

const sleep = (ms: number) => new Promise((res) => setTimeout(res, ms));

// ── API(게이트웨이 경유, 브라우저와 같은 개발 사용자) ─────────────────────

export type Svc = 'requirements' | 'storyboard' | 'mi' | 'competitor' | 'vp' | 'spec' | 'image' | 'birdseye' | 'scenario' | 'proposal'
  | 'jobs' | 'workspace' | 'files' | 'export' | 'kb';

/** GET 은 게이트웨이 일시 오류(5xx)면 두 번까지 다시 묻는다 */
export async function api<T = any>(req: APIRequestContext, svc: Svc, method: string, p: string, body?: unknown, headers?: Record<string, string>): Promise<T> {
  for (let i = 0; ; i++) {
    const r = await req.fetch(`/api/${svc}/v1${p}`, { method, data: body === undefined ? undefined : body, headers });
    if (r.ok()) return (r.status() === 204 ? null : await r.json().catch(() => null)) as T;
    const text = await r.text();
    if (method === 'GET' && r.status() >= 500 && i < 2) { await sleep(400); continue; }
    throw new Error(`${method} /api/${svc}/v1${p} → ${r.status()} ${text.slice(0, 600)}`);
  }
}

/** 서비스 간 호출 흉내(internal 경로) — 내부 토큰 + 호출 서비스 + 지금 사용자 */
function internalToken(): string {
  if (process.env.INTERNAL_TOKEN) return process.env.INTERNAL_TOKEN;
  const p = path.resolve(E2E, '..', '..', 'data', '.internal_token');
  return fs.existsSync(p) ? fs.readFileSync(p, 'utf8').trim() : '';
}
let meId: string | null = null;
export async function myId(req: APIRequestContext): Promise<string> {
  if (!meId) meId = ((await (await req.get('/api/workspace/v1/me')).json()) as { user_id: string }).user_id;
  return meId;
}
export async function internalApi<T = any>(req: APIRequestContext, caller: Svc, svc: Svc, method: string, p: string, body?: unknown): Promise<T> {
  const headers = { 'X-Internal-Token': internalToken(), 'X-Caller-Service': caller, 'X-User-Id': await myId(req), 'X-User-Name': encodeURIComponent('통합 시험') };
  return api<T>(req, svc, method, p, body, headers);
}

export async function waitJob(req: APIRequestContext, jobId: string, timeout = 180_000, until = ['succeeded', 'failed', 'canceled', 'awaiting_input']): Promise<any> {
  const t0 = Date.now();
  let last: any = null;
  while (Date.now() - t0 < timeout) {
    last = await api(req, 'jobs', 'GET', `/jobs/${jobId}`).catch(() => last);
    if (last && until.includes(last.status)) return last;
    await sleep(700);
  }
  throw new Error(`잡 ${jobId} 이 끝나지 않음 (지금 ${last?.status})`);
}

/** 조건이 맞을 때까지 다시 읽는다 */
export async function until<T>(read: () => Promise<T>, ok: (x: T) => boolean, timeout = 120_000, what = '조건'): Promise<T> {
  const t0 = Date.now();
  let last: T | undefined;
  while (Date.now() - t0 < timeout) {
    try { last = await read(); if (ok(last)) return last; } catch { /* 다시 */ }
    await sleep(800);
  }
  throw new Error(`${what} 이(가) 맞지 않음: ${JSON.stringify(last)?.slice(0, 400)}`);
}

/** 기능 서비스가 게이트웨이에서 보이는지 — 안 보이면 이유 */
export async function backendDown(req: APIRequestContext, svcs: Svc[]): Promise<string | null> {
  for (const s of svcs) {
    const r = await req.get(`/api/${s}/v1/info`).catch(() => null);
    if (!r || !r.ok()) return `${s} 서비스가 게이트웨이에서 보이지 않아요(pm2 restart ${s})`;
  }
  return null;
}

// ── 화면 ──────────────────────────────────────────────────────────

/** 셸이 뜰 때까지 기다리며 연다(첫 진입은 Vite 가 모듈을 처음 변환해 느릴 수 있다) */
export async function open(page: Page, url: string) {
  await page.goto(url);
  await page.locator('#wm-main').first().waitFor({ timeout: 90_000 });
}

/**
 * 뜰 수도 있는 확인(예: 경쟁사 실명 묻기)이 뜨면 누른다 — `next`(다음에 나올 것: 주소 또는 요소)가 먼저 오면 그냥 지나간다.
 * `isVisible({timeout})` 은 기다리지 않으므로 쓰지 않는다.
 */
export async function clickIfShown(page: Page, btn: Locator, next: RegExp | Locator, timeout = 20_000): Promise<boolean> {
  const quiet = (p: Promise<unknown>) => p.then(() => true, () => false);
  const waits = [quiet(btn.waitFor({ state: 'visible', timeout })),
    quiet(next instanceof RegExp ? page.waitForURL(next, { timeout }) : next.first().waitFor({ state: 'visible', timeout }))];
  await Promise.race(waits);
  if (await btn.isVisible().catch(() => false)) {
    await btn.click();
    return true;
  }
  return false;
}

/** 내려받은 파일 이름 — 이 Chromium 은 한글 파일명을 `download` 로 줄 때가 있어 Content-Disposition 을 본다 */
export async function downloadName(req: APIRequestContext, d: { suggestedFilename(): string; url(): string }): Promise<string> {
  const s = d.suggestedFilename();
  if (s && s !== 'download') return s;
  const res = await req.get(d.url());
  const cd = res.headers()['content-disposition'] ?? '';
  const star = cd.match(/filename\*=UTF-8''([^;]+)/i);
  if (star) return decodeURIComponent(star[1]);
  const plain = cd.match(/filename="([^"]+)"/i);
  return plain ? plain[1] : s;
}

// ── 견본 파일 ──────────────────────────────────────────────────────

const MIME: Record<string, string> = {
  pptx: 'application/vnd.openxmlformats-officedocument.presentationml.presentation', txt: 'text/plain', pdf: 'application/pdf',
  png: 'image/png', jpg: 'image/jpeg', xlsx: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
};
/** 다른 기능 e2e 의 견본 파일(읽기만) — 한글 경로는 Chromium 이 setInputFiles 로 못 넣어 버퍼로 넘긴다 */
export function fixture(feature: string, name: string) {
  return { name, mimeType: MIME[name.split('.').pop() ?? ''] ?? 'application/octet-stream', buffer: fs.readFileSync(path.join(E2E, feature, 'fixtures', name)) };
}
export const RFP_PPTX = '제안지원요청서_용산 업무시설 재개발.pptx';
export const MEMO_TXT = '고객 미팅 메모_11월 4일.txt';

export async function uploadFile(req: APIRequestContext, f: ReturnType<typeof fixture>, purpose = 'rq.source', confidential = true): Promise<string> {
  const r = await req.post('/api/files/v1/files', { multipart: { file: f, confidential: String(confidential), purpose } });
  if (!r.ok()) throw new Error(`upload ${f.name} → ${r.status()} ${await r.text()}`);
  return ((await r.json()) as { id: string }).id;
}

// ── 시드(보드 예: E 자산운용 용산 AI Ready 오피스 — mock 고정 응답과 맞는 입력) ──────────────

const CROCK = '0123456789ABCDEFGHJKMNPQRSTVWXYZ';
const ulid = () => `01J${Array.from({ length: 23 }, () => CROCK[Math.floor(Math.random() * 32)]).join('')}`;
export const CUSTOMER = 'E 자산운용';
export const PROJECT = '용산 업무시설 재개발 AI Ready 오피스';
const KEYMEN: Array<[string, string, number]> = [['A', '대표이사', 50], ['B', '공간컨텐츠실장', 30], ['C', '개발사업팀장', 20]];
const ITEMS: Array<[string, string]> = [
  ['A', "사용자를 인식하고 반응하는 'AI Ready' 프라임 스마트 오피스"],
  ['B', '오피스를 업무환경 플랫폼으로 — 입주사 서비스까지'],
  ['C', 'AI 인프라를 설계 단계에 미리 반영하고 예산에 선반영'],
  ['B', '예측 · 반응형 공간(Connecting-AI)'],
  ['A', '에너지 사용량 20% 절감(유사 건물 대비) · 실제 정량 데이터로 증빙'],
  ['A', '건물 가치 · 임대 선호도 제고'],
  ['C', 'ICT 지구 테마 · 용적률 인센티브 연계'],
  ['A', "성수 오피스보다 발전한 '최초 AI Ready' 공간으로 알리기"],
  ['B', '공간별 SAC · 사이니지 · Harman 오디오 구성'],
  ['C', 'SmartThings Pro · b.IoT · VXT 통합 운영'],
  ['B', '로비 안내 로봇 · Digital Twin · BLE 위치 · 안면인식 출입'],
  ['B', '컨셉 구상과 공간 구성 지원'],
];

/** 저장된 정의서 v1(키맨 3 · 요구 12) */
export async function seedRequirement(req: APIRequestContext): Promise<{ id: string; project_id: string | null }> {
  const rq = await api(req, 'requirements', 'POST', '/requirements', { form: { project_name: PROJECT, customer_name: CUSTOMER, author_note: '설계 단계 삼성 스펙인이 목표.' } });
  const ids: Record<string, string> = {};
  const ops: Array<Record<string, unknown>> = [];
  for (const [k, name] of KEYMEN) { ids[k] = `km_${ulid()}`; ops.push({ op: 'add_keyman', keyman_id: ids[k], name }); }
  for (const [k, text] of ITEMS) ops.push({ op: 'add_item', keyman_id: ids[k], text });
  ops.push({ op: 'set_weights', weights: Object.fromEntries(KEYMEN.map(([k, , w]) => [ids[k], w])) });
  await api(req, 'requirements', 'PATCH', `/requirements/${rq.id}/draft`, { ops });
  const s = await api(req, 'requirements', 'POST', `/requirements/${rq.id}/save`, {});
  return { id: rq.id, project_id: s.requirement?.project_id ?? null };
}

export async function getSb(req: APIRequestContext, id: string) { return api(req, 'storyboard', 'GET', `/storyboards/${id}`); }
const sbIdle = (s: any) => !s.active_job;

/** 정의서로 Storyboard → 기획 방향(질의 건너뜀) → 목차 → 저장 */
export async function seedStoryboard(req: APIRequestContext, rqId: string, stage: 'source' | 'outline' | 'saved' = 'saved'): Promise<string> {
  const sb = await api(req, 'storyboard', 'POST', '/storyboards', { requirement_id: rqId });
  await until(() => getSb(req, sb.id), (s) => s.settings?.ready && sbIdle(s), 90_000, 'Storyboard 준비');
  if (stage === 'source') return sb.id;
  await advanceStoryboard(req, sb.id, stage);
  return sb.id;
}
export async function advanceStoryboard(req: APIRequestContext, sbId: string, stage: 'outline' | 'saved') {
  await until(() => getSb(req, sbId), (s) => s.settings?.ready && sbIdle(s), 90_000, 'Storyboard 준비');
  await api(req, 'storyboard', 'POST', `/storyboards/${sbId}/direction`, { skip_planning: true });
  await until(() => getSb(req, sbId), (s) => s.direction?.ready && sbIdle(s), 90_000, '기획 방향');
  await api(req, 'storyboard', 'POST', `/storyboards/${sbId}/outline`, {});
  await until(() => getSb(req, sbId), (s) => s.outline?.ready && sbIdle(s), 150_000, '목차');
  if (stage === 'saved') await api(req, 'storyboard', 'POST', `/storyboards/${sbId}/save`, {});
}

/** 정의서(+ Storyboard)로 MI 분석 끝까지 */
export async function seedMi(req: APIRequestContext, rqId: string, sbId?: string): Promise<string> {
  const a = await api(req, 'mi', 'POST', '/analyses', { links: { requirements_id: rqId } });
  if (sbId) {
    const sb = await getSb(req, sbId);
    await api(req, 'mi', 'POST', `/analyses/${a.id}/imports/storyboard`, {
      storyboard_id: sbId, title: sb.title, customer_name: sb.customer_name,
      requirements: (sb.trace?.items ?? []).map((i: any) => ({ text: i.text, origin: 'storyboard' })),
      key_messages: (sb.direction?.key_messages ?? []).map((k: any) => k.text),
    });
  }
  await api(req, 'mi', 'POST', `/analyses/${a.id}/design`);
  const d = await until(() => api(req, 'mi', 'GET', `/analyses/${a.id}/design`), (x: any) => ['done', 'ask', 'failed'].includes(x.status), 90_000, 'MI 설계');
  expect(d.status, 'MI 설계').toBe('done');
  await api(req, 'mi', 'POST', `/analyses/${a.id}/runs`, { mode: 'full' });
  await until(() => api(req, 'mi', 'GET', `/analyses/${a.id}`), (x: any) => ['done', 'upd'].includes(x.status), 180_000, 'MI 분석');
  return a.id;
}

/** 정의서로 경쟁사 분석 끝까지 */
export async function seedCa(req: APIRequestContext, rqId: string): Promise<string> {
  const a = await api(req, 'competitor', 'POST', '/analyses', { input_mode: 'requirements', requirements_id: rqId });
  await api(req, 'competitor', 'POST', `/analyses/${a.id}/find`);
  const c = await until(() => api(req, 'competitor', 'GET', `/analyses/${a.id}`), (x: any) => ['confirming', 'ask', 'failed'].includes(x.status), 90_000, '경쟁사 찾기');
  expect(c.status, '경쟁사 찾기').toBe('confirming');
  // 추천(자동 켬)이 없으면 사람이 CA2 에서 켜듯 확인 필요 후보 둘을 켠다
  const cands = await api(req, 'competitor', 'GET', `/analyses/${a.id}/candidates`);
  if (!cands.items.some((x: any) => x.on)) {
    for (const x of cands.items.filter((y: any) => !y.removed).slice(0, 2)) await api(req, 'competitor', 'PATCH', `/analyses/${a.id}/candidates/${x.id}`, { on: true });
  }
  await api(req, 'competitor', 'POST', `/analyses/${a.id}/runs`, { mode: 'full' });
  await until(() => api(req, 'competitor', 'GET', `/analyses/${a.id}`), (x: any) => ['done', 'upd', 'stopped'].includes(x.status), 180_000, '경쟁사 분석');
  return a.id;
}

/** Storyboard · MI 로 VP 생성까지 */
export async function seedVp(req: APIRequestContext, sbId: string, miId?: string): Promise<string> {
  const refs = [{ kind: 'storyboard', ref_id: sbId }, ...(miId ? [{ kind: 'mi', ref_id: miId }] : [])];
  const d = await api(req, 'vp', 'POST', '/vps', { start: 'storyboard', source_refs: refs, auto_answer: true });
  const c = await api(req, 'vp', 'POST', `/vps/${d.id}/materials:collect`, {});
  const j = await waitJob(req, c.job_id);
  expect(j.status, 'VP 재료').toBe('succeeded');
  const g = await api(req, 'vp', 'POST', `/vps/${d.id}/generate`, {});
  const j2 = await waitJob(req, g.job_id);
  expect(j2.status, 'VP 생성').toBe('succeeded');
  return d.id;
}

export const QM55C = 'LH55QMCEBGCXKR';
export const QB55C = 'LH55QBCEBGCXKR';

/** 정의서에 연결한 Spec 비교 시트(값 확인은 [확정 필요]로) */
export async function seedSpec(req: APIRequestContext, rq: { id: string; project_id: string | null }): Promise<string> {
  const s = await api(req, 'spec', 'POST', '/sheets', { start: 'model', products: [QM55C, QB55C], project_id: rq.project_id, rq_ref: { rq_id: rq.id, version: 1 } });
  await api(req, 'spec', 'PATCH', `/sheets/${s.id}`, { step: 2 });
  await api(req, 'spec', 'POST', `/sheets/${s.id}/generate`, { mode: 'full' });
  const idle = (x: any) => !x.active_job || !['queued', 'running'].includes(x.active_job.status);
  await until(() => api(req, 'spec', 'GET', `/sheets/${s.id}`), idle, 90_000, 'Spec 생성');
  await api(req, 'spec', 'POST', `/sheets/${s.id}/checks:defer-all`);
  await api(req, 'spec', 'POST', `/sheets/${s.id}/checks:apply`, { answers: [] });
  await until(() => api(req, 'spec', 'GET', `/sheets/${s.id}`), (x: any) => idle(x) && x.ui_status === 'done', 90_000, 'Spec 완료');
  return s.id;
}

/** 제품 참조를 넣은 이미지 작업 → 시안 2장 → 첫 장 저장 */
export async function seedImage(req: APIRequestContext, projectId: string | null): Promise<{ work: string; image: string; version: string }> {
  const w = await api(req, 'image', 'POST', '/works', { kind: 'space', description: '오피스 로비에 대형 사이니지가 있는 장면, 낮 시간', project_id: projectId });
  await api(req, 'image', 'POST', `/works/${w.id}:prefill`);
  await api(req, 'image', 'POST', `/works/${w.id}/products`, { refs: [`kb:model:${QM55C}`], qty: 2 });
  const acc = await api(req, 'image', 'POST', `/works/${w.id}/runs`, { kind: 'initial', count: 2, notify: false });
  const run = await until(() => api(req, 'image', 'GET', `/runs/${acc.run_id}`), (r: any) => ['succeeded', 'failed', 'canceled', 'awaiting_input'].includes(r.status), 150_000, '이미지 생성');
  expect(run.status, '이미지 생성').toBe('succeeded');
  const image = run.shots[0].image_id ?? run.shots[0].id;
  await api(req, 'image', 'POST', `/images/${image}:save`, {});
  const img = await api(req, 'image', 'GET', `/images/${image}`);
  return { work: w.id, image, version: img.current_version_id };
}

export const BE_DESC = '용산 오피스 1층 로비. 약 120평, 층고 4.5m, 정면이 전면 유리창이라 낮에는 밝고 저녁엔 외부에서 내부가 잘 보임. 중앙에 기둥 2개.';

/** 공간 → 제품(실제 KB) → 가구 → 배치 → 주 컷 → 존 */
export async function seedBirdseye(req: APIRequestContext, title: string, projectId: string | null): Promise<string> {
  const b = await api(req, 'birdseye', 'POST', '/birdseyes', { title, description: BE_DESC, project_id: projectId });
  const a = await api(req, 'birdseye', 'POST', `/birdseyes/${b.id}/space:analyze`);
  expect((await waitJob(req, a.job_id)).status, '공간 분석').toBe('succeeded');
  const items = [];
  for (const q of ['OH55', 'Flip Pro', 'The Wall']) {
    const s = await api(req, 'birdseye', 'GET', `/product-search?q=${encodeURIComponent(q)}&limit=1`);
    items.push({ ref: s.items[0].ref, family_id: s.items[0].family_id, model_code: s.items[0].model_code });
  }
  await api(req, 'birdseye', 'PUT', `/birdseyes/${b.id}/products`, { items });
  const f = await api(req, 'birdseye', 'POST', `/birdseyes/${b.id}/furniture:recommend`, { exclude: [] });
  expect((await waitJob(req, f.job_id)).status, '가구 추천').toBe('succeeded');
  const g = await api(req, 'birdseye', 'POST', `/birdseyes/${b.id}/layout:generate`, { none: false });
  expect((await waitJob(req, g.job_id)).status, '배치').toBe('succeeded');
  const c = await api(req, 'birdseye', 'POST', `/birdseyes/${b.id}/cuts`, { views: [{ preset: 'aerial45' }], lights: ['day'], primary: true, auto_extra: false, before: false });
  expect((await waitJob(req, c.job_id, 240_000)).status, '렌더').toBe('succeeded');
  const z = await api(req, 'birdseye', 'POST', `/birdseyes/${b.id}/zones:auto`, {});
  if (z?.job_id) expect((await waitJob(req, z.job_id)).status, '존').toBe('succeeded');
  return b.id;
}

/** 조감도 존으로 시나리오 → 생성 → 장면 이미지 */
export async function seedScenario(req: APIRequestContext, beId: string, title?: string): Promise<string> {
  const o = await api(req, 'scenario', 'GET', `/birdseye-options/${beId}`);
  const acc = await api(req, 'scenario', 'POST', '/scenarios:from-birdseye', {
    birdseye_id: beId, zone_ids: o.zones.map((z: any) => z.id), axis: o.axes[0], order: o.order, keep_link: true,
  });
  const id = acc.scenario_id ?? acc.id;
  if (acc.job_id) expect((await waitJob(req, acc.job_id)).status, '시나리오 골격').toBe('succeeded');
  if (title) await api(req, 'scenario', 'PATCH', `/scenarios/${id}`, { title });
  await api(req, 'scenario', 'PUT', `/scenarios/${id}/solutions`, { items: [{ solution_id: 'magicinfo' }] });
  await api(req, 'scenario', 'POST', `/scenarios/${id}:route-generate`);
  const g = await api(req, 'scenario', 'POST', `/scenarios/${id}/generate`, { scope: 'all' });
  expect((await waitJob(req, g.job_id)).status, '시나리오 생성').toBe('succeeded');
  const im = await api(req, 'scenario', 'POST', `/scenarios/${id}/images:generate-missing`, {});
  if (im?.job_id) expect((await waitJob(req, im.job_id, 300_000)).status, '장면 이미지').toBe('succeeded');
  return id;
}

/** 유형(표준) · 시트 구성 · 업종까지 정한 제안서 */
export async function composeProposal(req: APIRequestContext, pid: string, type: 'standard' | 'quickwin' | 'solution' = 'standard') {
  await api(req, 'proposal', 'PUT', `/proposals/${pid}/type`, { type });
  await api(req, 'proposal', 'POST', `/proposals/${pid}/composition:start`);
  await api(req, 'proposal', 'PUT', `/proposals/${pid}/industry`, { decided: true }).catch(() => null);
}

// ── 정리(지울 수 있는 것만 — requirements · storyboard 는 지우는 API 가 없다) ──

export async function cleanup(req: APIRequestContext, ids: Partial<Record<'pr' | 'mi' | 'ca' | 'vp' | 'sp' | 'img' | 'be' | 'sc', Array<string | null | undefined>>>) {
  const del = async (svc: Svc, method: string, p: string) => { await req.fetch(`/api/${svc}/v1${p}`, { method }).catch(() => null); };
  for (const id of ids.pr ?? []) if (id) await del('proposal', 'DELETE', `/proposals/${id}`);
  for (const id of ids.sc ?? []) if (id) await del('scenario', 'DELETE', `/scenarios/${id}`);
  for (const id of ids.be ?? []) if (id) await del('birdseye', 'DELETE', `/birdseyes/${id}`);
  for (const id of ids.img ?? []) if (id) await del('image', 'DELETE', `/works/${id}`);
  for (const id of ids.mi ?? []) if (id) await del('mi', 'DELETE', `/analyses/${id}`);
  for (const id of ids.ca ?? []) if (id) await del('competitor', 'DELETE', `/analyses/${id}`);
  for (const id of ids.vp ?? []) if (id) await del('vp', 'POST', `/vps/${id}:archive`);
  for (const id of ids.sp ?? []) if (id) await del('spec', 'POST', `/sheets/${id}:archive`);
}
