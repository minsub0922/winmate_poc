/**
 * 화면 → 셸 맥락 전달(00-shell §7.5).
 *
 *   useShellPage({ section: '고객 요구사항', title: '새 요구사항', hasTask: true, accepts: ['product'],
 *     onAdd: async (type, refs) => ({ added: refs }), stepper: { steps: ['입력','심층 작성','저장'], current: 1 } });
 */
import { createContext, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import type { ShellPageConfig } from './types';

interface Ctx {
  page: ShellPageConfig;
  setPage: (p: ShellPageConfig) => void;
}

const ShellCtx = createContext<Ctx>({ page: {}, setPage: () => undefined });

export function ShellProvider({ children }: { children: ReactNode }) {
  const [page, setPage] = useState<ShellPageConfig>({});
  const value = useMemo(() => ({ page, setPage }), [page]);
  return <ShellCtx.Provider value={value}>{children}</ShellCtx.Provider>;
}

export function useShell() {
  return useContext(ShellCtx);
}

/** 화면이 렌더될 때 셸 맥락을 설정한다(언마운트 시 비움). 핸들러는 최신 값을 쓴다(참조가 바뀌어도 다시 설정하지 않는다). */
export function useShellPage(config: ShellPageConfig) {
  const { setPage } = useContext(ShellCtx);
  const ref = useRef(config);
  ref.current = config;
  const st = config.stepper;
  const key = JSON.stringify({
    s: config.section, t: config.title, h: config.hasTask, a: config.accepts, aw: config.acceptsWork, d: config.added, ad: config.addable,
    oa: !!config.onAdd, ot: !!config.onAttach, g: config.sidebarGroup, tc: config.taskContext,
    st: st && {
      steps: st.steps, c: st.current, cp: st.complete, af: st.autoFrom, auto: st.auto, os: !!st.onStep, oo: st.oneClickOpen,
      pc: st.planConfirmed, pr: st.planRows, ps: st.planSummary,
      oc: !!st.oneClick, ocl: st.oneClick?.label, ocr: st.oneClick?.running, ocd: st.oneClick?.disabled,
    },
  });
  // stepper.right 는 노드라 키에 넣지 않는다(다른 값이 바뀔 때 함께 갱신된다)
  useEffect(() => {
    const c = ref.current;
    setPage({
      ...c,
      onAdd: c.onAdd ? (type, refs) => ref.current.onAdd!(type, refs) : undefined,
      onAttach: c.onAttach ? (imgs) => ref.current.onAttach!(imgs) : undefined,
      stepper: c.stepper && {
        ...c.stepper,
        onStep: c.stepper.onStep ? (i) => ref.current.stepper?.onStep?.(i) : undefined,
        oneClick: c.stepper.oneClick && { ...c.stepper.oneClick, onRun: (o) => ref.current.stepper?.oneClick?.onRun(o) },
      },
    });
  }, [key, setPage]);
  useEffect(() => () => setPage({}), [setPage]);
}
