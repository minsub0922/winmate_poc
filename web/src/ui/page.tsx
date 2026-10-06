/**
 * 화면 뼈대 — 작업 목록(보드 RQ0 · CA0 · MI0 · SP0), 섹션 카드, 하단 입력 카드(Composer, SP1Product 등 89개 보드).
 */
import { Fragment, type CSSProperties, type ReactNode } from 'react';
import { Link } from 'react-router';
import { Chip, cx, SearchField } from './controls';
import { Skeleton } from './display';
import { Icon } from './icons';

/** 화면 머리: 제목(22/700) · 설명(12.5) · 오른쪽 주 버튼 */
export function PageHeader({ title, desc, actions, level = 1 }: { title: ReactNode; desc?: ReactNode; actions?: ReactNode; level?: 1 | 2 }) {
  const H = level === 1 ? 'h1' : 'h2';
  return (
    <div className="wm-pagehead">
      <div style={{ display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        <H className="wm-pagehead__title">{title}</H>
        {desc && <div className="wm-pagehead__desc">{desc}</div>}
      </div>
      {actions && <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>{actions}</div>}
    </div>
  );
}

/** `+ 새 …` 주 버튼(링크). 보드: h44(RQ0) · h48(CA0) r12 14px 700 */
export function NewButton({ to, children, onClick, h = 44 }: { to?: string; children: ReactNode; onClick?: () => void; h?: 44 | 48 }) {
  const style: CSSProperties = { fontSize: 14, fontWeight: 700, gap: 7 };
  const inner = <><Icon name="plus" size={15} strokeWidth={2.4} />{children}</>;
  return to
    ? <Link to={to} className={cx('wm-btn wm-btn--primary', `wm-btn--h${h}`)} style={style} onClick={onClick}>{inner}</Link>
    : <button type="button" className={cx('wm-btn wm-btn--primary', `wm-btn--h${h}`)} style={style} onClick={onClick}>{inner}</button>;
}

export interface FilterTab<T extends string> { value: T; label: string; count?: number }
/** 상태 필터 알약(h34, 숫자 Manrope) — role=tablist */
export function FilterTabs<T extends string>({ value, onChange, items, ariaLabel = '상태' }: { value: T; onChange: (v: T) => void; items: Array<FilterTab<T>>; ariaLabel?: string }) {
  return (
    <div role="tablist" aria-label={ariaLabel} style={{ display: 'flex', gap: 6 }}>
      {items.map((it) => (
        <button key={it.value} type="button" role="tab" aria-selected={value === it.value} className={cx('wm-chip wm-chip--lg', value === it.value && 'wm-chip--on')}
          onClick={() => onChange(it.value)}>
          {it.label}{it.count !== undefined && <span className="wm-num" style={{ fontWeight: 700, marginLeft: 6 }}>{it.count}</span>}
        </button>
      ))}
    </div>
  );
}

/** 목록 도구 줄: 필터 · (빈 칸) · 검색(흰 바탕 280) · 정렬 등 */
export function ListToolbar({ left, search, right }: {
  left?: ReactNode;
  search?: { value: string; onChange: (v: string) => void; placeholder?: string; label?: string; width?: number };
  right?: ReactNode;
}) {
  return (
    <div className="wm-toolbar">
      {left}
      <div style={{ flex: 1 }} />
      {search && <SearchField tone="white" width={search.width ?? 280} value={search.value} onChange={search.onChange} placeholder={search.placeholder ?? '찾기'}
        label={search.label ?? '검색'} clearable />}
      {right}
    </div>
  );
}

export interface DataColumn<R> {
  key: string;
  label: ReactNode;
  /** grid 열 너비(예 '190px', 'minmax(0, 1fr)') */
  width: string;
  render: (row: R) => ReactNode;
  align?: 'start' | 'end' | 'center';
}

/** 표 카드(흰 바탕 r14, 머리 h42 `#fbfbfc`, 행 min-h64) */
export function DataTable<R>({ columns, rows, rowKey, loading, empty, onRowClick, rowHeight }:
  { columns: Array<DataColumn<R>>; rows: R[]; rowKey: (r: R) => string; loading?: boolean; empty?: ReactNode; onRowClick?: (r: R) => void; rowHeight?: number }) {
  const grid = { gridTemplateColumns: columns.map((c) => c.width).join(' ') };
  return (
    <div className="wm-dtable" role="table">
      <div className="wm-dtable__head" style={grid} role="row">
        {columns.map((c) => <span key={c.key} role="columnheader" style={{ justifySelf: c.align ?? 'start' }}>{c.label}</span>)}
      </div>
      {loading && [0, 1, 2].map((i) => (
        <div key={i} className="wm-dtable__row" style={grid} role="row">
          {columns.map((c, j) => <Skeleton key={c.key} h={j === 0 ? 18 : 14} w={j === 0 ? '70%' : '60%'} />)}
        </div>
      ))}
      {!loading && rows.length === 0 && <div className="wm-dtable__empty">{empty ?? '아직 작업이 없어요.'}</div>}
      {!loading && rows.map((r) => (
        <div key={rowKey(r)} role="row" className={cx('wm-dtable__row', onRowClick && 'wm-dtable__row--link')} style={{ ...grid, minHeight: rowHeight }}
          onClick={onRowClick ? (e) => { if ((e.target as HTMLElement).closest('a,button')) return; onRowClick(r); } : undefined}>
          {columns.map((c) => <div key={c.key} role="cell" style={{ minWidth: 0, justifySelf: c.align ?? 'stretch', display: 'flex', justifyContent: c.align === 'end' ? 'flex-end' : undefined }}>{c.render(r)}</div>)}
        </div>
      ))}
    </div>
  );
}

/** 표 첫 칸(제목 + 보조 줄) */
export function TitleCell({ title, sub, to }: { title: ReactNode; sub?: ReactNode; to?: string }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 3, minWidth: 0 }}>
      {to ? <Link to={to} className="wm-dtable__title">{title}</Link> : <span className="wm-dtable__title">{title}</span>}
      {sub && <span className="wm-dtable__sub">{sub}</span>}
    </div>
  );
}

