/**
 * 제안서 화면 공통 조각 — 화면 뼈대(위 내용 + 아래 카드), W 안내, 아래 카드, 요청 입력, 진행 칸 …
 * 모양은 보드 실측값(proposal.css), 색은 토큰만.
 */
import { useState, type ReactNode } from 'react';
import { Link } from 'react-router';
import { Icon, PathIcon, Skeleton, cx } from '@/ui';
import { SRC_ICON } from '../lib/catalog';

export function PrPage({ children, dock, wide, gap, testId, scrollRef, tight }:
  { children?: ReactNode; dock?: ReactNode; wide?: boolean; gap?: 14 | 22; testId?: string; scrollRef?: React.Ref<HTMLDivElement>; tight?: boolean }) {
  return (
    <div className={cx('pr-page', wide && 'pr-page--wide')} data-testid={testId}>
      <div className={cx('pr-scroll', tight && 'pr-scroll--tight')} ref={scrollRef}>
        <div className={cx('pr-col', wide && 'pr-col--wide', gap === 14 && 'pr-col--gap14')}>{children}</div>
      </div>
      {dock}
    </div>
  );
}

/** W 안내(보드: W 상자 28 + 14.5px 글) */
export function Agent({ children, text, testId }: { children?: ReactNode; text?: ReactNode; testId?: string }) {
  return (
    <div className="pr-agent">
      <div className="pr-agent__logo" aria-hidden="true">W</div>
      <div className="pr-agent__body">
        {text !== undefined && <div className="pr-agent__text" data-testid={testId ?? 'pr-agent'}>{text}</div>}
        {children}
      </div>
    </div>
  );
}

export const UserBubble = ({ children, testId }: { children: ReactNode; testId?: string }) => <div className="pr-user" data-testid={testId}>{children}</div>;

/** 아래 카드(보드 공통: 머리 「제목 · 단계」 + 오른쪽 칩, 본문, 아래 버튼 줄) */
export function Dock({ title, meta, right, children, foot, hint, testId }:
  { title?: ReactNode; meta?: ReactNode; right?: ReactNode; children?: ReactNode; foot?: ReactNode; hint?: ReactNode; testId?: string }) {
  return (
    <div className="pr-dock-wrap">
      <div className="pr-dock" data-testid={testId ?? 'pr-dock'}>
        {(title || right) && (
          <div className="pr-dock__head">
            <span className="pr-dock__title" data-testid="pr-dock-title">{title}{meta !== undefined && meta !== null && meta !== '' && <small> · {meta}</small>}</span>
            {right && <div className="pr-dock__right">{right}</div>}
          </div>
        )}
        {children && <div className="pr-dock__body">{children}</div>}
        {(foot || hint) && (
          <div className="pr-dock__foot">
            {hint !== undefined ? <div className="pr-dock__hint" title={typeof hint === 'string' ? hint : undefined}>{hint}</div> : <div style={{ flex: 1 }} />}
            {foot}
          </div>
        )}
      </div>
    </div>
  );
}

export const ArrowRight = ({ size = 16 }: { size?: number }) => <PathIcon d="M5 12h14M13 6l6 6-6 6" size={size} strokeWidth={2.2} />;
export const ChevronRight = ({ size = 12, color }: { size?: number; color?: string }) => <Icon name="chevronRight" size={size} color={color} strokeWidth={2.2} />;
export const SrcIcon = ({ kind, size = 14, color = 'var(--wm-brand)' }: { kind: string; size?: number; color?: string }) =>
  <PathIcon d={SRC_ICON[kind] ?? SRC_ICON.file} size={size} color={color} strokeWidth={2} />;
export const SpinIcon = ({ size = 14, color = 'var(--wm-brand)' }: { size?: number; color?: string }) =>
  <span className="pr-spin" style={{ display: 'inline-flex' }}><Icon name="refresh" size={size} color={color} /></span>;

/** 주 버튼(다음: …) */
export function NextButton({ children, onClick, to, disabled, disabledReason, busy, testId, arrow = true, icon }:
  { children: ReactNode; onClick?: () => void; to?: string; disabled?: boolean; disabledReason?: string; busy?: boolean; testId?: string; arrow?: boolean; icon?: ReactNode }) {
  const body = <>{busy ? <SpinIcon color="currentColor" /> : icon}<span>{children}</span>{arrow && !busy && <ArrowRight />}</>;
  if (to && !disabled) return <Link to={to} className="pr-btn pr-btn--primary" data-testid={testId}>{body}</Link>;
  return (
    <button type="button" className="pr-btn pr-btn--primary" onClick={onClick} disabled={disabled || busy} aria-disabled={disabled || undefined}
      title={disabled ? disabledReason : undefined} data-testid={testId}>{body}</button>
  );
}
export function GhostButton({ children, onClick, to, disabled, testId, icon, title }:
  { children: ReactNode; onClick?: () => void; to?: string; disabled?: boolean; testId?: string; icon?: ReactNode; title?: string }) {
  if (to && !disabled) return <Link to={to} className="pr-btn" data-testid={testId} title={title}>{icon}{children}</Link>;
  return <button type="button" className="pr-btn" onClick={onClick} disabled={disabled} data-testid={testId} title={title}>{icon}{children}</button>;
}

