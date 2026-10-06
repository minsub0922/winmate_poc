/**
 * 정의서 데이터 훅 — 읽기(TanStack Query) · 자동 저장(작업본 ops 큐 → 800ms 디바운스 PATCH) · 잡 구독(SSE).
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useJob } from '@/api/jobs';
import { toast } from '@/ui';
import { ApiError, errorText, rqApi, type DraftOp, type Requirement } from './api';
import { applyLocal, coalesce, emptyRequirement } from './lib/draft';

export const rqKey = (id: string | undefined) => ['rq', id] as const;

/** 정의서 읽기. 늦게 온 옛 응답(낮은 revision)이 새 값을 덮지 않게 한다. */
export function useRequirement(id: string | undefined) {
  const qc = useQueryClient();
  return useQuery({
    queryKey: rqKey(id),
    enabled: !!id,
    staleTime: 2_000,
    queryFn: async () => {
      const r = await rqApi.get(id!);
      const cur = qc.getQueryData<Requirement>(rqKey(id));
      return cur && cur.revision > r.revision && cur.updated_at >= r.updated_at ? cur : r;
    },
  });
}

/** 잡 진행 구독 — progress · step 이벤트마다(500ms 스로틀) onTick, 끝나면 onDone. */
export function useJobTicker(jobId: string | null | undefined, onTick: () => void, onDone?: () => void) {
  const last = useRef(0);
  const timer = useRef<number | null>(null);
  const tick = useRef(onTick);
  tick.current = onTick;
  const fire = useCallback(() => {
    const now = Date.now();
    const wait = 500 - (now - last.current);
    if (wait <= 0) {
      last.current = now;
      tick.current();
    } else if (timer.current === null) {
      timer.current = window.setTimeout(() => { timer.current = null; last.current = Date.now(); tick.current(); }, wait);
    }
  }, []);
  useEffect(() => () => { if (timer.current) window.clearTimeout(timer.current); }, []);
  return useJob(jobId, {
    onEvent: (e) => { if (e.type === 'progress' || e.type === 'step') fire(); },
    onDone: () => { tick.current(); onDone?.(); },
  });
}

interface EditorOptions {
  /** 처음 만들 때 붙일 쿼리(`?return=storyboard`) */
  returnQuery?: string;
}

/**
 * 폼 편집기. 화면은 `view`(서버 값 + 보내는 중 · 보낼 ops)를 그리고, 바꿀 때 `edit(op)` 를 부른다.
 * 자원이 없으면 첫 편집에서 만들고(POST) 주소를 `/requirements/{id}/form` 으로 바꾼다.
 */
