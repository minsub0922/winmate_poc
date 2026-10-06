/**
 * PRU3A — 활용 계획 · 기반으로 개선 · 수정(§4.27, 보드 PRU3A) · PRU3B — 논리 흐름만 차용(§4.28, 보드 PRU3B).
 *   /proposal/:id/reuse/plan?mode=improve|borrow  (없으면 서버가 정한 방식 = 추천)
 * 세그먼트로 방식을 바꾸면 `PUT …/reuse/mode` → 잡이 그 방식 계획을 만든다(폴링).
 * 「확정 · 섹션 작성 시작」 = `plan:confirm {then: sections}` → 첫 섹션(원본 대조 · 흐름 가이드), 「시트 구성에서 다듬기」 = `{then: compose}` → PR3.
 */
import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { Icon, cx, toast } from '@/ui';
import { confirmPlan, getProposal, getSection, putPlanRow, putReuseMode, qk, useProposal, useReuse } from '../api/proposal';
import { errText, jobErrText } from '../api/http';
import { useJobEvents } from '../api/jobs';
import type { PlanBorrow, PlanImprove, ReuseAnalysis } from '../api/types';
import { Agent, Dock, ErrorBand, LoadingCard, NextButton, PrPage, Rich, SpinIcon } from '../components/parts';
import { R, normalizeRoute } from '../lib/routes';
import { TYPES } from '../lib/catalog';
import { useProposalShell } from '../lib/useProposalShell';

type Verdict = 'keep' | 'update' | 'rewrite' | 'new' | 'drop';
export const VERDICT_LABEL: Record<Verdict, string> = { keep: '유지', update: '갱신', rewrite: '재작성', new: '신규', drop: '제외' };
const VERDICTS: Verdict[] = ['keep', 'update', 'rewrite', 'new', 'drop'];
const COVER_CLS: Record<string, string> = { has: 'pr-vchip pr-vchip--keep', part: 'pr-vchip pr-vchip--update', none: 'pr-vchip pr-vchip--new' };
const COVER_ICON: Record<string, string> = { has: '✓', part: '–', none: '+' };

