/**
 * mi API(게이트웨이 `/api/mi/v1`) — 타입은 contracts/mi.json 에서 생성(@/api/gen/mi).
 * 화면은 이 파일의 함수 · 훅만 쓴다(경로 문자열을 화면에 흩뜨리지 않는다).
 */
import { useQuery } from '@tanstack/react-query';
import { api, unwrap, ApiError } from '@/api/client';
import type { components } from '@/api/gen/mi';
import type { components as SbComponents } from '@/api/gen/storyboard';

type S = components['schemas'];
export type Analysis = S['Analysis'];
export type AnalysisList = S['AnalysisList'];
export type AnalysisListItem = S['AnalysisListItem'];
export type MenuItem = S['MenuItem'];
export type Requirement = S['Requirement'];
export type Competitor = S['Competitor'];
export type Criterion = S['Criterion'];
export type CriteriaList = S['CriteriaList'];
export type CriterionIn = S['CriterionIn'];
export type DesignView = S['DesignView'];
export type Decision = S['Decision'];
export type SheetPreview = S['SheetPreview'];
export type SegmentItem = S['SegmentItem'];
export type SegmentList = S['SegmentList'];
export type SegmentInsights = S['SegmentInsights'];
export type DetectOut = S['DetectOut'];
export type RoutingRules = S['RoutingRules'];
export type RunProgress = S['RunProgress'];
export type ResultView = S['ResultView'];
export type ClaimRef = S['ClaimRef'];
export type TabInfo = S['TabInfo'];
export type CompareTable = S['CompareTable'];
export type TableCell = S['TableCell'];
export type Strength = S['Strength'];
export type ClaimItem = S['ClaimItem'];
export type ClaimList = S['ClaimList'];
export type ClaimDetail = S['ClaimDetail'];
export type SourceCard = S['SourceCard'];
export type SourceOut = S['SourceOut'];
export type SourceList = S['SourceList'];
export type FixItem = S['FixItem'];
export type FixList = S['FixList'];
export type FixSuggestion = S['FixSuggestion'];
export type RevisionView = S['RevisionView'];
export type Change = S['Change'];
export type RevisionScope = S['RevisionScope'];
export type SlidePlan = S['SlidePlan'];
export type SlidesView = S['SlidesView'];
export type CandidatesView = S['CandidatesView'];
export type LayoutOption = S['LayoutOption'];
export type TemplateCandidate = S['TemplateCandidate'];
export type ExportView = S['ExportView'];
export type HandoffIn = S['HandoffIn'];
export type HandoffOut = S['HandoffOut'];
export type ChangesView = S['ChangesView'];
export type VersionList = S['VersionList'];
export type OnepagerOut = S['OnepagerOut'];
export type Capabilities = S['Capabilities'];
export type Mode = 'auto' | 'check' | 'ask' | 'pin';
export type Area = 'market' | 'customer' | 'user' | 'competitor';

/** 기본값이 있는 필드는 생략해도 된다(서버 Pydantic 기본값) — 생성 타입은 그 필드를 필수로 표시한다 */
type Loose<T> = { [K in keyof T]?: T[K] | null };

const mi = api.mi;
const A = (aid: string) => ({ params: { path: { aid } } });

export const AREAS: Area[] = ['market', 'customer', 'user', 'competitor'];
export const AREA_TAB: Record<Area, string> = { market: '시장조사', customer: '고객사 · 비즈니스', user: '사용자', competitor: '경쟁사 → 삼성 강점' };

