/**
 * IMG 화면 공용 부품 — 화면 틀(메아리 + W + 아래 카드), 상태 배지, 알약 버튼, 입력 줄, 스위치, 시안 카드, 확대 보기, 제품 칩 입력.
 * 키트(@/ui)에 없는 보드 모양은 여기서 만들고 docs/requests/workspace.md 에 적었다.
 */
import { useEffect, useId, useMemo, useRef, useState, type KeyboardEvent, type ReactNode } from 'react';
import { Link } from 'react-router';
import { cx, Icon, Img, PathIcon, Spinner, searchProducts, productName, useEscape, type ProductSearchItem } from '@/ui';
import { useShellPage, type ShellPageConfig } from '@/shell';
import type { Badge, ProductCond, Shot } from './api';
import { pct, SECTION, STEPS } from './lib';

// ── 아이콘(보드 path) ─────────────────────────────────
export const PATH = {
  camera: 'M4 8h3l2-3h6l2 3h3v11H4z M12 9.5a3.5 3.5 0 1 0 0 7 3.5 3.5 0 0 0 0-7z',
  gallery: 'M3 6a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z M9 8a2 2 0 1 0 0 4 2 2 0 0 0 0-4z M21 16l-5-5-9 9',
  space: 'M3 21V8l9-5 9 5v13 M9 21v-6h6v6',
  background: 'M3 6a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z M3 15l5-4 4 3 4-5 5 6',
  scenario: 'M9 4a3 3 0 1 0 0 6 3 3 0 0 0 0-6z M3 21v-2a5 5 0 0 1 5-5h2a5 5 0 0 1 5 5v2 M17 11h4 M19 9v4',
  zoom: 'M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14z M20 20l-4-4 M11 8v6 M8 11h6',
  bell: 'M6 16v-5a6 6 0 1 1 12 0v5l2 2H4z M10 21h4',
  rect: 'M4 7V4h3 M10 4h4 M17 4h3v3 M20 10v4 M20 17v3h-3 M14 20h-4 M7 20H4v-3 M4 14v-4',
  brush: 'M18 3l3 3-10 10-4 1 1-4L18 3z M4 21h7',
  object: 'M4 20L14 10 M15 3v3 M15 14v3 M8 9h3 M19 9h3 M17.5 6.5l2-2 M17.5 11.5l2 2',
  eraser: 'M20 20H9l-5-5 9-9 7 7-5 5 M9 20l3-3',
  redo: 'M15 14l5-5-5-5 M20 9H9a5 5 0 0 0 0 10h3',
  compare: 'M9 7l-5 5 5 5 M15 7l5 5-5 5',
  pause: 'M9 6v12 M15 6v12',
  ban: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18z M5.6 5.6l12.8 12.8',
  scan: 'M4 8V4h4 M16 4h4v4 M20 16v4h-4 M8 20H4v-4 M9 9h6v6H9z',
  personX: 'M9 4a3 3 0 1 0 0 6 3 3 0 0 0 0-6z M3 20v-1a5 5 0 0 1 5-5h2a5 5 0 0 1 3 1 M16 15l5 5 M21 15l-5 5',
  doc: 'M6 3h8l5 5v13H6z M14 3v5h5 M9 13h6 M9 17h6',
  present: 'M3 4h18v12H3z M8 20h8 M12 16v4',
  play: 'M4 6h16v12H4z M10 9l5 3-5 3V9z',
  cube: 'M12 3l8 4.5v9L12 21l-8-4.5v-9z M12 12l8-4.5 M12 12v9 M12 12L4 7.5',
  share: 'M18 2a3 3 0 1 0 0 6 3 3 0 0 0 0-6z M6 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6z M18 16a3 3 0 1 0 0 6 3 3 0 0 0 0-6z M8.6 13.5l6.8 4 M15.4 6.5l-6.8 4',
  persp: 'M5 5l14 2v10L5 19z',
  display: 'M3 5h18v11H3z M9 20h6 M12 16v4',
  download: 'M12 4v12 M6 10l6 6 6-6 M4 20h16',
  sun: 'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8z M12 2v2 M12 20v2 M4.9 4.9l1.4 1.4 M17.7 17.7l1.4 1.4 M2 12h2 M20 12h2 M4.9 19.1l1.4-1.4 M17.7 6.3l1.4-1.4',
  measure: 'M3 12h18 M3 12l3-3 M3 12l3 3 M21 12l-3-3 M21 12l-3 3',
};
export const Ico = ({ d, size = 16, color, sw = 2 }: { d: string; size?: number; color?: string; sw?: number }) =>
  <PathIcon d={d} size={size} color={color} strokeWidth={sw} />;

