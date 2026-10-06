/**
 * SC3 · 솔루션 · 제품 입력(§4.7) — 장면 칩, 솔루션 칩 · 탐색 · 입력(자동완성), 제품 칩 · 추천(점선) · 입력 → R4(SC3R 또는 SC4G).
 * 상단바 솔루션 · 제품 탐색의 「현재 작업에 추가」와 끌어 놓기도 받는다(accepts: solution · product).
 */
import { useEffect, useRef, useState, type ReactNode } from 'react';
import { useNavigate, useParams } from 'react-router';
import { useQuery } from '@tanstack/react-query';
import { cx, Icon, useDropTarget, type DragPayload } from '@/ui';
import { parseRef, useOpenPopover, useShellPage } from '@/shell';
import { ApiError, errMessage, scApi, type ProductItem, type ProductPick, type RelatedProduct, type SearchHit } from '../api';
import { qk, useDebounced, useInvalidate, useScenario } from '../hooks';
import { route, SECTION, stepper } from '../lib';
import { Btn, Card, Echo, Ico, Loading, NextButton, Note, P, Screen, W } from '../parts';

const toItem = (p: ProductPick | RelatedProduct, source?: ProductItem['source']): ProductItem => ({
  ref: p.ref ?? null, family_id: p.family_id ?? null, model_code: p.model_code ?? null, label: p.label, short: p.short,
  qty: 'qty' in p ? p.qty ?? null : null, source: source ?? ('source' in p ? p.source : 'user'),
});

