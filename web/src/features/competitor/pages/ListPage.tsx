/** CA0 — 경쟁사 분석 작업 목록(§4.2). 실명은 어디에도 없다. */
import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Button, Icon, Modal, PathIcon, Spinner, cx } from '@/ui';
import {
  createAnalysis, errText, listAnalyses, miBundleForCompetitor, miWithCompetitors, qk, savedDefinitions, startRun, type ListItem, type MiItem,
} from '../api';
import { useCaShell, useDebounced } from '../hooks';
import { Band } from '../parts';

const SORTS = [
  { value: 'updated_desc', label: '최근 수정순' },
  { value: 'created_desc', label: '최근 만든순' },
  { value: 'title', label: '제목순' },
];
const IN_ICON: Record<string, string> = {
  free: 'M4 20h4L19 9l-4-4L4 16v4z',
  requirements: 'M9 4h6v3H9z M7 5.5H5V21h14V5.5h-2 M8.5 12h7 M8.5 16h5',
  mi: 'M4 20h16 M7 16V10 M12 16V5 M17 16v-7',
};

export function ListPage() {
  useCaShell({ list: true, current: 0 });
  const nav = useNavigate();
  const qc = useQueryClient();
  const [sp, setSp] = useSearchParams();
  const status = sp.get('status') || 'all';
  const sort = sp.get('sort') || 'updated_desc';
  const [q, setQ] = useState(sp.get('q') ?? '');
  const dq = useDebounced(q, 300);
  useEffect(() => {
    const next = new URLSearchParams(sp);
    if (dq) next.set('q', dq); else next.delete('q');
    if (next.toString() !== sp.toString()) setSp(next, { replace: true });
  }, [dq]); // eslint-disable-line react-hooks/exhaustive-deps

  const params = { status: status === 'all' ? '' : status, q: dq, sort };
  const list = useQuery({ queryKey: qk.list(params), queryFn: () => listAnalyses(params), refetchInterval: 15_000 });
  const defs = useQuery({ queryKey: ['ca', 'ext', 'definitions'], queryFn: () => savedDefinitions(), staleTime: 60_000, retry: false });
  const mis = useQuery({ queryKey: ['ca', 'ext', 'mi'], queryFn: () => miWithCompetitors(), staleTime: 60_000, retry: false });
  const [pickMi, setPickMi] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [sortOpen, setSortOpen] = useState(false);
  const sortRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!sortOpen) return;
    const close = (e: MouseEvent) => { if (!sortRef.current?.contains(e.target as Node)) setSortOpen(false); };
    window.addEventListener('mousedown', close);
    return () => window.removeEventListener('mousedown', close);
  }, [sortOpen]);

  const data = list.data;
  const counts = data?.counts;
  const setParam = (k: string, v: string | null) => {
    const next = new URLSearchParams(sp);
    if (v) next.set(k, v); else next.delete(k);
    setSp(next, { replace: true });
  };

  async function rerun() {
    const b = data?.banner;
    if (!b) return;
    setBusy('rerun');
    setErr(null);
    try {
      await startRun(b.target_id, 'changed_only', b.competitor_ids?.length ? b.competitor_ids : null);
      void qc.invalidateQueries({ queryKey: ['ca'] });
      nav(`/competitor/${b.target_id}/run`);
    } catch (e) {
      setErr(errText(e, '다시 분석하지 못했어요'));
    } finally {
      setBusy(null);
    }
  }

  async function fromMi(m: MiItem) {
    setBusy(m.id);
    setErr(null);
    try {
      const bundle = await miBundleForCompetitor(m.id);
      const a = await createAnalysis({ input_mode: 'mi', mi_bundle: bundle as unknown as Record<string, unknown>, mi_ref: { analysis_id: m.id, version: m.version ?? null } });
      setPickMi(false);
      void qc.invalidateQueries({ queryKey: ['ca', 'list'] });
      nav(a.route || `/competitor/${a.id}/finding`);
    } catch (e) {
      setErr(errText(e, 'MI 작업에서 시작하지 못했어요'));
    } finally {
      setBusy(null);
    }
  }

  const tabs = [
    { value: 'all', label: '전체', n: counts?.all ?? 0 },
    { value: 'done', label: '완료', n: counts?.done ?? 0 },
    { value: 'check', label: '확인 중', n: counts?.check ?? 0 },
  ];
  const defCount = defs.data ? `${defs.data.length}건` : '—';
  const miCount = mis.data ? `${mis.data.length}건` : '—';

  return (
    <div className="ca-wide">
      <div className="ca-lhead">
        <div>
          <h1>경쟁사 분석 작업</h1>
          <p>{data?.header || '분석 0건 · 업데이트 필요 0건 · 경쟁사는 실명 없이 A · B · C 로 표기해요'}</p>
        </div>
        <Link to="/competitor/legacy/new" className="ca-new"><Icon name="plus" size={15} strokeWidth={2.4} /><span>새 분석</span></Link>
      </div>

      <div className="ca-tools">
        <div className="ca-search">
          <Icon name="search" size={15} color="var(--wm-text-subtle)" />
          <label htmlFor="ca-q" className="wm-sr-only">작업 검색</label>
          <input id="ca-q" placeholder="고객사 · 작업명 · 업종 검색" value={q} onChange={(e) => setQ(e.target.value)} />
        </div>
        <div className="ca-pills" role="tablist" aria-label="상태 필터">
          {tabs.map((t) => (
            <button key={t.value} type="button" role="tab" aria-selected={status === t.value} className="ca-pill"
              onClick={() => setParam('status', t.value === 'all' ? null : t.value)}>
              <span>{t.label}</span><b>{t.n}</b>
            </button>
          ))}
        </div>
        <span className="ca-grow" />
        <div className="ca-sort" ref={sortRef}>
          <button type="button" aria-haspopup="menu" aria-expanded={sortOpen} onClick={() => setSortOpen((v) => !v)}>
            {SORTS.find((s) => s.value === sort)?.label ?? '최근 수정순'}<Icon name="chevronDown" size={12} strokeWidth={2.4} color="var(--wm-text-muted)" />
          </button>
          {sortOpen && (
            <div className="ca-menu" role="menu">
              {SORTS.map((s) => (
                <button key={s.value} type="button" role="menuitemradio" aria-checked={sort === s.value}
                  onClick={() => { setParam('sort', s.value === 'updated_desc' ? null : s.value); setSortOpen(false); }}>{s.label}</button>
              ))}
            </div>
          )}
        </div>
      </div>

      {data?.banner && (
        <div className="ca-upd" role="status">
          <span className="ca-upd__icon"><Icon name="refresh" size={15} strokeWidth={2.2} /></span>
          <div className="ca-upd__text"><b>{data.banner.title}</b> <span>{data.banner.text}</span></div>
          <Button h={32} variant="primary" onClick={rerun} loading={busy === 'rerun'}>다시 분석</Button>
        </div>
      )}
      {err && <div style={{ marginTop: 12 }}><Band tone="danger">{err}</Band></div>}

      <div className="ca-tbl" role="table" aria-label="경쟁사 분석 작업">
        <div className="ca-tbl__grid ca-tbl__head" role="row">
          <span role="columnheader">작업</span><span role="columnheader">입력 방식</span><span role="columnheader">경쟁사 수</span>
          <span role="columnheader">상태</span><span role="columnheader">보낸 곳</span><span role="columnheader">열기</span>
        </div>
        {list.isLoading && <div className="ca-tbl__empty"><Spinner /></div>}
        {list.isError && <div className="ca-tbl__empty">목록을 불러오지 못했어요 · <button type="button" className="ca-linkbtn ca-linkbtn--brand" onClick={() => list.refetch()}>다시 시도</button></div>}
        {data && !data.items.length && (
          <div className="ca-tbl__empty">{dq || status !== 'all' ? '조건에 맞는 작업이 없어요' : '아직 경쟁사 분석이 없어요 · 새 분석으로 시작해 보세요'}</div>
        )}
        {data?.items.map((r) => <Row key={r.id} r={r} />)}
      </div>

      <div className="ca-starts">
        <b>다른 곳에서 시작</b>
        <small>고객사 · 업종 · 장소 · 제품을 그 작업에서 가져와요</small>
        <span className="ca-starts__sep" />
        <Link to="/competitor/legacy/new?input=requirements" className="ca-start">고객 요구사항 정의서에서<b>{defCount}</b></Link>
        <button type="button" className="ca-start" onClick={() => setPickMi(true)}>MI 작업의 경쟁사에서<b>{miCount}</b></button>
      </div>
      <div className="ca-lnote">
        <Icon name="info" size={13} color="var(--wm-text-subtle)" />
        <span>결과는 MI 작업의 경쟁사 영역 · 제안서 Why Samsung · Storyboard 비교 기준으로 보내요 · 고객 제출물엔 익명(경쟁사 A · B · C)으로 들어가요</span>
      </div>

      <Modal open={pickMi} onClose={() => setPickMi(false)} title="MI 작업의 경쟁사에서 시작" width={560}>
        <div className="ca-pick" role="list" aria-label="경쟁사가 있는 MI 작업">
          {mis.isLoading && <Spinner />}
          {mis.isError && <span className="ca-muted">MI 작업을 불러오지 못했어요</span>}
          {mis.data && !mis.data.length && <span className="ca-muted">경쟁사가 있는 MI 작업이 없어요</span>}
          {mis.data?.map((m) => (
            <button key={m.id} type="button" role="listitem" className="ca-pick__row" onClick={() => fromMi(m)} disabled={!!busy}>
              <span className="ca-pick__main">
                <span className="ca-pick__title">{m.title}</span>
                <span className="ca-pick__sub">{[m.segment_label, m.sub].filter(Boolean).join(' · ')}</span>
              </span>
              {busy === m.id ? <Spinner /> : <Icon name="chevronRight" size={14} color="var(--wm-text-subtle)" />}
            </button>
          ))}
        </div>
        <p className="ca-hint" style={{ marginTop: 10 }}>그 MI 작업의 경쟁사는 켜짐 · 고정으로 들어가고, 새 후보만 더 찾아요.</p>
      </Modal>
    </div>
  );
}

