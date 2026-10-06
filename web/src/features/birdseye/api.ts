/**
 * birdseye 서비스 호출(게이트웨이 `/api/birdseye/v1`) — 타입은 contracts/birdseye.json 에서 생성한 `@/api/gen/birdseye`.
 * 화면 데이터는 react-query 로 읽고, 잡 진행은 `@/api/jobs` 의 useJob(SSE) + 짧은 다시 읽기로 맞춘다.
 */
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api, ApiError, unwrap, uploadFile } from '@/api/client';
import type { components } from '@/api/gen/birdseye';

export type S = components['schemas'];
export type Birdseye = S['Birdseye'];
export type Row = S['BirdseyeRow'];
export type BList = S['BirdseyeList'];
export type SpaceModel = S['SpaceModel'];
export type SpaceView = S['SpaceView'];
export type PlanView = S['PlanView'];
export type Question = S['Question'];
export type PhotoSet = S['PhotoSet'];
export type Photo = S['Photo'];
export type ProductsView = S['ProductsView'];
export type ProductItem = S['ProductItem'];
export type FurnitureView = S['FurnitureView'];
export type FurnitureItem = S['FurnitureItem'];
export type LayoutView = S['LayoutView'];
export type Layout = S['Layout'];
export type LayoutItem = S['LayoutItem'];
export type LayoutGroup = S['LayoutGroup'];
export type LayoutWarning = S['LayoutWarning'];
export type PlanGeometry = S['PlanGeometry'];
export type Overlays = S['Overlays'];
export type SessionView = S['SessionView'];
export type MoveMark = S['MoveMark'];
export type Op = S['Op'];
export type Cut = S['Cut'];
export type ZonesView = S['ZonesView'];
export type ZonePoint = S['ZonePoint'];
export type ExportOptions = S['ExportOptions'];
export type Quantities = S['Quantities'];
export type ExportRecord = S['ExportRecord'];
export type Catalog = S['CatalogOut'];
export type UploadToken = S['UploadToken'];

const B = api.birdseye;
const id_ = (be_id: string) => ({ params: { path: { be_id } } });

