/**
 * kb 응답 타입 — contracts/kb.json 에서 생성한 `@/api/gen/kb` 스키마에 셸 쪽 이름을 붙인 것(00-shell §7.2).
 * 계약에 아직 없는 §7.2 필드(갭 G-*)는 `&` 로 선택 필드만 덧붙인다 — kb 가 채우면 화면이 바로 쓴다.
 * 타입 갱신: `cd web && node scripts/gen-api.mjs kb` (또는 make contracts SERVICE=kb).
 */
import type { components } from '@/api/gen/kb';
import type { ProductSearchItem } from '@/ui';

type S = components['schemas'];

export type { ProductSearchItem };

export type MediaInfo = S['ImageDims'];

/** §7.2.1 ImageCard */
export type KbImageCard = S['ImageCard'];

/** §7.2.1 ImageMeta */
export type KbImageMeta = S['ImageMeta'];

/** §7.2.1 CaseCard — `summary` 는 G-CASE-1(요약 미적재)이면 null, 그때는 원문 인용 `quote` 를 보여 준다 */
export type KbCaseCard = S['CaseCard'];

export type KbCorpus = S['Corpus'];

/** §7.2.2 */
export type KbMeta = S['MetaOut'];

/** §7.2.3 */
export type KbCategory = S['CategoryItem'];

/** §7.2.4 */
export type KbFamily = S['FamilyItem'];

export type KbColumn = S['Column'];
export type KbModelValue = S['ModelValue'];
export type KbModelRow = S['ModelRow'];
export type KbModelList = S['ModelList'];

/** §7.2.6 */
export type KbSpecRow = S['winmate_kb__schemas__SpecRow'];
export type KbSpecGroup = S['SpecGroup'];
export interface KbDocument { name: string; version?: string | null; lang?: string | null; size_label?: string | null; date?: string | null; url: string; cta?: string | null }
/** `documents` 는 G-PRD-3(공식 자료 미수집) — 계약에 생기기 전까지 선택 필드 */
export type KbModelDetail = Omit<S['ModelDetail'], 'documents'> & { documents?: KbDocument[] | null };

/** §7.2.7 */
export type KbImageList = S['ImageList'];

/** §7.2.8 */
export type KbModelCase = S['ModelCaseItem'];
export type KbModelCases = S['ModelCases'];

/** §7.2.9 */
export type KbSolution = S['SolutionItem'];

/** §7.2.10 */
export type KbSolutionDetail = S['SolutionDetail'];

/** §7.2.11 */
export type KbSolutionImages = S['SolutionImages'];

/** §7.2.12 */
export type KbSolutionCases = S['SolutionCases'];

/** §7.2.13 */
export type KbImageSearch = S['ImageSearchOut'];

/** §7.2.15 */
export type KbCaseSearch = S['CaseSearchOut'];

/** §7.2.16 */
export type KbVertical = S['VerticalItem'];

/** image 서비스 `내 생성 이미지`(§7.4) — image 계약에 목록이 생기기 전까지 셸이 정한 모양 */
export interface GeneratedImage { id: string; title?: string | null; width?: number; height?: number; format?: string; bytes?: number; created_at?: string; file_id?: string; thumb_url?: string | null }