/** 행 끝 버튼(`열기` · `이어서` · `결과 보기 ›`) — primary 면 진행 중 강조 */
export function RowAction({ to, children, primary, chevron }: { to: string; children: ReactNode; primary?: boolean; chevron?: boolean }) {
  return (
    <Link to={to} className={cx('wm-btn wm-btn--h32', primary && 'wm-btn--primary')} style={{ justifySelf: 'end' }}>
      {children}{chevron && <Icon name="chevronRight" size={12} strokeWidth={2.4} />}
    </Link>
  );
}

/**
 * 작업 목록 화면 뼈대(§4 기능 라우트 `/<service>`): 머리 + 도구 줄 + (배너) + 표 + 아래 영역.
 *   <ListPage title="고객 요구사항" action={<NewButton to="new">새 요구사항</NewButton>} toolbar={…} table={<DataTable …/>} />
 */
export function ListPage({ title, desc, action, toolbar, banner, table, children, footer }:
  { title: ReactNode; desc?: ReactNode; action?: ReactNode; toolbar?: ReactNode; banner?: ReactNode; table?: ReactNode; children?: ReactNode; footer?: ReactNode }) {
  return (
    <section className="wm-listpage">
      <PageHeader title={title} desc={desc} actions={action} />
      {toolbar}
      {banner}
      {table}
      {children}
      {footer}
    </section>
  );
}

/** 섹션 카드: 제목 · 설명 · 오른쪽 동작 · 본문 */
export function Section({ title, desc, actions, children, flat, style, id }:
  { title?: ReactNode; desc?: ReactNode; actions?: ReactNode; children?: ReactNode; flat?: boolean; style?: CSSProperties; id?: string }) {
  return (
    <section className={cx('wm-section', flat && 'wm-section--flat')} style={style} id={id}>
      {(title || actions) && (
        <div className="wm-section__head">
          {title && <h3 className="wm-section__title">{title}</h3>}
          {desc && <span className="wm-section__desc">{desc}</span>}
          <span style={{ flex: 1 }} />
          {actions}
        </div>
      )}
      {children}
    </section>
  );
}

/**
 * 하단 입력 카드(§2.4 --wm-shadow-composer, 폭 800 r18): 머리 `{title} · {meta}` · 본문 · 아래 동작(오른쪽 정렬).
 * 화면 맨 아래에 두려면 본문 영역을 flex column 으로 두고 이 카드를 마지막에 둔다(`wrap` 기본 true = 가운데 정렬 + 패딩 16 40 24).
 */
