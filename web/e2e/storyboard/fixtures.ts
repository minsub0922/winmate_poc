/**
 * Storyboard e2e 도우미 — 실제 백엔드(게이트웨이 /api)에 정의서를 만들고(requirements API) 스토리보드 상태를 기다린다.
 * 공유 개발 사용자 · 데이터라 목록이 비어 있다고 가정하지 않는다(만든 것만 id 로 찾는다).
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { expect, type APIRequestContext, type Page } from '@playwright/test';

const here = path.dirname(fileURLToPath(import.meta.url));
export const SCREENS = path.join(here, '__screens__');

export async function shot(page: Page, name: string) {
  fs.mkdirSync(SCREENS, { recursive: true });
  await page.waitForTimeout(150);
  await page.screenshot({ path: path.join(SCREENS, `${name}.png`) });
}

/** 이 e2e 는 실제 requirements · storyboard 서비스가 떠 있어야 한다(게이트웨이 경유). 없으면 이유를 남기고 건너뛴다. */
export async function backendDown(request: APIRequestContext): Promise<string | null> {
  for (const svc of ['storyboard', 'requirements']) {
    const r = await request.get(`/api/${svc}/v1/info`).catch(() => null);
    if (!r || !r.ok()) return `${svc} 서비스가 꺼져 있어요(make dev-bg SERVICE=${svc})`;
  }
  return null;
}

const CROCK = '0123456789ABCDEFGHJKMNPQRSTVWXYZ';
function ulid(): string {
  let s = '01J';
  for (let i = 0; i < 23; i++) s += CROCK[Math.floor(Math.random() * 32)];
  return s;
}

