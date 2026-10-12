/**
 * 콘텐츠 목록 · Storyboard 목록(보드 webapp1 List · SB0 v61) — 실제 스택(게이트웨이 + storyboard · dss).
 *   가운데 「새 ○○ 만들기」 1100×156(머리 아래 22) → 44 → 작업 내역 → 16 → 그리드 260 × 4(간격 20) · 썸네일 148 · n/N 단계.
 * 실행: WM_E2E_SUITE=shell WM_E2E_DEV=1 WM_E2E_PORT=5197 npx playwright test e2e/shell/content-list.spec.ts --workers=1
 */
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { expect, test, type Locator } from '@playwright/test';
import { internalHeaders, makeStoryboard, shotTo, tag } from './flowkit';

const DIR = path.join(path.dirname(fileURLToPath(import.meta.url)), '__screens__');
const box = async (l: Locator) => (await l.boundingBox())!;

/** 보기 팝업 카드(= 목록 썸네일 재료) — 보드 ContentPopup DSS-01 그대로 */
const DSS_CARD = {
  title: '용산 오피스 공간별 제품',
  facts: [['업종', '오피스 · 업무시설'], ['공간 · 제품', '3 · 6'], ['솔루션', 'MagicINFO · SmartThings Pro']],
  groups: [
    { h: '로비', sub: '제품 3', lines: [{ t: 'The Wall IAB 146" · 1식' }, { t: 'Smart Signage QM55C · 2대' }, { t: '삼성 키오스크 · 1대' }] },
    { h: '회의실', sub: '제품 2', lines: [{ t: 'Flip Pro WA75D · 실 수', note: '확인 필요' }, { t: 'Smart Signage QB55C · 실당 1대' }] },
    { h: '주차장', sub: '제품 1', lines: [{ t: '옥외형 사이니지 OHC55', note: '확장' }] },
  ],
  line: '공간 3 · 제품 6 · 솔루션 2',
};

