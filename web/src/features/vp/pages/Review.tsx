/**
 * VP1A — 재료 자동 수집 · 충돌 정리(`/vp/:id/materials/review`): 뽑은 재료 4축 + 출처 태그 · 에이전트가 정리한 것(합침 · 고쳐 씀 · 다시 찾음).
 */
import { useState } from 'react';
import { useNavigate, useParams } from 'react-router';
import { Skeleton } from '@/ui';
import { decideFix, errText, getVp, postMessage, refreshPlan, useRefresh, useVp, type Fix, type MaterialItem } from '../api';
import { Agent, BtnLink, Btn, CardHead, Dock, ModeChip, Page, SrcTag, UserBubble, useJobDone, useVpShell } from '../parts';

const AXES: Array<[string, string]> = [['challenge', '과제'], ['value', '가치'], ['evidence', '근거 수치'], ['stakeholder', '이해관계자']];

export function ReviewPage() {
  const { id = '' } = useParams();
  const nav = useNavigate();
  const vp = useVp(id);
  const doc = vp.data;
  useVpShell(doc, 1);
  const refresh = useRefresh(id);
  const [busy, setBusy] = useState('');
  const [err, setErr] = useState('');
  const [job, setJob] = useState<string | null>(null);
  useJobDone(job, async () => { setJob(null); await refresh(); });

  if (!doc) return <Page><Skeleton h={320} /></Page>;
  const mats = (doc.materials ?? []).filter((m) => !m.excluded && m.axis !== 'product');
  const fixes = doc.fixes ?? [];
  const nAuto = fixes.filter((f) => f.mode === 'auto').length;
  const nCheck = fixes.filter((f) => f.mode === 'check').length;

  const decide = async (f: Fix, d: 'accept' | 'revert') => {
    setBusy(f.id);
    try { await decideFix(id, f.id, d); await refresh(); } catch (e) { setErr(errText(e)); } finally { setBusy(''); }
  };
  const next = async () => {
    setBusy('next');
    try {
      await refreshPlan(id);
      const fresh = await getVp(id);
      await refresh();
      const ask = (fresh.questions ?? []).some((q) => q.status === 'open');
      nav(ask ? `/vp/${id}/questions` : `/vp/${id}/structure`);
    } catch (e) { setErr(errText(e)); setBusy(''); }
  };
  const send = async (text: string) => {
    try { const r = await postMessage(id, { text, context: 'materials' }); setJob(r.job_id); } catch (e) { setErr(errText(e)); }
  };

  return (
    <Page dock={
      <Dock title="재료 확인" meta={`1 / 3 · 자동 정리 ${nAuto} · 확인 권장 ${nCheck} — 답이 없으면 고쳐 쓴 문장으로 진행`}
        input={{ placeholder: '재료에 덧붙일 말 (예: 손님 관점은 빼고 본사 기준으로)', label: '재료에 덧붙일 말', onSend: send, busy: !!job }}
        actions={<>
          {err && <span className="vp-err">{err}</span>}
          <BtnLink to={`/vp/${id}/materials`}>이전</BtnLink>
          <Btn primary onClick={next} busy={busy === 'next'}>가치 구조로</Btn>
        </>} />
    }>
      {doc.labels?.connect && <UserBubble head="자료 연결" rest={doc.labels.connect} />}
      <Agent text={doc.intros?.materials_review}>
        <div className="vp-card" data-testid="vp-materials">
          <CardHead title="뽑은 재료" meta={`4축 · ${mats.length}개`}>
            <span className="vp-grow" />
            {(doc.legend ?? []).map((l) => (
              <span key={l.tag} style={{ display: 'inline-flex', alignItems: 'center', gap: 5, fontSize: 11.5, color: 'var(--wm-text-muted)', whiteSpace: 'nowrap' }}>
                <SrcTag tag={l.tag} />{l.name}
              </span>
            ))}
          </CardHead>
          {AXES.map(([axis, label]) => (
            <div key={axis} className="vp-axis">
              <span className="vp-axis__k">{label}</span>
              <div className="vp-axis__items">
                {mats.filter((m) => m.axis === axis).map((m) => <Mat key={m.id} m={m} />)}
                {!mats.some((m) => m.axis === axis) && <span style={{ fontSize: 12, color: 'var(--wm-text-subtle)', lineHeight: '26px' }}>아직 없어요 — 만들 때 사례 DB로 채워요</span>}
              </div>
            </div>
          ))}
        </div>
        {fixes.length > 0 && (
          <div className="vp-card" data-testid="vp-fixes">
            <CardHead title="에이전트가 정리한 것" meta={String(fixes.length)} />
            {fixes.map((f) => (
              <div key={f.id} className="vp-fix" data-decision={f.decision}>
                <span className="vp-fix__k">{f.kind_label}</span>
                <span style={{ display: 'flex', flexDirection: 'column', gap: 1, minWidth: 0 }}>
                  <span className="vp-fix__from" title={f.from_text}>{f.from_text}</span>
                  <span className="vp-fix__to" title={f.to_text}>→ {f.to_text}</span>
                </span>
                <ModeChip mode={f.mode} />
                <span className="vp-fix__acts">
                  {f.decision === 'reverted'
                    ? <><span className="vp-mini vp-mini--done">원래대로 둠</span><button type="button" className="vp-mini vp-mini--ghost" onClick={() => decide(f, 'accept')} disabled={busy === f.id}>다시 적용</button></>
                    : f.mode === 'check' && f.decision === 'pending'
                      ? <>
                        <button type="button" className="vp-mini" onClick={() => decide(f, 'revert')} disabled={busy === f.id}>원래대로</button>
                        <button type="button" className="vp-mini vp-mini--primary" onClick={() => decide(f, 'accept')} disabled={busy === f.id}>좋아요</button>
                      </>
                      : <button type="button" className="vp-mini vp-mini--ghost" onClick={() => decide(f, 'revert')} disabled={busy === f.id}>되돌리기</button>}
                </span>
              </div>
            ))}
          </div>
        )}
      </Agent>
    </Page>
  );
}

function Mat({ m }: { m: MaterialItem }) {
  const num = m.number?.display && !m.text.includes(m.number.display) ? ` ${m.number.display}` : '';
  const flags = (m.flags ?? []).filter((f) => f.startsWith('['));
  return (
    <span className={`vp-mat vp-mat--${m.state}`} title={(m.sources ?? []).map((s) => `${s.tag}${s.locator ? ' ' + s.locator : ''}`).join(' · ')} data-state={m.state}>
      <span>{m.text}{num}</span>
      {flags.map((f) => <span key={f} className="vp-mat__flag">{f}</span>)}
      {m.state === 'inferred' && <span className="vp-mat__flag">추론</span>}
      {Array.from(new Set((m.sources ?? []).map((s) => s.tag))).map((t) => <SrcTag key={t} tag={t} />)}
    </span>
  );
}
