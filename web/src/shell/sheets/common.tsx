/**
 * 상세 시트 공통(00-shell §3.4 · §5.8 · §5.9): 틀(딤 · 포커스 가두기 · Esc) · 머리 · 탭 · 갤러리 · 선택한 이미지 패널 · 추가 버튼.
 */
import { useEffect, useRef, useState, type ReactNode } from 'react';
import { Badge, Button, CloseButton, Icon, Img, ImageTile, MetaRows, formatDate, formatKB, formatMediaSize, shortFileUrl, useEscape, useFocusTrap, type MetaRow } from '@/ui';
import { imageAlt, imageSrc, usageNoteSheet } from '../kb';
import type { KbImageMeta } from '../kbTypes';
import { NO_TASK_TIP, useShellRuntime } from '../runtime';
import { useAssetUsage, usageText } from '../workspace';
import type { DragType } from '../types';

export function SheetFrame({ ariaLabel, onClose, ready, children }: { ariaLabel: string; onClose: () => void; ready?: boolean; children: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);
  useFocusTrap(ref, true, { initialFocus: () => ref.current?.querySelector<HTMLElement>('[role="tab"][aria-selected="true"]') ?? null });
  useEscape(onClose, true);
  // 데이터가 늦게 오면 탭이 생긴 뒤 첫 탭으로 옮긴다(§5.8.1 [제안])
  useEffect(() => {
    if (!ready) return;
    const t = window.setTimeout(() => {
      const root = ref.current;
      const tab = root?.querySelector<HTMLElement>('[role="tab"][aria-selected="true"]');
      const a = document.activeElement;
      if (root && tab && (a === root || a === document.body || a?.classList.contains('sh-backbtn'))) tab.focus({ preventScroll: true });
    }, 0);
    return () => window.clearTimeout(t);
  }, [ready]);
  return (
    <>
      <div className="sh-scrim" onMouseDown={onClose} data-testid="sheet-scrim" />
      <div ref={ref} className="sh-sheet" role="dialog" aria-modal="true" aria-label={ariaLabel} tabIndex={-1}>{children}</div>
    </>
  );
}

export function SheetHeader({ backLabel, onBack, path, last, links, onClose }:
  { backLabel: string; onBack: () => void; path: string[]; last: string; links: Array<{ label: string; href?: string | null; icon?: boolean }>; onClose: () => void }) {
  return (
    <header className="sh-sheet__head">
      <button type="button" className="sh-backbtn" onClick={onBack}><Icon name="chevronLeft" size={16} strokeWidth={2.2} />{backLabel}</button>
      <div className="sh-sheet__path" aria-label="경로">
        {path.map((p, i) => <span key={i} style={{ display: 'contents' }}><span>{p}</span><span aria-hidden="true">›</span></span>)}
        <b>{last}</b>
      </div>
      {links.filter((l) => l.href).map((l) => (
        <a key={l.label} className="sh-extbtn" href={l.href!} target="_blank" rel="noopener noreferrer">{l.label}{l.icon && <Icon name="external" size={12} strokeWidth={2.4} />}</a>
      ))}
      <CloseButton label="상세 닫기" size={34} onClick={onClose} />
    </header>
  );
}

export interface SheetTab { value: string; label: string; count?: number | string }
export function SheetTabs({ tabs, value, onChange, verified }: { tabs: SheetTab[]; value: string; onChange: (v: string) => void; verified?: string | null }) {
  return (
    <nav className="sh-sheet__tabs" role="tablist" aria-label="상세 항목">
      {tabs.map((t, i) => (
        <button key={t.value} type="button" role="tab" aria-selected={value === t.value} tabIndex={value === t.value ? 0 : -1} data-tab={t.value}
          className={value === t.value ? 'wm-tab wm-tab--sheet wm-tab--on' : 'wm-tab wm-tab--sheet'} onClick={() => onChange(t.value)}
          onKeyDown={(e) => {
            if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
            e.preventDefault();
            const n = tabs[(i + (e.key === 'ArrowRight' ? 1 : tabs.length - 1)) % tabs.length];
            const list = e.currentTarget.parentElement; // 합성 이벤트의 currentTarget 은 처리 뒤 비므로 미리 잡는다
            onChange(n.value);
            window.setTimeout(() => list?.querySelector<HTMLElement>(`[data-tab="${n.value}"]`)?.focus(), 0);
          }}>
          {t.label}{t.count !== undefined && t.count !== '' && <span className="wm-tab__n">{t.count}</span>}
        </button>
      ))}
      {verified && <span className="sh-sheet__verified">공식 정보 확인 {formatDate(verified)}</span>}
    </nav>
  );
}

