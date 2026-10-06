/**
 * 필요할 때 — SB3R(수정 요청) · SB3R2(바뀐 곳 확인) · SB3V(버전 비교 · 미리 보기). §4.16–4.18
 */
import { useEffect, useMemo, useRef, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Navigate, useNavigate, useParams, useSearchParams } from 'react-router';
import { Icon } from '@/ui';
import {
  latestRqVersion, sbApi, sbKey, sectionLabel, shortDate, useAction, useJobRefresh, useSb, useSbShell, vRo,
  type ChangeEntry, type Revision, type Sb,
} from './lib';
import { Back, Bottom, FailBand, Gate, GreyLink, Head, LoadingHead, Page, Primary, SbBadge, Seg, SkeletonRows, Tok } from './parts';

type Target = { kind: 'section' | 'space'; id: string; label: string; group: 'start' | 'part1' | 'part2' | 'part3' | 'end' };
const CHIPS = ['더 짧게', '비교표로', '주장은 각주로'];
const GROUP_ALL: Record<Target['group'], string> = { start: '시작 전체', part1: 'Part 1 전체', part2: 'Part 2 전체', part3: 'Part 3 전체', end: '마무리 전체' };
const STATUS_RANK: Record<string, number> = { needs_confirmation: 0, reviewing: 1, tbd: 2 };

function targetsOf(sb: Sb): Target[] {
  const secs = [...(sb.outline?.sections ?? [])].sort((a, b) => a.order - b.order);
  const out: Target[] = [];
  for (const s of secs) {
    out.push({ kind: 'section', id: s.id, label: sectionLabel(s), group: s.group_key });
    if (s.group_key === 'part2') {
      for (const sp of [...(sb.outline?.spaces ?? [])].sort((a, b) => a.order - b.order)) {
        out.push({ kind: 'space', id: sp.id, label: `Part 2 ${sp.name}`, group: 'part2' });
      }
    }
  }
  return out;
}

function defaultTarget(sb: Sb, targets: Target[]): Target | undefined {
  const secs = (sb.outline?.sections ?? []).filter((s) => s.status in STATUS_RANK && s.group_key !== 'part2')
    .sort((a, b) => STATUS_RANK[a.status] - STATUS_RANK[b.status] || a.order - b.order);
  const pick = secs[0] ?? (sb.outline?.sections ?? []).find((s) => s.key === 'overview');
  return targets.find((t) => t.id === pick?.id) ?? targets[0];
}

