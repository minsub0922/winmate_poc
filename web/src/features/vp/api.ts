/**
 * vp API(contracts/vp.json → @/api/gen/vp) — 화면이 쓰는 호출 · react-query 훅.
 * 오래 걸리는 일은 202 {job_id} → useJob(SSE) → 끝나면 문서를 다시 읽는다.
 */
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api, unwrap, ApiError } from '@/api/client';
import type { components } from '@/api/gen/vp';

type S = components['schemas'];
export type VPDoc = S['VPDoc'];
export type VPList = S['VPList'];
export type VPListItem = S['VPListItem'];
export type Plan = S['Plan'];
export type Sheet = S['Sheet'];
export type Question = S['Question'];
export type MaterialItem = S['MaterialItem'];
export type Fix = S['Fix'];
export type Mode = 'auto' | 'check' | 'ask' | 'pin';
export type LayoutOptions = S['LayoutOptions'];
export type MetricsView = S['MetricsView'];
export type Metric = S['Metric'];
export type ImageSlot = S['ImageSlot'];
export type ImageSlotsView = S['ImageSlotsView'];
export type SlotCandidates = S['SlotCandidates'];
export type SlotCandidate = S['SlotCandidate'];
export type PackageSet = S['PackageSet'];
export type Package = S['Package'];
export type RoutingRules = S['RoutingRules'];
export type IndustryPacks = S['IndustryPacks'];
export type SourceCandidates = S['SourceCandidates'];
export type Decision = S['Decision'];
export type JobAccepted = S['JobAccepted'];
export type CheckItem = S['CheckItem'];
export type LayoutChip = S['LayoutChip'];

export { ApiError };

const P = (vp_id: string) => ({ params: { path: { vp_id } } });

export const vpKeys = {
  all: ['vp'] as const,
  list: (q: Record<string, unknown>) => ['vp', 'list', q] as const,
  doc: (id: string) => ['vp', 'doc', id] as const,
  plan: (id: string) => ['vp', 'plan', id] as const,
  sources: (id: string) => ['vp', 'sources', id] as const,
  layout: (id: string, sh: string, pillars?: number, req?: string) => ['vp', 'layout', id, sh, pillars ?? 0, req ?? ''] as const,
  metrics: (id: string, sh: string) => ['vp', 'metrics', id, sh] as const,
  slots: (id: string) => ['vp', 'slots', id] as const,
  cands: (id: string, vis: string) => ['vp', 'cands', id, vis] as const,
  packages: (id: string, sel?: string, notes?: boolean) => ['vp', 'packages', id, sel ?? '', notes ?? true] as const,
  rules: ['vp', 'rules'] as const,
  packs: ['vp', 'packs'] as const,
};

// ── 읽기 ────────────────────────────────────────────────

export async function getVp(id: string): Promise<VPDoc> {
  return unwrap(await api.vp.GET('/v1/vps/{vp_id}', P(id)));
}

export function useVp(id: string | undefined, opts: { poll?: number | false } = {}) {
  return useQuery({
    queryKey: vpKeys.doc(id ?? ''), queryFn: () => getVp(id!), enabled: !!id,
    staleTime: 1500, // 단계 화면을 옮길 때마다 새로 읽는다(잡이 문서를 계속 바꾼다)
    refetchInterval: (q) => {
      if (opts.poll === false) return false;
      const d = q.state.data as VPDoc | undefined;
      return d && d.active_job && !['succeeded', 'failed', 'canceled'].includes(d.active_job.status ?? '') ? (opts.poll ?? 2500) : false;
    },
  });
}

export function useVpList(q: { status?: string; industry?: string; q?: string }) {
  return useQuery({
    queryKey: vpKeys.list(q),
    queryFn: async () => unwrap(await api.vp.GET('/v1/vps', { params: { query: { limit: 100, ...q, q: q.q || undefined, status: q.status || undefined, industry: q.industry || undefined } } })),
    refetchInterval: (qq) => ((qq.state.data as VPList | undefined)?.items.some((i) => i.ui_status === 'run') ? 3000 : false),
  });
}

