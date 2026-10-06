/**
 * PR7 — PPTX 생성 결과(§4.19, 보드 PR7, 6/6) + PR7X(`?export=1` 모달, `&lang=en` · `&version=n`).
 * 생성 중이면 같은 화면에 진행 카드(조립 · 넘침 맞춤 · 노트 · 렌더), 실패면 오류 + 「다시 생성」.
 */
import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { Icon, toast } from '@/ui';
import { generate, generateNotes, proposalRequest, qk, useProposal, useResult } from '../api/proposal';
import { errText, jobErrText } from '../api/http';
import { useJobEvents } from '../api/jobs';
import { Agent, Bar, Dock, ErrorBand, GhostButton, LoadingCard, Prompt, SpinIcon } from '../components/parts';
import { SlideThumb } from '../components/SlideThumb';
import { R, normalizeRoute } from '../lib/routes';
import { useProposalShell } from '../lib/useProposalShell';
import { useQuickExport } from '../lib/useQuickExport';
import { ExportModal } from './ExportModal';

const GEN_STEPS = [['assemble', '조립'], ['fit', '넘침 맞춤'], ['notes', '노트'], ['render', '렌더']] as const;

export function ResultPage() {
  const { id } = useParams();
  const [sp, setSp] = useSearchParams();
  const nav = useNavigate();
  const qc = useQueryClient();
  const pq = useProposal(id);
  const p = pq.data;
  const rq = useResult(id);
  const rv = rq.data;
  const [job, setJob] = useState<string | null>(null);
  const activeJob = job ?? (rv?.status === 'running' ? rv.job_id ?? null : null);
  const ev = useJobEvents(activeJob, { onDone: (j) => { setJob(null); if (j.status === 'failed') toast(jobErrText(j.error)); void rq.refetch(); if (id) void qc.invalidateQueries({ queryKey: qk.p(id) }); } });
  const [reqBusy, setReqBusy] = useState(false);
  const qe = useQuickExport(id);
  useProposalShell({ p, step: 6 });
  useEffect(() => { if (rv?.status !== 'running') return; const t = window.setInterval(() => void rq.refetch(), 3000); return () => window.clearInterval(t); }, [rv?.status, rq]);
  // 파생 제안서(기존 제안서 활용)의 결과 자리는 PRU5
  useEffect(() => { if (rv?.derived && rv.status === 'done' && rv.summary_route && !sp.get('export')) nav(normalizeRoute(rv.summary_route)!, { replace: true }); }, [rv, nav, sp]);

  const exportOpen = sp.get('export') === '1';
  const openExport = (lang?: string) => setSp((cur) => { const x = new URLSearchParams(cur); x.set('export', '1'); if (lang) x.set('lang', lang); return x; });
  const closeExport = () => setSp((cur) => { const x = new URLSearchParams(cur); x.delete('export'); x.delete('lang'); x.delete('version'); return x; });

  if (pq.isError) return <div className="pr-page"><div className="pr-scroll"><ErrorBand message={errText(pq.error, '제안서를 찾을 수 없어요')} onRetry={() => void pq.refetch()} /></div></div>;
  if (!p) return <div className="pr-page"><div className="pr-scroll"><div className="pr-col"><LoadingCard /></div></div></div>;

  const running = !!activeJob;
  const file = rv?.file;
  const thumbs = (rv?.thumbs ?? []).slice(0, 10);
  const regen = rv?.regen_section;
  const quick = async (k: 'regen' | 'notes') => {
    try {
      const r = k === 'regen' ? await generate(p.id, { scope: 'section', section_key: rv?.regen_section_key ?? null }) : await generateNotes(p.id);
      setJob(r.job_id);
      if (k === 'notes') toast('발표자 노트를 쓰는 중이에요');
    } catch (e) { toast(errText(e)); }
  };
  const sendRequest = async (text: string) => {
    setReqBusy(true);
    try { const r = await proposalRequest(p.id, text); setJob(r.job_id); toast('수정 요청을 반영하는 중이에요'); } catch (e) { toast(errText(e)); } finally { setReqBusy(false); }
  };
  const sheetRoute = (sheetId?: string | null, no?: number) => {
    const s = sheetId ? p.sheets?.find((x) => x.id === sheetId) : null;
    return R.preview(p.id, s?.sheet_no ?? (no ? undefined : undefined));
  };

  const dock = (
    <Dock testId="pr7-dock" title={<>PPTX 생성 <span className="pr-muted" style={{ fontWeight: 500 }}>· {rv?.footer_label?.replace(/^PPTX 생성 · /, '') || '6 / 6 · 완료'}</span></>}
      right={<>
        {regen && <button type="button" className="pr-quick" disabled={running} onClick={() => void quick('regen')} data-testid="pr7-regen">{regen.label}</button>}
        <button type="button" className="pr-quick" disabled={running} onClick={() => void quick('notes')}>발표자 노트 추가</button>
        <button type="button" className="pr-quick" onClick={() => openExport('en')}>영문 버전</button>
      </>}>
      <div className="pr-row" style={{ gap: 10, paddingBottom: 14 }}>
        <Prompt placeholder="수정 요청 (예: 18번 Why Samsung 비교표에 유지보수 항목 추가)" label="수정 요청" onSend={sendRequest} busy={reqBusy || running} testId="pr7-request" />
        <GhostButton to={R.design(p.id)}>이전</GhostButton>
        <GhostButton to={R.review(p.id)} icon={<Icon name="link" size={15} />} testId="pr7-share">팀에 공유</GhostButton>
        <button type="button" className="pr-btn pr-btn--primary" disabled={!file || !!qe.busy} onClick={() => void qe.run('pptx', file?.pptx_url, file?.name)} data-testid="pr7-download">
          {qe.busy === 'pptx' ? <SpinIcon color="currentColor" /> : <Icon name="download" size={15} strokeWidth={2.2} />}PPTX 다운로드
        </button>
      </div>
    </Dock>
  );

  return (
    <div className="pr-page" data-testid="pr7">
      <div className="pr-scroll">
        <div className="pr-col" style={{ gap: 14 }}>
          {rq.isError && <ErrorBand message={errText(rq.error)} onRetry={() => void rq.refetch()} />}
          {running || rv?.status === 'running' ? (
            <Agent text="PPTX를 만들고 있어요. 다른 작업을 해도 돼요, 끝나면 알려드릴게요.">
              <div className="pr-progress-card" data-testid="pr7-progress">
                <div className="pr-row pr-row--between"><b style={{ fontSize: 14 }}>PPTX 만드는 중</b><span className="pr-num" style={{ fontWeight: 700 }}>{Math.round(ev.progress)}%</span></div>
                <Bar value={ev.progress} label="생성 진행률" />
                <div className="pr-row pr-row--wrap" style={{ gap: 6 }}>
                  {GEN_STEPS.map(([k, l]) => {
                    const st = ev.steps.get(k)?.status;
                    return <span key={k} className={st === 'done' ? 'pr-phase pr-phase--done' : st === 'running' ? 'pr-phase pr-phase--busy' : 'pr-phase'}>{st === 'done' && <Icon name="check" size={11} strokeWidth={3} />}{st === 'running' && <SpinIcon size={11} />}{l}</span>;
                  })}
                </div>
              </div>
            </Agent>
          ) : rv?.status === 'failed' ? (
            <Agent text="PPTX를 만들지 못했어요.">
              <ErrorBand message={jobErrText(rv.error as { code?: string; message?: string } | null)} onRetry={() => { void generate(p.id, { scope: 'all' }).then((r) => setJob(r.job_id)).catch((e) => toast(errText(e))); }} />
            </Agent>
          ) : rv?.status === 'none' ? (
            <Agent text="아직 PPTX를 만들지 않았어요. 디자인 템플릿을 고른 뒤 「PPTX 생성」을 눌러 주세요.">
              <div><Link to={R.design(p.id)} className="pr-btn pr-btn--primary">디자인 템플릿으로</Link></div>
            </Agent>
          ) : !rv ? <LoadingCard lines={4} /> : (
            <Agent testId="pr7-agent" text={rv.message}>
              {file && (
                <div className="pr-filecard" data-testid="pr7-file">
                  <div className="pr-filecard__head">
                    <span className="pr-filecard__icon"><Icon name="file" size={16} /></span>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 2, flex: 1, minWidth: 0 }}>
                      <span className="pr-filecard__name">{file.name}</span>
                      <span className="pr-filecard__meta" data-testid="pr7-file-meta">{file.meta || `${file.slides} 슬라이드 · ${file.type_label} ${file.sections}섹션 · ${file.created_label ?? '방금 생성'} · 노트 ${file.notes_count}건`}</span>
                    </div>
                    <button type="button" className="pr-btn pr-btn--h38" style={{ height: 34 }} disabled={!!qe.busy} onClick={() => void qe.run('pdf', file.pdf_url, file.name.replace(/\.pptx$/, '.pdf'))}>
                      {qe.busy === 'pdf' ? <SpinIcon /> : null}PDF</button>
                    <button type="button" className="pr-btn pr-btn--h38 pr-btn--primary" style={{ height: 34, fontSize: 13 }} onClick={() => openExport()} data-testid="pr7-export">
                      <Icon name="download" size={14} strokeWidth={2.2} />PPTX 다운로드</button>
                  </div>
                  <div className="pr-filecard__body">
                    <div className="pr-thumbs" data-testid="pr7-thumbs">
                      {thumbs.map((t) => (
                        <Link key={t.slide_no} to={t.sheet_id ? sheetRoute(t.sheet_id) : R.preview(p.id)} className="pr-thumbcell" title={t.label}>
                          <SlideThumb url={t.thumb_url} label={t.label} kind={t.kind} inferred={t.inferred} />
                          <span className="pr-ell"><span className="pr-num">{String(t.slide_no).padStart(2, '0')}</span> {t.label.replace(/^\d{1,3}\s+/, '')}</span>
                        </Link>
                      ))}
                    </div>
                    <div className="pr-ranges">
                      <span className="pr-grow" data-testid="pr7-ranges">
                        {(rv.ranges ?? []).map((r, i) => (
                          <span key={`${r.from}-${r.to}`}>{i > 0 && ' · '}{r.from === r.to ? r.from : `${r.from}–${r.to}`} {r.label}{r.flag && <> <span className="pr-mark">{r.flag}</span></>}</span>
                        ))}
                        {!rv.ranges?.length && rv.ranges_label}
                      </span>
                      <Link to={R.preview(p.id)} className="pr-btn pr-btn--sm" style={{ height: 28, fontSize: 12 }}>전체 슬라이드 보기</Link>
                    </div>
                  </div>
                </div>
              )}
            </Agent>
          )}
          {qe.busy && <div className="pr-band pr-band--muted"><SpinIcon /> <span className="pr-grow">{qe.busy.toUpperCase()} 파일을 만드는 중이에요 · {Math.round(qe.progress)}%</span></div>}
        </div>
      </div>
      {dock}
      {exportOpen && <ExportModal proposalId={p.id} open onClose={closeExport} initialLang={(sp.get('lang') as 'ko' | 'en' | 'ko_en' | null) ?? null} version={sp.get('version') ? Number(sp.get('version')) : null} />}
    </div>
  );
}