/** SB3R — 수정 요청 */
export function ReviseScreen() {
  const { sbId = '' } = useParams();
  const [params] = useSearchParams();
  const q = useSb(sbId);
  const sb = q.data;
  useSbShell(sb, 3);
  const navigate = useNavigate();
  const act = useAction();
  const fromRev = params.get('from');
  const prev = useQuery({
    queryKey: ['storyboard', sbId, 'revision', fromRev],
    queryFn: () => sbApi.revision(sbId, fromRev!),
    enabled: !!fromRev,
  });
  const targets = useMemo(() => (sb ? targetsOf(sb) : []), [sb]);
  const [target, setTarget] = useState<Target | null>(null);
  const [text, setText] = useState('');
  const [chips, setChips] = useState<string[]>([]);
  const [scope, setScope] = useState<'target' | 'group'>('target');
  const [menu, setMenu] = useState(false);
  const inited = useRef(false);
  useEffect(() => {
    if (inited.current || !sb || !targets.length) return;
    if (fromRev && !prev.data && !prev.isError) return;
    inited.current = true;
    const r = prev.data;
    const want = r?.target.id ?? params.get('target');
    setTarget(targets.find((t) => t.id === want) ?? defaultTarget(sb, targets) ?? null);
    if (r) { setText(r.instruction); setChips(r.chips ?? []); setScope(r.scope); }
  }, [sb, targets, prev.data, prev.isError, fromRev, params]);
  if (!sb) return <Gate loading={q.isLoading} error={q.error} onRetry={() => void q.refetch()} />;
  if (!sb.outline?.ready) return <Navigate to={`/storyboard/${sb.id}/outline`} replace />;

  const submit = () => void act.run(async () => {
    if (!target) return;
    const r = await sbApi.createRevision(sb.id, {
      target: { kind: target.kind, id: target.id, label: target.label }, scope, instruction: text.trim(), chips,
    });
    const revId = r.ref?.id;
    if (revId) navigate(`/storyboard/${sb.id}/revise/${revId}`);
  });
  const empty = !text.trim() && !chips.length;
  return (
    <Page label="수정 요청">
      <Head eyebrow="목차 · 수정 요청" title="어떻게 바꿀까요?" sub="섹션 하나씩 다시 써요. 검토 중인 내용과 [확인 필요]는 그대로 둬요." />
      <div className="sb-revcard">
        <button type="button" className="sb-target" aria-haspopup="listbox" aria-expanded={menu} onClick={() => setMenu(!menu)} data-testid="revise-target">
          <span className="sb-target__k">고칠 섹션</span>
          <b className="sb-target__v sb-ell">{target?.label ?? '—'}</b>
          <Icon name="chevronDown" size={13} strokeWidth={2.4} />
        </button>
        {menu && (
          <div className="sb-menu" role="listbox" aria-label="고칠 섹션">
            {targets.map((t) => (
              <button key={t.id} type="button" role="option" aria-selected={t.id === target?.id}
                style={t.kind === 'space' ? { paddingLeft: 24 } : undefined}
                onClick={() => { setTarget(t); setMenu(false); }}>{t.label}</button>
            ))}
          </div>
        )}
        <label className="wm-sr-only" htmlFor="sb-rev-text">어떻게 바꿀까요</label>
        <textarea id="sb-rev-text" className="sb-revtext" value={text} onChange={(e) => setText(e.target.value)}
          placeholder="예) 경영진용으로 짧게. 성과 3가지는 한 장 비교표로, 임대료 프리미엄 주장은 출처 확인 전까지 각주로" />
        <div className="sb-revchips">
          {CHIPS.map((c) => (
            <button key={c} type="button" className="sb-chip" aria-pressed={chips.includes(c)}
              onClick={() => setChips(chips.includes(c) ? chips.filter((x) => x !== c) : [...chips, c])}>{c}</button>
          ))}
        </div>
      </div>
      <div className="sb-scope">
        <span className="sb-scope__k">다시 쓸 범위</span>
        <Seg<'target' | 'group'> label="다시 쓸 범위" value={scope} onChange={setScope}
          items={[{ value: 'target', label: '이 섹션만' }, { value: 'group', label: target ? GROUP_ALL[target.group] : '묶음 전체' }]} />
      </div>
      <Bottom
        back={<Back to={`/storyboard/${sb.id}/outline`}>목차</Back>}
        primary={<Primary onClick={submit} busy={act.busy} disabled={empty || !target} disabledReason="요청을 적거나 빠른 칩을 골라 주세요">다시 쓰기</Primary>} />
    </Page>
  );
}

const REV_BADGE: Record<string, { label: string; tone: 'fill' | 'muted' }> = {
  changed: { label: '바뀜', tone: 'fill' }, added: { label: '새 줄', tone: 'fill' }, removed: { label: '삭제', tone: 'fill' }, kept: { label: '유지', tone: 'muted' },
};

