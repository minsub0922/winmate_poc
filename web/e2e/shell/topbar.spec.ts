/**
 * 00-shell §8.4 상단바(T) · §8.5 제품 탐색(P) · §8.6 솔루션 탐색(S) · §8.15 X-01.
 * "작업 있음" = 개발 화면 `/_dev/shell?task=1&…`(§8.0).
 */
import { expect, test, type Page } from '@playwright/test';
import { devLog, setupShell } from './fixtures/mock';

const css = (loc: import('@playwright/test').Locator, prop: string) => loc.evaluate((el, p) => getComputedStyle(el).getPropertyValue(p), prop);
const dialog = (page: Page, name: string) => page.getByRole('dialog', { name });
const NO_TASK = {
  product: '진행 중인 작업이 없어 탐색만 할 수 있어요. 작업을 시작하면 제품을 추가할 수 있습니다.',
  solution: '진행 중인 작업이 없어 탐색만 할 수 있어요.',
  image: '진행 중인 작업이 없어 탐색만 할 수 있어요.',
  case: '진행 중인 작업이 없어 탐색만 할 수 있어요. 원문 열기는 계속 가능합니다.',
};

test.beforeEach(async ({ page }) => { await setupShell(page); });

test.describe('상단바 (T)', () => {
  test('T-01 브레드크럼 — 홈 / 기능 화면', async ({ page }) => {
    await page.goto('/');
    const crumbs = page.getByRole('navigation', { name: '현재 위치' });
    await expect(crumbs).toHaveText('홈');
    await page.goto('/spec/new');
    await expect(crumbs).toHaveText('홈/Spec 시트 생성/새 작업');
    const cur = crumbs.locator('[aria-current="page"]');
    await expect(cur).toHaveText('새 작업');
    expect(await css(cur, 'color')).toBe('rgb(18, 20, 23)');
    expect(await css(cur, 'font-weight')).toBe('600');
  });

  test('T-02 · T-03 버튼 순서 · 제품 탐색 열기(700×540, 버튼 오른쪽 맞춤, 탭 모양)', async ({ page }) => {
    await page.goto('/');
    const pills = page.locator('.sh-pill');
    await expect(pills).toHaveText(['제품 탐색', '솔루션 탐색', '이미지 검색', '유관 사례 검색']);
    const btn = page.getByRole('button', { name: '제품 탐색' });
    await btn.click();
    const d = dialog(page, '제품 탐색');
    await expect(d).toBeVisible();
    await expect(page).toHaveURL(/[?&]pop=product/);
    const db = (await d.boundingBox())!;
    const bb = (await btn.boundingBox())!;
    expect(db.width).toBe(700);
    expect(db.height).toBe(540);
    expect(Math.round(db.x + db.width)).toBe(Math.round(bb.x + bb.width));
    expect(Math.round(db.y)).toBe(Math.round(bb.y + 35));
    expect(await css(btn, 'border-top-color')).toBe('rgb(20, 40, 160)');
    expect(await css(btn, 'border-bottom-color')).toBe('rgb(255, 255, 255)');
    expect(await css(btn, 'border-top-left-radius')).toBe('12px');
    expect(await css(btn, 'border-bottom-left-radius')).toBe('0px');
    expect(await css(d, 'border-top-right-radius')).toBe('0px');
    expect(await css(d, 'border-top-left-radius')).toBe('14px');
  });

  test('T-04 다른 버튼 → 하나만 · T-05 닫기 · Esc · 바깥 클릭', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('button', { name: '제품 탐색' }).click();
    await expect(dialog(page, '제품 탐색')).toBeVisible();
    await page.getByRole('button', { name: '솔루션 탐색' }).click();
    await expect(dialog(page, '솔루션 탐색')).toBeVisible();
    await expect(dialog(page, '제품 탐색')).toHaveCount(0);
    await expect(page.locator('[role="dialog"][data-popover]')).toHaveCount(1);
    // 닫기
    await dialog(page, '솔루션 탐색').getByRole('button', { name: '닫기' }).click();
    await expect(page.locator('[data-popover]')).toHaveCount(0);
    await expect(page).not.toHaveURL(/pop=/);
    // Esc
    await page.getByRole('button', { name: '이미지 검색' }).click();
    await expect(dialog(page, '이미지 검색')).toBeVisible();
    await page.keyboard.press('Escape');
    await expect(page.locator('[data-popover]')).toHaveCount(0);
    await expect(page).not.toHaveURL(/pop=/);
    // 바깥 클릭
    await page.getByRole('button', { name: '유관 사례 검색' }).click();
    await expect(dialog(page, '유관 사례 검색')).toBeVisible();
    await page.mouse.click(400, 850);
    await expect(page.locator('[data-popover]')).toHaveCount(0);
    await expect(page).not.toHaveURL(/pop=/);
    // 같은 버튼 다시 → 닫기
    await page.getByRole('button', { name: '제품 탐색' }).click();
    await page.getByRole('button', { name: '제품 탐색' }).click();
    await expect(page.locator('[data-popover]')).toHaveCount(0);
  });

  test('T-06 `/?pop=image&q=카페 메뉴보드` 로 들어오면 이미지 검색 열림 · 입력값', async ({ page }) => {
    await page.goto('/?pop=image&q=' + encodeURIComponent('카페 메뉴보드'));
    await expect(dialog(page, '이미지 검색')).toBeVisible();
    await expect(dialog(page, '이미지 검색').getByRole('textbox', { name: '이미지 검색' })).toHaveValue('카페 메뉴보드');
  });

  test('T-07 작업 없음 — 4종 모두 추가 비활성 · 안내', async ({ page }) => {
    const urls = { product: '/?pop=product&node=fam_G000182628', solution: '/?pop=solution', image: '/?pop=image&q=카페 메뉴보드', case: '/?pop=case&q=프랜차이즈 메뉴보드' };
    for (const [kind, url] of Object.entries(urls) as Array<[keyof typeof NO_TASK, string]>) {
      await page.goto(url);
      const d = page.locator(`[data-popover="${kind}"]`);
      await expect(d).toBeVisible();
      if (kind !== 'image') {
        const adds = d.locator('.wm-addbtn');
        await expect(adds.first()).toBeVisible();
        const n = await adds.count();
        expect(n).toBeGreaterThan(0);
        for (let i = 0; i < n; i++) {
          await expect(adds.nth(i)).toHaveText('+ 추가');
          await expect(adds.nth(i)).toBeDisabled();
          await expect(adds.nth(i)).toHaveAttribute('title', '진행 중인 작업이 없어 추가할 수 없습니다');
        }
      } else {
        await expect(d.locator('.wm-tilewrap').first()).toBeVisible();
        await expect(d.locator('.wm-tile__check')).toHaveCount(0);
      }
      const foot = d.locator('[data-footer="no-task"]');
      await expect(foot).toContainText(NO_TASK[kind]);
      const addAll = foot.getByRole('button', { name: '현재 작업에 추가' });
      await expect(addAll).toBeDisabled();
      await expect(addAll).toHaveAttribute('title', '진행 중인 작업이 없습니다');
    }
  });

  test('T-08 작업 있음 — + 추가 → ✓ 선택 · 트레이 · 다시 누르면 해제', async ({ page }) => {
    await page.goto('/_dev/shell?task=1&pop=product&node=fam_G000182628');
    const d = dialog(page, '제품 탐색');
    const add = d.getByRole('button', { name: '추가 QM43C' });
    await add.click();
    const sel = d.getByRole('button', { name: '선택 해제 QM43C' });
    await expect(sel).toHaveText('✓ 선택');
    expect(await css(sel, 'background-color')).toBe('rgb(20, 40, 160)');
    const foot = d.locator('[data-footer="task"]');
    await expect(foot).toContainText('선택 1');
    await expect(foot.locator('.wm-traychip')).toHaveText(['QM43C×']);
    await sel.click();
    await expect(d.getByRole('button', { name: '추가 QM43C' })).toHaveText('+ 추가');
    await expect(foot).toContainText('선택 0');
  });

  test('T-09 added 항목 → ✓ 추가됨 · 비활성 · 손잡이 없음', async ({ page }) => {
    await page.goto('/_dev/shell?task=1&accepts=product&added=kb:model:mdl_LH43QMCEBGCXKR&pop=product&node=fam_G000182628');
    const d = dialog(page, '제품 탐색');
    const btn = d.getByRole('button', { name: '추가 QM43C' });
    await expect(btn).toHaveText('✓ 추가됨');
    await expect(btn).toBeDisabled();
    await expect(btn).toHaveAttribute('title', '이미 현재 작업에 있습니다');
    const row = d.locator('[data-model="LH43QMCEBGCXKR"]');
    await expect(row).not.toHaveAttribute('draggable', 'true');
    await expect(row.locator('svg[viewBox="0 0 10 14"]')).toHaveCount(0);
    await expect(d.locator('[data-model="LH55QMCEBGCXKR"]')).toHaveAttribute('draggable', 'true');
  });

  test('T-10 선택 0 → 추가 비활성 · 선택 2 → onAdd 한 번 · ✓ 추가됨 · 트레이 비움', async ({ page }) => {
    await page.goto('/_dev/shell?task=1&pop=product&node=fam_G000182628');
    const d = dialog(page, '제품 탐색');
    const addAll = d.getByRole('button', { name: '현재 작업에 추가' });
    await expect(addAll).toBeDisabled();
    await d.getByRole('button', { name: '추가 QM43C' }).click();
    await d.getByRole('button', { name: '추가 QM55C' }).click();
    await expect(addAll).toBeEnabled();
    await addAll.click();
    await expect(d.getByRole('button', { name: '추가 QM43C' })).toHaveText('✓ 추가됨');
    await expect(d.getByRole('button', { name: '추가 QM55C' })).toHaveText('✓ 추가됨');
    await expect(d.locator('[data-footer="task"]')).toContainText('선택 0');
    await expect(d.locator('.wm-traychip')).toHaveCount(0);
    const log = (await devLog(page)).filter((e) => e.kind === 'onAdd');
    expect(log).toHaveLength(1);
    expect(log[0]).toMatchObject({ type: 'product', refs: ['kb:model:mdl_LH43QMCEBGCXKR', 'kb:model:mdl_LH55QMCEBGCXKR'] });
  });

  test('T-11 onAdd 실패 → 선택 유지 · 안내', async ({ page }) => {
    await page.goto('/_dev/shell?task=1&fail=1&pop=product&node=fam_G000182628');
    const d = dialog(page, '제품 탐색');
    await d.getByRole('button', { name: '추가 QM55C' }).click();
    await d.getByRole('button', { name: '현재 작업에 추가' }).click();
    await expect(d.locator('[data-footer="task"]')).toContainText('추가하지 못했어요. 다시 시도해 주세요.');
    await expect(d.getByRole('button', { name: '선택 해제 QM55C' })).toHaveText('✓ 선택');
    await expect(d.locator('.wm-traychip')).toHaveCount(1);
  });

  test('T-12 같은 작업에서 닫았다 다시 열면 검색어 · 선택 유지', async ({ page }) => {
    await page.goto('/_dev/shell?task=1');
    await page.getByRole('button', { name: '제품 탐색' }).click();
    let d = dialog(page, '제품 탐색');
    await d.getByRole('textbox', { name: '제품 검색' }).fill('QM5');
    await expect(d.locator('[data-model="LH55QMCEBGCXKR"]')).toBeVisible();
    await d.getByRole('button', { name: '추가 QM55C' }).click();
    await d.getByRole('button', { name: '닫기' }).click();
    await expect(page.locator('[data-popover]')).toHaveCount(0);
    await page.getByRole('button', { name: '제품 탐색' }).click();
    d = dialog(page, '제품 탐색');
    await expect(d.getByRole('textbox', { name: '제품 검색' })).toHaveValue('QM5');
    await expect(d.getByRole('button', { name: '선택 해제 QM55C' })).toBeVisible();
    await expect(d.locator('[data-footer="task"]')).toContainText('선택 1');
    // 솔루션 업종 칩도 유지
    await page.getByRole('button', { name: '솔루션 탐색' }).click();
    await dialog(page, '솔루션 탐색').getByRole('button', { name: '교육' }).click();
    await page.keyboard.press('Escape');
    await page.getByRole('button', { name: '솔루션 탐색' }).click();
    await expect(dialog(page, '솔루션 탐색').getByRole('button', { name: '교육' })).toHaveAttribute('aria-pressed', 'true');
  });
});

