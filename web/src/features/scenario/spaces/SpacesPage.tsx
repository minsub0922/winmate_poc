/**
 * 공간 시나리오 · 공간 → 시나리오 → 장면(보드 webapp1 SC2 · SC2_AI · SC2_Pick · SC2_Empty · SC_Done) — `/scenario/spaces/:id`
 * 공간(196) | [공간 헤더 · 공간 제품 · 솔루션(하나 이상)] + [시나리오 목록(236) | 시나리오 편집]. 입력 폼은 고정하지 않는다(단계 수 · 항목 자유).
 * 고칠 때마다 자동 저장(PUT, 낙관적 잠금). 제품 · 솔루션이 빈 공간 · 시나리오가 있으면 저장 버튼이 막힌다.
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { useShellPage } from '@/shell/ShellContext';
import { AiButton, ErrorState, FlowDone, FlowFooter, FlowPanel, FlowScreen, LinkedStoryboardBar, ProductPickerDialog, Skeleton, cx, toast, type PickItem } from '@/ui';
import { acceptCandidate, dropCandidate, finishSpaceSet, putSpaceSet, ssKey, suggestScenarios, useSpaceSet, type SSCandidate, type SSDoc, type SSScenario, type SSSpace, type SSStageOut } from './api';
import './spaces.css';

const SECTION = '공간 시나리오 생성';
const STEPS = ['Storyboard', '공간 · 시나리오'];
const FIELD_PRESETS = ['시간대', '기대 효과', '연결 요구', '페인 포인트', '직접 이름 짓기'];
const PRESET_KEYS = FIELD_PRESETS.slice(0, 4);
let seq = 0;

/** 고르기 묶음: 이 공간 · 다른 공간에 있는 제품 · 솔루션(DSS 묶음) — 빼도 다시 넣을 수 있게 */
function pickGroups(spaces: SSSpace[], sp: SSSpace) {
  const here = sp.products.map((p) => ({ name: p.name, kind: (p.kind ?? 'product') as 'product' | 'solution', ref: p.ref, where: sp.name }));
  const seen = new Set(here.map((x) => x.name));
  const other: typeof here = [];
  for (const s of spaces) {
    if (s.id === sp.id) continue;
    for (const p of s.products) {
      if (seen.has(p.name)) continue;
      seen.add(p.name);
      other.push({ name: p.name, kind: (p.kind ?? 'product') as 'product' | 'solution', ref: p.ref, where: `다른 공간 · ${s.name}` });
    }
  }
  return [...(here.length ? [{ label: '이 공간', items: here }] : []), ...(other.length ? [{ label: '다른 공간의 제품 · 솔루션', items: other }] : [])];
}
const tmpId = () => `scn_new_${Date.now().toString(36)}${(seq++).toString(36)}`;

function byLabel(by: string | null | undefined): [string, string] {
  if (!by || by === 'manual') return ['직접', 'wm-bytag--manual'];
  if (by === 'ai-pending') return ['AI 후보', 'wm-bytag--ai-pending'];
  return [`AI ${by.slice(-1)}안 · 수락`, 'wm-bytag--ai-accepted'];
}