export const qk = {
  list: (p: Record<string, unknown>) => ['mi', 'list', p] as const,
  analysis: (id: string) => ['mi', 'analysis', id] as const,
  design: (id: string) => ['mi', 'design', id] as const,
  competitors: (id: string) => ['mi', 'competitors', id] as const,
  criteria: (id: string) => ['mi', 'criteria', id] as const,
  progress: (id: string) => ['mi', 'progress', id] as const,
  result: (id: string, p: Record<string, unknown>) => ['mi', 'result', id, p] as const,
  claims: (id: string, p: Record<string, unknown>) => ['mi', 'claims', id, p] as const,
  claim: (id: string, clm: string, v?: number | null) => ['mi', 'claim', id, clm, v ?? null] as const,
  sources: (id: string, p: Record<string, unknown>) => ['mi', 'sources', id, p] as const,
  fix: (id: string) => ['mi', 'fix', id] as const,
  revision: (id: string, rev: string) => ['mi', 'revision', id, rev] as const,
  slides: (id: string) => ['mi', 'slides', id] as const,
  candidates: (id: string, sht: string, p: Record<string, unknown>) => ['mi', 'candidates', id, sht, p] as const,
  exportView: (id: string, t?: string | null) => ['mi', 'export-view', id, t ?? null] as const,
  segments: ['mi', 'segments'] as const,
  insights: (code: string) => ['mi', 'insights', code] as const,
  rules: ['mi', 'rules'] as const,
  caps: ['mi', 'caps'] as const,
  versions: (id: string) => ['mi', 'versions', id] as const,
  changes: (id: string) => ['mi', 'changes', id] as const,
  onepager: (id: string) => ['mi', 'onepager', id] as const,
};

// ── 오류 ─────────────────────────────────────────────────

export const RETRY_TEXT = '잠시 후 다시 시도해 주세요';

/** 오류 → 화면 문구. 422 · 409 는 서버 한국어 메시지 그대로(§4.0), 그 밖은 `잠시 후 다시 시도해 주세요` */
export function errText(e: unknown, fallback = RETRY_TEXT): string {
  if (e instanceof ApiError) {
    if (e.status === 422 || e.status === 409 || e.status === 403 || e.status === 404) return e.message || fallback;
    if (e.code === 'LLM_UNAVAILABLE' || e.code === 'POLICY_CONFIDENTIAL' || e.status === 503 || e.status === 504) return e.message || fallback;
    return fallback;
  }
  return fallback;
}
export const isApiError = (e: unknown, code?: string): e is ApiError => e instanceof ApiError && (!code || e.code === code);
export { ApiError };

// ── 목록 · 작업 ─────────────────────────────────────────

export interface ListParams { status?: string; segment?: string; q?: string; sort?: string }

export const useAnalysisList = (p: ListParams, poll: number | false = false) =>
  useQuery({
    queryKey: qk.list(p as Record<string, unknown>),
    queryFn: async () => unwrap(await mi.GET('/v1/analyses', { params: { query: {
      limit: 20, status: p.status && p.status !== 'all' ? p.status : undefined, segment: p.segment || undefined, q: p.q || undefined, sort: p.sort || undefined,
    } } })),
    refetchInterval: poll,
  });

export async function listMore(p: ListParams, cursor: string) {
  return unwrap(await mi.GET('/v1/analyses', { params: { query: {
    limit: 20, cursor, status: p.status && p.status !== 'all' ? p.status : undefined, segment: p.segment || undefined, q: p.q || undefined, sort: p.sort || undefined,
  } } }));
}

export const useAnalysis = (id: string | undefined, opts: { poll?: number | false; version?: number | null } = {}) =>
  useQuery({
    queryKey: [...qk.analysis(id ?? ''), opts.version ?? null],
    queryFn: async () => unwrap(await mi.GET('/v1/analyses/{aid}', { params: { path: { aid: id! }, query: { version: opts.version ?? undefined } } })),
    enabled: !!id,
    refetchInterval: opts.poll ?? false,
  });

