/**
 * RQ1 폼 상태(화면 쪽) — 서버 문서(RFDoc)에서 만들고, 고칠 때마다 폼 전체를 PUT 한다.
 * id 는 화면이 만든다(k_ · q_ + 8자) — 자동 저장을 여러 번 해도 요구 · 키맨 id 가 바뀌지 않게(심층 질의가 id 로 가리킨다).
 */
import { distribute } from '../lib/weights';
import type { By, Flag, RFDoc, RFUpdate } from './api';

export interface FReq { id: string; text: string; status: 'ok' | 'check'; flag: Flag; by: By }
export interface FKeyman { id: string; role: string; weight: number; weight_by: By; reqs: FReq[] }
export interface FForm {
  title: string; customer: string; target: string; note: string;
  title_by: By | null; customer_by: By | null; target_by: By | null;
  keymen: FKeyman[];
}

const hex = () => Math.random().toString(16).slice(2, 10).padEnd(8, '0');
export const newId = (prefix: 'k_' | 'q_') => `${prefix}${hex()}`;

export function emptyForm(): FForm {
  return { title: '', customer: '', target: '', note: '', title_by: null, customer_by: null, target_by: null,
    keymen: [{ id: newId('k_'), role: '', weight: 100, weight_by: 'manual', reqs: [] }] };
}

export function formOf(d: RFDoc): FForm {
  return {
    title: d.title ?? '', customer: d.customer ?? '', target: d.target ?? '', note: d.note ?? '',
    title_by: d.title_by ?? null, customer_by: d.customer_by ?? null, target_by: d.target_by ?? null,
    keymen: (d.keymen ?? []).map((k) => ({ id: k.id, role: k.role ?? '', weight: k.weight ?? 0, weight_by: k.weight_by ?? 'manual',
      reqs: (k.reqs ?? []).map((r) => ({ id: r.id, text: r.text, status: r.status ?? 'ok', flag: r.flag ?? 'none', by: r.by ?? 'manual' })) })),
  };
}

/** PUT 본문 — 빈 문장 요구는 서버가 버린다(입력 중인 빈 줄은 화면에만 남는다) */
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

export const weightSum = (f: FForm) => f.keymen.reduce((a, k) => a + (Number(k.weight) || 0), 0);

/** 한 키맨 가중치를 바꾸면 나머지는 지금 비율대로 남은 몫을 나눈다(합 100) */
export function setWeight(kms: FKeyman[], i: number, w: number): FKeyman[] {
  const v = Math.max(0, Math.min(100, Math.round(w)));
  if (kms.length === 1) return [{ ...kms[0], weight: v, weight_by: 'manual' }];
  const others = kms.map((_, j) => j).filter((j) => j !== i);
  const shares = distribute(others.map((j) => kms[j].weight), 100 - v, 0);
  return kms.map((k, j) => (j === i ? { ...k, weight: v, weight_by: 'manual' }
    : { ...k, weight: shares[others.indexOf(j)], weight_by: k.weight === shares[others.indexOf(j)] ? k.weight_by : 'manual' }));
}

/** 키맨 더하기 — 새 키맨은 고른 몫(100/n), 나머지는 지금 비율대로 */
export function addKeyman(kms: FKeyman[]): FKeyman[] {
  const n = kms.length + 1;
  const mine = Math.floor(100 / n);
  const shares = distribute(kms.map((k) => k.weight), 100 - mine, 0);
  return [...kms.map((k, j) => ({ ...k, weight: shares[j], weight_by: (k.weight === shares[j] ? k.weight_by : 'manual') as By })),
    { id: newId('k_'), role: '', weight: mine, weight_by: 'manual', reqs: [] }];
}

/** 키맨 빼기 — 그 몫은 나머지에 비율대로 */
export function removeKeyman(kms: FKeyman[], i: number): FKeyman[] {
  const rest = kms.filter((_, j) => j !== i);
  if (!rest.length) return [{ id: newId('k_'), role: '', weight: 100, weight_by: 'manual', reqs: [] }];
  const shares = distribute(rest.map((k) => k.weight), 100, 0);
  return rest.map((k, j) => ({ ...k, weight: shares[j], weight_by: (k.weight === shares[j] ? k.weight_by : 'manual') as By }));
}

/** '으로/로' — 받침 없거나 ㄹ 받침이면 '로'(숫자: 0 · 3 · 6 만 '으로') */
export function euro(word: string) {
  const ch = word.trim().slice(-1);
  if (!ch) return '로';
  const c = ch.charCodeAt(0);
  if (c >= 0xac00 && c <= 0xd7a3) { const f = (c - 0xac00) % 28; return f === 0 || f === 8 ? '로' : '으로'; }
  if (/[0-9]/.test(ch)) return '036'.includes(ch) ? '으로' : '로';
  return /[mnMN]/.test(ch) ? '으로' : '로';
}