export function usePlan(id: string | undefined) {
  return useQuery({ queryKey: vpKeys.plan(id ?? ''), queryFn: async () => unwrap(await api.vp.GET('/v1/vps/{vp_id}/plan', P(id!))), enabled: !!id });
}

export function useSourceCandidates(id: string | undefined) {
  return useQuery({ queryKey: vpKeys.sources(id ?? ''), queryFn: async () => unwrap(await api.vp.GET('/v1/vps/{vp_id}/source-candidates', P(id!))), enabled: !!id });
}

export function useLayoutOptions(id: string | undefined, sh: string | undefined, pillars?: number, req?: string) {
  return useQuery({
    queryKey: vpKeys.layout(id ?? '', sh ?? '', pillars, req),
    queryFn: async () => unwrap(await api.vp.GET('/v1/vps/{vp_id}/sheets/{sh}/layout-options', {
      params: { path: { vp_id: id!, sh: sh! }, query: { pillars: pillars || undefined, request_id: req || undefined } },
    })),
    enabled: !!id && !!sh,
  });
}

export function useMetrics(id: string | undefined, sh: string | undefined) {
  return useQuery({
    queryKey: vpKeys.metrics(id ?? '', sh ?? ''),
    queryFn: async () => unwrap(await api.vp.GET('/v1/vps/{vp_id}/sheets/{sh}/metrics', { params: { path: { vp_id: id!, sh: sh! } } })),
    enabled: !!id && !!sh,
  });
}

export function useSlots(id: string | undefined) {
  return useQuery({ queryKey: vpKeys.slots(id ?? ''), queryFn: async () => unwrap(await api.vp.GET('/v1/vps/{vp_id}/image-slots', P(id!))), enabled: !!id });
}

export function useSlotCandidates(id: string | undefined, vis: string | undefined) {
  return useQuery({
    queryKey: vpKeys.cands(id ?? '', vis ?? ''),
    queryFn: async () => unwrap(await api.vp.GET('/v1/vps/{vp_id}/image-slots/{vis}/candidates', { params: { path: { vp_id: id!, vis: vis! } } })),
    enabled: !!id && !!vis,
  });
}

export function usePackages(id: string | undefined, selected?: string, notes = true) {
  return useQuery({
    queryKey: vpKeys.packages(id ?? '', selected, notes),
    queryFn: async () => unwrap(await api.vp.GET('/v1/vps/{vp_id}/packages', {
      params: { path: { vp_id: id! }, query: { selected: (selected || undefined) as 'standard' | 'quickwin' | 'solution' | undefined, estimates_as_notes: notes } },
    })),
    enabled: !!id,
  });
}

export function useRules() {
  return useQuery({ queryKey: vpKeys.rules, queryFn: async () => unwrap(await api.vp.GET('/v1/routing-rules')), staleTime: 60_000 });
}

export function usePacks() {
  return useQuery({ queryKey: vpKeys.packs, queryFn: async () => unwrap(await api.vp.GET('/v1/industry-packs')), staleTime: 60_000 });
}

/** 문서 · 플랜 · 보조 조회를 한 번에 새로 읽는다. */
export function useRefresh(id: string | undefined) {
  const qc = useQueryClient();
  return async () => {
    if (!id) return;
    await Promise.all([
      qc.invalidateQueries({ queryKey: vpKeys.doc(id) }),
      qc.invalidateQueries({ queryKey: ['vp', 'plan', id] }),
      qc.invalidateQueries({ queryKey: ['vp', 'layout', id] }),
      qc.invalidateQueries({ queryKey: ['vp', 'metrics', id] }),
      qc.invalidateQueries({ queryKey: ['vp', 'slots', id] }),
      qc.invalidateQueries({ queryKey: ['vp', 'cands', id] }),
      qc.invalidateQueries({ queryKey: ['vp', 'packages', id] }),
      qc.invalidateQueries({ queryKey: ['vp', 'sources', id] }),
      qc.invalidateQueries({ queryKey: ['vp', 'list'] }),
    ]);
  };
}