export async function createAnalysis(body: Loose<S['CreateAnalysisIn']>) {
  return unwrap(await mi.POST('/v1/analyses', { body: body as S['CreateAnalysisIn'] })) as Analysis;
}
export async function getAnalysis(id: string) {
  return unwrap(await mi.GET('/v1/analyses/{aid}', A(id)));
}
export async function patchAnalysis(id: string, body: Loose<S['AnalysisPatch']>) {
  return unwrap(await mi.PATCH('/v1/analyses/{aid}', { ...A(id), body: body as S['AnalysisPatch'] }));
}
export async function deleteAnalysis(id: string) {
  const r = await mi.DELETE('/v1/analyses/{aid}', A(id));
  if (!r.response.ok) unwrap(r as never);
}
export async function duplicateAnalysis(id: string) {
  return unwrap(await mi.POST('/v1/analyses/{aid}/duplicate', { ...A(id), body: { keep_scope: true } }));
}
export async function importStoryboard(id: string, body: Loose<S['StoryboardImportIn']> & { storyboard_id: string }) {
  return unwrap(await mi.POST('/v1/analyses/{aid}/imports/storyboard', { ...A(id), body: body as S['StoryboardImportIn'] }));
}
export async function addRefs(id: string, kind: 'product' | 'solution' | 'case' | 'image', ids: string[]) {
  return unwrap(await mi.POST('/v1/analyses/{aid}/additions', { ...A(id), body: { kind, ids } }));
}
export const useVersions = (id: string | undefined) =>
  useQuery({ queryKey: qk.versions(id ?? ''), queryFn: async () => unwrap(await mi.GET('/v1/analyses/{aid}/versions', A(id!))), enabled: !!id });
export async function restoreVersion(id: string, n: number) {
  return unwrap(await mi.POST('/v1/analyses/{aid}/versions/{n}/restore', { params: { path: { aid: id, n } } }));
}

// ── 업종 · 규칙 ─────────────────────────────────────────

export const useSegments = () =>
  useQuery({ queryKey: qk.segments, queryFn: async () => unwrap(await mi.GET('/v1/segments')), staleTime: 10 * 60_000 });
export const useInsights = (code: string | null | undefined) =>
  useQuery({ queryKey: qk.insights(code ?? ''), queryFn: async () => unwrap(await mi.GET('/v1/segments/{code}/insights', { params: { path: { code: code! } } })),
    enabled: !!code, staleTime: 10 * 60_000 });
export async function detectSegment(text: string, analysisId?: string | null) {
  return unwrap(await mi.POST('/v1/segments/detect', { body: { text, analysis_id: analysisId ?? null } }));
}
export const useRules = () =>
  useQuery({ queryKey: qk.rules, queryFn: async () => unwrap(await mi.GET('/v1/routing-rules')), staleTime: 10 * 60_000 });
export const useCapabilities = () =>
  useQuery({ queryKey: qk.caps, queryFn: async () => unwrap(await mi.GET('/v1/capabilities')), staleTime: 60_000, retry: 0 });

// ── 설계 ─────────────────────────────────────────────────

export async function startDesign(id: string) {
  return unwrap(await mi.POST('/v1/analyses/{aid}/design', A(id)));
}
export const useDesign = (id: string | undefined, poll: number | false = false) =>
  useQuery({ queryKey: qk.design(id ?? ''), queryFn: async () => unwrap(await mi.GET('/v1/analyses/{aid}/design', A(id!))), enabled: !!id, refetchInterval: poll });
export async function designMemo(id: string, text: string) {
  return unwrap(await mi.POST('/v1/analyses/{aid}/design/memo', { ...A(id), body: { text } }));
}

// ── 경쟁사 · 기준 ───────────────────────────────────────

export const useCompetitors = (id: string | undefined, poll: number | false = false) =>
  useQuery({ queryKey: qk.competitors(id ?? ''), queryFn: async () => unwrap(await mi.GET('/v1/analyses/{aid}/competitors', A(id!))), enabled: !!id, refetchInterval: poll });
export async function addCompetitor(id: string, name: string) {
  return unwrap(await mi.POST('/v1/analyses/{aid}/competitors', { ...A(id), body: { name } }));
}
export async function patchCompetitor(id: string, cmp: string, body: Loose<S['CompetitorPatch']>) {
  return unwrap(await mi.PATCH('/v1/analyses/{aid}/competitors/{cmp}', { params: { path: { aid: id, cmp } }, body: body as S['CompetitorPatch'] }));
}
export const useCriteria = (id: string | undefined) =>
  useQuery({ queryKey: qk.criteria(id ?? ''), queryFn: async () => unwrap(await mi.GET('/v1/analyses/{aid}/criteria', A(id!))), enabled: !!id });
