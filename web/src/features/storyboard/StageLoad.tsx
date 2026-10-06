/**
 * 1단계 `요구사항 불러오기` — SB1(정의서 고르기) · SB1S(설정 바꾸기) · SB1Q/Q2/Q3(기획 질의). §4.3–4.7
 */
import { useEffect, useMemo, useRef, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, Navigate, useNavigate, useParams, useSearchParams } from 'react-router';
import { Icon, Skeleton, toast } from '@/ui';
import {
  errorText, sbApi, sbKey, savedRequirements, savedTime, useAction, useJobRefresh, useSb, useSbShell,
  type PlanningQuestion, type RqListItem, type Sb,
} from './lib';
import { Back, Bottom, Choice, CustomInput, Gate, GreyLink, Head, Page, Primary, SbBadge, Seg, SkeletonRows } from './parts';

const RQ_LIST_KEY = ['storyboard', 'rq-saved'] as const;

function useSavedRequirements() {
  return useQuery({ queryKey: RQ_LIST_KEY, queryFn: () => savedRequirements(5), staleTime: 10_000, retry: 1 });
}

/** 정의서 카드 둘째 줄: `요구 12개 · 확인 필요 4개 · 오늘 13:40 저장` / `… · 심층 작성 중` */
function rqLine(r: { item_count: number; open_question_count: number; saved_at?: string | null; deepening?: boolean }) {
  const parts = [`요구 ${r.item_count}개`];
  if (r.open_question_count > 0) parts.push(`확인 필요 ${r.open_question_count}개`);
  if (r.deepening) parts.push('심층 작성 중');
  else if (r.saved_at) parts.push(savedTime(r.saved_at));
  return parts.join(' · ');
}

interface RqCard { id: string; title: string; version: number; line: string }

function cardsFor(list: RqListItem[] | undefined, sb?: Sb): RqCard[] {
  const out: RqCard[] = (list ?? []).map((r) => ({
    id: r.id, title: r.title || r.project_name || '이름 없는 정의서', version: r.version,
    line: rqLine({ item_count: r.item_count, open_question_count: r.open_question_count, saved_at: r.saved_at,
      deepening: !!r.active_deep || r.list_state === 'deepening' }),
  }));
  const ref = sb?.requirement_ref;
  if (ref && !out.some((c) => c.id === ref.requirement_id)) {
    out.unshift({ id: ref.requirement_id, title: ref.title, version: ref.version, line: rqLine(ref) });
  }
  return out.slice(0, 5);
}

function NoRqCard({ emphasized }: { emphasized?: boolean }) {
  return (
    <Link to="/requirements/new?return=storyboard" className="sb-norq" data-emph={emphasized || undefined}>
      <Icon name="plus" size={16} strokeWidth={2.4} />정의서가 없어요 — 요청서 · 메모부터 넣기
    </Link>
  );
}

function SettingsRow({ sb, preparing }: { sb?: Sb; preparing: boolean }) {
  const st = sb?.settings;
  return (
    <div className="sb-setrow" aria-busy={preparing || undefined}>
      <span className="sb-setrow__k">설정</span>
      {preparing || !st?.ready
        ? <span className="sb-grow" data-testid="settings-skeleton"><Skeleton w="62%" h={16} r={6} /></span>
        : <span className="sb-setrow__v" data-testid="settings-summary">{st.summary}</span>}
      {!preparing && st?.ready && st.all_from_rq && <span className="sb-setrow__src">정의서에서 읽었어요</span>}
      {sb && !preparing && st?.ready
        ? <Link to={`/storyboard/${sb.id}/settings`} className="sb-setrow__btn"><Icon name="edit" size={13} />바꾸기</Link>
        : <span className="sb-setrow__btn" aria-disabled="true"><Icon name="edit" size={13} />바꾸기</span>}
    </div>
  );
}

const SB1_TITLE = '어떤 요구사항 정의서로 시작할까요?';
const SB1_SUB = '정의서가 스토리보드의 근거가 돼요. 확인 필요한 값은 추정하지 않고 TBD로 둬요.';

