/**
 * RQ1 · RQ1_AI — 고객 요구사항 입력(보드 webapp1 RQ1.dc.html 인라인 px 그대로 · rqflow.css).
 * 왼쪽 400px(AI 질의가 열리면 300px) 폼 | 오른쪽 1fr 키맨별 요구사항. AI 심층 질의는 오른쪽 380px 패널(눌러야 열림).
 */
import { useCallback, useEffect, useLayoutEffect, useRef, useState, type ChangeEvent, type DragEvent } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { uploadFile } from '@/api/client';
import { useJob } from '@/api/jobs';
import { FlowBar, useFlowInvalidate } from '@/shell';
import { FlowFooter, FlowScreen, LinkedStoryboardBar, cx, toast } from '@/ui';
import { rfApi, rfListKey, type By, type RFDoc, type RFStageOut } from './api';
import { DeepPanel } from './DeepPanel';
import { addKeyman, newId, removeKeyman, setWeight, weightSum, type FForm, type FKeyman, type FReq } from './form';
import { AI_DOWN, errText, useRfEditor } from './useRfEditor';

const ACCEPT = '.pptx,.pdf,.docx,.txt,.eml,.msg';
const OK_EXT = ['pptx', 'pdf', 'docx', 'txt', 'eml', 'msg'];
const STARS = 'M12 2.5l1.9 5.6 5.6 1.9-5.6 1.9L12 17.5l-1.9-5.6L4.5 10l5.6-1.9z M19 15l.9 2.1 2.1.9-2.1.9L19 21l-.9-2.1L16 18l2.1-.9z';

const isAi = (by: By | null | undefined) => by === 'ai-accepted';

/** 글이 길면 줄이 늘어나는 한 줄 입력(보드 요구 문장 span 과 같은 모양) */
function AutoText({ value, onChange, onEnter, onEmptyBackspace, className, label, readOnly, inputRef }: {
  value: string; onChange: (v: string) => void; onEnter?: () => void; onEmptyBackspace?: () => void; className?: string; label: string; readOnly?: boolean;
  inputRef?: (el: HTMLTextAreaElement | null) => void;
}) {
  const ref = useRef<HTMLTextAreaElement | null>(null);
  const fit = useCallback(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = '0px';
    el.style.height = `${el.scrollHeight}px`;
  }, []);
  useLayoutEffect(fit, [value, fit]);
  useEffect(() => {
    const el = ref.current;
    if (!el || typeof ResizeObserver === 'undefined') return;
    let w = el.clientWidth;
    const ro = new ResizeObserver(() => { if (el.clientWidth !== w) { w = el.clientWidth; fit(); } });
    ro.observe(el);
    return () => ro.disconnect();
  }, [fit]);
  return (
    <textarea ref={(el) => { ref.current = el; inputRef?.(el); }} rows={1} className={className} aria-label={label} value={value} readOnly={readOnly}
      onChange={(e) => onChange(e.target.value.replace(/\n/g, ' '))}
      onKeyDown={(e) => {
        if (e.nativeEvent.isComposing) return;
        if (e.key === 'Enter') { e.preventDefault(); onEnter?.(); }
        if (e.key === 'Backspace' && !value && onEmptyBackspace) { e.preventDefault(); onEmptyBackspace(); }
      }} />
  );
}

/** 가중치 알약(보드 h28 r999 Manrope 12/800) — 누르면 숫자 입력 */
function WeightPill({ value, ai, onCommit, label, readOnly }: { value: number; ai: boolean; onCommit: (w: number) => void; label: string; readOnly?: boolean }) {
  const [edit, setEdit] = useState<string | null>(null);
  if (edit !== null) {
    const commit = () => { const n = Number(edit.replace(/[^0-9]/g, '')); setEdit(null); if (edit.trim() && Number.isFinite(n) && n !== value) onCommit(n); };
    return (
      <span className={cx('rqf-w', 'rqf-w--edit', ai && 'rqf-w--ai')}>
        <input autoFocus inputMode="numeric" aria-label={`${label} 가중치(%)`} value={edit} onChange={(e) => setEdit(e.target.value.replace(/[^0-9]/g, '').slice(0, 3))}
          onBlur={commit} onKeyDown={(e) => { if (e.key === 'Enter') commit(); if (e.key === 'Escape') setEdit(null); }} />%
      </span>
    );
  }
  return (
    <button type="button" className={cx('rqf-w', ai && 'rqf-w--ai')} aria-label={`${label} 가중치 ${value}% · 눌러서 바꾸기`} disabled={readOnly}
      onClick={() => setEdit(String(value))}>{value}%</button>
  );
}

