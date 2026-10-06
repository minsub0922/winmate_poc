/**
 * proposal API 함수 · 조회 훅(§6) — `api.proposal`(계약 contracts/proposal.json 의 타입). 화면은 이 파일만 쓴다.
 */
import { useQuery, useQueryClient, type QueryClient } from '@tanstack/react-query';
import { api } from '@/api/client';
import type { components } from '@/api/gen/proposal';
import { call, isApiError } from './http';

type S = components['schemas'];
/** 서버 기본값이 있는 필드는 생략해도 된다(Pydantic 기본값) — 생성 타입은 그 필드를 필수로 표시한다 */
export type Loose<T> = { [K in keyof T]?: T[K] | null };
const pr = api.proposal;
const pp = (id: string) => ({ proposal_id: id });

export const qk = {
  all: ['pr'] as const,
  list: (p: Record<string, unknown>) => ['pr', 'list', p] as const,
  p: (id: string) => ['pr', 'p', id] as const,
  sub: (id: string, ...rest: unknown[]) => ['pr', 'p', id, ...rest] as const,
};
/** 그 제안서에 딸린 조회를 모두 새로 읽는다 */
export const invalidateProposal = (qc: QueryClient, id: string) => qc.invalidateQueries({ queryKey: qk.p(id) });
export function useInvalidate(id: string | undefined) {
  const qc = useQueryClient();
  return (...rest: unknown[]) => (id ? qc.invalidateQueries({ queryKey: rest.length ? qk.sub(id, ...rest) : qk.p(id) }) : Promise.resolve());
}

// ── 제안서 §6.2 ──────────────────────────────────────────
export interface ListParams { tab?: string; q?: string; owner?: string; type?: string; sort?: string; limit?: number; cursor?: string; project_id?: string }
export const listProposals = (p: ListParams) => call(pr.GET('/v1/proposals', { params: { query: { ...p, sort: p.sort as 'due_asc' | 'updated_desc' | undefined, limit: p.limit ?? 20 } } }));
export const useProposalList = (p: ListParams) => useQuery({ queryKey: qk.list(p as Record<string, unknown>), queryFn: () => listProposals(p), refetchInterval: 20_000, retry: 0 });
export const createProposal = (b: Loose<S['ProposalCreate']>) => call(pr.POST('/v1/proposals', { body: b as S['ProposalCreate'] }));
export const getProposal = (id: string) => call(pr.GET('/v1/proposals/{proposal_id}', { params: { path: pp(id) } }));
export const useProposal = (id: string | undefined, poll: number | false = false) =>
  useQuery({ queryKey: qk.p(id ?? ''), queryFn: () => getProposal(id!), enabled: !!id, refetchInterval: poll, retry: 1 });
export const patchProposal = (id: string, b: Loose<S['ProposalPatch']>, rev?: number | null) =>
  call(pr.PATCH('/v1/proposals/{proposal_id}', { params: { path: pp(id) }, body: b as S['ProposalPatch'], headers: rev != null ? { 'If-Match': String(rev) } : undefined }));
export const markSubmitted = (id: string) => call(pr.POST('/v1/proposals/{proposal_id}:mark-submitted', { params: { path: pp(id) }, body: {} }));

// ── 시작 방식 §6.3 ───────────────────────────────────────
export const startRfp = (id: string, fileIds: string[], extra?: string[]) =>
  call(pr.POST('/v1/proposals/{proposal_id}/rfp', { params: { path: pp(id) }, body: { file_ids: fileIds, extra_file_ids: extra } }));
export const getRfp = (id: string) => call(pr.GET('/v1/proposals/{proposal_id}/rfp', { params: { path: pp(id) } }));
export const useRfp = (id: string | undefined, poll: number | false = false) =>
  useQuery({ queryKey: qk.sub(id ?? '', 'rfp'), queryFn: () => getRfp(id!), enabled: !!id, refetchInterval: poll, retry: 0 });
export const putRfpField = (id: string, key: string, value: string) =>
  call(pr.PUT('/v1/proposals/{proposal_id}/rfp/fields/{key}', { params: { path: { ...pp(id), key } }, body: { value } }));
export const confirmRfp = (id: string) => call(pr.POST('/v1/proposals/{proposal_id}/rfp:confirm', { params: { path: pp(id) } }));

