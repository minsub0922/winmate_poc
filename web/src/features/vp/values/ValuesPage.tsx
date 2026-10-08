/**
 * VP · 가치 · 고객의 니즈(보드 webapp1 VP2 · VP2_AI · VP2_Pick · VP2_Detail · VP_Done) — `/vp/values/:id`
 * 왼쪽 고른 제품 · 솔루션(280) | 오른쪽 선택한 것의 가치 카드 여러 장. 가치마다 고객의 니즈(직접 · AI 추론, 점선 → 수락).
 * 값은 보드 px 그대로(values.css). 본문 열은 셸 규칙(최대 1180 가운데) · 높이는 화면을 채우고 패널 안에서 스크롤.
 */
import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router';
import { useShellPage } from '@/shell/ShellContext';
import {
  AiBar, AiButton, ByTag, ErrorState, FlowDone, FlowFooter, FlowHead, FlowPanel, FlowScreen, KindTag, LinkedStoryboardBar, ProductPickerDialog, Skeleton, cx, toast,
  type ByKind, type PickItem,
} from '@/ui';
import { useValueMap, useVmActions, type VMDoc, type VMItem, type VMStageOut, type VMValue } from './api';
import { VpDetailDialog } from './VpDetailDialog';
import './values.css';

const SECTION = 'Value Proposition';
const STEPS = ['Storyboard', '가치 · 고객의 니즈'];

function NeedRow({ v, onSave, onInfer, onAccept, inferring }: {
  v: VMValue; onSave: (t: string) => void; onInfer: () => void; onAccept: () => void; inferring: boolean;
}) {
  const [draft, setDraft] = useState('');
  const need = v.need;
  const pendingValue = v.by === 'ai-pending';
  return (
    <div className="vv-need">
      <span className="vv-need__label">고객의 니즈</span>
      {need && (need.by !== 'ai-pending' || pendingValue) && (
        <>
          <span className="vv-need__text">“{need.text}”</span>
          <ByTag by={need.by === 'manual' ? 'manual' : pendingValue ? 'ai-pending' : 'ai-accepted'} label={need.by === 'manual' ? '직접' : pendingValue ? 'AI 추론' : 'AI 추론 · 수락'} />
        </>
      )}
      {need && need.by === 'ai-pending' && !pendingValue && (
        <>
          <span className="vv-need__text vv-need__text--pend">“{need.text}”</span>
          <ByTag by="ai-pending" label="AI 추론" />
          <button type="button" className="vv-mini vv-mini--primary" onClick={onAccept}>수락</button>
        </>
      )}
      {!need && (
        <>
          <label className="wm-sr" htmlFor={`need-${v.id}`}>고객의 니즈</label>
          <input id={`need-${v.id}`} className="vv-need__input" value={draft} onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter' && draft.trim()) { onSave(draft.trim()); setDraft(''); } }}
            onBlur={() => { if (draft.trim()) { onSave(draft.trim()); setDraft(''); } }}
            placeholder="고객이 할 말처럼 적어요 · 예: 여름에도 쾌적한 교실 환경이 필요해요" disabled={pendingValue} />
          {!pendingValue && <AiButton size={30} onClick={onInfer} busy={inferring}>AI 니즈 추론</AiButton>}
        </>
      )}
    </div>
  );
}

