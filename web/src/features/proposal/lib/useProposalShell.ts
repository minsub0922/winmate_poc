/**
 * 제안서 화면 → 셸 맥락(브레드크럼 · 스텝바 · 딸깍 · 드롭 받는 종류 · 추가 핸들러).
 * 딸깍(§3.9 · §4.1): 1–5단계 화면에서 버튼, 팝오버 내용은 `GET …/one-click/plan`(없으면 보드 로직으로 계산), 실행은 `POST …/one-click` → OneClickGen.
 */
import { useNavigate } from 'react-router';
import { useShellPage } from '@/shell';
import type { DragType, FeatureCode, ShellPageConfig, StepperPlanRow } from '@/shell';
import { toast } from '@/ui';
import { startOneClick, useOneClickPlan } from '../api/proposal';
import { errText } from '../api/http';
import type { Proposal, Stage } from '../api/types';
import { SECTIONS, STEPS, TYPES, type SectionKey } from './catalog';
import { R } from './routes';

export const SECTION_NAME = 'B2B 제안서 생성';

export interface ProposalShellOptions {
  p?: Proposal | null;
  /** 스텝바 현재 단계(1–6). 없으면 스텝바 없음 */
  step?: number;
  title?: string;
  complete?: boolean;
  autoFrom?: number;
  /** 딸깍 버튼(1–5단계). from = 누른 단계, section = 작성 중인 섹션 */
  oneClick?: { from: Stage; section?: SectionKey | null } | null;
  oneClickOpen?: boolean;
  accepts?: DragType[];
  acceptsWork?: FeatureCode[];
  added?: string[];
  onAdd?: ShellPageConfig['onAdd'];
  addable?: DragType[];
  hasTask?: boolean;
  sidebarGroup?: string;
}

/** 보드 로직 기본 계획(서버 계획이 없을 때) — OneClickEarly · OneClickConfirm · Stepper 기본값 */
export function fallbackPlan(p: Proposal | null | undefined, from: Stage, section?: SectionKey | null): { confirmed: string[]; rows: StepperPlanRow[]; summary: string } {
  const type = p?.type ?? null;
  const design = p?.design?.master_name ? p.design.master_name : '삼성 B2B 표준 (기본값)';
  const tail = [{ label: '디자인 템플릿', note: design }, { label: 'PPTX 생성', note: '표지 · 목차 포함' }];
  if (from === 'sections' && type && section) {
    const T = TYPES[type];
    const keys = T.secs.filter((k) => p?.sections?.find((s) => s.key === k)?.enabled !== false && !p?.sections?.find((s) => s.key === k)?.hidden);
    const i0 = Math.max(0, keys.indexOf(section));
    const sheetsOf = (k: SectionKey) => p?.sections?.find((s) => s.key === k)?.sheet_count ?? SECTIONS[k].sheets.length;
    const confirmed = ['고객 · 프로젝트', T.name, '시트 구성'].concat(keys.slice(0, i0).map((k) => SECTIONS[k].short));
    const rows = [{ label: `${SECTIONS[section].short} (작성 중)`, note: `입력한 내용 반영 · ${SECTIONS[section].infer}` }]
      .concat(keys.slice(i0 + 1).map((k) => ({ label: SECTIONS[k].short, note: SECTIONS[k].infer })))
      .concat(tail);
    const remain = keys.slice(i0).reduce((a, k) => a + sheetsOf(k), 0);
    return { confirmed, rows, summary: `섹션 ${keys.length - i0} · 시트 ${remain}` };
  }
  const stepNo = from === 'customer' ? 1 : from === 'type' ? 2 : from === 'compose' || from === 'industry' ? 3 : from === 'design' ? 5 : 4;
  const recType = type ?? 'standard';
  const typeName = TYPES[recType].name;
  const secCount = TYPES[recType].secs.length;
  const all: StepperPlanRow[] = [
    { label: '제안서 유형', note: type ? typeName : `${typeName} (요구사항 기반 추천)` },
    { label: '시트 구성', note: `${secCount}섹션 · 요구사항 기반 추천 시트` },
    { label: '섹션 작성', note: '연결된 작업 + 추론 · 시트마다 템플릿 자동 추천' },
    ...tail,
  ];
  const rows = stepNo === 1 ? [{ label: '고객 · 프로젝트', note: '입력한 내용까지 반영하고 나머지 추론' }, ...all] : all.slice(stepNo - 2);
  const confirmed = STEPS.slice(0, stepNo - 1).map((s, i) => (i === 1 && type ? TYPES[type].name : s));
  return { confirmed: confirmed.length ? confirmed : [], rows, summary: `남은 ${rows.length}단계` };
}

export function useProposalShell(o: ProposalShellOptions) {
  const nav = useNavigate();
  const p = o.p ?? null;
  const ocRunning = p?.one_click?.status === 'running';
  const showOc = !!o.oneClick && !!p && !ocRunning && (o.step ?? 6) <= 5;
  const plan = useOneClickPlan(p?.id, o.oneClick?.from, o.oneClick?.section ?? null, showOc);
  const fb = o.oneClick ? fallbackPlan(p, o.oneClick.from, o.oneClick.section) : null;
  const planOk = plan.data && Array.isArray(plan.data.rows) ? plan.data : null;

  const run = async (opts: { markInferred: boolean; collectReview: boolean }) => {
    if (!p || !o.oneClick) return;
    try {
      const r = await startOneClick(p.id, {
        options: { mark_inferred: opts.markInferred, collect_reviews: opts.collectReview }, from_stage: o.oneClick.from, from_section_key: o.oneClick.section ?? null,
      });
      nav(R.oneClick(p.id, r.job_id));
    } catch (e) {
      toast(errText(e));
    }
  };

  useShellPage({
    section: SECTION_NAME,
    title: o.title ?? (p ? (p.title?.trim() || '새 제안서') : undefined),
    hasTask: o.hasTask ?? true,
    accepts: o.accepts,
    acceptsWork: o.acceptsWork,
    added: o.added,
    onAdd: o.onAdd,
    addable: o.addable,
    sidebarGroup: o.sidebarGroup,
    taskContext: p?.customer?.kr_vertical_id ? { verticalId: p.customer.kr_vertical_id, verticalName: p.customer.industry_label ?? undefined } : undefined,
    stepper: o.step ? {
      steps: STEPS,
      current: o.step,
      complete: o.complete,
      autoFrom: o.autoFrom,
      oneClick: showOc ? { onRun: run } : undefined,
      oneClickOpen: o.oneClickOpen,
      planConfirmed: showOc ? (planOk?.confirmed ?? fb?.confirmed) : undefined,
      planRows: showOc ? (planOk?.rows ?? fb?.rows) : undefined,
      planSummary: showOc ? (planOk?.summary ?? fb?.summary) : undefined,
    } : undefined,
  });
}
