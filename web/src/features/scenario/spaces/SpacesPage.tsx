/**
 * 공간 시나리오 상세(웹앱 ① v63 · 보드 webapp1 SCBody · View content=sc) — `/scenario/spaces/:id` 한 장.
 * 래퍼 보드: SC2(새로 · DSS 공간 · 제품만) · SC_Draft(작성 중) · SC2_AI(AI 3안 점선 카드 · 수락) · SC2_Pick(공간 제품 · 솔루션 고르기 팝업) ·
 *   SC2_Empty(시나리오 없는 공간) · SC2_Edit(저장된 것을 그 자리에서 고치는 중 · 고친 곳 n) · SC_View(저장됨).
 * 셸 ContentDetail(SBBar · 머리 · 저장 · 고친 곳 n · 되돌리기 · flow.json · 고치다 나가면 묻기) + 본문 SCBody:
 *   공간 목록 220 | 고른 공간(머리: 이름 · 시나리오 n · AI 시나리오 3안 · 공간 제품 · 솔루션 칩 · + 추가 · 변경) + 시나리오 카드 2열(그 자리에서 고침) · + 시나리오 추가.
 * 칸은 바로 고친다: 글은 칸을 떠날 때(Enter) · 고르기 · 토글은 누르는 즉시 → 자동 저장(PUT · expected_version · 모아서 400ms).
 * 저장(:finish)하면 그 자리에서 저장됨으로(문서 다시 읽기 · 토스트). 저장 뒤 고친 칸은 cd-in--chg(화면 상태 — 저장 · 되돌리기 하면 지움).
 * 저장 막기(canSave): 제품 · 솔루션 없는 공간 · 제품을 고르지 않은 시나리오(API 422 SPACE_WITHOUT_PRODUCT · SCENARIO_WITHOUT_PRODUCT).
 * 보드에 없는 것: Storyboard 의 DSS 가 바뀌면 본문 위 안내 줄(AiBar · 「다시 가져오기」 — 그만큼 그리드만 줄고 칸 폭 그대로) · 새로 / DSS에서 빠짐 표시,
 *   장면 · 항목 빼기(× — 마우스 · 키보드가 머물 때만 보인다).
 */
import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react';
import { useParams } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { CONTENT, ContentDetail, InlineInput, useShellPage } from '@/shell';
import { AiBar, AiButton, ErrorState, ProductPickerDialog, Skeleton, cx, toast, type PickGroup, type PickItem } from '@/ui';
import {
  acceptCandidate, dropCandidate, dssChangeText, finishSpaceSet, getSpaceSet, putSpaceSet, resyncSpaceSet, resyncToast, revertSpaceSet,
  ssKey, ssListKey, suggestScenarios, useSpaceSet,
  type SSCandidate, type SSDoc, type SSScenario, type SSSpace, type SSStageOut, type SSStep,
} from './api';
import './spaces.css';

/** 보드 SCBody 「항목 추가」(있는 것은 빼고 4개까지) */
const MORE = ['시간대', '기대 효과', '연결 요구', '페인 포인트', '직접 이름 짓기'];
let seq = 0;
const tmpId = () => `scn_new_${Date.now().toString(36)}${(seq++).toString(36)}`;

const X = ({ s = 11, w = 2.6 }: { s?: number; w?: number }) => (
  <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={w} strokeLinecap="round" aria-hidden><path d="M6 6l12 12M18 6L6 18" /></svg>
);

/**
 * 고르기 묶음(보드 SC2_Pick · ProdPicker): `DSS-01 · 제품`(있던 공간) · `DSS-01 · 솔루션` · `카탈로그 · DSS에 없는 것`(다른 공간에 더한 것).
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

/** 출처 태그(보드 SCBody by): 직접 · AI A안 · 수락(초록) · AI B안(점선 후보) */
function byTag(by: string | null | undefined, cid?: string): [string, string] {
  if (cid) return [`AI ${cid}안`, 'ss-tag--pend'];
  const m = /^ai-candidate-([A-Z])$/.exec(by ?? '');
  if (m) return [`AI ${m[1]}안 · 수락`, 'ss-tag--ai'];
  if (by && by !== 'manual') return ['AI · 수락', 'ss-tag--ai'];
  return ['직접', 'ss-tag--man'];
}

