/**
 * 공간 시나리오 · 공간 → 시나리오 → 장면(보드 webapp1 SC2 · SC2_AI · SC2_Pick · SC2_Empty · SC_Done · SC_DoneJson) — `/scenario/spaces/:id`
 * 위: 연결된 Storyboard 바(허브 FlowBar). 공간(196) | [공간 헤더 · 공간 제품 · 솔루션(하나 이상)] + [시나리오 목록(236) | 시나리오 편집].
 * 공간 · 공간 제품은 Gate 에서 고른 Storyboard 의 DSS 로 미리 채워진다. 입력 폼은 고정하지 않는다(단계 수 · 항목 자유).
 * 고칠 때마다 자동 저장(PUT, 낙관적 잠금 · 600ms). 제품 · 솔루션이 빈 공간이 있으면 저장 버튼이 막힌다(보드 canSave).
 * 저장 → 허브 stages.sc · 요약본 반영 → 완료(보드 Done: FlowDoneView · 전체 JSON).
 * Storyboard 의 DSS 가 바뀌었으면(보드에 없음) 머리 아래 안내 줄 하나(AiBar · 「다시 가져오기」) — 그 줄만큼 작업 그리드가 줄고 칸 폭은 그대로.
 * 다시 가져온 뒤 새로 놓인 제품 · 공간은 「새로」, 시나리오가 써서 남긴 빠진 제품 · 공간은 「DSS에서 빠짐」(주황).
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useParams } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { FlowBar, FlowDoneView, useFlowInvalidate, useShellPage } from '@/shell';
import { AiBar, AiButton, ErrorState, FlowFooter, FlowPanel, FlowScreen, LinkedStoryboardBar, ProductPickerDialog, Skeleton, cx, toast, type PickGroup, type PickItem } from '@/ui';
import {
  acceptCandidate, dropCandidate, dssChangeText, finishSpaceSet, putSpaceSet, resyncSpaceSet, resyncToast, ssKey, suggestScenarios, useSpaceSet,
  type SSCandidate, type SSDoc, type SSScenario, type SSSpace, type SSStageOut,
} from './api';
import { GATE_STEPS } from './FlowPages';
import './spaces.css';

const SECTION = '공간 시나리오 생성';
/** 보드 SC2 스텝바(완료 화면은 Gate META 문구 GATE_STEPS) */
const STEPS = ['Storyboard', '공간 · 시나리오'];
const FIELD_PRESETS = ['시간대', '기대 효과', '연결 요구', '페인 포인트', '직접 이름 짓기'];
const PRESET_KEYS = FIELD_PRESETS.slice(0, 4);
let seq = 0;
const tmpId = () => `scn_new_${Date.now().toString(36)}${(seq++).toString(36)}`;

const X = ({ s = 11, w = 2.6 }: { s?: number; w?: number }) => (
  <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={w} strokeLinecap="round" aria-hidden><path d="M6 6l12 12M18 6L6 18" /></svg>
);

/**
 * 고르기 묶음(보드 SC2_Pick): `DSS-01 · 제품`(있던 공간) · `DSS-01 · 솔루션` · `카탈로그 · DSS에 없는 것`(다른 공간에 더한 것).
 * DSS 없이 만든 묶음(이전 시작)은 이 공간 · 다른 공간의 제품 · 솔루션.
 */