export const getRelatedWorks = (id: string, scope: 'customer' | 'all', q?: string) =>
  call(pr.GET('/v1/proposals/{proposal_id}/related-works', { params: { path: pp(id), query: { scope, q: q || undefined } } }));
export const useRelatedWorks = (id: string | undefined, scope: 'customer' | 'all', q: string) =>
  useQuery({ queryKey: qk.sub(id ?? '', 'works', scope, q), queryFn: () => getRelatedWorks(id!, scope, q), enabled: !!id, retry: 0 });
export const putLinks = (id: string, links: Array<Loose<S['LinkToggle']> & { feature: string; ref_id: string; on: boolean }>) =>
  call(pr.PUT('/v1/proposals/{proposal_id}/links', { params: { path: pp(id) }, body: { links } as S['LinksPut'] }));
export const applyLinks = (id: string) => call(pr.POST('/v1/proposals/{proposal_id}/links:apply', { params: { path: pp(id) } }));
export const deleteLink = (id: string, lnk: string) => call(pr.DELETE('/v1/proposals/{proposal_id}/links/{link_id}', { params: { path: { ...pp(id), link_id: lnk } } }));
export const restoreLink = (id: string, lnk: string) => call(pr.POST('/v1/proposals/{proposal_id}/links/{link_id}:restore', { params: { path: { ...pp(id), link_id: lnk } } }));
export const refreshLink = (id: string, lnk: string) => call(pr.POST('/v1/proposals/{proposal_id}/links/{link_id}:refresh', { params: { path: { ...pp(id), link_id: lnk } } }));

// ── 유형 · 구성 · 업종 §6.4 ──────────────────────────────
export const useTypeOptions = (id: string | undefined) =>
  useQuery({ queryKey: qk.sub(id ?? '', 'type-options'), queryFn: () => call(pr.GET('/v1/proposals/{proposal_id}/type-options', { params: { path: pp(id!) } })), enabled: !!id, retry: 0 });
export const putType = (id: string, type: S['TypePut']['type']) => call(pr.PUT('/v1/proposals/{proposal_id}/type', { params: { path: pp(id) }, body: { type } }));
export const useComposition = (id: string | undefined, open?: string | null) =>
  useQuery({
    queryKey: qk.sub(id ?? '', 'composition'),
    queryFn: () => call(pr.GET('/v1/proposals/{proposal_id}/composition', { params: { path: pp(id!), query: { open: open || undefined } } })),
    enabled: !!id, retry: 0,
  });
export const putComposition = (id: string, sections: Array<Loose<S['CompSectionPut']> & { key: string }>) =>
  call(pr.PUT('/v1/proposals/{proposal_id}/composition', { params: { path: pp(id) }, body: { sections } as S['CompositionPut'] }));
export const startComposition = (id: string) => call(pr.POST('/v1/proposals/{proposal_id}/composition:start', { params: { path: pp(id) } }));
export const useIndustry = (id: string | undefined, code?: string | null) =>
  useQuery({
    queryKey: qk.sub(id ?? '', 'industry', code ?? null),
    queryFn: () => call(pr.GET('/v1/proposals/{proposal_id}/industry', { params: { path: pp(id!), query: { code: code ?? undefined } } })),
    enabled: !!id, retry: 0,
  });
export const putIndustry = (id: string, b: Loose<S['IndustryPut']>) => call(pr.PUT('/v1/proposals/{proposal_id}/industry', { params: { path: pp(id) }, body: b as S['IndustryPut'] }));

// ── 섹션 · 시트 · 값 §6.5 ────────────────────────────────
const pk = (id: string, key: string) => ({ ...pp(id), key });
const ps = (id: string, sheetId: string) => ({ ...pp(id), sheet_id: sheetId });
export const getSection = (id: string, key: string) => call(pr.GET('/v1/proposals/{proposal_id}/sections/{key}', { params: { path: pk(id, key) } }));
export const useSection = (id: string | undefined, key: string | undefined, poll: number | false = false) =>
  useQuery({ queryKey: qk.sub(id ?? '', 'section', key), queryFn: () => getSection(id!, key!), enabled: !!id && !!key, refetchInterval: poll, retry: 1 });
export const fillSection = (id: string, key: string, reason: 'enter' | 'sources_changed' | 'regen', quick_action?: string) =>
  call(pr.POST('/v1/proposals/{proposal_id}/sections/{key}:fill', { params: { path: pk(id, key) }, body: { reason, quick_action: quick_action ?? null } }));