test('List v61 — 가운데 새로 만들기 · 작업 내역 그리드 · 썸네일 · n/N 단계(저장 · 초안)', async ({ page, request }) => {
  test.setTimeout(120_000);
  const t = tag();
  const saved = await makeStoryboard(request, { name: `목록 저장 ${t}` });
  const ref = `DSS-L${t}`;
  const put = await request.put(`/api/storyboard/v1/flows/${saved.id}/stages/dss`, {
    headers: internalHeaders('dss'),
    data: { ref, ver: 1, res_id: `dss_list_${t}`, title: `용산 오피스 공간별 제품 ${t}`, value: { counts: { spaces: 3, products: 6, solutions: 2 } }, md: '- 공간 3 · 제품 6', card: DSS_CARD },
  });
  expect(put.ok()).toBe(true);
  // 초안 — 저장 전 DSS(2/3 공간 · 제품)
  const draftSb = await makeStoryboard(request, { name: `목록 초안 ${t}` });
  const dr = await request.post('/api/dss/v1/dss', { data: { sb_id: draftSb.id } });
  expect(dr.ok()).toBe(true);
  const draft = await dr.json();

  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto('/dss');
  const savedCard = page.locator('.fl-card').filter({ hasText: `${ref} v1` });
  const draftCard = page.locator('.fl-card').filter({ hasText: draft.code ?? draft.title });
  await expect(savedCard).toHaveCount(1, { timeout: 20_000 });
  await expect(draftCard).toHaveCount(1);

  // 새로 만들기 — 본문 폭 전체(1100) · 높이 156 · 머리 아래 22 · 단계 흐름
  const hero = page.locator('.fl-hero');
  await expect(hero).toHaveAttribute('href', '/dss/new');
  await expect(hero.locator('.fl-hero__label')).toHaveText('새 DSS 만들기');
  await expect(hero.locator('.fl-hero__step')).toHaveText(['1Storyboard', '2공간 · 제품', '3솔루션']);
  await expect(hero.locator('.fl-hero__note')).toHaveText('모두 3단계');
  const hb = await box(hero);
  const head = await box(page.locator('.fl-listhead'));
  expect(hb.width).toBe(1100);
  expect(hb.height).toBe(156);
  expect(Math.round(hb.y - (head.y + head.height))).toBe(22);
  // 가운데 정렬: 글자 묶음의 가운데 = 버튼의 가운데
  const lb = await box(hero.locator('.fl-hero__main'));
  expect(Math.abs(lb.x + lb.width / 2 - (hb.x + hb.width / 2))).toBeLessThanOrEqual(1);

  // 작업 내역 — 44 아래 · 그리드 16 아래 · 카드 260 · 간격 20 · 썸네일 148
  const hh = await box(page.locator('.fl-histhead'));
  expect(Math.round(hh.y - (hb.y + hb.height))).toBe(44);
  await expect(page.locator('.fl-histhead h2')).toHaveText('작업 내역');
  const grid = await box(page.locator('.fl-grid'));
  expect(Math.round(grid.y - (hh.y + hh.height))).toBe(16);
  const cards = page.locator('.fl-grid > .fl-card');
  const c0 = await box(cards.nth(0));
  const c1 = await box(cards.nth(1));
  expect(c0.width).toBe(260);
  expect(Math.round(c1.x - (c0.x + c0.width))).toBe(20);
  expect((await box(savedCard.locator('.fl-thumb'))).height).toBe(148);

  // 저장한 것 — 썸네일 = 보기 팝업 카드 · 배지 완성 · 3/3 단계 · 막대 3칸 모두 지난 단계 · 제목은 편집(보기) 화면으로
  await expect(savedCard.locator('.fl-mini__fact b')).toHaveText(['오피스 · 업무시설', '3 · 6', 'MagicINFO · SmartThings Pro']);
  await expect(savedCard.locator('.fl-mini__gh b')).toHaveText(['로비', '회의실', '주차장']);
  await expect(savedCard.locator('.fl-mini__tag--warn')).toHaveText('확인 필요');
  await expect(savedCard.locator('.fl-thumb__badge')).toHaveText('완성');
  await expect(savedCard.locator('.fl-steptxt')).toHaveText('3/3단계· 완성');
  await expect(savedCard.locator('.fl-seg--done')).toHaveCount(3);
  await expect(savedCard.locator('.fl-cardtitle')).toHaveAttribute('href', `/dss/dss_list_${t}`);
  await expect(savedCard.locator('.fl-sbchip')).toHaveText(saved.name);
  await expect(savedCard.locator('.fl-del')).toHaveCount(0);

  // 초안 — 빈 틀 썸네일 · 배지 작성 중 · 2/3 단계 · 공간 · 제품(지난 1 · 지금 1 · 남은 1) · 손을 올리면 ×
  await expect(draftCard.locator('.fl-thumb__badge')).toHaveText('작성 중');
  await expect(draftCard.locator('.fl-mini__note')).toHaveText('작성 중 · 공간 · 제품 단계');
  await expect(draftCard.locator('.fl-steptxt')).toHaveText('2/3단계· 공간 · 제품');
  await expect(draftCard.locator('.fl-seg')).toHaveClass([/fl-seg--done/, /fl-seg--cur/, /fl-seg--todo/]);
  await expect(draftCard.locator('.fl-sbchip')).toHaveText(draftSb.name);
  await draftCard.hover();
  await expect(draftCard.getByRole('button', { name: /지우기$/ })).toBeVisible();
  await page.mouse.move(0, 0);
  await shotTo(page, DIR, 'DS0-new');

  // 썸네일 · 제목 모두 같은 화면으로(썸네일은 탭 순서에서 빠짐)
  await expect(draftCard.locator('.fl-thumb')).toHaveAttribute('tabindex', '-1');
  await draftCard.locator('.fl-cardtitle').click();
  await expect(page).toHaveURL(new RegExp(`/dss/${draft.id}$`));

  // 새로 만들기 → Gate
  await page.goto('/dss');
  await page.locator('.fl-hero').click();
  await expect(page).toHaveURL(/\/dss\/new$/);
  await request.delete(`/api/dss/v1/dss/${draft.id}`);
});