function ValueCard({ v, actions, inferringId, setInferring }: { v: VMValue; actions: ReturnType<typeof useVmActions>; inferringId: string | null; setInferring: (id: string | null) => void }) {
  const [edit, setEdit] = useState(false);
  const [msg, setMsg] = useState(v.message);
  const [space, setSpace] = useState(v.space);
  const [req, setReq] = useState(v.req ?? '');
  const pend = v.by === 'ai-pending';
  const by = (v.by as ByKind) ?? 'manual';
  const infer = async () => {
    setInferring(v.id);
    try {
      const r = await actions.inferNeed(v.id);
      if (!r.need) toast(r.reason ?? 'AI 로 니즈를 추론하지 못했어요. 직접 적어 주세요.');
    } catch { toast('AI 니즈 추론에 실패했어요. 잠시 후 다시 시도해 주세요.'); } finally { setInferring(null); }
  };
  if (edit) {
    return (
      <div className="vv-card vv-card--edit">
        <div className="vv-editrow">
          <label className="vv-editlab">공간<input className="vv-in" value={space} onChange={(e) => setSpace(e.target.value)} /></label>
          <label className="vv-editlab">연결 요구<input className="vv-in" value={req} onChange={(e) => setReq(e.target.value)} placeholder="예: RQ-01 에너지 20% 절감" /></label>
        </div>
        <label className="vv-editlab vv-editlab--full">가치 메시지<input className="vv-in vv-in--strong" value={msg} onChange={(e) => setMsg(e.target.value)} /></label>
        <div className="vv-editbtns">
          <button type="button" className="vv-mini vv-mini--danger" onClick={async () => { await actions.deleteValue(v.id); }}>지우기</button>
          <span style={{ flex: 1 }} />
          <button type="button" className="vv-mini" onClick={() => { setEdit(false); setMsg(v.message); }}>취소</button>
          <button type="button" className="vv-mini vv-mini--primary" disabled={!msg.trim()}
            onClick={async () => { await actions.patchValue(v.id, { message: msg, space, req }); setEdit(false); }}>저장</button>
        </div>
      </div>
    );
  }
  return (
    <div className={cx('vv-card', pend && 'vv-card--pend')} data-value={v.id}>
      <div className="vv-card__top">
        <span className="vv-space">{v.space}</span>
        <ByTag by={by} />
        <span style={{ flex: 1 }} />
        {v.req && <span className="vv-req">{v.req}</span>}
        {pend ? (
          <>
            <button type="button" className="vv-mini vv-mini--primary" onClick={() => actions.patchValue(v.id, { accept: true })}>수락</button>
            <button type="button" className="vv-mini vv-mini--ghost" onClick={() => actions.deleteValue(v.id)}>빼기</button>
          </>
        ) : <button type="button" className="vv-mini vv-mini--link" onClick={() => setEdit(true)}>고치기</button>}
      </div>
      <span className={cx('vv-msg', pend && 'vv-msg--pend')}>{v.message}</span>
      {v.basis && pend && <span className="vv-basis">근거 · {v.basis}</span>}
      <NeedRow v={v} inferring={inferringId === v.id} onInfer={infer}
        onSave={(t) => actions.patchValue(v.id, { need: t })} onAccept={() => actions.patchValue(v.id, { accept_need: true })} />
    </div>
  );
}

function AddCard({ item, actions, onDone }: { item: VMItem; actions: ReturnType<typeof useVmActions>; onDone: () => void }) {
  const [space, setSpace] = useState(item.spaces?.[0] ?? '전체');
  const [msg, setMsg] = useState('');
  const [need, setNeed] = useState('');
  const [req, setReq] = useState('');
  return (
    <div className="vv-card vv-card--edit" data-add-value="">
      <div className="vv-editrow">
        <label className="vv-editlab">공간<input className="vv-in" value={space} onChange={(e) => setSpace(e.target.value)} /></label>
        <label className="vv-editlab">연결 요구<input className="vv-in" value={req} onChange={(e) => setReq(e.target.value)} placeholder="예: RQ-01 에너지 20% 절감" /></label>
      </div>
      <label className="vv-editlab vv-editlab--full">가치 메시지<input className="vv-in vv-in--strong" value={msg} onChange={(e) => setMsg(e.target.value)} placeholder="고객에게 주는 가치 한 문장" autoFocus /></label>
      <label className="vv-editlab vv-editlab--full">고객의 니즈<input className="vv-in" value={need} onChange={(e) => setNeed(e.target.value)} placeholder="예: 여름에도 쾌적한 교실 환경이 필요해요 (비워 두고 AI 니즈 추론도 돼요)" /></label>
      <div className="vv-editbtns">
        <span style={{ flex: 1 }} />
        <button type="button" className="vv-mini" onClick={onDone}>취소</button>
        <button type="button" className="vv-mini vv-mini--primary" disabled={!msg.trim()}
          onClick={async () => { await actions.addValue(item.key, { space: space || '전체', message: msg.trim(), need: need.trim() || null, req: req.trim() || null }); onDone(); }}>추가</button>
      </div>
    </div>
  );
}

