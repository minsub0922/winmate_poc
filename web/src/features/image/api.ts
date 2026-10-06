/**
 * image 서비스 호출(게이트웨이 `/api/image/v1`, 타입은 contracts/image.json 에서 생성한 `@/api/gen/image`).
 * 제안서 연동(§8 「proposal(웹에서만)」)은 제안서 계약이 아직 없어 fetch 로 부르고, 없으면(404) 빈 목록으로 다룬다.
 */
import { api, ApiError, unwrap, uploadFile } from '@/api/client';
import type { components } from '@/api/gen/image';

export type S = components['schemas'];
export type Work = S['Work'];
export type WorkRow = S['WorkRow'];
export type WorkList = S['WorkList'];
export type Conditions = S['Conditions'];
export type ProductCond = S['ProductCond'];
export type Reference = S['Reference'];
export type ReferenceIn = S['ReferenceIn'];
export type RefSearch = S['RefSearch'];
export type RefSearchItem = S['RefSearchItem'];
export type SitePhoto = S['SitePhoto'];
export type PlacementGroup = S['PlacementGroup'];
export type PlacementResult = S['PlacementResult'];
export type CompositeState = S['CompositeState'];
export type RunDetail = S['RunDetail'];
export type RunAccepted = S['RunAccepted'];
export type Shot = S['Shot'];
export type PolicyIssue = S['PolicyIssue'];
export type QueueList = S['QueueList'];
export type ImageTile = S['ImageTile'];
export type ImageList = S['ImageList'];
export type ImageDetail = S['ImageDetail'];
export type ImageInfo = S['ImageInfo'];
export type Version = S['Version'];
export type EditRegion = S['EditRegion'];
export type RegionCreated = S['RegionCreated'];
export type Detections = S['Detections'];
export type InterpretResult = S['InterpretResult'];
export type ExportOut = S['ExportOut'];
export type ImageRequest = S['ImageRequest'];
export type Capabilities = S['Capabilities'];
export type Badge = S['Badge'];
export type Answer = S['Answer'];

const I = api.image;
const P = (o: Record<string, string>) => ({ params: { path: o } }) as never;