export default function SolutionsPage() {
  const { id = '' } = useParams();
  const nav = useNavigate();
  const inv = useInvalidate();
  const sc = useScenario(id);
  const tl = useQuery({ queryKey: qk.timeline(id), queryFn: () => scApi.timeline(id), enabled: !!id });
  const openPop = useOpenPopover();
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const s = sc.data;
  const isWith = s?.type === 'with';
  const solutions = s?.solution_picks ?? [];
  const products = s?.product_picks ?? [];
  const related = s?.related_products ?? [];

  const saveSolutions = async (ids: string[]) => {
    setErr(null);
    try { await scApi.putSolutions(id, ids); await inv.sc(id); } catch (e) { setErr(errMessage(e)); }
  };
  const saveProducts = async (items: ProductItem[]) => {
    setErr(null);
    try { await scApi.putProducts(id, items); await inv.sc(id); } catch (e) { setErr(errMessage(e)); }
  };
  const addProducts = async (more: ProductItem[]) => {
    const cur = products.map((p) => toItem(p));
    const keys = new Set(cur.map((p) => p.ref || p.label));
    const next = [...cur, ...more.filter((m) => !keys.has(m.ref || m.label || ''))];
    await saveProducts(next);
  };

  useShellPage({
    section: SECTION, title: s?.title ?? '', stepper: stepper(3), sidebarGroup: 'scenario',
    accepts: isWith ? ['solution', 'product'] : ['product'], addable: isWith ? ['solution', 'product'] : ['product'],
    added: [...solutions.map((x) => `kb:solution:${x.solution_id}`), ...products.map((p) => p.ref).filter(Boolean) as string[]],
    onAdd: async (type, refs) => {
      if (type === 'solution') {
        await saveSolutions([...solutions.map((x) => x.solution_id), ...refs.map((r) => parseRef(r).id)]);
        return { added: refs };
      }
      if (type === 'product') {
        await addProducts(refs.map((r) => ({ ref: r, source: 'user' as const })));
        return { added: refs };
      }
      return { added: [] };
    },
    taskContext: { products: products.filter((p) => p.ref).map((p) => ({ ref: p.ref!, label: p.short })) },
  });

  if (sc.isLoading || !s) return <Loading />;

  const scenes = [...(tl.data?.scenes ?? [])].sort((a, b) => a.no - b.no);
  const slots = [...(tl.data?.slots ?? [])].sort((a, b) => a.ord - b.ord);
  const roles = [...(tl.data?.roles ?? [])].sort((a, b) => a.ord - b.ord);
  const slotLabel = (slotId: string) => slots.find((x) => x.id === slotId)?.label ?? '';
  const used = slots.filter((x) => scenes.some((y) => y.slot_id === x.id));
  const echo = `${used.map((x) => `${x.time ? `${x.time} ` : ''}${x.label}`).join(' → ')}${roles.length ? ` · ${roles.map((r) => r.name).join(' / ')}` : ''}`;
  const n = scenes.length;
  const empty = isWith ? solutions.length + products.length === 0 : products.length === 0;

  const generate = async () => {
    setBusy(true); setErr(null);
    try {
      const r = await scApi.routeGenerate(id);
      if (r.next === 'SC3R') { nav(route.recommend(id)); return; }
      const g = await scApi.generate(id, 'all');
      await inv.sc(id);
      nav(route.generate(id, g.job_id));
    } catch (e) {
      if (e instanceof ApiError && e.code === 'GENERATION_IN_PROGRESS') {
        const fresh = await scApi.get(id).catch(() => null);
        if (fresh?.generation?.job_id) { nav(route.generate(id, fresh.generation.job_id)); return; }
      }
      setErr(errMessage(e));
    } finally { setBusy(false); }
  };

  const dock = (
    <Card title="솔루션 · 제품" meta="3 / 4" testId="sc3-card">
      {isWith && (
        <PickBox kind="solution" label="솔루션" inputLabel="솔루션 입력" placeholder="솔루션명 입력…" testId="sc3-solutions"
          browse={<button type="button" className="sc-link" onClick={() => openPop('solution')} data-testid="sc3-browse-solution">솔루션 탐색에서 고르기</button>}
          chips={solutions.map((x) => ({ key: x.solution_id, label: x.name, onRemove: () => void saveSolutions(solutions.filter((y) => y.solution_id !== x.solution_id).map((y) => y.solution_id)) }))}
          search={(q, signal) => scApi.solutionSearch(q, signal).then((r) => r.items)}
          onPick={(h) => { if (h) void saveSolutions([...solutions.map((x) => x.solution_id), h.id]); }}
          onDrop={async (p) => { await saveSolutions([...solutions.map((x) => x.solution_id), parseRef(p.ref).id]); }} />
      )}
      <PickBox kind="product" label="제품" inputLabel="제품 입력" placeholder="제품명 입력…" testId="sc3-products" allowCustom
        labelExtra={related.length > 0 && s.related_for ? <span style={{ color: 'var(--wm-brand)' }} data-testid="sc3-related-for"> · {s.related_for} 연관 제품 추천됨</span> : null}
        browse={<button type="button" className="sc-link" onClick={() => openPop('product')} data-testid="sc3-browse-product">제품 탐색에서 고르기</button>}
        chips={products.map((p, i) => ({
          key: p.ref || p.label, label: p.label, qty: p.qty ?? null,
          onQty: (q: number) => void saveProducts(products.map((x, j) => toItem(j === i ? { ...x, qty: q } : x))),
          onRemove: () => void saveProducts(products.filter((_, j) => j !== i).map((x) => toItem(x))),
        }))}
        recs={related.map((r) => ({ key: r.ref || r.label, label: `추천: ${r.short || r.label}`, title: r.why, onAdd: () => void addProducts([toItem(r, 'recommended')]) }))}
        search={(q, signal) => scApi.productSearch(q, signal).then((r) => r.items)}
        onPick={(h, text) => {
          if (h) void addProducts([{ ref: h.ref, family_id: h.family_id ?? null, model_code: h.model_code ?? null, label: h.label, short: h.short, source: 'user' }]);
          else if (text) void addProducts([{ ref: `custom:${text}`, label: text, short: text, source: 'user' }]);
        }}
        onDrop={async (p) => { await addProducts([{ ref: p.ref, label: p.label, short: p.label, source: 'user' }]); }} />
      {err && <div className="sc-card__sec"><Note tone="err" testId="sc3-err">{err}</Note></div>}
      <div className="sc-card__foot">
        <Btn to={s.via_timeline ? route.timeline(id) : route.input(id)} testId="sc3-prev">이전</Btn>
        <NextButton onClick={() => void generate()} busy={busy} disabled={empty} testId="sc3-generate"
          reason={isWith ? '솔루션이나 제품을 하나 이상 넣어 주세요' : '제품을 하나 이상 넣어 주세요'}>시나리오 생성</NextButton>
      </div>
    </Card>
  );

  return (
    <Screen dock={dock} testId="sc3">
      {echo && <Echo testId="sc3-echo">{echo}</Echo>}
      <W testId="sc3-w" extra={(
        <>
          <div className="sc-row sc-wrap" style={{ gap: 8 }} data-testid="sc3-scenes">
            {scenes.map((x) => <span key={x.id} className="sc-scenechip">장면 {x.no} · {slotLabel(x.slot_id)}</span>)}
          </div>
          {s.notices?.real_names && <div className="sc-w__note" data-testid="sc3-realnames"><Icon name="info" size={13} />실제 인물 이름은 역할로 바꿔 썼어요</div>}
        </>
      )}>
        {isWith
          ? `${n}개 장면으로 나눌 수 있겠네요. 시나리오에 넣을 솔루션과 제품을 입력해 주세요. 솔루션을 고르면 연관 제품을 추천해 드립니다.`
          : `${n}개 장면으로 나눌 수 있겠네요. 시나리오에 넣을 제품을 입력해 주세요.`}
      </W>
    </Screen>
  );
}

