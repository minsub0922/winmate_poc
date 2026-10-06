/** MI0 — 분석 작업 목록 `/mi?status=&q=&segment=&sort=` (§4.2) */
import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { useShellPage } from '@/shell';
import { PathIcon, Skeleton, cx, toast, useConfirm } from '@/ui';
import { cancelJob } from '@/api/jobs';
import {
  deleteAnalysis, duplicateAnalysis, errText, listMore, startRun, useAnalysisList, useSegments,
  type AnalysisList, type AnalysisListItem, type MenuItem,
} from '../api';
import { Ic, P, SECTION } from '../parts';

const FILTERS: Array<{ value: string; label: string; key: 'all' | 'run' | 'done' | 'upd' | 'draft' }> = [
  { value: 'all', label: '전체', key: 'all' }, { value: 'run', label: '진행 중', key: 'run' }, { value: 'done', label: '완료', key: 'done' },
  { value: 'upd', label: '업데이트 필요', key: 'upd' }, { value: 'draft', label: '작성 중', key: 'draft' },
];
const SORTS = [{ value: 'updated_desc', label: '최근 수정순' }, { value: 'created_desc', label: '최근 만든 순' }, { value: 'title', label: '이름순' }];

export function ListPage() {
  useShellPage({ section: SECTION, title: '분석 작업 목록', hasTask: false, sidebarGroup: 'mi' });
  const [sp, setSp] = useSearchParams();
  const nav = useNavigate();
  const qc = useQueryClient();
  const { confirm, dialog } = useConfirm();
  const status = sp.get('status') ?? 'all';
  const segment = sp.get('segment') ?? '';
  const sort = sp.get('sort') ?? 'updated_desc';
  const q = sp.get('q') ?? '';
  const [text, setText] = useState(q);
  useEffect(() => { setText(q); }, [q]);
  useEffect(() => {
    if (text === q) return;
    const t = window.setTimeout(() => set({ q: text || null }), 300);
    return () => window.clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [text]);

  function set(p: Record<string, string | null>) {
    const next = new URLSearchParams(sp);
    for (const [k, v] of Object.entries(p)) { if (v) next.set(k, v); else next.delete(k); }
    setSp(next, { replace: true });
  }

  const params = { status, segment, q, sort };
  const [poll, setPoll] = useState<number | false>(false);
  const list = useAnalysisList(params, poll);
  const [more, setMore] = useState<AnalysisListItem[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  useEffect(() => { setMore([]); setCursor(list.data?.next_cursor ?? null); }, [list.data]);
  const rows = useMemo(() => [...(list.data?.items ?? []), ...more], [list.data, more]);
  useEffect(() => { setPoll(rows.some((r) => r.status === 'queued' || r.status === 'running') ? 10_000 : false); }, [rows]);
  const segs = useSegments();

  const refresh = () => qc.invalidateQueries({ queryKey: ['mi', 'list'] });

  async function loadMore() {
    if (!cursor) return;
    try {
      const r = await listMore(params, cursor);
      setMore((m) => [...m, ...r.items]);
      setCursor(r.next_cursor ?? null);
    } catch (e) { toast(errText(e)); }
  }

  async function rerun(id: string, mode: 'changed_only' | 'full' | 'resume') {
    try {
      await startRun(id, { mode });
      nav(`/mi/${id}/run`);
    } catch (e) {
      if (e && (e as { code?: string }).code === 'RUN_IN_PROGRESS') { nav(`/mi/${id}/run`); return; }
      toast(errText(e));
    }
  }

  async function onAction(r: AnalysisListItem) {
    if (r.action.kind === 'rerun') return rerun(r.id, 'changed_only');
    if (r.action.kind === 'retry') return rerun(r.id, 'resume');
    nav(r.action.route);
  }

  async function onMenu(r: AnalysisListItem, m: MenuItem) {
    if (m.key === 'changed_only') return rerun(r.id, 'changed_only');
    if (m.key === 'full') return rerun(r.id, 'full');
    if (m.key === 'duplicate') {
      try {
        const d = await duplicateAnalysis(r.id);
        nav(`/mi/${d.id}/input`);
      } catch (e) { toast(errText(e)); }
      return;
    }
    if (m.key === 'stop') {
      if (r.current_job_id) await cancelJob(r.current_job_id);
      void refresh();
      return;
    }
    if (m.key === 'delete') {
      if (await confirm({ title: '이 분석을 지울까요?', message: '지운 분석은 되돌릴 수 없어요.', tone: 'danger', confirmLabel: '지우기' })) {
        try { await deleteAnalysis(r.id); void refresh(); } catch (e) { toast(errText(e)); }
      }
      return;
    }
    if (m.route) nav(m.route);
  }

  async function rerunAll(ids: string[]) {
    let first: string | null = null;
    for (const id of ids) {
      try {
        await startRun(id, { mode: 'changed_only' });
        first = first ?? id;
      } catch (e) {
        if ((e as { code?: string }).code === 'RUN_IN_PROGRESS') first = first ?? id;
        else toast(errText(e));
      }
    }
    if (first) nav(`/mi/${first}/run`);
  }

  const counts = list.data?.counts;
  const segName = segs.data?.items.find((s) => s.code === segment)?.short;
  return (
    <div className="mi-list">
      <div className="mi-list__head">
        <div>
          <h1 className="mi-list__title">Market Intelligence 작업</h1>
          <div className="mi-list__sum" data-testid="mi0-header">{list.data?.header ?? ' '}</div>
        </div>
        <div className="mi-row" style={{ gap: 8 }}>
          <Link to="/mi/new/industry" className="mi-btn mi-btn--h42"><Ic d={P.grid} size={15} w={2} />업종 인사이트로 시작</Link>
          <Link to="/mi/new" className="mi-btn mi-btn--primary mi-btn--h42" style={{ fontSize: 13.5, padding: '0 16px', gap: 7 }}>
            <Ic d={P.plus} size={15} w={2.4} />새 분석
          </Link>
        </div>
      </div>

      <div className="mi-list__tools">
        <div className="mi-search">
          <Ic d={P.search} size={15} w={2} />
          <label htmlFor="mi-q" className="wm-sr-only">작업 검색</label>
          <input id="mi-q" value={text} onChange={(e) => setText(e.target.value)} placeholder="고객사 · 작업명 · 경쟁사 검색" />
        </div>
        <div className="mi-filters" role="tablist" aria-label="상태 필터">
          {FILTERS.map((f) => (
            <button key={f.value} type="button" role="tab" className="mi-filter" aria-selected={status === f.value}
              onClick={() => set({ status: f.value === 'all' ? null : f.value })}>
              <span>{f.label}</span><b>{counts ? counts[f.key] : ''}</b>
            </button>
          ))}
        </div>
        <div className="mi-grow" />
        <Dropdown label={segName ?? '업종 전체'} items={[{ value: '', label: '업종 전체' }, ...(segs.data?.items ?? []).map((s) => ({ value: s.code, label: s.short })),
          { value: 'GEN', label: '범용' }]} value={segment} onPick={(v) => set({ segment: v || null })} ariaLabel="업종 필터" />
        <Dropdown label={SORTS.find((s) => s.value === sort)?.label ?? '최근 수정순'} items={SORTS} value={sort}
          onPick={(v) => set({ sort: v === 'updated_desc' ? null : v })} ariaLabel="정렬" />
      </div>

      {list.data?.banner && <UpdBanner data={list.data} onRerun={rerunAll} />}

      <div className="mi-table-card" role="table" aria-label="분석 작업" aria-busy={list.isLoading}>
        <div className="mi-trow mi-trow--head" role="row">
          <span role="columnheader">작업</span><span role="columnheader">업종</span><span role="columnheader">분석 범위</span>
          <span role="columnheader">상태</span><span role="columnheader">연결된 제안서</span><span />
        </div>
        {list.isLoading && Array.from({ length: 4 }, (_, i) => (
          <div key={i} className="mi-trow" aria-hidden="true">
            <span><Skeleton w="60%" h={15} /><Skeleton w="35%" h={11} style={{ marginTop: 6 }} /></span>
            <Skeleton w={60} h={13} /><Skeleton w={120} h={13} /><Skeleton w={90} h={22} r={11} /><Skeleton w={110} h={13} /><span />
          </div>
        ))}
        {list.isError && <div className="mi-empty" role="alert">잠시 후 다시 시도해 주세요<button type="button" className="mi-mini" onClick={() => void list.refetch()}>다시 시도</button></div>}
        {!list.isLoading && !list.isError && rows.length === 0 && (
          <div className="mi-empty">
            {q || status !== 'all' || segment ? '찾는 분석이 없어요' : <>아직 분석이 없어요<Link to="/mi/new" className="mi-btn mi-btn--primary mi-btn--h42">새 분석</Link></>}
          </div>
        )}
        {rows.map((r) => <Row key={r.id} r={r} onAction={onAction} onMenu={onMenu} upd={list.data?.upd_changes?.[r.id] as { title?: string; summary?: string } | undefined} />)}
        {cursor && <div className="mi-more-rows"><button type="button" className="mi-mini" onClick={() => void loadMore()}>더 보기</button></div>}
      </div>

      <div className="mi-inds">
        <span className="mi-inds__label">업종 인사이트로 시작</span>
        <span className="mi-inds__basis">삼성 도입사례 {segs.data?.case_total ?? '—'}건 기준</span>
        <span className="mi-inds__sep" aria-hidden="true" />
        {(segs.data?.home ?? []).map((h) => {
          const it = h as { code: string; short: string; n: number };
          return <Link key={it.code} to={`/mi/new/industry?segment=${it.code}`} className="mi-indchip">{it.short}<b>{it.n}건</b></Link>;
        })}
        <Link to="/mi/new/industry" className="mi-link" style={{ height: 30, padding: '0 6px' }}>16개 업종 모두</Link>
      </div>
      {dialog}
    </div>
  );
}

const ST_ICON: Record<string, string> = { done: P.check, upd: P.refresh, draft: P.edit };

function Row({ r, onAction, onMenu, upd }: { r: AnalysisListItem; onAction: (r: AnalysisListItem) => void; onMenu: (r: AnalysisListItem, m: MenuItem) => void;
  upd?: { title?: string; summary?: string } }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => { if (!ref.current?.contains(e.target as Node)) setOpen(false); };
    const esc = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false); };
    document.addEventListener('mousedown', close);
    document.addEventListener('keydown', esc);
    return () => { document.removeEventListener('mousedown', close); document.removeEventListener('keydown', esc); };
  }, [open]);
  const tone = r.status_tone;
  const head = r.changes_head as { title?: string; summary?: string } | null | undefined ?? upd;
  return (
    <div className={cx('mi-trow', open && 'mi-trow--menu')} role="row" data-status={r.status} data-id={r.id} ref={ref}>
      <div role="cell" style={{ display: 'flex', flexDirection: 'column', gap: 3, minWidth: 0 }}>
        <div className="mi-row" style={{ gap: 6 }}>
          <Link to={r.route} className="mi-trow__title">{r.title}</Link>
          {r.version > 0 && <span className="mi-ver">v{r.version}</span>}
        </div>
        <span className="mi-trow__sub">{r.sub}</span>
      </div>
      <span role="cell" className="mi-trow__ind">{r.segment_label}</span>
      <span role="cell" className={cx('mi-trow__scope', !r.scope_selected && 'mi-trow__scope--off')}>{r.scope_label}</span>
      <div role="cell" style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: 4, minWidth: 0 }}>
        <span className={cx('mi-st', `mi-st--${tone}`)}>
          {tone === 'run' ? <RunDot /> : <PathIcon d={ST_ICON[tone] ?? P.edit} size={11} strokeWidth={tone === 'done' ? 3 : 2.5} />}
          <span>{r.status_label}</span>
        </span>
        <span className="mi-trow__note">{r.note}</span>
      </div>
      <div role="cell" className="mi-row" style={{ gap: 7 }}>
        {r.proposal_title
          ? <><Ic d={P.monitor} size={14} w={2} /><span className="mi-trow__prop">{r.proposal_title}</span></>
          : <span className="mi-trow__none">아직 없음</span>}
      </div>
      <div role="cell" className="mi-row" style={{ justifyContent: 'flex-end', gap: 6, position: 'static' }}>
        <button type="button" className={cx('mi-act', tone === 'upd' && 'mi-act--primary')} onClick={() => onAction(r)}>{r.action.label}</button>
        <button type="button" className="mi-more" aria-label={`${r.title} 메뉴`} aria-haspopup="menu" aria-expanded={open} onClick={() => setOpen((o) => !o)}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><circle cx="5" cy="12" r="1.8" /><circle cx="12" cy="12" r="1.8" /><circle cx="19" cy="12" r="1.8" /></svg>
        </button>
      </div>
      {open && (
        <div className="mi-menu mi-rowmenu" role="menu" aria-label={`${r.title} 작업 메뉴`}>
          {r.status === 'upd' && head && (
            <div className="mi-menu__head"><b>{head.title}</b><span>{head.summary}</span></div>
          )}
          {r.menu.map((m) => (
            <button key={m.key} type="button" role="menuitem" className={cx('mi-menu__item', m.highlight && 'mi-menu__item--hi')}
              onClick={() => { setOpen(false); onMenu(r, m); }}>
              <b>{m.label}</b><small>{m.hint}</small>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function RunDot() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" aria-hidden="true" className="mi-spin">
      <circle cx="12" cy="12" r="9" stroke="var(--wm-brand-sel-line)" strokeWidth="3" />
      <path d="M12 3a9 9 0 0 1 9 9" stroke="var(--wm-brand)" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
}

function UpdBanner({ data, onRerun }: { data: AnalysisList; onRerun: (ids: string[]) => void }) {
  const b = data.banner!;
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => { if (!ref.current?.contains(e.target as Node)) setOpen(false); };
    document.addEventListener('mousedown', close);
    return () => document.removeEventListener('mousedown', close);
  }, [open]);
  const changes = data.upd_changes as Record<string, { title?: string; summary?: string }>;
  const titleOf = (id: string) => data.items.find((i) => i.id === id)?.title ?? '';
  return (
    <div className="mi-updband" ref={ref} data-testid="mi0-banner">
      <div className="mi-updband__icon"><PathIcon d={P.refresh} size={15} strokeWidth={2.2} /></div>
      <div className="mi-updband__text"><b>{b.title}</b> <span>{b.text}</span></div>
      <button type="button" className="mi-link" style={{ height: 32, padding: '0 10px' }} aria-expanded={open} onClick={() => setOpen((o) => !o)}>바뀐 자료 보기</button>
      <button type="button" className="mi-act mi-act--primary" style={{ height: 32, padding: '0 12px', fontSize: 12.5 }} disabled={busy}
        onClick={async () => { setBusy(true); try { await onRerun(b.target_ids ?? []); } finally { setBusy(false); } }}>{b.n}건 다시 분석</button>
      {open && (
        <div className="mi-menu" role="dialog" aria-label="바뀐 자료" style={{ width: 360, right: 12 }}>
          {(b.target_ids ?? []).map((id) => (
            <div key={id} className="mi-menu__head" style={{ borderBottom: 'none' }}>
              <b>{titleOf(id) || '분석'} · {changes?.[id]?.title}</b>
              <span>{changes?.[id]?.summary}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function Dropdown({ label, items, value, onPick, ariaLabel }: { label: string; items: Array<{ value: string; label: string }>; value: string; onPick: (v: string) => void; ariaLabel: string }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => { if (!ref.current?.contains(e.target as Node)) setOpen(false); };
    const esc = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false); };
    document.addEventListener('mousedown', close);
    document.addEventListener('keydown', esc);
    return () => { document.removeEventListener('mousedown', close); document.removeEventListener('keydown', esc); };
  }, [open]);
  return (
    <div className="mi-select" ref={ref}>
      <button type="button" className="mi-select__btn" aria-haspopup="menu" aria-expanded={open} aria-label={ariaLabel} onClick={() => setOpen((o) => !o)}>
        {label}<Ic d={P.chevD} size={12} w={2.4} />
      </button>
      {open && (
        <div className="mi-menu" role="menu" aria-label={ariaLabel}>
          {items.map((it) => (
            <button key={it.value || 'all'} type="button" role="menuitemradio" aria-checked={value === it.value} className="mi-menu__item"
              onClick={() => { setOpen(false); onPick(it.value); }}>{it.label}</button>
          ))}
        </div>
      )}
    </div>
  );
}