test.describe('제품 탐색 (P)', () => {
  test('P-01 · P-02 · P-03 트리 L1 9 · 사이니지 자식 · LCD 고르면 경로 · 열 · 행', async ({ page }) => {
    await page.goto('/?pop=product');
    const d = dialog(page, '제품 탐색');
    const tree = d.getByRole('navigation', { name: '제품 분류' });
    const l1 = ['사이니지', 'TV/음향', 'IT·PC·프린팅', '모바일', '시스템에어컨·공조', '리빙가전', '주방가전', '솔루션', '서비스'];
    await expect(tree.locator('[data-node^="top_"]')).toHaveCount(9);
    await expect(tree.locator('[data-node^="top_"] .sh-tree__label')).toHaveText(l1);
    // 처음 열기 = 첫 L1 펼침
    await expect(tree.locator('[data-node="top_display"]')).toHaveAttribute('aria-expanded', 'true');
    await expect(tree.locator('[data-node^="cat_"] .sh-tree__label')).toHaveText(['스마트 LED 사이니지', '스마트 LCD 사이니지']);
    await tree.locator('[data-node="cat_smart-signage"]').click();
    await expect(page).toHaveURL(/node=cat_smart-signage/);
    await expect(d.locator('.sh-path')).toHaveText('전체›사이니지›스마트 LCD 사이니지');
    await expect(d.locator('.sh-mhead [role="columnheader"]')).toHaveText(['모델', '크기', '밝기', '해상도']);
    expect(await d.locator('[data-model]').count()).toBeGreaterThan(0);
  });

  test('P-04 · P-05 시리즈(fam_G000182628) 7행 · 크기 오름차순 · 값', async ({ page }) => {
    await page.goto('/?pop=product&node=fam_G000182628');
    const d = dialog(page, '제품 탐색');
    const rows = d.locator('[data-model]');
    await expect(rows).toHaveCount(7);
    await expect(d.locator('[data-col="size"]')).toHaveText(['32"', '43"', '50"', '55"', '65"', '75"', '85"']);
    const r55 = d.locator('[data-model="LH55QMCEBGCXKR"]');
    await expect(r55.locator('[data-col="brightness"]')).toHaveText('500nit');
    await expect(r55.locator('[data-col="resolution"]')).toHaveText('4K UHD');
    const r32 = d.locator('[data-model="LH32QMCEBGCXKR"]');
    await expect(r32.locator('[data-col="brightness"]')).toHaveText('400nit');
    await expect(r32.locator('[data-col="resolution"]')).toHaveText('FHD');
    await expect(d.locator('[data-col="size"]', { hasText: '98"' })).toHaveCount(0);
    // 깊은 링크에서도 경로 · 트리 펼침
    await expect(d.locator('.sh-path')).toHaveText('전체›사이니지›스마트 LCD 사이니지›QMC Series');
    await expect(d.locator('[data-node="fam_G000182628"]')).toHaveAttribute('aria-current', 'true');
  });

  test('P-06 · P-07 검색 → 전체 › 검색 결과 · 지우면 노드로 · 결과 없음', async ({ page }) => {
    await page.goto('/?pop=product&node=fam_G000182628');
    const d = dialog(page, '제품 탐색');
    const q = d.getByRole('textbox', { name: '제품 검색' });
    await q.fill('LH55QMC');
    await expect(d.locator('[data-model="LH55QMCEBGCXKR"]')).toBeVisible();
    await expect(d.locator('.sh-path')).toHaveText('전체›검색 결과');
    await expect(page).toHaveURL(/q=LH55QMC/);
    await q.fill('');
    await expect(d.locator('[data-model]')).toHaveCount(7);
    await expect(d.locator('.sh-path')).toContainText('QMC Series');
    await q.fill('zzzz');
    await expect(d.getByText('‘zzzz’에 맞는 제품이 없어요. 제품명이나 모델코드 일부로 찾아보세요.')).toBeVisible();
  });

  test('P-08 상세 aria-label · 시트 spec 탭', async ({ page }) => {
    await page.goto('/?pop=product&node=fam_G000182628');
    const d = dialog(page, '제품 탐색');
    const link = d.getByRole('link', { name: 'QM55C 상세 보기 — 스펙 · 이미지 · 활용 사례' });
    await expect(link).toHaveText('상세');
    await link.click();
    await expect(dialog(page, 'QM55C 제품 상세')).toBeVisible();
    await expect(page).toHaveURL(/detail=product%3ALH55QMCEBGCXKR|detail=product:LH55QMCEBGCXKR/);
    await expect(page.getByRole('tab', { name: '스펙 · 자료' })).toHaveAttribute('aria-selected', 'true');
  });

  test('P-09 끌기 불가 안내 / 끌기 가능 손잡이 · cursor grab', async ({ page }) => {
    await page.goto('/?pop=product&node=fam_G000182628');
    let d = dialog(page, '제품 탐색');
    await expect(d.locator('.sh-pop__bar--path')).toContainText("'상세'에서 스펙 · 이미지 · 활용 사례를 모두 볼 수 있어요");
    await expect(d.locator('[data-model][draggable="true"]')).toHaveCount(0);
    await page.goto('/_dev/shell?task=1&accepts=product&pop=product&node=fam_G000182628');
    d = dialog(page, '제품 탐색');
    await expect(d.locator('.sh-pop__bar--path')).toContainText('끌어서 바로 추가');
    const rows = d.locator('[data-model]');
    await expect(rows).toHaveCount(7);
    for (let i = 0; i < 7; i++) {
      await expect(rows.nth(i)).toHaveAttribute('draggable', 'true');
      expect(await css(rows.nth(i), 'cursor')).toBe('grab');
      await expect(rows.nth(i).locator('svg[viewBox="0 0 10 14"]')).toHaveCount(1);
    }
  });

  test('P-10 행 썸네일 56×38 contain · alt 형식', async ({ page }) => {
    await page.goto('/?pop=product&node=fam_G000182628');
    const d = dialog(page, '제품 탐색');
    const thumb = d.locator('[data-model="LH65QMCEBGCXKR"] .sh-mthumb');
    const b = (await thumb.boundingBox())!;
    expect(b.width).toBe(56);
    expect(b.height).toBe(38);
    const img = thumb.locator('img');
    await expect(img).toHaveAttribute('alt', 'QMC 시리즈 정면 (QM55C 공식 제품 이미지)');
    expect(await css(img, 'object-fit')).toBe('contain');
  });

  test('P-11 트레이 칩 × → + 추가 로', async ({ page }) => {
    await page.goto('/_dev/shell?task=1&pop=product&node=fam_G000182628');
    const d = dialog(page, '제품 탐색');
    await d.getByRole('button', { name: '추가 QM43C' }).click();
    await d.getByRole('button', { name: '추가 QM65C' }).click();
    await expect(d.locator('.wm-traychip')).toHaveCount(2);
    await d.locator('.wm-traychip', { hasText: 'QM65C' }).getByRole('button', { name: '선택 해제' }).click();
    await expect(d.getByRole('button', { name: '추가 QM65C' })).toHaveText('+ 추가');
    await expect(d.locator('[data-footer="task"]')).toContainText('선택 1');
  });
});