/** 시트 `현재 작업에 추가` · `작업에 추가` 버튼 상태 */
export function useSheetAdd(type: DragType, r: string | null) {
  const rt = useShellRuntime();
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);
  const added = !!r && rt.isAdded(r);
  const can = rt.canAdd(type) && !!r && !added;
  const reason = !rt.hasTask ? NO_TASK_TIP : added ? '이미 현재 작업에 있습니다' : rt.offReason(type, 'footer');
  const run = async () => {
    if (!r || !can) return;
    setBusy(true); setFailed(false);
    const res = await rt.runAdd(type, [r]);
    setBusy(false);
    if (!res.ok) setFailed(true);
  };
  return { added, can, reason, run, busy, failed };
}

export function SheetAddButton({ type, r, h = 44, label = '현재 작업에 추가' }: { type: DragType; r: string | null; h?: 44 | 28; label?: string }) {
  const s = useSheetAdd(type, r);
  return (
    <Button h={h} disabled={!s.can} loading={s.busy} onClick={s.run} disabledReason={s.reason} style={h === 44 ? { fontSize: 13, padding: '0 14px' } : undefined}
      title={s.failed ? '추가하지 못했어요. 다시 시도해 주세요.' : undefined}>
      {s.added ? '✓ 추가됨' : s.failed ? '다시 시도' : label}
    </Button>
  );
}

/** 이미지 라벨: API label → alt 에서 시리즈 이름을 뺀 것 → 제목 */
export function imageLabel(im: KbImageMeta, familyName?: string | null) {
  if (im.label) return im.label;
  const alt = imageAlt({ alt: im.alt }, '');
  if (familyName && alt.startsWith(familyName)) return alt.slice(familyName.length).trim() || alt;
  return imageAlt({ alt: im.title, title: alt }, '이미지');
}

/** 시트 갤러리 타일 메타: 제품 `1920 × 1280 PNG · 1,529 KB` · 솔루션 `1440×680 JPG · 669 KB` */
export function galleryMeta(im: KbImageMeta, compact?: boolean) {
  const o = im.original;
  if (!o) return '[확인 필요]';
  const dims = `${o.width}${compact ? '×' : ' × '}${o.height} ${(o.format ?? '').toUpperCase()}`.trim();
  return o.bytes != null ? `${dims} · ${formatKB(o.bytes)}` : dims; // 용량을 모르면(kb browser_probe) 크기만
}

