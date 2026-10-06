/**
 * IMG2P 현장 사진 제품 합성 — 업로드 → 벽면 인식 → 기본 배치 · 치수 라벨(AC46) · 배열 · 끌어 옮기기 · 합성 4장 생성(AC47 화면) ·
 * 어두운 사진(AC45).
 */
import { expect, test } from '@playwright/test';
import { api, fixture, QM55C, shot, waitRun } from './helpers';

test('현장 사진 올리기 → 인식 → 배치 · 치수 → 합성 4장', async ({ page, request }) => {
  test.setTimeout(180_000);
  await page.goto('/image');
  await page.getByRole('link', { name: '현장 사진에 제품 합성' }).first().click();
  await expect(page).toHaveURL(/\/image\/w\/imw_[^/]+\/composite$/, { timeout: 15_000 });
  const workId = /\/w\/(imw_[^/]+)\//.exec(page.url())![1];
  await expect(page.getByTestId('img2p-drop')).toContainText('현장 사진을 끌어 놓거나 올려 주세요 · JPG · PNG · HEIC');
  await expect(page.getByRole('button', { name: /합성 이미지 4장 생성/ })).toBeDisabled();
  await shot(page, 'IMG2P-empty');
  // 제품(QM55C ×3)은 상단 제품 탐색 「현재 작업에 추가」와 같은 API 로 넣는다
  await api(request, 'POST', `/works/${workId}/products`, { refs: ['kb:model:mdl_LH55QMCEBGCXKR'], qty: 1 });
  const w0 = await api(request, 'GET', `/works/${workId}`);
  await api(request, 'PATCH', `/works/${workId}`, { conditions: { ...w0.conditions, products: [QM55C] } });
  await page.reload();
  await page.getByTestId('img2p-file').setInputFiles(fixture('site.png'));
  await expect(page.getByTestId('img2p-status').first()).toHaveText('벽면 인식 완료', { timeout: 30_000 });
  await expect(page.getByTestId('img-w')).toHaveText('카운터 위 흰 벽면을 설치 가능한 면으로 인식하고 QM55C 3대를 올려두었습니다. 끌어서 위치를, 모서리로 크기를 맞춰 주세요. 실제 치수를 하나 알려주시면 비율을 정확히 맞춥니다.');
  await expect(page.getByRole('button', { name: /QM55C ×3 · 가로 3연/ })).toBeVisible();
  await expect(page.getByText('인식된 벽면 · 설치 가능')).toBeVisible();
  await expect(page.getByTestId('img2p-measure')).toContainText(/가로 약 [\d,]+ mm · 바닥에서 /);
  await shot(page, 'IMG2P');

  // AC46 — 카운터 폭 3600 → 가로 약 3,730 mm
  await page.getByLabel('카운터 폭').fill('3600');
  await expect(page.getByTestId('img2p-measure')).toContainText('가로 약 3,730 mm · 바닥에서', { timeout: 10_000 });
  // 배열 · 설치
  await page.getByRole('group', { name: '배열' }).getByRole('button', { name: '세로 3연' }).click();
  await expect(page.getByRole('button', { name: /QM55C ×3 · 세로 3연/ })).toBeVisible();
  await page.getByRole('group', { name: '배열' }).getByRole('button', { name: '가로 3연' }).click();
  // 끌어 옮기기(그룹 이름표 키보드 · 마우스)
  const before = (await api(request, 'GET', `/works/${workId}`)).composite.groups[0].quad;
  const label = page.getByRole('button', { name: /QM55C ×3 · 가로 3연/ });
  const lb = (await label.boundingBox())!;
  await page.mouse.move(lb.x + 20, lb.y + 8);
  await page.mouse.down();
  await page.mouse.move(lb.x + 60, lb.y + 30, { steps: 6 });
  await page.mouse.up();
  await expect.poll(async () => JSON.stringify((await api(request, 'GET', `/works/${workId}`)).composite.groups[0].quad), { timeout: 10_000 }).not.toBe(JSON.stringify(before));
  // 원근 맞춤 → 면에 맞춰 스냅
  await page.getByRole('button', { name: '원근 맞춤' }).click();
  await expect(page.getByRole('button', { name: '원근 맞춤' })).toHaveAttribute('aria-pressed', 'true');
  // 보기 전환
  await page.getByRole('button', { name: '원본 사진' }).click();
  await expect(page.getByText('인식된 벽면 · 설치 가능')).toHaveCount(0);
  await page.getByRole('button', { name: '배치 편집' }).click();
  await shot(page, 'IMG2P-placed');

  // 합성 4장
  await page.getByRole('button', { name: /합성 이미지 4장 생성/ }).click();
  await expect(page).toHaveURL(/\/run\/ign_/);
  const runId = /\/run\/(ign_[^/?]+)/.exec(page.url())![1];
  await expect(page.getByTestId('img3g-shots').locator('[data-testid^="shot-"]')).toHaveCount(4);
  await shot(page, 'IMG3G-composite');
  const run = await waitRun(request, runId);
  expect([run.kind, run.status, run.done]).toEqual(['composite', 'succeeded', 4]);
});

test('어두운 사진 — 「어두워 인식 어려움 · 다시 촬영 권장」(AC45)', async ({ page, request }) => {
  test.setTimeout(90_000);
  const w = await api(request, 'POST', '/works', { start: 'composite' });
  await page.goto(`/image/w/${w.id}/composite`);
  await page.getByTestId('img2p-file').setInputFiles(fixture('dark.png'));
  await expect(page.getByTestId('img2p-status').first()).toHaveText('어두워 인식 어려움 · 다시 촬영 권장', { timeout: 30_000 });
  await expect(page.getByText('사진이 어두워 합성 결과가 고르지 않을 수 있어요')).toBeVisible();
  await page.getByRole('button', { name: '촬영 가이드 · 다시 인식' }).click();
  await expect(page.getByRole('dialog', { name: '촬영 가이드' })).toBeVisible();
  await shot(page, 'IMG2P-dark');
});