export function ReusePlanPage() {
  const { id } = useParams();
  const [sp, setSp] = useSearchParams();
  const nav = useNavigate();
  const qc = useQueryClient();
  const pq = useProposal(id);
  const p = pq.data;
  const rq = useReuse(id);
  const rv = rq.data;
  const want = sp.get('mode') as 'improve' | 'borrow' | null;
  const [job, setJob] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const mode: 'improve' | 'borrow' = (rv?.mode ?? want ?? rv?.recommendation?.mode ?? 'improve') as 'improve' | 'borrow';
  const planning = rv?.status === 'planning' || !!job;
  useProposalShell({ p, step: 1 });
  useEffect(() => {
    if (rv?.status !== 'planning' || job) return;
    const t = window.setInterval(() => void rq.refetch(), 3000);
    return () => window.clearInterval(t);
  }, [rv?.status, job, rq]);
  const ev = useJobEvents(job ?? (rv?.status === 'planning' ? rv.job_id ?? null : null), {
    onDone: (j) => { setJob(null); if (j.status === 'failed') toast(jobErrText(j.error, '활용 계획을 만들지 못했어요')); void rq.refetch(); },
  });
  // 주소의 방식과 서버 방식이 다르면 한 번 맞춘다(PR1C에서 고른 방식 · 세그먼트)
  const synced = useRef(false);
  useEffect(() => {
    if (!rv || !id || synced.current) return;
    synced.current = true;
    if (!want || rv.mode === want || rv.status === 'analyzing') return;
    void switchMode(want);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rv, id, want]);

  async function switchMode(m: 'improve' | 'borrow') {
    if (!id) return;
    setBusy(`mode:${m}`);
    try {
      const v = await putReuseMode(id, m);
      qc.setQueryData(qk.sub(id, 'reuse'), v);
      setSp((c) => { const x = new URLSearchParams(c); x.set('mode', m); return x; }, { replace: true });
      if (v.status === 'planning' && v.job_id) setJob(v.job_id);
    } catch (e) { toast(errText(e)); } finally { setBusy(null); }
  }
  const setVerdict = async (rowId: string, verdict: Verdict) => {
    if (!id) return;
    setBusy(`row:${rowId}`);
    try { const v = await putPlanRow(id, rowId, verdict); qc.setQueryData(qk.sub(id, 'reuse'), v); } catch (e) { toast(errText(e)); } finally { setBusy(null); }
  };
  const go = async (then: 'sections' | 'compose') => {
    if (!id) return;
    setBusy(then);
    try {
      const r = await confirmPlan(id, then);
      // 확정 직후(status=applying) 몇 초는 유형 · 시트 구성이 아직 안 바뀌어 섹션이 422(SECTION_NOT_IN_TYPE) · 원본 대조가 404 —
      // 그 섹션이 열릴 때까지 기다렸다가 간다(최대 30초, 넘으면 그냥 이동 — 섹션 화면이 다시 읽는다)
      const to = normalizeRoute(r.route);
      const key = to?.match(/\/sections\/([A-Za-z]+)/)?.[1];
      if (key) await waitUntil(() => getSection(id, key).then(() => true, () => false), 30_000);
      else if (then === 'compose') await waitUntil(() => getProposal(id).then((np) => !!np.type, () => false), 30_000);
      void qc.invalidateQueries({ queryKey: qk.p(id) });
      if (to) { nav(to); return; }
      if (then === 'compose') { nav(R.compose(id)); return; }
      const np = await getProposal(id);
      qc.setQueryData(qk.p(id), np);
      const first = np.sections?.find((s) => s.enabled && !s.hidden);
      nav(first ? R.section(id, first.key, { view: mode === 'borrow' ? 'guide' : 'compare' }) : R.compose(id));
    } catch (e) { toast(errText(e)); } finally { setBusy(null); }
  };

  if (pq.isError) return <PrPage><ErrorBand message={errText(pq.error, '제안서를 찾을 수 없어요')} onRetry={() => void pq.refetch()} /></PrPage>;
  if (!p || !id) return <PrPage><LoadingCard /></PrPage>;
  if (rq.isError) return <PrPage wide><ErrorBand message={errText(rq.error, '활용 계획을 불러오지 못했어요')} onRetry={() => void rq.refetch()} /></PrPage>;
  if (!rv) return <PrPage wide><LoadingCard lines={8} /></PrPage>;

  const rec = rv.recommendation;
  const pi = rv.plan_improve;
  const pb = rv.plan_borrow;
  const hasPlan = mode === 'improve' ? !!pi : !!pb;
  const totals = (mode === 'improve' ? pi?.totals : pb?.counts) ?? {};

  const seg = (
    <div className="pr-colflex" style={{ gap: 6, alignItems: 'flex-end', flexShrink: 0 }}>
      <div role="radiogroup" aria-label="활용 방식" className="pr-miniseg pr-miniseg--tabs">
        <button type="button" role="radio" aria-checked={mode === 'improve'} onClick={() => mode !== 'improve' && void switchMode('improve')} disabled={!!busy} data-testid="pru3-mode-improve">기반으로 개선 · 수정</button>
        <button type="button" role="radio" aria-checked={mode === 'borrow'} onClick={() => mode !== 'borrow' && void switchMode('borrow')} disabled={!!busy} data-testid="pru3-mode-borrow">논리 흐름만 차용</button>
      </div>
      {rec && rec.mode === mode && <span className="pr-recbadge2"><Icon name="check" size={11} strokeWidth={3} />{rec.badge || '추천'}</span>}
    </div>
  );

  const footer = mode === 'improve' ? (pi?.footer_label?.replace(/^활용 계획 · /, '') || (pi ? `원본 ${pi.source_total}장 → 새 제안서 ${pi.new_total}장 · 1 / 6` : '1 / 6'))
    : (pb?.footer_label?.replace(/^시트 구성 초안 · /, '') || (pb ? `${pb.sections}섹션 · ${pb.sheets}시트 · 원본 내용 0줄 사용 · 1 / 6` : '1 / 6'));
  const dock = (
    <Dock testId="pru3-dock" title={mode === 'improve' ? '활용 계획' : '시트 구성 초안'} meta={footer}
      right={<span className="pr-row" style={{ gap: 6 }} data-testid="pru3-totals">
        {mode === 'improve' ? VERDICTS.map((v) => <span key={v} className={cx('pr-vchip', `pr-vchip--${v}`)}>{VERDICT_LABEL[v]} {totals[v] ?? 0}장</span>)
          : ([['flow', '흐름 차용'], ['new', '신규'], ['drop', '제외']] as const).map(([k, l]) => <span key={k} className={cx('pr-vchip', k === 'flow' ? 'pr-vchip--keep' : k === 'new' ? 'pr-vchip--new' : 'pr-vchip--drop')}>{l} {totals[k] ?? 0}장</span>)}
      </span>}
      hint={mode === 'improve' ? '확정하면 시트 구성(3단계)이 이 판정대로 채워지고, 섹션 작성에서는 원본 시트와 새 시트를 나란히 놓고 고쳐요.' : '확정하면 시트 구성(3단계)이 이 초안으로 채워지고, 섹션 작성에서는 원본 역할만 \'흐름 가이드\'로 보여요.'}
      foot={<>
        <Link to={R.reuseAnalysis(id)} className="pr-btn">이전</Link>
        <button type="button" className="pr-btn" disabled={!hasPlan || planning || !!busy} onClick={() => void go('compose')} data-testid="pru3-compose">시트 구성에서 다듬기</button>
        <NextButton onClick={() => void go('sections')} disabled={!hasPlan || planning || (!!busy && busy !== 'sections')} busy={busy === 'sections'} testId="pru3-confirm">
          {mode === 'improve' ? '확정 · 섹션 작성 시작 (원본 대조)' : '확정 · 섹션 작성 시작'}</NextButton>
      </>} />
  );

  return (
    <PrPage testId={mode === 'improve' ? 'pru3a' : 'pru3b'} dock={dock} wide gap={14} tight>
      <div className="pr-row" style={{ gap: 16, alignItems: 'flex-start' }}>
        <div className="pr-grow"><Agent text={rv.intro ? <Rich text={rv.intro} /> : rec?.reason ?? ''} testId="pru3-agent" /></div>
        {seg}
      </div>
      {planning && <div className="pr-band pr-band--muted" data-testid="pru3-planning"><SpinIcon /> <span className="pr-grow">{mode === 'improve' ? '시트마다 판정을 정하는 중이에요' : '원본 흐름을 이번 시트 구성으로 바꾸는 중이에요'} · {Math.round(ev.progress)}%</span></div>}
      {!hasPlan && !planning && <div className="pr-band pr-band--muted">아직 계획이 없어요. 위에서 활용 방식을 골라 주세요.</div>}
      {mode === 'improve' && pi && <ImproveView pi={pi} busy={busy} onVerdict={setVerdict} />}
      {mode === 'borrow' && pb && <BorrowView pb={pb} rv={rv} sub={[p?.type ? TYPES[p.type]?.short : null, p?.customer?.name, p?.title].filter(Boolean).join(' · ')} />}
    </PrPage>
  );
}