export const sectionRequest = (id: string, key: string, text: string) =>
  call(pr.POST('/v1/proposals/{proposal_id}/sections/{key}/requests', { params: { path: pk(id, key) }, body: { text } }));
export const confirmSection = (id: string, key: string) => call(pr.POST('/v1/proposals/{proposal_id}/sections/{key}:confirm', { params: { path: pk(id, key) } }));
export const sectionAutoTemplates = (id: string, key: string, includePinned = true) =>
  call(pr.POST('/v1/proposals/{proposal_id}/sections/{key}/templates:auto', { params: { path: pk(id, key) }, body: { include_pinned: includePinned } }));
export const getSheet = (id: string, sheetId: string) => call(pr.GET('/v1/proposals/{proposal_id}/sheets/{sheet_id}', { params: { path: ps(id, sheetId) } }));
export const useSheet = (id: string | undefined, sheetId: string | undefined) =>
  useQuery({ queryKey: qk.sub(id ?? '', 'sheet', sheetId), queryFn: () => getSheet(id!, sheetId!), enabled: !!id && !!sheetId, retry: 0 });
export const patchSheet = (id: string, sheetId: string, ops: S['SheetOp'][], rev?: number | null, reason?: string) =>
  call(pr.PATCH('/v1/proposals/{proposal_id}/sheets/{sheet_id}', { params: { path: ps(id, sheetId) }, body: { ops, reason: reason ?? null }, headers: rev != null ? { 'If-Match': String(rev) } : undefined }));
export const useTemplateOptions = (id: string | undefined, sheetId: string | undefined, productCount?: number | null) =>
  useQuery({
    queryKey: qk.sub(id ?? '', 'tpl-options', sheetId, productCount ?? null),
    queryFn: () => call(pr.GET('/v1/proposals/{proposal_id}/sheets/{sheet_id}/template-options', { params: { path: ps(id!, sheetId!), query: { product_count: productCount ?? undefined } } })),
    enabled: !!id && !!sheetId, retry: 0,
  });
export const putSheetTemplate = (id: string, sheetId: string, b: Loose<S['TemplatePut']> & { mode: 'auto' | 'pinned' }) =>
  call(pr.PUT('/v1/proposals/{proposal_id}/sheets/{sheet_id}/template', { params: { path: ps(id, sheetId) }, body: b as S['TemplatePut'] }));
export const rewriteSheet = (id: string, sheetId: string, b: { target_path?: string | null; instruction?: string | null; options?: Loose<S['RewriteOptions']> }) =>
  call(pr.POST('/v1/proposals/{proposal_id}/sheets/{sheet_id}:rewrite', { params: { path: ps(id, sheetId) }, body: b as S['SheetRewrite'] }));
export const useSheetMessages = (id: string | undefined, sheetId: string | undefined) =>
  useQuery({
    queryKey: qk.sub(id ?? '', 'sheet-msgs', sheetId),
    queryFn: () => call(pr.GET('/v1/proposals/{proposal_id}/sheets/{sheet_id}/messages', { params: { path: ps(id!, sheetId!) } })),
    enabled: !!id && !!sheetId, retry: 0,
  });
export const useFacts = (id: string | undefined) =>
  useQuery({ queryKey: qk.sub(id ?? '', 'facts'), queryFn: () => call(pr.GET('/v1/proposals/{proposal_id}/facts', { params: { path: pp(id!) } })), enabled: !!id, retry: 0 });
export const putFact = (id: string, factId: string, b: Loose<S['FactPut']>) =>
  call(pr.PUT('/v1/proposals/{proposal_id}/facts/{fact_id}', { params: { path: { ...pp(id), fact_id: factId } }, body: b as S['FactPut'] }));
export const proposalRequest = (id: string, text: string) => call(pr.POST('/v1/proposals/{proposal_id}/requests', { params: { path: pp(id) }, body: { text } }));
export const generateNotes = (id: string) => call(pr.POST('/v1/proposals/{proposal_id}/notes:generate', { params: { path: pp(id) }, body: { only_empty: true } }));

// ── 반입 §6.6 ────────────────────────────────────────────
export const postImport = (id: string, b: Loose<Omit<S['ImportRequest'], 'source'>> & { source: Loose<S['ImportSource']> }) =>
  call(pr.POST('/v1/proposals/{proposal_id}/imports', { params: { path: pp(id) }, body: b as S['ImportRequest'] })) as Promise<S['ImportResult'] & Partial<S['JobAccepted']>>;
