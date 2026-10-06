/**
 * competitor API(게이트웨이 `/api/competitor/v1`) — 타입은 contracts/competitor.json 에서 생성(@/api/gen/competitor).
 * 화면은 이 파일의 함수 · 훅만 쓴다. 다른 서비스(requirements · mi · proposal · storyboard · files · jobs)는 그 계약 타입으로 부른다.
 */
import { useQuery } from '@tanstack/react-query';
import { api, unwrap, ApiError } from '@/api/client';
import type { components } from '@/api/gen/competitor';
import type { components as RqComponents } from '@/api/gen/requirements';

type S = components['schemas'];
type RqS = RqComponents['schemas'];
export type Analysis = S['Analysis'];
export type AnalysisList = S['AnalysisList'];
export type ListItem = S['ListItem'];
export type SlotView = S['SlotView'];
export type SlotsView = S['SlotsView'];
export type ParseOut = S['ParseOut'];
export type ChipView = S['ChipView'];
export type CandidatesOut = S['CandidatesOut'];
export type CompetitorView = S['CompetitorView'];
export type CriteriaOut = S['CriteriaOut'];
export type CriterionView = S['CriterionView'];
export type CriterionIn = S['CriterionIn'];
export type ResultOut = S['ResultOut'];
export type ResultRow = S['ResultRow'];
export type TableView = S['TableView'];
export type CompetitorDetail = S['CompetitorDetail'];
export type FactView = S['FactView'];
export type ClaimList = S['ClaimList'];
export type ClaimItem = S['ClaimItem'];
export type ClaimDetail = S['ClaimDetail'];
export type SourceCard = S['SourceCard'];
export type FindLine = S['FindLine'];
export type RunCompetitor = S['RunCompetitor'];
export type AskRequest = S['AskRequest'];
export type HandoffOut = S['HandoffOut'];
export type Bundle = S['Bundle'];
export type Status = Analysis['status'];
export type SlotKey = SlotView['key'];
export type View = 'overview' | 'table' | 'strengths';
export type RunMode = 'full' | 'changed_only' | 'rejudge' | 'resume';

/** 기본값이 있는 필드는 생략해도 된다(서버 Pydantic 기본값) — 생성 타입은 그 필드를 필수로 표시한다 */
type Loose<T> = { [K in keyof T]?: T[K] | null };

const ca = api.competitor;
const A = (aid: string) => ({ params: { path: { aid } } });

export const SLOT_ORDER: SlotKey[] = ['customer', 'industry', 'place', 'product'];
export const STEPS = ['넣기', '경쟁사 확인', '분석', '결과'];

export const qk = {
  list: (p: Record<string, unknown>) => ['ca', 'list', p] as const,
  analysis: (id: string) => ['ca', 'analysis', id] as const,
  candidates: (id: string) => ['ca', 'candidates', id] as const,
  criteria: (id: string) => ['ca', 'criteria', id] as const,
  result: (id: string, view: View, version?: number | null) => ['ca', 'result', id, view, version ?? null] as const,
  detail: (id: string, cmp: string) => ['ca', 'detail', id, cmp] as const,
  claims: (id: string, p: Record<string, unknown>) => ['ca', 'claims', id, p] as const,
  claim: (id: string, clm: string) => ['ca', 'claim', id, clm] as const,
  handoffs: (id: string) => ['ca', 'handoffs', id] as const,
};

/** 오류 → 화면 문장(서버 한국어 메시지가 있으면 그것) */
export function errText(e: unknown, fallback = '잠시 뒤 다시 시도해 주세요'): string {
  if (e instanceof ApiError) return e.message || fallback;
  if (e instanceof Error && e.message) return e.message;
  return fallback;
}
export const errCode = (e: unknown): string | null => (e instanceof ApiError ? e.code : null);

