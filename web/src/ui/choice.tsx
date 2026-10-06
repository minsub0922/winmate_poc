/**
 * 선택 카드 · 직접 입력 줄 · Q 상자 — 질의 화면(보드 SB1Q~Q3 · SB3S · SB4U · SB4E, MI · 경쟁사 질의도 같은 모양).
 *
 *   <ChoiceCard kind="radio" pressed={v === 'a'} onClick={() => setV('a')} title="컨셉 제안" hint="Part 1 · 사업 논리" />
 *   <ChoiceCard kind="ordered" pressed={order > 0} order={order} onClick={toggle} title="컨셉 방향 합의" aside="Overview 목적" />
 *   <ChoiceCustomInput value={etc} onChange={setEtc} onCommit={addEtc} />
 */
import type { ReactNode } from 'react';
import { cx } from './controls';
import { Icon } from './icons';

export type QBadgeSize = 'xs' | 'sm' | 'md' | 'lg' | 'onPrimary';
/**
 * 질의 에이전트 표시 `Q` 상자: 흰 바탕 · brand 테두리 1.5 · Manrope 800. md 20 · sm 18 · xs 16 · lg 26.
 * 주 버튼(brand 바탕) 안에서는 `size="onPrimary"`(흰 테두리 · 흰 글자, 20).
 */
export function QBadge({ size = 'md', className, title }: { size?: QBadgeSize; className?: string; title?: string }) {
  return (
    <span className={cx('wm-q', size === 'onPrimary' ? 'wm-q--onprimary' : size !== 'md' && `wm-q--${size}`, className)} aria-hidden={title ? undefined : true} title={title}>Q</span>
  );
}

export interface ChoiceCardProps {
  pressed: boolean;
  onClick: () => void;
  /** radio = 단일(원형 라디오) · ordered = 순서 있는 복수(고르면 파란 원 순번, 아니면 빈 상자) · check = 순서 없는 복수(체크 상자) · none = 표시 없음 */
  kind?: 'radio' | 'ordered' | 'check' | 'none';
  /** ordered 일 때 순번(1부터) */
  order?: number;
  title: ReactNode;
  /** 제목 아래 한 줄(12.5px muted, 말줄임) */
  hint?: ReactNode;
  /** 제목 옆 배지(예: `<Badge tone="brand">추천</Badge>`) */
  badge?: ReactNode;
  /** 오른쪽 역할 라벨(12.5px subtle — `Overview 목적`) */
  aside?: ReactNode;
  /** 오른쪽 끝(12.5px muted, 안의 <b> 는 Manrope 15/800 숫자) */
  right?: ReactNode;
  /** 표시 뒤 40×40 아이콘 상자(SB4E `PPT` · `PDF`) */
  icon?: ReactNode;
  /** 최소 높이(기본 58, 보드 68 · 84) */
  minHeight?: number;
  /** 제목 굵기(기본: hint 가 있으면 700, 없으면 600 — 보드) */
  weight?: 600 | 700;
  disabled?: boolean;
  disabledReason?: string;
  /** 있으면 카드 아래쪽에 넓은 영역(카드가 세로로 늘어남) */
  children?: ReactNode;
  className?: string;
  id?: string;
  'data-testid'?: string;
}

function Marker({ kind, pressed, order }: { kind: ChoiceCardProps['kind']; pressed: boolean; order?: number }) {
  if (kind === 'none') return null;
  if (kind === 'radio') return <span className={cx('wm-choice__radio', pressed && 'wm-choice__radio--on')} aria-hidden="true" />;
  if (kind === 'ordered' && pressed && order) return <span className="wm-choice__ord" aria-hidden="true">{order}</span>;
  if (kind === 'check') {
    return <span className={cx('wm-choice__box', pressed && 'wm-choice__box--on')} aria-hidden="true">{pressed && <Icon name="check" size={12} strokeWidth={3} />}</span>;
  }
  return <span className="wm-choice__box" aria-hidden="true" />;
}

/**
 * 선택 카드(§SB 4.0.1): h58 r14 패딩 0 18, 선택 = 2px brand 테두리 + `--wm-shadow-choice`. `<button aria-pressed>`.
 * 순서 있는 복수는 접근 이름에 순번을 붙인다(`1번째 · 컨셉 방향 합의`).
 */
export function ChoiceCard({ pressed, onClick, kind = 'radio', order, title, hint, badge, aside, right, icon, minHeight, weight, disabled, disabledReason,
  children, className, id, ...rest }: ChoiceCardProps) {
  const w = weight ?? (hint ? 700 : 600);
  const head = (
    <>
      <Marker kind={kind} pressed={pressed} order={order} />
      {icon && <span className="wm-choice__icon" aria-hidden="true">{icon}</span>}
      <span className="wm-choice__body" style={hint || children ? undefined : { padding: 0 }}>
        <span className={cx('wm-choice__title', w === 700 && 'wm-choice__title--700')}>{title}{badge}</span>
        {hint && <span className="wm-choice__hint">{hint}</span>}
      </span>
      {aside !== undefined && aside !== null && <span className="wm-choice__aside">{aside}</span>}
      {right !== undefined && right !== null && <span className="wm-choice__right">{right}</span>}
    </>
  );
  return (
    <button type="button" id={id} className={cx('wm-choice', !!children && 'wm-choice--block', className)} aria-pressed={pressed} onClick={onClick}
      disabled={disabled} title={disabled ? disabledReason : undefined} style={minHeight ? { minHeight } : undefined} data-testid={rest['data-testid']}
      data-order={kind === 'ordered' && pressed && order ? order : undefined}>
      {children ? <><span className="wm-choice__row">{head}</span>{children}</> : head}
      {kind === 'ordered' && pressed && order ? <span className="wm-sr-only">{order}번째</span> : null}
    </button>
  );
}

/** 선택 카드 목록 묶음(간격 8) */
export function ChoiceList({ children, label }: { children: ReactNode; label?: string }) {
  return <div className="wm-choices" role="group" aria-label={label}>{children}</div>;
}

/** `직접 입력` 줄(점선, h52) — Enter 또는 포커스가 빠질 때 onCommit */
export function ChoiceCustomInput({ value, onChange, onCommit, placeholder = '직접 입력', label = '직접 입력', disabled }:
  { value: string; onChange: (v: string) => void; onCommit: () => void; placeholder?: string; label?: string; disabled?: boolean }) {
  return (
    <label className="wm-choice-custom">
      <span className="wm-choice__box wm-choice__box--dashed" aria-hidden="true" />
      <span className="wm-sr-only">{label}</span>
      <input value={value} placeholder={placeholder} disabled={disabled} onChange={(e) => onChange(e.target.value)} onBlur={onCommit}
        onKeyDown={(e) => { if (e.key === 'Enter' && !e.nativeEvent.isComposing) { e.preventDefault(); onCommit(); } }} />
    </label>
  );
}
