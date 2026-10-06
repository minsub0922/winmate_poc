/**
 * scenario 서비스 호출(게이트웨이 `/api/scenario/v1`, 타입은 contracts/scenario.json 에서 생성한 `@/api/gen/scenario`).
 * 제안서 연동(§8 「proposal(웹에서만)」)은 제안서 계약(`api.proposal`)으로 부른다.
 */
import { api, ApiError, unwrap } from '@/api/client';
import type { components } from '@/api/gen/scenario';

export type S = components['schemas'];
export type Scenario = S['Scenario'];
export type ScenarioRow = S['ScenarioRow'];
export type ScenarioList = S['ScenarioList'];
export type Timeline = S['Timeline'];
export type TimelineOp = S['TimelineOp'];
export type Slot = S['Slot'];
export type Role = S['Role'];
export type Beat = S['Beat'];
export type TimelineScene = S['TimelineScene'];
export type Recommendations = S['Recommendations'];
export type Recommendation = S['Recommendation'];
export type SceneOut = S['SceneOut'];
export type SceneProduct = S['SceneProduct'];
export type SceneSolution = S['SceneSolution'];
export type GenerationView = S['GenerationView'];
export type SheetPlan = S['SheetPlan'];
export type Sheet = S['Sheet'];
export type IndustryTemplate = S['IndustryTemplate'];
export type BirdseyePreview = S['BirdseyePreview'];
export type BirdseyeOption = S['BirdseyeOption'];
export type ZoneRow = S['ZoneRow'];
export type ProductPick = S['ProductPick'];
export type RelatedProduct = S['RelatedProduct'];
export type SearchHit = S['SearchHit'];
export type ProductItem = S['ProductItem'];
export type ExportOut = S['ExportOut'];
export type ActionItem = S['ActionItem'];
export type Aerial = S['Aerial'];

const C = api.scenario;
const sc = (sc_id: string) => ({ params: { path: { sc_id } } });
const scn = (scene_id: string) => ({ params: { path: { scene_id } } });

/** 204 응답(본문 없음) — 오류만 던진다 */
function ok204(r: { error?: unknown; response: Response }) {
  if (!r.response.ok) unwrap(r as never);
}

