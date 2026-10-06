/**
 * 고객 요구사항(RQ) 기본 흐름 — 실제 게이트웨이 → requirements(+워커) · files · kb · ai-tools(mock 고정 응답 mocks/ai-tools/rq.*.json).
 * docs/scenarios/01-requirements.md §9.2 E2E 2 · 3 · 6 ~ 13. 화면: e2e/requirements/__screens__/
 * 실행: make dev-bg SERVICE=requirements && make e2e-feature SERVICE=requirements
 */
import { expect, test } from '@playwright/test';
import { attach, files, shot, weightsOf } from './helpers';

test.describe.configure({ mode: 'serial' });
test.use({ permissions: ['clipboard-read', 'clipboard-write'] });

test('기본 흐름: 파일 → 채우기 → 심층 작성 → 저장 → 물을 것 → 정의서 → 답변 → v2', async ({ page }) => {
  test.setTimeout(240_000);

  // ── RQ1 빈 폼(E2E 1 일부 · 2)
  await page.goto('/requirements/new');
  await expect(page.getByPlaceholder('예) 용산 업무시설 재개발 제안')).toBeVisible();
  await expect(page.getByPlaceholder('키맨 (예: 대표이사)')).toBeVisible();
  await expect(page.locator('.sh-crumbs__cur')).toHaveText('새 요구사항');
  await expect(page.locator('[data-step="1"] [data-state="active"]')).toBeVisible();
  await expect(page.getByRole('button', { name: '바로 저장' })).toHaveAttribute('aria-disabled', 'true');
  await expect(page.getByRole('button', { name: '심층 작성' })).not.toHaveAttribute('aria-disabled', 'true');
  await shot(page, 'rq1-empty');

  // ── RQ1G 채우는 중 → RQ2(E2E 3 뒷부분)
  await attach(page, '[data-testid=rq-file-input]', files('제안지원요청서_용산 업무시설 재개발.pptx', '고객 미팅 메모_11월 4일.txt'));
  await expect(page).toHaveURL(/\/requirements\/rq_[0-9A-Z]{26}\/form$/);
  await expect(page.locator('.rq-filechip')).toHaveCount(2);
  await expect(page.getByTestId('fill-progress')).toContainText('채우는 중');
  await expect(page.getByTestId('fill-progress')).toContainText(/\d+ \/ \d+/);
  await expect(page.getByRole('button', { name: '심층 작성' })).toHaveAttribute('aria-disabled', 'true');
  await shot(page, 'rq1g-filling');
  await expect(page.getByRole('button', { name: '파일 첨부' })).toBeVisible({ timeout: 60_000 });
  await expect(page.locator('.rq-fld__box:has(#f-proj) .rq-src')).toHaveText('PPTX');
  await expect(page.locator('.rq-fld__box:has(#f-note) .rq-src')).toHaveText('TXT');
  await expect(page.getByTestId('equal-badge')).toHaveText('균등');
  await expect(page.locator('#f-proj')).toHaveValue('용산 업무시설 재개발 AI Ready 오피스');
  await expect(page.getByTestId('km-count')).toHaveText('3명');
  expect(await weightsOf(page)).toEqual([34, 33, 33]);
  const rqUrl = page.url();
  const rqId = rqUrl.match(/rq_[0-9A-Z]{26}/)![0];
  await expect(page.locator('.sh-crumbs__cur')).toHaveText('E 자산운용 용산 AI Ready 오피스', { timeout: 15_000 });
  await shot(page, 'rq2-filled');

  // 새로고침해도 값 유지(E2E 2)
  await page.reload();
  await expect(page.locator('#f-cust')).toHaveValue('E 자산운용');

  // ── RQ3 보강할 곳(E2E 6)
  await page.getByRole('button', { name: '심층 작성' }).click();
  await expect(page).toHaveURL(/\/deep\/ds_[0-9A-Z]{26}$/);
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('보강할 곳 5', { timeout: 30_000 });
  await expect(page.locator('.rq-complete')).toContainText('완성도');
  await expect(page.locator('.rq-complete')).toContainText('%');
  const boxes = page.getByTestId('gap-list').getByRole('checkbox');
  await expect(boxes).toHaveCount(5);
  for (const b of await boxes.all()) await expect(b).toBeChecked();
  await expect(page.locator('[data-step="2"] [data-state="active"]')).toBeVisible();
  await shot(page, 'rq3-gaps');
  await page.getByRole('checkbox', { name: /^가중치/ }).uncheck();
  await page.getByRole('button', { name: '시작' }).click();

  // ── RQ3A 값 답(E2E 7)
  await expect(page).toHaveURL(/\/q$/);
  await expect(page.getByTestId('ask-progress')).toHaveText('1 / 4');
  await expect(page.getByTestId('question')).toHaveText('최종 제안은 누구에게 하나요?');
  await expect(page.getByRole('progressbar', { name: '질의 진행' })).toHaveAttribute('aria-valuemax', '4');
  await shot(page, 'rq3a-ask');
  await page.getByRole('group', { name: '선택지' }).getByRole('button', { name: '대표이사', exact: true }).click();
  await expect(page.getByTestId('ask-progress')).toHaveText('2 / 4');
  const log = page.locator('.rq-logline[data-log="applied"]').first();
  await expect(log).toContainText('최종 제안대상');
  await expect(log).toContainText('→ 대표이사');
  const panelAudience = page.locator('[data-field="final_audience"]');
  await expect(panelAudience).toContainText('대표이사');
  await expect(panelAudience.locator('.rq-check')).toBeVisible();

  // ── RQ3B 문장 답 → 반영(E2E 8)
  await expect(page.getByTestId('question')).toHaveText("'에너지 절감'의 목표 수치가 있나요?");
  await page.getByLabel('답변').fill('유사 건물 대비 20%. 실측 데이터로 보여 주길 원해요');
  await page.getByLabel('답변').press('Enter');
  const card = page.getByTestId('proposal');
  await expect(card).toContainText('이렇게 바꿀까요?');
  await expect(card.locator('.rq-proposal__before')).toHaveText('에너지 절감 · 정량 데이터 확보');
  await expect(card.locator('.rq-proposal__after')).toHaveText('에너지 사용량 20% 절감 (유사 건물 대비) · 실측 데이터로 증빙');
  await expect(card.getByRole('checkbox')).toBeChecked();
  await expect(card).toContainText("고객 확인에 '유사 건물 사용량 자료' 추가");
  await shot(page, 'rq3b-proposal');
  await card.getByRole('button', { name: '고치기' }).click();
  await expect(card.getByLabel('고친 문장')).toHaveValue('에너지 사용량 20% 절감 (유사 건물 대비) · 실측 데이터로 증빙');
  await card.getByRole('button', { name: '취소' }).click();
  await card.getByRole('button', { name: '반영' }).click();
  await expect(page.getByTestId('ask-progress')).toHaveText('3 / 4');
  await expect(page.getByTestId('panel-items')).toContainText('에너지 사용량 20% 절감 (유사 건물 대비) · 실측 데이터로 증빙');

  // ── 모름 · 끝내기(E2E 9)
  await page.getByRole('button', { name: '모름 · 고객에게 확인' }).click();
  await expect(page.getByTestId('ask-progress')).toHaveText('4 / 4');
  await expect(page.locator('.rq-logline[data-log="deferred"]')).toContainText('고객 확인');
  await page.getByRole('button', { name: '끝내기' }).click();
  await expect(page).toHaveURL(/\/result$/);
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('2곳 보강했어요');
  await expect(page.locator('.rq-complete')).toContainText('완성도');
  await expect(page.locator('.rq-complete')).toContainText(/\d+% → \d+%/);
  await expect(page.getByTestId('customer-check')).toContainText('고객 확인 2');
  await expect(page.getByTestId('customer-check')).toHaveAttribute('href', `/requirements/${rqId}/questions`);
  await shot(page, 'rq3c-result');

  // ── RQ4 저장 완료(E2E 10)
  await page.getByRole('button', { name: '저장' }).click();
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('저장했어요');
  await expect(page.getByTestId('saved-version')).toHaveText('v1');
  await expect(page.getByRole('link', { name: '정의서 보기' })).toBeVisible();
  await expect(page.getByRole('link', { name: /고객에게 물을 것\s*2/ })).toBeVisible();
  await expect(page.locator('.rq-nextcard')).toHaveCount(3);
  await expect(page.locator('.rq-nextcard').first()).toHaveClass(/rq-nextcard--hi/);
  await expect(page.locator('.rq-nextcard').first()).toContainText('전략 수립 Storyboard');
  await expect(page.locator('.sh-step__circle[data-state="done"]')).toHaveCount(3);
  await shot(page, 'rq4-saved');

  // ── RQ5 고객에게 물을 것(E2E 11)
  await page.getByRole('link', { name: /고객에게 물을 것/ }).click();
  await expect(page.getByTestId('q-count')).toHaveText('2');
  const rows = page.getByTestId('question-list').locator('label');
  await expect(rows).toHaveCount(2);
  await expect(rows.filter({ hasText: '유사 건물 에너지 사용량 자료를 받을 수 있을까요?' }).locator('.rq-topic')).toContainText('대표이사');
  await expect(rows.filter({ hasText: '개발사업팀장' }).locator('.rq-topic')).toContainText('개발사업팀장');
  await shot(page, 'rq5-questions');
  await rows.filter({ hasText: '개발사업팀장' }).getByRole('checkbox').uncheck();
  await page.getByRole('button', { name: '메일 문구 복사' }).click();
  await expect(page.getByRole('button', { name: '복사했어요' })).toBeVisible();
  const clip = await page.evaluate(() => navigator.clipboard.readText());
  expect(clip).toContain('유사 건물 에너지 사용량 자료를 받을 수 있을까요?');
  expect(clip).not.toContain('개발사업팀장');
  expect(clip).not.toContain('스펙인');

  // ── RQ6 정의서(E2E 12)
  await page.getByRole('link', { name: '정의서' }).click();
  await expect(page.getByTestId('doc-version')).toHaveText('정의서 v1');
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('용산 업무시설 재개발 AI Ready 오피스');
  await expect(page.locator('.rq-doc .rq-wbar')).toContainText('%');
  const energy = page.locator('.rq-doc__item', { hasText: '에너지 사용량 20% 절감' });
  await expect(energy.locator('.rq-dash')).toHaveText('확인 필요');
  await expect(page.getByTestId('note-lock')).toHaveAttribute('title', '고객 문서 제외');
  await expect(page.locator('.rq-usechip')).toHaveText(['Storyboard', 'MI', '제안서']);
  await shot(page, 'rq6-doc-v1');
  await page.getByRole('link', { name: '고치기' }).click();
  await expect(page).toHaveURL(new RegExp(`/requirements/${rqId}/form$`));

  // ── RQ7 → RQ7B → v2(E2E 13 · 14 줄 없음)
  await page.goto(`/requirements/${rqId}/questions`);
  await page.getByRole('link', { name: '답변 반영하기' }).click();
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('답변을 붙여 넣어 주세요');
  await page.getByLabel('붙여 넣은 고객 답변').fill(replyText());
  await attach(page, '[data-testid=reply-file-input]', files('성수오피스_에너지사용량_2025.pdf'));
  await expect(page.locator('[data-att="성수오피스_에너지사용량_2025.pdf"]')).toBeVisible();
  await shot(page, 'rq7-reply');
  await page.getByRole('button', { name: '바뀌는 곳 찾기' }).click();
  await expect(page).toHaveURL(/\/reply\/rp_[0-9A-Z]{26}$/);
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('3곳이 바뀌어요', { timeout: 30_000 });
  const changes = page.getByTestId('change-list').locator('label');
  await expect(changes).toHaveCount(3);
  await expect(page.getByTestId('storyboard-line')).toHaveCount(0);
  await shot(page, 'rq7b-changes');
  await changes.filter({ hasText: '공간컨텐츠실장' }).getByRole('checkbox').uncheck();
  await page.getByRole('button', { name: 'v2로 저장' }).click();
  await expect(page.getByTestId('doc-version')).toHaveText('정의서 v2');
  await expect(page.locator('.rq-doc__item', { hasText: '오피스를 업무환경 플랫폼으로' })).toBeVisible();
  await expect(page.locator('.rq-doc__item', { hasText: '입주사 앱' })).toHaveCount(0);
  await expect(page.locator('.rq-doc__item', { hasText: '에너지 사용량 20% 절감' }).locator('.rq-dash')).toHaveCount(0);
  await expect(page.getByRole('main')).toContainText('대표이사 · 투자심의위원 2');
  await shot(page, 'rq6-doc-v2');
});

function replyText() {
  return [
    '안녕하세요, E 자산운용 공간컨텐츠실입니다.', '',
    '1. 업무환경 플랫폼은 입주사 앱, 공용 공간 예약, 방문객 안내를 생각하고 있습니다.',
    '2. 비교용으로 성수 오피스 에너지 사용량 자료를 첨부합니다.',
    '3. 제안 발표에는 대표이사님과 투자심의위원 2명이 참석합니다.', '', '감사합니다.',
  ].join('\n');
}

