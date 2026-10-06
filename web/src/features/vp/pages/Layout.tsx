/**
 * VP3L — 레이아웃 바꾸기 · 적합도(`/vp/:id/result/layout?sheet=&req=`): 선택지 A/B/C(요청이 있을 때) · 후보 그리드 · 기둥 수 · 고정.
 * 생성 전(`sheet=plan:VP`)이면 후보 · 적합도만 보고 플랜 대안으로 바꾼다.
 */
import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router';
import { Skeleton, ErrorState } from '@/ui';
import { cancelLayoutRequest, chooseLayout, errText, isJob, patchPlan, useLayoutOptions, useRefresh, useVp } from '../api';
import { Agent, Btn, CardHead, Dock, Page, Spinner, VThumb, useJobDone, useVpShell } from '../parts';

export function LayoutPage() {
  const { id = '' } = useParams();
  const [sp] = useSearchParams();
  const nav = useNavigate();
  const sheetId = sp.get('sheet') || '';
  const reqParam = sp.get('req') || undefined;
  const preset = sp.get('code') || '';
  const vp = useVp(id);
  const doc = vp.data;
  useVpShell(doc, doc?.generated ? 3 : 2);
  const [pillars, setPillars] = useState<number | undefined>(undefined);
  const opts = useLayoutOptions(id, sheetId, pillars, reqParam);
  const refresh = useRefresh(id);
  const [key, setKey] = useState<'A' | 'B' | 'C' | null>(null);
  const [code, setCode] = useState<string>(preset);
  const [pin, setPin] = useState(false);
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const [job, setJob] = useState<string | null>(null);
  const j = useJobDone(job, async (snap) => {
    await refresh();
    if (snap.status === 'succeeded') nav(`/vp/${id}/result`);
    else { setErr(snap.error?.message || '바꾸지 못했어요'); setJob(null); setBusy(false); }
  });
  const data = opts.data;
  useEffect(() => {
    if (!data) return;
    setPin(!!data.pinned);
    const rec = data.options?.find((o) => o.recommended);
    if (rec && !preset) { setKey(rec.key); setCode(''); }
  }, [data?.request_id, data?.pinned]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!doc || opts.isLoading) return <Page><Skeleton h={360} /></Page>;
  if (opts.isError || !data) return <Page><ErrorState message={errText(opts.error)} onRetry={() => opts.refetch()} /></Page>;
  const isPlan = sheetId.startsWith('plan:');
  const cur = data.candidates.find((c) => c.state === 'cur');
  const target = key ? null : (code || null);
  const ctaLabel = key ? `${key}로 바꾸기` : target ? `${data.candidates.find((c) => c.code === target)?.display ?? target}로 바꾸기` : (pin !== !!data.pinned ? '고정 바꾸기' : '그대로 두기');

  const apply = async () => {
    setBusy(true);
    setErr('');
    try {
      if (isPlan) {
        if (target) await patchPlan(id, { [sheetId.split(':')[1]]: target });
        await refresh();
        nav(`/vp/${id}/structure`);
        return;
      }
      if (!key && !target && pin === !!data.pinned) { nav(`/vp/${id}/result`); return; }
      const r = await chooseLayout(id, data.sheet_id, { option_key: key ?? undefined, layout_code: target ?? undefined, pillars, pin, note: note || undefined, request_id: data.request_id ?? undefined });
      if (isJob(r.data)) setJob(r.data.job_id);
      else { await refresh(); nav(`/vp/${id}/result`); }
    } catch (e) { setErr(errText(e)); setBusy(false); }
  };
  const cancel = async () => {
    if (data.request_id) await cancelLayoutRequest(id, data.request_id).catch(() => undefined);
    await refresh();
    nav(isPlan ? `/vp/${id}/structure` : `/vp/${id}/result`);
  };
  const reqText = doc.layout_requests?.find((r) => r.id === data.request_id)?.request_text;
  const intro = reqText && data.intro.startsWith(`'${reqText}'`) ? data.intro.slice(reqText.length + 2) : data.intro;

  return (
    <Page dock={
      <Dock title="레이아웃 바꾸기" meta={data.other_sheets_label.replace(/^· /, '')}
        headRight={<Link to="/vp/rules" state={{ back: `/vp/${id}/result/layout?sheet=${sheetId}` }} style={{ fontSize: 12.5, fontWeight: 600, whiteSpace: 'nowrap' }}>적합도 매기는 법</Link>}>
        <div className="vp-dock__row">
          <div className="vp-ask">
            <label className="wm-sr-only" htmlFor="vp-note">덧붙일 말</label>
            <input id="vp-note" value={note} onChange={(e) => setNote(e.target.value)} placeholder="덧붙일 말 (예: 요약 한 장은 원장님 관점으로)" />
          </div>
          {err && <span className="vp-err">{err}</span>}
          <button type="button" className="vp-btn" onClick={cancel}>취소</button>
          {job ? <Spinner label={`바꾸는 중 · ${j.progress}%`} /> : <Btn primary onClick={apply} busy={busy}>{ctaLabel}</Btn>}
        </div>
      </Dock>
    }>
      <Agent text={reqText ? <><b>'{reqText}'</b>{intro}</> : data.intro}>
        {!!data.options?.length && (
          <div className="vp-card" role="radiogroup" aria-label="선택지">
            {data.options.map((o) => (
              <label key={o.key} className={key === o.key ? 'vp-lopt vp-lopt--on' : 'vp-lopt'}>
                <input type="radio" name="opt" checked={key === o.key} onChange={() => { setKey(o.key); setCode(''); }} />
                <span className="vp-lopt__k">{o.key}</span>
                <span className="vp-lopt__t">{o.title}</span>
                {o.recommended && <span className="vp-opt__rec">추천</span>}
                <span className="vp-lopt__d">{o.desc}</span>
              </label>
            ))}
          </div>
        )}
        <div className="vp-card" data-testid="vp-candidates">
          <CardHead title={`${data.sheet_label} · 고를 수 있는 레이아웃`} meta={`제품 이미지판 ${data.header.image} + 이미지 없이 ${data.header.no_image} + 업종판 ${data.header.industry}`}
            right={<span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: 12, color: 'var(--wm-text-muted)' }}>기둥 수</span>
              <span className="vp-pillars" role="group" aria-label="기둥 수">
                {[2, 3, 4].map((x) => <button key={x} type="button" aria-pressed={(pillars ?? data.pillars) === x} onClick={() => setPillars(x)}>{x}</button>)}
              </span>
            </span>} />
          <div className="vp-cands">
            {data.candidates.map((c) => {
              const sel = !key && code === c.code;
              const no = c.state === 'no';
              return (
                <button key={c.code} type="button" disabled={no} title={no ? '업종판 제작 중 · 출시 알림 켜짐' : c.why}
                  className={['vp-cand', `vp-cand--${c.state}`, sel && 'vp-cand--sel'].filter(Boolean).join(' ')} data-state={c.state}
                  aria-pressed={sel} onClick={() => { if (!no) { setKey(null); setCode(c.code === cur?.code ? '' : c.code); } }}>
                  <span style={{ width: 120, height: 68, alignSelf: 'center' }}><VThumb code={c.code} kind={c.thumb.kind} n={c.thumb.n} dim={no} /></span>
                  <span className="vp-cand__row">
                    <span className="vp-cand__code">{c.display}</span>
                    <span className={c.fit >= 85 ? 'vp-cand__fit vp-cand__fit--hi' : 'vp-cand__fit'}>{c.fit < 0 ? '준비 중' : `${c.fit}%`}</span>
                  </span>
                  <span className="vp-cand__why">{c.why}</span>
                </button>
              );
            })}
          </div>
          {!isPlan && (
            <label className="vp-pin" style={{ padding: '0 16px 14px 16px' }}>
              <input type="checkbox" checked={pin} onChange={(e) => setPin(e.target.checked)} />이 시트 고정 — 재료가 바뀌어도 다시 고르지 않아요
            </label>
          )}
        </div>
      </Agent>
    </Page>
  );
}
