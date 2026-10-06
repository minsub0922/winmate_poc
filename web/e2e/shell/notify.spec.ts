/**
 * 작업물 알림(spec · proposal 요청) — 사이드바 그 항목 배지 · 그룹 점 · 사용자 메뉴 알림 목록 · 읽음, 사용자 관리 화면.
 * workspace 는 route 흉내(fixtures/mock.ts mockWorkspace notifications · users).
 */
import { expect, test } from '@playwright/test';
import { mockAuth, setupShell, type WsNotiFixture } from './fixtures/mock';

const NOTIS: WsNotiFixture[] = [
  { id: 'ntf_1', title: 'Spec 시트 값이 바뀌었어요 · QMC vs QBC 55" 비교', item_id: 'pr_a', feature: 'PR', route: '/proposal/pr_a/sections/spec', minutesAgo: 3, type: 'spec_link_changed' },
  { id: 'ntf_2', title: '검토 결과 · 변경 요청', item_id: 'pr_a', feature: 'PR', route: '/proposal/pr_a', minutesAgo: 20, type: 'review_decided', by_name: '라마바',
    data: { review_id: 'rvw_1', decision: 'request_changes', due_date: '2026-10-07' } },
  { id: 'ntf_3', title: '예전 알림', item_id: 'pr_b', feature: 'PR', route: '/proposal/pr_b', minutesAgo: 90, read: true },
];

