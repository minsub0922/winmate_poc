/**
 * DSS 화면 조각 — AI 추가기능 버튼(칸마다 보드 크기) · 출처 태그 · 제품 검색 줄(결과는 위로 열린다).
 */
import { useEffect, useRef, useState, type ReactNode } from 'react';
import { cx, searchProducts, useEscape, type ProductSearchItem } from '@/ui';
import type { By, DSAddProduct } from './api';

const STAR = 'M12 2.5l1.9 5.6 5.6 1.9-5.6 1.9L12 17.5l-1.9-5.6L4.5 10l5.6-1.9z';

/** AI 추가기능 버튼(보드 p-aib · o-aib) — size: 38 업종 · sol 솔루션 · sp 공간 · prod 공간별 제품 */
export function AiBtn({ size, onClick, busy, disabled, children }: { size: '38' | 'sol' | 'sp' | 'prod'; onClick: () => void; busy?: boolean; disabled?: boolean; children: ReactNode }) {
  const icon = size === 'sol' ? 14 : size === '38' ? 13 : 12;
  return (
    <button type="button" className={cx('ds-aib', `ds-aib--${size}`)} onClick={onClick} disabled={disabled || busy} aria-busy={busy || undefined}>
      <svg width={icon} height={icon} viewBox="0 0 24 24" fill="currentColor" aria-hidden><path d={STAR} /></svg>
      {busy ? 'AI가 찾는 중…' : children}
    </button>
  );
}

export function Star({ size = 13 }: { size?: number }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="var(--wm-brand)" aria-hidden><path d={STAR} /></svg>;
}

const BY_LABEL: Record<By, string> = { manual: '직접', 'ai-pending': 'AI 추천', 'ai-accepted': 'AI 추천 · 수락' };

/** 출처 태그(보드 tagBase) — 직접 · AI 추천(점선) · AI 추천 · 수락(초록) */
export function Tag({ by }: { by: By }) {
  return <span className={cx('ds-tag', by !== 'manual' && `ds-tag--${by}`)}>{BY_LABEL[by]}</span>;
}

export const Chevron = () => (
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden><path d="M6 9l6 6 6-6" /></svg>
);
export const XIcon = ({ size = 14 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" aria-hidden><path d="M6 6l12 12M18 6L6 18" /></svg>
);
export const ScreenIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--wm-text-muted)" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden><path d="M3 5h18v11H3z M8 20h8 M12 16v4" /></svg>
);
export const BackIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden><path d="M15 6l-6 6 6 6" /></svg>
);
export const ArrowIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden><path d="M5 12h14M13 6l6 6-6 6" /></svg>
);
export const CheckIcon = () => (
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="3.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden><path d="M5 12l5 5L20 7" /></svg>
);

/** `kb:model:mdl_<코드>` → 모델코드(상세 시트). 제품군은 대표 모델을 모른다 */
export function modelCodeOf(ref?: string | null): string | null {
  const m = /^kb:model:mdl_(.+)$/.exec(ref ?? '');
  return m ? m[1] : null;
}

/** DSS 제품 이름 — 모델도 계열명까지(보드 DS2 `Smart Signage QM55C`), 제품군은 이름 */
export const nameOf = (it: Pick<ProductSearchItem, 'display_name' | 'label'>) => (it.label || it.display_name || '').trim();

/** KB 검색 결과 → 제품 넣기 본문(근거 없는 수량 · 용도는 넣지 않는다) */
export function addBodyOf(it: ProductSearchItem): DSAddProduct {
  const cat = (it.category_path ?? []).slice(-1)[0] ?? null;
  return {
    name: nameOf(it), ref: `kb:${it.kind}:${it.id}`, model_code: it.model_code ?? null,
    family_id: it.kind === 'family' ? it.id : ((it as { family_id?: string | null }).family_id ?? null), category: cat, why: cat ? `${cat} · 직접 추가` : null,
  };
}

/**
 * 제품 추가 검색 줄(보드 DS2 아래 h38) — KB 제품 · 제품군 검색, 결과는 입력창 위로 열린다.
 * Enter: 고른 결과(없으면 첫 결과), 결과가 없으면 입력 그대로 「직접 추가 · KB 에 없음 · 확인 필요」.
 */
