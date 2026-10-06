/**
 * VP2 — 가치 구조(`/vp/:id/structure`): 메시지 구조 · 시트 척추 · 그 밖에 정한 것 7 · 대안 칩 · `{n}장 만들기 (약 {m}분)`.
 */
import { Fragment, useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router';
import { Icon, Skeleton } from '@/ui';
import { uploadFile } from '@/api/client';
import { addAttachment, ApiError, errText, generate, patchPlan, postMessage, useRefresh, useVp } from '../api';
import { Agent, BtnLink, Btn, CardHead, Dock, ModeChip, Page, VThumb, useJobDone, useVpShell } from '../parts';

export function StructurePage() {
  const { id = '' } = useParams();
  const nav = useNavigate();
  const vp = useVp(id);
  const doc = vp.data;
  useVpShell(doc, 2);
  const refresh = useRefresh(id);
  const [busy, setBusy] = useState('');
  const [err, setErr] = useState('');
  const [hl, setHl] = useState<string>('');
  const [job, setJob] = useState<string | null>(null);
  const [reply, setReply] = useState('');
  const fileRef = useRef<HTMLInputElement>(null);
  useJobDone(job, async (snap) => {
    setJob(null);
    setReply((snap.result?.needs_clarification as string) || (snap.result?.reply as string) || '');
    await refresh();
  });

  // AC 24 — 답이 필요한(선택 필요) 질문이 열려 있으면 되묻기로
  const openAsk = (doc?.questions ?? []).some((q) => q.status === 'open' && q.mode === 'ask');
  useEffect(() => { if (openAsk) nav(`/vp/${id}/questions`, { replace: true }); }, [openAsk, id]); // eslint-disable-line react-hooks/exhaustive-deps

  const plan = doc?.plan;
  if (!doc || !plan) return <Page><Skeleton h={320} /></Page>;
  const sheets = plan.sheets ?? [];
  const asks = (doc.questions ?? []).filter((q) => q.status === 'open' && q.mode === 'ask');

  const alt = async (role: string, code: string) => {
    setBusy(code);
    setErr('');
    try {
      await patchPlan(id, { [role]: code });
      setHl(role);
      await refresh();
    } catch (e) {
      if (e instanceof ApiError && e.code === 'PREREQUISITE_MISSING' && (e.details as { missing?: string }).missing === 'quote') {
        setErr(e.message);
        fileRef.current?.click();
      } else setErr(errText(e));
    } finally { setBusy(''); }
  };
  const attachQuote = async (files: FileList | null) => {
    if (!files?.length) return;
    setBusy('quote');
    try {
      const fm = await uploadFile(files[0], { confidential: true, purpose: 'vp' });
      await addAttachment(id, fm.id, 'quote');
      setErr('');
      await patchPlan(id, { EF: 'EF-B' }).catch(() => undefined);
      setHl('EF');
      await refresh();
    } catch (e) { setErr(errText(e)); } finally { setBusy(''); if (fileRef.current) fileRef.current.value = ''; }
  };
  const make = async () => {
    setBusy('gen');
    setErr('');
    try {
      const r = await generate(id, doc.status === 'failed' || doc.status === 'stopped');
      await refresh();
      nav(`/vp/${id}/generating?job=${r.job_id}`);
    } catch (e) {
      if (e instanceof ApiError && e.code === 'QUESTION_REQUIRED') nav(`/vp/${id}/questions`);
      setErr(errText(e));
      setBusy('');
    }
  };
  const send = async (text: string) => {
    try { const r = await postMessage(id, { text, context: 'structure' }); setJob(r.job_id); setReply(''); } catch (e) { setErr(errText(e)); }
  };
  const vpSheet = sheets.find((s) => s.role === 'VP');

  return (
    <Page dock={
      <Dock title="가치 구조" meta="2 / 3"
        headRight={<div className="vp-dock__alts">
          {(plan.alternatives ?? []).map((a) => (
            <button key={a.code} type="button" className="vp-alt" title={a.tip} aria-disabled={!!a.prerequisite}
              onClick={() => alt(a.role ?? 'VP', a.code)} disabled={busy === a.code}>
              <b>{a.display}</b>{a.label}
            </button>
          ))}
          {Object.keys(plan.overrides ?? {}).length > 0 && (
            <button type="button" className="vp-alt" onClick={() => patchPlan(id, { clear: true }).then(refresh)}>처음 구조로</button>
          )}
        </div>}
        input={{ placeholder: '구조 요청 (예: 기대 효과는 투자 회수로 보여줘)', label: '구조 요청', onSend: send, busy: !!job }}
        actions={<>
          <input ref={fileRef} type="file" hidden onChange={(e) => attachQuote(e.target.files)} aria-label="견적 첨부" />
          <BtnLink to={`/vp/${id}/materials`}>이전</BtnLink>
          <Btn primary onClick={make} busy={busy === 'gen'} disabled={asks.length > 0} reason="답이 필요한 질문이 남아 있어요">{plan.cta_label}</Btn>
        </>}>
        {(err || reply) && <div style={{ padding: '6px 18px 0 18px' }} className={err ? 'vp-err' : 'vp-card__sub'}>{err || reply}</div>}
      </Dock>
    }>
      <Agent text={plan.intro || doc.intros?.structure}>
        <div className="vp-card" data-testid="vp-structure">
          <CardHead title={`메시지 구조 · ${plan.flow_label}`}
            right={vpSheet && <Link to={`/vp/${id}/result/layout?sheet=plan:VP`} style={{ fontSize: 12, fontWeight: 600, whiteSpace: 'nowrap' }}>레이아웃 전체 보기</Link>}>
            <span className="vp-card__sub">{plan.reason}</span>
          </CardHead>
          <div className="vp-spine">
            {(plan.omitted ?? []).filter((o) => o.role === 'CH').map((o) => (
              <Fragment key="omit">
                <div className="vp-spine__omit" title={o.why}>{o.label}<br />{o.why}</div>
                <span className="vp-spine__arrow"><Icon name="chevronRight" size={16} /></span>
              </Fragment>
            ))}
            {sheets.map((s, i) => (
              <Fragment key={s.role}>
                <div className={hl === s.role ? 'vp-spine__card vp-spine__card--hl' : 'vp-spine__card'} data-role={s.role}>
                  <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 6 }}>
                    <span className="vp-spine__step">{s.step_label}</span>
                    <ModeChip mode={s.mode} />
                  </span>
                  <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span className="vp-spine__thumb"><VThumb code={s.layout.code} kind={s.layout.thumb.kind} n={s.layout.thumb.n} /></span>
                    <span style={{ display: 'flex', flexDirection: 'column', gap: 2, minWidth: 0 }}>
                      <span className="vp-spine__code">{s.chip || s.layout.display}</span>
                      <span className="vp-spine__name">{s.layout.name}</span>
                    </span>
                  </span>
                  <span className="vp-spine__content">{s.content_preview || '—'}</span>
                  <span className="vp-spine__why">{s.layout.why}</span>
                </div>
                {i < sheets.length - 1 && <span className="vp-spine__arrow"><Icon name="chevronRight" size={16} /></span>}
              </Fragment>
            ))}
          </div>
        </div>
        <div className="vp-card" data-testid="vp-decisions">
          <CardHead title="그 밖에 정한 것" meta={String((plan.decisions ?? []).length)}
            right={<Link to="/vp/rules" state={{ back: `/vp/${id}/structure` }} style={{ fontSize: 12, fontWeight: 600 }}>판단 규칙</Link>} />
          {(plan.decisions ?? []).map((r) => (
            <div key={r.key} className="vp-dec">
              <span className="vp-dec__k">{r.key}</span>
              <span className="vp-dec__v" title={r.value}>{r.value}</span>
              <span className="vp-dec__why" title={r.why}>{r.why}</span>
              <ModeChip mode={r.mode} />
            </div>
          ))}
        </div>
      </Agent>
    </Page>
  );
}
