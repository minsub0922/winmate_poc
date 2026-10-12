/**
 * MI 검색 팝업(보드 webapp1 MISearch 1040×740 · 래퍼 MI2_Loading · MI2 · MI_Search) — AI 가 Storyboard 를 읽는 동안의 단계 카드(phase loading),
 * 다 읽으면 검색어(시장 · 고객사 · 사용자 — × 빼기 · + 다시 넣기 · 더하기 칸) · 검색 조건(기간 · 출처, 저장한 MI 면 「기존 MI-01 · 유지 / 처음부터」).
 * 고친 값은 바로 저장(250ms 모아서 PATCH · expected_version 409 면 다시 읽고 한 번 더). 「웹 검색」은 분석이 끝나야 눌린다 → 팝업을 닫고 화면이 찾는 중으로.
 * 닫아도 분석은 이어진다. px 는 보드 인라인 값 그대로(miflow.css · mis-).
 */
import { useEffect, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { ApiError } from '@/api/client';
import { useFlow } from '@/shell';
import { Modal, cx, toast } from '@/ui';
import { GROUPS, PERIODS, SOURCE_TYPES, mfKey, nOn, qsOf, type GroupKey, type MFDoc, type MFFilters, type MFQuery, type MFStep, type Qs, type useMfActions } from './api';

type Actions = ReturnType<typeof useMfActions>;

const SPIN = 'M12 3a9 9 0 1 1-9 9';
const SPARK = 'M12 2.5l1.9 5.6 5.6 1.9-5.6 1.9L12 17.5l-1.9-5.6L4.5 10l5.6-1.9z';
const X_PATH = 'M6 6l12 12M18 6L6 18';
const PLUS_PATH = 'M12 5v14M5 12h14';
const SB_ICON = 'M4 5h16v14H4z M4 11h16 M10 11v8';
const MAX_Q = 10;

const norm = (t: string) => t.toLowerCase().replace(/[^0-9a-z가-힣]+/g, '');

export function MiSearchPopup({ open, doc, actions, ready, steps, onClose, onSearched }: {
  open: boolean; doc: MFDoc; actions: Actions;
  /** Storyboard 분석이 끝났는가(단계 보여 주기 포함) — 아니면 단계 카드 */
  ready: boolean; steps: MFStep[];
  onClose: () => void;
  /** 웹 검색을 시작했다(팝업은 닫히고 화면이 찾는 중으로) */
  onSearched: () => void;
}) {
  const flow = useFlow(open ? doc.sb_id : null);
  const saved = doc.ver != null;
  const rule = doc.analysis_mode === 'rule';
  const failed = doc.progress?.kind === 'analyze' ? doc.progress?.error : null;
  const h1 = ready ? (saved ? '검색어 · 조건 고치고 다시 검색' : '무엇을 검색할까요?') : 'Storyboard를 읽는 중이에요';
  const sub = !ready ? '다 읽으면 검색어와 검색 조건이 나타나요.'
    : failed ? (doc.warnings ?? []).slice(-1)[0] ?? `${failed}.`
      : rule ? '지금은 AI 분석을 쓸 수 없어 Storyboard 값으로 검색어를 만들었어요. 빼거나 더해 주세요.'
        : 'AI가 Storyboard의 고객사 · 업종 · 공간 · 요구에서 검색어를 만들었어요. 빼거나 더하면 돼요.';
  return (
    <Modal open={open} onClose={onClose} width={1040} height={740} ariaLabel="MI 검색"
      bodyStyle={{ padding: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden', background: 'var(--wm-bg)' }}>
      <div className="mis-head">
        <span className="mis-ic" aria-hidden><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round"><circle cx="11" cy="11" r="7" /><path d="M20 20l-4-4" /></svg></span>
        <span className="mis-titles">
          <span className="mis-h1">{h1}</span>
          <span className={cx('mis-sub', ready && (rule || failed) && 'mis-sub--warn')}>{sub}</span>
        </span>
        <span className="mis-sb" title={doc.sb_id}>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden><path d={SB_ICON} /></svg>
          {flow.data?.name ?? doc.sb_id}
        </span>
        <button type="button" className="mis-x" onClick={onClose} aria-label="닫기">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" aria-hidden><path d={X_PATH} /></svg>
        </button>
      </div>
      {ready
        ? <SearchForm key={`${doc.id}:${doc.progress?.job_id ?? ''}`} doc={doc} actions={actions} onClose={onClose} onSearched={onSearched} />
        : (
          <>
            <section className="mis-sec">
              <StepsCard title="AI가 Storyboard를 분석하고 있어요" steps={steps} />
              <span className="mis-note">닫아도 분석은 이어져요 · 다 읽으면 검색어와 검색 조건이 나타나요</span>
            </section>
            <Foot line="분석이 끝나면 웹 검색을 시작할 수 있어요" onClose={onClose} disabled />
          </>
        )}
    </Modal>
  );
}

/** 아래 줄(보드: h76 · 한 줄 13 · 닫기 h46 · 웹 검색 h46 + 돋보기) */
function Foot({ line, onClose, onSearch, disabled, busy, warn }: { line: string; onClose: () => void; onSearch?: () => void; disabled?: boolean; busy?: boolean; warn?: boolean }) {
  return (
    <div className="mis-foot">
      <span className={cx('mis-footline', warn && 'mis-footline--warn')}>{line}</span>
      <button type="button" className="mis-close" onClick={onClose}>닫기</button>
      <button type="button" className="mis-run" onClick={onSearch} disabled={disabled || busy} aria-busy={busy || undefined}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" aria-hidden><circle cx="11" cy="11" r="7" /><path d="M20 20l-4-4" /></svg>
        {busy ? '시작하는 중…' : '웹 검색'}
      </button>
    </div>
  );
}

/** AI 단계 카드(보드 MISearch loading: r16 · padding 22 24 · 줄 h44) */
export function StepsCard({ title, steps }: { title: string; steps: MFStep[] }) {
  return (
    <div className="mis-steps" role="status" aria-live="polite" data-testid="mif-steps">
      <span className="mis-steps__title">
        <svg className="mif-spin" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" aria-hidden><path d={SPIN} /></svg>
        {title}
      </span>
      {steps.map((s) => (
        <div key={s.key} className="mis-step" data-state={s.state}>
          <span className={cx('mis-dot', `mis-dot--${s.state}`)} aria-hidden />
          <span className="mis-step__t">{s.label}</span>
          <span className="mis-step__note">{s.state === 'done' || s.state === 'error' ? s.note : ''}</span>
        </div>
      ))}
    </div>
  );
}

/** 검색어 · 검색 조건(보드 MISearch ready) */
function SearchForm({ doc, actions, onClose, onSearched }: { doc: MFDoc; actions: Actions; onClose: () => void; onSearched: () => void }) {
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
  // 닫으면(웹 검색 없이) 모아 둔 고친 값을 바로 보낸다
  useEffect(() => () => { if (pending.current) void send(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

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
    try { await send(); await actions.search(); onSearched(); } catch (e) { toast((e as Error).message || '검색을 시작하지 못했어요'); setBusy(false); }
  };
  const saved = doc.ver != null;
  const rule = doc.analysis_mode === 'rule';
  const opts: Array<{ k: string; vs: Array<{ t: string; on: boolean; pick: () => void }> }> = [
    { k: '기간', vs: PERIODS.map((p) => ({ t: p, on: filters.period === p, pick: () => setPeriod(p) })) },
    { k: '출처', vs: SOURCE_TYPES.map((t) => ({ t, on: (filters.sourceTypes ?? []).includes(t), pick: () => toggleType(t) })) },
  ];
  if (saved) {
    opts.push({ k: `기존 ${doc.code ?? 'MI'}`, vs: [
      { t: `담은 정보 ${doc.counts.kept ?? 0}개 유지 · 새로 찾은 것만 더하기`, on: keep, pick: () => setKeepPrev(true) },
      { t: '처음부터 다시', on: !keep, pick: () => setKeepPrev(false) },
    ] });
  }
  const line = !nq ? '검색어를 하나 이상 넣어 주세요' : noTypes ? '출처를 하나 이상 골라 주세요'
    : `검색어 ${nq}개 · 1–2분 · 찾은 정보는 MI 화면에 바로 모이고, 거기서 담을 것을 골라요`;
  return (
    <>
      <section className="mis-sec">
        <div className="mis-basis">
          <span className="mis-aitag">{!rule && <svg width="11" height="11" viewBox="0 0 24 24" fill="currentColor" aria-hidden><path d={SPARK} /></svg>}{rule ? '규칙' : 'AI 분석'}</span>
          <span className="mis-basis__label">Storyboard에서 읽은 것</span>
          {(doc.basis ?? []).map((b) => <span key={b.k} className="mis-basis__chip"><b>{b.k}</b>{b.v}</span>)}
        </div>
        <div className="mis-cols">
          {GROUPS.map((g) => <QueryCol key={g.key} label={g.label} gkey={g.key} rows={qs[g.key]} onToggle={(i) => toggle(g.key, i)} onAdd={(t) => add(g.key, t)} />)}
        </div>
        <div className="mis-opts">
          {opts.map((o) => (
            <div key={o.k} className="mis-opt" role="group" aria-label={o.k}>
              <span className="mis-opt__k">{o.k}</span>
              <div className="mis-opt__vs">
                {o.vs.map((v) => <button key={v.t} type="button" className={cx('mis-chip', v.on && 'mis-chip--on')} aria-pressed={v.on} onClick={v.pick}>{v.t}</button>)}
              </div>
            </div>
          ))}
        </div>
      </section>
      <Foot line={line} warn={!nq || noTypes} onClose={onClose} onSearch={search} busy={busy} disabled={!nq || noTypes} />
    </>
  );
}

function QueryCol({ label, gkey, rows, onToggle, onAdd }: {
  label: string; gkey: GroupKey; rows: MFQuery[]; onToggle: (i: number) => void; onAdd: (t: string) => boolean;
}) {
  const [draft, setDraft] = useState('');
  const n = nOn(rows);
  const id = `mis-add-${gkey}`;
  const commit = () => { if (draft.trim() && onAdd(draft)) setDraft(''); };
  return (
    <div className="mis-col" data-group={gkey}>
      <div className="mis-col__head"><span className="mis-col__t">{label}</span><span className="mis-col__n">검색어 {n}</span></div>
      <div className="mis-qs">
        {rows.map((q, i) => {
          const off = !(q.on ?? true);
          return (
            <span key={`${q.text}-${i}`} className={cx('mis-q', off && 'mis-q--off')} data-by={q.by}>
              <span className="mis-q__t" title={q.text}>{q.text}</span>
              <button type="button" className="mis-q__x" onClick={() => onToggle(i)} aria-label={`${off ? '다시 넣기' : '빼기'} · ${q.text}`}>
                <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" aria-hidden><path d={off ? PLUS_PATH : X_PATH} /></svg>
              </button>
            </span>
          );
        })}
      </div>
      <div className="mis-add">
        <label htmlFor={id} className="cd-sr">{label} 검색어 추가</label>
        <input id={id} placeholder="+ 검색어" value={draft} maxLength={40} onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && !e.nativeEvent.isComposing) { e.preventDefault(); commit(); } if (e.key === 'Escape' && draft) { e.preventDefault(); setDraft(''); } }}
          onBlur={commit} />
      </div>
    </div>
  );
}
