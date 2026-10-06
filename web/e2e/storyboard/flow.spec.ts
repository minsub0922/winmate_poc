/**
 * Storyboard 기본 흐름 e2e(02-storyboard §9.2 2–15) — 실제 백엔드(storyboard · requirements · jobs · export, 모델 mock).
 * 한 정의서로 SB1 → 기획 질의 → 기획 방향 → 메시지 → 목차 → 공간 질의 → 수정 요청 → 요구 추적 → 일정 · 저장 → 내보내기 → 버전 비교.
 * 화면 캡처: e2e/storyboard/__screens__/SB*.png (보드 docs/screens/webapp1/SB*.dc.html 과 비교).
 */
import { expect, test } from '@playwright/test';
import { backendDown, downloadName, getSb, idle, seedRequirement, shot, waitSb } from './fixtures';

// 같은 작업 트리의 다른 세션이 공용 파일을 바꾸면 Vite 가 화면을 다시 읽을 수 있어 한 번 더 시도한다(묶음 전체)
test.describe.configure({ mode: 'serial', retries: 1 });
test.setTimeout(90_000);

let rqId = '';
let sbId = '';
const sbUrl = (p = '') => `/storyboard/${sbId}${p}`;

test.beforeAll(async ({ request }) => {
  const down = await backendDown(request);
  test.skip(!!down, down ?? '');
  rqId = await seedRequirement(request);
});

test('SB1 정의서 미리 선택 · prepare 동안 스켈레톤 · 설정 요약(§9.2-2)', async ({ page, request }) => {
  // prepare 가 끝나기 전 상태를 확실히 보려고 첫 응답 몇 개는 `준비 중`으로 보여 준다(그다음은 실제 응답)
  let held = 0;
  await page.route(/\/api\/storyboard\/v1\/storyboards\/sb_[0-9A-Z]+$/, async (route) => {
    const res = await route.fetch();
    const body = await res.json();
    if (held < 2 && route.request().method() === 'GET') {
      held += 1;
      body.settings = { ...body.settings, ready: false };
      body.active_job = { job_id: 'job_e2e_hold', kind: 'sb.prepare' };
    }
    await route.fulfill({ response: res, json: body });
  });
  await page.goto(`/storyboard/new?rq=${rqId}`);
  await page.waitForURL(/\/storyboard\/sb_[0-9A-HJKMNP-TV-Z]{26}\/source$/);
  sbId = page.url().match(/(sb_[0-9A-Z]{26})/)![1];
  await expect(page.getByTestId('settings-skeleton')).toBeVisible();
  await expect(page.getByRole('button', { name: /^다음 · 기획/ })).toBeDisabled();
  await expect(page.getByText('정의서에서 읽었어요')).toHaveCount(0);
  await page.unroute(/\/api\/storyboard\/v1\/storyboards\/sb_[0-9A-Z]+$/);

  await expect(page.getByTestId('settings-summary')).toHaveText('컨셉 제안 · 고객 맞춤 제안 · 약 20장 · 한국어', { timeout: 15_000 });
  await expect(page.getByText('정의서에서 읽었어요')).toBeVisible();
  const card = page.locator('.sb-choices .sb-choice[aria-pressed="true"]');
  await expect(card).toHaveCount(1);
  await expect(card).toContainText('E 자산운용 용산 AI Ready 오피스');
  await expect(card.locator('.sb-ver')).toHaveText('v1');
  await expect(card).toContainText(/요구 12개 · 확인 필요 \d+개 · (오늘|어제) \d\d:\d\d 저장/);
  await expect(page.getByRole('button', { name: '다음 · 기획 질의 3개' })).toBeEnabled();
  await expect(page.getByRole('link', { name: /정의서가 없어요 — 요청서 · 메모부터 넣기/ })).toHaveAttribute('href', '/requirements/new?return=storyboard');
  await shot(page, 'SB1');
  const sb = await getSb(request, sbId);
  expect(sb.started).toBe(false);
});

