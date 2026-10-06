/**
 * SP3 → SP3E(편집 세션) → SP3 → SP4(내보내기 · 제안서로) — 06-spec §4.12 · §4.13 · §9.10 · §9.11.
 * 시트는 API 로 준비(QM55C · QB55C, 값 확인은 [확정 필요]로 미룸).
 */
import { expect, test } from '@playwright/test';
import { QB55C, QM55C, api, generatedSheet, shot } from './helpers';

test('편집 세션: 이동 · 강조 · 메모 · 숨김 · 추가 → 실행 취소/다시 실행 → 편집 완료', async ({ page, request }) => {
  const s = await generatedSheet(request, [QM55C, QB55C]);
  await page.goto(`/spec/${s.id}`);
  await expect(page.getByTestId('sp-sheet-title')).toHaveText('Smart Signage 55" 비교 — QM55C vs QB55C');
  await page.getByRole('button', { name: '항목 순서 바꾸기' }).click();
  await expect(page).toHaveURL(new RegExp(`/spec/${s.id}/edit\\?session=ses_`));
  await expect(page.getByText('편집 모드예요. 행을 끌어 순서를 바꾸고', { exact: false })).toBeVisible();
  await expect(page.getByTestId('sp-dock-title')).toHaveText('시트 편집 · 변경 없음');

  const row = (label: string) => page.getByTestId('sp-erow').filter({ has: page.locator('.sp-erow__name', { hasText: new RegExp(`^${label.replace(/[()]/g, '\\$&')}$`) }) });
  // 키보드로 운영 시간을 밝기 · 명암비 위로(Alt+↑)
  await row('운영 시간').getByRole('button', { name: '끌어서 순서 바꾸기' }).focus();
  await page.keyboard.press('Alt+ArrowUp');
  await expect(row('운영 시간')).toContainText('↑ 1칸');
  await row('운영 시간').getByRole('button', { name: '강조' }).click();
  await expect(row('운영 시간')).toContainText('강조');
  // 메모(각주)
  await row('밝기 · 명암비').getByRole('button', { name: '메모' }).click();
  await page.getByLabel('밝기 · 명암비 메모').fill('창가 매장은 오후 직사광이 들어 QM55C 권장 — 고객 미팅에서 언급');
  await page.getByRole('button', { name: '메모 저장' }).click();
  // 숨김
  await row('내장 플레이어 · OS').getByRole('button', { name: '숨기기' }).click();
  await expect(row('내장 플레이어 · OS')).toContainText('숨김');
  await expect(row('내장 플레이어 · OS').getByRole('button', { name: '다시 보이기' })).toBeVisible();
  // 항목 추가 → 크기 (W×H×D)
  await page.getByRole('button', { name: '항목 추가' }).click();
  await page.getByRole('menuitem', { name: '크기 (W×H×D)' }).click();
  await expect(row('크기 (W×H×D)')).toContainText('추가됨');

  await expect(page.getByTestId('sp-dock-title')).toHaveText('시트 편집 · 변경 5건 — 이동 1 · 강조 1 · 메모 1 · 숨김 1 · 추가 1');
  await expect(page.getByTestId('sp-visible')).toHaveText('보이는 행 7 / 8');
  await expect(page.getByRole('switch', { name: /숨긴 행 보기 1/ })).toHaveAttribute('aria-checked', 'true');
  for (const m of ['입출력 단자', '베젤', '인증', '액세서리']) await expect(page.getByRole('button', { name: m, exact: true })).toBeVisible();
  await shot(page, 'SP3E');

  // 실행 취소 두 번 → 다시 실행 한 번
  await page.getByRole('button', { name: '실행 취소' }).click();
  await expect(page.getByTestId('sp-dock-title')).toHaveText(/변경 4건/);
  await page.getByRole('button', { name: '실행 취소' }).click();
  await expect(page.getByTestId('sp-dock-title')).toHaveText(/변경 3건/);
  await page.getByRole('button', { name: '다시 실행' }).click();
  await expect(page.getByTestId('sp-dock-title')).toHaveText(/변경 4건/);
  await page.getByRole('button', { name: '다시 실행' }).click();
  await expect(page.getByTestId('sp-dock-title')).toHaveText(/변경 5건/);

  // 새로고침해도 세션 유지
  await page.reload();
  await expect(page.getByTestId('sp-dock-title')).toHaveText(/변경 5건/);

  // 숨긴 행 감추기 스위치
  await page.getByRole('switch', { name: /숨긴 행 보기/ }).click();
  await expect(row('내장 플레이어 · OS')).toHaveCount(0);

  const before = await api(request, 'GET', `/sheets/${s.id}`);
  await page.getByRole('button', { name: '편집 완료' }).click();
  await expect(page).toHaveURL(new RegExp(`/spec/${s.id}$`));
  const after = await api(request, 'GET', `/sheets/${s.id}`);
  expect(after.version).toBe(before.version + 1);
  const labels = (after.table.rows as Array<{ label: string; hidden: boolean }>).filter((r) => !r.hidden).map((r) => r.label);
  expect(labels.indexOf('운영 시간')).toBeLessThan(labels.indexOf('밝기 · 명암비'));
  expect(labels).not.toContain('내장 플레이어 · OS');
  expect(labels).toContain('크기 (W×H×D)');
  await expect(page.getByText('* 밝기 · 명암비 — 창가 매장은 오후 직사광이 들어 QM55C 권장', { exact: false })).toBeVisible();
  await expect(page.getByRole('rowheader', { name: '밝기 · 명암비 *' })).toBeVisible();

  // SP4
  await page.getByRole('button', { name: '제안서에 넣기' }).click();
  await expect(page).toHaveURL(new RegExp(`/spec/${s.id}/export$`));
  await expect(page.getByText("시트를 어디로 보낼까요? 파일로 내려받거나", { exact: false })).toBeVisible();
  await expect(page.getByRole('radio', { name: /Excel \(\.xlsx\)/ })).toHaveAttribute('aria-checked', 'true');
  await expect(page.getByRole('checkbox', { name: '숨긴 행 1개 빼기' })).toHaveAttribute('aria-checked', 'true');
  await expect(page.getByRole('checkbox', { name: '메모를 각주로 넣기' })).toHaveAttribute('aria-checked', 'true');
  await expect(page.getByRole('checkbox', { name: '[확정 필요] 칸 표시 유지' })).toHaveAttribute('aria-checked', 'true');
  await expect(page.getByLabel('파일명')).toHaveValue(/QM55C-QB55C_스펙비교\.xlsx$/);
  await expect(page.getByRole('button', { name: 'Excel 다운로드' })).toBeVisible();
  const carry = page.getByTestId('sp-carry');
  await expect(carry).toContainText('보이는 행 7개 — 숨긴 1행은 빠져요');
  await expect(carry).toContainText('각주 메모 1건 그대로');
  await expect(carry).toContainText('시트와 연결 유지 — 값이 바뀌면 제안서에 알림');
  const slide = page.getByRole('img', { name: '제안서 시트 미리보기' });
  await expect(slide).toContainText('08 · 제품 스펙');
  await expect(slide).toContainText('QM55C vs QB55C 사양 비교');
  await expect(slide).toContainText('밝기 · 명암비 *');
  await expect(slide).toContainText('CONFIDENTIAL');
  await expect(page.getByTestId('sp-dock-title')).toHaveText(/^내보내기 · Spec 시트 완료 · /);
  await shot(page, 'SP4');

  await page.getByRole('radio', { name: /^PDF/ }).click();
  await expect(page.getByLabel('파일명')).toHaveValue(/\.pdf$/);
  await expect(page.getByRole('button', { name: 'PDF 다운로드' })).toBeVisible();
  await page.getByRole('radio', { name: /Excel \(\.xlsx\)/ }).click();

  // Excel 다운로드 → export 잡 → 파일
  const dl = page.waitForEvent('download', { timeout: 30_000 });
  await page.getByRole('button', { name: 'Excel 다운로드' }).click();
  const file = await dl;
  expect(file.url()).toMatch(/\/api\/files\/v1\/files\/file_[A-Z0-9]+\/content\?download=1$/);

  // 새 제안서로 시작 → 대상 없는 넘김
  await page.getByRole('button', { name: '새 제안서로 시작' }).click();
  await expect(page).toHaveURL(/\/proposal\/new\?handoff=sho_/);
  const sho = new URL(page.url()).searchParams.get('handoff')!;
  const h = await api(request, 'GET', `/handoffs/${sho}`);
  expect(h.proposal_id).toBeNull();
  expect(h.package.carry).toMatchObject({ visible_rows: 7, hidden_rows_dropped: 1, footnote_memos: 1 });
  expect(h.package.sheets[0].data.rows).toHaveLength(7);
});
