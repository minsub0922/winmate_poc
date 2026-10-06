/** 표시 형식 — 마감 D-day(KST), 진행 라벨 대체값(§10.11). 서버가 라벨을 주면 서버 값이 먼저다. */
import type { Proposal, ProposalRow, Stage } from '../api/types';
import { INDUSTRIES, TYPE_ROW_LABEL, type ProposalType } from './catalog';
import { STAGE_STEP } from './routes';

export type ProposalStatus = 'draft' | 'review' | 'done';

export const STATUS_LABEL: Record<ProposalStatus, string> = { draft: '작성 중', review: '검토 중', done: '완료' };

/** KST 날짜 YYYY-MM-DD */
export function kstDate(d: Date = new Date()): string {
  const t = new Date(d.getTime() + 9 * 3600_000);
  return t.toISOString().slice(0, 10);
}
export function dayDiff(dueIso: string, today = kstDate()): number {
  const a = Date.parse(`${today}T00:00:00Z`);
  const b = Date.parse(`${dueIso.slice(0, 10)}T00:00:00Z`);
  return Math.round((b - a) / 86_400_000);
}
/** 「10.08」 · 「D-7」(≤ 7 강조) · 지난 마감 「D+n」 */
export function dueLabels(due: string | null | undefined, status: ProposalStatus, submittedAt?: string | null) {
  if (status === 'done') {
    const d = submittedAt ? kstDate(new Date(submittedAt)) : '';
    return { due: '제출함', dday: d ? d.replace(/-/g, '.') : '', urgent: false };
  }
  if (!due) return { due: '—', dday: '', urgent: false };
  const n = dayDiff(due);
  return { due: `${due.slice(5, 7)}.${due.slice(8, 10)}`, dday: n >= 0 ? `D-${n}` : `D+${-n}`, urgent: n <= 7 };
}

export function initialOf(name?: string | null) {
  return (name ?? '').trim().slice(0, 1) || '·';
}

/** 행 표시값 — 서버 ProposalRow 값을 먼저 쓰고 없으면 계산 */
export function rowView(r: ProposalRow) {
  const dl = dueLabels(r.due_date ?? null, r.status);
  return {
    title: r.title || '새 제안서',
    sub: r.sub_label || [r.industry_label, r.customer_name].filter(Boolean).join(' · '),
    type: r.type_label ?? (r.type ? TYPE_ROW_LABEL[r.type as ProposalType] : '—'),
    statusLabel: r.status_label || STATUS_LABEL[r.status],
    due: r.due_label || dl.due,
    dday: r.d_day_label ?? dl.dday,
    urgent: r.urgent ?? dl.urgent,
    done: r.steps_done ?? 0,
    cur: r.current_step ?? 0,
    progress: r.progress_label ?? '',
    owner: r.owner?.name ?? '',
    initial: r.owner?.initial || initialOf(r.owner?.name),
  };
}

export function industryLabel(p: Proposal | null | undefined): string {
  const c = p?.customer;
  if (!c) return '';
  if (c.industry_label) return c.industry_label;
  return c.industry_code ? INDUSTRIES[c.industry_code] ?? '' : '';
}

export function stepOf(p: Proposal | null | undefined): number {
  return p?.stage_no ?? (p?.stage ? STAGE_STEP[p.stage as Stage] ?? 1 : 1);
}

/** 「M월 D일 (요일)」 */
export function koDate(iso?: string | null): string {
  if (!iso) return '';
  const [y, m, dd] = [Number(iso.slice(0, 4)), Number(iso.slice(5, 7)), Number(iso.slice(8, 10))];
  const w = ['일', '월', '화', '수', '목', '금', '토'][new Date(Date.UTC(y, m - 1, dd)).getUTCDay()];
  return `${m}월 ${dd}일 (${w})`;
}
/** 「오늘 11:00」 · 「어제 18:30」 · 「10.05 14:20」 */
export function whenLabel(iso?: string | null): string {
  if (!iso) return '';
  const d = new Date(iso);
  const day = kstDate(d);
  const today = kstDate();
  const hm = new Date(d.getTime() + 9 * 3600_000).toISOString().slice(11, 16);
  if (day === today) return `오늘 ${hm}`;
  if (dayDiff(day, today) === -1) return `어제 ${hm}`;
  return `${day.slice(5, 7)}.${day.slice(8, 10)} ${hm}`;
}
