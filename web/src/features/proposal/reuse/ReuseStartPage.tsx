/**
 * PR1C — 기존 제안서로 시작(§4.10, 보드 PR1C, 1/6).
 * 원본 고르기(내 제안서 목록 · 파일 올리기) → `POST …/reuse`(잡: 읽기 → 쪽 나누기 → 기준별 분석). 원본을 더하면 같은 분석에 더해 다시 시작.
 * 활용 방식 3개(기본 「분석 뒤 추천받기」)는 저장만(분석은 그대로) — 시작 뒤 바꾼 값은 PRU3 를 그 방식으로 여는 데 쓴다.
 * 「분석 결과 확인」은 분석이 사람 확인 대기(awaiting_confirm)가 되면 활성 → PRU2.
 */
import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { uploadFile } from '@/api/client';
import { Icon, cx, toast } from '@/ui';
import { deleteReuse, listProposals, patchProposal, putReuseModePref, qk, startReuse, useProposal, useReuse, useReuseCandidates } from '../api/proposal';
import { errText, isMissing, jobErrText } from '../api/http';
import { useJobEvents } from '../api/jobs';
import type { ReuseAnalysis } from '../api/types';
import { Agent, Dock, ErrorBand, LoadingCard, NextButton, PrPage, SpinIcon } from '../components/parts';
import { R } from '../lib/routes';
import { useProposalShell } from '../lib/useProposalShell';

type ModePref = 'improve' | 'borrow' | 'auto';
const MB50 = 50 * 1024 * 1024;
const MODES: Array<{ key: ModePref; label: string; desc: string; sub?: string }> = [
  { key: 'improve', label: '기반으로 개선 · 수정', desc: '내용까지 가져와 현행화 · 보강 · 재작성. 같은 고객의 지난 제안서에 알맞아요', sub: '시트별 유지 · 갱신 · 재작성 · 신규 · 제외를 정해요' },
  { key: 'borrow', label: '논리 흐름만 차용', desc: '설득 구조(스토리라인 · 시트 역할 · 주장 순서)만 가져오고 내용은 이번 고객으로 새로 써요. 다른 고객 · 동료 제안서에 알맞아요', sub: '고객 정보 · 사진 · 수치는 쓰지 않아요' },
  { key: 'auto', label: '분석 뒤 추천받기', desc: '9가지 기준 분석 결과를 보고 에이전트가 추천해요 · 같은 고객 + 요구사항 겹침 3건 이상이면 개선 · 수정, 다른 고객이면 흐름 차용' },
];
const PHASES = [['read', '읽기'], ['split', '쪽 나누기'], ['analyze', '기준별 분석']] as const;
type SrcIn = { kind: 'proposal' | 'file'; proposal_id?: string | null; version?: number | null; file_id?: string | null };

/** 활용 방식 선호 — 분석 시작 뒤 바꾼 값은 서버 계약(ModePut: improve|borrow)에 auto 가 없어 이 창에 기억해 PRU2 → PRU3 열 때 쓴다 */
export const modePrefKey = (id: string) => `pr:reuse-mode:${id}`;
export function readModePref(id: string): ModePref | null {
  try { const v = window.sessionStorage.getItem(modePrefKey(id)); return v === 'improve' || v === 'borrow' || v === 'auto' ? v : null; } catch { return null; }
}
function writeModePref(id: string, v: ModePref) { try { window.sessionStorage.setItem(modePrefKey(id), v); } catch { /* 저장 못 해도 진행 */ } }

const srcOf = (s: ReuseAnalysis['sources'][number]): SrcIn => ({ kind: s.kind, proposal_id: s.proposal_id ?? null, version: s.version ?? null, file_id: s.file_id ?? null });

