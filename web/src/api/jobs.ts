/**
 * 잡 진행 구독(jobs 서비스 SSE).
 *
 *   const { job, events, progress, done } = useJob(jobId, { onDone: () => refetch() });
 */
import { useEffect, useRef, useState } from 'react';
import { probeAuth, reportUnauthorized } from './client';

/** fetch + 401(로그인 필요)이면 셸에 알림 */
const jfetch = (url: string, init?: RequestInit) => fetch(url, { credentials: 'same-origin', ...init }).then((r) => { reportUnauthorized(r, url); return r; });

export type JobStatus = 'queued' | 'running' | 'awaiting_input' | 'succeeded' | 'failed' | 'canceled';

export interface JobEvent {
  id?: string;
  type: string;
  data: Record<string, any>;
  ts?: string;
}

export interface JobSnapshot {
  id: string;
  service: string;
  kind: string;
  status: JobStatus;
  progress: number;
  message: string;
  title?: string;
  ref?: string | null;
  result?: Record<string, any> | null;
  error?: { code: string; message: string } | null;
  input_request?: Record<string, any> | null;
  queue_position?: number | null;
}

const TERMINAL: JobStatus[] = ['succeeded', 'failed', 'canceled'];

export function useJob(jobId: string | null | undefined, opts: { onDone?: (job: JobSnapshot) => void; onEvent?: (e: JobEvent) => void } = {}) {
  const [job, setJob] = useState<JobSnapshot | null>(null);
  const [events, setEvents] = useState<JobEvent[]>([]);
  const optsRef = useRef(opts);
  optsRef.current = opts;

  useEffect(() => {
    if (!jobId) return;
    let closed = false;
    setEvents([]);
    jfetch(`/api/jobs/v1/jobs/${jobId}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((j) => { if (!closed && j) setJob(j); })
      .catch(() => undefined);
    const es = new EventSource(`/api/jobs/v1/jobs/${jobId}/events`);
    // 연결이 아주 끊기면(EventSource 는 상태 코드를 못 본다) 로그인이 끝났는지 확인한다 — 401 이면 셸이 로그인 화면으로
    es.addEventListener('error', (ev) => {
      if (!(ev instanceof MessageEvent) && es.readyState === EventSource.CLOSED && !closed) void probeAuth();
    });
    const handle = (type: string) => (ev: MessageEvent) => {
      let data: any = {};
      try { data = JSON.parse(ev.data); } catch { data = { raw: ev.data }; }
      const e: JobEvent = { id: ev.lastEventId, type, data };
      setEvents((prev) => [...prev, e]);
      optsRef.current.onEvent?.(e);
      setJob((prev) => {
        if (!prev) return prev;
        const next = { ...prev };
        if (type === 'progress') { next.progress = data.progress ?? next.progress; if (data.message) next.message = data.message; }
        if (type === 'status') { next.status = data.status ?? next.status; if (data.message) next.message = data.message; }
        if (type === 'awaiting_input') { next.status = 'awaiting_input'; next.input_request = data; }
        if (type === 'result') next.result = data;
        if (type === 'error') next.error = data as any;
        return next;
      });
      if (type === 'done') {
        es.close();
        jfetch(`/api/jobs/v1/jobs/${jobId}`)
          .then((r) => (r.ok ? r.json() : null))
          .then((j) => { if (!closed && j) { setJob(j); optsRef.current.onDone?.(j); } })
          .catch(() => undefined);
      }
    };
    for (const t of ['status', 'progress', 'step', 'log', 'partial', 'memo', 'awaiting_input', 'result', 'error', 'done']) {
      es.addEventListener(t, handle(t) as EventListener);
    }
    return () => { closed = true; es.close(); };
  }, [jobId]);

  return {
    job,
    events,
    progress: job?.progress ?? 0,
    status: job?.status,
    done: job ? TERMINAL.includes(job.status) : false,
  };
}

export async function cancelJob(jobId: string) {
  await jfetch(`/api/jobs/v1/jobs/${jobId}/cancel`, { method: 'POST' });
}

export async function answerJob(jobId: string, answer: unknown) {
  const r = await jfetch(`/api/jobs/v1/jobs/${jobId}/input`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ answer }),
  });
  if (!r.ok) throw new Error((await r.json().catch(() => ({})))?.error?.message ?? r.statusText);
}

export async function addJobMemo(jobId: string, text: string) {
  await jfetch(`/api/jobs/v1/jobs/${jobId}/memos`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text }),
  });
}
