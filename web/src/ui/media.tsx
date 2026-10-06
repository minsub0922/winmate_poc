/**
 * 이미지 · 사례 표시 — 이미지 타일(§2.8 ImageTile) · 사례 카드(§5.6.2 · §5.8.7 · §5.9.3).
 * 화면의 이미지는 같은 출처(게이트웨이) 저장본만 쓴다 — 외부 주소는 그리지 않는다(§9.6-8, §8.1 L-03).
 */
import { useEffect, useState, type CSSProperties, type KeyboardEvent, type ReactNode } from 'react';
import { cx } from './controls';
import { Badge, Tag } from './display';
import { Grip, Icon } from './icons';

/** 같은 출처(또는 data:/blob:) 주소인가 */
export function isSameOrigin(src?: string | null) {
  if (!src) return false;
  if (src.startsWith('data:') || src.startsWith('blob:')) return true;
  if (typeof window === 'undefined') return src.startsWith('/');
  try { return new URL(src, window.location.href).origin === window.location.origin; } catch { return false; }
}

export interface Focal { x: number; y: number }
export const focalCss = (f?: Focal | null, fallback = '50% 50%') => (f ? `${Math.round(f.x * 100)}% ${Math.round(f.y * 100)}%` : fallback);

/**
 * 안전한 이미지: 같은 출처가 아니거나 없거나 못 불러오면 회색 자리(`#f5f6f8`)를 그린다.
 * fit: 제품 = contain, 사진 = cover(+ focal).
 */
export function Img({ src, alt, fit = 'cover', focal, position, className, style, emptyText }:
  { src?: string | null; alt: string; fit?: 'cover' | 'contain'; focal?: Focal | null; position?: string; className?: string; style?: CSSProperties; emptyText?: string }) {
  const [err, setErr] = useState(false);
  useEffect(() => { setErr(false); }, [src]);
  if (!src || !isSameOrigin(src) || err) {
    return <span className={cx('wm-photo-empty', className)} style={style} role={alt ? 'img' : undefined} aria-label={alt || undefined}>{emptyText}</span>;
  }
  return (
    <img src={src} alt={alt} loading="lazy" draggable={false} className={cx('wm-photo', fit === 'contain' && 'wm-photo--contain', className)}
      style={{ objectPosition: position ?? focalCss(focal), ...style }} onError={() => setErr(true)} />
  );
}

export type ImageKindTone = 'product' | 'photo' | 'dark';
export interface ImageTileProps {
  src?: string | null;
  alt?: string;
  title: string;
  meta?: ReactNode;
  /** 왼쪽 위 kind 배지(`제품` = product 톤, `도입사례` = photo 톤) */
  kind?: { label: string; tone: ImageKindTone } | null;
  fit?: 'cover' | 'contain';
  focal?: Focal | null;
  /** 이미지 영역 높이(팝오버 100 · 제품 시트 108 · 솔루션 시트 82) */
  imgHeight?: number;
  /** 포커스(정보 패널 대상) — 테두리 brand, aria-pressed=true */
  focused?: boolean;
  /** 선택(작업에 넣을 것) — 테두리 `#b8c3ee` + 체크 원 */
  selected?: boolean;
  /** 선택 체크 원을 쓸 수 있나(작업 있음) */
  selectable?: boolean;
  onSelectToggle?: () => void;
  onClick?: () => void;
  ariaLabel?: string;
  /** 끌기 원천 props(useDragSource 결과) */
  dragProps?: object;
  /** 끌기 손잡이 표시 */
  grip?: boolean;
  /** 지금 끌고 있는 항목 */
  dragging?: boolean;
  compact?: boolean;
  className?: string;
}

