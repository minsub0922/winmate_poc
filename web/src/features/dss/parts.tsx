/**
 * DSS 화면 조각 — 출처 태그(보드 DSBody tagBase) · 아이콘 · KB 참조 도우미 · 공간 카드 안 제품 찾기(보드 DSBody `sp.searching`).
 */
import { useEffect, useRef, useState } from 'react';
import { cx, searchProducts, useEscape, type ProductSearchItem } from '@/ui';
import type { By, DSAddProduct, DSCandidate } from './api';

/** 출처 태그(보드 DSBody tagBase h20 · 10.5/700): 직접(선) · AI(초록) · AI 점선 — 업종 「AI 추론」, 솔루션 「AI 추천」처럼 글은 자리마다 다르다 */
export function ByTag({ by, children }: { by: By; children?: string }) {
  const label = children ?? (by === 'manual' ? '직접' : 'AI');
  return <span className={cx('ds-by', by === 'manual' ? 'ds-by--man' : by === 'ai-pending' ? 'ds-by--pend' : 'ds-by--ai')}>{label}</span>;
}

export const Chevron = () => (
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden><path d="M6 9l6 6 6-6" /></svg>
);
/** × (보드: 공간 11 · 2.6 · 제품 10 · 2.8 · 솔루션 10 · 2.8) */
export const XIcon = ({ size = 11, w = 2.6 }: { size?: number; w?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={w} strokeLinecap="round" aria-hidden><path d="M6 6l12 12M18 6L6 18" /></svg>
);
export const CheckIcon = () => (
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="3.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden><path d="M5 12l5 5L20 7" /></svg>
);
export const STAR = 'M12 2.5l1.9 5.6 5.6 1.9-5.6 1.9L12 17.5l-1.9-5.6L4.5 10l5.6-1.9z';

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

interface Row { key: string; name: string; meta: string; body: DSAddProduct }

/**
 * 공간 카드 안 제품 찾기(보드 DSBody `+ 제품` → 검색 칸 h30 · 「제품 탐색」) — 비어 있으면 그 공간의 KB 추천(S1 후보),
 * 쓰면 KB 제품 · 제품군 검색. 결과는 칸 아래(카드 안)에 줄로 — 스크롤 칸에 잘리지 않게. 결과가 없으면 입력 그대로 「직접 추가 · KB 에 없음 · 확인 필요」.
 * Enter 고른 줄(없으면 첫 줄) · ↑↓ · Esc 닫기 · 카드 밖을 누르면 닫힌다.
 */
export function CardSearch({ id, space, candidates, onAdd, onPicker, onClose }: {
  id: string; space: string; candidates?: DSCandidate[]; onAdd: (b: DSAddProduct) => Promise<unknown>; onPicker: () => void; onClose: () => void;
}) {
  const [q, setQ] = useState('');
  const [found, setFound] = useState<ProductSearchItem[]>([]);
  const [hi, setHi] = useState(0);
  const [busy, setBusy] = useState(false);
  const wrap = useRef<HTMLDivElement>(null);
  useEscape(onClose);
  useEffect(() => {
    const t = q.trim();
    if (!t) { setFound([]); return; }
    const ac = new AbortController();
    const h = setTimeout(() => {
      searchProducts(t, { limit: 5, kinds: 'model,family', signal: ac.signal }).then((r) => { setFound(r); setHi(0); }).catch(() => { /* 검색 실패는 빈 결과 */ });
    }, 220);
    return () => { clearTimeout(h); ac.abort(); };
  }, [q]);
  useEffect(() => {
    const h = (e: MouseEvent) => { if (wrap.current && !wrap.current.contains(e.target as Node)) onClose(); };
    document.addEventListener('mousedown', h);
    return () => document.removeEventListener('mousedown', h);
  }, [onClose]);
  const t = q.trim();
  const rows: Row[] = t
    ? found.map((r) => ({ key: `${r.kind}:${r.id}`, name: nameOf(r), meta: `${r.meta_line || (r.category_path ?? []).join(' · ') || (r.kind === 'family' ? '제품군' : '모델')}${r.model_code ? ` · ${r.model_code}` : ''}`, body: addBodyOf(r) }))
    : (candidates ?? []).map((c) => ({ key: `kb:${c.ref ?? c.name}`, name: c.name, meta: c.why || c.category || 'KB 추천',
      body: { name: c.name, ref: c.ref, model_code: c.model_code, family_id: c.family_id, category: c.category, why: c.why } }));
  if (t && !rows.some((r) => r.name === t)) rows.push({ key: 'custom', name: t, meta: '직접 추가 · KB 에 없음 · 확인 필요', body: { name: t } });
  const pick = async (i: number) => {
    const r = rows[i];
    if (busy || !r) return;
    setBusy(true);
    try { await onAdd(r.body); setQ(''); setFound([]); } finally { setBusy(false); }
  };
  return (
    <div ref={wrap} className="ds-csearch">
      <span className="ds-csearch__box">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="var(--wm-text-muted)" strokeWidth="2.4" strokeLinecap="round" aria-hidden><circle cx="11" cy="11" r="7" /><path d="M20 20l-4-4" /></svg>
        <label className="cd-sr" htmlFor={id}>{space}에 제품 추가</label>
        <input id={id} autoFocus value={q} placeholder="모델명 · 용도로 찾기" autoComplete="off" role="combobox" aria-expanded={rows.length > 0} aria-controls={`${id}-rows`}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'ArrowDown') { e.preventDefault(); setHi((v) => Math.min(rows.length - 1, v + 1)); }
            else if (e.key === 'ArrowUp') { e.preventDefault(); setHi((v) => Math.max(0, v - 1)); }
            else if (e.key === 'Enter' && !e.nativeEvent.isComposing) { e.preventDefault(); void pick(Math.min(hi, rows.length - 1)); }
          }} />
        <button type="button" className="ds-csearch__pick" onClick={onPicker}>제품 탐색</button>
      </span>
      {rows.length > 0 && (
        <div className="ds-cres" id={`${id}-rows`} role="listbox" aria-label={`${space} 제품 찾기 결과`}>
          <span className="ds-cres__h">{t ? `“${t}” · Enter로 추가` : `KB 추천 · ${space}`}</span>
          {rows.map((r, i) => (
            <button key={r.key} type="button" role="option" aria-selected={hi === i} className={cx('ds-cres__row', hi === i && 'ds-cres__row--on')}
              onMouseEnter={() => setHi(i)} onClick={() => void pick(i)} disabled={busy}>
              <span className="ds-cres__name">{r.name}</span><span className="ds-cres__meta">{r.meta}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
