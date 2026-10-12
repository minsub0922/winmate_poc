/**
 * 경쟁사 분석 새 흐름(보드 webapp1 CA0 · CA1 · CA2 · CA2_Info · CA2_Pc · CA2_AI · View content=ca) — docs/scenarios/11-content-flow.md §6.
 *   /competitor            CA0  목록(보드 List content=ca · 저장된 것 = 허브, 작성 중 = /v1/ca-flows)
 *   /competitor/new        CA1  사전 작업 Storyboard 고르기(보드 Gate · `?sb=&auto=1` = Storyboard 화면의 「만들기」 → 바로 만든다)
 *   /competitor/flow/:id   저장한 분석 = CA_View(보드 View content=ca) · 저장 전 초안 · `?edit=1` = CA2 리스트업 · 제안 기준 비교(`?tab=info|pc`)
 *                          → 저장 → 같은 경로의 보기(`?edit` · `?tab` 를 뗀다 · 완료 안내 없음)
 * 이전 흐름의 목록 · 새로 만들기는 /competitor/legacy · /competitor/legacy/new(나머지 /competitor/:id/... 그대로).
 */
import { Navigate, useParams, useSearchParams } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { ContentListScreen, GateScreen, useEditMode, useFlowInvalidate, useShellPage, type DraftRow } from '@/shell';
import { ErrorState, Skeleton, toast } from '@/ui';
import { cfKey, cfListKey, cfRoute, createCaFlow, useCaFlow, useCaFlows, useCfDelete, type CFDoc } from './api';
import { CaView } from './CaView';
import { Editor } from './Editor';
import './caflow.css';

const SECTION = '경쟁사 분석';
const STEPS = ['Storyboard', '경쟁사 리스트업'];

/** CA0 — 보드 List(content=ca). 작성 중 초안은 이 서비스 목록에서 — 손을 올리면 ×(지우기) */
export function CaListScreen() {
  const flows = useCaFlows();
  const remove = useCfDelete();
  const drafts: DraftRow[] = (flows.data?.items ?? []).filter((m) => m.status !== 'done')
    .map((m) => ({ title: m.title, ref: m.code ?? null, to: cfRoute(m.id), sbIds: m.sb_id ? [m.sb_id] : [], when: m.updated_at, onDelete: () => remove(m.id) }));
  return <ContentListScreen content="ca" drafts={drafts} />;
}

/** CA1 — 보드 Gate(content=ca). 이전 흐름의 정의서 진입(`?input=requirements&rq=`)은 이전 화면으로.
 *  같은 Storyboard 의 저장 전 초안이 있으면 서버가 그 초안을 돌려준다 → 이어서 연다(초안이 늘지 않음) */
export function CaGateScreen() {
  const [sp] = useSearchParams();
  const qc = useQueryClient();
  const flows = useCaFlows();
  const drafts: DraftRow[] = (flows.data?.items ?? []).filter((m) => m.status !== 'done')
    .map((m) => ({ title: m.title, ref: m.code ?? null, to: cfRoute(m.id), sbIds: m.sb_id ? [m.sb_id] : [], when: m.updated_at }));
  if (sp.get('input')) return <Navigate to={`/competitor/legacy/new?${sp.toString()}`} replace />;
  return <GateScreen content="ca" initialSb={sp.get('sb')} autoStart={sp.get('auto') === '1'} drafts={drafts}
    onStart={async ({ sbId }) => {
      const { doc: d, reused } = await createCaFlow({ sb_id: sbId });
      qc.setQueryData(cfKey(d.id), d);
      void qc.invalidateQueries({ queryKey: cfListKey });
      if (reused) toast(`작성 중이던 ${d.code ?? '경쟁사 분석'} 초안을 이어서 열어요`);
      return cfRoute(d.id);
    }} />;
}

/** 한 번이라도 저장했으면 보여 줄 완성본이 있다 */
const isSaved = (d: CFDoc | undefined) => !!d && (d.status === 'done' || d.ver != null);

function Body({ id }: { id: string }) {
  const q = useCaFlow(id);
  const qc = useQueryClient();
  const inval = useFlowInvalidate();
  const { editing, toView } = useEditMode();
  const d = q.data;
  const view = isSaved(d) && !editing;
  const title = d && d.ver ? (d.code ?? d.title) : '새 경쟁사 분석';
  useShellPage(view ? { section: SECTION, title, hasTask: false } : { section: SECTION, title, hasTask: true, stepper: { steps: STEPS, current: 2 } });
  if (q.isError) {
    return <div className="wm-page"><ErrorState message="경쟁사 분석을 불러오지 못했어요 · 지워졌거나 주소가 바뀌었을 수 있어요" onRetry={() => q.refetch()} /></div>;
  }
  if (!d) return <div className="wm-page"><Skeleton h={520} r={16} /></div>;
  if (view) return <CaView doc={d} />;
  return (
    <Editor doc={d} onFinished={(doc) => {
      // 저장하면 그 분석 보기로(같은 주소 · ?edit · ?tab 만 뗀다 · 완료 안내 없음)
      qc.setQueryData(cfKey(doc.id), doc);
      void qc.invalidateQueries({ queryKey: cfListKey });
      void inval();
      toView(['tab']);
    }} />
  );
}

/** `/competitor/flow/:id` */
export function CaFlowPage() {
  const { id = '' } = useParams();
  return <Body key={id} id={id} />;
}
