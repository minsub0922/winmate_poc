/** MI3G — 분석 진행 중 `/mi/:id/run` (§4.10) — jobs SSE 의 step(stage 스냅숏) · progress(pct · eta_s) 로 그린다 */
import { useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { PathIcon, cx, toast } from '@/ui';
import { addJobMemo, cancelJob, type JobEvent } from '@/api/jobs';
import { errText, qk, startRun, useAnalysis, useProgress, type RunProgress } from '../api';
import { useJobWatch } from '../hooks';
import { AREA_NAME, clampPct, etaText } from '../lib';
import { Agent, BigButton, Dock, ErrorBand, Ic, LoadingCard, MiPage, P, PromptInput, SecButton, Spin, UserBubble, useAid, useMiShell } from '../parts';

type Snap = Pick<RunProgress, 'stages' | 'areas' | 'sources' | 'recent_sources' | 'previewable'>;

export function RunPage() {
  const aid = useAid();
  const nav = useNavigate();
  const qc = useQueryClient();
  const [sp] = useSearchParams();
  const then = sp.get('then') === 'slides' ? 'slides' : 'result';
  const a = useAnalysis(aid, { poll: 4000 });
  useMiShell(a.data, 3);
  const prog = useProgress(aid);
  const jobId = a.data?.current_job_id ?? prog.data?.job_id ?? null;
  const status = a.data?.status;
  const live = status === 'queued' || status === 'running';
  const [snap, setSnap] = useState<Snap | null>(null);
  const [pct, setPct] = useState<number | null>(null);
  const [eta, setEta] = useState<number | null>(null);
  const [memos, setMemos] = useState<Array<{ text: string; applied?: string }>>([]);
  const [failed, setFailed] = useState<string | null>(null);
  const [stopping, setStopping] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const [labels, setLabels] = useState<Array<{ label: string; status: string }>>([]);

  useEffect(() => { setSnap(null); setPct(null); setEta(null); setFailed(null); setLabels([]); }, [jobId]);

  const job = useJobWatch(live ? jobId : null, {
    onEvent: (e: JobEvent) => {
      if (e.type === 'step' && e.data.stage && e.data.stages) setSnap(e.data as unknown as Snap);
      if (e.type === 'step' && !e.data.stage && e.data.label) {
        setLabels((x) => [...x.filter((y) => y.label !== e.data.label), { label: String(e.data.label), status: String(e.data.status ?? 'run') }]);
      }
      if (e.type === 'progress') {
        if (typeof e.data.progress === 'number') setPct((p) => Math.max(p ?? 0, e.data.progress as number));
        if (typeof e.data.eta_s === 'number') setEta(e.data.eta_s as number);
      }
      if (e.type === 'log' && typeof e.data.message === 'string' && e.data.message.startsWith('메모를 반영했어요')) {
        const msg = e.data.message as string;
        setMemos((m) => {
          const i = m.findIndex((x) => !x.applied);
          return i < 0 ? m : m.map((x, j) => (j === i ? { ...x, applied: msg } : x));
        });
      }
      if (e.type === 'error') setFailed(String(e.data.message ?? ''));
    },
    onDone: (j) => {
      void qc.invalidateQueries({ queryKey: qk.analysis(aid ?? '') });
      void qc.invalidateQueries({ queryKey: ['mi', 'result', aid ?? ''] });
      void qc.invalidateQueries({ queryKey: ['mi', 'list'] });
      if (j.status === 'succeeded') nav(`/mi/${aid}/${then}`, { replace: true });
      else if (j.status === 'canceled') nav(`/mi/${aid}/${hasCompetitor() ? 'competitors' : 'scope'}`, { replace: true });
      else if (j.status === 'failed') setFailed(j.error?.message ?? '');
    },
  });
  const hasCompetitor = () => (a.data?.scope?.areas ?? []).includes('competitor');

  // 이미 끝났으면 결과로(MI0 `진행 보기` 가 늦게 열렸을 때 등)
  useEffect(() => {
    if (status === 'done' || status === 'upd') nav(`/mi/${aid}/${then}`, { replace: true });
  }, [status, aid, nav, then]);

  const s: Snap | undefined = snap ?? (prog.data as Snap | undefined);
  const p = clampPct(pct ?? prog.data?.pct ?? job.progress ?? 0);
  const etaS = eta ?? prog.data?.eta_s ?? null;
  const head = prog.data;
  const done = (s?.areas ?? []).filter((x) => x.status === 'done');
  const preview = s?.previewable ?? [];
  const src = (s?.sources ?? {}) as Record<string, number>;

  async function memo(text: string) {
    if (!jobId) return;
    setMemos((m) => [...m, { text }]);
    try { await addJobMemo(jobId, text); } catch (e) { toast(errText(e)); }
  }
  async function stop() {
    if (!jobId) return;
    setStopping(true);
    try { await cancelJob(jobId); } catch (e) { toast(errText(e)); setStopping(false); }
  }
  async function retry() {
    if (!aid) return;
    setRetrying(true);
    try {
      await startRun(aid, { mode: 'resume' });
      setFailed(null);
      await qc.invalidateQueries({ queryKey: qk.analysis(aid) });
      await qc.invalidateQueries({ queryKey: qk.progress(aid) });
    } catch (e) { toast(errText(e)); } finally { setRetrying(false); }
  }
  async function start() {
    if (!aid) return;
    try {
      await startRun(aid, { mode: 'full' });
      await qc.invalidateQueries({ queryKey: qk.analysis(aid) });
      await qc.invalidateQueries({ queryKey: qk.progress(aid) });
    } catch (e) { toast(errText(e)); }
  }

  const failedState = !!failed || status === 'failed';
  const idle = !!a.data && !live && !failedState && status !== 'done' && status !== 'upd';
  const chip = (head?.summary_chip ?? '').replace(/^분석 시작/, '').trim();
  const generic = !!job.job && job.job.kind !== 'mi.analyze';
  const title = generic ? `${job.job?.title || '데이터 보강'} 중` : head?.card_title;
  const sub = generic ? (then === 'slides' ? '레이아웃에 모자란 데이터만 더 찾아요' : '') : head?.card_sub;
  return (
    <MiPage dock={
      <Dock title="분석 진행 중" meta="3 / 3 · 다른 작업을 해도 돼요, 끝나면 알려 드릴게요"
        row={
          <div className="mi-dock__row">
            <PromptInput label="진행 방향 메모" placeholder="진행 중에도 방향을 알려주세요 (예: 경쟁사 C는 클라우드 CMS 위주로)" onSend={memo} disabled={!live || !jobId} />
            <SecButton to="/mi">목록으로</SecButton>
            <button type="button" className="mi-btn" title="중지하고 설정으로 돌아가요. 정리된 영역은 남겨 둡니다." onClick={() => void stop()} disabled={!live || !jobId || stopping}
              data-testid="mi3g-stop">
              {stopping ? <Spin size={12} /> : <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><rect x="6" y="6" width="12" height="12" rx="2" /></svg>}중지
            </button>
          </div>
        } />
    }>
      <UserBubble chip><b>분석 시작</b>{chip && <>{' '}<small>{chip}</small></>}</UserBubble>
      <Agent text="분석하고 있어요. 공개 자료와 사내 사례 DB를 찾아 읽고, 영역별로 정리한 뒤 결과를 씁니다. 이 화면을 떠나도 계속 진행되고, 끝나면 알려 드릴게요.">
        {(a.isError || prog.isError) && <ErrorBand onRetry={() => { void a.refetch(); void prog.refetch(); }} />}
        {!head && !prog.isError && <LoadingCard lines={6} />}
        {head && (
          <div className="mi-card" data-testid="mi3g-card">
            <div className="mi-prog__top">
              <div className="mi-row" style={{ justifyContent: 'space-between' }}>
                <div className="mi-row">
                  <div className="mi-prog__icon"><PathIcon d={P.chart} size={13} strokeWidth={2.4} /></div>
                  <span className="mi-prog__title">{title}</span>
                  <span className="mi-prog__sub">{sub}</span>
                </div>
                <span className="mi-prog__pct" data-testid="mi3g-pct"><span className="mi-num">{p}%</span>{etaS !== null && live ? ` · ${etaText(etaS)} 남음` : ''}</span>
              </div>
              <div className="mi-bar" role="progressbar" aria-valuenow={p} aria-valuemin={0} aria-valuemax={100} aria-label="분석 진행률"><div style={{ width: `${p}%` }} /></div>
            </div>
            {generic ? (
              <div className="mi-loading">
                <div className="mi-steps-mini">
                  {labels.map((l) => (
                    <div key={l.label} className={cx('mi-steps-mini__row', l.status === 'done' ? 'mi-steps-mini__row--done' : 'mi-steps-mini__row--run')}>
                      {l.status === 'done' ? <span className="mi-dot-done mi-dot-done--sm"><PathIcon d={P.check} size={9} strokeWidth={3.4} /></span> : <Spin size={18} />}{l.label}
                    </div>
                  ))}
                  {!labels.length && <div className="mi-steps-mini__row mi-steps-mini__row--run"><Spin size={18} />준비 중</div>}
                </div>
              </div>
            ) : (
            <>
            <div className="mi-stages">
              {(s?.stages ?? []).map((st, i, arr) => (
                <StageBox key={st.stage} no={i + 1} name={st.name} note={st.note} status={st.status} last={i === arr.length - 1} />
              ))}
            </div>
            <div className="mi-prog__grid">
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6, minWidth: 0 }}>
                <span style={{ fontSize: 12, fontWeight: 700 }}>영역별 진행</span>
                <div className="mi-areas">
                  {(s?.areas ?? []).map((x) => (
                    <div key={x.area} className={cx('mi-area', `mi-area--${x.status}`)} data-area={x.area} data-status={x.status}>
                      {x.status === 'done' ? <span className="mi-dot-done mi-dot-done--sm"><PathIcon d={P.check} size={9} strokeWidth={3.4} /></span>
                        : x.status === 'run' ? <Spin size={18} />
                          : x.status === 'failed' ? <span className="mi-dot-fail"><PathIcon d={P.x} size={9} strokeWidth={3.4} /></span>
                            : <span className="mi-dot-wait mi-dot-wait--sm" />}
                      <span className="mi-area__name">{x.name}</span>
                      <span className="mi-area__note">{x.note}</span>
                      <span className="mi-area__st">{x.status === 'done' ? '정리 완료' : x.status === 'run' ? '정리 중' : x.status === 'failed' ? '정리 실패' : '대기'}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div className="mi-srcbox">
                <div className="mi-row" style={{ justifyContent: 'space-between', alignItems: 'flex-end' }}>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                    <span style={{ fontSize: 12, fontWeight: 700 }}>확인한 출처</span>
                    <span className="mi-row" style={{ alignItems: 'baseline', gap: 3 }}><span className="mi-srcbox__total" data-testid="mi3g-src-total">{src.total ?? 0}</span><span style={{ fontSize: 12.5, color: 'var(--wm-text-2)' }}>곳</span></span>
                  </div>
                  <span className="mi-srcbox__meta">사용 {src.used ?? 0} · 확인 중 {src.checking ?? 0}<br />제외 {src.excluded ?? 0} (오래됨 · 중복)</span>
                </div>
                <div className="mi-srcbox__list">
                  {(s?.recent_sources ?? []).slice(0, 4).map((o, i) => (
                    <div key={o.name + i} className="mi-srcrow">
                      <span className={cx('mi-srckind', o.kind === '사내' && 'mi-srckind--in')}>{o.kind}</span>
                      <span className="mi-grow mi-ell">{o.name}</span>
                      <span className={cx('mi-srcrow__st', o.state === '사용' && 'mi-srcrow__st--used', o.state === '확인 중' && 'mi-srcrow__st--checking')}>{o.state}</span>
                    </div>
                  ))}
                </div>
                <Link to={`/mi/${aid}/result?preview=1&panel=sources`} className="mi-link" style={{ fontSize: 12 }} aria-disabled={!preview.length}
                  onClick={(e) => { if (!preview.length) { e.preventDefault(); toast('정리된 영역이 생기면 볼 수 있어요'); } }}>
                  출처 전체 보기<Ic d={P.chevR} size={12} w={2.4} /></Link>
              </div>
            </div>
            </>
            )}
            {preview.length > 0 && !generic && (
              <div className="mi-prog__foot" data-testid="mi3g-preview">
                <span>먼저 끝난 영역부터 볼 수 있어요 · {preview.map((x) => AREA_NAME[x as keyof typeof AREA_NAME] ?? x).join(' · ')}</span>
                <Link to={`/mi/${aid}/result?preview=1`} className="mi-link">정리된 내용 미리 보기<Ic d={P.chevR} size={12} w={2.4} /></Link>
              </div>
            )}
            {failedState && (
              <div className="mi-prog__err" role="alert">
                <Ic d={P.warn} size={15} />
                <span className="mi-grow">분석을 마치지 못했어요. 정리된 영역은 남겨 두었어요.{failed ? ` (${failed})` : ''}</span>
                <button type="button" className="mi-mini mi-mini--primary" onClick={() => void retry()} disabled={retrying}>다시 시도</button>
              </div>
            )}
            {idle && (
              <div className="mi-prog__err">
                <span className="mi-grow">{status === 'stopped' ? `중지했어요 · 정리된 영역 ${done.length}개를 남겨 두었어요.` : '아직 분석을 시작하지 않았어요.'}</span>
                <BigButton onClick={() => void start()} arrow={false}>{a.data?.run_label || '분석 시작 (약 3분)'}</BigButton>
              </div>
            )}
          </div>
        )}
      </Agent>
      {memos.map((m, i) => (
        <div key={i} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <UserBubble>{m.text}</UserBubble>
          {m.applied && <Agent text={m.applied} />}
        </div>
      ))}
    </MiPage>
  );
}

function StageBox({ no, name, note, status, last }: { no: number; name: string; note?: string; status: string; last: boolean }) {
  return (
    <>
      <div className={cx('mi-stage', status === 'run' && 'mi-stage--run', status === 'wait' && 'mi-stage--wait')} data-stage-status={status}>
        {status === 'done' ? <span className="mi-dot-done"><PathIcon d={P.check} size={10} strokeWidth={3.2} /></span> : status === 'run' ? <Spin size={20} /> : <span className="mi-dot-wait" />}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 1, minWidth: 0 }}>
          <span className="mi-stage__name">{no} {name}</span>
          <span className="mi-stage__note">{note}</span>
        </div>
      </div>
      {!last && <Ic d={P.chevR} size={14} w={2.4} className="mi-sub" />}
    </>
  );
}
