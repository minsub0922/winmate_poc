/**
 * 경쟁사 분석 본문(보드 CABody)의 작은 편집 조각 — 칸 자체는 공용 InlineInput(@/shell)을 쓰고, 여기는 고르기 · 더하기 줄만.
 *   Pick        알약 단추 + 고르기 목록(판정 우위 · 비슷 · 열위 · 자료 없음 / 주장 축) — 보드 c-pill(aria-haspopup=listbox · ▾)
 *   NewLine     「+ 추가」로 여는 빈 줄(칸 하나) — Enter · 칸을 떠나면 더하고, 비었거나 Esc 면 거둔다
 *   NewPair     「+ 기준 추가」 · 「+ 주장 추가」의 빈 줄(앞 칸 + 글 칸)
 */
import { useEffect, useLayoutEffect, useRef, useState, type ReactNode } from 'react';
import { cx } from '@/ui';
import type { Verdict } from './api';

export type V = NonNullable<Verdict>;

const Chevron = () => (
  <svg width={9} height={9} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={3} strokeLinecap="round" strokeLinejoin="round" aria-hidden><path d="M6 9l6 6 6-6" /></svg>
);

/** 알약 + 고르기 목록. className 은 알약 모양(판정 색 · 축 알약), changed 면 파란 고리(보드 CA2_Edit) */
export function Pick<T extends string>({ value, options, labelOf, label, onPick, className, optionClass, changed }: {
  value: T; options: readonly T[]; labelOf: (v: T) => string; label: string; onPick: (v: T) => void;
  className: string; optionClass?: (v: T) => string; changed?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLSpanElement>(null);
  const btn = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (!open) return;
    const off = (e: MouseEvent) => { if (!ref.current?.contains(e.target as Node)) setOpen(false); };
    const esc = (e: KeyboardEvent) => { if (e.key === 'Escape') { setOpen(false); btn.current?.focus(); } };
    document.addEventListener('mousedown', off);
    document.addEventListener('keydown', esc);
    return () => { document.removeEventListener('mousedown', off); document.removeEventListener('keydown', esc); };
  }, [open]);
  return (
    <span ref={ref} className="caf-pickwrap">
      <button ref={btn} type="button" className={cx(className, changed && 'caf-ring')} aria-haspopup="listbox" aria-expanded={open} aria-label={`${label} · ${labelOf(value)}`}
        onClick={() => setOpen((o) => !o)}>{labelOf(value)}<Chevron /></button>
      {open && (
        <span className="caf-pickmenu" role="listbox" aria-label={label}>
          {options.map((x) => (
            // 고른 뒤 포커스를 알약으로 돌린다(새 주장 줄처럼 포커스로 열림을 정하는 곳에서 줄이 닫히지 않게)
            <button key={x} type="button" role="option" aria-selected={x === value} className={cx('caf-pickopt', optionClass?.(x))}
              onClick={() => { btn.current?.focus(); setOpen(false); if (x !== value) onPick(x); }}>{labelOf(x)}</button>
          ))}
        </span>
      )}
    </span>
  );
}

/** 처음부터 입력칸이 열린 빈 줄 — 글 칸 하나 */
export function NewLine({ placeholder, label, className, onAdd, onClose }: { placeholder: string; label: string; className?: string; onAdd: (v: string) => void; onClose: () => void }) {
  const [v, setV] = useState('');
  const done = useRef(false);
  const finish = (save: boolean) => {
    if (done.current) return;
    done.current = true;
    const t = v.replace(/\s+/g, ' ').trim();
    if (save && t) onAdd(t);
    onClose();
  };
  return (
    <input autoFocus className={cx('cd-in', className)} aria-label={label} placeholder={placeholder} value={v} maxLength={300}
      onChange={(e) => setV(e.target.value)} onBlur={() => finish(true)}
      onKeyDown={(e) => {
        if (e.nativeEvent.isComposing) return;
        if (e.key === 'Enter') { e.preventDefault(); finish(true); }
        if (e.key === 'Escape') { e.preventDefault(); finish(false); }
      }} />
  );
}

