/**
 * spec API(게이트웨이 `/api/spec/v1`) — 타입은 contracts/spec.json 에서 생성(@/api/gen/spec).
 * 화면은 이 파일의 함수 · 훅만 쓴다(경로 문자열을 화면에 흩뜨리지 않는다).
 */
import { useQuery, useQueryClient, type QueryClient } from '@tanstack/react-query';
import { api, unwrap, ApiError } from '@/api/client';
import type { components } from '@/api/gen/spec';

type S = components['schemas'];
export type Sheet = S['SheetDoc'];
export type SheetList = S['SheetList'];
export type SheetListItem = S['SheetListItem'];
export type Product = S['Product'];
export type Row = S['Row'];
export type Cell = S['Cell'];
export type SheetTable = S['SheetTable'];
export type ValueCheck = S['ValueCheck'];
export type Warning = S['Warning'];
export type WarningsView = S['WarningsView'];
export type Compliance = S['Compliance'];
export type ComplianceRow = S['ComplianceRow'];
export type FinderState = S['FinderState'];
export type FinderConditions = S['FinderConditions'];
export type FinderCandidate = S['FinderCandidate'];
export type FormatSettings = S['FormatSettings'];
export type FormatPreview = S['FormatPreview'];
export type EditView = S['EditView'];
export type EditOp = S['EditOp'];
export type Package = S['Package'];
export type ExportRecord = S['ExportRecord'];
export type Source = S['Source'];
export type ItemCatalog = S['ItemCatalog'];
export type Combo = S['Combo'];
export type PageView = S['PageView'];
export type AskDraft = S['AskDraft'];
export type Preferences = S['Preferences'];
export type CreateSheet = S['CreateSheet'];

const sp = api.spec;
const P = (sheet_id: string) => ({ params: { path: { sheet_id } } });

export const qk = {
  sheet: (id: string) => ['spec', 'sheet', id] as const,
  list: (p: Record<string, unknown>) => ['spec', 'list', p] as const,
  warnings: (id: string) => ['spec', 'warnings', id] as const,
  itemCatalog: ['spec', 'item-catalog'] as const,
  combos: ['spec', 'combos'] as const,
  prefs: ['spec', 'prefs'] as const,
};

/** 오류 → 화면 문구(서버 한국어 메시지 그대로, 없으면 기본) */
export function errText(e: unknown, fallback = '처리하지 못했어요. 잠시 뒤 다시 시도해 주세요.'): string {
  if (e instanceof ApiError) return e.message || fallback;
  if (e instanceof Error && e.message) return e.message;
  return fallback;
}
export const isApiError = (e: unknown, code?: string): e is ApiError => e instanceof ApiError && (!code || e.code === code);

// ── 목록 · 작업 ─────────────────────────────────────────

export interface ListParams { tab?: 'all' | 'draft' | 'check' | 'done'; q?: string; linked?: boolean; archived?: boolean; sort?: 'updated_desc' | 'title' | 'status' }

export const useSheetList = (p: ListParams) =>
  useQuery({
    queryKey: qk.list(p as Record<string, unknown>),
    queryFn: async () => unwrap(await sp.GET('/v1/sheets', { params: { query: { limit: 200, tab: p.tab, q: p.q || undefined, linked: p.linked || undefined,
      archived: p.archived || undefined, sort: p.sort } } })),
    refetchInterval: 20_000,
  });

/** poll: 고정 간격 또는 (시트) => 간격 — 서버에서 도는 일(찾기 · 대응표 · 생성)을 화면이 놓쳤을 때(새로고침 등) 따라잡는다 */
export const useSheet = (id: string | undefined, opts: { poll?: number | false | ((s: Sheet | undefined) => number | false) } = {}) => {
  const poll = opts.poll ?? false;
  return useQuery({
    queryKey: qk.sheet(id ?? ''),
    queryFn: async () => unwrap(await sp.GET('/v1/sheets/{sheet_id}', P(id!))),
    enabled: !!id,
    refetchInterval: typeof poll === 'function' ? (q) => poll(q.state.data as Sheet | undefined) : poll,
  });
};