export async function putCriteria(id: string, items: Array<Loose<CriterionIn> & { name: string }>) {
  return unwrap(await mi.PUT('/v1/analyses/{aid}/criteria', { ...A(id), body: { items: items as CriterionIn[] } }));
}

// ── 실행 · 진행 ─────────────────────────────────────────

export async function startRun(id: string, body: { mode?: 'auto' | 'full' | 'changed_only' | 'resume'; areas?: Area[] | null } = { mode: 'full' }) {
  return unwrap(await mi.POST('/v1/analyses/{aid}/runs', { ...A(id), body: body as S['RunIn'] }));
}
export const useProgress = (id: string | undefined, poll: number | false = false) =>
  useQuery({ queryKey: qk.progress(id ?? ''), queryFn: async () => unwrap(await mi.GET('/v1/analyses/{aid}/progress', A(id!))), enabled: !!id, refetchInterval: poll });

// ── 결과 · 출처 · 질문 ──────────────────────────────────

export const useResult = (id: string | undefined, p: { version?: number | null; preview?: boolean } = {}) =>
  useQuery({
    queryKey: qk.result(id ?? '', p as Record<string, unknown>),
    queryFn: async () => unwrap(await mi.GET('/v1/analyses/{aid}/result', { params: { path: { aid: id! }, query: { version: p.version ?? undefined, preview: p.preview || undefined } } })),
    enabled: !!id,
    retry: (n, e) => !(e instanceof ApiError && e.status === 404) && n < 2,
  });
export const useClaims = (id: string | undefined, p: { tab?: Area | null; version?: number | null }) =>
  useQuery({
    queryKey: qk.claims(id ?? '', p as Record<string, unknown>),
    queryFn: async () => unwrap(await mi.GET('/v1/analyses/{aid}/claims', { params: { path: { aid: id! }, query: { tab: p.tab ?? undefined, version: p.version ?? undefined } } })),
    enabled: !!id,
  });
export const useClaim = (id: string | undefined, clm: string | null | undefined, version?: number | null) =>
  useQuery({
    queryKey: qk.claim(id ?? '', clm ?? '', version),
    queryFn: async () => unwrap(await mi.GET('/v1/analyses/{aid}/claims/{clm}', { params: { path: { aid: id!, clm: clm! }, query: { version: version ?? undefined } } })),
    enabled: !!id && !!clm,
  });
export const useSources = (id: string | undefined, p: { tab?: Area | null; kind?: string | null; state?: string | null; version?: number | null }, enabled = true) =>
  useQuery({
    queryKey: qk.sources(id ?? '', p as Record<string, unknown>),
    queryFn: async () => unwrap(await mi.GET('/v1/analyses/{aid}/sources', { params: { path: { aid: id! }, query: {
      tab: p.tab ?? undefined, kind: p.kind ?? undefined, state: p.state ?? undefined, version: p.version ?? undefined } } })),
    enabled: !!id && enabled,
  });
export async function listSources(id: string, p: { tab?: Area | null; kind?: string | null; version?: number | null }) {
  return unwrap(await mi.GET('/v1/analyses/{aid}/sources', { params: { path: { aid: id }, query: { tab: p.tab ?? undefined, kind: p.kind ?? undefined,
    version: p.version ?? undefined } } }));
}
export async function addSource(id: string, body: Loose<S['SourceAddIn']>) {
  return unwrap(await mi.POST('/v1/analyses/{aid}/sources', { ...A(id), body: body as S['SourceAddIn'] }));
}
export async function getSnapshot(id: string, src: string) {
  return unwrap(await mi.GET('/v1/analyses/{aid}/sources/{src}/snapshot', { params: { path: { aid: id, src } } }));
}
export async function removeCitation(id: string, clm: string, src: string) {
  return unwrap(await mi.DELETE('/v1/analyses/{aid}/claims/{clm}/sources/{src}', { params: { path: { aid: id, clm, src } } }));
}
export async function askQuestion(id: string, body: { text: string; tab?: Area | null; claim_id?: string | null }) {
  return unwrap(await mi.POST('/v1/analyses/{aid}/questions', { ...A(id), body: body as S['QuestionIn'] }));
}
export async function followup(id: string, body: { text: string; tab?: Area | null }) {
  return unwrap(await mi.POST('/v1/analyses/{aid}/followups', { ...A(id), body: body as S['FollowupIn'] }));
}
export async function startOnepager(id: string) {
  return unwrap(await mi.POST('/v1/analyses/{aid}/onepager', A(id)));
}
export async function getOnepager(id: string) {
  return unwrap(await mi.GET('/v1/analyses/{aid}/onepager', A(id)));
}

