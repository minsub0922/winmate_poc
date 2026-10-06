/**
 * kb 서비스 호출(게이트웨이 `/api/kb/v1`, 00-shell §7.2)과 react-query 훅. 기능 화면도 쓸 수 있다(`@/shell`).
 */
import { keepPreviousData, useInfiniteQuery, useQuery } from '@tanstack/react-query';
import { ApiError } from '@/api/client';
import type {
  GeneratedImage, KbCaseSearch, KbCategory, KbFamily, KbImageList, KbImageMeta, KbImageSearch, KbMeta, KbModelCases, KbModelDetail, KbModelList, KbSolution,
  KbSolutionCases, KbSolutionDetail, KbSolutionImages, KbVertical, ProductSearchItem,
} from './kbTypes';

type Params = Record<string, string | number | boolean | null | undefined>;

function qs(params?: Params) {
  if (!params) return '';
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== null && v !== '') p.set(k, String(v));
  const s = p.toString();
  return s ? `?${s}` : '';
}

export async function getJson<T>(url: string, signal?: AbortSignal): Promise<T> {
  const r = await fetch(url, { credentials: 'same-origin', signal, headers: { Accept: 'application/json' } });
  const text = await r.text();
  let body: unknown = null;
  try { body = text ? JSON.parse(text) : null; } catch { body = null; }
  if (!r.ok) {
    const e = (body as { error?: { code?: string; message?: string; details?: Record<string, unknown> } } | null)?.error;
    throw new ApiError(r.status, e?.code ?? 'ERROR', e?.message ?? r.statusText, e?.details ?? {});
  }
  return body as T;
}

export const kbGet = <T>(path: string, params?: Params, signal?: AbortSignal) => getJson<T>(`/api/kb/v1${path}${qs(params)}`, signal);
const enc = encodeURIComponent;

export const kb = {
  meta: (s?: AbortSignal) => kbGet<KbMeta>('/meta', undefined, s),
  categories: (parentId?: string | null, s?: AbortSignal) => kbGet<{ items: KbCategory[] }>('/categories', { parent_id: parentId ?? undefined, limit: 100 }, s),
  families: (categoryId: string, s?: AbortSignal) => kbGet<{ items: KbFamily[]; next_cursor?: string | null }>('/families', { category_id: categoryId, limit: 100 }, s),
  models: (p: { family_id?: string; category_id?: string; q?: string; limit?: number; cursor?: string }, s?: AbortSignal) => kbGet<KbModelList>('/models', p, s),
  productSearch: (q: string, limit = 5, kinds = 'model,family', s?: AbortSignal) => kbGet<{ items: ProductSearchItem[] }>('/products/search', { q, limit, kinds }, s),
  model: (code: string, s?: AbortSignal) => kbGet<KbModelDetail>(`/models/${enc(code)}`, undefined, s),
  modelImages: (code: string, s?: AbortSignal) => kbGet<KbImageList>(`/models/${enc(code)}/images`, undefined, s),
  modelCases: (code: string, match?: string, s?: AbortSignal) => kbGet<KbModelCases>(`/models/${enc(code)}/cases`, { match }, s),
  solutions: (p: { q?: string; industry?: string }, s?: AbortSignal) => kbGet<{ items: KbSolution[] }>('/solutions', p, s),
  solution: (id: string, s?: AbortSignal) => kbGet<KbSolutionDetail>(`/solutions/${enc(id)}`, undefined, s),
  solutionImages: (id: string, s?: AbortSignal) => kbGet<KbSolutionImages>(`/solutions/${enc(id)}/images`, undefined, s),
  solutionCases: (id: string, s?: AbortSignal) => kbGet<KbSolutionCases>(`/solutions/${enc(id)}/cases`, undefined, s),
  imageSearch: (p: { q: string; source?: string; verified_only?: boolean; limit?: number; cursor?: string }, s?: AbortSignal) => kbGet<KbImageSearch>('/images/search', p, s),
  image: (id: string, s?: AbortSignal) => kbGet<KbImageMeta>(`/images/${enc(id)}`, undefined, s),
  /** `target` 은 `family:fam_…` · `model:mdl_…` · `category:cat_…` · `solution:<id>` (kb: 접두사 없이) · `vertical_from` 은 vertical_id 를 누가 정했나(user · task) */
  caseSearch: (p: { q?: string; vertical_id?: string; vertical_from?: 'user' | 'task'; target?: string; period?: string; region?: string; infer_vertical?: boolean; limit?: number; cursor?: string }, s?: AbortSignal) =>
    kbGet<KbCaseSearch>('/cases/search', p, s),
  verticals: (s?: AbortSignal) => kbGet<{ items: KbVertical[] }>('/verticals', { scheme: 'kr_site' }, s),
};

const LONG = 5 * 60_000;

export const useKbMeta = () => useQuery({ queryKey: ['kb', 'meta'], queryFn: ({ signal }) => kb.meta(signal), staleTime: LONG, retry: 0 });
export const useCategories = (parentId?: string | null, enabled = true) =>
  useQuery({ queryKey: ['kb', 'categories', parentId ?? null], queryFn: ({ signal }) => kb.categories(parentId, signal), staleTime: LONG, enabled, retry: 1 });