function Editor({ doc, onFinished }: { doc: VMDoc; onFinished: (s: VMStageOut) => void }) {
  const actions = useVmActions(doc.id);
  const [selKey, setSelKey] = useState<string | null>(doc.items[0]?.key ?? null);
  const [pop, setPop] = useState<'' | 'pick' | 'detail'>('');
  const [adding, setAdding] = useState(false);
  const [inferring, setInferring] = useState<string | null>(null);
  const [aiBusy, setAiBusy] = useState(false);
  const [saving, setSaving] = useState(false);
  const items = doc.items;
  const cur = items.find((i) => i.key === selKey) ?? items[0] ?? null;
  useEffect(() => { if (!cur && items[0]) setSelKey(items[0].key); }, [cur, items]);
  useEffect(() => { setAdding(false); }, [selKey]);

  const pendV = items.reduce((a, it) => a + it.values.filter((v) => v.by === 'ai-pending').length, 0);
  const pendN = items.reduce((a, it) => a + it.values.filter((v) => v.by !== 'ai-pending' && v.need?.by === 'ai-pending').length, 0);
  const c = doc.counts;
  const picked = items.map((i) => i.name);
  const groups = useMemo(() => {
    const cands = doc.candidates ?? [];
    const prods = cands.filter((x) => x.kind === 'product');
    const sols = cands.filter((x) => x.kind === 'solution');
    const g = [] as Array<{ label: string; items: PickItem[] }>;
    if (prods.length) g.push({ label: 'DSS · 제품', items: prods.map((x) => ({ name: x.name, kind: 'product', ref: x.ref, where: `DSS · ${(x.spaces ?? []).join(' · ') || '공간 미정'}` })) });
    if (sols.length) g.push({ label: 'DSS · 솔루션', items: sols.map((x) => ({ name: x.name, kind: 'solution', ref: x.ref, where: `DSS · ${(x.spaces ?? []).join(' · ') || '여러 공간'}` })) });
    return g;
  }, [doc.candidates]);

  const togglePick = async (it: PickItem) => {
    const has = picked.includes(it.name);
    const next = has ? items.filter((x) => x.name !== it.name).map((x) => ({ name: x.name, kind: x.kind, ref: x.ref, spaces: x.spaces }))
      : [...items.map((x) => ({ name: x.name, kind: x.kind, ref: x.ref, spaces: x.spaces })), { name: it.name, kind: it.kind, ref: it.ref ?? null, spaces: (doc.candidates ?? []).find((x) => x.name === it.name)?.spaces ?? [] }];
    if (!next.length) { toast('제품 · 솔루션을 하나 이상 골라 주세요.'); return; }
    await actions.setItems(next);
  };
  const runAi = async () => {
    setAiBusy(true);
    try {
      const r = await actions.suggest();
      if (!r.added_values && !r.added_needs) toast('더할 추천이 없어요. 이미 가치가 충분하거나 근거 메시지가 없어요.');
      else if (r.mode === 'kb_only') toast(`KB 원문 메시지로 가치 후보 ${r.added_values}개를 넣었어요 · 지금은 AI 니즈 추론을 쓸 수 없어요`);
    } catch { toast('AI 가치 매칭 추천에 실패했어요. 잠시 후 다시 시도해 주세요.'); } finally { setAiBusy(false); }
  };
  const save = async () => {
    setSaving(true);
    try { onFinished(await actions.finish()); } catch (e) { toast((e as Error).message || '저장하지 못했어요.'); } finally { setSaving(false); }
  };

  return (
    <FlowScreen pad="18px 40px" gap={12} className="vv-screen"
      bar={<LinkedStoryboardBar chips={doc.sb_id ? [{ id: doc.sb_id, name: doc.title, done: ['rq', 'dss'], current: 'vp' }] : []}
        note={doc.sb_id ? 'Storyboard를 그대로 가져왔어요 · 사전 작업 DSS 확인됨' : undefined} emptyText="연결된 Storyboard가 없어요 · 요구 문장으로 시작했어요" />}>
      <FlowHead title="제품 · 솔루션마다 가치와 고객의 니즈를 적어요"
        desc="가치 하나에 고객이 실제로 할 말 같은 니즈 하나 · 예: 학교 · 교실 · 에어컨 → “여름에도 쾌적한 교실 환경이 필요해요”"
        actions={<>
          <button type="button" className="vv-ghost38" onClick={() => setPop('pick')}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" aria-hidden><path d="M4 6h16M4 12h10M4 18h7" /></svg>
            제품 · 솔루션 고르기 · {items.length}
          </button>
          <AiButton onClick={runAi} busy={aiBusy}>AI 가치 매칭 추천</AiButton>
        </>} />
      {(pendV + pendN) > 0 && (
        <AiBar onAction={() => actions.acceptAll()}>Storyboard context(요구 · 공간 · MI)로 가치 {pendV}개와 니즈 {pendN}개를 추천했어요. 점선은 수락해야 들어가요.</AiBar>
      )}
      <div className="wm-flow__grid" style={{ gridTemplateColumns: '280px minmax(0, 1fr)' }}>
        <FlowPanel>
          <div className="vv-lhead"><span>고른 제품 · 솔루션 {items.length}</span><button type="button" className="vv-mini vv-mini--link" onClick={() => setPop('pick')}>고르기 · 바꾸기</button></div>
          <div className="vv-list">
            {items.map((it) => {
              const done = it.values.filter((v) => v.by !== 'ai-pending');
              const needs = done.filter((v) => v.need && v.need.by !== 'ai-pending').length;
              const pend = it.values.filter((v) => v.by === 'ai-pending' || v.need?.by === 'ai-pending').length;
              return (
                <button key={it.key} type="button" className={cx('vv-item', it.key === cur?.key && 'vv-item--on')} aria-pressed={it.key === cur?.key} onClick={() => setSelKey(it.key)}>
                  <KindTag kind={it.kind} />
                  <span className="vv-item__txt">
                    <span className="vv-item__name">{it.name}</span>
                    <span className={cx('vv-item__count', !done.length && 'vv-item__count--warn')}>{done.length ? `가치 ${done.length} · 니즈 ${needs}/${done.length}` : '가치 없음'}</span>
                  </span>
                  {pend > 0 && <span className="vv-item__pend">추천 {pend}</span>}
                </button>
              );
            })}
          </div>
        </FlowPanel>
        <FlowPanel>
          {cur ? (
            <>
              <div className="vv-rhead">
                <span className="vv-rhead__txt">
                  <span className="vv-rhead__title"><span className="vv-rhead__name">{cur.name}</span><KindTag kind={cur.kind} /></span>
                  <span className="vv-rhead__where">{doc.sb_id ? 'DSS 공간 · ' : '공간 · '}{(cur.spaces ?? []).join(' · ') || '정하지 않음'}{cur.from_dss ? '' : ' · DSS 밖에서 더함'}</span>
                </span>
                <button type="button" className="vv-ghost34" onClick={() => setPop('detail')}>연결된 가치 전체 보기<span className="vv-badge">이 제안 {cur.values.filter((v) => v.by !== 'ai-pending').length}</span></button>
              </div>
              <div className="vv-cards">
                {!cur.values.length && !adding && (
                  <div className="vv-empty"><b>아직 적은 가치가 없어요</b><span>아래에서 직접 적거나, 위의 AI 가치 매칭 추천으로 후보를 받아 보세요.</span></div>
                )}
                {cur.values.map((v) => <ValueCard key={v.id} v={v} actions={actions} inferringId={inferring} setInferring={setInferring} />)}
                {adding ? <AddCard item={cur} actions={actions} onDone={() => setAdding(false)} />
                  : <button type="button" className="vv-add" onClick={() => setAdding(true)}>+ 가치 추가 · 공간 · 가치 · 니즈 · 요구</button>}
              </div>
            </>
          ) : <div className="vv-empty" style={{ margin: 14 }}><b>제품 · 솔루션을 골라 주세요</b><span>위의 “제품 · 솔루션 고르기”에서 VP 에 넣을 것을 고르세요.</span></div>}
        </FlowPanel>
      </div>
      <FlowFooter back={{ to: '/vp', label: '목록' }} summary={`제품 · 솔루션 ${c.items} · 가치 ${c.values} · 니즈 ${c.needs}/${c.values}`}
        primary={{ label: '저장', onClick: save, busy: saving, disabled: c.values === 0 }} />
      <ProductPickerDialog open={pop === 'pick'} onClose={() => setPop('')} title="VP에 넣을 제품 · 솔루션 고르기" min={1}
        sub="DSS에서 고른 것 중 가치를 적을 것을 고르세요. DSS에 없는 제품 · 솔루션도 카탈로그에서 더할 수 있어요."
        groups={groups} picked={picked} onToggle={togglePick} />
      {cur && <VpDetailDialog open={pop === 'detail'} onClose={() => setPop('')} doc={doc} item={cur} onImport={(b) => actions.importValue(cur.key, b)} />}
    </FlowScreen>
  );
}

