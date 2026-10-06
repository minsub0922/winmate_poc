/**
 * PRU2 — 기준별 분석 결과(§4.25, 보드 PRU2) · PRU2F — 기준 상세(§4.26, 보드 PRU2F).
 *   /proposal/:id/reuse/analysis          9기준 표 + 원본 쪽 띠 → 필수 3곳 확인 → 「확인 완료 · 활용 방식 추천 보기」(confirm-analysis) → PRU3A|B
 *   /proposal/:id/reuse/analysis/:no      기준 상세(2 논리 흐름 = 스토리라인 · 쪽별 역할 태그 · 에이전트 메모, 나머지 = 상세 표)
 */
import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { Icon, cx, toast } from '@/ui';
import { confirmAnalysis, putCriterion, putPageRole, qk, reanalyze, useProposal, useReuse, useReuseCriterion } from '../api/proposal';
import { errText, jobErrText } from '../api/http';
import { useJobEvents } from '../api/jobs';
import type { ReuseAnalysis, ReusePage } from '../api/types';
import { Agent, Dock, ErrorBand, LoadingCard, NextButton, PrPage, Rich, SpinIcon } from '../components/parts';
import { R, normalizeRoute } from '../lib/routes';
import { useProposalShell } from '../lib/useProposalShell';
import { readModePref } from './ReuseStartPage';

export const ROLE_TAGS = ['표지', '문제 제기', '시장 변화', '고객 과제', '가치 제안', '솔루션 구성', '도입 사례', '제품 스펙', '견적 · 일정', '공간 시나리오', 'Why Samsung · 경쟁 비교'];
const STATE_CLS: Record<string, string> = { ok: 'pr-rstate pr-rstate--ok', need: 'pr-rstate pr-rstate--need', edited: 'pr-rstate pr-rstate--edited', auto: 'pr-rstate pr-rstate--auto' };

function Conf({ n, warn }: { n: number; warn?: boolean }) {
  const w = warn ?? n < 80;
  return (
    <span className="pr-row" style={{ gap: 6 }} aria-label={`신뢰도 ${n}%`}>
      <span className="pr-confbar"><span className={cx(w && 'pr-confbar--warn')} style={{ width: `${Math.max(0, Math.min(100, n))}%` }} /></span>
      <span className={cx('pr-num', w ? 'pr-confpct--warn' : 'pr-brand')} style={{ fontSize: 11.5, fontWeight: 800 }}>{n}%</span>
    </span>
  );
}

/** 분석 중 · 실패 공통 처리 — 잡을 따라가며 다시 읽는다 */
function useReuseLive(id: string | undefined) {
  const rq = useReuse(id);
  const rv = rq.data;
  const live = rv?.status === 'analyzing' || rv?.status === 'planning';
  useEffect(() => {
    if (!live) return;
    const t = window.setInterval(() => void rq.refetch(), 3000);
    return () => window.clearInterval(t);
  }, [live, rq]);
  const ev = useJobEvents(live ? rv?.job_id ?? null : null, { onDone: () => void rq.refetch() });
  return { rq, rv, live, ev };
}

