/**
 * 버튼 · 입력 · 칩 · 탭 · 토글 — 00-shell §2.8.
 */
import {
  forwardRef, useId, type AnchorHTMLAttributes, type ButtonHTMLAttributes, type InputHTMLAttributes, type KeyboardEvent, type ReactNode,
  type Ref, type TextareaHTMLAttributes,
} from 'react';
import { Icon } from './icons';

export const cx = (...xs: Array<string | false | null | undefined | 0>) => xs.filter(Boolean).join(' ');

// ── Button ──────────────────────────────────────────────
export type ButtonVariant = 'primary' | 'secondary' | 'dark' | 'outline' | 'ghost' | 'danger' | 'soft';
export type ButtonSize = 'xs' | 'sm' | 'md' | 'lg';
/** 보드의 버튼 높이 단계(§2.5): 26 · 28 · 32 · 34 · 36(알약) · 38 · 40 · 44 · 48 */
export type ButtonHeight = 26 | 28 | 32 | 34 | 36 | 38 | 40 | 44 | 48;

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  /** 기존 크기 이름(xs=26 · sm=32 · md=38 · lg=44). `h` 가 있으면 무시 */
  size?: ButtonSize;
  /** 보드 높이 그대로(우선) */
  h?: ButtonHeight;
  block?: boolean;
  /** 남는 폭을 채움(flex: 1) */
  grow?: boolean;
  loading?: boolean;
  icon?: ReactNode;
  /** 오른쪽 아이콘 */
  iconRight?: ReactNode;
  /** 비활성일 때 이유(§2.8 — 비활성 버튼은 title 필수) */
  disabledReason?: string;
  /** secondary 인데 글자를 brand 색으로(`+ 추가` · `"q" 그대로 추가`) */
  brandText?: boolean;
}

export const Button = forwardRef(function Button(
  { variant = 'secondary', size = 'md', h, block, grow, loading, icon, iconRight, children, className, disabledReason, brandText, title, ...rest }: ButtonProps,
  ref: Ref<HTMLButtonElement>,
) {
  const disabled = rest.disabled || loading;
  return (
    <button type="button" ref={ref} {...rest} disabled={disabled} title={disabled && disabledReason ? disabledReason : title}
      className={cx('wm-btn', variant !== 'secondary' && `wm-btn--${variant}`, h ? `wm-btn--h${h}` : `wm-btn--${size}`, block && 'wm-btn--block',
        grow && 'wm-btn--grow', brandText && 'wm-btn--brandtext', className)}>
      {loading ? <Spinner /> : icon}
      {children}
      {iconRight}
    </button>
  );
});

/** 버튼 모양 링크. 외부 주소면 새 탭 + `rel="noopener"` 를 자동으로 붙인다(§8.1 L-05). */
export function ButtonLink({ variant = 'secondary', h = 38, block, grow, icon, iconRight, external, className, children, brandText, ...rest }:
  AnchorHTMLAttributes<HTMLAnchorElement> & { variant?: ButtonVariant; h?: ButtonHeight; block?: boolean; grow?: boolean; icon?: ReactNode;
    iconRight?: ReactNode; external?: boolean; brandText?: boolean }) {
  const ext = external ?? /^https?:\/\//.test(rest.href ?? '');
  return (
    <a {...rest} target={ext ? '_blank' : rest.target} rel={ext ? 'noopener noreferrer' : rest.rel}
      className={cx('wm-btn', variant !== 'secondary' && `wm-btn--${variant}`, `wm-btn--h${h}`, block && 'wm-btn--block', grow && 'wm-btn--grow',
        brandText && 'wm-btn--brandtext', className)}>
      {icon}{children}{iconRight}
    </a>
  );
}

/** 외부 링크(새 탭 · noopener) — 글자 뒤에 ` ↗` 를 붙이려면 arrow */
export function ExternalLink({ href, children, arrow, className, ...rest }: AnchorHTMLAttributes<HTMLAnchorElement> & { arrow?: boolean }) {
  return (
    <a href={href} target="_blank" rel="noopener noreferrer" className={className} {...rest}>
      {children}{arrow && ' ↗'}
    </a>
  );
}