export const useFamilies = (categoryId?: string | null, enabled = true) =>
  useQuery({ queryKey: ['kb', 'families', categoryId], queryFn: ({ signal }) => kb.families(categoryId!, signal), staleTime: LONG, enabled: enabled && !!categoryId, retry: 1 });
export const useModels = (p: { family_id?: string; category_id?: string; q?: string }, enabled = true) =>
  useQuery({ queryKey: ['kb', 'models', p], queryFn: ({ signal }) => kb.models({ ...p, limit: 100 }, signal), staleTime: LONG, enabled, retry: 0, placeholderData: keepPreviousData });
export const useModel = (code?: string | null) =>
  useQuery({ queryKey: ['kb', 'model', code], queryFn: ({ signal }) => kb.model(code!, signal), staleTime: LONG, enabled: !!code, retry: 0 });
export const useModelImages = (code?: string | null, enabled = true) =>
  useQuery({ queryKey: ['kb', 'model', code, 'images'], queryFn: ({ signal }) => kb.modelImages(code!, signal), staleTime: LONG, enabled: !!code && enabled, retry: 0 });
export const useModelCases = (code?: string | null, match?: string, enabled = true) =>
  useQuery({ queryKey: ['kb', 'model', code, 'cases', match ?? null], queryFn: ({ signal }) => kb.modelCases(code!, match, signal), staleTime: LONG, enabled: !!code && enabled, retry: 0, placeholderData: keepPreviousData });
export const useSolutions = (p: { q?: string; industry?: string }) =>
  useQuery({ queryKey: ['kb', 'solutions', p], queryFn: ({ signal }) => kb.solutions(p, signal), staleTime: LONG, retry: 0, placeholderData: keepPreviousData });
export const useSolution = (id?: string | null) =>
  useQuery({ queryKey: ['kb', 'solution', id], queryFn: ({ signal }) => kb.solution(id!, signal), staleTime: LONG, enabled: !!id, retry: 0 });
export const useSolutionImages = (id?: string | null, enabled = true) =>
  useQuery({ queryKey: ['kb', 'solution', id, 'images'], queryFn: ({ signal }) => kb.solutionImages(id!, signal), staleTime: LONG, enabled: !!id && enabled, retry: 0 });
export const useSolutionCases = (id?: string | null, enabled = true) =>
  useQuery({ queryKey: ['kb', 'solution', id, 'cases'], queryFn: ({ signal }) => kb.solutionCases(id!, signal), staleTime: LONG, enabled: !!id && enabled, retry: 0 });
export const useImageSearch = (p: { q: string; source: string; verified_only: boolean }, enabled = true) =>
  useQuery({ queryKey: ['kb', 'images', p], queryFn: ({ signal }) => kb.imageSearch({ ...p, limit: 24 }, signal), staleTime: LONG, enabled: enabled && !!p.q, retry: 0, placeholderData: keepPreviousData });
/** 이미지 검색 — 쪽 단위(`더 보기`). `data.pages[0].counts` 가 탭 숫자 */
export const useImageSearchPages = (p: { q: string; source: string; verified_only: boolean }, enabled = true) =>
  useInfiniteQuery({
    queryKey: ['kb', 'images', 'pages', p],
    queryFn: ({ signal, pageParam }) => kb.imageSearch({ ...p, limit: 24, cursor: pageParam ?? undefined }, signal),
    initialPageParam: null as string | null,
    getNextPageParam: (last) => last.next_cursor ?? null,
    staleTime: LONG, enabled: enabled && !!p.q, retry: 0, placeholderData: keepPreviousData,
  });
export const useImageMeta = (id?: string | null) =>
  useQuery({ queryKey: ['kb', 'image', id], queryFn: ({ signal }) => kb.image(id!, signal), staleTime: LONG, enabled: !!id, retry: 0 });
export const useCaseSearch = (p: { q?: string; vertical_id?: string; vertical_from?: 'user' | 'task'; target?: string; period?: string; infer_vertical?: boolean }, enabled = true) =>
  useQuery({ queryKey: ['kb', 'cases', p], queryFn: ({ signal }) => kb.caseSearch({ ...p, limit: 10 }, signal), staleTime: LONG, enabled, retry: 0, placeholderData: keepPreviousData });
/** 사례 검색 — 쪽 단위(`더 보기`). `data.pages[0]` 에 corpus · applied · total */
export const useCaseSearchPages = (p: { q?: string; vertical_id?: string; vertical_from?: 'user' | 'task'; target?: string; period?: string; infer_vertical?: boolean }, enabled = true) =>
  useInfiniteQuery({
    queryKey: ['kb', 'cases', 'pages', p],
    queryFn: ({ signal, pageParam }) => kb.caseSearch({ ...p, limit: 10, cursor: pageParam ?? undefined }, signal),
    initialPageParam: null as string | null,
    getNextPageParam: (last) => last.next_cursor ?? null,
    staleTime: LONG, enabled, retry: 0, placeholderData: keepPreviousData,
  });