export function ValuesPage() {
  const { id = '' } = useParams();
  const q = useValueMap(id);
  const [done, setDone] = useState<VMStageOut | null>(null);
  const nav = useNavigate();
  useShellPage({ section: SECTION, title: q.data ? (q.data.code ? `${q.data.code} · ${q.data.title}` : q.data.title) : '새 VP', hasTask: !done, stepper: { steps: STEPS, current: 2, complete: !!done } });
  if (q.isError) return <div className="wm-page"><ErrorState message="가치 맵을 불러오지 못했어요" onRetry={() => q.refetch()} /></div>;
  if (!q.data) return <div className="wm-page"><Skeleton h={480} r={14} /></div>;
  if (done) {
    const c = q.data.counts;
    const d = q.data;
    return (
      <div className="wm-flow">
        <LinkedStoryboardBar chips={d.sb_id ? [{ id: d.sb_id, name: d.title, done: ['rq', 'dss', 'vp'], current: 'vp' }] : []} note="요약본이 방금 갱신됐어요"
          emptyText="연결된 Storyboard가 없어요" />
        <FlowDone title="가치 제안을 저장했어요" sub={`제품 · 솔루션 ${c.items}개의 가치 ${c.values}개와 고객의 니즈를 Storyboard에 담았어요`}
          sbName={d.sb_id ? d.title : null}
          stages={[['rq', '요구사항'], ['dss', 'DSS'], ['mi', 'MI'], ['ca', '경쟁사'], ['vp', 'VP'], ['sp', 'Spec'], ['sc', '시나리오'], ['ppt', '제안서']].map(([k, l]) => ({
            key: k, label: l, ref: k === 'vp' ? (d.code ?? d.id) : null, state: k === 'vp' ? 'cur' as const : (d.sb_id && (k === 'rq' || k === 'dss')) ? 'done' as const : 'none' as const }))}
          md={done.summary_md} stageKey="vp" stage={done.stage} onEdit={() => setDone(null)} onOpenStoryboard={() => nav('/storyboard')} />
      </div>
    );
  }
  return <Editor doc={q.data} onFinished={setDone} />;
}