/** SB3R2 — 수정 요청 · 바뀐 곳 확인 */
export function RevisionScreen() {
  const { sbId = '', revId = '' } = useParams();
  const q = useSb(sbId);
  const sb = q.data;
  useSbShell(sb, 3);
  const navigate = useNavigate();
  const qc = useQueryClient();
  const act = useAction();
  const rev = useQuery({
    queryKey: ['storyboard', sbId, 'revision', revId],
    queryFn: () => sbApi.revision(sbId, revId),
    refetchInterval: (qq) => (qq.state.data?.status === 'running' ? 1500 : false),
  });
  useJobRefresh(sbId, rev.data?.status === 'running' ? rev.data.job_id : null, () => void rev.refetch());
  if (!sb) return <Gate loading={q.isLoading} error={q.error} onRetry={() => void q.refetch()} />;
  const r: Revision | undefined = rev.data;
  const back = <Back to={`/storyboard/${sb.id}/revise?from=${revId}`}>요청 고치기</Back>;
  if (!r || r.status === 'running') {
    return (
      <Page label="수정 요청 확인">
        <div className="sb-head"><span className="sb-eyebrow">수정 요청 · 확인</span></div>
        {rev.isError ? <FailBand message="수정안을 불러오지 못했어요." onRetry={() => void rev.refetch()} /> : (
          <>
            <LoadingHead title="다시 쓰는 중이에요" sub={r ? `${r.target.label} · 바뀐 줄만 보여 드릴게요.` : undefined} />
            <SkeletonRows n={4} h={68} />
          </>
        )}
        <Bottom back={back} primary={<Primary arrow={false} disabled disabledReason="다시 쓰는 중이에요">적용</Primary>} />
      </Page>
    );
  }
  if (r.status === 'failed') {
    return (
      <Page label="수정 요청 확인">
        <Head eyebrow="수정 요청 · 확인" title="다시 쓰지 못했어요" sub={`${r.target.label} · 요청을 고쳐 다시 시도해 주세요.`} />
        <FailBand message={String((r.error as { message?: string } | null)?.message ?? '수정안을 만들지 못했어요.')} />
        <Bottom back={back} primary={<Primary to={`/storyboard/${sb.id}/outline`}>목차</Primary>} />
      </Page>
    );
  }
  const done = r.status === 'applied' || r.status === 'discarded';
  const apply = () => void act.run(async () => {
    const updated = await sbApi.applyRevision(sb.id, r.id);
    qc.setQueryData(sbKey(sb.id), updated);
    navigate(`/storyboard/${sb.id}/outline`);
  });
  const discard = () => void act.run(async () => {
    await sbApi.discardRevision(sb.id, r.id);
    await qc.invalidateQueries({ queryKey: sbKey(sb.id) });
    navigate(`/storyboard/${sb.id}/outline`);
  });
  const multi = new Set((r.rows ?? []).map((x) => x.section_label).filter(Boolean)).size > 1;
  return (
    <Page label="수정 요청 확인">
      <Head eyebrow="수정 요청 · 확인" title={`${r.changed_count}줄이 바뀌어요`}
        sub={`${r.scope === 'group' ? r.scope_label : r.target.label} · 위는 지금, 아래는 바뀐 문장이에요.`} />
      {done && <div className="sb-band sb-band--plain">{r.status === 'applied' ? '이미 적용한 수정안이에요.' : '적용하지 않은 수정안이에요.'}</div>}
      <div className="sb-card" data-testid="revision-rows">
        {(r.rows ?? []).map((row, i) => {
          const b = REV_BADGE[row.kind];
          return (
            <div key={i} className="sb-revrow" data-kind={row.kind}>
              <span className="sb-col sb-grow" style={{ gap: 4 }}>
                <span className={`sb-before sb-ell${row.kind === 'changed' || row.kind === 'removed' ? ' sb-strike' : ''}`}>
                  {multi && row.section_label ? <b className="sb-subtle">{row.section_label} · </b> : null}
                  {row.kind === 'added' ? '없음' : <Tok text={row.before ?? ''} />}
                </span>
                {row.kind === 'kept'
                  ? <span className="sb-after sb-after--kept sb-ell">{row.reason ?? '그대로'}</span>
                  : <span className="sb-after sb-ell">{row.kind === 'removed' ? '없음' : <Tok text={row.after ?? ''} />}</span>}
              </span>
              <SbBadge tone={b.tone}>{b.label}</SbBadge>
            </div>
          );
        })}
      </div>
      <Bottom
        back={back}
        links={<GreyLink onClick={discard} disabled={act.busy || done}>적용하지 않기</GreyLink>}
        primary={<Primary arrow={false} onClick={apply} busy={act.busy} disabled={done} disabledReason="이미 처리한 수정안이에요">적용</Primary>} />
    </Page>
  );
}

const CHG_BADGE: Record<ChangeEntry['kind'], { label: string; tone: 'fill' | 'muted' }> = {
  changed: { label: '변경', tone: 'fill' }, added: { label: '추가', tone: 'fill' }, removed: { label: '삭제', tone: 'fill' }, kept: { label: '유지', tone: 'muted' },
};

