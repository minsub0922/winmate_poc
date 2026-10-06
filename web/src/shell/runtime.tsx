/**
 * 셸 실행 맥락(라우터 안) — 작업 유무 · 추가 가능 여부 · 이미 추가된 참조 · 팝오버 기억(같은 작업 동안 유지, T-12).
 * 팝오버 · 상세 시트 · 사이드바가 쓴다. 기능 화면은 `useShellPage` 만 쓰면 된다.
 */
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { useLocation } from 'react-router';
import { onItemDropped } from '@/ui';
import { useShell } from './ShellContext';
import type { DragType, ShellPageConfig } from './types';

const ADDABLE_ALL: DragType[] = ['product', 'solution', 'image', 'case'];
export const NO_TASK_ITEM_TIP = '진행 중인 작업이 없어 추가할 수 없습니다';
export const NO_TASK_TIP = '진행 중인 작업이 없습니다';
export const NO_HANDLER_TIP = '이 화면에서는 추가할 수 없습니다';

export interface ShellRuntime {
  /** 작업 식별(현재 경로) — 팝오버 기억 · 세션 added 의 범위 */
  taskKey: string;
  page: ShellPageConfig;
  hasTask: boolean;
  canAdd: (type: DragType) => boolean;
  /** 추가 버튼이 꺼진 이유(항목 버튼용 · 푸터/시트용) */
  offReason: (type: DragType, where?: 'item' | 'footer') => string;
  canDrag: (type: DragType) => boolean;
  isAdded: (r: string) => boolean;
  markAdded: (refs: string[]) => void;
  /** page.onAdd 를 부르고 성공하면 added 로 표시한다 */
  runAdd: (type: DragType, refs: string[]) => Promise<{ ok: boolean; added: string[] }>;
  /** 팝오버 기억(키: 팝오버 종류) */
  remember: <T>(kind: string, value: T) => void;
  recall: <T>(kind: string) => T | undefined;
}

const RuntimeCtx = createContext<ShellRuntime | null>(null);

export function ShellRuntimeProvider({ children }: { children: ReactNode }) {
  const { page } = useShell();
  const loc = useLocation();
  const taskKey = loc.pathname;
  const [sessionAdded, setSessionAdded] = useState<Set<string>>(() => new Set());
  const memory = useRef(new Map<string, unknown>());
  const pageAddedKey = JSON.stringify(page.added ?? []);

  // 작업이 바뀌거나 기능이 added 를 새로 넘기면 세션 표시는 비운다(기능 값이 원천)
  useEffect(() => { setSessionAdded(new Set()); }, [taskKey, pageAddedKey]);

  const markAdded = useCallback((refs: string[]) => {
    if (!refs.length) return;
    setSessionAdded((prev) => { const n = new Set(prev); refs.forEach((r) => n.add(r)); return n; });
  }, []);

  // 드롭 영역에서 성공하면 그 항목을 added 로
  useEffect(() => onItemDropped((p) => markAdded([p.ref])), [markAdded]);

  const hasTask = page.hasTask ?? !!page.section;
  const addedSet = useMemo(() => new Set([...(page.added ?? []), ...sessionAdded]), [page.added, sessionAdded]);
  const pageRef = useRef(page);
  pageRef.current = page;

  const value = useMemo<ShellRuntime>(() => ({
    taskKey,
    page,
    hasTask,
    canAdd: (type) => hasTask && !!page.onAdd && (page.addable ?? ADDABLE_ALL).includes(type),
    offReason: (type, where = 'item') => {
      if (!hasTask) return where === 'item' ? NO_TASK_ITEM_TIP : NO_TASK_TIP;
      if (!page.onAdd || !(page.addable ?? ADDABLE_ALL).includes(type)) return NO_HANDLER_TIP;
      return '';
    },
    canDrag: (type) => hasTask && (page.accepts ?? []).includes(type),
    isAdded: (r) => addedSet.has(r),
    markAdded,
    runAdd: async (type, refs) => {
      const fn = pageRef.current.onAdd;
      if (!fn || !refs.length) return { ok: false, added: [] };
      try {
        const res = await fn(type, refs);
        const added = res && Array.isArray(res.added) ? res.added : refs;
        markAdded(added);
        return { ok: true, added };
      } catch {
        return { ok: false, added: [] };
      }
    },
    remember: (kind, v) => { memory.current.set(`${taskKey}|${kind}`, v); },
    recall: <T,>(kind: string) => memory.current.get(`${taskKey}|${kind}`) as T | undefined,
  }), [taskKey, page, hasTask, addedSet, markAdded]);

  return <RuntimeCtx.Provider value={value}>{children}</RuntimeCtx.Provider>;
}

export function useShellRuntime(): ShellRuntime {
  const v = useContext(RuntimeCtx);
  if (!v) throw new Error('useShellRuntime 은 셸 Layout 안에서만 쓸 수 있습니다');
  return v;
}
