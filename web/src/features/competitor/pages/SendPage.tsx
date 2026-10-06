/** CA5 — 저장 · 보내기(§4.9). MI 합치기 · 제안서 Why Samsung · Storyboard 비교 기준 · 리포트 저장 + 익명 스위치. */
import { useState, type ReactNode } from 'react';
import { Link, useNavigate, useParams } from 'react-router';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Button, Icon, Modal, PathIcon, Spinner, cx } from '@/ui';
import {
  createHandoff, errText, fileDownloadUrl, getBundle, miByCustomer, miGet, miImport, patchAnalysis, patchHandoff, proposalImport, qk,
  recentProposals, recentStoryboards, startExport, storyboardImport, useAnalysis, waitJob, type ProposalItem, type StoryboardItem,
} from '../api';
import { useCaShell } from '../hooks';
import { Band, BigButton, CaPage, ErrorCol, FootBar, Head, LoadingCol, Switch } from '../parts';

type CardKey = 'mi' | 'proposal' | 'storyboard' | 'report';
type CardState = { busy?: boolean; ok?: string | null; err?: string | null; href?: string | null };

export function SendPage() {
  const { id: aid = '' } = useParams();
  const nav = useNavigate();
  const qc = useQueryClient();
  const aq = useAnalysis(aid);
  const a = aq.data;
  useCaShell({ aid, title: a?.title, current: 4, complete: true, added: a?.added_refs });
  const customer = a?.customer_name ?? null;
  const mi = useQuery({
    queryKey: ['ca', 'ext', 'mi-target', aid, a?.mi_ref?.analysis_id ?? null, customer],
    enabled: !!a,
    retry: false,
    queryFn: async () => {
      if (a?.mi_ref?.analysis_id) {
        const m = await miGet(a.mi_ref.analysis_id).catch(() => null);
        if (m) return { id: m.id, title: m.title };
      }
      if (!customer) return null;
      const list = await miByCustomer(customer);
      const m = list[0];
      return m ? { id: m.id, title: m.title } : null;
    },
  });
  const [st, setSt] = useState<Record<CardKey, CardState>>({ mi: {}, proposal: {}, storyboard: {}, report: {} });
  const [ask, setAsk] = useState(false);
  const [pick, setPick] = useState<null | { kind: 'proposal'; named: boolean | null } | { kind: 'storyboard' }>(null);
  const [anonBusy, setAnonBusy] = useState(false);
  const set = (k: CardKey, s: CardState) => setSt((m) => ({ ...m, [k]: s }));

  if (aq.isLoading) return <LoadingCol lines={5} />;
  if (aq.isError || !a) return <ErrorCol message="작업을 찾지 못했어요" onRetry={() => aq.refetch()} />;
  const letters = a.letters_on ?? [];
  const lettersText = letters.length ? `경쟁사 ${letters.join(' · ')}` : '경쟁사 A · B …';
  const hasResult = a.version > 0;

  // ── 카드 1: MI 작업에 합치기 ──
  async function toMi() {
    set('mi', { busy: true });
    let hof: string | null = null;
    try {
      const target = mi.data ?? null;
      const h = await createHandoff(aid, { target: 'mi', target_id: target?.id ?? null, target_title: target?.title ?? null });
      hof = h.handoff_id ?? null;
      const bundle = await getBundle(aid, 'mi', hof);
      const r = await miImport({ analysis_id: target?.id ?? null, customer_name: customer, ca_bundle: bundle as unknown as Record<string, unknown> });
      const j = await waitJob(r.job_id, 90_000);
      if (j.status !== 'succeeded') throw new Error(j.error?.message || 'MI 작업에 넣지 못했어요');
      const miTitle = target?.title ?? null;
      if (hof) await patchHandoff(aid, hof, { status: 'delivered', target_id: r.analysis_id, target_title: miTitle });
      void qc.invalidateQueries({ queryKey: ['ca'] });
      set('mi', { ok: 'MI 작업에 넣었어요' });
      nav(r.revision_id ? `/mi/${r.analysis_id}/revise` : `/mi/${r.analysis_id}/result?tab=competitor`);
    } catch (e) {
      if (hof) await patchHandoff(aid, hof, { status: 'failed' }).catch(() => undefined);
      set('mi', { err: `${errText(e, 'MI 작업에 넣지 못했어요')} · 다시 시도해 주세요` });
    }
  }

  // ── 카드 2: 제안서 Why Samsung ──
  function toProposal() {
    if (!a!.anonymize) { setAsk(true); return; }
    setPick({ kind: 'proposal', named: null });
  }
  async function sendProposal(p: ProposalItem | null, named: boolean | null) {
    setPick(null);
    set('proposal', { busy: true });
    let hof: string | null = null;
    try {
      if (!p) {
        // 새 제안서: 유형을 고르기 전엔 섹션이 없어 가져오기가 TYPE_REQUIRED 로 막힌다 — 넘김 기록만 만들고 제안서 시작 화면으로 넘긴다.
        // 제안서는 `?handoff=hof_…&link=ca_…&feature=competitor` 를 연결 자료로 받아 유형을 고르면 Why Samsung 섹션에 넣는다(통합 규칙).
        const h = await createHandoff(aid, { target: 'proposal_why', target_id: null, target_title: null,
          confirm: named === null ? null : { real_names: named } });
        hof = h.handoff_id ?? null;
        if (!hof) throw new Error('넘김 기록을 만들지 못했어요');
        await patchHandoff(aid, hof, { status: 'delivered', target_id: null, target_title: '새 제안서' }).catch(() => undefined);
        void qc.invalidateQueries({ queryKey: ['ca'] });
        set('proposal', { ok: '새 제안서로 시작해요' });
        nav(`/proposal/new?handoff=${encodeURIComponent(hof)}&link=${encodeURIComponent(aid)}&feature=competitor`);
        return;
      }
      const target = p;
      const h = await createHandoff(aid, { target: 'proposal_why', target_id: target.id, target_title: target.title ?? null,
        confirm: named === null ? null : { real_names: named } });
      hof = h.handoff_id ?? null;
      if (!hof) throw new Error('넘김 기록을 만들지 못했어요');
      const r = await proposalImport(target.id, { ref_id: aid, version: a!.version, handoff_id: hof, title: a!.title });
      await patchHandoff(aid, hof, { status: 'delivered', target_id: target.id, target_title: target.title ?? null });
      void qc.invalidateQueries({ queryKey: ['ca'] });
      set('proposal', { ok: '제안서로 보냈어요' });
      nav(r.route || `/proposal/${target.id}/sections/why`);
    } catch (e) {
      if (hof) await patchHandoff(aid, hof, { status: 'failed' }).catch(() => undefined);
      set('proposal', { err: errText(e, '제안서로 보내지 못했어요') });
    }
  }

  // ── 카드 3: Storyboard 비교 기준 ──
  async function sendStoryboard(sb: StoryboardItem) {
    setPick(null);
    set('storyboard', { busy: true });
    let hof: string | null = null;
    try {
      const h = await createHandoff(aid, { target: 'storyboard', target_id: sb.id, target_title: sb.title });
      hof = h.handoff_id ?? null;
      const bundle = await getBundle(aid, 'storyboard', hof);
      await storyboardImport(sb.id, bundle);
      if (hof) await patchHandoff(aid, hof, { status: 'delivered', target_id: sb.id, target_title: sb.title });
      void qc.invalidateQueries({ queryKey: ['ca'] });
      set('storyboard', { ok: 'Storyboard 에 넣었어요' });
      nav(`/storyboard/${sb.id}/planning/3`);
    } catch (e) {
      if (hof) await patchHandoff(aid, hof, { status: 'failed' }).catch(() => undefined);
      set('storyboard', { err: errText(e, 'Storyboard 로 보내지 못했어요') });
    }
  }

  // ── 카드 4: 리포트 저장(사내용 · 실명) ──
  async function saveReport() {
    set('report', { busy: true });
    try {
      const r = await startExport(aid, 'internal');
      const j = await waitJob(r.job_id, 120_000);
      if (j.status !== 'succeeded') throw new Error(j.error?.message || '리포트를 만들지 못했어요');
      const fid = String((j.result ?? {}).file_id ?? '');
      const href = fid ? fileDownloadUrl(fid) : null;
      set('report', { ok: '리포트를 저장했어요', href });
      void qc.invalidateQueries({ queryKey: ['ca'] });
      if (href) {
        const el = document.createElement('a');
        el.href = href;
        el.rel = 'noopener';
        el.click();
      }
    } catch (e) {
      set('report', { err: errText(e, '리포트를 만들지 못했어요') });
    }
  }

  async function setAnon(v: boolean) {
    setAnonBusy(true);
    try {
      const out = await patchAnalysis(aid, { anonymize: v });
      qc.setQueryData(qk.analysis(aid), out);
    } finally {
      setAnonBusy(false);
    }
  }

  const miSub = mi.isLoading ? 'MI 작업을 찾는 중…'
    : mi.data ? `${mi.data.title}의 경쟁사 영역으로` : '같은 고객사의 MI 작업이 없어요 · 누르면 새 MI 작업을 만들어 넣어요';
  return (
    <CaPage>
      <Head kicker="저장 완료" kickerIcon={<Icon name="check" size={12} strokeWidth={3} />} title="저장했어요. 어디에 쓸까요?"
        desc="결과는 작업 목록과 사이드바에 남아요. 보낼 곳을 고르면 그 자리에 맞게 바뀌어 들어가요." />
      {!hasResult && <Band tone="warn" action={<Link to={`/competitor/${aid}/result`} className="ca-linkbtn ca-linkbtn--brand">결과로</Link>}>아직 저장된 결과가 없어요 · 분석이 끝나면 보낼 수 있어요</Band>}
      <div className="ca-cards">
        <SendCard icon="M4 20h16 M7 16V10 M12 16V5 M17 16v-7" title="Market Intelligence 작업에 합치기" sub={miSub} state={st.mi} onClick={toMi} disabled={!hasResult} />
        <SendCard icon="M3 4h18v12H3z M8 20h8 M12 16v4" title="제안서 Why Samsung · 경쟁 비교 시트로"
          sub={a.anonymize ? `익명 표기 (${lettersText}) 로 Why Samsung 비교 시트에 들어가요` : '실명 표기 · 보낼 때 한 번 더 물어요'} state={st.proposal} onClick={toProposal} disabled={!hasResult} />
        <SendCard icon={null} grid title="Storyboard 비교 기준으로" sub="기획 질의 3 / 3 비교 기준에 채우기" state={st.storyboard} onClick={() => setPick({ kind: 'storyboard' })} />
        <SendCard icon="M12 4v11 M7 10l5 5 5-5 M4 20h16" title="리포트 저장" sub="PDF · 사내용 · 실명 표기 — 고객에게는 보내지 않아요" state={st.report} onClick={saveReport} disabled={!hasResult} />
      </div>
      {st.report.href && <Band action={<a href={st.report.href} className="ca-linkbtn ca-linkbtn--brand" download>내려받기</a>}>리포트를 저장했어요 · PDF · 사내용</Band>}
      <div className="ca-anon">
        <Switch on={a.anonymize} onChange={setAnon} label="고객 제출물엔 익명으로 표기" disabled={anonBusy} />
        <b>고객 제출물엔 익명으로 표기</b>
        <span className="ca-anon__desc">— {a.anonymize ? lettersText : '실명 표기 · 고객 제출물에 넣을 땐 한 번 더 물어요'}</span>
        <span className="ca-anon__lock"><Icon name="lock" size={12} strokeWidth={2.2} />실명은 이 작업 안에서만 보여요</span>
      </div>
      <FootBar back={{ to: '/competitor', label: '작업 목록', icon: <PathIcon d="M4 6h16 M4 12h16 M4 18h10" size={14} strokeWidth={2.2} /> }}>
        <BigButton onClick={() => nav('/')}>홈으로</BigButton>
      </FootBar>

      <Modal open={ask} onClose={() => setAsk(false)} variant="dialog" width={460} title="경쟁사 실명을 고객 제출물에 넣을까요?"
        footer={<div className="ca-row" style={{ justifyContent: 'flex-end' }}>
          <Button h={40} onClick={() => { setAsk(false); setPick({ kind: 'proposal', named: false }); }}>익명으로 보내기</Button>
          <Button h={40} variant="primary" onClick={() => { setAsk(false); setPick({ kind: 'proposal', named: true }); }}>실명으로 보내기</Button>
        </div>}>
        <div className="ca-ask2">
          <span>익명 표기가 꺼져 있어요. 이 제안서에 경쟁사 실명이 그대로 들어가요.</span>
          <span className="ca-muted">익명으로 보내면 {lettersText} 로 들어가요. 답이 없으면 익명으로 보내요.</span>
        </div>
      </Modal>
      {pick?.kind === 'proposal' && <ProposalPick customer={customer} onClose={() => setPick(null)} onPick={(p) => sendProposal(p, pick.named)} />}
      {pick?.kind === 'storyboard' && <StoryboardPick customer={customer} onClose={() => setPick(null)} onPick={sendStoryboard} />}
    </CaPage>
  );
}

