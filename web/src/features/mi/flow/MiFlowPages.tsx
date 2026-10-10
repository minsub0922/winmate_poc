/**
 * Market Intelligence 새 흐름(보드 webapp1 MI0 · MI1 · MI1_Branch · MI2_Loading · MI2 · MI3 · MI_Done · MI_DoneJson) — docs/scenarios/11-content-flow.md §1 · §6.
 *   /mi              MI0  목록(보드 List content=mi · 저장된 것 = 허브, 작성 중 = /v1/mi-flows)
 *   /mi/new          MI1  사전 작업 Storyboard 고르기(보드 Gate · 이미 있으면 MI1_Branch 수정/복제본) · `?sb=&auto=1` 은 바로 만들기(CF-07)
 *   /mi/flow/:id     MI2_Loading(AI 가 Storyboard 를 먼저 읽는다 — CF-08 의 MI 예외) → MI2 검색어 · 검색 조건 → (웹 검색) → MI3 정제 → MI_Done
 *                    저장한 MI 를 열면(Gate 「수정」 · 목록 「열기」) Storyboard 를 다시 읽고 고치기 시작(v1 → v2). `?done=1` 은 완료 화면.
 */
import { useEffect, useRef, useState } from 'react';
import { Link, Navigate, useParams, useSearchParams } from 'react-router';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { CONTENT, ContentListScreen, FlowBar, FlowDoneView, GateScreen, useShellPage, type DraftRow } from '@/shell';
import { ErrorState, FlowScreen, Skeleton, josa, toast } from '@/ui';
import { GROUPS, isBusy, mfApi, mfKey, mfRoute, nOn, qsOf, useMfActions, useMiFlow, useMiFlows, type MFDoc, type MFStageOut } from './api';
import { usePacedSteps } from './pace';
import { RefineView } from './RefineStep';
import { LoadingView, SearchView } from './SearchStep';
import './miflow.css';

const SECTION = CONTENT.mi.label;
const STEPS = CONTENT.mi.steps;

/** MI0 — 보드 List(content=mi). 저장 전 초안은 「작성 중」 */
export function MiListScreen() {
  const flows = useMiFlows();
  const drafts: DraftRow[] = (flows.data?.items ?? []).filter((m) => m.status !== 'done')
    .map((m) => ({ title: m.title, ref: m.code ?? null, to: mfRoute(m.id), sbIds: m.sb_id ? [m.sb_id] : [], when: m.updated_at }));
  return <ContentListScreen content="mi" drafts={drafts} />;
}

/** MI1 · MI1_Branch — 보드 Gate(content=mi). 이전 흐름 링크(`/mi/new?rq=` — 요구사항 정의서의 「Market Intelligence」)는 이전 MI1 로 */
export function MiGateScreen() {
  const [sp] = useSearchParams();
  const qc = useQueryClient();
  if (sp.get('rq') && !sp.get('sb')) return <Navigate to={`/mi/legacy/new?${sp.toString()}`} replace />;
  // 만든 문서(분석 중)를 캐시에 먼저 넣어 편집 화면이 분석 단계부터 그리게 한다(빠른 모델이면 첫 조회 때 이미 끝나 있다)
  return <GateScreen content="mi" initialSb={sp.get('sb')} autoStart={sp.get('auto') === '1'}
    onStart={async ({ sbId }) => { const d = await mfApi.create(sbId); qc.setQueryData(mfKey(d.id), d); return mfRoute(d.id); }} />;
}

/** 저장한 MI 를 열어 다시 읽기 시작하기 전(응답 전) — 서버 분석 단계와 같은 이름 */
const firstSteps = (sb: string) => [
  { key: 'read', label: `Storyboard ${sb} 읽기`, state: 'run' as const, note: '' },
  { key: 'extract', label: '고객사 · 업종 · 공간 · 요구 뽑기', state: 'wait' as const, note: '' },
  { key: 'queries', label: '시장 · 고객사 · 사용자 검색어 만들기', state: 'wait' as const, note: '' },
];

interface DoneInfo { out: MFStageOut | null; prev: { ver: number | null; kept: number } | null }

