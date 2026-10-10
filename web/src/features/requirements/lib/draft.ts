/**
 * 작업본 ops 를 화면에서 먼저 적용(낙관적) — 서버 domain.apply_ops 와 같은 규칙의 간단판.
 * 보낸 ops 는 서버 응답으로 바뀌고, 아직 안 보낸 ops 는 그 위에 다시 적용한다(같은 op 를 두 번 적용해도 결과가 같다).
 */
import type { DraftOp, Form, FormField, Keyman, ReqItem, Requirement, Source } from '../api';
import { distribute, equalWeights } from './weights';

function clone<T>(x: T): T {
  return JSON.parse(JSON.stringify(x)) as T;
}

function rebalance(form: Form, added: string[] = []) {
  const ks = form.keymen;
  if (ks.length === 0) return;
  if (ks.length === 1) { ks[0].weight = 100; return; }
  if (form.weights_mode !== 'custom') {
    equalWeights(ks.length).forEach((w, i) => { ks[i].weight = w; });
    return;
  }
  const old = ks.filter((k) => !added.includes(k.id) && typeof k.weight === 'number');
  const fresh = ks.filter((k) => !old.includes(k));
  if (old.length === 0) { equalWeights(ks.length).forEach((w, i) => { ks[i].weight = w; }); return; }
  const share = fresh.length ? Math.floor(100 / ks.length) : 0;
  const vals = distribute(old.map((k) => k.weight ?? 0), 100 - share * fresh.length);
  old.forEach((k, i) => { k.weight = vals[i]; });
  fresh.forEach((k) => { k.weight = share; });
  if (ks.some((k) => (k.weight ?? 0) < 5)) {
    const all = distribute(ks.map((k) => k.weight ?? 0), 100);
    ks.forEach((k, i) => { k.weight = all[i]; });
  }
}

export const userSrc = (): Source => ({
  kind: 'user', file_id: null, file_label: null, file_name: null, job_id: null, locator: null, quote: null, reply_id: null, service: null, session_id: null,
});

const userField = (value: string | null, prev: FormField): FormField => ({
  ...prev, value: value && value.length ? value : null, source: value ? userSrc() : null,
});

export function applyLocal(rq: Requirement, ops: DraftOp[]): Requirement {
  if (!ops.length) return rq;
  const out = clone(rq);
  const form = out.form;
  const findItem = (id: string): [Keyman | undefined, ReqItem | undefined] => {
    for (const k of form.keymen) {
      const it = k.items.find((i) => i.id === id);
      if (it) return [k, it];
    }
    return [undefined, undefined];
  };
  for (const op of ops) {
    switch (op.op) {
      case 'set_field':
        form[op.field] = userField(op.value ?? null, form[op.field]);
        break;
      case 'add_keyman': {
        if (op.keyman_id && form.keymen.some((k) => k.id === op.keyman_id)) break;
        const k: Keyman = { id: op.keyman_id ?? `km_local${form.keymen.length}`, name: op.name ?? '', weight: null, color_index: form.keymen.reduce((m, x) => Math.max(m, x.color_index + 1), 0), order: form.keymen.length, source: userSrc(), items: [], rev: 0 };
        const at = op.after_keyman_id ? form.keymen.findIndex((x) => x.id === op.after_keyman_id) + 1 : form.keymen.length;
        form.keymen.splice(at > 0 ? at : form.keymen.length, 0, k);
        rebalance(form, [k.id]);
        break;
      }
      case 'update_keyman': {
        const k = form.keymen.find((x) => x.id === op.keyman_id);
        if (k) { k.name = op.name; k.source = userSrc(); }
        break;
      }
      case 'remove_keyman': {
        const i = form.keymen.findIndex((x) => x.id === op.keyman_id);
        if (i >= 0) {
          form.keymen.splice(i, 1);
          rebalance(form);
          if (form.keymen.length < 2) form.weights_mode = 'equal_default';
        }
        break;
      }
      case 'set_weights':
        if (Object.keys(op.weights).length === form.keymen.length) {
          form.keymen.forEach((k) => { if (op.weights[k.id] !== undefined) k.weight = op.weights[k.id]; });
          form.weights_mode = 'custom';
        }
        break;
      case 'reset_weights_equal':
        form.weights_mode = 'equal_default';
        rebalance(form);
        break;
      case 'add_item': {
        const k = form.keymen.find((x) => x.id === op.keyman_id);
        if (!k || (op.item_id && findItem(op.item_id)[1])) break;
        const it: ReqItem = { id: op.item_id ?? `ri_local${Date.now()}`, code: '', text: op.text ?? '', short: null, source: userSrc(), needs_confirmation: false, evidence: [], entities: [], order: k.items.length, rev: 0, updated_at: null };
        const at = op.after_item_id ? k.items.findIndex((x) => x.id === op.after_item_id) + 1 : k.items.length;
        k.items.splice(at > 0 ? at : k.items.length, 0, it);
        break;
      }
      case 'update_item': {
        const [, it] = findItem(op.item_id);
        if (it) { it.text = op.text; it.source = userSrc(); it.short = null; }
        break;
      }
      case 'remove_item': {
        const [k, it] = findItem(op.item_id);
        if (k && it) k.items.splice(k.items.indexOf(it), 1);
        break;
      }
      case 'move_item': {
        const [k, it] = findItem(op.item_id);
        const dst = form.keymen.find((x) => x.id === op.keyman_id);
        if (k && it && dst) { k.items.splice(k.items.indexOf(it), 1); dst.items.splice(op.index, 0, it); }
        break;
      }
    }
  }
  return out;
}

