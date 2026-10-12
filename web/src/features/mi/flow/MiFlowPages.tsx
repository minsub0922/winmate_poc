/**
 * Market Intelligence 새 흐름(보드 webapp1 v63 MI0 · MI1 · MI1_Branch · MI2_Loading · MI2 · MI2_Run · MI3 · MI3_Edit · MI_View · MI_Search · MI_Draft)
 * — docs/scenarios/11-content-flow.md §1 · §6 · docs/handoff/2026-10-12-content-detail-v63.md.
 *   /mi              MI0  목록(보드 List content=mi · 저장된 것 = 허브, 작성 중 = /v1/mi-flows)
 *   /mi/new          MI1 · MI1_Branch  목록 위 Storyboard 고르기 팝업(공용 GateScreen) · `?sb=&auto=1` 은 바로 만들기(CF-07)
 *   /mi/flow/:id     상세 한 장(공용 ContentDetail + 본문 MIBody) — 새로 만들면 들어오자마자 검색 팝업(MISearch: AI 분석 로딩 → 검색어 · 조건)
 *                    → 웹 검색 → 같은 화면에서 찾는 중(MI2_Run) → 찾은 정보 그 자리에서 담기 · 문장 고치기(MI3) → 저장하면 그 자리에서 저장됨(MI_View).
 *                    저장한 것을 고치면 머리에 「고친 곳 n · 되돌리기 · 저장 · vN+1」(MI3_Edit). 검색 전에 팝업을 닫으면 작성 중(MI_Draft · 「검색 시작」).
 *                    완료 화면 · 단계 페이지는 없다(예전 `?done=1` 주소도 상세가 뜬다).
 */
import { useEffect, useRef, useState } from 'react';
import { Navigate, useParams, useSearchParams } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { ContentDetail, ContentListScreen, GateScreen, detailMode, type DraftRow } from '@/shell';
import { ErrorState, Skeleton, toast } from '@/ui';
import { freshMi, isBusy, mfApi, mfKey, mfListKey, mfRoute, useMfActions, useMfDelete, useMiFlow, useMiFlows, type MFStageOut } from './api';
import { MiBody, type Stage, type Touched } from './MiBody';
import { MiSearchPopup } from './MiSearch';
import { usePacedSteps } from './pace';
import './miflow.css';

/** MI0 — 보드 List(content=mi). 저장 전 초안은 「작성 중」 — 손을 올리면 ×(지우기) */
export function MiListScreen() {
  const flows = useMiFlows();
  const remove = useMfDelete();
  const drafts: DraftRow[] = (flows.data?.items ?? []).filter((m) => m.status !== 'done')
    .map((m) => ({ title: m.title, ref: m.code ?? null, to: mfRoute(m.id), sbIds: m.sb_id ? [m.sb_id] : [], when: m.updated_at,
      // 지금 단계(보드 List v61 n/3): 찾은 정보가 있으면 3(정제), 분석 · 검색 중이면 2
      step: m.phase === 'refine' ? 3 : 2,
      onDelete: m.ver == null ? () => remove(m.id) : undefined }));
  return <ContentListScreen content="mi" drafts={drafts} />;
}

/** MI1 · MI1_Branch — 목록 위 Storyboard 고르기 팝업(공용 GateScreen · 보드 Gate content=mi). 이전 흐름 링크(`/mi/new?rq=`)는 이전 MI1 로.
 *  같은 Storyboard 의 저장 전 초안이 있으면(다시 시작) 서버가 그 초안을 돌려준다 → 작성 중으로 이어서 연다 */
export function MiGateScreen() {
  const [sp] = useSearchParams();
  const qc = useQueryClient();
  const flows = useMiFlows();
  const drafts: DraftRow[] = (flows.data?.items ?? []).filter((m) => m.status !== 'done' && m.ver == null)
    .map((m) => ({ title: m.title, ref: m.code ?? null, to: mfRoute(m.id), sbIds: m.sb_id ? [m.sb_id] : [], when: m.updated_at }));
  if (sp.get('rq') && !sp.get('sb')) return <Navigate to={`/mi/legacy/new?${sp.toString()}`} replace />;
  // 만든 문서(분석 중)를 캐시에 먼저 넣어 상세가 바로 검색 팝업(분석 로딩)을 그리게 한다
  return <GateScreen content="mi" initialSb={sp.get('sb')} autoStart={sp.get('auto') === '1'} drafts={drafts}
    onStart={async ({ sbId }) => {
      const { doc: d, reused } = await mfApi.create(sbId);
      qc.setQueryData(mfKey(d.id), d);
      void qc.invalidateQueries({ queryKey: mfListKey });
      if (reused) toast(`작성 중이던 ${d.code ?? 'MI'} 초안을 이어서 열어요`);
      else freshMi.add(d.id);
      return mfRoute(d.id);
    }} />;
}