/** MI_Done · MI_DoneJson — 보드 Done(content=mi): 요약본에 더해진 부분 · stages.mi(접힘) · 전체 JSON · 후속 작업 없음 */
function MiDone({ doc, info, onEdit }: { doc: MFDoc; info: DoneInfo; onEdit: () => void }) {
  // 새로 고침해서 연 완료 화면이면 저장 응답이 없다 → 지금 값으로 만든 stages.mi · 요약 줄(GET …/stage)
  const st = useQuery({ queryKey: ['mi', 'mi-flow', doc.id, 'stage'], enabled: !info.out, queryFn: () => mfApi.stage(doc.id) });
  const out = info.out ?? st.data ?? null;
  const ver = (out?.stage as { ver?: number } | undefined)?.ver ?? doc.ver ?? 1;
  const kept = (out?.stage as { counts?: { kept?: number } } | undefined)?.counts?.kept ?? doc.counts.kept;
  const code = doc.code ?? 'MI';
  const prev = info.prev;
  const edited = prev ? prev.ver != null : ver > 1;
  const by = doc.counts.by_group ?? {};
  const parts = GROUPS.map((g) => `${g.label} ${(by[g.label] ?? [0])[0]}`).join(' · ');
  const sub = prev && prev.ver != null ? `${code} v${prev.ver} → v${ver} · 담은 정보 ${prev.kept} → ${kept}`
    : edited ? `${code} v${ver} · 담은 정보 ${kept}` : `${parts} · 담은 정보 ${kept}개를 Storyboard에 담았어요`;
  const synced = info.out?.flow_sync?.synced ?? [];
  if (!out) return <div className="wm-page"><Skeleton h={480} r={16} /></div>;
  return (
    <div className="mif-done">
      <FlowDoneView sbId={doc.sb_id} stageKey="mi" stage={out.stage} mdAdded={out.flow_sync?.md_added || out.summary_md}
        title={edited ? 'MI를 고쳐 저장했어요' : 'MI를 저장했어요'} sub={sub} onEdit={onEdit}
        note={synced.length ? `연결된 Storyboard ${synced.length + 1}개에 반영했어요` : '요약본이 방금 갱신됐어요'}
        follow={(
          <div className="mif-nofollow">
            <span>이 콘텐츠는 후속 작업이 없어요. Storyboard에서 다른 콘텐츠를 이어서 만들 수 있어요.</span>
            <Link to={`/storyboard/flow/${doc.sb_id}`}>Storyboard로</Link>
          </div>
        )} />
    </div>
  );
}

function Body({ id }: { id: string }) {
  const q = useMiFlow(id);
  const actions = useMfActions(id);
  const [sp, setSp] = useSearchParams();
  const [info, setInfo] = useState<DoneInfo | null>(sp.get('done') === '1' ? { out: null, prev: null } : null);
  const d = q.data;
  const busy = isBusy(d);
  const prog = d?.progress ?? null;
  const paced = usePacedSteps(prog?.steps ?? [], busy, `${prog?.kind ?? ''}:${prog?.job_id ?? ''}`);
  const starting = useRef(false);

  // 저장한 MI 를 열면 고치기 시작(Gate 「수정」 · 목록 「열기」 · Storyboard 「편집 화면에서 고치기」) — 보드 MI2 「MI-01 수정」
  const startEdit = () => {
    if (starting.current) return;
    starting.current = true;
    actions.analyze().catch((e) => toast((e as Error).message || 'Storyboard를 다시 읽지 못했어요')).finally(() => { starting.current = false; });
  };
  useEffect(() => {
    if (d && d.phase === 'done' && !info) startEdit();
  }, [d?.phase, info]); // eslint-disable-line react-hooks/exhaustive-deps

  const view: 'load' | 'analyze' | 'search' | 'searching' | 'refine' | 'done' =
    !d ? 'load' : info && (info.out || d.status === 'done') ? 'done'
      : d.phase === 'done' ? 'analyze'
        : prog?.kind === 'analyze' && (d.phase === 'analyzing' || !paced.settled) ? 'analyze'
          : prog?.kind === 'search' && (d.phase === 'searching' || !paced.settled) ? 'searching'
            : d.phase === 'refine' ? 'refine' : 'search';
  const editing = d?.ver != null && view !== 'done';
  const code = d?.code ?? 'MI';
  useShellPage({
    section: SECTION,
    title: !d ? '' : view === 'done' ? code : editing ? `${code} 수정` : `새 ${CONTENT.mi.short}`,
    hasTask: view !== 'done',
    stepper: view === 'done' ? { steps: STEPS, current: 3, complete: true } : { steps: STEPS, current: view === 'refine' ? 3 : 2 },
  });

  if (q.isError) return <div className="wm-page"><ErrorState message="MI를 불러오지 못했어요 · 지워졌거나 주소가 바뀌었을 수 있어요" onRetry={() => q.refetch()} /></div>;
  if (!d) return <div className="wm-page"><Skeleton h={520} r={16} /></div>;
  if (view === 'done' && info) {
    return <MiDone doc={d} info={info} onEdit={() => { setInfo(null); setSp({}, { replace: true }); startEdit(); }} />;
  }
  const note = editing && d.ver != null
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
        <RefineView doc={d} actions={actions} onFinished={(out, prev) => { setInfo({ out, prev }); setSp({ done: '1' }, { replace: true }); }} />
      )}
    </FlowScreen>
  );
}

/** `/mi/flow/:id` — 다른 MI 로 옮겨 가면 화면 상태를 새로 */
export function MiFlowPage() {
  const { id = '' } = useParams();
  return <Body key={id} id={id} />;
}
