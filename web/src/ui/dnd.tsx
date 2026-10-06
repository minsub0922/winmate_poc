/**
 * 끌어서 추가(DnD) 기반 — 00-shell §5.7 · §2.8(DragGhost · DropZone) · §7.5(드래그 데이터).
 *
 * - 끌 수 있는 것: 셸 팝오버 항목(제품·솔루션·이미지·사례)과 사이드바 작업 항목. 셸이 `useDragSource` 로 붙인다.
 * - 드래그 데이터: MIME `application/x-winmate` JSON `{type, ref, label, sub, feature?}`.
 * - 놓는 곳: 기능 화면이 `<DropZone accept=[…] onDrop={…}>` 또는 `useDropTarget` 으로 만든다.
 *   onDrop 이 성공하면(false 가 아니면) 셸이 그 항목을 `✓ 추가됨` 으로 표시한다(`onItemDropped` 구독).
 */
import { useCallback, useEffect, useRef, useState, useSyncExternalStore, type CSSProperties, type DragEvent, type ReactNode } from 'react';
import { Button, cx } from './controls';
import { Grip, Icon, PathIcon } from './icons';

export type DragType = 'product' | 'solution' | 'image' | 'case' | 'work_item';
export const DRAG_MIME = 'application/x-winmate';

export interface DragPayload {
  type: DragType;
  /** 참조 문자열: `kb:model:mdl_…` · `kb:solution:magicinfo` · `kb:image:img_…` · `kb:case:dep_…` · `ws:item:<id>` */
  ref: string;
  /** 고스트 이름 줄(예: `QM65C`) */
  label: string;
  /** 고스트 보조 줄(예: `제품 · 단독형 UHD M 시리즈 65"` · `사이드바 · Market Intelligence`) */
  sub: string;
  /** work_item 이면 기능 코드(RQ…PR) */
  feature?: string;
  /** 고스트 아이콘 path(24×24). 없으면 유형 기본 아이콘 */
  icon?: string;
}

/** 유형 기본 아이콘(부록 A: 드래그 유형 아이콘) */
export const DRAG_TYPE_ICON: Record<DragType, string> = {
  product: 'M4 4h7v7H4z M13 4h7v7h-7z M4 13h7v7H4z M13 13h7v7h-7z',
  solution: 'M12 3l9 5-9 5-9-5 9-5z M3 13l9 5 9-5',
  image: 'M3 6a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z M9 8a2 2 0 1 0 0 4 2 2 0 0 0 0-4z M21 16l-5-5-9 9',
  case: 'M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7z M9 14h6',
  work_item: 'M6 3h8l5 5v13H6z M14 3v5h5',
};
/** 받는 유형 칩 글(§5.7) */
export const DRAG_TYPE_LABEL: Record<DragType, string> = { product: '제품', solution: '솔루션', image: '이미지', case: '유관 사례', work_item: '작업 (사이드바)' };

// ── 전역 상태(지금 끄는 항목) ──────────────────────────
let active: DragPayload | null = null;
let cancelled = false;
let startPos = { x: 0, y: 0 };
const subs = new Set<() => void>();
const dropSubs = new Set<(p: DragPayload) => void>();
const subscribe = (cb: () => void) => { subs.add(cb); return () => { subs.delete(cb); }; };
function setActive(p: DragPayload | null) { active = p; subs.forEach((f) => f()); }

/** 지금 끄는 항목(없으면 null) */
export const getActiveDrag = () => active;
export function useActiveDrag() { return useSyncExternalStore(subscribe, getActiveDrag, getActiveDrag); }
/** 드롭이 성공했을 때 알림을 받는다(셸이 `added` 표시에 쓴다). 해제 함수를 돌려준다. */
export function onItemDropped(fn: (p: DragPayload) => void) { dropSubs.add(fn); return () => { dropSubs.delete(fn); }; }
export function notifyDropped(p: DragPayload) { dropSubs.forEach((f) => f(p)); }
/** 끄는 중이면 취소한다(Esc). */
export function cancelActiveDrag() { if (active) { cancelled = true; setActive(null); } }

if (typeof window !== 'undefined') {
  window.addEventListener('keydown', (e) => { if (e.key === 'Escape' && active) { e.preventDefault(); cancelActiveDrag(); } }, true);
}

