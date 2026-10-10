/**
 * 콘텐츠 흐름 허브 공통 화면 — 보드 webapp1 SB0 · SB1 · List(VP0) · Gate(VP1) · SBPopup.
 * 실제 스택(게이트웨이 + storyboard · vp). 기능 화면이 쓰는 공용 부품이 보드 폭대로 그려지는지 본다.
 */
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { expect, test } from '@playwright/test';
import { makeStoryboard, shotTo, tag } from './flowkit';

const DIR = path.join(path.dirname(fileURLToPath(import.meta.url)), '__screens__');

test('허브 — SB0 목록 · SB1 상세 · List · Gate · 요약 팝업', async ({ page, request }) => {
  test.setTimeout(120_000);
  const name = `용산 AI Ready 오피스 ${tag()}`;
  const sb = await makeStoryboard(request, { name, dss: true });
  await page.setViewportSize({ width: 1440, height: 900 });

  await page.goto('/storyboard');
  await expect(page.getByText(name).first()).toBeVisible({ timeout: 20_000 });
  await shotTo(page, DIR, 'SB0-new');

  await page.goto(`/storyboard/flow/${sb.id}`);
  await expect(page.getByText(name).first()).toBeVisible({ timeout: 20_000 });
  await shotTo(page, DIR, 'SB1-new');

  await page.goto('/vp');
  await page.waitForLoadState('networkidle');
  await shotTo(page, DIR, 'VP0-new');

  await page.goto(`/vp/new?sb=${sb.id}`);
  await expect(page.getByText(name).first()).toBeVisible({ timeout: 20_000 });
  await shotTo(page, DIR, 'VP1-new');
});
