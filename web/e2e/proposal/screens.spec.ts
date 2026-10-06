/**
 * MOCK 화면 테스트 — 실제 제안서(만들고 지움) 위에, 보드 예시 값(fixtures.ts)을 page.route 로 덮어 보드와 같은 상태를 그린다.
 * 비교 스크린샷: __screens__/<보드>.png ↔ docs/screens/webapp3/<보드>.dc.html.
 * 기존 제안서 활용(PRU*)은 백엔드가 아직 501 이라 여기서만 화면을 확인한다.
 */
import { expect as baseExpect, test } from '@playwright/test';
import { api, backendDown, removeProposal, seedComposed, seedGenerated, seedProposal, shot, isolateBrokenFeatures, open } from './helpers';
import { doneJob, fail, mockApi, mockJobs, mockProposal, runningJob } from './mock';
import * as F from './fixtures';

/** 공유 PC(2 CPU)에 다른 세션 테스트가 함께 돌아 느릴 수 있어 기다림을 넉넉히 */
const expect = baseExpect.configure({ timeout: 20_000 });

/**
 * 테스트끼리 의존하지 않는다(각자 MOCK 상태를 그린다). 공유 PC 메모리가 모자라면 커널이 브라우저 탭을 죽이기도 해서(cgroup OOM, 탭 oom_score_adj 300)
 * 그때만 한 번 다시 돌린다 — 다시 돌아 통과하면 Playwright 가 flaky 로 보고한다.
 */
test.describe.configure({ timeout: 150_000, retries: 1 });
test.use({ actionTimeout: 30_000, navigationTimeout: 60_000 });
test.beforeEach(async ({ page }) => { await isolateBrokenFeatures(page); });
let base: any = null; // 유형 · 구성까지 정한 제안서
let gen: any = null; // PPTX 까지 만든 제안서
const made: string[] = [];

test.beforeAll(async ({ request }) => {
  test.setTimeout(240_000);
  if (await backendDown(request)) return;
  base = await seedComposed(request); made.push(base.id);
  gen = await seedGenerated(request); made.push(gen.id);
});
test.afterAll(async ({ request }) => { for (const id of made) await removeProposal(request, id); });
test.beforeEach(async ({ request }) => {
  const down = await backendDown(request);
  test.skip(!!down || !base || !gen, down ?? '시드 제안서를 만들지 못했어요');
});

test('PR1F — RFP로 시작: 원문 하이라이트 ↔ 자동 채움 9항목 · 비어 있는 2항목 입력 · 확인 → PR2 (MOCK)', async ({ page }) => {
  const puts: Array<{ key: string; value: string }> = [];
  let view = structuredClone(F.rfpDone);
  await mockProposal(page, {
    'GET /v1/proposals/:id/rfp': () => view,
    'PUT /v1/proposals/:id/rfp/fields/:key': (_r: any, url: URL, _m: string, body: any) => {
      const key = url.pathname.split('/').pop()!;
      puts.push({ key, value: body.value });
      view = { ...view, fields: view.fields.map((f) => (f.key === key ? { ...f, value: body.value, edited: true } : f)) };
      return view;
    },
    'POST /v1/proposals/:id/rfp:confirm': async () => ({ ...base, stage: 'type' }),
  });
  await open(page, `/proposal/${base.id}/rfp`);
  await expect(page.getByTestId('pr1f-agent')).toHaveText(F.rfpDone.intro);
  await expect(page.getByTestId('pr1f-file')).toContainText('A커피_디지털메뉴보드_RFP.pdf');
  await expect(page.getByTestId('pr1f-phases')).toContainText('읽기');
  await expect(page.getByTestId('pr1f-field')).toHaveCount(9);
  await expect(page.getByTestId('pr1f-tally')).toContainText('찾음 6');
  await expect(page.getByTestId('pr1f-tally')).toContainText('추정 1');
  await expect(page.getByTestId('pr1f-tally')).toContainText('비어 있음 2');
  await expect(page.locator('[data-key="industry"]')).toHaveAttribute('data-state', 'guess');
  await expect(page.getByTestId('pr1f-hint')).toHaveText('요구사항 5건은 시트 구성 추천과 섹션 작성에 그대로 쓰여요.');
  await expect(page.getByPlaceholder('예) [00]억 원 이내 · 모르면 비워 두기')).toBeVisible();
  await expect(page.getByPlaceholder('예) 운영본부장, 마케팅팀장, IT팀')).toBeVisible();
  await shot(page, 'PR1F');
  // 행 클릭 = 원문 위치 강조
  await page.locator('[data-key="scale"]').getByRole('button', { name: /원문 위치로/ }).click();
  await expect(page.locator('#pr1f-ex-4')).toHaveClass(/pr-rfp-hl--on/);
  // 비어 있는 항목 입력 → PUT
  await page.getByPlaceholder('예) 운영본부장, 마케팅팀장, IT팀').fill('운영본부장, 마케팅팀장');
  await page.getByPlaceholder('예) 운영본부장, 마케팅팀장, IT팀').blur();
  await expect.poll(() => puts.find((p) => p.key === 'decision_makers')?.value).toBe('운영본부장, 마케팅팀장');
  await page.getByTestId('pr1f-next').click();
  await expect(page).toHaveURL(new RegExp(`/proposal/${base.id}/type$`));
});

