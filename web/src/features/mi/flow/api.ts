/**
 * 새 MI 흐름 API — contracts/mi.json `/v1/mi-flows*` → @/api/gen/mi(MF* 스키마). 화면은 문서 하나(MFDoc)를 읽고,
 * 바꾸는 호출은 모두 고친 문서를 돌려준다(캐시에 그대로 넣는다). AI 가 일하는 동안(analyzing · searching)은 문서를 폴링한다.
 */
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api, unwrap } from '@/api/client';
import type { components } from '@/api/gen/mi';

type S = components['schemas'];
export type MFDoc = S['MFDoc'];
export type MFItem = S['MFItem'];
export type MFQuery = S['MFQuery'];
export type MFQueries = S['MFQueries'];
export type MFFilters = S['MFFilters'];
export type MFStep = S['MFStep'];
export type MFResult = S['MFResult'];
export type MFStageOut = S['MFStageOut'];
export type MFListItem = S['MFListItem'];
export type GroupKey = 'market' | 'customer' | 'user';

const mi = api.mi;
const P = (flow_id: string) => ({ params: { path: { flow_id } } });

/** 보드 MI2 · MI3 그룹 순서(시장 · 고객사 · 사용자) */
export const GROUPS: Array<{ key: GroupKey; label: '시장' | '고객사' | '사용자' }> = [
  { key: 'market', label: '시장' }, { key: 'customer', label: '고객사' }, { key: 'user', label: '사용자' },
];
/** 보드 MI2 검색 조건(기간 하나 · 출처 여러 개) */
export const PERIODS = ['최근 1년', '최근 3년', '전체'] as const;
export const SOURCE_TYPES = ['뉴스', '공시 · IR', '리포트', '정부 통계'] as const;

export const mfKey = (id: string) => ['mi', 'mi-flow', id] as const;
export const mfListKey = ['mi', 'mi-flows'] as const;

/** 편집 경로(허브 cells[].route 와 같다) */
export const mfRoute = (id: string) => `/mi/flow/${id}`;

/** 응답 스키마의 기본값 칸은 선택(?)으로 생성된다 — 화면은 늘 배열로 쓴다 */
export type Qs = Record<GroupKey, MFQuery[]>;
export const qsOf = (d: MFDoc): Qs => ({ market: d.queries?.market ?? [], customer: d.queries?.customer ?? [], user: d.queries?.user ?? [] });
export const itemsOf = (d: MFDoc | undefined): MFItem[] => d?.items ?? [];
export const nOn = (rows: MFQuery[]) => rows.filter((q) => q.on !== false && q.text.trim()).length;

export const isBusy = (d: MFDoc | undefined) => !!d && (d.phase === 'analyzing' || d.phase === 'searching');

export function useMiFlow(id: string | undefined) {
  return useQuery({
    queryKey: mfKey(id ?? ''), enabled: !!id,
    queryFn: async () => unwrap(await mi.GET('/v1/mi-flows/{flow_id}', P(id!))),
    refetchInterval: (q) => (isBusy(q.state.data as MFDoc | undefined) ? 600 : false),
  });
}

export function useMiFlows() {
  return useQuery({ queryKey: mfListKey, queryFn: async () => unwrap(await mi.GET('/v1/mi-flows', { params: { query: { limit: 100 } } })) });
}

export const mfApi = {
  create: async (sbId: string) => unwrap(await mi.POST('/v1/mi-flows', { body: { sb_id: sbId } })),
  get: async (id: string) => unwrap(await mi.GET('/v1/mi-flows/{flow_id}', P(id))),
  patch: async (id: string, body: S['MFPatch']) => unwrap(await mi.PATCH('/v1/mi-flows/{flow_id}', { ...P(id), body })),
  analyze: async (id: string) => unwrap(await mi.POST('/v1/mi-flows/{flow_id}:analyze', P(id))),
  search: async (id: string) => unwrap(await mi.POST('/v1/mi-flows/{flow_id}:search', P(id))),
  item: async (id: string, itemId: string, body: S['MFItemPatch']) =>
    unwrap(await mi.PATCH('/v1/mi-flows/{flow_id}/items/{item_id}', { params: { path: { flow_id: id, item_id: itemId } }, body })),
  finish: async (id: string) => unwrap(await mi.POST('/v1/mi-flows/{flow_id}:finish', P(id))),
  stage: async (id: string) => unwrap(await mi.GET('/v1/mi-flows/{flow_id}/stage', P(id))),
};

/** 바꾸는 호출 → 돌려받은 문서를 캐시에 넣는다(목록 · 허브 캐시는 새로) */
export function useMfActions(id: string) {
  const qc = useQueryClient();
  const put = (d: MFDoc) => { qc.setQueryData(mfKey(id), d); return d; };
  const run = async (fn: () => Promise<MFDoc>) => {
    const d = put(await fn());
    void qc.invalidateQueries({ queryKey: mfListKey });
    return d;
  };
  return {
    patch: (body: S['MFPatch']) => run(() => mfApi.patch(id, body)),
    analyze: () => run(() => mfApi.analyze(id)),
    search: () => run(() => mfApi.search(id)),
    item: (itemId: string, body: S['MFItemPatch']) => run(() => mfApi.item(id, itemId, body)),
    finish: async () => {
      const out = await mfApi.finish(id);
      void qc.invalidateQueries({ queryKey: mfKey(id) });
      void qc.invalidateQueries({ queryKey: mfListKey });
      void qc.invalidateQueries({ queryKey: ['storyboard'] });
      return out;
    },
    refresh: async () => put(await mfApi.get(id)),
  };
}