export function ReuseAnalysisPage() {
  const { id } = useParams();
  const nav = useNavigate();
  const qc = useQueryClient();
  const pq = useProposal(id);
  const p = pq.data;
  const { rq, rv, live, ev } = useReuseLive(id);
  const [busy, setBusy] = useState<string | null>(null);
  const [planJob, setPlanJob] = useState<string | null>(null);
  useProposalShell({ p, step: 1 });
  const pref = rv?.mode_pref ?? (id ? readModePref(id) : null);
  const goPlan = (route?: string | null) => { if (!id) return; nav(normalizeRoute(route) ?? R.reusePlan(id, pref === 'improve' || pref === 'borrow' ? pref : null)); };
  const pj = useJobEvents(planJob, {
    onDone: (j) => {
      setPlanJob(null);
      if (j.status !== 'succeeded' && j.status !== 'awaiting_input') { toast(jobErrText(j.error, '활용 계획을 만들지 못했어요')); return; }
      if (id) void qc.invalidateQueries({ queryKey: qk.sub(id, 'reuse') });
      goPlan();
    },
  });

  const setState = async (no: number, state: 'ok' | 'need') => {
    if (!id) return;
    setBusy(`c:${no}`);
    try { const v = await putCriterion(id, no, { state }); qc.setQueryData(qk.sub(id, 'reuse'), v); } catch (e) { toast(errText(e)); } finally { setBusy(null); }
  };
  const again = async () => {
    if (!id) return;
    setBusy('re');
    try { await reanalyze(id); toast('고정한 결과는 그대로 두고 다시 분석해요'); void rq.refetch(); } catch (e) { toast(errText(e)); } finally { setBusy(null); }
  };
  const done = async () => {
    if (!id) return;
    setBusy('done');
    try {
      const r = await confirmAnalysis(id);
      if (r.job_id && r.status !== 'awaiting_plan_confirm' && !r.route) setPlanJob(r.job_id);
      else goPlan(r.route);
    } catch (e) { toast(errText(e)); } finally { setBusy(null); }
  };

  if (pq.isError) return <PrPage><ErrorBand message={errText(pq.error, '제안서를 찾을 수 없어요')} onRetry={() => void pq.refetch()} /></PrPage>;
  if (!p || !id) return <PrPage><LoadingCard /></PrPage>;
  if (rq.isError) return <PrPage wide><ErrorBand message={errText(rq.error, '분석 결과를 불러오지 못했어요')} onRetry={() => void rq.refetch()} /><Link to={R.reuse(id)} className="pr-link">원본 고르기로</Link></PrPage>;
  if (!rv) return <PrPage wide><LoadingCard lines={8} /></PrPage>;

  const crit = rv.criteria ?? [];
  const nOk = crit.filter((c) => c.state === 'ok').length;
  const nNeed = crit.filter((c) => c.state === 'need').length;
  const nEd = crit.filter((c) => c.state === 'edited').length;
  const doneN = nOk + nEd;
  const mustTotal = rv.must_total ?? crit.filter((c) => c.must).length;
  const mustDone = rv.must_done ?? crit.filter((c) => c.must && c.state !== 'need').length;
  const can = (rv.can_confirm ?? mustDone >= mustTotal) && rv.status === 'awaiting_confirm' && !live;
  const fileName = rv.sources?.[0]?.name ?? '원본';
  const total = rv.pages?.length ?? rv.sources?.reduce((n, s) => n + (s.pages ?? 0), 0) ?? 0;

  const dock = (
    <Dock testId="pru2-dock" title="분석 결과 확인"
      meta={rv.footer_label?.replace(/^분석 결과 확인 · /, '') || `${crit.length}개 기준 중 ${doneN}개 확인 · 필수 확인 ${mustDone} / ${mustTotal} 마침 · ${Math.max(0, mustTotal - mustDone)}곳 남음`}
      right={<>
        <span className="pr-cfbar" role="progressbar" aria-label={`확인 진행률 ${doneN} / ${crit.length || 9}`} aria-valuenow={doneN} aria-valuemin={0} aria-valuemax={crit.length || 9} style={{ width: 160 }}><span style={{ width: `${crit.length ? (doneN / crit.length) * 100 : 0}%` }} /></span>
        <span className="pr-rstate pr-rstate--ok">확인됨 {nOk}</span><span className="pr-rstate pr-rstate--need">확인 필요 {nNeed}</span><span className="pr-rstate pr-rstate--edited">수정함 {nEd}</span>
      </>}
      hint={`직접 고친 결과(수정함)는 다시 분석해도 바뀌지 않아요${rv.excluded_page_count ? ` · 비복제 항목 ${rv.excluded_page_count}장은 이미 자동 제외됐어요` : ''}`}
      foot={<>
        <Link to={R.reuse(id)} className="pr-btn">이전</Link>
        <button type="button" className="pr-btn" disabled={!!busy || live} onClick={() => void again()} data-testid="pru2-reanalyze">{busy === 're' ? <SpinIcon size={13} /> : <Icon name="refresh" size={14} />}다시 분석</button>
        {!can && <span className="pr-subtle" style={{ fontSize: 11.5, whiteSpace: 'nowrap' }}>필수 확인을 마치면 활성화</span>}
        <NextButton onClick={() => void done()} disabled={!can} busy={busy === 'done' || !!planJob} disabledReason="필수 확인을 마치면 활성화" testId="pru2-confirm">확인 완료 · 활용 방식 추천 보기</NextButton>
      </>} />
  );

  return (
    <PrPage testId="pru2" dock={dock} wide gap={14} tight>
      <Agent text={rv.intro ? <Rich text={rv.intro} /> : <><b>{fileName}</b> {total}장을 9가지 기준으로 분석했어요. 기준마다 결과를 확인해 주세요 — 필수 확인 3곳(논리 흐름 · 고객 맥락 · 비복제)을 확인하면 활용 방식을 추천해요.</>} testId="pru2-agent" />
      {(live || planJob) && (
        <div className="pr-band pr-band--muted" data-testid="pru2-live"><SpinIcon /> <span className="pr-grow">{planJob ? `활용 계획을 만드는 중이에요 · ${Math.round(pj.progress)}%` : `${rv.status_label} · ${Math.round(ev.progress)}%`}</span></div>
      )}
      {rv.status === 'failed' && <ErrorBand message={jobErrText(rv.error as { code?: string; message?: string } | null, '원본을 분석하지 못했어요')} onRetry={() => void again()} />}
      <div className="pr-pru2">
        <SourceStrip rv={rv} />
        <div className="pr-card" style={{ overflow: 'hidden' }} data-testid="pru2-criteria">
          <div className="pr-crit pr-crit--head"><span /><span>기준</span><span>결과 요약</span><span>신뢰도</span><span>상태</span><span /><span>확인</span></div>
          {crit.length === 0 && <div className="pr-empty">{live ? '기준별로 분석하는 중이에요' : '분석 결과가 없어요'}</div>}
          {crit.map((c) => (
            <div key={c.no} className={cx('pr-crit', c.must && c.state === 'need' && 'pr-crit--must')} data-testid="pru2-criterion" data-state={c.state}>
              <span className="pr-num pr-subtle" style={{ fontSize: 12, fontWeight: 700 }}>{c.no}</span>
              <span className="pr-colflex" style={{ gap: 1 }}><b style={{ fontSize: 13 }}>{c.name}</b>{c.must && <span className="pr-brand" style={{ fontSize: 11, fontWeight: 600 }}>필수 확인</span>}</span>
              <span style={{ fontSize: 12, lineHeight: 1.5, color: 'var(--wm-text-2)' }}>{c.summary}</span>
              <Conf n={c.confidence} warn={c.warn} />
              <span className={STATE_CLS[c.state] ?? 'pr-rstate'}>{c.state === 'edited' && <Icon name="lock" size={10} />}{c.state_label}</span>
              <Link to={R.reuseCriterion(id, c.no)} className="pr-link" style={{ fontSize: 12.5 }}>자세히<Icon name="chevronRight" size={11} strokeWidth={2.4} /></Link>
              <input type="checkbox" className="pr-critcheck" aria-label={`${c.name} 확인`} checked={c.state !== 'need'} disabled={c.state === 'edited' || busy === `c:${c.no}` || live}
                onChange={(e) => void setState(c.no, e.target.checked ? 'ok' : 'need')} />
            </div>
          ))}
        </div>
      </div>
    </PrPage>
  );
}

