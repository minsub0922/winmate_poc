/**
 * 겹침 요소 — 모달(시트) · 포커스 가두기 · 확인 대화상자 · 토스트.
 */
import { useCallback, useEffect, useId, useRef, useState, useSyncExternalStore, type CSSProperties, type ReactNode, type RefObject } from 'react';
import { Button, CloseButton, cx } from './controls';

const FOCUSABLE = [
  'a[href]', 'area[href]', 'button:not([disabled])', 'input:not([disabled]):not([type="hidden"])', 'select:not([disabled])',
  'textarea:not([disabled])', 'iframe', '[tabindex]:not([tabindex="-1"])', '[contenteditable="true"]',
].join(',');

export function focusablesIn(root: HTMLElement): HTMLElement[] {
  return Array.from(root.querySelectorAll<HTMLElement>(FOCUSABLE)).filter((el) => el.getClientRects().length > 0 && !el.closest('[inert]'));
}

/**
 * 포커스를 컨테이너 안에 가둔다(Tab/Shift+Tab 순환). 켤 때 첫 요소(또는 initialFocus)로, 끌 때 원래 자리로 되돌린다.
 */
export function useFocusTrap(ref: RefObject<HTMLElement | null>, active: boolean, opts: { initialFocus?: () => HTMLElement | null; restoreFocus?: boolean } = {}) {
  const optsRef = useRef(opts);
  optsRef.current = opts;
  useEffect(() => {
    if (!active) return;
    const root = ref.current;
    if (!root) return;
    const opener = document.activeElement as HTMLElement | null;
    const t = window.setTimeout(() => {
      const el = optsRef.current.initialFocus?.() ?? focusablesIn(root)[0] ?? root;
      if (el && !root.contains(document.activeElement)) el.focus({ preventScroll: true });
    }, 0);
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== 'Tab') return;
      const r = ref.current;
      if (!r) return;
      const list = focusablesIn(r);
      if (!list.length) { e.preventDefault(); r.focus(); return; }
      const first = list[0];
      const last = list[list.length - 1];
      const cur = document.activeElement as HTMLElement | null;
      if (!cur || !r.contains(cur)) { e.preventDefault(); (e.shiftKey ? last : first).focus(); return; }
      if (e.shiftKey && cur === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && cur === last) { e.preventDefault(); first.focus(); }
    };
    document.addEventListener('keydown', onKey, true);
    return () => {
      window.clearTimeout(t);
      document.removeEventListener('keydown', onKey, true);
      if (optsRef.current.restoreFocus !== false && opener && opener.isConnected && typeof opener.focus === 'function') {
        window.setTimeout(() => { if (opener.isConnected) opener.focus({ preventScroll: true }); }, 0);
      }
    };
  }, [active, ref]);
}

/** Esc 로 닫기(창 수준). enabled 가 false 면 듣지 않는다. */
export function useEscape(onEscape: () => void, enabled = true) {
  const cb = useRef(onEscape);
  cb.current = onEscape;
  useEffect(() => {
    if (!enabled) return;
    const h = (e: KeyboardEvent) => { if (e.key === 'Escape' && !e.defaultPrevented) cb.current(); };
    window.addEventListener('keydown', h);
    return () => window.removeEventListener('keydown', h);
  }, [enabled]);
}

export interface ModalProps {
  open: boolean;
  onClose: () => void;
  title?: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
  width?: number;
  height?: number;
  /** title 이 노드가 아닐 때 대화상자 접근 이름 */
  ariaLabel?: string;
  /**
   * 'sheet'(가운데 r18 · --wm-shadow-sheet, 기본) · 'dialog'(작은 확인창) ·
   * 'side'(오른쪽에 붙는 높이 100% 시트 — 읽기 전용 규칙 · 상세 보기, 폭 = width, 왼쪽 모서리만 r18 · 밀려 들어옴)
   */
  variant?: 'sheet' | 'dialog' | 'side';
  /** 딤 클릭으로 닫기(기본 true) */
  closeOnScrim?: boolean;
  bodyStyle?: CSSProperties;
}

