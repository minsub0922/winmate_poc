/**
 * 공통 제품 입력창(§5.10 ProductInput) — 입력하면 결과가 입력창 **위로** 열리고, 고르면 버블로 고정된다.
 * 조감도 · 시나리오 · Spec 시트 · 제안서 등 모든 스텝에서 같은 컴포넌트를 쓴다.
 *
 *   const [items, setItems] = useState<ProductToken[]>([]);
 *   <ProductInput value={items} onChange={setItems} placeholder="제품명 · 모델명을 입력해 추가…" legend />
 *
 * 값: `[{kind: 'model'|'family'|'custom', ref?: 'kb:model:mdl_…'|'kb:family:fam_…', label}]` — 같은 ref(직접 입력은 같은 글)는 두 번 넣지 않는다.
 * 데이터: kb `GET /api/kb/v1/products/search?q=&limit=5&kinds=model,family`(§7.2.5). `search` 로 바꿀 수 있다.
 */
import { useCallback, useEffect, useId, useMemo, useRef, useState, type KeyboardEvent, type ReactNode } from 'react';
import { useEscape } from './overlay';
import { cx } from './controls';
import { Icon } from './icons';
import { Img, type Focal } from './media';

export interface ProductToken {
  kind: 'model' | 'family' | 'custom';
  /** `kb:model:mdl_…` · `kb:family:fam_…` · 직접 입력은 `custom:<글>` */
  ref?: string;
  label: string;
  /** 모델코드(있으면) */
  model_code?: string;
  /** 수량(`qty` 를 켠 입력창 — 버블 `×n`, 1~qtyMax). 없으면 1 */
  qty?: number;
}

/** kb `/v1/products/search` 결과 행(§7.2.5) */
export interface ProductSearchItem {
  kind: 'model' | 'family';
  id: string;
  display_name: string;
  label?: string;
  model_code?: string | null;
  family_name?: string | null;
  category_path?: string[];
  meta_line?: string | null;
  thumb?: { thumb_url?: string | null; stored_url?: string | null; focal?: Focal | null } | null;
  highlight?: Array<[number, number]>;
}

/** 기본 검색: kb 제품 검색 */
export async function searchProducts(q: string, opts: { limit?: number; kinds?: string; signal?: AbortSignal } = {}): Promise<ProductSearchItem[]> {
  const p = new URLSearchParams({ q, limit: String(opts.limit ?? 5), kinds: opts.kinds ?? 'model,family' });
  const r = await fetch(`/api/kb/v1/products/search?${p}`, { credentials: 'same-origin', signal: opts.signal });
  if (!r.ok) throw new Error(`products/search ${r.status}`);
  const body = (await r.json()) as { items?: ProductSearchItem[] };
  return body.items ?? [];
}

/** 결과 행 · 버블 이름: 모델은 표시명(`QM55C`), 제품군은 이름(`실내용 The Wall IWC`) — kb `label` 은 모델이면 영문 계열명이다 */
export const productName = (it: Pick<ProductSearchItem, 'kind' | 'display_name' | 'label'>) =>
  (it.kind === 'model' ? it.display_name || it.label : it.label || it.display_name) || '';

export const tokenOf = (it: ProductSearchItem): ProductToken => ({
  kind: it.kind, ref: `kb:${it.kind}:${it.id}`, label: productName(it), model_code: it.model_code ?? undefined,
});

function Highlighted({ text, q, ranges }: { text: string; q: string; ranges?: Array<[number, number]> }) {
  const ql = q.trim().toLowerCase();
  // kb 범위는 표시명 · 모델코드 어느 쪽 기준일 수 있다 → 이 글에서 검색어와 맞는 범위만 쓴다
  let rs = ranges?.filter(([a, b]) => b > a && a >= 0 && b <= text.length && ql.includes(text.slice(a, b).toLowerCase().trim())) ?? [];
  if (!rs.length && ql) {
    const i = text.toLowerCase().indexOf(ql);
    if (i >= 0) rs = [[i, i + ql.length]];
  }
  if (!rs.length) return <>{text}</>;
  const out: ReactNode[] = [];
  let pos = 0;
  [...rs].sort((a, b) => a[0] - b[0]).forEach(([a, b], k) => {
    if (a < pos) return;
    if (a > pos) out.push(text.slice(pos, a));
    out.push(<mark key={k}>{text.slice(a, b)}</mark>);
    pos = b;
  });
  if (pos < text.length) out.push(text.slice(pos));
  return <>{out}</>;
}

