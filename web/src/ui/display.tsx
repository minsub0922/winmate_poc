/**
 * 표시용 조각 — 태그 · 배지 · 칩 · 상태 · 정보 상자 · 메타 행 · 안내 · 빈 상태 · 배너 · 스켈레톤(00-shell §2.8).
 */
import type { CSSProperties, ReactNode } from 'react';
import { cx } from './controls';
import { Icon } from './icons';

export function Tag({ tone = 'brand', children, title }: { tone?: 'brand' | 'neutral' | 'ok' | 'warn' | 'danger'; children: ReactNode; title?: string }) {
  return <span title={title} className={cx('wm-tag', tone !== 'brand' && `wm-tag--${tone}`)}>{children}</span>;
}
/** 사례 제품 칩 등 중립 태그(11px `#3d4452` / `#f0f2f5` r4) */
export const NeutralTag = ({ children, title }: { children: ReactNode; title?: string }) => <Tag tone="neutral" title={title}>{children}</Tag>;

export type BadgeTone = 'brand' | 'brand-soft' | 'brandline' | 'dark' | 'darksm' | 'dashed' | 'photo' | 'product' | 'new' | 'start' | 'core' | 'ok' | 'warn' | 'ai';
/**
 * 배지(§2.8 Badge): photo(사진 위 `도입사례 사진`) · product(이미지 kind `제품`) · brand(-soft) · brandline(`1 / 8 · 정면 · 삼성 공식`)
 * · dashed(`용도 일치 · …`) · dark(`제목에 명시`) · new(`NEW`) · start(`여기서 시작`) · core(`핵심 기능`)
 */
export function Badge({ tone = 'brand', children, title, style }: { tone?: BadgeTone; children: ReactNode; title?: string; style?: CSSProperties }) {
  const t = tone === 'brand-soft' ? 'brand' : tone;
  return <span title={title} style={style} className={cx('wm-badge', `wm-badge--${t}`)}>{children}</span>;
}
/** 사이드바 그룹 개수(§2.8 CountPill) */
export function Count({ n }: { n: number | string }) { return <span className="wm-count">{n}</span>; }
export const CountPill = Count;
/** 시트 핵심 칩(h24 `#eaeefb`/`#1428a0` 12px 700) */
export function KeyChip({ children }: { children: ReactNode }) { return <span className="wm-keychip">{children}</span>; }
/** 딸깍 확정 칩 등 체크 붙은 brand 칩 */
export function CheckChip({ children }: { children: ReactNode }) {
  return <span className="wm-checkchip"><Icon name="check" size={10} strokeWidth={3} />{children}</span>;
}
/** 일치 칩(§2.8 MatchChip): on = 어두운 칩. 숫자는 Manrope 800 */
export function MatchChip({ label, n, on, onClick }: { label: string; n: number | string; on?: boolean; onClick?: () => void }) {
  const cls = cx('wm-matchchip', on && 'wm-matchchip--on');
  const inner = <>{label}<span className="wm-num">{n}</span></>;
  return onClick
    ? <button type="button" className={cls} aria-pressed={!!on} onClick={onClick}>{inner}</button>
    : <span className={cls}>{inner}</span>;
}
/** 선택 트레이 칩(§2.8 TrayChip): `{이름} ×` — × 의 aria-label 은 `선택 해제` */
export function TrayChip({ label, onRemove, removeLabel = '선택 해제' }: { label: string; onRemove?: () => void; removeLabel?: string }) {
  return (
    <span className="wm-traychip">
      {label}
      {onRemove && <button type="button" aria-label={removeLabel} onClick={onRemove}>×</button>}
    </span>
  );
}
/** 작은 칩(h22 r6) — 솔루션 기둥 항목 · 기기 관리 기능 등 */
export function MiniChip({ children, tone = 'gray' }: { children: ReactNode; tone?: 'gray' | 'line' | 'pill' }) {
  return <span className={cx('wm-minichip', tone === 'line' && 'wm-minichip--line', tone === 'pill' && 'wm-minichip--pill')}>{children}</span>;
}

