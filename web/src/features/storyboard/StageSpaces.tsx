/**
 * 3단계 섹션 질의 — SB3S(빈 칸만, 칸당 질문 하나) · SB3S2(완성 결과 · 작성자 보완). §4.14–4.15
 */
import { useEffect, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Link, Navigate, useNavigate, useParams, useSearchParams } from 'react-router';
import { Icon, Skeleton } from '@/ui';
import {
  errorText, firstEmptySlot, jobErrorText, sbApi, sbKey, slotState, SLOT_FULL, SLOT_KEYS, SLOT_SHORT, spaceRoute, useAction, useJobRefresh, usePoll, useSb, useSbShell,
  type SlotKey, type Space,
} from './lib';
import { Back, Bottom, Choice, CustomInput, FailBand, Gate, GreyLink, Head, LoadingHead, Page, Primary, SbBadge, Segs, SkeletonRows } from './parts';

function SlotChips({ space, current }: { space: Space; current: SlotKey }) {
  return (
    <div className="sb-slotchips" aria-label="5칸 진행">
      {SLOT_KEYS.map((k, i) => {
        const st = slotState(space, k).state;
        const kind = k === current ? 'now' : st !== 'empty' ? 'done' : 'rest';
        return (
          <span key={k} style={{ display: 'contents' }}>
            {i > 0 && <span className="sb-slotsep" aria-hidden="true"><Icon name="chevronRight" size={12} strokeWidth={2.4} /></span>}
            <span className={`sb-slotchip sb-slotchip--${kind}`} data-state={kind} aria-current={kind === 'now' ? 'step' : undefined}>
              {kind === 'done' && <Icon name="check" size={12} strokeWidth={3} />}{SLOT_SHORT[k]}
            </span>
          </span>
        );
      })}
    </div>
  );
}

function nextEmpty(space: Space, after?: SlotKey): SlotKey | null {
  const start = after ? SLOT_KEYS.indexOf(after) + 1 : 0;
  for (let i = 0; i < SLOT_KEYS.length; i++) {
    const k = SLOT_KEYS[(start + i) % SLOT_KEYS.length];
    if (k !== after && slotState(space, k).state === 'empty') return k;
  }
  return null;
}

/** SB3S — 3 섹션 질의 · {공간} {k}/5 {칸} */
export function SpaceQScreen() {
  const { sbId = '', spcId = '' } = useParams();
  const [params, setParams] = useSearchParams();
  const [qJob, setQJob] = useState<string | null>(null);
  const q = useSb(sbId, { poll: !!qJob });
  const sb = q.data;
  useSbShell(sb, 3);
  const navigate = useNavigate();
  const qc = useQueryClient();
  const act = useAction();
  const [failed, setFailed] = useState<string | null>(null);
  useJobRefresh(sbId, qJob, (ok, job) => { setQJob(null); if (!ok) setFailed(jobErrorText(job.error)); });
  const space = sb?.outline?.spaces?.find((s) => s.id === spcId);
  const asked = useRef(false);
  const slotParam = params.get('slot') as SlotKey | null;
  const current: SlotKey | null = space
    ? (slotParam && SLOT_KEYS.includes(slotParam) && slotState(space, slotParam).state === 'empty' ? slotParam : firstEmptySlot(space))
    : null;
  const question = space?.questions?.find((x) => x.slot === current);
  const [sel, setSel] = useState<string[]>([]);
  const [custom, setCustom] = useState('');
  useEffect(() => { setSel([]); setCustom(''); }, [current, spcId]);

  // 질의가 없으면 만든다(빈 칸만 — sb.space.questions)
  const requestQuestions = () => {
    if (!sb || !space) return;
    asked.current = true;
    setFailed(null);
    sbApi.spaceQuestions(sb.id, space.id)
      .then(async (r) => {
        if (r && typeof r === 'object' && 'job_id' in r) setQJob((r as { job_id: string }).job_id);
        else await qc.invalidateQueries({ queryKey: sbKey(sb.id) });
      })
      .catch((e) => setFailed(errorText(e)));
  };
  useEffect(() => {
    if (!sb || !space || asked.current || qJob) return;
    const empties = SLOT_KEYS.filter((k) => slotState(space, k).state === 'empty');
    const have = new Set((space.questions ?? []).map((x) => x.slot));
    if (empties.some((k) => !have.has(k))) requestQuestions();
  });  // eslint-disable-line react-hooks/exhaustive-deps

  if (!sb) return <Gate loading={q.isLoading} error={q.error} onRetry={() => void q.refetch()} />;
  if (!space) return <Navigate to={`/storyboard/${sb.id}/outline/part2`} replace />;
  if (!current) return <Navigate to={`/storyboard/${sb.id}/spaces/${space.id}/done`} replace />;

  const k = SLOT_KEYS.indexOf(current) + 1;
  const afterAnswer = async (result: Space) => {
    await qc.invalidateQueries({ queryKey: sbKey(sb.id) });
    const nxt = nextEmpty(result, current);
    if (nxt) setParams({ slot: nxt });
    else {
      await sbApi.compose(sb.id, space.id);
      await qc.invalidateQueries({ queryKey: sbKey(sb.id) });
      navigate(`/storyboard/${sb.id}/spaces/${space.id}/done`);
    }
  };
  const next = () => void act.run(async () => {
    const r = await sbApi.putSlot(sb.id, space.id, current, { selected_option_ids: sel, custom_text: custom.trim() || null });
    await afterAnswer(r as unknown as Space);
  });
  const unknown = () => void act.run(async () => {
    const r = await sbApi.putSlot(sb.id, space.id, current, { unknown: true });
    await afterAnswer(r as unknown as Space);
  });
  const toggle = (id: string) => setSel(sel.includes(id) ? sel.filter((x) => x !== id) : [...sel, id]);
  const eyebrow = `섹션 질의 · Part 2 ${space.name} · ${k} / 5 ${SLOT_SHORT[current]}`;
  return (
    <Page label={eyebrow}>
      {question ? (
        <Head q eyebrow={eyebrow} title={question.text} />
      ) : (
        <div className="sb-head">
          <span className="sb-eyebrow"><span className="sb-q" aria-hidden="true">Q</span>{eyebrow}</span>
          {failed ? <h1 className="sb-h1">질문을 만들지 못했어요</h1> : <LoadingHead title="질문을 만드는 중이에요" />}
        </div>
      )}
      <SlotChips space={space} current={current} />
      {failed && !question && <FailBand message={failed} onRetry={requestQuestions} />}
      {question ? (
        <>
          <div className="sb-info"><Icon name="info" size={14} /><span>{question.info}</span></div>
          <div className="sb-choices" role="group" aria-label={question.text}>
            {question.options.map((o) => {
              const pos = sel.indexOf(o.id);
              return <Choice key={o.id} kind="ordered" weight={600} pressed={pos >= 0} order={pos + 1} title={o.label} role="" onClick={() => toggle(o.id)} />;
            })}
            {question.allow_custom && <CustomInput value={custom} onChange={setCustom} onCommit={() => undefined} />}
          </div>
        </>
      ) : !failed && <SkeletonRows n={4} />}
      <Bottom
        back={<GreyLink onClick={unknown} disabled={act.busy || !question}>모르겠어요 → 고객에게 묻기</GreyLink>}
        primary={(
          <Primary onClick={next} busy={act.busy} disabled={!question || (!sel.length && !custom.trim())} disabledReason="선택지를 하나 이상 골라 주세요">다음</Primary>
        )} />
    </Page>
  );
}