test('List v62 — 요구사항 1/1 단계 · 빈 목록(VP)은 범례 없이 안내', async ({ page, request }) => {
  test.setTimeout(90_000);
  const sb = await makeStoryboard(request, { name: `목록 요구 ${tag()}` }) as { id: string; name: string; cells: Array<{ key: string; ref: string | null }> };
  const rqRef = sb.cells.find((c) => c.key === 'rq')!.ref!;
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto('/requirements');
  await expect(page.locator('.fl-hero__label')).toHaveText('새 요구사항 만들기');
  await expect(page.locator('.fl-hero__step')).toHaveText(['1요구사항 입력']);
  const card = page.locator('.fl-card').filter({ hasText: `${rqRef} v1` });
  await expect(card.locator('.fl-steptxt')).toHaveText('1/1단계· 완성');
  await expect(card.locator('.fl-mini__fact b').first()).toHaveText('E 자산운용');
  await shotTo(page, DIR, 'RQ0-new');

  // VP — 저장된 VP 가 없으면 범례 없이 빈 안내(위 「새 VP 만들기」)
  const vps = await (await request.get('/api/storyboard/v1/flows/contents/vp')).json();
  const drafts = await (await request.get('/api/vp/v1/value-maps?limit=200')).json();
  test.skip(vps.items.length > 0 || (drafts.items ?? []).some((x: { status: string }) => x.status !== 'done'), '다른 시험이 VP 를 남겼어요');
  await page.goto('/vp');
  await expect(page.locator('.fl-empty--hist')).toContainText('아직 만든 VP가 없어요');
  await expect(page.locator('.fl-empty--hist')).toContainText('위 「새 VP 만들기」로 시작해요 · 최소 DSS까지 된 Storyboard가 있어야 해요.');
  await expect(page.locator('.fl-seglegend')).toHaveCount(0);
  await expect(page.locator('.fl-histcount')).toHaveText('0');
  await shotTo(page, DIR, 'VP0-new');
});

test('SB0 v61 — 가운데 시작 · Storyboard 카드(진행 8칸 · 요약본 썸네일 · n/8 단계 · Key message)', async ({ page, request }) => {
  test.setTimeout(90_000);
  const sb = await makeStoryboard(request, { name: `목록 SB ${tag()}`, dss: true });
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto('/storyboard');
  const hero = page.locator('.fl-hero');
  await expect(hero.locator('.fl-hero__label')).toHaveText('새 고객 요구사항으로 시작');
  await expect(hero).toHaveAttribute('href', '/requirements/new');
  expect((await box(hero)).width).toBe(1100);
  const card = page.locator(`.sbf-card[data-sb="${sb.id}"]`);
  await expect(card).toHaveCount(1, { timeout: 20_000 });
  await expect(card.locator('.sbf-cardname b')).toHaveText(sb.name);
  await expect(card.locator('.fl-steptxt')).toHaveText('2/8단계· DSS까지');
  await expect(card.locator('.fl-seg--done')).toHaveCount(2);
  await expect(card.locator('.sbf-mcell--on')).toHaveCount(2);
  await expect(card.locator('.sbf-mmd--h1')).toHaveText(`# ${sb.name} — Storyboard 요약`);
  await expect(card.locator('.sbf-km')).toHaveText('Key message 아직 없음');
  expect((await box(card)).width).toBe(260);
  await shotTo(page, DIR, 'SB0-new');
  await card.locator('.sbf-cardlink').click();
  await expect(page).toHaveURL(new RegExp(`/storyboard/flow/${sb.id}$`));
});
