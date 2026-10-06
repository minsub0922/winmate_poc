/**
 * 3단계 `목차 · 서사` — SB3G(만드는 중, 자동 넘어감) · SB3(묶음 5) · SB3P(Part 2 공간) · SB3D(전체 보기). §4.10–4.13
 */
import { Fragment, useEffect, useMemo, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Link, useLocation, useNavigate, useParams, useSearchParams } from 'react-router';
import { Icon, Skeleton, toast } from '@/ui';
import {
  audienceNames, copyText, emptySpaces, emptySpacesLabel, sbApi, sbKey, sectionLabel, selectedDirection, spaceRoute,
  STATUS_STYLE, STATUS_TEXT, stepsFrom, useAction, useJobRefresh, useSb, useSbShell, vIga, type Group, type Sb, type Section, type Space,
} from './lib';
import { Back, Bottom, Chevron, FailBand, Gate, GreyLink, Head, Page, Primary, Q, SbBadge, Tok } from './parts';

const SECTION_COUNT: Record<number, number> = { 12: 8, 20: 11, 30: 14 };
const STEP_KEYS = ['classify', 'map_axes', 'write_sections', 'trace'] as const;

/** 작업본 배지: `v1 초안`(초안) · `v2`(저장본과 같음) */
function DraftBadge({ sb }: { sb: Sb }) {
  return <SbBadge tone={sb.draft_label.includes('초안') ? 'draft' : 'muted'}>{sb.draft_label}</SbBadge>;
}

function HeadActions({ sb, share }: { sb: Sb; share?: boolean }) {
  const act = useAction();
  const doShare = () => void act.run(async () => {
    const r = await sbApi.share(sb.id);
    const url = r.url.startsWith('http') ? r.url : `${window.location.origin}${r.url}`;
    toast((await copyText(url)) ? '링크를 복사했어요' : url);
  });
  return (
    <>
      <Link to={`/storyboard/${sb.id}/revise`} className="sb-hbtn"><Icon name="edit" size={13} />수정 요청</Link>
      {sb.version > 0
        ? <Link to={`/storyboard/${sb.id}/versions`} className="sb-hbtn">버전</Link>
        : <button type="button" className="sb-hbtn" disabled title="저장한 버전이 생기면 비교할 수 있어요">버전</button>}
      {share
        ? <button type="button" className="sb-hbtn" onClick={doShare} disabled={act.busy}>공유</button>
        : <Link to={`/storyboard/${sb.id}/outline/all`} className="sb-hbtn">전체 보기</Link>}
    </>
  );
}

/** `/storyboard/:sbId/outline` — 목차 잡이 돌면 SB3G, 끝나면 그 자리에서 SB3 */
export function OutlineScreen() {
  const { sbId = '' } = useParams();
  const [params, setParams] = useSearchParams();
  const partial = params.get('view') === 'partial';
  const q = useSb(sbId);
  const sb = q.data;
  useSbShell(sb, 3);
  const job = useJobRefresh(sbId, sb?.active_job?.job_id);
  const generating = sb?.active_job?.kind === 'sb.outline';
  useEffect(() => {
    if (sb && !generating && partial) setParams({}, { replace: true });
  }, [sb, generating, partial, setParams]);
  if (!sb) return <Gate loading={q.isLoading} error={q.error} onRetry={() => void q.refetch()} />;
  if (generating && !partial) return <Generating sb={sb} events={job.events} progress={job.progress} onPartial={() => setParams({ view: 'partial' })} />;
  if (!sb.outline || (!sb.outline.ready && !generating)) return <NotReady sb={sb} />;
  return <OutlineView sb={sb} partial={generating} />;
}