let blankImg: HTMLImageElement | null = null;
function blank() {
  if (!blankImg && typeof Image !== 'undefined') {
    blankImg = new Image();
    blankImg.src = 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7';
  }
  return blankImg;
}
blank();

/** dataTransfer 에서 드래그 데이터를 읽는다(없으면 지금 끄는 항목). */
export function readDragPayload(e: DragEvent | globalThis.DragEvent): DragPayload | null {
  try {
    const raw = e.dataTransfer?.getData(DRAG_MIME);
    if (raw) return JSON.parse(raw) as DragPayload;
  } catch { /* 형식이 다르면 무시 */ }
  return active;
}

/**
 * 끌기 원천 props. payload 가 null 이면 끌 수 없다(빈 객체).
 *   <div {...useDragSource(canDrag ? payload : null)}>…</div>
 */
export function useDragSource(payload: DragPayload | null) {
  const ref = useRef(payload);
  ref.current = payload;
  const onDragStart = useCallback((e: DragEvent) => {
    const p = ref.current;
    if (!p) return;
    e.stopPropagation();
    e.dataTransfer.setData(DRAG_MIME, JSON.stringify(p));
    e.dataTransfer.setData('text/plain', p.label);
    e.dataTransfer.effectAllowed = 'copy';
    const img = blank();
    if (img && img.complete) { try { e.dataTransfer.setDragImage(img, 0, 0); } catch { /* 일부 브라우저 */ } }
    cancelled = false;
    startPos = { x: e.clientX, y: e.clientY };
    // 같은 틱에 원천의 스타일을 바꾸면 크롬이 끌기를 취소한다 → 다음 틱에 상태를 켠다
    window.setTimeout(() => { if (!cancelled) setActive(p); }, 0);
  }, []);
  const onDragEnd = useCallback(() => { setActive(null); }, []);
  if (!payload) return {};
  return { draggable: true, onDragStart, onDragEnd };
}

export type DropState = 'idle' | 'dragging' | 'over' | 'dropped';
export interface DropResult { note?: ReactNode }

export interface UseDropTargetOptions {
  accept: DragType[];
  /** work_item 일 때 받는 기능 코드(없으면 모든 기능) */
  acceptWork?: string[];
  /** 성공이면 아무것도 안 돌려주거나 true/{note}. false 면 실패(added 표시 안 함). 예외도 실패. */
  onDrop: (p: DragPayload) => void | boolean | DropResult | Promise<void | boolean | DropResult>;
  disabled?: boolean;
}

/** 드롭 영역 훅 — 상태(idle · dragging · over · dropped)와 영역에 펼칠 props 를 준다. */
export function useDropTarget({ accept, acceptWork, onDrop, disabled }: UseDropTargetOptions) {
  const cur = useActiveDrag();
  const [over, setOver] = useState(false);
  const [dropped, setDropped] = useState<{ payload: DragPayload; note?: ReactNode } | null>(null);
  const [busy, setBusy] = useState(false);
  const depth = useRef(0);
  const cb = useRef(onDrop);
  cb.current = onDrop;
  const accepts = useCallback((p: DragPayload | null) => {
    if (!p || disabled) return false;
    if (!accept.includes(p.type)) return false;
    if (p.type === 'work_item' && acceptWork?.length && !(p.feature && acceptWork.includes(p.feature))) return false;
    return true;
  }, [accept, acceptWork, disabled]);
  const dragging = accepts(cur);
  useEffect(() => { if (!cur) { depth.current = 0; setOver(false); } }, [cur]);

  // 지금 끄는 항목을 받을 수 있나(상태가 아직 안 켜졌으면 MIME 형식만 본다)
  const ok = (e: DragEvent) => {
    const a = getActiveDrag();
    if (a) return accepts(a);
    return !disabled && !!e.dataTransfer?.types?.includes(DRAG_MIME);
  };
  const props = {
    onDragEnter: (e: DragEvent) => { if (!ok(e)) return; e.preventDefault(); depth.current += 1; setOver(true); },
    onDragOver: (e: DragEvent) => { if (!ok(e)) return; e.preventDefault(); e.dataTransfer.dropEffect = 'copy'; },
    onDragLeave: () => { depth.current = Math.max(0, depth.current - 1); if (depth.current === 0) setOver(false); },
    onDrop: async (e: DragEvent) => {
      const p = readDragPayload(e);
      depth.current = 0;
      setOver(false);
      if (!p || cancelled || !accepts(p)) return;
      e.preventDefault();
      setActive(null);
      setBusy(true);
      try {
        const r = await cb.current(p);
        if (r === false) return;
        notifyDropped(p);
        setDropped({ payload: p, note: r && typeof r === 'object' ? r.note : undefined });
      } catch { /* 기능이 오류를 보여 준다 */ } finally { setBusy(false); }
    },
  };
  const state: DropState = dragging ? (over ? 'over' : 'dragging') : dropped ? 'dropped' : 'idle';
  return { state, props, dragging, over, busy, active: cur, dropped, clearDropped: () => setDropped(null) };
}