export const img = {
  capabilities: async () => unwrap(await I.GET('/v1/capabilities')),
  // 작업
  works: async (q?: string) => unwrap(await I.GET('/v1/works', { params: { query: { q: q || undefined, limit: 100 } } })),
  work: async (id: string) => unwrap(await I.GET('/v1/works/{work_id}', { params: { path: { work_id: id } } })),
  createWork: async (body: S['WorkCreate']) => unwrap(await I.POST('/v1/works', { body })),
  patchWork: async (id: string, body: S['WorkPatch']) => unwrap(await I.PATCH('/v1/works/{work_id}', { params: { path: { work_id: id } }, body })),
  deleteWork: async (id: string) => { await I.DELETE('/v1/works/{work_id}', { params: { path: { work_id: id } } }); },
  prefill: async (id: string) => unwrap(await I.POST('/v1/works/{work_id}:prefill', { params: { path: { work_id: id } } })),
  addProducts: async (id: string, refs: string[]) =>
    unwrap(await I.POST('/v1/works/{work_id}/products', { params: { path: { work_id: id } }, body: { refs, qty: 1 } })),
  // 참조
  refSearch: async (p: { tab: 'kb' | 'mine' | 'cases'; q?: string; industry?: string | null; style?: 'all' | 'photo' | 'illustration'; work_id?: string; limit?: number }) =>
    unwrap(await I.GET('/v1/reference-search', { params: { query: { ...p, q: p.q || undefined, industry: p.industry || undefined, limit: p.limit ?? 8 } } })),
  addReference: async (id: string, body: ReferenceIn) =>
    unwrap(await I.POST('/v1/works/{work_id}/references', { params: { path: { work_id: id } }, body })),
  setReferences: async (id: string, items: ReferenceIn[], via: 'picker' | 'topbar' | 'drop' | 'upload' = 'picker') =>
    unwrap(await I.PUT('/v1/works/{work_id}/references', { params: { path: { work_id: id } }, body: { items, via } })),
  deleteReference: async (id: string, refId: string) => {
    const r = await I.DELETE('/v1/works/{work_id}/references/{ref_id}', { params: { path: { work_id: id, ref_id: refId } } });
    if (!r.response.ok) unwrap(r as never);
  },
  // 현장 사진
  photos: async (id: string) => unwrap(await I.GET('/v1/works/{work_id}/site-photos', { params: { path: { work_id: id } } })),
  addPhoto: async (id: string, fileId: string) =>
    unwrap(await I.POST('/v1/works/{work_id}/site-photos', { params: { path: { work_id: id } }, body: { file_id: fileId } })),
  recognize: async (id: string, photoId: string) =>
    unwrap(await I.POST('/v1/works/{work_id}/site-photos/{photo_id}:recognize', { params: { path: { work_id: id, photo_id: photoId } } })),
  deletePhoto: async (id: string, photoId: string) => {
    await I.DELETE('/v1/works/{work_id}/site-photos/{photo_id}', { params: { path: { work_id: id, photo_id: photoId } } });
  },
  placements: async (id: string, body: S['PlacementsIn']) =>
    unwrap(await I.PUT('/v1/works/{work_id}/placements', { params: { path: { work_id: id } }, body })),
  // run
  startRun: async (id: string, body: { kind: S['RunCreate']['kind']; count?: 2 | 4 | null; notify?: boolean }) =>
    unwrap(await I.POST('/v1/works/{work_id}/runs', { params: { path: { work_id: id } }, body: { notify: true, ...body } })),
  runs: async (id: string, p: { kind?: string; active?: boolean } = {}) =>
    unwrap(await I.GET('/v1/works/{work_id}/runs', { params: { path: { work_id: id }, query: p } })),
  run: async (runId: string) => unwrap(await I.GET('/v1/runs/{run_id}', { params: { path: { run_id: runId } } })),
  setNotify: async (runId: string, notify: boolean) =>
    unwrap(await I.PATCH('/v1/runs/{run_id}', { params: { path: { run_id: runId } }, body: { notify } })),
  cancelRun: async (runId: string) => unwrap(await I.POST('/v1/runs/{run_id}:cancel', { params: { path: { run_id: runId } } })),
  cancelShot: async (runId: string, imageId: string) =>
    unwrap(await I.POST('/v1/runs/{run_id}/shots/{image_id}:cancel', { params: { path: { run_id: runId, image_id: imageId } } })),
  answer: async (runId: string, body: { answers?: Answer[]; skip_held?: boolean; all_recommended?: boolean }) =>
    unwrap(await I.POST('/v1/runs/{run_id}/answers', { params: { path: { run_id: runId } }, body: { answers: [], skip_held: false, all_recommended: false, ...body } })),
  alternative: async (runId: string, text: string) =>
    unwrap(await I.POST('/v1/runs/{run_id}/alternatives', { params: { path: { run_id: runId } }, body: { text } })),
  queue: async () => unwrap(await I.GET('/v1/queue')),
  // 시안
  images: async (p: { kind?: string; customer?: string; aspect?: string; in_proposal?: boolean; q?: string; work_id?: string; saved?: boolean; running?: boolean; limit?: number }) =>
    unwrap(await I.GET('/v1/images', { params: { query: { ...p, q: p.q || undefined, limit: p.limit ?? 60 } } })),
  image: async (imageId: string) => unwrap(await I.GET('/v1/images/{image_id}', { params: { path: { image_id: imageId } } })),
  save: async (imageId: string) => unwrap(await I.POST('/v1/images/{image_id}:save', { params: { path: { image_id: imageId } } })),
  versions: async (imageId: string) => unwrap(await I.GET('/v1/images/{image_id}/versions', { params: { path: { image_id: imageId } } })),
  restore: async (imageId: string, n: number) =>
    unwrap(await I.POST('/v1/images/{image_id}/versions/{n}/restore', P({ image_id: imageId, n: String(n) }))),
  detections: async (imageId: string, body: S['DetectIn'] = {}) =>
    unwrap(await I.POST('/v1/images/{image_id}/detections', { params: { path: { image_id: imageId } }, body })),
  regions: async (imageId: string) => unwrap(await I.GET('/v1/images/{image_id}/regions', { params: { path: { image_id: imageId } } })),
  addRegion: async (imageId: string, body: Partial<S['RegionIn']>) =>
    unwrap(await I.POST('/v1/images/{image_id}/regions', { params: { path: { image_id: imageId } }, body: { shape: 'rect', ...body } })),
  patchRegion: async (imageId: string, regionId: string, body: S['RegionPatch']) =>
    unwrap(await I.PATCH('/v1/images/{image_id}/regions/{region_id}', { params: { path: { image_id: imageId, region_id: regionId } }, body })),
  deleteRegion: async (imageId: string, regionId: string) => {
    await I.DELETE('/v1/images/{image_id}/regions/{region_id}', { params: { path: { image_id: imageId, region_id: regionId } } });
  },
  revertRegion: async (imageId: string, regionId: string) =>
    unwrap(await I.POST('/v1/images/{image_id}/regions/{region_id}:revert', { params: { path: { image_id: imageId, region_id: regionId } } })),
  edit: async (imageId: string, body: Partial<S['EditIn']>) =>
    unwrap(await I.POST('/v1/images/{image_id}/edits', { params: { path: { image_id: imageId } }, body: { mode: 'region', protect_products: true, ...body } })),
  adjust: async (imageId: string, body: S['AdjustIn']) =>
    unwrap(await I.POST('/v1/images/{image_id}/adjust', { params: { path: { image_id: imageId } }, body })),
  variants: async (imageId: string, body: S['VariantsIn']) =>
    unwrap(await I.POST('/v1/images/{image_id}/variants', { params: { path: { image_id: imageId } }, body })),
  renditions: async (imageId: string, body: S['RenditionsIn']) =>
    unwrap(await I.POST('/v1/images/{image_id}/renditions', { params: { path: { image_id: imageId } }, body })),
  interpret: async (imageId: string, body: S['InterpretIn']) =>
    unwrap(await I.POST('/v1/images/{image_id}:interpret', { params: { path: { image_id: imageId } }, body })),
  caption: async (imageId: string) => unwrap(await I.POST('/v1/images/{image_id}/caption', { params: { path: { image_id: imageId } } })),
  filename: async (imageId: string, body: S['FilenameIn']) =>
    unwrap(await I.POST('/v1/images/{image_id}/filename', { params: { path: { image_id: imageId } }, body })),
  info: async (imageId: string) => unwrap(await I.GET('/v1/images/{image_id}/info', { params: { path: { image_id: imageId } } })),
  // 내보내기
  exportImage: async (imageId: string, body: S['ExportIn']) =>
    unwrap(await I.POST('/v1/images/{image_id}/exports', { params: { path: { image_id: imageId } }, body })),
  exportStatus: async (exportId: string) => unwrap(await I.GET('/v1/exports/{export_id}', { params: { path: { export_id: exportId } } })),
  bulkExport: async (versionIds: string[]) => unwrap(await I.POST('/v1/images:bulk-export', { body: { version_ids: versionIds, format: 'png', ai_label: true } })),
  // 다른 기능의 요청
  requests: async () => unwrap(await I.GET('/v1/requests', { params: { query: { status: 'open,in_progress' } } })),
  startRequest: async (requestId: string) =>
    unwrap(await I.POST('/v1/requests/{request_id}:start', { params: { path: { request_id: requestId } } })),
  fulfillRequest: async (requestId: string, versionId: string) =>
    unwrap(await I.POST('/v1/requests/{request_id}:fulfill', { params: { path: { request_id: requestId } }, body: { version_id: versionId } })),
};