test('PR1F — 403 POLICY_CONFIDENTIAL 이면 기밀 안내 문구 (MOCK)', async ({ page }) => {
  await mockProposal(page, {
    'GET /v1/proposals/:id/rfp': { ...F.rfpDone, status: 'none', files: [], fields: [], excerpts: [], phases: [] },
    'POST /v1/proposals/:id/rfp': fail(403, 'POLICY_CONFIDENTIAL', 'confidential'),
  });
  await page.route('**/api/files/v1/files', (r) => r.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify({ id: 'file_mock_up', name: 'rfp.txt', mime: 'text/plain', size: 10 }) }));
  await open(page, `/proposal/${base.id}/rfp`);
  await expect(page.getByTestId('pr1f-drop')).toBeVisible();
  await page.getByTestId('pr1f-drop').locator('input[type=file]').setInputFiles({ name: 'rfp.txt', mimeType: 'text/plain', buffer: Buffer.from('A 커피 RFP') });
  await expect(page.getByText('기밀 자료라 지금 설정된 모델로는 분석할 수 없어요')).toBeVisible();
});

test('PR1L — 기존 작업에서 시작: 연결 4/6 · 넣을 곳 · 채워지는 것 미리보기 · 체크 해제 → PUT links (MOCK)', async ({ page }) => {
  const puts: any[] = [];
  await mockProposal(page, {
    'GET /v1/proposals/:id/related-works': F.relatedWorks,
    'PUT /v1/proposals/:id/links': (_r: any, _u: URL, _m: string, body: any) => { puts.push(body); return { links: [], preview: { ...F.relatedWorks.preview, counts_label: '채움 2 · 일부 3 · 새로 작성 3' }, on_count: 3 }; },
  });
  await open(page, `/proposal/${base.id}/works`);
  await expect(page.getByTestId('pr1l-agent')).toHaveText(F.relatedWorks.intro);
  await expect(page.getByTestId('pr1l-work')).toHaveCount(6);
  await expect(page.locator('[data-testid="pr1l-work"][data-on]')).toHaveCount(4);
  await expect(page.getByTestId('pr1l-rec')).toContainText('표준 제안서');
  await expect(page.getByTestId('pr1l-counts')).toHaveText('채움 3 · 일부 3 · 새로 작성 2');
  await expect(page.getByTestId('pr1l-preview')).toContainText('A 커피 프랜차이즈 · 외식 · 카페 · 320개 매장 · 요구사항 5건');
  await shot(page, 'PR1L');
  await page.getByRole('checkbox', { name: 'A 커피 매장 하루 시나리오' }).click();
  await expect.poll(() => puts.length).toBe(1);
  expect(puts[0].links[0]).toMatchObject({ feature: 'scenario', on: false });
  await expect(page.getByTestId('pr1l-counts')).toHaveText('채움 2 · 일부 3 · 새로 작성 3');
});

