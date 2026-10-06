/** 경쟁사 분석 화면 훅 — 넣기 자동 저장(800ms) · 읽기(600ms) · 잡 구독 · 셸 맥락. */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { useShellPage } from '@/shell/ShellContext';
import type { DragType, StepperConfig } from '@/shell/types';
import { addRefs, createAnalysis, errText, parse, patchAnalysis, qk, STEPS, type Analysis, type ParseOut } from './api';

export type InputMode = 'free' | 'requirements';
export interface Draft { input_mode: InputMode; text: string; extra_text: string; file_ids: string[]; requirements_id: string | null }
const EMPTY: Draft = { input_mode: 'free', text: '', extra_text: '', file_ids: [], requirements_id: null };

export function useDebounced<T>(value: T, ms: number): T {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = window.setTimeout(() => setV(value), ms);
    return () => window.clearTimeout(t);
  }, [value, ms]);
  return v;
}

/**
 * CA1 · CA1R 편집기. 작업이 없으면 첫 의미 있는 입력 800ms 뒤 `POST /v1/analyses`(draft)로 만들고 주소를 `/competitor/:id/input` 으로 바꾼다.
 * 이후 바꾼 칸만 800ms 디바운스 PATCH. `flush()` 는 남은 것을 보내고 작업 id 를 돌려준다.
 */
export function useInputEditor(routeId: string | undefined, server: Analysis | undefined, initialMode: InputMode) {
  const qc = useQueryClient();
  const nav = useNavigate();
  const idRef = useRef<string | undefined>(routeId);
  const [id, setId] = useState(routeId);
  const [draft, setDraftState] = useState<Draft>({ ...EMPTY, input_mode: initialMode });
  const draftRef = useRef(draft);
  const dirty = useRef<Partial<Draft>>({});
  const timer = useRef<number | null>(null);
  const creating = useRef<Promise<string> | null>(null);
  const loadedFor = useRef<string | undefined>(undefined);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    if (routeId && routeId !== idRef.current) {
      idRef.current = routeId;
      setId(routeId);
      dirty.current = {};
      loadedFor.current = undefined;
    }
  }, [routeId]);

  // 서버 값 → 입력칸(처음 한 번, 고치는 중인 칸은 덮지 않는다)
  useEffect(() => {
    if (!server || loadedFor.current === server.id) return;
    loadedFor.current = server.id;
    const mode: InputMode = server.input_mode === 'requirements' ? 'requirements' : 'free';
    const next: Draft = {
      input_mode: (dirty.current.input_mode as InputMode | undefined) ?? (server.requirements_id || server.input_mode === 'requirements' ? mode : draftRef.current.input_mode),
      text: dirty.current.text ?? server.text ?? '',
      extra_text: dirty.current.extra_text ?? server.extra_text ?? '',
      file_ids: dirty.current.file_ids ?? server.file_ids ?? [],
      requirements_id: dirty.current.requirements_id ?? server.requirements_id ?? null,
    };
    draftRef.current = next;
    setDraftState(next);
  }, [server]);

  const ensureId = useCallback(async (): Promise<string> => {
    if (idRef.current) return idRef.current;
    if (!creating.current) {
      const d = draftRef.current;
      dirty.current = {};
      creating.current = createAnalysis({
        input_mode: d.input_mode, text: d.input_mode === 'free' ? d.text : '', file_ids: d.input_mode === 'free' ? d.file_ids : [],
        requirements_id: d.input_mode === 'requirements' ? d.requirements_id : null, extra_text: d.input_mode === 'requirements' ? d.extra_text : '',
      }).then((a) => {
        idRef.current = a.id;
        loadedFor.current = a.id;
        qc.setQueryData(qk.analysis(a.id), a);
        setId(a.id);
        nav(`/competitor/${a.id}/input${d.input_mode === 'requirements' ? '?input=requirements' : ''}`, { replace: true });
        void qc.invalidateQueries({ queryKey: ['ca', 'list'] });
        return a.id;
      }).finally(() => { creating.current = null; });
    }
    return creating.current;
  }, [nav, qc]);

  const flush = useCallback(async (): Promise<string | null> => {
    if (timer.current) { window.clearTimeout(timer.current); timer.current = null; }
    setSaving(true);
    try {
      const had = !!idRef.current;
      const aid = await ensureId();
      const ch = dirty.current;
      dirty.current = {};
      if (had && Object.keys(ch).length) {
        const a = await patchAnalysis(aid, ch);
        qc.setQueryData(qk.analysis(aid), a);
      }
      setSaveError(null);
      return aid;
    } catch (e) {
      setSaveError(errText(e, '저장하지 못했어요'));
      return null;
    } finally {
      setSaving(false);
    }
  }, [ensureId, qc]);

  /** 칸 바꾸기. save=false 면 화면만(기본 선택 등 사용자가 하지 않은 변화) */
  const update = useCallback((patch: Partial<Draft>, opts: { save?: boolean } = {}) => {
    const next = { ...draftRef.current, ...patch };
    draftRef.current = next;
    setDraftState(next);
    if (opts.save === false) return;
    dirty.current = { ...dirty.current, ...patch };
    const meaningful = next.input_mode === 'free' ? !!(next.text.trim() || next.file_ids.length) : !!next.requirements_id;
    if (!idRef.current && !meaningful) return;
    if (timer.current) window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => { timer.current = null; void flush(); }, 800);
  }, [flush]);

  useEffect(() => () => { if (timer.current) window.clearTimeout(timer.current); }, []);

  const current = useCallback(() => draftRef.current, []);
  return { id, draft, update, flush, saving, saveError, current };
}