/** 원본 쪽 띠(보드 PRU2 왼쪽 카드) */
function SourceStrip({ rv }: { rv: ReuseAnalysis }) {
  const pages = rv.pages ?? [];
  const secs = rv.source_sections ?? [];
  const total = pages.length || rv.sources?.reduce((n, s) => n + (s.pages ?? 0), 0) || 0;
  return (
    <div className="pr-card pr-srcstrip" data-testid="pru2-source">
      <div className="pr-row pr-row--between" style={{ padding: '12px 14px', borderBottom: '1px solid var(--wm-line)' }}>
        <b style={{ fontSize: 13, whiteSpace: 'nowrap' }}>원본 {total}장</b>
        <span className="pr-note pr-ell" style={{ fontSize: 11.5 }}>{rv.band_label?.replace(/^원본\s*\d+장\s*·\s*/, '') || (rv.sources?.some((s) => s.kind === 'proposal') ? `Winmate 제안서 · 섹션 ${secs.length}개` : `외부 파일 · 섹션 ${secs.length}개`)}</span>
      </div>
      <div className="pr-pagegrid">
        {pages.map((pg) => (
          <span key={pg.no} className={cx('pr-pagecard', pg.excluded && 'pr-pagecard--off')} title={`${pg.no} ${pg.title}${pg.excluded ? ` · ${pg.exclude_reason ?? '제외'}` : ''}`}>
            <span className="pr-pagecard__thumb">
              {pg.thumb_url ? <img src={pg.thumb_url} alt="" /> : <><i /><i /><i /></>}
              <span className="pr-pagecard__dot" style={{ background: pg.section_color || 'var(--wm-text-subtle)' }} />
            </span>
            <span className="pr-num">{pg.no}</span>
          </span>
        ))}
        {pages.length === 0 && Array.from({ length: Math.min(total || 12, 24) }, (_, i) => <span key={i} className="pr-pagecard pr-skel" style={{ height: 44 }} />)}
      </div>
      {secs.length > 0 && (
        <div className="pr-row pr-row--wrap" style={{ gap: '4px 12px', padding: '10px 14px 12px', fontSize: 11 }}>
          {secs.map((s) => <span key={s.name} className="pr-row" style={{ gap: 4, color: s.excluded ? 'var(--wm-text-subtle)' : 'var(--wm-text)' }}><i className="pr-legdot" style={{ background: s.color }} />{s.name} <b className="pr-num">{s.count}</b></span>)}
        </div>
      )}
    </div>
  );
}