/** SB3G — 3 목차 만드는 중 */
function Generating({ sb, events, progress, onPartial }: { sb: Sb; events: Parameters<typeof stepsFrom>[0]; progress: number; onPartial: () => void }) {
  const steps = stepsFrom(events);
  const writing = sb.outline?.writing;
  const stage = writing?.stage ?? (sb.outline ? 'map_axes' : 'classify');
  const stageIdx = Math.max(0, STEP_KEYS.indexOf(stage as (typeof STEP_KEYS)[number]));
  const n = sb.requirement_ref?.item_count ?? 0;
  const k = sb.direction?.internal_goal_count ?? 0;
  const total = writing?.total || steps.write_sections?.total || SECTION_COUNT[sb.settings?.volume?.value ?? 20] || 11;
  const done = steps.write_sections?.done ?? writing?.done ?? 0;
  const labels: Record<string, string> = {
    classify: `요구 ${n}개 분류 · 내부 목표 ${k}개 분리`,
    map_axes: '기획 축을 파트에 반영',
    write_sections: `섹션 ${total}개 작성 방향 쓰기`,
    trace: '요구 → 섹션 연결',
  };
  const rows = STEP_KEYS.map((key, i) => {
    const ev = steps[key];
    const state: 'done' | 'run' | 'wait' = ev?.state === 'done' || i < stageIdx ? 'done' : ev?.state === 'running' || i === stageIdx ? 'run' : 'wait';
    return { key, label: ev?.label || labels[key], state };
  });
  const weights = [10, 10, 70, 10];
  const computed = rows.reduce((acc, r, i) => acc + (r.state === 'done' ? weights[i] : r.state === 'run' && r.key === 'write_sections' ? weights[i] * (done / Math.max(1, total)) : 0), 0);
  const pct = Math.min(99, Math.max(progress || 0, computed));
  const unknown = (sb.requirement_ref?.open_question_count ?? 0) + (sb.counts?.unknown_answers ?? 0);
  return (
    <Page label="목차 만드는 중">
      <div className="sb-gen" aria-live="polite">
        <div className="sb-wbox" aria-hidden="true">W</div>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6 }}>
          <h1 className="sb-h1" style={{ fontSize: 24 }}>목차와 서사를 쓰는 중이에요</h1>
          <span className="sb-muted" style={{ fontSize: 14 }}>약 1분 · 끝나면 자동으로 넘어가요</span>
        </div>
        <div className="sb-genbar" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(pct)} aria-label="목차 쓰는 진행">
          <div style={{ width: `${pct}%` }} />
        </div>
        <div className="sb-gensteps" data-testid="gen-steps">
          {rows.map((r) => (
            <div key={r.key} className="sb-genstep" data-state={r.state}>
              <span className={`sb-genstep__dot sb-genstep__dot--${r.state}`}>
                {r.state === 'done' && <Icon name="check" size={13} strokeWidth={3} />}
                {r.state === 'run' && <span />}
              </span>
              <span className="sb-genstep__label" style={r.state === 'wait' ? { color: 'var(--wm-text-subtle)' } : undefined}>{r.label}</span>
              <span className={`sb-genstep__state${r.state === 'run' ? ' sb-genstep__state--run' : ''}`}>
                {r.state === 'done' ? '끝' : r.state === 'wait' ? '대기' : r.key === 'write_sections' ? `${done} / ${total}` : '쓰는 중'}
              </span>
            </div>
          ))}
        </div>
        {unknown > 0 && <span className="sb-muted" style={{ fontSize: 13 }}>확인 필요 {unknown}개는 추정하지 않고 TBD로 둬요</span>}
        <button type="button" className="sb-glink" style={{ fontSize: 13 }} onClick={onPartial}>기다리지 않고 지금까지 쓴 것 보기</button>
      </div>
    </Page>
  );
}

