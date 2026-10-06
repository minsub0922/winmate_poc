/**
 * 로그인(AUTH_MODE=local) — 게이트웨이 `/api/_auth/login · logout · me` 와 셸 문(AuthGate).
 *
 * - AuthGate: 셸(Layout) 경로를 감싼다. `/api/_auth/me` 가 401 이면 `/login?next=<지금 화면>` 으로 보낸다.
 *   그리고 API 401(`@/api/client` onUnauthorized — openapi 클라이언트 · 전역 fetch 감시 · 잡 SSE)을 받으면 같은 곳으로 보낸다.
 *   그 밖의 오류(게이트웨이 꺼짐 등)는 막지 않는다(화면이 각자 오류를 보인다).
 * - AUTH_MODE=none(개발)이면 `/api/_auth/me` 가 늘 개발 사용자라 그대로 들어간다.
 * - 셸 밖 경로(기능 publicRoutes · /login)는 AuthGate 밖이라 401 이어도 로그인 화면으로 가지 않는다.
 */
import { useEffect, type ReactNode } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { ApiError, onUnauthorized } from '@/api/client';

export interface AuthMe {
  id: string;
  name: string;
  /** 'none'(로그인 없음 · 개발 사용자) | 'local'(로컬 계정) */
  auth_mode: string;
}

export const AUTH_ME_KEY = ['auth', 'me'] as const;

async function errorOf(r: Response): Promise<ApiError> {
  const body = await r.json().catch(() => ({}));
  return new ApiError(r.status, body?.error?.code ?? 'ERROR', body?.error?.message ?? r.statusText, body?.error?.details ?? {});
}

/** 지금 로그인한 사용자 — 로그인 안 됨(401)이면 null */
export async function fetchAuthMe(): Promise<AuthMe | null> {
  const r = await fetch('/api/_auth/me', { credentials: 'same-origin', headers: { Accept: 'application/json' } });
  if (r.status === 401) return null;
  if (!r.ok) throw await errorOf(r);
  return (await r.json()) as AuthMe;
}

/** 로그인 — 틀리면 ApiError(401 INVALID_CREDENTIALS) */
export async function login(username: string, password: string): Promise<AuthMe> {
  const r = await fetch('/api/_auth/login', {
    method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  if (!r.ok) throw await errorOf(r);
  redirecting = false;
  return (await r.json()) as AuthMe;
}

export async function logout(): Promise<void> {
  await fetch('/api/_auth/logout', { method: 'POST', credentials: 'same-origin' }).catch(() => undefined);
}

export function useAuthMe() {
  return useQuery({
    queryKey: AUTH_ME_KEY,
    queryFn: fetchAuthMe,
    staleTime: 5 * 60_000,
    retry: (n, e) => n < 1 && !(e instanceof ApiError && e.status < 500),
  });
}

/** `?next=` 로 받은 돌아갈 곳 — 같은 사이트 경로만(`/…`, `//` · `/\` · `/login` 은 안 됨) */
export function safeNext(next: string | null | undefined): string {
  if (!next || !next.startsWith('/') || next.startsWith('//') || next.startsWith('/\\')) return '/';
  if (next === '/login' || next.startsWith('/login?') || next.startsWith('/login/')) return '/';
  return next;
}

/** 로그인 화면 주소(돌아올 곳 포함) */
export function loginHref(loc: { pathname: string; search?: string; hash?: string }): string {
  const here = `${loc.pathname}${loc.search ?? ''}${loc.hash ?? ''}`;
  return here === '/' ? '/login' : `/login?next=${encodeURIComponent(here)}`;
}

let redirecting = false;

/** 셸 문 — 로그인 확인 전에는 빈 화면, 401 이면 로그인 화면으로 */
export function AuthGate({ children }: { children: ReactNode }) {
  const me = useAuthMe();
  const loc = useLocation();
  const nav = useNavigate();
  const qc = useQueryClient();

  useEffect(() => onUnauthorized(() => {
    if (redirecting) return;
    redirecting = true;
    qc.setQueryData(AUTH_ME_KEY, null);
    nav(loginHref(window.location), { replace: true });
  }), [nav, qc]);
  useEffect(() => { if (me.data) redirecting = false; }, [me.data]);

  if (me.isPending) return <div className="sh-authwait" aria-busy="true" aria-label="로그인 확인 중" />;
  if (me.data === null) return <Navigate to={loginHref(loc)} replace />;
  return <>{children}</>;
}
