/**
 * RQ1 빈 폼 · RQ1D 끌어다 놓기 · RQ1G 채우는 중 · RQ2 채워진 폼 — `/requirements/new` · `/requirements/:rqId/form`.
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { uploadFile } from '@/api/client';
import { useShellPage } from '@/shell';
import { Button, Icon, toast } from '@/ui';
import { ApiError, errorText, rqApi, type FieldName, type FormField, type Requirement, type SourceFile } from '../api';
import { KeymenCard } from '../components/KeymenCard';
import { LiveInput, LiveTextarea } from '../components/LiveInput';
import { Shim, SrcBadge } from '../components/bits';
import { rqKey, useAfterSave, useDraftEditor, useJobTicker } from '../hooks';
import { isFormEmpty } from '../lib/draft';

const ACCEPT = '.pptx,.pdf,.docx,.txt,.eml,.msg';
const SUPPORTED: Record<string, string> = { pptx: 'PPTX', pdf: 'PDF', docx: 'DOCX', txt: 'TXT', eml: '메일', msg: '메일' };
export const STEPS = ['입력', '심층 작성', '저장'];

export const labelOf = (name: string) => SUPPORTED[(name.split('.').pop() ?? '').toLowerCase()];

export function computeTitle(view: Requirement, server?: Requirement) {
  const c = view.form.customer_name.value;
  const p = view.form.project_name.value;
  if (server?.title && server.form.customer_name.value === c && server.form.project_name.value === p) return server.title;
  return [c, p].filter(Boolean).join(' ') || null;
}

export function FormPage() {
  const { rqId } = useParams();
  const [sp] = useSearchParams();
  const ret = sp.get('return');
  const retQuery = ret ? `?return=${encodeURIComponent(ret)}` : '';
  const navigate = useNavigate();
  const qc = useQueryClient();
  const ed = useDraftEditor(rqId, { returnQuery: retQuery });
  const v = ed.view;
  const fillJob = v.active_job?.kind === 'rq.fill' ? v.active_job.job_id : null;
  const filling = !!fillJob || (v.queued_jobs?.length ?? 0) > 0;
  const [uploading, setUploading] = useState<Array<{ name: string; label: string }>>([]);
  const [prog, setProg] = useState<{ filled: number; total: number } | null>(null);
  const [saveAfterFill, setSaveAfterFill] = useState(false);
  const [busy, setBusy] = useState<'save' | 'deep' | null>(null);
  const [drag, setDrag] = useState<{ count: number; names: Array<{ name: string; label: string }> } | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  const title = computeTitle(v, ed.server) || '새 요구사항';
  const afterSave = useAfterSave();

  useShellPage({ section: '고객 요구사항', title, hasTask: true, stepper: { steps: STEPS, current: 1 } });

  const refetch = useCallback(() => { if (ed.id) void qc.invalidateQueries({ queryKey: rqKey(ed.id) }); }, [ed.id, qc]);
  const job = useJobTicker(fillJob, refetch);
  useEffect(() => {
    const last = [...job.events].reverse().find((e) => e.type === 'progress' && typeof e.data.filled === 'number');
    if (last) setProg({ filled: last.data.filled, total: last.data.total });
    const err = job.events.find((e) => e.type === 'error');
    if (err && job.done) toast(err.data.message || '파일을 읽지 못했어요');
  }, [job.events, job.done]);
  useEffect(() => { if (!fillJob) setProg(null); }, [fillJob]);

  const doSave = useCallback(async () => {
    setBusy('save');
    try {
      await ed.flushNow();
      const id = await ed.ensureId();
      const res = await rqApi.save(id);
      await afterSave(id, res);
      navigate(`/requirements/${id}/saved?v=${res.version}${ret ? `&return=${encodeURIComponent(ret)}` : ''}`);
    } catch (e) {
      if (e instanceof ApiError && e.code === 'JOB_RUNNING') { setSaveAfterFill(true); return; }
      toast(errorText(e));
    } finally {
      setBusy(null);
    }
  }, [ed, navigate, ret, afterSave]);

  // RQ1G `바로 저장`: 채우기가 끝난 뒤 저장(§3.2)
  useEffect(() => {
    if (saveAfterFill && !filling && ed.server && !ed.server.active_job) {
      setSaveAfterFill(false);
      void doSave();
    }
  }, [saveAfterFill, filling, ed.server, doSave]);

  const onSave = () => {
    if (filling) { setSaveAfterFill(true); return; }
    void doSave();
  };

  const onDeep = async () => {
    setBusy('deep');
    try {
      await ed.flushNow();
      const id = await ed.ensureId();
      const cur = qc.getQueryData<Requirement>(rqKey(id)) ?? v;
      if (cur.active_deep_session_id) {
        navigate(cur.active_deep?.status === 'asking' ? `/requirements/${id}/deep/${cur.active_deep_session_id}/q` : `/requirements/${id}/deep/${cur.active_deep_session_id}`);
        return;
      }
      const acc = await rqApi.startDeep(id);
      navigate(`/requirements/${id}/deep/${acc.ref.id}`);
    } catch (e) {
      if (e instanceof ApiError && e.code === 'SESSION_ACTIVE' && ed.id) { navigate(`/requirements/${ed.id}/deep/${String(e.details.session_id)}`); return; }
      toast(errorText(e));
    } finally {
      setBusy(null);
    }
  };

  const addFiles = useCallback(async (files: File[]) => {
    const ok = files.filter((f) => labelOf(f.name));
    if (ok.length < files.length) toast('PPTX · PDF · DOCX · TXT · 메일만 넣을 수 있어요');
    if (!ok.length) return;
    try {
      const id = await ed.ensureId();
      setUploading(ok.map((f) => ({ name: f.name, label: labelOf(f.name) })));
      const metas = await Promise.all(ok.map((f) => uploadFile(f, { confidential: true, purpose: 'rq.source' })));
      await rqApi.addFiles(id, metas.map((m) => m.id));
      await qc.invalidateQueries({ queryKey: rqKey(id) });
    } catch (e) {
      toast(errorText(e));
    } finally {
      setUploading([]);
    }
  }, [ed, qc]);

  // RQ1D — 화면 어디에 끌어도 오버레이(파일만)
  useEffect(() => {
    let depth = 0;
    const isFiles = (e: DragEvent) => Array.from(e.dataTransfer?.types ?? []).includes('Files');
    const enter = (e: DragEvent) => {
      if (!isFiles(e)) return;
      depth += 1;
      const items = Array.from(e.dataTransfer?.items ?? []).filter((i) => i.kind === 'file');
      const names = Array.from(e.dataTransfer?.files ?? []).map((f) => ({ name: f.name, label: labelOf(f.name) ?? '' })).filter((x) => x.name);
      setDrag({ count: items.length || names.length, names });
    };
    const over = (e: DragEvent) => { if (isFiles(e)) e.preventDefault(); };
    const leave = (e: DragEvent) => {
      if (!isFiles(e)) return;
      depth = Math.max(0, depth - 1);
      if (depth === 0 || !e.relatedTarget) setDrag(null);
    };
    const drop = (e: DragEvent) => {
      if (!isFiles(e)) return;
      e.preventDefault();
      depth = 0;
      setDrag(null);
      void addFiles(Array.from(e.dataTransfer?.files ?? []));
    };
    const esc = (e: KeyboardEvent) => { if (e.key === 'Escape') { depth = 0; setDrag(null); } };
    window.addEventListener('dragenter', enter);
    window.addEventListener('dragover', over);
    window.addEventListener('dragleave', leave);
    window.addEventListener('drop', drop);
    window.addEventListener('keydown', esc);
    return () => {
      window.removeEventListener('dragenter', enter);
      window.removeEventListener('dragover', over);
      window.removeEventListener('dragleave', leave);
      window.removeEventListener('drop', drop);
      window.removeEventListener('keydown', esc);
    };
  }, [addFiles]);

  const removeFile = async (f: SourceFile) => {
    if (!ed.id) return;
    try {
      const res = await rqApi.removeFile(ed.id, f.file_id);
      qc.setQueryData(rqKey(ed.id), res);
      const rid = ed.id;
      toast('파일을 뺐어요', {
        duration: 5000,
        action: { label: '되돌리기', onClick: () => { void rqApi.restoreFile(rid, f.file_id).then((r) => qc.setQueryData(rqKey(rid), r)).catch((e) => toast(errorText(e))); } },
      });
    } catch (e) {
      toast(errorText(e));
    }
  };

  const retryFile = async (f: SourceFile) => {
    if (!ed.id) return;
    try {
      await rqApi.addFiles(ed.id, [f.file_id]);
      refetch();
    } catch (e) {
      toast(errorText(e));
    }
  };

  const files = v.files ?? [];
  const hasFiles = files.length > 0 || uploading.length > 0 || filling;
  const empty = isFormEmpty(v) && !uploading.length;
  const progress = prog ?? (v.fill_progress ? { filled: v.fill_progress.filled, total: v.fill_progress.total } : null);

  return (
    <div className="rq-root">
      <section className="rq-form-section" aria-busy={ed.query.isLoading && !!ed.id}>
        <input ref={fileInput} type="file" multiple accept={ACCEPT} hidden data-testid="rq-file-input"
          onChange={(e) => { const fs = Array.from(e.target.files ?? []); e.target.value = ''; void addFiles(fs); }} />
        {hasFiles ? (
          <div className="rq-filerow" data-testid="file-row">
            <span style={{ color: 'var(--wm-text-subtle)', display: 'inline-flex' }} aria-hidden="true"><Icon name="upload" size={18} /></span>
            <div style={{ display: 'flex', gap: 8, minWidth: 0, overflow: 'hidden', flex: '0 1 auto' }}>
              {files.map((f) => <FileChip key={f.file_id} f={f} busy={filling} onRemove={() => void removeFile(f)} onRetry={() => void retryFile(f)} />)}
              {uploading.map((u) => (
                <span key={u.name} className="rq-filechip" data-state="uploading">
                  <span className="rq-src">{u.label}</span><span className="rq-filechip__name">{u.name}</span>
                  <span className="rq-reading" role="status" aria-label="올리는 중" />
                </span>
              ))}
            </div>
            <span style={{ flex: 1 }} />
            {filling ? (
              <div className="rq-fillprog" data-testid="fill-progress">
                <span>채우는 중</span>
                <span className="rq-fillprog__bar" aria-hidden="true"><span style={{ width: `${progress && progress.total ? Math.round((100 * progress.filled) / progress.total) : 4}%` }} /></span>
                <b>{progress ? `${progress.filled} / ${Math.max(progress.total, progress.filled)}` : '0 / 0'}</b>
              </div>
            ) : (
              <Button h={34} icon={<Icon name="upload" size={14} color="var(--wm-brand)" />} onClick={() => fileInput.current?.click()}>파일 첨부</Button>
            )}
          </div>
        ) : (
          <div className="rq-drop" data-testid="drop-zone">
            <span className="rq-drop__icon" aria-hidden="true"><Icon name="upload" size={22} /></span>
            <div>
              <div className="rq-drop__title">파일을 끌어다 놓으면 폼이 채워져요</div>
              <div className="rq-drop__sub">PPTX · PDF · DOCX · TXT · 메일</div>
            </div>
            <Button h={38} icon={<Icon name="upload" size={14} color="var(--wm-brand)" />} onClick={() => fileInput.current?.click()}>파일 첨부</Button>
          </div>
        )}
        <div className="rq-grid">
          <div className="rq-leftcard">
            <TextField id="f-proj" field="project_name" label="프로젝트명" placeholder="예) 용산 업무시설 재개발 제안" max={120} v={v} edit={ed.edit} filling={filling} fillJob={fillJob} />
            <TextField id="f-cust" field="customer_name" label="고객사" placeholder="예) E 자산운용" max={80} v={v} edit={ed.edit} filling={filling} fillJob={fillJob} />
            <TextField id="f-to" field="final_audience" label="최종 제안대상" placeholder="예) 대표이사" max={80} v={v} edit={ed.edit} filling={filling} fillJob={fillJob} />
            <div className="rq-divider" />
            <NoteField v={v} edit={ed.edit} filling={filling} fillJob={fillJob} />
          </div>
          <KeymenCard rq={v} edit={ed.edit} filling={filling} fillJobId={fillJob} />
        </div>
        <div className="rq-actions">
          <Button h={48} style={{ padding: '0 18px', fontSize: 15, fontWeight: 700 }} aria-disabled={empty && !filling ? 'true' : undefined}
            className={empty && !filling ? 'rq-off' : undefined} title={empty && !filling ? '폼이 비어 있어요' : undefined}
            loading={busy === 'save' || saveAfterFill} onClick={() => { if (!(empty && !filling)) onSave(); }}>바로 저장</Button>
          <Button h={48} variant="primary" style={{ padding: '0 22px', fontSize: 15, fontWeight: 700 }} icon={<Icon name="sparkle" size={15} />}
            aria-disabled={filling ? 'true' : undefined} className={filling ? 'rq-off' : undefined} title={filling ? '파일로 폼을 채우는 중이에요' : undefined}
            loading={busy === 'deep'} onClick={() => { if (!filling) void onDeep(); }}>심층 작성</Button>
        </div>
        {drag && (
          <div className="rq-overlay" role="region" aria-label="여기에 놓기" onDragOver={(e) => e.preventDefault()}>
            <span className="rq-overlay__icon" aria-hidden="true"><Icon name="upload" size={28} /></span>
            <div className="rq-overlay__title">놓으면 폼을 채워요</div>
            <div className="rq-overlay__sub">파일 {drag.count}개</div>
            {drag.names.length > 0 && (
              <div className="rq-overlay__chips">
                {drag.names.map((n) => (
                  <span key={n.name} className="rq-overlay__chip">{n.label && <span className="rq-src">{n.label}</span>}{n.name}</span>
                ))}
              </div>
            )}
          </div>
        )}
      </section>
    </div>
  );
}

function FileChip({ f, busy, onRemove, onRetry }: { f: SourceFile; busy: boolean; onRemove: () => void; onRetry: () => void }) {
  const failed = f.status === 'failed';
  return (
    <span className={`rq-filechip ${failed ? 'rq-filechip--failed' : ''}`} data-state={f.status} data-file={f.name}
      title={failed ? '읽지 못했어요' : f.name} onClick={failed ? onRetry : undefined} role={failed ? 'button' : undefined}
      aria-label={failed ? `${f.name} 다시 시도` : undefined}>
      <span className="rq-src">{f.type_label}</span>
      <span className="rq-filechip__name">{f.name}</span>
      {f.status === 'done' && <span className="rq-done" aria-label="완료"><Icon name="check" size={11} strokeWidth={3} /></span>}
      {(f.status === 'reading' || f.status === 'uploading') && <span className="rq-reading" role="status" aria-label="읽는 중" />}
      {failed && <span className="rq-failed" aria-hidden="true">!</span>}
      {!busy && f.status !== 'reading' && (
        <button type="button" className="rq-iconx" aria-label="빼기" onClick={(e) => { e.stopPropagation(); onRemove(); }}>
          <Icon name="x" size={11} strokeWidth={2.4} />
        </button>
      )}
    </span>
  );
}

function TextField({ id, field, label, placeholder, max, v, edit, filling, fillJob }: {
  id: string; field: FieldName; label: string; placeholder: string; max: number; v: Requirement;
  edit: ReturnType<typeof useDraftEditor>['edit']; filling: boolean; fillJob: string | null;
}) {
  const f: FormField = v.form[field];
  const fromJob = !!fillJob && f.source?.job_id === fillJob;
  const badge = f.source?.kind === 'file' && f.source.file_label;
  const skeleton = filling && !f.value;
  return (
    <div className="rq-fld">
      <label htmlFor={id}>{label}</label>
      <div className="rq-fld__box">
        <LiveInput id={id} className={`rq-input ${badge ? 'rq-input--badge' : ''} ${fromJob ? 'rq-input--fill' : ''}`} placeholder={placeholder} maxLength={max}
          value={f.value ?? ''} onText={(t) => edit({ op: 'set_field', field, value: t || null })} data-source={f.source?.kind ?? ''} />
        {skeleton && <span className="rq-skel" aria-busy="true" style={{ pointerEvents: 'none' }}><Shim w="58%" /></span>}
        <SrcBadge source={f.source} className="rq-fld__badge" style={{ position: 'absolute' }} />
      </div>
    </div>
  );
}

function NoteField({ v, edit, filling, fillJob }: { v: Requirement; edit: ReturnType<typeof useDraftEditor>['edit']; filling: boolean; fillJob: string | null }) {
  const f = v.form.author_note;
  const fromJob = !!fillJob && f.source?.job_id === fillJob;
  return (
    <div className="rq-fld rq-fld--grow">
      <label htmlFor="f-note">
        제작자 의견
        <span title="고객 문서 제외" style={{ display: 'inline-flex', color: 'var(--wm-text-subtle)' }}><Icon name="lock" size={13} title="고객 문서 제외" /></span>
      </label>
      <div className="rq-fld__box">
        <LiveTextarea id="f-note" className={`rq-textarea ${fromJob ? 'rq-textarea--fill' : ''}`} placeholder="제안 방향 · 강조할 점" maxLength={2000}
          value={f.value ?? ''} onText={(t) => edit({ op: 'set_field', field: 'author_note', value: t || null })} />
        {filling && !f.value && (
          <span className="rq-skel" aria-busy="true" style={{ pointerEvents: 'none', inset: 0, padding: '15px 12px' }}><Shim w="80%" /><Shim w="48%" /></span>
        )}
        <SrcBadge source={f.source} className="rq-fld__badge rq-fld__badge--bottom" style={{ position: 'absolute' }} />
      </div>
    </div>
  );
}
