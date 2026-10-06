/** MI 화면 훅 — MI1 자동 저장(첫 입력 800ms 뒤 작업 생성 · 이후 800ms 디바운스 PATCH) · 잡 구독 · 작업 상태 따라 이동. */
import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { toast } from '@/ui';
import { useJob, type JobEvent, type JobSnapshot } from '@/api/jobs';
import { createAnalysis, errText, patchAnalysis, qk, type Analysis } from './api';

export interface InputDraft { customer_name: string; requirements_text: string }

/**
 * MI1 편집기. 작업이 없으면 첫 의미 있는 입력 800ms 뒤 `POST /v1/analyses` 로 만들고 주소를 `/mi/:id/input` 으로 바꾼다(AC-MI-86).
 * 이후 바꾼 칸만 800ms 디바운스 PATCH. `flush()` 는 남은 것을 보내고 작업 id 를 돌려준다.
 */
export function useInputEditor(routeId: string | undefined, server: Analysis | undefined, extra?: () => Record<string, unknown>) {
  const qc = useQueryClient();
  const nav = useNavigate();
  const [id, setId] = useState<string | undefined>(routeId);
  const idRef = useRef(id);
  const [draft, setDraft] = useState<InputDraft>({ customer_name: '', requirements_text: '' });
  const draftRef = useRef(draft);
  const dirty = useRef<Partial<InputDraft>>({});
  const timer = useRef<number | null>(null);
  const creating = useRef<Promise<string> | null>(null);
  const loadedFor = useRef<string | undefined>(undefined);
  const [saving, setSaving] = useState(false);
  const extraRef = useRef(extra);
  extraRef.current = extra;

  // 다른 작업으로 옮겨 가면 새로 시작(방금 만든 작업으로 주소만 바뀐 경우는 그대로)
  useEffect(() => {
    if (routeId && routeId !== idRef.current) {
      idRef.current = routeId;
      setId(routeId);
      dirty.current = {};
      loadedFor.current = undefined;
    }
    if (!routeId && idRef.current && !creating.current) {
      idRef.current = undefined;
      setId(undefined);
      dirty.current = {};
      loadedFor.current = undefined;
      draftRef.current = { customer_name: '', requirements_text: '' };
      setDraft(draftRef.current);
    }
  }, [routeId]);

  // 서버 값 → 입력칸(처음 한 번, 사용자가 고치는 중인 칸은 덮지 않는다)
  useEffect(() => {
    if (!server || loadedFor.current === server.id) return;
    loadedFor.current = server.id;
    const next = {
      customer_name: dirty.current.customer_name ?? server.customer_name ?? '',
      requirements_text: dirty.current.requirements_text ?? server.requirements_text ?? '',
    };
    draftRef.current = next;
    setDraft(next);
  }, [server]);

  const ensureId = useCallback(async (): Promise<string> => {
    if (idRef.current) return idRef.current;
    if (!creating.current) {
      const d = draftRef.current;
      dirty.current = {};
      creating.current = createAnalysis({ customer_name: d.customer_name.trim() || null, requirements_text: d.requirements_text || null, ...(extraRef.current?.() ?? {}) })
        .then((a) => {
          idRef.current = a.id;
          loadedFor.current = a.id;
          qc.setQueryData([...qk.analysis(a.id), null], a);
          setId(a.id);
          nav(`/mi/${a.id}/input`, { replace: true });
          void qc.invalidateQueries({ queryKey: ['mi', 'list'] });
          return a.id;
        })
        .finally(() => { creating.current = null; });
    }
    return creating.current;
  }, [nav, qc]);

  const flush = useCallback(async (): Promise<string | null> => {
    if (timer.current) { window.clearTimeout(timer.current); timer.current = null; }
    const d = draftRef.current;
    const empty = !d.customer_name.trim() && !d.requirements_text.trim();
    if (!idRef.current) {
      if (empty) return null;
      setSaving(true);
      try { return await ensureId(); } catch (e) { toast(errText(e)); return null; } finally { setSaving(false); }
    }
    const aid = idRef.current;
    const body = dirty.current;
    if (!Object.keys(body).length) return aid;
    dirty.current = {};
    setSaving(true);
    try {
      const a = await patchAnalysis(aid, body);
      qc.setQueryData([...qk.analysis(aid), null], a);
      return aid;
    } catch (e) {
      dirty.current = { ...body, ...dirty.current };
      toast(errText(e));
      return aid;
    } finally {
      setSaving(false);
    }
  }, [ensureId, qc]);

  const edit = useCallback((field: keyof InputDraft, value: string) => {
    draftRef.current = { ...draftRef.current, [field]: value };
    setDraft(draftRef.current);
    if (idRef.current || creating.current) dirty.current = { ...dirty.current, [field]: value };
    if (timer.current) window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => { void flush(); }, 800);
  }, [flush]);

  /** 서버가 바꾼 값(가져오기 등)으로 입력칸을 바꾼다 — 보낼 것으로 표시하지 않는다 */
  const replace = useCallback((a: Analysis) => {
    draftRef.current = { customer_name: a.customer_name ?? '', requirements_text: a.requirements_text ?? '' };
    dirty.current = {};
    setDraft(draftRef.current);
  }, []);

  // 떠날 때 남은 것을 보낸다
  useEffect(() => () => {
    if (timer.current) window.clearTimeout(timer.current);
    if (idRef.current && Object.keys(dirty.current).length) void patchAnalysis(idRef.current, dirty.current).catch(() => undefined);
  }, []);

  return { id, draft, edit, flush, ensureId, saving, replace };
}

/** 잡 구독(SSE) — 이벤트마다 onEvent, 끝나면 onDone. jobId 가 없으면 아무것도 안 한다. */
export function useJobWatch(jobId: string | null | undefined, opts: { onEvent?: (e: JobEvent) => void; onDone?: (j: JobSnapshot) => void } = {}) {
  return useJob(jobId ?? null, opts);
}

/** 화면이 보여야 할 곳과 다르면 그리로 보낸다(작업 상태 · last_screen) — 진행 중이면 MI3G 등 */
export function useLastScreen(aid: string | undefined, screen: string) {
  const sent = useRef<string | null>(null);
  useEffect(() => {
    if (!aid || sent.current === `${aid}:${screen}`) return;
    sent.current = `${aid}:${screen}`;
    void patchAnalysis(aid, { last_screen: screen }).catch(() => undefined);
  }, [aid, screen]);
}
