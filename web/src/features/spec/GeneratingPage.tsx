/** SP3G — 생성 중 · 값 확인(`/spec/:id/generating?job=`, 06-spec §4.9 · §3.4) */
import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router';
import { uploadFile } from '@/api/client';
import { cancelJob, useJob, type JobEvent } from '@/api/jobs';
import { PathIcon, cx, toast } from '@/ui';
import {
  addDatasheet, answerCheck, applyChecks, deferAll, errText, generate, isApiError, sendMessage, useSheet, useSheetCache,
  type Sheet, type ValueCheck,
} from './api';
import { SourcesModal, useFilePicker } from './parts';
import { Agent, BigButton, Dock, PromptInput, SpPage, UserBubble, useSpecShell } from './ui';

type StepState = { status: 'wait' | 'run' | 'done'; note: string };
const STAGES: Array<[string, string]> = [
  ['resolve_models', '모델 확인'], ['fetch_specs', '스펙 가져오기'], ['verify', '값 검증'], ['mark_wins', '우위 항목 표시'], ['compose', '시트 구성'],
];
const LANG_LABEL: Record<string, string> = { ko: '한국어', en: 'English', ko_en: '한/영' };

function waitNotes(s: Sheet | undefined): Record<string, string> {
  const single = (s?.products.length ?? 0) < 2;
  return {
    resolve_models: '', fetch_specs: '', verify: '',
    mark_wins: single ? '단일 제품 — 건너뜀' : '모델 간 차이 비교',
    compose: `${s?.agent?.kind_name ?? '비교표'} · ${LANG_LABEL[s?.format.language ?? 'ko']}`,
  };
}