export async function createSheet(body: CreateSheet) {
  return unwrap(await sp.POST('/v1/sheets', { body }));
}
export async function getSheet(id: string) {
  return unwrap(await sp.GET('/v1/sheets/{sheet_id}', P(id)));
}
/** 기본값이 있는 필드는 생략 가능(서버 Pydantic 기본값) — 생성 타입은 기본값 필드를 필수로 표시한다 */
type Loose<T> = Partial<T>;

export async function patchSheet(id: string, body: Loose<S['PatchSheet']>) {
  return unwrap(await sp.PATCH('/v1/sheets/{sheet_id}', { ...P(id), body: body as S['PatchSheet'] }));
}
export async function cloneSheet(id: string) {
  return unwrap(await sp.POST('/v1/sheets/{sheet_id}:clone', { ...P(id), body: {} }));
}
export async function archiveSheet(id: string) {
  const r = await sp.POST('/v1/sheets/{sheet_id}:archive', P(id));
  if (!r.response.ok) unwrap(r as never);
}
export async function saveSheet(id: string) {
  return unwrap(await sp.POST('/v1/sheets/{sheet_id}:save', P(id)));
}

// ── 제품 ─────────────────────────────────────────────────

export async function addProducts(id: string, refs: string[], source?: S['AddProducts']['source'], role?: S['AddProducts']['role']) {
  return unwrap(await sp.POST('/v1/sheets/{sheet_id}/products', { ...P(id), body: { refs, source, role } }));
}
export async function removeProduct(id: string, productId: string) {
  return unwrap(await sp.DELETE('/v1/sheets/{sheet_id}/products/{product_id}', { params: { path: { sheet_id: id, product_id: productId } } }));
}
export const useCombos = () =>
  useQuery({ queryKey: qk.combos, queryFn: async () => unwrap(await sp.GET('/v1/combos', {})).items, staleTime: 10 * 60_000, retry: 1 });

// ── 찾기 ─────────────────────────────────────────────────

export async function putFinder(id: string, body: S['FinderPut']) {
  return unwrap(await sp.PUT('/v1/sheets/{sheet_id}/finder', { ...P(id), body }));
}
export async function parseFinder(id: string, text: string) {
  return unwrap(await sp.POST('/v1/sheets/{sheet_id}/finder:parse', { ...P(id), body: { text } }));
}
export async function commitFinder(id: string, selected: string[], to: 'items' | 'products') {
  return unwrap(await sp.POST('/v1/sheets/{sheet_id}/finder:commit', { ...P(id), body: { selected, to } }));
}

// ── 대응표 ───────────────────────────────────────────────

export async function addRequirementDoc(id: string, fileId: string, note?: string) {
  return unwrap(await sp.POST('/v1/sheets/{sheet_id}/requirement-docs', { ...P(id), body: { file_id: fileId, note: note || null } }));
}
export async function patchCompliance(id: string, body: S['CompliancePatch']) {
  return unwrap(await sp.PATCH('/v1/sheets/{sheet_id}/compliance', { ...P(id), body }));
}
export async function getAskDraft(id: string) {
  return unwrap(await sp.GET('/v1/sheets/{sheet_id}/compliance/ask-draft', P(id)));
}
export async function getPage(id: string, docId: string, n: number) {
  return unwrap(await sp.GET('/v1/sheets/{sheet_id}/requirement-docs/{doc_id}/pages/{n}', { params: { path: { sheet_id: id, doc_id: docId, n } } }));
}
export async function complianceToItems(id: string) {
  return unwrap(await sp.POST('/v1/sheets/{sheet_id}/compliance:to-items', P(id)));
}

// ── 항목 · 형식 ───────────────────────────────────────────

export const useItemCatalog = () =>
  useQuery({ queryKey: qk.itemCatalog, queryFn: async () => unwrap(await sp.GET('/v1/item-catalog', {})), staleTime: Infinity });