function pickGroups(doc: SSDoc, spaces: SSSpace[], sp: SSSpace): PickGroup[] {
  const kindOf = (k: string | null | undefined) => (k === 'solution' ? 'solution' : 'product') as PickItem['kind'];
  if (doc.dss_items.length) {
    const ref = doc.dss_ref ?? 'DSS';
    const dss = new Set(doc.dss_items.map((i) => i.name));
    const where = (xs: string[]) => [ref, ...xs].join(' · ');
    const prods = doc.dss_items.filter((i) => i.kind !== 'solution').map((i) => ({ name: i.name, kind: 'product' as const, ref: i.ref, where: where(i.spaces) }));
    const sols = doc.dss_items.filter((i) => i.kind === 'solution').map((i) => ({ name: i.name, kind: 'solution' as const, ref: i.ref, where: where(i.spaces.length ? i.spaces : i.links) }));
    const seen = new Set<string>();
    const outside: PickItem[] = [];
    for (const s of spaces) {
      for (const p of s.products) {
        if (dss.has(p.name) || seen.has(p.name)) continue;
        seen.add(p.name);
        outside.push({ name: p.name, kind: kindOf(p.kind), ref: p.ref, where: p.ref ? '카탈로그 · DSS 밖' : '직접 추가 · KB 에 없음 · 확인 필요' });
      }
    }
    return [{ label: `${ref} · 제품`, items: prods }, { label: `${ref} · 솔루션`, items: sols }, { label: '카탈로그 · DSS에 없는 것', items: outside }].filter((g) => g.items.length);
  }
  const here = sp.products.map((p) => ({ name: p.name, kind: kindOf(p.kind), ref: p.ref, where: sp.name }));
  const seen = new Set(here.map((x) => x.name));
  const other: PickItem[] = [];
  for (const s of spaces) {
    if (s.id === sp.id) continue;
    for (const p of s.products) {
      if (seen.has(p.name)) continue;
      seen.add(p.name);
      other.push({ name: p.name, kind: kindOf(p.kind), ref: p.ref, where: `다른 공간 · ${s.name}` });
    }
  }
  return [...(here.length ? [{ label: '이 공간', items: here }] : []), ...(other.length ? [{ label: '다른 공간의 제품 · 솔루션', items: other }] : [])];
}

/** 출처 태그(보드 tagOf): 직접 · AI 후보(점선) · AI A안 · 수락(초록) */
function byTag(by: string | null | undefined): [string, string] {
  if (!by || by === 'manual') return ['직접', 'wm-bytag--manual'];
  if (by === 'ai-pending') return ['AI 후보', 'wm-bytag--ai-pending'];
  return [`AI ${by.slice(-1)}안 · 수락`, 'wm-bytag--ai-accepted'];
}
const Tag = ({ by }: { by: string | null | undefined }) => {
  const [t, cls] = byTag(by);
  return <span className={cx('wm-bytag ss-tag', cls)}>{t}</span>;
};

/** 저장을 막는 첫 시나리오(공간 제품 중 하나도 고르지 않음) — 보드는 저장 버튼을 막지 않으니 누르면 그곳으로 데려간다 */
function firstScenarioIssue(spaces: SSSpace[]) {
  for (const s of spaces) {
    const names = s.products.map((p) => p.name);
    if (!names.length) continue;
    for (const sc of s.scenarios) if (!sc.products.some((p) => names.includes(p))) return { sp: s, sc };
  }
  return null;
}