export const useImport = (id: string | undefined, impId: string | undefined, poll: number | false = false) =>
  useQuery({
    queryKey: qk.sub(id ?? '', 'import', impId),
    queryFn: () => call(pr.GET('/v1/proposals/{proposal_id}/imports/{import_id}', { params: { path: { ...pp(id!), import_id: impId! } } })),
    enabled: !!id && !!impId, refetchInterval: poll, retry: 1,
  });
export const applyImport = (id: string, impId: string, keys: string[]) =>
  call(pr.POST('/v1/proposals/{proposal_id}/imports/{import_id}:apply', { params: { path: { ...pp(id), import_id: impId } }, body: { keys } }));
export const undoImport = (id: string, impId: string) =>
  call(pr.POST('/v1/proposals/{proposal_id}/imports/{import_id}:undo', { params: { path: { ...pp(id), import_id: impId } } }));

// ── 딸깍 §6.7 ────────────────────────────────────────────
export const getOneClickPlan = (id: string, from?: string, section?: string | null) =>
  call(pr.GET('/v1/proposals/{proposal_id}/one-click/plan', { params: { path: pp(id), query: { from, section: section ?? undefined } } }));
export const useOneClickPlan = (id: string | undefined, from?: string, section?: string | null, enabled = true) =>
  useQuery({ queryKey: qk.sub(id ?? '', 'oc-plan', from, section ?? null), queryFn: () => getOneClickPlan(id!, from, section), enabled: !!id && enabled, retry: 0, staleTime: 5_000 });
export const startOneClick = (id: string, b: { options: Loose<S['OneClickOptions']>; from_stage?: string | null; from_section_key?: string | null }) =>
  call(pr.POST('/v1/proposals/{proposal_id}/one-click', { params: { path: pp(id) }, body: b as S['OneClickStart'] }));
export const useOneClick = (id: string | undefined, jobId: string | undefined, poll: number | false = false) =>
  useQuery({
    queryKey: qk.sub(id ?? '', 'oc', jobId),
    queryFn: () => call(pr.GET('/v1/proposals/{proposal_id}/one-click/{job_id}', { params: { path: { ...pp(id!), job_id: jobId! } } })),
    enabled: !!id && !!jobId, refetchInterval: poll, retry: 1,
  });

// ── 디자인 · 생성 · 미리보기 §6.8 ────────────────────────
export const useDesign = (id: string | undefined) =>
  useQuery({ queryKey: qk.sub(id ?? '', 'design'), queryFn: () => call(pr.GET('/v1/proposals/{proposal_id}/design', { params: { path: pp(id!) } })), enabled: !!id, retry: 0 });
export const putDesign = (id: string, b: Loose<S['DesignPatch']>) => call(pr.PUT('/v1/proposals/{proposal_id}/design', { params: { path: pp(id) }, body: b as S['DesignPatch'] }));
export const postLogo = (id: string, fileId: string) => call(pr.POST('/v1/proposals/{proposal_id}/design/logo', { params: { path: pp(id) }, body: { file_id: fileId } }));
export const generate = (id: string, b: Loose<S['GenerateIn']> = { scope: 'all' }) => call(pr.POST('/v1/proposals/{proposal_id}:generate', { params: { path: pp(id) }, body: b as S['GenerateIn'] }));
export const useResult = (id: string | undefined, poll: number | false = false) =>
  useQuery({ queryKey: qk.sub(id ?? '', 'result'), queryFn: () => call(pr.GET('/v1/proposals/{proposal_id}/result', { params: { path: pp(id!) } })), enabled: !!id, refetchInterval: poll, retry: 0 });
export const useSlides = (id: string | undefined, filter?: string | null) =>
  useQuery({
    queryKey: qk.sub(id ?? '', 'slides', filter ?? null),
    queryFn: () => call(pr.GET('/v1/proposals/{proposal_id}/slides', { params: { path: pp(id!), query: { filter: filter ?? undefined } } })),
    enabled: !!id, retry: 0,
  });
export const requestRenders = (id: string, sheetIds?: string[]) => call(pr.POST('/v1/proposals/{proposal_id}/renders', { params: { path: pp(id) }, body: { sheet_ids: sheetIds ?? null } }));