export function Gallery({ images, focusId, onFocus, cols, imgHeight, fit, familyName, compact }:
  { images: KbImageMeta[]; focusId: string | null; onFocus: (id: string) => void; cols: number; imgHeight: number; fit: 'cover' | 'contain'; familyName?: string | null; compact?: boolean }) {
  return (
    <div className="sh-gallery" style={{ gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))`, gap: compact ? 8 : 10 }} role="list">
      {images.map((im) => {
        const label = imageLabel(im, familyName);
        const o = im.original;
        return (
          <ImageTile key={im.id} src={imageSrc(im)} title={label} meta={galleryMeta(im, compact)} fit={fit} focal={im.focal} imgHeight={imgHeight} compact={compact}
            focused={focusId === im.id} onClick={() => onFocus(im.id)}
            ariaLabel={o ? `${label} — 원본 ${o.width}×${o.height} ${(o.format ?? '').toUpperCase()}`.trim() : `${label} 이미지`} />
        );
      })}
    </div>
  );
}

/** 선택한 이미지 메타 행(§5.8.6 · §5.9.3) */
export function imageMetaRows(im: KbImageMeta, usage: string, opts: { pageLabel?: string; withPosted?: boolean; withPageNote?: boolean }): MetaRow[] {
  const rows: MetaRow[] = [
    // 원문 alt 가 `img` 같은 빈 값이면 KB 제목으로 대신한다
    { k: '이미지명', v: imageAlt({ alt: im.alt }) ? `${imageAlt({ alt: im.alt })} (원문 대체 텍스트)` : imageAlt({ alt: im.title }) || '[확인 필요]' },
    { k: '출처 유형', v: im.source_type_label || (im.rights === 'customer_case' ? '삼성전자 고객 도입사례' : im.kind === 'solution' ? '삼성전자 공식 · 솔루션 소개 이미지' : '삼성전자 공식 · 제품 갤러리') },
    { k: '출처 페이지', v: opts.pageLabel || im.source_page?.label || im.source_page?.title || '[확인 필요]', href: im.source_page?.url ?? null },
    { k: '원본 파일', v: im.original_url ? shortFileUrl(im.original_url) : '[확인 필요]', href: im.original_url ?? null, title: im.original_url ?? undefined },
    { k: '원본', v: formatMediaSize(im.original) || '[확인 필요]' },
    { k: '저장본', v: formatMediaSize(im.stored) || '[확인 필요]' },
  ];
  if (opts.withPosted) {
    rows.push({ k: '원본 등록', v: im.posted?.date ? `${im.posted.date} (${im.posted.basis === 'file_path' ? '파일 경로 기준' : '사례 게시일'})` : '[확인 필요]' });
  }
  rows.push({ k: '수집', v: im.collected_at ? `${formatDate(im.collected_at)} · 공식 페이지에서 수집` : '[확인 필요]' });
  if (opts.withPageNote && im.page_note) rows.push({ k: '원문 표기', v: im.page_note });
  rows.push({ k: '사용 조건', v: im.usage_note || usageNoteSheet(im.rights) }, { k: '사용 이력', v: usage });
  return rows;
}

export function SelectedImagePanel({ im, label, badge, actions, pageLabel, withPosted, withPageNote }:
  { im: KbImageMeta; label: string; badge: ReactNode; actions?: ReactNode; pageLabel?: string; withPosted?: boolean; withPageNote?: boolean }) {
  const r = `kb:image:${im.id}`;
  const usage = useAssetUsage([r]);
  return (
    <div className="sh-selpanel" aria-label="선택한 이미지">
      <div className="sh-selpanel__head">
        <span style={{ fontSize: 11.5, fontWeight: 700, color: 'var(--wm-text-muted)' }}>선택한 이미지</span>
        <span style={{ fontSize: 13, fontWeight: 700 }}>{label}</span>
        {badge}
        <span style={{ flex: 1 }} />
        {im.original_url && <a className="wm-btn wm-btn--h28" href={im.original_url} target="_blank" rel="noopener noreferrer">원본 열기 ↗</a>}
        {actions}
      </div>
      <MetaRows variant="sheet" rows={imageMetaRows(im, usageText(usage.data, r, usage.isLoading), { pageLabel, withPosted, withPageNote })} />
    </div>
  );
}

/** 왼쪽 패널 대표 이미지 + 배지 */
export function Hero({ src, alt, height, fit, badge, focal }: { src: string | null; alt: string; height: number; fit: 'cover' | 'contain'; badge?: ReactNode; focal?: KbImageMeta['focal'] }) {
  return (
    <div className="sh-sheet__hero" style={{ height }}>
      <Img src={src} alt={alt} fit={fit} focal={focal} />
      {badge && <span className="sh-sheet__hero-badge"><Badge tone="brandline">{badge}</Badge></span>}
    </div>
  );
}

export function SheetError({ message, onRetry, onClose }: { message: string; onRetry: () => void; onClose: () => void }) {
  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 10 }} role="alert">
      <span style={{ fontSize: 13, color: 'var(--wm-text-muted)' }}>{message}</span>
      <div style={{ display: 'flex', gap: 8 }}>
        <Button h={32} onClick={onRetry}>다시 시도</Button>
        <Button h={32} onClick={onClose}>닫기</Button>
      </div>
    </div>
  );
}
