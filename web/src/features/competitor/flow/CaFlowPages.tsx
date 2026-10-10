/**
 * 경쟁사 분석 새 흐름(보드 webapp1 CA0 · CA1 · CA2 · CA2_Info · CA2_Pc · CA2_AI · CA_Done · CA_DoneJson) — docs/scenarios/11-content-flow.md §6.
 *   /competitor            CA0  목록(보드 List content=ca · 저장된 것 = 허브, 작성 중 = /v1/ca-flows)
 *   /competitor/new        CA1  사전 작업 Storyboard 고르기(보드 Gate · `?sb=&auto=1` = Storyboard 화면의 「만들기」 → 바로 만든다)
 *   /competitor/flow/:id   CA2  리스트업 · 제안 기준 비교(`?tab=info|pc`) → 저장 → CA_Done(FlowDoneView · 전체 JSON)
 * 이전 흐름의 목록 · 새로 만들기는 /competitor/legacy · /competitor/legacy/new(나머지 /competitor/:id/... 그대로).
 */
import { useState } from 'react';
import { Link, Navigate, useParams, useSearchParams } from 'react-router';
import { ContentListScreen, FlowDoneView, GateScreen, useShellPage, type DraftRow } from '@/shell';
import { ErrorState, Skeleton } from '@/ui';
import { cfRoute, createCaFlow, useCaFlow, useCaFlows, type CFDoc, type CFStageOut } from './api';
import { Editor } from './Editor';
import './caflow.css';

const SECTION = '경쟁사 분석';
const STEPS = ['Storyboard', '경쟁사 리스트업'];

/** CA0 — 보드 List(content=ca). 작성 중 초안은 이 서비스 목록에서 */
export function CaListScreen() {
  const flows = useCaFlows();
  const drafts: DraftRow[] = (flows.data?.items ?? []).filter((m) => m.status !== 'done')
    .map((m) => ({ title: m.title, ref: m.code ?? null, to: cfRoute(m.id), sbIds: m.sb_id ? [m.sb_id] : [], when: m.updated_at }));
  return <ContentListScreen content="ca" drafts={drafts} />;
}

/** CA1 — 보드 Gate(content=ca). 이전 흐름의 정의서 진입(`?input=requirements&rq=`)은 이전 화면으로 */
export function CaGateScreen() {
  const [sp] = useSearchParams();
  if (sp.get('input')) return <Navigate to={`/competitor/legacy/new?${sp.toString()}`} replace />;
  return <GateScreen content="ca" initialSb={sp.get('sb')} autoStart={sp.get('auto') === '1'}
    onStart={async ({ sbId }) => cfRoute((await createCaFlow({ sb_id: sbId })).id)} />;
}

/** CA_Done — 보드 Done(content=ca): 후속 작업 없음 · 「Storyboard로」 */
function CaDone({ d, out, onEdit }: { d: CFDoc; out: CFStageOut; onEdit: () => void }) {
  const st = out.stage as { counts?: { competitors?: number } };
  const n = st.counts?.competitors ?? d.counts.competitors;
  const synced = out.flow_sync?.synced ?? [];
  const sbId = d.sb_id ?? null;
  return (
    <FlowDoneView sbId={sbId} stageKey="ca" stage={out.stage} mdAdded={out.flow_sync?.md_added || out.summary_md}
      title="경쟁사 분석을 저장했어요" sub={`경쟁사 ${n}곳을 Storyboard에 담았어요`}
      note={synced.length ? `연결된 Storyboard ${synced.length + 1}개에 반영했어요` : '요약본이 방금 갱신됐어요'}
      onEdit={onEdit}
      follow={(
        <div className="caf-nofollow">
          <span>이 콘텐츠는 후속 작업이 없어요. Storyboard에서 다른 콘텐츠를 이어서 만들 수 있어요.</span>
          {sbId && <Link to={`/storyboard/flow/${sbId}`}>Storyboard로</Link>}
        </div>
      )} />
  );
}

function Body({ id }: { id: string }) {
  const q = useCaFlow(id);
  const [done, setDone] = useState<CFStageOut | null>(null);
  const d = q.data;
  const title = d && (done || d.ver) ? (d.code ?? d.title) : '새 경쟁사 분석';
  useShellPage({ section: SECTION, title, hasTask: !done, stepper: { steps: STEPS, current: 2, complete: !!done } });
  if (q.isError) {
    return <div className="wm-page"><ErrorState message="경쟁사 분석을 불러오지 못했어요 · 지워졌거나 주소가 바뀌었을 수 있어요" onRetry={() => q.refetch()} /></div>;
  }
  if (!d) return <div className="wm-page"><Skeleton h={520} r={16} /></div>;
  if (done) return <CaDone d={d} out={done} onEdit={() => setDone(null)} />;
  return <Editor doc={d} onFinished={setDone} />;
}

/** `/competitor/flow/:id` */
export function CaFlowPage() {
  const { id = '' } = useParams();
  return <Body key={id} id={id} />;
}
