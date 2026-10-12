/**
 * Market Intelligence 새 흐름(보드 webapp1 MI0 · MI1 · MI1_Branch · MI2_Loading · MI2 · MI3 · View content=mi) — docs/scenarios/11-content-flow.md §1 · §6.
 *   /mi              MI0  목록(보드 List content=mi · 저장된 것 = 허브, 작성 중 = /v1/mi-flows)
 *   /mi/new          MI1  사전 작업 Storyboard 고르기(보드 Gate · 이미 있으면 MI1_Branch 수정/복제본) · `?sb=&auto=1` 은 바로 만들기(CF-07)
 *   /mi/flow/:id     저장 전 초안: MI2_Loading(AI 가 Storyboard 를 먼저 읽는다 — CF-08 의 MI 예외) → MI2 검색어 · 검색 조건 → (웹 검색) → MI3 정제
 *                    저장한 MI: MI_View(보기 · 목록 「열기」 · 작업 내역 · 허브 route) — 저장 직후도 같은 보기(완료 안내 없음)
 *   …?edit=1         저장한 MI 편집(보기 「편집」 · Gate 「수정하기」): 저장된 채면 Storyboard 를 다시 읽고(v1 → v2) MI2 → MI3 → 저장 → 보기.
 *                    이미 고치는 중이면(검색어 · 정제 단계) 다시 읽지 않고 그 단계에서 이어 간다.
 */
import { useEffect, useRef } from 'react';
import { Navigate, useParams, useSearchParams } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { CONTENT, ContentListScreen, FlowBar, GateScreen, useEditMode, useFlowInvalidate, useShellPage, type DraftRow } from '@/shell';
import { ErrorState, FlowScreen, Skeleton, josa, toast } from '@/ui';
import { GROUPS, isBusy, mfApi, mfKey, mfListKey, mfRoute, nOn, qsOf, useMfActions, useMfDelete, useMiFlow, useMiFlows, type MFDoc } from './api';
import { MiView } from './MiView';
import { usePacedSteps } from './pace';
import { RefineView } from './RefineStep';
import { LoadingView, SearchView } from './SearchStep';
import './miflow.css';

const SECTION = CONTENT.mi.label;
const STEPS = CONTENT.mi.steps;

/** MI0 — 보드 List(content=mi). 저장 전 초안은 「작성 중」 — 손을 올리면 ×(지우기) */
export function MiListScreen() {
  const flows = useMiFlows();
  const remove = useMfDelete();
  const drafts: DraftRow[] = (flows.data?.items ?? []).filter((m) => m.status !== 'done')
    .map((m) => ({ title: m.title, ref: m.code ?? null, to: mfRoute(m.id), sbIds: m.sb_id ? [m.sb_id] : [], when: m.updated_at,
      // 지금 단계(보드 List v61 n/3): 정제 중이면 3, 분석 · 검색 중이면 2
      step: m.phase === 'refine' ? 3 : 2,
      onDelete: m.ver == null ? () => remove(m.id) : undefined }));
  return <ContentListScreen content="mi" drafts={drafts} />;
}

/** MI1 · MI1_Branch — 보드 Gate(content=mi). 이전 흐름 링크(`/mi/new?rq=` — 요구사항 정의서의 「Market Intelligence」)는 이전 MI1 로.
 *  같은 Storyboard 의 저장 전 초안이 있으면(「‹ Storyboard」 → Gate → 다시 시작) 서버가 그 초안을 돌려준다 → 이어서 연다 */
export function MiGateScreen() {
  const [sp] = useSearchParams();
  const qc = useQueryClient();
  const flows = useMiFlows();
  const drafts: DraftRow[] = (flows.data?.items ?? []).filter((m) => m.status !== 'done' && m.ver == null)
    .map((m) => ({ title: m.title, ref: m.code ?? null, to: mfRoute(m.id), sbIds: m.sb_id ? [m.sb_id] : [], when: m.updated_at }));
  if (sp.get('rq') && !sp.get('sb')) return <Navigate to={`/mi/legacy/new?${sp.toString()}`} replace />;
  // 만든 문서(분석 중)를 캐시에 먼저 넣어 편집 화면이 분석 단계부터 그리게 한다(빠른 모델이면 첫 조회 때 이미 끝나 있다)
  return <GateScreen content="mi" initialSb={sp.get('sb')} autoStart={sp.get('auto') === '1'} drafts={drafts}
    onStart={async ({ sbId }) => {
      const { doc: d, reused } = await mfApi.create(sbId);
      qc.setQueryData(mfKey(d.id), d);
      void qc.invalidateQueries({ queryKey: mfListKey });
      if (reused) toast(`작성 중이던 ${d.code ?? 'MI'} 초안을 이어서 열어요`);
      return mfRoute(d.id);
    }} />;
}

/** 저장한 MI 를 열어 다시 읽기 시작하기 전(응답 전) — 서버 분석 단계와 같은 이름 */
const firstSteps = (sb: string) => [
  { key: 'read', label: `Storyboard ${sb} 읽기`, state: 'run' as const, note: '' },
  { key: 'extract', label: '고객사 · 업종 · 공간 · 요구 뽑기', state: 'wait' as const, note: '' },
  { key: 'queries', label: '시장 · 고객사 · 사용자 검색어 만들기', state: 'wait' as const, note: '' },
];

