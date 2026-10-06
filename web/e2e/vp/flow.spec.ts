/**
 * 05-vp §3.1 기본 흐름 — VP0 → VP1(RFP) → VP1A/VP1Q → VP2 → VP3G → VP3 → VP3L · VP3N · VPI → VP4 → 제안서로 넘김.
 * 실제 스택(mock 모델)으로 돈다. 화면마다 e2e/vp/__screens__/{보드}.png 를 남긴다.
 */
import { test } from '@playwright/test';
import { archive, collectToStructure, expect, shot, startDirect, tag } from './helpers';

test.describe.configure({ mode: 'serial' });

test('기본 흐름 — 재료 → 가치 구조 → 결과 → 다듬기 → 제안서 Value Props 로', async ({ page }) => {
  test.setTimeout(300_000);

  // VP0 — 작업 목록
  await page.goto('/vp');
  await expect(page.getByRole('heading', { name: 'Value Proposition 작업' })).toBeVisible();
  for (const t of ['직접 입력으로', 'Storyboard에서', 'MI 결과에서', '이전 가치 제안 복제']) await expect(page.getByRole('button', { name: new RegExp(t) })).toBeVisible();
  await expect(page.getByText('Value Props 업종 레이아웃 16종은 제작 중이에요.')).toBeVisible();
  await expect(page.getByRole('tablist', { name: '상태 필터' })).toBeVisible();
  await shot(page, 'VP0');

  // VP1 — 재료(고객사 → 작업 생성 → RFP 첨부)
  const customer = `가람 커피 ${tag()}`;
  const id = await startDirect(page, customer);
  await expect(page.getByTestId('vp-coverage')).toContainText('재료 커버리지');
  await expect(page.getByTestId('vp-sources')).toContainText('연결할 수 있는 자료');
  await expect(page.getByText('보낼 곳 · 연결 안 됨 — 3장 기본으로 만들고 보낼 때 맞춰요')).toBeVisible();
  await shot(page, 'VP1');

  // VP1A / VP1Q → VP2
  await collectToStructure(page, async (r) => { await shot(page, r === 'review' ? 'VP1A' : 'VP1Q'); });
  await expect(page).toHaveURL(new RegExp(`/vp/${id}/structure$`));
  await expect(page.getByText(/^메시지 구조 · /)).toBeVisible();
  await expect(page.getByText('그 밖에 정한 것')).toBeVisible();
  await expect(page.getByTestId('vp-decisions').locator('.vp-dec__k')).toHaveText(['업종', '업종 레이아웃', '이해관계자형', '시트 수', '추정 값', '이미지', '톤']);
  await shot(page, 'VP2');

  // VP3G — 만들기
  await page.getByRole('button', { name: /장 만들기/ }).click();
  await page.waitForURL(/\/generating\?job=job_/, { timeout: 20_000 });
  await expect(page.getByTestId('vp-generating')).toBeVisible();
  await expect(page.getByText('결정 기록')).toBeVisible();
  // 시트 칸은 플랜 3장으로 먼저 보이고(대기), 결정 기록이 쌓인다 — 빨리 끝나면 결과로 넘어가므로 기다리기만
  if (/generating/.test(page.url())) await page.locator('.vp-log__row').nth(1).waitFor({ timeout: 15_000 }).catch(() => undefined);
  await shot(page, 'VP3G');

  // VP3 — 결과
  await page.waitForURL(new RegExp(`/vp/${id}/result$`), { timeout: 150_000 });
  const cards = page.getByTestId('vp-sheet');
  await expect(cards).toHaveCount(3);
  await expect(cards.first()).toContainText('왜 이 레이아웃?');
  await expect(page.getByTestId('vp-checks')).toContainText('확인할 것');
  await expect(page.getByText(/^가치 제안 3장을 만들었어요/)).toBeVisible();
  await shot(page, 'VP3');

  // VP3L — 레이아웃 바꾸기 · 적합도
  await page.locator('.vp-dock').getByRole('link', { name: '레이아웃 바꾸기' }).click();
  await expect(page.getByTestId('vp-candidates')).toContainText('고를 수 있는 레이아웃');
  await expect(page.getByRole('group', { name: '기둥 수' })).toBeVisible();
  await expect(page.locator('.vp-cand--cur')).toHaveCount(1);
  await shot(page, 'VP3L');
  await page.getByRole('button', { name: '취소' }).click();
  await page.waitForURL(new RegExp(`/vp/${id}/result$`));

  // VP3N — 수치 보강
  await page.locator('.vp-dock').getByRole('link', { name: '수치 보강' }).click();
  await expect(page.getByTestId('vp-metrics')).toContainText('기대 효과 수치');
  await expect(page.getByTestId('vp-rule')).toBeVisible();
  await expect(page.getByTestId('vp-data-request')).toContainText('고객 데이터 요청 초안');
  await shot(page, 'VP3N');
  await page.getByRole('link', { name: '결과로' }).click();

  // VPI — 이미지 칸
  await page.goto(`/vp/${id}/result/images`);
  await expect(page.getByTestId('vp-slots')).toContainText('이미지 칸');
  await expect(page.getByTestId('vp-slot-candidates')).toContainText('바꿀 수 있는 후보');
  await shot(page, 'VPI');

  // VP4 — 결과 활용 → 제안서로 넘김
  await page.getByRole('link', { name: '제안서 Value Props로' }).click();
  await page.waitForURL(new RegExp(`/vp/${id}/export$`));
  await expect(page.getByTestId('vp-export')).toContainText('제안서 유형마다 시트 구성이 달라져요');
  await expect(page.getByRole('radiogroup', { name: '제안서 유형' }).getByRole('radio')).toHaveCount(3);
  await expect(page.getByText('파일 · 공유')).toBeVisible();
  await expect(page.getByText('다른 기능으로 이어가기')).toBeVisible();
  await shot(page, 'VP4');
  await page.getByRole('button', { name: /제안서에 \d시트 보내기/ }).click();
  await page.waitForURL(/\/proposal\//, { timeout: 30_000 });
  expect(page.url()).toMatch(/\/proposal\/(new\?handoff=vho_|pr_)/);
  // 제안서 화면이 넘김으로 새 제안서를 만들면(시험 데이터) 지운다 — 주소의 pr_ 또는 넘김 기록(ack)의 proposal_id
  const vho = page.url().match(/handoff=(vho_[A-Z0-9]+)/)?.[1];
  await page.waitForURL(/\/proposal\/pr_/, { timeout: 15_000 }).catch(() => undefined);
  let pid = page.url().match(/\/proposal\/(pr_[A-Z0-9]+)/)?.[1];
  if (!pid && vho) {
    const r = await page.request.get(`/api/vp/v1/handoffs/${vho}`).catch(() => null);
    pid = r && r.ok() ? ((await r.json()) as { proposal_id?: string | null }).proposal_id ?? undefined : undefined;
  }
  if (pid) await page.request.delete(`/api/proposal/v1/proposals/${pid}`).catch(() => undefined);

  // 목록에 돌아오면 생성이 끝난 작업으로 보인다(빈 수치가 남았으면 '수치 선택 n' · 답하기 → VP3N)
  await page.goto('/vp');
  const row = page.getByTestId('vp-row').filter({ hasText: customer });
  await expect(row).toHaveCount(1);
  await expect(row).toHaveAttribute('data-status', /done|check|ask/);
  const st = (await row.getAttribute('data-status'))!;
  if (st === 'ask') await expect(row.getByRole('link', { name: '답하기' })).toHaveAttribute('href', new RegExp(`/vp/${id}/result/numbers`));
  await archive(page, id);
});
