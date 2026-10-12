/**
 * DSS 본문(보드 webapp1 v63 DSBody — mode saved · editing · new · draft · AI 점선) — 최종본 한 장에서 바로 입력 · 수정한다.
 *   요약 칸: 업종(2.2fr · 근거 · 고르기 · AI 추론 태그 · 수락 · AI 업종 추론) | 공간 | 제품(수량 확인 필요 n) | 솔루션
 *   공간 · 제품: 머리 줄(AI 공간 추천 · AI 공간별 제품 자동 매칭) · 점선 줄(PendingBar) · 공간 카드 4열(이름 바로 고침 · 제품 n · + 제품 · ×
 *     · 근거 · 제품 줄 「모델 · 수량 칸 60 · 직접/AI · (점선: 수락 ×)」 · 카드 안 제품 찾기) · 「+ 공간 추가」 점선 카드
 *   솔루션 띠: 칩(최대 236 · 근거 · 출처 · ×) · 「+ 고르기」 · AI 솔루션 추천 → 솔루션 고르기 팝업(SolPicker)
 * 수락하지 않은 추천(점선)은 저장되지 않는다(CF-08). 저장한 뒤 이 화면에서 고친 칸은 cd-in--chg, 더한 줄은 cd-chgrow(marks).
 */
import { useEffect, useMemo, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { AiButton, InlineInput, PendingBar, useOpenDetail, useOpenPopover } from '@/shell';
import { ProductPickerDialog, cx, toast, useConfirm, useEscape, type PickItem } from '@/ui';
import { fetchCandidates, type DSAddProduct, type DSDoc, type DSProduct, type DSSpace, type DSSpaceRec, type DsActions } from './api';
import { ByTag, CardSearch, Chevron, XIcon, modelCodeOf } from './parts';
import { SolPicker } from './SolPicker';

const errMsg = (e: unknown, fb: string) => (e as Error)?.message || fb;
const isPend = (p: DSProduct) => p.by === 'ai-pending';
const needQty = (q?: string | null) => !q || q.includes('[');

/** 이 화면에서 고친 칸 · 줄(저장한 뒤에만 표시 — 저장 · 되돌리기 하면 지운다) */
export interface Marks { has: (k: string) => boolean; add: (...k: string[]) => void }

type AiScope = 'industry' | 'spaces' | 'products';

function IndustryCell({ doc, actions, marks, busy, onAi }: { doc: DSDoc; actions: DsActions; marks: Marks; busy: boolean; onAi: () => void }) {
  const [open, setOpen] = useState(false);
  const wrap = useRef<HTMLDivElement>(null);
  useEscape(() => setOpen(false), open);
  useEffect(() => {
    if (!open) return;
    const h = (e: MouseEvent) => { if (wrap.current && !wrap.current.contains(e.target as Node)) setOpen(false); };
    document.addEventListener('mousedown', h);
    return () => document.removeEventListener('mousedown', h);
  }, [open]);
  const cur = doc.industry ?? null;
  const ai = doc.industry_ai && doc.industry_ai.value !== cur?.value ? doc.industry_ai : null;
  const options = doc.industry_options.length ? doc.industry_options : [];
  const list = cur && !options.includes(cur.value) ? [...options, cur.value] : options;
  // 근거 줄(보드: 「업종 · 근거 RQ-01」 · 점선이면 AI 근거 · 비면 「목록에서 고르거나 AI 업종 추론」)
  const basis = ai ? `근거 ${ai.basis ?? ''}`.trim() : cur ? (cur.basis ? `근거 ${cur.basis}` : '직접 골랐어요') : '목록에서 고르거나 AI 업종 추론';
  const pick = (v: string) => {
    setOpen(false);
    if (v === cur?.value && !ai) return;
    actions.setIndustry(v).then(() => { if (doc.ver != null) marks.add('ind'); }).catch((e) => toast(errMsg(e, '업종을 바꾸지 못했어요')));
  };
  return (
    <div className="ds-ind" ref={wrap}>
      <span className="ds-ind__col">
        <span className="ds-ind__k">업종 <span title={basis}>· {basis}</span></span>
        <span className="ds-ind__row">
          <button type="button" aria-haspopup="listbox" aria-expanded={open} aria-label={`업종 ${ai?.value ?? cur?.value ?? '선택해 주세요'}`}
            className={cx('cd-in ds-ind__btn', ai ? 'ds-ind__btn--pend' : cur ? 'ds-ind__btn--set' : 'ds-ind__btn--empty', !ai && marks.has('ind') && 'cd-in--chg')}
            onClick={() => setOpen((v) => !v)}>{ai?.value ?? cur?.value ?? '선택해 주세요'}<Chevron /></button>
          {ai ? <ByTag by="ai-pending">AI 추론</ByTag> : cur && <ByTag by={cur.by}>{cur.by === 'manual' ? '직접' : 'AI 추론 · 수락'}</ByTag>}
          {ai && <button type="button" className="ds-ind__ok" onClick={() => actions.acceptIndustry().then(() => { if (doc.ver != null) marks.add('ind'); }).catch((e) => toast(errMsg(e, '수락하지 못했어요')))}>수락</button>}
        </span>
      </span>
      <AiButton size={32} onClick={onAi} busy={busy}>AI 업종 추론</AiButton>
      {open && (
        <div className="ds-indmenu" role="listbox" aria-label="업종">
          {list.map((t) => (
            <button key={t} type="button" role="option" aria-selected={t === cur?.value} className={cx('ds-indopt', t === cur?.value && 'ds-indopt--on')} onClick={() => pick(t)}>{t}</button>
          ))}
        </div>
      )}
    </div>
  );
}

function Fact({ k, v, note, warn }: { k: string; v: string | number; note?: string; warn?: boolean }) {
  return (
    <div className="ds-fact">
      <span className="ds-fact__k">{k}</span>
      <span className="ds-fact__v"><b>{v}</b>{note && <span className={cx('ds-fact__note', warn && 'ds-fact__note--warn')}>{note}</span>}</span>
    </div>
  );
}

function ProductRow({ p, actions, marks, saved, space }: { p: DSProduct; actions: DsActions; marks: Marks; saved: boolean; space: string }) {
  const openDetail = useOpenDetail();
  const openPop = useOpenPopover();
  const pend = isPend(p);
  const run = (f: () => Promise<unknown>, fb: string) => f().catch((e) => toast(errMsg(e, fb)));
  const code = p.model_code || modelCodeOf(p.ref);
  const chgQty = marks.has(`qty:${p.id}`);
  return (
    <span className={cx('ds-prow', pend && 'ds-prow--pend', !pend && marks.has(`row:${p.id}`) && 'cd-chgrow')} data-product={p.name} data-by={p.by} data-space={space}>
      <button type="button" className="ds-prow__model" title={`${p.name} · ${p.why || (p.ref ? '직접 추가' : '직접 추가 · KB 에 없음 · 확인 필요')}`}
        onClick={() => (code ? openDetail('product', code) : openPop('product', p.name))}>{p.name}</button>
      <InlineInput value={p.qty ?? ''} label={`${p.name} 수량`} placeholder="수량" maxLength={30} changed={chgQty}
        className={cx('ds-qty', !chgQty && (needQty(p.qty) ? 'ds-qty--warn' : 'ds-qty--set'))}
        onCommit={(v) => run(async () => { await actions.setQty(p.id, v); if (saved && !pend) marks.add(`qty:${p.id}`); }, '수량을 고치지 못했어요')} />
      <ByTag by={p.by} />
      {pend ? <>
        <button type="button" className="ds-prow__ok" aria-label={`수락 · ${p.name}`}
          onClick={() => void run(async () => { await actions.acceptProduct(p.id); if (saved) marks.add(`row:${p.id}`); }, '수락하지 못했어요')}>수락</button>
        <button type="button" className="cd-x ds-prow__x" aria-label={`빼기 · ${p.name}`} onClick={() => void run(() => actions.deleteProduct(p.id), '빼지 못했어요')}><XIcon size={10} w={2.8} /></button>
      </> : (
        /* 보드에 없음: 수락한 제품 빼기 — 손을 올리거나 키보드로 닿을 때만 보인다 */
        <button type="button" className="cd-x ds-prow__x ds-prow__x--hover" aria-label={`빼기 · ${p.name}`} onClick={() => void run(() => actions.deleteProduct(p.id), '빼지 못했어요')}><XIcon size={10} w={2.8} /></button>
      )}
    </span>
  );
}

/** 공간 카드(보드 DSBody sp) — 공간(직접 · 수락) 또는 AI 추천 공간(점선) */
function SpaceCard({ doc, sp, rec, actions, marks, searching, onSearch, onPicker }: {
  doc: DSDoc; sp?: DSSpace; rec?: DSSpaceRec; actions: DsActions; marks: Marks; searching: boolean; onSearch: (on: boolean) => void; onPicker: () => void;
}) {
  const { confirm, dialog } = useConfirm();
  const saved = doc.ver != null;
  const name = sp?.name ?? rec!.name;
  const prods = sp?.products ?? rec?.products ?? [];
  const n = prods.filter((p) => !isPend(p)).length;
  const ext = !!(sp?.ext ?? rec?.ext);
  const basis = ext ? '확장 공간 · 요구에는 없음' : rec ? `AI 추천 · ${rec.basis ?? rec.why}` : sp!.basis ? `근거 · ${sp!.basis}` : sp!.by === 'manual' ? '직접 추가한 공간' : 'AI 추천 공간 · 수락';
  const basisCls = ext ? 'ds-sp__basis--ext' : rec || (!sp!.basis && sp!.by !== 'manual') ? 'ds-sp__basis--ai' : '';
  const cands = useQuery({ queryKey: ['dss', 'candidates', doc.id, sp?.key ?? '', 'card'], enabled: searching && !!sp,
    queryFn: () => fetchCandidates(doc.id, sp!.key), staleTime: 60_000 });
  const del = async () => {
    try {
      if (rec) { await actions.dismiss('space', rec.name); return; }
      if (n && !(await confirm({ title: `‘${name}’ 공간을 뺄까요?`, message: `이 공간의 제품 ${n}개도 함께 빠져요.`, confirmLabel: '빼기', tone: 'danger' }))) return;
      await actions.deleteSpace(sp!.key);
    } catch (e) { toast(errMsg(e, '공간을 빼지 못했어요')); }
  };
  const add = async (b: DSAddProduct) => {
    try {
      const before = new Set(prods.map((p) => p.id));
      const d = await actions.addProduct(sp!.key, b);
      const now = d.spaces.find((s) => s.key === sp!.key)?.products ?? [];
      const added = now.filter((p) => !before.has(p.id)).map((p) => `row:${p.id}`);
      if (saved && added.length) marks.add(...added);
      if (!added.length) toast(`‘${b.name}’은 이미 ${name}에 있어요`);
    } catch (e) { toast(errMsg(e, '제품을 넣지 못했어요')); }
  };
  return (
    <div className={cx('ds-sp', rec && 'ds-sp--pend')} data-space-card={name} data-rec={rec ? name : undefined}>
      <span className="ds-sp__head">
        {sp
          ? <InlineInput value={sp.name} label={`공간 이름 · ${sp.name}`} maxLength={40} className="cd-in--bare ds-sp__name" changed={marks.has(`name:${sp.key}`)}
              onCommit={(v) => { if (!v) return; actions.renameSpace(sp.key, v).then(() => { if (saved) marks.add(`name:${sp.key}`); }).catch((e) => toast(errMsg(e, '이름을 바꾸지 못했어요'))); }} />
          : <span className="ds-sp__name ds-sp__name--rec">{name}</span>}
        <span className="ds-sp__n">제품 {n}</span>
        {sp && !searching && <button type="button" className="ds-sp__add" aria-label={`${name}에 제품 추가`} onClick={() => onSearch(true)}>+ 제품</button>}
        {rec && <button type="button" className="cd-ok" aria-label={`수락 · ${name} 공간`}
          onClick={() => actions.addSpace(rec.name).catch((e) => toast(errMsg(e, '수락하지 못했어요')))}>수락</button>}
        <button type="button" className="cd-x" aria-label={`공간 빼기 · ${name}`} onClick={() => void del()}><XIcon /></button>
      </span>
      <span className={cx('ds-sp__basis', basisCls)} title={basis}>{basis}</span>
      {prods.length > 0 && (
        <span className="ds-sp__prods">
          {prods.map((p) => <ProductRow key={p.id} p={p} actions={actions} marks={marks} saved={saved} space={name} />)}
        </span>
      )}
      {sp && searching && (
        <CardSearch id={`ds-add-${sp.key}`} space={name} candidates={cands.data?.items} onAdd={add} onPicker={onPicker} onClose={() => onSearch(false)} />
      )}
      {dialog}
    </div>
  );
}

function AddSpaceCard({ onAdd }: { onAdd: (name: string) => Promise<boolean> }) {
  const [v, setV] = useState('');
  const [busy, setBusy] = useState(false);
  const submit = async () => {
    const t = v.trim();
    if (!t || busy) return;
    setBusy(true);
    try { if (await onAdd(t)) setV(''); } finally { setBusy(false); }
  };
  return (
    <div className="ds-spadd">
      <span className="ds-spadd__t">+ 공간 추가</span>
      <label className="cd-sr" htmlFor="ds-add-space">공간 이름</label>
      <input id="ds-add-space" className="cd-in ds-spadd__in" value={v} placeholder="공간 이름 · 예) 라운지" maxLength={40} autoComplete="off" disabled={busy}
        onChange={(e) => setV(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter' && !e.nativeEvent.isComposing) { e.preventDefault(); void submit(); } }} />
    </div>
  );
}

/** 솔루션 근거 — 이유에서 요구 ref · 번호 머리를 떼고(보드 「RQ-01 업무환경 플랫폼」 → 「업무환경 플랫폼」 · 「RQ-05 1 입주사 안내」 → 「입주사 안내」),
 *  이유가 없으면 함께 쓰는 제품 첫 줄 */
function solBasis(doc: DSDoc, why?: string | null, links: string[] = []) {
  const ref = (doc.rq_ref ?? '').replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const w = (why ?? '').trim();
  if (w) return ref ? w.replace(new RegExp(`^${ref}(?:\\s+\\d+(?:\\s*·\\s*\\d+)*)?\\s+`), '') : w;
  return links[0] ?? '';
}

export function DsBody({ doc, actions, marks }: { doc: DSDoc; actions: DsActions; marks: Marks }) {
  const [busy, setBusy] = useState<AiScope | ''>('');
  const [search, setSearch] = useState<string | null>(null);        // 제품 찾기를 연 공간 key
  const [picker, setPicker] = useState<string | null>(null);        // 제품 탐색(ProdPicker)을 연 공간 key
  const [solPop, setSolPop] = useState<'' | 'pick' | 'ai'>('');
  const saved = doc.ver != null;
  const spaces = doc.spaces;
  const kept = spaces.flatMap((s) => s.products.filter((p) => !isPend(p)));
  const nQty = kept.filter((p) => needQty(p.qty)).length;
  const indPend = !!doc.industry_ai && doc.industry_ai.value !== doc.industry?.value;
  const nPend = (indPend ? 1 : 0) + doc.space_recs.length + doc.space_recs.reduce((a, r) => a + r.products.length, 0)
    + spaces.reduce((a, s) => a + s.products.filter(isPend).length, 0);
  const sols = doc.solutions;

  const ai = async (scope: AiScope) => {
    setBusy(scope);
    try {
      const r = await actions.suggest(scope);
      if (scope === 'industry' && r.doc.industry_ai && r.doc.industry_ai.value === r.doc.industry?.value) toast(`AI 업종 추론도 ‘${r.doc.industry_ai.value}’이에요`);
      else if (!r.added && r.message) toast(r.message);
    } catch (e) { toast(errMsg(e, 'AI 추천에 실패했어요. 잠시 후 다시 시도해 주세요.')); } finally { setBusy(''); }
  };
  const addSpace = async (name: string) => {
    try { await actions.addSpace(name); return true; } catch (e) { toast(errMsg(e, '공간을 넣지 못했어요')); return false; }
  };

  // 제품 탐색에서 고르기(ProdPicker 760×640) — KB 가 이 공간 요구로 추천한 제품 + 카탈로그 검색 + 직접 추가
  const pickSp = spaces.find((s) => s.key === picker) ?? null;
  const pc = useQuery({ queryKey: ['dss', 'candidates', doc.id, picker ?? '', 'card'], enabled: !!pickSp,
    queryFn: () => fetchCandidates(doc.id, pickSp!.key), staleTime: 60_000 });
  const groups = useMemo(() => {
    const items: PickItem[] = (pc.data?.items ?? []).map((x) => ({ name: x.name, kind: 'product', ref: x.ref, where: x.why || x.category || 'KB 추천' }));
    return items.length ? [{ label: `KB 추천 · ${pickSp?.name ?? ''}`, items }] : [];
  }, [pc.data, pickSp?.name]);
  const pickKept = pickSp ? pickSp.products.filter((p) => !isPend(p)) : [];
  const onToggle = async (it: PickItem) => {
    if (!pickSp) return;
    if (it.kind === 'solution') { toast('솔루션은 아래 솔루션 칸의 「+ 고르기」에서 골라요'); return; }
    try {
      const has = pickKept.find((p) => p.name === it.name);
      if (has) { await actions.deleteProduct(has.id); return; }
      const cd = pc.data?.items.find((x) => x.name === it.name);
      const before = new Set(pickSp.products.map((p) => p.id));
      const d = await actions.addProduct(pickSp.key, cd ? { name: cd.name, ref: cd.ref, model_code: cd.model_code, family_id: cd.family_id, category: cd.category, why: cd.why }
        : { name: it.name, ref: it.ref ?? null, model_code: modelCodeOf(it.ref) });
      const added = (d.spaces.find((s) => s.key === pickSp.key)?.products ?? []).filter((p) => !before.has(p.id)).map((p) => `row:${p.id}`);
      if (saved && added.length) marks.add(...added);
    } catch (e) { toast(errMsg(e, '제품을 바꾸지 못했어요')); }
  };

  return (
    <div className="ds-body">
      {/* 요약 칸 — 업종은 여기서 바로 고른다 */}
      <div className="ds-facts">
        <IndustryCell doc={doc} actions={actions} marks={marks} busy={busy === 'industry'} onAi={() => void ai('industry')} />
        <Fact k="공간" v={spaces.length} />
        <Fact k="제품" v={kept.length} note={nQty ? `수량 확인 필요 ${nQty}` : undefined} warn />
        <Fact k="솔루션" v={sols.length} note={sols.length ? undefined : '0개도 돼요'} />
      </div>

      {/* ① 공간 · 제품 */}
      <div className="ds-sechead">
        <span className="ds-sechead__t">공간 · 제품</span>
        <span className="ds-sechead__hint">공간마다 제품을 넣어요 · 수량은 칸에서 바로 고쳐요</span>
        <span className="ds-grow" />
        <AiButton size={32} onClick={() => void ai('spaces')} busy={busy === 'spaces'}>AI 공간 추천</AiButton>
        <AiButton size={32} onClick={() => void ai('products')} busy={busy === 'products'}>AI 공간별 제품 자동 매칭</AiButton>
      </div>
      <PendingBar count={nPend}
        onClearAll={() => actions.dismiss('all').catch((e) => toast(errMsg(e, '지우지 못했어요')))}
        onAcceptAll={() => {
          // 수락한 제품 줄 = 이 화면에서 더한 줄(저장한 뒤라면 cd-chgrow)
          const ids = [...spaces.flatMap((s) => s.products), ...doc.space_recs.flatMap((r) => r.products)].filter(isPend).map((p) => `row:${p.id}`);
          actions.acceptAll('all').then(() => { if (saved && ids.length) marks.add(...ids); }).catch((e) => toast(errMsg(e, '수락하지 못했어요')));
        }} />
      <div className="ds-grid" aria-label="공간">
        {spaces.map((s) => (
          <SpaceCard key={s.key} doc={doc} sp={s} actions={actions} marks={marks} searching={search === s.key}
            onSearch={(on) => setSearch(on ? s.key : null)} onPicker={() => { setSearch(null); setPicker(s.key); }} />
        ))}
        {doc.space_recs.map((r) => (
          <SpaceCard key={`rec:${r.name}`} doc={doc} rec={r} actions={actions} marks={marks} searching={false} onSearch={() => {}} onPicker={() => {}} />
        ))}
        <AddSpaceCard onAdd={addSpace} />
      </div>

      {/* ② 솔루션 0개 이상 */}
      <div className="ds-sols">
        <span className="ds-sols__t">솔루션 {sols.length}</span>
        {!sols.length && <span className="ds-sols__none">고르지 않아도 저장돼요</span>}
        <span className="ds-sols__chips">
          {sols.map((o) => {
            const b = solBasis(doc, o.why, o.links);
            return (
              <span key={o.id} className="ds-chip" data-solution={o.id}>
                <span className="ds-chip__name">{o.name}</span>
                {b && <span className="ds-chip__basis" title={b}>{b}</span>}
                <ByTag by={o.by}>{o.by === 'manual' ? '직접' : 'AI 추천'}</ByTag>
                <button type="button" className="cd-x ds-chip__x" aria-label={`빼기 · ${o.name}`}
                  onClick={() => actions.setSolutions(sols.filter((x) => x.id !== o.id).map((x) => x.id)).catch((e) => toast(errMsg(e, '솔루션을 빼지 못했어요')))}><XIcon size={10} w={2.8} /></button>
              </span>
            );
          })}
          <button type="button" className="ds-sols__pick" onClick={() => setSolPop('pick')}>+ 고르기</button>
        </span>
        <AiButton size={32} onClick={() => setSolPop('ai')}>AI 솔루션 추천</AiButton>
      </div>

      {solPop && <SolPicker doc={doc} actions={actions} runAi={solPop === 'ai'} onClose={() => setSolPop('')} />}
      {pickSp && (
        <ProductPickerDialog open onClose={() => setPicker(null)} title={`${pickSp.name}에 넣을 제품 고르기`}
          sub={`KB가 ‘${pickSp.name}’ 요구로 추천한 제품이에요. 없으면 아래에서 카탈로그로 찾거나 직접 넣어요.`}
          groups={groups} picked={pickKept.map((p) => p.name)} onToggle={(it) => void onToggle(it)} />
      )}
    </div>
  );
}