/** 출처 배지 — 값이 어디서 왔는지(사용자 입력 · 파일 · KB · AI 추론 · 웹 · 확인 필요) */
export function SourceBadge({ kind, children, title }: { kind: 'user' | 'file' | 'kb' | 'ai' | 'web' | 'warn'; children: ReactNode; title?: string }) {
  return <span title={title} className={cx('wm-src', kind !== 'kb' && `wm-src--${kind}`)}>{children}</span>;
}

export type StatusTone = 'neutral' | 'brand' | 'ok' | 'warn' | 'danger' | 'dark';
/**
 * 작업 상태 알약(작업 목록 보드 RQ0 · CA0): neutral(저장됨 · 완료) · brand(진행 중 · 확인 중) · warn(업데이트 필요) · ok · danger.
 * icon: 'check' · 'spin' · 'refresh' · 'warn' 또는 직접 넘긴 노드.
 */
export function StatusBadge({ tone = 'neutral', icon, children, size = 'md', title }:
  { tone?: StatusTone; icon?: 'check' | 'spin' | 'refresh' | 'warn' | ReactNode; children: ReactNode; size?: 'md' | 'lg'; title?: string }) {
  let ic: ReactNode = icon;
  if (icon === 'check') ic = <Icon name="check" size={11} strokeWidth={3} />;
  else if (icon === 'refresh') ic = <Icon name="refresh" size={11} strokeWidth={2.6} />;
  else if (icon === 'warn') ic = <Icon name="warn" size={11} strokeWidth={2.4} />;
  else if (icon === 'spin') ic = (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" aria-hidden="true" style={{ animation: 'wm-spin 1s linear infinite' }}>
      <circle cx="12" cy="12" r="9" stroke="var(--wm-brand-sel-line)" strokeWidth="3" />
      <path d="M12 3a9 9 0 0 1 9 9" stroke="var(--wm-brand)" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
  return <span title={title} className={cx('wm-status', tone !== 'neutral' && `wm-status--${tone}`, size === 'lg' && 'wm-status--lg')}>{ic}{children}</span>;
}

/** 아바타(32 원, 성 한 글자) */
export function Avatar({ initial, size = 32, title }: { initial: string; size?: number; title?: string }) {
  return <span className="wm-avatar" title={title} style={size !== 32 ? { width: size, height: size, fontSize: Math.round(size * 0.4) } : undefined}>{initial}</span>;
}

/** 회색 정보 상자(§2.8 InfoBox): 제목 · 보조 줄 · 오른쪽 링크 */
export function InfoBox({ title, sub, action, children, style }: { title?: ReactNode; sub?: ReactNode; action?: ReactNode; children?: ReactNode; style?: CSSProperties }) {
  return (
    <div className="wm-infobox" style={style}>
      {(title || sub) && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 2, flex: 1, minWidth: 0 }}>
          {title && <span style={{ fontSize: 12.5, fontWeight: 700 }}>{title}</span>}
          {sub && <span style={{ fontSize: 11.5, color: 'var(--wm-text-muted)' }}>{sub}</span>}
        </div>
      )}
      {children}
      {action}
    </div>
  );
}

export interface MetaRow { k: string; v: ReactNode; href?: string | null; title?: string }
/**
 * 출처 메타 행(§2.8 MetaRows). variant `popover`(키 10.5px 위 · 값 아래, 이미지 정보 패널) · `sheet`(2열, 키 폭 74).
 * href 가 있으면 새 탭 링크(600 + ` ↗`).
 */
export function MetaRows({ rows, variant = 'popover' }: { rows: MetaRow[]; variant?: 'popover' | 'sheet' }) {
  return (
    <div className={cx('wm-meta', variant === 'sheet' && 'wm-meta--sheet')}>
      {rows.map((r) => (
        <div key={r.k} className="wm-meta__row" data-key={r.k}>
          <span className="wm-meta__k">{r.k}</span>
          {r.href
            ? <a className="wm-meta__v" href={r.href} target="_blank" rel="noopener noreferrer" title={r.title ?? r.href}>{r.v} ↗</a>
            : <span className="wm-meta__v" title={r.title}>{r.v}</span>}
        </div>
      ))}
    </div>
  );
}

