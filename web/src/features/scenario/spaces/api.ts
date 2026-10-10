/**
 * 공간 → 시나리오 → 장면(새 흐름) API — contracts/scenario.json `/v1/space-sets*` → @/api/gen/scenario.
 * 만들기는 Gate 에서 고른 Storyboard(`sb_id`)의 DSS 로 시작하고, 저장(`:finish`)은 허브 stages.sc 에 반영된다(flow_sync).
 * 같은 Storyboard 의 저장 전 초안이 있으면 만들기가 그 초안을 돌려준다. `dss_changed` 는 GET · 다시 가져오기 응답에만 계산돼 온다.
 */
import { useQuery } from '@tanstack/react-query';
import { api, unwrap } from '@/api/client';
import type { components } from '@/api/gen/scenario';

type S = components['schemas'];
export type SSStep = S['SSStep'];
export type SSField = S['SSFieldKV'];
export type SSProduct = S['SSProduct'];
export type SSScenario = Omit<S['SSScenario'], 'products' | 'steps' | 'fields'> & { products: string[]; steps: SSStep[]; fields: SSField[] };
export type SSCandidate = Omit<S['SSCandidate'], 'products' | 'steps' | 'fields'> & { products: string[]; steps: SSStep[]; fields: SSField[] };
export type SSSpace = Omit<S['SSSpace'], 'products' | 'scenarios' | 'candidates'> & { products: SSProduct[]; scenarios: SSScenario[]; candidates: SSCandidate[] };
export type SSDssItem = Omit<S['SSDssItem'], 'spaces' | 'links'> & { spaces: string[]; links: string[] };
export type SSDoc = Omit<S['SSDoc'], 'spaces' | 'issues' | 'dss_items'> & { spaces: SSSpace[]; issues: S['SSIssue'][]; dss_items: SSDssItem[] };
export type SSStageOut = S['SSStageOut'];
export type SSListItem = S['SSListItem'];
export type SSDssChange = S['SSDssChange'];
export type SSResync = S['SSResync'];

const sc = <T extends { products?: string[] | null; steps?: SSStep[] | null; fields?: SSField[] | null }>(x: T) =>
  ({ ...x, products: x.products ?? [], steps: x.steps ?? [], fields: x.fields ?? [] });

export function normalize(d: S['SSDoc']): SSDoc {
  return {
    ...d, issues: d.issues ?? [],
    dss_items: (d.dss_items ?? []).map((i) => ({ ...i, spaces: i.spaces ?? [], links: i.links ?? [] })),
    spaces: d.spaces.map((s) => ({ ...s, products: s.products ?? [], scenarios: (s.scenarios ?? []).map(sc), candidates: (s.candidates ?? []).map(sc) })),
  };
}

const P = (set_id: string) => ({ params: { path: { set_id } } });
export const ssKey = (id: string) => ['scenario', 'spaceset', id] as const;
export const ssListKey = ['scenario', 'spacesets'] as const;

/** 목록(보드 List content=sc 의 작성 중 초안) */
export function useSpaceSets() {
  return useQuery({ queryKey: ssListKey, queryFn: async () => unwrap(await api.scenario.GET('/v1/space-sets', { params: { query: { limit: 100 } } })) });
}

export function useSpaceSet(id: string) {
  return useQuery({ queryKey: ssKey(id), enabled: !!id, queryFn: async () => normalize(unwrap(await api.scenario.GET('/v1/space-sets/{set_id}', P(id)))) });
}

export async function createSpaceSet(body: S['SSCreate']): Promise<SSDoc> {
  return normalize(unwrap(await api.scenario.POST('/v1/space-sets', { body })));
}

export async function putSpaceSet(id: string, spaces: SSSpace[], expected?: number): Promise<SSDoc> {
  return normalize(unwrap(await api.scenario.PUT('/v1/space-sets/{set_id}', { ...P(id), body: { spaces, expected_version: expected ?? null } })));
}

