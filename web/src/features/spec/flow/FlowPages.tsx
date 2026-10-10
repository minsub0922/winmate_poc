/**
 * Spec 시트 새 흐름(보드 webapp1 SP0 · SP1 · SP2 · SP_Done) — docs/scenarios/11-content-flow.md §6 `sp`.
 *   /spec            SP0  목록(보드 List content=sp · 저장된 것 = 허브, 작성 중 = /v1/spec-flows)
 *   /spec/new        SP1  사전 작업 Storyboard 고르기(보드 Gate · `?sb=&auto=1` = Storyboard · DSS 완료 화면의 「만들기」 → 바로 만든다)
 *   /spec/flow/:id   SP2  시트 작성 → 저장 → SP_Done(FlowDoneView · 전체 JSON) — ./SheetPage.tsx
 * `/spec/new?models=…` · `?from=…` · `?pop=…`(제품 상세 · MI · VP · 조감도에서 넘겨받은 모델 — Storyboard 없음)는 이전 흐름 입력 화면 `/spec/legacy/new` 로 그대로 넘긴다.
 */
import { Navigate, useLocation, useSearchParams } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { ContentListScreen, GateScreen, type DraftRow } from '@/shell';
import { createSpecFlow, deleteSpecFlow, sfListKey, sfRoute, useSpecFlows } from './api';

/** SP0 — 보드 List(content=sp). 작성 중 초안은 이 서비스 목록에서 · 저장 전 초안은 줄의 × 로 지운다(보드에 없음 — 셸이 확인을 묻는다) */
export function SpListScreen() {
  const q = useSpecFlows();
  const qc = useQueryClient();
  const drafts: DraftRow[] = (q.data?.items ?? []).filter((m) => m.status !== 'done')
    .map((m) => ({ title: m.title, ref: m.code ?? null, to: sfRoute(m.id), sbIds: m.sb_id ? [m.sb_id] : [], when: m.updated_at,
      onDelete: async () => { await deleteSpecFlow(m.id); void qc.invalidateQueries({ queryKey: sfListKey }); } }));
  return <ContentListScreen content="sp" drafts={drafts} />;
}

/** SP1 — 보드 Gate(content=sp) */
export function SpGateScreen() {
  const [sp] = useSearchParams();
  const loc = useLocation();
  const q = useSpecFlows();
  const drafts: DraftRow[] = (q.data?.items ?? []).filter((m) => m.status !== 'done')
    .map((m) => ({ title: m.title, ref: m.code ?? null, to: sfRoute(m.id), sbIds: m.sb_id ? [m.sb_id] : [], when: m.updated_at }));
  if (!sp.get('sb') && (sp.get('models') || sp.get('from') || sp.get('pop'))) {
    return <Navigate to={`/spec/legacy/new${loc.search}`} replace state={loc.state} />;
  }
  return <GateScreen content="sp" initialSb={sp.get('sb')} autoStart={sp.get('auto') === '1'} drafts={drafts}
    onStart={async ({ sbId }) => sfRoute((await createSpecFlow(sbId)).id)} />;
}
