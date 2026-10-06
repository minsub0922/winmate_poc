/**
 * 잡 진행(jobs SSE) — 공통 `useJob` 위에 제안서 잡의 step 이벤트(`{step|key, label, status, note}`)와 진행률(`progress`, `eta_sec`)을 모은다(§6.14).
 */
import { useMemo, useRef } from 'react';
import { useJob, type JobEvent, type JobSnapshot } from '@/api/jobs';

export interface StepEvent { key: string; label?: string; status: string; note?: string }

export function useJobEvents(jobId: string | null | undefined, opts: { onDone?: (j: JobSnapshot) => void; onEvent?: (e: JobEvent) => void } = {}) {
  const r = useJob(jobId ?? null, opts);
  const steps = useMemo(() => {
    const m = new Map<string, StepEvent>();
    for (const e of r.events) {
      if (e.type !== 'step') continue;
      const d = e.data as Record<string, unknown>;
      const key = String(d.key ?? d.step ?? d.node ?? '');
      if (!key) continue;
      m.set(key, { key, label: (d.label as string) ?? m.get(key)?.label, status: String(d.status ?? 'running'), note: (d.note as string) ?? m.get(key)?.note });
    }
    return m;
  }, [r.events]);
  const last = r.events.filter((e) => e.type === 'progress').at(-1)?.data as { progress?: number; pct?: number; eta_sec?: number; message?: string } | undefined;
  const progress = last?.pct ?? last?.progress ?? r.progress ?? 0;
  const errorEv = r.events.filter((e) => e.type === 'error').at(-1)?.data as { code?: string; message?: string } | undefined;
  return {
    ...r,
    steps,
    progress,
    eta: last?.eta_sec ?? null,
    message: last?.message ?? r.job?.message ?? '',
    error: errorEv ?? r.job?.error ?? null,
    failed: r.job?.status === 'failed',
    succeeded: r.job?.status === 'succeeded',
    canceled: r.job?.status === 'canceled',
    running: !!jobId && !r.done,
  };
}

/** 같은 잡의 끝을 한 번만 처리 */
export function useOnce() {
  const seen = useRef(new Set<string>());
  return (key: string, fn: () => void) => { if (seen.current.has(key)) return; seen.current.add(key); fn(); };
}