export async function putItems(id: string, body: S['ItemsPut']) {
  return unwrap(await sp.PUT('/v1/sheets/{sheet_id}/items', { ...P(id), body }));
}
export async function diffItems(id: string) {
  return unwrap(await sp.GET('/v1/sheets/{sheet_id}/diff-items', P(id))).different;
}
export async function putFormat(id: string, body: FormatSettings) {
  return unwrap(await sp.PUT('/v1/sheets/{sheet_id}/format', { ...P(id), body }));
}
export async function formatPreview(id: string, body: S['FormatPreviewBody']) {
  return unwrap(await sp.POST('/v1/sheets/{sheet_id}/format:preview', { ...P(id), body }));
}
export async function addTemplate(id: string, fileId: string) {
  return unwrap(await sp.POST('/v1/sheets/{sheet_id}/templates', { ...P(id), body: { file_id: fileId } }));
}
export async function removeTemplate(id: string, templateId: string) {
  const r = await sp.DELETE('/v1/sheets/{sheet_id}/templates/{template_id}', { params: { path: { sheet_id: id, template_id: templateId } } });
  if (!r.response.ok) unwrap(r as never);
}
export const usePreferences = () =>
  useQuery({ queryKey: qk.prefs, queryFn: async () => unwrap(await sp.GET('/v1/preferences', {})), staleTime: 60_000 });
export async function savePreferences(body: S['FormatSettingsPatch']) {
  return unwrap(await sp.PUT('/v1/preferences', { body }));
}

// ── 생성 · 값 확인 ────────────────────────────────────────

export async function generate(id: string, body: Loose<S['GenerateBody']> = {}) {
  return unwrap(await sp.POST('/v1/sheets/{sheet_id}/generate', { ...P(id), body: body as S['GenerateBody'] }));
}
export async function answerCheck(id: string, checkId: string, body: S['CheckAnswerBody']) {
  return unwrap(await sp.POST('/v1/sheets/{sheet_id}/checks/{check_id}:answer', { params: { path: { sheet_id: id, check_id: checkId } }, body }));
}
export async function applyChecks(id: string, answers: S['ApplyAnswer'][]) {
  return unwrap(await sp.POST('/v1/sheets/{sheet_id}/checks:apply', { ...P(id), body: { answers } }));
}
export async function deferAll(id: string) {
  return unwrap(await sp.POST('/v1/sheets/{sheet_id}/checks:defer-all', P(id)));
}
export async function addDatasheet(id: string, fileId: string, productId: string) {
  return unwrap(await sp.POST('/v1/sheets/{sheet_id}/datasheets', { ...P(id), body: { file_id: fileId, product_id: productId } }));
}
export async function cellSources(id: string, rowId: string, productId: string) {
  return unwrap(await sp.GET('/v1/sheets/{sheet_id}/cells/{row_id}/{product_id}/sources', { params: { path: { sheet_id: id, row_id: rowId, product_id: productId } } })).sources;
}
export async function patchCell(id: string, rowId: string, productId: string, valueText: string) {
  return unwrap(await sp.PATCH('/v1/sheets/{sheet_id}/cells/{row_id}/{product_id}', {
    params: { path: { sheet_id: id, row_id: rowId, product_id: productId } }, body: { value_text: valueText } }));
}
export async function sendMessage(id: string, text: string, context: S['MessageBody']['context']) {
  return unwrap(await sp.POST('/v1/sheets/{sheet_id}/messages', { ...P(id), body: { text, context } }));
}

// ── 내보내기 · 공유 · 넘김 ─────────────────────────────────

export async function createExport(id: string, body: S['ExportBody']) {
  return unwrap(await sp.POST('/v1/sheets/{sheet_id}/exports', { ...P(id), body }));
}
export async function getExport(id: string, exportId: string) {
  return unwrap(await sp.GET('/v1/sheets/{sheet_id}/exports/{export_id}', { params: { path: { sheet_id: id, export_id: exportId } } }));
}
export async function shareSheet(id: string) {
  return unwrap(await sp.POST('/v1/sheets/{sheet_id}/share', P(id)));
}
export async function getPackage(id: string, templates: string[], locale?: string) {
  return unwrap(await sp.GET('/v1/sheets/{sheet_id}/package', {
    params: { path: { sheet_id: id }, query: { templates: templates.join(','), locale: locale || undefined } } }));
}
export async function createHandoff(id: string, body: S['HandoffBody']) {
  return unwrap(await sp.POST('/v1/sheets/{sheet_id}/handoffs', { ...P(id), body }));
}

// ── 편집 세션 ─────────────────────────────────────────────