/** 이미지 타일(§2.8 ImageTile · §5.5.2). 타일 클릭 = 포커스, 체크 원 클릭 또는 Space = 선택. */
export function ImageTile({ src, alt, title, meta, kind, fit = 'cover', focal, imgHeight = 100, focused, selected, selectable, onSelectToggle, onClick,
  ariaLabel, dragProps, grip, dragging, compact, className }: ImageTileProps) {
  const onKey = (e: KeyboardEvent) => {
    if (e.key === ' ' && selectable && onSelectToggle) { e.preventDefault(); onSelectToggle(); }
  };
  return (
    <div className={cx('wm-tilewrap', grip && 'wm-grab', dragging && 'wm-dragging', className)} style={{ position: 'relative', minWidth: 0, borderRadius: 10 }} {...dragProps}>
      <button type="button" className={cx('wm-tile', selected && 'wm-tile--sel', focused && 'wm-tile--focus')} aria-label={ariaLabel ?? title}
        aria-pressed={!!focused} onClick={onClick} onKeyDown={onKey}
        style={compact ? { padding: 5, gap: 3, borderRadius: 9, width: '100%' } : { width: '100%' }}>
        <span className="wm-tile__img" style={{ height: imgHeight, borderRadius: compact ? 6 : 7 }}>
          <Img src={src} alt={alt ?? title} fit={fit} focal={focal} />
          {kind && <span className="wm-tile__kind"><Badge tone={kind.tone === 'product' ? 'product' : kind.tone === 'dark' ? 'darksm' : 'photo'}>{kind.label}</Badge></span>}
          {grip && <span className="wm-tile__grip"><Grip color="var(--wm-text-muted)" width={8} height={12} /></span>}
        </span>
        <span className="wm-tile__title" style={compact ? { fontSize: 11.5 } : undefined}>{title}</span>
        {meta !== undefined && <span className="wm-tile__meta" style={compact ? { fontSize: 10.5 } : undefined}>{meta}</span>}
      </button>
      {selectable && (
        <button type="button" className="wm-tile__check" aria-pressed={!!selected} aria-label={(selected ? '선택 해제 ' : '선택 ') + title}
          style={{ top: 14, right: 14 }} onClick={(e) => { e.stopPropagation(); onSelectToggle?.(); }}>
          {selected && <Icon name="check" size={11} color="#fff" strokeWidth={3} />}
        </button>
      )}
    </div>
  );
}

/** 기능 화면용 이미지 카드(출처 요약 줄 포함) — ImageTile 의 간단한 모양 */
export function ImageCard({ src, title, kind, source, meta, fit, focal, onClick, selected }:
  { src?: string | null; title: string; kind?: { label: string; tone: ImageKindTone } | null; source?: string; meta?: ReactNode; fit?: 'cover' | 'contain';
    focal?: Focal | null; onClick?: () => void; selected?: boolean }) {
  return <ImageTile src={src} title={title} kind={kind} meta={meta ?? (source ? `출처 ${source}` : undefined)} fit={fit} focal={focal} onClick={onClick} focused={selected} />;
}

/** 사진 위 배지(`도입사례 사진` · `도입사례 사진 · 3장`) */
export function PhotoBadge({ children, style }: { children: ReactNode; style?: CSSProperties }) {
  return <span style={{ position: 'absolute', left: 6, bottom: 6, ...style }}><Badge tone="photo">{children}</Badge></span>;
}

const linkIcon = <Icon name="link" size={13} />;

export interface CaseCardPhoto { src?: string | null; alt: string; focal?: Focal | null }
export interface CaseCardProps {
  title: string;
  date?: string | null;
  /** 원문 주소 — 없으면(null) 링크 · `원문 열기` 를 숨긴다 */
  url?: string | null;
  urlDisplay?: string | null;
  /** `{업종} · {세부}` 태그 */
  tag?: string | null;
  /** 2줄 요약 */
  summary?: string | null;
  /** 요약이 없을 때 대신 보여 줄 원문 인용(따옴표를 붙여 그대로) — kb G-CASE-1 */
  quote?: string | null;
  products?: string[];
  /** `일치 · …` 토큰 */
  matchTerms?: string[];
  photos: CaseCardPhoto[];
  /** 배지 `도입사례 사진 · {N}장` 의 N */
  photoCount?: number;
  /** 오른쪽 아래(원문 열기 옆) 추가 버튼 자리 */
  action?: ReactNode;
  selected?: boolean;
  grip?: boolean;
  dragging?: boolean;
  dragProps?: object;
}