export function ReuseStartPage() {
  const { id } = useParams();
  const [sp, setSp] = useSearchParams();
  const nav = useNavigate();
  const qc = useQueryClient();
  const pq = useProposal(id);
  const p = pq.data;
  const [job, setJob] = useState<string | null>(null);
  const rq = useReuse(id, job ? 3000 : false);
  const rv = rq.isError ? null : rq.data ?? null;
  const cq = useReuseCandidates(id);
  const [tab, setTab] = useState<'list' | 'files'>('files');
  const [mode, setMode] = useState<ModePref>('auto');
  const [title, setTitle] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [hidden, setHidden] = useState<Set<string>>(new Set());
  const titleTimer = useRef<number | null>(null);
  const activeJob = job ?? (rv?.status === 'analyzing' ? rv.job_id ?? null : null);
  const ev = useJobEvents(activeJob, {
    onDone: (j) => {
      setJob(null);
      if (j.status === 'failed') toast(jobErrText(j.error, '원본을 분석하지 못했어요. 다른 파일을 올려 주세요.'));
      void rq.refetch();
    },
  });
  useEffect(() => {
    if (rv?.status !== 'analyzing' || job) return;
    const t = window.setInterval(() => void rq.refetch(), 3000);
    return () => window.clearInterval(t);
  }, [rv?.status, job, rq]);
  useEffect(() => { if (id) { const m = rv?.mode_pref ?? readModePref(id); if (m) setMode(m); } }, [id, rv?.mode_pref]);
  useProposalShell({ p, step: 1, oneClick: { from: 'customer' } });

  // 내 제안서 목록(현재 제안서 제외)
  const lq = useQuery({
    queryKey: ['pr', 'reuse-mine', id],
    queryFn: () => listProposals({ tab: 'all', owner: 'me', sort: 'updated_desc', limit: 30 }),
    enabled: !!id && tab === 'list', retry: 0,
  });

  const sources = useMemo(() => (rv?.sources ?? []).filter((s) => !hidden.has(s.file_id ?? s.proposal_id ?? '')), [rv, hidden]);
  const start = async (next: SrcIn[]) => {
    if (!id) return;
    if (!next.length) return;
    // 화면이 들고 있는 원본 목록 전체를 보낸다(replace) — 더하기 · 빼기 모두 같은 길
    const r = await startReuse(id, { sources: next, mode_pref: mode, new_title: (title ?? p?.title) || null, replace: true });
    setJob(r.job_id);
    void rq.refetch();
  };

  // PR0 「복제해서 시작」(?source=) — 그 제안서를 원본으로 바로 분석
  const auto = useRef(false);
  useEffect(() => {
    const src = sp.get('source');
    if (!src || !id || auto.current || rq.isLoading) return;
    if (rv && rv.sources?.length) { auto.current = true; return; }
    auto.current = true;
    void start([{ kind: 'proposal', proposal_id: src }]).catch((e) => toast(errText(e)));
    if (sp.get('source')) setSp((cur) => { const x = new URLSearchParams(cur); x.delete('source'); return x; }, { replace: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sp, p, rv, rq.isLoading, id]);

  const onFiles = async (files: File[]) => {
    if (!id || !files.length) return;
    for (const f of files) {
      if (!/\.(pptx|pdf)$/i.test(f.name)) { toast('PPTX · PDF만 올릴 수 있어요'); return; }
      if (f.size > MB50) { toast('파일당 50MB까지 올릴 수 있어요'); return; }
    }
    setBusy('upload');
    try {
      const ups = [];
      for (const f of files) ups.push(await uploadFile(f, { projectId: p?.project_id ?? undefined, purpose: 'proposal_reuse_source' }));
      await start([...sources.map(srcOf), ...ups.map((u) => ({ kind: 'file' as const, file_id: u.id }))]);
    } catch (e) { toast(errText(e)); } finally { setBusy(null); }
  };
  const importProposal = async (pid: string, version?: number | null) => {
    if (sources.some((s) => s.proposal_id === pid)) { toast('이미 원본으로 가져왔어요'); return; }
    setBusy(`imp:${pid}`);
    try { await start([...sources.map(srcOf), { kind: 'proposal', proposal_id: pid, version: version ?? null }]); setTab('files'); toast('원본으로 가져왔어요 · 분석을 다시 시작해요'); }
    catch (e) { toast(errText(e)); } finally { setBusy(null); }
  };
  const remove = async (s: ReuseAnalysis['sources'][number]) => {
    const k = s.file_id ?? s.proposal_id ?? '';
    const rest = sources.filter((x) => (x.file_id ?? x.proposal_id ?? '') !== k);
    setHidden((h) => new Set(h).add(k));
    setBusy('remove');
    try {
      if (rest.length) await start(rest.map(srcOf));
      else { await deleteReuse(id!); setJob(null); qc.removeQueries({ queryKey: qk.sub(id!, 'reuse') }); void rq.refetch(); } // 마지막 원본 → 분석 지움
    } catch (e) { toast(errText(e)); setHidden((h) => { const n = new Set(h); n.delete(k); return n; }); } finally { setBusy(null); }
  };
  // 분석이 있으면 서버에 「저장만」(PUT …/reuse/mode {mode_pref}), 없으면 분석 시작 때 함께 보낸다
  const pickMode = (m: ModePref) => {
    setMode(m);
    if (!id) return;
    writeModePref(id, m);
    if (rv) void putReuseModePref(id, m).then((nv) => qc.setQueryData(qk.sub(id, 'reuse'), nv)).catch((e) => toast(errText(e)));
  };
  const onTitle = (v: string) => {
    setTitle(v);
    if (titleTimer.current) window.clearTimeout(titleTimer.current);
    titleTimer.current = window.setTimeout(() => { if (id) void patchProposal(id, { title: v }).then((np) => qc.setQueryData(qk.p(id), np)).catch(() => { /* 다음 저장에서 */ }); }, 800);
  };

  if (pq.isError) return <PrPage><ErrorBand message={errText(pq.error, '제안서를 찾을 수 없어요')} onRetry={() => void pq.refetch()} /></PrPage>;
  if (!p) return <PrPage><LoadingCard /></PrPage>;

  const analyzing = !!activeJob || rv?.status === 'analyzing';
  const ready = !!rv && sources.length > 0 && ['awaiting_confirm', 'planning', 'awaiting_plan_confirm', 'applied'].includes(rv.status);
  const failed = rv?.status === 'failed' && !analyzing;
  const totalPages = sources.reduce((n, s) => n + (s.pages ?? 0), 0);
  const cands = cq.data?.items ?? [];
  const statusLabel = !sources.length ? null : analyzing ? (rv?.status_label && rv.status === 'analyzing' ? rv.status_label : '기준별 분석 진행 중') : failed ? '분석 실패' : ready ? '분석 완료' : rv?.status_label ?? null;
  const notImpl = rq.isError && isMissing(rq.error) && (rq.error as { code?: string }).code === 'NOT_IMPLEMENTED';

  const dock = (
    <Dock testId="pr1c-dock" title="기존 제안서로 시작" meta="1 / 6"
      right={sources.length ? <>
        <span className="pr-tally pr-tally--found" data-testid="pr1c-count">원본 <b className="pr-num">{sources.length}</b>개{totalPages ? <> · <b className="pr-num">{totalPages}</b>장</> : null}</span>
        {statusLabel && <span className="pr-tally pr-tally--empty" data-testid="pr1c-status">{statusLabel}</span>}
      </> : null}>
      <div className="pr-row" style={{ gap: 10, paddingBottom: 14 }}>
        <div className="pr-titlefield">
          <label htmlFor="pr1c-title">새 프로젝트명</label>
          <span className="pr-vdiv" style={{ height: 18 }} />
          <input id="pr1c-title" value={title ?? p.title ?? ''} onChange={(e) => onTitle(e.target.value)} placeholder="이번 프로젝트 이름" data-testid="pr1c-title" />
        </div>
        <button type="button" className="pr-btn" onClick={() => nav(R.list())}>이전</button>
        <button type="button" className="pr-btn" onClick={() => nav(R.customer(p.id))} data-testid="pr1c-manual">직접 입력으로</button>
        <NextButton onClick={() => nav(R.reuseAnalysis(p.id))} disabled={!ready} disabledReason={analyzing ? '기준별 분석 진행 중' : '원본을 먼저 골라 주세요'} testId="pr1c-next">분석 결과 확인</NextButton>
      </div>
    </Dock>
  );

  return (
    <PrPage testId="pr1c" dock={dock} gap={14} tight>
      <Agent text="기존 제안서를 가져와 이번 제안서의 바탕으로 쓸 수 있어요. 내 제안서 목록에서 고르거나 PPTX · PDF 파일을 올리면, 9가지 기준으로 분석한 뒤 확인을 거쳐 활용 방식을 정해요. 내용만 갈아 끼우는 게 아니라 이번 요구사항에 맞게 구조와 내용을 다시 짜요." testId="pr1c-agent">
        {notImpl && <div className="pr-band pr-band--muted">기존 제안서 분석은 아직 준비 중이에요. 원본을 올려 두면 준비되는 대로 분석해요.</div>}
        <div className="pr-card" data-testid="pr1c-source">
          <div className="pr-cardhead">
            <span style={{ fontSize: 13, fontWeight: 700 }}>원본 고르기</span>
            <span className="pr-grow" />
            <div role="tablist" aria-label="원본 출처" className="pr-miniseg pr-miniseg--tabs">
              <button type="button" role="tab" aria-selected={tab === 'list'} aria-checked={tab === 'list'} onClick={() => setTab('list')} data-testid="pr1c-tab-list">내 제안서 목록</button>
              <button type="button" role="tab" aria-selected={tab === 'files'} aria-checked={tab === 'files'} onClick={() => setTab('files')} data-testid="pr1c-tab-files">파일 올리기</button>
            </div>
          </div>
          <div className="pr-colflex" style={{ padding: '10px 14px', gap: 8 }}>
            {tab === 'files' ? (
              <>
                {sources.map((s, i) => {
                  const phases = (s.phases?.length ? s.phases : rv?.phases?.length ? rv.phases : PHASES.map(([key, label]) => ({ key, label, status: ready ? 'done' : 'todo' as const })))
                    .map((ph) => { const st = ev.steps.get(ph.key)?.status; return { ...ph, status: st === 'done' ? 'done' : st === 'running' ? 'busy' : ph.status }; });
                  return (
                    <div key={`${s.file_id ?? s.proposal_id}-${i}`} className="pr-srcfile" data-testid="pr1c-file">
                      <span className="pr-srcfile__icon"><Icon name="file" size={15} color="var(--wm-brand)" /></span>
                      <span className="pr-colflex pr-grow" style={{ gap: 1 }}>
                        <span className="pr-ell" style={{ fontSize: 13, fontWeight: 600 }}>{s.name}</span>
                        <span className="pr-ell" style={{ fontSize: 11.5, color: 'var(--wm-text-muted)' }}>{s.meta_label || [s.format?.toUpperCase(), s.pages ? `${s.pages}장` : null, s.doc_date, s.author].filter(Boolean).join(' · ')}</span>
                      </span>
                      <span className="pr-row" style={{ gap: 4 }}>
                        {phases.map((ph) => (
                          <span key={ph.key} className={cx('pr-phasechip', ph.status === 'done' && 'pr-phasechip--done', ph.status === 'busy' && 'pr-phasechip--outline')}>
                            {ph.status === 'done' ? <Icon name="check" size={10} strokeWidth={3} /> : ph.status === 'busy' ? <SpinIcon size={10} color="currentColor" /> : null}
                            {ph.label}{ph.status === 'busy' ? ' · 진행 중' : ''}
                          </span>
                        ))}
                      </span>
                      <span className="pr-vdiv" style={{ height: 22 }} />
                      <button type="button" className="pr-iconbtn" aria-label="올린 파일 지우기" onClick={() => void remove(s)} disabled={!!busy}><Icon name="trash" size={14} /></button>
                    </div>
                  );
                })}
                {failed && <ErrorBand message={jobErrText(rv?.error as { code?: string; message?: string } | null, '원본을 분석하지 못했어요. 다른 파일을 올려 주세요.')} />}
                <FileDrop busy={busy === 'upload'} onFiles={(fs) => void onFiles(fs)} />
                {cands.length > 0 && (
                  <div className="pr-recline" data-testid="pr1c-recs">
                    <span style={{ width: 128, flexShrink: 0, fontSize: 12, lineHeight: 1.4, color: 'var(--wm-text-muted)' }}>내 제안서 목록에서는<br /><b style={{ color: 'var(--wm-text)' }}>{cq.data?.label || `${cands.length}개 추천`}</b></span>
                    <span className="pr-vdiv" style={{ height: 36 }} />
                    <div className="pr-colflex pr-grow" style={{ gap: 2 }}>
                      {cands.slice(0, 3).map((c) => (
                        <div key={c.proposal_id} className="pr-row" style={{ height: 23, gap: 8, minWidth: 0 }}>
                          <span className="pr-ell" style={{ fontSize: 12, fontWeight: 600 }}>{c.name}</span>
                          <span className="pr-whypill">{c.why}</span>
                          <span className="pr-grow" />
                          <button type="button" className="pr-tinybtn" disabled={!!busy} onClick={() => void importProposal(c.proposal_id, c.version)} data-testid="pr1c-import">
                            {busy === `imp:${c.proposal_id}` ? <SpinIcon size={10} /> : null}가져오기</button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            ) : (
              <div className="pr-colflex" style={{ gap: 0 }} data-testid="pr1c-mine">
                {lq.isError ? <ErrorBand message={errText(lq.error)} onRetry={() => void lq.refetch()} />
                  : !lq.data ? <LoadingCard lines={3} />
                    : (() => {
                      const why = new Map(cands.map((c) => [c.proposal_id, c.why]));
                      const rows = (lq.data.items ?? []).filter((r) => r.id !== p.id)
                        .sort((a, b) => Number(why.has(b.id)) - Number(why.has(a.id)));
                      if (!rows.length) return <div className="pr-empty">가져올 제안서가 없어요. 「파일 올리기」로 PPTX · PDF를 올려 주세요.</div>;
                      return rows.map((r) => (
                        <div key={r.id} className="pr-minerow">
                          <span className="pr-colflex pr-grow" style={{ gap: 1 }}>
                            <span className="pr-row" style={{ gap: 6, minWidth: 0 }}><span className="pr-ell" style={{ fontSize: 13, fontWeight: 600 }}>{r.title}</span>{why.get(r.id) && <span className="pr-whypill">{why.get(r.id)}</span>}</span>
                            <span className="pr-ell" style={{ fontSize: 11.5, color: 'var(--wm-text-muted)' }}>{[r.customer_name, r.type_label, r.sub_label].filter(Boolean).join(' · ')}</span>
                          </span>
                          <button type="button" className="pr-tinybtn" disabled={!!busy || sources.some((s) => s.proposal_id === r.id)} onClick={() => void importProposal(r.id)}>
                            {sources.some((s) => s.proposal_id === r.id) ? '가져옴' : '가져오기'}</button>
                        </div>
                      ));
                    })()}
              </div>
            )}
          </div>
        </div>
        <div className="pr-card" style={{ padding: '12px 14px 14px', gap: 10, display: 'flex', flexDirection: 'column' }}>
          <div className="pr-row" style={{ height: 20 }}>
            <span style={{ fontSize: 13, fontWeight: 700 }}>활용 방식</span>
            <span style={{ fontSize: 12, color: 'var(--wm-text-muted)' }}>· 에이전트가 추천하되 결정은 직접 해요</span>
          </div>
          <div role="radiogroup" aria-label="활용 방식" className="pr-modes">
            {MODES.map((m) => {
              const rec = rv?.recommendation ? rv.recommendation.mode === m.key : m.key === 'auto';
              return (
                <button key={m.key} type="button" role="radio" aria-checked={mode === m.key} className="pr-modecard" onClick={() => pickMode(m.key)} data-testid={`pr1c-mode-${m.key}`}>
                  <span className="pr-row" style={{ gap: 7, height: 20 }}>
                    <span className={cx('pr-radiodot', mode === m.key && 'pr-radiodot--on')} />
                    <span className="pr-ell" style={{ fontSize: 13, fontWeight: 700 }}>{m.label}</span>
                    {rec && <span className="pr-recpill pr-recpill--solid">{rv?.recommendation?.badge || '추천'}</span>}
                  </span>
                  <span style={{ fontSize: 11.5, lineHeight: 1.5, color: 'var(--wm-text-2)' }}>{m.desc}</span>
                  {m.sub && <span style={{ fontSize: 11, lineHeight: 1.5, color: 'var(--wm-text-subtle)' }}>{m.sub}</span>}
                </button>
              );
            })}
          </div>
        </div>
        <div className="pr-autoline">
          <Icon name="info" size={12} color="var(--wm-brand)" />
          <div className="pr-autoline__grid">
            <b>분석에서 자동으로 하는 것</b><span className="pr-ell">가격 · 견적 · 일정 · 고객 기밀 제외, 단종 모델 후속 치환 제안, 이미지 출처 분류</span>
            <b>확인받는 것</b><span className="pr-ell">시트 역할, 템플릿 매핑, 요구사항 겹침 · 활용 방식</span>
          </div>
        </div>
      </Agent>
    </PrPage>
  );
}

function FileDrop({ onFiles, busy }: { onFiles: (f: File[]) => void; busy: boolean }) {
  const [over, setOver] = useState(false);
  const ref = useRef<HTMLInputElement>(null);
  return (
    <div className={cx('pr-filedrop', over && 'pr-filedrop--over')} data-testid="pr1c-drop"
      onDragOver={(e) => { if (!e.dataTransfer.types.includes('Files')) return; e.preventDefault(); setOver(true); }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => { if (!e.dataTransfer.files.length) return; e.preventDefault(); setOver(false); onFiles(Array.from(e.dataTransfer.files)); }}>
      <span className="pr-iconbox" style={{ width: 36, height: 36, borderRadius: 10 }}>{busy ? <SpinIcon size={18} /> : <Icon name="upload" size={18} color="var(--wm-brand)" />}</span>
      <span className="pr-colflex" style={{ gap: 2 }}>
        <span style={{ fontSize: 13, fontWeight: 600 }}>{busy ? '올리는 중…' : '여기에 끌어다 놓거나 파일을 고르세요'}</span>
        <span style={{ fontSize: 11.5, color: 'var(--wm-text-muted)' }}>PPTX · PDF · 여러 파일 가능 · 파일당 50MB</span>
      </span>
      <input ref={ref} id="pr1c-pick" type="file" multiple accept=".pptx,.pdf" className="wm-sr-only" onChange={(e) => { onFiles(Array.from(e.target.files ?? [])); e.target.value = ''; }} data-testid="pr1c-file-input" />
      <label htmlFor="pr1c-pick" className="pr-btn pr-btn--sm" style={{ marginLeft: 10 }}>파일 선택</label>
    </div>
  );
}