export const be = {
  list: async (q: { filter?: 'all' | 'in_progress' | 'needs_check' | 'done'; in_proposal?: boolean; q?: string; scope?: 'mine' | 'team'; limit?: number } = {}) =>
    unwrap(await B.GET('/v1/birdseyes', { params: { query: { ...q, q: q.q || undefined, limit: q.limit ?? 50 } } })),
  create: async (body: S['BirdseyeCreate']) => unwrap(await B.POST('/v1/birdseyes', { body })),
  get: async (id: string) => unwrap(await B.GET('/v1/birdseyes/{be_id}', id_(id))),
  patch: async (id: string, body: Partial<S['BirdseyePatch']>) =>
    unwrap(await B.PATCH('/v1/birdseyes/{be_id}', { ...id_(id), body: { clear_area: false, clear_ceiling: false, ...body } })),
  remove: async (id: string) => { const r = await B.DELETE('/v1/birdseyes/{be_id}', id_(id)); if (!r.response.ok) unwrap(r as never); },
  clone: async (id: string, title?: string) => unwrap(await B.POST('/v1/birdseyes/{be_id}:clone', { ...id_(id), body: { title: title ?? null } })),
  save: async (id: string) => unwrap(await B.POST('/v1/birdseyes/{be_id}:save', id_(id))),
  // 공간
  analyze: async (id: string) => unwrap(await B.POST('/v1/birdseyes/{be_id}/space:analyze', id_(id))),
  space: async (id: string) => unwrap(await B.GET('/v1/birdseyes/{be_id}/space', id_(id))),
  attach: async (id: string, fileIds: string[]) => unwrap(await B.POST('/v1/birdseyes/{be_id}/attachments', { ...id_(id), body: { file_ids: fileIds } })),
  addPlan: async (id: string, fileId: string, page = 1) => unwrap(await B.POST('/v1/birdseyes/{be_id}/plans', { ...id_(id), body: { file_id: fileId, page } })),
  plans: async (id: string) => unwrap(await B.GET('/v1/birdseyes/{be_id}/plans', id_(id))),
  recognize: async (id: string, planId: string, page?: number) =>
    unwrap(await B.POST('/v1/birdseyes/{be_id}/plans/{plan_id}:recognize', { params: { path: { be_id: id, plan_id: planId } }, body: { page: page ?? null } })),
  answer: async (id: string, body: S['AnswerIn'], planId?: string) =>
    unwrap(await B.POST('/v1/birdseyes/{be_id}/space/answers', { params: { path: { be_id: id }, query: { plan_id: planId ?? null } }, body })),
  spaceNlEdit: async (id: string, text: string) => unwrap(await B.POST('/v1/birdseyes/{be_id}/space:nl-edit', { ...id_(id), body: { text } })),
  addPhoto: async (id: string, fileId: string, o: { replace?: string; ceiling?: boolean } = {}) =>
    unwrap(await B.POST('/v1/birdseyes/{be_id}/photos', { ...id_(id), body: { file_id: fileId, replace_photo_id: o.replace ?? null, is_ceiling: !!o.ceiling } })),
  photos: async (id: string) => unwrap(await B.GET('/v1/birdseyes/{be_id}/photos', id_(id))),
  acceptPhoto: async (id: string, photoId: string) =>
    unwrap(await B.PATCH('/v1/birdseyes/{be_id}/photos/{photo_id}', { params: { path: { be_id: id, photo_id: photoId } }, body: { accept: true } })),
  recognizePhoto: async (id: string, photoId: string) =>
    unwrap(await B.POST('/v1/birdseyes/{be_id}/photos/{photo_id}:recognize', { params: { path: { be_id: id, photo_id: photoId } } })),
  facts: async (id: string, text: string) => unwrap(await B.POST('/v1/birdseyes/{be_id}/space/facts', { ...id_(id), body: { text } })),
  uploadToken: async (id: string) => unwrap(await B.POST('/v1/birdseyes/{be_id}/upload-tokens', id_(id))),
  tokenInfo: async (token: string) => unwrap(await B.GET('/v1/upload-tokens/{token}', { params: { path: { token } } })),
  tokenPhoto: async (token: string, fileId: string) =>
    unwrap(await B.POST('/v1/upload-tokens/{token}/photos', { params: { path: { token } }, body: { file_id: fileId } })),
  // 제품 · 가구
  search: async (q: string, limit = 5) => unwrap(await B.GET('/v1/product-search', { params: { query: { q, limit } } })),
  products: async (id: string) => unwrap(await B.GET('/v1/birdseyes/{be_id}/products', id_(id))),
  putProducts: async (id: string, items: S['ProductPick'][]) => unwrap(await B.PUT('/v1/birdseyes/{be_id}/products', { ...id_(id), body: { items } })),
  recommend: async (id: string, exclude: string[] = []) => unwrap(await B.POST('/v1/birdseyes/{be_id}/furniture:recommend', { ...id_(id), body: { exclude } })),
  furniture: async (id: string) => unwrap(await B.GET('/v1/birdseyes/{be_id}/furniture', id_(id))),
  putFurniture: async (id: string, body: S['FurniturePut']) => unwrap(await B.PUT('/v1/birdseyes/{be_id}/furniture', { ...id_(id), body })),
  catalog: async () => unwrap(await B.GET('/v1/catalog', {})),
  // 레이아웃
  generate: async (id: string, none = false) => unwrap(await B.POST('/v1/birdseyes/{be_id}/layout:generate', { ...id_(id), body: { none } })),
  layout: async (id: string, version?: number) => unwrap(await B.GET('/v1/birdseyes/{be_id}/layout', { params: { path: { be_id: id }, query: { version: version ?? null } } })),
  layoutNlEdit: async (id: string, text: string, sessionId?: string) =>
    unwrap(await B.POST('/v1/birdseyes/{be_id}/layout:nl-edit', { ...id_(id), body: { text, session_id: sessionId ?? null } })),
  validate: async (id: string, baseVersion: number, ops: Op[]) =>
    unwrap(await B.POST('/v1/birdseyes/{be_id}/layout:validate', { ...id_(id), body: { base_version: baseVersion, ops } })),
  newSession: async (id: string) => unwrap(await B.POST('/v1/birdseyes/{be_id}/layout-sessions', id_(id))),
  session: async (sid: string) => unwrap(await B.GET('/v1/layout-sessions/{session_id}', { params: { path: { session_id: sid } } })),
  sessionOps: async (sid: string, body: { ops?: Op[]; undo?: boolean; redo?: boolean }) =>
    unwrap(await B.POST('/v1/layout-sessions/{session_id}/ops', { params: { path: { session_id: sid } }, body: { ops: body.ops ?? [], undo: !!body.undo, redo: !!body.redo } })),
  warning: async (sid: string, wid: string, body: S['WarningActionIn']) =>
    unwrap(await B.POST('/v1/layout-sessions/{session_id}/warnings/{warning_id}', { params: { path: { session_id: sid, warning_id: wid } }, body })),
  autofix: async (sid: string) => unwrap(await B.POST('/v1/layout-sessions/{session_id}:autofix', { params: { path: { session_id: sid } } })),
  commit: async (sid: string) => unwrap(await B.POST('/v1/layout-sessions/{session_id}:commit', { params: { path: { session_id: sid } } })),
  discard: async (sid: string) => unwrap(await B.POST('/v1/layout-sessions/{session_id}:discard', { params: { path: { session_id: sid } } })),
  // 컷
  cuts: async (id: string) => unwrap(await B.GET('/v1/birdseyes/{be_id}/cuts', id_(id))),
  createCuts: async (id: string, body: S['CutsCreate']) => unwrap(await B.POST('/v1/birdseyes/{be_id}/cuts', { ...id_(id), body })),
  cancelCut: async (cutId: string) => unwrap(await B.POST('/v1/cuts/{cut_id}:cancel', { params: { path: { cut_id: cutId } } })),
  primary: async (cutId: string) => unwrap(await B.PATCH('/v1/cuts/{cut_id}', { params: { path: { cut_id: cutId } }, body: { is_primary: true } })),
  resultEdit: async (id: string, text: string, cutId?: string) =>
    unwrap(await B.POST('/v1/birdseyes/{be_id}/result:edit', { ...id_(id), body: { text, cut_id: cutId ?? null } })),
  // 존
  zonesAuto: async (id: string, cutId?: string) => unwrap(await B.POST('/v1/birdseyes/{be_id}/zones:auto', { ...id_(id), body: { cut_id: cutId ?? null } })),
  zones: async (id: string, cutId?: string) => unwrap(await B.GET('/v1/birdseyes/{be_id}/zones', { params: { path: { be_id: id }, query: { cut_id: cutId ?? null } } })),
  addZone: async (id: string, body: S['ZoneCreate']) => unwrap(await B.POST('/v1/birdseyes/{be_id}/zones', { ...id_(id), body })),
  patchZone: async (zid: string, body: S['ZonePatch']) => unwrap(await B.PATCH('/v1/zones/{zone_id}', { params: { path: { zone_id: zid } }, body })),
  deleteZone: async (zid: string) => { const r = await B.DELETE('/v1/zones/{zone_id}', { params: { path: { zone_id: zid } } }); if (!r.response.ok) unwrap(r as never); },
  renumber: async (id: string, cutId?: string) =>
    unwrap(await B.POST('/v1/birdseyes/{be_id}/zones:renumber-by-path', { params: { path: { be_id: id }, query: { cut_id: cutId ?? null } } })),
  rewrite: async (id: string, text: string, zoneIds?: string[]) =>
    unwrap(await B.POST('/v1/birdseyes/{be_id}/zones:rewrite', { ...id_(id), body: { text, zone_ids: zoneIds ?? null } })),
  // 내보내기
  exportOptions: async (id: string) => unwrap(await B.GET('/v1/birdseyes/{be_id}/export-options', id_(id))),
  quantities: async (id: string) => unwrap(await B.GET('/v1/birdseyes/{be_id}/quantities', id_(id))),
  createExport: async (id: string, body: S['ExportCreate']) => unwrap(await B.POST('/v1/birdseyes/{be_id}/exports', { ...id_(id), body })),
  exportRecord: async (xid: string) => unwrap(await B.GET('/v1/exports/{export_id}', { params: { path: { export_id: xid } } })),
};

