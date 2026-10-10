/**
 * 고객 요구사항 새 흐름(보드 webapp1 RQ0 · RQ1 · RQ1_AI · RQ_Done) — docs/scenarios/11-content-flow.md §6.
 *   /requirements            RQ0  목록(보드 List content=rq · 저장된 것 = 허브, 작성 중 = /v1/rq-flows)
 *   /requirements/new        RQ1  새 요구사항(사전 작업이 없어 Gate 없이 바로 폼 · 첫 입력 때 만든다)
 *   /requirements/flow/:id   RQ1 · RQ1_AI 편집 → 저장 → RQ_Done(FlowDoneView · Storyboard 자동 생성)
 */
import { useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { CONTENT, ContentListScreen, FlowDoneView, useFlow, useShellPage, type DraftRow } from '@/shell';
import { ErrorState, FollowCard, Skeleton, josa } from '@/ui';
import { rfKey, rfRoute, useRfDelete, useRqFlow, useRqFlows, type RFDoc, type RFStageOut } from './api';
import { Editor } from './Editor';
import { euro } from './form';
import './rqflow.css';

const SECTION = '고객 요구사항';
const STEPS = ['요구사항 입력', '저장'];

/** RQ0 — 보드 List(content=rq). 아무것도 적지 않은 초안은 보이지 않는다 · 저장 전 초안은 줄에 손을 올리면 ×(지우기) */
export function RqListScreen() {
  const flows = useRqFlows();
  const remove = useRfDelete();
  const drafts: DraftRow[] = (flows.data?.items ?? [])
    .filter((m) => m.status !== 'done' && (m.title !== '새 요구사항' || m.counts.reqs > 0))
    .map((m) => ({ title: m.title, ref: m.code, to: rfRoute(m.id), sbIds: m.sb_ids, when: m.updated_at,
      onDelete: m.ver === 0 && !m.sb_ids.length ? () => remove(m.id) : undefined }));
  return <ContentListScreen content="rq" drafts={drafts} />;
}

/** 요약본 머리(첫 `## ` 절 앞 줄들) + 더해진 절 */
function withHead(summary: string | undefined, added: string) {
  if (!summary) return added;
  const lines = summary.split('\n');
  const i = lines.findIndex((l) => l.startsWith('## '));
  const head = (i > 0 ? lines.slice(0, i) : []).join('\n').trimEnd();
  return head ? `${head}\n\n${added}` : added;
}

/** RQ_Done — 보드 Done(content=rq): 요약본에 더해진 부분 · stages.rq(접힘) · 전체 JSON · 후속 작업 DSS */
function RqDone({ out, onEdit }: { out: RFStageOut; onEdit: () => void }) {
  const sbId = out.sb_id ?? null;
  const flow = useFlow(sbId);
  const name = out.sb_name ?? flow.data?.name ?? sbId ?? '';
  const synced = out.flow_sync?.synced ?? [];
  const sub = !sbId ? 'Storyboard를 만들지 못했어요 · 다시 저장하면 다시 만들어요'
    : out.created ? `Storyboard ‘${name}’(${sbId})${josa(sbId, '이', '가')} 자동으로 만들어졌어요`
      : synced.length ? `연결된 Storyboard ${synced.length + 1}개에 반영했어요` : `Storyboard ‘${name}’(${sbId})에 반영했어요`;
  const added = out.flow_sync?.md_added || out.summary_md;
  // 새로 만든 Storyboard 면 요약본 머리(# 이름 · 고객 줄)도 이번에 더해진 부분이다(보드 RQ_Done) — 「남은 것」 절은 넣지 않는다
  const md = out.created ? withHead(flow.data?.summary_md, added) : added;
  return (
    <div className="rqf-done">
      {/* stage 는 허브의 stages.rq(ref · ver 포함)를 쓴다 — 허브가 없을 때만 저장 응답 값 */}
      <FlowDoneView sbId={sbId} sbIds={sbId ? [sbId, ...(out.doc.sb_ids ?? []).filter((x) => x !== sbId)] : undefined} stageKey="rq" stage={sbId ? undefined : out.stage}
        mdAdded={md} title="요구사항을 저장했어요" sub={sub} onEdit={onEdit} newStoryboard={!!out.created}
        follow={sbId ? (
          <div className="rqf-follows">
            <FollowCard to={`/dss/new?sb=${encodeURIComponent(sbId)}&auto=1`} icon={CONTENT.dss.icon} title={CONTENT.dss.label}
              desc={`${sbId}${euro(sbId)} 공간마다 제품 · 솔루션을 골라요`} />
          </div>
        ) : undefined} />
    </div>
  );
}

function Body({ id, onCreated }: { id: string | undefined; onCreated: (d: RFDoc) => void }) {
  const nav = useNavigate();
  const qc = useQueryClient();
  const q = useRqFlow(id);
  const [done, setDone] = useState<RFStageOut | null>(null);
  const d = q.data;
  const title = done ? done.doc.code : d && d.ver > 0 ? d.code : '새 요구사항';
  useShellPage({ section: SECTION, title, hasTask: !done, stepper: done ? { steps: ['요구사항 입력'], current: 1, complete: true } : { steps: STEPS, current: 1 } });
  if (id && q.isError) {
    return <div className="wm-page"><ErrorState message="요구사항을 불러오지 못했어요 · 지워졌거나 주소가 바뀌었을 수 있어요" onRetry={() => q.refetch()} /></div>;
  }
  if (id && !d) return <div className="wm-page"><Skeleton h={520} r={16} /></div>;
  if (done) {
    return <RqDone out={done} onEdit={() => { qc.setQueryData(rfKey(done.doc.id), done.doc); setDone(null); }} />;
  }
  return (
    <Editor initial={d ?? null} onFinished={setDone}
      onCreated={(doc) => { onCreated(doc); nav(rfRoute(doc.id), { replace: true }); }} />
  );
}

/** `/requirements/new` · `/requirements/flow/:id` — 새로 만든 문서로 주소가 바뀔 때는 편집 상태를 그대로 둔다 */
export function RqFlowPage() {
  const { id } = useParams();
  const created = useRef<string | null>(null);
  const [key, setKey] = useState(id ?? 'new');
  const [prev, setPrev] = useState(id);
  if (id !== prev) {
    setPrev(id);
    if (!(id && id === created.current)) setKey(id ?? 'new');
  }
  return <Body key={key} id={id} onCreated={(d) => { created.current = d.id; }} />;
}