/** 버블(§2.8 Bubble): matched = `#eaeefb`/brand · custom = 회색 점선. `qty` + `onQtyChange` 면 이름 뒤 `×n` 을 눌러 1~qtyMax 로 바꾼다(07-image §4.3). */
export function Bubble({ label, custom, onRemove, onClick, qty, qtyMax = 9, onQtyChange }:
  { label: string; custom?: boolean; onRemove?: () => void; onClick?: () => void; qty?: number; qtyMax?: number; onQtyChange?: (n: number) => void }) {
  const [menu, setMenu] = useState(false);
  const wrap = useRef<HTMLSpanElement>(null);
  useEscape(() => setMenu(false), menu);
  useEffect(() => {
    if (!menu) return;
    const h = (e: MouseEvent) => { if (wrap.current && !wrap.current.contains(e.target as Node)) setMenu(false); };
    document.addEventListener('mousedown', h);
    return () => document.removeEventListener('mousedown', h);
  }, [menu]);
  const showQty = qty !== undefined && !!onQtyChange;
  return (
    <span ref={wrap} className={cx('wm-bubble', custom && 'wm-bubble--custom', onClick && 'wm-bubble--clickable', showQty && 'wm-bubble--qty')}
      data-bubble={custom ? 'custom' : 'matched'} data-qty={showQty ? qty : undefined}>
      <span onClick={onClick} title={onClick ? `${label} 상세 보기` : label}>{label}</span>
      {showQty && (
        <button type="button" className="wm-bubble__qty" title="수량 바꾸기" aria-label={`${label} 수량 바꾸기`} aria-haspopup="menu" aria-expanded={menu}
          onMouseDown={(e) => e.preventDefault()} onClick={(e) => { e.stopPropagation(); setMenu((v) => !v); }}>×{qty}</button>
      )}
      {showQty && menu && (
        <span className="wm-qtymenu" role="menu" aria-label={`${label} 수량`} style={{ gridTemplateColumns: `repeat(${Math.min(qtyMax, 9)}, 26px)` }}
          onMouseDown={(e) => e.preventDefault()}>
          {Array.from({ length: qtyMax }, (_, i) => i + 1).map((n) => (
            <button key={n} type="button" role="menuitemradio" aria-checked={qty === n}
              onClick={(e) => { e.stopPropagation(); onQtyChange?.(n); setMenu(false); }}>{n}</button>
          ))}
        </span>
      )}
      {onRemove && (
        <button type="button" aria-label={`${label} 제거`} onClick={(e) => { e.stopPropagation(); onRemove(); }}>
          <Icon name="x" size={11} strokeWidth={2.6} />
        </button>
      )}
    </span>
  );
}

/** 범례: `파란 버블: …` · `점선 버블: …` */
export function ProductLegend() {
  return (
    <div className="wm-legend">
      <span><i />파란 버블: 카탈로그에서 매칭된 삼성 제품</span>
      <span><i className="wm-legend--custom" />점선 버블: 사용자가 직접 입력한 항목</span>
    </div>
  );
}

export interface ProductInputProps {
  value: ProductToken[];
  onChange: (next: ProductToken[]) => void;
  placeholder?: string;
  /** 시각 숨김 라벨(기본 `제품명 입력`, 버블이 있으면 `제품명 추가 입력`) */
  label?: string;
  /** 범례 보이기 */
  legend?: boolean;
  /** 검색 함수 바꾸기(기본 kb 제품 검색) */
  search?: (q: string, signal: AbortSignal) => Promise<ProductSearchItem[]>;
  /** 최대 결과 행(기본 5) */
  maxResults?: number;
  /** 디바운스 ms(기본 150) */
  debounceMs?: number;
  /** 결과 패널 방향(기본 위) */
  placement?: 'top' | 'bottom';
  /** 하단 입력 카드 안 크기(min-h56 r12) */
  compact?: boolean;
  autoFocus?: boolean;
  disabled?: boolean;
  /** 매칭 버블 클릭(예: 제품 상세 시트 열기) */
  onTokenClick?: (t: ProductToken) => void;
  /** 직접 입력 허용(기본 true) */
  allowCustom?: boolean;
  /** 수량 칩 — 매칭 버블에 `×n`(눌러 1~qtyMax), 새로 넣은 제품은 1(07-image §4.3 · 조감도 · 시나리오 · 제안서) */
  qty?: boolean;
  /** 수량 최대(기본 9) */
  qtyMax?: number;
  /** 결과 머리 글(기본 `"{q}" 검색 결과 · 방향키로 이동, Enter로 추가` — BE2 는 `"{q}" 검색 결과 · Enter로 추가`) */
  headText?: (q: string) => ReactNode;
  /** 결과 행 오른쪽(기본: 포커스 행만 `추가 ↵` / 이미 넣은 행 `이미 추가됨`). null 이면 비움 */
  rowCta?: (item: ProductSearchItem, added: boolean, active: boolean) => ReactNode;
}

