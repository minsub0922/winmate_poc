/**
 * RQBody 폼 상태(화면 쪽) — 서버 문서(RFDoc)에서 만들고, 칸을 떠날 때마다 폼 전체를 PUT 한다.
 * id 는 화면이 만든다(k_ · q_ + 8자) — 자동 저장을 여러 번 해도 요구 · 키맨 id 가 바뀌지 않게(서버 changes 도 id 로 맞춰 센다).
 * 가중치는 칸마다 따로 고친다(다른 키맨 값을 몰래 바꾸지 않음 — 합이 100 이 아니면 보드처럼 노란 글씨, 저장 때 서버가 비율대로 맞춘다).
 */
import type { By, Flag, RFDoc, RFUpdate } from './api';

export interface FReq { id: string; text: string; status: 'ok' | 'check'; flag: Flag; by: By }
export interface FKeyman { id: string; role: string; weight: number; weight_by: By; reqs: FReq[] }
export interface FForm {
  title: string; customer: string; target: string; note: string;
  title_by: By | null; customer_by: By | null; target_by: By | null;
  keymen: FKeyman[];
}

export const MAX_KEYMEN = 8;
export const MAX_REQS = 12;

const hex = () => Math.random().toString(16).slice(2, 10).padEnd(8, '0');
export const newId = (prefix: 'k_' | 'q_') => `${prefix}${hex()}`;

export const emptyReq = (): FReq => ({ id: newId('q_'), text: '', status: 'ok', flag: 'none', by: 'manual' });

/** 보드 RQBody new: 키맨 하나(가중치 100) · 빈 요구 줄 하나 */
export function emptyForm(): FForm {
  return { title: '', customer: '', target: '', note: '', title_by: null, customer_by: null, target_by: null,
    keymen: [{ id: newId('k_'), role: '', weight: 100, weight_by: 'manual', reqs: [emptyReq()] }] };
}

/** 서버 문서 → 폼. 요구가 없는 키맨은 빈 요구 줄 하나를 둔다(보드 new 와 같이 바로 쓸 수 있게 — 빈 줄은 저장하지 않는다) */
export function formOf(d: RFDoc): FForm {
  const keymen = (d.keymen ?? []).map((k) => {
    const reqs = (k.reqs ?? []).map((r) => ({ id: r.id, text: r.text, status: r.status ?? 'ok', flag: r.flag ?? 'none', by: r.by ?? 'manual' }));
    return { id: k.id, role: k.role ?? '', weight: k.weight ?? 0, weight_by: k.weight_by ?? 'manual', reqs: reqs.length ? reqs : [emptyReq()] };
  });
  return {
    title: d.title ?? '', customer: d.customer ?? '', target: d.target ?? '', note: d.note ?? '',
    title_by: d.title_by ?? null, customer_by: d.customer_by ?? null, target_by: d.target_by ?? null,
    keymen: keymen.length ? keymen : emptyForm().keymen,
  };
}

/** PUT 본문 — 빈 문장 요구는 보내지 않는다(입력 중인 빈 줄은 화면에만 남는다) */
export function bodyOf(f: FForm, expected?: number): RFUpdate {
  return {
    title: f.title, customer: f.customer, target: f.target, note: f.note,
    keymen: f.keymen.map((k) => ({ id: k.id, role: k.role, weight: k.weight, weight_by: k.weight_by,
      reqs: k.reqs.filter((r) => r.text.trim()).map((r) => ({ id: r.id, text: r.text, status: r.status, flag: r.flag, by: r.by })) })),
    expected_version: expected ?? null,
  };
}

export const isEmpty = (f: FForm) =>
  !f.title.trim() && !f.customer.trim() && !f.target.trim() && !f.note.trim() && f.keymen.every((k) => !k.role.trim() && k.reqs.every((r) => !r.text.trim()));

/** 저장할 수 있는가(서버 422 EMPTY_FORM 과 같은 규칙) — 프로젝트명 · 고객사 · 요구사항 중 하나 */
export const canFinish = (f: FForm) => !!(f.title.trim() || f.customer.trim() || f.keymen.some((k) => k.reqs.some((r) => r.text.trim())));

export const weightSum = (f: FForm) => f.keymen.reduce((a, k) => a + (Number(k.weight) || 0), 0);

/** 머리 한 줄 · 본문 요약 줄의 수 — keymen 은 이름이나 요구가 있는 키맨(서버 counts 와 같다), all 은 화면의 키맨 카드 수(보드 RQBody sumLine) */
export function countsOf(f: FForm) {
  const reqs = f.keymen.flatMap((k) => k.reqs.filter((r) => r.text.trim()));
  return {
    all: f.keymen.length,
    keymen: f.keymen.filter((k) => k.role.trim() || k.reqs.some((r) => r.text.trim())).length,
    reqs: reqs.length,
    check: reqs.filter((r) => r.status === 'check').length,
    weight: weightSum(f),
  };
}

/** 키맨 더하기 — 다른 키맨 가중치는 그대로, 새 키맨은 남은 몫(합이 100 이면 0) · 빈 요구 줄 하나 */
export function addKeyman(kms: FKeyman[]): FKeyman[] {
  const left = Math.max(0, 100 - kms.reduce((a, k) => a + (Number(k.weight) || 0), 0));
  return [...kms, { id: newId('k_'), role: '', weight: left, weight_by: 'manual', reqs: [emptyReq()] }];
}

/** 키맨 빼기 — 하나도 안 남으면 빈 키맨(100) 하나 */
export function removeKeyman(kms: FKeyman[], id: string): FKeyman[] {
  const rest = kms.filter((k) => k.id !== id);
  return rest.length ? rest : emptyForm().keymen;
}

// ── 이 화면에서 고친 칸(보드 RQ1_Edit: 고친 칸 cd-in--chg · 요구 줄 「고침」/「새로 씀」) ──
// 기준(base)은 저장한 문서를 처음 열었을 때 · 저장 · 되돌리기 한 때의 폼(화면 상태로 기억 — 새로 읽으면 사라진다).

export type ReqMark = 'chg' | 'add' | null;

export interface Marks {
  field: (k: 'title' | 'customer' | 'target' | 'note') => boolean;
  role: (k: FKeyman) => boolean;
  weight: (k: FKeyman) => boolean;
  req: (r: FReq) => ReqMark;
}

const NO_MARKS: Marks = { field: () => false, role: () => false, weight: () => false, req: () => null };

export function marksOf(base: FForm | null, f: FForm): Marks {
  if (!base) return NO_MARKS;
  const kms = new Map(base.keymen.map((k) => [k.id, k]));
  const reqs = new Map(base.keymen.flatMap((k) => k.reqs.map((r) => [r.id, r] as const)));
  return {
    field: (k) => f[k].trim() !== base[k].trim(),
    role: (k) => { const b = kms.get(k.id); return b ? b.role.trim() !== k.role.trim() : !!k.role.trim(); },
    weight: (k) => { const b = kms.get(k.id); return b ? b.weight !== k.weight : false; },
    req: (r) => {
      const b = reqs.get(r.id);
      if (!b || !b.text.trim()) return r.text.trim() ? 'add' : null;
      return b.text.trim() !== r.text.trim() || b.status !== r.status ? 'chg' : null;
    },
  };
}
