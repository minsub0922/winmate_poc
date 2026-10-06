/**
 * 심층 작성 — RQ3 보강할 곳 `/requirements/:rqId/deep/:sid` · RQ3A/B 질의 `…/q` · RQ3C 결과 `…/result`.
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, Navigate, useNavigate, useParams } from 'react-router';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useShellPage } from '@/shell';
import { Button, Icon, Skeleton, toast } from '@/ui';
import { ApiError, errorText, rqApi, type DeepSession, type Gap, type Keyman, type LogEntry, type Proposal, type Requirement } from '../api';
import { Arrow, CheckMark, Completeness, KmAvatar, TopicChip, WeightBar } from '../components/bits';
import { rqKey, useAfterSave, useJobTicker, useRequirement } from '../hooks';
import { stepWeights } from '../lib/weights';
import { STEPS } from './FormPage';

export const sessionKey = (sid?: string) => ['rq-session', sid] as const;

function useSession(rqId?: string, sid?: string) {
  return useQuery({ queryKey: sessionKey(sid), enabled: !!rqId && !!sid, queryFn: () => rqApi.session(rqId!, sid!), staleTime: 1_000 });
}

function useDeepShell(rq?: Requirement) {
  useShellPage({ section: '고객 요구사항', title: rq?.title || '새 요구사항', hasTask: true, stepper: { steps: STEPS, current: 2 } });
}

// ── RQ3 보강할 곳 ───────────────────────────────────────

export function GapsPage() {
  const { rqId, sid } = useParams();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const rq = useRequirement(rqId);
  const sq = useSession(rqId, sid);
  const s = sq.data;
  useDeepShell(rq.data);
  const refetch = useCallback(() => { void qc.invalidateQueries({ queryKey: sessionKey(sid) }); }, [qc, sid]);
  useJobTicker(s?.status === 'analyzing' ? s.job_id : null, refetch, () => { refetch(); void qc.invalidateQueries({ queryKey: rqKey(rqId) }); });
  const [busy, setBusy] = useState(false);
  const afterSave = useAfterSave();
  const reanalyzed = useRef(false);
  // 고른 것은 서버 응답이 올 때까지 화면 값을 우선한다(늦게 온 다시 읽기가 체크를 되돌리지 않게)
  const [localSel, setLocalSel] = useState<string[] | null>(null);
  const pendingSel = useRef(0);

  // 폼이 크게 바뀐 ready 세션은 자동 재분석(§3.2)
  useEffect(() => {
    if (s?.status === 'ready' && s.stale && !reanalyzed.current && rqId && sid) {
      reanalyzed.current = true;
      void rqApi.reanalyze(rqId, sid).then(refetch).catch((e) => toast(errorText(e)));
    }
  }, [s?.status, s?.stale, rqId, sid, refetch]);

  if (!rqId || !sid) return null;
  if (s?.status === 'asking') return <Navigate to={`/requirements/${rqId}/deep/${sid}/q`} replace />;
  if (s?.status === 'finished') return <Navigate to={`/requirements/${rqId}/deep/${sid}/result`} replace />;
  if (s?.status === 'canceled') return <Navigate to={`/requirements/${rqId}/form`} replace />;

  const analyzing = !s || s.status === 'analyzing';
  const gaps = (s?.gaps ?? []).filter((g) => g.status !== 'resolved_by_form');
  const selected = new Set(localSel ?? s?.selected_gap_ids ?? []);

  const toggle = async (g: Gap) => {
    if (!s) return;
    const next = selected.has(g.id) ? [...selected].filter((x) => x !== g.id) : [...selected, g.id];
    setLocalSel(next);
    pendingSel.current += 1;
    try {
      const res = await rqApi.selectGaps(rqId, sid, next);
      pendingSel.current -= 1;
      qc.setQueryData(sessionKey(sid), res);
      if (pendingSel.current === 0) setLocalSel(null);
    } catch (e) {
      pendingSel.current -= 1;
      if (pendingSel.current === 0) setLocalSel(null);
      toast(errorText(e));
      refetch();
    }
  };

  const start = async () => {
    setBusy(true);
    try {
      const st = await rqApi.start(rqId, sid);
      qc.setQueryData(sessionKey(sid), st);
      void qc.invalidateQueries({ queryKey: rqKey(rqId) });
      navigate(`/requirements/${rqId}/deep/${sid}/q`);
    } catch (e) {
      toast(errorText(e));
    } finally {
      setBusy(false);
    }
  };

  const save = async () => {
    setBusy(true);
    try {
      await rqApi.finish(rqId, sid).catch(() => undefined);
      const res = await rqApi.save(rqId, 'deep');
      await afterSave(rqId, res);
      navigate(`/requirements/${rqId}/saved?v=${res.version}`);
    } catch (e) {
      toast(errorText(e));
    } finally {
      setBusy(false);
    }
  };

  const retry = async () => {
    try {
      const acc = await rqApi.startDeep(rqId);
      navigate(`/requirements/${rqId}/deep/${acc.ref.id}`, { replace: true });
    } catch (e) {
      if (e instanceof ApiError && e.code === 'SESSION_ACTIVE') navigate(`/requirements/${rqId}/deep/${String(e.details.session_id)}`, { replace: true });
      else toast(errorText(e));
    }
  };

  if (s?.status === 'failed') {
    return (
      <div className="rq-root"><div className="rq-center rq-center--stepper"><div className="rq-center__col">
        <div className="rq-eyebrow">심층 작성</div>
        <h1 className="rq-h1">보강할 곳을 찾지 못했어요</h1>
        <p className="wm-muted" style={{ margin: 0 }}>{s.error?.code === 'LLM_UNAVAILABLE' || s.error?.code === 'POLICY_CONFIDENTIAL' ? '지금은 AI를 쓸 수 없어요. 직접 입력은 계속할 수 있어요.' : s.error?.message}</p>
        <div className="rq-foot">
          <Link className="rq-backlink" to={`/requirements/${rqId}/form`}><Icon name="chevronLeft" size={14} />폼</Link>
          <span className="rq-grow" />
          <Button h={48} variant="primary" onClick={() => void retry()}>다시 시도</Button>
        </div>
      </div></div></div>
    );
  }

  return (
    <div className="rq-root">
      <div className="rq-center rq-center--stepper">
        <div className="rq-center__col">
          <div className="rq-headrow">
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              <span className="rq-eyebrow">심층 작성</span>
              <h1 className="rq-h1" aria-live="polite">
                {analyzing ? '보강할 곳을 찾는 중이에요' : gaps.length === 0 ? '보강할 곳이 없어요' : <>보강할 곳 <span className="wm-num">{gaps.length}</span></>}
              </h1>
            </div>
            <span className="rq-grow" />
            {!analyzing && s?.completeness != null && <Completeness value={s.completeness} />}
          </div>
          {analyzing ? (
            <div className="rq-rows" aria-busy="true">
              {Array.from({ length: 5 }, (_, i) => (
                <div key={i} className="rq-skelrow"><Skeleton w={18} h={18} r={4} /><Skeleton w={100} h={22} r={6} /><Skeleton w={`${40 + (i % 3) * 12}%`} h={14} /></div>
              ))}
            </div>
          ) : gaps.length > 0 && (
            <div className="rq-rows" data-testid="gap-list">
              {gaps.map((g) => (
                <label key={g.id} className="rq-row" data-gap={g.kind}>
                  <input type="checkbox" checked={selected.has(g.id)} onChange={() => void toggle(g)} aria-label={`${g.chip_label} · ${g.problem}`} />
                  <span className="rq-row__chipcol"><TopicChip gap={g} keymen={rq.data?.form.keymen} /></span>
                  <span className="rq-row__text">{g.problem}</span>
                </label>
              ))}
            </div>
          )}
          <div className="rq-foot">
            <Link className="rq-backlink" to={`/requirements/${rqId}/form`}><Icon name="chevronLeft" size={14} />폼</Link>
            <span className="rq-grow" />
            {!analyzing && gaps.length === 0 ? (
              <Button h={48} variant="primary" loading={busy} iconRight={<Icon name="arrowRight" size={15} />} onClick={() => void save()}>저장</Button>
            ) : (
              <Button h={48} variant="primary" style={{ padding: '0 22px', fontSize: 15, fontWeight: 700 }} loading={busy}
                disabled={analyzing || selected.size === 0} disabledReason={analyzing ? '보강할 곳을 찾는 중이에요' : '다룰 곳을 골라 주세요'}
                iconRight={<Icon name="arrowRight" size={15} />} onClick={() => void start()}>시작</Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ── RQ3A · RQ3B 질의 ───────────────────────────────────

export function AskPage() {
  const { rqId, sid } = useParams();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const rq = useRequirement(rqId);
  const sq = useSession(rqId, sid);
  const s = sq.data;
  useDeepShell(rq.data);
  const [text, setText] = useState('');
  const [sending, setSending] = useState(false);
  const [editing, setEditing] = useState<string | null>(null);
  const [sides, setSides] = useState<Record<string, boolean>>({});
  const [wedit, setWedit] = useState<number[] | null>(null);
  const bodyRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const proposal = s?.pending_proposal ?? null;

  useEffect(() => { bodyRef.current?.scrollTo({ top: bodyRef.current.scrollHeight }); }, [s?.log.length, proposal?.id, sending]);
  useEffect(() => { setSides({}); setEditing(null); }, [proposal?.id]);
  useEffect(() => { setWedit(null); }, [s?.current_gap_id]);

  if (!rqId || !sid) return null;
  if (s && s.status === 'ready') return <Navigate to={`/requirements/${rqId}/deep/${sid}`} replace />;
  if (s && s.status === 'finished') return <Navigate to={`/requirements/${rqId}/deep/${sid}/result`} replace />;
  if (s && s.status !== 'asking') return <Navigate to={`/requirements/${rqId}/form`} replace />;

  const gap = s?.gaps.find((g) => g.id === (proposal?.gap_id ?? s?.current_gap_id));
  const keymen = rq.data?.form.keymen ?? [];
  const total = s?.total ?? 0;
  const idx = Math.min(Math.max(s?.current_index ?? 1, 1), Math.max(total, 1));

  const after = async (fn: () => Promise<{ session: DeepSession }>, restore?: string) => {
    setSending(true);
    try {
      const res = await fn();
      qc.setQueryData(sessionKey(sid), res.session);
      void qc.invalidateQueries({ queryKey: rqKey(rqId) });
      if (res.session.status === 'finished') navigate(`/requirements/${rqId}/deep/${sid}/result`);
    } catch (e) {
      toast(errorText(e));
      if (restore) setText(restore);
      if (e instanceof ApiError && e.status === 409) void qc.invalidateQueries({ queryKey: sessionKey(sid) });
    } finally {
      setSending(false);
      inputRef.current?.focus();
    }
  };

  const send = () => {
    const t = text.trim();
    if (!t || !s || sending) return;
    setText('');
    if (proposal) void after(() => rqApi.revise(rqId, sid, proposal.id, t), t);
    else if (gap) void after(() => rqApi.answer(rqId, sid, { gap_id: gap.id, kind: 'text', text: t }), t);
  };
  const pick = (optionId: string) => { if (gap && !sending) void after(() => rqApi.answer(rqId, sid, { gap_id: gap.id, kind: 'option', option_id: optionId })); };
  const unknown = () => { if (gap && !sending) void after(() => rqApi.answer(rqId, sid, { gap_id: gap.id, kind: 'unknown' })); };
  const skip = () => { if (gap && !sending) void after(() => rqApi.answer(rqId, sid, { gap_id: gap.id, kind: 'skip' })); };
  const finish = () => void after(async () => ({ session: await rqApi.finish(rqId, sid) }));
  const accept = (edited?: string) => {
    if (!proposal) return;
    const se = proposal.side_effects.map((x) => ({ id: x.id, checked: sides[x.id] ?? x.checked }));
    void after(() => rqApi.accept(rqId, sid, proposal.id, { edited_text: edited, side_effects: se }));
  };
  const applyWeights = () => {
    if (!gap || !wedit) return;
    void after(() => rqApi.answer(rqId, sid, { gap_id: gap.id, kind: 'weights', weights: Object.fromEntries(keymen.map((k, i) => [k.id, wedit[i]])) }));
  };

  const isWeights = gap?.question.answer_type === 'weights';
  return (
    <div className="rq-root">
      <div className="rq-ask">
        <section className="rq-chat" aria-label="질의">
          <div className="rq-chat__head">
            <div className="rq-segs" role="progressbar" aria-valuemin={0} aria-valuemax={total} aria-valuenow={idx} aria-label="질의 진행">
              {Array.from({ length: total }, (_, i) => <span key={i} className={i < idx ? 'on' : ''} />)}
            </div>
            <span className="rq-chat__count" data-testid="ask-progress">{idx} / {total}</span>
            {gap && <TopicChip gap={gap} keymen={keymen} />}
            <span className="rq-grow" />
            <button type="button" className="rq-textlink" onClick={finish} disabled={sending}>끝내기</button>
          </div>
          <div ref={bodyRef} className={`rq-chat__body ${proposal ? 'rq-chat__body--end' : ''}`}>
            {(s?.log ?? []).map((e, i) => <LogLine key={`${e.gap_id}-${i}`} e={e} />)}
            {gap && (
              <div className="rq-bubble-row">
                <span className="rq-wav" aria-hidden="true">W</span>
                <div className="rq-bubble" data-testid="question">{gap.question.text}</div>
              </div>
            )}
            {gap && !proposal && !sending && !isWeights && gap.question.options.length > 0 && (
              <div className="rq-opts" role="group" aria-label="선택지">
                {gap.question.options.slice(0, 4).map((o) => (
                  <button key={o.id} type="button" className="rq-opt" onClick={() => pick(o.id)}>{o.label}</button>
                ))}
              </div>
            )}
            {gap && isWeights && !sending && (
              <WeightsChoice gap={gap} keymen={keymen} values={wedit} onValues={setWedit} onPick={pick} onApply={applyWeights} />
            )}
            {proposal?.answer_text && <div className="rq-userbubble">{proposal.answer_text}</div>}
            {proposal && !sending && (
              <ProposalCard p={proposal} editing={editing} setEditing={setEditing} sides={sides} setSides={setSides} onAccept={accept} />
            )}
            {sending && <div className="rq-bubble-row"><span className="rq-wav" aria-hidden="true">W</span><span className="rq-typing" aria-label="답을 정리하는 중"><i /><i /><i /></span></div>}
          </div>
          <div className="rq-chat__input">
            <div className="rq-chat__inputrow">
              <label className="wm-sr-only" htmlFor="rq-answer">답변</label>
              <input id="rq-answer" ref={inputRef} className="rq-input" placeholder={proposal ? '고칠 점을 적어 주세요' : '직접 입력'} value={text} disabled={sending}
                onChange={(e) => setText(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter' && !e.nativeEvent.isComposing) { e.preventDefault(); send(); } }} />
              <button type="button" className="rq-send" aria-label="보내기" disabled={sending || !text.trim()} onClick={send}><Icon name="arrowUp" size={18} strokeWidth={2.4} /></button>
            </div>
            <div className="rq-chat__links">
              <button type="button" className="rq-textlink" disabled={sending || !!proposal} onClick={unknown}>모름 · 고객에게 확인</button>
              <button type="button" className="rq-textlink" disabled={sending || !!proposal} onClick={skip}>건너뛰기</button>
            </div>
          </div>
        </section>
        <FormPanel rqId={rqId} rq={rq.data} s={s} gap={gap} proposal={proposal} />
      </div>
    </div>
  );
}

function LogLine({ e }: { e: LogEntry }) {
  if (e.kind === 'deferred') {
    return <div className="rq-logline" data-log="deferred"><span className="rq-topic" style={{ height: 20 }}>고객 확인</span><span>{e.value_display}</span></div>;
  }
  if (e.kind === 'skipped') return <div className="rq-logline" data-log="skipped"><span>건너뜀 · {e.value_display}</span></div>;
  return (
    <div className="rq-logline" data-log={e.kind}>
      <CheckMark size={13} /><b>{e.label}</b><span>→ {e.value_display}</span>
    </div>
  );
}

function WeightsChoice({ gap, keymen, values, onValues, onPick, onApply }: {
  gap: Gap; keymen: Keyman[]; values: number[] | null; onValues: (v: number[] | null) => void; onPick: (id: string) => void; onApply: () => void;
}) {
  const cur = values ?? keymen.map((k) => k.weight ?? 0);
  return (
    <>
      <div className="rq-opts" role="group" aria-label="선택지">
        {gap.question.options.slice(0, 4).map((o) => <button key={o.id} type="button" className="rq-opt" onClick={() => onPick(o.id)}>{o.label}</button>)}
        <button type="button" className="rq-opt" style={{ color: 'var(--wm-text-muted)' }} onClick={() => onValues(values ? null : cur)}>직접 조정</button>
      </div>
      {values && (
        <div className="rq-weditor" style={{ marginLeft: 40 }}>
          {keymen.map((k, i) => (
            <div key={k.id} className="rq-weditor__row">
              <KmAvatar name={k.name} colorIndex={k.color_index} size={20} />
              <span style={{ flex: 1 }}>{k.name}</span>
              <span className="rq-stepper">
                <button type="button" aria-label={`${k.name} 가중치 낮추기`} onClick={() => onValues(stepWeights(cur, i, -1))}>−</button>
                <span>{cur[i]}%</span>
                <button type="button" aria-label={`${k.name} 가중치 높이기`} onClick={() => onValues(stepWeights(cur, i, 1))}>+</button>
              </span>
            </div>
          ))}
          <div style={{ display: 'flex', justifyContent: 'flex-end' }}><Button h={34} variant="primary" onClick={onApply}>반영</Button></div>
        </div>
      )}
    </>
  );
}

function ProposalCard({ p, editing, setEditing, sides, setSides, onAccept }: {
  p: Proposal; editing: string | null; setEditing: (v: string | null) => void; sides: Record<string, boolean>;
  setSides: (f: (s: Record<string, boolean>) => Record<string, boolean>) => void; onAccept: (edited?: string) => void;
}) {
  return (
    <div className="rq-bubble-row">
      <span className="rq-wav" aria-hidden="true">W</span>
      <div className="rq-proposal" data-testid="proposal">
        <div className="rq-proposal__title">이렇게 바꿀까요?</div>
        {p.before_text ? <div className="rq-proposal__before">{p.before_text}</div> : <span><span className="rq-add">추가</span></span>}
        {editing !== null ? (
          <textarea className="rq-textarea" style={{ minHeight: 70 }} aria-label="고친 문장" value={editing} maxLength={200} autoFocus onChange={(e) => setEditing(e.target.value)} />
        ) : (
          <div className="rq-proposal__after">{p.after_text}</div>
        )}
        {p.side_effects.map((se) => (
          <label key={se.id} className="rq-proposal__side">
            <input type="checkbox" checked={sides[se.id] ?? se.checked} onChange={(e) => setSides((x) => ({ ...x, [se.id]: e.target.checked }))} />
            고객 확인에 &apos;{se.label}&apos; 추가
          </label>
        ))}
        <div style={{ display: 'flex', gap: 8 }}>
          <Button h={38} variant="primary" style={{ padding: '0 18px' }} disabled={editing !== null && !editing.trim()}
            onClick={() => onAccept(editing !== null ? editing.trim() : undefined)}>반영</Button>
          {editing === null
            ? <Button h={38} onClick={() => setEditing(p.after_text)}>고치기</Button>
            : <Button h={38} onClick={() => setEditing(null)}>취소</Button>}
        </div>
      </div>
    </div>
  );
}

function FormPanel({ rqId, rq, s, gap, proposal }: { rqId: string; rq?: Requirement; s?: DeepSession; gap?: Gap; proposal: Proposal | null }) {
  const f = rq?.form;
  const applied = new Set((s?.log ?? []).filter((e) => e.kind === 'applied' || e.kind === 'resolved').map((e) => e.label));
  const t = gap?.target;
  const cur = (k: string) => (t?.kind === 'field' && t.field === k) || (t?.kind === 'weights' && k === 'weights');
  const fld = (k: 'project_name' | 'customer_name' | 'final_audience' | 'author_note', label: string) => (
    <div className={`rq-panel__fld ${cur(k) ? 'rq-panel__fld--cur' : ''}`} data-field={k}>
      <div className="rq-panel__lab">{label}</div>
      <div className="rq-panel__val">
        {f?.[k]?.value ? <span className="wm-ellipsis">{f[k].value}</span> : <span className="rq-panel__empty">—</span>}
        {applied.has(label) && f?.[k]?.value && <CheckMark size={13} />}
      </div>
    </div>
  );
  const ks = f?.keymen ?? [];
  const targetKm = proposal?.keyman_id ?? (t?.kind === 'keyman' || t?.kind === 'item' ? (t.keyman_id ?? gap?.chip_keyman_id) : null);
  // 방금 반영한 항목의 키맨은 펼쳐 둔다(반영 결과가 보이게)
  const lastLog = s?.log.length ? s.log[s.log.length - 1] : null;
  const lastKm = lastLog?.kind === 'applied' ? s?.gaps.find((g) => g.id === lastLog.gap_id)?.change?.keyman_id ?? null : null;
  const changedText = lastLog?.kind === 'applied' ? s?.gaps.find((g) => g.id === lastLog.gap_id)?.change?.after_display : null;
  return (
    <aside className="rq-panel" aria-label="폼">
      <div className="rq-panel__head"><span>폼</span><Link to={`/requirements/${rqId}/form`} style={{ fontSize: 13, fontWeight: 600 }}>열기</Link></div>
      {fld('project_name', '프로젝트명')}
      {fld('customer_name', '고객사')}
      {fld('final_audience', '최종 제안대상')}
      {ks.length >= 2 && (
        <div className={`rq-panel__fld ${cur('weights') ? 'rq-panel__fld--cur' : ''}`} data-field="weights">
          <div className="rq-panel__lab">가중치{applied.has('가중치') && <CheckMark size={12} />}</div>
          <div style={{ marginTop: 6 }}><WeightBar keymen={ks} size="sm" showPercent={false} /></div>
        </div>
      )}
      {ks.map((k) => {
        const open = (targetKm === k.id && !!proposal) || (!proposal && lastKm === k.id);
        const focus = targetKm === k.id;
        return (
          <div key={k.id} className={focus && !proposal ? 'rq-panel__fld rq-panel__fld--cur' : ''} style={focus && !proposal ? { padding: 0 } : undefined}>
            <div className="rq-panel__km">
              <KmAvatar name={k.name} colorIndex={k.color_index} size={20} />
              <span className="wm-ellipsis">{k.name}</span>
              <small>{ks.length >= 2 ? `${k.weight ?? 0}%${open ? '' : ` · ${k.items.length}`}` : k.items.length}</small>
            </div>
            {open && (
              <div className="rq-panel__items" data-testid="panel-items">
                {k.items.map((it) => proposal && it.id === proposal.target.item_id && proposal.kind === 'replace_item' ? (
                  <div key={it.id} className="rq-panel__change"><s>{it.text}</s><b>{proposal.after_text}</b></div>
                ) : (
                  <span key={it.id} className="wm-ellipsis" title={it.text}
                    style={!proposal && it.text === changedText ? { color: 'var(--wm-brand)', fontWeight: 600 } : undefined}>{it.text}</span>
                ))}
                {proposal?.kind === 'add_item' && <div className="rq-panel__change"><span className="rq-add" style={{ alignSelf: 'flex-start' }}>추가</span><b>{proposal.after_text}</b></div>}
              </div>
            )}
          </div>
        );
      })}
      {fld('author_note', '제작자 의견')}
    </aside>
  );
}

// ── RQ3C 결과 ───────────────────────────────────────────

export function ResultPage() {
  const { rqId, sid } = useParams();
  const navigate = useNavigate();
  const rq = useRequirement(rqId);
  const sq = useSession(rqId, sid);
  const s = sq.data;
  useDeepShell(rq.data);
  const [busy, setBusy] = useState(false);
  const afterSave = useAfterSave();
  if (!rqId || !sid) return null;
  if (s && s.status !== 'finished') return <Navigate to={`/requirements/${rqId}/deep/${sid}${s.status === 'asking' ? '/q' : ''}`} replace />;
  const res = s?.result;
  const qs = res?.customer_questions ?? [];
  const save = async () => {
    setBusy(true);
    try {
      const r = await rqApi.save(rqId, 'deep');
      await afterSave(rqId, r);
      navigate(`/requirements/${rqId}/saved?v=${r.version}`);
    } catch (e) {
      toast(errorText(e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="rq-root">
      <div className="rq-center rq-center--stepper">
        <div className="rq-center__col">
          <div className="rq-headrow">
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              <span className="rq-eyebrow">심층 작성</span>
              <h1 className="rq-h1"><span className="wm-num">{res?.reinforced_count ?? 0}</span>곳 보강했어요</h1>
            </div>
            <span className="rq-grow" />
            {s?.completeness_after != null && <Completeness value={s.completeness_after} before={s.completeness_before} />}
          </div>
          {(res?.changes.length ?? 0) > 0 && (
            <div className="rq-rows" data-testid="result-changes">
              {res!.changes.map((ch, i) => (
                <div key={i} className="rq-row" style={{ minHeight: 56 }}>
                  <CheckMark />
                  <span className="rq-row__label">{ch.label}</span>
                  {ch.is_addition ? <span className="rq-add">추가</span> : (
                    <><span className="rq-before" style={{ textDecoration: ch.before_display ? 'line-through' : 'none' }}>{ch.before_display || '—'}</span><Arrow /></>
                  )}
                  <span className="rq-after" title={ch.after_display}>{ch.after_short || ch.after_display}</span>
                </div>
              ))}
            </div>
          )}
          {qs.length > 0 && (
            <Link to={`/requirements/${rqId}/questions`} className="rq-dashcard" data-testid="customer-check">
              <span style={{ fontSize: 15, fontWeight: 700 }}>고객 확인 <span className="wm-num" style={{ color: 'var(--wm-brand)' }}>{qs.length}</span></span>
              <span className="wm-ellipsis" style={{ fontSize: 13, color: 'var(--wm-text-muted)', flex: 1 }}>{qs.map((q) => q.short_label || q.text).join(' · ')}</span>
              <Icon name="chevronRight" size={14} color="var(--wm-text-subtle)" />
            </Link>
          )}
          <div className="rq-foot">
            <Link className="rq-backlink" to={`/requirements/${rqId}/form`}><Icon name="chevronLeft" size={14} />폼에서 보기</Link>
            <span className="rq-grow" />
            <Button h={48} variant="primary" style={{ padding: '0 22px', fontSize: 15, fontWeight: 700 }} loading={busy}
              iconRight={<Icon name="arrowRight" size={15} />} onClick={() => void save()}>저장</Button>
          </div>
        </div>
      </div>
    </div>
  );
}