/** `/storyboard/new?rq=` — 들어오면 바로 만든다(시작 전 초안 재사용 · Q-7) → `/storyboard/{sb}/source` */
export function NewScreen() {
  useSbShell(undefined, 1, { title: '새 스토리보드' });
  const [params] = useSearchParams();
  const rqParam = params.get('rq');
  const navigate = useNavigate();
  const rqs = useSavedRequirements();
  const started = useRef(false);
  const [error, setError] = useState<string | null>(null);
  const target = rqParam ?? rqs.data?.[0]?.id ?? null;
  const none = !rqParam && rqs.isSuccess && !rqs.data.length;

  useEffect(() => {
    if (started.current || !target) return;
    started.current = true;
    sbApi.create(target)
      .then((sb) => navigate(`/storyboard/${sb.id}/source`, { replace: true }))
      .catch((e) => { setError(errorText(e)); started.current = false; });
  }, [target, navigate]);

  const retry = () => { setError(null); started.current = false; if (!rqParam) void rqs.refetch(); else navigate(0); };
  return (
    <Page label="정의서 고르기">
      <Head title={SB1_TITLE} sub={SB1_SUB} />
      {none ? (
        <div className="sb-choices"><NoRqCard emphasized /></div>
      ) : error || rqs.isError ? (
        <div className="sb-choices">
          <div className="sb-band sb-band--plain" role="alert">
            <Icon name="warn" size={15} /><span className="sb-grow">{error ?? '정의서 목록을 불러오지 못했어요.'}</span>
            <button type="button" className="sb-hbtn" onClick={retry}>다시 시도</button>
          </div>
          <NoRqCard />
        </div>
      ) : (
        <>
          <SkeletonRows n={3} h={68} />
          <SettingsRow preparing />
        </>
      )}
      <Bottom
        back={<Back to="/storyboard">목록</Back>}
        links={<GreyLink disabled disabledReason="정의서를 먼저 골라 주세요">질의 건너뛰고 기획 방향</GreyLink>}
        primary={<Primary disabled disabledReason="정의서를 먼저 골라 주세요">다음 · 기획 질의</Primary>} />
    </Page>
  );
}

/** SB1 — 1 정의서 고르기(만든 뒤) */
export function SourceScreen() {
  const { sbId = '' } = useParams();
  const q = useSb(sbId);
  const sb = q.data;
  useSbShell(sb, 1);
  const rqs = useSavedRequirements();
  const qc = useQueryClient();
  const navigate = useNavigate();
  const act = useAction();
  useJobRefresh(sbId, sb?.active_job?.job_id);
  const cards = useMemo(() => cardsFor(rqs.data, sb), [rqs.data, sb]);
  if (!sb) return <Gate loading={q.isLoading} error={q.error} onRetry={() => void q.refetch()} />;

  const preparing = !sb.settings?.ready || sb.active_job?.kind === 'sb.prepare';
  const locked = sb.started || sb.step >= 2;
  const n = sb.planning?.questions?.length ?? 0;
  const hasDirection = !!sb.direction?.options?.length;

  const pick = (id: string) => {
    if (id === sb.requirement_ref?.requirement_id || locked) return;
    void act.run(async () => {
      await sbApi.putRequirement(sb.id, id);
      await qc.invalidateQueries({ queryKey: sbKey(sb.id) });
    });
  };
  const skip = () => {
    if (hasDirection) { navigate(`/storyboard/${sb.id}/direction`); return; }
    void act.run(async () => {
      await sbApi.startDirection(sb.id, true);
      await qc.invalidateQueries({ queryKey: sbKey(sb.id) });
      navigate(`/storyboard/${sb.id}/direction`);
    });
  };
  const next = () => {
    if (n > 0) { navigate(`/storyboard/${sb.id}/planning/1`); return; }
    skip();
  };
  return (
    <Page label="정의서 고르기">
      <Head title={SB1_TITLE} sub={SB1_SUB} />
      <div className="sb-choices" role="group" aria-label="요구사항 정의서">
        {rqs.isLoading && !cards.length ? <SkeletonRows n={3} h={68} /> : cards.map((c) => {
          const on = c.id === sb.requirement_ref?.requirement_id;
          return (
            <Choice key={c.id} pressed={on} tall onClick={() => pick(c.id)} disabled={!on && locked}
              disabledReason="새 스토리보드에서 바꿀 수 있어요"
              title={<><span className="sb-ell">{c.title}</span><span className={`sb-ver ${on ? 'sb-ver--on' : 'sb-ver--off'}`}>v{c.version}</span></>}
              hint={c.line} />
          );
        })}
        <NoRqCard />
      </div>
      <SettingsRow sb={sb} preparing={preparing} />
      <Bottom
        back={<Back to="/storyboard">목록</Back>}
        links={<GreyLink onClick={skip} disabled={preparing || act.busy} disabledReason="정의서를 읽는 중이에요">질의 건너뛰고 기획 방향</GreyLink>}
        primary={(
          <Primary onClick={next} disabled={preparing} busy={act.busy} disabledReason="정의서를 읽는 중이에요">
            {n > 0 ? `다음 · 기획 질의 ${n}개` : '다음 · 기획 방향'}
          </Primary>
        )} />
    </Page>
  );
}