test('SB1S 설정 바꾸기 — 약 30장 → 요약 반영 · 출처 문구 숨김(§9.2-3)', async ({ page }) => {
  await page.goto(sbUrl('/source'));
  await page.getByRole('link', { name: '바꾸기' }).click();
  await expect(page).toHaveURL(sbUrl('/settings'));
  await expect(page.locator('.sb-setting')).toHaveCount(4);
  await expect(page.getByRole('group', { name: '분량' }).getByRole('button', { name: '약 20장' })).toHaveAttribute('aria-pressed', 'true');
  await shot(page, 'SB1S');
  await page.getByRole('group', { name: '분량' }).getByRole('button', { name: '약 30장' }).click();
  await page.getByRole('button', { name: '저장' }).click();
  await expect(page).toHaveURL(sbUrl('/source'));
  await expect(page.getByTestId('settings-summary')).toContainText('약 30장');
  await expect(page.getByText('정의서에서 읽었어요')).toHaveCount(0);
  // 흐름을 보드(약 20장 · 섹션 11)대로 이어 가려고 되돌린다
  await page.getByRole('link', { name: '바꾸기' }).click();
  await page.getByRole('group', { name: '분량' }).getByRole('button', { name: '약 20장' }).click();
  await page.getByRole('button', { name: '저장' }).click();
  await expect(page.getByTestId('settings-summary')).toContainText('약 20장');
});

test('SB1Q 순서 선택 · SB1Q2 청중 · SB1Q3 꼬리 질문 → SB2(§9.2-4 · 5)', async ({ page }) => {
  await page.goto(sbUrl('/source'));
  await page.getByRole('button', { name: '다음 · 기획 질의 3개' }).click();
  await expect(page).toHaveURL(sbUrl('/planning/1'));
  await expect(page.getByText('기획 질의 1 / 3 · 결정할 것')).toBeVisible();
  const next = page.getByRole('button', { name: '다음', exact: true });
  await expect(next).toBeDisabled();
  const a = page.getByRole('button', { name: /컨셉 방향 합의/ });
  const b = page.getByRole('button', { name: /설계 반영 범위/ });
  await a.click();
  await b.click();
  await expect(a.locator('.sb-ord')).toHaveText('1');
  await expect(b.locator('.sb-ord')).toHaveText('2');
  await expect(a).toContainText('Overview 목적');
  await expect(b).toContainText('Outro 다음 단계');
  await shot(page, 'SB1Q');
  await a.click();   // 첫 것을 풀면 남은 것이 1 + Overview 목적
  await expect(b.locator('.sb-ord')).toHaveText('1');
  await expect(b).toContainText('Overview 목적');
  await b.click();
  await expect(next).toBeDisabled();
  await a.click();
  await b.click();
  await expect(next).toBeEnabled();
  await next.click();

  await expect(page).toHaveURL(sbUrl('/planning/2'));
  await expect(page.getByText('기획 질의 2 / 3 · 청중')).toBeVisible();
  await expect(page.getByRole('button', { name: /최종 의사결정자/ })).toContainText('확인 필요');
  await page.getByRole('button', { name: /공간컨텐츠실/ }).click();
  await page.getByRole('button', { name: /개발사업팀/ }).click();
  await shot(page, 'SB1Q2');
  await page.getByRole('button', { name: '다음', exact: true }).click();

  await expect(page).toHaveURL(sbUrl('/planning/3'));
  await expect(page.getByText('기획 질의 3 / 3 · 비교 기준')).toBeVisible();
  await page.getByRole('button', { name: /성수 Tech Ready 오피스/ }).click();
  const follow = page.getByRole('group', { name: '이어서 하나만' });
  await expect(follow).toBeVisible();
  const make = page.getByRole('button', { name: '기획 방향 만들기' });
  await expect(make).toBeDisabled();
  await follow.getByRole('button', { name: '고객 공개 자료 있음' }).click();
  await expect(make).toBeEnabled();
  await shot(page, 'SB1Q3');
  await make.click();

  await expect(page).toHaveURL(sbUrl('/direction'));
  const combo = page.getByTestId('dir-combo');
  await expect(combo).toBeVisible({ timeout: 20_000 });
  await expect(combo).toContainText('추천');
  await expect(combo).toContainText(/요구 12 \/ 12/);
  await expect(combo.locator('.sb-map')).toHaveCount(3);
  await expect(page.locator('[data-testid^="dir-axis-"]')).toHaveCount(3);
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('기획 방향 — 세 축을 섞어 쓰는 걸 추천해요');
  await shot(page, 'SB2');
});

