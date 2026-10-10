/**
 * proposal API 모양 — contracts/proposal.json 에서 생성한 타입(@/api/gen/proposal)에 화면이 쓰는 이름을 붙인 것.
 * 갱신: `cd web && node scripts/gen-api.mjs proposal`.
 */
import type { components } from '@/api/gen/proposal';

type S = components['schemas'];
export type Stage = 'customer' | 'type' | 'compose' | 'industry' | 'sections' | 'design' | 'result';

export type Proposal = S['Proposal'];
export type ProposalRow = S['ProposalRow'];
export type ProposalList = S['ProposalList'];
export type ProposalCreate = S['ProposalCreate'];
export type ProposalPatch = S['ProposalPatch'];
export type Customer = S['Customer'];
export type Design = S['Design'];
export type SectionSummary = S['SectionSummary'];

export type RfpView = S['RfpView'];
export type RfpField = S['RfpField'];
export type RelatedWorks = S['RelatedWorks'];
export type RelatedWork = S['RelatedWork'];
export type HubInfo = S['HubInfo'];
export type HubContent = S['HubContent'];
export type FillPreview = S['FillPreview'];
export type LinksOut = S['LinksOut'];

export type TypeOptions = S['TypeOptions'];
export type Composition = S['Composition'];
export type CompSection = S['CompSection'];
export type CompType = S['CompType'];
export type NextStep = S['NextStep'];
export type IndustryView = S['IndustryView'];
export type IndustryFamily = S['IndustryFamily'];

export type SectionView = S['SectionView'];
export type SectionSheet = S['SectionSheet'];
export type SourceChip = S['SourceChip'];
export type Sheet = S['Sheet'];
export type TemplateState = S['TemplateState'];
export type TemplateOptions = S['TemplateOptions'];
export type TemplateVariant = S['TemplateVariant'];
export type SheetOp = S['SheetOp'];
export type SheetPatchResult = S['SheetPatchResult'];
export type Message = S['Message'];
export type Fact = S['Fact'];

export type ImportRequest = S['ImportRequest'];
export type ImportResult = S['ImportResult'];
export type ImportRec = S['Import'];
export type ImportItem = S['ImportItem'];
export type ImageSlots = S['ImageSlots'];

export type OneClickPlan = S['OneClickPlan'];
export type OneClickView = S['OneClickView'];
export type OneClickStep = S['OneClickStep'];

export type DesignView = S['DesignView'];
export type ResultView = S['ResultView'];
export type SlidesView = S['SlidesView'];
export type SlideThumb = S['SlideThumb'];

export type ConfirmList = S['ConfirmList'];
export type ConfirmItem = S['ConfirmItem'];
export type FactEvidence = S['FactEvidence'];

export type ReviewView = S['ReviewView'];
export type Reviewer = S['Reviewer'];
export type Suggestion = S['Suggestion'];

export type VersionsView = S['VersionsView'];
export type CompareView = S['CompareView'];
export type DiffItem = S['DiffItem'];

export type ExportOptions = S['ExportOptions'];
export type ExportRequest = S['ExportRequest'];
export type ExportRecord = S['ExportRecord'];

export type ReuseCandidates = S['ReuseCandidates'];
export type ReuseAnalysis = S['ReuseView'];
export type ReuseCriterion = S['ReuseCriterion'];
export type ReusePage = S['ReusePage'];
export type CriterionDetail = S['CriterionDetail'];
export type ReuseSectionView = S['ReuseSectionView'];
export type ReuseLineView = S['ReuseLineView'];
export type ReuseSummary = S['ReuseSummary'];
export type PlanImprove = S['PlanImprove'];
export type PlanBorrow = S['PlanBorrow'];

export type JobAccepted = S['JobAccepted'];

/** 시트 내용 칸(§5.3.1) — 계약은 `content: object` 라 화면이 읽는 모양을 여기서 정한다 */
export interface SlotTableRow { id: string; label?: string; cells: Array<{ text: string; mark?: 'full' | 'half' | 'none' | null } | string> }
export interface SheetContent {
  eyebrow?: string; title?: string; subtitle?: string; notes?: string; footnotes?: Array<{ text: string; source_ref?: string }>;
  slots?: Record<string, { type: string; [k: string]: unknown }>;
}
