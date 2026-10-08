/**
 * 공간 → 시나리오 → 장면(새 흐름) API — contracts/scenario.json `/v1/space-sets*` → @/api/gen/scenario.
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
export type SSDoc = Omit<S['SSDoc'], 'spaces' | 'issues'> & { spaces: SSSpace[]; issues: S['SSIssue'][] };
export type SSStageOut = S['SSStageOut'];

const sc = <T extends { products?: string[] | null; steps?: SSStep[] | null; fields?: SSField[] | null }>(x: T) =>
  ({ ...x, products: x.products ?? [], steps: x.steps ?? [], fields: x.fields ?? [] });

export function normalize(d: S['SSDoc']): SSDoc {
  return {
    ...d, issues: d.issues ?? [],
    spaces: d.spaces.map((s) => ({ ...s, products: s.products ?? [], scenarios: (s.scenarios ?? []).map(sc), candidates: (s.candidates ?? []).map(sc) })),
  };
}

const P = (set_id: string) => ({ params: { path: { set_id } } });
export const ssKey = (id: string) => ['scenario', 'spaceset', id] as const;

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
