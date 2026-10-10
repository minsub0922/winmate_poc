/**
 * 공간 → 시나리오 → 장면(새 흐름) API — contracts/scenario.json `/v1/space-sets*` → @/api/gen/scenario.
 * 만들기는 Gate 에서 고른 Storyboard(`sb_id`)의 DSS 로 시작하고, 저장(`:finish`)은 허브 stages.sc 에 반영된다(flow_sync).
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

/** 목록(보드 List content=sc 의 작성 중 초안) */
export function useSpaceSets() {
  return useQuery({ queryKey: ['scenario', 'spacesets'], queryFn: async () => unwrap(await api.scenario.GET('/v1/space-sets', { params: { query: { limit: 100 } } })) });
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