export const scApi = {
  // 목록 · 만들기
  list: async (q: { status?: 'all' | 'draft' | 'generating' | 'done' | 'failed'; start_mode?: 'all' | 'blank' | 'template' | 'birdseye'; q?: string;
    sort?: 'updated' | 'created' | 'title'; limit?: number; cursor?: string } = {}) =>
    unwrap(await C.GET('/v1/scenarios', { params: { query: { ...q, q: q.q || undefined, cursor: q.cursor || undefined, limit: q.limit ?? 50 } } })),
  dismissAlert: async (id: string) => ok204(await C.POST('/v1/scenarios/{sc_id}/alerts:dismiss', sc(id))),
  create: async (body: S['CreateScenario']) => unwrap(await C.POST('/v1/scenarios', { body })),
  fromTemplate: async (body: S['FromTemplate']) => unwrap(await C.POST('/v1/scenarios:from-template', { body })),
  fromBirdseye: async (body: S['FromBirdseye']) => unwrap(await C.POST('/v1/scenarios:from-birdseye', { body })),
  get: async (id: string) => unwrap(await C.GET('/v1/scenarios/{sc_id}', sc(id))),
  patch: async (id: string, body: S['PatchScenario']) => unwrap(await C.PATCH('/v1/scenarios/{sc_id}', { ...sc(id), body })),
  remove: async (id: string) => ok204(await C.DELETE('/v1/scenarios/{sc_id}', sc(id))),
  clone: async (id: string) => unwrap(await C.POST('/v1/scenarios/{sc_id}:clone', sc(id))),
  save: async (id: string) => unwrap(await C.POST('/v1/scenarios/{sc_id}:save', sc(id))),
  resync: async (id: string, apply: boolean) => unwrap(await C.POST('/v1/scenarios/{sc_id}/birdseye:resync', { ...sc(id), body: { apply } })),
  // 카탈로그
  industries: async (projectId?: string | null) => unwrap(await C.GET('/v1/industries', { params: { query: { project_id: projectId || undefined } } })),
  skeletons: async (industry?: string | null) => unwrap(await C.GET('/v1/skeletons', { params: { query: { industry: industry || undefined } } })),
  actions: async (solutionIds: string[]) =>
    unwrap(await C.GET('/v1/solution-actions', { params: { query: { solution_ids: solutionIds.join(',') || undefined } } })),
  birdseyeOptions: async () => unwrap(await C.GET('/v1/birdseye-options')),
  birdseyePreview: async (beId: string, scenarioId?: string | null) =>
    unwrap(await C.GET('/v1/birdseye-options/{be_id}', { params: { path: { be_id: beId }, query: { scenario_id: scenarioId || undefined } } })),
  importItem: async (id: string, body: S['ImportRequest']) => unwrap(await C.POST('/v1/scenarios/{sc_id}/imports', { ...sc(id), body })),
  // 입력 · 타임라인
  parse: async (id: string, raw_text: string, characters: string[]) =>
    unwrap(await C.POST('/v1/scenarios/{sc_id}/input:parse', { ...sc(id), body: { raw_text, characters } })),
  extract: async (id: string, raw_text: string, exclude: string[], signal?: AbortSignal) =>
    unwrap(await C.POST('/v1/scenarios/{sc_id}/characters:extract', { ...sc(id), body: { raw_text, exclude }, signal })),
  timeline: async (id: string) => unwrap(await C.GET('/v1/scenarios/{sc_id}/timeline', sc(id))),
  ops: async (id: string, ops: TimelineOp[]) => unwrap(await C.POST('/v1/scenarios/{sc_id}/timeline/ops', { ...sc(id), body: { ops, undo: false, redo: false } })),
  undo: async (id: string) => unwrap(await C.POST('/v1/scenarios/{sc_id}/timeline/ops', { ...sc(id), body: { ops: [], undo: true, redo: false } })),
  redo: async (id: string) => unwrap(await C.POST('/v1/scenarios/{sc_id}/timeline/ops', { ...sc(id), body: { ops: [], undo: false, redo: true } })),
  nlEdit: async (id: string, text: string) => unwrap(await C.POST('/v1/scenarios/{sc_id}/timeline:nl-edit', { ...sc(id), body: { text } })),
  patchRole: async (id: string, roleId: string, body: S['PatchRole']) =>
    unwrap(await C.PATCH('/v1/scenarios/{sc_id}/roles/{role_id}', { params: { path: { sc_id: id, role_id: roleId } }, body })),
  timelineText: async (id: string) => unwrap(await C.GET('/v1/scenarios/{sc_id}/timeline:text', sc(id))),
  // 솔루션 · 제품
  putSolutions: async (id: string, ids: string[]) =>
    unwrap(await C.PUT('/v1/scenarios/{sc_id}/solutions', { ...sc(id), body: { items: ids.map((solution_id) => ({ solution_id })) } })),
  putProducts: async (id: string, items: ProductItem[]) => unwrap(await C.PUT('/v1/scenarios/{sc_id}/products', { ...sc(id), body: { items } })),
  solutionSearch: async (q: string, signal?: AbortSignal) => unwrap(await C.GET('/v1/solution-search', { params: { query: { q, limit: 8 } }, signal })),
  productSearch: async (q: string, signal?: AbortSignal) => unwrap(await C.GET('/v1/product-search', { params: { query: { q, limit: 6 } }, signal })),
  routeGenerate: async (id: string) => unwrap(await C.POST('/v1/scenarios/{sc_id}:route-generate', sc(id))),
  computeRecs: async (id: string) => unwrap(await C.POST('/v1/scenarios/{sc_id}/recommendations:compute', sc(id))),
  recs: async (id: string) => unwrap(await C.GET('/v1/scenarios/{sc_id}/recommendations', sc(id))),
  setRec: async (id: string, sceneId: string, applied: boolean) =>
    unwrap(await C.PATCH('/v1/scenarios/{sc_id}/recommendations/{scene_id}', { params: { path: { sc_id: id, scene_id: sceneId } }, body: { applied } })),
  applyAllRecs: async (id: string) => unwrap(await C.POST('/v1/scenarios/{sc_id}/recommendations:apply-all', sc(id))),
  commitRecs: async (id: string, mode: 'apply' | 'products_only') =>
    unwrap(await C.POST('/v1/scenarios/{sc_id}/recommendations:commit', { ...sc(id), body: { mode } })),
  // 생성
  generate: async (id: string, scope: 'all' | 'unlocked' = 'all') => unwrap(await C.POST('/v1/scenarios/{sc_id}/generate', { ...sc(id), body: { scope } })),
  resume: async (id: string, jobId: string) => unwrap(await C.POST('/v1/scenarios/{sc_id}/generate:resume', { ...sc(id), body: { job_id: jobId } })),
  cancel: async (id: string) => unwrap(await C.POST('/v1/scenarios/{sc_id}/generate:cancel', sc(id))),
  generation: async (id: string) => unwrap(await C.GET('/v1/scenarios/{sc_id}/generation', sc(id))),
  // 장면
  scenes: async (id: string) => unwrap(await C.GET('/v1/scenarios/{sc_id}/scenes', sc(id))),
  addScene: async (id: string, afterSceneId?: string | null) =>
    unwrap(await C.POST('/v1/scenarios/{sc_id}/scenes', { ...sc(id), body: { after_scene_id: afterSceneId ?? null } })),
  scene: async (sceneId: string) => unwrap(await C.GET('/v1/scenes/{scene_id}', scn(sceneId))),
  patchScene: async (sceneId: string, body: S['PatchScene']) => unwrap(await C.PATCH('/v1/scenes/{scene_id}', { ...scn(sceneId), body })),
  deleteScene: async (sceneId: string) => ok204(await C.DELETE('/v1/scenes/{scene_id}', scn(sceneId))),
  rewrite: async (sceneId: string, body: S['RewriteRequest']) => unwrap(await C.POST('/v1/scenes/{scene_id}:rewrite', { ...scn(sceneId), body })),
  sceneVersions: async (sceneId: string) => unwrap(await C.GET('/v1/scenes/{scene_id}/versions', scn(sceneId))),
  restoreScene: async (sceneId: string, n: number) =>
    unwrap(await C.POST('/v1/scenes/{scene_id}/versions/{n}/restore', { params: { path: { scene_id: sceneId, n } } })),
  edit: async (id: string, text: string) => unwrap(await C.POST('/v1/scenarios/{sc_id}:edit', { ...sc(id), body: { text } })),
  shorten: async (id: string) => unwrap(await C.POST('/v1/scenarios/{sc_id}:shorten', sc(id))),
  // 이미지
  imageRequest: async (sceneId: string) => unwrap(await C.POST('/v1/scenes/{scene_id}/image-request', scn(sceneId))),
  attachImage: async (sceneId: string, body: S['AttachImage']) => unwrap(await C.POST('/v1/scenes/{scene_id}/image:attach', { ...scn(sceneId), body })),
  syncImages: async (id: string) => unwrap(await C.POST('/v1/scenarios/{sc_id}/images:sync', sc(id))),
  generateMissing: async (id: string) => unwrap(await C.POST('/v1/scenarios/{sc_id}/images:generate-missing', sc(id))),
  imageReturn: async (requestId: string, versionId: string) =>
    unwrap(await C.POST('/v1/image-returns', { body: { request_id: requestId, image_version_id: versionId } })),
  imagePrefill: async (sceneId: string) => unwrap(await C.GET('/v1/scenes/{scene_id}/image-prefill', scn(sceneId))),
  // 보내기
  sheetPlan: async (id: string) => unwrap(await C.GET('/v1/scenarios/{sc_id}/sheet-plan', sc(id))),
  exportStart: async (id: string, kind: 'pptx' | 'pdf' | 'docx' | 'zip') => unwrap(await C.POST('/v1/scenarios/{sc_id}/exports', { ...sc(id), body: { kind } })),
  exportGet: async (id: string, exportId: string) =>
    unwrap(await C.GET('/v1/scenarios/{sc_id}/exports/{export_id}', { params: { path: { sc_id: id, export_id: exportId } } })),
  share: async (id: string) => unwrap(await C.POST('/v1/scenarios/{sc_id}/share', sc(id))),
};