/** SB3S2 — 3 섹션 질의 · {공간} 완료 */
export function SpaceDoneScreen() {
  const { sbId = '', spcId = '' } = useParams();
  const q = useSb(sbId);
  const sb = q.data;
  usePoll(sbId, !!sb?.outline?.spaces?.find((s) => s.id === spcId)?.composing);
  useSbShell(sb, 3);
  useJobRefresh(sbId, sb?.active_job?.job_id);
  if (!sb) return <Gate loading={q.isLoading} error={q.error} onRetry={() => void q.refetch()} />;
  const spaces = [...(sb.outline?.spaces ?? [])].sort((a, b) => a.order - b.order);
  const space = spaces.find((s) => s.id === spcId);
  if (!space) return <Navigate to={`/storyboard/${sb.id}/outline/part2`} replace />;
  const nextSpace = spaces.find((s) => s.id !== space.id && s.filled_count === 0);
  const eyebrow = `섹션 질의 · Part 2 ${space.name} · 완료`;
  const ext = (space.products ?? []).filter((p) => p.is_extension).length;
  const added = space.added_questions ?? [];
  const rq = sb.requirement_ref?.requirement_id;
  return (
    <Page label={eyebrow}>
      {space.composing ? (
        <>
          <div className="sb-head">
            <span className="sb-eyebrow"><span className="sb-q" aria-hidden="true">Q</span>{eyebrow}</span>
          </div>
          <LoadingHead title={`${space.name} 시나리오를 다듬는 중이에요`} sub="답을 문장으로 다듬고, 모르는 값은 [00]으로 남겨요." />
          <div className="sb-card" aria-busy="true">
            {SLOT_KEYS.map((key) => <div key={key} className="sb-slotrow"><Skeleton w="70%" h={16} r={6} /></div>)}
          </div>
        </>
      ) : (
        <>
          <Head q eyebrow={eyebrow} title={`${space.name} 시나리오 5칸을 채웠어요`}
            sub="점선 밑줄은 AI가 보탠 문장이에요(고객 확인 전). 모르는 값은 [00]으로 남겼어요." />
          <div className="sb-card" data-testid="slots">
            {SLOT_KEYS.map((key, i) => {
              const sl = slotState(space, key);
              return (
                <div key={key} className="sb-slotrow" data-slot={key} data-state={sl.state}>
                  <span className="sb-slotrow__n wm-num">{i + 1}</span>
                  <span className="sb-slotrow__k">{SLOT_FULL[key]}</span>
                  <span className="sb-slotrow__v">{sl.segments?.length ? <Segs segments={sl.segments} /> : <span className="sb-subtle">—</span>}</span>
                </div>
              );
            })}
          </div>
          {(space.products ?? []).length > 0 && (
            <div className="sb-prodline">
              <span className="sb-prodline__k">제품 후보</span>
              <span className="sb-ell">{(space.products ?? []).map((p) => p.name).join(' · ')}</span>
              {ext > 0 && <SbBadge tone="ext">확장 {ext}</SbBadge>}
            </div>
          )}
          {added.length > 0 && rq && (
            <Link to={`/requirements/${rq}/questions`} className="sb-notice" data-testid="added-questions">
              <Icon name="info" size={15} />
              <span className="sb-grow sb-ell">고객에게 물을 것에 {added.length}개 더했어요 — {added.map((a) => a.short_label).join(' · ')}</span>
              <span className="sb-notice__go">보기</span>
            </Link>
          )}
        </>
      )}
      <Bottom
        back={<Back to={`/storyboard/${sb.id}/outline`}>목차</Back>}
        primary={nextSpace
          ? <Primary q to={spaceRoute(sb.id, nextSpace)} disabled={space.composing}>다음 공간 · {nextSpace.name}</Primary>
          : <Primary to={`/storyboard/${sb.id}/outline`} disabled={space.composing}>목차 보기</Primary>} />
    </Page>
  );
}
