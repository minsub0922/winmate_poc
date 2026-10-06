/**
 * 딸깍 진행 · 완료(§4.17 · §3.9, 보드 OneClickGen · OneClickDone) — `/proposal/:id/one-click/:jobId`.
 * 진행: 머리 띠 「딸깍 · {시작 섹션}부터 나머지 자동 완성」 + 진행 카드(%, 남은 시간, 섹션 10행: 확정 · 추론 완료 · 생성 중 · 대기).
 *   「진행 방향 메모」 → jobs 메모, 「중지」 → jobs 취소 → 딸깍을 누른 화면으로.
 * 완료: 파일 카드(확정 · 추론 · 검토 필요) · 썸네일 8(추론 = 점선 + 배지) · 나머지 줄 · 검토 패널(이대로 확정 · 섹션 열기).
 *   「추론한 시트만 보기」 → PR7P(filter=inferred) · 「추론 근거 보기」 → PR7P(panel=evidence) · 수정 요청 → POST …/requests.
 */
import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { BoltIcon, Icon, cx, toast, useConfirm } from '@/ui';
import { addJobMemo, cancelJob } from '@/api/jobs';
import { proposalRequest, qk, resolveConfirm, startOneClick, useOneClick, useProposal } from '../api/proposal';
import { errText, jobErrText } from '../api/http';
import { useJobEvents } from '../api/jobs';
import type { OneClickView } from '../api/types';
import { Agent, Bar, Dock, ErrorBand, LoadingCard, Prompt, PrPage, Rich, SpinIcon } from '../components/parts';
import { SlideThumb } from '../components/SlideThumb';
import { R, normalizeRoute } from '../lib/routes';
import { useProposalShell } from '../lib/useProposalShell';
import { useQuickExport } from '../lib/useQuickExport';

type Step = OneClickView['steps'][number];
const ST_LABEL: Record<string, string> = { confirmed: '확정', inferred_done: '추론 완료', running: '생성 중', waiting: '대기', skipped: '건너뜀', canceled: '중지됨' };

function StepIcon({ s }: { s: Step['status'] }) {
  if (s === 'confirmed') return <span className="pr-ocicon pr-ocicon--ok"><Icon name="check" size={11} strokeWidth={3} /></span>;
  if (s === 'inferred_done') return <span className="pr-ocicon pr-ocicon--inf"><BoltIcon size={10} color="var(--wm-surface)" /></span>;
  if (s === 'running') return <span className="pr-ocicon pr-ocicon--run" aria-hidden="true" />;
  return <span className="pr-ocicon" />;
}

/** 딸깍을 누른 화면(중지 후 돌아갈 곳) */
function fromRoute(id: string, v: OneClickView | undefined) {
  if (!v) return R.open(id);
  if (v.from_section_key) return R.section(id, v.from_section_key);
  switch (v.from_stage) {
    case 'customer': return R.customer(id);
    case 'type': return R.type(id);
    case 'compose': return R.compose(id);
    case 'industry': return R.industry(id);
    case 'design': return R.design(id);
    default: return R.open(id);
  }
}

