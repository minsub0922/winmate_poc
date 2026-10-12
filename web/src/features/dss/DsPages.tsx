/**
 * 공간별 제품 매칭 DSS 새 흐름(보드 webapp1 DS0 · DS1 · DS2 · DS2_AI · DS4 · DS4_AI · DS_View) — docs/scenarios/11-content-flow.md §6.
 *   /dss                  DS0  목록(보드 List content=dss · 저장된 것 = 허브, 작성 중 = /v1/dss)
 *   /dss/new              DS1  사전 작업 Storyboard 고르기(보드 Gate content=dss · `?sb=&auto=1` 이면 바로 만든다)
 *   /dss/:id              저장한 DSS = DS_View(보기 · 후속 공간 시나리오 · Spec 시트) · 저장 전 초안 = DS2 편집
 *   /dss/:id?edit=1       DS2 업종 · 공간 · 공간별 제품 → `&step=solution` DS4 솔루션 → 저장하면 다시 보기(완료 안내 화면은 없다)
 */
import { useParams, useSearchParams } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { CONTENT, ContentListScreen, GateScreen, useEditMode, useFlowInvalidate, useShellPage, type DraftRow, type ShellPageConfig } from '@/shell';
import { ErrorState, Skeleton, toast } from '@/ui';
import { createDss, dsKey, dsListKey, dsRoute, useDsActions, useDsDelete, useDss, useDssList, type DSDoc } from './api';
import { DsView } from './DsView';
import { dsShell } from './shellcfg';
import { SolutionsStep } from './SolutionsStep';
import { SpacesStep } from './SpacesStep';
import './dss.css';

const M = CONTENT.dss;

/** DS0 — 보드 List(content=dss). 작성 중(저장 전) DSS 는 초안 줄 — 손을 올리면 ×(지우기) */
export function DsListScreen() {
  const list = useDssList();
  const remove = useDsDelete();
  const drafts: DraftRow[] = (list.data?.items ?? []).filter((d) => d.status !== 'done')
    .map((d) => ({ title: d.title, ref: d.code ?? null, to: dsRoute(d.id), sbIds: d.sb_id ? [d.sb_id] : [], when: d.updated_at, onDelete: () => remove(d.id),
      // 지금 단계(보드 List v61 n/3): 솔루션을 하나라도 골랐으면 3 솔루션, 아니면 2 공간 · 제품
      step: d.counts.solutions > 0 ? 3 : 2 }));
  return <ContentListScreen content="dss" drafts={drafts} />;
}

/** DS1 — 보드 Gate(content=dss). Storyboard 화면의 「만들기」는 `?sb=<id>&auto=1` 로 와서 고르기를 건너뛴다(CF-07).
 *  같은 Storyboard 의 저장 전 초안이 있으면 서버가 그 초안을 돌려준다 → 이어서 연다(초안이 늘지 않음) */
export function DsGateScreen() {
  const [sp] = useSearchParams();
  const qc = useQueryClient();
  const list = useDssList();
  const drafts: DraftRow[] = (list.data?.items ?? []).filter((d) => d.status !== 'done')
    .map((d) => ({ title: d.title, ref: d.code ?? null, to: dsRoute(d.id), sbIds: d.sb_id ? [d.sb_id] : [], when: d.updated_at }));
  return <GateScreen content="dss" initialSb={sp.get('sb')} autoStart={sp.get('auto') === '1'} drafts={drafts}
    onStart={async ({ sbId }) => {
      const { doc: d, reused } = await createDss(sbId);
      qc.setQueryData(['dss', 'doc', d.id], d);
      void qc.invalidateQueries({ queryKey: dsListKey });
      if (reused) toast(`작성 중이던 ${d.code ?? 'DSS'} 초안을 이어서 열어요`);
      return dsRoute(d.id);
    }} />;
}

/** 셸 맥락만 넘기는 빈 조각(불러오는 중 · 보기) — 작업 화면은 SpacesStep · SolutionsStep 이 직접 넘긴다 */
function Shell({ cfg }: { cfg: ShellPageConfig }) {
  useShellPage(cfg);
  return null;
}

/** 한 번이라도 저장했으면 보여 줄 완성본이 있다 */
const isSaved = (d: DSDoc | undefined) => !!d && (d.status === 'done' || d.ver != null);

/** `/dss/:id` — 저장한 DSS 는 DS_View · `?edit=1`(또는 저장 전 초안)은 DS2(공간 · 제품) → DS4(솔루션, `?step=solution`) → 저장하면 보기로 */
export function DsEditPage() {
  const { id = '' } = useParams();
  const q = useDss(id);
  const actions = useDsActions(id);
  const qc = useQueryClient();
  const inval = useFlowInvalidate();
  const { editing, toView } = useEditMode();
  const [sp, setSp] = useSearchParams();
  const step = sp.get('step') === 'solution' ? 3 : 2;
  const d = q.data;
  const view = isSaved(d) && !editing;
  const goStep = (s: 2 | 3) => setSp((prev) => {
    const n = new URLSearchParams(prev);
    if (s === 3) n.set('step', 'solution'); else n.delete('step');
    return n;
  });
  if (q.isError) return <div className="wm-page"><Shell cfg={dsShell(undefined, step)} /><ErrorState message="DSS를 불러오지 못했어요 · 지워졌거나 주소가 바뀌었을 수 있어요" onRetry={() => q.refetch()} /></div>;
  if (!d) return <div className="wm-page"><Shell cfg={dsShell(undefined, step)} /><Skeleton h={520} r={16} /></div>;
  if (view) {
    return (<>
      <Shell cfg={{ section: M.label, title: d.code ?? 'DSS', hasTask: false }} />
      <DsView doc={d} />
    </>);
  }
  return step === 3
    ? <SolutionsStep doc={d} actions={actions} onBack={() => goStep(2)} onSaved={async () => {
        // 저장하면 그 DSS 보기로(같은 주소 · ?edit · ?step 만 뗀다). :finish 는 stages.dss 만 돌려주므로
        // 저장 판(status done · ver)이 든 문서를 다시 읽어 캐시에 넣은 뒤 보기로 바꾼다
        const fresh = await q.refetch();
        if (fresh.data) qc.setQueryData(dsKey(id), fresh.data);
        void qc.invalidateQueries({ queryKey: dsListKey });
        void inval();
        toView(['step']);
      }} />
    : <SpacesStep doc={d} actions={actions} onNext={() => goStep(3)} />;
}
