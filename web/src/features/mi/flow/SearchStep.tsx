/**
 * MI2_Loading · MI2(보드 webapp1 MI2.dc.html) — AI 가 Storyboard 를 읽는 동안의 단계 카드, 그다음 검색어(시장 · 고객사 · 사용자) · 검색 조건.
 * 웹 검색이 도는 동안도 같은 단계 카드를 쓴다(보드에는 검색 중 화면이 없다). 값은 보드 인라인 스타일 px 그대로(miflow.css).
 */
import { useEffect, useRef, useState, type ReactNode } from 'react';
import { Link } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { ApiError } from '@/api/client';
import { cx, toast } from '@/ui';
import { GROUPS, PERIODS, SOURCE_TYPES, mfKey, nOn, qsOf, type GroupKey, type MFDoc, type MFFilters, type MFQuery, type MFStep, type Qs, type useMfActions } from './api';

type Actions = ReturnType<typeof useMfActions>;

const SPIN = 'M12 3a9 9 0 1 1-9 9';
const SPARK = 'M12 2.5l1.9 5.6 5.6 1.9-5.6 1.9L12 17.5l-1.9-5.6L4.5 10l5.6-1.9z';
const X_PATH = 'M6 6l12 12M18 6L6 18';
const PLUS_PATH = 'M12 5v14M5 12h14';
const MAX_Q = 10;

const norm = (t: string) => t.toLowerCase().replace(/[^0-9a-z가-힣]+/g, '');

/** 아래 줄(보드: ‹ 뒤로 · 빈칸 · 요약 13 · 주 버튼 h48 + 돋보기) */
export function SearchFooter({ backTo, backLabel, summary, onSearch, disabled, busy }: {
  backTo?: string; backLabel: string; summary?: ReactNode; onSearch?: () => void; disabled?: boolean; busy?: boolean;
}) {
  return (
    <div className="wm-flow__foot mif-foot">
      {backTo ? (
        <Link className="wm-flow__back" to={backTo}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden><path d="M15 6l-6 6 6 6" /></svg>{backLabel}
        </Link>
      ) : <span className="wm-flow__back mif-back--off">{backLabel}</span>}
      <span style={{ flexGrow: 1 }} />
      {summary && <span className="wm-flow__summary">{summary}</span>}
      <button type="button" className="wm-flow__primary mif-primary" onClick={onSearch} disabled={disabled || busy} aria-busy={busy || undefined}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" aria-hidden><circle cx="11" cy="11" r="7" /><path d="M20 20l-4-4" /></svg>
        {busy ? '검색을 시작하는 중…' : '웹 검색 후 정제로'}
      </button>
    </div>
  );
}

/** AI 단계 카드(보드 MI2 loading: r16 · padding 22 24 · 줄 h44) */
export function StepsCard({ title, steps }: { title: string; steps: MFStep[] }) {
  return (
    <div className="mif-steps" role="status" aria-live="polite" data-testid="mif-steps">
      <span className="mif-steps__title">
        <svg className="mif-spin" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" aria-hidden><path d={SPIN} /></svg>
        {title}
      </span>
      {steps.map((s) => (
        <div key={s.key} className="mif-step" data-state={s.state}>
          <span className={cx('mif-dot', `mif-dot--${s.state}`)} aria-hidden />
          <span className="mif-step__t">{s.label}</span>
          <span className="mif-step__note">{s.state === 'done' || s.state === 'error' ? s.note : ''}</span>
        </div>
      ))}
    </div>
  );
}

/** MI2_Loading — Storyboard 분석 중 · 웹 검색 중 */
export function LoadingView({ kind, steps, backTo, summary }: { kind: 'analyze' | 'search'; steps: MFStep[]; backTo?: string; summary?: string }) {
  const an = kind === 'analyze';
  return (
    <>
      <div className="mif-head">
        <div className="wm-flow__titles">
          <h1 className="wm-flow__h1">{an ? 'Storyboard를 읽는 중이에요' : '웹에서 찾는 중이에요'}</h1>
          <span className="wm-flow__desc">{an ? '다 읽으면 검색어와 검색 조건이 나타나요.' : '다 찾으면 찾은 정보를 정리하는 화면으로 넘어가요.'}</span>
        </div>
      </div>
      <StepsCard title={an ? 'AI가 Storyboard를 분석하고 있어요' : 'AI가 웹에서 시장 · 고객사 · 사용자 정보를 찾고 있어요'} steps={steps} />
      <SearchFooter backTo={backTo} backLabel={an ? 'Storyboard' : '검색어 고치기'} summary={summary} disabled />
    </>
  );
}