/** 안내(§2.8 Notice(info)): 정보 아이콘 15 + 12px `#596170` lh 1.45. tone 은 기능 화면용 */
export function Notice({ tone = 'info', children, icon }: { tone?: 'info' | 'warn' | 'ok' | 'danger'; children: ReactNode; icon?: ReactNode }) {
  return (
    <div className={cx('wm-notice', tone !== 'info' && `wm-notice--${tone}`)} role={tone === 'danger' ? 'alert' : undefined}>
      {icon ?? <Icon name={tone === 'ok' ? 'check' : tone === 'warn' || tone === 'danger' ? 'warn' : 'info'} size={15} />}
      <div style={{ minWidth: 0 }}>{children}</div>
    </div>
  );
}

export function Empty({ title, children, action, size }: { title?: ReactNode; children?: ReactNode; action?: ReactNode; size?: 'md' | 'sm' }) {
  return (
    <div className={cx('wm-empty', size === 'sm' && 'wm-empty--sm')}>
      {title && <strong style={{ color: 'var(--wm-text)', fontSize: size === 'sm' ? 13 : 14 }}>{title}</strong>}
      {children}
      {action}
    </div>
  );
}

/** 오류 상태: 문구 + `다시 시도`(보드에 빨강 없음 — Q-UI-1) */
export function ErrorState({ message, onRetry }: { message: ReactNode; onRetry?: () => void }) {
  return (
    <div className="wm-empty wm-empty--sm" role="alert">
      <span style={{ fontSize: 12.5, color: 'var(--wm-text-muted)' }}>{message}</span>
      {onRetry && <button type="button" className="wm-btn wm-btn--h28" onClick={onRetry}>다시 시도</button>}
    </div>
  );
}

export function Progress({ value }: { value: number }) {
  return <div className="wm-progress" role="progressbar" aria-valuenow={value} aria-valuemin={0} aria-valuemax={100}><span style={{ width: `${Math.max(0, Math.min(100, value))}%` }} /></div>;
}

/** 자리 표시 스켈레톤(`#f0f2f5`) */
export function Skeleton({ w = '100%', h = 16, r = 8, style }: { w?: number | string; h?: number | string; r?: number; style?: CSSProperties }) {
  return <span className="wm-skel" aria-hidden="true" style={{ display: 'block', width: w, height: h, borderRadius: r, ...style }} />;
}

/**
 * 화면 안 배너(셸 보드의 결과 알림은 모두 배너 — Q-UI-2). 기본 = 드롭 완료 배너 모양(바탕 `#f5f7fd` · 테두리 brand · h40).
 * tone `info` = 작업 목록 안내(바탕 `#eaeefb` h54, 아이콘 상자).
 */
export function Banner({ tone = 'done', title, sub, action, onUndo, undoLabel = '실행 취소', icon, children }:
  { tone?: 'done' | 'info' | 'ok' | 'warn' | 'danger'; title?: ReactNode; sub?: ReactNode; action?: ReactNode; onUndo?: () => void; undoLabel?: string;
    icon?: ReactNode; children?: ReactNode }) {
  const ic = icon ?? (tone === 'info'
    ? <span className="wm-banner__icon"><Icon name="refresh" size={15} color="#fff" strokeWidth={2.2} /></span>
    : <Icon name={tone === 'warn' || tone === 'danger' ? 'warn' : 'check'} size={14} strokeWidth={2.8}
        color={tone === 'warn' ? 'var(--wm-warn)' : tone === 'danger' ? 'var(--wm-danger)' : tone === 'ok' ? 'var(--wm-ok)' : 'var(--wm-brand)'} />);
  return (
    <div className={cx('wm-banner', tone !== 'done' && `wm-banner--${tone}`)} role="status">
      {ic}
      <span className="wm-banner__text">{title && <b>{title}</b>}{title && sub ? ' ' : ''}{sub && <span className="wm-banner__sub">{sub}</span>}{children}</span>
      {action}
      {onUndo && <button type="button" className="wm-btn wm-btn--h26 wm-btn--brandtext" style={{ padding: '0 10px' }} onClick={onUndo}>{undoLabel}</button>}
    </div>
  );
}