/** 목차가 없거나 다 쓰지 못함(SB3G error) */
function NotReady({ sb }: { sb: Sb }) {
  const qc = useQueryClient();
  const act = useAction();
  const failed = !!sb.outline && !sb.outline.ready;
  const start = () => void act.run(async () => {
    await sbApi.startOutline(sb.id, { retry: failed });
    await qc.invalidateQueries({ queryKey: sbKey(sb.id) });
  });
  return (
    <Page label="목차">
      {failed ? (
        <>
          <Head title="목차를 다 쓰지 못했어요" sub="다시 시도하면 이미 쓴 섹션은 건너뛰고 이어서 써요." />
          <FailBand message="목차를 쓰다가 멈췄어요." onRetry={start} busy={act.busy} />
        </>
      ) : <Head title="아직 목차가 없어요" sub="기획 방향을 고르면 묶음 5개로 목차와 서사를 써요." />}
      <Bottom
        back={<Back to={`/storyboard/${sb.id}/direction`}>기획 방향</Back>}
        primary={<Primary onClick={start} busy={act.busy} disabled={!sb.direction?.ready} disabledReason="기획 방향을 먼저 골라 주세요">
          {failed ? '다시 시도' : '목차 만들기'}
        </Primary>} />
    </Page>
  );
}

function groupRoute(sb: Sb, g: Group) {
  return g.key === 'part2' ? `/storyboard/${sb.id}/outline/part2` : `/storyboard/${sb.id}/outline/all#g-${g.key}`;
}

/** SB3 — 3 목차 — 묶음 5개(부분 보기면 쓰는 중 띠 + 스켈레톤) */
function OutlineView({ sb, partial }: { sb: Sb; partial: boolean }) {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const act = useAction();
  const outline = sb.outline!;
  const sections = outline.sections ?? [];
  const groups = [...(outline.groups ?? [])].sort((a, b) => a.order - b.order);
  const empties = emptySpaces(sb);
  const dir = selectedDirection(sb);
  const aud = audienceNames(sb);
  const sub = [dir?.title, `섹션 ${sections.length}개`, aud.length ? `청중 ${aud.join(' · ')}` : '청중 확인 필요'].filter(Boolean).join(' · ');
  const discussions = outline.discussions ?? [];
  const writing = outline.writing;
  const syncChanges = (sb.changes ?? []).filter((c) => c.cause.kind === 'rq_sync');
  const toTrace = () => void act.run(async () => {
    if (sb.step < 4) await sbApi.patch(sb.id, { step: 4 });
    await qc.invalidateQueries({ queryKey: sbKey(sb.id) });
    navigate(`/storyboard/${sb.id}/trace`);
  });
  const applyRq = () => void act.run(async () => {
    const ref = sb.requirement_ref!;
    await sbApi.sync(sb.id, { requirement_id: ref.requirement_id, to_version: sb.rq_update!.version, dry_run: false });
    await qc.invalidateQueries({ queryKey: sbKey(sb.id) });
    navigate(`/storyboard/${sb.id}/versions`);
  });
  return (
    <Page label="목차">
      <Head title={sb.name} badge={<DraftBadge sb={sb} />} actions={<HeadActions sb={sb} />} sub={sub} />
      {partial && (
        <div className="sb-band" role="status" data-testid="partial-band">
          <span className="wm-spinner" aria-hidden="true" />
          <span>목차 쓰는 중 · <b className="wm-num">{writing?.done ?? 0} / {writing?.total ?? sections.length}</b> 섹션</span>
        </div>
      )}
      {sb.active_job?.kind === 'sb.rq_sync' && (
        <div className="sb-band" role="status"><span className="wm-spinner" aria-hidden="true" /><span>요구사항 정의서 새 버전을 반영하는 중이에요</span></div>
      )}
      {sb.rq_update && !sb.active_job && (
        <div className="sb-band" data-testid="rq-update-band">
          <Icon name="refresh" size={15} />
          <span className="sb-grow">요구사항 정의서 {vIga(sb.rq_update.version)} 새로 저장됐어요{sb.rq_update.note ? ` · ${sb.rq_update.note}` : ''}</span>
          <button type="button" className="sb-hbtn" onClick={applyRq} disabled={act.busy}>반영하기</button>
        </div>
      )}
      {!sb.rq_update && !sb.active_job && syncChanges.length > 0 && (
        <div className="sb-band sb-band--plain">
          <Icon name="check" size={15} />
          <span className="sb-grow">요구사항 정의서 v{sb.requirement_ref?.version}을 반영했어요 · 바뀐 곳 {syncChanges.filter((c) => c.kind !== 'kept').length}</span>
          <Link to={`/storyboard/${sb.id}/versions`} className="sb-hbtn">바뀐 곳 보기</Link>
        </div>
      )}
      {empties.length > 0 && !partial && (
        <div className="sb-qbanner" data-testid="q-banner">
          <Q size="lg" />
          <span className="sb-col sb-grow" style={{ gap: 2 }}>
            <span className="sb-qbanner__title">{emptySpacesLabel(empties)} 시나리오가 비어 있어요</span>
            <span className="sb-qbanner__sub sb-ell">질문 몇 개에 답하면 행위 → 트리거 → 반응 → 예외 → 지표 5칸을 채워요</span>
          </span>
          <Link to={spaceRoute(sb.id, empties[0])} className="sb-outline-btn">{empties[0].name}부터 채우기</Link>
        </div>
      )}
      <div className="sb-card" data-testid="groups">
        {groups.map((g) => {
          const gs = sections.filter((s) => s.group_key === g.key);
          const written = gs.length > 0 && gs.every((s) => s.written);
          const pending = partial && !written && !(g.key === 'part2' && (outline.spaces ?? []).length);
          return (
            <Link key={g.key} to={groupRoute(sb, g)} className={`sb-card__row sb-group${g.key === 'part2' ? ' sb-card__row--soft' : ''}`} data-testid={`group-${g.key}`}>
              <span className="sb-num">{g.order}</span>
              <span className="sb-col sb-grow" style={{ gap: 4 }}>
                <span className="sb-group__top"><span className="sb-group__name">{g.name}</span><span className="sb-group__meta">{g.meta}</span></span>
                {pending ? <Skeleton w="64%" h={14} r={5} /> : <span className="sb-group__sum sb-ell">{g.summary}</span>}
              </span>
              {!pending && (g.badges ?? []).map((b) => <SbBadge key={b.label} tone={b.style}>{b.label}</SbBadge>)}
              <Chevron />
            </Link>
          );
        })}
      </div>
      <Bottom
        back={<Back to={`/storyboard/${sb.id}/direction`}>기획 방향</Back>}
        links={discussions.length > 0 ? <GreyLink to={`/storyboard/${sb.id}/outline/all#discussions`}>추가 논의 {discussions.length}</GreyLink> : undefined}
        primary={(
          <Primary onClick={toTrace} busy={act.busy} disabled={partial} disabledReason="목차를 다 쓴 뒤에 볼 수 있어요">요구 추적 확인</Primary>
        )} />
    </Page>
  );
}

