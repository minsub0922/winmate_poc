/**
 * 5단계 `일정 · 공유` — SB5(일정 · 분담) · SB4(저장 완료 · 다음 할 일) · SB4E(내보내기). §4.24–4.26
 */
import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, Navigate, useNavigate, useParams, useSearchParams } from 'react-router';
import { Icon, toast } from '@/ui';
import { FeatureIcon } from '@/shell/icons';
import { fileUrl } from '@/api/client';
import { useJob } from '@/api/jobs';
import { jobErrorText, sbApi, sbKey, useAction, useSb, useSbShell, vEul, type HandoffCard } from './lib';
import { Back, Bottom, Chevron, Gate, Head, Page, Primary, SbBadge, SkeletonRows } from './parts';

/** SB5 — 5 일정 · 분담 */
export function ScheduleScreen() {
  const { sbId = '' } = useParams();
  const q = useSb(sbId);
  const sb = q.data;
  useSbShell(sb, 5);
  const navigate = useNavigate();
  const qc = useQueryClient();
  const act = useAction();
  if (!sb) return <Gate loading={q.isLoading} error={q.error} onRetry={() => void q.refetch()} />;
  const sch = sb.schedule;
  const phases = sch?.phases ?? [];
  const open = sch?.open_question_count ?? 0;
  const rq = sb.requirement_ref?.requirement_id;
  const save = () => void act.run(async () => {
    const r = await sbApi.save(sb.id);
    await qc.invalidateQueries({ queryKey: sbKey(sb.id) });
    navigate(`/storyboard/${sb.id}/saved?v=${r.version}`);
  });
  return (
    <Page label="제작 일정">
      <Head title={`제작 일정 — D-${sch?.start_d ?? 21}부터 납품까지`}
        actions={rq ? <Link to={`/requirements/${rq}/questions`} className="sb-asklink">물을 것 보기<Icon name="external" size={13} /></Link> : undefined}
        sub={open > 0 ? `확정 전에 고객 확인 ${open}개가 남아 있어요. 스토리보드 공유 때 함께 물어봐요.` : '고객 확인은 모두 끝났어요.'} />
      <div className="sb-card" data-testid="phases">
        {phases.map((p) => (
          <div key={p.id} className={`sb-phase${p.current ? ' sb-phase--now' : ''}`} data-testid="phase" data-current={p.current || undefined}>
            <span className={`sb-circle${p.current ? ' sb-circle--on' : ''}`}>{p.n}</span>
            <span className="sb-col sb-grow" style={{ gap: 3 }}>
              <span className="sb-phase__top">
                <span className="sb-phase__name">{p.name}</span>
                {(p.badges ?? []).map((b) => <SbBadge key={b} tone="soft">{b}</SbBadge>)}
              </span>
              <span className="sb-phase__owner sb-ell">{p.owner}</span>
            </span>
            <span className="sb-phase__d wm-num">D-{p.d_from} ~ D-{p.d_to}</span>
          </div>
        ))}
      </div>
      <Bottom
        back={<Back to={`/storyboard/${sb.id}/trace`}>요구 추적</Back>}
        primary={<Primary onClick={save} busy={act.busy} disabled={!sb.outline?.ready} disabledReason="목차를 다 쓴 뒤에 저장할 수 있어요">저장하고 공유</Primary>} />
    </Page>
  );
}

const HANDOFF_ICON: Record<HandoffCard['target'], string> = { proposal: 'PR', mi: 'MI', scenario: 'SC' };