const SP_ = (sheet_id: string, session_id: string) => ({ params: { path: { sheet_id, session_id } } });
export async function createEditSession(id: string) {
  return unwrap(await sp.POST('/v1/sheets/{sheet_id}/edit-sessions', P(id)));
}
export async function getEditSession(id: string, ses: string) {
  return unwrap(await sp.GET('/v1/sheets/{sheet_id}/edit-sessions/{session_id}', SP_(id, ses)));
}
export async function addEditOps(id: string, ses: string, ops: EditOp[]) {
  return unwrap(await sp.POST('/v1/sheets/{sheet_id}/edit-sessions/{session_id}/ops', { ...SP_(id, ses), body: { ops } }));
}
export async function editAction(id: string, ses: string, action: 'undo' | 'redo' | 'reset') {
  if (action === 'undo') return unwrap(await sp.POST('/v1/sheets/{sheet_id}/edit-sessions/{session_id}:undo', SP_(id, ses)));
  if (action === 'redo') return unwrap(await sp.POST('/v1/sheets/{sheet_id}/edit-sessions/{session_id}:redo', SP_(id, ses)));
  return unwrap(await sp.POST('/v1/sheets/{sheet_id}/edit-sessions/{session_id}:reset', SP_(id, ses)));
}
export async function editMessage(id: string, ses: string, text: string) {
  return unwrap(await sp.POST('/v1/sheets/{sheet_id}/edit-sessions/{session_id}/messages', { ...SP_(id, ses), body: { text } }));
}
export async function commitEdit(id: string, ses: string, rebase = false) {
  return unwrap(await sp.POST('/v1/sheets/{sheet_id}/edit-sessions/{session_id}:commit', { ...SP_(id, ses), body: { rebase } }));
}
export async function discardEdit(id: string, ses: string) {
  const r = await sp.DELETE('/v1/sheets/{sheet_id}/edit-sessions/{session_id}', SP_(id, ses));
  if (!r.response.ok) unwrap(r as never);
}

// ── 경고 ─────────────────────────────────────────────────

export const useWarnings = (id: string | undefined) =>
  useQuery({ queryKey: qk.warnings(id ?? ''), queryFn: async () => unwrap(await sp.GET('/v1/sheets/{sheet_id}/warnings', P(id!))), enabled: !!id });
export async function decideWarning(id: string, warningId: string, optionKey: string) {
  return unwrap(await sp.PATCH('/v1/sheets/{sheet_id}/warnings/{warning_id}', {
    params: { path: { sheet_id: id, warning_id: warningId } }, body: { option_key: optionKey } }));
}
export async function applyWarnings(id: string) {
  return unwrap(await sp.POST('/v1/sheets/{sheet_id}/warnings:apply', P(id)));
}

// ── 캐시 ─────────────────────────────────────────────────

export function setSheetCache(qc: QueryClient, s: Sheet) {
  qc.setQueryData(qk.sheet(s.id), s);
  void qc.invalidateQueries({ queryKey: ['spec', 'list'] });
  void qc.invalidateQueries({ queryKey: ['ws'] });
}

export function useSheetCache() {
  const qc = useQueryClient();
  return {
    qc,
    put: (s: Sheet) => setSheetCache(qc, s),
    refresh: (id: string) => qc.invalidateQueries({ queryKey: qk.sheet(id) }),
    refreshWarnings: (id: string) => qc.invalidateQueries({ queryKey: qk.warnings(id) }),
  };
}

/** 파일 내려받기(files 서비스) */
export function downloadFile(fileId: string, filename?: string) {
  const a = document.createElement('a');
  a.href = `/api/files/v1/files/${fileId}/content?download=1`;
  if (filename) a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
}

/** 내보내기 잡이 끝날 때까지 기다린다(빠른 내보내기 · SP4). */
export async function waitExport(id: string, exportId: string, signal?: AbortSignal): Promise<ExportRecord> {
  for (let i = 0; i < 240; i++) {
    if (signal?.aborted) throw new Error('취소됨');
    const rec = await getExport(id, exportId);
    if (rec.status === 'done' || rec.status === 'failed') return rec;
    await new Promise((r) => setTimeout(r, i < 10 ? 500 : 1500));
  }
  throw new Error('파일을 만드는 데 시간이 너무 오래 걸려요.');
}