// ── 쓰기 ────────────────────────────────────────────────

/** 생성 — 기본값이 있는 필드(auto_answer 등)는 비워도 된다 */
export async function createVp(body: Partial<S['CreateVP']> & Pick<S['CreateVP'], 'start'>): Promise<VPDoc> {
  return unwrap(await api.vp.POST('/v1/vps', { body: body as S['CreateVP'] }));
}
/** 부분 수정 — 보낸 필드만 바뀐다 */
export async function patchVp(id: string, body: Partial<S['PatchVP']>): Promise<VPDoc> {
  return unwrap(await api.vp.PATCH('/v1/vps/{vp_id}', { ...P(id), body: body as S['PatchVP'] }));
}
export async function cloneVp(id: string, body: S['CloneVP']): Promise<VPDoc> {
  return unwrap(await api.vp.POST('/v1/vps/{vp_id}:clone', { ...P(id), body }));
}
export async function putSources(id: string, sources: S['SourceToggle'][]): Promise<VPDoc> {
  return unwrap(await api.vp.PUT('/v1/vps/{vp_id}/sources', { ...P(id), body: { sources } }));
}
export async function addAttachment(id: string, file_id: string, kind?: S['AddAttachment']['kind']) {
  const r = await api.vp.POST('/v1/vps/{vp_id}/attachments', { ...P(id), body: { file_id, kind } });
  return unwrap(r) as S['Attachment'] | JobAccepted;
}
export async function deleteAttachment(id: string, att: string) {
  const r = await api.vp.DELETE('/v1/vps/{vp_id}/attachments/{att_id}', { params: { path: { vp_id: id, att_id: att } } });
  if (!r.response.ok) unwrap(r);
}
export async function collect(id: string, note?: string): Promise<JobAccepted> {
  return unwrap(await api.vp.POST('/v1/vps/{vp_id}/materials:collect', { ...P(id), body: note !== undefined ? { note } : {} }));
}
export async function decideFix(id: string, fx: string, decision: 'accept' | 'revert'): Promise<VPDoc> {
  return unwrap(await api.vp.POST('/v1/vps/{vp_id}/fixes/{fx}:decide', { params: { path: { vp_id: id, fx } }, body: { decision } }));
}
export async function answerQuestions(id: string, answers: S['AnswerItem'][], proceed = true) {
  return unwrap(await api.vp.POST('/v1/vps/{vp_id}/questions:answer', { ...P(id), body: { answers, proceed } }));
}
export async function refreshPlan(id: string): Promise<Plan> {
  return unwrap(await api.vp.POST('/v1/vps/{vp_id}/plan:refresh', P(id)));
}
export async function patchPlan(id: string, override: Partial<S['PlanOverride']>): Promise<Plan> {
  return unwrap(await api.vp.PATCH('/v1/vps/{vp_id}/plan', { ...P(id), body: { override: override as S['PlanOverride'] } }));
}
export async function generate(id: string, retry = false): Promise<JobAccepted> {
  return unwrap(await api.vp.POST('/v1/vps/{vp_id}/generate', { ...P(id), body: { retry } }));
}
export async function postMessage(id: string, body: S['MessageBody']): Promise<JobAccepted> {
  return unwrap(await api.vp.POST('/v1/vps/{vp_id}/messages', { ...P(id), body }));
}
export async function chooseLayout(id: string, sh: string, body: S['ChooseLayout']) {
  const r = await api.vp.POST('/v1/vps/{vp_id}/sheets/{sh}/layout', { params: { path: { vp_id: id, sh } }, body });
  const data = unwrap(r) as Sheet | JobAccepted;
  return { status: r.response.status, data };
}
export async function cancelLayoutRequest(id: string, vlr: string) {
  const r = await api.vp.POST('/v1/vps/{vp_id}/layout-requests/{vlr}:cancel', { params: { path: { vp_id: id, vlr } } });
  if (!r.response.ok) unwrap(r);
}
export async function addSheet(id: string, body: S['AddSheet']): Promise<JobAccepted> {
  return unwrap(await api.vp.POST('/v1/vps/{vp_id}/sheets', { ...P(id), body }));
}
export async function patchMetric(id: string, vmt: string, body: S['PatchMetric']): Promise<MetricsView> {
  return unwrap(await api.vp.PATCH('/v1/vps/{vp_id}/metrics/{vmt}', { params: { path: { vp_id: id, vmt } }, body }));
}
export async function applyMetrics(id: string, sh: string) {
  const r = await api.vp.POST('/v1/vps/{vp_id}/sheets/{sh}/metrics:apply', { params: { path: { vp_id: id, sh } } });
  return { status: r.response.status, data: unwrap(r) as VPDoc | JobAccepted };
}
export async function dataRequestDraft(id: string, sheet?: string) {
  return unwrap(await api.vp.GET('/v1/vps/{vp_id}/data-request-draft', { params: { path: { vp_id: id }, query: { sheet } } }));
}
export async function putSlot(id: string, vis: string, asset: S['AssetRef']): Promise<ImageSlot> {
  return unwrap(await api.vp.PUT('/v1/vps/{vp_id}/image-slots/{vis}', { params: { path: { vp_id: id, vis } }, body: { asset } }));
}
export async function restyle(id: string): Promise<JobAccepted> {
  return unwrap(await api.vp.POST('/v1/vps/{vp_id}/images:restyle', { ...P(id), body: { style: 'illustration' } }));
}
export async function startExport(id: string, format: 'pptx' | 'pdf_summary', proposal_type?: string, include_notes = true): Promise<JobAccepted> {
  return unwrap(await api.vp.POST('/v1/vps/{vp_id}/exports', {
    ...P(id), body: { format, include_notes, proposal_type: (proposal_type || undefined) as 'standard' | 'quickwin' | 'solution' | undefined },
  }));
}
export async function getExport(id: string, vex: string) {
  return unwrap(await api.vp.GET('/v1/vps/{vp_id}/exports/{vex}', { params: { path: { vp_id: id, vex } } }));
}
export async function copyText(id: string): Promise<string> {
  return unwrap(await api.vp.GET('/v1/vps/{vp_id}/copy-text', P(id))).text;
}
export async function createHandoff(id: string, body: S['HandoffBody']) {
  const r = await api.vp.POST('/v1/vps/{vp_id}/handoffs', { ...P(id), body });
  return { status: r.response.status, data: unwrap(r) as S['HandoffCreated'] | JobAccepted };
}
export async function savePoint(id: string, reason = '저장'): Promise<VPDoc> {
  return unwrap(await api.vp.POST('/v1/vps/{vp_id}/versions', { ...P(id), body: { reason } }));
}
export async function decidePackOffer(id: string, vpo: string, decision: 'apply' | 'dismiss') {
  const r = await api.vp.POST('/v1/vps/{vp_id}/pack-offers/{vpo}:decide', { params: { path: { vp_id: id, vpo } }, body: { decision } });
  return { status: r.response.status, data: unwrap(r) as VPDoc | JobAccepted };
}
export async function archiveVp(id: string) {
  const r = await api.vp.POST('/v1/vps/{vp_id}:archive', P(id));
  if (!r.response.ok) unwrap(r);
}

export const isJob = (x: unknown): x is JobAccepted => !!x && typeof x === 'object' && 'job_id' in (x as object);

/** 화면에 보일 오류 글(ApiError 면 서비스 한국어 메시지). */
export function errText(e: unknown): string {
  if (e instanceof ApiError) return e.message;
  if (e instanceof Error) return e.message;
  return '잠시 후 다시 시도해 주세요.';
}