export interface DropZoneProps extends UseDropTargetOptions {
  /** 대기 글(기본 `여기에 끌어 놓기`) */
  idleText?: ReactNode;
  /** 받는 유형 칩 글을 바꿀 때 */
  chipLabels?: Partial<Record<DragType, string>>;
  /** work_item 칩 앞 기능 이름(예: 'MI' → `MI 작업 (사이드바)`) */
  workLabel?: string;
  /** 끄는 중 제목(기본 `여기에 놓아 「{이름}」 추가`) */
  dragTitle?: (p: DragPayload) => ReactNode;
  /** 끄는 중 보조 줄 */
  dragSub?: (p: DragPayload) => ReactNode;
  /** 놓은 뒤 설명(기본은 onDrop 이 돌려준 note) */
  droppedNote?: (p: DragPayload) => ReactNode;
  /** 있으면 놓은 뒤 `실행 취소` 버튼 */
  onUndo?: (p: DragPayload) => void | Promise<void>;
  className?: string;
  style?: CSSProperties;
}

/**
 * 드롭 영역(§2.8 DropZone): 대기 h40 점선 + 받는 유형 칩 / 끄는 중 h76 강조 / 놓은 뒤 `「{이름}」 추가됨 · {설명}` + `실행 취소`.
 */
export function DropZone(props: DropZoneProps) {
  const { idleText = '여기에 끌어 놓기', chipLabels, workLabel, dragTitle, dragSub, droppedNote, onUndo, className, style, accept } = props;
  const t = useDropTarget(props);
  const p = t.active;
  const chip = (k: DragType) => chipLabels?.[k] ?? (k === 'work_item' ? `${workLabel ? `${workLabel} ` : ''}작업 (사이드바)` : DRAG_TYPE_LABEL[k]);
  let body: ReactNode;
  if ((t.state === 'dragging' || t.state === 'over') && p) {
    body = (
      <>
        <span className="wm-drop__icon"><Icon name="drop" size={18} color="var(--wm-brand)" /></span>
        <span style={{ display: 'flex', flexDirection: 'column', gap: 3, minWidth: 0, maxWidth: 480 }}>
          <span className="wm-drop__title wm-ellipsis">{dragTitle ? dragTitle(p) : <>여기에 놓아 「{p.label}」 추가</>}</span>
          {dragSub && <span className="wm-drop__sub wm-ellipsis">{dragSub(p)}</span>}
        </span>
      </>
    );
  } else if (t.state === 'dropped' && t.dropped) {
    const d = t.dropped;
    const note = droppedNote ? droppedNote(d.payload) : d.note;
    body = (
      <>
        <Icon name="check" size={14} color="var(--wm-brand)" strokeWidth={2.8} />
        <span className="wm-ellipsis" style={{ flex: 1 }}>
          <b style={{ fontWeight: 700 }}>「{d.payload.label}」</b> 추가됨{note ? <> · <span style={{ color: 'var(--wm-text-muted)' }}>{note}</span></> : null}
        </span>
        {onUndo && <Button h={26} brandText onClick={async () => { await onUndo(d.payload); t.clearDropped(); }}>실행 취소</Button>}
      </>
    );
  } else {
    body = (
      <>
        <Icon name="drop" size={14} color="var(--wm-text-muted)" />
        <span style={{ flexShrink: 0 }}>{idleText}</span>
        {accept.map((k) => <span key={k} className="wm-drop__chip">{chip(k)}</span>)}
      </>
    );
  }
  const vis = t.state === 'over' ? 'dragging' : t.state;
  return (
    <div {...t.props} className={cx('wm-drop', `wm-drop--${vis}`, t.state === 'over' && 'wm-drop--over', className)} style={style}
      data-drop-state={t.state} aria-busy={t.busy || undefined} aria-label="끌어 놓는 영역">
      {body}
    </div>
  );
}