export async function suggestScenarios(id: string, spaceId: string) {
  const r = unwrap(await api.scenario.POST('/v1/space-sets/{set_id}/spaces/{space_id}:suggest', { params: { path: { set_id: id, space_id: spaceId } } }));
  return { set: normalize(r.set), mode: r.mode };
}

export async function acceptCandidate(id: string, spaceId: string, cid: string): Promise<SSDoc> {
  return normalize(unwrap(await api.scenario.POST('/v1/space-sets/{set_id}/spaces/{space_id}/candidates/{cid}:accept', { params: { path: { set_id: id, space_id: spaceId, cid } } })));
}

export async function dropCandidate(id: string, spaceId: string, cid: string): Promise<SSDoc> {
  return normalize(unwrap(await api.scenario.DELETE('/v1/space-sets/{set_id}/spaces/{space_id}/candidates/{cid}', { params: { path: { set_id: id, space_id: spaceId, cid } } })));
}

export async function finishSpaceSet(id: string): Promise<SSStageOut> {
  return unwrap(await api.scenario.POST('/v1/space-sets/{set_id}:finish', P(id)));
}

/** DSS 다시 가져오기 — 새 공간 · 제품은 더하고, 빠진 제품은 쓰는 시나리오가 없을 때만 뺀다(쓰면 「DSS에서 빠짐」) */
export async function resyncSpaceSet(id: string): Promise<SSDoc> {
  return normalize(unwrap(await api.scenario.POST('/v1/space-sets/{set_id}:resync-dss', P(id))));
}

/** 저장 전 초안 지우기(목록 줄의 ×) — 저장한 묶음은 409 SAVED_CONTENT */
export async function deleteSpaceSet(id: string): Promise<void> {
  const r = await api.scenario.DELETE('/v1/space-sets/{set_id}', P(id));
  if (!r.response.ok) unwrap(r);
}

/** 「DSS-01 v1 → v2」 — 같은 DSS 면 뒤쪽은 판만 */
export function dssFromTo(c: { from: string; to: string }) {
  const ref = c.from.replace(/ v\d+$/, '');
  return `${c.from} → ${c.to.startsWith(`${ref} v`) ? c.to.slice(ref.length + 1) : c.to}`;
}

/** 안내 줄 문장 — 「Storyboard의 DSS가 바뀌었어요 · DSS-01 v1 → v2 · 제품 2 추가 · 1 빠짐 · 공간 1 추가」 */
export function dssChangeText(c: SSDssChange) {
  const parts = [c.added ? `제품 ${c.added} 추가` : '', c.removed ? `${c.added ? '' : '제품 '}${c.removed} 빠짐` : '', c.changed ? `놓인 공간 ${c.changed} 바뀜` : '',
    c.spaces_added ? `공간 ${c.spaces_added} 추가` : '', c.spaces_removed ? `공간 ${c.spaces_removed} 빠짐` : ''].filter(Boolean);
  return [c.ref_changed ? 'Storyboard의 DSS가 다른 DSS로 바뀌었어요' : 'Storyboard의 DSS가 바뀌었어요', dssFromTo(c), ...parts].join(' · ');
}

/** 다시 가져온 뒤 토스트 */
export function resyncToast(r: SSResync | null | undefined) {
  if (!r) return 'DSS를 다시 가져왔어요';
  const parts = [r.spaces_added?.length ? `공간 ${r.spaces_added.length} 추가` : '', r.added?.length ? `제품 ${r.added.length} 추가` : '',
    r.removed?.length ? `${r.removed.length} 뺌` : '', r.kept?.length ? `${r.kept.length}개 「DSS에서 빠짐」` : '',
    r.spaces_removed?.length ? `빈 공간 ${r.spaces_removed.length} 뺌` : ''].filter(Boolean);
  return ['DSS를 다시 가져왔어요', ...(parts.length ? parts : ['바뀐 제품 없음'])].join(' · ');
}
