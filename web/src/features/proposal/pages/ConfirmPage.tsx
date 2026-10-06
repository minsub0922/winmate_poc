/**
 * PR7Q — 확정 필요 목록(§4.21, 보드 PR7Q) — `/proposal/:id/confirm`(`?export=1`).
 * 머리(확정 필요 t곳 · c곳 확정 · o곳 남음 · 진행 막대 · 보기 라디오) · 항목 행(시트 번호 · 문장 · 부제 · 태그 · 바로가기 · 고치기/접기)
 * 펼친 고치기: 문장 틀 + 입력 · 식 · 같이 바뀌는 시트 · 근거 붙이기 · 고객에게 물을 문장 복사 · 모르면 노트로 옮기기 · 섹션 열기 · 확정.
 * 아래 카드: 남은 수치 W가 다시 찾기(research 잡 → 후보) · 남은 곳 노트로 옮기기 · 요청 · 미리보기 · 검토 요청 · 내보내기.
 */
import { useMemo, useRef, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { uploadFile } from '@/api/client';
import { Icon, cx, toast, useConfirm } from '@/ui';
import {
  anonymizeConfirm, evidenceConfirm, moveAllToNote, moveConfirmToNote, qk, questionConfirm, researchConfirm, resolveConfirm, useConfirmItems, useProposal,
} from '../api/proposal';
import { errText, jobErrText } from '../api/http';
import { useJobEvents } from '../api/jobs';
import type { ConfirmItem } from '../api/types';
import { Agent, Dock, ErrorBand, GhostButton, LoadingCard, MarkText, Prompt, PrPage, SpinIcon } from '../components/parts';
import { useExportParam } from '../components/ResultToolbar';
import { R, normalizeRoute } from '../lib/routes';
import { useProposalShell } from '../lib/useProposalShell';
import { ExportModal } from './ExportModal';

type View = 'open' | 'confirmed' | 'all';

export function ConfirmPage() {
  const { id } = useParams();
  const qc = useQueryClient();
  const pq = useProposal(id);
  const p = pq.data;
  const cq = useConfirmItems(id, 'all');
  const cl = cq.data;
  const [view, setView] = useState<View>('open');
  const [openId, setOpenId] = useState<string | null>(null);
  const [showDone, setShowDone] = useState(false);
  const [job, setJob] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const { confirm, dialog } = useConfirm();
  const ex = useExportParam();
  useProposalShell({ p, step: 6 });
  const refresh = () => { if (id) { void qc.invalidateQueries({ queryKey: qk.sub(id, 'confirm') }); void qc.invalidateQueries({ queryKey: qk.p(id) }); void qc.invalidateQueries({ queryKey: qk.sub(id, 'slides') }); } };
  const ev = useJobEvents(job, { onDone: (j) => { setJob(null); if (j.status === 'failed') toast(jobErrText(j.error)); else toast('후보 값을 붙여 두었어요 · 확인하고 확정해 주세요'); refresh(); } });

  const items = cl?.items ?? [];
  const open = items.filter((i) => i.status === 'open');
  const closed = items.filter((i) => i.status !== 'open');
  const counts = { open: cl?.counts?.open ?? open.length, confirmed: cl?.counts?.confirmed ?? closed.length, total: cl?.counts?.total ?? items.length };
  const shown = view === 'open' ? open : view === 'confirmed' ? closed : items;

  const run = async (tag: string, fn: () => Promise<unknown>, ok?: string) => {
    setBusy(tag);
    try { await fn(); if (ok) toast(ok); refresh(); return true; } catch (e) { toast(errText(e)); return false; } finally { setBusy(null); }
  };
  const research = async (instruction?: string) => {
    if (!id) return;
    setBusy('research');
    try { const r = await researchConfirm(id, instruction, open.map((i) => i.id)); setJob(r.job_id); toast('남은 수치를 다시 찾는 중이에요'); }
    catch (e) { toast(errText(e)); } finally { setBusy(null); }
  };
  const allToNote = async () => {
    if (!id || !open.length) return;
    const ok = await confirm({ title: `남은 ${open.length}곳을 노트로 옮길까요?`, message: '슬라이드에서는 값 대신 「—」로 두고, 문장은 발표자 노트에 [확정 필요]로 남겨요.', confirmLabel: '노트로 옮기기', tone: 'dark' });
    if (ok) await run('allnote', () => moveAllToNote(id, open.map((i) => i.id)), '남은 곳을 노트로 옮겼어요');
  };

  if (pq.isError) return <PrPage><ErrorBand message={errText(pq.error, '제안서를 찾을 수 없어요')} onRetry={() => void pq.refetch()} /></PrPage>;
  if (!p || !id) return <PrPage><LoadingCard /></PrPage>;

  const pct = counts.total ? Math.round((counts.confirmed / counts.total) * 100) : 0;
  const intro = cl?.intro || `제안서 ${cl?.sheets_total ?? p.sheets?.length ?? 0}시트에서 사실 확인이 필요한 곳 ${counts.total}곳을 모았어요. 값을 넣거나 근거를 붙이면 그 값이 쓰인 시트에 모두 반영되고, 확정하지 않은 곳은 내보낼 때 표시를 남길 수 있어요.`;

  const dock = (
    <Dock testId="pr7q-dock" title="확정 필요" meta={cl?.footer_label?.replace(/^확정 필요 · /, '') || `${counts.open}곳 남음 · 확정한 값은 버전 기록에 남아요`}
      right={<>
        <button type="button" className="pr-quick" disabled={!open.length || !!job || busy === 'research'} onClick={() => void research()} data-testid="pr7q-research">
          {job ? <><SpinIcon size={11} /> 찾는 중 {Math.round(ev.progress)}%</> : '남은 수치 W가 다시 찾기'}</button>
        <button type="button" className="pr-quick" disabled={!open.length || !!busy} onClick={() => void allToNote()} data-testid="pr7q-allnote">남은 곳 노트로 옮기기</button>
      </>}>
      <div className="pr-row" style={{ gap: 10, paddingBottom: 14 }}>
        <Prompt placeholder="요청 (예: 경쟁사 수치는 MI 작업에서 다시 찾아줘)" label="요청" onSend={(t) => research(t)} busy={!!job} testId="pr7q-request" />
        <GhostButton to={R.preview(id)}>미리보기</GhostButton>
        <GhostButton to={R.review(id)}>검토 요청</GhostButton>
        <button type="button" className="pr-btn pr-btn--primary" onClick={() => ex.openExport()} data-testid="pr7q-export"><Icon name="download" size={15} strokeWidth={2.2} />내보내기</button>
      </div>
    </Dock>
  );

  return (
    <PrPage testId="pr7q" dock={dock} gap={14} tight>
      <Agent text={intro} testId="pr7q-agent">
        {cq.isError ? <ErrorBand message={errText(cq.error)} onRetry={() => void cq.refetch()} /> : !cl ? <LoadingCard lines={5} /> : (
          <div className="pr-card" style={{ overflow: 'hidden' }} data-testid="pr7q-list">
            <div className="pr-cfhead">
              <b style={{ fontSize: 13.5, whiteSpace: 'nowrap' }} data-testid="pr7q-header">{cl.header_label || `확정 필요 ${counts.total}곳`}</b>
              <span className="pr-note" style={{ whiteSpace: 'nowrap' }}>{cl.progress_label || `${counts.confirmed}곳 확정 · ${counts.open}곳 남음`}</span>
              <span className="pr-cfbar" role="progressbar" aria-label={`확정 진행률 ${counts.confirmed} / ${counts.total}`} aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}><span style={{ width: `${pct}%` }} /></span>
              <span className="pr-grow" />
              <div role="radiogroup" aria-label="보기" className="pr-miniseg pr-miniseg--tabs">
                {([['open', `남은 곳 ${counts.open}`], ['confirmed', `확정 ${counts.confirmed}`], ['all', `전체 ${counts.total}`]] as const).map(([k, l]) => (
                  <button key={k} type="button" role="radio" aria-checked={view === k} onClick={() => setView(k)} data-testid={`pr7q-view-${k}`}>{l}</button>
                ))}
              </div>
            </div>
            {shown.length === 0 && <div className="pr-empty" data-testid="pr7q-empty">{view === 'open' ? '확정이 필요한 곳이 없어요. 바로 내보내도 돼요.' : '아직 확정한 곳이 없어요'}</div>}
            {shown.map((it) => (
              <ItemRow key={it.id} id={id} it={it} open={openId === it.id} onToggle={() => setOpenId((o) => (o === it.id ? null : it.id))} busy={busy} run={run} />
            ))}
            {view === 'open' && closed.length > 0 && (
              <div className="pr-cfdone" data-testid="pr7q-done">
                <span className="pr-cficon pr-cficon--ok"><Icon name="check" size={11} strokeWidth={3} /></span>
                <b style={{ fontSize: 12.5, whiteSpace: 'nowrap' }}>확정한 곳 {closed.length}</b>
                <span className="pr-ell pr-grow pr-note">{cl.confirmed_summary || closed.map((c) => `${c.sheet_no_label ?? ''} ${c.where ?? c.text.mark}`.trim()).join(' · ')}</span>
                <button type="button" className="pr-link" onClick={() => setShowDone((s) => !s)}>{showDone ? '접기' : '펼치기'}</button>
              </div>
            )}
            {view === 'open' && showDone && closed.map((it) => <ItemRow key={it.id} id={id} it={it} open={false} onToggle={() => undefined} busy={busy} run={run} />)}
          </div>
        )}
      </Agent>
      {dialog}
      {ex.open && <ExportModal proposalId={id} open onClose={ex.closeExport} initialLang={ex.lang} version={ex.version} />}
    </PrPage>
  );
}