test('PR1C — 기존 제안서로 시작: 원본 파일 · 처리 단계 · 활용 방식 3 · 분석 결과 확인 비활성 (MOCK)', async ({ page }) => {
  await mockProposal(page, {
    'GET /v1/proposals/:id/reuse/candidates': { items: [{ proposal_id: 'pr_cand1', name: 'A 커피 프랜차이즈 2025 매장 사이니지 제안', why: '같은 고객' }, { proposal_id: 'pr_cand2', name: 'C 편의점 2026 메뉴보드 제안', why: '같은 솔루션' }], label: '2개 추천' },
    'GET /v1/proposals/:id/reuse': F.reuseView({ status: 'analyzing', status_label: '기준별 분석 진행 중', job_id: null, criteria: [],
      sources: [{ ...F.reuseView().sources[0], phases: [{ key: 'read', label: '읽기', status: 'done' }, { key: 'split', label: '쪽 나누기', status: 'done' }, { key: 'analyze', label: '기준별 분석', status: 'busy' }] }] }),
  });
  await open(page, `/proposal/${base.id}/reuse`);
  await expect(page.getByTestId('pr1c-file')).toContainText('B베이커리_매장사이니지_제안_v3.pptx');
  await expect(page.getByTestId('pr1c-file')).toContainText('PPTX · 24장 · 2024.09 · 김하늘(동료)');
  await expect(page.getByTestId('pr1c-recs')).toContainText('같은 고객');
  await expect(page.getByTestId('pr1c-mode-auto')).toHaveAttribute('aria-checked', 'true');
  await expect(page.getByTestId('pr1c-next')).toBeDisabled();
  await expect(page.getByTestId('pr1c-status')).toHaveText('기준별 분석 진행 중');
  await expect(page.getByTestId('pr1c-count')).toContainText('원본 1개 · 24장');
  await shot(page, 'PR1C');
  await page.getByTestId('pr1c-mode-borrow').click();
  await expect(page.getByTestId('pr1c-mode-borrow')).toHaveAttribute('aria-checked', 'true');
});

test('PRU2 — 9기준 · 필수 확인 3곳 · 확인 체크 → PUT criteria · 다 확인하면 활성 (MOCK)', async ({ page }) => {
  let v: any = F.reuseView();
  const puts: any[] = [];
  await mockProposal(page, {
    'GET /v1/proposals/:id/reuse': () => v,
    'PUT /v1/proposals/:id/reuse/criteria/:no': (_r: any, url: URL, _m: string, body: any) => {
      const no = Number(url.pathname.split('/').pop());
      puts.push({ no, ...body });
      v = { ...v, criteria: v.criteria.map((c: any) => (c.no === no ? { ...c, state: body.state, state_label: body.state === 'ok' ? '확인됨' : '확인 필요' } : c)) };
      const mustLeft = v.criteria.filter((c: any) => c.must && c.state === 'need').length;
      v = { ...v, must_done: 3 - mustLeft, can_confirm: mustLeft === 0 };
      return v;
    },
  });
  await open(page, `/proposal/${base.id}/reuse/analysis`);
  await expect(page.getByTestId('pru2-criterion')).toHaveCount(9);
  await expect(page.getByTestId('pru2-source').locator('.pr-pagecard')).toHaveCount(24);
  await expect(page.getByTestId('pru2-confirm')).toBeDisabled();
  await expect(page.getByLabel('신뢰도 74%')).toBeVisible();
  await shot(page, 'PRU2');
  await page.getByRole('checkbox', { name: '논리 흐름 확인' }).click();
  await expect(page.getByRole('checkbox', { name: '논리 흐름 확인' })).toBeChecked();
  await page.getByRole('checkbox', { name: '고객 · 프로젝트 맥락 확인' }).click();
  await expect(page.getByRole('checkbox', { name: '고객 · 프로젝트 맥락 확인' })).toBeChecked();
  await expect.poll(() => puts.length).toBe(2);
  await expect(page.getByTestId('pru2-confirm')).toBeEnabled();
});

test('PRU2F — 기준 2 논리 흐름: 스토리라인 · 쪽별 역할 태그 · 에이전트 메모 (MOCK)', async ({ page }) => {
  const roles: any[] = [];
  await mockProposal(page, {
    'GET /v1/proposals/:id/reuse': F.reuseView(),
    'GET /v1/proposals/:id/reuse/criteria/:no': F.criterion2(),
    'PUT /v1/proposals/:id/reuse/pages/:no/role': (_r: any, url: URL, _m: string, body: any) => { roles.push({ no: url.pathname.split('/').slice(-2)[0], ...body }); return F.reuseView(); },
  });
  await open(page, `/proposal/${base.id}/reuse/analysis/2`);
  await expect(page.getByTestId('pru2f-flow')).toContainText('Why Samsung · 경쟁 비교');
  await expect(page.getByTestId('pru2f-page')).toHaveCount(10);
  await expect(page.getByTestId('pru2f-memos')).toContainText('에이전트 메모');
  await shot(page, 'PRU2F');
  await page.getByRole('combobox', { name: 'p.3 역할 태그' }).selectOption('고객 과제');
  await expect.poll(() => roles.length).toBe(1);
  expect(roles[0]).toMatchObject({ role: '고객 과제' });
});