/** 앞 칸(기준 이름 · 주장 축) + 글 칸으로 된 빈 줄 — 포커스가 줄을 떠나거나 Enter 면 더한다(글이 비면 거둠) */
export function NewPair({ head, text, className, onAdd, onClose }: {
  /** 앞 칸 — (값, 바꾸기) 를 받아 그린다 */
  head: (v: string, set: (v: string) => void) => ReactNode;
  text: { placeholder: string; label: string; className?: string };
  className?: string;
  onAdd: (head: string, text: string) => void;
  onClose: () => void;
}) {
  const [h, setH] = useState('');
  const [t, setT] = useState('');
  const done = useRef(false);
  const finish = (save: boolean) => {
    if (done.current) return;
    done.current = true;
    const x = t.replace(/\s+/g, ' ').trim();
    if (save && x) onAdd(h.trim(), x);
    onClose();
  };
  return (
    <div className={className} onBlur={(e) => { if (!e.currentTarget.contains(e.relatedTarget as Node | null)) finish(true); }}>
      {head(h, setH)}
      <input autoFocus className={cx('cd-in', text.className)} aria-label={text.label} placeholder={text.placeholder} value={t} maxLength={300}
        onChange={(e) => setT(e.target.value)}
        onKeyDown={(e) => {
          if (e.nativeEvent.isComposing) return;
          if (e.key === 'Enter') { e.preventDefault(); finish(true); }
          if (e.key === 'Escape') { e.preventDefault(); finish(false); }
        }} />
    </div>
  );
}

/** 여러 줄로 감기는 짧은 메모 칸(보드 비교 메모 상자) — 글 높이만큼 자라고, Enter · 칸을 떠나면 한 번 저장(Shift+Enter 줄바꿈 없음 · Esc 취소).
 *  공용 InlineInput(multiline)은 높이가 고정이라 여기서 따로 둔다(보고서: 공용 부품 요청) */
export function NoteBox({ value, onCommit, label, className, changed, placeholder, maxLength = 120 }: {
  value: string; onCommit: (v: string) => unknown; label: string; className?: string; changed?: boolean; placeholder?: string; maxLength?: number;
}) {
  const [v, setV] = useState(value);
  useEffect(() => { setV(value); }, [value]);
  const ref = useRef<HTMLTextAreaElement>(null);
  const fit = () => {
    const el = ref.current;
    if (!el) return;
    const border = el.offsetHeight - el.clientHeight;
    el.style.height = 'auto';
    el.style.height = `${el.scrollHeight + border}px`;
  };
  useLayoutEffect(fit, [v, changed]);
  useEffect(() => {
    const el = ref.current;
    if (!el || typeof ResizeObserver === 'undefined') return;
    let w = el.clientWidth;
    const ro = new ResizeObserver(() => { if (el.clientWidth !== w) { w = el.clientWidth; fit(); } });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  const commit = () => { const t = v.replace(/\s+/g, ' ').trim(); if (t !== value.trim()) void onCommit(t); };
  return (
    <textarea ref={ref} rows={1} className={cx('caf-note', changed && 'caf-note--chg', className)} aria-label={label} value={v} placeholder={placeholder} maxLength={maxLength}
      onChange={(e) => setV(e.target.value.replace(/\n/g, ' '))} onBlur={commit}
      onKeyDown={(e) => {
        if (e.nativeEvent.isComposing) return;
        if (e.key === 'Enter') { e.preventDefault(); e.currentTarget.blur(); }
        if (e.key === 'Escape') { e.preventDefault(); setV(value); requestAnimationFrame(() => ref.current?.blur()); }
      }} />
  );
}

/** 자리표시([위키 값] · [견적 확인] · [확인 필요] · [00])가 있는 값 */
export const hasPlaceholder = (s: string | null | undefined) => !!s && s.includes('[');