// ── 확정 필요 §6.9 ───────────────────────────────────────
const pi = (id: string, item: string) => ({ ...pp(id), item_id: item });
export const useConfirmItems = (id: string | undefined, status: 'open' | 'confirmed' | 'all' = 'all', sheetId?: string | null) =>
  useQuery({
    queryKey: qk.sub(id ?? '', 'confirm', status, sheetId ?? null),
    queryFn: () => call(pr.GET('/v1/proposals/{proposal_id}/confirm-items', { params: { path: pp(id!), query: { status, sheet_id: sheetId ?? undefined } } })),
    enabled: !!id, retry: 0,
  });
export const createConfirmItem = (id: string, b: Loose<S['ConfirmCreate']> & { sheet_id: string; text: string }) => call(pr.POST('/v1/proposals/{proposal_id}/confirm-items', { params: { path: pp(id) }, body: b as S['ConfirmCreate'] }));
export const resolveConfirm = (id: string, item: string, b: Loose<S['ConfirmResolve']>) =>
  call(pr.POST('/v1/proposals/{proposal_id}/confirm-items/{item_id}:resolve', { params: { path: pi(id, item) }, body: b as S['ConfirmResolve'] }));
export const moveConfirmToNote = (id: string, item: string) => call(pr.POST('/v1/proposals/{proposal_id}/confirm-items/{item_id}:move-to-note', { params: { path: pi(id, item) } }));
export const anonymizeConfirm = (id: string, item: string) => call(pr.POST('/v1/proposals/{proposal_id}/confirm-items/{item_id}:anonymize', { params: { path: pi(id, item) } }));
export const questionConfirm = (id: string, item: string) =>
  call(pr.POST('/v1/proposals/{proposal_id}/confirm-items/{item_id}:question', { params: { path: pi(id, item) }, body: { push_to_rq: true } }));
export const evidenceConfirm = (id: string, item: string, evidence: S['FactEvidence']) =>
  call(pr.POST('/v1/proposals/{proposal_id}/confirm-items/{item_id}:evidence', { params: { path: pi(id, item) }, body: { evidence } }));
export const moveAllToNote = (id: string, ids?: string[]) => call(pr.POST('/v1/proposals/{proposal_id}/confirm-items:move-to-note', { params: { path: pp(id) }, body: { ids: ids ?? null } }));
export const researchConfirm = (id: string, instruction?: string, ids?: string[]) =>
  call(pr.POST('/v1/proposals/{proposal_id}/confirm-items:research', { params: { path: pp(id) }, body: { ids: ids ?? null, instruction: instruction ?? null } }));

// ── 검토 §6.10 ───────────────────────────────────────────
export const useReview = (id: string | undefined) =>
  useQuery({ queryKey: qk.sub(id ?? '', 'review'), queryFn: () => call(pr.GET('/v1/proposals/{proposal_id}/review', { params: { path: pp(id!) } })), enabled: !!id, retry: 0, refetchInterval: 20_000 });
export const requestReview = (id: string, b: Loose<S['ReviewRequestIn']> & { reviewer_ids: string[] }) => call(pr.POST('/v1/proposals/{proposal_id}/review-requests', { params: { path: pp(id) }, body: b as S['ReviewRequestIn'] }));
export const resubmitReview = (id: string, reviewId: string, message?: string) =>
  call(pr.POST('/v1/proposals/{proposal_id}/review-requests/{review_id}:resubmit', { params: { path: { ...pp(id), review_id: reviewId } }, body: { message: message ?? null } }));
export const decideReview = (id: string, decision: 'approve' | 'request_changes', comment?: string) =>
  call(pr.POST('/v1/proposals/{proposal_id}/review/decision', { params: { path: pp(id) }, body: { decision, comment: comment ?? null } }));
export const putCheck = (id: string, sheetId: string, state: 'ok' | 'todo') =>
  call(pr.PUT('/v1/proposals/{proposal_id}/review/checks/{sheet_id}', { params: { path: ps(id, sheetId) }, body: { state } }));
export const applyComments = (id: string, commentIds?: string[]) =>
  call(pr.POST('/v1/proposals/{proposal_id}/review:apply-comments', { params: { path: pp(id) }, body: { comment_ids: commentIds ?? null } }));
