/**
 * requirements API(계약에서 만든 타입) — 화면은 이 함수들만 쓴다.
 */
import { api, ApiError, unwrap } from '@/api/client';
import type { components } from '@/api/gen/requirements';

type S = components['schemas'];
export type Requirement = S['Requirement'];
export type RequirementListItem = S['RequirementListItem'];
export type Form = S['Form'];
export type FormField = S['FormField'];
export type Keyman = S['Keyman'];
export type ReqItem = S['ReqItem'];
export type Source = S['Source'];
export type SourceFile = S['SourceFile'];
export type DeepSession = S['DeepSession'];
export type Gap = S['Gap'];
export type Proposal = S['Proposal'];
export type LogEntry = S['LogEntry'];
export type CustomerQuestion = S['CustomerQuestion'];
export type RequirementVersion = S['RequirementVersion'];
export type VersionSummary = S['VersionSummary'];
export type ReplyAnalysis = S['ReplyAnalysis'];
export type ReplyChange = S['ReplyChange'];
export type UsageLink = S['UsageLink'];
export type AnswerResult = S['AnswerResult'];
export type JobAccepted = S['JobAccepted'];
export type DraftOp = NonNullable<S['PatchDraft']['ops']>[number];
export type FieldName = 'project_name' | 'customer_name' | 'final_audience' | 'author_note';
export type Tab = 'all' | 'in_progress' | 'saved';

const rq = api.requirements;
const P = (rq_id: string) => ({ params: { path: { rq_id } } });

export { ApiError };