// ── 확정 필요 ───────────────────────────────────────────

export const useFixItems = (id: string | undefined, poll: number | false = false) =>
  useQuery({ queryKey: qk.fix(id ?? ''), queryFn: async () => unwrap(await mi.GET('/v1/analyses/{aid}/fix-items', A(id!))), enabled: !!id, refetchInterval: poll });
export async function patchFix(id: string, fix: string, body: { value: string; unit?: string | null; note?: string | null }) {
  return unwrap(await mi.PATCH('/v1/analyses/{aid}/fix-items/{fix}', { params: { path: { aid: id, fix } }, body: body as S['FixPatch'] }));
}
export async function revertFix(id: string, fix: string) {
  return unwrap(await mi.POST('/v1/analyses/{aid}/fix-items/{fix}/revert', { params: { path: { aid: id, fix } } }));
}
export async function cancelFix(id: string, fix: string) {
  return unwrap(await mi.POST('/v1/analyses/{aid}/fix-items/{fix}/cancel', { params: { path: { aid: id, fix } } }));
}
export async function scanFix(id: string, body: { file_id: string; classification?: 'internal' | 'confidential' | 'customer' | 'public'; fix_ids?: string[] | null }) {
  return unwrap(await mi.POST('/v1/analyses/{aid}/fix-items/scan', { ...A(id), body: body as S['FixScanIn'] }));
}
export async function parseFix(id: string, text: string) {
  return unwrap(await mi.POST('/v1/analyses/{aid}/fix-items/parse', { ...A(id), body: { text } }));
}
export async function fixQuestion(id: string, fix: string) {
  return unwrap(await mi.POST('/v1/analyses/{aid}/fix-items/{fix}/question', { params: { path: { aid: id, fix } } }));
}
export async function applyFix(id: string, carry: boolean) {
  return unwrap(await mi.POST('/v1/analyses/{aid}/fix-items/apply', { ...A(id), body: { carry_remaining: carry } }));
}

// ── 부분 재분석 ─────────────────────────────────────────

export async function startRevision(id: string, scope: RevisionScope, instruction: string) {
  return unwrap(await mi.POST('/v1/analyses/{aid}/revisions', { ...A(id), body: { scope, instruction } }));
}
export const useRevision = (id: string | undefined, rev: string | null | undefined, poll: number | false = false) =>
  useQuery({ queryKey: qk.revision(id ?? '', rev ?? ''), queryFn: async () => unwrap(await mi.GET('/v1/analyses/{aid}/revisions/{rev}', { params: { path: { aid: id!, rev: rev! } } })),
    enabled: !!id && !!rev, refetchInterval: poll });
export async function addRound(id: string, rev: string, instruction: string, scope?: RevisionScope | null) {
  return unwrap(await mi.POST('/v1/analyses/{aid}/revisions/{rev}/rounds', { params: { path: { aid: id, rev } }, body: { instruction, scope: scope ?? null } }));
}
export async function patchChange(id: string, rev: string, chg: string, reverted: boolean) {
  return unwrap(await mi.PATCH('/v1/analyses/{aid}/revisions/{rev}/changes/{chg}', { params: { path: { aid: id, rev, chg } }, body: { reverted } }));
}
export async function revertAll(id: string, rev: string) {
  return unwrap(await mi.POST('/v1/analyses/{aid}/revisions/{rev}/revert-all', { params: { path: { aid: id, rev } } }));
}
export async function applyRevision(id: string, rev: string) {
  return unwrap(await mi.POST('/v1/analyses/{aid}/revisions/{rev}/apply', { params: { path: { aid: id, rev } } }));
}
export async function discardRevision(id: string, rev: string) {
  const r = await mi.POST('/v1/analyses/{aid}/revisions/{rev}/discard', { params: { path: { aid: id, rev } } });
  if (!r.response.ok) unwrap(r as never);
}