export function IconButton({ label, children, className, size = 32, bordered, ...rest }:
  ButtonHTMLAttributes<HTMLButtonElement> & { label: string; size?: 32 | 34; bordered?: boolean }) {
  return (
    <button type="button" aria-label={label} title={rest.title ?? label} {...rest}
      className={cx('wm-iconbtn', size === 34 && 'wm-iconbtn--34', bordered && 'wm-iconbtn--sq', className)}>
      {children}
    </button>
  );
}

export function CloseButton({ label = '닫기', size = 32, onClick }: { label?: string; size?: 32 | 34; onClick?: () => void }) {
  return (
    <IconButton label={label} size={size} onClick={onClick}>
      <Icon name="x" size={size === 34 ? 18 : 16} strokeWidth={2.2} />
    </IconButton>
  );
}

/** 항목 추가 버튼 상태(§5.2.4) */
export type AddState = 'add' | 'sel' | 'added' | 'off';
const ADD_LABEL: Record<AddState, string> = { add: '+ 추가', sel: '✓ 선택', added: '✓ 추가됨', off: '+ 추가' };

/**
 * 팝오버 4종 공통 항목 버튼. `add` 누르면 트레이에 담고, `sel` 누르면 뺀다. `added` · `off` 는 비활성.
 * aria-label: `추가 {이름}` / `선택 해제 {이름}`. title: off = `진행 중인 작업이 없어 추가할 수 없습니다`, added = `이미 현재 작업에 있습니다`.
 */
export function ItemAddButton({ state, name, onToggle, offReason = '진행 중인 작업이 없어 추가할 수 없습니다' }:
  { state: AddState; name: string; onToggle?: () => void; offReason?: string }) {
  const disabled = state === 'off' || state === 'added';
  return (
    <button type="button" className={cx('wm-addbtn', `wm-addbtn--${state}`)} disabled={disabled}
      aria-label={(state === 'sel' ? '선택 해제 ' : '추가 ') + name}
      title={state === 'off' ? offReason : state === 'added' ? '이미 현재 작업에 있습니다' : undefined}
      onClick={(e) => { e.stopPropagation(); onToggle?.(); }}>
      {ADD_LABEL[state]}
    </button>
  );
}

// ── Form ───────────────────────────────────────────────
export function Field({ label, hint, children, extra }: { label?: ReactNode; hint?: ReactNode; children: ReactNode; extra?: ReactNode }) {
  return (
    <label className="wm-field">
      {label && <span className="wm-label">{label}{extra}</span>}
      {children}
      {hint && <span className="wm-small wm-subtle">{hint}</span>}
    </label>
  );
}
export const Input = forwardRef(function Input({ className, size, ...rest }: Omit<InputHTMLAttributes<HTMLInputElement>, 'size'> & { size?: 'sm' | 'md' },
  ref: Ref<HTMLInputElement>) {
  return <input ref={ref} {...rest} className={cx('wm-input', size === 'sm' && 'wm-input--sm', className)} />;
});
export const TextArea = forwardRef(function TextArea({ className, ...rest }: TextareaHTMLAttributes<HTMLTextAreaElement>, ref: Ref<HTMLTextAreaElement>) {
  return <textarea ref={ref} {...rest} className={cx('wm-textarea', className)} />;
});
export function Select<T extends string>({ value, onChange, options, className, ...rest }:
  { value: T; onChange: (v: T) => void; options: Array<{ value: T; label: string }>; className?: string; 'aria-label'?: string }) {
  return (
    <select className={cx('wm-select', className)} value={value} onChange={(e) => onChange(e.target.value as T)} {...rest}>
      {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
    </select>
  );
}

export interface SearchFieldProps {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  autoFocus?: boolean;
  onEnter?: () => void;
  onKeyDown?: (e: KeyboardEvent<HTMLInputElement>) => void;
  /** 시각적으로 숨긴 라벨(접근 이름) */
  label?: string;
  id?: string;
  /** 흰 바탕(작업 목록 화면) — 기본은 팝오버용 회색 바탕 */
  tone?: 'gray' | 'white';
  width?: number | string;
  /** 값이 있으면 지우기 버튼 */
  clearable?: boolean;
  inputRef?: Ref<HTMLInputElement>;
}

/** 검색 입력(§2.8 SearchField): h38 r10, 돋보기 15, 13.5px, 라벨은 시각적으로 숨김 */
export function SearchField({ value, onChange, placeholder, autoFocus, onEnter, onKeyDown, label = '검색', id, tone = 'gray', width, clearable, inputRef }: SearchFieldProps) {
  const auto = useId();
  const inputId = id ?? `wm-s-${auto}`;
  return (
    <div className={cx('wm-search', tone === 'white' && 'wm-search--white')} style={width !== undefined ? { width } : undefined}>
      <label htmlFor={inputId} className="wm-sr-only">{label}</label>
      <Icon name="search" size={15} color={tone === 'white' ? 'var(--wm-text-subtle)' : 'var(--wm-text-muted)'} />
      <input id={inputId} ref={inputRef} value={value} autoFocus={autoFocus} placeholder={placeholder} autoComplete="off" spellCheck={false}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => { onKeyDown?.(e); if (e.key === 'Enter' && !e.nativeEvent.isComposing) onEnter?.(); }} />
      {clearable && value && (
        <button type="button" className="wm-search__clear" aria-label="검색어 지우기" onClick={() => onChange('')}><Icon name="x" size={13} /></button>
      )}
    </div>
  );
}