test('SB2E 표현 표시 — 바꾸기 · 되돌리기 · 빼기(§9.2-6)', async ({ page }) => {
  await page.goto(sbUrl('/direction'));
  await page.getByRole('button', { name: '핵심 메시지 고치기' }).click();
  await expect(page).toHaveURL(sbUrl('/direction/messages'));
  const blocks = page.getByTestId('kmsg');
  await expect(blocks).toHaveCount(3, { timeout: 20_000 });
  const first = blocks.nth(0);
  await expect(first.locator('.sb-mark')).toHaveText('국내 최초 AI Ready 오피스');
  await expect(first.locator('.sb-flag')).toContainText("'국내 최초'는 아직 검증 전이에요 → '다음 단계의 AI Ready 오피스'로");
  const second = blocks.nth(1);
  await expect(second.locator('.sb-flag')).toContainText("'설계 단계 삼성 스펙인'은 삼성 영업목표라 고객 메시지에서 빼고 내부 메모로 옮겼어요");
  await expect(second.getByTestId('kmsg-text')).not.toContainText('스펙인');
  await shot(page, 'SB2E');
  await first.getByRole('button', { name: '바꾸기' }).click();
  await expect(first.getByTestId('kmsg-text')).toContainText('다음 단계의 AI Ready 오피스');
  await expect(first.locator('.sb-flag')).toHaveCount(0);
  await second.getByRole('button', { name: '되돌리기' }).click();
  await expect(second.getByTestId('kmsg-text')).toContainText('설계 단계 삼성 스펙인');
  await expect(second.locator('.sb-flag')).toContainText("'설계 단계 삼성 스펙인'은 삼성 영업목표예요");
  await second.getByRole('button', { name: '빼기' }).click();
  await expect(second.getByTestId('kmsg-text')).not.toContainText('스펙인');
});

test('SB3G 목차 만드는 중 → 자동으로 SB3 · 부분 보기(§9.2-7 · 8)', async ({ page, request }) => {
  await page.goto(sbUrl('/direction/messages'));
  await page.getByRole('button', { name: '저장하고 목차 만들기' }).click();
  await expect(page).toHaveURL(sbUrl('/outline'));
  const steps = page.getByTestId('gen-steps');
  await expect(page.getByRole('heading', { name: '목차와 서사를 쓰는 중이에요' })).toBeVisible();
  await expect(steps.locator('.sb-genstep')).toHaveCount(4);
  await expect(steps.locator('.sb-genstep').nth(2)).toContainText(/섹션 11개 작성 방향 쓰기/);
  await expect(steps.locator('.sb-genstep[data-state="run"]')).toContainText(/\d+ \/ 11/, { timeout: 10_000 });
  await expect(steps.locator('.sb-genstep[data-state="wait"]').first()).toContainText('대기');
  await expect(steps.locator('.sb-genstep[data-state="done"]').first()).toContainText('끝');
  await shot(page, 'SB3G');
  // 기다리지 않고 지금까지 쓴 것 보기 → SB3 부분 보기(쓰는 중 띠), 잡이 끝나면 같은 자리에서 갱신
  await page.getByRole('button', { name: '기다리지 않고 지금까지 쓴 것 보기' }).click();
  await expect(page.getByTestId('partial-band')).toBeVisible();
  await expect(page.getByTestId('groups').locator('a')).toHaveCount(5);
  await waitSb(request, sbId, (s) => s.outline?.ready && idle(s));
  await expect(page.getByTestId('partial-band')).toHaveCount(0, { timeout: 15_000 });
  await expect(page).toHaveURL(sbUrl('/outline'));
  await expect(page.locator('.sb-h1 .sb-badge')).toHaveText('v1 초안');
  await expect(page.locator('.sb-sub').first()).toHaveText(/· 섹션 11개 · 청중 공간컨텐츠실 · 개발사업팀$/);
  const groups = page.getByTestId('groups');
  for (const name of ['시작', 'Part 1', 'Part 2', 'Part 3', '마무리']) await expect(groups).toContainText(name);
  await expect(page.getByTestId('group-part2')).toContainText('작성 중');
  await expect(page.getByTestId('group-part2')).toContainText('미완 2');
  await expect(page.getByRole('button', { name: '버전' })).toBeDisabled();
  await shot(page, 'SB3');
});