function SpaceCells({ sp }: { sp: Space }) {
  const k = sp.filled_count;
  return (
    <span className="sb-cells" title={`5칸 중 ${k}칸`} aria-label={`5칸 중 ${k}칸`}>
      {[0, 1, 2, 3, 4].map((i) => <span key={i} className={`sb-cell${k === 0 ? ' sb-cell--empty' : i < k ? ' sb-cell--on' : ''}`} />)}
    </span>
  );
}

/** SB3P — 3 Part 2 공간 시나리오 */
export function Part2Screen() {
  const { sbId = '' } = useParams();
  const q = useSb(sbId);
  const sb = q.data;
  useSbShell(sb, 3);
  const navigate = useNavigate();
  useJobRefresh(sbId, sb?.active_job?.job_id);
  if (!sb) return <Gate loading={q.isLoading} error={q.error} onRetry={() => void q.refetch()} />;
  const spaces = [...(sb.outline?.spaces ?? [])].sort((a, b) => a.order - b.order);
  const empties = spaces.filter((s) => s.filled_count === 0);
  return (
    <Page label="Part 2 공간 시나리오">
      <Head eyebrow="목차 · Part 2" title={`Part 2 공간 시나리오 — ${spaces.length}개 공간`}
        sub="공간마다 행위 → 트리거 → 반응 → 예외 → 지표 5칸을 채워요. 비어 있는 곳만 질문으로 채우면 돼요." />
      <div className="sb-card" data-testid="spaces">
        {spaces.map((sp) => {
          const empty = sp.filled_count === 0;
          const to = spaceRoute(sb.id, sp);
          return (
            <div key={sp.id} role="link" tabIndex={0} className={`sb-card__row sb-space${empty ? ' sb-card__row--soft' : ''}`} data-testid={`space-${sp.key}`}
              onClick={(e) => { if (!(e.target as HTMLElement).closest('a')) navigate(to); }}
              onKeyDown={(e) => { if (e.key === 'Enter') navigate(to); }}>
              <span className={`sb-spnum${empty ? ' sb-spnum--on' : ''}`}>{sp.order}</span>
              <span className="sb-space__name">{sp.name}{sp.is_extension && <SbBadge tone="ext">확장</SbBadge>}</span>
              <span className="sb-space__purpose sb-ell">{sp.purpose}</span>
              <SpaceCells sp={sp} />
              <span className="sb-space__k wm-num">{sp.filled_count}/5</span>
              <span className="sb-space__st">
                {empty
                  ? <Link to={to} className="sb-fillbtn"><span className="sb-q sb-q--xs" aria-hidden="true">Q</span>질의로 채우기</Link>
                  : sp.status === 'supplemented' ? <SbBadge tone="dashed">작성자 보완</SbBadge> : <SbBadge tone="draft">초안</SbBadge>}
              </span>
            </div>
          );
        })}
      </div>
      <Bottom
        back={<Back to={`/storyboard/${sb.id}/outline`}>목차</Back>}
        primary={empties.length
          ? <Primary q to={spaceRoute(sb.id, empties[0])}>{empties[0].name}부터 채우기</Primary>
          : <Primary to={`/storyboard/${sb.id}/outline`}>목차 보기</Primary>} />
    </Page>
  );
}