export { ApiError, uploadFile };

export const errMessage = (e: unknown, fallback = '잠시 뒤 다시 시도해 주세요') =>
  (e instanceof ApiError ? e.message : e instanceof Error ? e.message : '') || fallback;

// ── 제안서(웹에서만, §8) — 계약에 아직 없다(docs/requests/proposal.md). 없으면 404 → 빈 목록 ──
export interface ProposalRow { id: string; title: string; meta?: string; short_title?: string; project_id?: string | null; updated_at?: string }
export interface ImageSlotSheet { sheet_id: string; name: string; section?: string; recommended?: boolean; slots?: number; preview_url?: string | null }
export interface ImageSlots { sheets: ImageSlotSheet[] }

async function proposalFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`/api/proposal/v1${path}`, { credentials: 'same-origin', headers: { 'Content-Type': 'application/json', Accept: 'application/json' }, ...init });
  const text = await r.text();
  let body: unknown = null;
  try { body = text ? JSON.parse(text) : null; } catch { body = null; }
  if (!r.ok) {
    const e = (body as { error?: { code?: string; message?: string } } | null)?.error;
    throw new ApiError(r.status, e?.code ?? 'ERROR', e?.message ?? r.statusText);
  }
  return body as T;
}

export const proposal = {
  /** 진행 중 제안서(작성 중 · 검토 중). 계약이 없으면 빈 목록 */
  list: async (): Promise<{ items: ProposalRow[]; available: boolean }> => {
    try {
      const res = await proposalFetch<{ items?: ProposalRow[] }>('/proposals?tab=draft,review&limit=20');
      return { items: res.items ?? [], available: true };
    } catch (e) {
      if (e instanceof ApiError && (e.status === 404 || e.status === 405)) return { items: [], available: false };
      throw e;
    }
  },
  slots: async (proposalId: string, versionId: string): Promise<ImageSlots> => {
    try {
      const res = await proposalFetch<{ sheets?: ImageSlotSheet[]; items?: ImageSlotSheet[] }>(
        `/proposals/${encodeURIComponent(proposalId)}/image-slots?image_version=${encodeURIComponent(versionId)}`);
      return { sheets: res.sheets ?? res.items ?? [] };
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) return { sheets: [] };
      throw e;
    }
  },
  importImage: (proposalId: string, body: { source: { service: 'image'; version_id: string; image_id: string }; target: { sheet_id: string | null; mode: 'replace_slot' | 'new_sheet' }; caption?: string | null }) =>
    proposalFetch<Record<string, unknown>>(`/proposals/${encodeURIComponent(proposalId)}/imports`, { method: 'POST', body: JSON.stringify(body) }),
};

/** 「팀에 공유」 — workspace 공유 링크 */
export async function createShareLink(target: string, routePath: string, title: string): Promise<string> {
  const res = unwrap(await api.workspace.POST('/v1/share-links', { body: { target, route: routePath, title, expires_days: 30 } }));
  return (res as { url: string }).url;
}
