/**
 * Storyboard 화면 공용 부품 — 보드 실측(§4.0): 가운데 820 · 하단 줄(되돌아가기 · 보조 링크 · 큰 주 버튼 하나) · 선택 카드 · 배지 · 자리표시.
 * 키트(@/ui)에 없는 모양(브랜드 분할 버튼 · Q 상자 · 순서 선택 카드)은 여기서 만든다 — docs/requests/workspace.md 참고.
 */
import { Fragment, type ReactNode } from 'react';
import { Link } from 'react-router';
import { Icon, Skeleton } from '@/ui';
import type { BadgeStyle, Segment } from './lib';
import './sb.css';

export function Page({ children, variant, label }: { children: ReactNode; variant?: 'wide' | 'list' | 'center'; label?: string }) {
  return <section className={`sb-page${variant ? ` sb-page--${variant}` : ''}`} aria-label={label}>{children}</section>;
}

export function Q({ size }: { size?: 'lg' | 'btn' }) {
  return <span className={`sb-q${size ? ` sb-q--${size}` : ''}`} aria-hidden="true">Q</span>;
}

export function Head({ eyebrow, q, title, badge, actions, sub, info }: {
  eyebrow?: ReactNode; q?: boolean; title: ReactNode; badge?: ReactNode; actions?: ReactNode; sub?: ReactNode; info?: ReactNode;
}) {
  return (
    <>
      <div className="sb-head">
        {eyebrow && <span className="sb-eyebrow">{q && <Q />}{eyebrow}</span>}
        <div className="sb-head__row">
          <h1 className="sb-h1">{title}{badge}</h1>
          {actions && <span className="sb-actions">{actions}</span>}
        </div>
        {sub && <p className="sb-sub">{sub}</p>}
      </div>
      {info && <Info>{info}</Info>}
    </>
  );
}

export function Info({ children }: { children: ReactNode }) {
  return <div className="sb-info"><Icon name="info" size={14} /><span>{children}</span></div>;
}

/** 하단 줄: 왼쪽 되돌아가기 · (가운데 빈 칸) · 보조 링크 · 주 버튼 */
export function Bottom({ back, links, primary }: { back?: ReactNode; links?: ReactNode; primary?: ReactNode }) {
  return (
    <div className="sb-bottom">
      {back}
      <span className="sb-bottom__fill" />
      {links}
      {primary}
    </div>
  );
}

export function Back({ to, children, onClick, brand }: { to?: string; children: ReactNode; onClick?: () => void; brand?: boolean }) {
  const inner = <><Icon name="chevronLeft" size={14} strokeWidth={2.4} />{children}</>;
  const cls = `sb-back${brand ? ' sb-back--brand' : ''}`;
  return to ? <Link to={to} className={cls} onClick={onClick}>{inner}</Link> : <button type="button" className={cls} onClick={onClick}>{inner}</button>;
}

export function GreyLink({ to, onClick, children, disabled, disabledReason, icon }: {
  to?: string; onClick?: () => void; children: ReactNode; disabled?: boolean; disabledReason?: string; icon?: ReactNode;
}) {
  if (to && !disabled) return <Link to={to} className="sb-glink">{icon}{children}</Link>;
  return (
    <button type="button" className="sb-glink" onClick={onClick} disabled={disabled} title={disabled ? disabledReason : undefined}>
      {icon}{children}
    </button>
  );
}

export function Primary({ children, onClick, to, disabled, disabledReason, q, arrow = true, busy, type = 'button' }: {
  children: ReactNode; onClick?: () => void; to?: string; disabled?: boolean; disabledReason?: string; q?: boolean; arrow?: boolean; busy?: boolean;
  type?: 'button' | 'submit';
}) {
  const inner = (
    <>
      {q && <Q size="btn" />}
      {children}
      {busy ? <span className="wm-spinner" aria-hidden="true" style={{ width: 14, height: 14 }} /> : arrow && <Icon name="arrowRight" size={16} strokeWidth={2.2} />}
    </>
  );
  const cls = `sb-primary${q ? ' sb-primary--q' : ''}`;
  if (to && !disabled) return <Link to={to} className={cls}>{inner}</Link>;
  return (
    <button type={type} className={cls} onClick={onClick} disabled={disabled || busy} aria-busy={busy || undefined}
      title={disabled ? disabledReason : undefined}>
      {inner}
    </button>
  );
}

/** 배지 §4.0.2 */
export function SbBadge({ tone, children, title, small }: { tone: BadgeStyle | 'fill'; children: ReactNode; title?: string; small?: boolean }) {
  return <span className={`sb-badge sb-badge--${tone}${small ? ' sb-badge--sm' : ''}`} title={title}>{children}</span>;
}

