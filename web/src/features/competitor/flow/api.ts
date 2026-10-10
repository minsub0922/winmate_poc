/**
 * 경쟁사 리스트업(새 CA 흐름) API — contracts/competitor.json `/v1/ca-flows*` → @/api/gen/competitor.
 * 화면은 문서 하나(CFDoc)를 읽고, 바꾸는 호출은 모두 고친 문서를 돌려준다(→ 캐시에 바로 넣는다).
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api, unwrap } from '@/api/client';
import type { components } from '@/api/gen/competitor';

type S = components['schemas'];
export type CFDim = S['CFDim'];
export type CFMatch = S['CFMatch'];
export type CFClaim = S['CFClaim'];
export type CFCriterion = S['CFCriterion'];
export type CFWiki = S['CFWiki'];
export type CFDssItem = S['CFDssItem'];
/** 응답의 기본값 목록(default_factory)은 계약에서 선택 필드다 → 화면에서는 늘 배열로 맞춘다 */
export type CFCompetitor = Omit<S['CFCompetitor'], 'categories' | 'spaces' | 'criteria' | 'matches' | 'pros' | 'cons' | 'claims'> & {
  categories: string[]; spaces: string[]; criteria: CFCriterion[]; matches: CFMatch[]; pros: string[]; cons: string[]; claims: CFClaim[];
};
export type CFDoc = Omit<S['CFDoc'], 'competitors' | 'dss_items'> & { competitors: CFCompetitor[]; dss_items: CFDssItem[] };
export type CFStageOut = S['CFStageOut'];
export type CFCandidatesResult = S['CFCandidatesResult'];
export type DimKey = 'spec' | 'price' | 'cases' | 'esg' | 'brand';
export type Verdict = CFDim['verdict'];

export const DIMS: Array<[DimKey, string]> = [['spec', '스펙'], ['price', '가격'], ['cases', '유관 사례'], ['esg', 'ESG'], ['brand', '브랜드 평판']];
export const VERDICTS: Array<NonNullable<Verdict>> = ['ours-better', 'similar', 'ours-worse', 'no-data'];
export const VERDICT_LABEL: Record<NonNullable<Verdict>, string> = { 'ours-better': '우위', similar: '비슷', 'ours-worse': '열위', 'no-data': '자료 없음' };
export const VERDICT_NEXT: Record<NonNullable<Verdict>, NonNullable<Verdict>> = { 'ours-better': 'similar', similar: 'ours-worse', 'ours-worse': 'no-data', 'no-data': 'ours-better' };
/** 편집 경로(허브 cells[].route 와 같다) */
export const cfRoute = (id: string) => `/competitor/flow/${id}`;
export const cfListKey = ['competitor', 'cflows'] as const;

export function normalize(d: S['CFDoc']): CFDoc {
  return {
    ...d,
    dss_items: d.dss_items ?? [],
    competitors: (d.competitors ?? []).map((c) => ({
      ...c, categories: c.categories ?? [], spaces: c.spaces ?? [], criteria: c.criteria ?? [], matches: c.matches ?? [],
      pros: c.pros ?? [], cons: c.cons ?? [], claims: c.claims ?? [],
    })),
  };
}

const P = (flow_id: string) => ({ params: { path: { flow_id } } });
export const cfKey = (id: string) => ['competitor', 'cflow', id] as const;

export function useCaFlow(id: string) {
  return useQuery({ queryKey: cfKey(id), enabled: !!id, queryFn: async () => normalize(unwrap(await api.competitor.GET('/v1/ca-flows/{flow_id}', P(id)))) });
}

export function useCaFlows() {
  return useQuery({ queryKey: cfListKey, queryFn: async () => unwrap(await api.competitor.GET('/v1/ca-flows', { params: { query: { limit: 50 } } })) });
}

export async function createCaFlow(body: S['CFCreate']): Promise<CFDoc> {
  return normalize(unwrap(await api.competitor.POST('/v1/ca-flows', { body })));
}

/** 문서를 돌려주는 호출 묶음 — 성공하면 캐시를 그 문서로 바꾼다 */
export function useCfActions(id: string) {
  const qc = useQueryClient();
  const put = (raw: S['CFDoc']) => { const d = normalize(raw); qc.setQueryData(cfKey(id), d); return d; };
  const m = useMutation({ mutationFn: async (fn: () => Promise<S['CFDoc']>) => put(await fn()) });
  const run = (fn: () => Promise<S['CFDoc']>) => m.mutateAsync(fn);
  const C = (cid: string) => ({ params: { path: { flow_id: id, cid } } });
  const M = (cid: string, mid: string) => ({ params: { path: { flow_id: id, cid, mid } } });
  return {
    busy: m.isPending,
    addCompetitor: (name: string) => run(async () => unwrap(await api.competitor.POST('/v1/ca-flows/{flow_id}/competitors', { ...P(id), body: { name, lookup: true } }))),
    patchCompetitor: (cid: string, body: S['CFCompetitorPatch']) => run(async () => unwrap(await api.competitor.PATCH('/v1/ca-flows/{flow_id}/competitors/{cid}', { ...C(cid), body }))),
    deleteCompetitor: (cid: string) => run(async () => unwrap(await api.competitor.DELETE('/v1/ca-flows/{flow_id}/competitors/{cid}', C(cid)))),
    addMatch: (cid: string, body: S['CFMatchAdd']) => run(async () => unwrap(await api.competitor.POST('/v1/ca-flows/{flow_id}/competitors/{cid}/matches', { ...C(cid), body }))),
    patchMatch: (cid: string, mid: string, body: S['CFMatchPatch']) => run(async () => unwrap(await api.competitor.PATCH('/v1/ca-flows/{flow_id}/competitors/{cid}/matches/{mid}', { ...M(cid, mid), body }))),
    deleteMatch: (cid: string, mid: string) => run(async () => unwrap(await api.competitor.DELETE('/v1/ca-flows/{flow_id}/competitors/{cid}/matches/{mid}', M(cid, mid)))),
    candidates: async (): Promise<CFCandidatesResult> => {
      const r = unwrap(await api.competitor.POST('/v1/ca-flows/{flow_id}:candidates', P(id)));
      put(r.flow);
      return r;
    },
    finish: async (): Promise<CFStageOut> => {
      const r = unwrap(await api.competitor.POST('/v1/ca-flows/{flow_id}:finish', P(id)));
      void qc.invalidateQueries({ queryKey: cfKey(id) });
      void qc.invalidateQueries({ queryKey: ['storyboard'] });
      void qc.invalidateQueries({ queryKey: cfListKey });
      return r;
    },
  };
}