/** 같은 대상의 앞선 값 op 는 뒤 것으로 합친다(set_field · update_item · update_keyman · set_weights). */
export function coalesce(queue: DraftOp[], op: DraftOp): DraftOp[] {
  const key = (o: DraftOp) => o.op === 'set_field' ? `f:${o.field}` : o.op === 'update_item' ? `i:${o.item_id}` : o.op === 'update_keyman' ? `k:${o.keyman_id}` : o.op === 'set_weights' ? 'w' : null;
  const k = key(op);
  if (!k) return [...queue, op];
  // 같은 대상의 add 가 아직 큐에 있으면 그 add 를 고친다(새 항목 · 새 키맨을 만든 뒤 바로 타이핑)
  if (op.op === 'update_item') {
    const i = queue.findIndex((o) => o.op === 'add_item' && o.item_id === op.item_id);
    if (i >= 0) { const next = [...queue]; next[i] = { ...(queue[i] as Extract<DraftOp, { op: 'add_item' }>), text: op.text }; return next; }
  }
  if (op.op === 'update_keyman') {
    const i = queue.findIndex((o) => o.op === 'add_keyman' && o.keyman_id === op.keyman_id);
    if (i >= 0) { const next = [...queue]; next[i] = { ...(queue[i] as Extract<DraftOp, { op: 'add_keyman' }>), name: op.name }; return next; }
  }
  const last = queue.length ? queue[queue.length - 1] : null;
  if (last && key(last) === k) return [...queue.slice(0, -1), op];
  return [...queue, op];
}

export function isFormEmpty(rq: Requirement | null | undefined): boolean {
  if (!rq) return true;
  const f = rq.form;
  if ([f.project_name, f.customer_name, f.final_audience, f.author_note].some((x) => x?.value)) return false;
  if (f.keymen.some((k) => (k.name ?? '').trim() || k.items.some((i) => (i.text ?? '').trim()))) return false;
  return !(rq.files ?? []).length;
}

export const EMPTY_FIELD: FormField = { value: null, source: null, derived_from: null, alternatives: [], updated_at: null, rev: 0 };

export function emptyRequirement(): Requirement {
  const now = new Date().toISOString();
  return {
    id: '', owner: { id: '', name: '' }, project_id: null, title: null, short_title: null, version: 0, revision: 0,
    has_unsaved_changes: false, list_state: 'input', state_label: '입력 중',
    form: { project_name: { ...EMPTY_FIELD }, customer_name: { ...EMPTY_FIELD }, final_audience: { ...EMPTY_FIELD }, author_note: { ...EMPTY_FIELD }, keymen: [], weights_mode: 'equal_default' },
    files: [], context: { spaces: [], products: [], solutions: [] }, open_question_count: 0, item_count: 0, keyman_count: 0,
    active_job: null, queued_jobs: [], fill_progress: null, active_deep_session_id: null, active_deep: null, last_deep_session_id: null,
    route: '/requirements/legacy/new', created_at: now, updated_at: now, saved_at: null, skipped_ops: null,
  } as unknown as Requirement;
}
