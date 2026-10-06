/**
 * BE4E 배치 직접 수정(§4.8) — 제품 이동 → 시야각 경고 · 「원래 위치」 유령 · 수정안 적용 · 끌어서 옮기기 · 자동 조정 · 수정 적용.
 * AC 32 · 33(같은 꼴, 실제 KB 제품) · 36(전원 → 메모) · 37 · 38.
 */
import { expect, test } from '@playwright/test';
import { api, makeLayout, shot } from './helpers';

test('배치 직접 수정 — 시야각 경고 → 벤치 함께 옮기기 → 끌기 → 자동 조정 → 수정 적용', async ({ page, request }) => {
  test.setTimeout(150_000);
  const id = await makeLayout(request);
  const before = await api(request, 'GET', `/birdseyes/${id}`);
  const lay = (await api(request, 'GET', `/birdseyes/${id}/layout`)).layout;
  const flip = lay.groups.find((g: any) => g.short === 'Flip Pro');
  const sofa = lay.groups.find((g: any) => g.kind === 'furniture' && g.short === '라운지 소파');
  const item = lay.items.find((it: any) => it.id === flip.item_ids[0]);
  const vertical = Math.round(item.rot_deg) % 180 !== 0;       // 옆벽이면 벽을 따라 위아래로
  const mv = vertical ? `${item.id}:0:3` : `${item.id}:3:0`;

  // BE4 → 경고 링크 → BE4E(이동 3.0 m 를 바로 건 상태로 연다)
  await page.goto(`/birdseye/${id}/layout`);
  await expect(page.getByTestId('be4-warn-link')).toContainText('직접 수정에서 보기', { timeout: 30_000 });
  await page.goto(`/birdseye/${id}/layout/edit?move=${mv}`);
  const view = page.getByTestId('be4e-warn-viewing_angle');
  await expect(view).toContainText(`Flip Pro를 ${vertical ? '아래로' : '오른쪽으로'} 3.0 m 옮겨 관람 벤치`, { timeout: 30_000 });
  await expect(view).toContainText('시야각 밖이에요');
  await expect(view).toHaveAttribute('title', /^pr_warn_viewing_angle · .+\(draft\)$/);   // AC37 규칙 툴팁
  await expect(page.getByTestId('be4e-canvas')).toContainText('원래 위치');
  await expect(page.getByTestId('be4e-changes')).toContainText('변경 1 건');
  await shot(page, 'BE4E');

  await view.getByRole('button', { name: '벤치 함께 옮기기' }).click();
  await expect(view).toContainText('조정함', { timeout: 10_000 });
  await expect(page.getByTestId('be4e-changes')).toContainText('변경 2 건');

  // 끌어서 옮기기 — 라운지 소파를 오른쪽으로
  const poly = page.locator(`[data-testid="be4e-canvas"] polygon[data-item="${sofa.item_ids[0]}"]`);
  await page.getByTestId('be4e-canvas').scrollIntoViewIfNeeded();
  const box = (await poly.boundingBox())!;
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width / 2 + 20, box.y + box.height / 2, { steps: 4 });
  await page.mouse.move(box.x + box.width / 2 + 40, box.y + box.height / 2, { steps: 4 });
  await page.mouse.up();
  await expect(page.getByTestId('be4e-changes')).toContainText('변경 3 건', { timeout: 10_000 });

  // 되돌리기 → 다시 실행
  await page.getByRole('button', { name: '되돌리기' }).click();
  await expect(page.getByTestId('be4e-changes')).toContainText('변경 2 건');
  await page.getByRole('button', { name: '다시 실행' }).click();
  await expect(page.getByTestId('be4e-changes')).toContainText('변경 3 건');

  // 경고 모두 자동 조정 → 전원은 메모(AC36)
  await page.getByTestId('be4e-autofix').click();
  await expect(page.getByTestId('be4e-warn-power').first()).toContainText('메모로 남김', { timeout: 10_000 });
  await expect(page.getByTestId('be4e-autofix')).toBeDisabled();

  await page.getByTestId('be4e-apply').click();
  await expect(page).toHaveURL(new RegExp(`/birdseye/${id}/layout$`), { timeout: 15_000 });
  const after = await api(request, 'GET', `/birdseyes/${id}`);
  expect(after.layout_version).toBe(before.layout_version + 1);
  await expect(page.getByTestId('be4-canvas')).toBeVisible();

  // 취소는 버전을 바꾸지 않는다(AC38)
  await page.goto(`/birdseye/${id}/layout/edit?move=${mv}`);
  await expect(page.getByTestId('be4e-changes')).toContainText('변경 1 건', { timeout: 30_000 });
  await page.getByTestId('be4e-cancel').click();
  await expect(page).toHaveURL(new RegExp(`/birdseye/${id}/layout$`));
  expect((await api(request, 'GET', `/birdseyes/${id}`)).layout_version).toBe(before.layout_version + 1);
});
