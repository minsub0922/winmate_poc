/**
 * 라우터 — 기능 모듈(registry.loadFeatures())을 불러온 뒤 main.tsx 가 `createAppRouter()` 로 만든다.
 *
 *   셸 밖(로그인 확인 없음): /login · 기능 publicRoutes(예 /m/upload/:token)
 *   /  ─ AuthGate(AUTH_MODE=local 로그인 확인 · 401 → /login?next=) ─ Layout(사이드바 · 상단바) ─ 홈 · /<기능 key>/…(기능마다 오류 경계) · /_dev/…
 *
 * 기능 하나가 import 오류면 그 경로만 FeatureLoadFailed, 그리다 오류면 FeatureError(사이드바 · 다른 기능은 그대로).
 */
import { lazy, Suspense, type ReactNode } from 'react';
import { createBrowserRouter, Link, Outlet, type RouteObject } from 'react-router';
import { Layout } from './shell/Layout';
import { Home } from './shell/Home';
import { failedFeatures, features } from './shell/registry';
import { useShellPage } from './shell/ShellContext';
import { FeatureError, FeatureLoadFailed, PublicError, RootError } from './shell/errors';
import { AuthGate } from './shell/auth';
import { LoginPage } from './shell/LoginPage';
import { Empty, ToastHost } from './ui';

function NotFound() {
  useShellPage({ hasTask: false });
  return <Empty title="페이지를 찾을 수 없어요" action={<Link to="/">홈으로</Link>} />;
}

// 셸 개발 화면(§8.0 [제안]) — 테스트가 게이트웨이(dist)를 보므로 빌드에 둔다(지연 로드, 링크 없음). VITE_WM_DEVTOOLS=0 이면 뺀다.
const DEVTOOLS = import.meta.env.VITE_WM_DEVTOOLS !== '0';
const DevShell = lazy(() => import('./shell/dev/DevShell'));
const DevKit = lazy(() => import('./shell/dev/DevKit'));
// 사용자 관리(관리자 · AUTH_MODE=none) — 사용자 메뉴에서 연다
const UsersPage = lazy(() => import('./shell/admin/UsersPage'));
const lazyEl = (el: ReactNode) => <Suspense fallback={null}>{el}</Suspense>;

/** 셸 밖 화면 틀(사이드바 · 상단바 없음) — 토스트만 */
function PublicLayout() {
  return (
    <>
      <Outlet />
      <ToastHost />
    </>
  );
}

/** 기능 라우트: 불러온 기능은 오류 경계와 함께, 불러오지 못한 기능은 그 경로 전체에 오류 화면 */
function featureRoutes(): RouteObject[] {
  const ok: RouteObject[] = features.map((f) => ({ path: f.key, errorElement: <FeatureError featureKey={f.key} />, children: f.routes }));
  const broken: RouteObject[] = failedFeatures.map((x) => {
    const el = <FeatureLoadFailed featureKey={x.key} error={x.error} />;
    return { path: x.key, children: [{ index: true, element: el }, { path: '*', element: el }] };
  });
  return [...ok, ...broken];
}

/** 기능이 등록한 셸 밖 경로(절대 경로만) */
export function publicFeatureRoutes(): RouteObject[] {
  return features.flatMap((f) => (f.publicRoutes ?? []).filter((r) => typeof r.path === 'string' && r.path.startsWith('/'))
    .map((r) => ({ ...r, errorElement: r.errorElement ?? <PublicError /> }) as RouteObject));
}

export function createAppRouter() {
  const devRoutes: RouteObject[] = DEVTOOLS
    ? [{ path: '_dev/shell', element: lazyEl(<DevShell />) }, { path: '_dev/kit', element: lazyEl(<DevKit />) }]
    : [];
  return createBrowserRouter([
    { element: <PublicLayout />, errorElement: <PublicError />, children: [{ path: '/login', element: <LoginPage /> }, ...publicFeatureRoutes()] },
    {
      path: '/',
      element: <AuthGate><Layout /></AuthGate>,
      errorElement: <RootError />,
      children: [
        { index: true, element: <Home /> }, ...featureRoutes(), { path: 'admin/users', element: lazyEl(<UsersPage />) }, ...devRoutes,
        { path: '*', element: <NotFound /> },
      ],
    },
  ]);
}