function SendCard({ icon, grid, title, sub, state, onClick, disabled }:
  { icon: string | null; grid?: boolean; title: string; sub: ReactNode; state: CardState; onClick: () => void; disabled?: boolean }) {
  return (
    <button type="button" className="ca-card" onClick={onClick} disabled={disabled || state.busy} aria-busy={state.busy || undefined}>
      <span className="ca-card__icon" aria-hidden="true">
        {grid
          ? <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="4" width="7" height="7" rx="1.5" /><rect x="14" y="4" width="7" height="7" rx="1.5" /><rect x="3" y="14" width="7" height="7" rx="1.5" /><rect x="14" y="14" width="7" height="7" rx="1.5" /></svg>
          : <PathIcon d={icon ?? ''} size={18} />}
      </span>
      <span className="ca-card__body">
        <span className="ca-card__title">{title}</span>
        <span className="ca-card__sub">{state.err ?? sub}</span>
      </span>
      {state.busy && <span className="ca-card__state"><Spinner label="보내는 중" />보내는 중</span>}
      {!state.busy && state.ok && (
        <span className={cx('ca-card__state', 'ca-card__state--ok')}>
          <Icon name="check" size={12} strokeWidth={3} />{state.ok}
        </span>
      )}
      {!state.busy && state.err && <span className={cx('ca-card__state', 'ca-card__state--err')}>다시 시도</span>}
      <Icon name="chevronRight" size={14} strokeWidth={2.4} color="var(--wm-text-subtle)" />
    </button>
  );
}