/** 이 화면에서 처음 바꾸기 전 값을 남긴다(같은 칸을 여러 번 바꿔도 처음 값) */
function touch(prev: Touched, id: string, before: { kept?: boolean; summary?: string }): Touched {
  const cur = prev[id] ?? {};
  const next = { ...cur };
  if (before.kept !== undefined && cur.kept === undefined) next.kept = before.kept;
  if (before.summary !== undefined && cur.summary === undefined) next.summary = before.summary;
  return { ...prev, [id]: next };
}

function Body({ id }: { id: string }) {
  const q = useMiFlow(id);
  const actions = useMfActions(id);
  const d = q.data;
  const busy = isBusy(d);
  const prog = d?.progress ?? null;
  const paced = usePacedSteps(prog?.steps ?? [], busy, `${prog?.kind ?? ''}:${prog?.job_id ?? ''}`);
  // 이 탭에서 방금 만든 MI 면 「새로 만들기」(보드 status new), 아니면 작성 중(draft)
  const [fresh, setFresh] = useState(() => freshMi.has(id));
  const [pop, setPop] = useState(false);
  const [touched, setTouched] = useState<Touched>({});
  const autoOpened = useRef(false);

  const saved = d?.ver != null;
  const items = d?.items ?? [];
  const analyzing = !!d && (d.phase === 'analyzing' || (prog?.kind === 'analyze' && !paced.settled));
  const searching = !!d && (d.phase === 'searching' || (prog?.kind === 'search' && !paced.settled));
  const searched = saved || items.length > 0 || d?.phase === 'refine' || d?.phase === 'done';
  const stage: Stage = searching ? 'searching' : searched ? 'found' : 'empty';

  // 새로 만든 MI 는 들어오자마자 검색 팝업(보드 MI2_Loading → MI2)
  useEffect(() => {
    if (!d || autoOpened.current) return;
    autoOpened.current = true;
    if (fresh && !saved && !searched && d.phase !== 'searching') setPop(true);
  }, [d, fresh, saved, searched]);

  if (q.isError) return <div className="wm-page"><ErrorState message="MI를 불러오지 못했어요 · 지워졌거나 주소가 바뀌었을 수 있어요" onRetry={() => q.refetch()} /></div>;
  if (!d) return <div className="wm-page"><Skeleton h={520} r={16} /></div>;

  const isNew = !saved && fresh;
  const mode = detailMode({ saved, changes: d.changes, empty: isNew });
  const c = d.counts;
  const facts = searched ? [`담은 정보 ${c.kept} (찾은 ${c.found})`, `수치 원문 확인 ${c.numberCheck}`] : [analyzing ? 'Storyboard 분석 중' : searching ? '검색 중' : '검색 전'];
  const closePop = () => {
    setPop(false);
    // 검색하기 전에 닫으면 작성 중으로 남는다(보드 MI_Draft · 「검색 시작」)
    if (!saved && !searched && d.phase !== 'searching') { freshMi.delete(id); setFresh(false); }
  };
  const save = async () => {
    if (busy) throw new Error('AI가 아직 일하고 있어요. 끝나면 저장할 수 있어요.');
    if (!searched || !items.length) throw new Error('웹 검색으로 찾은 정보를 담은 뒤 저장할 수 있어요');
    if (!c.kept) throw new Error('담은 정보가 하나 이상 있어야 저장할 수 있어요');
    const out = await actions.finish();
    freshMi.delete(id);
    setFresh(false);
    setTouched({});
    return out;
  };
  const revert = async () => { await actions.revert(); setTouched({}); };
  const savedToast = (o: unknown) => {
    const out = o as MFStageOut;
    const st = out?.stage as { ver?: number; counts?: { kept?: number } } | undefined;
    const synced = out?.flow_sync?.synced ?? [];
    return `${d.code ?? 'MI'} v${st?.ver ?? (d.ver ?? 0) + 1} 저장 · 담은 정보 ${st?.counts?.kept ?? c.kept} · ${synced.length ? `연결된 Storyboard ${synced.length + 1}개에 반영했어요` : `${d.sb_id}에 반영했어요`}`;
  };
  // 검색 팝업은 상세 안에 둔다(셸 본문 열의 바로 아래 자식은 1180 폭으로 묶여 딤이 화면을 다 덮지 못한다)
  return (
    <ContentDetail content="mi" saved={saved} changes={d.changes} empty={isNew} title={d.title} refCode={d.code} ver={d.ver}
      savedAt={d.saved_at} updatedAt={d.updated_at} facts={facts} sbIds={[d.sb_id]} onSave={save} onRevert={revert} savedToast={savedToast}>
      <MiBody doc={d} actions={actions} stage={stage} mode={mode} onOpenSearch={() => setPop(true)}
        touched={touched} onTouch={(iid, before) => setTouched((t) => touch(t, iid, before))} />
      <MiSearchPopup open={pop} doc={d} actions={actions} ready={!analyzing} steps={paced.view} onClose={closePop}
        onSearched={() => setPop(false)} />
    </ContentDetail>
  );
}

/** `/mi/flow/:id` — 다른 MI 로 옮겨 가면 화면 상태를 새로 */
export function MiFlowPage() {
  const { id = '' } = useParams();
  return <Body key={id} id={id} />;
}