export function useDraftEditor(routeId: string | undefined, opts: EditorOptions = {}) {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [id, setId] = useState<string | undefined>(routeId);
  const idRef = useRef(id);
  const [queue, setQueue] = useState<DraftOp[]>([]);
  const [inflight, setInflight] = useState<DraftOp[]>([]);
  const queueRef = useRef<DraftOp[]>([]);
  const inflightRef = useRef<DraftOp[]>([]);
  const creating = useRef<Promise<string> | null>(null);
  const timer = useRef<number | null>(null);
  const failures = useRef(0);
  const waiters = useRef<Array<() => void>>([]);

  // 다른 정의서로 옮겨 가면(사이드바) 새로 시작한다. 방금 만든 정의서로 주소만 바뀐 경우는 그대로.
  useEffect(() => {
    if (routeId && routeId !== idRef.current) {
      idRef.current = routeId;
      setId(routeId);
      queueRef.current = [];
      inflightRef.current = [];
      setQueue([]);
      setInflight([]);
    }
    if (!routeId && idRef.current && !creating.current) {
      idRef.current = undefined;
      setId(undefined);
      queueRef.current = [];
      setQueue([]);
    }
  }, [routeId]);

  const query = useRequirement(id);
  const server = query.data;
  const view = useMemo(() => applyLocal(applyLocal(server ?? emptyRequirement(), inflight), queue), [server, inflight, queue]);

  const settle = () => {
    if (!queueRef.current.length && !inflightRef.current.length) {
      const ws = waiters.current;
      waiters.current = [];
      ws.forEach((w) => w());
    }
  };

  const flush = useCallback(async (): Promise<void> => {
    if (timer.current) { window.clearTimeout(timer.current); timer.current = null; }
    const rid = idRef.current;
    if (!rid || inflightRef.current.length || !queueRef.current.length) { settle(); return; }
    const ops = queueRef.current;
    queueRef.current = [];
    inflightRef.current = ops;
    setQueue([]);
    setInflight(ops);
    const base = qc.getQueryData<Requirement>(rqKey(rid))?.revision ?? null;
    try {
      const res = await rqApi.patch(rid, base, ops);
      failures.current = 0;
      qc.setQueryData(rqKey(rid), res);
      inflightRef.current = [];
      setInflight([]);
    } catch (e) {
      inflightRef.current = [];
      setInflight([]);
      queueRef.current = [...ops, ...queueRef.current];
      setQueue(queueRef.current);
      if (e instanceof ApiError && e.code === 'REVISION_CONFLICT' && e.details?.current) {
        qc.setQueryData(rqKey(rid), e.details.current as Requirement);
        failures.current += 1;
        if (failures.current <= 3) { void flush(); return; }
      } else if (e instanceof ApiError && e.status === 422) {
        // 받아들일 수 없는 op(예: 가중치 규칙) — 버리고 서버 값으로
        queueRef.current = queueRef.current.filter((o) => !ops.includes(o));
        setQueue(queueRef.current);
        toast(errorText(e));
        void qc.invalidateQueries({ queryKey: rqKey(rid) });
        settle();
        return;
      } else {
        failures.current += 1;
        if (failures.current <= 3) {
          timer.current = window.setTimeout(() => { void flush(); }, 1000 * failures.current);
          return;
        }
        toast('자동 저장에 실패했어요. 연결을 확인해 주세요.', { action: { label: '다시 시도', onClick: () => { failures.current = 0; void flush(); } } });
      }
    }
    if (queueRef.current.length) {
      timer.current = window.setTimeout(() => { void flush(); }, 300);
    }
    settle();
  }, [qc]);

  const ensureId = useCallback(async (): Promise<string> => {
    if (idRef.current) return idRef.current;
    if (!creating.current) {
      creating.current = rqApi.create().then((r) => {
        idRef.current = r.id;
        qc.setQueryData(rqKey(r.id), r);
        setId(r.id);
        navigate(`/requirements/${r.id}/form${opts.returnQuery ?? ''}`, { replace: true });
        return r.id;
      }).finally(() => { creating.current = null; });
    }
    return creating.current;
  }, [navigate, opts.returnQuery, qc]);

  const edit = useCallback((op: DraftOp | DraftOp[]) => {
    for (const o of Array.isArray(op) ? op : [op]) queueRef.current = coalesce(queueRef.current, o);
    setQueue(queueRef.current);
    void ensureId().then(() => {
      if (timer.current) window.clearTimeout(timer.current);
      timer.current = window.setTimeout(() => { void flush(); }, 800);
    }).catch((e) => toast(errorText(e)));
  }, [ensureId, flush]);

  /** 보낼 것을 모두 보내고 끝날 때까지 기다린다(저장 · 화면 이동 전에). */
  const flushNow = useCallback(async () => {
    if (!queueRef.current.length && !inflightRef.current.length) return;
    const done = new Promise<void>((res) => waiters.current.push(res));
    void flush();
    await Promise.race([done, new Promise((res) => window.setTimeout(res, 8000))]);
  }, [flush]);

  // 떠날 때 남은 것을 보낸다
  useEffect(() => () => { if (queueRef.current.length) void flush(); }, [flush]);

  const pending = queue.length + inflight.length > 0;
  return { id, ensureId, query, server, view, edit, flushNow, pending };
}

/** 저장 뒤 캐시 갱신(정의서 · 목록) — 저장 응답에 작업본이 있으면 바로 넣는다. */
export function useAfterSave() {
  const qc = useQueryClient();
  return useCallback(async (id: string, res?: { requirement?: Requirement | null }) => {
    if (res?.requirement) qc.setQueryData(rqKey(id), res.requirement);
    else await qc.invalidateQueries({ queryKey: rqKey(id) });
    void qc.invalidateQueries({ queryKey: ['rq-list'] });
    void qc.invalidateQueries({ queryKey: ['rq-questions', id] });
  }, [qc]);
}