// ── 시트 구성 · 레이아웃 ─────────────────────────────────

export const useSlides = (id: string | undefined) =>
  useQuery({ queryKey: qk.slides(id ?? ''), queryFn: async () => unwrap(await mi.GET('/v1/analyses/{aid}/slides', A(id!))), enabled: !!id });
export async function patchSlide(id: string, sht: string, body: { included?: boolean; template_code?: string; pinned?: boolean }) {
  return unwrap(await mi.PATCH('/v1/analyses/{aid}/slides/{sht}', { params: { path: { aid: id, sht } }, body: body as S['SlidePatch'] }));
}
export const useCandidates = (id: string | undefined, sht: string | undefined, p: { requested?: string | null; text?: string | null }) =>
  useQuery({
    queryKey: qk.candidates(id ?? '', sht ?? '', p as Record<string, unknown>),
    queryFn: async () => unwrap(await mi.GET('/v1/analyses/{aid}/slides/{sht}/candidates', { params: { path: { aid: id!, sht: sht! },
      query: { requested: p.requested ?? undefined, text: p.text ?? undefined } } })),
    enabled: !!id && !!sht,
  });
/** 선택지 A 는 202(잡) · B · C 는 200(시트) */
export async function chooseLayout(id: string, sht: string, body: { option: 'A' | 'B' | 'C'; template: string; axes?: Record<string, string> | null; pin?: boolean | null }) {
  const r = await mi.POST('/v1/analyses/{aid}/slides/{sht}/layout', { params: { path: { aid: id, sht } }, body: body as S['LayoutIn'] });
  const data = unwrap(r) as SlidePlan | S['JobAccepted'];
  return r.response.status === 202 ? { job: data as S['JobAccepted'] } : { sheet: data as SlidePlan };
}
export async function slideRequest(id: string, text: string) {
  return unwrap(await mi.POST('/v1/analyses/{aid}/slides/requests', { ...A(id), body: { text } }));
}

// ── 넘김 · 내보내기 · 공유 ──────────────────────────────

export const useExportView = (id: string | undefined, targetId?: string | null) =>
  useQuery({ queryKey: qk.exportView(id ?? '', targetId), queryFn: async () => unwrap(await mi.GET('/v1/analyses/{aid}/export-view', { params: { path: { aid: id! },
    query: { target_id: targetId ?? undefined } } })), enabled: !!id });
export async function handoff(id: string, body: Loose<HandoffIn> & { target: HandoffIn['target'] }) {
  return unwrap(await mi.POST('/v1/analyses/{aid}/handoffs', { ...A(id), body: body as HandoffIn }));
}
export async function patchHandoff(id: string, hof: string, body: { status: 'delivered' | 'failed'; target_title?: string | null; target_id?: string | null }) {
  return unwrap(await mi.PATCH('/v1/analyses/{aid}/handoffs/{hof}', { params: { path: { aid: id, hof } }, body: body as S['HandoffPatch'] }));
}
export async function startExport(id: string, format: 'pdf_report' | 'pptx_onepager' | 'xlsx_table', audience: 'customer' | 'internal' = 'customer') {
  return unwrap(await mi.POST('/v1/analyses/{aid}/exports', { ...A(id), body: { format, audience } }));
}
export async function shareAnalysis(id: string) {
  return unwrap(await mi.POST('/v1/analyses/{aid}/share', A(id)));
}
export const useSharedView = (id: string | undefined) =>
  useQuery({ queryKey: ['mi', 'shared', id], queryFn: async () => unwrap(await mi.GET('/v1/analyses/{aid}/shared-view', A(id!))), enabled: !!id });