// ── 작업 ───────────────────────────────────────────────
export async function listAnalyses(p: { status?: string; q?: string; sort?: string; limit?: number }): Promise<AnalysisList> {
  return unwrap(await ca.GET('/v1/analyses', { params: { query: { limit: p.limit ?? 50, status: p.status || null, q: p.q || null, sort: p.sort || null } } }));
}
export async function getAnalysis(aid: string): Promise<Analysis> {
  return unwrap(await ca.GET('/v1/analyses/{aid}', A(aid)));
}
export type CreateBody = Loose<S['AnalysisCreate']>;
export async function createAnalysis(body: CreateBody): Promise<Analysis> {
  return unwrap(await ca.POST('/v1/analyses', { body: body as S['AnalysisCreate'] })) as Analysis;
}
export type PatchBody = Loose<S['AnalysisPatch']>;
export async function patchAnalysis(aid: string, body: PatchBody): Promise<Analysis> {
  return unwrap(await ca.PATCH('/v1/analyses/{aid}', { ...A(aid), body: body as S['AnalysisPatch'] }));
}
export async function deleteAnalysis(aid: string): Promise<void> {
  const r = await ca.DELETE('/v1/analyses/{aid}', A(aid));
  if (!r.response.ok) unwrap(r as never);
}
export async function parse(body: Loose<S['ParseIn']>, signal?: AbortSignal): Promise<ParseOut> {
  return unwrap(await ca.POST('/v1/parse', { body: { file_ids: [], ...body } as S['ParseIn'], signal }));
}
export async function startFind(aid: string): Promise<S['JobAccepted']> {
  return unwrap(await ca.POST('/v1/analyses/{aid}/find', A(aid)));
}
export async function getCandidates(aid: string): Promise<CandidatesOut> {
  return unwrap(await ca.GET('/v1/analyses/{aid}/candidates', A(aid)));
}
export async function setCandidate(aid: string, cmp: string, on: boolean): Promise<CompetitorView> {
  return unwrap(await ca.PATCH('/v1/analyses/{aid}/candidates/{cmp}', { params: { path: { aid, cmp } }, body: { on } }));
}
export async function addCandidate(aid: string, name: string): Promise<S['CandidateAddOut']> {
  return unwrap(await ca.POST('/v1/analyses/{aid}/candidates', { ...A(aid), body: { name } }));
}
export async function getCriteria(aid: string): Promise<CriteriaOut> {
  return unwrap(await ca.GET('/v1/analyses/{aid}/criteria', A(aid)));
}
export async function putCriteria(aid: string, items: Array<Loose<CriterionIn> & { name: string }>): Promise<S['CriteriaPutOut']> {
  return unwrap(await ca.PUT('/v1/analyses/{aid}/criteria', { ...A(aid), body: { items: items as CriterionIn[] } }));
}
export async function startRun(aid: string, mode: RunMode, competitorIds?: string[] | null): Promise<S['JobAccepted']> {
  return unwrap(await ca.POST('/v1/analyses/{aid}/runs', { ...A(aid), body: { mode, competitor_ids: competitorIds ?? null } }));
}
export async function getResult(aid: string, view: View, version?: number | null): Promise<ResultOut> {
  return unwrap(await ca.GET('/v1/analyses/{aid}/result', { params: { path: { aid }, query: { view, version: version ?? null } } }));
}
export async function getDetail(aid: string, cmp: string): Promise<CompetitorDetail> {
  return unwrap(await ca.GET('/v1/analyses/{aid}/competitors/{cmp}', { params: { path: { aid, cmp } } }));
}
export async function research(aid: string, cmp: string, facts?: string[] | null): Promise<S['JobAccepted']> {
  return unwrap(await ca.POST('/v1/analyses/{aid}/competitors/{cmp}/research', {
    params: { path: { aid, cmp } }, body: { facts: (facts ?? null) as S['ResearchIn']['facts'] },
  }));
}
export async function getClaims(aid: string, p: { competitor?: string | null; fact?: string | null; status?: string | null }): Promise<ClaimList> {
  return unwrap(await ca.GET('/v1/analyses/{aid}/claims', { params: { path: { aid }, query: { competitor: p.competitor ?? null, fact: p.fact ?? null, status: p.status ?? null } } }));
}
export async function getClaim(aid: string, clm: string): Promise<ClaimDetail> {
  return unwrap(await ca.GET('/v1/analyses/{aid}/claims/{clm}', { params: { path: { aid, clm } } }));
}
export async function removeSource(aid: string, clm: string, src: string): Promise<ClaimItem> {
  return unwrap(await ca.DELETE('/v1/analyses/{aid}/claims/{clm}/sources/{src}', { params: { path: { aid, clm, src } } }));
}
export async function addSource(aid: string, body: Loose<S['SourceAddIn']>): Promise<S['SourceAddOut']> {
  return unwrap(await ca.POST('/v1/analyses/{aid}/sources', { ...A(aid), body: body as S['SourceAddIn'] }));
}
export async function addRefs(aid: string, kind: 'product' | 'solution' | 'case', ids: string[]): Promise<string[]> {
  const out = unwrap(await ca.POST('/v1/analyses/{aid}/additions', { ...A(aid), body: { kind, ids } }));
  return out.added ?? [];
}
export async function createHandoff(aid: string, body: Loose<S['HandoffIn']> & { target: S['HandoffIn']['target'] }): Promise<HandoffOut> {
  return unwrap(await ca.POST('/v1/analyses/{aid}/handoffs', { ...A(aid), body: body as S['HandoffIn'] }));
}
export async function patchHandoff(aid: string, hof: string, body: Loose<S['HandoffPatch']> & { status: S['HandoffPatch']['status'] }) {
  return unwrap(await ca.PATCH('/v1/analyses/{aid}/handoffs/{hof}', { params: { path: { aid, hof } }, body: body as S['HandoffPatch'] }));
}
export async function getBundle(aid: string, target: 'mi' | 'proposal_why' | 'storyboard', handoffId?: string | null): Promise<Bundle> {
  return unwrap(await ca.GET('/v1/analyses/{aid}/bundle', { params: { path: { aid }, query: { target, handoff_id: handoffId ?? null } } }));
}
export async function getChanges(aid: string): Promise<S['ChangesOut']> {
  return unwrap(await ca.GET('/v1/analyses/{aid}/changes', A(aid)));
}
export async function startExport(aid: string, audience: 'internal' | 'customer' = 'internal'): Promise<S['JobAccepted']> {
  return unwrap(await ca.POST('/v1/analyses/{aid}/exports', { ...A(aid), body: { format: 'pdf', audience } }));
}