// ── 셸 맥락 ───────────────────────────────────────────
/** 화면마다 한 번 — section 「이미지 생성」 + 스텝바(1/2/3, IMG4 는 complete) */
export function useImgShell(cfg: Omit<ShellPageConfig, 'section' | 'stepper'> & { step?: 1 | 2 | 3; complete?: boolean; noStepper?: boolean }) {
  const { step, complete, noStepper, ...rest } = cfg;
  useShellPage({
    section: SECTION, hasTask: true, sidebarGroup: 'image', ...rest,
    stepper: noStepper || !step ? undefined : { steps: STEPS, current: step, complete },
  });
}

// ── 화면 틀 ───────────────────────────────────────────
export function Screen({ children, composer, testid }: { children: ReactNode; composer?: ReactNode; testid?: string }) {
  return (
    <div className="img-screen" data-testid={testid}>
      <div className="img-scroll"><div className="img-col">{children}</div></div>
      {composer}
    </div>
  );
}
/** 사용자 입력 메아리 — 입력(text)이 없으면 그리지 않는다 */
export function Echo({ head, text }: { head?: string | null; text?: string | null }) {
  if (!text) return null;
  return (
    <div className="img-echo-row">
      <div className="img-echo" data-testid="img-echo">{head && <b>{head}</b>}{head && text ? ' · ' : ''}{text}</div>
    </div>
  );
}
/** W 말풍선(템플릿 문구) + 그 아래 작업 영역 */
export function WSay({ text, children }: { text: ReactNode; children?: ReactNode }) {
  return (
    <div className="img-w">
      <span className="img-w__logo" aria-hidden="true">W</span>
      <div className="img-w__body">
        <div className="img-w__text" data-testid="img-w">{text}</div>
        {children}
      </div>
    </div>
  );
}
export function Loading({ label = '불러오는 중' }: { label?: string }) {
  return <div className="img-center"><Spinner label={label} /></div>;
}

// ── 상태 배지(§4.1 표) ────────────────────────────────
const BADGE_ICON: Record<string, string> = {
  check: 'M5 12l5 5L20 7', clock: 'M12 3a9 9 0 1 0 0 18a9 9 0 1 0 0-18z M12 7v5l3 2',
  info: 'M12 3a9 9 0 1 0 0 18a9 9 0 1 0 0-18z M12 11v5 M12 8h.01', edit: 'M4 20h4L19 9l-4-4L4 16v4z', download: 'M12 4v12 M6 10l6 6 6-6 M4 20h16',
};
export function StatusPill({ badge }: { badge: Badge }) {
  const cls = badge.code === 'running' ? 'run' : badge.code === 'in_proposal' ? 'use' : badge.tone === 'ink' ? 'check' : badge.tone === 'brand' ? 'run' : 'done';
  return (
    <span className={cx('img-status', `img-status--${cls}`)} data-badge={badge.code}>
      {badge.icon !== 'none' && BADGE_ICON[badge.icon] && <PathIcon d={BADGE_ICON[badge.icon]} size={11} strokeWidth={2.6} />}
      <span>{badge.label}</span>
    </span>
  );
}

// ── 버튼 · 입력 ───────────────────────────────────────
export function Pill({ on, children, onClick, title, disabled, h, className, def, ariaLabel, pressed }:
  { on?: boolean; children: ReactNode; onClick?: () => void; title?: string; disabled?: boolean; h?: 26 | 28 | 30 | 32; className?: string; def?: boolean; ariaLabel?: string; pressed?: boolean }) {
  return (
    <button type="button" className={cx('img-pill', h && h !== 30 && `img-pill--h${h}`, on && 'img-pill--on', def && !on && 'img-pill--def', className)}
      aria-pressed={pressed ?? (on !== undefined ? !!on : undefined)} title={title} disabled={disabled} onClick={onClick} aria-label={ariaLabel}>
      {children}
    </button>
  );
}

