/**
 * 공간 시나리오 화면 부품 — 화면 틀(W 말풍선 + 메아리 + 아래 작업 카드), 버튼 · 칩 · 메뉴 · 상태 아이콘 · 입력 줄.
 * 키트(@/ui)에 없는 보드 모양만 여기 둔다(docs/requests/workspace.md 참고).
 */
import { useEffect, useRef, useState, type ReactNode } from 'react';
import { Link } from 'react-router';
import { cx, Icon, PathIcon } from '@/ui';
import { splitTokens } from './lib';

export const P = {
  arrow: 'M5 12h14M13 6l6 6-6 6',
  play: 'M4 6h16v12H4z M10 9l5 3-5 3V9z',
  grid: 'M4 4h7v7H4z M13 4h7v7h-7z M4 13h7v7H4z M13 13h7v7h-7z',
  cube: 'M12 3l8 4.5v9L12 21l-8-4.5v-9L12 3z M12 12l8-4.5 M12 12v9 M12 12L4 7.5',
  pencil: 'M4 20h4L19 9l-4-4L4 16v4z',
  send: 'M4 12l16-8-6 16-3-7-7-1z',
  warn: 'M12 3l9.5 17h-19L12 3z M12 10v4 M12 17v.5',
  check: 'M5 12l5 5L20 7',
  x: 'M6 6l12 12M18 6L6 18',
  pin: 'M12 21s-6-5.5-6-11a6 6 0 0 1 12 0c0 5.5-6 11-6 11z M12 8a2 2 0 1 0 0 4a2 2 0 1 0 0-4',
  user: 'M12 4a4 4 0 1 0 0 8a4 4 0 1 0 0-8 M4 21c1.5-4 4.5-6 8-6s6.5 2 8 6',
  plus: 'M12 5v14M5 12h14',
  undo: 'M9 14L4 9l5-5 M4 9h11a5 5 0 0 1 0 10h-3',
  redo: 'M15 14l5-5-5-5 M20 9H9a5 5 0 0 0 0 10h3',
  image: 'M4 5h16v14H4z M4 16l5-5 4 4 3-3 4 4 M15 9.5a1 1 0 1 0 0-.01',
  sparkle: 'M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8L12 3z',
  down: 'M6 9l6 6 6-6',
  file: 'M6 3h8l5 5v13H6z M14 3v5h5',
  download: 'M12 4v11 M7 10l5 5 5-5 M5 20h14',
  share: 'M16 6l-4-4-4 4 M12 2v13 M5 12v7h14v-7',
  stop: 'M7 7h10v10H7z',
  refresh: 'M20 11a8 8 0 1 0-2.3 5.7 M20 4v7h-7',
  link: 'M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1 M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1',
  drag: 'M9 6h.01M15 6h.01M9 12h.01M15 12h.01M9 18h.01M15 18h.01',
  trash: 'M4 7h16 M10 11v6 M14 11v6 M6 7l1 13h10l1-13 M9 7V4h6v3',
};

export const Ico = ({ d, size = 16, color, sw = 2, style }: { d: string; size?: number; color?: string; sw?: number; style?: React.CSSProperties }) =>
  <PathIcon d={d} size={size} color={color} strokeWidth={sw} style={style} />;

/** 화면 틀 — 위는 스크롤되는 대화 열, 아래는 작업 카드(dock) */
export function Screen({ children, dock, wide, tight, testId, scrollRef }:
  { children: ReactNode; dock?: ReactNode; wide?: boolean; tight?: boolean; testId?: string; scrollRef?: React.Ref<HTMLDivElement> }) {
  return (
    <section className="sc-screen" data-testid={testId}>
      <div className={cx('sc-scroll', tight && 'sc-scroll--tight')} ref={scrollRef}>
        <div className={cx('sc-col', wide && 'sc-col--wide')}>{children}</div>
      </div>
      {dock && <div className="sc-dock">{dock}</div>}
    </section>
  );
}

/** 사용자 입력 메아리(오른쪽 말풍선) */
export function Echo({ children, testId }: { children: ReactNode; testId?: string }) {
  return <div className="sc-echo-row"><div className="sc-echo" data-testid={testId}>{children}</div></div>;
}

/** W 말풍선 */
export function W({ children, extra, testId }: { children: ReactNode; extra?: ReactNode; testId?: string }) {
  return (
    <div className="sc-w">
      <span className="sc-w__logo" aria-hidden="true">W</span>
      <div className="sc-w__body">
        <div className="sc-w__text" data-testid={testId}>{children}</div>
        {extra}
      </div>
    </div>
  );
}

/** 아래 작업 카드(800 r18) */
export function Card({ title, meta, right, children, foot, footLeft, wide, testId, className }:
  { title?: ReactNode; meta?: ReactNode; right?: ReactNode; children?: ReactNode; foot?: ReactNode; footLeft?: ReactNode; wide?: boolean; testId?: string; className?: string }) {
  return (
    <div className={cx('sc-card', wide && 'sc-card--wide', className)} data-testid={testId}>
      {(title || right) && (
        <div className="sc-card__head">
          <div className="sc-card__title">{title}{meta && <small> · {meta}</small>}</div>
          {right}
        </div>
      )}
      {children}
      {(foot || footLeft) && (
        <div className={cx('sc-card__foot', footLeft ? 'sc-card__foot--split' : undefined)}>
          {footLeft && <div className="sc-grow">{footLeft}</div>}
          {foot && <div className="sc-row" style={{ flexShrink: 0 }}>{foot}</div>}
        </div>
      )}
    </div>
  );
}