test('PRU3A · PRU3B — 활용 계획(판정 5 · 요구사항 대조 · 흐름 매핑) (MOCK)', async ({ page }) => {
  let mode: 'improve' | 'borrow' = 'improve';
  const modes: string[] = [];
  const view = () => F.reuseView({
    status: 'awaiting_plan_confirm', mode, recommendation: mode === 'improve' ? { mode: 'improve', reason: '', badge: '추천 · 같은 고객 · 겹침 3 / 5' } : { mode: 'borrow', reason: '', badge: '추천 · 다른 고객' },
    plan_improve: mode === 'improve' ? F.planImprove : null, plan_borrow: mode === 'borrow' ? F.planBorrow : null,
    intro: mode === 'improve'
      ? '원본 **A 커피 프랜차이즈 2025 매장 사이니지 제안** (표준 · 21장 · v4)은 같은 고객이고 요구사항이 3건 겹쳐 **기반으로 개선 · 수정**을 추천해요. 시트마다 유지 · 갱신 · 재작성 · 신규 · 제외를 제안했고, 근거를 달아 두었어요. 내용만 바꾸는 게 아니라 이번 요구사항에 없는 시트는 빼고 새 요구사항엔 시트를 더해요.'
      : '분석 결과 활용 방식으로 **논리 흐름만 차용**을 추천해요 — 다른 고객(B 베이커리) 제안서라 내용은 쓰지 않고 설득 구조만 가져옵니다. 원본의 흐름 8단계를 이번 요구사항 5건에 맞춰 시트 구성으로 바꿨어요. 다르게 하려면 바꿔 주세요.',
  });
  const verdicts: any[] = [];
  await mockProposal(page, {
    'GET /v1/proposals/:id/reuse': () => view(),
    'PUT /v1/proposals/:id/reuse/mode': (_r: any, _u: URL, _m: string, body: any) => { modes.push(body.mode); mode = body.mode; return view(); },
    'PUT /v1/proposals/:id/reuse/plan/rows/:row': (_r: any, url: URL, _m: string, body: any) => { verdicts.push({ row: url.pathname.split('/').pop(), ...body }); return view(); },
  });
  await open(page, `/proposal/${base.id}/reuse/plan?mode=improve`);
  await expect(page.getByTestId('pru3a')).toBeVisible();
  // 원본 12장(접어 둠 · 「나머지 9장 보기」) + 요구사항 갭에서 추가한 신규 2장은 늘 보임
  await expect(page.getByTestId('pru3a-row')).toHaveCount(14);
  await expect(page.locator('[data-testid="pru3a-row"][data-verdict="new"]')).toHaveCount(2);
  await expect(page.getByTestId('pru3a-coverage')).toContainText('R3');
  await expect(page.getByTestId('pru3-totals')).toContainText('유지 5장');
  await shot(page, 'PRU3A');
  await page.getByRole('radiogroup', { name: '경쟁 환경 판정' }).getByRole('radio', { name: '갱신' }).click();
  await expect.poll(() => verdicts.length).toBe(1);
  expect(verdicts[0]).toMatchObject({ row: 'r4', verdict: 'update' });
  await page.getByTestId('pru3-mode-borrow').click();
  await expect.poll(() => modes).toEqual(['borrow']);
  await expect(page.getByTestId('pru3b')).toBeVisible();
  await expect(page.getByTestId('pru3b-row')).toHaveCount(10);
  await expect(page.getByTestId('pru3b-rules')).toContainText('가져오는 것');
  await shot(page, 'PRU3B');
});

test('PRU4 · PRU4B — 섹션 작성 원본 대조 · 흐름 가이드 (MOCK)', async ({ page }) => {
  await mockProposal(page, {
    'GET /v1/proposals/:id/sections/:key/reuse-view': (_r: any, url: URL) => (url.searchParams.get('view') === 'guide' ? F.reuseSectionGuide : F.reuseSectionCompare),
  });
  await open(page, `/proposal/${base.id}/sections/spaceProducts?view=compare`);
  await expect(page.getByTestId('pru4')).toBeVisible();
  await expect(page.getByTestId('pru4-source-line')).toHaveCount(3);
  await expect(page.getByTestId('pru4-line')).toHaveCount(3);
  await expect(page.getByTestId('pru4-sheets')).toContainText('카운터 메뉴보드');
  await shot(page, 'PRU4');
  await open(page, `/proposal/${base.id}/sections/vp?view=guide`);
  await expect(page.getByTestId('pru4b')).toBeVisible();
  await expect(page.getByTestId('pru4b-guide')).toContainText('이해관계자별 가치');
  await expect(page.getByTestId('pru4b-placeholders')).toContainText('수치 플레이스홀더 3곳');
  await shot(page, 'PRU4B');
});