export const useVerticals = (enabled = true) =>
  useQuery({ queryKey: ['kb', 'verticals'], queryFn: ({ signal }) => kb.verticals(signal), staleTime: LONG, enabled, retry: 0 });

/** image 서비스 `내 생성 이미지`(§7.4) — 계약이 아직 없으면 빈 목록 */
export const useMyImages = (q: string, enabled = true) =>
  useQuery({
    queryKey: ['image', 'mine', q],
    queryFn: async ({ signal }) => {
      try { return await getJson<{ items: GeneratedImage[] }>(`/api/image/v1/images${qs({ owner: 'me', q, limit: 24 })}`, signal); }
      catch { return { items: [] as GeneratedImage[] }; }
    },
    staleTime: 60_000, enabled: enabled && !!q, retry: 0,
  });

/** image 서비스 `내 생성 이미지` 정보 행(`GET /api/image/v1/images/{id}/info` → `{rows: [{k, v, href?}]}` — 출처 · 원본 · 저장본 · 생성 · 사용 조건 · 사용 이력) */
export const useMyImageInfo = (id: string | null | undefined) =>
  useQuery({
    queryKey: ['image', 'info', id],
    queryFn: ({ signal }) => getJson<{ image_id: string; title?: string; rows: Array<{ k: string; v: string; href?: string | null }> }>(`/api/image/v1/images/${encodeURIComponent(id!)}/info`, signal),
    enabled: !!id, staleTime: 60_000, retry: 0,
  });

// ── 참조 문자열(§7.1) ──────────────────────────────────
export const ref = {
  model: (id: string) => `kb:model:${id}`,
  family: (id: string) => `kb:family:${id}`,
  solution: (id: string) => `kb:solution:${id}`,
  image: (id: string) => `kb:image:${id}`,
  case: (id: string) => `kb:case:${id}`,
  workItem: (id: string) => `ws:item:${id}`,
  generated: (id: string) => `img:image:${id}`,
};
export function parseRef(r: string): { ns: string; kind: string; id: string } {
  const [ns, kind, ...rest] = r.split(':');
  return { ns: ns ?? '', kind: kind ?? '', id: rest.join(':') };
}

// ── 표시 규칙 ──────────────────────────────────────────
/** 모델 표시명(G-PRD-1: 없으면 모델코드) */
export const modelName = (m: { display_name?: string | null; model_code: string }) => m.display_name || m.model_code;
/** `QMC Series` → `QMC` · 코드가 아니면 null */
export function seriesCode(seriesLabel?: string | null) {
  const m = /^(.+?) Series$/.exec(seriesLabel ?? '');
  return m ? m[1] : null;
}
/** 행 썸네일 alt: `{시리즈} 정면 ({대표 모델 표시명} 공식 제품 이미지)` — `QMC 시리즈 정면 (QM55C 공식 제품 이미지)` */
export function seriesFrontAlt(family: { name: string; series_label?: string | null }, repName: string) {
  const code = seriesCode(family.series_label);
  const series = code ? `${code} 시리즈` : family.name;
  return `${series} 정면 (${repName} 공식 제품 이미지)`;
}
/** kind 배지 글 */
export const imageKindLabel = (kind?: string | null) =>
  kind === 'product' ? '제품' : kind === 'case' ? '도입사례' : kind === 'solution' ? '솔루션' : kind === 'industry' ? '업종' : kind === 'generated' ? '생성' : '이미지';
/** 사용 조건(§9.6-6) — 팝오버 */
export const usageNotePopover = (rights?: string | null) =>
  rights === 'customer_case' ? '“도입사례 사진” 표기 필수 · 대외 사용 범위 확인 필요' : '대외 사용 범위 확인 필요';
/** 사용 조건(§9.6-6) — 시트 */
export const usageNoteSheet = (rights?: string | null) =>
  rights === 'customer_case' ? '“도입사례 사진” 표기 필수 · 대외 사용 범위 확인 필요' : rights === 'official' ? '삼성전자 저작물 · 대외 사용 범위 확인 필요' : '대외 사용 범위 확인 필요';
/** 쓸모없는 대체 텍스트(`img` 등 수집 원문의 빈 alt) */
const JUNK_ALT = /^\s*(img|image|photo|picture|이미지|사진)?\s*$/i;
/** 이미지 대체 텍스트: alt → 제목 → 대신할 말. `img` 같은 빈 alt 는 건너뛴다 */
export function imageAlt(im: { alt?: string | null; title?: string | null } | null | undefined, fallback = '') {
  const a = im?.alt && !JUNK_ALT.test(im.alt) ? im.alt : null;
  const t = im?.title && !JUNK_ALT.test(im.title) ? im.title.trim() : null;
  return a ?? t ?? fallback;
}
/** 이미지 저장본 주소(같은 출처만) */
export const imageSrc = (im?: { thumb_url?: string | null; stored_url?: string | null } | null, prefer: 'thumb' | 'stored' = 'thumb') =>
  (prefer === 'thumb' ? im?.thumb_url ?? im?.stored_url : im?.stored_url ?? im?.thumb_url) ?? null;