/** 저장을 막는 첫 이유(보드 canSave · API 422) — 없으면 true */
function saveBlock(spaces: SSSpace[]): true | string {
  const bare = spaces.find((s) => !s.products.length);
  if (bare) return `${bare.name}에 제품 · 솔루션이 없어요 · 공간마다 하나 이상 있어야 저장돼요`;
  for (const s of spaces) {
    const names = s.products.map((p) => p.name);
    const sc = s.scenarios.find((x) => !x.products.some((p) => names.includes(p)));
    if (sc) return `${s.name} · ${sc.title || '새 시나리오'}에 쓰는 제품 · 솔루션을 하나 이상 골라 주세요`;
  }
  return true;
}

/** 장면에 쓰인 제품(보드 SCBody: 고른 제품 이름 또는 「+ 쓰인 제품」 · 누르면 시나리오 제품 목록) */
function StepProduct({ value, options, onPick, label }: { value: string | null | undefined; options: string[]; onPick: (v: string | null) => void; label: string }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLSpanElement>(null);
  useEffect(() => {
    if (!open) return undefined;
    const down = (e: MouseEvent) => { if (!ref.current?.contains(e.target as Node)) setOpen(false); };
    const key = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false); };
    document.addEventListener('mousedown', down);
    document.addEventListener('keydown', key);
    return () => { document.removeEventListener('mousedown', down); document.removeEventListener('keydown', key); };
  }, [open]);
  const pick = (v: string | null) => { onPick(v); setOpen(false); };
  return (
    <span className="ss-stepp" ref={ref}>
      <button type="button" className={cx('ss-pbtn', value && 'ss-pbtn--on')} aria-haspopup="listbox" aria-expanded={open} title={value ? `${label} · ${value}` : undefined}
        onClick={() => setOpen((o) => !o)}>{value || '+ 쓰인 제품'}</button>
      {open && (
        <span className="wm-menu ss-menu" role="listbox" aria-label={`${label} 쓰인 제품`}>
          {options.map((o) => (
            <button key={o} type="button" role="option" aria-selected={o === value} className={cx('wm-menu__item', o === value && 'ss-menu__on')} onClick={() => pick(o)}>{o}</button>
          ))}
          {!options.length && <span className="ss-menu__none">이 시나리오의 제품을 먼저 골라요</span>}
          {value && <button type="button" role="option" aria-selected={false} className="wm-menu__item ss-menu__clear" onClick={() => pick(null)}>쓰인 제품 빼기</button>}
        </span>
      )}
    </span>
  );
}

type Item = (SSScenario | SSCandidate) & { cid?: string };

