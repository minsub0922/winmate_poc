/**
 * 로그인(AUTH_MODE=local) · 401 처리 · 로그아웃 · 셸 밖 경로 — 실제 스택은 AUTH_MODE=none 이라 `/api/_auth/*` 를 route 흉내로 바꾼다.
 */
import { expect, test, type Page } from '@playwright/test';
import { mockAuth, setupShell } from './fixtures/mock';

const login = (page: Page) => page.getByRole('main', { name: '로그인' });

test.describe('로그인 · 401 (AUTH)', () => {
  test('AUTH-01 로그인 안 됨 → /login?next=… · 틀린 비밀번호 → 오류 · 맞으면 보던 화면으로', async ({ page }) => {
    await setupShell(page);
    const auth = await mockAuth(page, { signedIn: false });
    await page.goto('/_dev/shell?task=1');
    await expect(page).toHaveURL(/\/login\?next=%2F_dev%2Fshell%3Ftask%3D1$/);
    await expect(login(page)).toBeVisible();
    await expect(page.getByRole('heading', { name: '로그인' })).toBeVisible();
    await expect(page.getByText('로그인하면 보던 화면으로 돌아가요.')).toBeVisible();
    await expect(page.getByRole('navigation', { name: '작업 내역' })).toHaveCount(0); // 셸 밖
    // 빈 칸
    await page.getByRole('button', { name: '로그인' }).click();
    await expect(page.getByRole('alert')).toContainText('아이디를 입력해 주세요');
    // 틀린 비밀번호
    await page.getByLabel('아이디').fill('kim');
    await page.getByLabel('비밀번호').fill('nope');
    await page.getByRole('button', { name: '로그인' }).click();
    await expect(page.getByRole('alert')).toContainText('아이디 또는 비밀번호가 맞지 않습니다');
    await expect(page.getByLabel('비밀번호')).toHaveValue('');
    expect(auth.signedIn).toBe(false);
    // 맞는 비밀번호(Enter 로 보내기)
    await page.getByLabel('비밀번호').fill('password');
    await page.getByLabel('비밀번호').press('Enter');
    await expect(page).toHaveURL(/\/_dev\/shell\?task=1$/);
    await expect(page.getByRole('navigation', { name: '작업 내역' })).toBeVisible();
    expect(auth.calls).toContain('POST /api/_auth/login');
    await page.screenshot({ path: 'e2e/shell/__screens__/auth-after-login.png' });
  });

  test('AUTH-02 로그인 화면 모양 · next 는 같은 사이트 경로만', async ({ page }) => {
    await setupShell(page);
    const auth = await mockAuth(page, { signedIn: false });
    await page.goto('/login?next=' + encodeURIComponent('//evil.example.com/x'));
    await expect(login(page)).toBeVisible();
    await expect(page.getByText('winmate')).toBeVisible();
    const btn = page.getByRole('button', { name: '로그인' });
    expect(await btn.evaluate((el) => getComputedStyle(el).backgroundColor)).toBe('rgb(20, 40, 160)');
    await page.screenshot({ path: 'e2e/shell/__screens__/auth-login.png' });
    await page.getByLabel('아이디').fill('kim');
    await page.getByLabel('비밀번호').fill('password');
    await btn.click();
    await expect(page).toHaveURL(/127\.0\.0\.1:\d+\/$/); // 바깥 주소로 가지 않고 홈
    expect(auth.signedIn).toBe(true);
    await expect(page.locator('[data-greeting]')).toBeVisible();
  });

  test('AUTH-03 이미 로그인돼 있으면 /login → next 로 바로', async ({ page }) => {
    await setupShell(page);
    await mockAuth(page, { signedIn: true });
    await page.goto('/login?next=%2Fadmin%2Fusers');
    await expect(page).toHaveURL(/\/admin\/users$/);
  });

  test('AUTH-04 로그인한 뒤 API 401(openapi 클라이언트) → 로그인 화면(next = 지금 화면)', async ({ page }) => {
    await setupShell(page);
    const auth = await mockAuth(page, { signedIn: true });
    await page.goto('/_dev/shell?task=1');
    await expect(page.getByRole('navigation', { name: '작업 내역' })).toBeVisible();
    // 세션이 끝났다 — 이후 workspace 는 401
    auth.signedIn = false;
    await page.route('**/api/workspace/v1/items**', (route) => route.fulfill({ status: 401, contentType: 'application/json',
      body: JSON.stringify({ error: { code: 'UNAUTHENTICATED', message: '로그인이 필요합니다', details: {} } }) }));
    await page.getByRole('button', { name: 'Market Intelligence 펼치기' }).click();
    await expect(page).toHaveURL(/\/login\?next=%2F_dev%2Fshell%3Ftask%3D1$/);
    await expect(login(page)).toBeVisible();
  });

  test('AUTH-05 기능 화면의 fetch(…) 401 도 잡는다(전역 감시) · 로그인 API 401 은 그대로', async ({ page }) => {
    await setupShell(page);
    const auth = await mockAuth(page, { signedIn: true });
    await page.goto('/_dev/kit');
    await expect(page.getByTestId('product-input')).toBeVisible();
    auth.signedIn = false;
    await page.route('**/api/kb/v1/products/search**', (route) => route.fulfill({ status: 401, contentType: 'application/json',
      body: JSON.stringify({ error: { code: 'UNAUTHENTICATED', message: '로그인이 필요합니다', details: {} } }) }));
    await page.getByTestId('product-input').getByRole('combobox').fill('QM');
    await expect(page).toHaveURL(/\/login\?next=%2F_dev%2Fkit$/);
    // 로그인 화면의 /api/_auth/me 401 은 다시 보내지 않는다(같은 화면 유지)
    await page.waitForTimeout(500);
    await expect(page).toHaveURL(/\/login\?next=%2F_dev%2Fkit$/);
  });

  test('AUTH-05b 잡 SSE(EventSource)가 401 로 끊기면 /api/_auth/me 로 확인 → 로그인 화면', async ({ page }) => {
    await setupShell(page);
    const auth = await mockAuth(page, { signedIn: true });
    await page.goto('/_dev/shell?task=1');
    await expect(page.getByRole('navigation', { name: '작업 내역' })).toBeVisible();
    auth.signedIn = false;
    await page.route('**/api/jobs/v1/jobs/**', (route) => route.fulfill({ status: 401, contentType: 'application/json',
      body: JSON.stringify({ error: { code: 'UNAUTHENTICATED', message: '로그인이 필요합니다', details: {} } }) }));
    await page.evaluate(() => { new EventSource('/api/jobs/v1/jobs/job_x/events'); });
    await expect(page).toHaveURL(/\/login\?next=%2F_dev%2Fshell%3Ftask%3D1$/);
    expect(auth.calls.filter((c) => c === 'GET /api/_auth/me').length).toBeGreaterThanOrEqual(2);
  });

  test('AUTH-06 셸 밖 경로(/m/upload/:token)는 401 이어도 로그인으로 가지 않는다', async ({ page }) => {
    await setupShell(page);
    await mockAuth(page, { signedIn: false });
    await page.route('**/api/birdseye/v1/upload-tokens/**', (route) => route.fulfill({ status: 401, contentType: 'application/json',
      body: JSON.stringify({ error: { code: 'UNAUTHENTICATED', message: '로그인이 필요합니다', details: {} } }) }));
    await page.goto('/m/upload/abcdefgh1234');
    await expect(page.getByTestId('be-mobile')).toBeVisible();
    await page.waitForTimeout(500);
    await expect(page).toHaveURL(/\/m\/upload\/abcdefgh1234$/);
    await expect(page.getByRole('navigation', { name: '작업 내역' })).toHaveCount(0);
    await expect(page.getByRole('alert')).toContainText('QR 유효 시간이 지났어요');
  });

  test('AUTH-07 사용자 메뉴 — 아이디 · 관리자 · 로그아웃(local)', async ({ page }) => {
    await setupShell(page, { ws: { me: { role: 'admin', username: 'kim', has_password: true } } });
    const auth = await mockAuth(page, { signedIn: true });
    await page.goto('/');
    await page.getByRole('button', { name: '설정' }).click();
    const menu = page.getByRole('menu', { name: '사용자 메뉴' });
    await expect(menu).toBeVisible();
    await expect(menu).toContainText('아이디 kim · 관리자');
    await expect(menu.getByRole('menuitem', { name: '사용자 관리' })).toBeVisible();
    await expect(menu.getByRole('menuitem', { name: '비밀번호 바꾸기' })).toBeVisible();
    await page.screenshot({ path: 'e2e/shell/__screens__/auth-user-menu.png' });
    await menu.getByRole('menuitem', { name: '로그아웃' }).click();
    await expect(page).toHaveURL(/\/login$/);
    await expect(login(page)).toBeVisible();
    expect(auth.calls).toContain('POST /api/_auth/logout');
    expect(auth.signedIn).toBe(false);
  });

  test('AUTH-08 AUTH_MODE=none — 로그인 화면 없음 · 로그아웃 꺼짐(이유 툴팁)', async ({ page }) => {
    await setupShell(page);
    await mockAuth(page, { mode: 'none', user: { id: 'u_dev', name: '최민섭' } });
    await page.goto('/login?next=%2F');
    await expect(page).toHaveURL(/127\.0\.0\.1:\d+\/$/);
    await page.getByRole('button', { name: '설정' }).click();
    const out = page.getByRole('menu', { name: '사용자 메뉴' }).getByRole('menuitem', { name: '로그아웃' });
    await expect(out).toBeDisabled();
    await expect(out).toHaveAttribute('title', /AUTH_MODE=none/);
    await page.keyboard.press('Escape');
    await expect(page.getByRole('menu', { name: '사용자 메뉴' })).toHaveCount(0);
  });

  test('AUTH-09 비밀번호 바꾸기 대화상자', async ({ page }) => {
    const calls: string[] = [];
    await setupShell(page, { ws: { me: { username: 'kim', has_password: true }, calls } });
    await mockAuth(page, { signedIn: true });
    await page.route('**/api/workspace/v1/me/password', async (route) => {
      const b = route.request().postDataJSON() as { current_password: string };
      if (b.current_password !== 'old-pass') {
        return route.fulfill({ status: 400, contentType: 'application/json', body: JSON.stringify({ error: { code: 'INVALID_PASSWORD', message: '지금 비밀번호가 맞지 않습니다', details: {} } }) });
      }
      return route.fulfill({ status: 204, body: '' });
    });
    await page.goto('/');
    await page.getByRole('button', { name: '설정' }).click();
    await page.getByRole('menuitem', { name: '비밀번호 바꾸기' }).click();
    const d = page.getByRole('dialog', { name: '비밀번호 바꾸기' });
    await d.getByLabel('지금 비밀번호').fill('wrong');
    await d.getByLabel('새 비밀번호', { exact: false }).first().fill('new-pass');
    await d.getByLabel('새 비밀번호 확인').fill('new-pass2');
    await d.getByRole('button', { name: '바꾸기' }).click();
    await expect(d.getByRole('alert')).toContainText('새 비밀번호가 서로 달라요');
    await d.getByLabel('새 비밀번호 확인').fill('new-pass');
    await d.getByRole('button', { name: '바꾸기' }).click();
    await expect(d.getByRole('alert')).toContainText('지금 비밀번호가 맞지 않습니다');
    await d.getByLabel('지금 비밀번호').fill('old-pass');
    await d.getByRole('button', { name: '바꾸기' }).click();
    await expect(d).toHaveCount(0);
    await expect(page.getByText('비밀번호를 바꿨어요')).toBeVisible();
  });
});