// ── PRU2F 기준 상세 ─────────────────────────────────────────
export function ReuseCriterionPage() {
  const { id, no } = useParams();
  const n = Number(no) || 2;
  const nav = useNavigate();
  const qc = useQueryClient();
  const pq = useProposal(id);
  const p = pq.data;
  const cq = useReuseCriterion(id, n);
  const cd = cq.data;
  const { rv } = useReuseLive(id);
  const [busy, setBusy] = useState<string | null>(null);
  const [more, setMore] = useState(false);
  useProposalShell({ p, step: 1 });

  const pages = useMemo(() => cd?.pages ?? rv?.pages ?? [], [cd, rv]);
  const setRole = async (pg: ReusePage, role: string) => {
    if (!id) return;
    setBusy(`p:${pg.no}`);
    try { const v = await putPageRole(id, pg.no, role); qc.setQueryData(qk.sub(id, 'reuse'), v); void cq.refetch(); } catch (e) { toast(errText(e)); } finally { setBusy(null); }
  };
  const confirmFlow = async () => {
    if (!id) return;
    setBusy('ok');
    try {
      // 남은 「확인 필요」 쪽은 첫 후보로 확정(§4.26)
      for (const pg of pages.filter((x) => x.role_state === 'need' && x.role_candidates?.length)) await putPageRole(id, pg.no, pg.role_candidates![0]);
      const v = await putCriterion(id, n, { state: 'ok' });
      qc.setQueryData(qk.sub(id, 'reuse'), v);
      nav(R.reuseAnalysis(id));
    } catch (e) { toast(errText(e)); } finally { setBusy(null); }
  };

  if (pq.isError) return <PrPage><ErrorBand message={errText(pq.error, '제안서를 찾을 수 없어요')} onRetry={() => void pq.refetch()} /></PrPage>;
  if (!p || !id) return <PrPage><LoadingCard /></PrPage>;
  if (cq.isError) return <PrPage wide><ErrorBand message={errText(cq.error)} onRetry={() => void cq.refetch()} /><Link to={R.reuseAnalysis(id)} className="pr-link">기준별 분석 결과로</Link></PrPage>;
  if (!cd) return <PrPage wide><LoadingCard lines={8} /></PrPage>;

  const flow = cd.flow ?? (n === 2 ? rv?.flow ?? null : null);
  const nAuto = pages.filter((x) => x.role_state === 'auto' || x.role_state === 'ok').length;
  const nEd = pages.filter((x) => x.role_state === 'edited').length;
  const nNeed = pages.filter((x) => x.role_state === 'need').length;
  const shown = more ? pages : pages.slice(0, 10);
  const chips = (cd.chips?.length ? cd.chips : Array.from({ length: 9 }, (_, i) => ({ no: i + 1, name: rv?.criteria?.find((c) => c.no === i + 1)?.name ?? '' }))) as Array<{ no?: number; name?: string; label?: string }>;

  const dock = (
    <Dock testId="pru2f-dock" title={n === 2 ? '논리 흐름 확인' : `${cd.name} 확인`}
      meta={cd.footer_label?.replace(/^[^·]+ · /, '') || (pages.length ? `${pages.length}장 중 태그 확인 ${nAuto} · 수정 ${nEd} · 남음 ${nNeed}` : cd.state_label)}
      right={pages.length ? <>
        <span className="pr-cfbar" role="progressbar" aria-label={`태그 확인 진행률 ${nAuto + nEd} / ${pages.length}`} aria-valuenow={nAuto + nEd} aria-valuemin={0} aria-valuemax={pages.length} style={{ width: 130 }}><span style={{ width: `${pages.length ? ((nAuto + nEd) / pages.length) * 100 : 0}%` }} /></span>
        <span className="pr-rstate pr-rstate--ok">확인 {nAuto}</span><span className="pr-rstate pr-rstate--edited">수정함 {nEd}</span><span className="pr-rstate pr-rstate--need">확인 필요 {nNeed}</span>
      </> : null}
      hint={nNeed ? `남은 ${nNeed}장은 확인하지 않으면 에이전트 태그로 넘어가요 · 고정한 태그는 재분석에서 제외` : '고정한 결과는 다시 분석해도 바뀌지 않아요'}
      foot={<>
        <Link to={R.reuseAnalysis(id)} className="pr-btn">이전</Link>
        <NextButton onClick={() => void confirmFlow()} busy={busy === 'ok'} arrow={false} icon={<Icon name="check" size={15} strokeWidth={2.6} />} testId="pru2f-confirm">{n === 2 ? '이 흐름으로 확인' : '이 결과로 확인'}</NextButton>
      </>} />
  );

  return (
    <PrPage testId="pru2f" dock={dock} wide gap={14} tight>
      <div className="pr-row" style={{ gap: 10 }}>
        <Link to={R.reuseAnalysis(id)} className="pr-link" style={{ fontSize: 13 }}><Icon name="chevronLeft" size={13} strokeWidth={2.4} />기준별 분석 결과</Link>
        <b className="pr-brand pr-num" style={{ fontSize: 17 }}>{cd.no}</b><b style={{ fontSize: 17 }}>{cd.name}</b>
        <span className={STATE_CLS[cd.state] ?? 'pr-rstate'} style={{ border: '1px solid var(--wm-text)' }}>{cd.state_label}{cd.must ? ' · 필수' : ''}</span>
        <span className="pr-note pr-ell" style={{ fontSize: 12 }}>{cd.header_label || `신뢰도 ${cd.confidence}%${cd.must && cd.state === 'need' ? ' · 다음 단계로 가려면 확인이 필요해요' : ''}`}</span>
        <span className="pr-grow" />
        <span className="pr-note" style={{ fontSize: 12 }}>기준</span>
        {chips.map((c, i) => {
          const k = c.no ?? i + 1;
          return <Link key={k} to={R.reuseCriterion(id, k)} aria-label={`${k} · ${c.name ?? c.label ?? ''}`} aria-current={k === n ? 'page' : undefined} className={cx('pr-critchip', k === n && 'pr-critchip--on')}>{k}</Link>;
        })}
      </div>
      <Agent text={cd.intro ? <Rich text={cd.intro} /> : cd.summary} testId="pru2f-agent" />
      {flow && (
        <div className="pr-card" style={{ padding: '14px 16px', display: 'flex', flexDirection: 'column', gap: 10 }} data-testid="pru2f-flow">
          <div className="pr-flowband">
            {flow.steps.map((s, i) => (
              <span key={`${s.name}-${i}`} className="pr-row" style={{ gap: 4, minWidth: 0, flex: 1 }}>
                <span className={cx('pr-flowstep', s.dashed && 'pr-flowstep--new', s.excluded && 'pr-flowstep--off')}>
                  <b className="pr-ell">{s.dashed ? '+ ' : <i className="pr-legdot" />}{s.name}</b>
                  <span className="pr-ell">{s.note || (s.excluded ? `${s.count}장 · 자동 제외` : s.dashed ? '원본에 없음 → 이번엔 추가 제안' : `${s.count}장`)}</span>
                </span>
                {i < flow.steps.length - 1 && <Icon name="chevronRight" size={12} color="var(--wm-text-subtle)" />}
              </span>
            ))}
          </div>
          <div className="pr-row pr-row--wrap pr-note" style={{ gap: 8, fontSize: 12 }}>
            {flow.pattern && <span><b style={{ color: 'var(--wm-text)' }}>패턴 · {flow.pattern.name ?? flow.pattern.label ?? ''}</b> {flow.pattern.en ?? ''}</span>}
            {flow.claims && <span>| 주장 → 근거 연결 <b className="pr-brand">{flow.claims.linked ?? flow.claims.a ?? 0} / {flow.claims.total ?? flow.claims.b ?? 0}</b></span>}
            {!!flow.broken?.length && <span>| 끊긴 고리 <b className="pr-confpct--warn">{flow.broken.length}</b> · {flow.broken.join(' · ')}</span>}
            <span className="pr-grow" />
            {flow.steps.some((s) => s.dashed) && <span>점선 단계는 원본에 없어 이번 시트 구성에 추가를 제안해요</span>}
          </div>
        </div>
      )}
      <div className={cx(flow && 'pr-pru2f')}>
        {pages.length > 0 ? (
          <div className="pr-card" style={{ overflow: 'hidden' }} data-testid="pru2f-pages">
            <div className="pr-prow pr-prow--head"><span>쪽</span><span /><span>원본 제목 · 추출 텍스트</span><span>역할 태그</span><span>주장 → 근거</span><span>상태</span></div>
            {shown.map((pg) => (
              <div key={pg.no} className={cx('pr-prow', pg.role_state === 'edited' && 'pr-prow--edited', pg.role_state === 'need' && 'pr-prow--need', pg.excluded && 'pr-prow--off')} data-testid="pru2f-page">
                <span className="pr-num pr-subtle" style={{ fontSize: 11.5, fontWeight: 700 }}>p.{pg.no}{pg.locked && <Icon name="lock" size={10} />}</span>
                <span className="pr-pagecard__thumb" style={{ width: 54, height: 30 }}>{pg.thumb_url ? <img src={pg.thumb_url} alt="" /> : <><i /><i /></>}</span>
                <b className="pr-ell" style={{ fontSize: 13 }}>{pg.title}</b>
                {pg.role_state === 'need' && pg.role_candidates?.length ? (
                  <span role="radiogroup" aria-label={`p.${pg.no} 역할 태그`} className="pr-row" style={{ gap: 4 }}>
                    {pg.role_candidates.slice(0, 2).map((c) => <button key={c} type="button" role="radio" aria-checked={pg.flow_role === c} className="pr-rolecand" onClick={() => void setRole(pg, c)} disabled={busy === `p:${pg.no}`}>{c}</button>)}
                  </span>
                ) : (
                  <select aria-label={`p.${pg.no} 역할 태그`} className="pr-rolesel" value={pg.flow_role ?? ''} disabled={pg.excluded || busy === `p:${pg.no}`} onChange={(e) => void setRole(pg, e.target.value)}>
                    {!pg.flow_role && <option value="">—</option>}
                    {[...new Set([...(pg.flow_role ? [pg.flow_role] : []), ...ROLE_TAGS])].map((r) => <option key={r} value={r}>{r}</option>)}
                  </select>
                )}
                <span className={cx('pr-ell', pg.evidence_warn && 'pr-confpct--warn')} style={{ fontSize: 12 }}>{pg.evidence_warn && <Icon name="warn" size={11} />} {pg.evidence || '—'}</span>
                <span className={STATE_CLS[pg.role_state ?? 'auto'] ?? 'pr-rstate'}>{pg.role_state === 'edited' && <Icon name="lock" size={10} />}{pg.role_state_label || ({ auto: '자동', ok: '확인됨', edited: '수정함', need: '확인 필요' } as Record<string, string>)[pg.role_state ?? 'auto']}</span>
              </div>
            ))}
            {pages.length > 10 && (
              <button type="button" className="pr-prmore" onClick={() => setMore((m) => !m)}>
                {more ? '접기' : <><b className="pr-brand">쪽 11–{pages.length} 더 보기</b> · 확인 필요 {pages.slice(10).filter((x) => x.role_state === 'need').length} · 수정함 {pages.slice(10).filter((x) => x.role_state === 'edited').length}</>}
                <Icon name={more ? 'chevronUp' : 'chevronDown'} size={12} />
              </button>
            )}
          </div>
        ) : <DetailTable detail={cd.detail} />}
        {flow && !!flow.memos?.length && (
          <div className="pr-card pr-memos" data-testid="pru2f-memos">
            <div className="pr-row" style={{ gap: 6 }}><span className="pr-chat__w">W</span><b style={{ fontSize: 13 }}>에이전트 메모</b><span className="pr-note" style={{ fontSize: 11.5 }}>· 이번 제안서에 쓸 때</span></div>
            {flow.memos.map((m) => (
              <div key={m.no} className="pr-row" style={{ gap: 8, alignItems: 'flex-start' }}>
                <span className="pr-revno pr-num" style={{ width: 18, height: 18, fontSize: 10.5 }}>{m.no}</span>
                <span className="pr-colflex" style={{ gap: 4 }}>
                  <span style={{ fontSize: 12.5, lineHeight: 1.55 }}>{m.text}</span>
                  <span className="pr-row" style={{ gap: 6 }}><span className="pr-badge pr-badge--soft" style={{ height: 18, fontSize: 10.5 }}>{m.tag}</span><span className="pr-note pr-ell" style={{ fontSize: 11.5 }}>{m.action}</span></span>
                </span>
              </div>
            ))}
            <span className="pr-note" style={{ fontSize: 11.5, borderTop: '1px solid var(--wm-line)', paddingTop: 8 }}>메모는 활용 방식 추천과 시트 구성 초안에 그대로 반영돼요.</span>
          </div>
        )}
      </div>
    </PrPage>
  );
}