export function OneClickPage() {
  const { id, jobId } = useParams();
  const nav = useNavigate();
  const qc = useQueryClient();
  const { confirm, dialog } = useConfirm();
  const pq = useProposal(id);
  const p = pq.data;
  const [live, setLive] = useState(true);
  const oq = useOneClick(id, jobId, live ? 2500 : false);
  const v = oq.data;
  const running = !v || v.status === 'running' || v.status === 'queued';
  const ev = useJobEvents(running ? jobId : null, {
    onDone: (j) => {
      void oq.refetch();
      if (id) void qc.invalidateQueries({ queryKey: qk.p(id) });
      if (j.status === 'canceled') { toast('딸깍을 멈췄어요. 끝난 섹션은 「추론 완료」로 남겨 두었어요'); if (id) nav(fromRoute(id, v), { replace: true }); }
      else if (j.status === 'failed') toast(jobErrText(j.error, '딸깍을 마치지 못했어요. 다시 시도해 주세요'));
    },
  });
  useEffect(() => { if (v && !running) setLive(false); }, [v, running]);
  // 「완료 후 검토가 필요한 곳 모아 보기」를 끄고 실행했으면 끝나면 PR7(AC-119)
  useEffect(() => { if (id && v?.status === 'succeeded' && v.options?.collect_reviews === false) nav(R.result(id), { replace: true }); }, [id, v?.status, v?.options?.collect_reviews, nav]);
  const qe = useQuickExport(id);
  const [stopping, setStopping] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const [reqBusy, setReqBusy] = useState(false);
  const [done, setDone] = useState<Set<string>>(new Set());
  const auto = v?.auto_from_step ?? p?.one_click?.auto_from_step ?? 4;
  useProposalShell({ p, step: 6, autoFrom: auto, complete: !!v && v.status === 'succeeded' });

  if (pq.isError) return <PrPage><ErrorBand message={errText(pq.error, '제안서를 찾을 수 없어요')} onRetry={() => void pq.refetch()} /></PrPage>;
  if (!p || !id || !jobId) return <PrPage><LoadingCard /></PrPage>;
  if (oq.isError && !v) return <PrPage><ErrorBand message={errText(oq.error, '딸깍 진행 상황을 불러오지 못했어요')} onRetry={() => void oq.refetch()} /></PrPage>;
  if (!v) return <PrPage><LoadingCard lines={6} /></PrPage>;

  const pct = Math.max(v.pct ?? 0, Math.round(ev.progress || 0));
  const steps = v.steps.map((s) => {
    const e = ev.steps.get(s.key)?.status;
    if (s.status === 'confirmed' || s.status === 'inferred_done') return s;
    // 잡이 끝났는데(실패 · 중지) 아직 「생성 중」인 단계는 멈춤으로
    if ((v.status === 'failed' || v.status === 'canceled') && (s.status === 'running' || e === 'running')) return { ...s, status: 'waiting' as const, status_label: '멈춤' };
    if (e === 'done') return { ...s, status: 'inferred_done' as const, status_label: '추론 완료' };
    if (e === 'running') return { ...s, status: 'running' as const, status_label: '생성 중' };
    return s;
  });
  const headTail = v.header.replace(/^\s*(딸깍)?\s*·?\s*/, '');
  const failed = v.status === 'failed';
  // 서버 slides_label 이 이미 「표준 제안서 · 27장」이면 유형을 두 번 쓰지 않는다
  const metaLine = v.slides_label && v.type_label && v.slides_label.includes(v.type_label) ? v.slides_label : [v.type_label, v.slides_label].filter(Boolean).join(' · ');
  const retry = async () => {
    setRetrying(true);
    try {
      const r = await startOneClick(id, { options: (v.options ?? {}) as never, from_stage: v.from_stage ?? null, from_section_key: v.from_section_key ?? null });
      nav(R.oneClick(id, r.job_id), { replace: true });
    } catch (e) { toast(errText(e)); } finally { setRetrying(false); }
  };

  const stop = async () => {
    const ok = await confirm({ title: '딸깍을 멈출까요?', message: '지금 만드는 섹션까지 마치고 멈춰요. 이미 끝난 섹션은 「추론 완료」로 남고, 딸깍을 누른 화면으로 돌아가요.', confirmLabel: '중지', tone: 'danger' });
    if (!ok) return;
    setStopping(true);
    try { await cancelJob(jobId); } catch (e) { toast(errText(e)); setStopping(false); }
  };
  const memo = async (text: string) => {
    try { await addJobMemo(jobId, text); toast('메모를 보냈어요 · 다음 섹션부터 반영돼요'); void oq.refetch(); } catch (e) { toast(errText(e)); }
  };
  const request = async (text: string) => {
    setReqBusy(true);
    try { await proposalRequest(id, text); toast('수정 요청을 반영하는 중이에요'); } catch (e) { toast(errText(e)); } finally { setReqBusy(false); }
  };
  const keep = async (itemId: string) => {
    try { await resolveConfirm(id, itemId, {}); setDone((s) => new Set(s).add(itemId)); void qc.invalidateQueries({ queryKey: qk.sub(id, 'confirm') }); }
    catch (e) { toast(errText(e)); }
  };

  if (running || v.status === 'canceled' || v.status === 'failed') {
    const dock = (
      <Dock testId="oc-gen-dock" title={failed ? '딸깍 멈춤' : v.status === 'canceled' ? '딸깍 중지됨' : '딸깍 진행 중'}
        meta={failed ? '끝난 섹션은 「추론 완료」로 남아 있어요' : v.status === 'canceled' ? '딸깍을 누른 화면으로 돌아가요' : '다른 작업을 해도 돼요, 끝나면 알려드릴게요'}>
        <div className="pr-row" style={{ gap: 10, paddingBottom: 14 }}>
          {failed ? (
            <>
              <span className="pr-grow" />
              <Link to={normalizeRoute(v.next_route) ?? fromRoute(id, v)} className="pr-btn" data-testid="oc-back">돌아가기</Link>
              <button type="button" className="pr-btn pr-btn--primary" onClick={() => void retry()} disabled={retrying} data-testid="oc-retry">
                {retrying ? <SpinIcon size={12} color="currentColor" /> : <BoltIcon size={13} color="var(--wm-surface)" />}딸깍 다시 시도</button>
            </>
          ) : (
            <>
              <Prompt placeholder="진행 중에도 방향을 알려주세요 (예: Why Samsung은 비용 중심으로)" label="진행 방향 메모" onSend={memo} busy={!running} testId="oc-memo" />
              <button type="button" className="pr-btn" onClick={() => void stop()} disabled={!running || stopping} data-testid="oc-stop">
                {stopping ? <SpinIcon size={12} /> : <span className="pr-stopsq" aria-hidden="true" />}중지</button>
            </>
          )}
        </div>
      </Dock>
    );
    return (
      <PrPage testId="oc-gen" dock={dock} gap={14} tight>
        <div className="pr-ocpill" data-testid="oc-header"><BoltIcon size={13} color="var(--wm-surface)" /><b>딸깍</b><span>· {headTail}</span></div>
        <Agent text={v.intro} testId="oc-agent">
          {failed && <ErrorBand testId="oc-failed" message={jobErrText(v.error as { code?: string; message?: string } | null, '딸깍을 마치지 못했어요')} />}
          <div className="pr-card pr-occard" data-testid="oc-progress">
            <div className="pr-occard__head">
              <div className="pr-row" style={{ gap: 10 }}>
                <span className="pr-ocbolt"><BoltIcon size={13} color="var(--wm-surface)" /></span>
                <b style={{ fontSize: 14 }}>{failed ? '제안서 생성을 마치지 못했어요' : v.status === 'canceled' ? '제안서 생성 중지됨' : '제안서 생성 중'}</b>
                <span className="pr-note">{metaLine}</span>
                <span className="pr-grow" />
                <span className={running ? 'pr-brand' : 'pr-muted'} style={{ fontSize: 13, fontWeight: 700 }} data-testid="oc-pct"><span className="pr-num">{pct}%</span>{running && v.eta_label ? ` · ${v.eta_label}` : ''}</span>
              </div>
              <Bar value={pct} label="딸깍 진행률" />
            </div>
            <div className="pr-ocrows" data-testid="oc-steps">
              {steps.map((s) => (
                <div key={s.key} className={cx('pr-ocrow', s.status === 'running' && 'pr-ocrow--run')} data-testid="oc-step" data-status={s.status}>
                  <StepIcon s={s.status} />
                  <span className="pr-ocrow__name">{s.label}</span>
                  <span className="pr-ell pr-ocrow__note">{s.note}</span>
                  <span className={cx('pr-ocrow__st', `pr-ocrow__st--${s.status}`)}>{s.status_label || ST_LABEL[s.status]}</span>
                </div>
              ))}
            </div>
          </div>
          {!!v.memos?.length && (
            <div className="pr-colflex" style={{ gap: 4 }} data-testid="oc-memos">
              {v.memos.map((m, i) => (
                <div key={i} className="pr-ocmemo"><Icon name="edit" size={12} color="var(--wm-text-muted)" /><span className="pr-grow">{m.text}</span><span className="pr-note">{m.status_label || (m.applied_at ? '반영됨' : '메모 반영 예정 · 다음 섹션부터')}</span></div>
              ))}
            </div>
          )}
        </Agent>
        {dialog}
      </PrPage>
    );
  }

  // ── 완료(OneClickDone) ──
  const file = v.file;
  const items = (v.review_items ?? []).filter((it) => !done.has(it.id) && it.status === 'open');
  const counts = v.counts ?? {};
  const firstOpen = items[0];
  const refine = firstOpen?.route ? normalizeRoute(firstOpen.route)! : firstOpen?.section_key ? R.section(id, firstOpen.section_key)
    : (() => { const s = p.sections?.find((x) => x.inferred && x.enabled); return s ? normalizeRoute(s.route) ?? R.section(id, s.key) : R.preview(id); })();
  const dock = (
    <Dock testId="oc-done-dock" title="딸깍 완료" meta="섹션을 열어 다듬으면 그 섹션만 다시 생성됩니다"
      right={<>
        <Link to={R.preview(id, null, { filter: 'inferred' })} className="pr-quick" data-testid="oc-only-inferred">추론한 시트만 보기</Link>
        <Link to={R.preview(id, null, { panel: 'evidence' })} className="pr-quick">추론 근거 보기</Link>
      </>}>
      <div className="pr-row" style={{ gap: 10, paddingBottom: 14 }}>
        <Prompt placeholder="수정 요청 (예: 공간별 제품 수량을 매장당 2대로)" label="수정 요청" onSend={request} busy={reqBusy} testId="oc-request" />
        <Link to={refine} className="pr-btn" data-testid="oc-refine">섹션 열어 다듬기</Link>
        <button type="button" className="pr-btn pr-btn--primary" disabled={!!qe.busy} onClick={() => void qe.run('pptx', file?.pptx_url ?? null, file?.name)} data-testid="oc-download">
          {qe.busy === 'pptx' ? <SpinIcon color="currentColor" /> : <Icon name="download" size={15} strokeWidth={2.2} />}PPTX 다운로드</button>
      </div>
    </Dock>
  );
  return (
    <PrPage testId="oc-done" dock={dock} gap={14} tight>
      <Agent text={<Rich text={v.done_intro || v.intro} />} testId="oc-agent">
        {file && (
          <div className="pr-filecard" data-testid="oc-file">
            <div className="pr-filecard__head">
              <span className="pr-filecard__icon"><Icon name="file" size={16} /></span>
              <div className="pr-colflex pr-grow" style={{ gap: 2 }}>
                <span className="pr-filecard__name">{file.name}</span>
                <span className="pr-filecard__meta pr-row" style={{ gap: 6 }} data-testid="oc-counts">
                  <span>{file.meta}</span>
                  {counts.confirmed !== undefined && <span className="pr-row" style={{ gap: 4 }}><i className="pr-sq pr-sq--brand" />확정 {counts.confirmed}</span>}
                  {counts.inferred !== undefined && <span className="pr-row" style={{ gap: 4 }}><i className="pr-sq pr-sq--dark" />추론 {counts.inferred}</span>}
                  {(counts.review ?? items.length) > 0 && <b className="pr-brand">검토 필요 {counts.review ?? items.length}</b>}
                  {!counts.confirmed && !counts.inferred && v.counts_label?.map((l) => <span key={l}>{l}</span>)}
                </span>
              </div>
              <button type="button" className="pr-btn pr-btn--h38" style={{ height: 34 }} disabled={!!qe.busy} onClick={() => void qe.run('pdf', null, file.name.replace(/\.pptx$/, '.pdf'))}>{qe.busy === 'pdf' ? <SpinIcon /> : null}PDF</button>
              <button type="button" className="pr-btn pr-btn--h38 pr-btn--primary" style={{ height: 34, fontSize: 13 }} disabled={!!qe.busy} onClick={() => void qe.run('pptx', file.pptx_url ?? null, file.name)}>
                <Icon name="download" size={14} strokeWidth={2.2} />PPTX 다운로드</button>
            </div>
            <div className="pr-filecard__body">
              <div className="pr-thumbs pr-thumbs--8" data-testid="oc-thumbs">
                {(v.thumbs ?? []).slice(0, 8).map((t) => (
                  <Link key={t.slide_no} to={R.preview(id, (t.sheet_id && p.sheets?.find((x) => x.id === t.sheet_id)?.sheet_no) || null)} className="pr-thumbcell" title={t.label}>
                    <SlideThumb url={t.thumb_url} label={t.label} kind={t.kind} inferred={t.inferred} />
                    <span className="pr-ell"><span className="pr-num">{String(t.slide_no).padStart(2, '0')}</span> {t.label.replace(/^\d{1,3}\s+/, '')}</span>
                  </Link>
                ))}
              </div>
              {v.rest_label && <div className="pr-ranges"><span className="pr-grow" data-testid="oc-rest">{v.rest_label}</span></div>}
            </div>
          </div>
        )}
        {(v.review_items?.length ?? 0) > 0 && (
          <div className="pr-card" style={{ overflow: 'hidden' }} data-testid="oc-review">
            <div className="pr-cardhead" style={{ height: 38 }}>
              <b style={{ fontSize: 13 }}>{v.review_header || `검토가 필요한 곳 ${items.length}`}</b>
              <span className="pr-grow" />
              <span className="pr-note">나머지 추론 시트는 근거 노트만 확인하면 돼요</span>
            </div>
            {items.length === 0 && <div className="pr-empty" style={{ padding: 16 }}>검토가 필요한 곳을 모두 확인했어요</div>}
            {items.map((it, i) => (
              <div key={it.id} className="pr-revrow" data-testid="oc-review-item">
                <span className="pr-revno pr-num">{i + 1}</span>
                <span className="pr-colflex pr-grow" style={{ gap: 1 }}>
                  <b className="pr-ell" style={{ fontSize: 13 }}>{it.where || `${it.text.pre ?? ''}${it.text.mark}${it.text.post ?? ''}`}</b>
                  <span className="pr-ell" style={{ fontSize: 12, color: 'var(--wm-text-muted)' }}>{it.why || it.sub}</span>
                </span>
                <button type="button" className="pr-mini" onClick={() => void keep(it.id)} data-testid="oc-keep">이대로 확정</button>
                <Link to={normalizeRoute(it.route) ?? (it.section_key ? R.section(id, it.section_key) : R.confirm(id))} className="pr-mini pr-mini--primary">섹션 열기</Link>
              </div>
            ))}
          </div>
        )}
        {qe.busy && <div className="pr-band pr-band--muted"><SpinIcon /> <span className="pr-grow">{qe.busy.toUpperCase()} 파일을 만드는 중이에요 · {Math.round(qe.progress)}%</span></div>}
      </Agent>
    </PrPage>
  );
}