export { ApiError, uploadFile };

export const errText = (e: unknown) => (e instanceof ApiError ? e.message : e instanceof Error ? e.message : '요청을 처리하지 못했어요');
export const isCode = (e: unknown, code: string) => e instanceof ApiError && e.code === code;

// ── react-query ─────────────────────────────────────────

export const qk = {
  all: ['be'] as const,
  list: (p: unknown) => ['be', 'list', p] as const,
  one: (id: string) => ['be', id] as const,
  space: (id: string) => ['be', id, 'space'] as const,
  plans: (id: string) => ['be', id, 'plans'] as const,
  photos: (id: string) => ['be', id, 'photos'] as const,
  products: (id: string) => ['be', id, 'products'] as const,
  furniture: (id: string) => ['be', id, 'furniture'] as const,
  layout: (id: string) => ['be', id, 'layout'] as const,
  session: (sid: string) => ['be', 'session', sid] as const,
  cuts: (id: string) => ['be', id, 'cuts'] as const,
  zones: (id: string, cut?: string) => ['be', id, 'zones', cut ?? ''] as const,
  options: (id: string) => ['be', id, 'export-options'] as const,
  quantities: (id: string) => ['be', id, 'quantities'] as const,
  catalog: ['be', 'catalog'] as const,
};

const POLL = 1500;