/** MI2 — 검색어 · 검색 조건 */
export function SearchView({ doc, actions, backTo }: { doc: MFDoc; actions: Actions; backTo: string }) {
  const qc = useQueryClient();
  const [qs, setQs] = useState<Qs>(() => qsOf(doc));
  const [filters, setFilters] = useState<MFFilters>(() => ({ period: doc.filters?.period ?? '최근 1년', sourceTypes: [...(doc.filters?.sourceTypes ?? [])] }));
  const [keep, setKeep] = useState<boolean>(doc.keep_previous ?? true);
  const [busy, setBusy] = useState(false);
  const pending = useRef<{ queries?: Qs; filters?: MFFilters; keep_previous?: boolean } | null>(null);
  const timer = useRef<number | null>(null);
  const chain = useRef<Promise<unknown>>(Promise.resolve());

  const send = () => {
    const body = pending.current;
    pending.current = null;
    if (timer.current) { window.clearTimeout(timer.current); timer.current = null; }
    if (!body) return chain.current;
    chain.current = chain.current.then(async () => {
      const ver = (qc.getQueryData(mfKey(doc.id)) as MFDoc | undefined)?.version ?? doc.version;
      try {
        await actions.patch({ ...body, expected_version: ver });
      } catch (e) {
        if (e instanceof ApiError && e.status === 409 && e.code === 'CONFLICT') {
          const fresh = await actions.refresh();
          await actions.patch({ ...body, expected_version: fresh.version });
        } else {
          toast((e as Error).message || '저장하지 못했어요');
        }
      }
    }).catch(() => undefined);
    return chain.current;
  };
  const queue = (part: { queries?: Qs; filters?: MFFilters; keep_previous?: boolean }) => {
    pending.current = { ...(pending.current ?? {}), ...part };
    if (timer.current) window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => { void send(); }, 250);
  };
  useEffect(() => () => { if (timer.current) window.clearTimeout(timer.current); }, []);

  const setGroup = (g: GroupKey, rows: MFQuery[]) => { const next = { ...qs, [g]: rows }; setQs(next); queue({ queries: next }); };
  const toggle = (g: GroupKey, i: number) => setGroup(g, qs[g].map((q, j) => (j === i ? { ...q, on: !(q.on ?? true) } : q)));
  const add = (g: GroupKey, text: string) => {
    const t = text.replace(/\s+/g, ' ').trim().slice(0, 40);
    if (!t) return false;
    const i = qs[g].findIndex((q) => norm(q.text) === norm(t));
    if (i >= 0) { if (!(qs[g][i].on ?? true)) toggle(g, i); return true; }
    if (qs[g].length >= MAX_Q) { toast(`검색어는 묶음마다 ${MAX_Q}개까지예요`); return false; }
    setGroup(g, [...qs[g], { text: t, on: true, by: 'manual' }]);
    return true;
  };
  const setPeriod = (p: MFFilters['period']) => { const next = { ...filters, period: p }; setFilters(next); queue({ filters: next }); };
  const toggleType = (t: string) => {
    const cur = filters.sourceTypes ?? [];
    const next = { ...filters, sourceTypes: cur.includes(t) ? cur.filter((x) => x !== t) : SOURCE_TYPES.filter((x) => x === t || cur.includes(x)) };
    setFilters(next); queue({ filters: next });
  };
  const setKeepPrev = (v: boolean) => { setKeep(v); queue({ keep_previous: v }); };

  const nq = GROUPS.reduce((a, g) => a + nOn(qs[g.key]), 0);
  const noTypes = !(filters.sourceTypes ?? []).length;
  const search = async () => {
    if (busy) return;
    setBusy(true);
    try { await send(); await actions.search(); } catch (e) { toast((e as Error).message || '검색을 시작하지 못했어요'); } finally { setBusy(false); }
  };
  const editing = doc.ver != null;
  const rule = doc.analysis_mode === 'rule';
  const failed = doc.progress?.error;
  const sub = failed ? (doc.warnings ?? []).slice(-1)[0] ?? `${failed}.`
    : rule ? '지금은 AI 분석을 쓸 수 없어 Storyboard 값으로 검색어를 만들었어요. 빼거나 더해 주세요.'
      : 'AI가 Storyboard의 고객사 · 업종 · 공간 · 요구에서 검색어를 만들었어요. 빼거나 더하면 돼요.';
  const opts: Array<{ k: string; vs: Array<{ t: string; on: boolean; pick: () => void }> }> = [
    { k: '기간', vs: PERIODS.map((p) => ({ t: p, on: filters.period === p, pick: () => setPeriod(p) })) },
    { k: '출처', vs: SOURCE_TYPES.map((t) => ({ t, on: (filters.sourceTypes ?? []).includes(t), pick: () => toggleType(t) })) },
  ];
  if (editing) {
    opts.push({ k: `기존 ${doc.code ?? 'MI'}`, vs: [
      { t: `담은 정보 ${doc.saved_kept ?? 0}개 유지 · 새로 찾은 것만 더하기`, on: keep, pick: () => setKeepPrev(true) },
      { t: '처음부터 다시', on: !keep, pick: () => setKeepPrev(false) },
    ] });
  }
  return (
    <>
      <div className="mif-head">
        <div className="wm-flow__titles">
          <h1 className="wm-flow__h1">무엇을 검색할까요?</h1>
          <span className={cx('wm-flow__desc', (rule || failed) && 'mif-desc--warn')}>{sub}</span>
        </div>
      </div>
      <div className="mif-basis">
        <span className="mif-aitag">{!rule && <svg width="11" height="11" viewBox="0 0 24 24" fill="currentColor" aria-hidden><path d={SPARK} /></svg>}{rule ? '규칙' : 'AI 분석'}</span>
        <span className="mif-basis__label">Storyboard에서 읽은 것</span>
        {(doc.basis ?? []).map((b) => <span key={b.k} className="mif-basis__chip"><b>{b.k}</b>{b.v}</span>)}
      </div>
      <div className="mif-cols">
        {GROUPS.map((g) => <QueryCol key={g.key} label={g.label} gkey={g.key} rows={qs[g.key]} onToggle={(i) => toggle(g.key, i)} onAdd={(t) => add(g.key, t)} />)}
      </div>
      <div className="mif-opts">
        {opts.map((o) => (
          <div key={o.k} className="mif-opt" role="group" aria-label={o.k}>
            <span className="mif-opt__k">{o.k}</span>
            <div className="mif-opt__vs">
              {o.vs.map((v) => <button key={v.t} type="button" className={cx('mif-chip', v.on && 'mif-chip--on')} aria-pressed={v.on} onClick={v.pick}>{v.t}</button>)}
            </div>
          </div>
        ))}
      </div>
      <SearchFooter backTo={backTo} backLabel="Storyboard" onSearch={search} busy={busy} disabled={!nq || noTypes}
        summary={!nq ? '검색어를 하나 이상 넣어 주세요' : noTypes ? '출처를 하나 이상 골라 주세요' : `검색어 ${nq}개 · 1–2분`} />
    </>
  );
}