test('빈 공간 채우기 — SB3 Q 배너 → SB3S 5칸 → SB3S2 · SB3P 5/5(§9.2-9)', async ({ page }) => {
  await page.goto(sbUrl('/outline'));
  await expect(page.getByTestId('q-banner')).toContainText('로비 · 라운지 시나리오가 비어 있어요');
  await page.getByRole('link', { name: '로비부터 채우기' }).click();
  await expect(page).toHaveURL(/\/spaces\/spc_[0-9A-Z]+\/q/);
  for (let k = 1; k <= 5; k++) {
    await expect(page.locator('.sb-eyebrow')).toContainText(`섹션 질의 · Part 2 로비 · ${k} / 5`, { timeout: 15_000 });
    await expect(page.locator('.sb-slotchip--now')).toHaveCount(1);
    await expect(page.locator('.sb-slotchip--done')).toHaveCount(k - 1);
    const opts = page.locator('.sb-choices .sb-choice');
    await expect(opts.first()).toBeVisible();
    if (k === 4) await shot(page, 'SB3S');
    await opts.nth(0).click();
    if (k === 4) await opts.nth(1).click();
    await page.getByRole('button', { name: '다음', exact: true }).click();
  }
  await expect(page).toHaveURL(/\/spaces\/spc_[0-9A-Z]+\/done/);
  await expect(page.getByRole('heading', { name: '로비 시나리오 5칸을 채웠어요' })).toBeVisible({ timeout: 20_000 });
  await expect(page.locator('.sb-ai').first()).toBeVisible();
  await expect(page.getByTestId('slots')).toContainText('[00]');
  const notice = page.getByTestId('added-questions');
  await expect(notice).toContainText(/고객에게 물을 것에 \d+개 더했어요 — /);
  await expect(page.getByRole('link', { name: /다음 공간 · 라운지/ })).toBeVisible();
  await shot(page, 'SB3S2');
  await notice.click();
  await expect(page).toHaveURL(`/requirements/${rqId}/questions`);
  await page.goto(sbUrl('/outline/part2'));
  await expect(page.getByTestId('space-lobby')).toContainText('5/5');
  await expect(page.getByTestId('space-lobby')).toContainText('작성자 보완');
  await shot(page, 'SB3P');
});

test('수정 요청 — SB3R → SB3R2 n줄 · 적용(§9.2-10)', async ({ page }) => {
  await page.goto(sbUrl('/outline'));
  await page.getByRole('link', { name: '수정 요청' }).click();
  await expect(page).toHaveURL(sbUrl('/revise'));
  await expect(page.getByTestId('revise-target')).toContainText('Part 1-2 Tech Ready 모델의 성과');
  const go = page.getByRole('button', { name: '다시 쓰기' });
  await expect(go).toBeDisabled();
  await page.getByLabel('어떻게 바꿀까요').fill('경영진용으로 짧게. 성과 3가지는 한 장 비교표로');
  await page.getByRole('button', { name: '비교표로' }).click();
  await expect(page.getByRole('button', { name: '비교표로' })).toHaveAttribute('aria-pressed', 'true');
  await expect(page.getByRole('group', { name: '다시 쓸 범위' }).getByRole('button', { name: 'Part 1 전체' })).toBeVisible();
  await shot(page, 'SB3R');
  await go.click();
  await expect(page).toHaveURL(/\/revise\/rev_[0-9A-Z]+$/);
  await expect(page.getByRole('heading', { name: '4줄이 바뀌어요' })).toBeVisible({ timeout: 20_000 });
  await expect(page.getByTestId('revision-rows').locator('.sb-revrow')).toHaveCount(5);
  await expect(page.getByTestId('revision-rows')).toContainText('유지');
  await shot(page, 'SB3R2');
  await page.getByRole('button', { name: '적용', exact: true }).click();
  await expect(page).toHaveURL(sbUrl('/outline'));
});

