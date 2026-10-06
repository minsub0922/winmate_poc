/**
 * 팝오버 4종 공통 틀(00-shell §3.3 · §5.2.4 · §5.2.5) — 틀 · 검색 줄 · 끌기 안내 · 푸터 · 상태 기억.
 */
import { useCallback, useEffect, useRef, useState, type CSSProperties, type ReactNode } from 'react';
import { Button, CloseButton, Grip, Icon, SearchField, type AddState } from '@/ui';
import { NO_TASK_TIP, useShellRuntime } from '../runtime';
import type { DragType } from '../types';
import type { PopoverKind } from '../urlState';

export const POP_SIZE: Record<PopoverKind, [number, number]> = { product: [700, 540], solution: [600, 500], image: [820, 560], case: [780, 730] };
export const POP_TITLE: Record<PopoverKind, string> = { product: '제품 탐색', solution: '솔루션 탐색', image: '이미지 검색', case: '유관 사례 검색' };

/** 팝오버 틀: role=dialog, 크기는 보드 값(작은 화면에선 줄어든다 §3.5), 끄는 중이면 반투명 + 포인터 통과 */
export function PopoverFrame({ kind, hidden, dragging, children }: { kind: PopoverKind; hidden?: boolean; dragging?: boolean; children: ReactNode }) {
  const [w, h] = POP_SIZE[kind];
  const style: CSSProperties = { width: w, height: `min(${h}px, calc(100vh - 80px))` };
  return (
    <div role="dialog" aria-label={POP_TITLE[kind]} id={`sh-pop-${kind}`} data-popover={kind} aria-hidden={hidden || undefined}
      className={['sh-pop', dragging && 'sh-pop--dragging', hidden && 'sh-pop--hidden'].filter(Boolean).join(' ')} style={style}>
      {children}
    </div>
  );
}

/** 검색 줄(§5.3.1-1): 검색 입력 + 닫기 32×32 */
export function PopSearch({ label, placeholder, value, onChange, onClose, autoFocus = true }:
  { label: string; placeholder?: string; value: string; onChange: (v: string) => void; onClose: () => void; autoFocus?: boolean }) {
  return (
    <div className="sh-pop__search">
      <SearchField label={label} placeholder={placeholder} value={value} onChange={onChange} autoFocus={autoFocus} />
      <CloseButton onClick={onClose} />
    </div>
  );
}

/** `끌어서 바로 추가`(그립 brand) */
export function DragHint() {
  return <span className="sh-draghint"><Grip color="var(--wm-brand)" />끌어서 바로 추가</span>;
}

/** Esc 로 닫기 — 끄는 중(Esc 는 끌기 취소)과 상세 시트가 열린 동안은 무시 */
export function usePopoverEscape(onClose: () => void, enabled: boolean) {
  const cb = useRef(onClose);
  cb.current = onClose;
  useEffect(() => {
    if (!enabled) return;
    const h = (e: KeyboardEvent) => {
      if (e.key !== 'Escape' || e.defaultPrevented) return;
      if (document.querySelector('.sh-sheet')) return;
      cb.current();
    };
    window.addEventListener('keydown', h);
    return () => window.removeEventListener('keydown', h);
  }, [enabled]);
}

export function useDebounced<T>(value: T, ms: number) {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = window.setTimeout(() => setV(value), ms);
    return () => window.clearTimeout(t);
  }, [value, ms]);
  return v;
}

/** 팝오버 상태를 같은 작업 동안 기억한다(T-12) */
export function usePopMemory<T extends object>(kind: string, init: () => T): [T, (patch: Partial<T> | ((s: T) => Partial<T>)) => void] {
  const rt = useShellRuntime();
  const [state, setState] = useState<T>(() => ({ ...init(), ...(rt.recall<Partial<T>>(kind) ?? {}) }));
  const remember = rt.remember;
  useEffect(() => { remember(kind, state); }, [kind, state, remember]);
  const patch = useCallback((p: Partial<T> | ((s: T) => Partial<T>)) => setState((s) => ({ ...s, ...(typeof p === 'function' ? p(s) : p) })), []);
  return [state, patch];
}

export interface TrayEntry { ref: string; label: string }

/** 항목 버튼 상태(§5.2.4) */
export function useAddState(type: DragType) {
  const rt = useShellRuntime();
  return useCallback((r: string, inTray: boolean): AddState => {
    if (!rt.canAdd(type)) return rt.isAdded(r) && rt.hasTask ? 'added' : 'off';
    if (rt.isAdded(r)) return 'added';
    return inTray ? 'sel' : 'add';
  }, [rt, type]);
}

/** `현재 작업에 추가` 실행 + 결과 상태 */
export function useAddRunner(type: DragType, tray: TrayEntry[], clear: () => void) {
  const rt = useShellRuntime();
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);
  const run = async () => {
    if (!tray.length || busy) return;
    setBusy(true);
    setFailed(false);
    const res = await rt.runAdd(type, tray.map((t) => t.ref));
    setBusy(false);
    if (res.ok) clear(); else setFailed(true);
  };
  return { run, busy, failed, setFailed };
}

export const ADD_FAIL_TEXT = '추가하지 못했어요. 다시 시도해 주세요.';

/** 작업 없음 푸터(정보 아이콘 + 안내 + 비활성 버튼) */
export function NoTaskFooter({ text, buttons = ['현재 작업에 추가'] }: { text: string; buttons?: string[] }) {
  return (
    <div className="sh-pop__foot" data-footer="no-task">
      <Icon name="info" size={15} color="var(--wm-text-muted)" />
      <span className="sh-pop__foot-note">{text}</span>
      {buttons.map((b) => <Button key={b} h={32} disabled disabledReason={NO_TASK_TIP}>{b}</Button>)}
    </div>
  );
}

/** `현재 작업에 추가` 버튼(n>0 이면 primary, 0 이면 off) */
export function AddAllButton({ n, onClick, busy, disabledReason }: { n: number; onClick: () => void; busy?: boolean; disabledReason?: string }) {
  const off = n === 0 || !!disabledReason;
  return (
    <Button h={32} variant={off ? 'secondary' : 'primary'} disabled={off} loading={busy} onClick={onClick}
      disabledReason={disabledReason || '먼저 추가할 항목을 고르세요'}>
      현재 작업에 추가
    </Button>
  );
}