// ── 훅 ─────────────────────────────────────────────────
/** 작업 상태는 다른 프로세스(워커)가 바꾸므로 화면에 들어올 때마다 새로 읽는다(staleTime 0) */
export function useAnalysis(aid: string | undefined, opts: { poll?: number | false } = {}) {
  return useQuery({ queryKey: qk.analysis(aid ?? ''), queryFn: () => getAnalysis(aid!), enabled: !!aid, refetchInterval: opts.poll ?? false, staleTime: 0 });
}
export function useCandidates(aid: string | undefined, poll?: number | false) {
  return useQuery({ queryKey: qk.candidates(aid ?? ''), queryFn: () => getCandidates(aid!), enabled: !!aid, refetchInterval: poll ?? false, staleTime: 0 });
}
export function useCriteria(aid: string | undefined) {
  return useQuery({ queryKey: qk.criteria(aid ?? ''), queryFn: () => getCriteria(aid!), enabled: !!aid, staleTime: 0 });
}
export function useResult(aid: string | undefined, view: View, poll?: number | false) {
  return useQuery({ queryKey: qk.result(aid ?? '', view), queryFn: () => getResult(aid!, view), enabled: !!aid, refetchInterval: poll ?? false, staleTime: 0 });
}
export function useChanges(aid: string | undefined, enabled = true) {
  return useQuery({ queryKey: ['ca', 'changes', aid ?? ''], queryFn: () => getChanges(aid!), enabled: !!aid && enabled });
}
export function useDetail(aid: string | undefined, cmp: string | undefined) {
  return useQuery({ queryKey: qk.detail(aid ?? '', cmp ?? ''), queryFn: () => getDetail(aid!, cmp!), enabled: !!aid && !!cmp, retry: false, staleTime: 0 });
}

// ── 다른 서비스(계약 타입) ──────────────────────────────
/** CA1R 정의서 목록 — 저장본이 있는 정의서(최근 저장순) */
export type Definition = RqS['RequirementListItem'];
/**
 * 저장된 정의서(최근 50) — `preferred`(CA1R `?rq=`)가 그 밖이면 따로 읽어 맨 앞에 둔다
 * (통합: 정의서가 많으면 넘겨받은 정의서 대신 첫 줄이 골라져 엉뚱한 정의서로 경쟁사를 찾던 것).
 */
export async function savedDefinitions(preferred?: string | null): Promise<Definition[]> {
  const out = unwrap(await api.requirements.GET('/v1/requirements', { params: { query: { tab: 'saved', has_version: true, limit: 50 } } }));
  const items = [...(out.items ?? [])];
  if (preferred && !items.some((x) => x.id === preferred)) {
    try {
      const r = unwrap(await api.requirements.GET('/v1/requirements/{rq_id}', { params: { path: { rq_id: preferred } } }));
      if ((r.version ?? 0) >= 1) {
        items.unshift({
          id: r.id, title: r.title, customer_name: r.form?.customer_name?.value ?? null, project_name: r.form?.project_name?.value ?? null,
          project_id: r.project_id, list_state: r.list_state, state_label: r.state_label, version: r.version, has_unsaved_changes: r.has_unsaved_changes,
          keyman_count: r.keyman_count, item_count: r.item_count, open_question_count: r.open_question_count, updated_at: r.updated_at,
          saved_at: r.saved_at, route: r.route, active_deep: r.active_deep, owner: r.owner,
        });
      }
    } catch { /* 목록만 */ }
  }
  return items;
}

/** 경쟁사가 있는 MI 작업(CA0 `MI 작업의 경쟁사에서`) */
export async function miWithCompetitors(q?: string) {
  const out = unwrap(await api.mi.GET('/v1/analyses', { params: { query: { has_competitors: true, limit: 30, q: q || null } } }));
  return out.items ?? [];
}
export type MiItem = Awaited<ReturnType<typeof miWithCompetitors>>[number];