/** 하단 카드의 입력 줄(라벨은 숨김) + 보내기 */
export function AskInput({ label, placeholder, onSend, busy, disabled, value, onChange, testid }:
  { label: string; placeholder: string; onSend: (text: string) => void | Promise<void>; busy?: boolean; disabled?: boolean; value?: string; onChange?: (v: string) => void; testid?: string }) {
  const [own, setOwn] = useState('');
  const text = value ?? own;
  const set = onChange ?? setOwn;
  const id = useId();
  const send = async () => {
    const t = text.trim();
    if (!t || busy || disabled) return;
    await onSend(t);
    set('');
  };
  return (
    <div className="img-ask">
      <label htmlFor={id} className="wm-sr-only">{label}</label>
      <input id={id} value={text} placeholder={placeholder} disabled={disabled} data-testid={testid} autoComplete="off"
        onChange={(e) => set(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter' && !e.nativeEvent.isComposing) { e.preventDefault(); void send(); } }} />
      <button type="button" className={cx('img-ask__send', text.trim() && 'img-ask__send--on')} aria-label="보내기" disabled={busy || disabled || !text.trim()} onClick={() => void send()}>
        {busy ? <Spinner label="보내는 중" /> : <Icon name="arrowUp" size={14} strokeWidth={2.4} />}
      </button>
    </div>
  );
}

export function Switch({ checked, onChange, children, label, disabled }: { checked: boolean; onChange: (v: boolean) => void; children?: ReactNode; label: string; disabled?: boolean }) {
  return (
    <button type="button" role="switch" aria-checked={checked} aria-label={label} className="img-switch" disabled={disabled} onClick={() => onChange(!checked)}>
      {children && <span>{children}</span>}
      <span className="img-switch__track" />
    </button>
  );
}
/** 스위치를 오른쪽 · 글을 왼쪽 */
export function SwitchRow({ checked, onChange, label, icon }: { checked: boolean; onChange: (v: boolean) => void; label: string; icon?: ReactNode }) {
  return (
    <button type="button" role="switch" aria-checked={checked} aria-label={label} className="img-switch" onClick={() => onChange(!checked)}>
      {icon}<span>{label}</span><span className="img-switch__track" />
    </button>
  );
}

export interface SegItem<T extends string> { value: T; label: ReactNode; disabled?: boolean; title?: string }
export function Seg<T extends string>({ items, value, onChange, ariaLabel, size, variant = 'gray', multi }:
  { items: Array<SegItem<T>>; value: T | T[]; onChange: (v: T) => void; ariaLabel: string; size?: 'sm'; variant?: 'gray' | 'line'; multi?: boolean }) {
  const isOn = (v: T) => (Array.isArray(value) ? value.includes(v) : value === v);
  return (
    <div role="group" aria-label={ariaLabel} className={cx(variant === 'gray' ? 'img-seg' : 'img-segb', size === 'sm' && (variant === 'gray' ? 'img-seg--sm' : 'img-segb--sm'))}>
      {items.map((it) => (
        <button key={it.value} type="button" aria-pressed={isOn(it.value)} disabled={it.disabled} title={it.title}
          onClick={() => (multi || !isOn(it.value)) && onChange(it.value)}>{it.label}</button>
      ))}
    </div>
  );
}

// ── 시안 카드(IMG3G · IMG3 · IMG3V) ───────────────────
export function ShotCard({ shot, tall, fill, selected, onSelect, onZoom, onDownload, onCancel, heldTo, tagExtra, showSelectedBadge, testid }:
  { shot: Shot; tall?: boolean; fill?: boolean; selected?: boolean; onSelect?: () => void; onZoom?: () => void; onDownload?: () => void; onCancel?: () => void;
    heldTo?: string; tagExtra?: string; showSelectedBadge?: boolean; testid?: string }) {
  const st = shot.state;
  const label = shot.label;
  const canCancel = !!onCancel && ['waiting', 'composing', 'rendering', 'qc'].includes(st);
  const tag = (txt: string, done?: boolean) => (
    <span className={cx('img-shot__tag', done && 'img-shot__tag--done')}>{done && <Icon name="check" size={11} strokeWidth={3} />}{txt}</span>
  );
  let body: ReactNode;
  if (st === 'done') {
    body = (
      <>
        <Img src={shot.thumb_url ?? shot.url} alt={`${label} — 생성 이미지`} />
        {onSelect && <button type="button" className="img-shot__hit" aria-label={selected ? `${label} 선택됨` : `${label} 선택`} aria-pressed={!!selected} onClick={onSelect} />}
        {showSelectedBadge && selected && <span className="img-shot__sel">선택됨</span>}
        {shot.qc_flag && <span className="img-shot__qc" title={shot.qc_reason ?? '품질 확인이 필요해요'}><Icon name="info" size={11} strokeWidth={2.6} />확인 필요</span>}
        {(onZoom || onDownload) && (
          <span className="img-shot__tools">
            {onZoom && <button type="button" className="img-shot__tool" aria-label={showSelectedBadge ? '확대' : '크게 보기'} onClick={onZoom}><Ico d={PATH.zoom} size={14} /></button>}
            {onDownload && <button type="button" className="img-shot__tool" aria-label="다운로드" onClick={onDownload}><Ico d={PATH.download} size={14} /></button>}
          </span>
        )}
        {showSelectedBadge ? tag(selected ? `${label}${tagExtra ? ` · ${tagExtra}` : ''}` : label) : tag(`${label} · 완료`, true)}
      </>
    );
  } else if (st === 'rendering' || st === 'qc') {
    body = (
      <>
        {shot.preview_url && <img className="img-shot__blur" src={shot.preview_url} alt={`${label} — 렌더링 중인 미리보기(흐림)`} />}
        <div className="img-shot__veil">
          <span className="img-shot__state">{shot.stage_label || '렌더링 중'} <b>{pct(shot.progress)}</b></span>
          <span className="img-shot__bar"><span style={{ width: pct(shot.progress) }} /></span>
        </div>
        {tag(label)}
      </>
    );
  } else if (st === 'composing') {
    body = (
      <>
        {shot.preview_url
          ? <img className="img-shot__blur" src={shot.preview_url} alt={`${label} — 합성 초안(흐림)`} />
          : <span className="img-shot__wire" aria-hidden="true"><span /><span /><span /></span>}
        <div className="img-shot__center" style={{ top: '58%' }}>
          <span className="img-shot__state">장면 구성 중 <b>{pct(shot.progress)}</b></span>
          <span className="img-shot__bar"><span style={{ width: pct(shot.progress) }} /></span>
        </div>
        {tag(label)}
      </>
    );
  } else if (st === 'waiting') {
    body = (
      <>
        <div className="img-shot__center">
          <Icon name="clock" size={18} color="var(--wm-text-muted)" />
          <span className="img-shot__state">대기 중</span>
          {shot.wait_for && <small>{shot.wait_for}</small>}
        </div>
        {tag(label)}
      </>
    );
  } else if (st === 'held') {
    body = (
      <>
        <div className="img-shot__center">
          <Ico d={PATH.pause} size={16} color="var(--wm-text-muted)" />
          {heldTo ? <Link to={heldTo} className="img-shot__state">보류 · 대안 필요</Link> : <span className="img-shot__state">보류 · 대안 필요</span>}
        </div>
        {tag(label)}
      </>
    );
  } else if (st === 'canceled') {
    body = (<><div className="img-shot__center"><span className="img-shot__state">취소됨</span></div>{tag(label)}</>);
  } else {
    body = (<><div className="img-shot__center"><span className="img-shot__state">만들지 못했어요</span>{shot.error && <small>{shot.error}</small>}</div>{tag(label)}</>);
  }
  return (
    <div className={cx('img-shot', tall && 'img-shot--tall', fill && 'img-shot--fill', (st === 'waiting' || st === 'held' || st === 'canceled') && 'img-shot--wait', selected && showSelectedBadge && 'img-shot--sel')}
      data-state={st} data-testid={testid ?? `shot-${shot.index}`}>
      {body}
      {canCancel && (
        <button type="button" className={cx('img-shot__cancel', st === 'waiting' && 'img-shot__cancel--show')} onClick={onCancel} aria-label={`${label} 이 장 취소`}>
          <Icon name="x" size={11} strokeWidth={2.6} />이 장 취소
        </button>
      )}
    </div>
  );
}

// ── 확대 보기 ─────────────────────────────────────────
export function ZoomView({ src, alt, caption, onClose }: { src: string | null | undefined; alt: string; caption?: string; onClose: () => void }) {
  useEscape(onClose, !!src);
  const ref = useRef<HTMLButtonElement>(null);
  useEffect(() => { if (src) ref.current?.focus(); }, [src]);
  if (!src) return null;
  return (
    <div className="img-zoom" role="dialog" aria-modal="true" aria-label={alt} onClick={onClose}>
      <img src={src} alt={alt} onClick={(e) => e.stopPropagation()} />
      <button ref={ref} type="button" className="img-zoom__close" aria-label="닫기" onClick={onClose}><Icon name="x" size={16} /></button>
      {caption && <span className="img-zoom__cap">{caption}</span>}
    </div>
  );
}

// ── 제품 칩 입력(IMG2 「등장 제품」) ─────────────────
/** 키트 ProductInput 은 수량(×3) · 수량 바꾸기를 못 그려서 만든 지역 부품(docs/requests/workspace.md) — 검색은 키트 searchProducts */
export function ProductChips({ value, onChange, onDropRefs, dropActive, message }:
  { value: ProductCond[]; onChange: (next: ProductCond[]) => void; onDropRefs?: ReactNode; dropActive?: boolean; message?: string | null }) {
  const [q, setQ] = useState('');
  const [items, setItems] = useState<ProductSearchItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const [qtyFor, setQtyFor] = useState<number | null>(null);
  const pending = useRef(false);
  const inputId = useId();
  const listId = `img-pl-${inputId}`;
  const valueRef = useRef(value);
  valueRef.current = value;

  const add = (it: ProductSearchItem) => {
    const p: ProductCond = {
      family_id: (it as ProductSearchItem & { family_id?: string | null }).family_id ?? (it.kind === 'family' ? it.id : null),
      model_code: it.model_code ?? null, name: it.label || productName(it), short: productName(it), qty: 1, source: 'user',
    };
    const key = p.model_code ?? p.family_id;
    if (!valueRef.current.some((x) => (x.model_code ?? x.family_id) === key)) onChange([...valueRef.current, p].slice(0, 9));
    setQ(''); setItems([]); setOpen(false);
  };
  useEffect(() => {
    const s = q.trim();
    if (!s) { setItems([]); setLoading(false); return; }
    const ac = new AbortController();
    setLoading(true);
    const t = window.setTimeout(() => {
      searchProducts(s, { limit: 5, signal: ac.signal })
        .then((r) => { setItems(r); setActive(0); setLoading(false); if (pending.current) { pending.current = false; if (r[0]) add(r[0]); } })
        .catch(() => { if (!ac.signal.aborted) { setItems([]); setLoading(false); pending.current = false; } });
    }, 150);
    return () => { window.clearTimeout(t); ac.abort(); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q]);
  const onKey = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.nativeEvent.isComposing) return;
    if (e.key === 'ArrowDown') { e.preventDefault(); setOpen(true); setActive((a) => Math.min(a + 1, Math.max(0, items.length - 1))); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setActive((a) => Math.max(0, a - 1)); }
    else if (e.key === 'Enter') {
      e.preventDefault();
      if (!q.trim()) return;
      if (items.length && !loading) add(items[Math.min(active, items.length - 1)]);
      else pending.current = true;
    } else if (e.key === 'Escape') { setOpen(false); setQtyFor(null); }
    else if (e.key === 'Backspace' && !q && value.length) onChange(value.slice(0, -1));
  };
  const show = open && q.trim().length > 0;
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      <div className={cx('img-prodbox', dropActive && 'img-prodbox--drop')} data-testid="img-products">
        {show && (
          <div className="img-results" id={listId} role="listbox" aria-label="제품 검색 결과" onMouseDown={(e) => e.preventDefault()}>
            <div className="img-results__head">"{q.trim()}" 검색 결과 · 방향키로 이동, Enter로 추가</div>
            {loading && !items.length && <div className="img-results__head">찾는 중…</div>}
            {!loading && !items.length && <div className="img-results__head">카탈로그에서 맞는 제품을 찾지 못했어요.</div>}
            {items.map((it, i) => (
              <button key={`${it.kind}:${it.id}`} type="button" role="option" aria-selected={i === active} className="img-result" onMouseEnter={() => setActive(i)} onClick={() => add(it)}>
                <span className="img-result__thumb"><Img src={it.thumb?.thumb_url ?? null} alt="" fit="contain" /></span>
                <span style={{ display: 'flex', flexDirection: 'column', minWidth: 0 }}>
                  <span className="img-result__name">{it.label || productName(it)}</span>
                  {it.meta_line && <span className="img-result__meta">{it.meta_line}</span>}
                </span>
              </button>
            ))}
          </div>
        )}
        {value.map((p, i) => (
          <span key={`${p.model_code ?? p.family_id ?? p.name}-${i}`} className="img-prodchip" data-testid="img-prodchip">
            <span>{p.name}</span>
            <button type="button" className="img-prodchip__qty" title="수량 바꾸기" aria-label={`${p.short} 수량 바꾸기`} aria-haspopup="menu" aria-expanded={qtyFor === i}
              onClick={() => setQtyFor(qtyFor === i ? null : i)}>{p.qty > 1 ? `×${p.qty}` : '×1'}</button>
            <button type="button" className="img-prodchip__x" aria-label="제거" title={`${p.short} 제거`} onClick={() => onChange(value.filter((_, k) => k !== i))}>
              <Icon name="x" size={11} strokeWidth={2.6} />
            </button>
            {qtyFor === i && (
              <span className="img-qtymenu" role="menu" aria-label="수량">
                {[1, 2, 3, 4, 5, 6, 7, 8, 9].map((n) => (
                  <button key={n} type="button" role="menuitemradio" aria-checked={p.qty === n} aria-pressed={p.qty === n}
                    onClick={() => { onChange(value.map((x, k) => (k === i ? { ...x, qty: n } : x))); setQtyFor(null); }}>{n}</button>
                ))}
              </span>
            )}
          </span>
        ))}
        <label htmlFor={inputId} className="wm-sr-only">제품명 입력</label>
        <input id={inputId} value={q} placeholder="제품명을 입력해 추가…" autoComplete="off" spellCheck={false} role="combobox" aria-expanded={show} aria-controls={listId}
          onChange={(e) => { setQ(e.target.value); setOpen(true); }} onKeyDown={onKey} onFocus={() => setOpen(true)} onBlur={() => setOpen(false)} />
        {onDropRefs}
      </div>
      {message && <span className="img-hint img-hint--sm" data-testid="img-prefill-msg">{message}</span>}
    </div>
  );
}

