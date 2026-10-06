/** MI3 — 분석 결과 `/mi/:id/result?tab=&version=&preview=1` (§4.7) · `&panel=sources&claim=` 이면 MI3S */
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { Modal, Thumb, cx, toast } from '@/ui';
import { useJob } from '@/api/jobs';
import { fileUrl } from '@/api/client';
import {
  AREAS, errText, followup, getOnepager, handoff, isApiError, patchAnalysis, patchHandoff, proposalImport, qk, restoreVersion, startExport,
  startOnepager, startRun, tableText, useAnalysis, useResult, useSegments, useVersions, type Analysis, type Area, type ResultView,
} from '../api';
import { useLastScreen } from '../hooks';
import { AREA_NAME, copyText, tsvToHtml, withRo } from '../lib';
import { TabBody } from '../blocks';
import { Agent, BigButton, Dock, ErrorBand, Ic, LoadingCard, MiPage, ModeChip, P, Pill, PromptInput, ResultTabs, SecButton, Spin, UserBubble, useAid, useMiShell } from '../parts';
import { SourcesView } from './SourcesView';

export function ResultPage() {
  const aid = useAid();
  const [sp, setSp] = useSearchParams();
  const nav = useNavigate();
  const qc = useQueryClient();
  const version = sp.get('version') ? Number(sp.get('version')) : null;
  const preview = sp.get('preview') === '1';
  const panel = sp.get('panel') === 'sources';
  const claimId = sp.get('claim');
  const a = useAnalysis(aid, { poll: preview ? 4000 : false });
  const res = useResult(aid, { version, preview });
  const r = res.data;
  useMiShell(a.data, 3);
  useLastScreen(aid, panel ? 'result' : 'result');

  const tabs = r?.tabs ?? [];
  const firstDone = tabs.find((t) => t.status === 'done')?.area as Area | undefined;
  const tabParam = sp.get('tab') as Area | null;
  const tab: Area = tabParam && AREAS.includes(tabParam) ? tabParam : (firstDone ?? (tabs[0]?.area as Area) ?? 'market');

  const set = useCallback((p: Record<string, string | null>, replace = true) => {
    const next = new URLSearchParams(sp);
    for (const [k, v] of Object.entries(p)) { if (v) next.set(k, v); else next.delete(k); }
    setSp(next, { replace });
  }, [sp, setSp]);

  // 미리 보기에서 분석이 끝나면 최신 결과로
  useEffect(() => {
    if (preview && a.data && (a.data.status === 'done' || a.data.status === 'upd')) set({ preview: null });
  }, [preview, a.data, set]);

  if (res.isError && isApiError(res.error) && res.error.status === 404) {
    return (
      <MiPage>
        <Agent text="아직 결과가 없어요.">
          <div className="mi-row"><Link to={`/mi/${aid}/run`} className="mi-btn">진행 보기</Link><Link to="/mi" className="mi-btn">목록으로</Link></div>
        </Agent>
      </MiPage>
    );
  }
  if (panel && r && aid) {
    return (
      <SourcesView aid={aid} r={r} tab={tab} claimId={claimId} version={version}
        onTab={(t) => set({ tab: t, claim: null })} onClaim={(c) => set({ claim: c })} onClose={() => set({ panel: null, claim: null })} />
    );
  }
  return <ResultMain aid={aid!} a={a.data} r={r} loading={res.isLoading} error={res.isError} retry={() => void res.refetch()} tab={tab} preview={preview}
    version={version} onTab={(t) => set({ tab: t })} openPanel={(claim) => set({ panel: 'sources', claim: claim ?? null })} showVersions={sp.get('versions') === '1'}
    closeVersions={() => set({ versions: null })} nav={nav} qc={qc} />;
}