/** 고스트 카드(§2.8 DragGhost) — 폭 270(항목)/290(사이드바 작업), rotate(-2deg) */
export function DragGhost({ payload, x, y, style }: { payload: DragPayload; x: number; y: number; style?: CSSProperties }) {
  const work = payload.type === 'work_item';
  const w = work ? 290 : 270;
  return (
    <div className="wm-ghost" role="presentation" data-testid="drag-ghost" data-ref={payload.ref}
      style={{ width: w, transform: `translate(${Math.round(x - w + 22)}px, ${Math.round(y - 34)}px) rotate(-2deg)`, ...style }}>
      <span className="wm-ghost__icon"><PathIcon d={payload.icon ?? DRAG_TYPE_ICON[payload.type]} size={16} color="var(--wm-brand)" /></span>
      <span style={{ display: 'flex', flexDirection: 'column', gap: 2, minWidth: 0, flex: 1 }}>
        <span className="wm-ghost__sub">{payload.sub}</span>
        <span className="wm-ghost__label">{payload.label}</span>
      </span>
      {!work && <span className="wm-ghost__plus"><Icon name="plus" size={12} color="#fff" strokeWidth={3} /></span>}
    </div>
  );
}

/** 끄는 동안 커서를 따라 고스트를 그린다. 앱에 한 번만 둔다(셸 Layout). */
export function DragGhostLayer() {
  const p = useActiveDrag();
  const [pos, setPos] = useState(startPos);
  useEffect(() => {
    if (!p) return;
    setPos(startPos);
    let raf = 0;
    let last = startPos;
    const h = (e: globalThis.DragEvent) => {
      if (!e.clientX && !e.clientY) return;
      last = { x: e.clientX, y: e.clientY };
      if (!raf) raf = requestAnimationFrame(() => { raf = 0; setPos(last); });
    };
    document.addEventListener('dragover', h, true);
    document.addEventListener('drag', h, true);
    return () => { document.removeEventListener('dragover', h, true); document.removeEventListener('drag', h, true); if (raf) cancelAnimationFrame(raf); };
  }, [p]);
  if (!p) return null;
  return <DragGhost payload={p} x={pos.x} y={pos.y} />;
}

/** 끌기 손잡이 표시(행 그립) */
export const DragHandle = ({ color }: { color?: string }) => <Grip color={color} />;

// ── 파일 업로드 영역(파일을 끌어다 놓기 · 클릭해 고르기) ──
export function Dropzone({ onFiles, accept, multiple = true, title, hint, children, disabled }:
  { onFiles: (files: File[]) => void; accept?: string; multiple?: boolean; title?: ReactNode; hint?: ReactNode; children?: ReactNode; disabled?: boolean }) {
  const [over, setOver] = useState(false);
  const ref = useRef<HTMLInputElement>(null);
  const take = useCallback((list: FileList | null) => { if (list && list.length) onFiles(Array.from(list)); }, [onFiles]);
  return (
    <div className={cx('wm-dropzone', over && 'wm-dropzone--over')} role="button" tabIndex={0} aria-disabled={disabled}
      onClick={() => !disabled && ref.current?.click()}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); ref.current?.click(); } }}
      onDragOver={(e) => { if (!e.dataTransfer.types.includes('Files')) return; e.preventDefault(); if (!disabled) setOver(true); }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => { if (!e.dataTransfer.files.length) return; e.preventDefault(); setOver(false); if (!disabled) take(e.dataTransfer.files); }}>
      <input ref={ref} type="file" hidden accept={accept} multiple={multiple} onChange={(e) => { take(e.target.files); e.target.value = ''; }} />
      {children ?? (
        <>
          <span style={{ width: 46, height: 46, borderRadius: 14, background: 'var(--wm-brand-50)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Icon name="upload" size={22} color="var(--wm-brand)" />
          </span>
          <span style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            <span style={{ fontSize: 15, fontWeight: 700 }}>{title ?? '파일을 끌어다 놓으세요'}</span>
            {hint && <span style={{ fontSize: 12.5, color: 'var(--wm-text-subtle)' }}>{hint}</span>}
          </span>
          <Button size="md" icon={<Icon name="upload" size={14} color="var(--wm-brand)" />}>파일 첨부</Button>
        </>
      )}
    </div>
  );
}
export const FileDropzone = Dropzone;