export function Composer({ title, meta, headRight, children, actions, footLeft, wrap = true, width = 800 }:
  { title?: ReactNode; meta?: ReactNode; headRight?: ReactNode; children?: ReactNode; actions?: ReactNode; footLeft?: ReactNode; wrap?: boolean; width?: number }) {
  const card = (
    <div className="wm-composer" style={{ width }}>
      {(title || headRight) && (
        <div className="wm-composer__head">
          <span>{title}{meta && <small> · {meta}</small>}</span>
          {headRight}
        </div>
      )}
      {children && <div className="wm-composer__body">{children}</div>}
      {(actions || footLeft) && (
        <div className="wm-composer__foot">
          {footLeft && <div style={{ flex: 1, minWidth: 0 }}>{footLeft}</div>}
          {actions}
        </div>
      )}
    </div>
  );
  return wrap ? <div className="wm-composer-wrap">{card}</div> : card;
}

/**
 * 어시스턴트 말풍선 줄(로고 W + 글, lh 1.65). `body` 를 주면 글 아래(간격 12)에 작업 영역(카드 · 표 · 버튼 줄)을 둔다(IMG 보드 W 말풍선 + 작업 카드).
 *   <ChatLine body={<ShotGrid … />}>공간과 제품을 넣어 시안 4장을 만들었어요.</ChatLine>
 */
export function ChatLine({ children, body, className, 'data-testid': testId }: { children: ReactNode; body?: ReactNode; className?: string; 'data-testid'?: string }) {
  if (body === undefined || body === null || body === false) {
    return (
      <div className={cx('wm-chat', className)} data-testid={testId}>
        <span className="wm-chat__logo" aria-hidden="true">W</span>
        <div className="wm-chat__text">{children}</div>
      </div>
    );
  }
  return (
    <div className={cx('wm-chat', className)} data-testid={testId}>
      <span className="wm-chat__logo" aria-hidden="true">W</span>
      <div className="wm-chat__main">
        <div className="wm-chat__text">{children}</div>
        {body}
      </div>
    </div>
  );
}

/**
 * 사용자 입력 메아리 말풍선(오른쪽 정렬 · `--wm-surface-3` · r 16/16/4/16 · 14.5px, 최대 폭 560) — IMG 화면 맨 위 「**공간** · 카페 …」.
 * `head` 는 굵게(600) + ` · `. 글이 없으면 아무것도 그리지 않는다.
 */
export function EchoBubble({ head, children, 'data-testid': testId }: { head?: ReactNode; children?: ReactNode; 'data-testid'?: string }) {
  if ((children === undefined || children === null || children === '') && !head) return null;
  const hasText = children !== undefined && children !== null && children !== '';
  return (
    <div className="wm-echo-row">
      <div className="wm-echo" data-testid={testId}>{head && <b>{head}</b>}{head && hasText ? ' · ' : ''}{children}</div>
    </div>
  );
}

/** 가운데 고정 폭 본문(기능 화면 §3.1: 폭 800, 패딩 28 40 0) */
export function ContentColumn({ children, width = 800, gap = 22 }: { children: ReactNode; width?: number; gap?: number }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'center', padding: '28px 40px 0 40px' }}>
      <div style={{ width, maxWidth: '100%', display: 'flex', flexDirection: 'column', gap }}>{children}</div>
    </div>
  );
}

/** 칩 목록 줄(다른 곳에서 시작 등) */
export function ChipRow({ label, desc, items }: { label?: ReactNode; desc?: ReactNode; items: Array<{ key: string; label: ReactNode; count?: number | string; to?: string; onClick?: () => void }> }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0, flexWrap: 'wrap' }}>
      {label && <span style={{ fontSize: 12.5, fontWeight: 600 }}>{label}</span>}
      {desc && <span style={{ fontSize: 12, color: 'var(--wm-text-subtle)' }}>{desc}</span>}
      {(label || desc) && <span style={{ width: 1, height: 14, background: 'var(--wm-line)', margin: '0 4px' }} />}
      {items.map((it) => (
        <Fragment key={it.key}>
          {it.to
            ? <Link to={it.to} className="wm-chip" style={{ height: 30, fontSize: 12.5, gap: 6 }}>{it.label}{it.count !== undefined && <span className="wm-num" style={{ fontWeight: 700, fontSize: 11.5, color: 'var(--wm-text-muted)' }}>{it.count}</span>}</Link>
            : <Chip onClick={it.onClick} count={it.count}>{it.label}</Chip>}
        </Fragment>
      ))}
    </div>
  );
}
