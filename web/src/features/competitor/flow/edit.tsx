/**
 * 경쟁사 리스트업 화면의 작은 편집 조각 — 보드 모양은 그대로 두고, 눌러서 고친다.
 *   InlineText  글을 누르면 같은 글꼴의 입력칸(엔터 · 밖 누르기 = 저장, Esc = 취소)
 *   VerdictPill 판정 알약(보드 h22 r999) — 누르면 우위 · 비슷 · 열위 · 자료 없음 고르기
 */
import { useEffect, useRef, useState, type ReactNode } from 'react';
import { cx } from '@/ui';
import { VERDICTS, VERDICT_LABEL, type Verdict } from './api';

export type V = NonNullable<Verdict>;

export function InlineText({ value, onCommit, className, label, placeholder, display, inline, startEditing, onCancel, editValue }: {
  value: string;
  onCommit: (v: string) => void;
  className?: string;
  /** 접근 이름(‘… 고치기’) */
  label: string;
  placeholder?: string;
  /** 보이는 글(없으면 value) */
  display?: ReactNode;
  /** 문장 안에 끼는 글(inline) */
  inline?: boolean;
  /** 처음부터 입력칸(새 줄 더하기) */
  startEditing?: boolean;
  /** 입력칸에서 Esc · 빈 채로 나갈 때(새 줄 더하기를 거둔다) */
  onCancel?: () => void;
  /** 입력칸 처음 값(없으면 value) */
  editValue?: string;
}) {
  const [edit, setEdit] = useState<string | null>(startEditing ? (editValue ?? value) : null);
  const cancelled = useRef(false);
  if (edit !== null) {
    const commit = () => {
      if (cancelled.current) { cancelled.current = false; return; }
      const v = edit.replace(/\s+/g, ' ').trim();
      setEdit(null);
      if (v === (editValue ?? value).trim()) { if (!v) onCancel?.(); return; }
      onCommit(v);
    };
    return (
      <input autoFocus className={cx('caf-edin', inline && 'caf-edin--inline', className)} aria-label={label} value={edit} placeholder={placeholder}
        onChange={(e) => setEdit(e.target.value)} onBlur={commit}
        onKeyDown={(e) => {
          if (e.nativeEvent.isComposing) return;
          if (e.key === 'Enter') { e.preventDefault(); e.currentTarget.blur(); }
          if (e.key === 'Escape') { e.preventDefault(); cancelled.current = true; setEdit(null); onCancel?.(); }
        }} />
    );
  }
  const shown = display ?? value;
  return (
    <button type="button" className={cx('caf-ed', inline && 'caf-ed--inline', !value && !display && 'caf-ed--empty', className)} aria-label={`${label} 고치기`}
      title="눌러서 고치기" onClick={() => { cancelled.current = false; setEdit(editValue ?? value); }}>
      {shown || placeholder}
    </button>
  );
}

export function VerdictPill({ v, label, onPick }: { v: V; label: string; onPick: (v: V) => void }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const off = (e: MouseEvent) => { if (!ref.current?.contains(e.target as Node)) setOpen(false); };
    const esc = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false); };
    document.addEventListener('mousedown', off);
    document.addEventListener('keydown', esc);
    return () => { document.removeEventListener('mousedown', off); document.removeEventListener('keydown', esc); };
  }, [open]);
  return (
    <div ref={ref} className="caf-vwrap">
      <button type="button" className={cx('caf-pill', `caf-pill--${v}`)} aria-haspopup="menu" aria-expanded={open} aria-label={`${label} 판정 ${VERDICT_LABEL[v]} · 바꾸기`}
        onClick={() => setOpen((o) => !o)}>{VERDICT_LABEL[v]}</button>
      {open && (
        <div className="caf-vmenu" role="menu" aria-label={`${label} 판정`}>
          {VERDICTS.map((x) => (
            <button key={x} type="button" role="menuitemradio" aria-checked={x === v} className={cx('caf-pill', `caf-pill--${x}`)}
              onClick={() => { setOpen(false); if (x !== v) onPick(x); }}>{VERDICT_LABEL[x]}</button>
          ))}
        </div>
      )}
    </div>
  );
}

/** 자리표시([위키 값] · [견적 확인] · [확인 필요] · [00])가 있는 값 */
export const hasPlaceholder = (s: string | null | undefined) => !!s && s.includes('[');
