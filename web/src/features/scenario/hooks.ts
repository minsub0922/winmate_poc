/**
 * react-query 훅 — 시나리오 · 타임라인 · 장면 · 생성 보기 · 잡 끝 기다리기.
 * 진행 갱신: 잡 SSE(jobs) 이벤트마다 다시 읽고, SSE 가 끊겨도 폴링이 받친다.
 */
import { useEffect, useRef, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { scApi } from './api';

export const qk = {
  all: ['scenario'] as const,
  list: (p: unknown) => ['scenario', 'list', p] as const,
  sc: (id?: string | null) => ['scenario', 'sc', id] as const,
  timeline: (id?: string | null) => ['scenario', 'timeline', id] as const,
  scenes: (id?: string | null) => ['scenario', 'scenes', id] as const,
  scene: (id?: string | null) => ['scenario', 'scene', id] as const,
  versions: (id?: string | null) => ['scenario', 'scene-versions', id] as const,
  recs: (id?: string | null) => ['scenario', 'recs', id] as const,
  gen: (id?: string | null) => ['scenario', 'gen', id] as const,
  plan: (id?: string | null) => ['scenario', 'plan', id] as const,
  industries: () => ['scenario', 'industries'] as const,
  beOptions: () => ['scenario', 'be-options'] as const,
};

export function useScenario(id?: string | null, opts: { poll?: number | false } = {}) {
  return useQuery({ queryKey: qk.sc(id), queryFn: () => scApi.get(id!), enabled: !!id, staleTime: 1_000, refetchInterval: opts.poll ?? false });
}

export function useInvalidate() {
  const qc = useQueryClient();
  return {
    sc: (id?: string | null) => qc.invalidateQueries({ queryKey: qk.sc(id) }),
    timeline: (id?: string | null) => qc.invalidateQueries({ queryKey: qk.timeline(id) }),
    scenes: (id?: string | null) => qc.invalidateQueries({ queryKey: qk.scenes(id) }),
    scene: (id?: string | null) => qc.invalidateQueries({ queryKey: qk.scene(id) }),
    all: () => qc.invalidateQueries({ queryKey: qk.all }),
    qc,
  };
}

const TERMINAL = new Set(['succeeded', 'failed', 'canceled']);

/** 잡 하나가 끝날 때까지 기다린다(SSE + 1초 폴링). 결과 상태를 돌려준다.
 * 폴링 요청마다 8초 제한을 둬 걸린 요청 하나가 기다림 전체를 붙잡지 않게 하고, SSE 가 끝 상태를 알려 주면 그 값도 쓴다. */
export async function waitJob(jobId: string, opts: { timeoutMs?: number; signal?: AbortSignal; onEvent?: (type: string, data: Record<string, unknown>) => void } = {}):
  Promise<{ status: string; error?: { code?: string; message?: string } | null; result?: Record<string, unknown> | null }> {
  const until = Date.now() + (opts.timeoutMs ?? 180_000);
  let es: EventSource | null = null;
  let wake: (() => void) | null = null;
  let sseStatus: string | null = null;
  let sseError: { code?: string; message?: string } | null = null;
  try {
    es = new EventSource(`/api/jobs/v1/jobs/${jobId}/events`);
    const kick = (type: string) => (ev: MessageEvent) => {
      let data: Record<string, unknown> = {};
      try { data = JSON.parse(ev.data); } catch { /* 무시 */ }
      if ((type === 'status' || type === 'done') && typeof data.status === 'string') sseStatus = data.status;
      if (type === 'error') sseError = data as { code?: string; message?: string };
      if (opts.onEvent) { try { opts.onEvent(type, data); } catch { /* 무시 */ } }
      wake?.();
    };
    for (const t of ['status', 'progress', 'step', 'log', 'result', 'error', 'done']) es.addEventListener(t, kick(t) as EventListener);
    es.onerror = () => { /* 폴링이 받친다 */ };
  } catch { es = null; }
  const poll = async () => {
    const ctl = new AbortController();
    const t = window.setTimeout(() => ctl.abort(), 8_000);
    try {
      const r = await fetch(`/api/jobs/v1/jobs/${jobId}`, { credentials: 'same-origin', signal: ctl.signal });
      return r.ok ? await r.json() : null;
    } catch { return null; } finally { window.clearTimeout(t); }
  };
  try {
    while (Date.now() < until) {
      if (opts.signal?.aborted) return { status: 'aborted' };
      const j = await poll();
      if (j && TERMINAL.has(j.status)) return { status: j.status, error: j.error, result: j.result };
      if (!j && sseStatus && TERMINAL.has(sseStatus)) return { status: sseStatus, error: sseError };
      await new Promise<void>((res) => { const t = window.setTimeout(res, 1_000); wake = () => { window.clearTimeout(t); res(); }; });
      wake = null;
    }
    return { status: 'timeout' };
  } finally { es?.close(); }
}

/** 여러 잡의 SSE 를 구독해 이벤트마다 onEvent(400ms 묶음) — 열린 잡 수는 6개까지 */
export function useJobsPulse(jobIds: Array<string | null | undefined>, onEvent: () => void) {
  const key = jobIds.filter(Boolean).slice(0, 6).join(',');
  const cb = useRef(onEvent);
  cb.current = onEvent;
  useEffect(() => {
    if (!key) return;
    let t: number | undefined;
    const fire = () => { if (t) return; t = window.setTimeout(() => { t = undefined; try { cb.current(); } catch { /* 무시 */ } }, 400); };
    const sources = key.split(',').map((id) => {
      const es = new EventSource(`/api/jobs/v1/jobs/${id}/events`);
      for (const ev of ['status', 'progress', 'step', 'log', 'partial', 'result', 'error', 'done']) es.addEventListener(ev, fire);
      es.onerror = () => { /* 폴링이 받친다 */ };
      return es;
    });
    return () => { if (t) window.clearTimeout(t); sources.forEach((s) => s.close()); };
  }, [key]);
}

/** 입력이 멈춘 뒤 ms 뒤에 값 */
export function useDebounced<T>(value: T, ms: number): T {
  const [v, setV] = useState(value);
  useEffect(() => { const t = window.setTimeout(() => setV(value), ms); return () => window.clearTimeout(t); }, [value, ms]);
  return v;
}