export async function tableText(id: string, audience: 'customer' | 'internal' = 'customer') {
  return unwrap(await mi.GET('/v1/analyses/{aid}/table-text', { params: { path: { aid: id }, query: { audience } } }));
}

// ── 재확인 ───────────────────────────────────────────────

export const useChanges = (id: string | undefined, enabled = true) =>
  useQuery({ queryKey: qk.changes(id ?? ''), queryFn: async () => unwrap(await mi.GET('/v1/analyses/{aid}/changes', A(id!))), enabled: !!id && enabled });

// ── 다른 서비스(웹이 옮겨 주는 것, §8 · Q4) ─────────────

/** Storyboard 묶음 읽기(storyboard 계약) → MI 가져오기 본문 */
export async function readStoryboard(sbId: string): Promise<{ title: string; customer_name: string | null; requirements: string[]; key_messages: string[]; rq_id: string | null }> {
  const r = await fetch(`/api/storyboard/v1/storyboards/${encodeURIComponent(sbId)}`, { credentials: 'same-origin' });
  if (!r.ok) throw new ApiError(r.status, 'STORYBOARD_UNAVAILABLE', 'Storyboard 를 읽지 못했어요');
  const sb = await r.json();
  const reqs: string[] = [];
  for (const it of sb?.trace?.items ?? []) if (typeof it?.text === 'string' && it.text.trim()) reqs.push(it.text.trim());
  const kms: string[] = [];
  for (const k of sb?.direction?.key_messages ?? []) if (typeof k?.text === 'string' && k.text.trim()) kms.push(k.text.trim());
  return {
    title: sb?.title || sb?.name || '',
    customer_name: sb?.customer_name ?? sb?.requirement_ref?.customer_name ?? null,
    requirements: reqs,
    key_messages: kms,
    rq_id: sb?.requirement_ref?.requirement_id ?? null,
  };
}

/** Key Message 근거 스냅숏(익명 처리 끝 · MI4 `Key Message에 근거로 붙이기`) */
export type EvidenceSnapshot = S['EvidenceSnapshot'];
export type EvidenceItem = S['EvidenceItem'];
export const useEvidence = (id: string | undefined, enabled = true) =>
  useQuery({
    queryKey: ['mi', 'evidence', id ?? ''] as const,
    queryFn: async () => unwrap(await mi.GET('/v1/analyses/{aid}/evidence', A(id!))),
    enabled: !!id && enabled,
  });

/** Storyboard Key Message(02-storyboard §8.3 — mi 는 storyboard 를 부르지 않으므로 웹이 읽고 올린다) */
type SbS = SbComponents['schemas'];
export type KeyMessage = SbS['KeyMessage'];
export const useKeyMessages = (sbId: string | null | undefined) =>
  useQuery({
    queryKey: ['mi', 'sb-key-messages', sbId ?? ''] as const,
    queryFn: async () => unwrap(await api.storyboard.GET('/v1/storyboards/{sb_id}/key-messages', { params: { path: { sb_id: sbId! } } })).items,
    enabled: !!sbId,
    retry: false,
  });
export async function addKeyMessageEvidence(sbId: string, kmsg: string, body: SbS['PostEvidence']) {
  return unwrap(await api.storyboard.POST('/v1/storyboards/{sb_id}/key-messages/{kmsg}/evidence', { params: { path: { sb_id: sbId, kmsg } }, body }));
}

/** 제안서 가져오기(10-proposal §6.6) — 실패하면 예외 */
export async function proposalImport(proposalId: string, body: Record<string, unknown>) {
  const r = await fetch(`/api/proposal/v1/proposals/${encodeURIComponent(proposalId)}/imports`, {
    method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
  });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new ApiError(r.status, data?.error?.code ?? 'PROPOSAL_IMPORT_FAILED', data?.error?.message ?? '제안서에 보내지 못했어요');
  return data as { import_id?: string; job_id?: string };
}