/** SB4 — 5 저장 완료 · 다음 할 일 */
export function SavedScreen() {
  const { sbId = '' } = useParams();
  const [params] = useSearchParams();
  const q = useSb(sbId);
  const sb = q.data;
  useSbShell(sb, 5, { complete: true });
  const navigate = useNavigate();
  const qc = useQueryClient();
  const act = useAction();
  const review = useAction();
  const cards = useQuery({ queryKey: ['storyboard', sbId, 'handoffs', sb?.revision], queryFn: () => sbApi.handoffs(sbId), enabled: !!sb && sb.version > 0 });
  if (!sb) return <Gate loading={q.isLoading} error={q.error} onRetry={() => void q.refetch()} />;
  if (sb.version === 0) return <Navigate to={`/storyboard/${sb.id}/schedule`} replace />;
  const v = Number(params.get('v')) || sb.version;
  const c = sb.counts ?? {};
  const s = c.sections ?? sb.outline?.sections?.length ?? 0;
  const nc = c.needs_confirmation ?? 0;
  const tbd = c.tbd ?? 0;
  const marks = [nc ? `확인 필요 ${nc}개` : '', tbd ? `TBD ${tbd}개` : ''].filter(Boolean);
  const sub = marks.length ? `섹션 ${s}개 · ${marks.join('와 ')}는 표시한 채로 저장했어요` : `섹션 ${s}개를 저장했어요`;
  const requestReview = () => void review.run(async () => {
    await sbApi.review(sb.id);
    await qc.invalidateQueries({ queryKey: sbKey(sb.id) });
    toast('내부 검토를 요청했어요');
  });
  const go = (card: HandoffCard) => void act.run(async () => {
    const r = await sbApi.handoff(sb.id, card.target);
    await qc.invalidateQueries({ queryKey: sbKey(sb.id) });
    navigate(r.route || card.route);
  });
  return (
    <Page label="저장 완료">
      <div className="sb-saved">
        <span className="sb-done-mark" aria-hidden="true"><Icon name="check" size={26} strokeWidth={3} /></span>
        <h1 className="sb-h1" style={{ marginTop: 6 }}>스토리보드 {vEul(v)} 저장했어요</h1>
        <span className="sb-muted" style={{ fontSize: 14 }}>{sub}</span>
        <div className="sb-saved__btns">
          <Link to={`/storyboard/${sb.id}/export`} className="sb-hbtn">내보내기</Link>
          <button type="button" className="sb-hbtn" onClick={requestReview} disabled={sb.review_requested || review.busy}
            title={sb.review_requested ? '이미 내부 검토를 요청했어요' : undefined}>
            {sb.review_requested ? '검토 요청함' : '내부 검토 요청'}
          </button>
          <Link to={`/storyboard/${sb.id}/outline/all`} className="sb-hbtn">전체 보기</Link>
        </div>
      </div>
      <div className="sb-col" style={{ gap: 10, marginTop: 10 }}>
        <span className="sb-nexthead">다음에 할 일</span>
        {cards.isLoading ? <SkeletonRows n={3} h={68} /> : (cards.data?.items ?? []).map((card) => (
          <button key={card.target} type="button" className={`sb-next${card.emphasized ? ' sb-next--hi' : ''}`} onClick={() => go(card)} disabled={act.busy}
            data-testid={`handoff-${card.target}`}>
            <span className={`sb-next__icon${card.emphasized ? ' sb-next__icon--hi' : ''}`}><FeatureIcon code={HANDOFF_ICON[card.target]} size={18} /></span>
            <span className="sb-col sb-grow" style={{ gap: 2 }}>
              <span className="sb-next__title">{card.title}{card.done && <span className="sb-subtle" style={{ fontSize: 12, fontWeight: 600, marginLeft: 8 }}>넘김</span>}</span>
              <span className="sb-next__desc sb-ell">{card.description}</span>
            </span>
            <Chevron />
          </button>
        ))}
      </div>
    </Page>
  );
}