/** 유관 사례 카드(§5.6.2): 큰 사진 184×104 + 작은 사진 2 · 태그 · 제목 · 날짜 · 요약 2줄 · 제품 칩 · URL · 출처 주석 · 원문 열기 */
/** 요약 줄: 요약이 있으면 요약, 없으면 원문 인용을 “ ” 로 감싸서 */
function summaryLine(summary?: string | null, quote?: string | null) {
  if (summary) return { text: summary, quoted: false };
  if (quote) return { text: `“${quote}”`, quoted: true };
  return null;
}

export function CaseCard({ title, date, url, urlDisplay, tag, summary, quote, products = [], matchTerms = [], photos, photoCount, action, selected, grip, dragging, dragProps }: CaseCardProps) {
  const [p1, p2, p3] = photos;
  const n = photoCount ?? photos.length;
  const line = summaryLine(summary, quote);
  return (
    <div className={cx('wm-listcard', selected && 'wm-listcard--sel', grip && 'wm-grab', dragging && 'wm-dragging')} data-case-card=""
      style={{ display: 'flex', gap: 10, padding: '10px 12px 10px 8px', flexShrink: 0 }} {...dragProps}>
      <span style={{ width: 10, flexShrink: 0, display: 'flex', justifyContent: 'center', paddingTop: 4 }}>{grip && <Grip />}</span>
      <div style={{ width: 184, flexShrink: 0, display: 'flex', flexDirection: 'column', gap: 6 }}>
        <span style={{ position: 'relative', display: 'block', width: 184, height: 104, borderRadius: 8, overflow: 'hidden', background: 'var(--wm-bg)' }}>
          <Img src={p1?.src} alt={p1?.alt ?? ''} focal={p1?.focal} position={p1?.focal ? undefined : '50% 40%'} emptyText={n === 0 ? '사진 없음' : undefined} />
          {n > 0 && <PhotoBadge>도입사례 사진 · {n}장</PhotoBadge>}
        </span>
        <div style={{ display: 'flex', gap: 6 }}>
          {[p2, p3].map((p, i) => (
            <span key={i} style={{ width: 89, height: 46, borderRadius: 6, overflow: 'hidden', background: 'var(--wm-bg)', display: 'block' }}>
              <Img src={p?.src} alt={p?.alt ?? ''} position="50% 20%" />
            </span>
          ))}
        </div>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6, flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 }}>
          {tag && <Tag>{tag}</Tag>}
          <span className="wm-ellipsis" style={{ fontSize: 13.5, fontWeight: 600, flex: 1 }} title={title}>{title}</span>
          {date && <span style={{ fontSize: 11.5, color: 'var(--wm-text-muted)', whiteSpace: 'nowrap' }}>{date}</span>}
        </div>
        {line && <div style={{ fontSize: 12, color: 'var(--wm-text-2)', lineHeight: 1.5, height: 36, overflow: 'hidden' }} data-summary={line.quoted ? 'quote' : ''}
          title={line.quoted ? '요약 대신 원문 인용' : undefined}>{line.text}</div>}
        {(products.length > 0 || matchTerms.length > 0) && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, minWidth: 0, overflow: 'hidden' }}>
            {products.map((c) => <Tag key={c} tone="neutral">{c}</Tag>)}
            {matchTerms.length > 0 && <span className="wm-ellipsis" style={{ fontSize: 11, color: 'var(--wm-text-subtle)' }}>일치 · {matchTerms.join(' · ')}</span>}
          </div>
        )}
        {url && (
          <a href={url} target="_blank" rel="noopener noreferrer" title={url} data-case-url=""
            style={{ display: 'flex', alignItems: 'center', gap: 6, height: 22, minWidth: 0, fontSize: 11.5, color: 'var(--wm-brand)' }}>
            {linkIcon}<span className="wm-ellipsis">{urlDisplay || url}</span>
          </a>
        )}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 'auto' }}>
          <span className="wm-ellipsis" style={{ fontSize: 11, color: 'var(--wm-text-subtle)', flex: 1 }}>내용 · 사진 출처 삼성전자 고객 도입사례</span>
          {url && (
            <a href={url} target="_blank" rel="noopener noreferrer" className="wm-btn wm-btn--h26" style={{ fontSize: 11.5, gap: 4 }}>
              원문 열기<Icon name="external" size={11} strokeWidth={2.4} />
            </a>
          )}
          {action}
        </div>
      </div>
    </div>
  );
}