/** `POST /v1/parse` — 600ms 디바운스 · 앞 요청 취소. key 가 null 이면 읽지 않는다. */
export function useParse(input: { text?: string; file_ids?: string[]; requirements_id?: string | null; extra_text?: string } | null) {
  const key = input ? JSON.stringify(input) : null;
  const debounced = useDebounced(key, 600);
  const [data, setData] = useState<ParseOut | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    if (!debounced) { setLoading(false); return; }
    const ctl = new AbortController();
    setLoading(true);
    parse(JSON.parse(debounced), ctl.signal)
      .then((d) => { setData(d); setError(null); })
      .catch((e) => { if (!ctl.signal.aborted) setError(errText(e, '읽지 못했어요')); })
      .finally(() => { if (!ctl.signal.aborted) setLoading(false); });
    return () => ctl.abort();
  }, [debounced]);
  const reset = useCallback(() => setData(null), []);
  return { data, loading: loading || (key !== debounced && !!key), error, reset };
}

/** 셸 맥락(§4.0) — 경쟁사 분석 화면 공통. 작업이 있으면 `현재 작업에 추가`(제품 · 솔루션 · 사례 → POST additions). */
export function useCaShell(opts: { aid?: string; title?: string | null; current: number; complete?: boolean; list?: boolean; added?: string[] | null }) {
  const qc = useQueryClient();
  const stepper: StepperConfig | undefined = opts.list ? undefined : { steps: STEPS, current: opts.current, complete: !!opts.complete };
  const aid = opts.aid;
  const onAdd = useMemo(() => (aid ? async (type: DragType, refs: string[]) => {
    if (type !== 'product' && type !== 'solution' && type !== 'case') return { added: [] };
    const added = await addRefs(aid, type, refs);
    void qc.invalidateQueries({ queryKey: qk.analysis(aid) });
    return { added };
  } : undefined), [aid, qc]);
  useShellPage({
    section: '경쟁사 분석',
    title: opts.list ? '작업 목록' : (opts.title || '새 분석'),
    hasTask: !opts.list,
    accepts: [],
    added: opts.added ?? [],
    stepper,
    sidebarGroup: 'competitor',
    ...(onAdd ? { onAdd, addable: ['product', 'solution', 'case'] as DragType[] } : {}),
  });
}