/** SB4E — 5 내보내기 */
export function ExportScreen() {
  const { sbId = '' } = useParams();
  const q = useSb(sbId);
  const sb = q.data;
  useSbShell(sb, 5, { complete: true });
  const qc = useQueryClient();
  const act = useAction();
  const [fmt, setFmt] = useState<'pptx' | 'pdf'>('pptx');
  const [trace, setTrace] = useState(true);
  const [disc, setDisc] = useState(true);
  const [memo, setMemo] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const job = useJob(jobId, {
    onDone: (j) => {
      setJobId(null);
      void qc.invalidateQueries({ queryKey: sbKey(sbId) });
      if (j.status === 'succeeded' && j.result?.file_id) {
        const a = document.createElement('a');
        a.href = `${fileUrl(String(j.result.file_id))}?download=true`;
        a.download = String(j.result.name ?? '');
        document.body.appendChild(a);
        a.click();
        a.remove();
        toast('내보냈어요');
      } else {
        toast(jobErrorText(j.error), { action: { label: '다시 시도', onClick: () => run() } });
      }
    },
  });
  if (!sb) return <Gate loading={q.isLoading} error={q.error} onRetry={() => void q.refetch()} />;
  const n = sb.trace?.items?.length ?? 0;
  const ds = sb.outline?.discussions ?? [];
  const busy = act.busy || !!jobId;
  function run() {
    if (!sb) return;
    void act.run(async () => {
      const r = await sbApi.exportFile(sb.id, { format: fmt, options: { trace_appendix: trace, discussions: disc, internal_memo: memo } });
      setJobId(r.job_id);
    });
  }
  const opt = (on: boolean, label: string, hint: string, toggle?: () => void, fixed?: boolean) => (
    <button type="button" className="sb-opt" aria-pressed={on} aria-disabled={fixed || undefined} onClick={fixed ? undefined : toggle}
      title={fixed ? '항상 켜져 있어요' : undefined}>
      <span className={`sb-checkbox${fixed ? ' sb-checkbox--fixed' : on ? ' sb-checkbox--on' : ''}`} aria-hidden="true">{on && <Icon name="check" size={13} strokeWidth={3} />}</span>
      <span className="sb-opt__label">{label}</span>
      <span className="sb-opt__hint">{hint}</span>
    </button>
  );
  return (
    <Page label="내보내기">
      <Head eyebrow="공유 · 내보내기" title="어떻게 내보낼까요?" sub="고객에게 가는 파일에서는 내부 메모가 자동으로 빠져요." />
      <div className="sb-fmts" role="group" aria-label="형식">
        {(['pptx', 'pdf'] as const).map((f) => (
          <button key={f} type="button" className="sb-choice sb-fmtcard" aria-pressed={fmt === f} onClick={() => setFmt(f)} data-testid={`fmt-${f}`}>
            <span className={`sb-radio${fmt === f ? ' sb-radio--on' : ''}`} aria-hidden="true" />
            <span className="sb-fmt">{f === 'pptx' ? 'PPT' : 'PDF'}</span>
            <span className="sb-col" style={{ gap: 3 }}>
              <span className="sb-choice__title">{f === 'pptx' ? 'PPTX · 스토리보드 양식' : 'PDF'}</span>
              <span className="sb-choice__hint">{f === 'pptx' ? '섹션 표 그대로 · 편집할 수 있어요' : '공유 · 인쇄용'}</span>
            </span>
          </button>
        ))}
      </div>
      <div className="sb-card" role="group" aria-label="옵션">
        {opt(trace, '요구 추적표를 부록으로', `${n}행 · 연결 유형`, () => setTrace(!trace))}
        {opt(disc, `추가 논의 ${ds.length} 포함`, ds.map((d) => d.short).join(' · ') || '추가 논의 없음', () => setDisc(!disc))}
        {opt(true, '확인 필요 · TBD 표시 유지', '항상 켜져 있어요', undefined, true)}
        {opt(memo, '내부 목표 메모 포함', '내부 검토용 파일에만', () => setMemo(!memo))}
      </div>
      {jobId && (
        <div className="sb-band" role="status"><span className="wm-spinner" aria-hidden="true" /><span>내보내는 중… {job.progress ? `${Math.round(job.progress)}%` : ''}</span></div>
      )}
      <Bottom
        back={<Back to={`/storyboard/${sb.id}/saved?v=${sb.version}`}>저장 완료</Back>}
        primary={<Primary arrow={false} onClick={run} busy={busy} disabled={!sb.outline?.ready} disabledReason="목차를 다 쓴 뒤에 내보낼 수 있어요">내보내기</Primary>} />
    </Page>
  );
}