/** 주 버튼(→ 화살표) */
export function NextButton({ children, onClick, disabled, reason, busy, to, testId, arrow = true }:
  { children: ReactNode; onClick?: () => void; disabled?: boolean; reason?: string; busy?: boolean; to?: string; testId?: string; arrow?: boolean }) {
  const inner = <><span>{children}</span>{busy ? <span className="wm-spinner" aria-hidden="true" style={{ width: 14, height: 14 }} /> : arrow && <Ico d={P.arrow} size={16} sw={2.2} />}</>;
  if (to && !disabled) return <Link to={to} className="sc-btn sc-btn--primary" data-testid={testId}>{inner}</Link>;
  return (
    <button type="button" className="sc-btn sc-btn--primary" onClick={onClick} disabled={disabled || busy} title={disabled ? reason : undefined} data-testid={testId}
      aria-busy={busy || undefined}>
      {inner}
    </button>
  );
}

export function Btn({ children, onClick, disabled, reason, to, testId, size, brand, icon }:
  { children: ReactNode; onClick?: () => void; disabled?: boolean; reason?: string; to?: string; testId?: string; size?: 'sm' | 'xs'; brand?: boolean; icon?: ReactNode }) {
  const cls = cx('sc-btn', size === 'sm' && 'sc-btn--sm', size === 'xs' && 'sc-btn--xs', brand && 'sc-btn--brand');
  if (to && !disabled) return <Link to={to} className={cls} data-testid={testId}>{icon}{children}</Link>;
  return <button type="button" className={cls} onClick={onClick} disabled={disabled} title={disabled ? reason : undefined} data-testid={testId}>{icon}{children}</button>;
}

/** 지울 수 있는 칩(「점장 ×」) */
export function ChipX({ label, onRemove, removeLabel = '제거', isNew, tone, testId, title }:
  { label: ReactNode; onRemove?: () => void; removeLabel?: string; isNew?: boolean; tone?: 'gray' | 'brand'; testId?: string; title?: string }) {
  return (
    <span className={cx('sc-chip', tone === 'gray' && 'sc-chip--gray', !onRemove && 'sc-chip--plain')} data-testid={testId} title={title}>
      {label}
      {isNew && <span className="sc-chip__new">새로</span>}
      {onRemove && (
        <button type="button" className="sc-chip__x" aria-label={`${removeLabel} ${typeof label === 'string' ? label : ''}`.trim()} onClick={onRemove}>
          <Icon name="x" size={11} strokeWidth={2.6} />
        </button>
      )}
    </span>
  );
}

/** 바깥을 누르면 닫히는 메뉴 */
export function useOutside<T extends HTMLElement>(open: boolean, onClose: () => void) {
  const ref = useRef<T>(null);
  const cb = useRef(onClose);
  cb.current = onClose;
  useEffect(() => {
    if (!open) return;
    const down = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) cb.current(); };
    const key = (e: KeyboardEvent) => { if (e.key === 'Escape') cb.current(); };
    document.addEventListener('mousedown', down);
    document.addEventListener('keydown', key);
    return () => { document.removeEventListener('mousedown', down); document.removeEventListener('keydown', key); };
  }, [open]);
  return ref;
}

/** 드롭다운(「시작 방식 · 전체」 · 「최근 수정순」) */
export function Dropdown<T extends string>({ label, value, options, onChange, testId, up }:
  { label: string; value: T; options: Array<{ value: T; label: string }>; onChange: (v: T) => void; testId?: string; up?: boolean }) {
  const [open, setOpen] = useState(false);
  const ref = useOutside<HTMLDivElement>(open, () => setOpen(false));
  return (
    <div className="sc-menuwrap" ref={ref}>
      <button type="button" className="sc-dd" aria-haspopup="menu" aria-expanded={open} onClick={() => setOpen(!open)} data-testid={testId}>
        {label}<Ico d={P.down} size={11} sw={2.4} color="var(--wm-text-muted)" />
      </button>
      {open && (
        <div className={cx('sc-menu', up && 'sc-menu--up')} role="menu">
          {options.map((o) => (
            <button key={o.value} type="button" role="menuitemradio" aria-checked={o.value === value} onClick={() => { onChange(o.value); setOpen(false); }}>{o.label}</button>
          ))}
        </div>
      )}
    </div>
  );
}