const pc = (id: string, c: string) => ({ ...pp(id), comment_id: c });
export const suggestComment = (id: string, commentId: string) => call(pr.POST('/v1/proposals/{proposal_id}/comments/{comment_id}:suggest', { params: { path: pc(id, commentId) } }));
export const getSuggestion = (id: string, commentId: string) => call(pr.GET('/v1/proposals/{proposal_id}/comments/{comment_id}/suggestion', { params: { path: pc(id, commentId) } }));
export const applySuggestion = (id: string, commentId: string) =>
  call(pr.POST('/v1/proposals/{proposal_id}/comments/{comment_id}:apply-suggestion', { params: { path: pc(id, commentId) } }));
export const shareLink = (id: string, permission: 'team_comment' | 'team_view' = 'team_comment') =>
  call(pr.POST('/v1/proposals/{proposal_id}/share-link', { params: { path: pp(id) }, body: { permission } }));

// ── 버전 §6.11 ───────────────────────────────────────────
export const useVersions = (id: string | undefined, all: boolean) =>
  useQuery({
    queryKey: qk.sub(id ?? '', 'versions', all),
    queryFn: () => call(pr.GET('/v1/proposals/{proposal_id}/versions', { params: { path: pp(id!), query: { include: all ? 'changes,events' : 'events' } } })),
    enabled: !!id, retry: 0,
  });
export const saveVersion = (id: string, desc?: string) => call(pr.POST('/v1/proposals/{proposal_id}/versions', { params: { path: pp(id) }, body: { desc: desc ?? null } }));
export const useCompare = (id: string | undefined, a: number | null, b: number | null, sheet?: string | null, mode: 'side' | 'changes' = 'side') =>
  useQuery({
    queryKey: qk.sub(id ?? '', 'compare', a, b, sheet ?? null, mode),
    queryFn: () => call(pr.GET('/v1/proposals/{proposal_id}/versions/compare', { params: { path: pp(id!), query: { a: a ?? undefined, b: b ?? undefined, sheet: sheet ?? undefined, mode } } })),
    enabled: !!id && a !== null && b !== null && a !== b, retry: 0,
  });
export const restoreVersion = (id: string, n: number, scope: 'all' | 'sheet', sheetId?: string) =>
  call(pr.POST('/v1/proposals/{proposal_id}/versions/{n}/restore', { params: { path: { ...pp(id), n } }, body: { scope, sheet_id: sheetId ?? null } }));
export const revertChange = (id: string, chg: string) => call(pr.POST('/v1/proposals/{proposal_id}/changes/{change_id}:revert', { params: { path: { ...pp(id), change_id: chg } } }));

// ── 내보내기 §6.12 ───────────────────────────────────────
export const useExportOptions = (id: string | undefined, version?: number | null, enabled = true) =>
  useQuery({
    queryKey: qk.sub(id ?? '', 'export-options', version ?? null),
    queryFn: () => call(pr.GET('/v1/proposals/{proposal_id}/export-options', { params: { path: pp(id!), query: { version: version ?? undefined } } })),
    enabled: !!id && enabled, retry: 0,
  });
export const postExport = (id: string, b: Loose<S['ExportRequest']>) => call(pr.POST('/v1/proposals/{proposal_id}/exports', { params: { path: pp(id) }, body: b as S['ExportRequest'] }));
export const getExport = (id: string, xpt: string) => call(pr.GET('/v1/proposals/{proposal_id}/exports/{export_id}', { params: { path: { ...pp(id), export_id: xpt } } }));
export const postMaster = (id: string, fileId: string, name?: string) => call(pr.POST('/v1/proposals/{proposal_id}/masters', { params: { path: pp(id) }, body: { file_id: fileId, name: name ?? null } }));

// ── 기존 제안서 활용 §6.13 ───────────────────────────────
export const useReuseCandidates = (id: string | undefined) =>
  useQuery({ queryKey: qk.sub(id ?? '', 'reuse-cand'), queryFn: () => call(pr.GET('/v1/proposals/{proposal_id}/reuse/candidates', { params: { path: pp(id!) } })), enabled: !!id, retry: 0 });
/** `replace: true` = 원본 목록을 이대로 바꿈(빼기 포함), 없으면 더하기 */
export const startReuse = (id: string, b: { sources: Array<Loose<S['ReuseSourceIn']> & { kind: 'proposal' | 'file' }>; mode_pref?: 'improve' | 'borrow' | 'auto'; new_title?: string | null; replace?: boolean }) =>
  call(pr.POST('/v1/proposals/{proposal_id}/reuse', { params: { path: pp(id) }, body: b as S['ReuseStart'] }));
