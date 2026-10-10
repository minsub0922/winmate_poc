/**
 * 고객 요구사항 새 흐름 API — contracts/requirements.json `/v1/rq-flows*` → @/api/gen/requirements(RF* 스키마).
 * 화면은 문서 하나(RFDoc)를 읽고, 바꾸는 호출은 모두 고친 문서를 돌려준다.
 */
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api, unwrap } from '@/api/client';
import type { components } from '@/api/gen/requirements';

type S = components['schemas'];
export type RFDoc = S['RFDoc'];
export type RFKeyman = S['RFKeyman'];
export type RFReq = S['RFReq'];
export type RFDeep = S['RFDeep'];
export type RFDeepQuestion = S['RFDeepQuestion'];
export type RFStageOut = S['RFStageOut'];
export type RFListItem = S['RFListItem'];
export type RFCreate = S['RFCreate'];
export type RFUpdate = S['RFUpdate'];
export type RFAnswer = S['RFAnswer'];
export type By = RFReq['by'];
export type Flag = RFReq['flag'];

const rq = api.requirements;
const P = (flow_id: string) => ({ params: { path: { flow_id } } });

export const rfKey = (id: string) => ['requirements', 'rq-flow', id] as const;
export const rfListKey = ['requirements', 'rq-flows'] as const;

/** 편집 경로(허브 cells[].route 와 같다) */
export const rfRoute = (id: string) => `/requirements/flow/${id}`;

export function useRqFlow(id: string | undefined) {
  return useQuery({ queryKey: rfKey(id ?? ''), enabled: !!id, queryFn: async () => unwrap(await rq.GET('/v1/rq-flows/{flow_id}', P(id!))) });
}

export function useRqFlows() {
  return useQuery({ queryKey: rfListKey, queryFn: async () => unwrap(await rq.GET('/v1/rq-flows', { params: { query: { limit: 100 } } })) });
}

export const rfApi = {
  create: async (body: RFCreate) => unwrap(await rq.POST('/v1/rq-flows', { body })),
  get: async (id: string) => unwrap(await rq.GET('/v1/rq-flows/{flow_id}', P(id))),
  put: async (id: string, body: RFUpdate) => unwrap(await rq.PUT('/v1/rq-flows/{flow_id}', { ...P(id), body })),
  fill: async (id: string, fileIds: string[]) => unwrap(await rq.POST('/v1/rq-flows/{flow_id}:fill', { ...P(id), body: { file_ids: fileIds } })),
  deep: async (id: string) => unwrap(await rq.POST('/v1/rq-flows/{flow_id}/deep-questions', P(id))),
  answer: async (id: string, qid: string, body: RFAnswer) =>
    unwrap(await rq.POST('/v1/rq-flows/{flow_id}/deep-questions/{question_id}:answer', { params: { path: { flow_id: id, question_id: qid } }, body })),
  closeDeep: async (id: string) => unwrap(await rq.POST('/v1/rq-flows/{flow_id}/deep-questions:close', P(id))),
  finish: async (id: string) => unwrap(await rq.POST('/v1/rq-flows/{flow_id}:finish', P(id))),
  /** 저장 전 초안 지우기(204) — 저장한 것은 409 SAVED_CONTENT */
  remove: async (id: string) => { unwrap(await rq.DELETE('/v1/rq-flows/{flow_id}', P(id))); },
};

/** 목록 줄 × — 초안을 지우고 목록 · 사이드바 작업 이력(workspace 색인)을 새로 읽게 한다 */
export function useRfDelete() {
  const qc = useQueryClient();
  return async (id: string) => {
    await rfApi.remove(id);
    qc.removeQueries({ queryKey: rfKey(id) });
    for (const queryKey of [rfListKey, ['ws', 'items'], ['ws', 'recent'], ['ws', 'counts']]) void qc.invalidateQueries({ queryKey });
  };
}
