/**
 * IMG2R 참조 이미지 고르기 — AC 6(검색어 · 검수 완료 · 권리) · 7(요소 · 강도 저장) · 8(업로드 강 불가) · 9(3장 제한) · 「참조 이미지로 시작」.
 */
import { expect, test } from '@playwright/test';
import { api, DESC, fixture, newWork, shot } from './helpers';

test('사내 자산에서 2장 고르고 요소 · 강도 지정 → 적용', async ({ page, request }) => {
  test.setTimeout(90_000);
  const w = await newWork(request, { kind: 'space', description: DESC });
  await api(request, 'POST', `/works/${w.id}:prefill`);
  await page.goto(`/image/w/${w.id}/references`);
  await expect(page.getByTestId('img2r')).toBeVisible();

  // AC6
  await expect(page.getByLabel('참조 이미지 검색')).toHaveValue('카페 메뉴보드');
  await expect(page.getByTestId('img2r-head')).toHaveText(/^\d+개 · 검수 완료$/, { timeout: 20_000 });
  const tiles = page.getByTestId('img2r-grid').locator('.img-rtile');
  await expect(tiles.first()).toBeVisible();
  for (const r of await tiles.evaluateAll((els) => els.map((e) => e.getAttribute('data-rights')))) expect(['official', 'customer_case']).toContain(r);

  // AC7 — 1: 구도 + 제품 배치 · 중 / 2: 색감 · 조명 + 소재 · 강
  await tiles.nth(0).click();
  await tiles.nth(1).click();
  const picks = page.getByTestId('img2r-pick');
  await expect(picks).toHaveCount(2);
  await expect(tiles.nth(0).locator('.img-rtile__role')).toHaveText('구도');
  await picks.nth(0).getByRole('button', { name: '제품 배치' }).click();
  const p2 = picks.nth(1);
  await p2.getByRole('button', { name: '색감 · 조명' }).click();
  await p2.getByRole('button', { name: '소재' }).click();
  await p2.getByRole('button', { name: '구도' }).click();
  await p2.getByRole('button', { name: '강', exact: true }).click();
  await expect(tiles.nth(1).locator('.img-rtile__role')).toHaveText('색감 · 조명 · 소재');
  await shot(page, 'IMG2R');

  // AC9 — 3장까지
  await tiles.nth(2).click();
  await tiles.nth(3).click();
  await expect(page.getByTestId('img2r-msg')).toHaveText('참조는 3장까지 고를 수 있어요');
  await expect(picks).toHaveCount(3);
  await picks.nth(2).getByRole('button', { name: '참조 빼기' }).click();
  await expect(picks).toHaveCount(2);

  await page.getByRole('button', { name: /참조 2장 적용/ }).click();
  await expect(page).toHaveURL(new RegExp(`/image/w/${w.id}/conditions$`));
  await expect(page.getByTestId('img2-refs').locator('.img-refthumb')).toHaveCount(2);
  const refs = (await api(request, 'GET', `/works/${w.id}/references`)).items;
  expect(refs.map((r: { aspects: string[]; strength: string }) => [r.aspects, r.strength])).toEqual([
    [['composition', 'placement'], 'mid'], [['color_light', 'material'], 'high'],
  ]);
  await shot(page, 'IMG2-with-refs');
});

test('내 파일 올리기 — 업로드 참조는 강도 「강」을 고를 수 없다(AC8)', async ({ page, request }) => {
  const w = await newWork(request, { kind: 'space', description: DESC });
  await page.goto(`/image/w/${w.id}/references`);
  await page.getByRole('tab', { name: '내 파일 올리기' }).click();
  await expect(page.getByTestId('img2r-upload')).toContainText('JPG · PNG · HEIC');
  await page.getByTestId('img2r-upload').locator('input[type=file]').setInputFiles(fixture('ref.png'));
  const pick = page.getByTestId('img2r-pick');
  await expect(pick).toHaveCount(1, { timeout: 15_000 });
  await expect(pick).toContainText('내 파일 · 업로드');
  const strong = pick.getByRole('button', { name: '강', exact: true });
  await expect(strong).toBeDisabled();
  await expect(strong).toHaveAttribute('title', '올린 사진은 ‘중’까지 따를 수 있어요');
  await shot(page, 'IMG2R-upload');
  // 서버도 막는다(422 STRENGTH_NOT_ALLOWED)
  await page.getByRole('button', { name: /참조 1장 적용/ }).click();
  await expect(page).toHaveURL(/\/conditions$/);
  const ref = (await api(request, 'GET', `/works/${w.id}/references`)).items[0];
  const r = await request.fetch(`/api/image/v1/works/${w.id}/references/${ref.id}`, { method: 'PATCH', data: { strength: 'high' } });
  expect(r.status()).toBe(422);
  expect((await r.json()).error.code).toBe('STRENGTH_NOT_ALLOWED');
});

test('참조 이미지로 시작 — 설명 없이 적용하면 참조 설명으로 메아리를 채운다', async ({ page }) => {
  test.setTimeout(60_000);
  await page.goto('/image');
  await page.getByRole('link', { name: '참조 이미지로 시작' }).first().click();
  await expect(page).toHaveURL(/\/image\/w\/imw_[^/]+\/references$/, { timeout: 15_000 });
  await expect(page.getByTestId('img-echo')).toHaveCount(0);
  const tiles = page.getByTestId('img2r-grid').locator('.img-rtile');
  await expect(tiles.first()).toBeVisible({ timeout: 20_000 });
  await tiles.first().click();
  await page.getByRole('button', { name: /참조 1장 적용/ }).click();
  await expect(page).toHaveURL(/\/conditions$/);
  await expect(page.getByTestId('img-echo')).toContainText('공간 · ');
});

test('상단 이미지 검색 「현재 작업에 추가」 2장 → IMG2 참조 · 안내(AC4)', async ({ page, request }) => {
  test.setTimeout(90_000);
  const w = await newWork(request, { kind: 'space', description: DESC });
  await api(request, 'POST', `/works/${w.id}:prefill`);
  await page.goto(`/image/w/${w.id}/conditions?pop=image&q=${encodeURIComponent('카페 메뉴보드')}`);
  const grid = page.getByRole('list', { name: '이미지 결과' });
  const checks = grid.locator('.wm-tile__check');
  await expect(checks.nth(1)).toBeAttached({ timeout: 20_000 });
  // 체크 단추는 타일에 올려야 보인다
  for (const i of [0, 1]) { await grid.locator('.wm-tilewrap').nth(i).hover(); await checks.nth(i).click(); }
  await page.getByRole('button', { name: '현재 작업에 추가' }).click();
  await expect(page.getByTestId('img2-refs').locator('.img-refthumb')).toHaveCount(2, { timeout: 20_000 });
  await expect(page.getByTestId('img2-refnotice')).toHaveText('이미지 검색에서 선택한 2장이 참조로 들어갔습니다');
  await shot(page, 'IMG2-topbar-refs');
});
