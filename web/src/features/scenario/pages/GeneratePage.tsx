/**
 * SC4G · 생성 중(§4.9) — 진행 카드(단계 4 · {pct}% · 약 {t} 남음), 미리보기(완성 · 작성 중(부분 문장) · 대기), 진행 방향 메모, 중지 · 입력 고치기.
 * 실패: 「시나리오를 쓰다가 멈췄어요」 + 다시 시도(같은 thread 재개) · 입력 고치기. 끝나면 SC4 로 바로 간다.
 */
import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router';
import { useQuery } from '@tanstack/react-query';
import { addJobMemo, useJob } from '@/api/jobs';
import { cx } from '@/ui';
import { useShellPage } from '@/shell';
import { errMessage, scApi, type GenerationView } from '../api';
import { qk, useInvalidate, useScenario } from '../hooks';
import { route, SECTION, stepper } from '../lib';
import { Ask, Btn, Card, Ico, Loading, Marked, Note, P, Screen, StatusIcon, W } from '../parts';

export default function GeneratePage() {
  const { id = '', jobId = '' } = useParams();
  const nav = useNavigate();
  const inv = useInvalidate();
  const sc = useScenario(id);
  const [partials, setPartials] = useState<Record<string, string>>({});
  const [memoNote, setMemoNote] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState<'retry' | 'stop' | null>(null);
  const gen = useQuery({ queryKey: qk.gen(id), queryFn: () => scApi.generation(id), enabled: !!id, refetchInterval: (q) => (isLive(q.state.data) ? 1_500 : false) });
  const refetchSoon = useRef<number | undefined>(undefined);
  const job = useJob(jobId, {
    onEvent: (e) => {
      if (e.type === 'log' && e.data?.scene_id && typeof e.data.partial_story === 'string') {
        setPartials((p) => ({ ...p, [e.data.scene_id as string]: e.data.partial_story as string }));
      }
      if (['step', 'progress', 'result', 'status', 'error'].includes(e.type)) {
        if (!refetchSoon.current) refetchSoon.current = window.setTimeout(() => { refetchSoon.current = undefined; void gen.refetch(); }, 250);
      }
    },
    onDone: () => { void gen.refetch(); void inv.sc(id); },
  });
  useEffect(() => () => { if (refetchSoon.current) window.clearTimeout(refetchSoon.current); }, []);

  const g = gen.data;
  const failed = g?.status === 'failed' || job.status === 'failed';
  const done = g?.status === 'done' || sc.data?.status === 'done';
  useEffect(() => {
    if (done) { void inv.scenes(id); nav(route.result(id), { replace: true }); }
  }, [done]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (job.status === 'canceled' || g?.status === 'canceled') nav(route.solutions(id), { replace: true });
  }, [job.status, g?.status]); // eslint-disable-line react-hooks/exhaustive-deps

  useShellPage({ section: SECTION, title: sc.data?.title ?? '', stepper: stepper(4), sidebarGroup: 'scenario' });
  if (!g) return <Loading />;

  const retry = async () => {
    setBusy('retry'); setErr(null);
    try { await scApi.resume(id, jobId); await gen.refetch(); await inv.sc(id); } catch (e) { setErr(errMessage(e)); } finally { setBusy(null); }
  };
  const stop = async () => {
    setBusy('stop'); setErr(null);
    try { await scApi.cancel(id); await inv.sc(id); nav(route.solutions(id)); } catch (e) { setErr(errMessage(e)); setBusy(null); }
  };
  const memo = async (text: string) => {
    try {
      await addJobMemo(jobId, text);
      setMemoNote(`「${text}」 — 다음 장면부터 반영해요 · 이미 쓴 장면은 결과에서 고칠 수 있어요`);
    } catch (e) { setErr(errMessage(e)); }
  };

  const n = g.total || g.scenes.length;
  const reason = g.failed_reason || job.job?.error?.message || '잠시 뒤 다시 시도해 주세요';
  const dock = failed ? (
    <Card title="시나리오 생성 멈춤" meta="4 / 4 · 끝난 장면은 그대로 두고 이어서 써요" testId="sc4g-failed-card"
      foot={<>
        <Btn to={route.solutions(id)} testId="sc4g-fix">입력 고치기</Btn>
        <button type="button" className="sc-btn sc-btn--primary" onClick={() => void retry()} disabled={busy === 'retry'} data-testid="sc4g-retry">
          <Ico d={P.refresh} size={15} sw={2.2} />다시 시도
        </button>
      </>}>
      {err && <div className="sc-card__sec"><Note tone="err">{err}</Note></div>}
    </Card>
  ) : (
    <Card title="시나리오 생성 중" meta="4 / 4 · 다른 작업을 해도 돼요, 끝나면 알려드릴게요" testId="sc4g-card"
      right={<Link to={route.list()} className="sc-link" data-testid="sc4g-wait"><Ico d="M4 6h16M4 12h16M4 18h10" size={13} sw={2.2} />작업 목록에서 기다리기</Link>}>
      <div className="sc-card__foot" style={{ gap: 10 }}>
        <Ask id="sc4g-memo" label="진행 방향 메모" placeholder="진행 중에도 방향을 알려주세요 (예: 장면 3은 본사 담당자 시점으로)" onSubmit={memo} sendLabel="보내기" testId="sc4g-memo" />
        <button type="button" className="sc-btn" onClick={() => void stop()} disabled={busy === 'stop'} data-testid="sc4g-stop">
          <svg width="12" height="12" viewBox="0 0 24 24" aria-hidden="true"><rect x="6" y="6" width="12" height="12" rx="2" style={{ fill: 'var(--wm-text)' }} /></svg>중지 · 입력 고치기
        </button>
      </div>
      {err && <div className="sc-card__sec" style={{ paddingBottom: 14 }}><Note tone="err">{err}</Note></div>}
    </Card>
  );

  return (
    <Screen dock={dock} tight testId="sc4g">
      <div className="sc-w">
        <span className="sc-w__logo" aria-hidden="true">W</span>
        <div className="sc-w__body" style={{ gap: 12 }}>
          <div className="sc-w__text" data-testid="sc4g-w">
            {failed ? `시나리오를 쓰다가 멈췄어요. ${reason}` : `${n}개 장면으로 시나리오를 쓰고 있어요. 끝난 장면부터 아래에 미리 보여드릴게요.`}
          </div>
          {memoNote && !failed && <div className="sc-w__note" data-testid="sc4g-memo-note"><Ico d={P.check} size={13} sw={2.4} color="var(--wm-brand)" />{memoNote}</div>}
          <ProgressCard g={g} id={id} />
          <div className="sc-row" style={{ justifyContent: 'space-between', paddingTop: 2 }}>
            <span style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--wm-text-2)' }}>미리보기 <span style={{ color: 'var(--wm-text-muted)', fontWeight: 500 }}>· 끝난 장면부터</span></span>
            <span className="wm-num" style={{ fontSize: 12, fontWeight: 700, color: 'var(--wm-text-muted)' }} data-testid="sc4g-count">{g.done} / {n}</span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }} data-testid="sc4g-preview">
            {g.scenes.map((s) => {
              if (s.status === 'done') {
                return (
                  <div key={s.id} className="sc-prev" data-testid="sc4g-scene" data-status="done">
                    <TimeNo time={s.time} no={s.no} />
                    <div className="sc-prev__main">
                      <div className="sc-prev__title"><Marked text={s.title} /></div>
                      <div className="sc-row" style={{ gap: 6, whiteSpace: 'nowrap', overflow: 'hidden' }}>
                        {(s.chips ?? []).map((c) => <span key={c} className="sc-mini sc-mini--brand">{c}</span>)}
                        {(s.product_chips ?? []).map((c) => <span key={c} className="sc-mini">{c}</span>)}
                      </div>
                    </div>
                    <span className="sc-prev__st"><Ico d={P.check} size={13} sw={2.6} color="var(--wm-brand)" />완성</span>
                  </div>
                );
              }
              if (s.status === 'writing') {
                const part = partials[s.id] ?? s.partial_story ?? '';
                return (
                  <div key={s.id} className="sc-prev sc-prev--run" data-testid="sc4g-scene" data-status="writing">
                    <TimeNo time={s.time} no={s.no} />
                    <div className="sc-prev__main" style={{ gap: 5 }}>
                      <div className="sc-prev__title">{s.title || `${s.label} — 작성 중`}</div>
                      {g.streaming && part
                        ? <div className="sc-prev__partial" data-testid="sc4g-partial"><span className="wm-ellipsis">{part}</span><span className="sc-caret" /></div>
                        : <div className="sc-prev__partial"><span className="wm-ellipsis">{s.beat_text}</span><span className="sc-typing" aria-label="입력 중"><i /><i /><i /></span></div>}
                      <div className="sc-row" style={{ gap: 6 }}><span className="sc-skel" style={{ width: 220 }} /><span className="sc-skel" style={{ width: 120 }} /></div>
                    </div>
                    <span className="sc-prev__st sc-prev__st--run"><StatusIcon kind="gen" size={14} />작성 중</span>
                  </div>
                );
              }
              return (
                <div key={s.id} className={cx('sc-prev sc-prev--wait', s.status === 'failed' && 'sc-prev--failed')} data-testid="sc4g-scene" data-status={s.status}>
                  <div style={{ width: 54, flexShrink: 0 }}><span className="wm-num" style={{ fontSize: 12, fontWeight: 700, color: 'var(--wm-text-subtle)' }}>{s.time ?? ''}</span></div>
                  <div style={{ flex: 1, minWidth: 0, fontSize: 13, color: 'var(--wm-text-subtle)', whiteSpace: 'nowrap' }}>장면 {s.no} · {s.label}</div>
                  <span style={{ flexShrink: 0, fontSize: 12, fontWeight: 600, color: s.status === 'failed' ? 'var(--wm-warn)' : 'var(--wm-text-subtle)' }}>{s.status === 'failed' ? '멈춤' : '대기'}</span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </Screen>
  );
}

const isLive = (g?: GenerationView) => !!g && ['queued', 'running', 'idle'].includes(g.status);

function TimeNo({ time, no }: { time?: string | null; no: number }) {
  return (
    <div style={{ width: 54, flexShrink: 0, display: 'flex', flexDirection: 'column', gap: 2 }}>
      <span className="wm-num" style={{ fontSize: 12, fontWeight: 700, color: 'var(--wm-brand)' }}>{time ?? ''}</span>
      <span style={{ fontSize: 11, color: 'var(--wm-text-muted)' }}>장면 {no}</span>
    </div>
  );
}

function ProgressCard({ g, id }: { g: GenerationView; id: string }) {
  const ST: Record<string, string> = { done: '완료', run: '진행 중', wait: '대기' };
  const inner = (
    <>
      <div className="sc-progress__head">
        <div className="sc-row" style={{ justifyContent: 'space-between', gap: 12 }}>
          <div className="sc-row" style={{ gap: 8, minWidth: 0 }}>
            <span className="sc-progress__icon"><Ico d={P.play} size={14} color="var(--wm-brand)" /></span>
            <span style={{ fontSize: 14, fontWeight: 700, whiteSpace: 'nowrap' }}>시나리오 생성 중</span>
            <span className="wm-ellipsis" style={{ fontSize: 12, color: 'var(--wm-text-muted)' }} data-testid="sc4g-summary">{g.summary}</span>
          </div>
          <span className="wm-num" style={{ fontSize: 13, fontWeight: 700, color: 'var(--wm-brand)', whiteSpace: 'nowrap', flexShrink: 0 }} data-testid="sc4g-pct">
            {g.pct}%{g.eta_text ? ` · ${g.eta_text}` : ''}
          </span>
        </div>
        <div className="sc-bar" role="progressbar" aria-valuenow={g.pct} aria-valuemin={0} aria-valuemax={100} aria-label="시나리오 생성 진행"><span style={{ width: `${g.pct}%` }} /></div>
      </div>
      <div className="sc-progress__stages" data-testid="sc4g-stages">
        {g.stages.map((s) => (
          <div key={s.key} className={cx('sc-stage', s.state === 'run' && 'sc-stage--run')} data-state={s.state} data-testid="sc4g-stage">
            <StatusIcon kind={s.state === 'done' ? 'done' : s.state === 'run' ? 'gen' : 'wait'} size={20} />
            <span className="sc-stage__name">{s.name}</span>
            <span className="sc-stage__note">{s.note}</span>
            <span className={cx('sc-stage__st', s.state === 'run' && 'sc-stage__st--run', s.state === 'wait' && 'sc-stage__st--wait')}>{ST[s.state]}</span>
          </div>
        ))}
      </div>
    </>
  );
  return g.status === 'done'
    ? <Link to={route.result(id)} className="sc-progress" data-testid="sc4g-progress">{inner}</Link>
    : <div className="sc-progress" data-testid="sc4g-progress">{inner}</div>;
}