function ProposalPick({ customer, onClose, onPick }: { customer: string | null; onClose: () => void; onPick: (p: ProposalItem | null) => void }) {
  const q = useQuery({ queryKey: ['ca', 'ext', 'proposals'], queryFn: () => recentProposals(), retry: false });
  const list = q.data ?? [];
  const mine = customer ? [...list.filter((p) => p.customer_name === customer), ...list.filter((p) => p.customer_name !== customer)] : list;
  return (
    <Modal open onClose={onClose} title="어느 제안서로 보낼까요?" width={560}>
      <div className="ca-pick" role="list" aria-label="최근 제안서">
        <button type="button" className="ca-pick__row" role="listitem" onClick={() => onPick(null)}>
          <span className="ca-card__icon" aria-hidden="true"><Icon name="plus" size={16} /></span>
          <span className="ca-pick__main"><span className="ca-pick__title">새 제안서로 시작</span><span className="ca-pick__sub">{customer ? `${customer} · ` : ''}Why Samsung 섹션에 경쟁 비교를 넣어 시작해요</span></span>
        </button>
        {q.isLoading && <Spinner />}
        {q.isError && <span className="ca-muted">제안서 목록을 불러오지 못했어요</span>}
        {mine.map((p) => (
          <button key={p.id} type="button" className="ca-pick__row" role="listitem" onClick={() => onPick(p)}>
            <span className="ca-pick__main"><span className="ca-pick__title">{p.title}</span><span className="ca-pick__sub">{[p.customer_name, p.type_label, p.status_label].filter(Boolean).join(' · ')}</span></span>
            <Icon name="chevronRight" size={14} color="var(--wm-text-subtle)" />
          </button>
        ))}
      </div>
    </Modal>
  );
}