function ImproveView({ pi, busy, onVerdict }: { pi: PlanImprove; busy: string | null; onVerdict: (rowId: string, v: Verdict) => void }) {
  const [all, setAll] = useState(false);
  let shownCount = 0;
  const LIMIT = 12;
  return (
    <div className="pr-pru3a">
      <div className="pr-card" style={{ overflow: 'hidden' }} data-testid="pru3a-table">
        <div className="pr-plrow pr-plrow--head"><span>쪽</span><span /><span>시트</span><span>판정</span><span>근거</span><span>요구사항</span></div>
        {pi.groups.map((g, gi) => {
          // 요구사항 갭에서 더한 신규 묶음은 접어 둘 때도 늘 보인다(보드: 12 / 21장 표시 아래 「요구사항 갭에서 추가」)
          if (!all && !g.is_new && shownCount >= LIMIT) return null;
          return (
            <div key={`${g.name}-${gi}`}>
              <div className={cx('pr-plgroup', g.is_new && 'pr-plgroup--new')}>
                <b>{g.name}</b><span className="pr-note">{g.label || `${g.count}장${g.range ? ` · ${g.range}` : ''}`}</span>
                {g.is_new && <span className="pr-vchip pr-vchip--new" style={{ height: 18 }}>요구사항 갭</span>}
                <span className="pr-grow" />
                {gi === 0 && pi.shown_label && <button type="button" className="pr-link" style={{ fontSize: 11.5 }} onClick={() => setAll((a) => !a)}>{all ? '접기' : pi.shown_label}</button>}
              </div>
              {g.rows.map((r) => {
                if (!all && !g.is_new && shownCount >= LIMIT) return null;
                if (!g.is_new) shownCount += 1;
                return (
                  <div key={r.row_id} className="pr-plrow" data-testid="pru3a-row" data-verdict={r.verdict}>
                    <span className={cx('pr-num', r.verdict === 'new' ? 'pr-okc' : 'pr-subtle')} style={{ fontSize: 11.5, fontWeight: 700 }}>{r.page_label || (r.page ? `p.${r.page}` : '신규')}</span>
                    <span className={cx('pr-plthumb', r.verdict === 'new' && 'pr-plthumb--new')}>{r.verdict === 'new' ? '+' : ''}</span>
                    <b className={cx('pr-ell', r.verdict === 'drop' && 'pr-strike')} style={{ fontSize: 13 }}>{r.sheet_name}</b>
                    <span role="radiogroup" aria-label={`${r.sheet_name} 판정`} className="pr-verdicts">
                      {VERDICTS.map((v) => (
                        <button key={v} type="button" role="radio" aria-checked={r.verdict === v} className={cx('pr-verdict', `pr-verdict--${v}`)}
                          disabled={busy === `row:${r.row_id}` || (r.noncopy && v !== 'drop') || (v === 'new' && r.verdict !== 'new' && !!r.page) || (r.verdict === 'new' && !r.page && v !== 'new' && v !== 'drop')}
                          onClick={() => r.verdict !== v && onVerdict(r.row_id, v)}>{VERDICT_LABEL[v]}</button>
                      ))}
                    </span>
                    <span className="pr-ell" style={{ fontSize: 12, color: 'var(--wm-text-2)' }}>{r.locked && <Icon name="lock" size={10} />} {r.note}</span>
                    <span className="pr-row" style={{ gap: 3 }}>{(r.rq_ids ?? []).map((q) => <span key={q} className="pr-rqchip">{q}</span>)}</span>
                  </div>
                );
              })}
            </div>
          );
        })}
      </div>
      <div className="pr-colflex" style={{ gap: 14 }}>
        <div className="pr-card" style={{ padding: '12px 14px', display: 'flex', flexDirection: 'column', gap: 8 }} data-testid="pru3a-coverage">
          <div className="pr-row pr-row--between"><b style={{ fontSize: 13 }}>요구사항 대조</b><span className="pr-note" style={{ fontSize: 11.5 }}>이번 {pi.requirement_coverage.length}건 ↔ 원본 {pi.source_total}장</span></div>
          {pi.requirement_coverage.map((c) => (
            <div key={c.rq_id} className="pr-coverrow">
              <span className="pr-rqchip pr-rqchip--lg">{c.code}</span>
              <span className="pr-colflex pr-grow" style={{ gap: 1, minWidth: 0 }}><b className="pr-ell" style={{ fontSize: 12.5 }}>{c.name}</b><span className="pr-ell pr-note" style={{ fontSize: 11 }}>{c.where}</span></span>
              <span className={COVER_CLS[c.state]}>{COVER_ICON[c.state]} {c.state_label}</span>
            </div>
          ))}
          {pi.only_in_source.length > 0 && (
            <>
              <div className="pr-row" style={{ gap: 6, paddingTop: 6, borderTop: '1px solid var(--wm-line)' }}><b style={{ fontSize: 12.5 }}>원본에만 있는 것</b><span className="pr-note">{pi.only_in_source.length}</span></div>
              {pi.only_in_source.map((o) => <div key={o.label} className="pr-row" style={{ gap: 8, fontSize: 12.5 }}><i className="pr-legdot" style={{ background: 'var(--wm-text-subtle)' }} /><span className="pr-grow pr-ell">{o.label}</span><span className="pr-cftag">{o.tag}</span></div>)}
            </>
          )}
        </div>
        <div className="pr-card" style={{ padding: '12px 14px', display: 'flex', flexDirection: 'column', gap: 8, background: 'var(--wm-surface-2)' }} data-testid="pru3a-summary">
          <b style={{ fontSize: 12.5 }}>판정 요약 · {pi.source_total}장</b>
          <div className="pr-row pr-row--wrap" style={{ gap: '4px 10px', fontSize: 12 }}>
            {VERDICTS.map((v) => <span key={v} className="pr-row" style={{ gap: 4 }}><i className={cx('pr-legdot', `pr-legdot--${v}`)} />{VERDICT_LABEL[v]} <b className="pr-num">{pi.totals[v] ?? 0}</b></span>)}
          </div>
          {pi.summary_note && <span className="pr-note" style={{ fontSize: 11.5, lineHeight: 1.5 }}>{pi.summary_note}</span>}
        </div>
      </div>
    </div>
  );
}

