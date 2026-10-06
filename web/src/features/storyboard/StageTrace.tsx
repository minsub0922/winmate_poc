/**
 * 4단계 `요구 추적` — SB4T(요약 3묶음) · SB4U(정리 1/n) · SB4U2(정리 완료) · SB4TD(추적표 전체) · SB4X(스토리보드에만 있는 것). §4.19–4.23
 */
import { useEffect, useMemo, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Link, Navigate, useNavigate, useParams } from 'react-router';
import { Icon } from '@/ui';
import {
  codeList, iga, sbApi, sbKey, useAction, useJobRefresh, useSb, useSbShell, type BadgeStyle, type Sb, type TraceItem,
} from './lib';
import { Back, Bottom, Chevron, Choice, FailBand, Gate, GreyLink, Head, Page, Primary, Q, SbBadge, SkeletonRows } from './parts';

const LINK_BADGE: Record<string, { label: string; tone: BadgeStyle }> = {
  direct: { label: '직접', tone: 'fill' }, interpreted: { label: '해석', tone: 'soft' }, extension: { label: '확장', tone: 'ext' },
  reviewing: { label: '검토', tone: 'dashed' }, unconfirmed: { label: '미확인', tone: 'tbd' }, deferred: { label: '보류', tone: 'muted' },
  excluded: { label: '제외', tone: 'tbd' },
};
const RESULT_BADGE: Record<string, BadgeStyle> = { 직접: 'fill', '확인 필요': 'soft', 보류: 'muted', 제외: 'tbd' };

function items(sb: Sb): TraceItem[] {
  return [...(sb.trace?.items ?? [])].sort((a, b) => a.code.localeCompare(b.code));
}
/**
 * 정리 순서: 이미 정리한 것(정리한 때 순) → 남은 정리할 요구(LLM 우선순위). 하나를 정리해도 앞 번호가 그대로라
 * `정리 {i} / {n}` 이 흔들리지 않고, 다시 들어오면 앞의 답을 고쳐 쓸 수 있다.
 */
function queue(sb: Sb): TraceItem[] {
  const items = (sb.trace?.items ?? []).filter((i) => i.question && (i.state === 'to_resolve' || i.state === 'resolved'));
  const done = items.filter((i) => i.state === 'resolved')
    .sort((a, b) => (a.resolution?.at ?? '').localeCompare(b.resolution?.at ?? '') || a.priority - b.priority);
  const open = items.filter((i) => i.state === 'to_resolve').sort((a, b) => a.priority - b.priority || a.code.localeCompare(b.code));
  return [...done, ...open];
}

function TraceWaiting({ sb }: { sb: Sb }) {
  return (
    <Page label="요구 추적">
      {sb.outline?.ready ? <SkeletonRows n={3} h={84} /> : (
        <>
          <Head title="아직 요구 추적이 없어요" sub="목차를 다 쓰면 정의서 항목을 섹션에 연결해요." />
          <Bottom back={<Back to={`/storyboard/${sb.id}/outline`}>목차</Back>} primary={<Primary to={`/storyboard/${sb.id}/outline`}>목차 보기</Primary>} />
        </>
      )}
    </Page>
  );
}

