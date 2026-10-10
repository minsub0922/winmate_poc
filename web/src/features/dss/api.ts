/**
 * 공간별 제품 매칭 DSS(새 흐름) API — contracts/dss.json `/v1/dss*` → @/api/gen/dss(DS* 스키마).
 * 바꾸는 호출은 모두 고친 DSS 문서(DSDoc)를 돌려준다 → 캐시에 그대로 넣는다(다시 읽지 않음).
 */
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api, unwrap } from '@/api/client';
import type { components } from '@/api/gen/dss';

type S = components['schemas'];
export type DSProduct = S['DSProduct'];
export type DSSpaceRec = S['DSSpaceRec'];
export type DSSolution = Omit<S['DSSolution'], 'links'> & { links: string[] };
/** 서버는 배열을 늘 채워 보내지만(default_factory) 생성 타입은 선택이라 — 화면이 쓰는 모양으로 맞춘다(norm) */
export type DSSpace = Omit<S['DSSpace'], 'products'> & { products: DSProduct[] };
export type DSDoc = Omit<S['DSDoc'], 'spaces' | 'space_recs' | 'solutions' | 'solution_recs' | 'reqs' | 'industry_options'> & {
  spaces: DSSpace[]; space_recs: DSSpaceRec[]; solutions: DSSolution[]; solution_recs: S['DSSolutionRec'][]; reqs: S['DSReq'][]; industry_options: string[];
};
export type DSSolutionOption = Omit<S['DSSolutionOption'], 'links'> & { links: string[] };
export type DSSolutionOptions = S['DSSolutionOptions'];
export type DSStageOut = S['DSStageOut'];
export type DSCandidate = S['DSCandidate'];
export type DSAddProduct = S['DSAddProduct'];
export type DSSuggestResult = Omit<S['DSSuggestResult'], 'doc'> & { doc: DSDoc };
export type SuggestScope = S['DSSuggestBody']['scope'];
export type By = DSProduct['by'];

const ds = api.dss;

export function norm(d: S['DSDoc']): DSDoc {
  return {
    ...d, spaces: (d.spaces ?? []).map((sp) => ({ ...sp, products: sp.products ?? [] })), space_recs: d.space_recs ?? [],
    solutions: (d.solutions ?? []).map((so) => ({ ...so, links: so.links ?? [] })), solution_recs: d.solution_recs ?? [], reqs: d.reqs ?? [], industry_options: d.industry_options ?? [],
  };
}
const P = (dss_id: string) => ({ params: { path: { dss_id } } });

export const dsKey = (id: string) => ['dss', 'doc', id] as const;
export const dsListKey = ['dss', 'list'] as const;
export const dsOptionsKey = (id: string) => ['dss', 'solution-options', id] as const;

/** 편집 경로(허브 cells[].route 와 같다) */
export const dsRoute = (id: string) => `/dss/${id}`;

export function useDss(id: string | undefined) {
  return useQuery({ queryKey: dsKey(id ?? ''), enabled: !!id, queryFn: async () => norm(unwrap(await ds.GET('/v1/dss/{dss_id}', P(id!)))) });
}

export function useDssList() {
  return useQuery({ queryKey: dsListKey, queryFn: async () => unwrap(await ds.GET('/v1/dss', { params: { query: { limit: 100 } } })) });
}

export function useSolutionOptions(id: string, enabled = true) {
  return useQuery({ queryKey: dsOptionsKey(id), enabled, queryFn: async () => {
    const o = unwrap(await ds.GET('/v1/dss/{dss_id}/solution-options', P(id)));
    return { ...o, items: o.items.map((x) => ({ ...x, links: x.links ?? [] })) };
  } });
}

export async function fetchCandidates(id: string, spaceKey: string) {
  return unwrap(await ds.GET('/v1/dss/{dss_id}/spaces/{space_key}/candidates', { params: { path: { dss_id: id, space_key: spaceKey } } }));
}

