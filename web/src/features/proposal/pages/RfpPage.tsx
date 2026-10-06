/**
 * PR1F — RFP로 시작(§4.8, 보드 PR1F, 1/6).
 * 파일을 올리면 `POST …/rfp`(잡: 읽기 → 항목 찾기 → 채우기) → 원문 발췌(①…⑨ 하이라이트) ↔ 자동 채움 9항목(찾음 · 추정 · 비어 있음).
 * 행 클릭 = 원문 위치로 스크롤 · 강조, 값 클릭 = 바로 고치기(PUT fields/{key}), 비어 있는 항목은 아래 카드에서 입력.
 * 「확인 · 다음: 제안서 유형」 → `rfp:confirm`(서버가 stage=type) → PR2. 「직접 입력으로」 → PR1(채운 값 유지).
 */
import { useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { uploadFile } from '@/api/client';
import { Dropzone, Icon, cx, toast } from '@/ui';
import { confirmRfp, putRfpField, qk, startRfp, useProposal, useRfp } from '../api/proposal';
import { errText, jobErrText } from '../api/http';
import { useJobEvents } from '../api/jobs';
import type { RfpField, RfpView } from '../api/types';
import { Agent, Dock, ErrorBand, LoadingCard, NextButton, PrPage, SpinIcon } from '../components/parts';
import { R } from '../lib/routes';
import { useProposalShell } from '../lib/useProposalShell';

export const NUM = ['①', '②', '③', '④', '⑤', '⑥', '⑦', '⑧', '⑨', '⑩', '⑪', '⑫'];
const MB50 = 50 * 1024 * 1024;
const RFP_EXT = /\.(pdf|docx|pptx|txt)$/i;
const NOTE_EXT = /\.(pdf|docx|txt|eml)$/i;
const PHASES = [['read', '읽기'], ['find', '항목 찾기'], ['fill', '채우기']] as const;
/** 아래 카드 입력 라벨 · 자리표시(보드 원문) */
const EMPTY_LABEL: Record<string, string> = { decision_makers: '의사결정자 · 청중' };
const EMPTY_PH: Record<string, string> = {
  budget: '예) [00]억 원 이내 · 모르면 비워 두기',
  decision_makers: '예) 운영본부장, 마케팅팀장, IT팀',
};
const STATE_CLS: Record<string, string> = { found: 'pr-state pr-state--found', guess: 'pr-state pr-state--guess', empty: 'pr-state pr-state--empty' };
const STATE_LABEL: Record<string, string> = { found: '찾음', guess: '추정', empty: '비어 있음' };
const STATE_ICON: Record<string, string> = { found: 'M5 12l5 5L20 7', guess: 'M12 8v5 M12 16.5v.5', empty: 'M6 12h12' };

function StateIcon({ d }: { d: string }) {
  return <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={d} /></svg>;
}

function checkFile(f: File, re: RegExp, kinds: string) {
  if (!re.test(f.name)) return `${kinds}만 올릴 수 있어요`;
  if (f.size > MB50) return '파일당 50MB까지 올릴 수 있어요';
  return null;
}

export function RfpPage() {
  const { id } = useParams();
  const nav = useNavigate();
  const qc = useQueryClient();
  const pq = useProposal(id);
  const p = pq.data;
  const [job, setJob] = useState<string | null>(null);
  const [busy, setBusy] = useState<'file' | 'extra' | 'confirm' | null>(null);
  const rq = useRfp(id, job ? 2500 : false);
  const rv = rq.data;
  const activeJob = job ?? (rv?.status === 'running' ? rv.job_id ?? null : null);
  const ev = useJobEvents(activeJob, {
    onDone: (j) => {
      setJob(null);
      if (j.status === 'failed') toast(jobErrText(j.error, '파일을 읽지 못했어요. 다른 파일을 올려 주세요.'));
      void rq.refetch();
    },
  });
  // 잡 이벤트 없이 상태만 running 이면 폴링(다른 창에서 시작한 경우)
  useEffect(() => {
    if (rv?.status !== 'running' || job) return;
    const t = window.setInterval(() => void rq.refetch(), 2500);
    return () => window.clearInterval(t);
  }, [rv?.status, job, rq]);
  useProposalShell({ p, step: 1, oneClick: { from: 'customer' } });

  const fileRef = useRef<HTMLInputElement>(null);
  const noteRef = useRef<HTMLInputElement>(null);
  const [focusNo, setFocusNo] = useState<number | null>(null);
  const [editing, setEditing] = useState<string | null>(null);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const pending = useRef<Record<string, string>>({});

  const setView = (v: RfpView) => { if (id) qc.setQueryData(qk.sub(id, 'rfp'), v); };
  const upload = async (files: File[], extra: boolean) => {
    if (!id || !files.length) return;
    const f = files[0];
    const bad = checkFile(f, extra ? NOTE_EXT : RFP_EXT, extra ? 'TXT · DOCX · PDF · 메일(.eml)' : 'PDF · DOCX · PPTX · TXT');
    if (bad) { toast(bad); return; }
    setBusy(extra ? 'extra' : 'file');
    try {
      const up = await uploadFile(f, { projectId: p?.project_id ?? undefined, purpose: extra ? 'proposal_rfp_note' : 'proposal_rfp' });
      const cur = rv?.files?.map((x) => x.file_id) ?? [];
      const curExtra = rv?.extra_files?.map((x) => x.file_id) ?? [];
      const r = extra ? await startRfp(id, cur, [...curExtra, up.id]) : await startRfp(id, [up.id], curExtra.length ? curExtra : undefined);
      setJob(r.job_id);
      void rq.refetch();
    } catch (e) { toast(errText(e)); } finally { setBusy(null); }
  };
  const saveField = async (key: string, value: string) => {
    if (!id) return;
    delete pending.current[key];
    try { setView(await putRfpField(id, key, value)); } catch (e) { toast(errText(e)); }
  };
  const flush = async () => { for (const [k, v] of Object.entries(pending.current)) await saveField(k, v); };
  const goNext = async () => {
    if (!id) return;
    setBusy('confirm');
    try {
      await flush();
      const np = await confirmRfp(id);
      qc.setQueryData(qk.p(id), np);
      void qc.invalidateQueries({ queryKey: qk.p(id) });
      nav(R.type(id));
    } catch (e) { toast(errText(e)); } finally { setBusy(null); }
  };
  const goManual = async () => { await flush(); if (id) nav(R.customer(id)); };
  const jump = (no: number) => {
    setFocusNo(no);
    document.getElementById(`pr1f-ex-${no}`)?.scrollIntoView({ block: 'center', behavior: 'smooth' });
  };

  if (pq.isError) return <PrPage><ErrorBand message={errText(pq.error, '제안서를 찾을 수 없어요')} onRetry={() => void pq.refetch()} /></PrPage>;
  if (!p) return <PrPage><LoadingCard /></PrPage>;

  const status = rv?.status ?? (rq.isError ? 'none' : undefined);
  const running = !!activeJob || status === 'running';
  const failed = status === 'failed' && !running;
  const done = status === 'done' && !running;
  const fields = rv?.fields ?? [];
  const empty = fields.filter((f) => f.state === 'empty');
  const tally = rv?.tally ?? { found: fields.filter((f) => f.state === 'found').length, guess: fields.filter((f) => f.state === 'guess').length, empty: empty.length };
  const file = rv?.files?.[0];
  const phases = (rv?.phases?.length ? rv.phases : PHASES.map(([key, label]) => ({ key, label, status: done ? 'done' : 'todo' as const })))
    .map((ph) => { const st = ev.steps.get(ph.key)?.status; return { ...ph, status: st === 'done' ? 'done' : st === 'running' ? 'busy' : ph.status }; });
  const intro = !rv || status === 'none' || (rq.isError && !rv)
    ? 'RFP 파일을 올리면 고객 · 프로젝트 · 요구사항 · 일정을 읽어서 채워 드릴게요. 원문에서 찾은 곳에 번호를 달아 둘 테니 맞는지 확인만 해 주세요.'
    : running ? 'RFP를 읽고 있어요. 원문에서 고객 · 프로젝트 정보를 찾아 채우는 중이에요.'
      : failed ? '파일을 읽지 못했어요. 다른 파일을 올려 주세요.'
        : rv.intro || `RFP를 읽고 고객 · 프로젝트 정보를 채웠어요. 원문에서 찾은 곳에 번호를 달아 두었으니 맞는지 확인해 주세요. 원문에 없는 ${empty.length}개 항목은 비워 두었어요.`;
  const rqHint = rv?.rq_label || (rv?.rq_count ? `요구사항 ${rv.rq_count}건은 시트 구성 추천과 섹션 작성에 그대로 쓰여요.` : null);

  const dock = (
    <Dock testId="pr1f-dock" title="RFP에서 채운 고객 · 프로젝트 정보" meta="1 / 6"
      right={done || fields.length ? (
        <span className="pr-row" style={{ gap: 6 }} data-testid="pr1f-tally">
          {(['found', 'guess', 'empty'] as const).map((k) => <span key={k} className={cx('pr-tally', `pr-tally--${k}`)}>{STATE_LABEL[k]} <b className="pr-num">{tally[k] ?? 0}</b></span>)}
        </span>
      ) : null}
      hint={<span data-testid="pr1f-hint">{rqHint ?? (done ? '' : 'PDF · DOCX · PPTX · TXT · 파일당 50MB')}</span>}
      foot={<>
        <button type="button" className="pr-btn" onClick={() => void goManual()} data-testid="pr1f-manual">직접 입력으로</button>
        <NextButton onClick={() => void goNext()} busy={busy === 'confirm'} disabled={!done} disabledReason={running ? 'RFP를 읽는 중이에요' : '먼저 RFP 파일을 올려 주세요'} testId="pr1f-next">확인 · 다음: 제안서 유형</NextButton>
      </>}>
      {done && empty.length > 0 && (
        <div className="pr-grid2" data-testid="pr1f-empty">
          {empty.map((f) => (
            <div key={f.key} className="pr-field">
              <label htmlFor={`pr1f-in-${f.key}`}>{NUM[f.no - 1]} {EMPTY_LABEL[f.key] ?? f.label} <span className="pr-subtle">· 원문에 없음</span></label>
              <input id={`pr1f-in-${f.key}`} className="pr-input pr-input--white pr-input--dashed" placeholder={EMPTY_PH[f.key] ?? '원문에 없음 · 직접 입력'}
                value={drafts[f.key] ?? (f.edited ? f.value ?? '' : '')}
                onChange={(e) => { const v = e.target.value; setDrafts((d) => ({ ...d, [f.key]: v })); pending.current[f.key] = v; }}
                onBlur={(e) => { if (pending.current[f.key] !== undefined) void saveField(f.key, e.target.value); }} />
            </div>
          ))}
        </div>
      )}
    </Dock>
  );

  return (
    <PrPage testId="pr1f" dock={dock} gap={14} tight>
      <Agent text={intro} testId="pr1f-agent">
        <input ref={fileRef} type="file" hidden accept=".pdf,.docx,.pptx,.txt" onChange={(e) => { void upload(Array.from(e.target.files ?? []), false); e.target.value = ''; }} data-testid="pr1f-file-input" />
        <input ref={noteRef} type="file" hidden accept=".txt,.docx,.pdf,.eml" onChange={(e) => { void upload(Array.from(e.target.files ?? []), true); e.target.value = ''; }} data-testid="pr1f-note-input" />
        {!file && !running ? (
          <div data-testid="pr1f-drop">
            <Dropzone onFiles={(fs) => void upload(fs, false)} accept=".pdf,.docx,.pptx,.txt" multiple={false} disabled={!!busy}
              title={busy === 'file' ? '올리는 중…' : 'RFP 파일을 끌어다 놓거나 고르세요'} hint="PDF · DOCX · PPTX · TXT · 파일당 50MB" />
          </div>
        ) : (
          <div className="pr-rfp-file" data-testid="pr1f-file">
            <span className="pr-iconbox"><Icon name="file" size={16} color="var(--wm-brand)" /></span>
            <span className="pr-colflex pr-grow" style={{ gap: 1 }}>
              <span className="pr-ell" style={{ fontSize: 13.5, fontWeight: 600 }}>{file?.name ?? '올린 파일'}</span>
              <span className="pr-note">
                {[file?.kind_label, file?.pages ? `${file.pages}쪽` : null, job ? '방금 올림' : null].filter(Boolean).join(' · ')}
                {rv?.extra_files?.length ? ` · 회의록 ${rv.extra_files.length}개` : ''}
              </span>
            </span>
            <span className="pr-row" style={{ gap: 4 }} data-testid="pr1f-phases">
              {phases.map((ph) => (
                <span key={ph.key} className={cx('pr-phasechip', ph.status === 'done' && 'pr-phasechip--done', ph.status === 'busy' && 'pr-phasechip--busy')}>
                  {ph.status === 'done' ? <StateIcon d="M5 12l5 5L20 7" /> : ph.status === 'busy' ? <SpinIcon size={10} color="currentColor" /> : null}{ph.label}
                </span>
              ))}
            </span>
            <span className="pr-vdiv" />
            <button type="button" className="pr-mini" style={{ height: 30 }} disabled={running || failed || !!busy} onClick={() => noteRef.current?.click()} data-testid="pr1f-add-note">
              {busy === 'extra' ? <SpinIcon size={12} /> : null}회의록 추가</button>
            <button type="button" className="pr-link" style={{ fontSize: 12, padding: '0 8px', height: 30 }} disabled={running || !!busy} onClick={() => fileRef.current?.click()} data-testid="pr1f-other">
              {busy === 'file' ? <SpinIcon size={12} /> : null}다른 파일</button>
          </div>
        )}
        {failed && <ErrorBand message={jobErrText(rv?.error as { code?: string; message?: string } | null, '파일을 읽지 못했어요. 다른 파일을 올려 주세요.')} testId="pr1f-error" />}
        {(running || done) && (
          <div className="pr-rfp-grid" data-testid="pr1f-grid">
            <div className="pr-rfp-src">
              <div className="pr-rfp-head"><b>원문</b><span className="pr-muted">찾은 곳 {rv?.found_count ?? fields.filter((f) => f.state !== 'empty').length}</span></div>
              <div className="pr-rfp-pages" data-testid="pr1f-source">
                {running && !rv?.excerpts?.length ? [0, 1, 2].map((i) => <span key={i} className="pr-skel" style={{ height: 44 }} />) : (rv?.excerpts ?? []).map((ex, i) => (
                  <div key={`${ex.page_label}-${i}`} className="pr-colflex" style={{ gap: 4 }}>
                    <span className="pr-rfp-page">{ex.page_label}</span>
                    <div className="pr-rfp-text">
                      {ex.parts.map((pt, j) => pt.field_no ? (
                        <span key={j} id={`pr1f-ex-${pt.field_no}`} className={cx('pr-rfp-hl', focusNo === pt.field_no && 'pr-rfp-hl--on')}>
                          <span className="pr-rfp-no">{NUM[pt.field_no - 1]}</span>{pt.text}
                        </span>
                      ) : <span key={j}>{pt.text}</span>)}
                    </div>
                  </div>
                ))}
              </div>
            </div>
            <div className="pr-colflex" style={{ gap: 0, minWidth: 0 }}>
              <div className="pr-rfp-head"><b>자동으로 채운 항목</b><span className="pr-muted">누르면 원문 위치로 이동</span></div>
              <div className="pr-rfp-fields" data-testid="pr1f-fields">
                {running && !fields.length ? Array.from({ length: 9 }, (_, i) => <span key={i} className="pr-skel" style={{ height: 24, margin: '4px 6px' }} />)
                  : fields.map((f) => <FieldRow key={f.key} f={f} on={focusNo === f.no} editing={editing === f.key}
                    onJump={() => jump(f.no)} onEdit={() => setEditing(f.key)} onCancel={() => setEditing(null)}
                    onSave={(v) => { setEditing(null); if (v !== (f.value ?? '')) void saveField(f.key, v); }} />)}
              </div>
            </div>
          </div>
        )}
        {done && fields.length === 0 && <div className="pr-band pr-band--muted">원문에서 채울 항목을 찾지 못했어요. 「직접 입력으로」 넘어가 주세요.</div>}
      </Agent>
    </PrPage>
  );
}

function FieldRow({ f, on, editing, onJump, onEdit, onSave, onCancel }:
  { f: RfpField; on: boolean; editing: boolean; onJump: () => void; onEdit: () => void; onSave: (v: string) => void; onCancel: () => void }) {
  const [v, setV] = useState(f.value ?? '');
  useEffect(() => { if (editing) setV(f.value ?? ''); }, [editing, f.value]);
  const isEmpty = f.state === 'empty' && !f.edited;
  return (
    <div className={cx('pr-rfp-row', on && 'pr-rfp-row--on')} data-testid="pr1f-field" data-key={f.key} data-state={f.state}>
      <button type="button" className={cx('pr-rfp-rowno', isEmpty && 'pr-subtle')} onClick={onJump} aria-label={`${f.label} 원문 위치로`}>{NUM[f.no - 1]}</button>
      <button type="button" className="pr-rfp-rowlabel" onClick={onJump}>{f.label}</button>
      {editing ? (
        <input className="pr-rfp-edit" autoFocus value={v} aria-label={`${f.label} 고치기`} onChange={(e) => setV(e.target.value)}
          onBlur={() => onSave(v)} onKeyDown={(e) => { if (e.key === 'Enter') onSave(v); if (e.key === 'Escape') onCancel(); }} />
      ) : (
        <button type="button" className={cx('pr-rfp-val', isEmpty && 'pr-rfp-val--empty')} onClick={onEdit} title="눌러서 고치기" data-testid="pr1f-value">
          {isEmpty ? '원문에 없음' : f.value}{f.edited && <span className="pr-subtle" style={{ fontWeight: 500, fontSize: 11 }}> · 고침</span>}
        </button>
      )}
      <span className="pr-rfp-srcno pr-num">{f.source_label || f.source?.page_label || '—'}</span>
      <span className={STATE_CLS[f.state]}><StateIcon d={STATE_ICON[f.state]} />{f.state_label || STATE_LABEL[f.state]}</span>
    </div>
  );
}