const STAGE_ITEMS = [{ value: 'concept', label: '컨셉 제안' }, { value: 'main', label: '본제안' }] as const;
const DOC_ITEMS = [{ value: 'common_pitch', label: '공통 Pitch deck' }, { value: 'custom', label: '고객 맞춤 제안' }] as const;
const VOLUME_ITEMS = [{ value: 12, label: '약 12장' }, { value: 20, label: '약 20장' }, { value: 30, label: '약 30장' }] as const;
const LANG_ITEMS = [{ value: 'ko', label: '한국어' }, { value: 'en', label: '영문' }, { value: 'ko_en', label: '한 · 영 병기' }] as const;
type StageV = (typeof STAGE_ITEMS)[number]['value'];
type DocV = (typeof DOC_ITEMS)[number]['value'];
type VolV = (typeof VOLUME_ITEMS)[number]['value'];
type LangV = (typeof LANG_ITEMS)[number]['value'];

/** SB1S — 1 설정 바꾸기 */
export function SettingsScreen() {
  const { sbId = '' } = useParams();
  const q = useSb(sbId);
  const sb = q.data;
  useSbShell(sb, 1);
  const navigate = useNavigate();
  const qc = useQueryClient();
  const act = useAction();
  const st = sb?.settings;
  const [v, setV] = useState<{ stage: StageV; doc: DocV; volume: VolV; lang: LangV } | null>(null);
  useEffect(() => {
    if (st?.ready && !v) {
      setV({ stage: st.stage?.value ?? 'concept', doc: st.doc_type?.value ?? 'custom', volume: (st.volume?.value ?? 20) as VolV, lang: st.language?.value ?? 'ko' });
    }
  }, [st, v]);
  if (!sb) return <Gate loading={q.isLoading} error={q.error} onRetry={() => void q.refetch()} />;
  if (!st?.ready && !q.isLoading && !sb.active_job) return <Navigate to={`/storyboard/${sb.id}/source`} replace />;

  const save = () => {
    if (!v || !st) return;
    const body: Record<string, string | number> = {};
    if (v.stage !== st.stage?.value) body.stage = v.stage;
    if (v.doc !== st.doc_type?.value) body.doc_type = v.doc;
    if (v.volume !== st.volume?.value) body.volume = v.volume;
    if (v.lang !== st.language?.value) body.language = v.lang;
    void act.run(async () => {
      if (Object.keys(body).length) {
        await sbApi.patchSettings(sb.id, body);
        await qc.invalidateQueries({ queryKey: sbKey(sb.id) });
      }
      navigate(`/storyboard/${sb.id}/source`);
    });
  };
  const row = (label: string, control: React.ReactNode, hint?: string | null) => (
    <div className="sb-setting">
      <span className="sb-setting__k">{label}</span>
      <div className="sb-setting__v">{control}{hint && <span className="sb-setting__hint">{hint}</span>}</div>
    </div>
  );
  return (
    <Page label="스토리보드 설정">
      <Head eyebrow="요구사항 불러오기 · 설정" title="스토리보드 설정" sub="정의서에서 읽은 값으로 골라 뒀어요. 바꿀 것만 바꾸세요." />
      {!v ? <SkeletonRows n={4} h={72} /> : (
        <div className="sb-card">
          {row('제안 단계', <Seg<StageV> label="제안 단계" value={v.stage} onChange={(x) => setV({ ...v, stage: x })} items={[...STAGE_ITEMS]} />,
            st?.stage?.evidence)}
          {row('문서 형식', <Seg<DocV> label="문서 형식" value={v.doc} onChange={(x) => setV({ ...v, doc: x })} items={[...DOC_ITEMS]} />,
            '공통 Pitch deck은 여러 고객에게 쓸 때')}
          {row('분량', <Seg<VolV> label="분량" value={v.volume} onChange={(x) => setV({ ...v, volume: x })} items={[...VOLUME_ITEMS]} />,
            st?.volume?.evidence)}
          {row('언어', <Seg<LangV> label="언어" value={v.lang} onChange={(x) => setV({ ...v, lang: x })} items={[...LANG_ITEMS]} />)}
        </div>
      )}
      <Bottom
        back={<Back to={`/storyboard/${sb.id}/source`}>정의서</Back>}
        primary={<Primary onClick={save} arrow={false} busy={act.busy} disabled={!v}>저장</Primary>} />
    </Page>
  );
}