export function ProductSearch({ placeholder, disabled, onAdd }: { placeholder: string; disabled?: boolean; onAdd: (b: DSAddProduct) => Promise<unknown> }) {
  const [q, setQ] = useState('');
  const [rows, setRows] = useState<ProductSearchItem[]>([]);
  const [open, setOpen] = useState(false);
  const [hi, setHi] = useState(0);
  const [busy, setBusy] = useState(false);
  const wrap = useRef<HTMLDivElement>(null);
  useEscape(() => setOpen(false), open);
  useEffect(() => {
    const t = q.trim();
    if (!t) { setRows([]); return; }
    const ac = new AbortController();
    const h = setTimeout(() => {
      searchProducts(t, { limit: 6, kinds: 'model,family', signal: ac.signal }).then((r) => { setRows(r); setHi(0); }).catch(() => { /* 검색 실패는 빈 결과 */ });
    }, 220);
    return () => { clearTimeout(h); ac.abort(); };
  }, [q]);
  useEffect(() => {
    if (!open) return;
    const h = (e: MouseEvent) => { if (wrap.current && !wrap.current.contains(e.target as Node)) setOpen(false); };
    document.addEventListener('mousedown', h);
    return () => document.removeEventListener('mousedown', h);
  }, [open]);
  const t = q.trim();
  const custom = !!t && !rows.some((r) => nameOf(r) === t);
  const n = rows.length + (custom ? 1 : 0);
  const pick = async (i: number) => {
    if (busy || !t) return;
    setBusy(true);
    try {
      await onAdd(i < rows.length ? addBodyOf(rows[i]) : { name: t });
      setQ(''); setRows([]); setOpen(false);
    } finally { setBusy(false); }
  };
  return (
    <div ref={wrap} className="ds-psearch">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="var(--wm-text-subtle)" strokeWidth="2" strokeLinecap="round" aria-hidden><circle cx="11" cy="11" r="7" /><path d="M20 20l-4-4" /></svg>
      <label className="wm-sr" htmlFor="ds-add">제품 추가</label>
      <input id="ds-add" value={q} placeholder={placeholder} disabled={disabled} autoComplete="off" role="combobox" aria-expanded={open && !!t} aria-controls="ds-add-results"
        onChange={(e) => { setQ(e.target.value); setOpen(true); }} onFocus={() => setOpen(true)}
        onKeyDown={(e) => {
          if (e.key === 'ArrowDown') { e.preventDefault(); setHi((v) => Math.min(n - 1, v + 1)); }
          else if (e.key === 'ArrowUp') { e.preventDefault(); setHi((v) => Math.max(0, v - 1)); }
          else if (e.key === 'Enter' && !e.nativeEvent.isComposing) { e.preventDefault(); void pick(Math.min(hi, n - 1)); }
        }} />
      {open && !!t && (
        <div className="ds-presults" id="ds-add-results" role="listbox" aria-label="제품 검색 결과">
          <span className="ds-presults__h">“{t}” 검색 결과 · Enter로 추가</span>
          {rows.map((r, i) => (
            <button key={`${r.kind}:${r.id}`} type="button" role="option" aria-selected={hi === i} className={cx('ds-pres', hi === i && 'ds-pres--on')}
              onMouseEnter={() => setHi(i)} onClick={() => void pick(i)}>
              <span className="ds-pres__txt"><span className="ds-pres__name">{nameOf(r)}</span>
                <span className="ds-pres__meta">{r.meta_line || (r.category_path ?? []).join(' · ') || (r.kind === 'family' ? '제품군' : '모델')}{r.model_code ? ` · ${r.model_code}` : ''}</span></span>
              <span className="ds-pres__add">추가</span>
            </button>
          ))}
          {custom && (
            <button type="button" role="option" aria-selected={hi === rows.length} className={cx('ds-pres', hi === rows.length && 'ds-pres--on')}
              onMouseEnter={() => setHi(rows.length)} onClick={() => void pick(rows.length)}>
              <span className="ds-pres__txt"><span className="ds-pres__name">{t}</span><span className="ds-pres__meta">직접 추가 · KB 에 없음 · 확인 필요</span></span>
              <span className="ds-pres__add">추가</span>
            </button>
          )}
        </div>
      )}
    </div>
  );
}