function Spin({ size = 18 }: { size?: number }) {
  return (
    <svg className="sp-spin" width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle cx="12" cy="12" r="9" stroke="var(--wm-line-step)" strokeWidth="3" />
      <path d="M12 3a9 9 0 0 1 9 9" stroke="var(--wm-brand)" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
}

function StepIcon({ st }: { st: StepState['status'] }) {
  if (st === 'done') return <span className="sp-gstep__done"><PathIcon d="M5 12l5 5L20 7" size={9} strokeWidth={3.4} /></span>;
  if (st === 'run') return <Spin />;
  return <span className="sp-gstep__wait" />;
}

export default function GeneratingPage() {
  const { id = '' } = useParams();
  const [sp, setSp] = useSearchParams();
  const nav = useNavigate();
  const cache = useSheetCache();
  const jobParam = sp.get('job');
  const [running, setRunning] = useState(true);
  const sheetQ = useSheet(id, { poll: running ? 1000 : false });
  const s = sheetQ.data;
  const jobId = jobParam ?? s?.active_job?.id ?? null;

  const [steps, setSteps] = useState<Record<string, StepState>>({});
  const [pct, setPct] = useState(0);
  const [eta, setEta] = useState<number | null>(null);
  const [failed, setFailed] = useState<string | null>(null);
  const [answers, setAnswers] = useState<Record<string, { option_key?: string; value_text?: string; alt_measure?: string }>>({});
  const [errs, setErrs] = useState<Record<string, string>>({});
  const [applying, setApplying] = useState(false);
  const [waitingApply, setWaitingApply] = useState(false);
  const [dsJob, setDsJob] = useState<{ job: string; check: string } | null>(null);
  const [src, setSrc] = useState<ValueCheck | null>(null);
  const dsTarget = useRef<ValueCheck | null>(null);

  useSpecShell(s, 3);

  const onEvent = (e: JobEvent) => {
    if (e.type === 'step' && e.data.step) {
      setSteps((prev) => ({ ...prev, [e.data.step]: { status: e.data.status === 'done' ? 'done' : 'run', note: e.data.note ?? prev[e.data.step]?.note ?? '' } }));
    }
    if (e.type === 'progress') {
      if (typeof e.data.progress === 'number') setPct(e.data.progress);
      setEta(typeof e.data.eta_s === 'number' ? e.data.eta_s : null);
    }
  };

  const finish = async (status: string, result: Record<string, unknown> | null | undefined, error?: { message?: string } | null) => {
    setRunning(false);
    await cache.refresh(id);
    if (status === 'canceled') { nav(`/spec/${id}/items`, { replace: true }); return; }
    if (status === 'failed') { setFailed(error?.message ?? '알 수 없는 오류'); return; }
    setPct(100);
    setEta(null);
    const next = typeof result?.next_route === 'string' ? (result.next_route as string) : null;
    if (next && !next.includes('/generating')) nav(next, { replace: true });
  };

  const jobState = useJob(jobId, { onEvent, onDone: (j) => { void finish(j.status, j.result, j.error); } });

  // 처음 열었을 때 이미 끝난 잡(값 확인으로 돌아온 경우) — 스냅숏으로 판단
  useEffect(() => {
    const j = jobState.job;
    if (!j) return;
    if (['succeeded', 'failed', 'canceled'].includes(j.status)) {
      setRunning(false);
      if (j.status === 'succeeded') setPct(100);
      if (j.status === 'failed') setFailed(j.error?.message ?? '알 수 없는 오류');
    } else if (typeof j.progress === 'number') setPct((p) => Math.max(p, j.progress));
  }, [jobState.job]);
  useEffect(() => { if (s && !jobId) setRunning(false); }, [s, jobId]);

  // 데이터시트 잡
  useJob(dsJob?.job, {
    onDone: (j) => {
      setDsJob(null);
      void cache.refresh(id);
      if (j.status === 'failed') toast(j.error?.message ?? '데이터시트를 읽지 못했어요.');
    },
  });

  const picker = useFilePicker('.pdf,.png,.jpg,.jpeg,.xlsx,.docx', async (f) => {
    const chk = dsTarget.current;
    if (!chk || !s) return;
    try {
      const meta = await uploadFile(f, { confidential: true, purpose: 'sp.datasheet', projectId: s.project_id ?? undefined });
      const r = await addDatasheet(s.id, meta.id, chk.product_id);
      setDsJob({ job: r.job_id, check: chk.id });
    } catch (e) { toast(errText(e)); }
  });

  const open = useMemo(() => (s?.checks.items ?? []).filter((c) => c.status === 'open'), [s]);
  const done = !running && !failed;
  const nOpen = open.length;

  // 눌린 칩 기본값(미리 고른 답)
  const chosen = (c: ValueCheck) => answers[c.id]?.option_key ?? c.answer?.option_key ?? c.options?.find((o) => o.preselected)?.key;

  const pickOption = async (c: ValueCheck, key: string) => {
    setAnswers((a) => ({ ...a, [c.id]: { option_key: key } }));
    try { await answerCheck(id, c.id, { option_key: key }); } catch (e) { if (!isApiError(e, 'CHECK_CLOSED')) toast(errText(e)); }
  };
  const pickAlt = async (c: ValueCheck, label: string) => {
    setAnswers((a) => ({ ...a, [c.id]: { alt_measure: label } }));
    setErrs((x) => ({ ...x, [c.id]: '' }));
    try { await answerCheck(id, c.id, { alt_measure: label }); } catch (e) { toast(errText(e)); }
  };
  const typeValue = (c: ValueCheck, v: string) => {
    setAnswers((a) => ({ ...a, [c.id]: { value_text: v } }));
    setErrs((x) => ({ ...x, [c.id]: '' }));
  };
  const commitValue = async (c: ValueCheck) => {
    const v = answers[c.id]?.value_text?.trim();
    if (!v) return true;
    try {
      await answerCheck(id, c.id, { value_text: v });
      return true;
    } catch (e) {
      if (isApiError(e, 'INVALID_VALUE')) {
        const unit = (e.details as { expected_unit?: string } | undefined)?.expected_unit ?? c.unit ?? '';
        setErrs((x) => ({ ...x, [c.id]: e.message || `${unit} 단위로 넣어 주세요.` }));
        return false;
      }
      toast(errText(e));
      return false;
    }
  };

  const deferEverything = async () => {
    try {
      const r = await deferAll(id);
      cache.put(r.sheet);
      setAnswers({});
    } catch (e) { toast(errText(e)); }
  };

  const applyAndFinish = async () => {
    if (!s) return;
    setApplying(true);
    try {
      for (const c of open) {
        if (answers[c.id]?.value_text && !(await commitValue(c))) { setApplying(false); return; }
      }
      const list = Object.entries(answers).filter(([cid]) => open.some((c) => c.id === cid)).map(([check_id, a]) => ({ check_id, ...a }));
      const r = await applyChecks(id, list);
      cache.put(r.sheet);
      if (r.pending_until_job_done) { setWaitingApply(true); return; }
      nav(r.next_route, { replace: true });
    } catch (e) {
      if (isApiError(e, 'INVALID_VALUE')) {
        const d = e.details as { check_id?: string } | undefined;
        if (d?.check_id) setErrs((x) => ({ ...x, [d.check_id!]: e.message }));
      } else toast(errText(e));
    } finally { setApplying(false); }
  };

  const stop = async () => {
    if (!jobId) { nav(`/spec/${id}/items`); return; }
    try { await cancelJob(jobId); } catch { /* 잡이 이미 끝났으면 무시 */ }
    await cache.refresh(id);
    nav(`/spec/${id}/items`, { replace: true });
  };

  const memo = async (text: string) => {
    try {
      const r = await sendMessage(id, text, 'generating');
      if (r.memo) toast('요청을 받았어요. 시트 구성 전에 반영할게요.');
      else if (r.job_id) { toast('요청을 반영하고 있어요.'); setSp({ job: r.job_id }, { replace: true }); setRunning(true); }
    } catch (e) { toast(errText(e)); }
  };

  const retry = async () => {
    try {
      const r = await generate(id, { mode: 'full' });
      setFailed(null);
      setSteps({});
      setPct(0);
      setRunning(true);
      setSp({ job: r.job_id }, { replace: true });
    } catch (e) { toast(errText(e)); }
  };

  if (sheetQ.isError) return <SpPage><Agent text={`작업을 불러오지 못했어요. ${errText(sheetQ.error)}`} /></SpPage>;
  if (!s) return <SpPage><div className="sp-note">불러오는 중…</div></SpPage>;

  const wn = waitNotes(s);
  const stepRows = STAGES.map(([key, name]) => {
    const st = steps[key] ?? (done ? { status: 'done' as const, note: wn[key] } : { status: 'wait' as const, note: wn[key] });
    return { key, name, ...st };
  });
  const title = failed ? '시트를 만들지 못했어요' : done ? (nOpen ? `시트 생성 완료 · 값 확인 필요 ${nOpen}` : '시트 생성 완료') : '시트 생성 중';
  const table = s.table;
  const cols = s.products;
  const checkedItems = s.items.filter((i) => i.checked);

  return (
    <SpPage
      dock={
        <Dock title="Spec 시트" meta={`3 / 3 · ${running ? '생성 중' : '값 확인'}`}
          right={<span className="sp-note" style={{ fontSize: 12 }}>다른 작업을 해도 돼요. 끝나면 알려드릴게요</span>}
          row={
            <>
              <PromptInput label="진행 중 요청" placeholder="진행 중에도 요청하세요 (예: 소비전력은 연간 전기료로도 보여줘)" onSend={memo} />
              <button type="button" className="sp-btn2 sp-btn2--icon" onClick={() => void stop()} disabled={!running}>
                <svg width="12" height="12" viewBox="0 0 24 24" aria-hidden="true"><rect x="6" y="6" width="12" height="12" rx="2" fill="currentColor" /></svg>중지
              </button>
              <BigButton onClick={() => void applyAndFinish()} busy={applying || waitingApply} disabled={!!failed}>답 반영하고 완성</BigButton>
            </>
          }
        />
      }>
      {picker.input}
      {s.agent?.sp3g_user && <UserBubble>{s.agent.sp3g_user}</UserBubble>}
      <Agent text={s.agent?.sp3g ?? ''}>
        <div className="sp-gcard" data-testid="sp-progress" aria-live="polite">
          <div className="sp-gcard__head">
            <div className="sp-gcard__top">
              <div className="sp-gcard__title">
                {running ? <Spin /> : failed ? null : <span className="sp-gstep__done"><PathIcon d="M5 12l5 5L20 7" size={9} strokeWidth={3.4} /></span>}
                <b data-testid="sp-progress-title">{title}</b>
                <span className="sp-gcard__sub">{s.agent?.sp3g_sub}</span>
              </div>
              <span className="sp-gcard__pct"><span className="sp-numf">{pct}%</span>{running && eta !== null && eta > 0 ? ` · 약 ${eta}초 남음` : ''}</span>
            </div>
            <div className="sp-gbar"><div style={{ width: `${pct}%` }} /></div>
          </div>
          {failed ? (
            <div className="sp-gfail" role="alert">
              시트를 만들지 못했어요. {failed} · <button type="button" className="sp-link" onClick={() => void retry()}>다시 시도</button>
            </div>
          ) : (
            <div className="sp-gcard__body">
              <div className="sp-gsteps">
                {stepRows.map((r) => (
                  <div key={r.key} className={cx('sp-gstep', `sp-gstep--${r.status}`)} data-step={r.key} data-status={r.status}>
                    <StepIcon st={r.status} />
                    <div className="sp-gstep__text">
                      <span className="sp-gstep__name">{r.name}</span>
                      <span className="sp-gstep__note">{r.note}</span>
                    </div>
                  </div>
                ))}
              </div>
              <div className="sp-gprev">
                <div className="sp-gprev__head"><span>미리보기 · 채워지는 중</span><span>점선 칸 = 아래에서 확인</span></div>
                <div className="sp-gprev__row sp-gprev__row--head">
                  <span className="sp-gprev__k">항목</span>
                  {cols.map((p) => <span key={p.id} className="sp-gprev__v">{p.column_label || p.display_name}</span>)}
                </div>
                {table
                  ? table.rows.filter((r) => !r.hidden).map((r) => (
                    <div key={r.id} className="sp-gprev__row">
                      <span className="sp-gprev__k" title={r.label}>{r.label}</span>
                      {(r.cells ?? []).map((c) => {
                        const flag = !!c.check_n || c.state === 'flag';
                        const chk = c.state === 'checking';
                        return (
                          <span key={c.product_id} className="sp-gprev__v">
                            <span className={cx('sp-gcell', flag && 'sp-gcell--flag', chk && 'sp-gcell--chk')} data-state={c.state}>
                              {flag && c.check_n ? <span className="sp-gcell__n">{c.check_n}</span> : null}
                              <span className="sp-gcell__t">{c.state === 'flag' ? (c.flag_text ?? '값 없음') : (c.text || '…')}</span>
                            </span>
                          </span>
                        );
                      })}
                    </div>
                  ))
                  : checkedItems.map((i) => (
                    <div key={i.key} className="sp-gprev__row">
                      <span className="sp-gprev__k">{i.label}</span>
                      {cols.map((p) => <span key={p.id} className="sp-gprev__v"><span className="sp-gcell sp-gcell--chk">…</span></span>)}
                    </div>
                  ))}
              </div>
            </div>
          )}
        </div>

        {nOpen > 0 && (
          <div className="sp-qcard" data-testid="sp-checks">
            <div className="sp-qcard__head">
              <div className="sp-qcard__title">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--wm-brand)" strokeWidth="2.2" strokeLinecap="round" aria-hidden="true">
                  <circle cx="12" cy="12" r="9" /><path d="M12 7.5v5.5M12 16.5v.01" />
                </svg>
                <b>값 확인 필요 <span className="sp-numf sp-brand">{nOpen}</span></b>
                <span className="sp-qcard__sub">답하지 않은 칸은 [확정 필요]로 표시하고 계속 만들어요</span>
              </div>
              <button type="button" className="sp-link" onClick={() => void deferEverything()}>모두 [확정 필요]로 두기</button>
            </div>
            {open.map((c) => {
              const inputId = `sp-chk-${c.id}`;
              const err = errs[c.id];
              const reading = dsJob?.check === c.id;
              return (
                <div key={c.id} className="sp-q" data-testid="sp-check" data-kind={c.kind}>
                  <div className="sp-q__line">
                    <span className="sp-q__n">{c.n}</span>
                    <div className="sp-q__text">
                      <span className="sp-q__title">{c.title}</span>
                      <span className="sp-q__body" title={c.body}>{c.body}</span>
                    </div>
                    {c.kind === 'conflict' ? (
                      <>
                        {(c.options ?? []).map((o) => (
                          <button key={o.key} type="button" className="sp-chip sp-chip--f" aria-pressed={chosen(c) === o.key} onClick={() => void pickOption(c, o.key)}>
                            {o.label}
                          </button>
                        ))}
                        <button type="button" className="sp-link sp-q__link" onClick={() => setSrc(c)}>출처 보기</button>
                      </>
                    ) : (
                      <>
                        {c.kind !== 'missing_product' && (
                          <>
                            <label htmlFor={inputId} className="wm-sr-only">{c.input_label ?? '값 입력'}</label>
                            <div className={cx('sp-q__input', err && 'sp-q__input--bad')}>
                              <input id={inputId} placeholder={c.placeholder ?? '값 입력'} value={answers[c.id]?.value_text ?? c.answer?.value_text ?? ''}
                                onChange={(e) => typeValue(c, e.target.value)} onBlur={() => void commitValue(c)}
                                onKeyDown={(e) => { if (e.key === 'Enter' && !e.nativeEvent.isComposing) void commitValue(c); }}
                                aria-invalid={!!err || undefined} aria-describedby={err ? `${inputId}-err` : undefined} />
                            </div>
                          </>
                        )}
                        <button type="button" className="sp-minibtn sp-minibtn--32" onClick={() => { dsTarget.current = c; picker.open(); }} disabled={reading}>
                          <PathIcon d="M12 16V4M6 10l6-6 6 6M4 20h16" size={12} strokeWidth={2.2} />데이터시트 올리기
                        </button>
                      </>
                    )}
                  </div>
                  {(c.alt_measures ?? []).length > 0 && (
                    <div className="sp-q__alts">
                      {(c.alt_measures ?? []).map((m) => (
                        <button key={m.label} type="button" className="sp-chip sp-chip--h28" aria-pressed={answers[c.id]?.alt_measure === m.label}
                          onClick={() => void pickAlt(c, m.label)}>{m.label} · {m.value_text}</button>
                      ))}
                    </div>
                  )}
                  {reading && <div className="sp-q__note" role="status">데이터시트를 읽고 있어요</div>}
                  {err && <div className="sp-q__err" id={`${inputId}-err`} role="alert">{err}</div>}
                </div>
              );
            })}
          </div>
        )}
        {waitingApply && <div className="sp-note" role="status">답을 받아 두었어요. 시트가 다 만들어지면 반영하고 넘어갈게요.</div>}
      </Agent>
      <SourcesModal sheetId={id} rowId={src?.row_id} productId={src?.product_id} title={src ? `${src.title} · 출처` : ''} onClose={() => setSrc(null)} />
    </SpPage>
  );
}
