/**
 * VP1Q — 되묻기(`/vp/:id/questions`): 방향(선택 필요) · 결재자(확인 권장) · 업종 · Storyboard ↔ MI 충돌 + 자동으로 정한 것.
 */
import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router';
import { Icon, Skeleton } from '@/ui';
import { answerQuestions, errText, getVp, postMessage, useRefresh, useVp, type Question } from '../api';
import { Agent, BtnLink, Btn, Dock, ModeChip, Page, UserBubble, VThumb, useJobDone, useVpShell, Spinner } from '../parts';

export function QuestionsPage() {
  const { id = '' } = useParams();
  const nav = useNavigate();
  const vp = useVp(id);
  const doc = vp.data;
  useVpShell(doc, 2);
  const refresh = useRefresh(id);
  const open = useMemo(() => (doc?.questions ?? []).filter((q) => q.status === 'open'), [doc]);
  const [sel, setSel] = useState<Record<string, string[]>>({});
  const [busy, setBusy] = useState('');
  const [err, setErr] = useState('');
  const [job, setJob] = useState<string | null>(null);
  const [resumed, setResumed] = useState<string | null>(null);

  const server = useRef<Record<string, string>>({});
  useEffect(() => {
    setSel((cur) => {
      const next = { ...cur };
      for (const q of open) {
        const sv = (q.selected_keys?.length ? q.selected_keys : q.default_keys) ?? [];
        if (!next[q.id] || server.current[q.id] !== sv.join()) next[q.id] = sv;
        server.current[q.id] = sv.join();
      }
      return next;
    });
  }, [open]);

  useJobDone(job, async () => { setJob(null); await refresh(); });
  const rj = useJobDone(resumed, async (snap) => {
    const fresh = await getVp(id);
    await refresh();
    nav(snap.status === 'succeeded' ? ((snap.result?.next_route as string) || fresh.resume_route) : fresh.resume_route);
  });

  if (!doc || (!open.length && vp.isFetching && !resumed)) return <Page><Skeleton h={320} /></Page>;
  if (!open.length && !resumed) {
    return <Page><Agent text="지금은 물어볼 것이 없어요."><div><BtnLink to={doc.resume_route && !doc.resume_route.endsWith('/questions') ? doc.resume_route : `/vp/${id}/structure`} primary>이어서 하기</BtnLink></div></Agent></Page>;
  }
  const nAsk = open.filter((q) => q.mode === 'ask').length;
  const nCheck = open.filter((q) => q.mode === 'check').length;

  const pick = (q: Question, key: string) => setSel((s) => {
    const cur = s[q.id] ?? [];
    if (!q.multi) return { ...s, [q.id]: [key] };
    return { ...s, [q.id]: cur.includes(key) ? cur.filter((k) => k !== key) : [...cur, key] };
  });
  const go = async () => {
    setBusy('go');
    setErr('');
    try {
      const r = await answerQuestions(id, open.map((q) => ({ question_id: q.id, keys: sel[q.id] ?? q.default_keys })), true);
      await refresh();
      if (r.resumed_job_id) setResumed(r.resumed_job_id);
      else nav(r.next_route || `/vp/${id}/structure`);
    } catch (e) { setErr(errText(e)); setBusy(''); }
  };
  const send = async (text: string) => {
    try { const r = await postMessage(id, { text, context: 'questions' }); setJob(r.job_id); } catch (e) { setErr(errText(e)); }
  };

  return (
    <Page dock={
      <Dock title="되묻기" meta={`선택 필요 ${nAsk} · 확인 권장 ${nCheck}`} headRight={<Link to="/vp/rules" state={{ back: `/vp/${id}/questions` }} style={{ fontSize: 12.5, fontWeight: 600 }}>언제 묻는지 보기</Link>}
        input={{ placeholder: '직접 답하기 (예: 매출이 먼저, 결재는 대표와 재무 둘)', label: '직접 답하기', onSend: send, busy: !!job }}
        actions={<>
          {err && <span className="vp-err">{err}</span>}
          <BtnLink to={`/vp/${id}/materials`}>이전</BtnLink>
          {resumed ? <Spinner label={`이어서 정리하는 중 · ${rj.progress}%`} /> : <Btn primary onClick={go} busy={busy === 'go'}>이대로 진행</Btn>}
        </>} />
    }>
      <UserBubble head={doc.customer_name || doc.title} rest={doc.labels?.questions} />
      <Agent text={doc.intros?.questions}>
        {open.map((q) => <QuestionCard key={q.id} q={q} sel={sel[q.id] ?? []} onPick={(k) => pick(q, k)} />)}
        {doc.intros?.questions_default && (
          <div className="vp-defaults"><Icon name="clock" size={14} /><span>{doc.intros.questions_default}</span></div>
        )}
        {!!doc.auto_chips?.length && (
          <div className="vp-autos" aria-label="자동으로 정한 것">
            <span className="vp-autos__k">자동으로 정한 것</span>
            {doc.auto_chips.map((c) => <span key={c} className="vp-autos__chip"><Icon name="bolt" size={11} />{c}</span>)}
          </div>
        )}
      </Agent>
    </Page>
  );
}