/** 모달(§2.8 Sheet(Modal)): 딤 `rgba(18,20,23,0.42)` · r18 · 포커스 가두기 · Esc · 딤 클릭. `variant="side"` 면 오른쪽 시트 */
export function Modal({ open, onClose, title, children, footer, width = 720, height, ariaLabel, variant = 'sheet', closeOnScrim = true, bodyStyle }: ModalProps) {
  const ref = useRef<HTMLDivElement>(null);
  const titleId = useId();
  useFocusTrap(ref, open);
  useEscape(onClose, open);
  if (!open) return null;
  const side = variant === 'side';
  return (
    <div className={cx('wm-scrim', side && 'wm-scrim--side')} onMouseDown={(e) => { if (closeOnScrim && e.target === e.currentTarget) onClose(); }}>
      <div ref={ref} className={cx('wm-modal', variant === 'dialog' && 'wm-modal--dialog', side && 'wm-modal--side')} role="dialog" aria-modal="true" tabIndex={-1}
        aria-label={typeof title === 'string' ? title : ariaLabel} aria-labelledby={title && typeof title !== 'string' ? titleId : undefined}
        data-variant={variant}
        style={side ? { width, height: '100vh', maxWidth: 'calc(100vw - 48px)', maxHeight: '100vh' }
          : { width, height, maxWidth: 'calc(100vw - 80px)', maxHeight: 'calc(100vh - 72px)' }}>
        {title !== undefined && (
          <div className="wm-modal__head"><div className="wm-modal__title" id={titleId}>{title}</div><CloseButton size={34} onClick={onClose} /></div>
        )}
        <div className="wm-modal__body" style={bodyStyle}>{children}</div>
        {footer && <div className="wm-modal__foot">{footer}</div>}
      </div>
    </div>
  );
}

/**
 * 오른쪽 시트(읽기 전용 규칙 · 상세 보기) — `Modal variant="side"` 와 같다. 폭 기본 560, Esc · 딤 클릭으로 닫힘, 포커스 가둠.
 *   <SideSheet open={open} onClose={close} title="에이전트 라우팅 규칙" width={880}>…</SideSheet>
 */
export function SideSheet(props: Omit<ModalProps, 'variant'>) {
  return <Modal width={560} {...props} variant="side" />;
}

export interface ConfirmOptions {
  title: ReactNode;
  message?: ReactNode;
  confirmLabel?: string;
  cancelLabel?: string;
  /** primary(기본) · dark · danger */
  tone?: 'primary' | 'dark' | 'danger';
}

/** 확인 대화상자(폭 420). */
export function ConfirmDialog({ open, title, message, confirmLabel = '확인', cancelLabel = '취소', tone = 'primary', busy, onConfirm, onCancel }:
  ConfirmOptions & { open: boolean; busy?: boolean; onConfirm: () => void; onCancel: () => void }) {
  return (
    <Modal open={open} onClose={onCancel} variant="dialog" width={420} ariaLabel={typeof title === 'string' ? title : '확인'} bodyStyle={{ padding: '20px 22px 8px' }}
      footer={<>
        <Button h={38} onClick={onCancel}>{cancelLabel}</Button>
        <Button h={38} variant={tone === 'danger' ? 'danger' : tone} loading={busy} onClick={onConfirm}>{confirmLabel}</Button>
      </>}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        <strong style={{ fontSize: 15 }}>{title}</strong>
        {message && <div style={{ fontSize: 12.5, color: 'var(--wm-text-muted)', lineHeight: 1.5 }}>{message}</div>}
      </div>
    </Modal>
  );
}

/**
 * 약속형 확인창: `const { confirm, dialog } = useConfirm(); … if (await confirm({ title: '삭제할까요?' })) …; return <>{dialog}</>`
 */
export function useConfirm() {
  const [state, setState] = useState<(ConfirmOptions & { resolve: (v: boolean) => void }) | null>(null);
  const confirm = useCallback((o: ConfirmOptions) => new Promise<boolean>((resolve) => setState({ ...o, resolve })), []);
  const close = (v: boolean) => { state?.resolve(v); setState(null); };
  const dialog = state ? <ConfirmDialog open {...state} onConfirm={() => close(true)} onCancel={() => close(false)} /> : null;
  return { confirm, dialog };
}

// ── Toast(보드에 없음 — Q-UI-2. 화면 안 배너를 먼저 쓰고, 화면을 떠나는 알림에만 쓴다) ──
interface ToastItem { id: number; message: ReactNode; action?: { label: string; onClick: () => void } }
let toasts: ToastItem[] = [];
let seq = 0;
const toastSubs = new Set<() => void>();
const emit = () => toastSubs.forEach((f) => f());

export function toast(message: ReactNode, opts: { action?: { label: string; onClick: () => void }; duration?: number } = {}) {
  const id = ++seq;
  toasts = [...toasts, { id, message, action: opts.action }];
  emit();
  window.setTimeout(() => { toasts = toasts.filter((t) => t.id !== id); emit(); }, opts.duration ?? 3200);
  return id;
}

export function ToastHost() {
  const list = useSyncExternalStore((cb) => { toastSubs.add(cb); return () => { toastSubs.delete(cb); }; }, () => toasts, () => toasts);
  if (!list.length) return null;
  return (
    <div className="wm-toasts" aria-live="polite">
      {list.map((t) => (
        <div key={t.id} className="wm-toast" role="status">
          <span>{t.message}</span>
          {t.action && <button type="button" onClick={() => { t.action!.onClick(); toasts = toasts.filter((x) => x.id !== t.id); emit(); }}>{t.action.label}</button>}
        </div>
      ))}
    </div>
  );
}