function QueryCol({ label, gkey, rows, onToggle, onAdd }: {
  label: string; gkey: GroupKey; rows: MFQuery[]; onToggle: (i: number) => void; onAdd: (t: string) => boolean;
}) {
  const [draft, setDraft] = useState('');
  const n = nOn(rows);
  const id = `mi-add-${gkey}`;
  const commit = () => { if (draft.trim() && onAdd(draft)) setDraft(''); };
  return (
    <div className="mif-col" data-group={gkey}>
      <div className="mif-col__head"><span className="mif-col__t">{label}</span><span className="mif-col__n">검색어 {n}</span></div>
      <div className="mif-qs">
        {rows.map((q, i) => {
          const off = !(q.on ?? true);
          return (
            <span key={`${q.text}-${i}`} className={cx('mif-q', off && 'mif-q--off')} data-by={q.by}>
              <span className="mif-q__t" title={q.text}>{q.text}</span>
              <button type="button" className="mif-q__x" onClick={() => onToggle(i)} aria-label={`${off ? '다시 넣기' : '빼기'} · ${q.text}`}>
                <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" aria-hidden><path d={off ? PLUS_PATH : X_PATH} /></svg>
              </button>
            </span>
          );
        })}
      </div>
      <div className="mif-add">
        <label htmlFor={id} className="wm-sr">{label} 검색어 추가</label>
        <input id={id} placeholder="+ 검색어" value={draft} maxLength={40} onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && !e.nativeEvent.isComposing) { e.preventDefault(); commit(); } if (e.key === 'Escape') setDraft(''); }}
          onBlur={commit} />
      </div>
    </div>
  );
}