/** 기준별 상세(§7.10 노드 출력) — 배열이면 표, 아니면 항목 줄 */
function DetailTable({ detail }: { detail?: Record<string, unknown> | null }) {
  if (!detail || !Object.keys(detail).length) return <div className="pr-card pr-empty">이 기준의 상세 내용이 아직 없어요</div>;
  return (
    <div className="pr-colflex" style={{ gap: 12 }} data-testid="pru2f-detail">
      {Object.entries(detail).map(([k, v]) => {
        if (Array.isArray(v) && v.length && typeof v[0] === 'object' && v[0]) {
          const cols = [...new Set(v.flatMap((r) => Object.keys(r as object)))].slice(0, 6);
          return (
            <div key={k} className="pr-card" style={{ overflow: 'hidden' }}>
              <div className="pr-cardhead" style={{ height: 36 }}><b style={{ fontSize: 12.5 }}>{k}</b></div>
              <table className="pr-dtable"><thead><tr>{cols.map((c) => <th key={c}>{c}</th>)}</tr></thead>
                <tbody>{v.map((r, i) => <tr key={i}>{cols.map((c) => <td key={c}>{fmt((r as Record<string, unknown>)[c])}</td>)}</tr>)}</tbody></table>
            </div>
          );
        }
        return <div key={k} className="pr-card pr-card--pad" style={{ fontSize: 13 }}><b>{k}</b> · {Array.isArray(v) ? v.map(fmt).join(' · ') : fmt(v)}</div>;
      })}
    </div>
  );
}
const fmt = (v: unknown) => (v === null || v === undefined ? '—' : typeof v === 'object' ? JSON.stringify(v) : String(v));
