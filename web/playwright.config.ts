/**
 * Playwright — 셸 e2e(web/e2e/shell) · 기능 e2e(web/e2e/<기능>).
 *   기본: 게이트웨이(5000)가 서빙하는 web/dist(+ /api).
 *     cd web && npx vite build && PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers npx playwright test e2e/shell
 *   WM_E2E_PREVIEW=1: 따로 빌드해 vite preview(WM_E2E_PORT, 기본 5097, /api 는 5000 으로 프록시)로 돈다.
 *   WM_E2E_DEV=1: 빌드 없이 Vite 개발 서버(WM_E2E_PORT)로 돈다 — 기능 세션은 `make e2e-feature SERVICE=<기능>`
 *     (포트 = 서비스 포트 + 100, 결과 폴더 = e2e/<기능>/.results). 세션끼리 포트 · 빌드 폴더가 겹치지 않는다.
 * 설치된 Chromium 판이 Playwright 기대 판과 다르면(사내 PC 고정 설치) 있는 판을 찾아 쓴다(PW_CHROMIUM_PATH 로 지정 가능).
 */
import fs from 'node:fs';
import path from 'node:path';
import { chromium, defineConfig, devices } from '@playwright/test';

const preview = !!process.env.WM_E2E_PREVIEW;
const dev = !!process.env.WM_E2E_DEV;
const port = Number(process.env.WM_E2E_PORT || 5097);
const suite = process.env.WM_E2E_SUITE || 'shell';

function chromiumPath(): string | undefined {
  if (process.env.PW_CHROMIUM_PATH) return process.env.PW_CHROMIUM_PATH;
  try { if (fs.existsSync(chromium.executablePath())) return undefined; } catch { /* 기대 판 없음 */ }
  const root = process.env.PLAYWRIGHT_BROWSERS_PATH || '/opt/pw-browsers';
  if (!fs.existsSync(root)) return undefined;
  const found = fs.readdirSync(root).filter((d) => /^chromium-\d+$/.test(d)).sort((a, b) => Number(b.split('-')[1]) - Number(a.split('-')[1]))
    .map((d) => path.join(root, d, 'chrome-linux', 'chrome')).find((p) => fs.existsSync(p));
  return found;
}
const exe = chromiumPath();

export default defineConfig({
  testDir: './e2e',
  timeout: 45_000,
  expect: { timeout: 8_000 },
  fullyParallel: true,
  workers: process.env.CI ? 2 : 4,
  retries: 0,
  reporter: [['list']],
  outputDir: `./e2e/${suite}/.results`,
  use: {
    ...devices['Desktop Chrome'],
    baseURL: process.env.WM_E2E_BASE_URL ?? (preview || dev ? `http://127.0.0.1:${port}` : 'http://127.0.0.1:5000'),
    viewport: { width: 1440, height: 900 },
    locale: 'ko-KR',
    timezoneId: 'Asia/Seoul',
    trace: 'retain-on-failure',
    launchOptions: exe ? { executablePath: exe } : {},
  },
  projects: [{ name: 'chromium' }],
  webServer: dev ? {
    command: `npx vite --port ${port} --strictPort --host 127.0.0.1`,
    url: `http://127.0.0.1:${port}/`,
    reuseExistingServer: true,
    timeout: 120_000,
  } : preview ? {
    command: `npx vite build --outDir e2e/${suite}/.dist --emptyOutDir && npx vite preview --outDir e2e/${suite}/.dist --port ${port} --strictPort --host 127.0.0.1`,
    url: `http://127.0.0.1:${port}/`,
    reuseExistingServer: true,
    timeout: 180_000,
  } : undefined,
});
