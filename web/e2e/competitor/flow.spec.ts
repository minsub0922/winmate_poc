/**
 * 경쟁사 분석 기본 흐름(실제 competitor · 플랫폼 · mock 모델) — CA0 → CA1 → CA1G → CA2 → CA3 → CA4(3 보기) → CA4D(+근거 패널) → CA5.
 * AC-CA-01 · 04 · 07 · 18 · 25 · 26 · 32 · 35 · 39 · 41 · 44 · 47 화면 쪽.
 */
import { expect, test } from '@playwright/test';
import { A_TEXT, CA_ID, REAL, SETUP_MS, api, backendDown, budget, noRealNames, shot, waitStatus } from './helpers';

test.describe.configure({ mode: 'serial', timeout: SETUP_MS });

test('CA0 → CA1 → 찾기 → CA2 → 분석 → CA4 → CA4D → CA5 한 바퀴', async ({ page, request }) => {
  budget(240_000);
  const down = await backendDown(request);
  test.skip(!!down, down ?? '');

  // CA0 작업 목록
  await page.goto('/competitor');
  await expect(page.getByRole('heading', { name: '경쟁사 분석 작업' })).toBeVisible();
  await expect(page.getByText(/분석 \d+건 · 업데이트 필요 \d+건 · 경쟁사는 실명 없이 A · B · C 로 표기해요/)).toBeVisible();
  await expect(page.getByRole('tablist', { name: '상태 필터' }).getByRole('tab')).toHaveText([/전체\s*\d+/, /완료\s*\d+/, /확인 중\s*\d+/]);
  await expect(page.getByText('다른 곳에서 시작')).toBeVisible();
  await noRealNames(page);
  await shot(page, 'ca0-list');

  // CA1 넣기 · 자유 양식
  await page.getByRole('link', { name: '새 분석' }).click();
  await expect(page).toHaveURL(/\/competitor\/new$/);
  await expect(page.getByRole('heading', { name: '어떤 고객의 경쟁사를 찾을까요?' })).toBeVisible();
  await expect(page.getByRole('tab', { name: '자유 양식' })).toHaveAttribute('aria-selected', 'true');
  const find = page.getByRole('button', { name: '경쟁사 찾기' });
  await expect(find).toBeDisabled();                                   // AC-CA-04
  await expect(page.getByText('고객사 · 업종 · 장소 · 제품까지 알려 주면 경쟁사를 훨씬 잘 찾아요.', { exact: false })).toBeVisible();
  await page.getByLabel('고객 · 사업 설명').fill(A_TEXT);
  await expect(find).toBeEnabled();
  const strip = page.getByRole('group', { name: '입력에서 읽은 것' });
  await expect(strip).toContainText('고객사·A 커피 프랜차이즈', { timeout: 15_000 });     // AC-CA-01
  await expect(strip).toContainText('업종·외식 · 카페');
  await expect(strip).toContainText('장소·수도권 직영점');
  await expect(strip).toContainText('제품·55" 사이니지 + 배포 솔루션');
  await expect(strip).toContainText('4 / 4');
  await expect(page).toHaveURL(new RegExp(`/competitor/${CA_ID.source}/input$`), { timeout: 6_000 });   // 800ms 뒤 draft
  const id = page.url().match(CA_ID)![0];
  expect((await api(request, 'GET', `/analyses/${id}`)).status).toBe('draft');
  await shot(page, 'ca1-input');

  // 찾기 → CA1G → CA2(자동 이동, AC-CA-07)
  await find.click();
  await expect(page).toHaveURL(new RegExp(`/competitor/${id}/(finding|candidates)$`));
  if (page.url().endsWith('/finding')) {
    await expect(page.getByRole('heading', { name: '경쟁사를 찾는 중' })).toBeVisible();
    await shot(page, 'ca1g-finding');
  }
  await expect(page).toHaveURL(new RegExp(`/competitor/${id}/candidates$`), { timeout: 30_000 });
  await expect(page.getByRole('heading', { name: '이 경쟁사들로 분석할까요?' })).toBeVisible();
  await expect(page.getByText('입력에서 읽은 4가지로 후보 6곳을 찾았어요. 추천 4곳은 켜 두었고, 빼거나 더할 수 있어요.')).toBeVisible();
  const list = page.getByRole('group', { name: '경쟁사 후보 6곳' });
  await expect(list.locator('.ca-cand')).toHaveCount(6);
  await expect(list.locator('.ca-cand__badge')).toHaveText(['추천', '추천', '추천', '추천', '확인 필요', '제외 제안']);  // AC-CA-18
  await expect(list.locator('.ca-letter')).toHaveText(['A', 'B', 'C', 'D', 'E', 'F']);
  await expect(page.getByRole('switch', { name: '경쟁사 A 빼기' })).toHaveAttribute('aria-checked', 'true');
  await expect(page.getByRole('switch', { name: '경쟁사 E 넣기' })).toHaveAttribute('aria-checked', 'false');
  await expect(page.getByText(/선택\s*4\s*곳/)).toBeVisible();
  await expect(page.getByRole('button', { name: '4곳으로 분석' })).toBeEnabled();
  await shot(page, 'ca2-candidates');

  // 켜고 끄기(고정) · 직접 추가 · 중복(AC-CA-24 · 25)
  await page.getByRole('switch', { name: '경쟁사 E 넣기' }).click();
  await expect(page.getByRole('button', { name: '5곳으로 분석' })).toBeVisible();
  await page.getByRole('switch', { name: '경쟁사 E 빼기' }).click();
  await expect(page.getByRole('button', { name: '4곳으로 분석' })).toBeVisible();
  const add = page.getByLabel('경쟁사 직접 추가');
  await add.fill('ZZ 사이니지');
  await add.press('Enter');
  await expect(page.getByRole('group', { name: '경쟁사 후보 7곳' })).toBeVisible({ timeout: 10_000 });
  const zz = page.locator('.ca-cand', { hasText: 'ZZ 사이니지' });
  await expect(zz.locator('.ca-letter')).toHaveText('G');
  await expect(zz.locator('.ca-cand__badge')).toHaveText('직접 추가');
  await add.fill('ZZ사이니지');
  await add.press('Enter');
  await expect(page.getByRole('alert')).toHaveText('이미 있는 경쟁사예요');
  await page.getByRole('switch', { name: '경쟁사 G 빼기' }).click();
  await expect(page.getByRole('button', { name: '4곳으로 분석' })).toBeVisible();

  // 분석 → CA3 → CA4(AC-CA-32 자동 이동)
  await page.getByRole('button', { name: '4곳으로 분석' }).click();
  await expect(page).toHaveURL(new RegExp(`/competitor/${id}/(run|result)$`));
  if (page.url().endsWith('/run')) {
    await expect(page.getByRole('heading', { name: '4곳을 분석하는 중' })).toBeVisible();
    await shot(page, 'ca3-run');
  }
  await expect(page).toHaveURL(new RegExp(`/competitor/${id}/result$`), { timeout: 60_000 });
  await expect(page.getByRole('heading', { name: '경쟁사 4곳, 한눈에' })).toBeVisible();
  const rows = page.getByRole('list', { name: '경쟁사' }).getByRole('listitem');
  await expect(rows).toHaveCount(4);
  await expect(rows.first()).toContainText('경쟁사 A');
  await expect(rows.first()).toContainText(/우위 \d/);
  await expect(page.getByLabel('삼성 강점')).toContainText('서버 없는 통합 관리');
  await expect(page.getByText(/출처 \d+ · 공개 자료 \d+ · 사내 사례 DB \d+/)).toBeVisible();   // AC-CA-39
  await shot(page, 'ca4-result');

  await page.getByRole('tab', { name: '비교표' }).click();
  const table = page.getByRole('table', { name: '비교표' });
  await expect(table.getByRole('columnheader')).toHaveText(['비교 기준', '경쟁사 A', '경쟁사 B', '경쟁사 C', '경쟁사 D', '삼성']);   // AC-CA-41
  await expect(table.getByRole('rowheader').first()).toContainText('본사 일괄 배포');
  await expect(table).toContainText('[확인 필요]');
  await shot(page, 'ca4-table');
  await page.getByRole('tab', { name: '삼성 강점' }).click();
  await expect(page.getByText('중요도 × 이긴 경쟁사 수가 큰 순서', { exact: false })).toBeVisible();
  await shot(page, 'ca4-strengths');
  await page.getByRole('tab', { name: '한눈에' }).click();

  // CA4D 상세 · 근거 패널
  await rows.first().click();
  await expect(page).toHaveURL(new RegExp(`/competitor/${id}/competitors/cmp_`));
  await expect(page.getByRole('heading', { name: '경쟁사 A' })).toBeVisible();
  await expect(page.getByRole('navigation', { name: '경쟁사 전환' }).getByRole('link')).toHaveCount(4);
  const facts = page.getByRole('list', { name: '경쟁사 항목' });
  await expect(facts.getByRole('listitem')).toHaveCount(6);
  await expect(facts.locator('[data-fact="price"]')).toContainText('[확인 필요]');
  await expect(facts.locator('[data-fact="price"]')).toContainText('확인 필요');
  await expect(facts.locator('[data-fact="vs"]')).toContainText(/우위 \d/);
  await shot(page, 'ca4d-detail');
  await page.getByRole('button', { name: '출처 · 근거 보기' }).click();
  const panel = page.getByRole('dialog', { name: '경쟁사 A 출처 · 근거' });
  await expect(panel).toBeVisible();
  await expect(panel.locator('.ca-scard2').first()).toBeVisible();
  await shot(page, 'ca4d-evidence');
  await panel.getByRole('button', { name: '닫기' }).click();
  await expect(panel).toBeHidden();

  // CA5 저장 · 보내기 + 익명 스위치(AC-CA-44)
  await page.getByRole('button', { name: '저장 · 보내기' }).click();
  await expect(page).toHaveURL(new RegExp(`/competitor/${id}/send$`));
  await expect(page.getByRole('heading', { name: '저장했어요. 어디에 쓸까요?' })).toBeVisible();
  await expect(page.getByText('익명 표기 (경쟁사 A · B · C · D) 로 Why Samsung 비교 시트에 들어가요')).toBeVisible();
  await shot(page, 'ca5-send');
  const anon = page.getByRole('switch', { name: '고객 제출물엔 익명으로 표기' });
  await anon.click();
  await expect(page.getByText('실명 표기 · 보낼 때 한 번 더 물어요')).toBeVisible();
  await expect(page.getByText('— 실명 표기 · 고객 제출물에 넣을 땐 한 번 더 물어요')).toBeVisible();
  await anon.click();
  await expect(anon).toHaveAttribute('aria-checked', 'true');

  // 리포트 저장(AC-CA-46)
  await page.getByRole('button', { name: /리포트 저장/ }).click();
  await expect(page.getByText('리포트를 저장했어요').first()).toBeVisible({ timeout: 60_000 });

  // CA0 행 · 보낸 곳(실명 없음, AC-CA-47)
  await page.goto('/competitor');
  const row = page.locator(`[data-id="${id}"]`);
  await expect(row).toContainText('A 커피 메뉴보드 경쟁사 분석');
  await expect(row).toContainText('완료');
  await expect(row).toContainText('리포트');
  await expect(row).toContainText(/출처 \d+ · 삼성 강점 \d/);
  await noRealNames(page, REAL);
  const done = await waitStatus(request, id, ['done']);
  expect(done.version).toBe(1);
});