function Editor({ doc, onFinished }: { doc: SSDoc; onFinished: (s: SSStageOut) => void }) {
  const qc = useQueryClient();
  const invalFlow = useFlowInvalidate();
  const [spaces, setSpaces] = useState<SSSpace[]>(doc.spaces);
  const [spId, setSpId] = useState(doc.spaces[0]?.id ?? '');
  const [cur, setCur] = useState<Record<string, string | null>>({});
  const [pick, setPick] = useState(false);
  const [aiBusy, setAiBusy] = useState(false);
  const [saving, setSaving] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const timer = useRef<number | null>(null);
  const pending = useRef<SSSpace[] | null>(null);
  const verRef = useRef(doc.version);

  /** 응답 문서를 캐시에 — dss_changed 는 GET · 다시 가져오기 응답에만 계산돼 오므로 다른 응답에서는 앞의 값을 잇는다 */
  const apply = useCallback((d: SSDoc, replace = true, keepDss = true) => {
    if (replace) setSpaces(d.spaces);
    verRef.current = d.version;
    qc.setQueryData<SSDoc>(ssKey(d.id), (prev) => (keepDss ? { ...d, dss_changed: d.dss_changed ?? prev?.dss_changed ?? null } : d));
  }, [qc]);

  const flush = useCallback(async () => {
    if (timer.current) { window.clearTimeout(timer.current); timer.current = null; }
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
  useEffect(() => () => { void flush(); }, [flush]);

  const sp = spaces.find((s) => s.id === spId) ?? spaces[0];
  const spNames = sp ? sp.products.map((p) => p.name) : [];
  const list: Array<SSScenario | SSCandidate> = sp ? [...sp.scenarios, ...sp.candidates] : [];
  const curKey = sp && list.some((x) => x.id === cur[sp.id]) ? cur[sp.id] : list[0]?.id ?? null;
  const sel = list.find((x) => x.id === curKey) ?? null;
  const candSel = (sel && sp?.candidates.find((c) => c.id === sel.id)) || null;
  const isCand = !!candSel;
  const setSp = (patch: Partial<SSSpace>) => edit(spaces.map((s) => (s.id === sp!.id ? { ...s, ...patch } : s)));
  const setSc = (patch: Partial<SSScenario>) => {
    if (!sp || !sel) return;
    // 보드 SC2_AI: 점선 후보도 수락 전에 고칠 수 있다(서버는 같은 id · cid 의 고친 내용만 받는다)
    if (isCand) setSp({ candidates: sp.candidates.map((x) => (x.id === sel.id ? { ...x, ...patch } : x)) });
    else setSp({ scenarios: sp.scenarios.map((x) => (x.id === sel.id ? { ...x, ...patch } : x)) });
  };
  const removeScenario = (id: string) => {
    if (!sp) return;
    setSp({ scenarios: sp.scenarios.filter((x) => x.id !== id) });
    if (curKey === id) setCur((c) => ({ ...c, [sp.id]: null }));
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
  const onCandidate = async (cid: string, accept: boolean) => {
    if (!sp) return;
    await flush();
    try {
      apply(accept ? await acceptCandidate(doc.id, sp.id, cid) : await dropCandidate(doc.id, sp.id, cid));
      if (!accept) setCur((c) => ({ ...c, [sp.id]: null }));
    } catch (e) { toast((e as Error).message || '반영하지 못했어요.'); }
  };
  const addScenario = () => {
    if (!sp) return;
    const sc: SSScenario = { id: tmpId(), title: '', user: '', products: spNames.slice(), steps: [{ text: '', product: null }], fields: [], by: 'manual', basis: null };
    setSp({ scenarios: [...sp.scenarios, sc] });
    setCur((c) => ({ ...c, [sp.id]: sc.id }));
  };
  const resync = async () => {
    if (syncing) return;
    setSyncing(true);
    try {
      await flush();
      const d = await resyncSpaceSet(doc.id);
      apply(d, true, false);
      toast(resyncToast(d.last_resync));
    } catch (e) { toast((e as Error).message || 'DSS를 다시 가져오지 못했어요.'); } finally { setSyncing(false); }
  };
  const save = async () => {
    const bad = firstScenarioIssue(spaces);
    if (bad) {
      setSpId(bad.sp.id);
      setCur((c) => ({ ...c, [bad.sp.id]: bad.sc.id }));
      toast(`${bad.sp.name} · ${bad.sc.title || '새 시나리오'}에 쓰는 제품 · 솔루션을 하나 이상 골라 주세요.`);
      return;
    }
    setSaving(true);
    try {
      await flush();
      const out = await finishSpaceSet(doc.id);
      invalFlow();
      void qc.invalidateQueries({ queryKey: ['scenario', 'spacesets'] });
      void qc.invalidateQueries({ queryKey: ssKey(doc.id) });
      onFinished(out);
    } catch (e) { toast((e as Error).message || '저장하지 못했어요.'); } finally { setSaving(false); }
  };

  const fieldsHave = sel ? sel.fields.map((f) => f.k) : [];
  const selProds = sel ? sel.products.filter((p) => spNames.includes(p)) : [];
  return (
    <FlowScreen pad="16px 32px" gap={12} className="ss-screen"
      bar={doc.sb_id ? <FlowBar sbIds={[doc.sb_id]} current="sc" note="Storyboard를 그대로 가져왔어요 · 사전 작업 DSS 확인됨" />
        : <LinkedStoryboardBar chips={[]} emptyText="연결된 Storyboard가 없어요 · 요구 문장으로 시작했어요" />}>
      <div className="ss-head">
        <h1 className="ss-h1">공간마다 시나리오를 여러 개 써요</h1>
        <span className="ss-hint">공간 → 시나리오 → 장면 · 공간과 시나리오마다 제품 · 솔루션을 골라요</span>
      </div>
      {doc.dss_changed && (
        <AiBar actionLabel={syncing ? '가져오는 중…' : '다시 가져오기'} onAction={resync}>
          <span data-testid="ss-dss-changed" title={(doc.dss_changed.added_names ?? []).map((n) => `+ ${n}`).concat((doc.dss_changed.removed_names ?? []).map((n) => `− ${n}`)).join('\n') || undefined}>
            {dssChangeText(doc.dss_changed)}</span>
        </AiBar>
      )}
      <div className="wm-flow__grid ss-grid" style={{ gridTemplateColumns: '196px minmax(0, 1fr)', gap: 12 }}>
        <FlowPanel className="ss-spaces" role="tablist" aria-orientation="vertical" aria-label="공간">
          <span className="ss-spaces__h">공간 · {doc.dss_ref ?? 'DSS'}</span>
          {spaces.map((s) => {
            const n = s.scenarios.length;
            const pn = s.products.length;
            return (
              <button key={s.id} type="button" role="tab" aria-selected={s.id === sp?.id} className={cx('ss-sp', s.id === sp?.id && 'ss-sp--on')} onClick={() => setSpId(s.id)}>
                <span className="ss-sp__top"><span className="ss-sp__name">{s.name}</span>{!pn && <span className="ss-sp__warn" aria-label="제품 · 솔루션 없음" />}</span>
                {s.dss_status === 'removed'
                  ? <span className="ss-sp__sub ss-sp__sub--warn" title="DSS에서 빠졌지만 시나리오 · 제품이 있어 남겨 뒀어요">DSS에서 빠짐 · 시나리오 {n}</span>
                  : <span className={cx('ss-sp__sub', !pn && 'ss-sp__sub--warn', pn && !n && 'ss-sp__sub--empty')}>{pn ? `시나리오 ${n} · 제품 ${pn}` : '제품 · 솔루션 없음'}
                    {s.dss_status === 'added' && <em className="ss-flag ss-flag--new" title="DSS 다시 가져오기로 새로 생긴 공간"> · 새 공간</em>}</span>}
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
              <div className="ss-pchips">
                {sp.products.map((p) => (
                  <span key={p.name} className={cx('ss-pchip', p.dss_status === 'removed' && 'ss-pchip--gone')} data-dss={p.dss_status ?? undefined}
                    title={p.dss_status === 'removed' ? 'DSS에서 빠졌지만 이 공간의 시나리오가 써서 남겨 뒀어요 · 필요 없으면 빼 주세요' : p.dss_status === 'added' ? 'DSS 다시 가져오기로 새로 들어왔어요' : undefined}>
                    <span className={cx('ss-pchip__kind', p.kind === 'solution' && 'ss-pchip__kind--sol')}>{p.kind === 'solution' ? '솔루션' : '제품'}</span>{p.name}
                    {p.dss_status === 'removed' && <span className="ss-pchip__flag">DSS에서 빠짐</span>}{p.dss_status === 'added' && <span className="ss-pchip__flag ss-pchip__flag--new">새로</span>}
                    <button type="button" className="ss-x" aria-label={`${p.name} 빼기`} onClick={() => setSp({ products: sp.products.filter((x) => x.name !== p.name) })}><X s={10} w={3} /></button></span>
                ))}
                <button type="button" className="ss-dash" onClick={() => setPick(true)}>+ 추가 · 변경</button>
                {!spNames.length && <span className="ss-warnpill">공간마다 제품 · 솔루션이 하나 이상 있어야 해요</span>}
              </div>
            </div>
            <div className="ss-grid2">
              <FlowPanel className="ss-lpanel">
                <div className="ss-lhead"><span>시나리오 {sp.scenarios.length}</span>{!!sp.candidates.length && <small>점선은 AI 후보</small>}</div>
                <div className="ss-list">
                  {!list.length && <span className="ss-none">아직 시나리오가 없어요. 직접 추가하거나 AI 3안을 받아 보세요.</span>}
                  {list.map((x) => {
                    const cand = sp.candidates.some((c) => c.id === x.id);
                    const prods = x.products.filter((p) => spNames.includes(p));
                    return (
                      <div key={x.id} className="ss-scwrap">
                        <button type="button" aria-pressed={x.id === curKey} className={cx('ss-sc', cand && 'ss-sc--cand', x.id === curKey && 'ss-sc--on')}
                          onClick={() => setCur((c) => ({ ...c, [sp.id]: x.id }))}>
                          <span className="ss-sc__top"><span className="ss-sc__title">{x.title || '새 시나리오'}</span><Tag by={cand ? 'ai-pending' : x.by} /></span>
                          <span className="ss-sc__who">{x.user || '사용자 미정'}</span>
                          <span className="ss-sc__meta">제품 {prods.length} · 단계 {x.steps.length}</span>
                        </button>
                        {/* 보드에 없는 지우기 — 쉴 때는 보이지 않고 마우스 · 키보드가 머물 때만 */}
                        {!cand && <button type="button" className="ss-scdel" aria-label={`${x.title || '새 시나리오'} 지우기`} title="시나리오 지우기" onClick={() => removeScenario(x.id)}><X s={10} /></button>}
                      </div>
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
                      <div className="ss-aibar" role="status" title={candSel.basis ? `근거 · ${candSel.basis}` : undefined}>
                        <span className="ss-aibar__t">AI 후보 {candSel.cid}안이에요 · 수락해야 시나리오로 들어가요</span>
                        <button type="button" className="ss-aibar__ok" onClick={() => onCandidate(candSel.cid, true)}>수락</button>
                        <button type="button" className="ss-aibar__drop" onClick={() => onCandidate(candSel.cid, false)}>빼기</button>
                      </div>
                    )}
                    <div className="ss-row">
                      <label className="wm-sr" htmlFor="ss-title">시나리오 이름</label>
                      <input id="ss-title" className="ss-in ss-in--title" value={sel.title} onChange={(e) => setSc({ title: e.target.value })} placeholder="시나리오 이름 · 예: 예약 방문객의 첫 5분" />
                      <Tag by={isCand ? 'ai-pending' : sel.by} />
                    </div>
                    <div className="ss-row"><label className="ss-lab" htmlFor="ss-who">사용자</label>
                      <input id="ss-who" className="ss-in" value={sel.user} onChange={(e) => setSc({ user: e.target.value })} placeholder="누구의 장면인가요?" /></div>
                    <div className="ss-row ss-row--top"><span className="ss-lab ss-lab--chips">제품 · 솔루션</span>
                      <span className="ss-tchips">
                        {spNames.map((n) => {
                          const on = sel.products.includes(n);
                          return <button key={n} type="button" role="checkbox" aria-checked={on} className={cx('ss-tchip', on && 'ss-tchip--on')}
                            onClick={() => setSc({ products: on ? sel.products.filter((x) => x !== n) : [...sel.products, n], steps: on ? sel.steps.map((st) => (st.product === n ? { ...st, product: null } : st)) : sel.steps })}>{n}</button>;
                        })}
                        <button type="button" className="ss-dash ss-dash--sm" onClick={() => setPick(true)}>+ 공간에 더하기</button>
                        {!selProds.length && <span className="ss-warntext">하나 이상 골라 주세요</span>}
                      </span></div>
                    <div className="ss-flowh"><b>장면 흐름</b><span>단계 수 · 항목은 자유 · 단계마다 쓰인 제품을 눌러 바꿔요</span></div>
                    {sel.steps.map((st, i) => {
                      const opts = [null, ...selProds];
                      const nextP = opts[(opts.indexOf(st.product ?? null) + 1) % opts.length];
                      return (
                        <div key={i} className="ss-row">
                          <span className="ss-num">{i + 1}</span>
                          <label className="wm-sr" htmlFor={`ss-step-${i}`}>{i + 1}단계 장면</label>
                          <input id={`ss-step-${i}`} className="ss-in" value={st.text} placeholder="장면을 적어요"
                            onChange={(e) => setSc({ steps: sel.steps.map((x, j) => (j === i ? { ...x, text: e.target.value } : x)) })} />
                          <button type="button" className={cx('ss-ptag', st.product && 'ss-ptag--on')}
                            onClick={() => setSc({ steps: sel.steps.map((x, j) => (j === i ? { ...x, product: nextP } : x)) })}>{st.product || '+ 쓰인 제품'}</button>
                          <button type="button" className="ss-x ss-x--26" aria-label={`${i + 1}단계 빼기`} onClick={() => setSc({ steps: sel.steps.filter((_, j) => j !== i) })}><X /></button>
                        </div>
                      );
                    })}
                    <button type="button" className="ss-dash ss-addstep" onClick={() => setSc({ steps: [...sel.steps, { text: '', product: null }] })}>+ 단계 추가</button>
                    {sel.fields.map((f, i) => (
                      <div key={i} className="ss-row ss-frow">
                        {PRESET_KEYS.includes(f.k) ? <label className="ss-lab" htmlFor={`ss-f-${i}`}>{f.k}</label>
                          : <input className="ss-lab ss-labin" aria-label="항목 이름" value={f.k} maxLength={30} title="항목 이름 고치기"
                            onChange={(e) => setSc({ fields: sel.fields.map((x, j) => (j === i ? { ...x, k: e.target.value || '항목' } : x)) })} />}
                        <input id={`ss-f-${i}`} className="ss-in" value={f.v ?? ''} placeholder={`${f.k} 적기`}
                          onChange={(e) => setSc({ fields: sel.fields.map((x, j) => (j === i ? { ...x, v: e.target.value } : x)) })} />
                        {/* 보드에 없는 빼기 — 입력칸 오른쪽 끝에, 머물 때만 보인다 */}
                        <button type="button" className="ss-fdel" aria-label={`${f.k} 빼기`} title="항목 빼기" onClick={() => setSc({ fields: sel.fields.filter((_, j) => j !== i) })}><X s={10} /></button>
                      </div>
                    ))}
                    <div className="ss-addf"><span>항목 추가</span>
                      {FIELD_PRESETS.filter((t) => !fieldsHave.includes(t)).map((t) => (
                        <button key={t} type="button" className="ss-fchip" onClick={() => setSc({ fields: [...sel.fields, { k: t === '직접 이름 짓기' ? '새 항목' : t, v: '' }] })}>+ {t}</button>
                      ))}
                    </div>
                  </>
                )}
              </FlowPanel>
            </div>
          </div>
        )}
      </div>
      <FlowFooter back={doc.sb_id ? { to: `/storyboard/flow/${doc.sb_id}`, label: 'Storyboard' } : { to: '/scenario', label: '목록' }}
        summary={`공간 ${spaces.length} · 시나리오 ${totalSc}${noProd ? ` · 제품 · 솔루션 없는 공간 ${noProd}` : ''}`} summaryTone={noProd ? 'warn' : undefined}
        primary={{ label: '저장', onClick: save, busy: saving, disabled: !!noProd }} />
      {sp && <ProductPickerDialog open={pick} onClose={() => setPick(false)} title={`${sp.name} · 제품 · 솔루션 고르기`} min={1}
        sub="공간에 쓸 제품 · 솔루션을 고르세요. 하나 이상 있어야 하고, 고른 것 중에서 시나리오마다 다시 골라요."
        groups={pickGroups(doc, spaces, sp)} picked={spNames} onToggle={togglePick} />}
    </FlowScreen>
  );
}

/** 보드 Done(content=sc) — 후속 작업 없음 · 「Storyboard로」 */
function Done({ d, out, onEdit }: { d: SSDoc; out: SSStageOut; onEdit: () => void }) {
  const c = (out.stage as { counts?: { spaces?: number; scenarios?: number } }).counts ?? {};
  const synced = out.flow_sync?.synced ?? [];
  const sbId = d.sb_id ?? null;
  return (
    <FlowDoneView sbId={sbId} stageKey="sc" stage={out.stage} mdAdded={out.flow_sync?.md_added || out.summary_md}
      title="공간 시나리오를 저장했어요" sub={`공간 ${c.spaces ?? d.counts.spaces}개 · 시나리오 ${c.scenarios ?? d.counts.scenarios}개를 Storyboard에 담았어요`}
      note={synced.length ? `연결된 Storyboard ${synced.length + 1}개에 반영했어요` : '요약본이 방금 갱신됐어요'}
      onEdit={onEdit}
      follow={(
        <div className="ss-nofollow">
          <span>이 콘텐츠는 후속 작업이 없어요. Storyboard에서 다른 콘텐츠를 이어서 만들 수 있어요.</span>
          <Link to={sbId ? `/storyboard/flow/${sbId}` : '/storyboard'}>Storyboard로</Link>
        </div>
      )} />
  );
}

function Body({ id }: { id: string }) {
  const q = useSpaceSet(id);
  const [done, setDone] = useState<SSStageOut | null>(null);
  const d = q.data;
  // 보드 SC2 머리 「새 공간 시나리오」 · 저장한 뒤(완료 · 다시 고치기)는 코드(SC_Done 「SC-01」)
  const title = d && (done || d.ver) ? (d.code ?? d.title) : '새 공간 시나리오';
  useShellPage({ section: SECTION, title, hasTask: !done, stepper: done ? { steps: GATE_STEPS, current: 2, complete: true } : { steps: STEPS, current: 2 } });
  if (q.isError) return <div className="wm-page"><ErrorState message="공간 시나리오를 불러오지 못했어요 · 지워졌거나 주소가 바뀌었을 수 있어요" onRetry={() => q.refetch()} /></div>;
  if (!d) return <div className="wm-page"><Skeleton h={480} r={14} /></div>;
  if (done) return <Done d={d} out={done} onEdit={() => setDone(null)} />;
  return <Editor key={`${d.id}:${d.ver}`} doc={d} onFinished={setDone} />;
}

export function SpacesPage() {
  const { id = '' } = useParams();
  return <Body key={id} id={id} />;
}
