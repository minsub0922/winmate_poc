/**
 * VP · 가치 · 고객의 니즈 — `/vp/values/:id` 한 장(보드 webapp1 v63 View content=vp + VPBody · VP2 · VP_Draft · VP2_AI · VP2_Edit · VP_View).
 * 새로 만들기 · 작성 중 · 저장됨 · 고치는 중 모두 같은 화면이다(ContentDetail). 칸은 그 자리에서 바로 고치고(글은 떠날 때 · 고르기는 누르는 즉시 저장),
 * 저장하면 그 자리에서 「저장됨」으로 바뀐다(완료 화면 없음). 저장한 뒤 고친 칸은 cd-in--chg(머리 「고친 곳 n · 되돌리기」는 서버 changes).
 *
 * 본문(VPBody 1100): 흰 띠 48(「DSS-01에서 n개를 골랐어요 · 고르지 않은 k — …」 · 제품 · 솔루션 고르기 · n · AI 가치 매칭 추천)
 *   → 점선 일괄 줄(PendingBar · AI 추천이 있을 때) → 흰 패널 하나(안에서만 스크롤)에 제품 · 솔루션마다 줄: 그리드 200px | 1fr ·
 *   왼쪽 종류 · 이름 · 공간 · 「가치 n · 니즈 m/n」(없으면 주황 「가치 없음」) · 연결된 가치 전체 보기 → (VpDetail 팝업),
 *   오른쪽 가치 칸(공간 칩 · 가치 메시지 · 연결 요구 칩 · 점선이면 수락 / 고객의 니즈 칸 · 직접 | AI 추론 · 수락 · 점선이면 수락 · 비면 AI 니즈 추론) · + 가치 추가.
 * 팝업은 보드에 [팝업]으로 적힌 것만: 제품 · 솔루션 고르기(ProdPicker 760×640) · 연결된 가치 전체(VpDetail 900×720).
 * Storyboard 의 DSS 가 바뀌었으면(보드에 없음) 본문 맨 위 안내 줄 하나(AiBar · 「다시 가져오기」) — 그 줄만큼(38 + 12) 패널만 줄고 칸 폭은 그대로.
 */
import { useMemo, useRef, useState, type FocusEvent } from 'react';
import { useParams } from 'react-router';
import { AiButton, ContentDetail, InlineInput, PendingBar, useFlow } from '@/shell';
import { useShellPage } from '@/shell/ShellContext';
import { AiBar, ErrorState, KindTag, ProductPickerDialog, Skeleton, cx, toast, type PickItem } from '@/ui';
import { dssChangeText, resyncToast, useValueMap, useVmActions, type VMDoc, type VMItem, type VMValue } from './api';
import { ChipSelect } from './ChipSelect';
import { VpDetailDialog } from './VpDetailDialog';
import './values.css';

type Actions = ReturnType<typeof useVmActions>;
type Field = 'msg' | 'need' | 'space' | 'req';
/** 화면에 그리는 가치 하나 — 저장된 것(id) 또는 아직 서버에 없는 새 가치(id null · 가치 메시지를 쓰면 만든다) */
interface Val { id: string | null; space: string; message: string; need: { text: string; by: string } | null; req: string | null; by: string }
interface Draft { key: string; space: string; req: string; need: string; posting: boolean; before: Set<string> }

const NEED_PH = '고객이 할 말처럼 적어요 · 예) 여름에도 쾌적한 교실 환경이 필요해요';
const failText = (e: unknown, fb: string) => (e as Error)?.message || fb;

/** 고친 칸 표시(화면 상태 — 저장 · 되돌리기 하면 지운다). 저장한 적이 있고 서버가 고친 곳이 있다고 할 때만 보인다 */
interface Chg { show: boolean; has: (k: string) => boolean; mark: (k: string) => void }