test.describe('솔루션 탐색 (S)', () => {
  const SOL = [
    ['MagicINFO', '디스플레이 · 설치형 사이니지 CMS · 콘텐츠 · 스케줄 · 데이터 연동'],
    ['Samsung VXT', '디스플레이 · 클라우드 사이니지 CMS · Canvas · 원격 관리'],
    ['SmartThings Pro', '공간 · 에너지 · 여러 사업장 IoT · 에너지 대시보드'],
    ['b.IoT', '공간 · 에너지 · 공조 중심 빌딩 관리'],
    ['LYNK Cloud', '호스피탈리티 · 호텔 객실 TV · 투숙객 서비스'],
    ['Knox Suite', '모바일 · 업무용 갤럭시 등록 · 관리 · 보안'],
    ['Knox Capture', '모바일 · 갤럭시 카메라로 바코드 스캔'],
    ['Samsung DeX', '모바일 · 휴대폰을 모니터에 연결해 PC처럼'],
    ['삼성 콜드체인', '공조 · 냉장 · 냉동 쇼케이스 · 저장고 + 에어컨 통합 관리'],
    ['삼성 통합공조', '공조 · 개별공조 + 중앙공조 + b.IoT 통합'],
    ['SAC 제어 시스템', '공조 · 리모컨부터 DMS · BMS 연동 · 전력량 분배'],
  ];

  test('S-01 · S-02 · S-03 11행 순서·글 · 업종 칩 · 호스피탈리티 필터', async ({ page }) => {
    await page.goto('/?pop=solution');
    const d = dialog(page, '솔루션 탐색');
    await expect(d.locator('[data-solution] [data-name]')).toHaveText(SOL.map((s) => s[0]));
    await expect(d.locator('[data-solution] [data-desc]')).toHaveText(SOL.map((s) => s[1]));
    await expect(d.getByRole('group', { name: '업종' }).locator('.wm-chip')).toHaveText(['리테일', '호스피탈리티', '교육', '헬스케어', '오피스']);
    await d.getByRole('button', { name: '호스피탈리티' }).click();
    await expect(d.locator('[data-solution="lynk_cloud"]')).toBeVisible();
    await expect(d.locator('[data-solution="knox_capture"]')).toHaveCount(0);
    await d.getByRole('button', { name: '호스피탈리티' }).click();
    await expect(d.locator('[data-solution]')).toHaveCount(11);
  });

  test('S-04 상세 → `detail=solution:magicinfo&tab=overview`', async ({ page }) => {
    await page.goto('/?pop=solution');
    await dialog(page, '솔루션 탐색').getByRole('link', { name: 'MagicINFO 상세 보기 — 개요 · 이미지 · 활용 사례' }).click();
    await expect(dialog(page, 'MagicINFO 솔루션 상세')).toBeVisible();
    await expect(page).toHaveURL(/detail=solution%3Amagicinfo&tab=overview|detail=solution:magicinfo&tab=overview/);
  });

  test('S-05 · S-06 작업 있음 — 선택 푸터 · 아이콘 상자 · 선택 행 모양', async ({ page }) => {
    await page.goto('/_dev/shell?task=1&pop=solution');
    const d = dialog(page, '솔루션 탐색');
    await expect(d.locator('[data-footer="task"]')).toContainText('선택 0 · 없음');
    const box = d.locator('[data-solution="magicinfo"] .sh-solicon');
    const b = (await box.boundingBox())!;
    expect(b.width).toBe(36);
    expect(b.height).toBe(36);
    await d.getByRole('button', { name: '추가 MagicINFO' }).click();
    await expect(d.locator('[data-footer="task"]')).toContainText('선택 1 · MagicINFO');
    expect(await css(box, 'background-color')).toBe('rgb(234, 238, 251)');
    expect(await box.locator('svg').getAttribute('stroke')).toBe('var(--wm-brand)');
    expect(await css(d.locator('[data-solution="magicinfo"]'), 'border-top-color')).toBe('rgb(20, 40, 160)');
  });
});

test('X-01 팝오버 4종 role=dialog · 이름 · 검색 입력 접근 이름', async ({ page }) => {
  const pairs: Array<[string, string]> = [['제품 탐색', '제품 검색'], ['솔루션 탐색', '솔루션 검색'], ['이미지 검색', '이미지 검색'], ['유관 사례 검색', '사례 검색']];
  await page.goto('/');
  for (const [name, input] of pairs) {
    await page.locator('.sh-pill', { hasText: name }).click();
    const d = dialog(page, name);
    await expect(d).toBeVisible();
    await expect(d.getByRole('textbox', { name: input })).toBeVisible();
  }
});
