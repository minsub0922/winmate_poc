/**
 * VP3G — 생성 중 · 결정 기록(`/vp/:id/generating?job=`): 5단계 · 결정 기록(log 이벤트) · 지금 하는 일 · 시트 · 미리 보기 · 메모 · 중지.
 */
import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router';
import { Icon, Skeleton } from '@/ui';
import { addJobMemo, cancelJob } from '@/api/jobs';
import { errText, generate, useRefresh, useVp } from '../api';
import { Agent, Btn, BtnLink, Dock, ICONS, ModeChip, PIcon, Page, UserBubble, VThumb, useJobDone, useVpShell } from '../parts';

const STAGES = ['재료 정리', '구조 결정', '시트 작성', '레이아웃 맞춤', '검토'];
const NODE_STAGE: Record<string, number> = { prepare: 1, decide: 2, write_sheets: 3, fit_layout: 4, review: 5, apply: 3, images: 4, export: 1 };

export function GeneratingPage() {
  const { id = '' } = useParams();
  const [sp] = useSearchParams();
  const nav = useNavigate();
  const vp = useVp(id, { poll: 2000 });
  const doc = vp.data;
  useVpShell(doc, 3);
  const refresh = useRefresh(id);
  const jobId = sp.get('job') || doc?.active_job?.job_id || doc?.last_job?.job_id || null;
  const [err, setErr] = useState('');
  const [stopping, setStopping] = useState(false);
  const j = useJobDone(jobId, async (snap) => {
    await refresh();
    if (snap.status === 'succeeded') nav(`/vp/${id}/result`);
    else if (snap.status === 'canceled') nav(`/vp/${id}/structure`);
    else setErr(snap.error?.message || '만들기를 마치지 못했어요');
  });

  useEffect(() => { void refresh(); }, [j.events.length]); // eslint-disable-line react-hooks/exhaustive-deps

  const stageNow = useMemo(() => {
    let st = 0;
    let activity = '';
    for (const e of j.events) {
      if (e.type === 'step') {
        const s = Number(e.data.stage) || NODE_STAGE[e.data.step as string] || 0;
        if (e.data.status === 'running') { st = Math.max(st, s); if (e.data.activity) activity = String(e.data.activity); }
        if (e.data.status === 'done') st = Math.max(st, s + 1);
      }
    }
    return { st, activity };
  }, [j.events]);

  if (!doc) return <Page><Skeleton h={320} /></Page>;
  const done = j.status === 'succeeded';
  const failed = j.status === 'failed' || doc.status === 'failed';
  const pct = done ? 100 : j.progress || doc.active_job?.progress || 0;
  const evProgress = [...j.events].reverse().find((e) => e.type === 'progress');
  const eta = Number(evProgress?.data.eta_seconds ?? 0);
  const etaText = done ? '완료' : eta >= 90 ? `약 ${Math.round(eta / 60)}분 남음` : eta > 0 ? `약 ${eta}초 남음` : '곧 끝나요';
  const sheets = (doc.sheets ?? []).filter((s) => s.kind === 'main' || s.kind === 'summary');
  const n = sheets.length || (doc.plan?.sheets?.length ?? 0);
  const k = sheets.filter((s) => s.status === 'done').length;
  const firstDone = sheets.find((s) => s.status === 'done');
  const logs = (doc.decisions ?? []).filter((d) => !jobId || d.job_id === jobId);
  const live = j.events.filter((e) => e.type === 'log').map((e) => ({ id: String(e.data.id ?? e.id), t: String(e.data.t ?? ''), text: String(e.data.message ?? ''), mode: String(e.data.mode ?? 'auto') }));
  const rows = (logs.length >= live.length ? logs.map((d) => ({ id: d.id, t: d.t, text: d.text, mode: d.mode })) : live).slice(-8);
  const curStage = done ? 6 : Math.max(stageNow.st, 1);

  const stop = async () => {
    if (!jobId) return;
    setStopping(true);
    try { await cancelJob(jobId); } catch (e) { setErr(errText(e)); setStopping(false); }
  };
  const retry = async () => {
    try { const r = await generate(id, true); setErr(''); nav(`/vp/${id}/generating?job=${r.job_id}`, { replace: true }); } catch (e) { setErr(errText(e)); }
  };
  const memo = async (text: string) => { if (jobId) await addJobMemo(jobId, text); };

  return (
    <Page dock={
      <Dock title="만드는 중" meta={`${k} / ${n} · 다른 작업을 해도 돼요`}
        input={{ placeholder: '진행 중에도 방향을 알려주세요 (예: 학생 가치는 수업 참여도로)', label: '진행 방향 메모', onSend: memo, disabled: done || failed }}
        actions={<>
          <BtnLink to="/vp/legacy">목록으로</BtnLink>
          {failed
            ? <Btn primary onClick={retry}>다시 시도</Btn>
            : <Btn onClick={stop} busy={stopping} disabled={done} title="중지하고 가치 구조로 돌아가요. 끝난 시트는 남겨 둡니다.">
              <Icon name="stop" size={14} />중지
            </Btn>}
        </>} />
    }>
      <UserBubble head="만들기" rest={doc.labels?.generate} />
      <Agent text="만들고 있어요. 단계마다 스스로 정한 것을 아래에 남겨 둘게요 — 이 화면을 떠나도 계속 진행되고, 끝나면 알려 드립니다.">
        <div className="vp-card" data-testid="vp-generating">
          <div className="vp-gen__top">
            <div className="vp-gen__head">
              <span style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 }}>
                <span className="vp-gen__icon"><PIcon d={ICONS.diamond} size={13} /></span>
                <span style={{ fontSize: 14, fontWeight: 700, whiteSpace: 'nowrap' }}>가치 제안 {n}장 만드는 중</span>
                <span className="vp-card__sub">{doc.labels?.head_codes}</span>
              </span>
              <span className="vp-gen__pct"><span className="vp-num">{pct}%</span> · {etaText}</span>
            </div>
            <div className="vp-bar" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}><i style={{ width: `${pct}%` }} /></div>
            <div className="vp-stages">
              {STAGES.map((name, i) => {
                const s = i + 1;
                const state = s < curStage ? 'done' : s === curStage ? 'run' : 'wait';
                return (
                  <div key={name} className={`vp-stage vp-stage--${state}`} data-state={state}>
                    {state === 'done' && <span className="vp-stage__done"><Icon name="check" size={10} /></span>}
                    {state === 'run' && <span className="vp-spin" />}
                    {state === 'wait' && <span className="vp-stage__wait" />}
                    <span className="vp-stage__name">{name}</span>
                  </div>
                );
              })}
            </div>
          </div>
          <div className="vp-gen__grid">
            <div className="vp-log">
              <span style={{ fontSize: 12, fontWeight: 700, marginBottom: 4 }}>결정 기록 <span style={{ color: 'var(--wm-text-muted)', fontWeight: 500 }}>· 에이전트가 스스로 정한 순서대로</span></span>
              {rows.map((r) => (
                <div key={r.id} className="vp-log__row">
                  <span className="vp-log__t">{r.t}</span>
                  <span className="vp-log__d" title={r.text}>{r.text}</span>
                  <ModeChip mode={r.mode} />
                </div>
              ))}
              {!done && !failed && (
                <div className="vp-log__now"><span className="vp-spin" /><span>{stageNow.activity || '준비하고 있어요'}</span></div>
              )}
              {failed && <div className="vp-err" style={{ minHeight: 30, display: 'flex', alignItems: 'center' }}>만들기를 마치지 못했어요 · {err || doc.last_error?.message as string || '잠시 후 다시 시도해 주세요'}</div>}
            </div>
            <div className="vp-gsheets">
              <span style={{ fontSize: 12, fontWeight: 700 }}>시트</span>
              {(sheets.length
                ? sheets.map((s) => ({ key: s.id, status: s.status, layout: s.layout, step_label: s.step_label }))
                : (doc.plan?.sheets ?? []).map((p) => ({ key: `plan:${p.role}`, status: 'waiting', layout: p.layout, step_label: p.step_label }))
              ).map((s) => {
                const st = s.status === 'done' ? 'done' : s.status === 'writing' ? 'run' : 'wait';
                return (
                  <div key={s.key} className={`vp-gsheet vp-gsheet--${st}`} data-status={s.status}>
                    <span style={{ width: 120, height: 68, alignSelf: 'center' }}><VThumb code={s.layout.code} kind={s.layout.thumb.kind} n={s.layout.thumb.n} /></span>
                    <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 6 }}>
                      <span style={{ fontSize: 12, fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}><span className="vp-num">{s.layout.display}</span> {s.step_label}</span>
                      <span className="vp-gsheet__st">{st === 'done' ? '완료' : st === 'run' ? '작성 중' : '대기'}</span>
                    </span>
                  </div>
                );
              })}
              <span style={{ fontSize: 11.5, color: 'var(--wm-text-muted)', lineHeight: 1.5 }}>재료 · {doc.labels?.materials_footer || '연결한 자료'}</span>
            </div>
          </div>
          {firstDone && (
            <div className="vp-card__foot" style={{ justifyContent: 'space-between', fontSize: 12.5 }}>
              <span>먼저 끝난 시트부터 볼 수 있어요 · {firstDone.step_label} ({firstDone.layout.display})</span>
              <Link to={`/vp/${id}/result`} style={{ fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: 4 }}>미리 보기<Icon name="arrowRight" size={13} /></Link>
            </div>
          )}
        </div>
      </Agent>
    </Page>
  );
}