/** 선택 카드 — 단일(라디오) · 순서 있는 복수(번호) */
export function Choice({ pressed, onClick, kind = 'radio', order, title, hint, badge, role, right, tall, disabled, disabledReason, weight, children, testId }: {
  pressed: boolean; onClick: () => void; kind?: 'radio' | 'ordered'; order?: number; title: ReactNode; hint?: ReactNode; badge?: ReactNode; role?: ReactNode;
  right?: ReactNode; tall?: boolean; disabled?: boolean; disabledReason?: string; weight?: 600 | 700; children?: ReactNode; testId?: string;
}) {
  const marker = kind === 'radio'
    ? <span className={`sb-radio${pressed ? ' sb-radio--on' : ''}`} aria-hidden="true" />
    : pressed && order ? <span className="sb-ord" aria-hidden="true">{order}</span> : <span className="sb-box" aria-hidden="true" />;
  return (
    <button type="button" className={`sb-choice${tall ? ' sb-choice--tall' : ''}${children ? ' sb-choice--block' : ''}`} aria-pressed={pressed} onClick={onClick}
      disabled={disabled} title={disabled ? disabledReason : undefined} data-testid={testId}>
      {children ? (
        <>
          <span className="sb-choice__row">
            {marker}
            <span className="sb-choice__body">
              <span className={`sb-choice__title${weight === 600 ? ' sb-choice__title--600' : ''}`}>{badge}{title}</span>
              {hint && <span className="sb-choice__hint">{hint}</span>}
            </span>
            {right && <span className="sb-choice__right">{right}</span>}
          </span>
          {children}
        </>
      ) : (
        <>
          {marker}
          <span className="sb-choice__body" style={hint ? undefined : { padding: 0 }}>
            <span className={`sb-choice__title${weight === 600 ? ' sb-choice__title--600' : ''}`}>{title}{badge}</span>
            {hint && <span className="sb-choice__hint">{hint}</span>}
          </span>
          {role !== undefined && <span className="sb-choice__role">{role}</span>}
          {right && <span className="sb-choice__right">{right}</span>}
        </>
      )}
    </button>
  );
}

/** 직접 입력 줄(점선) — Enter 나 포커스 아웃 때 onCommit */
export function CustomInput({ value, onChange, onCommit, placeholder = '직접 입력', label = '직접 입력' }: {
  value: string; onChange: (v: string) => void; onCommit: () => void; placeholder?: string; label?: string;
}) {
  return (
    <label className="sb-custom">
      <span className="sb-box sb-box--dashed" aria-hidden="true" />
      <span className="wm-sr-only">{label}</span>
      <input value={value} placeholder={placeholder} onChange={(e) => onChange(e.target.value)} onBlur={onCommit}
        onKeyDown={(e) => { if (e.key === 'Enter' && !e.nativeEvent.isComposing) { e.preventDefault(); onCommit(); } }} />
    </label>
  );
}

/** 브랜드 분할 버튼(SB1S · SB3R) */
export function Seg<T extends string | number>({ value, onChange, items, label }: {
  value: T; onChange: (v: T) => void; items: Array<{ value: T; label: ReactNode }>; label?: string;
}) {
  return (
    <div className="sb-seg" role="group" aria-label={label}>
      {items.map((it) => (
        <button key={String(it.value)} type="button" aria-pressed={value === it.value} onClick={() => onChange(it.value)}>{it.label}</button>
      ))}
    </div>
  );
}

/** 문장 안 자리표시 `[00]` 강조 */
export function Tok({ text }: { text: string }) {
  const parts = text.split(/(\[00\])/g);
  return <>{parts.map((p, i) => (p === '[00]' ? <span key={i} className="sb-tok">[00]</span> : <Fragment key={i}>{p}</Fragment>))}</>;
}

/** 공간 칸 문장 — AI 보탠 구간 점선 밑줄 */
export function Segs({ segments }: { segments: Segment[] }) {
  return (
    <>
      {segments.map((s, i) => (s.ai_added
        ? <span key={i} className="sb-ai" title="AI가 보탠 문장(고객 확인 전)"><Tok text={s.text} /></span>
        : <Fragment key={i}><Tok text={s.text} /></Fragment>))}
    </>
  );
}

export function SkeletonRows({ n = 4, h = 58 }: { n?: number; h?: number }) {
  return (
    <div className="sb-skel-list" aria-busy="true" aria-label="불러오는 중">
      {Array.from({ length: n }, (_, i) => <Skeleton key={i} h={h} r={14} />)}
    </div>
  );
}

/** 잡 결과를 기다리는 화면의 머리 자리(§4.0.6) */
export function LoadingHead({ title, sub }: { title: string; sub?: string }) {
  return (
    <div className="sb-head" aria-live="polite">
      <div className="sb-head__row"><h1 className="sb-h1"><span className="wm-spinner" aria-hidden="true" style={{ width: 18, height: 18 }} />{title}</h1></div>
      {sub && <p className="sb-sub">{sub}</p>}
    </div>
  );
}

export function Chevron() {
  return <span className="sb-chev"><Icon name="chevronRight" size={14} strokeWidth={2.2} /></span>;
}

/** 잡 실패 띠 + 다시 시도 */
export function FailBand({ message, onRetry, busy }: { message: string; onRetry?: () => void; busy?: boolean }) {
  return (
    <div className="sb-band sb-band--plain" role="alert">
      <Icon name="warn" size={15} />
      <span className="sb-grow">{message}</span>
      {onRetry && <button type="button" className="sb-hbtn" onClick={onRetry} disabled={busy}>다시 시도</button>}
    </div>
  );
}

/** 스토리보드를 불러오는 중 · 못 불러옴(§4.0.6) */
export function Gate({ loading, error, onRetry }: { loading: boolean; error: unknown; onRetry?: () => void }) {
  const status = (error as { status?: number } | null)?.status;
  return (
    <Page>
      {loading ? (
        <>
          <div className="sb-head"><Skeleton w="55%" h={30} r={8} /><Skeleton w="70%" h={18} r={6} /></div>
          <SkeletonRows n={4} />
        </>
      ) : status === 404 ? (
        <div className="wm-empty" role="alert">
          <strong>스토리보드를 찾을 수 없어요</strong>
          <span className="sb-muted">지워졌거나 주소가 바뀌었어요.</span>
          <Link to="/storyboard/legacy" className="wm-btn wm-btn--h36">작업 목록</Link>
        </div>
      ) : (
        <div className="wm-empty" role="alert">
          <strong>스토리보드를 불러오지 못했어요</strong>
          {onRetry && <button type="button" className="wm-btn wm-btn--h36" onClick={onRetry}>다시 시도</button>}
        </div>
      )}
    </Page>
  );
}