function ChangeRows({ rows, onRevert, busy }: { rows: ChangeEntry[]; onRevert?: (c: ChangeEntry) => void; busy?: boolean }) {
  return (
    <div className="sb-card" data-testid="change-rows">
      {rows.length === 0 && <div className="sb-revrow"><span className="sb-muted">바뀐 곳이 없어요.</span></div>}
      {rows.map((c) => (
        <div key={c.id} className="sb-chgrow" data-kind={c.kind} data-testid="change-row">
          <span className="sb-col sb-grow" style={{ gap: 5 }}>
            <span className="sb-chgrow__head">
              <span className="sb-chgrow__place">{c.place_label}</span>
              <SbBadge tone={CHG_BADGE[c.kind].tone}>{CHG_BADGE[c.kind].label}</SbBadge>
              {(c.tags ?? []).includes('extension') && <SbBadge tone="ext">확장</SbBadge>}
              {(c.tags ?? []).includes('author_supplemented') && <SbBadge tone="dashed">작성자 보완</SbBadge>}
            </span>
            <span className="sb-chgrow__diff">
              <span className={`sb-ell${c.kind === 'kept' ? ' sb-subtle' : ' sb-strike'}`} style={{ flexShrink: 1 }}><Tok text={c.before_summary} /></span>
              <Icon name="arrowRight" size={13} />
              <span className="sb-ell" style={{ color: 'var(--wm-text)' }}><Tok text={c.after_summary} /></span>
            </span>
          </span>
          {onRevert && c.revertible && c.kind !== 'kept' && (
            <button type="button" className="sb-smallbtn" onClick={() => onRevert(c)} disabled={busy}>되돌리기</button>
          )}
        </div>
      ))}
    </div>
  );
}

/** SB3V — 버전 비교 · 미리 보기(RQ7B) */
export function VersionsScreen() {
  const { sbId = '' } = useParams();
  const [params, setParams] = useSearchParams();
  const previewRq = params.get('preview_rq');
  const q = useSb(sbId);
  const sb = q.data;
  useSbShell(sb, 3);
  useJobRefresh(sbId, sb?.active_job?.job_id);
  if (!sb) return <Gate loading={q.isLoading} error={q.error} onRetry={() => void q.refetch()} />;
  if (previewRq) return <PreviewMode sb={sb} rq={previewRq} reply={params.get('reply')} syp={params.get('syp')} setSyp={(s) => setParams({ preview_rq: previewRq, ...(params.get('reply') ? { reply: params.get('reply')! } : {}), syp: s }, { replace: true })} />;
  return (
    <CompareMode sb={sb} from={params.get('from')} to={params.get('to')}
      pin={(f, t) => { if (!params.get('from') && !params.get('to')) setParams({ from: f, to: t }, { replace: true }); }} />
  );
}

function CompareMode({ sb, from, to, pin }: { sb: Sb; from: string | null; to: string | null; pin: (from: string, to: string) => void }) {
  const qc = useQueryClient();
  const act = useAction();
  const syncing = sb.active_job?.kind === 'sb.rq_sync';
  const cmp = useQuery({
    queryKey: ['storyboard', sb.id, 'compare', from, to, sb.revision, sb.version],
    queryFn: () => sbApi.compare(sb.id, from ? Number(from) : null, to),
    enabled: sb.version > 0 && !syncing,
  });
  // 처음 정한 비교 쌍을 주소에 고정 — 마지막 변경을 되돌려도 v{a} → v{b} 가 바뀌지 않게
  useEffect(() => {
    if (cmp.data) pin(String(cmp.data.from.version), cmp.data.to.is_draft ? 'draft' : String(cmp.data.to.version));
  }, [cmp.data]);  // eslint-disable-line react-hooks/exhaustive-deps
  const back = <Back to={`/storyboard/${sb.id}/outline`}>목차</Back>;
  if (sb.version === 0) {
    return (
      <Page label="버전">
        <Head eyebrow="목차 · 버전" title="저장한 버전이 아직 없어요" sub="저장한 버전이 생기면 비교할 수 있어요. 버전은 일정 · 분담에서 저장하고 공유할 때 생겨요." />
        <Bottom back={back} primary={<Primary to={`/storyboard/${sb.id}/outline`}>목차 보기</Primary>} />
      </Page>
    );
  }
  if (syncing || !cmp.data) {
    return (
      <Page label="버전">
        <div className="sb-head"><span className="sb-eyebrow">목차 · 버전</span></div>
        {cmp.isError ? <FailBand message="버전을 비교하지 못했어요." onRetry={() => void cmp.refetch()} />
          : <><LoadingHead title={syncing ? '요구사항 정의서 새 버전을 반영하는 중이에요' : '버전을 비교하는 중이에요'} /><SkeletonRows n={4} h={70} /></>}
        <Bottom back={back} />
      </Page>
    );
  }
  const c = cmp.data;
  const a = c.from.version;
  const b = c.to.version;
  const revert = (row: ChangeEntry) => void act.run(async () => {
    const updated = await sbApi.revert(sb.id, row.id);
    qc.setQueryData(sbKey(sb.id), updated);
    await qc.invalidateQueries({ queryKey: ['storyboard', sb.id, 'compare'] });
  });
  const causes = c.causes ?? [];
  return (
    <Page label="버전 비교">
      <Head eyebrow="목차 · 버전" title={`v${a} → v${b}, 바뀐 곳 ${c.count}`}
        actions={(
          <span className="sb-verpath">v{a}{c.from.note ? ` ${c.from.note}` : ''} · {shortDate(c.from.date)} → <b>v{b} · {c.to.is_draft ? '오늘' : shortDate(c.to.date)}</b></span>
        )}
        sub={c.count === 0 ? `v${b}에서 바뀐 곳이 없어요.` : `v${b} = ${causes.length ? causes.join(' · ') : '작업본'}. ${c.revertible ? '하나씩 되돌릴 수 있어요.' : ''}`.trim()} />
      <ChangeRows rows={c.rows ?? []} onRevert={c.revertible ? revert : undefined} busy={act.busy} />
      <Bottom back={back} primary={<Primary to={`/storyboard/${sb.id}/outline`}>{vRo(b)} 계속</Primary>} />
    </Page>
  );
}