/** 요청 입력(보드: h44 r12 + 보내기 화살표) */
export function Prompt({ placeholder, label, onSend, busy, testId, defaultValue, inputRef }:
  { placeholder: string; label?: string; onSend: (text: string) => void | Promise<void>; busy?: boolean; testId?: string; defaultValue?: string; inputRef?: React.Ref<HTMLInputElement> }) {
  const [v, setV] = useState(defaultValue ?? '');
  const ok = v.trim().length > 0 && !busy;
  const send = async () => { if (!ok) return; const t = v.trim(); setV(''); await onSend(t); };
  return (
    <div className="pr-prompt">
      <input aria-label={label ?? placeholder} placeholder={placeholder} value={v} onChange={(e) => setV(e.target.value)} data-testid={testId} ref={inputRef}
        onKeyDown={(e) => { if (e.key === 'Enter' && !e.nativeEvent.isComposing) { e.preventDefault(); void send(); } }} />
      <button type="button" className={cx('pr-send', ok && 'pr-send--on')} aria-label="보내기" disabled={!ok} onClick={() => void send()}>
        {busy ? <SpinIcon size={13} color="currentColor" /> : <Icon name="arrowUp" size={15} strokeWidth={2.2} />}
      </button>
    </div>
  );
}

/** 진행 6칸(PR0) */
export function Segs({ done, cur, total = 6 }: { done: number; cur: number; total?: number }) {
  return (
    <span className="pr-segs" aria-label={`진행 ${done} / ${total}`}>
      {Array.from({ length: total }, (_, i) => i + 1).map((n) => <span key={n} className={cx('pr-seg', n <= done && 'pr-seg--done', n === cur && n > done && 'pr-seg--cur')} />)}
    </span>
  );
}

export function Bar({ value, warn, label }: { value: number; warn?: boolean; label?: string }) {
  const v = Math.max(0, Math.min(100, value));
  return <div className={cx('pr-bar', warn && 'pr-bar--warn')} role="progressbar" aria-valuenow={Math.round(v)} aria-valuemin={0} aria-valuemax={100} aria-label={label}><span style={{ width: `${v}%` }} /></div>;
}

export function LoadingCard({ lines = 3 }: { lines?: number }) {
  return (
    <div className="pr-card pr-card--pad" aria-busy="true" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      {Array.from({ length: lines }, (_, i) => <Skeleton key={i} h={16} w={`${90 - i * 12}%`} />)}
    </div>
  );
}

export function ErrorBand({ message, onRetry, testId }: { message: ReactNode; onRetry?: () => void; testId?: string }) {
  return (
    <div className="pr-error" role="alert" data-testid={testId ?? 'pr-error'}>
      <Icon name="warn" size={15} />
      <span className="pr-grow">{message}</span>
      {onRetry && <button type="button" className="pr-mini" onClick={onRetry}>다시 시도</button>}
    </div>
  );
}

export function CheckBox({ on }: { on: boolean }) {
  return <span className={cx('pr-check', on && 'pr-check--on')} aria-hidden="true">{on && <Icon name="check" size={11} color="var(--wm-surface)" strokeWidth={3} />}</span>;
}

export function Switch({ on, onChange, label, disabled }: { on: boolean; onChange: (v: boolean) => void; label: string; disabled?: boolean }) {
  return <button type="button" role="switch" aria-checked={on} aria-label={label} className="pr-switch" disabled={disabled} onClick={() => onChange(!on)} />;
}

/** 붙은 버튼 묶음(보드 세그먼트) */
export function SegCtl<T extends string>({ value, onChange, items, label, testId }:
  { value: T; onChange: (v: T) => void; items: Array<{ value: T; label: ReactNode; disabled?: boolean; title?: string }>; label: string; testId?: string }) {
  return (
    <div className="pr-segctl" role="radiogroup" aria-label={label} data-testid={testId}>
      {items.map((it) => (
        <button key={it.value} type="button" role="radio" aria-checked={value === it.value} disabled={it.disabled} title={it.title}
          onClick={() => !it.disabled && onChange(it.value)}>{it.label}</button>
      ))}
    </div>
  );
}

/** 「{pre}**{mark}**{post}」 문장 */
export const MarkText = ({ t, cls = 'pr-mark' }: { t?: { pre?: string; mark?: string; post?: string } | null; cls?: string }) =>
  t ? <>{t.pre}{t.mark && <span className={cls}>{t.mark}</span>}{t.post}</> : null;

/** 「…」 안 강조: `{{text}}` 의 **굵게** 부분을 굵게 */
export function Rich({ text }: { text?: string | null }) {
  if (!text) return null;
  const parts = text.split(/(\*\*[^*]+\*\*|\[[^\]]*확정 필요[^\]]*\])/g);
  return <>{parts.map((s, i) => s.startsWith('**') ? <b key={i}>{s.slice(2, -2)}</b> : /^\[.*확정 필요.*\]$/.test(s) ? <span key={i} className="pr-mark">{s}</span> : <span key={i}>{s}</span>)}</>;
}