/** SB4T — 4 요구 추적 — 요약 3묶음 */
export function TraceScreen() {
  const { sbId = '' } = useParams();
  const q = useSb(sbId);
  const sb = q.data;
  useSbShell(sb, 4);
  const navigate = useNavigate();
  const qc = useQueryClient();
  const act = useAction();
  useJobRefresh(sbId, sb?.active_job?.job_id);
  if (!sb) return <Gate loading={q.isLoading} error={q.error} onRetry={() => void q.refetch()} />;
  if (!sb.trace?.items?.length) return <TraceWaiting sb={sb} />;
  const all = items(sb);
  const n = all.length;
  const toResolve = queue(sb).filter((i) => i.state === 'to_resolve');
  const ok = all.filter((i) => i.state === 'ok' || i.state === 'resolved');
  const owners = all.filter((i) => i.state === 'owner_check');
  const exts = sb.trace?.extensions ?? [];
  const k = ok.length;
  const firstIdx = queue(sb).findIndex((i) => i.state === 'to_resolve') + 1;
  const toSchedule = () => void act.run(async () => {
    if (sb.step < 5) await sbApi.patch(sb.id, { step: 5 });
    await qc.invalidateQueries({ queryKey: sbKey(sb.id) });
    navigate(`/storyboard/${sb.id}/schedule`);
  });
  return (
    <Page label="요구 추적">
      <Head title={k >= n ? `요구 ${n}개가 모두 잘 들어갔어요` : `요구 ${n}개 중 ${k}개는 잘 들어갔어요`}
        sub="남은 건 하나씩 정리하면 돼요. '직접'은 주제가 보인다는 뜻이지 범위 · 성능의 확정은 아니에요." />
      <div className="sb-tcards">
        {toResolve.length > 0 && (
          <Link to={`/storyboard/${sb.id}/trace/resolve/${firstIdx}`} className="sb-tcard sb-tcard--hi" data-testid="tcard-resolve">
            <span className="sb-tcard__n sb-tcard__n--on wm-num">{toResolve.length}</span>
            <span className="sb-col sb-grow" style={{ gap: 4 }}>
              <span className="sb-tcard__top"><span className="sb-tcard__title">정리할 요구</span>
                <span className="sb-tcard__codes sb-ell">{codeList(toResolve.map((i) => i.code))}</span><Q /></span>
              <span className="sb-tcard__desc sb-ell">넣을 곳이 없거나 내용이 비어 있어요 — 하나씩 물어볼게요</span>
            </span>
            <SbBadge tone="tbd">미확인 {toResolve.length}</SbBadge>
            <Chevron />
          </Link>
        )}
        <Link to={`/storyboard/${sb.id}/trace/all`} className="sb-tcard" data-testid="tcard-ok">
          <span className="sb-tcard__n wm-num">{ok.length}</span>
          <span className="sb-col sb-grow" style={{ gap: 4 }}>
            <span className="sb-tcard__top"><span className="sb-tcard__title">잘 들어간 요구</span>
              <span className="sb-tcard__codes sb-ell">{codeList(ok.map((i) => i.code))}</span></span>
            <span className="sb-tcard__desc sb-ell">직접 · 해석으로 섹션에 연결됐어요</span>
          </span>
          <SbBadge tone="fill">직접 · 해석</SbBadge>
          <Chevron />
        </Link>
        <Link to={`/storyboard/${sb.id}/trace/extensions`} className="sb-tcard" data-testid="tcard-ext">
          <span className="sb-tcard__n wm-num">{exts.length}</span>
          <span className="sb-col sb-grow" style={{ gap: 4 }}>
            <span className="sb-tcard__top"><span className="sb-tcard__title">스토리보드에만 있는 것</span><span className="sb-tcard__codes">확장</span></span>
            <span className="sb-tcard__desc sb-ell">{exts.length ? `${exts.map((e) => e.short).join(' · ')} — 고객 요구로 기록하지 않아요` : '요구에 없던 해결안이 아직 없어요'}</span>
          </span>
          <SbBadge tone="ext">확장</SbBadge>
          <Chevron />
        </Link>
      </div>
      {owners.slice(0, 2).map((i) => (
        <div key={i.rq_item_id} className="sb-ownerline" data-testid="owner-line">
          <SbBadge tone="muted">담당 확인</SbBadge>
          <span className="sb-ell">{i.code} {i.short} 역할은 {iga(i.owner_note || '담당')} 확인 중이에요</span>
        </div>
      ))}
      <Bottom
        back={<GreyLink to={`/storyboard/${sb.id}/trace/all`}>추적표 전체 보기</GreyLink>}
        links={toResolve.length > 0 ? <GreyLink onClick={toSchedule} disabled={act.busy}>나중에 하고 일정으로</GreyLink> : undefined}
        primary={toResolve.length > 0
          ? <Primary q to={`/storyboard/${sb.id}/trace/resolve/${firstIdx}`}>{toResolve.length}개 정리하기</Primary>
          : <Primary onClick={toSchedule} busy={act.busy}>일정 · 분담으로</Primary>} />
    </Page>
  );
}