test.describe('작업물 알림 · 사용자 관리 (NT)', () => {
  test('NT-01 사이드바 — 알림 있는 항목에 읽지 않은 수 · 그룹 이름 옆 점 · 설정 버튼 점', async ({ page }) => {
    await setupShell(page, { ws: { notifications: NOTIS.map((n) => ({ ...n })) } });
    await page.goto('/_dev/shell?group=proposal');
    const nav = page.getByRole('navigation', { name: '작업 내역' });
    const group = page.locator('[data-group="proposal"]');
    await expect(group.locator('.sh-group__dot')).toHaveAttribute('data-unread', '2');
    await expect(page.locator('[data-group="spec"] .sh-group__dot')).toHaveCount(0);
    const item = nav.getByRole('link', { name: /A 커피 프랜차이즈 메뉴보드 제안/ });
    await expect(item.locator('.sh-item__new')).toHaveText('2건 새 알림');
    await expect(item).toHaveAttribute('title', 'A 커피 프랜차이즈 메뉴보드 제안 · 새 알림 2건');
    await expect(nav.getByRole('link', { name: /B 병원 안내 시스템 제안/ }).locator('.sh-item__new')).toHaveCount(0);
    await expect(page.getByRole('button', { name: '설정' })).toHaveAttribute('data-unread', '2');
    expect((await item.locator('.sh-item__new').boundingBox())!.height).toBe(18);
    await page.screenshot({ path: 'e2e/shell/__screens__/notify-sidebar.png' });
  });

  test('NT-02 사용자 메뉴 알림 — 목록 · 누르면 그 경로로 · 읽음 표시', async ({ page }) => {
    const calls: string[] = [];
    await setupShell(page, { ws: { notifications: NOTIS.map((n) => ({ ...n })), calls } });
    await page.goto('/');
    await page.getByRole('button', { name: '설정' }).click();
    const menu = page.getByRole('menu', { name: '사용자 메뉴' });
    await expect(menu).toContainText('알림 2');
    const rows = menu.locator('[data-noti]');
    await expect(rows).toHaveCount(3);
    await expect(rows.first()).toContainText('Spec 시트 값이 바뀌었어요');
    await expect(rows.first()).toContainText('김영업 · 3분 전');
    await expect(rows.nth(2)).not.toHaveClass(/sh-noti--new/);
    await expect(rows.nth(1).locator('[data-dday]')).toHaveText('D-1'); // 검토 마감일(data.due_date) — 기준 2026-10-06 KST
    await page.screenshot({ path: 'e2e/shell/__screens__/notify-menu.png' });
    await rows.first().click();
    await expect(page).toHaveURL(/\/proposal\/pr_a\/sections\/spec$/);
    await expect.poll(() => calls.some((c) => c.startsWith('POST /notifications/read') && c.includes('ntf_1'))).toBe(true);
  });

  test('NT-03 그 작업물 화면을 열면(경로에 항목 id) 그 항목 알림이 읽음', async ({ page }) => {
    const calls: string[] = [];
    await setupShell(page, { ws: { notifications: NOTIS.map((n) => ({ ...n })), calls } });
    await page.goto('/proposal/pr_a');
    await expect.poll(() => calls.find((c) => c.startsWith('POST /notifications/read'))).toBe('POST /notifications/read {"item_id":"pr_a"}');
    await expect(page.getByRole('button', { name: '설정' })).not.toHaveAttribute('data-unread', /.+/);
  });

  test('NT-04 모두 읽음', async ({ page }) => {
    const calls: string[] = [];
    await setupShell(page, { ws: { notifications: NOTIS.map((n) => ({ ...n })), calls } });
    await page.goto('/');
    await page.getByRole('button', { name: '설정' }).click();
    await page.getByRole('menu', { name: '사용자 메뉴' }).getByRole('button', { name: '모두 읽음' }).click();
    await expect.poll(() => calls.includes('POST /notifications/read {}')).toBe(true);
    await expect(page.locator('[data-group="proposal"] .sh-group__dot')).toHaveCount(0);
  });

  test('NT-05 알림 API 가 없어도(옛 workspace 404) 사이드바 · 메뉴는 그대로', async ({ page }) => {
    await setupShell(page);
    await page.route('**/api/workspace/v1/notifications**', (route) => route.fulfill({ status: 404, contentType: 'application/json',
      body: JSON.stringify({ error: { code: 'NOT_FOUND', message: '없음', details: {} } }) }));
    await page.goto('/');
    await expect(page.getByRole('navigation', { name: '작업 내역' })).toBeVisible();
    await page.getByRole('button', { name: '설정' }).click();
    await expect(page.getByRole('menu', { name: '사용자 메뉴' })).toContainText('알림을 불러오지 못했어요');
  });

  test('NT-06 사용자 관리 — 목록 · 새 사용자(아이디 형식 · 중복) · 고치기(역할 · 사용 중지 · 비밀번호 재설정)', async ({ page }) => {
    const calls: string[] = [];
    await setupShell(page, {
      ws: {
        calls, me: { role: 'admin', username: 'admin', has_password: true },
        users: [
          { id: 'u_admin', username: 'admin', name: '관리자', role: 'admin', last_login_at: '2026-10-06T04:00:00Z' },
          { id: 'u_kim', username: 'kim', name: '김영업', org: 'B2B영업' },
          { id: 'u_dev', username: 'u_dev', name: '최민섭', has_password: false },
        ],
      },
    });
    await mockAuth(page, { signedIn: true, user: { id: 'u_admin', name: '관리자' } });
    await page.goto('/');
    await page.getByRole('button', { name: '설정' }).click();
    await page.getByRole('menuitem', { name: '사용자 관리' }).click();
    await expect(page).toHaveURL(/\/admin\/users$/);
    await expect(page.getByRole('heading', { name: '사용자 관리' })).toBeVisible();
    await expect(page.getByRole('navigation', { name: '현재 위치' })).toContainText('사용자 관리');
    const rows = page.getByRole('row');
    await expect(rows).toHaveCount(4);
    await expect(rows.nth(3)).toContainText('비밀번호 없음');
    await expect(rows.nth(1)).toContainText('관리자');
    await page.screenshot({ path: 'e2e/shell/__screens__/admin-users.png' });
    // 새 사용자
    await page.getByRole('button', { name: '+ 새 사용자' }).click();
    const d = page.getByRole('dialog', { name: '새 사용자' });
    await d.getByLabel('아이디').fill('a b');
    await d.getByLabel('이름', { exact: true }).fill('이기획');
    await d.getByLabel('비밀번호').fill('123456');
    await d.getByRole('button', { name: '만들기' }).click();
    await expect(d.getByRole('alert')).toContainText('아이디는 영문');
    await d.getByLabel('아이디').fill('KIM');
    await d.getByRole('button', { name: '만들기' }).click();
    await expect(d.getByRole('alert')).toContainText('이미 있는 아이디입니다');
    await d.getByLabel('아이디').fill('lee');
    await d.getByRole('group', { name: '역할' }).getByRole('button', { name: '관리자' }).click();
    await d.getByRole('button', { name: '만들기' }).click();
    await expect(d).toHaveCount(0);
    await expect(rows).toHaveCount(5);
    expect(calls.some((c) => c.startsWith('POST /users') && c.includes('"username":"lee"') && c.includes('"role":"admin"'))).toBe(true);
    // 고치기: 사용 중지 + 비밀번호 재설정
    await page.getByRole('button', { name: '김영업 고치기' }).click();
    const e = page.getByRole('dialog', { name: '사용자 고치기 · kim' });
    await e.getByRole('switch', { name: '사용 중지' }).click();
    await e.getByLabel('비밀번호 재설정').fill('reset-pass');
    await e.getByRole('button', { name: '저장' }).click();
    await expect(e).toHaveCount(0);
    expect(calls.some((c) => c.startsWith('PATCH /users/u_kim') && c.includes('"disabled":true') && c.includes('"password":"reset-pass"'))).toBe(true);
    await expect(page.getByRole('row', { name: /김영업/ })).toContainText('사용 중지');
  });

  test('NT-07 관리자가 아니면(AUTH_MODE=local) 사용자 관리가 닫혀 있다', async ({ page }) => {
    await setupShell(page, { ws: { me: { role: 'member', username: 'kim', has_password: true } } });
    await mockAuth(page, { signedIn: true });
    await page.goto('/');
    await page.getByRole('button', { name: '설정' }).click();
    await expect(page.getByRole('menuitem', { name: '사용자 관리' })).toHaveCount(0);
    await page.goto('/admin/users');
    await expect(page.getByText('관리자만 볼 수 있어요')).toBeVisible();
  });
});