function BorrowView({ pb, rv, sub }: { pb: PlanBorrow; rv: ReuseAnalysis; sub: string }) {
  const src = rv.sources?.[0];
  // 원본 단계 점 색 = 원본 섹션 색(PRU2 범례와 같은 순서) — 신규 줄은 건너뛴다
  const secColors = (rv.source_sections ?? []).map((x) => x.color);
  let srcIdx = 0;
  const dotOf = pb.rows.map((r) => (r.kind === 'new' ? undefined : secColors[srcIdx++]));
  return (
    <div className="pr-card pr-pru3b" data-testid="pru3b-map">
      <div className="pr-pru3b__col">
        <div className="pr-colhead"><b>원본 흐름</b><span>{[src?.customer, src?.pages ? `${src.pages}장` : null, src?.kind === 'file' ? '외부 파일' : 'Winmate 제안서'].filter(Boolean).join(' · ')}</span></div>
        {pb.rows.map((r, i) => (
          <div key={i} className={cx('pr-srcstep', r.kind === 'new' && 'pr-srcstep--new', r.kind === 'drop' && 'pr-srcstep--drop')}>
            <b className="pr-ell">{r.kind === 'new' ? '+ ' : <i className="pr-legdot" style={{ marginRight: 5, background: dotOf[i] }} />}{r.src_step}</b>
            <span className="pr-ell">{r.kind === 'new' ? '원본에 없음 → 추가 제안' : `${r.src_count}장${r.src_range ? ` · ${r.src_range}` : ''}`}</span>
          </div>
        ))}
      </div>
      <div className="pr-pru3b__arrows">
        {pb.rows.map((r, i) => <span key={i} className={cx('pr-maparrow', `pr-maparrow--${r.kind}`)}>{r.kind === 'drop' ? '→' : '→'}</span>)}
      </div>
      <div className="pr-pru3b__col" style={{ borderLeft: '1px solid var(--wm-line)' }}>
        <div className="pr-colhead pr-colhead--row">
          <span className="pr-colflex" style={{ gap: 1, minWidth: 0 }}><b>이번 제안서 시트 구성</b>{sub && <span className="pr-ell">{sub}</span>}</span>
          <span className="pr-row" style={{ gap: 4 }}><span className="pr-vchip pr-vchip--keep">흐름</span><span className="pr-vchip pr-vchip--new">신규</span><span className="pr-vchip pr-vchip--drop">제외</span></span>
        </div>
        {pb.rows.map((r, i) => (
          <div key={i} className={cx('pr-maprow', `pr-maprow--${r.kind}`)} data-testid="pru3b-row" data-kind={r.kind}>
            <span className={cx('pr-vchip', r.kind === 'flow' ? 'pr-vchip--keep' : r.kind === 'new' ? 'pr-vchip--new' : 'pr-vchip--drop')}>{r.kind === 'flow' ? '흐름' : r.kind === 'new' ? '신규' : '제외'}</span>
            <span className="pr-colflex pr-grow" style={{ gap: 1, minWidth: 0 }}><b className="pr-ell" style={{ fontSize: 12.5 }}>{r.new_label}</b><span className="pr-ell pr-note" style={{ fontSize: 11 }}>{r.note}</span></span>
            <span className="pr-row" style={{ gap: 3 }}>{(r.rq_ids ?? []).map((q) => <span key={q} className="pr-rqchip">{q}</span>)}</span>
            <b className="pr-num pr-brand" style={{ fontSize: 12, width: 28, textAlign: 'right' }}>{r.new_count}장</b>
          </div>
        ))}
      </div>
      <div className="pr-pru3b__col pr-pru3b__rules" data-testid="pru3b-rules">
        <div className="pr-colhead"><b>가져오는 것 / 안 가져오는 것</b><span>흐름 차용 규칙 · 고정</span></div>
        <b className="pr-brand" style={{ fontSize: 12.5 }}>가져오는 것 <span className="pr-note">{pb.take.length}</span></b>
        {pb.take.map((t) => <div key={t.label} className="pr-row" style={{ gap: 6, fontSize: 12 }}><span className="pr-circ"><Icon name="check" size={9} strokeWidth={3.2} color="var(--wm-brand)" /></span><b>{t.label}</b><span className="pr-note pr-ell">{t.sub}</span></div>)}
        <b style={{ fontSize: 12.5, paddingTop: 6 }}>안 가져오는 것 <span className="pr-note">{pb.not_take.length}</span></b>
        {pb.not_take.map((t) => <div key={t.label} className="pr-row pr-subtle" style={{ gap: 6, fontSize: 12 }}><span className="pr-circ"><Icon name="x" size={9} strokeWidth={3.2} /></span><s className="pr-ell">{t.label} {t.sub}</s></div>)}
        <span className="pr-note" style={{ fontSize: 11.5, lineHeight: 1.5, paddingTop: 6, borderTop: '1px solid var(--wm-line)' }}>안 가져오는 항목은 섹션 작성의 '원본 대조' 보기에서도 숨겨져요. 역할 태그와 구조만 '흐름 가이드'로 보여요.</span>
      </div>
    </div>
  );
}

/** fn 이 true 를 낼 때까지 1초 간격으로(최대 timeout) */
async function waitUntil(fn: () => Promise<boolean>, timeout: number) {
  const t0 = Date.now();
  while (Date.now() - t0 < timeout) {
    if (await fn()) return true;
    await new Promise((res) => window.setTimeout(res, 1000));
  }
  return false;
}