function QuestionCard({ q, sel, onPick }: { q: Question; sel: string[]; onPick: (k: string) => void }) {
  const isDirection = q.kind === 'direction';
  const multi = !!q.multi;
  return (
    <div className={q.mode === 'ask' ? 'vp-card vp-card--ask' : 'vp-card'} data-testid={`vp-q-${q.kind}`} role="group" aria-label={q.title}>
      <div className="vp-card__head vp-card__head--plain">
        <ModeChip mode={q.mode} />
        <span style={{ fontSize: 13.5, fontWeight: 700, whiteSpace: 'nowrap' }}>{q.title}</span>
        <span className="vp-grow" />
        <span className="vp-card__sub">{q.aside}</span>
      </div>
      {q.context_text && <div className="vp-q__ctx" title={q.context_text}>{q.context_text}</div>}
      {isDirection ? (
        <div className="vp-q__opts" role="radiogroup" aria-label={q.title}>
          {(q.options ?? []).map((o) => {
            const on = sel.includes(o.key);
            return (
              <label key={o.key} className={on ? 'vp-opt vp-opt--on' : 'vp-opt'}>
                <span style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 }}>
                  <input type="radio" name={q.id} checked={on} onChange={() => onPick(o.key)} />
                  <span className="vp-opt__t">{o.label}</span>
                  {o.recommended && <span className="vp-opt__rec">추천</span>}
                </span>
                <span className="vp-opt__d">{o.desc}</span>
                {o.preview && (
                  <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ width: 120, height: 68, flexShrink: 0 }}><VThumb kind={o.preview.thumb.kind} n={o.preview.thumb.n} /></span>
                    <span style={{ display: 'flex', flexDirection: 'column', gap: 2, minWidth: 0 }}>
                      <span className="vp-opt__code">{o.preview.display}</span>
                      <span className="vp-opt__so">{o.preview.effect}</span>
                    </span>
                  </span>
                )}
              </label>
            );
          })}
        </div>
      ) : (
        <div className="vp-q__chips" role={multi ? 'group' : 'radiogroup'} aria-label={q.title}>
          {(q.options ?? []).map((o) => {
            const on = sel.includes(o.key);
            return (
              <label key={o.key} className={on ? 'vp-pick vp-pick--on' : 'vp-pick'}>
                <input type={multi ? 'checkbox' : 'radio'} name={q.id} checked={on} onChange={() => onPick(o.key)} />{o.label}
                {o.recommended && !multi && <span className="vp-opt__rec">추천</span>}
              </label>
            );
          })}
          <span className="vp-grow" />
          {q.hint && (
            <span className={q.kind === 'approver' && sel.length >= 2 ? 'vp-q__hint vp-q__hint--strong' : 'vp-q__hint'}>
              {q.hint.split('VP-H').map((part, i, arr) => <span key={i}>{part}{i < arr.length - 1 && <b className="vp-num" style={{ color: 'var(--wm-brand)' }}>VP-H</b>}</span>)}
            </span>
          )}
        </div>
      )}
    </div>
  );
}