/** 시나리오 카드(보드 SCBody 카드) — 이름 · 출처 · (후보면 수락) · × / 사용자 / 제품 토글 / 장면 흐름 / 항목 / 항목 추가 */
function ScenarioCard({ x, spNames, chg, onPatch, onRemove, onAccept }: {
  x: Item; spNames: string[]; chg: (k: string) => boolean;
  onPatch: (patch: Partial<SSScenario>, mark?: string[]) => void; onRemove: () => void; onAccept?: () => void;
}) {
  const cand = !!x.cid;
  const [tag, tagCls] = byTag(x.by, x.cid);
  const title = x.title || '새 시나리오';
  const prods = x.products.filter((p) => spNames.includes(p));
  const have = x.fields.map((f) => f.k);
  const more = MORE.filter((m) => !have.includes(m)).slice(0, 4);
  const setStep = (i: number, s: Partial<SSStep>) => x.steps.map((t, j) => (j === i ? { ...t, ...s } : t));
  return (
    <div className={cx('ss-card', cand && 'cd-pend')} role="group" aria-label={title} data-sc={x.id} data-title={x.title}>
      <span className="ss-card__top">
        <InlineInput label="시나리오 이름" value={x.title} placeholder="시나리오 이름" className="ss-in ss-in--title" changed={chg(`t:${x.id}`)}
          onCommit={(v) => onPatch({ title: v }, [`t:${x.id}`])} />
        <span className={cx('ss-tag', tagCls)}>{tag}</span>
        {cand && <button type="button" className="ss-ok" onClick={onAccept}>수락</button>}
        <button type="button" className="ss-cx" aria-label={`${cand ? '후보 지우기' : '시나리오 빼기'} · ${title}`} onClick={onRemove}><X /></button>
      </span>
      <span className="ss-row">
        <span className="ss-lab">사용자</span>
        <InlineInput label="사용자" value={x.user} placeholder="누가 쓰나요" className={cx('ss-in', x.user.includes('[확인 필요]') && 'cd-in--warn')} changed={chg(`u:${x.id}`)}
          onCommit={(v) => onPatch({ user: v }, [`u:${x.id}`])} />
      </span>
      <span className="ss-row ss-row--top">
        <span className="ss-lab ss-lab--top">제품</span>
        <span className="ss-tchips">
          {spNames.map((n) => {
            const on = x.products.includes(n);
            return (
              <button key={n} type="button" className={cx('ss-tchip', on && 'ss-tchip--on')} aria-pressed={on}
                onClick={() => onPatch(on
                  ? { products: x.products.filter((p) => p !== n), steps: x.steps.map((t) => (t.product === n ? { ...t, product: null } : t)) }
                  : { products: [...x.products, n] })}>{n}</button>
            );
          })}
        </span>
      </span>
      <span className="ss-steps">
        <span className="ss-steps__h">장면 흐름 <span>· 단계 수 자유 · 단계마다 쓰인 제품</span></span>
        {x.steps.map((t, i) => (
          <span key={i} className="ss-step">
            <span className="ss-num">{i + 1}</span>
            <span className="ss-stepin">
              <InlineInput label={`장면 ${i + 1}`} value={t.text} placeholder="장면" className={cx('ss-in', t.text.includes('[확인 필요]') && 'cd-in--warn')}
                changed={chg(`s:${x.id}:${i}`)} onCommit={(v) => onPatch({ steps: setStep(i, { text: v }) }, [`s:${x.id}:${i}`])} />
              {/* 보드에 없는 장면 빼기 — 칸 안 오른쪽, 머물 때만 */}
              <button type="button" className="ss-del" aria-label={`장면 ${i + 1} 빼기`} title="장면 빼기"
                onClick={() => onPatch({ steps: x.steps.filter((_, j) => j !== i) }, [`-s:${x.id}:${i}`])}><X s={9} w={3} /></button>
            </span>
            <StepProduct label={`장면 ${i + 1}`} value={t.product} options={prods} onPick={(v) => onPatch({ steps: setStep(i, { product: v }) })} />
          </span>
        ))}
        <button type="button" className="ss-addstep" onClick={() => onPatch({ steps: [...x.steps, { text: '', product: null }] }, [`s:${x.id}:${x.steps.length}`])}>+ 단계</button>
      </span>
      {x.fields.map((f, i) => (
        <span key={i} className="ss-row ss-frow">
          {MORE.slice(0, 4).includes(f.k)
            ? <span className="ss-lab ss-lab--nw">{f.k}</span>
            : <InlineInput label="항목 이름" value={f.k} maxLength={30} className="ss-labin" onCommit={(v) => onPatch({ fields: x.fields.map((y, j) => (j === i ? { ...y, k: v || '항목' } : y)) }, [`f:${x.id}:${i}`])} />}
          <span className="ss-stepin">
            <InlineInput label={f.k} value={f.v ?? ''} className="ss-in" changed={chg(`f:${x.id}:${i}`)}
              onCommit={(v) => onPatch({ fields: x.fields.map((y, j) => (j === i ? { ...y, v } : y)) }, [`f:${x.id}:${i}`])} />
            {/* 보드에 없는 항목 빼기 — 칸 안 오른쪽, 머물 때만 */}
            <button type="button" className="ss-del" aria-label={`${f.k} 빼기`} title="항목 빼기"
              onClick={() => onPatch({ fields: x.fields.filter((_, j) => j !== i) }, [`-f:${x.id}:${i}`])}><X s={9} w={3} /></button>
          </span>
        </span>
      ))}
      <span className="ss-more">
        <span>항목 추가</span>
        {more.map((m) => (
          <button key={m} type="button" className="ss-fchip"
            onClick={() => onPatch({ fields: [...x.fields, { k: m === '직접 이름 짓기' ? '새 항목' : m, v: '' }] }, [`f:${x.id}:${x.fields.length}`])}>+ {m}</button>
        ))}
      </span>
    </div>
  );
}

