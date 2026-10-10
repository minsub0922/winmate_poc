/**
 * 콘텐츠 흐름 e2e 공용 도우미 — Storyboard 허브(storyboard `/v1/flows*`)에 사전 작업을 API 로 넣는다.
 * 허브의 만들기 · stage 넣기는 서비스 전용(internal) 경로라 내부 토큰 헤더로 부른다(게이트웨이 경유).
 *   import { makeStoryboard, shotTo } from '../shell/flowkit';
 *   const sb = await makeStoryboard(request, { dss: true, name: `용산 AI Ready 오피스 ${tag}` });
 * 값 모양은 docs/scenarios/11-content-flow.md §6(rq · dss). 문장은 보드 예시(webapp1 RQ1 · DS2)에서 가져왔다.
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import type { APIRequestContext, Page } from '@playwright/test';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..', '..');

export function internalHeaders(caller = 'requirements'): Record<string, string> {
  const token = fs.readFileSync(path.join(ROOT, 'data', '.internal_token'), 'utf8').trim();
  return { 'X-Internal-Token': token, 'X-Internal-Caller': caller, 'Content-Type': 'application/json' };
}

export const tag = () => Date.now().toString(36).slice(-4);

export const RQ_VALUE = {
  customer: 'E 자산운용',
  title: '용산 업무시설 재개발 AI Ready 오피스',
  target: '대표이사',
  keymen: [
    { role: '대표이사', weight: '50%', needs: ['사용자를 인식하고 반응하는 AI Ready 오피스', '최초 AI Ready 공간으로 알리기', '에너지 사용량 20% 절감 · 실측 증빙'] },
    { role: '공간컨텐츠실장', weight: '30%', needs: ['오피스를 업무환경 플랫폼으로', '예측 · 반응형 공간'] },
    { role: '개발사업팀장', weight: '20%', needs: ['AI 인프라를 설계 단계에 반영', '시공 · 운영 유지보수 부담 최소화'] },
  ],
  goals: ['최초 AI Ready 오피스', '에너지 20% 절감'],
  requirements: [
    { id: 'R1', text: '사용자를 인식하고 반응하는 AI Ready 오피스', status: 'ok', by: 'manual' },
    { id: 'R2', text: '에너지 사용량 20% 절감 · 실측 증빙', status: 'ok', by: 'manual' },
    { id: 'R3', text: '오피스를 업무환경 플랫폼으로', status: 'check', by: 'manual' },
  ],
  counts: { keymen: 3, reqs: 3, check: 1 },
};

export const DSS_VALUE = {
  industry: { value: '오피스 · 업무시설', by: 'manual', basis: null },
  spaces: [
    { name: '로비', by: 'manual', products: [
      { name: 'The Wall IAB 146"', kind: 'product', ref: null, qty: '1식', by: 'manual' },
      { name: 'Smart Signage QM55C', kind: 'product', ref: 'kb:model:mdl_LH55QMCEBGCXKR', model_code: 'LH55QMCEBGCXKR', qty: '2대', by: 'manual' },
      { name: '삼성 키오스크', kind: 'product', ref: null, qty: '1대', by: 'manual' },
    ] },
    { name: '회의실', by: 'manual', products: [
      { name: 'Flip Pro WA75D', kind: 'product', ref: null, qty: null, qtyStatus: '확인 필요', by: 'manual' },
      { name: 'Smart Signage QB55C', kind: 'product', ref: null, qty: '실당 1대', by: 'manual' },
    ] },
    { name: '주차장', by: 'manual', products: [{ name: '옥외형 사이니지 OHC55', kind: 'product', ref: null, qty: null, by: 'manual' }] },
  ],
  solutions: [
    { name: 'MagicINFO', ref: 'kb:solution:sol_magicinfo', by: 'manual', links: ['로비 Smart Signage QM55C'], why: null },
    { name: 'SmartThings Pro', ref: null, by: 'manual', links: [], why: null },
  ],
  counts: { spaces: 3, products: 6, solutions: 2 },
};

/** Storyboard 하나 — rq 는 늘, dss 는 opts.dss 일 때. 돌려주는 값: 허브 FlowDoc(id 포함) */
export async function makeStoryboard(request: APIRequestContext, opts: { name?: string; dss?: boolean } = {}) {
  const name = opts.name ?? `용산 AI Ready 오피스 ${tag()}`;
  const r = await request.post('/api/storyboard/v1/flows', {
    headers: internalHeaders('requirements'),
    data: { name, customer: RQ_VALUE.customer, target: RQ_VALUE.target,
      rq: { ref: `RQ-${tag()}`, ver: 1, value: RQ_VALUE, md: '- 고객사 E 자산운용 · 최종 제안대상 대표이사\n- 요구 3 · 확인 필요 1',
        card: { title: RQ_VALUE.title, facts: [['고객사', 'E 자산운용'], ['최종 제안대상', '대표이사'], ['요구', '3 · 확인 필요 1']], groups: [], line: '키맨 3 · 요구 3 · 확인 필요 1' } } },
  });
  if (r.status() !== 201 && r.status() !== 200) throw new Error(`flow create ${r.status()} ${await r.text()}`);
  const flow = await r.json();
  if (opts.dss) {
    const s = await request.put(`/api/storyboard/v1/flows/${flow.id}/stages/dss`, {
      headers: internalHeaders('dss'),
      data: { ref: `DSS-${tag()}`, ver: 1, value: DSS_VALUE, md: '- 업종: 오피스 · 업무시설 · 공간 3\n- 로비: The Wall IAB 146" · Smart Signage QM55C ×2 · 삼성 키오스크',
        card: { title: '용산 오피스 공간별 제품', facts: [['업종', '오피스 · 업무시설'], ['공간 · 제품', '3 · 6'], ['솔루션', 'MagicINFO · SmartThings Pro']], groups: [], line: '공간 3 · 제품 6 · 솔루션 2' } },
    });
    if (!s.ok()) throw new Error(`dss stage ${s.status()} ${await s.text()}`);
  }
  return flow as { id: string; name: string };
}

/** 화면 저장 — dir 은 e2e/<기능>/__screens__ */
export async function shotTo(page: Page, dir: string, name: string) {
  await page.waitForTimeout(300);
  await page.screenshot({ path: path.join(dir, `${name}.png`) });
}