export const AUTHOR_NOTE = '설계 단계 삼성 스펙인이 목표. 성수 Tech Ready 오피스 운영 성과를 비교 기준으로 쓰고 싶어 함.';
const KEYMEN: Array<[string, string, number]> = [['A', '대표이사', 50], ['B', '공간컨텐츠실장', 30], ['C', '개발사업팀장', 20]];
export const ITEMS: Array<[string, string]> = [
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
/** [질문, 짧은 이름, 대상 요구(글 일부)] — 대상이 있는 질문은 `이미 고객 확인 중` 항목이 된다(SB4U `확인 필요로 유지`) */
const QUESTIONS: Array<[string, string, string | null]> = [
  ["'업무환경 플랫폼'에 어떤 서비스가 들어가나요?", '업무환경 플랫폼 범위', '업무환경 플랫폼'],
  ['유사 건물 에너지 사용량 자료를 받을 수 있을까요?', '유사 건물 사용량 자료', '에너지 사용량'],
  ['최종 의사결정자는 누구인가요?', '최종 의사결정자', null],
  ['용적률 인센티브 조건을 공유해 주실 수 있을까요?', '용적률 인센티브 조건', null],
];

/** 저장된 정의서(v1) 하나 — 키맨 3 · 요구 12 · 열린 고객 질문 4 */
export async function seedRequirement(request: APIRequestContext, opts: { customer?: string; project?: string; questions?: number } = {}) {
  const customer = opts.customer ?? 'E 자산운용';
  const project = opts.project ?? '용산 업무시설 재개발 AI Ready 오피스';
  const r = await request.post('/api/requirements/v1/requirements', { data: { form: { project_name: project, customer_name: customer, author_note: AUTHOR_NOTE } } });
  expect(r.status(), await r.text()).toBe(201);
  const rq = (await r.json()) as { id: string };
  const ids: Record<string, string> = {};
  const ops: Array<Record<string, unknown>> = [];
  for (const [k, name] of KEYMEN) {
    ids[k] = `km_${ulid()}`;
    ops.push({ op: 'add_keyman', keyman_id: ids[k], name });
  }
  for (const [k, text] of ITEMS) ops.push({ op: 'add_item', keyman_id: ids[k], text });
  ops.push({ op: 'set_weights', weights: Object.fromEntries(KEYMEN.map(([k, , w]) => [ids[k], w])) });
  const d = await request.patch(`/api/requirements/v1/requirements/${rq.id}/draft`, { data: { ops } });
  expect(d.ok(), await d.text()).toBeTruthy();
  const full = await (await request.get(`/api/requirements/v1/requirements/${rq.id}`)).json();
  const items: Array<{ id: string; text: string }> = (full.form?.keymen ?? []).flatMap((k: { items?: Array<{ id: string; text: string }> }) => k.items ?? []);
  for (const [text, short, about] of QUESTIONS.slice(0, opts.questions ?? 4)) {
    const item = about ? items.find((i) => i.text.includes(about)) : undefined;
    const q = await request.post(`/api/requirements/v1/requirements/${rq.id}/customer-questions`, {
      data: { text, short_label: short, ...(item ? { target: { kind: 'item', id: item.id } } : {}) },
    });
    expect(q.ok(), await q.text()).toBeTruthy();
  }
  const s = await request.post(`/api/requirements/v1/requirements/${rq.id}/save`, { data: {} });
  expect([200, 201]).toContain(s.status());
  return rq.id;
}

/** 정의서 새 버전(항목 하나 고치기 → 저장) */
export async function saveNewRequirementVersion(request: APIRequestContext, rqId: string, note: string) {
  const r = await request.get(`/api/requirements/v1/requirements/${rqId}/versions/1`);
  const v1 = await r.json();
  const item = (v1.snapshot.items_flat as Array<{ id: string; text: string }>).find((i) => i.text.includes('업무환경 플랫폼'))!;
  const d = await request.patch(`/api/requirements/v1/requirements/${rqId}/draft`, {
    data: { ops: [{ op: 'update_item', item_id: item.id, text: '오피스를 업무환경 플랫폼으로 — 입주사 앱 · 공용 공간 예약 · 방문객 안내' }] },
  });
  expect(d.ok(), await d.text()).toBeTruthy();
  const s = await request.post(`/api/requirements/v1/requirements/${rqId}/save`, { data: { note } });
  expect([200, 201]).toContain(s.status());
  return (await s.json()).version as number;
}

export type Sb = Record<string, any>;

export async function getSb(request: APIRequestContext, sbId: string): Promise<Sb> {
  const r = await request.get(`/api/storyboard/v1/storyboards/${sbId}`);
  expect(r.ok()).toBeTruthy();
  return r.json();
}

/** 조건이 맞을 때까지 스토리보드를 다시 읽는다 */
export async function waitSb(request: APIRequestContext, sbId: string, cond: (sb: Sb) => boolean, timeout = 30_000): Promise<Sb> {
  let last: Sb = {};
  await expect.poll(async () => { last = await getSb(request, sbId); return cond(last); }, { timeout, intervals: [300, 500, 800] }).toBeTruthy();
  return last;
}

export const idle = (sb: Sb) => !sb.active_job;

/** API 로 스토리보드를 만들어 원하는 단계까지(목록 시험용) */
export async function storyboardAt(request: APIRequestContext, rqId: string, stage: 'direction' | 'outline' | 'saved'): Promise<Sb> {
  const c = await request.post('/api/storyboard/v1/storyboards', { data: { requirement_id: rqId } });
  expect([200, 201]).toContain(c.status());
  const id = (await c.json()).id as string;
  await waitSb(request, id, (s) => s.settings?.ready && idle(s));
  await request.post(`/api/storyboard/v1/storyboards/${id}/direction`, { data: { skip_planning: true } });
  let sb = await waitSb(request, id, (s) => s.direction?.ready && idle(s));
  if (stage === 'direction') return sb;
  await request.post(`/api/storyboard/v1/storyboards/${id}/outline`, { data: {} });
  sb = await waitSb(request, id, (s) => s.outline?.ready && idle(s));
  if (stage === 'outline') return sb;
  await request.post(`/api/storyboard/v1/storyboards/${id}/save`, { data: {} });
  return getSb(request, id);
}

/**
 * 내려받은 파일 이름. 설치된 Chromium 판이 Playwright 기대 판과 달라 `suggestedFilename()` 이 `download` 로 오는 일이 있어
 * 그때는 같은 주소의 Content-Disposition(`filename*=UTF-8''…`)에서 읽는다.
 */
export async function downloadName(request: APIRequestContext, d: { suggestedFilename(): string; url(): string }): Promise<string> {
  const s = d.suggestedFilename();
  if (s && s !== 'download') return s;
  const res = await request.get(d.url());
  const cd = res.headers()['content-disposition'] ?? '';
  const star = cd.match(/filename\*=UTF-8''([^;]+)/i);
  if (star) return decodeURIComponent(star[1]);
  const plain = cd.match(/filename="([^"]+)"/i);
  return plain ? plain[1] : s;
}