function ValueBlock({ v, chg, opts, act, onDraft, onDraftMsg, onDraftCancel }: {
  v: Val;
  chg: Chg;
  opts: { space: Array<{ value: string }>; req: Array<{ value: string; label?: string }> };
  act: Actions;
  /** 새 가치(아직 서버에 없음)일 때만 */
  onDraft?: (p: Partial<Pick<Draft, 'space' | 'req' | 'need'>>) => void;
  onDraftMsg?: (t: string) => void;
  onDraftCancel?: () => void;
}) {
  const id = v.id;
  const draft = id == null;
  const pend = v.by === 'ai-pending';
  const need = v.need;
  const needPend = !pend && need?.by === 'ai-pending';
  const hasTag = !!need && !pend && !needPend;
  const canInfer = !need && !pend;
  const [msgN, setMsgN] = useState(0);
  const [inferring, setInferring] = useState(false);
  const on = (f: Field) => chg.show && !!id && chg.has(`${id}:${f}`);
  const run = (p: Promise<unknown>, f?: Field) => p.then(() => { if (f && id) chg.mark(`${id}:${f}`); }).catch((e) => toast(failText(e, '저장하지 못했어요')));

  const setSpace = (s: string) => (draft ? onDraft?.({ space: s }) : run(act.patchValue(id, { space: s }), 'space'));
  const setReq = (r: string) => (draft ? onDraft?.({ req: r }) : run(act.patchValue(id, { req: r }), 'req'));
  const setMsg = (t: string) => {
    if (draft) { if (t) onDraftMsg?.(t); return; }
    if (!t) { toast('가치 메시지는 비울 수 없어요 · 가치를 빼려면 오른쪽 위 ×'); setMsgN((n) => n + 1); return; }
    return run(act.patchValue(id, { message: t }), 'msg');
  };
  const setNeed = (t: string) => (draft ? onDraft?.({ need: t }) : run(act.patchValue(id, { need: t }), 'need'));
  const accept = () => id && run(act.patchValue(id, { accept: true }).then(() => { chg.mark(`${id}:msg`); if (need) chg.mark(`${id}:need`); }));
  const acceptNeed = () => id && run(act.patchValue(id, { accept_need: true }), 'need');
  const remove = () => (draft ? onDraftCancel?.() : run(act.deleteValue(id!)));
  const infer = async () => {
    if (!id || inferring) return;
    setInferring(true);
    try {
      const r = await act.inferNeed(id);
      if (!r.need) toast(r.reason ?? 'AI로 니즈를 추론하지 못했어요. 직접 적어 주세요.');
    } catch { toast('AI 니즈 추론에 실패했어요. 잠시 후 다시 시도해 주세요.'); } finally { setInferring(false); }
  };
  // 새 가치: 아무것도 쓰지 않고 칸을 벗어나면 지운다(고르기 목록은 body 에 떠 있어 그리로 가는 것은 벗어난 게 아니다)
  const leave = (e: FocusEvent<HTMLDivElement>) => {
    if (!draft) return;
    const to = e.relatedTarget as Node | null;
    if (to && (e.currentTarget.contains(to) || (to as Element).closest?.('.vb-pop'))) return;
    const el = e.currentTarget;
    const empty = [...el.querySelectorAll('input')].every((i) => !i.value.trim());
    if (empty) onDraftCancel?.();
  };
  const needCls = on('need') ? 'vb-need--chg' : needPend ? 'vb-need--pend' : need ? 'vb-need--has' : 'vb-need--empty';
  return (
    <div className={cx('vb-val', pend && 'vb-val--pend', draft && 'vb-val--new')} data-value={id ?? 'new'} onBlur={leave}>
      <span className="vb-line">
        <ChipSelect label="공간" tone="space" value={v.space} placeholder="공간" options={opts.space} onPick={setSpace} changed={on('space')}
          custom="공간 직접 쓰기 · Enter" />
        <InlineInput key={`m${msgN}`} label="가치 메시지" value={v.message} onCommit={setMsg} maxLength={200} changed={on('msg')}
          className="vb-msg" placeholder={draft ? '고객에게 주는 가치 한 문장 · 쓰고 나면 바로 저장돼요' : undefined} />
        <ChipSelect label="연결 요구" tone="req" value={v.req} placeholder="연결 요구" options={opts.req} onPick={setReq} changed={on('req')}
          custom="직접 쓰기 · 예) RQ-01 에너지 20% 절감" />
        {pend && <button type="button" className="cd-ok vb-ok" onClick={accept}>수락</button>}
      </span>
      <span className="vb-line">
        <span className="vb-needlab">고객의 니즈</span>
        <InlineInput label="고객의 니즈" value={need?.text ?? ''} onCommit={setNeed} maxLength={200} placeholder={NEED_PH} changed={on('need')}
          className={cx('vb-need', needCls)} />
        {hasTag && <span className={cx('cd-tag', need!.by === 'manual' ? 'cd-tag--man' : 'cd-tag--ai')}>{need!.by === 'manual' ? '직접' : 'AI 추론 · 수락'}</span>}
        {needPend && <button type="button" className="cd-ok vb-ok" onClick={acceptNeed}>수락</button>}
        {canInfer && <AiButton size={28} onClick={infer} busy={inferring} disabled={draft}>AI 니즈 추론</AiButton>}
      </span>
      <button type="button" className="cd-x vb-x" onClick={remove} aria-label={draft ? '새 가치 취소' : pend ? `추천 빼기 · ${v.message}` : `가치 지우기 · ${v.message}`}>
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.8" strokeLinecap="round" aria-hidden><path d="M6 6l12 12M18 6L6 18" /></svg>
      </button>
    </div>
  );
}