/**
 * 시트 안 사례 행(§5.8.7 · §5.9.3): 사진(제품 196×124 · 솔루션 172×96) + `도입사례 사진` · 배지 · 제목 · 날짜 · 요약 · (원문에 나온 제품) · URL · `원문 열기 ↗`
 */
export function CaseRow({ title, date, url, urlDisplay, summary, quote, usedLine, badge, photo, size = 'product' }:
  { title: string; date?: string | null; url?: string | null; urlDisplay?: string | null; summary?: string | null; quote?: string | null; usedLine?: string | null; badge?: ReactNode;
    photo?: CaseCardPhoto | null; size?: 'product' | 'solution' }) {
  const big = size === 'product';
  const line = summaryLine(summary, quote);
  return (
    <div style={{ flexShrink: 0, display: 'flex', gap: 14, padding: big ? 10 : 8, border: '1px solid var(--wm-line)', borderRadius: 12 }} data-case-row="">
      <span style={{ position: 'relative', display: 'block', width: big ? 196 : 172, height: big ? 124 : 96, flexShrink: 0, borderRadius: 8, overflow: 'hidden', background: 'var(--wm-bg)' }}>
        <Img src={photo?.src} alt={photo?.alt ?? title} focal={photo?.focal} emptyText={photo ? undefined : '사진 없음'} />
        <PhotoBadge>도입사례 사진</PhotoBadge>
      </span>
      <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: big ? 5 : 4 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 }}>
          {badge}
          <span className="wm-ellipsis" style={{ fontSize: big ? 13.5 : 13, fontWeight: 700, flex: 1 }} title={title}>{title}</span>
          {date && <span style={{ fontSize: 11.5, color: 'var(--wm-text-muted)', whiteSpace: 'nowrap' }}>{date}</span>}
        </div>
        {line && <span style={{ fontSize: 12, color: 'var(--wm-text-2)', lineHeight: big ? 1.5 : 1.45, height: big ? 36 : 35, overflow: 'hidden' }}
          data-summary={line.quoted ? 'quote' : ''} title={line.quoted ? '요약 대신 원문 인용' : undefined}>{line.text}</span>}
        {usedLine && <span className="wm-ellipsis" style={{ fontSize: 11.5, color: 'var(--wm-text-muted)' }}>원문에 나온 제품 · {usedLine}</span>}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 'auto', minWidth: 0 }}>
          {url ? (
            <>
              <a href={url} target="_blank" rel="noopener noreferrer" className="wm-ellipsis" style={{ flex: 1, fontSize: 11.5 }} title={url}>{urlDisplay || url}</a>
              <a href={url} target="_blank" rel="noopener noreferrer" className="wm-btn wm-btn--h26" style={{ fontSize: 11.5, height: big ? 26 : 24 }}>원문 열기 ↗</a>
            </>
          ) : <span style={{ flex: 1, fontSize: 11.5, color: 'var(--wm-text-subtle)' }}>원문 주소 없음</span>}
        </div>
      </div>
    </div>
  );
}