export function ProductInput({ value, onChange, placeholder = '제품명을 입력해 추가…', label, legend, search, maxResults = 5, debounceMs = 150,
  placement = 'top', compact, autoFocus, disabled, onTokenClick, allowCustom = true, qty, qtyMax = 9, headText, rowCta }: ProductInputProps) {
  const [q, setQ] = useState('');
  const [dq, setDq] = useState('');
  const [items, setItems] = useState<ProductSearchItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [failed, setFailed] = useState(false);
  const [open, setOpen] = useState(false);
  const [focus, setFocus] = useState(false);
  const [active, setActive] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const uid = useId();
  const listId = `wm-pi-list-${uid}`;
  const inputId = `wm-pi-${uid}`;
  const searchFn = useMemo(() => search ?? ((s: string, signal: AbortSignal) => searchProducts(s, { limit: maxResults, signal })), [search, maxResults]);

  useEffect(() => {
    const t = window.setTimeout(() => setDq(q.trim()), debounceMs);
    return () => window.clearTimeout(t);
  }, [q, debounceMs]);

  const valueRef = useRef(value);
  valueRef.current = value;
  const onChangeRef = useRef(onChange);
  onChangeRef.current = onChange;
  /** 결과가 오기 전에 Enter 를 눌렀으면 결과가 오는 대로 첫 행(없으면 직접 입력)을 넣는다 */
  const pendingEnter = useRef(false);

  const has = useCallback((t: ProductToken, list: ProductToken[] = valueRef.current) =>
    list.some((v) => (t.ref && v.ref ? v.ref === t.ref : v.kind === 'custom' && t.kind === 'custom' && v.label === t.label)), []);
  const qtyRef = useRef(qty);
  qtyRef.current = qty;
  const add = useCallback((t: ProductToken) => {
    if (!has(t)) onChangeRef.current([...valueRef.current, qtyRef.current && t.kind !== 'custom' && t.qty === undefined ? { ...t, qty: 1 } : t]);
    setQ(''); setDq(''); setItems([]); setOpen(false);
    inputRef.current?.focus();
  }, [has]);
  const addCustomText = useCallback((text: string) => {
    const s = text.trim();
    if (!s || !allowCustom) return;
    add({ kind: 'custom', ref: `custom:${s}`, label: s });
  }, [add, allowCustom]);
  const addCustom = () => addCustomText(q);

  useEffect(() => {
    if (!dq) { setItems([]); setLoading(false); setFailed(false); return; }
    const ac = new AbortController();
    setLoading(true);
    setFailed(false);
    searchFn(dq, ac.signal)
      .then((r) => {
        if (ac.signal.aborted) return;
        const list = r.slice(0, maxResults);
        setItems(list); setActive(0); setLoading(false);
        if (pendingEnter.current) { pendingEnter.current = false; if (list.length) add(tokenOf(list[0])); else addCustomText(dq); }
      })
      .catch(() => {
        if (ac.signal.aborted) return;
        setItems([]); setFailed(true); setLoading(false);
        if (pendingEnter.current) { pendingEnter.current = false; addCustomText(dq); }
      });
    return () => ac.abort();
  }, [dq, searchFn, maxResults, add, addCustomText]);
  const remove = (i: number) => onChange(value.filter((_, k) => k !== i));

  const showPanel = open && q.trim().length > 0 && (dq.length > 0 || loading);
  const onKey = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.nativeEvent.isComposing) return;
    if (e.key === 'ArrowDown') { e.preventDefault(); setOpen(true); setActive((a) => Math.min(a + 1, Math.max(0, items.length - 1))); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setActive((a) => Math.max(0, a - 1)); }
    else if (e.key === 'Enter') {
      e.preventDefault();
      const cur = q.trim();
      if (!cur) return;
      if (dq === cur && !loading) {
        if (items.length) add(tokenOf(items[Math.min(active, items.length - 1)])); else addCustom();
      } else { pendingEnter.current = true; setDq(cur); }
    } else if (e.key === 'Escape') {
      if (showPanel) { e.preventDefault(); e.stopPropagation(); setOpen(false); }
    } else if (e.key === 'Backspace' && !q && value.length) {
      remove(value.length - 1);
    }
  };

  const panel = showPanel && (
    <div className={cx('wm-results', 'wm-dropdown')} id={listId} role="listbox" aria-label="제품 검색 결과"
      style={placement === 'top' ? { bottom: 'calc(100% + 14px)' } : { top: 'calc(100% + 8px)' }}
      onMouseDown={(e) => e.preventDefault()}>
      <div className="wm-results__head" data-results-head="">{headText ? headText(q.trim()) : `"${q.trim()}" 검색 결과 · 방향키로 이동, Enter로 추가`}</div>
      {loading && !items.length && <div className="wm-results__head" style={{ padding: '10px' }}>찾는 중…</div>}
      {!loading && failed && <div className="wm-results__head" style={{ padding: '10px' }}>제품을 찾지 못했어요. 잠시 뒤 다시 입력해 보세요.</div>}
      {!loading && !failed && dq && !items.length && <div className="wm-results__head" style={{ padding: '10px' }}>카탈로그에서 맞는 제품을 찾지 못했어요.</div>}
      {items.map((it, i) => {
        const name = productName(it);
        const on = i === active;
        const added = has(tokenOf(it), value);
        return (
          <button key={`${it.kind}:${it.id}`} type="button" role="option" aria-selected={on} id={`${listId}-${i}`}
            className={cx('wm-result', on && 'wm-result--active')} onMouseEnter={() => setActive(i)} onClick={() => add(tokenOf(it))}>
            <span className="wm-result__thumb"><Img src={it.thumb?.thumb_url ?? it.thumb?.stored_url} alt="" fit="contain" /></span>
            <span style={{ display: 'flex', flexDirection: 'column', gap: 1, flex: 1, minWidth: 0 }}>
              <span className="wm-result__name"><Highlighted text={name} q={q} ranges={it.highlight} /></span>
              {it.meta_line && <span className="wm-result__meta">{it.meta_line}</span>}
            </span>
            {(() => {
              const cta = rowCta ? rowCta(it, added, on) : on ? (added ? '이미 추가됨' : '추가 ↵') : null;
              return cta === null || cta === undefined || cta === false ? null : <span className="wm-result__cta">{cta}</span>;
            })()}
          </button>
        );
      })}
      {allowCustom && (
        <div className="wm-results__foot">
          <span>검색 결과에 없나요?</span>
          <button type="button" onClick={addCustom}>"{q.trim()}" 그대로 추가</button>
        </div>
      )}
    </div>
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div className="wm-tokens">
        {placement === 'top' && panel}
        <div className={cx('wm-tokens__box', compact && 'wm-tokens__box--compact', focus && 'wm-tokens__box--focus')} onClick={() => inputRef.current?.focus()}>
          {value.map((t, i) => (
            <Bubble key={`${t.ref ?? t.label}-${i}`} label={t.label} custom={t.kind === 'custom'} onRemove={disabled ? undefined : () => remove(i)}
              onClick={onTokenClick && t.kind !== 'custom' ? () => onTokenClick(t) : undefined}
              qty={qty && t.kind !== 'custom' ? (t.qty ?? 1) : undefined} qtyMax={qtyMax}
              onQtyChange={qty && !disabled ? (n) => onChange(value.map((x, k) => (k === i ? { ...x, qty: n } : x))) : undefined} />
          ))}
          <label htmlFor={inputId} className="wm-sr-only">{label ?? (value.length ? '제품명 추가 입력' : '제품명 입력')}</label>
          <input id={inputId} ref={inputRef} className="wm-tokens__input" value={q} placeholder={placeholder} autoFocus={autoFocus} disabled={disabled}
            autoComplete="off" spellCheck={false} role="combobox" aria-expanded={!!showPanel} aria-controls={listId} aria-autocomplete="list"
            aria-activedescendant={showPanel && items.length ? `${listId}-${active}` : undefined}
            onChange={(e) => { setQ(e.target.value); setOpen(true); }} onKeyDown={onKey}
            onFocus={() => { setFocus(true); setOpen(true); }} onBlur={() => { setFocus(false); setOpen(false); }} />
        </div>
        {placement === 'bottom' && panel}
      </div>
      {legend && <ProductLegend />}
    </div>
  );
}
