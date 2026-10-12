/**
 * 화면 → 셸 맥락 전달(00-shell §7.5).
 *
 *   useShellPage({ section: '고객 요구사항', title: '새 요구사항', hasTask: true, accepts: ['product'],
 *     onAdd: async (type, refs) => ({ added: refs }), stepper: { steps: ['입력','심층 작성','저장'], current: 1 } });
 */
import { createContext, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { useInStepPopup } from '@/ui';
import type { ShellPageConfig } from './types';

interface Ctx {
  /** 셸이 그리는 맥락 = 페이지 맥락 + (단계 팝업이 열려 있으면) 팝업 단계의 「현재 작업에 추가」 맥락 */
  page: ShellPageConfig;
  setPage: (p: ShellPageConfig) => void;
  /** 단계 팝업(StepModal) 안 화면의 맥락 — 상단바 제목 · 스텝바는 페이지(최종본) 것을 그대로 두고 추가 맥락만 얹는다 */
  setOverlay: (p: ShellPageConfig | null) => void;
}

const ShellCtx = createContext<Ctx>({ page: {}, setPage: () => undefined, setOverlay: () => undefined });

/** 팝업 단계가 얹는 키(작업 추가 · 끌어 놓기) — 제목 · 섹션 · 스텝바 · 사이드바 그룹은 페이지 것 */
const OVERLAY_KEYS = ['hasTask', 'accepts', 'acceptsWork', 'added', 'addable', 'onAdd', 'onAttach', 'taskContext'] as const;

export function ShellProvider({ children }: { children: ReactNode }) {
  const [base, setPage] = useState<ShellPageConfig>({});
  const [overlay, setOverlay] = useState<ShellPageConfig | null>(null);
  const page = useMemo<ShellPageConfig>(() => {
    if (!overlay) return base;
    const o: Record<string, unknown> = {};
    for (const k of OVERLAY_KEYS) if (overlay[k] !== undefined) o[k] = overlay[k];
    return { ...base, ...o };
  }, [base, overlay]);
  const value = useMemo(() => ({ page, setPage, setOverlay }), [page]);
  return <ShellCtx.Provider value={value}>{children}</ShellCtx.Provider>;
}

export function useShell() {
  return useContext(ShellCtx);
}

/** 화면이 렌더될 때 셸 맥락을 설정한다(언마운트 시 비움). 핸들러는 최신 값을 쓴다(참조가 바뀌어도 다시 설정하지 않는다). */
export function useShellPage(config: ShellPageConfig) {
  const { setPage: setBase, setOverlay } = useContext(ShellCtx);
  const inPop = useInStepPopup();
  const setPage = inPop ? setOverlay : setBase;
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
  useEffect(() => () => (inPop ? setOverlay(null) : setBase({})), [inPop, setBase, setOverlay]);
}
