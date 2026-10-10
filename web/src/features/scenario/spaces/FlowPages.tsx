/**
 * 공간 시나리오 목록 · 사전 작업 고르기(보드 webapp1 SC0 = List content=sc · SC1 = Gate content=sc) — 셸 흐름 화면에 공간 시나리오 자원만 붙인다.
 *   /scenario        SC0  저장된 것 = 허브(`/v1/flows/contents/sc`), 작성 중 = `/v1/space-sets`
 *   /scenario/new    SC1  `?sb=&auto=1`(DSS 완료 · Storyboard 화면의 「만들기」)이면 고르기를 건너뛰고 바로 만든다 → /scenario/spaces/:id(SC2)
 * 이전 흐름으로 들어오던 주소(`/scenario?image_version=` · `/scenario/new?sb=sb_…|from=|mi=`)는 index.tsx 가 이전 화면으로 나눈다.
 */
import { useSearchParams } from 'react-router';
import { CONTENT, ContentListScreen, GateScreen, useShellPage, type DraftRow } from '@/shell';
import { createSpaceSet, useSpaceSets } from './api';

/** 보드 SC1 · SC_Done 스텝바(Gate META `['Storyboard', '공간별 시나리오']`) — SC2 보드는 「공간 · 시나리오」 */
export const GATE_STEPS = ['Storyboard', '공간별 시나리오'];

export function ScListScreen() {
  const q = useSpaceSets();
  const drafts: DraftRow[] = (q.data?.items ?? []).filter((m) => m.status !== 'done')
    .map((m) => ({ title: m.title, ref: m.code ?? null, to: `/scenario/spaces/${m.id}`, sbIds: m.sb_id ? [m.sb_id] : [], when: m.updated_at }));
  return <ContentListScreen content="sc" drafts={drafts} />;
}

export function ScGateScreen() {
  const [sp] = useSearchParams();
  return <ScGate initialSb={sp.get('sb')} autoStart={sp.get('auto') === '1'} />;
}

function ScGate({ initialSb, autoStart }: { initialSb: string | null; autoStart: boolean }) {
  // 셸 GateScreen 의 스텝바는 CONTENT.sc.steps(SC2 문구) — 보드 SC1 문구로 덮는다(부모 효과가 자식 효과 뒤에 돈다)
  useShellPage({ section: CONTENT.sc.label, title: `새 ${CONTENT.sc.short}`, hasTask: false, stepper: { steps: GATE_STEPS, current: 1 } });
  return <GateScreen content="sc" initialSb={initialSb} autoStart={autoStart}
    onStart={async ({ sbId }) => `/scenario/spaces/${(await createSpaceSet({ sb_id: sbId })).id}`} />;
}