/** 짧은 숫자 알약 */
export function CountPill({ n, brand }: { n: number | string; brand?: boolean }) {
  return <span className={cx('img-count', brand && 'img-count--brand')}>{n}</span>;
}

/** 드롭다운(갤러리 필터) */
export function Dropdown<T extends string>({ label, value, options, onChange }: { label: string; value: T; options: Array<{ value: T; label: string }>; onChange: (v: T) => void }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const h = (e: MouseEvent) => { if (!ref.current?.contains(e.target as Node)) setOpen(false); };
    document.addEventListener('mousedown', h);
    return () => document.removeEventListener('mousedown', h);
  }, [open]);
  useEscape(() => setOpen(false), open);
  const cur = options.find((o) => o.value === value);
  return (
    <div className="img-drop" ref={ref}>
      <button type="button" className={cx('img-pill', value && options[0]?.value !== value && 'img-pill--on')} aria-haspopup="menu" aria-expanded={open} onClick={() => setOpen(!open)}>
        <span>{cur && cur.value !== options[0]?.value ? cur.label : label}</span><Icon name="chevronDown" size={11} strokeWidth={2.4} />
      </button>
      {open && (
        <div className="img-drop__menu" role="menu" aria-label={label}>
          {options.map((o) => (
            <button key={o.value} type="button" role="menuitemradio" aria-checked={o.value === value} onClick={() => { onChange(o.value); setOpen(false); }}>{o.label}</button>
          ))}
        </div>
      )}
    </div>
  );
}

/** 지연 효과(배치 저장 300ms 디바운스 등) */
export function useDebounced<T>(fn: (v: T) => void, ms: number) {
  const t = useRef<number | undefined>(undefined);
  const f = useRef(fn);
  f.current = fn;
  return useMemo(() => {
    const call = (v: T) => { if (t.current) window.clearTimeout(t.current); t.current = window.setTimeout(() => f.current(v), ms); };
    return call;
  }, [ms]);
}
