/** CA2 — 경쟁사 확인(§4.6). 스위치 = 고정(다시 찾기 · 다시 분석해도 유지), 직접 추가, `{n}곳으로 분석`. */
import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { useJob } from '@/api/jobs';
import { Icon, Spinner, cx } from '@/ui';
import { addCandidate, errCode, errText, qk, setCandidate, startRun, useAnalysis, useCandidates, type CompetitorView } from '../api';
import { useCaShell } from '../hooks';
import { Band, BigButton, CaPage, CandBadge, CmpName, ErrorCol, Flags, FootBar, Head, Letter, LoadingCol, SlotChip, Switch, slotList } from '../parts';

export function CandidatesPage() {
  const { id: aid = '' } = useParams();
  const nav = useNavigate();
  const qc = useQueryClient();
  const aq = useAnalysis(aid);
  const a = aq.data;
  const finding = a?.status === 'finding' || a?.status === 'ask';
  const cq = useCandidates(aid, finding ? 3000 : false);
  const out = cq.data;
  useCaShell({ aid, title: a?.title || '새 분석', current: 2, added: a?.added_refs });
  const [over, setOver] = useState<Record<string, boolean>>({});
  const [more, setMore] = useState(false);
  const [name, setName] = useState('');
  const [addErr, setAddErr] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);
  const [addJob, setAddJob] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const refresh = () => {
    void qc.invalidateQueries({ queryKey: qk.candidates(aid) });
    void qc.invalidateQueries({ queryKey: qk.analysis(aid) });
  };
  useJob(finding ? a?.current_job_id : null, { onDone: refresh });
  useJob(addJob, { onDone: () => { setAddJob(null); refresh(); } });
  useEffect(() => { if (a?.status === 'ask') nav(`/competitor/${aid}/ask`, { replace: true }); }, [a?.status, aid, nav]);
  useEffect(() => { setOver({}); }, [cq.dataUpdatedAt]);

  if (aq.isLoading || cq.isLoading) return <LoadingCol lines={6} />;
  if (aq.isError || cq.isError || !a || !out) return <ErrorCol message="후보를 불러오지 못했어요" onRetry={() => { void aq.refetch(); void cq.refetch(); }} />;

  const items = out.items.map((c) => (c.id in over ? { ...c, on: over[c.id] } : c));
  const onCount = items.filter((c) => c.on).length;
  const pageSize = out.page_size || 6;
  const shown = more ? items : items.slice(0, pageSize);
  const rest = items.length - shown.length;
  const found = slotList(out.slots ?? a.slots).filter((s) => s.found !== 'empty');
  const analyzing = a.status === 'analyzing';

  async function toggle(c: CompetitorView, on: boolean) {
    setOver((m) => ({ ...m, [c.id]: on }));
    try {
      await setCandidate(aid, c.id, on);
      refresh();
    } catch (e) {
      setOver((m) => { const n = { ...m }; delete n[c.id]; return n; });
      setErr(errText(e, '바꾸지 못했어요'));
    }
  }

  async function add() {
    const v = name.trim();
    if (!v) return;
    setAdding(true);
    setAddErr(null);
    try {
      const r = await addCandidate(aid, v);
      setName('');
      setMore(true);                                       // 새 행이 `더 보기` 뒤로 숨지 않게
      setAddJob(r.job_id);
      refresh();
    } catch (e) {
      setAddErr(errCode(e) === 'DUPLICATE_COMPETITOR' ? '이미 있는 경쟁사예요' : errText(e, '추가하지 못했어요'));
    } finally {
      setAdding(false);
    }
  }

  async function run() {
    setBusy(true);
    setErr(null);
    try {
      await startRun(aid, 'full');
      refresh();
      nav(`/competitor/${aid}/run`);
    } catch (e) {
      setErr(errText(e, '분석을 시작하지 못했어요'));
      setBusy(false);
    }
  }

  return (
    <CaPage>
      <Head kicker={out.header?.kicker || '확인 1 / 1'} title={out.header?.title || '이 경쟁사들로 분석할까요?'} desc={out.header?.desc} />
      <div className="ca-strip ca-strip--slim" role="group" aria-label="입력에서 읽은 것">
        {found.length ? found.map((s) => <SlotChip key={s.key} slot={s} small />) : <span className="ca-hint">읽은 것이 없어요</span>}
        <span className="ca-grow" />
        <Link to={`/competitor/${aid}/input${a.input_mode === 'requirements' ? '?input=requirements' : ''}`} className="ca-strip__link">바꾸기</Link>
      </div>
      <Flags chips={out.chips} />
      {finding && <Band>아직 찾는 중이에요 · 후보가 더 생길 수 있어요</Band>}
      {analyzing && <Band action={<Link to={`/competitor/${aid}/run`} className="ca-linkbtn ca-linkbtn--brand">분석 화면으로</Link>}>분석하는 중이에요 · 끝나면 다시 넣고 뺄 수 있어요</Band>}
      <div className="ca-sec" style={{ gap: 10 }}>
        <div className="ca-list" role="group" aria-label={`경쟁사 후보 ${items.length}곳`}>
          {!items.length && <div className="ca-empty">아직 후보가 없어요 · 아래에서 경쟁사를 직접 추가해 주세요</div>}
          {shown.map((c) => <CandRow key={c.id} c={c} onToggle={(v) => toggle(c, v)} disabled={analyzing} />)}
          {rest > 0 && <button type="button" className="ca-more" onClick={() => setMore(true)}>후보 {rest}곳 더 보기<Icon name="chevronDown" size={13} /></button>}
        </div>
        <div className="ca-addrow">
          {adding ? <Spinner label="추가하는 중" /> : <Icon name="plus" size={14} strokeWidth={2.4} color="var(--wm-text-muted)" />}
          <label htmlFor="ca-comp" className="wm-sr-only">경쟁사 직접 추가</label>
          <input id="ca-comp" placeholder="경쟁사 직접 추가 (회사명 · 제품명)" value={name} maxLength={80} disabled={adding || analyzing}
            onChange={(e) => { setName(e.target.value); setAddErr(null); }}
            onKeyDown={(e) => { if (e.key === 'Enter' && !e.nativeEvent.isComposing) { e.preventDefault(); void add(); } }} />
        </div>
        {addErr && <span className="ca-adderr" role="alert">{addErr}</span>}
        <div className="ca-lock">
          <Icon name="lock" size={13} strokeWidth={2.2} color="var(--wm-text-subtle)" />
          <span>실명은 이 작업 안에서만 보여요 · 내보내기엔 익명(경쟁사 A · B …) · 직접 넣거나 뺀 곳은 다시 분석해도 유지돼요</span>
        </div>
      </div>
      {err && <Band tone="danger">{err}</Band>}
      <FootBar back={{ to: `/competitor/${aid}/input${a.input_mode === 'requirements' ? '?input=requirements' : ''}` }}>
        <span className="ca-sel">선택 <b>{onCount}</b>곳</span>
        <BigButton onClick={run} loading={busy} disabled={onCount === 0 || finding || analyzing}
          disabledReason={finding ? '찾기가 끝나면 분석할 수 있어요' : analyzing ? '분석하는 중이에요' : '켜진 경쟁사가 없어요'}>{onCount}곳으로 분석</BigButton>
      </FootBar>
    </CaPage>
  );
}