function ItemRow({ it, first, chg, spaceOpts, reqOpts, act, onDetail, dssRef }: {
  it: VMItem; first: boolean; chg: Chg; spaceOpts: Array<{ value: string }>; reqOpts: Array<{ value: string; label?: string }>;
  act: Actions; onDetail: () => void; dssRef: string | null;
}) {
  const [draft, setDraft] = useState<Draft | null>(null);
  const keys = useRef(new Map<string, string>());
  const lateNeed = useRef<string | null>(null);
  const real = it.values.filter((v) => v.by !== 'ai-pending');
  const needs = real.filter((v) => v.need && v.need.by !== 'ai-pending').length;
  // 새 가치가 서버에 생기면 같은 key 로 이어 그린다(칸 · 커서가 그대로 남게)
  const born = draft?.posting ? it.values.find((v) => !draft.before.has(v.id)) : undefined;
  if (born && draft && !keys.current.has(born.id)) keys.current.set(born.id, draft.key);
  const where = (it.spaces ?? []).join(' · ') || '전체';

  const add = () => {
    if (draft) { (document.querySelector(`[data-item="${CSS.escape(it.key)}"] [data-value="new"] input`) as HTMLInputElement | null)?.focus(); return; }
    setDraft({ key: `new-${Date.now()}`, space: (it.spaces ?? [])[0] ?? '전체', req: '', need: '', posting: false, before: new Set(it.values.map((v) => v.id)) });
    requestAnimationFrame(() => (document.querySelector(`[data-item="${CSS.escape(it.key)}"] [data-value="new"] input`) as HTMLInputElement | null)?.focus());
  };
  const postDraft = async (msg: string) => {
    if (!draft || draft.posting) return;
    const d = { ...draft, posting: true, before: new Set(it.values.map((v) => v.id)) };
    setDraft(d);
    try {
      const doc = await act.addValue(it.key, { space: d.space || '전체', message: msg, need: d.need || null, req: d.req || null });
      const nv = doc.items.find((x) => x.key === it.key)?.values.find((v) => !d.before.has(v.id));
      if (nv) {
        keys.current.set(nv.id, d.key);
        chg.mark(`${nv.id}:msg`);
        if (d.need) chg.mark(`${nv.id}:need`);
        if (lateNeed.current != null) {
          const t = lateNeed.current;
          lateNeed.current = null;
          act.patchValue(nv.id, { need: t }).then(() => chg.mark(`${nv.id}:need`)).catch((e) => toast(failText(e, '니즈를 저장하지 못했어요')));
        }
      }
      setDraft(null);
    } catch (e) {
      toast(failText(e, '가치를 더하지 못했어요'));
      setDraft((x) => x && { ...x, posting: false });
    }
  };
  const draftVal: Val | null = draft && !born ? { id: null, space: draft.space, message: '', need: draft.need ? { text: draft.need, by: 'manual' } : null, req: draft.req || null, by: 'manual' } : null;
  const nAll = it.values.length + (draftVal ? 1 : 0);
  const block = (v: VMValue) => (
    <ValueBlock key={keys.current.get(v.id) ?? v.id} v={{ id: v.id, space: v.space, message: v.message, need: v.need ?? null, req: v.req ?? null, by: v.by ?? 'manual' }}
      chg={chg} opts={{ space: withCur(spaceOpts, v.space), req: reqOpts }} act={act} />
  );
  return (
    <div className={cx('vb-row', first && 'vb-row--first', chg.show && chg.has(`item:${it.key}`) && 'cd-chgrow')} role="group" aria-label={it.name} data-item={it.key}>
      <span className="vb-left">
        <KindTag kind={it.kind} />
        <span className="vb-name">{it.name}</span>
        <span className="vb-where">{where}
          {it.dss_status === 'removed' && <em className="vb-gone"> · DSS에서 빠짐</em>}
          {!it.from_dss && it.dss_status !== 'removed' && dssRef && <em className="vb-outside"> · DSS 밖에서 더함</em>}</span>
        <span className={cx('vb-count', !real.length && 'vb-count--none')}>{real.length ? `가치 ${real.length} · 니즈 ${needs}/${real.length}` : '가치 없음'}</span>
        <button type="button" className="vb-detail" onClick={onDetail}>연결된 가치 전체 보기 →</button>
      </span>
      <span className="vb-right">
        {/* 새 가치 칸과 서버에 생긴 가치가 같은 목록 · 같은 key 라 칸(커서)이 그대로 이어진다 */}
        {[...it.values.map(block), draftVal && draft ? (
          <ValueBlock key={draft.key} v={draftVal} chg={chg} opts={{ space: withCur(spaceOpts, draft.space), req: reqOpts }} act={act}
            onDraft={(p) => { if (draft.posting && p.need != null) { lateNeed.current = p.need; return; } setDraft((x) => x && { ...x, ...p }); }}
            onDraftMsg={(t) => void postDraft(t)} onDraftCancel={() => { if (!draft.posting) setDraft(null); }} />
        ) : null]}
        <button type="button" className="vb-add" onClick={add}>{nAll ? '+ 가치 추가' : '+ 가치 추가 · 공간 · 가치 · 니즈 · 요구 — 또는 위의 AI 가치 매칭 추천'}</button>
      </span>
    </div>
  );
}