function ReqTag({ r, onClear }: { r: FReq; onClear: () => void }) {
  if (r.flag === 'vague') return <button type="button" className="rqf-tag rqf-tag--vague" onClick={onClear} title="눌러서 확인 필요 풀기">범위 불명확</button>;
  if (r.flag === 'ask') return <button type="button" className="rqf-tag rqf-tag--ask" onClick={onClear} title="눌러서 확인 필요 풀기">고객에게 확인</button>;
  if (isAi(r.by)) return <span className="rqf-tag rqf-tag--ai">AI 질의로 채움</span>;
  return null;
}

function KeymanCard({ k, idx, n, edit, readOnly, focusReq, setFocusReq }: {
  k: FKeyman; idx: number; n: number; edit: (fn: (f: FForm) => FForm) => void; readOnly: boolean;
  focusReq: string | null; setFocusReq: (id: string | null) => void;
}) {
  const refs = useRef(new Map<string, HTMLTextAreaElement>());
  useEffect(() => {
    if (!focusReq) return;
    const el = refs.current.get(focusReq);
    if (el) { el.focus(); el.setSelectionRange(el.value.length, el.value.length); setFocusReq(null); }
  }, [focusReq, setFocusReq, k.reqs]);
  const setKm = (fn: (x: FKeyman) => FKeyman) => edit((f) => ({ ...f, keymen: f.keymen.map((x) => (x.id === k.id ? fn(x) : x)) }));
  const setReq = (rid: string, fn: (r: FReq) => FReq) => setKm((x) => ({ ...x, reqs: x.reqs.map((r) => (r.id === rid ? fn(r) : r)) }));
  const addReq = (after?: string) => {
    const nr: FReq = { id: newId('q_'), text: '', status: 'ok', flag: 'none', by: 'manual' };
    setKm((x) => {
      const i = after ? x.reqs.findIndex((r) => r.id === after) : -1;
      const reqs = [...x.reqs];
      reqs.splice(i >= 0 ? i + 1 : reqs.length, 0, nr);
      return { ...x, reqs };
    });
    setFocusReq(nr.id);
  };
  const removeReq = (rid: string) => {
    const i = k.reqs.findIndex((r) => r.id === rid);
    setKm((x) => ({ ...x, reqs: x.reqs.filter((r) => r.id !== rid) }));
    const prev = k.reqs[i - 1];
    if (prev) setFocusReq(prev.id);
  };
  const who = k.role.trim() || `키맨 ${idx + 1}`;
  return (
    <div className="rqf-km" data-keyman={k.id}>
      <div className="rqf-kmrow">
        <label htmlFor={`rq-k${idx}`} className="wm-sr-only">키맨</label>
        <input id={`rq-k${idx}`} className="rqf-role" value={k.role} placeholder="키맨 직함 · 예) 자산관리팀장" readOnly={readOnly}
          onChange={(e) => setKm((x) => ({ ...x, role: e.target.value }))}
          onKeyDown={(e) => { if (e.key === 'Enter' && !e.nativeEvent.isComposing) { if (k.reqs[0]) setFocusReq(k.reqs[0].id); else addReq(); } }} />
        <WeightPill value={k.weight} ai={isAi(k.weight_by)} label={who} readOnly={readOnly}
          onCommit={(w) => edit((f) => ({ ...f, keymen: setWeight(f.keymen, idx, w) }))} />
      </div>
      {k.reqs.map((r, j) => (
        <div key={r.id} className="rqf-req" data-req={r.id}>
          <button type="button" className="rqf-n" aria-label={`${who} 요구 ${j + 1} 지우기`} title="지우기" disabled={readOnly} onClick={() => removeReq(r.id)}>
            <span className="rqf-n__num">{j + 1}</span><span className="rqf-n__x" aria-hidden>×</span>
          </button>
          <AutoText className={cx('rqf-rt', isAi(r.by) && r.flag === 'none' && 'rqf-rt--ai')} label={`${who} 요구 ${j + 1}`} value={r.text} readOnly={readOnly}
            inputRef={(el) => { if (el) refs.current.set(r.id, el); else refs.current.delete(r.id); }}
            onChange={(t) => setReq(r.id, (x) => ({ ...x, text: t, by: x.text !== t ? 'manual' : x.by }))}
            onEnter={() => addReq(r.id)} onEmptyBackspace={() => removeReq(r.id)} />
          <ReqTag r={r} onClear={() => setReq(r.id, (x) => ({ ...x, flag: 'none', status: 'ok' }))} />
          {r.flag === 'none' && !isAi(r.by) && !readOnly && r.text.trim() && (
            <button type="button" className="rqf-tag rqf-tag--mark" onClick={() => setReq(r.id, (x) => ({ ...x, flag: 'ask', status: 'check' }))}>확인 필요</button>
          )}
        </div>
      ))}
      <button type="button" className="rqf-addreq" disabled={readOnly} onClick={() => addReq()}>+ 요구사항</button>
      {n > 1 && !readOnly && (
        <button type="button" className="rqf-kmx" aria-label={`${who} 빼기`} title="키맨 빼기"
          onClick={() => edit((f) => ({ ...f, keymen: removeKeyman(f.keymen, idx) }))}>×</button>
      )}
    </div>
  );
}