function ResultMain({ aid, a, r, loading, error, retry, tab, preview, version, onTab, openPanel, showVersions, closeVersions, nav, qc }:
  { aid: string; a?: Analysis; r?: ResultView; loading: boolean; error: boolean; retry: () => void; tab: Area; preview: boolean; version: number | null;
    onTab: (t: Area) => void; openPanel: (claim?: string | null) => void; showVersions: boolean; closeVersions: () => void;
    nav: ReturnType<typeof useNavigate>; qc: ReturnType<typeof useQueryClient> }) {
  const [hlInferred, setHlInferred] = useState(false);
  const [talk, setTalk] = useState<Array<{ q: string; a?: string; cites?: number[]; busy?: boolean }>>([]);
  const [sending, setSending] = useState(false);
  const [segSheet, setSegSheet] = useState(false);
  const [onepager, setOnepager] = useState(false);

  const comp = (a?.scope?.areas ?? []).includes('competitor');
  const tabInfo = r?.tabs.find((t) => t.area === tab);
  const footer = r?.footers?.[tab];
  const isOld = !!r && !r.is_latest;

  async function ask(text: string) {
    const i = talk.length;
    setTalk((x) => [...x, { q: text, busy: true }]);
    try {
      const out = await followup(aid, { text, tab });
      if (out.intent === 'revision' && out.revision_id) { nav(`/mi/${aid}/revise?rev=${out.revision_id}`); return; }
      setTalk((x) => x.map((y, j) => (j === i ? { q: text, a: out.answer_md ?? '', cites: out.citations.map((c) => c.n) } : y)));
    } catch (e) {
      setTalk((x) => x.map((y, j) => (j === i ? { q: text, a: errText(e) } : y)));
    }
  }

  async function copyTable() {
    try {
      const t = await tableText(aid, 'customer');
      const [head = [], ...body] = t.text.split('\n').map((l) => l.split('\t'));
      const ok = await copyText(t.text, tsvToHtml(head, body));
      toast(ok ? '비교표를 복사했어요' : '복사하지 못했어요');
    } catch (e) { toast(errText(e)); }
  }

  /** `제안서 MI 섹션으로` — 바로 넘길 수 있으면 넘기고(연결된 제안서 · 묻기 없음), 아니면 MI4(§4.7 · AC-MI-65) */
  async function send() {
    setSending(true);
    try {
      const dry = await handoff(aid, { target: 'proposal_mi', dry_run: true });
      if (dry.status !== 'ready' || !dry.target_id) { nav(`/mi/${aid}/export`); return; }
      const out = await handoff(aid, { target: 'proposal_mi', target_id: dry.target_id, sheets: dry.sheets });
      try {
        await proposalImport(dry.target_id, {
          section_key: out.section_key, via: 'handoff', source: { feature: 'MI', ref_id: aid, version: r?.version, handoff_id: out.handoff_id }, include_keys: out.sheets,
        });
        await patchHandoff(aid, out.handoff_id!, { status: 'delivered', target_title: a?.links?.proposal_title ?? null, target_id: dry.target_id });
        void qc.invalidateQueries({ queryKey: ['mi', 'list'] });
        nav(`/proposal/${dry.target_id}/sections/${out.section_key === 'bigMi' ? 'bigMi' : 'mi'}`);
      } catch (e) {
        await patchHandoff(aid, out.handoff_id!, { status: 'failed' }).catch(() => undefined);
        toast(`제안서에 보내지 못했어요 · ${errText(e)}`);
        nav(`/mi/${aid}/export`);
      }
    } catch (e) {
      if (isApiError(e, 'ASK_REQUIRED') || isApiError(e, 'NO_TARGET')) nav(`/mi/${aid}/export`);
      else toast(errText(e));
    } finally {
      setSending(false);
    }
  }

  async function rerunArea(area: Area) {
    try {
      await startRun(aid, { mode: 'auto', areas: [area] });
      nav(`/mi/${aid}/run`);
    } catch (e) { toast(errText(e)); }
  }

  async function rerunChanged() {
    try {
      await startRun(aid, { mode: 'changed_only' });
      nav(`/mi/${aid}/run`);
    } catch (e) { toast(errText(e)); }
  }

  async function restore() {
    if (!version) return;
    try {
      await restoreVersion(aid, version);
      void qc.invalidateQueries({ queryKey: ['mi'] });
      nav(`/mi/${aid}/result`);
    } catch (e) { toast(errText(e)); }
  }

  function onChip(kind: string) {
    if (kind === 'segment') setSegSheet(true);
    else if (kind === 'competitors') nav(`/mi/${aid}/revise?scope=area&area=competitor`);
    else if (kind === 'conflict') openPanel(null);
    else if (kind === 'inferred') setHlInferred((v) => !v);
  }

  const doneLabel = preview ? '정리 중' : '완료';
  return (
    <MiPage dock={
      <Dock title="분석 결과" meta={`3 / 3 · ${doneLabel}`}
        right={<>
          {comp ? <Pill to={`/mi/${aid}/revise?scope=area&area=competitor`}>경쟁사 추가 분석</Pill> : <Pill to={`/mi/${aid}/scope`}>영역 추가 분석</Pill>}
          <Pill to={`/mi/${aid}/verify`}>수치 근거 더 찾기</Pill>
          <Pill onClick={() => setOnepager(true)} disabled={preview || !r}>한 장 요약</Pill>
        </>}
        row={
          <div className="mi-dock__row">
            <PromptInput label="후속 질문" placeholder="후속 질문 (예: 가맹점주 입장에서의 도입 장벽은?)" onSend={ask} disabled={preview || !r} />
            <SecButton to={`/mi/${aid}/export`} disabled={preview} title={preview ? '분석이 끝나면 저장할 수 있어요' : undefined}>리포트 저장</SecButton>
            <BigButton onClick={() => void send()} busy={sending} disabled={preview || !r || isOld} reason={preview ? '분석이 끝나면 보낼 수 있어요' : '최신 결과에서 보낼 수 있어요'}
              testId="mi3-send">제안서 MI 섹션으로</BigButton>
          </div>
        } />
    }>
      <Agent text={r?.agent_text ?? '분석 결과를 불러오고 있어요.'} testId="mi3-agent">
        {r && r.check_chips.length > 0 && !preview && (
          <div className="mi-chips" data-testid="mi3-chips">
            {r.check_chips.map((c) => (
              <button key={c.kind} type="button" className="mi-cchip" onClick={() => onChip(c.kind)} aria-pressed={c.kind === 'inferred' ? hlInferred : undefined}>
                {c.label}{c.mode && <ModeChip mode={c.mode} />}
              </button>
            ))}
          </div>
        )}
        {r?.upd && <div className="mi-band" data-testid="mi3-upd"><Ic d={P.refresh} size={15} className="mi-brand" /><span className="mi-band__grow">{(r.upd as { text?: string }).text}</span>
          <button type="button" className="mi-mini mi-mini--primary" onClick={() => void rerunChanged()}>바뀐 부분만 다시 분석</button></div>}
        {r?.web_unavailable && <div className="mi-band mi-band--muted" data-testid="mi3-web">웹 검색을 쓸 수 없어 사내 자료로만 분석했어요</div>}
        {isOld && r && <div className="mi-band mi-band--muted" data-testid="mi3-old"><span className="mi-band__grow">v{r.version} · {r.created_at.slice(0, 10)} 결과를 보고 있어요</span>
          <button type="button" className="mi-mini" onClick={() => void restore()}>이 버전으로 되돌리기</button></div>}
        {r?.stopped && <div className="mi-band mi-band--muted">중지한 분석이에요 · 정리된 영역만 보여요</div>}
        {error && <ErrorBand onRetry={retry} />}
        {loading && <LoadingCard lines={8} />}
        {r && (
          <div className="mi-card" data-testid="mi3-card">
            <ResultTabs tabs={r.tabs} value={tab} onChange={onTab} previewMode={preview} />
            <div className="mi-tabbody" role="tabpanel" aria-label={tabInfo?.label}>
              {tabInfo?.status === 'failed' && (
                <div className="mi-failed" data-testid="mi3-failed">
                  이 영역은 분석하지 못했어요
                  <button type="button" className="mi-mini mi-mini--primary" onClick={() => void rerunArea(tab)}>다시 분석</button>
                </div>
              )}
              {tabInfo && (tabInfo.status === 'running' || tabInfo.status === 'wait') && <div className="mi-wait"><Spin size={16} />정리 중</div>}
              {tabInfo?.status === 'done' && <TabBody r={r} area={tab} onCite={(id) => openPanel(id)} hl={hlInferred} />}
              {footer && tabInfo?.status === 'done' && (
                <div className="mi-footer">
                  <span data-testid="mi3-footer">{footer.text}</span>
                  <div className="mi-row" style={{ gap: 6, flexShrink: 0 }}>
                    <button type="button" className="mi-mini" onClick={() => openPanel(null)}>출처 보기</button>
                    {tab === 'competitor' && <button type="button" className="mi-mini" onClick={() => void copyTable()}>표 복사</button>}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
        {r?.implications && <Implications imp={r.implications as Record<string, unknown>} />}
      </Agent>
      {talk.map((x, i) => (
        <div key={i} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <UserBubble>{x.q}</UserBubble>
          <Agent>{x.busy ? <span className="mi-row"><Spin size={14} /> 이 작업의 출처에서 찾는 중</span>
            : <div className="mi-answer__text" data-testid="mi3-answer">{x.a}{(x.cites ?? []).map((n) => <button key={n} type="button" className="mi-cite" onClick={() => openPanel(null)}>{n}</button>)}</div>}</Agent>
        </div>
      ))}
      {segSheet && a && <SegmentSheet a={a} onClose={() => setSegSheet(false)} />}
      {onepager && <OnepagerSheet aid={aid} onClose={() => setOnepager(false)} />}
      {showVersions && <VersionsSheet aid={aid} onClose={closeVersions} />}
    </MiPage>
  );
}

function Implications({ imp }: { imp: Record<string, unknown> }) {
  const items = (imp.items ?? imp.findings ?? []) as Array<Record<string, string>>;
  if (!Array.isArray(items) || !items.length) return null;
  return (
    <div className="mi-card">
      <div className="mi-card__head"><span className="mi-card__title">MI 시사점</span></div>
      <div className="mi-card__body">
        {items.map((x, i) => <div key={i} className="mi-claim">{x.text ?? x.finding ?? x.title ?? ''}{x.direction ? ` → ${x.direction}` : ''}</div>)}
      </div>
    </div>
  );
}

/** 결과 화면 업종 칩 → 업종 바꾸기(MI1Q 선택지 형식, 제안) — 바꾸면 업종에 기대는 영역만 다시 분석 */
function SegmentSheet({ a, onClose }: { a: Analysis; onClose: () => void }) {
  const nav = useNavigate();
  const segs = useSegments();
  const [pick, setPick] = useState(a.segment?.code ?? '');
  const [busy, setBusy] = useState(false);
  const opts = useMemo(() => {
    const c = (a.segment?.candidates ?? []).filter((x) => x.code !== 'GEN').slice(0, 3);
    const items = segs.data?.items ?? [];
    const all = c.length ? c.map((x) => ({ code: x.code, score: x.confidence })) : items.slice(0, 3).map((s) => ({ code: s.code, score: null as number | null }));
    if (a.segment?.code && !all.some((x) => x.code === a.segment!.code)) all.unshift({ code: a.segment.code, score: a.segment.confidence ?? null });
    return all.map((x) => ({ ...x, name: x.code === 'GEN' ? '범용' : items.find((s) => s.code === x.code)?.short ?? x.code }));
  }, [a, segs.data]);
  const chosen = opts.find((o) => o.code === pick);
  async function go() {
    if (!chosen) return;
    setBusy(true);
    try {
      await patchAnalysis(a.id, { segment: { code: chosen.code, mode: 'pin' } });
      await startRun(a.id, { mode: 'auto' });
      nav(`/mi/${a.id}/run`);
    } catch (e) { toast(errText(e)); setBusy(false); }
  }
  return (
    <Modal open onClose={onClose} title="업종 바꾸기" width={620} footer={
      <div className="mi-row" style={{ justifyContent: 'space-between', gap: 8 }}>
        <Link to={`/mi/${a.id}/industry`} className="mi-link">다른 업종 고르기</Link>
        <div className="mi-row" style={{ gap: 8 }}>
          <SecButton onClick={onClose}>취소</SecButton>
          <BigButton onClick={() => void go()} busy={busy} disabled={!chosen || chosen.code === a.segment?.code}>{chosen ? `${withRo(chosen.name)} 다시 분석` : '다시 분석'}</BigButton>
        </div>
      </div>}>
      <div className="mi-opts" style={{ padding: 0 }} role="radiogroup" aria-label="업종">
        {opts.map((o) => (
          <div key={o.code} role="radio" aria-checked={o.code === pick} tabIndex={0} className="mi-opt" onClick={() => setPick(o.code)}
            onKeyDown={(e) => { if (e.key === ' ' || e.key === 'Enter') { e.preventDefault(); setPick(o.code); } }}>
            <span className="mi-opt__radio" />
            <div className="mi-opt__body">
              <div className="mi-row"><span className="mi-opt__name">{o.name}</span>{o.code === a.segment?.code && <ModeChip mode={(a.segment?.mode ?? 'auto') as 'auto'}>현재</ModeChip>}</div>
              <div className="mi-row">
                {o.score !== null && <><div className={cx('mi-score', o.code === opts[0]?.code && 'mi-score--top')}><div style={{ width: `${Math.round(o.score * 100)}%` }} /></div>
                  <span className="mi-num" style={{ fontSize: 12, fontWeight: 700 }}>{o.score.toFixed(2)}</span></>}
                <span className="mi-opt__codes">MI-{o.code}-A · B · C</span>
              </div>
            </div>
            <div className="mi-opt__thumbs">{['barline', 'process', 'journey'].map((k) => <div key={k} className="mi-thumb"><Thumb kind={k} n={3} /></div>)}</div>
          </div>
        ))}
      </div>
      <div className="mi-note" style={{ marginTop: 10 }}>바꾸면 업종에 기대는 영역(시장 · 고객 · 사용자)과 레이아웃만 다시 분석해요.</div>
    </Modal>
  );
}

/** `한 장 요약`(제안) — IM-B 형식(4분면 요약 + 결론) 미리보기 · 복사 · PPTX로 받기. 새 검색은 하지 않는다 */
function OnepagerSheet({ aid, onClose }: { aid: string; onClose: () => void }) {
  const [job, setJob] = useState<string | null>(null);
  const [data, setData] = useState<{ quadrants: Record<string, string>; conclusion: string } | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [fileJob, setFileJob] = useState<string | null>(null);
  useEffect(() => {
    let off = false;
    void (async () => {
      try {
        const cur = await getOnepager(aid);
        if (cur.status === 'done') { if (!off) setData(cur); return; }
        const r = await startOnepager(aid);
        if (!off) setJob(r.job_id);
      } catch (e) { if (!off) setErr(errText(e)); }
    })();
    return () => { off = true; };
  }, [aid]);
  useJob(job, { onDone: async (j) => {
    if (j.status !== 'succeeded') { setErr(j.error?.message || '한 장 요약을 만들지 못했어요'); return; }
    try { setData(await getOnepager(aid)); } catch (e) { setErr(errText(e)); }
  } });
  const fj = useJob(fileJob, { onDone: (j) => {
    setFileJob(null);
    const fid = (j.result as { file_id?: string } | null)?.file_id;
    if (j.status === 'succeeded' && fid) window.open(fileUrl(fid), '_blank', 'noopener,noreferrer');
    else toast(j.error?.message || '파일을 만들지 못했어요');
  } });
  const q = data?.quadrants ?? {};
  const label = (k: string) => AREA_NAME[k as Area] ?? k;
  const text = data ? [...Object.entries(q).map(([k, v]) => `${label(k)}: ${v}`), `결론: ${data.conclusion}`].join('\n') : '';
  return (
    <Modal open onClose={onClose} title="한 장 요약 · IM-B" width={720} footer={
      <div className="mi-row" style={{ justifyContent: 'flex-end', gap: 8 }}>
        <SecButton onClick={() => void copyText(text).then((ok) => toast(ok ? '요약을 복사했어요' : '복사하지 못했어요'))} disabled={!data}>복사</SecButton>
        <BigButton arrow={false} disabled={!data} busy={!!fileJob && !fj.done}
          onClick={() => void startExport(aid, 'pptx_onepager').then((r) => setFileJob(r.job_id)).catch((e) => toast(errText(e)))}>PPTX로 받기</BigButton>
      </div>}>
      {err && <ErrorBand message={err} />}
      {!data && !err && <div className="mi-wait"><Spin size={16} />분석 결과로 한 장 요약을 만드는 중</div>}
      {data && (
        <div className="mi-onepager" data-testid="mi3-onepager">
          {Object.entries(q).map(([k, v]) => <div key={k}><b>{label(k)}</b>{v}</div>)}
          <div className="mi-onepager__end"><b>결론</b>{data.conclusion}</div>
        </div>
      )}
    </Modal>
  );
}

function VersionsSheet({ aid, onClose }: { aid: string; onClose: () => void }) {
  const v = useVersions(aid);
  return (
    <Modal open onClose={onClose} title="지난 결과" width={520}>
      {!v.data && <div className="mi-wait"><Spin size={16} /></div>}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {(v.data?.items ?? []).map((x) => (
          <div key={x.n} className="mi-row" style={{ justifyContent: 'space-between', padding: '8px 4px', borderBottom: '1px solid var(--wm-line-soft)' }}>
            <span className="mi-ell"><b className="mi-num">v{x.n}</b> · {x.created_at.slice(0, 10)} · {x.summary}{x.current ? ' · 지금' : ''}</span>
            <Link to={`/mi/${aid}/result?version=${x.n}`} className="mi-mini" onClick={onClose}>열기</Link>
          </div>
        ))}
      </div>
    </Modal>
  );
}