function withCur(opts: Array<{ value: string }>, cur: string) {
  return cur && !opts.some((o) => o.value === cur) ? [...opts, { value: cur }] : opts;
}

function Detail({ doc }: { doc: VMDoc }) {
  const act = useVmActions(doc.id);
  const flow = useFlow(doc.sb_id ?? null);
  const [pop, setPop] = useState<'' | 'pick' | 'detail'>('');
  const [detailKey, setDetailKey] = useState<string | null>(null);
  const [aiBusy, setAiBusy] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [marks, setMarks] = useState<Set<string>>(() => new Set());
  const saved = !!doc.ver || doc.status === 'done';
  const changes = doc.changes ?? 0;
  const chg: Chg = {
    show: saved && changes > 0,
    has: (k) => marks.has(k),
    mark: (k) => { if (saved) setMarks((s) => (s.has(k) ? s : new Set(s).add(k))); },
  };
  const c = doc.counts;
  const items = doc.items;
  const dssRef = doc.dss_ref ?? null;
  const cands = doc.candidates ?? [];
  const candKeys = new Set(cands.map((x) => x.name));
  const chosen = new Set(items.map((x) => x.name));
  const excluded = cands.filter((x) => !chosen.has(x.name)).map((x) => x.name);
  const nFromDss = items.filter((x) => candKeys.has(x.name)).length;
  const outside = items.filter((x) => !candKeys.has(x.name) && x.dss_status !== 'removed').map((x) => x.name);
  const dropped = items.filter((x) => x.dss_status === 'removed').map((x) => x.name);
  const pendV = items.reduce((a, it) => a + it.values.filter((v) => v.by === 'ai-pending').length, 0);
  const pendN = items.reduce((a, it) => a + it.values.filter((v) => v.by !== 'ai-pending' && v.need?.by === 'ai-pending').length, 0);

  const fromLine = cands.length ? `${dssRef ?? 'DSS'}에서 ${nFromDss}개를 골랐어요` : `제품 · 솔루션 ${items.length}개를 골랐어요`;
  const outLine = [
    cands.length ? (excluded.length ? `고르지 않은 ${excluded.length} — ${excluded.join(' · ')}` : '고르지 않은 것 없음') : '',
    outside.length ? `DSS 밖에서 더함 ${outside.length} — ${outside.join(' · ')}` : '',
    dropped.length ? `DSS에서 빠짐 ${dropped.length} — ${dropped.join(' · ')}` : '',
  ].filter(Boolean).join(' · ');

  // 공간 칩: 그 제품의 공간 + 전체(솔루션 · 공간 없는 제품은 이 맵의 모든 공간)
  const allSpaces = useMemo(() => {
    const s: string[] = [];
    for (const x of [...cands, ...items]) for (const sp of x.spaces ?? []) if (!s.includes(sp)) s.push(sp);
    return s;
  }, [cands, items]);
  const spaceOptsOf = (it: VMItem) => [...new Set([...((it.spaces ?? []).length ? it.spaces : allSpaces), '전체'])].map((value) => ({ value }));
  // 연결 요구 칩: Storyboard 의 고객 요구사항(목표 · 요구) + 이 맵에서 쓴 요구 · 없음
  const reqOpts = useMemo(() => {
    const rq = ((flow.data?.stages ?? {}) as Record<string, unknown>).rq as { ref?: string; goals?: string[]; requirements?: Array<{ text?: string }> } | null | undefined;
    const ref = rq?.ref ?? 'RQ';
    const out: string[] = [];
    const push = (t?: string | null) => { const s = (t ?? '').trim(); if (s && !out.includes(s)) out.push(s); };
    for (const g of rq?.goals ?? []) push(`${ref} ${g}`);
    for (const r of rq?.requirements ?? []) push(r.text ? `${ref} ${r.text}` : null);
    for (const it of items) for (const v of it.values) push(v.req);
    return [...out.map((value) => ({ value })), { value: '', label: '연결 요구 없음' }];
  }, [flow.data, items]);

  const groups = useMemo(() => {
    const ref = dssRef ?? 'DSS';
    const fresh = (x: (typeof cands)[number]) => (x.dss_status === 'added' ? ' · 새로' : '');
    const prods = cands.filter((x) => x.kind === 'product');
    const sols = cands.filter((x) => x.kind === 'solution');
    const g = [] as Array<{ label: string; items: PickItem[] }>;
    if (prods.length) g.push({ label: `${ref} · 제품`, items: prods.map((x) => ({ name: x.name, kind: 'product', ref: x.ref, where: `${ref} · ${(x.spaces ?? []).join(' · ') || '공간 미정'}${fresh(x)}` })) });
    if (sols.length) g.push({ label: `${ref} · 솔루션`, items: sols.map((x) => ({ name: x.name, kind: 'solution', ref: x.ref, where: `${ref} · ${(x.spaces ?? []).join(' · ') || '공간 전체'}${fresh(x)}` })) });
    return g;
  }, [cands, dssRef]);
  const togglePick = async (it: PickItem) => {
    const has = chosen.has(it.name);
    const cur = items.map((x) => ({ name: x.name, kind: x.kind, ref: x.ref, spaces: x.spaces }));
    const next = has ? cur.filter((x) => x.name !== it.name)
      : [...cur, { name: it.name, kind: it.kind, ref: it.ref ?? null, spaces: cands.find((x) => x.name === it.name)?.spaces ?? [] }];
    if (!next.length) { toast('제품 · 솔루션을 하나 이상 골라 주세요.'); return; }
    try {
      const d = await act.setItems(next);
      if (!has) { const k = d.items.find((x) => x.name === it.name)?.key; if (k) chg.mark(`item:${k}`); }
    } catch (e) { toast(failText(e, '고르지 못했어요')); }
  };

  const runAi = async () => {
    setAiBusy(true);
    try {
      const r = await act.suggest();
      if (!r.added_values && !r.added_needs) toast('더할 추천이 없어요. 이미 가치가 충분하거나 근거 메시지가 없어요.');
      else if (r.mode === 'kb_only') toast(`KB 원문 메시지로 가치 후보 ${r.added_values}개를 넣었어요 · 지금은 AI 니즈 추론을 쓸 수 없어요`);
    } catch { toast('AI 가치 매칭 추천에 실패했어요. 잠시 후 다시 시도해 주세요.'); } finally { setAiBusy(false); }
  };
  const resync = async () => {
    if (syncing) return;
    setSyncing(true);
    try { toast(resyncToast((await act.resync()).last_resync)); } catch (e) { toast(failText(e, 'DSS를 다시 가져오지 못했어요.')); } finally { setSyncing(false); }
  };
  const save = async () => {
    const out = await act.finish();
    setMarks(new Set());
    return out;
  };
  const revert = async () => { await act.revert(); setMarks(new Set()); };
  const detailItem = items.find((x) => x.key === detailKey) ?? null;
  const facts = saved ? [`제품 · 솔루션 ${c.items}`, `가치 ${c.values}`, `고객의 니즈 ${c.needs}/${c.values}`] : [`가치 ${c.values}`, `니즈 ${c.needs}/${c.values}`];

  return (
    <ContentDetail content="vp" saved={saved} changes={changes} empty={c.values === 0 && c.pending === 0}
      title={doc.title} refCode={doc.code} ver={doc.ver} savedAt={doc.saved_at} updatedAt={doc.updated_at} facts={facts}
      sbIds={doc.sb_id ? [doc.sb_id] : []} onSave={save} onRevert={revert}
      savedToast={(o) => {
        const out = o as Awaited<ReturnType<Actions['finish']>>;
        const d = out.doc;
        return [`${d.code ?? 'VP'} v${d.ver ?? 1} 저장`, out.flow_sync?.synced?.length ? `연결된 Storyboard ${out.flow_sync.synced.length + 1}개에 반영했어요` : d.sb_id ? `${d.sb_id}에 반영했어요` : '',
          pendV + pendN ? `점선 추천 ${pendV + pendN}개는 빼고 저장했어요` : ''].filter(Boolean).join(' · ');
      }}>
      <div className="vb">
        {doc.dss_changed && (
          <AiBar actionLabel={syncing ? '가져오는 중…' : '다시 가져오기'} onAction={resync}>
            <span data-testid="vv-dss-changed" title={(doc.dss_changed.added_names ?? []).map((n) => `+ ${n}`).concat((doc.dss_changed.removed_names ?? []).map((n) => `− ${n}`)).join('\n') || undefined}>
              {dssChangeText(doc.dss_changed)}</span>
          </AiBar>
        )}
        <div className="cd-strip vb-strip">
          <span className="vb-from">{fromLine}</span>
          <span className="vb-out" title={outLine}>{outLine ? `· ${outLine}` : ''}</span>
          <button type="button" className="vb-pick" onClick={() => setPop('pick')}>
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" aria-hidden><path d="M4 6h16 M4 12h10 M4 18h6" /></svg>
            제품 · 솔루션 고르기 · {items.length}
          </button>
          <AiButton size={36} onClick={runAi} busy={aiBusy}>AI 가치 매칭 추천</AiButton>
        </div>
        <PendingBar count={pendV + pendN} text={`AI 추천 ${pendV + pendN}개 — 가치 후보와 빈 니즈 추론이 점선으로 들어왔어요 · 수락해야 들어가요`}
          onClearAll={() => act.clearPending().catch((e) => toast(failText(e, '지우지 못했어요')))}
          onAcceptAll={() => act.acceptAll().then(() => {
            if (!saved) return;
            for (const it of items) for (const v of it.values) {
              if (v.by === 'ai-pending') { chg.mark(`${v.id}:msg`); if (v.need) chg.mark(`${v.id}:need`); } else if (v.need?.by === 'ai-pending') chg.mark(`${v.id}:need`);
            }
          }).catch((e) => toast(failText(e, '수락하지 못했어요')))} />
        <div className="vb-panel">
          {items.map((it, i) => (
            <ItemRow key={it.key} it={it} first={i === 0} chg={chg} spaceOpts={spaceOptsOf(it)} reqOpts={reqOpts} act={act} dssRef={dssRef}
              onDetail={() => { setDetailKey(it.key); setPop('detail'); }} />
          ))}
          {!items.length && (
            <div className="vb-empty"><b>제품 · 솔루션을 골라 주세요</b><span>위의 「제품 · 솔루션 고르기」에서 VP에 넣을 것을 고르세요.</span></div>
          )}
        </div>
      </div>
      <ProductPickerDialog open={pop === 'pick'} onClose={() => setPop('')} title="VP에 넣을 제품 · 솔루션 고르기" min={1}
        sub={`${dssRef ?? 'DSS'}에서 고른 것 중 가치를 적을 것을 고르세요. DSS에 없는 제품 · 솔루션도 카탈로그에서 더할 수 있어요.`}
        groups={groups} picked={items.map((x) => x.name)} onToggle={togglePick} />
      {detailItem && <VpDetailDialog open={pop === 'detail'} onClose={() => setPop('')} doc={doc} item={detailItem}
        onImport={async (b) => {
          const before = new Set(detailItem.values.map((v) => v.id));
          const d = await act.importValue(detailItem.key, b);
          for (const v of d.items.find((x) => x.key === detailItem.key)?.values ?? []) if (!before.has(v.id)) { chg.mark(`${v.id}:msg`); if (v.need) chg.mark(`${v.id}:need`); }
        }} />}
    </ContentDetail>
  );
}

function Loading({ error, onRetry }: { error?: boolean; onRetry?: () => void }) {
  useShellPage({ section: 'Value Proposition', title: '', hasTask: false });
  return <div className="wm-page">{error ? <ErrorState message="가치 맵을 불러오지 못했어요" onRetry={onRetry} /> : <Skeleton h={480} r={14} />}</div>;
}

export function ValuesPage() {
  const { id = '' } = useParams();
  const q = useValueMap(id);
  if (q.isError) return <Loading error onRetry={() => q.refetch()} />;
  if (!q.data) return <Loading />;
  return <Detail key={q.data.id} doc={q.data} />;
}
