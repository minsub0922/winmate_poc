/**
 * 가치 맵(새 VP 흐름) API — contracts/vp.json `/v1/value-maps*` → @/api/gen/vp.
 * 화면은 문서 하나(VMDoc)를 읽고, 바꾸는 호출은 모두 고친 문서를 돌려준다(→ 캐시에 바로 넣는다).
 * `dss_changed`(Storyboard 의 DSS 가 바뀜)는 GET · 다시 가져오기 응답에만 계산돼 온다 → 다른 응답을 넣을 때는 앞의 값을 잇는다.
 * 최종본에서 바로 고치기(v63): 칸을 떠날 때마다 고침 호출이 나가므로, 쓰기는 한 줄로 세워 차례대로 보낸다 — 저장 · 되돌리기는 앞의 고침이 끝난 뒤에 간다.
 * 응답 `changes` = 저장한 판과 다른 곳 수(머리 「고친 곳 n」).
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useRef } from 'react';
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
export type VMDssChange = S['VMDssChange'];
export type VMResync = S['VMResync'];

const P = (map_id: string) => ({ params: { path: { map_id } } });
export const vmKey = (id: string) => ['vp', 'vmap', id] as const;
export const vmListKey = ['vp', 'vmaps'] as const;

export function useValueMap(id: string) {
  return useQuery({ queryKey: vmKey(id), queryFn: async () => normalize(unwrap(await api.vp.GET('/v1/value-maps/{map_id}', P(id)))), enabled: !!id });
}

export function useValueMaps() {
  return useQuery({ queryKey: vmListKey, queryFn: async () => unwrap(await api.vp.GET('/v1/value-maps', { params: { query: { limit: 50 } } })) });
}

/** 만들기 — Storyboard(sb_id 만)로 시작하면 같은 Storyboard 의 저장 전 초안이 있을 때 서버가 그 초안을 돌려준다 */
export async function createValueMap(body: S['VMCreate']): Promise<VMDoc> {
  return normalize(unwrap(await api.vp.POST('/v1/value-maps', { body })));
}

/** 저장 전 초안 지우기(목록 줄의 ×) — 저장한 맵은 409 SAVED_CONTENT */
export async function deleteValueMap(id: string): Promise<void> {
  const r = await api.vp.DELETE('/v1/value-maps/{map_id}', P(id));
  if (!r.response.ok) unwrap(r);
}

/** 문서를 돌려주는 호출 묶음 — 성공하면 캐시를 그 문서로 바꾼다. 화면에서 한 번만 부르고 아래로 넘긴다(쓰기 줄이 하나여야 한다) */
export function useVmActions(id: string) {
  const qc = useQueryClient();
  const chain = useRef<Promise<unknown>>(Promise.resolve());
  const put = (raw: S['VMDoc'], keepDss = true) => {
    const got = normalize(raw);
    const d = keepDss ? { ...got, dss_changed: got.dss_changed ?? qc.getQueryData<VMDoc>(vmKey(id))?.dss_changed ?? null } : got;
    qc.setQueryData(vmKey(id), d);
    return d;
  };
  /** 쓰기 줄 — 앞의 쓰기가 끝난 뒤에 보낸다(실패해도 다음 쓰기는 간다) */
  const queue = <T,>(fn: () => Promise<T>): Promise<T> => {
    const p = chain.current.then(fn, fn);
    chain.current = p.catch(() => undefined);
    return p;
  };
  const m = useMutation({ mutationFn: async (fn: () => Promise<S['VMDoc']>) => put(await fn()) });
  const run = (fn: () => Promise<S['VMDoc']>) => queue(() => m.mutateAsync(fn));
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
    /** 점선(AI 추천) 모두 지우기 */
    clearPending: () => run(async () => unwrap(await api.vp.POST('/v1/value-maps/{map_id}:clear-pending', P(id)))),
    suggest: (itemKeys?: string[]) => queue(async () => {
      const r = unwrap(await api.vp.POST('/v1/value-maps/{map_id}:suggest', { ...P(id), body: { item_keys: itemKeys ?? null } }));
      put(r.map);
      return r;
    }),
    inferNeed: (valueId: string) => queue(async () => {
      const r = unwrap(await api.vp.POST('/v1/value-maps/{map_id}/values/{value_id}:infer-need', { params: { path: { map_id: id, value_id: valueId } } }));
      put(r.map);
      return r;
    }),
    /** DSS 다시 가져오기 — 응답의 dss_changed(대개 null)를 그대로 넣는다 */
    resync: () => queue(async () => put(unwrap(await api.vp.POST('/v1/value-maps/{map_id}:resync-dss', P(id))), false)),
    /** 저장(판 +1) — 앞의 고침이 끝난 뒤에 · 끝나면 문서를 새로 읽어 그 자리에서 「저장됨」으로 */
    finish: () => queue(async (): Promise<VMStageOut & { doc: VMDoc }> => {
      const r = unwrap(await api.vp.POST('/v1/value-maps/{map_id}:finish', P(id)));
      const doc = put(unwrap(await api.vp.GET('/v1/value-maps/{map_id}', P(id))), false);
      return { ...r, doc };
    }),
    /** 저장한 판으로 되돌리기(저장한 적 없으면 409 NOT_SAVED) */
    revert: () => run(async () => unwrap(await api.vp.POST('/v1/value-maps/{map_id}:revert', P(id)))),
  };
}

export function useLinked(id: string, itemKey: string | null) {
  return useQuery({
    queryKey: ['vp', 'vmap', id, 'linked', itemKey],
    enabled: !!id && !!itemKey,
    queryFn: async () => unwrap(await api.vp.GET('/v1/value-maps/{map_id}/items/{item_key}/linked', { params: { path: { map_id: id, item_key: itemKey! } } })),
  });
}

/** 「DSS-01 v1 → v2」 — 같은 DSS 면 뒤쪽은 판만 */
export function dssFromTo(c: { from: string; to: string }) {
  const ref = c.from.replace(/ v\d+$/, '');
  return `${c.from} → ${c.to.startsWith(`${ref} v`) ? c.to.slice(ref.length + 1) : c.to}`;
}

/** 안내 줄 문장 — 「Storyboard의 DSS가 바뀌었어요 · DSS-01 v1 → v2 · 제품 2 추가 · 1 빠짐」 */
export function dssChangeText(c: VMDssChange) {
  const parts = [c.added ? `제품 ${c.added} 추가` : '', c.removed ? `${c.added ? '' : '제품 '}${c.removed} 빠짐` : '', c.changed ? `놓인 공간 ${c.changed} 바뀜` : ''].filter(Boolean);
  return [c.ref_changed ? 'Storyboard의 DSS가 다른 DSS로 바뀌었어요' : 'Storyboard의 DSS가 바뀌었어요', dssFromTo(c), ...parts].join(' · ');
}

/** 다시 가져온 뒤 토스트 */
export function resyncToast(r: VMResync | null | undefined) {
  if (!r) return 'DSS를 다시 가져왔어요';
  const parts = [r.added?.length ? `새 후보 ${r.added.length}(고르기에서)` : '', r.kept?.length ? `고른 것 ${r.kept.length}개 「DSS에서 빠짐」` : '',
    r.removed?.length ? `후보 ${r.removed.length} 뺌` : ''].filter(Boolean);
  return ['DSS를 다시 가져왔어요', ...(parts.length ? parts : ['바뀐 제품 없음'])].join(' · ');
}

export function counts(d: VMDoc | undefined) {
  const c = d?.counts;
  return { items: c?.items ?? 0, values: c?.values ?? 0, needs: c?.needs ?? 0, pending: c?.pending ?? 0 };
}