export { ApiError };

export const errMessage = (e: unknown, fallback = '잠시 뒤 다시 시도해 주세요') =>
  (e instanceof ApiError ? e.message : e instanceof Error ? e.message : '') || fallback;

// ── 제안서(웹에서만, §8 · 10-proposal §8.15 N1) ──
export interface ProposalPick { id: string; title: string; status: string; status_label: string; project_id?: string | null; updated_at?: string }

export const proposal = {
  /** 진행 중 제안서(작성 중 · 검토 중). 제안서 서비스가 꺼져 있으면 빈 목록 */
  list: async (projectId?: string | null): Promise<{ items: ProposalPick[]; available: boolean }> => {
    try {
      const r = unwrap(await api.proposal.GET('/v1/proposals', { params: { query: { tab: 'draft,review', sort: 'updated_desc', limit: 30 } } }));
      const items = (r.items ?? []).map((p) => ({
        id: p.id, title: p.title, status: p.status, status_label: p.status_label, project_id: p.project_id ?? null, updated_at: p.updated_at ?? undefined,
      }));
      // 기본 = 같은 프로젝트의 진행 중 제안서 중 최근 것(§4.12) — 같은 프로젝트를 앞으로
      if (projectId) items.sort((a, b) => Number(b.project_id === projectId) - Number(a.project_id === projectId));
      return { items, available: true };
    } catch (e) {
      if (e instanceof ApiError && [404, 405, 502, 503].includes(e.status)) return { items: [], available: false };
      throw e;
    }
  },
  importScenario: async (proposalId: string, s: { id: string; version: number; title: string }, includeKeys: string[]) =>
    unwrap(await api.proposal.POST('/v1/proposals/{proposal_id}/imports', {
      params: { path: { proposal_id: proposalId } },
      body: { section_key: 'spaceScenario', via: 'handoff', source: { feature: 'scenario', ref_id: s.id, version: s.version, title: s.title }, include_keys: includeKeys },
    })),
};