export const useBe = (id?: string) => useQuery({ queryKey: qk.one(id ?? ''), queryFn: () => be.get(id!), enabled: !!id });
export const useList = (p: Parameters<typeof be.list>[0]) => useQuery({ queryKey: qk.list(p), queryFn: () => be.list(p) });
export const useSpace = (id?: string) => useQuery({
  queryKey: qk.space(id ?? ''), queryFn: () => be.space(id!), enabled: !!id,
  refetchInterval: (q) => (q.state.data?.analyzing ? POLL : false),
});
export const usePlans = (id?: string) => useQuery({
  queryKey: qk.plans(id ?? ''), queryFn: () => be.plans(id!), enabled: !!id,
  refetchInterval: (q) => (q.state.data?.items.some((p) => p.status === 'recognizing') ? POLL : false),
});
/** watch: 휴대폰(QR)으로 올라오는 사진을 받으려고 인식 중이 아니어도 가볍게 다시 읽는다(사용자 단위 SSE 가 jobs 계약에 없음) */
export const usePhotos = (id?: string, watch = false) => useQuery({
  queryKey: qk.photos(id ?? ''), queryFn: () => be.photos(id!), enabled: !!id,
  refetchInterval: (q) => (q.state.data?.items.some((p) => p.status === 'recognizing') ? POLL : watch ? 4000 : false),
});
export const useProducts = (id?: string) => useQuery({ queryKey: qk.products(id ?? ''), queryFn: () => be.products(id!), enabled: !!id });
export const useFurniture = (id?: string) => useQuery({
  queryKey: qk.furniture(id ?? ''), queryFn: () => be.furniture(id!), enabled: !!id,
  refetchInterval: (q) => (q.state.data?.running ? POLL : false),
});
export const useLayout = (id?: string) => useQuery({
  queryKey: qk.layout(id ?? ''), queryFn: () => be.layout(id!), enabled: !!id,
  refetchInterval: (q) => (q.state.data?.running ? POLL : false),
});
export const useCuts = (id?: string, fast = false) => useQuery({
  queryKey: qk.cuts(id ?? ''), queryFn: () => be.cuts(id!), enabled: !!id,
  refetchInterval: (q) => (q.state.data?.some((c) => c.status === 'running' || c.status === 'queued') ? (fast ? 1000 : POLL) : false),
});
export const useZones = (id?: string, cut?: string) => useQuery({
  queryKey: qk.zones(id ?? '', cut), queryFn: () => be.zones(id!, cut), enabled: !!id,
  refetchInterval: (q) => (q.state.data?.running ? POLL : false),
});
export const useCatalog = () => useQuery({ queryKey: qk.catalog, queryFn: be.catalog, staleTime: Infinity });

export function useInvalidate() {
  const qc = useQueryClient();
  return (id?: string) => qc.invalidateQueries({ queryKey: id ? qk.one(id) : qk.all });
}

/** 파일 올리기(files) — 고객 도면 · 사진은 기밀로 */
export async function uploadAll(files: File[]): Promise<Array<{ id: string; name: string; mime: string }>> {
  const out = [];
  for (const f of files) out.push(await uploadFile(f, { confidential: true, purpose: 'birdseye.input' }));
  return out;
}

export const fileUrl = (fid?: string | null) => (fid ? `/api/files/v1/files/${fid}/content` : undefined);
export const thumbUrl = (fid?: string | null, w = 480) => (fid ? `/api/files/v1/files/${fid}/thumbnail?w=${w}` : undefined);