function Editor({ doc, onFinished }: { doc: SSDoc; onFinished: (s: SSStageOut) => void }) {
  const qc = useQueryClient();
  const [spaces, setSpaces] = useState<SSSpace[]>(doc.spaces);
  const [version, setVersion] = useState(doc.version);
  const [issues, setIssues] = useState(doc.issues);
  const [spId, setSpId] = useState(doc.spaces[0]?.id ?? '');
  const [cur, setCur] = useState<Record<string, string | null>>({});
  const [pick, setPick] = useState(false);
  const [aiBusy, setAiBusy] = useState(false);
  const [saving, setSaving] = useState(false);
  const timer = useRef<number | null>(null);
  const pending = useRef<SSSpace[] | null>(null);
  const verRef = useRef(version);
  verRef.current = version;

  const apply = useCallback((d: SSDoc, replace = true) => {
    if (replace) setSpaces(d.spaces);
    setVersion(d.version); setIssues(d.issues);
    qc.setQueryData(ssKey(d.id), d);
  }, [qc]);

  const flush = useCallback(async () => {
    const body = pending.current;
    if (!body) return;
    pending.current = null;
    try { apply(await putSpaceSet(doc.id, body, verRef.current), false); } catch (e) {
      toast((e as Error).message || '저장하지 못했어요.');
      qc.invalidateQueries({ queryKey: ssKey(doc.id) });
    }
  }, [apply, doc.id, qc]);

  const edit = (next: SSSpace[]) => {
    setSpaces(next);
    pending.current = next;
    if (timer.current) window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => { void flush(); }, 600);
  };
  useEffect(() => () => { if (timer.current) window.clearTimeout(timer.current); void flush(); }, [flush]);

  const sp = spaces.find((s) => s.id === spId) ?? spaces[0];
  const spNames = sp ? sp.products.map((p) => p.name) : [];
  const list: Array<SSScenario | SSCandidate> = sp ? [...sp.scenarios, ...sp.candidates] : [];
  const curKey = sp && list.some((x) => x.id === cur[sp.id]) ? cur[sp.id] : list[0]?.id ?? null;
  const sel = list.find((x) => x.id === curKey) ?? null;
  const candSel = sel && sp?.candidates.find((c) => c.id === sel.id) || null;
  const isCand = !!candSel;
  const setSp = (patch: Partial<SSSpace>) => edit(spaces.map((s) => (s.id === sp!.id ? { ...s, ...patch } : s)));
  const setSc = (patch: Partial<SSScenario>) => {
    if (!sp || !sel) return;
    // 보드 SC2_AI: 점선 후보도 수락 전에 고칠 수 있다(서버는 같은 id · cid 의 고친 내용만 받는다)
    if (isCand) setSp({ candidates: sp.candidates.map((x) => (x.id === sel.id ? { ...x, ...patch } : x)) });
    else setSp({ scenarios: sp.scenarios.map((x) => (x.id === sel.id ? { ...x, ...patch } : x)) });
  };
  const noProd = spaces.filter((s) => !s.products.length).length;
  const totalSc = spaces.reduce((a, s) => a + s.scenarios.length, 0);

  const togglePick = (it: PickItem) => {
    if (!sp) return;
    const has = spNames.includes(it.name);
    setSp({ products: has ? sp.products.filter((p) => p.name !== it.name) : [...sp.products, { name: it.name, kind: it.kind, ref: it.ref ?? null }] });
  };
  const runAi = async () => {
    if (!sp) return;
    await flush();
    setAiBusy(true);
    try {
      const r = await suggestScenarios(doc.id, sp.id);
      apply(r.set);
      const first = r.set.spaces.find((s) => s.id === sp.id)?.candidates[0];
      if (first) setCur((c) => ({ ...c, [sp.id]: first.id }));
      if (r.mode === 'kb_only') toast('지금은 AI 를 쓸 수 없어 KB 도입사례를 참고한 틀만 넣었어요 · [확인 필요] 를 채워 주세요');
    } catch (e) { toast((e as Error).message || 'AI 시나리오 3안을 만들지 못했어요.'); } finally { setAiBusy(false); }
  };
  const addScenario = () => {
    if (!sp) return;
    const sc: SSScenario = { id: tmpId(), title: '', user: '', products: spNames.slice(), steps: [{ text: '', product: null }], fields: [], by: 'manual', basis: null };
    setSp({ scenarios: [...sp.scenarios, sc] });
    setCur((c) => ({ ...c, [sp.id]: sc.id }));
  };
  const save = async () => {
    setSaving(true);
    try { await flush(); onFinished(await finishSpaceSet(doc.id)); } catch (e) { toast((e as Error).message || '저장하지 못했어요.'); } finally { setSaving(false); }
  };

  const fieldsHave = sel ? sel.fields.map((f) => f.k) : [];
  return (
    <FlowScreen pad="16px 32px" gap={12}
      bar={<LinkedStoryboardBar chips={doc.sb_id ? [{ id: doc.sb_id, name: doc.title, done: ['rq', 'dss'], current: 'sc' }] : []}
        note={doc.sb_id ? 'Storyboard를 그대로 가져왔어요 · 사전 작업 DSS 확인됨' : undefined} emptyText="연결된 Storyboard가 없어요 · 요구 문장으로 시작했어요" />}>
      <div className="ss-head">
        <h1 className="ss-h1">공간마다 시나리오를 여러 개 써요</h1>
        <span className="ss-hint">공간 → 시나리오 → 장면 · 공간과 시나리오마다 제품 · 솔루션을 골라요</span>
      </div>
      <div className="wm-flow__grid" style={{ gridTemplateColumns: '196px minmax(0, 1fr)', gap: 12 }}>
        <FlowPanel className="ss-spaces" role="tablist" aria-orientation="vertical" aria-label="공간">
          <span className="ss-spaces__h">공간 · DSS</span>
          {spaces.map((s) => {
            const n = s.scenarios.length;
            const pn = s.products.length;
            return (
              <button key={s.id} type="button" role="tab" aria-selected={s.id === sp?.id} className={cx('ss-sp', s.id === sp?.id && 'ss-sp--on')} onClick={() => setSpId(s.id)}>
                <span className="ss-sp__top"><span className="ss-sp__name">{s.name}</span>{!pn && <span className="ss-sp__warn" aria-label="제품 · 솔루션 없음" />}</span>
                <span className={cx('ss-sp__sub', !pn && 'ss-sp__sub--warn', pn && !n && 'ss-sp__sub--empty')}>{pn ? `시나리오 ${n} · 제품 ${pn}` : '제품 · 솔루션 없음'}</span>
              </button>
            );
          })}
        </FlowPanel>
        {sp && (
          <div className="ss-right">
            <div className={cx('ss-sphead', !spNames.length && 'ss-sphead--warn')}>
              <div className="ss-sphead__row">
                <span className="ss-sphead__name">{sp.name}</span>
                <span className="ss-sphead__note">공간 제품 · 솔루션 · 하나 이상</span>
                <AiButton size={34} onClick={runAi} busy={aiBusy} disabled={!spNames.length} title={!spNames.length ? '제품 · 솔루션을 먼저 넣어 주세요' : undefined}>AI 시나리오 3안</AiButton>
              </div>
              <div className="ss-chips">
                {sp.products.map((p) => (
                  <span key={p.name} className="ss-pchip"><span className={cx('ss-pchip__kind', p.kind === 'solution' && 'ss-pchip__kind--sol')}>{p.kind === 'solution' ? '솔루션' : '제품'}</span>{p.name}
                    <button type="button" className="ss-x" aria-label={`${p.name} 빼기`} onClick={() => setSp({ products: sp.products.filter((x) => x.name !== p.name) })}>
                      <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round"><path d="M6 6l12 12M18 6L6 18" /></svg></button></span>
                ))}
                <button type="button" className="ss-dash" onClick={() => setPick(true)}>+ 추가 · 변경</button>
                {!spNames.length && <span className="ss-warnpill">공간마다 제품 · 솔루션이 하나 이상 있어야 해요</span>}
              </div>
            </div>
            <div className="ss-grid2">
              <FlowPanel>
                <div className="ss-lhead"><span>시나리오 {sp.scenarios.length}</span>{!!sp.candidates.length && <small>점선은 AI 후보</small>}</div>
                <div className="ss-list">
                  {!list.length && <span className="ss-none">아직 시나리오가 없어요. 직접 추가하거나 AI 3안을 받아 보세요.</span>}
                  {list.map((x) => {
                    const cand = sp.candidates.some((c) => c.id === x.id);
                    const [t, cls] = byLabel(cand ? 'ai-pending' : x.by);
                    const prods = x.products.filter((p) => spNames.includes(p));
                    return (
                      <button key={x.id} type="button" aria-pressed={x.id === curKey} className={cx('ss-sc', cand && 'ss-sc--cand', x.id === curKey && 'ss-sc--on')}
                        onClick={() => setCur((c) => ({ ...c, [sp.id]: x.id }))}>
                        <span className="ss-sc__top"><span className="ss-sc__title">{x.title || '새 시나리오'}</span><span className={cx('wm-bytag', cls)}>{t}</span></span>
                        <span className="ss-sc__who">{x.user || '사용자 미정'}</span>
                        <span className="ss-sc__meta">제품 {prods.length} · 단계 {x.steps.length}</span>
                      </button>
                    );
                  })}
                </div>
                <div className="ss-lfoot"><button type="button" className="ss-dash ss-dash--block" onClick={addScenario}>+ 시나리오 추가</button></div>
              </FlowPanel>
              <FlowPanel className={cx('ss-ed', isCand && 'ss-ed--cand')} dashed={isCand}>
                {!sel && <div className="ss-edempty"><b>{sp.name} 시나리오를 시작해요</b><span>왼쪽 아래 “+ 시나리오 추가” 또는 위의 AI 3안</span></div>}
                {sel && (
                  <>
                    {candSel && (
                      <div className="wm-aibar" role="status"><span style={{ flex: 1 }}>AI 후보 {candSel.cid}안이에요 · 수락해야 시나리오로 들어가요{candSel.basis ? ` · ${candSel.basis}` : ''}</span>
                        <button type="button" className="wm-aibar__btn" onClick={async () => { apply(await acceptCandidate(doc.id, sp.id, candSel.cid)); }}>수락</button>
                        <button type="button" className="ss-ghostbtn" onClick={async () => { apply(await dropCandidate(doc.id, sp.id, candSel.cid)); setCur((c) => ({ ...c, [sp.id]: null })); }}>빼기</button></div>
                    )}
                    <div className="ss-row">
                      <label className="wm-sr" htmlFor="ss-title">시나리오 이름</label>
                      <input id="ss-title" className="ss-in ss-in--title" value={sel.title} onChange={(e) => setSc({ title: e.target.value })} placeholder="시나리오 이름 · 예: 예약 방문객의 첫 5분" />
                      <span className={cx('wm-bytag', byLabel(isCand ? 'ai-pending' : sel.by)[1])}>{byLabel(isCand ? 'ai-pending' : sel.by)[0]}</span>
                      {!isCand && <button type="button" className="ss-ghostbtn" onClick={() => { setSp({ scenarios: sp.scenarios.filter((x) => x.id !== sel.id) }); setCur((c) => ({ ...c, [sp.id]: null })); }}>지우기</button>}
                    </div>
                    <div className="ss-row"><label className="ss-lab" htmlFor="ss-who">사용자</label>
                      <input id="ss-who" className="ss-in" value={sel.user} onChange={(e) => setSc({ user: e.target.value })} placeholder="누구의 장면인가요?" /></div>
                    <div className="ss-row ss-row--top"><span className="ss-lab ss-lab--chips">제품 · 솔루션</span>
                      <span className="ss-chips">
                        {spNames.map((n) => {
                          const on = sel.products.includes(n);
                          return <button key={n} type="button" role="checkbox" aria-checked={on} className={cx('ss-tchip', on && 'ss-tchip--on')}
                            onClick={() => setSc({ products: on ? sel.products.filter((x) => x !== n) : [...sel.products, n], steps: on ? sel.steps.map((st) => (st.product === n ? { ...st, product: null } : st)) : sel.steps })}>{n}</button>;
                        })}
                        <button type="button" className="ss-dash ss-dash--sm" onClick={() => setPick(true)}>+ 공간에 더하기</button>
                        {!sel.products.filter((p) => spNames.includes(p)).length && <span className="ss-warntext">하나 이상 골라 주세요</span>}
                      </span></div>
                    <div className="ss-flowh"><b>장면 흐름</b><span>단계 수 · 항목은 자유 · 단계마다 쓰인 제품을 눌러 바꿔요</span></div>
                    {sel.steps.map((st, i) => {
                      const opts = [null, ...sel.products.filter((p) => spNames.includes(p))];
                      const nextP = opts[(opts.indexOf(st.product ?? null) + 1) % opts.length];
                      return (
                        <div key={i} className="ss-row">
                          <span className="ss-num">{i + 1}</span>
                          <label className="wm-sr" htmlFor={`ss-step-${i}`}>{i + 1}단계 장면</label>
                          <input id={`ss-step-${i}`} className="ss-in" value={st.text} placeholder="장면을 적어요"
                            onChange={(e) => setSc({ steps: sel.steps.map((x, j) => (j === i ? { ...x, text: e.target.value } : x)) })} />
                          <button type="button" className={cx('ss-ptag', st.product && 'ss-ptag--on')}
                            onClick={() => setSc({ steps: sel.steps.map((x, j) => (j === i ? { ...x, product: nextP } : x)) })}>{st.product || '+ 쓰인 제품'}</button>
                          {<button type="button" className="ss-x ss-x--26" aria-label={`${i + 1}단계 빼기`} onClick={() => setSc({ steps: sel.steps.filter((_, j) => j !== i) })}>
                            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round"><path d="M6 6l12 12M18 6L6 18" /></svg></button>}
                        </div>
                      );
                    })}
                    {<button type="button" className="ss-dash ss-dash--sm ss-addstep" onClick={() => setSc({ steps: [...sel.steps, { text: '', product: null }] })}>+ 단계 추가</button>}
                    {sel.fields.map((f, i) => (
                      <div key={i} className="ss-row">
                        {PRESET_KEYS.includes(f.k) ? <label className="ss-lab" htmlFor={`ss-f-${i}`}>{f.k}</label>
                          : <input className="ss-in ss-in--lab" aria-label="항목 이름" value={f.k} maxLength={30}
                            onChange={(e) => setSc({ fields: sel.fields.map((x, j) => (j === i ? { ...x, k: e.target.value || '항목' } : x)) })} />}
                        <input id={`ss-f-${i}`} className="ss-in" value={f.v ?? ''} placeholder={`${f.k} 적기`}
                          onChange={(e) => setSc({ fields: sel.fields.map((x, j) => (j === i ? { ...x, v: e.target.value } : x)) })} />
                        {<button type="button" className="ss-x ss-x--26" aria-label={`${f.k} 빼기`} onClick={() => setSc({ fields: sel.fields.filter((_, j) => j !== i) })}>
                          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round"><path d="M6 6l12 12M18 6L6 18" /></svg></button>}
                      </div>
                    ))}
                    {(
                      <div className="ss-addf"><span>항목 추가</span>
                        {FIELD_PRESETS.filter((t) => t === '직접 이름 짓기' || !fieldsHave.includes(t)).map((t) => (
                          <button key={t} type="button" className="ss-fchip" onClick={() => {
                            const k = t === '직접 이름 짓기' ? '새 항목' : t;
                            setSc({ fields: [...sel.fields, { k, v: '' }] });
                          }}>+ {t}</button>
                        ))}
                      </div>
                    )}
                  </>
                )}
              </FlowPanel>
            </div>
          </div>
        )}
      </div>
      <FlowFooter back={{ to: '/scenario', label: '목록' }}
        summary={`공간 ${spaces.length} · 시나리오 ${totalSc}${noProd ? ` · 제품 · 솔루션 없는 공간 ${noProd}` : ''}`} summaryTone={noProd ? 'warn' : undefined}
        primary={{ label: '저장', onClick: save, busy: saving, disabled: !!issues.length || !!noProd }} />
      {sp && <ProductPickerDialog open={pick} onClose={() => setPick(false)} title={`${sp.name} · 제품 · 솔루션 고르기`} min={1}
        sub="공간에 쓸 제품 · 솔루션을 고르세요. 하나 이상 있어야 하고, 고른 것 중에서 시나리오마다 다시 골라요."
        groups={pickGroups(spaces, sp)}
        picked={spNames} onToggle={togglePick} />}
    </FlowScreen>
  );
}

export function SpacesPage() {
  const { id = '' } = useParams();
  const q = useSpaceSet(id);
  const nav = useNavigate();
  const [done, setDone] = useState<SSStageOut | null>(null);
  useShellPage({ section: SECTION, title: q.data ? (q.data.code ? `${q.data.code} · ${q.data.title}` : q.data.title) : '새 공간 시나리오', hasTask: !done,
    stepper: { steps: STEPS, current: 2, complete: !!done } });
  if (q.isError) return <div className="wm-page"><ErrorState message="공간 시나리오를 불러오지 못했어요" onRetry={() => q.refetch()} /></div>;
  if (!q.data) return <div className="wm-page"><Skeleton h={480} r={14} /></div>;
  const d = q.data;
  if (done) {
    const c = d.counts;
    return (
      <div className="wm-flow">
        <LinkedStoryboardBar chips={d.sb_id ? [{ id: d.sb_id, name: d.title, done: ['rq', 'dss', 'sc'], current: 'sc' }] : []} note="요약본이 방금 갱신됐어요" emptyText="연결된 Storyboard가 없어요" />
        <FlowDone title="공간 시나리오를 저장했어요" sub={`공간 ${c.spaces}개 · 시나리오 ${c.scenarios}개를 Storyboard에 담았어요`} sbName={d.sb_id ? d.title : null}
          stages={[['rq', '요구사항'], ['dss', 'DSS'], ['mi', 'MI'], ['ca', '경쟁사'], ['vp', 'VP'], ['sp', 'Spec'], ['sc', '시나리오'], ['ppt', '제안서']].map(([k, l]) => ({
            key: k, label: l, ref: k === 'sc' ? (d.code ?? d.id) : null, state: k === 'sc' ? 'cur' as const : (d.sb_id && (k === 'rq' || k === 'dss')) ? 'done' as const : 'none' as const }))}
          md={done.summary_md} stageKey="sc" stage={done.stage} onEdit={() => setDone(null)} onOpenStoryboard={() => nav('/storyboard')} />
      </div>
    );
  }
  return <Editor key={d.id} doc={d} onFinished={setDone} />;
}
