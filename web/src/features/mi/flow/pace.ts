/**
 * AI 진행 단계 보여 주기(보드 MI2_Loading) — 서버 `progress.steps` 를 그대로 쓰되, 한 단계가 끝난 것을 보여 주는 간격을 최소 STEP_MS 로 둔다.
 * mock · 빠른 모델이면 분석이 0.3초에 끝나 단계가 보이지 않으므로(보드는 단계마다 약 0.8초) 화면에서만 천천히 넘긴다. 값 · 문구는 서버 것 그대로.
 * 이 화면에서 AI 가 일하는 것을 보지 않았으면(이미 끝난 문서를 연 경우) 기다리지 않는다.
 */
import { useEffect, useRef, useState } from 'react';
import type { MFStep } from './api';

export const STEP_MS = 800;

export function usePacedSteps(steps: MFStep[], busy: boolean, runKey: string) {
  const finished = steps.filter((s) => s.state === 'done' || s.state === 'error').length;
  const saw = useRef<string | null>(busy ? runKey : null);
  if (busy) saw.current = runKey;
  const watching = saw.current === runKey;
  const [shown, setShown] = useState(watching ? 0 : finished);
  const [key, setKey] = useState(runKey);
  if (key !== runKey) { setKey(runKey); setShown(busy ? 0 : finished); }
  useEffect(() => {
    if (!watching || shown >= finished) return;
    const t = setTimeout(() => setShown((n) => n + 1), STEP_MS);
    return () => clearTimeout(t);
  }, [watching, shown, finished]);
  const view: MFStep[] = steps.map((s, i) => (i < shown ? s : i === shown && (busy || shown < finished) ? { ...s, state: 'run', note: '' } : { ...s, state: 'wait', note: '' }));
  return { view, settled: !busy && (!watching || shown >= finished) };
}
