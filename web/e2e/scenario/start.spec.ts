/**
 * 시작 방식 — SC1T 업종 템플릿(AC8 · AC9 · AC10) · SC1B 조감도에서 이어 만들기(AC11 · AC13 화면 쪽).
 * SC1B 는 개발 공유 데이터에 존 포인트가 있는 조감도가 있다고 가정할 수 없어, 보드 예(강남 플래그십 · 존 5)를
 * scenario 백엔드가 테스트 세계에서 실제로 돌려준 응답(fixtures/birdseye.json)으로 받아 화면을 확인한다.
 */
import fs from 'node:fs';
import path from 'node:path';
import { expect, test } from '@playwright/test';
import { api, makeScenario, shot } from './helpers';

// 공유 개발 PC(2 CPU · 7GB, 다른 세션과 함께)에서 메모리 부족으로 브라우저 탭이 죽는 일이 있어 한 번만 다시 돌린다
test.describe.configure({ retries: 1 });

const BE = JSON.parse(fs.readFileSync(path.resolve(process.cwd(), 'e2e/scenario/fixtures/birdseye.json'), 'utf8'));

test('SC1T 업종 16 · 검색 · 이 골격으로 시작 → SC2E → SC3 솔루션 미리 채움', async ({ page }) => {
  test.setTimeout(90_000);
  await page.goto('/scenario/new/template');
  const tiles = page.getByTestId('sc1t-tile');
  await expect(tiles).toHaveCount(16);
  await expect(tiles.first()).toHaveAttribute('data-code', 'FB');
  await expect(tiles.first()).toHaveAttribute('aria-checked', 'true');
  const p1 = page.getByTestId('sc1t-preset').first();
  await expect(p1).toHaveAttribute('aria-checked', 'true');
  await expect(p1).toContainText('매장 하루');
  await expect(p1).toContainText('장면 4');
  await expect(p1).toContainText('오픈 → 점심 피크 → 본사 배포 → 마감');
  await expect(p1).toContainText('점장 · 손님 · 본사 담당자');
  await expect(page.getByTestId('sc1t-spaces').locator('.sc-chip')).toHaveCount(5);
  await expect(page.getByTestId('sc1t-needs').locator('.sc-chip')).toHaveCount(4);
  await expect(page.getByTestId('sc1t-used')).toHaveText('시스템에어컨 · LCD 사이니지 · 갤럭시 탭 · 파트너 앱 · 주문 결제 · MagicINFO');
  await shot(page, 'SC1T');
  // AC9 검색
  await page.getByLabel('업종 · 공간 검색').fill('병실');
  await expect(tiles).toHaveCount(1);
  await expect(tiles.first()).toContainText('의료 · 요양 · 케어');
  await page.getByLabel('업종 · 공간 검색').fill('');
  await expect(tiles).toHaveCount(16);
  // AC10 시작 → SC2E
  await page.getByTestId('sc1t-start').click();
  await expect(page).toHaveURL(/\/scenario\/sc_[^/]+\/timeline$/);
  await expect(page.getByTestId('sc2e-head')).toContainText('시간대 4 · 역할 3 · 장면 4', { timeout: 30_000 });
  await page.getByTestId('sc2e-next').click();
  await expect(page).toHaveURL(/\/solutions$/);
  await expect(page.getByTestId('sc3-solutions-chip').first()).toContainText('MagicINFO');
});

test('SC1B 존 4 / 5 · 축 · 동선 순서 바꾸기 → 존으로 장면 만들기 요청', async ({ page, request }) => {
  test.setTimeout(90_000);
  const target = await makeScenario(request, { until: 'parsed', title: 'SC1B 이어 만들기 대상' });
  let sent: Record<string, unknown> | null = null;
  await page.route('**/api/scenario/v1/birdseye-options', (r) => r.fulfill({ json: BE.options }));
  await page.route('**/api/scenario/v1/birdseye-options/*', (r) => r.fulfill({ json: BE.preview }));
  await page.route('**/api/scenario/v1/scenarios:from-birdseye', async (r) => {
    sent = r.request().postDataJSON();
    await r.fulfill({ status: 202, json: { job_id: 'job_e2e_sc1b', scenario_id: target } });
  });
  await page.goto('/scenario/new/birdseye');
  await expect(page.getByTestId('sc1b-option')).toHaveCount(3);
  await expect(page.getByTestId('sc1b-option').first()).toHaveAttribute('aria-pressed', 'true');
  await expect(page.getByTestId('sc1b-option').first()).toContainText('강남 플래그십 1층 로비');
  await expect(page.getByTestId('sc1b-zones-head')).toContainText('· 4 / 5 선택');
  const zones = page.getByTestId('sc1b-zone');
  await expect(zones).toHaveCount(5);
  await expect(zones.nth(4)).toContainText('배치 제품 없음 · 랩핑 포인트만 지정');
  await expect(zones.nth(4).getByTestId('sc1b-zone-badge')).toHaveText('제외');
  await expect(zones.nth(0).getByTestId('sc1b-zone-badge')).toHaveText('장면 1');
  await expect(page.getByTestId('sc1b-card')).toContainText('존 4개 → 장면 4개 · 2 / 4');
  await expect(page.getByTestId('sc1b-keep')).toBeChecked();
  await expect(page.getByTestId('sc1b-axis').first()).toHaveAttribute('aria-pressed', 'true');
  await expect(page.getByTestId('sc1b-plan')).toContainText('120평 · 층고 4.5m');
  await expect(page.getByTestId('sc1b-order-chip')).toHaveText(['1쇼윈도', '2미디어월', '3체험 · 시연 존', '4라운지 · 상담']);
  await shot(page, 'SC1B');
  // AC13 동선 순서 2 ↔ 3(끌어 놓기)
  await page.getByTestId('sc1b-order-chip').nth(2).dragTo(page.getByTestId('sc1b-order-chip').nth(1));
  await expect(page.getByTestId('sc1b-order-chip')).toHaveText(['1쇼윈도', '2체험 · 시연 존', '3미디어월', '4라운지 · 상담']);
  await expect(zones.nth(2).getByTestId('sc1b-zone-badge')).toHaveText('장면 2');
  // 빈 존을 넣으면 장면 5개
  await zones.nth(4).getByRole('checkbox').check();
  await expect(page.getByTestId('sc1b-card')).toContainText('존 5개 → 장면 5개');
  await zones.nth(4).getByRole('checkbox').uncheck();
  await page.getByTestId('sc1b-start').click();
  await expect(page).toHaveURL(new RegExp(`/scenario/${target}/timeline$`));
  expect(sent).toMatchObject({ birdseye_id: BE.preview.birdseye_id, zone_ids: ['bez_1', 'bez_3', 'bez_2', 'bez_4'], order: ['bez_1', 'bez_3', 'bez_2', 'bez_4'],
    axis: '방문객 동선', keep_link: true, type: 'with' });
  await api(request, 'DELETE', `/scenarios/${target}`);
});

test('UC_SC 유스케이스 맵(개발용) — 레인 5 · 카드 17', async ({ page }) => {
  await page.goto('/scenario/uc');
  await expect(page.getByTestId('sc-uc-lane')).toHaveCount(5);
  await expect(page.getByTestId('sc-uc-card')).toHaveCount(17);
  await expect(page.getByTestId('sc-uc')).toContainText('기본 흐름 4 · 추가 화면 8 · 다른 기능 5');
  await shot(page, 'UC_SC');
  await page.getByRole('link', { name: /^SC1T / }).click();
  await expect(page).toHaveURL(/\/scenario\/new\/template$/);
});