// ── Chips ──────────────────────────────────────────────
/** 필터 칩(§2.8 FilterChip): h28 r999 12px. on = brand 테두리·글자 + `#eaeefb` */
export function Chip({ on, children, onClick, title, tight, size, count, caret, disabled, className, ...rest }:
  { on?: boolean; children: ReactNode; onClick?: () => void; title?: string; tight?: boolean; size?: 'md' | 'lg'; count?: number | string;
    caret?: boolean; disabled?: boolean; className?: string; 'aria-haspopup'?: 'menu' | 'listbox' | 'true'; 'aria-expanded'?: boolean; 'aria-label'?: string }) {
  const cls = cx('wm-chip', on && 'wm-chip--on', tight && 'wm-chip--tight', size === 'lg' && 'wm-chip--lg', className);
  const inner = (
    <>
      {children}
      {count !== undefined && <span className="wm-chip__n">{count}</span>}
      {caret && <Icon name="chevronDown" size={11} strokeWidth={2.4} />}
    </>
  );
  return onClick
    ? <button type="button" title={title} className={cls} aria-pressed={rest['aria-haspopup'] ? undefined : !!on} onClick={onClick} disabled={disabled} {...rest}>{inner}</button>
    : <span title={title} className={cls}>{inner}</span>;
}
export const FilterChip = Chip;

// ── Tabs · segmented · toggle ──────────────────────────
export interface TabItem<T extends string> { value: T; label: ReactNode; count?: number | string; disabled?: boolean; id?: string }

/**
 * 밑줄 탭(§2.8 Tabs/underline). variant: `pop`(h36 12.5px) · `sheet`(h52 13.5px) · 기본(h40 13px).
 * role=tablist(+aria-label) · role=tab · aria-selected. 숫자는 Manrope.
 */
