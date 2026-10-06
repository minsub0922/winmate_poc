/**
 * 셸 공통 URL 상태(00-shell §4): pop · q · node · detail · tab · img — 어느 라우트에서나 붙는다.
 */
import { useCallback, useEffect, useMemo } from 'react';
import { useLocation, useNavigate } from 'react-router';

export type PopoverKind = 'product' | 'solution' | 'image' | 'case';
export const POPOVER_KINDS: PopoverKind[] = ['product', 'solution', 'image', 'case'];
export type DetailKind = 'product' | 'solution';

export function parseDetail(v?: string | null): { kind: DetailKind; id: string } | null {
  if (!v) return null;
  const i = v.indexOf(':');
  if (i < 0) return null;
  const kind = v.slice(0, i);
  const id = v.slice(i + 1);
  if ((kind !== 'product' && kind !== 'solution') || !id) return null;
  return { kind, id };
}

export type UrlPatch = Record<string, string | null | undefined>;

export function applyPatch(sp: URLSearchParams, patch: UrlPatch) {
  const next = new URLSearchParams(sp);
  for (const [k, v] of Object.entries(patch)) {
    if (v === null || v === undefined || v === '') next.delete(k); else next.set(k, v);
  }
  return next;
}

// 같은 틱에 여러 번 바꿔도 앞의 변경을 잃지 않도록, 아직 반영되지 않은 쿼리를 기억한다(다음 위치 변경 때 비운다)
let pending: { path: string; search: string } | null = null;

export function useShellUrl() {
  const loc = useLocation();
  const navigate = useNavigate();
  useEffect(() => { pending = null; }, [loc.key]);
  const sp = useMemo(() => new URLSearchParams(loc.search), [loc.search]);
  const update = useCallback((patch: UrlPatch, opts: { replace?: boolean } = {}) => {
    const path = window.location.pathname;
    const fresh = pending && pending.path === path ? pending.search : window.location.search;
    const cur = new URLSearchParams(fresh);
    const next = applyPatch(cur, patch);
    const s = next.toString();
    if (s === cur.toString() && fresh === window.location.search) return;
    pending = { path, search: s ? `?${s}` : '' };
    navigate({ pathname: path, search: s ? `?${s}` : '' }, { replace: opts.replace ?? true, preventScrollReset: true });
  }, [navigate]);
  const popRaw = sp.get('pop');
  return {
    sp,
    pop: (popRaw && (POPOVER_KINDS as string[]).includes(popRaw) ? popRaw : null) as PopoverKind | null,
    q: sp.get('q') ?? '',
    node: sp.get('node'),
    detail: parseDetail(sp.get('detail')),
    tab: sp.get('tab'),
    img: sp.get('img'),
    update,
  };
}

/** 상세 시트를 여는 URL 조각(현재 쿼리 유지) */
export function detailSearch(kind: DetailKind, id: string, tab?: string, base?: URLSearchParams) {
  const p = new URLSearchParams(base ?? (typeof window !== 'undefined' ? window.location.search : ''));
  p.set('detail', `${kind}:${id}`);
  if (tab) p.set('tab', tab); else p.delete('tab');
  p.delete('img');
  return `?${p.toString()}`;
}