function sortedQuestions(sb: Sb): PlanningQuestion[] {
  return [...(sb.planning?.questions ?? [])].sort((a, b) => a.order - b.order);
}

/** SB1Q · SB1Q2 · SB1Q3 — 기획 질의(한 화면에 질문 하나, 답은 누를 때마다 저장) */
export function PlanningScreen() {
  const { sbId = '', i = '1' } = useParams();
  const idx = Math.max(1, Number(i) || 1);
  const q = useSb(sbId);
  const sb = q.data;
  useSbShell(sb, 1);
  const navigate = useNavigate();
  const qc = useQueryClient();
  const act = useAction();
  const questions = useMemo(() => (sb ? sortedQuestions(sb) : []), [sb]);
  const question = questions[idx - 1];
  const answer = sb?.planning?.answers?.find((a) => a.question_id === question?.id);
  const [sel, setSel] = useState<string[]>([]);
  const [follow, setFollow] = useState<string | null>(null);
  const [custom, setCustom] = useState('');
  const chain = useRef<Promise<unknown>>(Promise.resolve());
  const loadedFor = useRef<string | null>(null);

  // 질의가 바뀌면 서버 답으로 다시 채운다
  useEffect(() => {
    if (!question || loadedFor.current === question.id) return;
    loadedFor.current = question.id;
    setSel(answer && !answer.unknown ? [...(answer.selected_option_ids ?? [])] : []);
    setFollow(answer?.follow_up_option_id ?? null);
    setCustom('');
  }, [question, answer]);

  if (!sb) return <Gate loading={q.isLoading} error={q.error} onRetry={() => void q.refetch()} />;
  if (!question) return <Navigate to={`/storyboard/${sb.id}/source`} replace />;

  const n = questions.length;
  const last = idx >= n;
  const single = question.select === 'single';
  const roles = question.order_roles ?? [];
  const chosen = single ? question.options.find((o) => o.id === sel[0]) : undefined;
  const followUp = chosen?.follow_up ?? null;

  const put = (body: Parameters<typeof sbApi.answer>[2]) => {
    chain.current = chain.current.then(() => sbApi.answer(sb.id, question.id, body)
      .then(() => qc.invalidateQueries({ queryKey: sbKey(sb.id) }))
      .catch((e) => { toast(errorText(e)); }));
    return chain.current;
  };
  const toggle = (id: string) => {
    let next: string[];
    if (single) next = [id];
    else next = sel.includes(id) ? sel.filter((x) => x !== id) : [...sel, id];
    setSel(next);
    if (single && id !== sel[0]) setFollow(null);
    if (next.length) void put({ selected_option_ids: next });
  };
  const commitCustom = () => {
    const text = custom.trim();
    if (!text) return;
    setCustom('');
    void put({ selected_option_ids: sel, custom_text: text }).then(() => {
      const fresh = qc.getQueryData<Sb>(sbKey(sb.id));
      const qq = fresh?.planning?.questions?.find((x) => x.id === question.id);
      const a = fresh?.planning?.answers?.find((x) => x.question_id === question.id);
      if (qq && a) setSel([...(a.selected_option_ids ?? [])]);
    });
  };
  const pickFollow = (fid: string) => {
    setFollow(fid);
    void put({ selected_option_ids: sel, follow_up_option_id: fid });
  };
  const toDirection = async () => {
    await sbApi.startDirection(sb.id, false);
    await qc.invalidateQueries({ queryKey: sbKey(sb.id) });
    navigate(`/storyboard/${sb.id}/direction`);
  };
  const goNext = () => void act.run(async () => {
    await chain.current;
    if (last) await toDirection();
    else navigate(`/storyboard/${sb.id}/planning/${idx + 1}`);
  });
  const unknown = () => void act.run(async () => {
    await chain.current;
    await sbApi.answer(sb.id, question.id, { unknown: true });
    await qc.invalidateQueries({ queryKey: sbKey(sb.id) });
    if (last) await toDirection();
    else navigate(`/storyboard/${sb.id}/planning/${idx + 1}`);
  });
  const nothing = sel.length === 0;
  const needFollow = !!followUp && !follow;
  return (
    <Page label={`기획 질의 ${idx} / ${n}`}>
      <Head q eyebrow={`기획 질의 ${idx} / ${n} · ${question.topic_label}`} title={question.text} info={question.info} />
      <div className="sb-choices" role="group" aria-label={question.text}>
        {question.options.map((o) => {
          const pos = sel.indexOf(o.id);
          const on = pos >= 0;
          const role = !single && on && roles[pos] ? roles[pos] : undefined;
          return (
            <Choice key={o.id} pressed={on} kind={single ? 'radio' : 'ordered'} order={pos + 1} weight={600} onClick={() => toggle(o.id)}
              title={o.label} badge={o.badge ? <SbBadge tone="soft">{o.badge}</SbBadge> : undefined}
              role={role ?? (o.hint || o.evidence || '')} testId={`opt-${o.id}`} />
          );
        })}
        {question.allow_custom && !single && (
          <CustomInput value={custom} onChange={setCustom} onCommit={commitCustom} />
        )}
      </div>
      {followUp && (
        <div className="sb-follow" role="group" aria-label="이어서 하나만">
          <span className="sb-follow__head">이어서 하나만</span>
          <span className="sb-follow__q">{followUp.text}</span>
          <div className="sb-chips">
            {followUp.options.map((fo) => (
              <button key={fo.id} type="button" className="sb-chip" aria-pressed={follow === fo.id} onClick={() => pickFollow(fo.id)}>{fo.label}</button>
            ))}
          </div>
        </div>
      )}
      <Bottom
        back={<GreyLink onClick={unknown} disabled={act.busy}>모르겠어요 → 확인 필요로 남기기</GreyLink>}
        primary={(
          <Primary onClick={goNext} busy={act.busy} disabled={nothing || needFollow}
            disabledReason={nothing ? '선택지를 하나 이상 골라 주세요' : '이어서 하나만 답해 주세요'}>
            {last ? '기획 방향 만들기' : '다음'}
          </Primary>
        )} />
    </Page>
  );
}
