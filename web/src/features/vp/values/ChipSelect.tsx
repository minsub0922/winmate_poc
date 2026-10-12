/**
 * 칩 고르기(보드 VPBody 공간 칩 · 연결 요구 칩 — `aria-haspopup="listbox"` · h26 · ▾) — 누르면 바로 아래에 고를 것 목록, 고르는 즉시 저장.
 * 목록은 body 에 띄운다(본문 패널이 스크롤돼도 잘리지 않게) · 밖을 누르거나 스크롤 · Esc 면 닫는다. custom 을 주면 맨 아래에 직접 쓰는 칸.
 */
import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { cx } from '@/ui';

export function ChipSelect({ label, value, options, onPick, tone, placeholder, changed, custom, disabled }: {
  label: string;
  value: string | null;
  options: Array<{ value: string; label?: string }>;
  onPick: (v: string) => void;
  tone: 'space' | 'req';
  placeholder: string;
  changed?: boolean;
  /** 직접 쓰는 칸의 안내 글(없으면 칸 없음) */
  custom?: string;
  disabled?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [pos, setPos] = useState<{ left: number; top: number; minW: number } | null>(null);
  const [text, setText] = useState('');
  const btn = useRef<HTMLButtonElement>(null);
  const pop = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const outside = (e: Event) => {
      const t = e.target as Node;
      if (pop.current?.contains(t) || btn.current?.contains(t)) return;
      setOpen(false);
    };
    const onScroll = (e: Event) => { if (!pop.current?.contains(e.target as Node)) setOpen(false); };
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') { e.stopPropagation(); setOpen(false); btn.current?.focus(); } };
    document.addEventListener('mousedown', outside);
    window.addEventListener('scroll', onScroll, true);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', outside);
      window.removeEventListener('scroll', onScroll, true);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  // 화면 아래가 모자라면 위로 띄운다
  useLayoutEffect(() => {
    if (!open || !pop.current || !btn.current || !pos) return;
    const h = pop.current.offsetHeight;
    const r = btn.current.getBoundingClientRect();
    if (r.bottom + 4 + h > window.innerHeight - 8 && r.top - 4 - h > 8) setPos({ ...pos, top: r.top - 4 - h });
    (pop.current.querySelector('[aria-selected="true"]') as HTMLElement | null ?? pop.current.querySelector('button, input') as HTMLElement | null)?.focus();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- 열 때 한 번만 자리를 잡는다
  }, [open]);

  const toggle = () => {
    if (disabled) return;
    if (!open && btn.current) {
      const r = btn.current.getBoundingClientRect();
      setPos({ left: r.left, top: r.bottom + 4, minW: Math.max(r.width, 180) });
      setText('');
    }
    setOpen((o) => !o);
  };
  const pick = (v: string) => {
    setOpen(false);
    btn.current?.focus();
    if (v !== (value ?? '')) onPick(v);
  };

  return (
    <>
      <button ref={btn} type="button" className={cx('vb-chip', `vb-chip--${tone}`, !value && 'vb-chip--empty', changed && 'vb-chip--chg')}
        aria-haspopup="listbox" aria-expanded={open} aria-label={`${label} · ${value || '없음'}`} onClick={toggle} disabled={disabled} title={value ?? undefined}>
        <span className="vb-chip__t">{value || placeholder}</span>
        <svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" aria-hidden><path d="M6 9l6 6 6-6" /></svg>
      </button>
      {open && pos && createPortal(
        <div ref={pop} className="vb-pop" role="listbox" aria-label={label} style={{ left: pos.left, top: pos.top, minWidth: pos.minW }}>
          {options.map((o) => (
            <button key={o.value || '∅'} type="button" role="option" aria-selected={o.value === (value ?? '')} className={cx('vb-pop__opt', o.value === (value ?? '') && 'vb-pop__opt--on')}
              onClick={() => pick(o.value)}>{o.label ?? o.value}</button>
          ))}
          {custom && (
            <input className="vb-pop__in" aria-label={`${label} 직접 쓰기`} value={text} placeholder={custom} maxLength={120}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && !e.nativeEvent.isComposing && text.trim()) pick(text.trim()); }} />
          )}
        </div>,
        document.body,
      )}
    </>
  );
}