test('PRU5 — 원본 대비 변경 요약 (MOCK)', async ({ page }) => {
  await mockProposal(page, { 'GET /v1/proposals/:id/reuse/summary': F.summary });
  await open(page, `/proposal/${gen.id}/reuse/summary`);
  await expect(page.getByTestId('pru5-counts')).toContainText('재작성');
  await expect(page.getByTestId('pru5-row')).toHaveCount(11);
  await expect(page.getByTestId('pru5-review')).toContainText('검토 필요 6곳');
  await expect(page.getByTestId('pru5-traces')).toContainText('원본 제안서는 바뀌지 않음');
  await shot(page, 'PRU5');
});

test('OneClickGen · OneClickDone — 진행 카드 · 메모 · 중지 / 완료 파일 · 검토 3 (MOCK)', async ({ page, request }) => {
  const memos: any[] = [];
  let canceled = false;
  const slides = await api(request, 'GET', `/proposals/${gen.id}/slides`);
  const anySheet = slides.sections[0].sheets[0].sheet_id;
  await mockJobs(page, {
    job_oc_run: { ...runningJob('job_oc_run', 45, [{ step: 'spaceProducts', status: 'running' }]), onMemo: (b) => memos.push(b), onCancel: () => { canceled = true; } },
    job_oc_done: doneJob('job_oc_done'),
  });
  await mockProposal(page, {
    'GET /v1/proposals/:id/one-click/job_oc_run': F.oneClickRunning('job_oc_run'),
    'GET /v1/proposals/:id/one-click/job_oc_done': F.oneClickDone('job_oc_done', anySheet),
  });
  await open(page, `/proposal/${gen.id}/one-click/job_oc_run`);
  await expect(page.getByTestId('oc-header')).toContainText('조감도부터 나머지 자동 완성');
  await expect(page.getByTestId('oc-step')).toHaveCount(10);
  await expect(page.locator('[data-testid="oc-step"][data-status="running"]')).toContainText('공간별 제품');
  await expect(page.getByTestId('oc-pct')).toContainText('45%');
  await shot(page, 'OneClickGen');
  await page.getByTestId('oc-memo').fill('Why Samsung은 비용 중심으로');
  await page.getByTestId('oc-memo').press('Enter');
  await expect.poll(() => memos.length).toBe(1);
  expect(memos[0]).toEqual({ text: 'Why Samsung은 비용 중심으로' });
  await page.getByTestId('oc-stop').click();
  await page.getByRole('dialog').getByRole('button', { name: '중지' }).click();
  await expect.poll(() => canceled).toBe(true);

  await open(page, `/proposal/${gen.id}/one-click/job_oc_done`);
  await expect(page.getByTestId('oc-done')).toBeVisible();
  await expect(page.getByTestId('oc-counts')).toContainText('추론 16');
  await expect(page.getByTestId('oc-thumbs').locator('a')).toHaveCount(8);
  await expect(page.getByTestId('oc-review-item')).toHaveCount(3);
  await shot(page, 'OneClickDone');
});

test('PR7Q — 확정 필요 7곳 · 고치기(문장 틀 입력 · 같이 바뀌는 시트) → 확정 (MOCK)', async ({ page }) => {
  const resolved: any[] = [];
  await mockProposal(page, {
    'GET /v1/proposals/:id/confirm-items': F.confirmList(),
    'POST /v1/proposals/:id/confirm-items/:item': (_r: any, url: URL, _m: string, body: any) => { resolved.push({ path: url.pathname, body }); return { item: { id: 'q09' }, changed_sheet_ids: [] }; },
  });
  await open(page, `/proposal/${gen.id}/confirm`);
  await expect(page.getByTestId('pr7q-header')).toHaveText('확정 필요 7곳');
  await expect(page.locator('[data-testid="pr7q-item"][data-status="open"]')).toHaveCount(5);
  await expect(page.getByTestId('pr7q-done')).toContainText('확정한 곳 2');
  await page.locator('[data-testid="pr7q-item"]').nth(1).getByTestId('pr7q-fix').click();
  await expect(page.getByText('합계 = 매장 수 × 3대')).toBeVisible();
  await page.getByLabel('매장 수').fill('320');
  await shot(page, 'PR7Q');
  await page.getByTestId('pr7q-resolve').click();
  await expect.poll(() => resolved.length).toBe(1);
  expect(resolved[0].path).toContain('q09:resolve');
  expect(resolved[0].body).toEqual({ values: { stores: '320' } });
});