export const rqApi = {
  list: async (q: { tab?: Tab; q?: string; limit?: number; cursor?: string | null; has_version?: boolean }) =>
    unwrap(await rq.GET('/v1/requirements', { params: { query: { tab: q.tab ?? 'all', q: q.q || undefined, limit: q.limit ?? 20, cursor: q.cursor || undefined, has_version: q.has_version } } })),
  counts: async (q?: string) => unwrap(await rq.GET('/v1/requirements/counts', { params: { query: { q: q || undefined } } })),
  create: async () => unwrap(await rq.POST('/v1/requirements', { body: {} })),
  get: async (id: string) => unwrap(await rq.GET('/v1/requirements/{rq_id}', P(id))),
  patch: async (id: string, base: number | null, ops: DraftOp[]) =>
    unwrap(await rq.PATCH('/v1/requirements/{rq_id}/draft', { ...P(id), body: { base_revision: base, ops } })),
  save: async (id: string, reason?: 'direct' | 'deep' | 'edit') =>
    unwrap(await rq.POST('/v1/requirements/{rq_id}/save', { ...P(id), body: reason ? { reason } : {} })),
  share: async (id: string) => unwrap(await rq.POST('/v1/requirements/{rq_id}/share', P(id))),
  addFiles: async (id: string, fileIds: string[]) =>
    unwrap(await rq.POST('/v1/requirements/{rq_id}/files', { ...P(id), body: { file_ids: fileIds } })),
  removeFile: async (id: string, fileId: string) =>
    unwrap(await rq.DELETE('/v1/requirements/{rq_id}/files/{file_id}', { params: { path: { rq_id: id, file_id: fileId }, query: { rollback: true } } })),
  restoreFile: async (id: string, fileId: string) =>
    unwrap(await rq.POST('/v1/requirements/{rq_id}/files/{file_id}/restore', { params: { path: { rq_id: id, file_id: fileId } } })),
  versions: async (id: string) => unwrap(await rq.GET('/v1/requirements/{rq_id}/versions', P(id))),
  version: async (id: string, n: number | 'latest') =>
    unwrap(await rq.GET('/v1/requirements/{rq_id}/versions/{n}', { params: { path: { rq_id: id, n: String(n) } } })),
  restoreVersion: async (id: string, n: number) =>
    unwrap(await rq.POST('/v1/requirements/{rq_id}/versions/{n}/restore', { params: { path: { rq_id: id, n } } })),
  links: async (id: string) => unwrap(await rq.GET('/v1/requirements/{rq_id}/links', P(id))),
  // 심층 작성
  startDeep: async (id: string) => unwrap(await rq.POST('/v1/requirements/{rq_id}/deep-sessions', P(id))),
  session: async (id: string, sid: string) =>
    unwrap(await rq.GET('/v1/requirements/{rq_id}/deep-sessions/{sid}', { params: { path: { rq_id: id, sid } } })),
  selectGaps: async (id: string, sid: string, ids: string[]) =>
    unwrap(await rq.PATCH('/v1/requirements/{rq_id}/deep-sessions/{sid}', { params: { path: { rq_id: id, sid } }, body: { selected_gap_ids: ids } })),
  reanalyze: async (id: string, sid: string) =>
    unwrap(await rq.POST('/v1/requirements/{rq_id}/deep-sessions/{sid}/reanalyze', { params: { path: { rq_id: id, sid } } })),
  start: async (id: string, sid: string) =>
    unwrap(await rq.POST('/v1/requirements/{rq_id}/deep-sessions/{sid}/start', { params: { path: { rq_id: id, sid } } })),
  answer: async (id: string, sid: string, body: S['AnswerRequest']) =>
    unwrap(await rq.POST('/v1/requirements/{rq_id}/deep-sessions/{sid}/answers', { params: { path: { rq_id: id, sid } }, body })),
  accept: async (id: string, sid: string, pid: string, body: S['AcceptProposal']) =>
    unwrap(await rq.POST('/v1/requirements/{rq_id}/deep-sessions/{sid}/proposals/{pid}/accept', { params: { path: { rq_id: id, sid, pid } }, body })),
  revise: async (id: string, sid: string, pid: string, instruction: string) =>
    unwrap(await rq.POST('/v1/requirements/{rq_id}/deep-sessions/{sid}/proposals/{pid}/revise', { params: { path: { rq_id: id, sid, pid } }, body: { instruction } })),
  finish: async (id: string, sid: string) =>
    unwrap(await rq.POST('/v1/requirements/{rq_id}/deep-sessions/{sid}/finish', { params: { path: { rq_id: id, sid } } })),
  // 고객 질문
  questions: async (id: string, status: 'open' | 'answered' | 'dismissed' | 'all' = 'open') =>
    unwrap(await rq.GET('/v1/requirements/{rq_id}/customer-questions', { params: { path: { rq_id: id }, query: { status } } })),
  patchQuestion: async (id: string, qid: string, body: S['PatchCustomerQuestion']) =>
    unwrap(await rq.PATCH('/v1/requirements/{rq_id}/customer-questions/{qid}', { params: { path: { rq_id: id, qid } }, body })),
  mailDraft: async (id: string, questionIds: string[]) =>
    unwrap(await rq.POST('/v1/requirements/{rq_id}/customer-questions/mail-draft', { ...P(id), body: { question_ids: questionIds } })),
  // 고객 답변
  createReply: async (id: string, text: string, fileIds: string[]) =>
    unwrap(await rq.POST('/v1/requirements/{rq_id}/replies', { ...P(id), body: { text, file_ids: fileIds } })),
  reply: async (id: string, rid: string) =>
    unwrap(await rq.GET('/v1/requirements/{rq_id}/replies/{rid}', { params: { path: { rq_id: id, rid } } })),
  selectChanges: async (id: string, rid: string, ids: string[]) =>
    unwrap(await rq.PATCH('/v1/requirements/{rq_id}/replies/{rid}', { params: { path: { rq_id: id, rid } }, body: { selected_change_ids: ids } })),
  applyReply: async (id: string, rid: string, ids: string[], propagate: boolean) =>
    unwrap(await rq.POST('/v1/requirements/{rq_id}/replies/{rid}/apply', {
      params: { path: { rq_id: id, rid } }, body: { selected_change_ids: ids, propagate: propagate ? ['storyboard'] : [] },
    })),
};

/** Storyboard 반영 실행(§4.15) — requirements 가 아니라 웹이 부른다. 기다리지 않는다. */
export async function requestStoryboardSync(sbId: string, requirementId: string, toVersion: number) {
  try {
    await fetch(`/api/storyboard/v1/storyboards/${sbId}/requirement-sync`, {
      method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ requirement_id: requirementId, to_version: toVersion, dry_run: false }),
    });
  } catch {
    /* Storyboard 가 열릴 때 링크 sync_state=pending 을 보고 스스로 동기화한다(§8.4) */
  }
}

export const AI_DOWN = '지금은 AI를 쓸 수 없어요. 직접 입력은 계속할 수 있어요.';

/** 오류 → 토스트 문구(§4.0.5) */
export function errorText(e: unknown): string {
  if (e instanceof ApiError) {
    if (e.code === 'LLM_UNAVAILABLE' || e.code === 'POLICY_CONFIDENTIAL') return AI_DOWN;
    return e.message || '문제가 생겼어요. 다시 시도해 주세요.';
  }
  return '연결이 끊겼어요. 다시 시도해 주세요.';
}