/** 한 번이라도 저장했으면 보여 줄 완성본이 있다(고치는 중이어도) */
const isSaved = (d: MFDoc | undefined) => !!d && (d.status === 'done' || d.ver != null);

function Body({ id }: { id: string }) {
  const q = useMiFlow(id);
  const actions = useMfActions(id);
  const inval = useFlowInvalidate();
  const { editing: editParam, toView } = useEditMode();
  const d = q.data;
  const busy = isBusy(d);
  const prog = d?.progress ?? null;
  const paced = usePacedSteps(prog?.steps ?? [], busy, `${prog?.kind ?? ''}:${prog?.job_id ?? ''}`);
  const starting = useRef(false);
  // 이번 편집에서 고치는 단계(analyzing · search · refine …)를 본 적이 있으면, 그 뒤의 done 은 「방금 저장」이다(다시 읽기 시작이 아니다)
  const sawWork = useRef(false);
  if (!editParam) sawWork.current = false;
  else if (d && d.phase !== 'done') sawWork.current = true;
  // 방금 저장(?edit 를 떼기 직전 한 번)도 보기 — 분석 로딩이 번쩍이지 않게
  const showView = isSaved(d) && (!editParam || (sawWork.current && d!.phase === 'done'));

  // 편집 화면(`?edit=1` — 보기 「편집」 · Gate 「수정하기」 · Storyboard 「편집 화면에서 고치기」)에서 저장된 채(phase done)면 고치기 시작:
  // Storyboard 를 다시 읽는다(보드 MI2_Loading 「MI-01 수정」 · v1 → v2). 이미 고치는 중(search · refine …)이면 그 자리에서 이어 간다(다시 읽지 않는다).
  useEffect(() => {
    if (!d || !editParam || d.phase !== 'done' || starting.current || sawWork.current) return;
    starting.current = true;
    actions.analyze().catch((e) => toast((e as Error).message || 'Storyboard를 다시 읽지 못했어요')).finally(() => { starting.current = false; });
  }, [d?.phase, editParam]); // eslint-disable-line react-hooks/exhaustive-deps

  const view: 'load' | 'analyze' | 'search' | 'searching' | 'refine' =
    !d ? 'load'
      : d.phase === 'done' ? 'analyze'
        : prog?.kind === 'analyze' && (d.phase === 'analyzing' || !paced.settled) ? 'analyze'
          : prog?.kind === 'search' && (d.phase === 'searching' || !paced.settled) ? 'searching'
            : d.phase === 'refine' ? 'refine' : 'search';
  const revising = d?.ver != null;
  const code = d?.code ?? 'MI';
  useShellPage(showView
    ? { section: SECTION, title: code, hasTask: false }
    : { section: SECTION, title: !d ? '' : revising ? `${code} 수정` : `새 ${CONTENT.mi.short}`, hasTask: true,
      stepper: { steps: STEPS, current: view === 'refine' ? 3 : 2 } });

  if (q.isError) return <div className="wm-page"><ErrorState message="MI를 불러오지 못했어요 · 지워졌거나 주소가 바뀌었을 수 있어요" onRetry={() => q.refetch()} /></div>;
  if (!d) return <div className="wm-page"><Skeleton h={520} r={16} /></div>;
  if (showView) return <MiView doc={d} />;
  const note = revising && d.ver != null
    ? `${code} v${d.ver}${josa(`v${d.ver}`, '을', '를')} 고쳐요 · 저장하면 v${d.ver + 1}`
    : 'Storyboard를 그대로 가져왔어요 · 사전 작업 DSS 확인됨';
  const gate = `/mi/new?sb=${encodeURIComponent(d.sb_id)}`;
  const nq = GROUPS.reduce((a, g) => a + nOn(qsOf(d)[g.key]), 0);
  return (
    <FlowScreen pad="22px 40px 22px 40px" gap={view === 'refine' ? 12 : 14} className="mif-screen" bar={<FlowBar sbIds={[d.sb_id]} current="mi" note={note} />}>
      {view === 'analyze' && <LoadingView kind="analyze" steps={d.phase === 'done' ? firstSteps(d.sb_id) : paced.view} backTo={gate} />}
      {view === 'searching' && <LoadingView kind="search" steps={paced.view} summary={`검색어 ${nq}개 · 1–2분`} />}
      {view === 'search' && <SearchView key={`${d.id}:${prog?.job_id ?? ''}`} doc={d} actions={actions} backTo={gate} />}
      {view === 'refine' && (
        <RefineView doc={d} actions={actions} onFinished={async () => {
          // 저장하면 그 MI 보기로(같은 주소 · ?edit 만 뗀다 · 완료 안내 없음) — 저장한 문서를 캐시에 넣고 목록 · 허브는 새로
          await actions.refresh();
          inval();
          toView(['done']);
        }} />
      )}
    </FlowScreen>
  );
}

/** `/mi/flow/:id` — 다른 MI 로 옮겨 가면 화면 상태를 새로 */
export function MiFlowPage() {
  const { id = '' } = useParams();
  return <Body key={id} id={id} />;
}