export function Tabs<T extends string>({ value, onChange, items, variant, ariaLabel, bare, className }:
  { value: T; onChange: (v: T) => void; items: Array<TabItem<T>>; variant?: 'pop' | 'sheet'; ariaLabel?: string; bare?: boolean; className?: string }) {
  const move = (e: KeyboardEvent<HTMLButtonElement>, i: number) => {
    if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
    e.preventDefault();
    const list = items.filter((x) => !x.disabled);
    const cur = list.findIndex((x) => x.value === items[i].value);
    const next = list[(cur + (e.key === 'ArrowRight' ? 1 : list.length - 1)) % list.length];
    if (next) {
      onChange(next.value);
      const el = (e.currentTarget.parentElement?.querySelector(`[data-tab="${next.value}"]`) as HTMLElement | null);
      el?.focus();
    }
  };
  return (
    <div className={cx('wm-tabs', (bare || variant) && 'wm-tabs--bare', className)} role="tablist" aria-label={ariaLabel}>
      {items.map((it, i) => (
        <button key={it.value} type="button" role="tab" id={it.id} data-tab={it.value} aria-selected={value === it.value} tabIndex={value === it.value ? 0 : -1}
          disabled={it.disabled} className={cx('wm-tab', variant && `wm-tab--${variant}`, value === it.value && 'wm-tab--on')}
          onClick={() => onChange(it.value)} onKeyDown={(e) => move(e, i)}>
          {it.label}{it.count !== undefined && it.count !== '' && <span className="wm-tab__n">{it.count}</span>}
        </button>
      ))}
    </div>
  );
}
export interface SegmentedItem<T extends string> { value: T; label: ReactNode; disabled?: boolean; title?: string }
export interface SegmentedProps<T extends string> {
  value: T;
  onChange: (v: T) => void;
  items: Array<SegmentedItem<T>>;
  /** 선택 글자색 — neutral(`--wm-text`, 기본) · brand(`--wm-brand` — SB1S · SB3R · IMG 보드) */
  tone?: 'neutral' | 'brand';
  /**
   * 버튼 높이(보드 그대로). track: 30(기본 12.5px) · 32(SB 13.5px, 선택 700) · 28(IMG 12.5px) · 24(IMG 12px) — 28 · 24 는 꺼진 글자 `--wm-text-2` 500, 선택 600.
   * line: 30(기본, 패딩 0 10) · 26(폭 30 고정 — IMG2R 강도).
   */
  h?: 24 | 26 | 28 | 30 | 32;
  /** track(회색 트랙 + 흰 선택, 기본) · line(선으로 나눈 묶음 + 선택 파랑 채움 — IMG2P 배열 · 설치, IMG2R 강도) */
  variant?: 'track' | 'line';
  /** 트랙 바탕을 한 단계 진하게(`--wm-line-disabled` — SB3R 범위 고르기) */
  trackStrong?: boolean;
  /** 묶음 접근 이름(role=group) */
  ariaLabel?: string;
  className?: string;
}
/**
 * 붙은 버튼 묶음에서 하나 고르기(`aria-pressed`). 보드별 모양은 `tone` · `h` · `variant` 로:
 *   SB1S `<Segmented tone="brand" h={32} …/>` · IMG3E 도구 `<Segmented tone="brand" h={28} …/>` · IMG2R 강도 `<Segmented variant="line" h={26} …/>`
 */
export function Segmented<T extends string>({ value, onChange, items, tone = 'neutral', h, variant = 'track', trackStrong, ariaLabel, className }: SegmentedProps<T>) {
  return (
    <div role="group" aria-label={ariaLabel}
      className={cx('wm-seg', variant === 'line' && 'wm-seg--line', tone === 'brand' && 'wm-seg--brand', h && h !== 30 && `wm-seg--h${h}`, trackStrong && 'wm-seg--strong', className)}>
      {items.map((it) => (
        <button key={it.value} type="button" aria-pressed={value === it.value} disabled={it.disabled} title={it.title} onClick={() => onChange(it.value)}>{it.label}</button>
      ))}
    </div>
  );
}
/**
 * 토글(§2.8): 트랙 28×16, 손잡이 12. role=switch. `size="lg"` = 트랙 36×22 · 손잡이 16(보드 CA2 후보 · CA3C 기준 · CA5 익명 · MI2C).
 * 글이 없으면 `label`(aria-label)만 — `<Toggle size="lg" checked={on} onChange={setOn} label="경쟁사 A 포함" />`
 */
export function Toggle({ checked, onChange, children, label, size = 'md', disabled, title }:
  { checked: boolean; onChange: (v: boolean) => void; children?: ReactNode; label?: string; size?: 'md' | 'lg'; disabled?: boolean; title?: string }) {
  const flip = () => { if (!disabled) onChange(!checked); };
  return (
    <span role="switch" tabIndex={disabled ? -1 : 0} aria-checked={checked} aria-label={label} aria-disabled={disabled || undefined} title={title}
      className={cx('wm-toggle', size === 'lg' && 'wm-toggle--lg', disabled && 'wm-toggle--off')} onClick={flip}
      onKeyDown={(e) => { if (e.key === ' ' || e.key === 'Enter') { e.preventDefault(); flip(); } }}>
      <span className="wm-toggle__track" />{children}
    </span>
  );
}

export function Spinner({ label = '불러오는 중' }: { label?: string }) { return <span className="wm-spinner" role="status" aria-label={label} />; }
