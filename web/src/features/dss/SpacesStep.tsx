/**
 * DSS · 공간 · 제품(보드 webapp1 DS2 · DS2_AI) — 한 화면에 업종 · 공간 · 공간별 제품.
 *   머리: 제목 · 공간 n · 제품 m · 업종 고르기(220 목록) · AI 업종 추론 → 점선 줄 「적용」
 *   왼쪽 270: 공간(개수 · 추천 +n) · AI 공간 추천(점선 · 추가) · 공간 이름으로 추가
 *   오른쪽 1fr: 고른 공간의 제품(직접 · AI 추천 점선 → 수락) · 수량 · 상세 · 빼기 · 제품 검색 · 제품 탐색에서 고르기(ProdPicker)
 * 수락하지 않은 추천(점선)은 저장되지 않는다(CF-08).
 */
import { useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router';
import { useQuery } from '@tanstack/react-query';
import { FlowBar, useOpenDetail, useOpenPopover, useShellPage } from '@/shell';
import { FlowScreen, ProductPickerDialog, cx, toast, useConfirm, useEscape, type PickItem } from '@/ui';
import { fetchCandidates, type DSDoc, type DSProduct, type DSSpace, type DsActions } from './api';
import { addedRefs, dsOnAdd, dsShell } from './shellcfg';
import { AiBtn, ArrowIcon, BackIcon, Chevron, ProductSearch, ScreenIcon, Star, Tag, XIcon, modelCodeOf } from './parts';

const errMsg = (e: unknown, fb: string) => (e as Error)?.message || fb;

function QtyChip({ p, onSave }: { p: DSProduct; onSave: (v: string) => Promise<unknown> }) {
  const [edit, setEdit] = useState(false);
  const [v, setV] = useState(p.qty ?? '');
  const done = useRef(false);
  const commit = async () => {
    if (done.current) return;
    done.current = true;
    setEdit(false);
    if (v.trim() !== (p.qty ?? '')) await onSave(v.trim());
  };
  if (edit) {
    return (
      <input className="ds-qtyin" autoFocus value={v} aria-label={`${p.name} 수량`} placeholder="예: 2대" maxLength={30}
        onChange={(e) => setV(e.target.value)} onBlur={() => void commit()}
        onKeyDown={(e) => { if (e.key === 'Enter' && !e.nativeEvent.isComposing) void commit(); if (e.key === 'Escape') { done.current = true; setEdit(false); setV(p.qty ?? ''); } }} />
    );
  }
  const warn = !p.qty || p.qty.includes('[');
  return (
    <button type="button" className={cx('ds-qty', warn && 'ds-qty--warn')} title="수량 고치기" aria-label={`${p.name} 수량 ${p.qty ?? '확인 필요'} · 고치기`}
      onClick={() => { done.current = false; setV(p.qty ?? ''); setEdit(true); }}>{p.qty || '[확인 필요]'}</button>
  );
}

function ProductRow({ p, actions }: { p: DSProduct; actions: DsActions }) {
  const openDetail = useOpenDetail();
  const openPop = useOpenPopover();
  const pend = p.by === 'ai-pending';
  const run = (f: () => Promise<unknown>, fb: string) => f().catch((e) => toast(errMsg(e, fb)));
  const code = p.model_code || modelCodeOf(p.ref);
  return (
    <div className={cx('ds-prow', pend && 'ds-prow--pend')} data-product={p.name} data-by={p.by}>
      <span className="ds-pic"><ScreenIcon /></span>
      <span className="ds-ptxt">
        <span className="ds-ptop"><span className="ds-pname" title={p.name}>{p.name}</span><Tag by={p.by} /></span>
        <span className="ds-pwhy">{p.why || (p.ref ? '직접 추가' : '직접 추가 · KB 에 없음 · 확인 필요')}</span>
      </span>
      <QtyChip key={`${p.id}:${p.qty ?? ''}`} p={p} onSave={(v) => run(() => actions.setQty(p.id, v), '수량을 고치지 못했어요')} />
      <button type="button" className="ds-ghost ds-ghost--32" onClick={() => (code ? openDetail('product', code) : openPop('product', p.name))}>상세</button>
      {pend && <button type="button" className="ds-btn ds-btn--32" onClick={() => void run(() => actions.acceptProduct(p.id), '수락하지 못했어요')}>수락</button>}
      <button type="button" className="ds-x" aria-label={`${p.name} 빼기`} onClick={() => void run(() => actions.deleteProduct(p.id), '빼지 못했어요')}><XIcon /></button>
    </div>
  );
}

function IndustryPicker({ doc, actions }: { doc: DSDoc; actions: DsActions }) {
  const [open, setOpen] = useState(false);
  const wrap = useRef<HTMLDivElement>(null);
  useEscape(() => setOpen(false), open);
  useEffect(() => {
    if (!open) return;
    const h = (e: MouseEvent) => { if (wrap.current && !wrap.current.contains(e.target as Node)) setOpen(false); };
    document.addEventListener('mousedown', h);
    return () => document.removeEventListener('mousedown', h);
  }, [open]);
  const cur = doc.industry?.value ?? null;
  const options = doc.industry_options?.length ? doc.industry_options : [];
  const list = cur && !options.includes(cur) ? [...options, cur] : options;
  return (
    <div className="ds-ind" ref={wrap}>
      <button type="button" className={cx('ds-indbtn', cur && 'ds-indbtn--set')} aria-haspopup="listbox" aria-expanded={open} onClick={() => setOpen((v) => !v)}>
        <span className="ds-indbtn__k">업종</span><span>{cur ?? '선택해 주세요'}</span><Chevron />
      </button>
      {open && (
        <div className="ds-indmenu" role="listbox" aria-label="업종">
          {list.map((t) => (
            <button key={t} type="button" role="option" aria-selected={t === cur} className={cx('ds-indopt', t === cur && 'ds-indopt--on')}
              onClick={() => { setOpen(false); if (t !== cur) actions.setIndustry(t).catch((e) => toast(errMsg(e, '업종을 바꾸지 못했어요'))); }}>{t}</button>
          ))}
        </div>
      )}
    </div>
  );
}

export function SpacesStep({ doc, actions, onNext }: { doc: DSDoc; actions: DsActions; onNext: () => void }) {
  const [sel, setSel] = useState<string | null>(doc.spaces[0]?.key ?? null);
  const [busy, setBusy] = useState<'' | 'industry' | 'spaces' | 'products'>('');
  const [spName, setSpName] = useState('');
  const [pick, setPick] = useState(0);            // 0 = 닫힘, n = 연 횟수(후보를 열 때마다 새로 읽는다)
  const { confirm, dialog } = useConfirm();
  const spaces = doc.spaces;
  const cur: DSSpace | null = spaces.find((s) => s.key === sel) ?? spaces[0] ?? null;
  useEffect(() => { if (!cur && spaces[0]) setSel(spaces[0].key); }, [cur, spaces]);
  useShellPage(dsShell(doc, 2, { addable: ['product', 'solution'], added: addedRefs(doc), onAdd: dsOnAdd(doc, actions, cur ? { key: cur.key, name: cur.name } : null) }));

  const pendOf = (s: DSSpace) => s.products.filter((p) => p.by === 'ai-pending').length;
  const pendAll = spaces.reduce((a, s) => a + pendOf(s), 0);
  const c = doc.counts;
  const showIndAi = !!doc.industry_ai && doc.industry_ai.value !== doc.industry?.value;

  const ai = async (scope: 'industry' | 'spaces' | 'products') => {
    setBusy(scope);
    try {
      const r = await actions.suggest(scope);
      if (scope === 'industry' && r.doc.industry_ai && r.doc.industry_ai.value === r.doc.industry?.value) toast(`AI 업종 추론도 ‘${r.doc.industry_ai.value}’이에요`);
      else if (!r.added && r.message) toast(r.message);
    } catch (e) { toast(errMsg(e, 'AI 추천에 실패했어요. 잠시 후 다시 시도해 주세요.')); } finally { setBusy(''); }
  };
  const addSpace = async (name: string) => {
    const t = name.trim();
    if (!t) return;
    try {
      const d = await actions.addSpace(t);
      const added = d.spaces.find((s) => s.name === t) ?? d.spaces[d.spaces.length - 1];
      if (added) setSel(added.key);
      setSpName('');
    } catch (e) { toast(errMsg(e, '공간을 넣지 못했어요')); }
  };
  const delSpace = async (s: DSSpace) => {
    const n = s.products.filter((p) => p.by !== 'ai-pending').length;
    if (n && !(await confirm({ title: `‘${s.name}’ 공간을 뺄까요?`, message: `이 공간의 제품 ${n}개도 함께 빠져요.`, confirmLabel: '빼기', tone: 'danger' }))) return;
    try { await actions.deleteSpace(s.key); } catch (e) { toast(errMsg(e, '공간을 빼지 못했어요')); }
  };

  // 제품 탐색에서 고르기(ProdPicker 760×640) — KB 가 이 공간 요구로 추천한 제품 + 카탈로그 검색 + 직접 추가
  const cands = useQuery({ queryKey: ['dss', 'candidates', doc.id, cur?.key ?? '', pick], enabled: pick > 0 && !!cur,
    queryFn: () => fetchCandidates(doc.id, cur!.key), staleTime: Infinity });
  const groups = useMemo(() => {
    const items: PickItem[] = (cands.data?.items ?? []).map((x) => ({ name: x.name, kind: 'product', ref: x.ref, where: x.why || x.category || 'KB 추천' }));
    return items.length ? [{ label: `KB 추천 · ${cur?.name ?? ''}`, items }] : [];
  }, [cands.data, cur?.name]);
  const kept = cur ? cur.products.filter((p) => p.by !== 'ai-pending') : [];
  const onToggle = async (it: PickItem) => {
    if (!cur) return;
    if (it.kind === 'solution') { toast('솔루션은 다음 단계 · 솔루션에서 골라요'); return; }
    try {
      const has = kept.find((p) => p.name === it.name);
      if (has) { await actions.deleteProduct(has.id); return; }
      const cd = cands.data?.items.find((x) => x.name === it.name);
      await actions.addProduct(cur.key, cd ? { name: cd.name, ref: cd.ref, model_code: cd.model_code, family_id: cd.family_id, category: cd.category, why: cd.why }
        : { name: it.name, ref: it.ref ?? null, model_code: modelCodeOf(it.ref) });
    } catch (e) { toast(errMsg(e, '제품을 바꾸지 못했어요')); }
  };

  return (
    <FlowScreen pad="18px 40px" gap={12} className="ds-screen"
      bar={<FlowBar sbIds={doc.sb_id ? [doc.sb_id] : []} note="DSS를 저장하면 이 Storyboard에 연결돼요" emptyText="연결된 Storyboard가 없어요" />}>
      <div className="ds-head">
        <h1>공간과 제품을 정해요</h1>
        <span className="ds-total">공간 {c.spaces} · 제품 {c.products}</span>
        <IndustryPicker doc={doc} actions={actions} />
        <AiBtn size="38" onClick={() => void ai('industry')} busy={busy === 'industry'}>AI 업종 추론</AiBtn>
      </div>
      {showIndAi && doc.industry_ai && (
        <div className="ds-indai" role="status" aria-label="AI 업종 추론">
          <Star />
          <span className="ds-indai__v">{doc.industry_ai.value}</span>
          <span className="ds-indai__why" title={doc.industry_ai.basis ?? ''}>{doc.industry_ai.basis ? `근거 · ${doc.industry_ai.basis}` : ''}</span>
          <button type="button" className="ds-btn ds-btn--28" onClick={() => actions.acceptIndustry().catch((e) => toast(errMsg(e, '적용하지 못했어요')))}>적용</button>
        </div>
      )}

      <div className="wm-flow__grid ds-grid">
        {/* 공간 */}
        <div className="wm-flow__panel ds-spaces">
          <div className="ds-sphead">
            <span className="ds-sphead__t">공간 {spaces.length}</span>
            <AiBtn size="sp" onClick={() => void ai('spaces')} busy={busy === 'spaces'}>AI 공간 추천</AiBtn>
          </div>
          <div className="ds-splist" role="tablist" aria-orientation="vertical" aria-label="공간">
            {spaces.map((s) => {
              const n = s.products.filter((p) => p.by !== 'ai-pending').length;
              const pend = pendOf(s);
              const on = s.key === cur?.key;
              return (
                <div key={s.key} className={cx('ds-sp', on && 'ds-sp--on')} role="tab" aria-selected={on} tabIndex={0} data-space={s.name}
                  onClick={() => setSel(s.key)} onKeyDown={(e) => { if (e.target === e.currentTarget && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); setSel(s.key); } }}>
                  <span className="ds-sp__name">{s.name}</span>
                  {pend > 0 && <span className="ds-sp__pend" title={`AI 추천 ${pend}개 · 수락해야 들어가요`}>+{pend}</span>}
                  <span className={cx('ds-sp__n', !n && 'ds-sp__n--zero')}>{n}</span>
                  <button type="button" className="ds-sp__del" aria-label={`${s.name} 공간 빼기`} onClick={(e) => { e.stopPropagation(); void delSpace(s); }}><XIcon size={12} /></button>
                </div>
              );
            })}
            {doc.space_recs.map((r) => (
              <div key={r.name} className="ds-rec" data-rec={r.name}>
                <span className="ds-rec__txt">
                  <span className="ds-rec__t">{r.name}{r.ext && <span className="ds-rec__ext">확장</span>}</span>
                  <span className="ds-rec__why" title={r.why}>{r.why}</span>
                </span>
                <button type="button" className="ds-btn ds-rec__add" aria-label={`${r.name} 공간 추가`} onClick={() => void addSpace(r.name)}>추가</button>
              </div>
            ))}
          </div>
          <div className="ds-spfoot">
            <form className="ds-spadd" onSubmit={(e) => { e.preventDefault(); void addSpace(spName); }}>
              <label className="wm-sr" htmlFor="ds-sp">공간 추가</label>
              <input id="ds-sp" value={spName} onChange={(e) => setSpName(e.target.value)} placeholder="공간 이름으로 추가" maxLength={40} autoComplete="off" />
              <button type="submit" disabled={!spName.trim()}>추가</button>
            </form>
          </div>
        </div>

        {/* 고른 공간의 제품 */}
        <div className="wm-flow__panel ds-prods">
          <div className="ds-phead">
            <span className="ds-phead__name">{cur?.name ?? '공간'}</span>
            <span className="ds-phead__line" title={cur?.basis ?? ''}>{cur ? (cur.basis ? `근거 · ${cur.basis}` : '직접 추가한 공간') : ''}</span>
            {pendAll > 0 && <button type="button" className="ds-acceptall" onClick={() => actions.acceptAll().catch((e) => toast(errMsg(e, '수락하지 못했어요')))}>추천 모두 수락 {pendAll}</button>}
            <AiBtn size="prod" onClick={() => void ai('products')} busy={busy === 'products'} disabled={!spaces.length}>AI 공간별 제품 자동 매칭</AiBtn>
          </div>
          <div className="ds-prows" aria-label={cur ? `${cur.name} 제품` : '제품'}>
            {cur && cur.products.map((p) => <ProductRow key={p.id} p={p} actions={actions} />)}
            {cur && !cur.products.length && (
              <div className="ds-pempty">아직 제품이 없어요. 아래에서 모델명으로 찾아 넣거나, AI 자동 매칭을 써 보세요.</div>
            )}
            {!cur && (
              <div className="ds-pempty">먼저 공간을 넣어 주세요. 왼쪽 아래에 공간 이름을 적거나, AI 공간 추천을 써 보세요.</div>
            )}
          </div>
          <div className="ds-pfoot">
            <ProductSearch key={cur?.key ?? 'none'} placeholder={cur ? `${cur.name}에 제품 추가 · 모델명이나 용도로 찾기` : '공간을 먼저 넣어 주세요'} disabled={!cur}
              onAdd={(b) => actions.addProduct(cur!.key, b).catch((e) => toast(errMsg(e, '제품을 넣지 못했어요')))} />
            <button type="button" className="ds-ghost ds-ghost--38" disabled={!cur} onClick={() => setPick((v) => v + 1)}>제품 탐색에서 고르기</button>
          </div>
        </div>
      </div>

      <div className="wm-flow__foot">
        {doc.sb_id ? <Link className="wm-flow__back" to={`/storyboard/flow/${doc.sb_id}`}><BackIcon />Storyboard</Link>
          : <Link className="wm-flow__back" to="/dss"><BackIcon />목록</Link>}
        <span style={{ flex: 1 }} />
        {pendAll > 0 && <span className="wm-flow__summary">수락하지 않은 추천은 저장되지 않아요</span>}
        <button type="button" className="ds-next" onClick={onNext}>다음 · 솔루션<ArrowIcon /></button>
      </div>

      {cur && (
        <ProductPickerDialog open={pick > 0} onClose={() => setPick(0)} title={`${cur.name}에 넣을 제품 고르기`}
          sub={`KB가 ‘${cur.name}’ 요구로 추천한 제품이에요. 없으면 아래에서 카탈로그로 찾거나 직접 넣어요.`}
          groups={groups} picked={kept.map((p) => p.name)} onToggle={(it) => void onToggle(it)} />
      )}
      {dialog}
    </FlowScreen>
  );
}