function CandRow({ c, onToggle, disabled }: { c: CompetitorView; onToggle: (on: boolean) => void; disabled?: boolean }) {
  return (
    <div className={cx('ca-cand', !c.on && 'ca-cand--off')} data-letter={c.letter} data-status={c.status}>
      <Switch on={c.on} onChange={onToggle} label={`경쟁사 ${c.letter} ${c.on ? '빼기' : '넣기'}`} disabled={disabled} />
      <Letter letter={c.letter} off={!c.on} />
      <div className="ca-cand__who">
        <span className="ca-cand__name"><CmpName letter={c.letter} real={c.real_name} /></span>
        <span className="ca-cand__kind">{c.add_state === 'pending' ? '유형 찾는 중…' : (c.kind_label || (c.status === 'user' ? '직접 추가' : ''))}</span>
      </div>
      <div className="ca-cand__ev" title={(c.chips ?? []).join(' · ')}>
        {(c.chips ?? []).slice(0, (c.chips ?? []).length > 3 ? 2 : 3).map((p) => <span key={p} className="ca-ev">{p}</span>)}
        {(c.chips ?? []).length > 3 && <span className="ca-ev">+{(c.chips ?? []).length - 2}</span>}
      </div>
      <span className="ca-cand__why" title={c.why}>{c.why}</span>
      <span className="ca-cand__badge"><CandBadge c={c} /></span>
      <span className="ca-cand__conf">{c.confidence_label}</span>
    </div>
  );
}

export default CandidatesPage;
