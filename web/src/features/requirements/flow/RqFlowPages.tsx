/**
 * 고객 요구사항 새 흐름(보드 webapp1 RQ0 · RQ1 · RQ_View) — docs/scenarios/11-content-flow.md §6.
 *   /requirements                  RQ0  목록(보드 List content=rq · 저장된 것 = 허브, 작성 중 = /v1/rq-flows)
 *   /requirements/new              RQ1  새 요구사항(사전 작업이 없어 Gate 없이 바로 폼 · 첫 입력 때 만든다)
 *   /requirements/flow/:id         저장한 요구사항 = RQ_View(보기 · 후속 DSS) · 저장 전 초안 = RQ1 편집
 *   /requirements/flow/:id?edit=1  RQ1 편집 → 저장하면 다시 보기(완료 안내 화면은 없다)
 */
import { useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { ContentListScreen, useEditMode, useFlowInvalidate, useShellPage, type DraftRow } from '@/shell';
import { ErrorState, Skeleton } from '@/ui';
import { rfKey, rfListKey, rfRoute, useRfDelete, useRqFlow, useRqFlows, type RFDoc } from './api';
import { Editor } from './Editor';
import { RqView } from './RqView';
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

/** 한 번이라도 저장했으면 보여 줄 완성본이 있다 */
const isSaved = (d: RFDoc | undefined) => !!d && (d.status === 'done' || d.ver > 0);

function Body({ id, onCreated }: { id: string | undefined; onCreated: (d: RFDoc) => void }) {
  const nav = useNavigate();
  const qc = useQueryClient();
  const inval = useFlowInvalidate();
  const { editing, toView } = useEditMode();
  const q = useRqFlow(id);
  const d = q.data;
  const view = isSaved(d) && !editing;
  const title = d && d.ver > 0 ? d.code : '새 요구사항';
  useShellPage(view ? { section: SECTION, title: d!.code, hasTask: false } : { section: SECTION, title, hasTask: true, stepper: { steps: STEPS, current: 1 } });
  if (id && q.isError) {
    return <div className="wm-page"><ErrorState message="요구사항을 불러오지 못했어요 · 지워졌거나 주소가 바뀌었을 수 있어요" onRetry={() => q.refetch()} /></div>;
  }
  if (id && !d) return <div className="wm-page"><Skeleton h={520} r={16} /></div>;
  if (view) return <RqView doc={d!} />;
  return (
    <Editor initial={d ?? null}
      onFinished={(out) => {
        // 저장하면 그 요구사항 보기로(같은 주소 · ?edit 만 뗀다)
        qc.setQueryData(rfKey(out.doc.id), out.doc);
        void qc.invalidateQueries({ queryKey: rfListKey });
        inval();
        if (out.doc.id !== id) nav(rfRoute(out.doc.id), { replace: true }); else toView();
      }}
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