test('요구 추적 — SB4T 요약 · SB4X 확장 · SB4U 정리 4 · SB4U2 · SB4TD(§9.2-12 · 13)', async ({ page }) => {
  await page.goto(sbUrl('/outline'));
  await page.getByRole('button', { name: '요구 추적 확인' }).click();
  await expect(page).toHaveURL(sbUrl('/trace'));
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('요구 12개 중 7개는 잘 들어갔어요');
  const nResolve = Number(await page.getByTestId('tcard-resolve').locator('.sb-tcard__n').innerText());
  const nOk = Number(await page.getByTestId('tcard-ok').locator('.sb-tcard__n').innerText());
  const nOwner = await page.getByTestId('owner-line').count();
  expect(nResolve + nOk + nOwner).toBe(12);
  await expect(page.getByTestId('tcard-resolve')).toContainText('RQ-11 · 07 · 03 · 05');
  await expect(page.getByTestId('owner-line').first()).toContainText('역할은 솔루션 담당이 확인 중이에요');
  await shot(page, 'SB4T');

  await page.getByTestId('tcard-ext').click();
  await expect(page).toHaveURL(sbUrl('/trace/extensions'));
  await expect(page.getByTestId('extensions')).toContainText('확장');
  await expect(page.getByTestId('extensions')).toContainText('검토 중');
  await shot(page, 'SB4X');
  await page.getByRole('button', { name: '확인했어요' }).click();
  await expect(page).toHaveURL(sbUrl('/trace'));

  await page.getByRole('link', { name: `${nResolve}개 정리하기` }).click();
  await expect(page).toHaveURL(sbUrl('/trace/resolve/1'));
  await expect(page.locator('.sb-eyebrow')).toContainText(`정리 1 / ${nResolve} · RQ-11`);
  await shot(page, 'SB4U');
  await page.getByRole('button', { name: 'Part 2 중앙관제실 시나리오에 넣기' }).click();
  await page.getByRole('button', { name: '다음 · RQ-07' }).click();
  await expect(page.locator('.sb-eyebrow')).toContainText('정리 2 / 4 · RQ-07');
  await page.getByRole('button', { name: '모르겠어요 → 고객에게 묻기' }).click();
  await expect(page.locator('.sb-eyebrow')).toContainText('정리 3 / 4 · RQ-03');
  await page.locator('.sb-choices .sb-choice').first().click();
  await page.getByRole('button', { name: '다음 · RQ-05' }).click();
  await expect(page.locator('.sb-eyebrow')).toContainText('정리 4 / 4 · RQ-05');
  await page.getByRole('button', { name: '제외하고 사유 기록' }).click();
  const finish = page.getByRole('button', { name: '정리 마치기' });
  await expect(finish).toBeDisabled();
  await page.getByPlaceholder('제외 사유').fill('본 제안 범위 밖');
  await expect(finish).toBeEnabled();
  await page.getByRole('button', { name: /확인 필요로 유지/ }).click();
  await finish.click();
  await expect(page).toHaveURL(sbUrl('/trace/resolved'));
  await expect(page.getByRole('heading', { name: '4개를 정리했어요' })).toBeVisible();
  await expect(page.getByTestId('resolved-rows')).toContainText('고객에게 묻기');
  await expect(page.getByTestId('resolved-rows')).toContainText('확인 필요로 유지 — 추정하지 않음');
  await shot(page, 'SB4U2');

  await page.getByRole('link', { name: '추적표 전체 보기' }).click();
  await expect(page).toHaveURL(sbUrl('/trace/all'));
  await expect(page.getByTestId('trace-row')).toHaveCount(12);
  await expect(page.getByTestId('legend')).toHaveText('직접 주제가 보임 · 해석 새 콘셉트로 · 확장 요구에 없던 해결안 · 검토 논의 중 · 미확인 담당 항목이 안 보임');
  await shot(page, 'SB4TD');
});

test('일정 · 저장 — SB5 6행 · 지금 1 → SB4 v1 저장 · 다음 할 일 3(§9.2-14)', async ({ page }) => {
  await page.goto(sbUrl('/trace/resolved'));
  await page.getByRole('button', { name: '일정 · 분담으로' }).click();
  await expect(page).toHaveURL(sbUrl('/schedule'));
  await expect(page.getByTestId('phase')).toHaveCount(6);
  await expect(page.getByTestId('phases').locator('.sb-badge', { hasText: '지금' })).toHaveCount(1);
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('제작 일정 — D-21부터 납품까지');
  await expect(page.getByRole('link', { name: '물을 것 보기' })).toHaveAttribute('href', `/requirements/${rqId}/questions`);
  await shot(page, 'SB5');
  await page.getByRole('button', { name: '저장하고 공유' }).click();
  await expect(page).toHaveURL(sbUrl('/saved?v=1'));
  await expect(page.getByRole('heading', { name: '스토리보드 v1을 저장했어요' })).toBeVisible();
  await expect(page.locator('.sb-saved')).toContainText('섹션 11개');
  await expect(page.locator('[data-testid^="handoff-"]')).toHaveCount(3);
  await expect(page.getByTestId('handoff-proposal')).toContainText('B2B 제안서');
  await shot(page, 'SB4');
});

