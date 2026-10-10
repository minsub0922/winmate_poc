/**
 * Spec 시트 새 흐름 API — contracts/spec.json `/v1/spec-flows*` → @/api/gen/spec.
 * 화면은 문서 하나(SFDoc)를 읽고, 바꾸는 호출은 고친 문서를 돌려준다(→ 캐시에 바로 넣는다).
 * 체크 · 칩은 먼저 화면을 바꾸고(낙관적), 마지막 요청의 응답만 캐시에 넣는다(빠르게 여러 번 눌러도 순서가 꼬이지 않게).
 */
import { useRef } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api, unwrap } from '@/api/client';
import type { components } from '@/api/gen/spec';

type S = components['schemas'];
export type SFRow = Omit<S['SFRow'], 'spaces' | 'cells' | 'pending' | 'warnings' | 'qty'> & {
  spaces: string[]; cells: Record<string, string>; pending: string[]; warnings: S['SFWarning'][]; qty: number | null;
};
export type SFDoc = Omit<S['SFDoc'], 'rows' | 'items' | 'columns'> & { rows: SFRow[]; items: string[]; columns: S['SFColumn'][] };
export type SFStageOut = S['SFStageOut'];
export type SFFile = S['SFFile'];
export type SFModelOption = S['SFModelOption'];
export type SFPatch = S['SFPatch'];
export type SFRowPatch = S['SFRowPatch'];

export function normalize(d: S['SFDoc']): SFDoc {
  return {
    ...d, items: d.items ?? [], columns: d.columns ?? [],
    rows: (d.rows ?? []).map((r) => ({ ...r, spaces: r.spaces ?? [], cells: r.cells ?? {}, pending: r.pending ?? [], warnings: r.warnings ?? [], qty: r.qty ?? null })),
  };
}

const P = (flow_id: string) => ({ params: { path: { flow_id } } });
export const sfKey = (id: string) => ['spec', 'flow', id] as const;
export const sfListKey = ['spec', 'flows'] as const;
export const sfRoute = (id: string) => `/spec/flow/${id}`;

export function useSpecFlow(id: string) {
  return useQuery({ queryKey: sfKey(id), enabled: !!id, queryFn: async () => normalize(unwrap(await api.spec.GET('/v1/spec-flows/{flow_id}', P(id)))) });
}

export function useSpecFlows() {
  return useQuery({ queryKey: sfListKey, queryFn: async () => unwrap(await api.spec.GET('/v1/spec-flows', { params: { query: { limit: 50 } } })) });
}

export async function createSpecFlow(sbId: string): Promise<SFDoc> {
  return normalize(unwrap(await api.spec.POST('/v1/spec-flows', { body: { sb_id: sbId } })));
}

export async function modelOptions(id: string, rowKey: string, q?: string) {
  return unwrap(await api.spec.GET('/v1/spec-flows/{flow_id}/rows/{row_key}/models', { params: { path: { flow_id: id, row_key: rowKey }, query: { q: q || null } } }));
}

export function useSfActions(id: string) {
  const qc = useQueryClient();
  const seq = useRef(0);
  const cur = () => qc.getQueryData<SFDoc>(sfKey(id));
  const run = async (optimistic: ((d: SFDoc) => SFDoc) | null, call: () => Promise<S['SFDoc']>) => {
    const n = ++seq.current;
    const before = cur();
    if (optimistic && before) qc.setQueryData(sfKey(id), optimistic(before));
    try {
      const d = normalize(await call());
      if (n === seq.current) qc.setQueryData(sfKey(id), d);
      return d;
    } catch (e) {
      if (n === seq.current) void qc.invalidateQueries({ queryKey: sfKey(id) });
      throw e;
    }
  };
  return {
    patch: (body: SFPatch, optimistic?: (d: SFDoc) => SFDoc) =>
      run(optimistic ?? null, async () => unwrap(await api.spec.PATCH('/v1/spec-flows/{flow_id}', { ...P(id), body }))),
    patchRow: (rowKey: string, body: SFRowPatch, optimistic?: (d: SFDoc) => SFDoc) =>
      run(optimistic ?? null, async () => unwrap(await api.spec.PATCH('/v1/spec-flows/{flow_id}/rows/{row_key}', { params: { path: { flow_id: id, row_key: rowKey } }, body }))),
    finish: async (): Promise<SFStageOut> => {
      const r = unwrap(await api.spec.POST('/v1/spec-flows/{flow_id}:finish', P(id)));
      void qc.invalidateQueries({ queryKey: sfKey(id) });
      void qc.invalidateQueries({ queryKey: sfListKey });
      void qc.invalidateQueries({ queryKey: ['storyboard'] });   // 허브 진행 칸 · flow.json · 목록(보드 List)
      return r;
    },
  };
}

/** 경고 종류 → 제품 줄 · 팝업에 붙는 짧은 이름(서버 rules: spec_flow.row_warnings) */
export const WARN_SHORT: Record<string, string> = {
  not_in_catalog: '카탈로그에 없음', discontinued: '단종', sold_out: '품절', mismatch: '모델 불일치', family_default: '대표 모델',
};

/** 항목 칩 이름(보드 SP2 ITEMS — 칩은 화면 말, 미리보기 · 시트는 표기 언어) */
export const ITEM_KO: Record<string, string> = {
  size_resolution: '화면 크기 · 해상도', brightness_contrast: '밝기 · 명암비', io_ports: '입출력 단자', power: '소비전력',
  size_weight: '크기 · 무게', install: '설치 방식', operation_hours: '운영 시간', warranty: '보증',
};