function Row({ r }: { r: ListItem }) {
  const tone = r.status_tone;
  return (
    <div className="ca-tbl__grid ca-tbl__row" role="row" data-id={r.id}>
      <div className="ca-tbl__title" role="cell">
        <Link to={r.action.route || r.route}>{r.title}</Link>
        <span>{r.sub}</span>
      </div>
      <span className="ca-tbl__input" role="cell"><PathIcon d={IN_ICON[r.input_mode] ?? IN_ICON.free} size={12} />{r.input_label}</span>
      <span className={cx('ca-tbl__count', r.count_unit === '후보' && 'ca-tbl__count--gray')} role="cell">
        {r.count_label === '—' ? <span>—</span> : <><b>{r.count_label}</b><span>{r.count_unit}</span></>}
      </span>
      <div className="ca-tbl__st" role="cell">
        <span className={cx('ca-stchip', tone === 'done' && 'ca-stchip--done', tone === 'upd' && 'ca-stchip--upd')}>
          {tone === 'done' && <Icon name="check" size={11} strokeWidth={3} />}
          {tone === 'check' && <Ring />}
          {tone === 'upd' && <Icon name="refresh" size={11} strokeWidth={2.6} />}
          <span>{r.status_label}</span>
        </span>
        <span className="ca-tbl__note">{r.note}</span>
      </div>
      <div className="ca-tbl__sent" role="cell">
        {r.sent_label
          ? <><PathIcon d="M4 12h12 M11 7l5 5-5 5 M20 5v14" size={14} color="var(--wm-text-muted)" /><span>{r.sent_label}</span></>
          : <span className="ca-subtle">아직 없음</span>}
      </div>
      <div className="ca-tbl__act" role="cell">
        <Link to={r.action.route || r.route}>{r.action.label}<Icon name="chevronRight" size={12} strokeWidth={2.4} /></Link>
      </div>
    </div>
  );
}

function Ring() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle cx="12" cy="12" r="9" stroke="var(--wm-brand-sel-line)" strokeWidth="3" />
      <path d="M12 3a9 9 0 0 1 9 9" stroke="var(--wm-brand)" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
}

export default ListPage;