/** 만들기 — 이 Storyboard 의 저장 전 초안이 이미 있으면 서버가 그것을 200 으로 돌려준다(reused) */
export async function createDss(sbId: string) {
  const res = await ds.POST('/v1/dss', { body: { sb_id: sbId } });
  return { doc: norm(unwrap(res)), reused: res.response.status === 200 };
}

/** 목록 줄 × — 저장 전 초안을 지우고(204, 저장한 것은 409 SAVED_CONTENT) 목록 · 사이드바 작업 이력을 새로 읽게 한다 */
export function useDsDelete() {
  const qc = useQueryClient();
  return async (id: string) => {
    unwrap(await ds.DELETE('/v1/dss/{dss_id}', P(id)));
    qc.removeQueries({ queryKey: dsKey(id) });
    for (const queryKey of [dsListKey, ['ws', 'items'], ['ws', 'recent'], ['ws', 'counts']]) void qc.invalidateQueries({ queryKey });
  };
}

/** 문서 하나를 고치는 호출 묶음 — 결과 문서를 캐시에 넣고, 솔루션 카드(함께 쓰는 제품 · 겹침)는 새로 읽게 한다 */
export function useDsActions(id: string) {
  const qc = useQueryClient();
  const put = (raw: S['DSDoc']) => {
    const d = norm(raw);
    qc.setQueryData(dsKey(id), d);
    void qc.invalidateQueries({ queryKey: dsOptionsKey(id) });
    void qc.invalidateQueries({ queryKey: dsListKey });
    return d;
  };
  const path = { dss_id: id };
  return {
    setIndustry: async (value: string | null) => put(unwrap(await ds.PUT('/v1/dss/{dss_id}/industry', { ...P(id), body: { value, accept_ai: false } }))),
    acceptIndustry: async () => put(unwrap(await ds.PUT('/v1/dss/{dss_id}/industry', { ...P(id), body: { accept_ai: true } }))),
    addSpace: async (name: string) => put(unwrap(await ds.POST('/v1/dss/{dss_id}/spaces', { ...P(id), body: { name } }))),
    deleteSpace: async (key: string) => put(unwrap(await ds.DELETE('/v1/dss/{dss_id}/spaces/{space_key}', { params: { path: { ...path, space_key: key } } }))),
    addProduct: async (key: string, body: DSAddProduct) =>
      put(unwrap(await ds.POST('/v1/dss/{dss_id}/spaces/{space_key}/products', { params: { path: { ...path, space_key: key } }, body }))),
    setQty: async (pid: string, qty: string) =>
      put(unwrap(await ds.PATCH('/v1/dss/{dss_id}/products/{product_id}', { params: { path: { ...path, product_id: pid } }, body: { qty } }))),
    acceptProduct: async (pid: string) =>
      put(unwrap(await ds.PATCH('/v1/dss/{dss_id}/products/{product_id}', { params: { path: { ...path, product_id: pid } }, body: { accept: true } }))),
    deleteProduct: async (pid: string) =>
      put(unwrap(await ds.DELETE('/v1/dss/{dss_id}/products/{product_id}', { params: { path: { ...path, product_id: pid } } }))),
    acceptAll: async () => put(unwrap(await ds.POST('/v1/dss/{dss_id}:accept-all', P(id)))),
    setSolutions: async (ids: string[]) => put(unwrap(await ds.PUT('/v1/dss/{dss_id}/solutions', { ...P(id), body: { ids } }))),
    suggest: async (scope: SuggestScope): Promise<DSSuggestResult> => {
      const r = unwrap(await ds.POST('/v1/dss/{dss_id}:suggest', { ...P(id), body: { scope } }));
      return { ...r, doc: put(r.doc) };
    },
    finish: async () => {
      const out = unwrap(await ds.POST('/v1/dss/{dss_id}:finish', P(id)));
      void qc.invalidateQueries({ queryKey: dsKey(id) });
      void qc.invalidateQueries({ queryKey: dsListKey });
      void qc.invalidateQueries({ queryKey: ['storyboard'] });
      return out;
    },
  };
}
export type DsActions = ReturnType<typeof useDsActions>;
