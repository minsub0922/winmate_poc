/**
 * 제품 탐색 트리 노드 정보(이름 · 부모) 캐시 — 트리를 펼칠 때 모으고, 깊은 링크(`?node=fam_…`)는 kb 로 조상을 찾는다.
 */
import { useEffect, useMemo, useSyncExternalStore } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { kb } from '../kb';
import type { KbCategory, KbFamily } from '../kbTypes';

export interface NodeInfo { id: string; name: string; parentId: string | null; kind: 'top' | 'cat' | 'fam' }

const nodes = new Map<string, NodeInfo>();
let version = 0;
const subs = new Set<() => void>();
const bump = () => { version += 1; subs.forEach((f) => f()); };
export const nodeKind = (id: string): NodeInfo['kind'] => (id.startsWith('fam_') ? 'fam' : id.startsWith('top_') ? 'top' : 'cat');

export function registerNode(n: NodeInfo) {
  const cur = nodes.get(n.id);
  if (cur && cur.name === n.name && (cur.parentId === n.parentId || !n.parentId)) return;
  nodes.set(n.id, { ...cur, ...n, parentId: n.parentId ?? cur?.parentId ?? null });
  bump();
}
export function registerCategories(items: KbCategory[] | undefined, parentId: string | null) {
  items?.forEach((c) => registerNode({ id: c.id, name: c.name, parentId: c.parent_id ?? parentId, kind: c.level === 1 && !parentId ? 'top' : nodeKind(c.id) }));
}
export const familyLabel = (f: { name: string; series_label?: string | null }) => f.series_label || f.name;
export function registerFamilies(items: KbFamily[] | undefined, parentId: string) {
  items?.forEach((f) => registerNode({ id: f.id, name: familyLabel(f), parentId, kind: 'fam' }));
}
export const getNode = (id?: string | null) => (id ? nodes.get(id) : undefined);

export function useNodeVersion() {
  return useSyncExternalStore((cb) => { subs.add(cb); return () => { subs.delete(cb); }; }, () => version, () => version);
}

/** 루트부터 그 노드까지(알 수 있는 데까지) */
export function chainOf(id?: string | null): NodeInfo[] {
  const out: NodeInfo[] = [];
  let cur = getNode(id);
  const seen = new Set<string>();
  while (cur && !seen.has(cur.id)) {
    seen.add(cur.id);
    out.unshift(cur);
    cur = cur.parentId ? getNode(cur.parentId) : undefined;
  }
  return out;
}
const complete = (id: string) => { const c = chainOf(id); return c.length > 0 && c[0].kind === 'top'; };

/** 노드의 조상 경로. 모르면 kb 로 찾아 채운다. */
export function useAncestry(id?: string | null) {
  const qc = useQueryClient();
  const ver = useNodeVersion();
  useEffect(() => {
    if (!id || complete(id)) return;
    let stop = false;
    (async () => {
      try {
        if (id.startsWith('fam_')) {
          const list = await qc.fetchQuery({ queryKey: ['kb', 'models', { family_id: id }], queryFn: ({ signal }) => kb.models({ family_id: id, limit: 100 }, signal), staleTime: 300_000 });
          const first = list.items?.[0];
          if (!first || stop) return;
          const d = await qc.fetchQuery({ queryKey: ['kb', 'model', first.model_code], queryFn: ({ signal }) => kb.model(first.model_code, signal), staleTime: 300_000 });
          const cp = d.category_path ?? [];
          cp.forEach((c, i) => registerNode({ id: c.id, name: c.name, parentId: i === 0 ? null : cp[i - 1].id, kind: i === 0 ? 'top' : 'cat' }));
          registerNode({ id, name: familyLabel(d.family), parentId: cp.length ? cp[cp.length - 1].id : null, kind: 'fam' });
        } else if (id.startsWith('cat_')) {
          const top = await qc.fetchQuery({ queryKey: ['kb', 'categories', null], queryFn: ({ signal }) => kb.categories(null, signal), staleTime: 300_000 });
          registerCategories(top.items, null);
          for (const t of top.items ?? []) {
            if (stop) return;
            const ch = await qc.fetchQuery({ queryKey: ['kb', 'categories', t.id], queryFn: ({ signal }) => kb.categories(t.id, signal), staleTime: 300_000 });
            registerCategories(ch.items, t.id);
            if (ch.items?.some((c) => c.id === id)) break;
          }
        } else if (id.startsWith('top_')) {
          const top = await qc.fetchQuery({ queryKey: ['kb', 'categories', null], queryFn: ({ signal }) => kb.categories(null, signal), staleTime: 300_000 });
          registerCategories(top.items, null);
        }
      } catch { /* 경로를 못 찾으면 이름만 보인다 */ }
    })();
    return () => { stop = true; };
  }, [id, qc]);
  return useMemo(() => chainOf(id), [id, ver]);
}