/** 같은 고객사의 MI 작업(CA5 카드 1) — 최근 수정순 */
export async function miByCustomer(customer: string) {
  const out = unwrap(await api.mi.GET('/v1/analyses', { params: { query: { q: customer, limit: 10 } } }));
  return out.items ?? [];
}
export async function miGet(aid: string) {
  return unwrap(await api.mi.GET('/v1/analyses/{aid}', { params: { path: { aid } } }));
}
export async function miBundleForCompetitor(miId: string) {
  return unwrap(await api.mi.GET('/v1/analyses/{aid}/bundle', { params: { path: { aid: miId }, query: { target: 'competitor' } } }));
}
export async function miImport(body: { analysis_id?: string | null; customer_name?: string | null; ca_bundle: Record<string, unknown> }) {
  return unwrap(await api.mi.POST('/v1/imports/competitor', { body: { analysis_id: body.analysis_id ?? null, customer_name: body.customer_name ?? null, ca_bundle: body.ca_bundle } }));
}

/** 제안서 목록(CA5 카드 2 고르기 시트) */
export async function recentProposals(q?: string) {
  const out = unwrap(await api.proposal.GET('/v1/proposals', { params: { query: { tab: 'all', owner: 'all', sort: 'updated_desc', limit: 20, q: q || null } } }));
  return out.items ?? [];
}
export type ProposalItem = Awaited<ReturnType<typeof recentProposals>>[number];

/** 제안서 Why Samsung 섹션으로 가져오기(10-proposal §8.8 C1 — 넘김 기록 handoff_id) */
export async function proposalImport(pid: string, source: { ref_id: string; version: number; handoff_id: string; title: string }) {
  const r = await api.proposal.POST('/v1/proposals/{proposal_id}/imports', {
    params: { path: { proposal_id: pid } },
    // feature 는 서비스 키(10-proposal §(반입) · proposal-web 요청 2 — 코드 `CA` 도 받기로 함)
    body: { section_key: 'why', via: 'handoff', source: { feature: 'competitor', ref_id: source.ref_id, version: source.version, handoff_id: source.handoff_id, title: source.title } } as never,
  });
  return unwrap(r) as { job_id?: string | null; route?: string | null; import_id?: string | null };
}

/** 새 제안서(CA5 `새 제안서로 시작`) — 넘김으로 시작 */
export async function createProposal(title: string, customer: string | null) {
  const p = unwrap(await api.proposal.POST('/v1/proposals', {
    body: { start_mode: 'handoff', title, customer: customer ? { name: customer } : null } as never,
  }));
  return p as { id: string; title?: string | null };
}

/** Storyboard 목록(CA5 카드 3 고르기 시트) */
export async function recentStoryboards(customer?: string | null) {
  const out = unwrap(await api.storyboard.GET('/v1/storyboards', { params: { query: { tab: 'all', limit: 20, customer: customer || null } } }));
  return out.items ?? [];
}
export type StoryboardItem = Awaited<ReturnType<typeof recentStoryboards>>[number];

export async function storyboardImport(sbId: string, b: Bundle) {
  const crit = (b.criteria ?? []) as Array<{ name: string; importance?: number | string | null; source?: string | null }>;
  return unwrap(await api.storyboard.POST('/v1/storyboards/{sb_id}/imports/competitor', {
    params: { path: { sb_id: sbId } },
    body: {
      analysis_id: b.analysis_id, title: (b as { title?: string }).title ?? null,
      criteria: crit.map((c) => ({ name: c.name, importance: c.importance == null ? null : String(c.importance), source: c.source ?? null })),
      competitors: ((b.competitors ?? []) as unknown[]).map((x) => String(x)), note: (b as { note?: string }).note ?? null,
    },
  }));
}

/** 잡이 끝날 때까지 기다린다(다른 서비스 잡 — MI 가져오기 · 리포트). */
export async function waitJob(jobId: string, timeoutMs = 120_000): Promise<{ status: string; result?: Record<string, unknown> | null; error?: { message?: string } | null }> {
  const t0 = Date.now();
  for (;;) {
    const j = unwrap(await api.jobs.GET('/v1/jobs/{job_id}', { params: { path: { job_id: jobId } } })) as { status: string; result?: Record<string, unknown> | null; error?: { message?: string } | null };
    if (['succeeded', 'failed', 'canceled'].includes(j.status)) return j;
    if (Date.now() - t0 > timeoutMs) return { status: 'timeout', error: { message: '시간이 오래 걸려요 · 잠시 뒤 다시 확인해 주세요' } };
    await new Promise((r) => setTimeout(r, 1000));
  }
}

/** 리포트 파일 내려받기 주소(files) */
export const fileDownloadUrl = (fileId: string) => `/api/files/v1/files/${fileId}/content?download=1`;