/** SB4U — 4 요구 정리 {i}/{n} */
export function ResolveScreen() {
  const { sbId = '', i = '1' } = useParams();
  const idx = Math.max(1, Number(i) || 1);
  const q = useSb(sbId);
  const sb = q.data;
  useSbShell(sb, 4);
  const navigate = useNavigate();
  const qc = useQueryClient();
  const act = useAction();
  const list = useMemo(() => (sb ? queue(sb) : []), [sb]);
  const item = list[idx - 1];
  const [optId, setOptId] = useState<string | null>(null);
  const [reason, setReason] = useState('');
  useEffect(() => {
    if (!item) return;
    setOptId(item.resolution?.option_id ?? item.question?.recommended_option_id ?? null);
    setReason(item.resolution?.reason ?? '');
  }, [item?.rq_item_id]);  // eslint-disable-line react-hooks/exhaustive-deps
  if (!sb) return <Gate loading={q.isLoading} error={q.error} onRetry={() => void q.refetch()} />;
  if (!item?.question) return <Navigate to={list.length ? `/storyboard/${sb.id}/trace/resolved` : `/storyboard/${sb.id}/trace`} replace />;
  const n = list.length;
  const last = idx >= n;
  const nextCode = list[idx]?.code;
  const opt = item.question.options.find((o) => o.id === optId);
  const go = () => (last ? navigate(`/storyboard/${sb.id}/trace/resolved`) : navigate(`/storyboard/${sb.id}/trace/resolve/${idx + 1}`));
  const submit = () => void act.run(async () => {
    if (!opt) return;
    await sbApi.resolve(sb.id, item.rq_item_id, { kind: opt.kind, option_id: opt.id, reason: opt.kind === 'exclude' ? reason.trim() : null });
    await qc.invalidateQueries({ queryKey: sbKey(sb.id) });
    go();
  });
  const ask = () => void act.run(async () => {
    await sbApi.resolve(sb.id, item.rq_item_id, { kind: 'ask_customer' });
    await qc.invalidateQueries({ queryKey: sbKey(sb.id) });
    go();
  });
  const needReason = opt?.kind === 'exclude' && !reason.trim();
  return (
    <Page label={`정리 ${idx} / ${n}`}>
      <Head q eyebrow={`정리 ${idx} / ${n} · ${item.code} ${item.short}`} title={item.question.text} info={item.question.info || undefined} />
      <div className="sb-choices" role="group" aria-label={item.question.text}>
        {item.question.options.map((o) => (
          <Choice key={o.id} pressed={o.id === optId} weight={600} onClick={() => setOptId(o.id)} title={o.label} role={o.hint} />
        ))}
      </div>
      {opt?.kind === 'exclude' && (
        <label className="sb-field">
          <span className="sb-field__label">제외 사유</span>
          <input className="sb-input" value={reason} onChange={(e) => setReason(e.target.value)} placeholder="제외 사유" aria-required="true" autoFocus />
        </label>
      )}
      <Bottom
        back={<GreyLink onClick={ask} disabled={act.busy}>모르겠어요 → 고객에게 묻기</GreyLink>}
        primary={(
          <Primary onClick={submit} busy={act.busy} disabled={!opt || needReason}
            disabledReason={!opt ? '넣을 곳을 골라 주세요' : '제외 사유를 적어 주세요'}>
            {last ? '정리 마치기' : `다음 · ${nextCode}`}
          </Primary>
        )} />
    </Page>
  );
}

/** SB4U2 — 4 요구 정리 완료 */
export function ResolvedScreen() {
  const { sbId = '' } = useParams();
  const q = useSb(sbId);
  const sb = q.data;
  useSbShell(sb, 4);
  const navigate = useNavigate();
  const qc = useQueryClient();
  const act = useAction();
  useJobRefresh(sbId, sb?.active_job?.job_id);
  if (!sb) return <Gate loading={q.isLoading} error={q.error} onRetry={() => void q.refetch()} />;
  const done = queue(sb).filter((i) => i.state === 'resolved' && i.resolution);
  const shown = done.slice(0, 7);
  const toSchedule = () => void act.run(async () => {
    if (sb.step < 5) await sbApi.patch(sb.id, { step: 5 });
    await qc.invalidateQueries({ queryKey: sbKey(sb.id) });
    navigate(`/storyboard/${sb.id}/schedule`);
  });
  return (
    <Page label="요구 정리 완료">
      <Head q eyebrow="요구 정리 · 완료" title={`${done.length}개를 정리했어요`}
        sub="버린 요구는 없어요. 모두 추적표에 남고, 고객에게 물을 것은 질문지에 더했어요." />
      <div className="sb-card" data-testid="resolved-rows">
        {shown.map((i) => (
          <div key={i.rq_item_id} className="sb-resrow">
            <span className="sb-resrow__code wm-num">{i.code}</span>
            <span className="sb-col sb-grow" style={{ gap: 3 }}>
              <span className="sb-before sb-ell">{i.short}</span>
              <span className="sb-resrow__result sb-ell">{i.resolution!.result_label}</span>
            </span>
            <SbBadge tone={RESULT_BADGE[i.resolution!.badge] ?? 'muted'}>{i.resolution!.badge}</SbBadge>
          </div>
        ))}
        {done.length > shown.length && (
          <Link to={`/storyboard/${sb.id}/trace/all`} className="sb-resrow sb-resrow--more">외 {done.length - shown.length}개 · 추적표에서 보기</Link>
        )}
        {!done.length && <div className="sb-resrow"><span className="sb-muted">아직 정리한 요구가 없어요.</span></div>}
      </div>
      <Bottom
        back={<GreyLink to={`/storyboard/${sb.id}/trace/all`}>추적표 전체 보기</GreyLink>}
        primary={<Primary onClick={toSchedule} busy={act.busy}>일정 · 분담으로</Primary>} />
    </Page>
  );
}