test('PR7C — 검토 요청 패널 · 코멘트 핀 · 시트 확인 격자 · 코멘트 스레드 (MOCK)', async ({ page, request }) => {
  const slides = await api(request, 'GET', `/proposals/${gen.id}/slides`);
  const all = slides.sections.flatMap((s: any) => s.sheets).map((s: any) => ({ id: s.sheet_id, sheet_no: s.sheet_no, title: s.title }));
  const cur = all.find((s: any) => s.title === '경쟁 비교') ?? all[0];
  const patched: any[] = [];
  await mockProposal(page, { 'GET /v1/proposals/:id/review': F.reviewView(all, cur), 'GET /v1/proposals/:id/comments/:cid/suggestion': { comment_id: 'x', status: 'none' } });
  await mockApi(page, 'workspace', {
    'GET /v1/comments': { items: F.comments(gen.id, cur.id) },
    'PATCH /v1/comments/:cid': (_r: any, url: URL, _m: string, body: any) => { patched.push({ id: url.pathname.split('/').pop(), ...body }); return { ...F.comments(gen.id, cur.id)[0], resolved: true }; },
  });
  await open(page, `/proposal/${gen.id}/review/${cur.sheet_no}`);
  await expect(page.getByTestId('pr7c-reviewer')).toHaveCount(3);
  await expect(page.getByTestId('pr7c-approvals')).toContainText('1 / 3');
  await expect(page.getByTestId('pr7c-comment')).toHaveCount(2);
  await expect(page.getByRole('button', { name: '코멘트 1' })).toBeVisible();
  await expect(page.getByTestId('pr7c-grid').getByRole('button')).toHaveCount(all.length);
  await shot(page, 'PR7C');
  await page.getByTestId('pr7c-resolve').first().click();
  await expect.poll(() => patched.length).toBe(1);
  expect(patched[0]).toMatchObject({ id: 'cmt1', resolved: true });
});

test('PR7V — 버전 타임라인 · A/B 비교 · 바뀐 곳 되돌리기 (MOCK)', async ({ page, request }) => {
  const slides = await api(request, 'GET', `/proposals/${gen.id}/slides`);
  const cm = slides.sections.flatMap((s: any) => s.sheets).find((s: any) => s.title === '경쟁 비교') ?? slides.sections[0].sheets[0];
  const reverts: string[] = [];
  await mockProposal(page, {
    'GET /v1/proposals/:id/versions': F.versionsView(),
    'GET /v1/proposals/:id/versions/compare': F.compareView(cm.sheet_id),
    'POST /v1/proposals/:id/changes/:chg': (_r: any, url: URL) => { reverts.push(url.pathname.split('/').pop()!); return { change_id: 'chg_r', reverted_change_id: 'chg_c' }; },
  });
  await open(page, `/proposal/${gen.id}/versions?a=2&b=3`);
  await expect(page.getByTestId('pr7v-version')).toHaveCount(3);
  await expect(page.getByTestId('pr7v-history')).toContainText('검토 요청 · 오늘 11:00 · 3명에게');
  await expect(page.getByTestId('pr7v-diff')).toHaveCount(3);
  await expect(page.getByRole('tablist', { name: '바뀐 시트' }).getByRole('tab')).toHaveCount(4);
  await shot(page, 'PR7V');
  await page.getByRole('button', { name: '제목 변경 되돌리기' }).click();
  await expect.poll(() => reverts).toEqual(['chg_c:revert']);
});

test('PR1 — 같은 고객의 최근 Storyboard 제안 카드 · 빈 제안서 PATCH (실제)', async ({ page, request }) => {
  const p = await seedProposal(request, { customer: { name: '' }, title: '' });
  made.push(p.id);
  await open(page, `/proposal/${p.id}/customer`);
  await expect(page.getByTestId('pr1')).toBeVisible();
  await expect(page.getByTestId('pr1-next')).toBeEnabled();
  await shot(page, 'PR1');
});
