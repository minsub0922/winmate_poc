/**
 * RQ1 편집 상태 — 화면 폼(FForm)이 원본이고 600ms 뒤 폼 전체를 PUT 한다(expected_version · 409 면 새로 읽고 한 번 더).
 * - 아직 문서가 없으면(`/requirements/new`) 첫 입력 때 만들고(POST) onCreated 로 주소를 바꾼다(빈 초안을 만들지 않는다).
 * - PUT 응답으로는 폼 글자를 덮어쓰지 않는다(입력 중 공백 · 빈 줄 보호). 서버가 폼을 바꾸는 호출(심층 질의 답 · 파일 채우기)만 폼을 바꾼다.
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { ApiError } from '@/api/client';
import { toast } from '@/ui';
import { rfApi, rfKey, type RFDoc } from './api';
import { bodyOf, emptyForm, formOf, isEmpty, type FForm } from './form';

export const AI_DOWN = '지금은 AI를 쓸 수 없어요. 직접 입력은 계속할 수 있어요.';

export function errText(e: unknown): string {
  if (e instanceof ApiError) {
    if (e.code === 'LLM_UNAVAILABLE' || e.code === 'POLICY_CONFIDENTIAL' || e.code === 'LLM_TIMEOUT') return AI_DOWN;
    return e.message || '문제가 생겼어요. 다시 시도해 주세요.';
  }
  return '연결이 끊겼어요. 다시 시도해 주세요.';
}

export function useRfEditor(initial: RFDoc | null, onCreated: (d: RFDoc) => void) {
  const qc = useQueryClient();
  const [doc, setDoc] = useState<RFDoc | null>(initial);
  const [form, setFormState] = useState<FForm>(() => (initial ? formOf(initial) : emptyForm()));
  const [saving, setSaving] = useState(false);
  const docRef = useRef(doc);
  const formRef = useRef(form);
  const rev = useRef(0);
  const savedRev = useRef(0);
  const timer = useRef<number | undefined>(undefined);
  const inflight = useRef<Promise<void> | null>(null);
  const creating = useRef<Promise<RFDoc> | null>(null);
  const createdRef = useRef(onCreated);
  createdRef.current = onCreated;

  /** 서버 문서 반영. replaceForm 이면 폼도 서버 값으로(심층 질의 답 · 파일 채우기 — 서버가 폼을 바꾼 경우) */
  const applyDoc = useCallback((d: RFDoc, replaceForm = false) => {
    docRef.current = d;
    setDoc(d);
    qc.setQueryData(rfKey(d.id), d);
    if (replaceForm) {
      window.clearTimeout(timer.current);
      const f = formOf(d);
      formRef.current = f;
      setFormState(f);
      savedRev.current = rev.current;
    }
  }, [qc]);

  const create = useCallback(async (f: FForm): Promise<RFDoc> => {
    if (docRef.current) return docRef.current;
    if (!creating.current) {
      const b = bodyOf(f);
      creating.current = rfApi.create({ title: b.title, customer: b.customer, target: b.target, note: b.note, keymen: b.keymen })
        .then((d) => { applyDoc(d); createdRef.current(d); return d; })
        .finally(() => { creating.current = null; });
    }
    return creating.current;
  }, [applyDoc]);

  const saveOnce = useCallback(async () => {
    const r = rev.current;
    const f = formRef.current;
    const d = docRef.current;
    if (!d) {
      if (isEmpty(f)) { savedRev.current = r; return; }
      await create(f);
      // 만든 뒤 들어온 입력은 다음 PUT 으로
      if (rev.current === r) savedRev.current = r;
      return;
    }
    if (d.fill_job) return;                      // 파일로 채우는 중 — 끝나면 서버 값으로 바뀐다
    try {
      applyDoc(await rfApi.put(d.id, bodyOf(f, d.version)));
    } catch (e) {
      if (!(e instanceof ApiError && e.code === 'VERSION_CONFLICT')) throw e;
      const fresh = await rfApi.get(d.id);         // 다른 탭 · 잡이 먼저 고침 → 새 버전 위에 지금 폼을 다시 쓴다
      applyDoc(fresh);
      applyDoc(await rfApi.put(d.id, bodyOf(f, fresh.version)));
    }
    savedRev.current = Math.max(savedRev.current, r);
  }, [applyDoc, create]);

  /** 남은 입력을 지금 저장 — 다 저장됐으면 true(그 사이 새 입력이 오면 몇 번 더) */
  const flush = useCallback(async (): Promise<boolean> => {
    window.clearTimeout(timer.current);
    for (let i = 0; i < 4; i++) {
      while (inflight.current) await inflight.current;
      if (savedRev.current >= rev.current) return true;
      if (docRef.current?.fill_job) return false;
      let ok = true;
      const run = (async () => {
        setSaving(true);
        try { await saveOnce(); } catch (e) {
          ok = false;
          if (!(e instanceof ApiError && e.code === 'FILLING')) toast(`자동 저장에 실패했어요 · ${errText(e)}`);
        } finally { setSaving(false); }
      })();
      inflight.current = run;
      await run;
      inflight.current = null;
      if (!ok) return false;
    }
    return savedRev.current >= rev.current;
  }, [saveOnce]);

  const flushRef = useRef(flush);
  flushRef.current = flush;

  const edit = useCallback((fn: (f: FForm) => FForm) => {
    const next = fn(formRef.current);
    if (next === formRef.current) return;
    formRef.current = next;
    setFormState(next);
    rev.current += 1;
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => { void flushRef.current(); }, 600);
  }, []);

  /** 문서가 꼭 있어야 하는 호출(파일 · AI · 저장) 전에 — 없으면 지금 폼으로 만든다 */
  const ensureDoc = useCallback(async (): Promise<RFDoc> => docRef.current ?? create(formRef.current), [create]);

  // 화면을 떠날 때 남은 입력 저장
  useEffect(() => () => { void flushRef.current(); }, []);

  return { doc, form, saving, edit, flush, applyDoc, ensureDoc, docRef, rev };
}