test('내보내기 — 기본 PPTX · 표시 유지 고정 · 다운로드(§9.2-15)', async ({ page, request }) => {
  await page.goto(sbUrl('/saved?v=1'));
  await page.getByRole('link', { name: '내보내기' }).click();
  await expect(page).toHaveURL(sbUrl('/export'));
  await expect(page.getByTestId('fmt-pptx')).toHaveAttribute('aria-pressed', 'true');
  const fixed = page.getByRole('button', { name: /확인 필요 · TBD 표시 유지/ });
  await expect(fixed).toHaveAttribute('aria-disabled', 'true');
  await fixed.click({ force: true });   // 꺼지지 않아야 한다(끌 수 없음)
  await expect(fixed).toHaveAttribute('aria-pressed', 'true');
  await shot(page, 'SB4E');
  const download = page.waitForEvent('download', { timeout: 40_000 });
  await page.getByRole('button', { name: '내보내기', exact: true }).click();
  const d = await download;
  const name = await downloadName(request, d);
  expect(name).toContain('_스토리보드_v');
  expect(name).toMatch(/\.pptx$/);
});

test('버전 비교 — v1 저장 뒤 수정 하나 → SB3V 되돌리기 · v2로 계속(§9.2-11)', async ({ page, request }) => {
  await page.goto(sbUrl('/revise'));
  await page.getByTestId('revise-target').click();
  await page.getByRole('option', { name: 'Intro' }).click();
  await page.getByLabel('어떻게 바꿀까요').fill('여는 방식을 시장 변화로 확정');
  await page.getByRole('button', { name: '다시 쓰기' }).click();
  await expect(page.getByRole('heading', { name: /줄이 바뀌어요$/ })).toBeVisible({ timeout: 20_000 });
  await page.getByRole('button', { name: '적용', exact: true }).click();
  await expect(page).toHaveURL(sbUrl('/outline'));
  await expect(page.locator('.sb-h1 .sb-badge')).toHaveText('v2 초안');
  await page.getByRole('link', { name: '버전' }).click();
  await expect(page).toHaveURL(sbUrl('/versions'));
  const h1 = page.getByRole('heading', { level: 1 });
  await expect(h1).toHaveText(/^v1 → v2, 바뀐 곳 \d+$/, { timeout: 15_000 });
  const before = Number(((await h1.textContent()) ?? '').replace(/\s+/g, ' ').trim().match(/(\d+)\s*$/)![1]);
  expect(before).toBeGreaterThan(0);
  await expect(page.locator('.sb-sub').first()).toContainText('하나씩 되돌릴 수 있어요.');
  await shot(page, 'SB3V');
  await page.getByTestId('change-row').getByRole('button', { name: '되돌리기' }).first().click();
  await expect(h1).toHaveText(`v1 → v2, 바뀐 곳 ${before - 1}`);
  await page.getByRole('link', { name: 'v2로 계속' }).click();
  await expect(page).toHaveURL(sbUrl('/outline'));
  const sb = await getSb(request, sbId);
  expect(sb.version).toBe(1);
});

test('전체 보기 — SB3D 11행 · 추가 논의 · 회의 안건 복사(§4.13)', async ({ page, context }) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write']);
  await page.goto(sbUrl('/outline/all'));
  await expect(page.getByTestId('section-row')).toHaveCount(11);
  await expect(page.locator('.sb-crumb')).toContainText(/^목차 · v\d( 초안)? · 자동 저장됨$/);
  const disc = page.getByTestId('discussions');
  await expect(disc).toContainText('추가 논의');
  await shot(page, 'SB3D');
  await disc.getByRole('button', { name: '회의 안건에 넣기' }).click();
  await expect(disc.getByRole('button', { name: '복사했어요' })).toBeVisible();
});
