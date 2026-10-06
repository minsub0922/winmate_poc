/**
 * VP3 — 결과(`/vp/:id/result`): 시트 카드 3 · 변형 시트 · 업종판 교체 제안 · 확인할 것 · 도크(레이아웃 바꾸기 · 수치 보강 · 한 문장 버전 · 후속 요청).
 */
import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router';
import { Banner, Skeleton } from '@/ui';
import { addSheet, decidePackOffer, errText, isJob, postMessage, savePoint, useRefresh, useVp, type Sheet } from '../api';
import { Agent, Btn, CardHead, Dock, ModeChip, Page, Spinner, VThumb, useJobDone, useVpShell } from '../parts';

export function ResultPage() {
  const { id = '' } = useParams();
  const nav = useNavigate();
  const vp = useVp(id, { poll: 2500 });
  const doc = vp.data;
  useVpShell(doc, 3, { complete: !!doc?.generated && doc?.ui_status !== 'run' });
  const refresh = useRefresh(id);
  const [job, setJob] = useState<string | null>(null);
  const [busy, setBusy] = useState('');
  const [msg, setMsg] = useState('');
  const [err, setErr] = useState('');
  const j = useJobDone(job, async (snap) => {
    setJob(null);
    await refresh();
    const r = snap.result ?? {};
    if (r.route) { nav(r.route as string); return; }
    if (r.layout_request_id) return;
    if (snap.status === 'failed') setErr(snap.error?.message || '바꾸지 못했어요');
    else setMsg((r.needs_clarification as string) || (r.reply as string) || (r.sheet_id ? '한 문장 버전을 만들었어요' : '반영했어요'));
  });

  if (!doc) return <Page><Skeleton h={360} /></Page>;
  if (!doc.generated && !(doc.sheets ?? []).some((s) => s.status === 'done')) {
    return <Page><Agent text="아직 만든 시트가 없어요. 가치 구조에서 만들기를 눌러 주세요."><Link to={`/vp/${id}/structure`}>가치 구조로</Link></Agent></Page>;
  }
  const sheets = (doc.sheets ?? []).filter((s) => s.kind === 'main' || s.kind === 'summary');
  const variants = doc.variants ?? [];
  const checks = (doc.checks ?? []).filter((c) => !c.resolved);
  const offers = (doc.pack_offers ?? []).filter((o) => o.status === 'open');
  const vpSheet = sheets.find((s) => s.role === 'VP');
  const ef = sheets.find((s) => s.role === 'EF');
  const n = sheets.length;
  const running = !!job || doc.ui_status === 'run';

  const send = async (text: string) => {
    setMsg(''); setErr('');
    try { const r = await postMessage(id, { text, context: 'result' }); setJob(r.job_id); } catch (e) { setErr(errText(e)); }
  };
  const oneLiner = async () => {
    setBusy('ol'); setMsg(''); setErr('');
    try { const r = await addSheet(id, { kind: 'one_liner', layout_code: 'VP-G' }); setJob(r.job_id); } catch (e) { setErr(errText(e)); } finally { setBusy(''); }
  };
  const offer = async (vpo: string, d: 'apply' | 'dismiss') => {
    try { const r = await decidePackOffer(id, vpo, d); if (isJob(r.data)) setJob(r.data.job_id); else await refresh(); } catch (e) { setErr(errText(e)); }
  };
  const save = async () => {
    setBusy('save');
    try { await savePoint(id, '저장 · 내보내기'); nav(`/vp/${id}/export`); } catch (e) { setErr(errText(e)); setBusy(''); }
  };

  return (
    <Page dock={
      <Dock title="결과" meta={`${sheets.filter((s) => s.status === 'done').length} / ${n} · ${doc.ui_status === 'run' ? '고치는 중' : '완료'}`}
        headRight={<div className="vp-dock__alts">
          {vpSheet && <Link className="vp-alt" to={`/vp/${id}/result/layout?sheet=${vpSheet.id}`}>레이아웃 바꾸기</Link>}
          {ef && <Link className="vp-alt" to={`/vp/${id}/result/numbers?sheet=${ef.id}`}>수치 보강</Link>}
          <button type="button" className="vp-alt" onClick={oneLiner} disabled={busy === 'ol' || running}>한 문장 버전도 만들기</button>
        </div>}
        input={{ placeholder: "후속 요청 (예: 두 번째 기둥을 '손님이 먼저 읽는 메뉴'로)", label: '후속 요청', onSend: send, busy: running }}
        actions={<>
          <Btn onClick={save} busy={busy === 'save'}>저장 · 내보내기</Btn>
          <Link to={`/vp/${id}/export`} className="vp-btn vp-btn--primary">제안서 Value Props로</Link>
        </>}>
        {(running || msg || err) && (
          <div style={{ padding: '8px 18px 0 18px' }}>
            {running ? <Spinner label={`고치는 중 · ${j.progress || doc.active_job?.progress || 0}%`} /> : <span className={err ? 'vp-err' : 'vp-card__sub'}>{err || msg}</span>}
          </div>
        )}
      </Dock>
    }>
      <Agent text={doc.intros?.result}>
        {offers.map((o) => (
          <Banner key={o.id} tone="info" title={`업종판이 나왔어요 — ${(o.changes ?? []).length}장을 업종 레이아웃으로 바꿀까요?`} sub="고정한 시트는 그대로 둡니다"
            action={<span style={{ display: 'flex', gap: 6 }}><button type="button" className="vp-mini" onClick={() => offer(o.id, 'dismiss')}>그대로 두기</button><button type="button" className="vp-mini vp-mini--primary" onClick={() => offer(o.id, 'apply')}>바꾸기</button></span>} />
        ))}
        <div className="vp-cards" data-testid="vp-result-cards">
          {sheets.map((s) => <SheetCard key={s.id} s={s} id={id} />)}
        </div>
        {variants.length > 0 && (
          <div className="vp-variants" aria-label="변형 시트">
            {variants.map((v) => (
              <div key={v.id} className="vp-variant" data-kind={v.kind}>
                <span style={{ width: 120, height: 68, flexShrink: 0 }}><VThumb code={v.layout.code} kind={v.layout.thumb.kind} n={v.layout.thumb.n} /></span>
                <span style={{ display: 'flex', flexDirection: 'column', gap: 2, minWidth: 0 }}>
                  <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--wm-text-2)' }}>{v.step_label} · <span className="vp-num">{v.layout.display}</span></span>
                  <span style={{ fontSize: 13, fontWeight: 700 }} className="wm-ellipsis">{v.title || '작성 중'}</span>
                  <span className="vp-scard__meta">{v.points}</span>
                </span>
              </div>
            ))}
          </div>
        )}
        <div className="vp-card" data-testid="vp-checks">
          <CardHead title="확인할 것" meta={checks.length ? `${checks.length} · 모두 그대로 둬도 제안서에 보낼 수 있어요` : '없어요'} />
          {checks.map((c) => (
            <div key={c.id} className="vp-check" data-tag={c.tag}>
              <span className={c.strong ? 'vp-check__tag vp-check__tag--strong' : 'vp-check__tag'}>{c.tag}</span>
              <span className="vp-check__t" title={c.text}>{c.text}</span>
              <Link to={c.action_route} className="vp-check__act">{c.action_label}</Link>
            </div>
          ))}
        </div>
      </Agent>
    </Page>
  );
}

function SheetCard({ s, id }: { s: Sheet; id: string }) {
  const waiting = s.status !== 'done';
  return (
    <div className={waiting ? 'vp-scard vp-scard--wait' : 'vp-scard'} data-testid="vp-sheet" data-role={s.role}>
      <div className="vp-scard__head">
        <span className="vp-scard__step">{s.step_label}</span>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, whiteSpace: 'nowrap' }}>
          <span className="vp-num" style={{ fontSize: 12 }}>{s.layout.display}</span>
          <ModeChip mode={s.pinned ? 'pin' : s.mode} small />
        </span>
      </div>
      <div className="vp-scard__thumb"><VThumb code={s.layout.code} kind={s.layout.thumb.kind} n={s.layout.thumb.n} /></div>
      <span className="vp-scard__title">{waiting ? '작성 중' : s.title}</span>
      <span className="vp-scard__points">{waiting ? '' : s.points}</span>
      <div className="vp-scard__foot">
        <span className="vp-scard__meta">{s.meta_label}</span>
        <Link to={`/vp/${id}/result/layout?sheet=${s.id}`} style={{ fontSize: 12, fontWeight: 600, whiteSpace: 'nowrap' }}>왜 이 레이아웃?</Link>
      </div>
    </div>
  );
}
