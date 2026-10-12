/**
 * 공간 시나리오 목록 · 사전 작업 고르기(보드 webapp1 SC0 = List content=sc · SC1 = 목록 위 Gate 팝업 content=sc) — 셸 흐름 화면에 공간 시나리오 자원만 붙인다.
 *   /scenario        SC0  저장된 것 = 허브(`/v1/flows/contents/sc`), 작성 중 = `/v1/space-sets`
 *   /scenario/new    SC1  목록 위 Storyboard 고르기 팝업 → 고르면 바로 상세(/scenario/spaces/:id · SC2 새로 만들기). 닫으면 목록.
 *                         `?sb=&auto=1`(DSS 상세 · Storyboard 화면의 「만들기」)이면 고르기를 건너뛰고 바로 만든다
 * 이전 흐름으로 들어오던 주소(`/scenario?image_version=` · `/scenario/new?sb=sb_…|from=|mi=`)는 index.tsx 가 이전 화면으로 나눈다.
 */
import { useSearchParams } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { ContentListScreen, GateScreen, type DraftRow } from '@/shell';
import { createSpaceSet, deleteSpaceSet, ssListKey, useSpaceSets } from './api';

/** SC0 — 저장 전 초안(한 번도 저장하지 않은 것)만 줄의 × 로 지운다(보드에 없음 — 셸이 확인을 묻는다). 저장 뒤 고친 묶음은 허브 줄로 보인다 */
export function ScListScreen() {
  const q = useSpaceSets();
  const qc = useQueryClient();
  const drafts: DraftRow[] = (q.data?.items ?? []).filter((m) => m.status !== 'done')
    .map((m) => ({ title: m.title, ref: m.code ?? null, to: `/scenario/spaces/${m.id}`, sbIds: m.sb_id ? [m.sb_id] : [], when: m.updated_at,
      onDelete: m.ver ? undefined : async () => { await deleteSpaceSet(m.id); void qc.invalidateQueries({ queryKey: ssListKey }); } }));
  return <ContentListScreen content="sc" drafts={drafts} />;
}

export function ScGateScreen() {
  const [sp] = useSearchParams();
  return <ScGate initialSb={sp.get('sb')} autoStart={sp.get('auto') === '1'} />;
}

/** 보드 v63 SC1 — 목록 위 팝업(셸 GateScreen) · 스텝바 없음. 같은 Storyboard 의 저장 전 초안은 「초안 이어 쓰기」 */
function ScGate({ initialSb, autoStart }: { initialSb: string | null; autoStart: boolean }) {
  const q = useSpaceSets();
  const drafts: DraftRow[] = (q.data?.items ?? []).filter((m) => m.status !== 'done' && !m.ver)
    .map((m) => ({ title: m.title, ref: m.code ?? null, to: `/scenario/spaces/${m.id}`, sbIds: m.sb_id ? [m.sb_id] : [], when: m.updated_at }));
  return <GateScreen content="sc" initialSb={initialSb} autoStart={autoStart} drafts={drafts}
    onStart={async ({ sbId }) => `/scenario/spaces/${(await createSpaceSet({ sb_id: sbId })).id}`} />;
}