/** 「더 보기」 메뉴 */
export function MoreMenu({ items, label = '더 보기', testId }:
  { items: Array<{ label: string; onClick: () => void; danger?: boolean; disabled?: boolean }>; label?: string; testId?: string }) {
  const [open, setOpen] = useState(false);
  const ref = useOutside<HTMLDivElement>(open, () => setOpen(false));
  return (
    <div className="sc-menuwrap" ref={ref}>
      <button type="button" className="sc-iconbtn" aria-label={label} aria-haspopup="menu" aria-expanded={open} onClick={() => setOpen(!open)} data-testid={testId}>
        <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><circle cx="5" cy="12" r="1.8" /><circle cx="12" cy="12" r="1.8" /><circle cx="19" cy="12" r="1.8" /></svg>
      </button>
      {open && (
        <div className="sc-menu" role="menu">
          {items.map((it) => (
            <button key={it.label} type="button" role="menuitem" disabled={it.disabled} className={it.danger ? 'sc-menu__danger' : undefined}
              onClick={() => { setOpen(false); it.onClick(); }}>{it.label}</button>
          ))}
        </div>
      )}
    </div>
  );
}

/** 상태 아이콘(SC0 표 · SC4G 단계): done(파란 체크) · draft(검은 호) · gen(파란 호, 돎) · wait(빈 원) */
export function StatusIcon({ kind, size = 16 }: { kind: 'done' | 'draft' | 'gen' | 'wait' | 'failed'; size?: number }) {
  if (kind === 'done') {
    return <span className="sc-stat sc-stat--done" style={{ width: size, height: size }}><Ico d={P.check} size={size * 0.62} sw={3.2} /></span>;
  }
  if (kind === 'failed') return <Ico d={P.warn} size={size} sw={2.2} color="var(--wm-warn)" />;
  if (kind === 'wait') {
    return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true" style={{ flexShrink: 0 }}><circle cx="12" cy="12" r="9" className="sc-ring-bg--soft" strokeWidth="2.4" /></svg>;
  }
  const gen = kind === 'gen';
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true" className={gen ? 'sc-spin' : undefined} style={{ flexShrink: 0 }}>
      <circle cx="12" cy="12" r="9" className={gen ? 'sc-ring-bg--soft' : 'sc-ring-bg'} strokeWidth="2.4" />
      <path d={gen ? 'M12 3a9 9 0 0 1 8.5 12' : 'M12 3a9 9 0 0 1 9 9'} className={gen ? 'sc-ring-fg--brand' : 'sc-ring-fg'} strokeWidth="2.4" strokeLinecap="round" />
    </svg>
  );
}

/** 입력 줄 + 보내기(수정 요청 · 편집 요청 · 메모 · 지시) */
export function Ask({ label, placeholder, onSubmit, sendLabel, disabled, busy, testId, id, maxLength = 1000 }:
  { label: string; placeholder: string; onSubmit: (text: string) => Promise<unknown> | unknown; sendLabel?: string; disabled?: boolean; busy?: boolean; testId?: string; id: string; maxLength?: number }) {
  const [v, setV] = useState('');
  const [pending, setPending] = useState(false);
  const submit = async () => {
    const t = v.trim();
    if (!t || disabled || pending) return;
    setPending(true);
    try { await onSubmit(t); setV(''); } finally { setPending(false); }
  };
  const off = !v.trim() || disabled || pending || busy;
  return (
    <div className="sc-ask" data-testid={testId}>
      <label htmlFor={id} className="wm-sr-only">{label}</label>
      <input id={id} value={v} onChange={(e) => setV(e.target.value)} placeholder={placeholder} maxLength={maxLength} disabled={disabled} autoComplete="off"
        onKeyDown={(e) => { if (e.key === 'Enter' && !e.nativeEvent.isComposing) { e.preventDefault(); void submit(); } }} />
      <button type="button" className="sc-ask__send" aria-label={sendLabel ?? `${label} 보내기`} disabled={off} onClick={() => void submit()}>
        {pending || busy ? <span className="wm-spinner" aria-hidden="true" style={{ width: 14, height: 14 }} /> : <Icon name="send" size={15} strokeWidth={2.4} />}
      </button>
    </div>
  );
}

/** `[00]` · `[확정 필요]` 강조 */
export function Marked({ text }: { text: string }) {
  return <>{splitTokens(text).map((p, i) => (p.mark ? <mark key={i} className="sc-mark">{p.t}</mark> : <span key={i}>{p.t}</span>))}</>;
}

/** 작은 알림 줄(성공 · 경고 · 오류) */
export function Note({ tone = 'info', children, testId, onClose }: { tone?: 'info' | 'ok' | 'warn' | 'err'; children: ReactNode; testId?: string; onClose?: () => void }) {
  return (
    <div className={cx('sc-banner', tone === 'ok' && 'sc-banner--ok', tone === 'warn' && 'sc-banner--warn', tone === 'err' && 'sc-banner--err')} role={tone === 'err' ? 'alert' : 'status'}
      data-testid={testId}>
      <span className="sc-grow">{children}</span>
      {onClose && <button type="button" className="sc-iconbtn" aria-label="닫기" onClick={onClose}><Icon name="x" size={12} strokeWidth={2.6} /></button>}
    </div>
  );
}

/** 불러오는 중(화면 가운데) */
export function Loading({ label = '불러오는 중' }: { label?: string }) {
  return <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 40 }}><span className="wm-spinner" aria-label={label} /></div>;
}