interface ChipSpec { key: string; label: string; qty?: number | null; onQty?: (q: number) => void; onRemove: () => void }
interface RecSpec { key: string; label: string; title?: string; onAdd: () => void }

/** 칩 + 추천 칩 + 입력(자동완성, 결과 패널은 위로) + 끌어 놓기 */
function PickBox({ kind, label, labelExtra, inputLabel, placeholder, browse, chips, recs = [], search, onPick, onDrop, allowCustom, testId }:
  { kind: 'solution' | 'product'; label: string; labelExtra?: ReactNode; inputLabel: string; placeholder: string; browse: ReactNode; chips: ChipSpec[];
    recs?: RecSpec[]; search: (q: string, signal: AbortSignal) => Promise<SearchHit[]>; onPick: (h: SearchHit | null, text?: string) => void;
    onDrop: (p: DragPayload) => Promise<void>; allowCustom?: boolean; testId: string }) {
  const [q, setQ] = useState('');
  const dq = useDebounced(q, 150);
  const [hits, setHits] = useState<SearchHit[]>([]);
  const [open, setOpen] = useState(false);
  const [cur, setCur] = useState(0);
  const [qtyFor, setQtyFor] = useState<string | null>(null);
  const boxRef = useRef<HTMLDivElement>(null);
  const drop = useDropTarget({ accept: [kind], onDrop: async (p) => { await onDrop(p); } });
  const inputId = `sc3-${kind}-q`;

  useEffect(() => {
    const t = dq.trim();
    if (!t) { setHits([]); return; }
    const ctl = new AbortController();
    search(t, ctl.signal).then((r) => { setHits(r); setCur(0); }).catch(() => undefined);
    return () => ctl.abort();
  }, [dq]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (!open && !qtyFor) return;
    const down = (e: MouseEvent) => { if (boxRef.current && !boxRef.current.contains(e.target as Node)) { setOpen(false); setQtyFor(null); } };
    document.addEventListener('mousedown', down);
    return () => document.removeEventListener('mousedown', down);
  }, [open, qtyFor]);

  const pick = (h: SearchHit | null) => {
    const text = q.trim();
    onPick(h, h ? undefined : text);
    setQ(''); setHits([]); setOpen(false);
  };
  const rows = hits.slice(0, kind === 'product' ? 5 : 8);
  return (
    <div className="sc-card__sec" style={{ display: 'flex', flexDirection: 'column', gap: 6 }} data-testid={testId}>
      <div className="sc-row" style={{ justifyContent: 'space-between' }}>
        <div className="sc-label">{label}{labelExtra}</div>
        {browse}
      </div>
      <div ref={boxRef} {...drop.props} className={cx('sc-box', drop.dragging && 'sc-box--drop', drop.over && 'sc-box--over')} data-drop-state={drop.state}>
        {chips.map((c) => (
          <span key={c.key} className="sc-bchip" data-testid={`${testId}-chip`}>
            <span>{c.label}</span>
            {c.onQty && (
              <span style={{ position: 'relative', display: 'inline-flex' }}>
                <button type="button" className={cx('sc-bchip__qty', !(c.qty && c.qty > 1) && 'sc-bchip__qty--one')} aria-label={`${c.label} 수량`} aria-haspopup="menu"
                  aria-expanded={qtyFor === c.key} title="수량" onClick={() => setQtyFor(qtyFor === c.key ? null : c.key)}>{c.qty && c.qty > 1 ? `×${c.qty}` : '×1'}</button>
                {qtyFor === c.key && (
                  <span className="sc-qtymenu" role="menu">
                    {[1, 2, 3, 4, 5, 6, 8, 10, 12].map((n) => (
                      <button key={n} type="button" role="menuitemradio" aria-checked={(c.qty ?? 1) === n} onClick={() => { c.onQty?.(n); setQtyFor(null); }}>{n}</button>
                    ))}
                  </span>
                )}
              </span>
            )}
            <button type="button" className="sc-chip__x" aria-label="제거" onClick={c.onRemove}><Icon name="x" size={11} strokeWidth={2.6} /></button>
          </span>
        ))}
        {recs.map((r) => (
          <button key={r.key} type="button" className="sc-bchip sc-bchip--rec" title={r.title} onClick={r.onAdd} data-testid={`${testId}-rec`}>
            <Ico d={P.plus} size={11} sw={2.6} />{r.label}
          </button>
        ))}
        <label htmlFor={inputId} className="wm-sr-only">{inputLabel}</label>
        <input id={inputId} className="sc-box__input" value={q} placeholder={placeholder} autoComplete="off" role="combobox" aria-expanded={open && rows.length > 0}
          aria-controls={`${inputId}-list`}
          onChange={(e) => { setQ(e.target.value); setOpen(true); }} onFocus={() => setOpen(true)}
          onKeyDown={(e) => {
            if (e.nativeEvent.isComposing) return;
            if (e.key === 'ArrowDown') { e.preventDefault(); setCur(Math.min(rows.length - 1, cur + 1)); }
            else if (e.key === 'ArrowUp') { e.preventDefault(); setCur(Math.max(0, cur - 1)); }
            else if (e.key === 'Escape') setOpen(false);
            else if (e.key === 'Enter') {
              e.preventDefault();
              if (rows[cur]) pick(rows[cur]);
              else if (allowCustom && q.trim()) pick(null);
            }
          }} />
        {drop.dragging && <span className="sc-box__dropnote">여기에 놓아 「{drop.active?.label}」 추가</span>}
        {open && q.trim() && (rows.length > 0 || allowCustom) && (
          <div className="sc-results" role="listbox" id={`${inputId}-list`}>
            {rows.map((h, i) => (
              <button key={h.ref} type="button" role="option" aria-selected={i === cur} className="sc-result" onMouseEnter={() => setCur(i)}
                onMouseDown={(e) => e.preventDefault()} onClick={() => pick(h)}>
                <span className="sc-result__name">{h.label}</span>
                {h.sub && <span className="sc-result__meta">{h.sub}</span>}
              </button>
            ))}
            {allowCustom && <button type="button" className="sc-result" onMouseDown={(e) => e.preventDefault()} onClick={() => pick(null)}>
              <span className="sc-result__name">"{q.trim()}" 그대로 추가</span>
            </button>}
          </div>
        )}
      </div>
    </div>
  );
}