function ItemRow({ id, it, open, onToggle, busy, run }:
  { id: string; it: ConfirmItem; open: boolean; onToggle: () => void; busy: string | null; run: (tag: string, fn: () => Promise<unknown>, ok?: string) => Promise<boolean> }) {
  const nav = useNavigate();
  const done = it.status !== 'open';
  const parts = it.fix?.sentence ?? [];
  const inputs = parts.filter((x) => x.input);
  const [vals, setVals] = useState<Record<string, string>>(() => Object.fromEntries(inputs.map((x) => [x.input!, x.value ?? ''])));
  const [single, setSingle] = useState('');
  const [evOpen, setEvOpen] = useState(false);
  const firstInput = useRef<HTMLInputElement>(null);
  const act = it.action;
  const actTarget = act?.target;
  const doAction = async () => {
    if (!act) return;
    if (actTarget?.op === 'anonymize') { await run(`anon:${it.id}`, () => anonymizeConfirm(id, it.id), '익명으로 바꿨어요'); return; }
    if (actTarget?.route) nav(normalizeRoute(actTarget.route)!);
  };
  const resolve = async () => {
    const body = inputs.length ? { values: vals } : single.trim() ? { value: single.trim() } : {};
    await run(`res:${it.id}`, () => resolveConfirm(id, it.id, body), '확정했어요 · 이 값을 쓰는 시트에 모두 반영했어요');
  };
  const copyQuestion = async () => {
    await run(`q:${it.id}`, async () => {
      const r = await questionConfirm(id, it.id);
      const q = r.text ?? '';
      if (q) { try { await navigator.clipboard.writeText(q); } catch { /* 권한이 없으면 문장만 보여 준다 */ } }
      toast(q ? `문장을 복사했어요 · 「${q}」` : '고객에게 물을 것에 추가했어요');
    });
  };
  const candidates = it.candidates ?? [];
  return (
    <div className={cx('pr-cfrow', open && 'pr-cfrow--open', done && 'pr-cfrow--done')} data-testid="pr7q-item" data-status={it.status}>
      <div className="pr-cfrow__main">
        <span className={cx('pr-cficon', done && 'pr-cficon--ok')}>{done ? <Icon name="check" size={11} strokeWidth={3} /> : <Icon name="info" size={13} strokeWidth={2.4} />}</span>
        <span className="pr-cfno pr-num">{it.sheet_no_label ?? (it.sheet_no ? String(it.sheet_no).padStart(2, '0') : '—')}</span>
        <span className="pr-colflex pr-grow" style={{ gap: 1 }}>
          <span className="pr-cftext"><MarkText t={it.text} cls="pr-ph" /></span>
          <span className="pr-ell" style={{ fontSize: 11.5, color: 'var(--wm-text-muted)' }}>{it.sub}{done && it.status_label ? ` · ${it.status_label}` : ''}</span>
        </span>
        {candidates.length > 0 && !done && <span className="pr-badge pr-badge--soft">후보 {candidates.length}</span>}
        <span className="pr-cftag">{it.tag}</span>
        {!done && act && <button type="button" className="pr-mini" onClick={() => void doAction()} disabled={busy === `anon:${it.id}`}>{act.label}</button>}
        {!done && <button type="button" className={cx('pr-mini', open ? 'pr-cfbtn--fold' : 'pr-mini--primary')} onClick={() => { onToggle(); window.setTimeout(() => firstInput.current?.focus(), 30); }} aria-expanded={open} data-testid="pr7q-fix">{open ? '접기' : '고치기'}</button>}
      </div>
      {open && !done && (
        <div className="pr-cfrow__fix">
          <div className="pr-cfsentence">
            {parts.length ? parts.map((x, i) => x.input ? (
              <input key={i} ref={i === parts.findIndex((y) => y.input) ? firstInput : undefined} className="pr-cfinput" placeholder={x.label ?? '값'} aria-label={x.label ?? '값'}
                value={vals[x.input] ?? ''} onChange={(e) => setVals((v) => ({ ...v, [x.input!]: e.target.value }))} onKeyDown={(e) => { if (e.key === 'Enter') void resolve(); }} />
            ) : <span key={i}>{x.text}</span>) : (
              <>
                <span><MarkText t={it.text} cls="pr-ph" /></span>
                <input ref={firstInput} className="pr-cfinput" placeholder="확정할 값 (비우면 지금 문장 그대로)" aria-label="확정할 값" value={single} onChange={(e) => setSingle(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') void resolve(); }} />
              </>
            )}
            <span className="pr-grow" />
            {it.fix?.formula && <span className="pr-cfformula">{it.fix.formula}</span>}
          </div>
          {candidates.length > 0 && (
            <div className="pr-row pr-row--wrap" style={{ gap: 6 }}>
              <span className="pr-note">{it.candidates_label || '후보'}</span>
              {candidates.map((c, i) => (
                <button key={i} type="button" className="pr-quick" onClick={() => { if (inputs[0]?.input) setVals((v) => ({ ...v, [inputs[0].input!]: c.value })); else setSingle(c.value); }}
                  title={typeof c.source === 'object' && c.source ? String((c.source as Record<string, unknown>).label ?? (c.source as Record<string, unknown>).url ?? '') : undefined}>{c.value}</button>
              ))}
            </div>
          )}
          {!!it.fix?.linked_sheets?.length && (
            <div className="pr-row pr-row--wrap" style={{ gap: 6 }}>
              <span className="pr-note">같이 바뀌는 시트</span>
              {it.fix.linked_sheets.map((s) => <Link key={s.sheet_id} to={R.preview(id, s.sheet_no)} className="pr-linkchip"><b className="pr-num">{String(s.sheet_no).padStart(2, '0')}</b> {s.name}</Link>)}
            </div>
          )}
          <div className="pr-row pr-row--wrap" style={{ gap: 6 }}>
            <button type="button" className="pr-mini" style={{ height: 32 }} onClick={() => setEvOpen((o) => !o)} aria-expanded={evOpen}><Icon name="link" size={13} />근거 붙이기</button>
            <button type="button" className="pr-mini" style={{ height: 32 }} onClick={() => void copyQuestion()} disabled={busy === `q:${it.id}`}>고객에게 물을 문장 복사</button>
            <button type="button" className="pr-mini" style={{ height: 32 }} onClick={() => void run(`note:${it.id}`, () => moveConfirmToNote(id, it.id), '노트로 옮겼어요')}>모르면 노트로 옮기기</button>
            <span className="pr-grow" />
            {it.route && <Link to={normalizeRoute(it.route)!} className="pr-link" style={{ fontSize: 12.5 }}>섹션 열기</Link>}
            <button type="button" className="pr-mini pr-mini--primary" style={{ height: 32, padding: '0 16px' }} onClick={() => void resolve()} disabled={busy === `res:${it.id}`} data-testid="pr7q-resolve">
              {busy === `res:${it.id}` ? <SpinIcon size={12} color="currentColor" /> : null}확정</button>
          </div>
          {evOpen && <EvidenceForm id={id} itemId={it.id} onDone={() => setEvOpen(false)} run={run} />}
        </div>
      )}
    </div>
  );
}

/** 근거 붙이기(제안: URL · 파일 · Winmate 작업 · 사내 자료 메모) */
function EvidenceForm({ id, itemId, onDone, run }: { id: string; itemId: string; onDone: () => void; run: (tag: string, fn: () => Promise<unknown>, ok?: string) => Promise<boolean> }) {
  const [kind, setKind] = useState<'url' | 'file' | 'internal_doc'>('url');
  const [ref, setRef] = useState('');
  const [note, setNote] = useState('');
  const fileRef = useRef<HTMLInputElement>(null);
  const valid = useMemo(() => (kind === 'url' ? /^https?:\/\/\S+$/.test(ref.trim()) : kind === 'file' ? !!ref : note.trim().length > 0), [kind, ref, note]);
  const save = async () => {
    const ok = await run(`ev:${itemId}`, () => evidenceConfirm(id, itemId, { kind, ref: ref.trim() || null, note: note.trim() || null }), '근거를 붙였어요');
    if (ok) onDone();
  };
  return (
    <div className="pr-evform" data-testid="pr7q-evidence">
      <div role="radiogroup" aria-label="근거 종류" className="pr-miniseg pr-miniseg--tabs" style={{ alignSelf: 'flex-start' }}>
        {([['url', '링크'], ['file', '파일'], ['internal_doc', '사내 자료']] as const).map(([k, l]) => <button key={k} type="button" role="radio" aria-checked={kind === k} onClick={() => { setKind(k); setRef(''); }}>{l}</button>)}
      </div>
      {kind === 'url' && <input className="pr-input pr-input--white" placeholder="https://" value={ref} onChange={(e) => setRef(e.target.value)} aria-label="근거 링크" />}
      {kind === 'file' && (
        <div className="pr-row" style={{ gap: 8 }}>
          <input ref={fileRef} type="file" hidden onChange={async (e) => { const f = e.target.files?.[0]; e.target.value = ''; if (!f) return; try { const up = await uploadFile(f, { purpose: 'proposal_evidence' }); setRef(up.id); setNote((n) => n || f.name); } catch (er) { toast(errText(er)); } }} />
          <button type="button" className="pr-mini" onClick={() => fileRef.current?.click()}><Icon name="upload" size={13} />파일 고르기</button>
          <span className="pr-note pr-ell">{ref ? note || '올렸어요' : 'PDF · 이미지 · 문서'}</span>
        </div>
      )}
      <input className="pr-input pr-input--white" placeholder={kind === 'internal_doc' ? '어떤 사내 자료인지 (예: 2025 영업 실적 보고서 p.4)' : '메모 (선택)'} value={note} onChange={(e) => setNote(e.target.value)} aria-label="근거 메모" />
      <div className="pr-row" style={{ justifyContent: 'flex-end', gap: 6 }}>
        <button type="button" className="pr-mini" onClick={onDone}>취소</button>
        <button type="button" className="pr-mini pr-mini--primary" disabled={!valid} onClick={() => void save()}>근거 저장</button>
      </div>
    </div>
  );
}