/** 고친 칸 표시 키 — 장면 · 항목을 빼면 뒤 칸 번호를 당긴다 */
function shiftMarks(set: Set<string>, prefix: string, removed: number) {
  const out = new Set<string>();
  for (const k of set) {
    if (!k.startsWith(prefix)) { out.add(k); continue; }
    const n = Number(k.slice(prefix.length));
    if (n < removed) out.add(k);
    else if (n > removed) out.add(`${prefix}${n - 1}`);
  }
  return out;
}

function Detail({ doc }: { doc: SSDoc }) {
  const qc = useQueryClient();
  const [spaces, setSpacesState] = useState<SSSpace[]>(doc.spaces);
  const spacesRef = useRef(doc.spaces);
  const setSpaces = (next: SSSpace[]) => { spacesRef.current = next; setSpacesState(next); };
  const [spId, setSpId] = useState(doc.spaces[0]?.id ?? '');
  const [pick, setPick] = useState(false);
  const [aiBusy, setAiBusy] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [marks, setMarks] = useState<Set<string>>(() => new Set());
  const [focusId, setFocusId] = useState<string | null>(null);
  const timer = useRef<number | null>(null);
  const pending = useRef<SSSpace[] | null>(null);
  const inflight = useRef<Promise<void> | null>(null);
  const verRef = useRef(doc.version);
  const saved = (doc.ver ?? 0) > 0;

  /** 응답 문서를 캐시에(머리 · 고친 곳 n). dss_changed 는 GET · 다시 가져오기 · 되돌리기만 계산해 주므로 다른 응답에서는 앞의 값을 잇는다 */
  const apply = useCallback((d: SSDoc, replace: boolean, keepDss = true) => {
    if (replace) { spacesRef.current = d.spaces; setSpacesState(d.spaces); }
    verRef.current = d.version;
    qc.setQueryData<SSDoc>(ssKey(d.id), (prev) => (keepDss ? { ...d, dss_changed: d.dss_changed ?? prev?.dss_changed ?? null } : d));
  }, [qc]);

  /** 모아 둔 고침을 한 번에 보낸다(앞 요청이 끝난 뒤 · 판 번호를 이어서) */
  const flush = useCallback(async () => {
    if (timer.current) { window.clearTimeout(timer.current); timer.current = null; }
    while (inflight.current) await inflight.current;
    const body = pending.current;
    if (!body) return;
    pending.current = null;
    const run = (async () => {
      try {
        const d = await putSpaceSet(doc.id, body, verRef.current);
        apply(d, !pending.current);
      } catch (e) {
        toast((e as Error).message || '저장하지 못했어요');
        try { apply(await getSpaceSet(doc.id), true); } catch { /* 다음 고침에서 다시 */ }
      }
    })();
    inflight.current = run;
    try { await run; } finally { if (inflight.current === run) inflight.current = null; }
  }, [apply, doc.id]);

  /** 고침 — 늘 가장 최근 값(spacesRef)에서 계산한다(칸을 떠나며 저장한 직후 다른 칸을 눌러도 앞 고침이 사라지지 않게) */
  const edit = (fn: (prev: SSSpace[]) => SSSpace[]) => {
    const next = fn(spacesRef.current);
    setSpaces(next);
    pending.current = next;
    if (timer.current) window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => { void flush(); }, 400);
  };
  useEffect(() => () => { void flush(); }, [flush]);
  useEffect(() => {
    if (!focusId) return;
    const el = document.querySelector<HTMLElement>(`[data-sc="${focusId}"]`);
    el?.scrollIntoView({ block: 'nearest' });
    el?.querySelector('input')?.focus();
    setFocusId(null);
  }, [focusId]);

  const mark = (keys?: string[]) => {
    if (!saved || !keys?.length) return;
    setMarks((m) => {
      let n = new Set(m);
      for (const k of keys) {
        if (k.startsWith('-')) {
          const [, kind, id, i] = /^-(s|f):(.+):(\d+)$/.exec(k) ?? [];
          if (kind) n = shiftMarks(n, `${kind}:${id}:`, Number(i));
        } else n.add(k);
      }
      return n;
    });
  };
  const chg = (k: string) => marks.has(k);

  const sp = spaces.find((s) => s.id === spId) ?? spaces[0];
  const spNames = sp ? sp.products.map((p) => p.name) : [];
  /** 고른 공간 하나를 고친다 — fn 은 그 공간의 가장 최근 값을 받는다 */
  const editSp = (fn: (s: SSSpace) => Partial<SSSpace>) => {
    const id = sp?.id;
    if (!id) return;
    edit((prev) => prev.map((s) => (s.id === id ? { ...s, ...fn(s) } : s)));
  };
  const patchItem = (x: Item, patch: Partial<SSScenario>, keys?: string[]) => {
    // 보드 SC2_AI: 점선 후보도 수락 전에 고칠 수 있다(서버는 같은 id · cid 의 고친 내용만 받는다)
    if (x.cid) editSp((s) => ({ candidates: s.candidates.map((c) => (c.id === x.id ? { ...c, ...patch } : c)) }));
    else { editSp((s) => ({ scenarios: s.scenarios.map((c) => (c.id === x.id ? { ...c, ...patch } : c)) })); mark(keys); }
  };
  const nSc = spaces.reduce((a, s) => a + s.scenarios.length, 0);
  const nCand = spaces.reduce((a, s) => a + s.candidates.length, 0);
  const nEmpty = spaces.filter((s) => !s.scenarios.length).length;

  const togglePick = (it: PickItem) => {
    if (!sp) return;
    editSp((s) => (s.products.some((p) => p.name === it.name)
      ? { products: s.products.filter((p) => p.name !== it.name) }
      : { products: [...s.products, { name: it.name, kind: it.kind, ref: it.ref ?? null }] }));
  };
  const runAi = async () => {
    if (!sp) return;
    await flush();
    setAiBusy(true);
    try {
      const r = await suggestScenarios(doc.id, sp.id);
      apply(r.set, true);
      if (r.mode === 'kb_only') toast('지금은 AI 를 쓸 수 없어 KB 도입사례를 참고한 틀만 넣었어요 · [확인 필요] 를 채워 주세요');
    } catch (e) { toast((e as Error).message || 'AI 시나리오 3안을 만들지 못했어요'); } finally { setAiBusy(false); }
  };
  const onCandidate = async (cid: string, accept: boolean) => {
    if (!sp) return;
    await flush();
    try { apply(accept ? await acceptCandidate(doc.id, sp.id, cid) : await dropCandidate(doc.id, sp.id, cid), true); } catch (e) { toast((e as Error).message || '반영하지 못했어요'); }
  };
  const addScenario = () => {
    if (!sp) return;
    const sc: SSScenario = { id: tmpId(), title: '', user: '', products: spNames.slice(), steps: [{ text: '', product: null }], fields: [], by: 'manual', basis: null };
    editSp((s) => ({ scenarios: [...s.scenarios, sc] }));
    setFocusId(sc.id);
  };
  const resync = async () => {
    if (syncing) return;
    setSyncing(true);
    try {
      await flush();
      const d = await resyncSpaceSet(doc.id);
      apply(d, true, false);
      toast(resyncToast(d.last_resync));
    } catch (e) { toast((e as Error).message || 'DSS를 다시 가져오지 못했어요'); } finally { setSyncing(false); }
  };
  const save = async (): Promise<SSStageOut> => {
    await flush();
    const out = await finishSpaceSet(doc.id);
    apply(await getSpaceSet(doc.id), true, false);
    setMarks(new Set());
    void qc.invalidateQueries({ queryKey: ssListKey });
    return out;
  };
  const revert = async () => {
    await flush();
    apply(await revertSpaceSet(doc.id), true, false);
    setMarks(new Set());
    void qc.invalidateQueries({ queryKey: ssListKey });
  };

  const sbIds = doc.sb_id ? [doc.sb_id] : [];
  const facts = saved ? [`공간 ${spaces.length}`, `시나리오 ${nSc}`, ...(nEmpty ? [`시나리오 없는 공간 ${nEmpty}`] : [])] : [`공간 ${spaces.length}`, `시나리오 ${nSc}`];
  const list: Item[] = sp ? [...sp.scenarios, ...sp.candidates.map((c) => ({ ...c, cid: c.cid }))] : [];
  return (
    <ContentDetail content="sc" saved={saved} changes={doc.changes} empty={!saved && !nSc && !nCand && doc.version <= 1}
      title={doc.title} refCode={doc.code} ver={doc.ver} savedAt={doc.saved_at} updatedAt={doc.updated_at} facts={facts} sbIds={sbIds}
      onSave={save} onRevert={revert} canSave={saveBlock(spaces)}
      savedToast={(o) => {
        const st = (o as SSStageOut).stage as { ref?: string; ver?: number };
        const synced = (o as SSStageOut).flow_sync?.synced ?? [];
        const ref = `${st.ref ?? doc.code} v${st.ver ?? ''}`;
        return !doc.sb_id ? `${ref} 저장했어요` : `${ref} 저장 · ${synced.length ? `연결된 Storyboard ${synced.length + 1}개에 반영했어요` : `${doc.sb_id}에 반영했어요`}`;
      }}>
      <div className="ss-body">
        {doc.dss_changed && (
          <AiBar actionLabel={syncing ? '가져오는 중…' : '다시 가져오기'} onAction={resync}>
            <span data-testid="ss-dss-changed" title={(doc.dss_changed.added_names ?? []).map((n) => `+ ${n}`).concat((doc.dss_changed.removed_names ?? []).map((n) => `− ${n}`)).join('\n') || undefined}>
              {dssChangeText(doc.dss_changed)}</span>
          </AiBar>
        )}
        <div className="ss-grid">
          {/* 공간(보드 220) */}
          <div className="ss-spaces" aria-label="공간">
            <span className="ss-spaces__h">공간 · {doc.dss_ref ?? 'DSS'}</span>
            {spaces.map((s) => {
              const n = s.scenarios.length;
              const pn = s.products.length;
              const sub = s.dss_status === 'removed' ? `DSS에서 빠짐 · 시나리오 ${n}` : !pn ? '제품 없음 · 저장 안 됨' : n ? `시나리오 ${n} · 제품 ${pn}` : `시나리오 없음 · 제품 ${pn}`;
              return (
                <button key={s.id} type="button" aria-pressed={s.id === sp?.id} className={cx('ss-sp', s.id === sp?.id && 'ss-sp--on')} onClick={() => setSpId(s.id)}>
                  <span className="ss-sp__name">{s.name}</span>
                  <span className={cx('ss-sp__sub', (!pn || s.dss_status === 'removed') && 'ss-sp__sub--warn', pn && !n && s.dss_status !== 'removed' && 'ss-sp__sub--empty')}
                    title={s.dss_status === 'removed' ? 'DSS에서 빠졌지만 시나리오 · 제품이 있어 남겨 뒀어요' : undefined}>
                    {sub}{s.dss_status === 'added' && <em className="ss-flag" title="DSS 다시 가져오기로 새로 생긴 공간"> · 새 공간</em>}</span>
                </button>
              );
            })}
            <span className="ss-spaces__foot">공간마다 제품 · 솔루션이 하나 이상 있어야 저장돼요</span>
          </div>

          {/* 고른 공간 */}
          {sp && (
            <div className="ss-main">
              <div className="ss-head">
                <span className="ss-head__row">
                  <span className="ss-head__name">{sp.name}</span>
                  <span className="ss-head__n">시나리오 {sp.scenarios.length}</span>
                  <span className="ss-grow" />
                  <AiButton size={34} onClick={runAi} busy={aiBusy} disabled={!spNames.length} title={!spNames.length ? '공간 제품 · 솔루션을 먼저 하나 이상 골라 주세요' : undefined}>AI 시나리오 3안</AiButton>
                </span>
                <span className="ss-pchips">
                  <span className="ss-pchips__h">공간 제품 · 솔루션</span>
                  {sp.products.map((p) => (
                    <span key={p.name} className={cx('ss-pchip', p.dss_status === 'removed' && 'ss-pchip--gone')} data-dss={p.dss_status ?? undefined}
                      title={p.dss_status === 'removed' ? 'DSS에서 빠졌지만 이 공간의 시나리오가 써서 남겨 뒀어요 · 필요 없으면 빼 주세요' : p.dss_status === 'added' ? 'DSS 다시 가져오기로 새로 들어왔어요' : undefined}>
                      <span className={cx('ss-pchip__kind', p.kind === 'solution' && 'ss-pchip__kind--sol')}>{p.kind === 'solution' ? '솔루션' : '제품'}</span>
                      <span className="ss-pchip__name">{p.name}</span>
                      {p.dss_status === 'removed' && <span className="ss-pchip__flag">DSS에서 빠짐</span>}
                      {p.dss_status === 'added' && <span className="ss-pchip__flag ss-pchip__flag--new">새로</span>}
                      <button type="button" className="ss-x" aria-label={`빼기 · ${p.name}`} onClick={() => editSp((s) => ({ products: s.products.filter((y) => y.name !== p.name) }))}><X s={10} w={2.8} /></button>
                    </span>
                  ))}
                  {!spNames.length && <span className="ss-warnpill">하나 이상 골라야 저장돼요</span>}
                  <button type="button" className="ss-dash" onClick={() => setPick(true)}>+ 추가 · 변경</button>
                </span>
              </div>
              <div className="ss-scroll">
                {!list.length && (
                  <div className="ss-empty">
                    <b>이 공간은 시나리오가 없어요</b>
                    <span>아래 「+ 시나리오 추가」로 바로 쓰거나 「AI 시나리오 3안」으로 후보를 받아요 · 없어도 저장돼요</span>
                  </div>
                )}
                <div className="ss-cards">
                  {list.map((x) => (
                    <ScenarioCard key={x.id} x={x} spNames={spNames} chg={chg}
                      onPatch={(patch, keys) => patchItem(x, patch, keys)}
                      onAccept={x.cid ? () => void onCandidate(x.cid!, true) : undefined}
                      onRemove={() => {
                        if (x.cid) void onCandidate(x.cid, false);
                        else editSp((s) => ({ scenarios: s.scenarios.filter((c) => c.id !== x.id) }));
                      }} />
                  ))}
                  <button type="button" className="ss-addcard" onClick={addScenario}>+ 시나리오 추가</button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
      {sp && <ProductPickerDialog open={pick} onClose={() => setPick(false)} title={`${sp.name} · 공간 제품 · 솔루션 고르기`} min={1}
        sub="공간에 쓸 제품 · 솔루션을 고르세요. 하나 이상 있어야 하고, 고른 것 중에서 시나리오마다 다시 골라요."
        groups={pickGroups(doc, spaces, sp)} picked={spNames} onToggle={togglePick} />}
    </ContentDetail>
  );
}

function Wait({ children }: { children: ReactNode }) {
  useShellPage({ section: CONTENT.sc.label, title: '', hasTask: false });
  return <div className="wm-page">{children}</div>;
}

function Body({ id }: { id: string }) {
  const q = useSpaceSet(id);
  if (q.isError) return <Wait><ErrorState message="공간 시나리오를 불러오지 못했어요 · 지워졌거나 주소가 바뀌었을 수 있어요" onRetry={() => q.refetch()} /></Wait>;
  if (!q.data) return <Wait><Skeleton h={480} r={14} /></Wait>;
  return <Detail doc={q.data} />;
}

export function SpacesPage() {
  const { id = '' } = useParams();
  return <Body key={id} id={id} />;
}