/** SB4TD — 4 추적표 전체 보기(스텝바 없음) */
export function TraceAllScreen() {
  const { sbId = '' } = useParams();
  const q = useSb(sbId);
  const sb = q.data;
  useSbShell(sb, null);
  useJobRefresh(sbId, sb?.active_job?.job_id);
  if (!sb) return <Gate loading={q.isLoading} error={q.error} onRetry={() => void q.refetch()} />;
  const all = items(sb);
  const exts = sb.trace?.extensions ?? [];
  return (
    <Page variant="wide" label="요구 → 스토리보드 추적표">
      <div className="sb-widehead">
        <div className="sb-col sb-grow" style={{ gap: 3 }}>
          <Link to={`/storyboard/${sb.id}/trace`} className="sb-crumb"><Icon name="chevronLeft" size={13} strokeWidth={2.6} />요구 추적</Link>
          <h1 className="sb-h1" style={{ fontSize: 24 }}>요구 → 스토리보드 추적표</h1>
        </div>
        <Link to={`/storyboard/${sb.id}/trace/extensions`} className="sb-hbtn">스토리보드에만 있는 것 {exts.length}</Link>
      </div>
      {!all.length ? <FailBand message="아직 추적표가 없어요. 목차를 다 쓰면 만들어져요." /> : (
        <div className="sb-table" data-testid="trace-table">
          <div className="sb-table__head sb-grid-t" role="row"><span /><span>고객 요구</span><span>스토리보드에 들어간 곳</span><span>연결</span></div>
          {all.map((i) => (
            <div key={i.rq_item_id} className="sb-table__row sb-grid-t" role="row" data-testid="trace-row" data-state={i.state}>
              <span className="sb-code wm-num">{i.code}</span>
              <span className="sb-ell" style={{ fontSize: 13.5 }} title={i.text}>{i.short}</span>
              <span className="sb-ell sb-celldir">{i.places_label || '—'}</span>
              <span className="sb-badges">
                {(i.link_types ?? []).map((lt) => <SbBadge key={lt} tone={LINK_BADGE[lt]?.tone ?? 'muted'}>{LINK_BADGE[lt]?.label ?? lt}</SbBadge>)}
              </span>
            </div>
          ))}
          <div className="sb-table__legend" data-testid="legend">
            <b>직접</b>&nbsp;주제가 보임 ·&nbsp;<b>해석</b>&nbsp;새 콘셉트로 ·&nbsp;<b>확장</b>&nbsp;요구에 없던 해결안 ·&nbsp;<b>검토</b>&nbsp;논의 중 ·&nbsp;<b>미확인</b>&nbsp;담당 항목이 안 보임
          </div>
        </div>
      )}
    </Page>
  );
}

/** SB4X — 4 스토리보드에만 있는 것 */
export function ExtensionsScreen() {
  const { sbId = '' } = useParams();
  const q = useSb(sbId);
  const sb = q.data;
  useSbShell(sb, 4);
  const navigate = useNavigate();
  const qc = useQueryClient();
  const act = useAction();
  if (!sb) return <Gate loading={q.isLoading} error={q.error} onRetry={() => void q.refetch()} />;
  const exts = sb.trace?.extensions ?? [];
  const ack = () => void act.run(async () => {
    await sbApi.ackExtensions(sb.id);
    await qc.invalidateQueries({ queryKey: sbKey(sb.id) });
    navigate(`/storyboard/${sb.id}/trace`);
  });
  return (
    <Page label="스토리보드에만 있는 것">
      <Head eyebrow="요구 추적 · 확장" title={`스토리보드에만 있는 것 ${exts.length}`}
        sub="요구사항에 없던 해결안이에요. 제안 옵션으로만 넘기고 고객 요구로 바꾸지 않아요." />
      <div className="sb-card" data-testid="extensions">
        {exts.map((e) => (
          <div key={e.id} className="sb-extrow">
            <span className="sb-extrow__name sb-ell">{e.name}</span>
            <span className="sb-extrow__where sb-ell">{e.where_label}</span>
            {e.status === 'reviewing' ? <SbBadge tone="line">검토 중</SbBadge> : <SbBadge tone="ext">확장</SbBadge>}
          </div>
        ))}
        {!exts.length && <div className="sb-extrow"><span className="sb-muted">요구에 없던 해결안이 아직 없어요.</span></div>}
      </div>
      <Bottom
        back={<Back to={`/storyboard/${sb.id}/trace`}>요구 추적</Back>}
        primary={<Primary onClick={ack} busy={act.busy}>확인했어요</Primary>} />
    </Page>
  );
}
