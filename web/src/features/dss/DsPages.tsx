/**
 * 공간별 제품 매칭 DSS 새 흐름(보드 webapp1 DS0 · DS1 · DS2 · DS2_AI · DS4 · DS4_AI · DS_Done) — docs/scenarios/11-content-flow.md §6.
 *   /dss                  DS0  목록(보드 List content=dss · 저장된 것 = 허브, 작성 중 = /v1/dss)
 *   /dss/new              DS1  사전 작업 Storyboard 고르기(보드 Gate content=dss · `?sb=&auto=1` 이면 바로 만든다)
 *   /dss/:id              DS2  업종 · 공간 · 공간별 제품 → `?step=solution` DS4 솔루션 → 저장 → DS_Done(FlowDoneView · 후속 작업)
 */
import { useState } from 'react';
import { useParams, useSearchParams } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { CONTENT, ContentListScreen, FlowDoneView, GateScreen, useShellPage, type DraftRow, type ShellPageConfig } from '@/shell';
import { ErrorState, FollowCard, Skeleton, josa, toast } from '@/ui';
import { createDss, dsListKey, dsRoute, useDsActions, useDsDelete, useDss, useDssList, type DSDoc, type DSStageOut } from './api';
import { dsShell } from './shellcfg';
import { SolutionsStep } from './SolutionsStep';
import { SpacesStep } from './SpacesStep';
import './dss.css';

const M = CONTENT.dss;
/** 후속 작업 아이콘(보드 Done IC) */
const IC_SC = 'M4 6h16v12H4z M10 9l5 3-5 3V9z';
const IC_SP = 'M6 3h8l5 5v13H6V3z M14 3v5h5 M9 13h7 M9 17h7';

/** DS0 — 보드 List(content=dss). 작성 중(저장 전) DSS 는 초안 줄 — 손을 올리면 ×(지우기) */
export function DsListScreen() {
  const list = useDssList();
  const remove = useDsDelete();
  const drafts: DraftRow[] = (list.data?.items ?? []).filter((d) => d.status !== 'done')
    .map((d) => ({ title: d.title, ref: d.code ?? null, to: dsRoute(d.id), sbIds: d.sb_id ? [d.sb_id] : [], when: d.updated_at, onDelete: () => remove(d.id) }));
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

/** 숫자 뒤 조사(공간 6 · 제품 10 · 솔루션 3을) */
const eul = (n: number) => josa(String(n), '을', '를');

/** DS_Done — 보드 Done(content=dss): 요약본에 더해진 부분 · stages.dss(접힘) · 전체 JSON · 후속 작업 공간 시나리오 · Spec 시트 */
function DsDone({ doc, out, onEdit }: { doc: DSDoc; out: DSStageOut; onEdit: () => void }) {
  const sbId = doc.sb_id ?? null;
  const c = (out.stage as { counts?: { spaces: number; products: number; solutions: number } }).counts ?? doc.counts;
  const parts = [`공간 ${c.spaces}`, `제품 ${c.products}`, ...(c.solutions ? [`솔루션 ${c.solutions}`] : [])];
  const last = c.solutions ? c.solutions : c.products;
  const synced = out.flow_sync?.synced ?? [];
  return (
    <FlowDoneView sbId={sbId} stageKey="dss" stage={sbId ? undefined : out.stage} mdAdded={out.flow_sync?.md_added || out.summary_md}
      title="DSS를 저장했어요" sub={`${parts.join(' · ')}${eul(last)} Storyboard에 담았어요`}
      note={synced.length ? `연결된 Storyboard ${synced.length + 1}개에 반영했어요` : '요약본이 방금 갱신됐어요'} onEdit={onEdit}
      follow={sbId ? (
        <div className="ds-follows">
          <FollowCard to={`/scenario/new?sb=${encodeURIComponent(sbId)}&auto=1`} icon={IC_SC} title={CONTENT.sc.label} desc={`공간 ${c.spaces}개에서 사용자가 겪는 장면을 만들어요`} />
          <FollowCard to={`/spec/new?sb=${encodeURIComponent(sbId)}&auto=1`} icon={IC_SP} title={CONTENT.sp.label} desc={`매칭한 제품 ${c.products}개를 스펙 시트로`} />
        </div>
      ) : undefined} />
  );
}

/** 셸 맥락만 넘기는 빈 조각(불러오는 중 · 완료 화면) — 작업 화면은 SpacesStep · SolutionsStep 이 직접 넘긴다 */
function Shell({ cfg }: { cfg: ShellPageConfig }) {
  useShellPage(cfg);
  return null;
}

/** `/dss/:id` — DS2(공간 · 제품) → DS4(솔루션, `?step=solution`) → 저장하면 DS_Done */
export function DsEditPage() {
  const { id = '' } = useParams();
  const q = useDss(id);
  const actions = useDsActions(id);
  const [sp, setSp] = useSearchParams();
  const [done, setDone] = useState<DSStageOut | null>(null);
  const step = sp.get('step') === 'solution' ? 3 : 2;
  const d = q.data;
  const goStep = (s: 2 | 3) => setSp((prev) => {
    const n = new URLSearchParams(prev);
    if (s === 3) n.set('step', 'solution'); else n.delete('step');
    return n;
  });
  if (q.isError) return <div className="wm-page"><Shell cfg={dsShell(undefined, step)} /><ErrorState message="DSS를 불러오지 못했어요 · 지워졌거나 주소가 바뀌었을 수 있어요" onRetry={() => q.refetch()} /></div>;
  if (!d) return <div className="wm-page"><Shell cfg={dsShell(undefined, step)} /><Skeleton h={520} r={16} /></div>;
  if (done) {
    return (<>
      <Shell cfg={{ section: M.label, title: d.code ?? 'DSS', hasTask: false, stepper: { steps: M.steps, current: 3, complete: true } }} />
      <DsDone doc={d} out={done} onEdit={() => { setDone(null); goStep(2); }} />
    </>);
  }
  return step === 3
    ? <SolutionsStep doc={d} actions={actions} onBack={() => goStep(2)} onSaved={setDone} />
    : <SpacesStep doc={d} actions={actions} onNext={() => goStep(3)} />;
}