function productsText(s: Section) {
  const names = (s.products ?? []).map((p) => p.name);
  if (!names.length) return null;
  return names.slice(0, 2).join(' · ') + (names.length > 2 ? ' 외' : '');
}

/** 구성 칸: Part 1 은 파란 코드 접두, Part 2 는 `Part 2` + 링크, Part 3 는 `Part 3` 접두 */
function Composition({ sb, s }: { sb: Sb; s: Section }) {
  if (s.group_key === 'part1') return <><span className="sb-prefix">{s.code}</span>{s.name}</>;
  if (s.group_key === 'part2') {
    return <><span className="sb-prefix">Part 2</span><Link to={`/storyboard/${sb.id}/outline/part2`} onClick={(e) => e.stopPropagation()}>{s.name}</Link></>;
  }
  if (s.group_key === 'part3') return <><span className="sb-prefix">{s.code && s.code !== 'Part 3' ? `Part ${s.code}` : 'Part 3'}</span>{s.name}</>;
  return <>{s.name}</>;
}

/** SB3D — 전체 보기(스텝바 없음, 좌우 120) */
export function OutlineAllScreen() {
  const { sbId = '' } = useParams();
  const q = useSb(sbId);
  const sb = q.data;
  useSbShell(sb, null);
  const location = useLocation();
  const [open, setOpen] = useState<Record<string, boolean>>({});
  const [copied, setCopied] = useState(false);
  const act = useAction();
  useJobRefresh(sbId, sb?.active_job?.job_id);
  const sections = useMemo(() => [...(sb?.outline?.sections ?? [])].sort((a, b) => a.order - b.order), [sb]);
  useEffect(() => {
    if (!sb || !location.hash) return;
    const el = document.getElementById(location.hash.slice(1));
    if (el) el.scrollIntoView({ block: 'center' });
  }, [sb, location.hash]);
  if (!sb) return <Gate loading={q.isLoading} error={q.error} onRetry={() => void q.refetch()} />;
  const discussions = sb.outline?.discussions ?? [];
  const dir = selectedDirection(sb);
  const agenda = () => void act.run(async () => {
    const r = await sbApi.agenda(sb.id);
    if (await copyText(r.text)) {
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } else toast('복사하지 못했어요. 브라우저 권한을 확인해 주세요.');
  });
  const firstOf = new Set<string>();
  return (
    <Page variant="wide" label="목차 전체 보기">
      <div className="sb-widehead">
        <div className="sb-col sb-grow" style={{ gap: 3 }}>
          <Link to={`/storyboard/${sb.id}/outline`} className="sb-crumb"><Icon name="chevronLeft" size={13} strokeWidth={2.6} />목차 · {sb.draft_label} · 자동 저장됨</Link>
          <h1 className="sb-h1" style={{ fontSize: 24 }}>{dir?.title ?? sb.name}</h1>
        </div>
        <HeadActions sb={sb} share />
      </div>
      {!sb.outline?.sections?.length ? <FailBand message="아직 목차가 없어요." /> : (
        <div className="sb-table" data-testid="outline-table">
          <div className="sb-table__head sb-grid-d" role="row">
            <span /><span>구성</span><span>작성 방향</span><span>제품 · 솔루션 후보</span><span>상태</span>
          </div>
          {sections.map((s, i) => {
            const anchor = firstOf.has(s.group_key) ? undefined : `g-${s.group_key}`;
            firstOf.add(s.group_key);
            const prods = productsText(s);
            const isOpen = !!open[s.id];
            return (
              <Fragment key={s.id}>
                <div id={anchor} role="row" className="sb-table__row sb-grid-d sb-table__row--click" aria-expanded={isOpen} data-testid="section-row"
                  onClick={() => setOpen({ ...open, [s.id]: !isOpen })}>
                  <span className="sb-rownum wm-num">{String(i + 1).padStart(2, '0')}</span>
                  <span className="sb-cellname sb-ell"><Composition sb={sb} s={s} /></span>
                  <span className="sb-celldir sb-ell"><Tok text={s.direction || (s.tbd_reason ?? '')} /></span>
                  <span className={`sb-cellprod sb-ell${prods ? '' : ' sb-cellprod--none'}`}>{prods ?? '—'}</span>
                  <span><SbBadge tone={STATUS_STYLE[s.status]}>{STATUS_TEXT[s.status]}</SbBadge></span>
                </div>
                {isOpen && (
                  <div className="sb-table__more">
                    {(s.lines ?? []).length ? (s.lines ?? []).map((ln) => (
                      <span key={ln.id}>· <Tok text={ln.text} />{ln.reviewing && <span className="sb-subtle"> (검토 중)</span>}</span>
                    )) : <span className="sb-subtle">{s.group_key === 'part2' ? '공간 시나리오는 Part 2 화면에서 봐요.' : '아직 본문 줄이 없어요.'}</span>}
                    {s.tbd_reason && <span className="sb-subtle">TBD — {s.tbd_reason}</span>}
                    <span className="sb-subtle">{sectionLabel(s)}</span>
                  </div>
                )}
              </Fragment>
            );
          })}
          {discussions.length > 0 && (
            <div className="sb-table__foot" id="discussions" data-testid="discussions">
              <span className="sb-dtitle">추가 논의 <span className="wm-num">{discussions.length}</span></span>
              {discussions.map((d) => (
                <span key={d.id} className="sb-dchip"><span className="sb-dchip__n wm-num">{d.n}</span>{d.label}</span>
              ))}
              <span className="sb-grow" />
              <button type="button" className="sb-hbtn" onClick={agenda} disabled={act.busy}>{copied ? '복사했어요' : '회의 안건에 넣기'}</button>
            </div>
          )}
        </div>
      )}
    </Page>
  );
}