function PreviewMode({ sb, rq, reply, syp, setSyp }: { sb: Sb; rq: string; reply: string | null; syp: string | null; setSyp: (s: string) => void }) {
  const navigate = useNavigate();
  const asked = useRef(false);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    if (syp || asked.current) return;
    asked.current = true;
    (async () => {
      // 답변(reply)이 없으면 정의서 최신 저장 버전으로 미리 본다
      const toVersion = reply ? null : await latestRqVersion(rq).catch(() => null);
      const r = await sbApi.sync(sb.id, { requirement_id: rq, reply_id: reply, to_version: toVersion, dry_run: true });
      if (r.ref?.id) setSyp(r.ref.id);
    })().catch((e) => setErr((e as Error).message || '미리 보기를 만들지 못했어요.'));
  }, [syp, sb.id, rq, reply, setSyp]);
  const pv = useQuery({
    queryKey: ['storyboard', sb.id, 'preview', syp],
    queryFn: () => sbApi.preview(sb.id, syp!),
    enabled: !!syp,
    refetchInterval: (qq) => (qq.state.data?.status === 'running' || !qq.state.data ? 1500 : false),
  });
  const backBtn = <Back onClick={() => (window.history.length > 1 ? navigate(-1) : navigate(`/requirements/${rq}`))}>뒤로</Back>;
  const p = pv.data;
  const a = p?.from_version ?? sb.version;
  return (
    <Page label="버전 미리 보기">
      {!p || p.status === 'running' ? (
        <>
          <div className="sb-head"><span className="sb-eyebrow">목차 · 버전 · 미리 보기</span></div>
          {err ? <FailBand message={err} /> : <><LoadingHead title="반영하면 어떻게 바뀌는지 보는 중이에요" /><SkeletonRows n={4} h={70} /></>}
        </>
      ) : p.status === 'failed' ? (
        <>
          <Head eyebrow="목차 · 버전 · 미리 보기" title="미리 보기를 만들지 못했어요" />
          <FailBand message={String((p.error as { message?: string } | null)?.message ?? '잠시 후 다시 시도해 주세요.')} />
        </>
      ) : (
        <>
          <Head eyebrow="목차 · 버전 · 미리 보기" title={`${a > 0 ? `v${a}` : sb.draft_label} → 반영 후, 바뀐 곳 ${p.count}`}
            sub="요구사항 정의서 답변을 반영하면 이렇게 바뀌어요." />
          <ChangeRows rows={p.rows ?? []} />
        </>
      )}
      <Bottom back={backBtn} />
    </Page>
  );
}

