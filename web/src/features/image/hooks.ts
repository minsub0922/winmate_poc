/**
 * react-query 훅 — 작업 · run(SSE + 폴링) · 시안 · 능력.
 * 진행 갱신(§4.1 · §4.6): 진행 중 run 마다 jobs SSE 를 구독하고 이벤트가 오면 다시 읽는다. SSE 가 끊겨도 폴링이 받친다.
 */
import { useEffect, useMemo, useRef } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useJob } from '@/api/jobs';
import { img, type RunDetail } from './api';

export const qk = {
  work: (id?: string | null) => ['image', 'work', id] as const,
  works: (q: string) => ['image', 'works', q] as const,
  gallery: (p: unknown) => ['image', 'gallery', p] as const,
  requests: () => ['image', 'requests'] as const,
  run: (id?: string | null) => ['image', 'run', id] as const,
  runs: (workId?: string | null) => ['image', 'runs', workId] as const,
  image: (id?: string | null) => ['image', 'image', id] as const,
  regions: (id?: string | null) => ['image', 'regions', id] as const,
  photos: (id?: string | null) => ['image', 'photos', id] as const,
  queue: () => ['image', 'queue'] as const,
  caps: () => ['image', 'caps'] as const,
};

const ACTIVE = new Set(['queued', 'running', 'awaiting_input']);
export const isActive = (s?: string | null) => !!s && ACTIVE.has(s);

export function useWork(id?: string | null) {
  return useQuery({ queryKey: qk.work(id), queryFn: () => img.work(id!), enabled: !!id, staleTime: 2_000 });
}

export function useCaps() {
  return useQuery({ queryKey: qk.caps(), queryFn: img.capabilities, staleTime: 60_000, retry: 0 });
}

export function useImage(id?: string | null, opts: { poll?: boolean } = {}) {
  return useQuery({
    queryKey: qk.image(id), queryFn: () => img.image(id!), enabled: !!id, staleTime: 2_000,
    refetchInterval: opts.poll ? 2_500 : false,
  });
}

/** 여러 잡의 SSE 를 구독해 이벤트마다 onEvent(던져도 무시) — 열린 잡 수는 6개까지 */
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
      for (const ev of ['status', 'progress', 'step', 'partial', 'awaiting_input', 'result', 'error', 'done']) es.addEventListener(ev, fire);
      es.onerror = () => { /* 끊기면 폴링이 받친다 */ };
      return es;
    });
    return () => { if (t) window.clearTimeout(t); sources.forEach((s) => s.close()); };
  }, [key]);
}

/**
 * run 상세 — 진행 중이면 SSE 이벤트마다 + 2초마다(추정 진행률이 움직이도록) 다시 읽는다.
 * 끝나면 작업 · 시안 목록도 새로 읽는다.
 */
export function useLiveRun(runId?: string | null) {
  const qc = useQueryClient();
  const q = useQuery({
    queryKey: qk.run(runId), queryFn: () => img.run(runId!), enabled: !!runId, staleTime: 0,
    refetchInterval: (query) => (isActive((query.state.data as RunDetail | undefined)?.status) ? 2_000 : false),
  });
  const run = q.data;
  const prev = useRef<string | undefined>(undefined);
  useJob(isActive(run?.status) ? run?.job_id : null, { onEvent: () => { void qc.invalidateQueries({ queryKey: qk.run(runId) }); } });
  useEffect(() => {
    if (!run) return;
    if (prev.current && prev.current !== run.status) {
      void qc.invalidateQueries({ queryKey: qk.work(run.work_id) });
      void qc.invalidateQueries({ queryKey: ['image', 'gallery'] });
      void qc.invalidateQueries({ queryKey: qk.queue() });
    }
    prev.current = run.status;
  }, [run, qc]);
  return q;
}

export function useQueue(enabled: boolean) {
  return useQuery({ queryKey: qk.queue(), queryFn: img.queue, enabled, refetchInterval: enabled ? 5_000 : false });
}

/** 작업의 최근 run 들 */
export function useWorkRuns(workId?: string | null, kind?: string) {
  return useQuery({ queryKey: [...qk.runs(workId), kind ?? ''], queryFn: () => img.runs(workId!, { kind }), enabled: !!workId, staleTime: 2_000 });
}

/** 무효화 도우미 */
export function useInvalidate() {
  const qc = useQueryClient();
  return useMemo(() => ({
    work: (id?: string | null) => qc.invalidateQueries({ queryKey: qk.work(id) }),
    image: (id?: string | null) => qc.invalidateQueries({ queryKey: qk.image(id) }),
    regions: (id?: string | null) => qc.invalidateQueries({ queryKey: qk.regions(id) }),
    run: (id?: string | null) => qc.invalidateQueries({ queryKey: qk.run(id) }),
    gallery: () => qc.invalidateQueries({ queryKey: ['image', 'gallery'] }),
    works: () => qc.invalidateQueries({ queryKey: ['image', 'works'] }),
    all: () => qc.invalidateQueries({ queryKey: ['image'] }),
    setWork: (w: { id: string }) => qc.setQueryData(qk.work(w.id), w),
  }), [qc]);
}