/** 마지막 원본까지 뺐을 때 — 분석을 지운다 */
export const deleteReuse = (id: string) => call(pr.DELETE('/v1/proposals/{proposal_id}/reuse', { params: { path: pp(id) } }));
export const getReuse = (id: string) => call(pr.GET('/v1/proposals/{proposal_id}/reuse', { params: { path: pp(id) } }));
export const useReuse = (id: string | undefined, poll: number | false = false) =>
  useQuery({ queryKey: qk.sub(id ?? '', 'reuse'), queryFn: () => getReuse(id!), enabled: !!id, refetchInterval: poll, retry: 0 });
export const useReuseCriterion = (id: string | undefined, no: number) =>
  useQuery({ queryKey: qk.sub(id ?? '', 'reuse-crit', no), queryFn: () => call(pr.GET('/v1/proposals/{proposal_id}/reuse/criteria/{no}', { params: { path: { ...pp(id!), no } } })), enabled: !!id, retry: 0 });
export const putCriterion = (id: string, no: number, b: Loose<S['CriterionPut']>) => call(pr.PUT('/v1/proposals/{proposal_id}/reuse/criteria/{no}', { params: { path: { ...pp(id), no } }, body: b as S['CriterionPut'] }));
export const putPageRole = (id: string, no: number, role: string) => call(pr.PUT('/v1/proposals/{proposal_id}/reuse/pages/{no}/role', { params: { path: { ...pp(id), no } }, body: { role } }));
export const reanalyze = (id: string) => call(pr.POST('/v1/proposals/{proposal_id}/reuse:reanalyze', { params: { path: pp(id) } }));
export const confirmAnalysis = (id: string) => call(pr.POST('/v1/proposals/{proposal_id}/reuse:confirm-analysis', { params: { path: pp(id) } }));
/** PRU3 방식 전환(계획을 그 방식으로 다시 계산) */
export const putReuseMode = (id: string, mode: 'improve' | 'borrow') => call(pr.PUT('/v1/proposals/{proposal_id}/reuse/mode', { params: { path: pp(id) }, body: { mode } }));
/** PR1C 라디오 — 선호만 저장(분석은 그대로) */
export const putReuseModePref = (id: string, modePref: 'improve' | 'borrow' | 'auto') =>
  call(pr.PUT('/v1/proposals/{proposal_id}/reuse/mode', { params: { path: pp(id) }, body: { mode_pref: modePref } }));
export const putPlanRow = (id: string, rowId: string, verdict: S['VerdictPut']['verdict']) =>
  call(pr.PUT('/v1/proposals/{proposal_id}/reuse/plan/rows/{row_id}', { params: { path: { ...pp(id), row_id: rowId } }, body: { verdict } }));
export const confirmPlan = (id: string, then: 'sections' | 'compose') => call(pr.POST('/v1/proposals/{proposal_id}/reuse/plan:confirm', { params: { path: pp(id) }, body: { then } }));
export const useReuseView = (id: string | undefined, key: string | undefined, sheetId: string | null, view: 'compare' | 'guide' | 'new_only' | null) =>
  useQuery({
    queryKey: qk.sub(id ?? '', 'reuse-view', key, sheetId, view),
    queryFn: () => call(pr.GET('/v1/proposals/{proposal_id}/sections/{key}/reuse-view', { params: { path: pk(id!, key!), query: { sheet_id: sheetId ?? undefined, view: view ?? undefined } } })),
    // 활용 계획 확정 직후 적용이 끝나기 전 잠깐 404(REUSE_NOT_FOUND) — 몇 번 다시 읽는다
    enabled: !!id && !!key && !!view, retry: (n, e) => n < 6 && isApiError(e, 'REUSE_NOT_FOUND'), retryDelay: 1500,
  });
export const pullLines = (id: string, sheetId: string, b: Loose<S['PullLines']>) => call(pr.POST('/v1/proposals/{proposal_id}/sheets/{sheet_id}/reuse:pull-lines', { params: { path: ps(id, sheetId) }, body: b as S['PullLines'] }));
export const useReuseSummary = (id: string | undefined) =>
  useQuery({ queryKey: qk.sub(id ?? '', 'reuse-summary'), queryFn: () => call(pr.GET('/v1/proposals/{proposal_id}/reuse/summary', { params: { path: pp(id!) } })), enabled: !!id, retry: 0 });