export function Editor({ initial, onCreated, onFinished }: { initial: RFDoc | null; onCreated: (d: RFDoc) => void; onFinished: (out: RFStageOut) => void }) {
  const qc = useQueryClient();
  const inval = useFlowInvalidate();
  const ed = useRfEditor(initial, onCreated);
  const { doc, form, edit, docRef, applyDoc } = ed;
  const [aiOpen, setAiOpen] = useState(false);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiBusy, setAiBusy] = useState(false);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState<string[]>([]);
  const [over, setOver] = useState(false);
  const [focusReq, setFocusReq] = useState<string | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  const fillJob = doc?.fill_job ?? null;
  const filling = !!fillJob || uploading.length > 0;
  const readOnly = filling;

  const job = useJob(fillJob, {
    onDone: async (j) => {
      if (!ed.docRef.current) return;
      try {
        const fresh = await rfApi.get(ed.docRef.current.id);
        ed.applyDoc(fresh, true);
        const filled = Number((j.result as { filled?: number } | null)?.filled ?? 0);
        if (j.status === 'failed') toast(j.error?.message || '파일을 읽지 못했어요');
        else if (!filled) toast((j.result as { note?: string } | null)?.note || '파일에서 새로 채울 값을 찾지 못했어요');
      } catch (e) { toast(errText(e)); }
    },
  });

  // SSE 가 끊겨도 채우기가 끝나면 풀리게(4초마다 문서 확인)
  useEffect(() => {
    if (!fillJob) return;
    const t = window.setInterval(async () => {
      const cur = docRef.current;
      if (!cur) return;
      try { const fresh = await rfApi.get(cur.id); if (!fresh.fill_job && docRef.current?.fill_job) applyDoc(fresh, true); } catch { /* 다음 번에 */ }
    }, 4000);
    return () => window.clearInterval(t);
  }, [fillJob, docRef, applyDoc]);

  const set = (patch: Partial<FForm>) => edit((f) => ({ ...f, ...patch }));
  const setField = (k: 'title' | 'customer' | 'target', v: string) => edit((f) => ({ ...f, [k]: v, [`${k}_by`]: v ? 'manual' : null }));

  const attach = async (files: File[]) => {
    const ok = files.filter((f) => OK_EXT.includes((f.name.split('.').pop() ?? '').toLowerCase()));
    if (ok.length < files.length) toast('PPTX · PDF · DOCX · TXT · 메일만 넣을 수 있어요');
    if (!ok.length || filling) return;
    setUploading(ok.map((f) => f.name));
    try {
      const d = await ed.ensureDoc();
      if (!(await ed.flush())) return;
      const metas = await Promise.all(ok.map((f) => uploadFile(f, { confidential: true, purpose: 'rq.source' })));
      const acc = await rfApi.fill(d.id, metas.map((m) => m.id));
      ed.applyDoc({ ...(ed.docRef.current ?? d), fill_job: acc.job_id });
    } catch (e) { toast(errText(e)); } finally { setUploading([]); }
  };
  const onDrag = (e: DragEvent, on: boolean) => {
    if (!Array.from(e.dataTransfer?.types ?? []).includes('Files')) return;
    e.preventDefault();
    if (!on && e.currentTarget.contains(e.relatedTarget as Node | null)) return;   // 안쪽 요소로 옮겨 갈 때는 그대로
    setOver(on);
  };
  const onDrop = (e: DragEvent) => {
    if (!Array.from(e.dataTransfer?.types ?? []).includes('Files')) return;
    e.preventDefault();
    setOver(false);
    void attach(Array.from(e.dataTransfer.files ?? []));
  };

  const openAi = async () => {
    if (filling) { toast('파일에서 폼을 채우는 중이에요. 끝난 뒤 다시 눌러 주세요.'); return; }
    setAiOpen(true);
    setAiLoading(true);
    try {
      const d = await ed.ensureDoc();
      if (!(await ed.flush())) { setAiOpen(false); return; }
      const out = await rfApi.deep(d.id);
      ed.applyDoc(out.doc);
    } catch (e) {
      toast(errText(e));
      setAiOpen(false);
    } finally { setAiLoading(false); }
  };
  const closeAi = async () => {
    setAiOpen(false);
    const d = ed.docRef.current;
    if (d && (d.counts?.pending ?? 0) > 0) {
      try { ed.applyDoc(await rfApi.closeDeep(d.id)); } catch { /* 다음 질의 때 새로 만든다 */ }
    }
  };
  const answer = async (qid: string, body: { option?: number | null; text?: string | null; later: boolean }) => {
    const d = ed.docRef.current;
    if (!d) return;
    setAiBusy(true);
    try {
      if (!(await ed.flush())) return;
      // 답은 서버가 폼에 넣는다 → 폼을 서버 값으로 바꾼다(안 그러면 다음 자동 저장이 답을 지운다)
      ed.applyDoc(await rfApi.answer(d.id, qid, { option: body.option ?? null, text: body.text ?? null, later: body.later }), true);
    } catch (e) { toast(errText(e)); } finally { setAiBusy(false); }
  };

  const save = async () => {
    if (saving) return;
    if (filling) { toast('파일에서 폼을 채우는 중이에요. 끝난 뒤 저장해 주세요.'); return; }
    setSaving(true);
    try {
      const d = await ed.ensureDoc();
      if (!(await ed.flush())) return;
      const out = await rfApi.finish(d.id);
      ed.applyDoc(out.doc);
      inval();
      void qc.invalidateQueries({ queryKey: rfListKey });
      onFinished(out);
    } catch (e) { toast(errText(e) === AI_DOWN ? '저장하지 못했어요. 다시 시도해 주세요.' : errText(e)); } finally { setSaving(false); }
  };

  const sources = doc?.sources ?? [];
  const sum = weightSum(form);
  const kmsShown = form.keymen;
  const fields: Array<{ id: string; k: 'title' | 'customer' | 'target'; label: string; ph: string }> = [
    { id: 'rq-proj', k: 'title', label: '프로젝트명', ph: '' },
    { id: 'rq-cust', k: 'customer', label: '고객사', ph: '' },
    { id: 'rq-to', k: 'target', label: '최종 제안대상', ph: doc?.target_ask && !form.target ? '[확인 필요]' : '예) 대표이사' },
  ];
  const progress = job.job && job.job.status === 'running' ? ` · ${job.job.progress ?? 0}%` : '';
  return (
    <FlowScreen pad="0" gap={0} className="rqf-screen"
      bar={doc?.sb_ids?.length ? <FlowBar sbIds={doc.sb_ids} current="rq" note="저장하면 연결된 Storyboard에 반영돼요" />
        : <LinkedStoryboardBar chips={[]} emptyText="저장하면 이 요구사항으로 Storyboard가 자동으로 만들어져요" />}>
      <div className="rqf-row">
        <section className={cx('rqf-main', aiOpen && 'rqf-main--ai')} onDragOver={(e) => onDrag(e, true)} onDragLeave={(e) => onDrag(e, false)} onDrop={onDrop}>
          <div className="rqf-head">
            <h1>고객 요구사항 입력</h1>
            {!aiOpen && (
              <button type="button" className="rqf-aibtn" onClick={() => void openAi()}>
                <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor" aria-hidden><path d={STARS} /></svg>AI 심층 질의로 폼 완성
              </button>
            )}
          </div>

          <div className={cx('rqf-drop', over && 'rqf-drop--over')} data-state={filling ? 'filling' : over ? 'over' : 'idle'}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--wm-brand)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }} aria-hidden>
              <path d="M12 15V4 M7 9l5-5 5 5 M4 15v5h16v-5" /></svg>
            <span className="rqf-drop__t">파일을 끌어다 놓으면 폼이 채워져요 <span>· PPTX · PDF · DOCX · 메일</span></span>
            {filling && <span className="rqf-chip" role="status">{(uploading[0] ?? sources[sources.length - 1]?.name ?? '파일')} 읽는 중{progress}</span>}
            {!filling && sources.slice(-1).map((s) => <span key={s.file_id} className="rqf-chip" title={sources.map((x) => x.name).join(' · ')}>{s.name}에서 읽음{sources.length > 1 ? ` 외 ${sources.length - 1}` : ''}</span>)}
            <button type="button" className="rqf-ghost34" onClick={() => fileInput.current?.click()} disabled={filling}>파일 첨부</button>
            <input ref={fileInput} type="file" multiple accept={ACCEPT} hidden aria-label="파일 첨부"
              onChange={(e: ChangeEvent<HTMLInputElement>) => { const fs = Array.from(e.target.files ?? []); e.target.value = ''; void attach(fs); }} />
          </div>

          <div className="rqf-grid">
            <div className="rqf-card rqf-left">
              {fields.map((f) => {
                const ai = isAi(form[`${f.k}_by`]);
                return (
                  <div key={f.id} className="rqf-field">
                    <label htmlFor={f.id} className="rqf-label">{f.label}{ai && <span className="rqf-aitag">AI 질의로 채움</span>}</label>
                    <input id={f.id} className={cx('rqf-input', ai && 'rqf-input--ai')} value={form[f.k]} placeholder={f.ph} readOnly={readOnly}
                      onChange={(e) => setField(f.k, e.target.value)} />
                  </div>
                );
              })}
              <div className="rqf-field rqf-field--grow">
                <label htmlFor="rq-note" className="rqf-label">제작자 의견<small>· 고객 문서에서 빠져요</small></label>
                <textarea id="rq-note" className="rqf-textarea" placeholder="제안 방향 · 강조할 점" value={form.note} readOnly={readOnly}
                  onChange={(e) => set({ note: e.target.value })} />
              </div>
            </div>
            <div className="rqf-card rqf-right">
              <div className="rqf-rhead"><b>키맨별 요구사항</b><span className={cx(sum !== 100 && 'rqf-warn')}>가중치 합 {sum}%</span></div>
              <div className="rqf-kms">
                {kmsShown.map((k, i) => (
                  <KeymanCard key={k.id} k={k} idx={i} n={kmsShown.length} edit={edit} readOnly={readOnly} focusReq={focusReq} setFocusReq={setFocusReq} />
                ))}
                <button type="button" className="rqf-addkm" disabled={readOnly || kmsShown.length >= 8}
                  onClick={() => edit((f) => ({ ...f, keymen: addKeyman(f.keymen) }))}>+ 키맨 추가</button>
              </div>
            </div>
          </div>

          <FlowFooter back={{ to: '/requirements', label: '목록' }} summary="모두 선택 항목이에요" primary={{ label: '저장', onClick: () => void save(), busy: saving }} />
        </section>
        {aiOpen && <DeepPanel deep={doc?.deep} loading={aiLoading} busy={aiBusy} onAnswer={answer} onClose={() => void closeAi()} />}
      </div>
    </FlowScreen>
  );
}