function StoryboardPick({ customer, onClose, onPick }: { customer: string | null; onClose: () => void; onPick: (s: StoryboardItem) => void }) {
  const q = useQuery({ queryKey: ['ca', 'ext', 'storyboards'], queryFn: () => recentStoryboards(), retry: false });
  const list = q.data ?? [];
  const mine = customer ? [...list.filter((s) => s.customer_name === customer), ...list.filter((s) => s.customer_name !== customer)] : list;
  return (
    <Modal open onClose={onClose} title="어느 Storyboard 의 비교 기준으로 넣을까요?" width={560}>
      <div className="ca-pick" role="list" aria-label="최근 Storyboard">
        {q.isLoading && <Spinner />}
        {q.isError && <span className="ca-muted">Storyboard 목록을 불러오지 못했어요</span>}
        {q.data && !list.length && <span className="ca-muted">Storyboard 가 없어요 · <Link to="/storyboard/new">새 Storyboard</Link> 를 먼저 만들어 주세요</span>}
        {mine.map((s) => (
          <button key={s.id} type="button" className="ca-pick__row" role="listitem" onClick={() => onPick(s)}>
            <span className="ca-pick__main"><span className="ca-pick__title">{s.title}</span><span className="ca-pick__sub">{[s.customer_name, s.step_label, s.status_label].filter(Boolean).join(' · ')}</span></span>
            <Icon name="chevronRight" size={14} color="var(--wm-text-subtle)" />
          </button>
        ))}
      </div>
    </Modal>
  );
}

export default SendPage;
