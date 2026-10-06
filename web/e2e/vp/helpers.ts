/**
 * vp e2e 도우미 — 실제 스택(게이트웨이 · vp 개발 서버 + 워커 · 플랫폼 mock 모델)으로 돈다.
 * 공유 개발 데이터라 목록이 비어 있다고 가정하지 않는다: 테스트마다 고객사 이름에 꼬리표를 붙여 자기 작업만 본다.
 */
import { expect as baseExpect, type Page } from '@playwright/test';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

/** 공유 PC(다른 세션이 함께 돈다)라 기다림을 넉넉히 */
export const expect = baseExpect.configure({ timeout: 20_000 });

export const SCREENS = path.join(path.dirname(fileURLToPath(import.meta.url)), '__screens__');

/** 보드 이름으로 화면 저장(e2e/vp/__screens__/{name}.png) */
export async function shot(page: Page, name: string) {
  await page.waitForTimeout(300);
  await page.screenshot({ path: path.join(SCREENS, `${name}.png`) });
}

export const tag = () => `${Date.now().toString(36).slice(-4)}`;

export const RFP_TEXT = `A 커피 프랜차이즈 디지털 메뉴보드 도입 제안요청서(RFP)

1. 사업 개요
전국 직영 · 가맹 매장 320곳의 종이 메뉴보드를 디지털 메뉴보드로 바꾼다.

2. 현황과 문제
메뉴가 바뀔 때마다 인쇄물을 만들어 매장에 배송하고 있어 인쇄 · 배송 비용 부담이 크다.
매장마다 가격 표기가 달라 오표기가 반복된다.
피크 시간 주문 대기가 길어 손님 불편이 크다.

3. 바라는 모습
본사에서 모든 매장 메뉴를 한 번에 운영하는 것이 목표다.

4. 결재
결재는 본사 운영본부장이 한다.

5. 평가 기준
기술 이해도 40점
운영 편의성 30점
수행 능력 30점
`;

/** VP1 — 고객사를 적으면 작업이 생기고(`/vp/:id/materials`) RFP 를 붙인다 */
export async function startDirect(page: Page, customer: string, opts: { rfp?: boolean; note?: string } = {}) {
  await page.goto('/vp/new');
  await expect(page.getByText('누구에게 어떤 가치를 말할지 정리할게요.', { exact: false })).toBeVisible();
  await page.getByLabel('고객사').fill(customer);
  await page.waitForURL(/\/vp\/vp_[^/]+\/materials$/, { timeout: 60_000 });
  if (opts.note) await page.locator('#vp-note').fill(opts.note);
  if (opts.rfp !== false) {
    await page.getByTestId('vp-file-input').setInputFiles({ name: 'A커피_디지털메뉴보드_RFP.txt', mimeType: 'text/plain', buffer: Buffer.from(RFP_TEXT, 'utf8') });
    await expect(page.getByLabel('첨부한 파일')).toContainText('A커피_디지털메뉴보드_RFP.txt', { timeout: 60_000 });
  }
  return page.url().match(/\/vp\/(vp_[^/]+)\//)![1];
}

/** `가치 구조 만들기` → (VP1A · VP1Q 를 기본값으로 지나) VP2 */
export async function collectToStructure(page: Page, onScreen?: (route: 'review' | 'questions') => Promise<void>) {
  await page.getByRole('button', { name: '가치 구조 만들기' }).click();
  await page.waitForURL(/\/(questions|materials\/review|structure)$/, { timeout: 90_000 });
  for (let i = 0; i < 3 && !/\/structure$/.test(page.url()); i++) {
    if (/\/materials\/review$/.test(page.url())) {
      await expect(page.getByText('뽑은 재료')).toBeVisible();
      await onScreen?.('review');
      await page.getByRole('button', { name: '가치 구조로' }).click();
    } else {
      await expect(page.getByRole('button', { name: '이대로 진행' })).toBeVisible();
      await onScreen?.('questions');
      await page.getByRole('button', { name: '이대로 진행' }).click();
    }
    await page.waitForURL(/\/(questions|materials\/review|structure)$/, { timeout: 90_000 });
  }
  await expect(page.getByText('그 밖에 정한 것')).toBeVisible({ timeout: 20_000 });
}

/** API 로 바로 — 작업 정리(보관) */
export async function archive(page: Page, id: string) {
  await page.request.post(`/api/vp/v1/vps/${id}:archive`).catch(() => undefined);
}
