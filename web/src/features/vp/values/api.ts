/**
 * 가치 맵(새 VP 흐름) API — contracts/vp.json `/v1/value-maps*` → @/api/gen/vp.
 * 화면은 문서 하나(VMDoc)를 읽고, 바꾸는 호출은 모두 고친 문서를 돌려준다(→ 캐시에 바로 넣는다).
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api, unwrap } from '@/api/client';
import type { components } from '@/api/gen/vp';

type S = components['schemas'];
export type VMValue = S['VMValue'];
/** 응답의 기본값 목록(default_factory)은 계약에서 선택 필드다 → 화면에서는 늘 배열로 맞춘다 */
export type VMItem = Omit<S['VMItem'], 'values' | 'spaces'> & { values: VMValue[]; spaces: string[] };
export type VMDoc = Omit<S['VMDoc'], 'items' | 'candidates'> & { items: VMItem[]; candidates: S['VMCandidate'][] };
export function normalize(d: S['VMDoc']): VMDoc {
  return { ...d, candidates: d.candidates ?? [], items: (d.items ?? []).map((it) => ({ ...it, values: it.values ?? [], spaces: it.spaces ?? [] })) };
}
export type VMCandidate = S['VMCandidate'];
export type VMLinked = S['VMLinked'];
export type VMStageOut = S['VMStageOut'];
export type VMListItem = S['VMListItem'];

const P = (map_id: string) => ({ params: { path: { map_id } } });
export const vmKey = (id: string) => ['vp', 'vmap', id] as const;

export function useValueMap(id: string) {
  return useQuery({ queryKey: vmKey(id), queryFn: async () => normalize(unwrap(await api.vp.GET('/v1/value-maps/{map_id}', P(id)))), enabled: !!id });
}

export function useValueMaps() {
  return useQuery({ queryKey: ['vp', 'vmaps'], queryFn: async () => unwrap(await api.vp.GET('/v1/value-maps', { params: { query: { limit: 50 } } })) });
}

export async function createValueMap(body: S['VMCreate']): Promise<VMDoc> {
  return normalize(unwrap(await api.vp.POST('/v1/value-maps', { body })));
}

/** 문서를 돌려주는 호출 묶음 — 성공하면 캐시를 그 문서로 바꾼다 */
export function useVmActions(id: string) {
  const qc = useQueryClient();
  const put = (raw: S['VMDoc']) => { const d = normalize(raw); qc.setQueryData(vmKey(id), d); return d; };
  const m = useMutation({ mutationFn: async (fn: () => Promise<S['VMDoc']>) => put(await fn()) });
  const run = (fn: () => Promise<S['VMDoc']>) => m.mutateAsync(fn);
  return {
    busy: m.isPending,
    error: m.error,
    setItems: (items: VMCandidate[]) => run(async () => unwrap(await api.vp.PUT('/v1/value-maps/{map_id}/items', { ...P(id), body: { items } }))),
    addValue: (itemKey: string, body: S['VMAddValue']) => run(async () => unwrap(await api.vp.POST('/v1/value-maps/{map_id}/items/{item_key}/values',
      { params: { path: { map_id: id, item_key: itemKey } }, body }))),
    patchValue: (valueId: string, body: S['VMPatchValue']) => run(async () => unwrap(await api.vp.PATCH('/v1/value-maps/{map_id}/values/{value_id}',
      { params: { path: { map_id: id, value_id: valueId } }, body }))),
    deleteValue: (valueId: string) => run(async () => unwrap(await api.vp.DELETE('/v1/value-maps/{map_id}/values/{value_id}',
      { params: { path: { map_id: id, value_id: valueId } } }))),
    acceptAll: () => run(async () => unwrap(await api.vp.POST('/v1/value-maps/{map_id}:accept-all', P(id)))),
    importValue: (itemKey: string, body: S['VMImportValue']) => run(async () => unwrap(await api.vp.POST('/v1/value-maps/{map_id}/items/{item_key}/values:import',
      { params: { path: { map_id: id, item_key: itemKey } }, body }))),
    suggest: async (itemKeys?: string[]) => {
      const r = unwrap(await api.vp.POST('/v1/value-maps/{map_id}:suggest', { ...P(id), body: { item_keys: itemKeys ?? null } }));
      put(r.map);
      return r;
    },
    inferNeed: async (valueId: string) => {
      const r = unwrap(await api.vp.POST('/v1/value-maps/{map_id}/values/{value_id}:infer-need', { params: { path: { map_id: id, value_id: valueId } } }));
      put(r.map);
      return r;
    },
    finish: async (): Promise<VMStageOut> => {
      const r = unwrap(await api.vp.POST('/v1/value-maps/{map_id}:finish', P(id)));
      qc.invalidateQueries({ queryKey: vmKey(id) });
      return r;
    },
  };
}

export function useLinked(id: string, itemKey: string | null) {
  return useQuery({
    queryKey: ['vp', 'vmap', id, 'linked', itemKey],
    enabled: !!id && !!itemKey,
    queryFn: async () => unwrap(await api.vp.GET('/v1/value-maps/{map_id}/items/{item_key}/linked', { params: { path: { map_id: id, item_key: itemKey! } } })),
  });
}

export function counts(d: VMDoc | undefined) {
  const c = d?.counts;
  return { items: c?.items ?? 0, values: c?.values ?? 0, needs: c?.needs ?? 0, pending: c?.pending ?? 0 };
}
