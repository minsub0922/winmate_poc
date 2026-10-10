/**
 * SP1C(조건으로 모델 찾기) · SP1R(고객 요구 스펙 대응표) — 06-spec §4.5 · §4.6 · §9.3 · §9.4.
 * 목: sp.parse_conditions(C 물류센터 관제실 · 55" 안팎 · 관제 · 벽걸이 · 필수 24시간 운영 · 벽걸이),
 *     sp.extract_requirements(B 병원 로비 규격서 · QM55C), 후보 · 판정 값은 kb 실데이터.
 */
import { expect, test } from '@playwright/test';
import { api, fileBuffer, shot } from './helpers';

test('조건으로 찾기 → 후보 카드 → 고르기 → 비교표', async ({ page }) => {
  await page.goto('/spec/legacy/new/find');
  await expect(page.getByText('어떤 디스플레이가 필요한지 말해 주세요.', { exact: false })).toBeVisible();
  await expect(page.getByTestId('sp-dock-title')).toHaveText('조건으로 찾기 · 0개 선택 · 1 / 3');
  const input = page.getByLabel('조건 추가');
  await input.fill('C 물류센터 관제실에 55인치 정도로 24시간 켜둘 거고 벽에 걸어요');
  await page.getByRole('button', { name: '후보 다시 찾기' }).click();
  await expect(page).toHaveURL(/\/spec\/sp_[A-Z0-9]+\/find/);
  await expect(page.getByTestId('sp-user')).toHaveText('C 물류센터 관제실에 55인치 정도로 24시간 켜둘 거고 벽에 걸어요');
  await expect(page.getByTestId('sp1c-head')).toHaveText(/후보 \d+개 · 조건 일치순/, { timeout: 20_000 });
  const group = (g: string) => page.getByRole('group', { name: g });
  await expect(group('크기').getByRole('button', { name: '55"' })).toHaveAttribute('aria-pressed', 'true');
  await expect(group('용도').getByRole('button', { name: '관제 · 모니터링' })).toHaveAttribute('aria-pressed', 'true');
  await expect(group('설치').getByRole('button', { name: '벽걸이' })).toHaveAttribute('aria-pressed', 'true');
  await expect(group('필수').getByRole('button', { name: '24시간 운영' })).toHaveAttribute('aria-pressed', 'true');
  const cards = page.getByTestId('sp1c-card');
  expect(await cards.count()).toBeGreaterThan(1);
  await expect(cards.first().locator('.sp-cand__score')).toHaveText(/조건 \d+\/\d+/);
  await shot(page, 'SP1C');

  // 두 모델 고르기 → `2개로 비교표 만들기`
  const inside = cards.filter({ has: page.locator('[data-out="0"]') });
  void inside;
  const pickable = page.locator('[data-testid="sp1c-card"][data-out="0"]');
  const n = await pickable.count();
  const targets = n >= 2 ? pickable : cards;
  await targets.nth(0).getByRole('button', { name: /선택$/ }).click();
  await expect(page.getByTestId('sp-dock-title')).toHaveText('조건으로 찾기 · 1개 선택 · 1 / 3');
  await expect(page.getByRole('button', { name: '1개로 시트 만들기' })).toBeEnabled();
  await targets.nth(1).getByRole('button', { name: '+ 시트에 담기' }).click();
  await expect(page.getByTestId('sp-dock-title')).toHaveText('조건으로 찾기 · 2개 선택 · 1 / 3');

  // 표로 비교 ↔ 카드
  await page.getByRole('button', { name: '표로 비교' }).click();
  await expect(page.getByRole('button', { name: '카드로 보기' })).toBeVisible();
  await page.getByRole('button', { name: '카드로 보기' }).click();

  await page.getByRole('button', { name: '2개로 비교표 만들기' }).click();
  await expect(page).toHaveURL(/\/items$/);
  await expect(page.getByTestId('sp-dock-title')).toHaveText(/스펙 항목 · \d+개 선택 · 2 \/ 3/);
  // 이전 → SP1C(시작 갈래)
  await page.getByRole('button', { name: '이전' }).click();
  await expect(page).toHaveURL(/\/find$/);
});

test('규격서 올리기 → 대응표 → 원문 · 묻기 초안 → 시트로', async ({ page, request }) => {
  await page.goto('/spec/legacy/new/requirements');
  await expect(page.getByText('고객 요구 규격서를 올려 주세요.', { exact: false })).toBeVisible();
  await page.locator('input[type=file]').first().setInputFiles(fileBuffer('B병원_로비디스플레이_요구규격서.pdf', 'application/pdf'));
  await expect(page).toHaveURL(/\/spec\/sp_[A-Z0-9]+\/requirements/);
  await expect(page.getByTestId('sp1r-file')).toContainText('B병원_로비디스플레이_요구규격서.pdf');
  const table = page.getByTestId('sp1r-table');
  await expect(table).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId('sp1r-file')).toContainText(/요구 항목 \d+개 인식/);
  const rows = page.getByTestId('sp1r-row');
  expect(await rows.count()).toBeGreaterThan(3);
  await expect(page.getByTestId('sp-dock-title')).toHaveText(/고객 요구 스펙 · 요구 \d+개 · 1 \/ 3/);
  await expect(table.getByRole('button', { name: /대응 모델 QM55C/ })).toBeVisible();
  // 밝기 450 cd/㎡ 이상 → QM55C 500 nit 충족(kb 실데이터)
  await expect(rows.filter({ hasText: '450 cd/㎡ 이상' })).toContainText('충족');
  await shot(page, 'SP1R');

  // 원문 쪽 번호 → 인용 팝오버
  const pref = rows.filter({ hasText: '450 cd/㎡ 이상' }).getByRole('button', { name: /^p\.\d+/ });
  await pref.click();
  await expect(page.getByTestId('sp1r-quote')).toHaveText('“2.3 밝기는 450 cd/㎡ 이상이어야 한다.”');
  await page.keyboard.press('Escape');

  // 확인 필요 → 담당자에게 묻기 초안
  const ask = page.getByRole('button', { name: /확인 필요 \d+건 담당자에게 묻기/ });
  if (await ask.isEnabled()) {
    await ask.click();
    await expect(page.getByRole('dialog', { name: /담당자에게 묻기/ })).toBeVisible();
    await page.getByRole('dialog', { name: /담당자에게 묻기/ }).getByRole('button', { name: '닫기' }).click();
  }

  // 대응표로 시트 만들기 → SP2(요구사항으로 미리 체크)
  const id = page.url().match(/\/spec\/(sp_[A-Z0-9]+)/)![1];
  await page.getByRole('button', { name: '대응표로 시트 만들기' }).click();
  await expect(page).toHaveURL(new RegExp(`/spec/${id}/items$`));
  await expect(page.getByText('고객 요구사항과 관련된 항목을 미리 체크해 두었습니다.', { exact: false })).toBeVisible();
  const s = await api(request, 'GET', `/sheets/${id}`);
  expect(s.kind).toBe('req');
  expect((s.items as Array<{ checked: boolean; prechecked_by: string }>).some((i) => i.checked && i.prechecked_by === 'requirement')).toBeTruthy();
});
