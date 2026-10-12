/**
 * Market Intelligence(보드 webapp1 v62 — MI0 · 최종본 View content=mi(MI_View · MI_Draft) + 단계 팝업 MI1 · MI1_Branch · MI2_Loading · MI2 · MI3)
 * 상세는 최종본 한 장이고 단계는 그 위 팝업이다(페이지 이동 없음) — docs/scenarios/11-content-flow.md CF-08(MI 예외) · CF-09 · CF-12.
 *   /mi                MI0  목록(보드 List content=mi · 저장된 것 = 허브, 작성 중 = /v1/mi-flows)
 *   /mi/new            빈 최종본 + ① Storyboard 팝업(보드 Gate content=mi · 이미 있으면 MI1_Branch 수정/복제본 · `?sb=&auto=1` 은 바로 만들기). 고르기 전에 닫으면 목록
 *   /mi/flow/:id       최종본(저장됨 · 작성 중). `?step=search` ② 검색 팝업(AI 가 Storyboard 를 먼저 읽는다 → 검색어 · 검색 조건 → 웹 검색) ·
 *                      `?step=refine` ③ 정제 팝업(「검색어 고치기」 → ②, 「MI 저장」 → 팝업이 닫히고 최종본)
 *                      — 작성 중을 열면 이어서 할 단계 팝업이 열린 채로. 저장된 것은 머리의 단계 칩 → 고치기 팝업(② 은 Storyboard 를 다시 읽고 시작 · 저장 · vN+1)
 *   이전 흐름 링크(`/mi/new?rq=` — 요구사항 정의서의 「Market Intelligence」)는 /mi/legacy/new 로.
 */
import { useEffect, useRef, useState } from 'react';
import { Navigate, useNavigate, useParams, useSearchParams } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { CONTENT, ContentDetail, ContentListScreen, GateScreen, StepModal, useCloseAsk, useFlow, useShellPage, useStepParam, whenText, type DraftRow } from '@/shell';
import { ErrorState, FlowScreen, Skeleton, toast } from '@/ui';
import { GROUPS, isBusy, itemsOf, mfApi, mfKey, mfListKey, mfRoute, nOn, qsOf, useMfActions, useMfDelete, useMiFlow, useMiFlows, type MFDoc } from './api';
import { MiViewBody, miDone, miSaved } from './MiView';
import { usePacedSteps } from './pace';
import { RefineView } from './RefineStep';
import { LoadingView, SearchView } from './SearchStep';
import './miflow.css';

const M = CONTENT.mi;
/** 팝업 단계 키(`?step=`) — ① Storyboard(사전 작업) · ② 검색 · ③ 정제 */
const KEYS = ['sb', 'search', 'refine'] as const;
const errMsg = (e: unknown, fb: string) => (e as Error)?.message || fb;

const draftRows = (items: { id: string; title: string; code?: string | null; sb_id: string; status: string; ver?: number | null; updated_at: string }[]) =>
  items.filter((m) => m.status !== 'done' && m.ver == null).map((m) => ({ title: m.title, ref: m.code ?? null, to: mfRoute(m.id), sbIds: m.sb_id ? [m.sb_id] : [], when: m.updated_at }));

/** MI0 — 보드 List(content=mi). 저장 전 초안은 「작성 중」 — 손을 올리면 ×(지우기) */
export function MiListScreen() {
  const flows = useMiFlows();
  const remove = useMfDelete();
  const drafts: DraftRow[] = (flows.data?.items ?? []).filter((m) => m.status !== 'done')
    .map((m) => ({ title: m.title, ref: m.code ?? null, to: mfRoute(m.id), sbIds: m.sb_id ? [m.sb_id] : [], when: m.updated_at,
      onDelete: m.ver == null ? () => remove(m.id) : undefined,
      // 지금 단계(보드 List n/3): 정제 중이면 ③, 분석 · 검색 중이면 ②
      step: m.phase === 'refine' ? 3 : 2 }));
  return <ContentListScreen content="mi" drafts={drafts} />;
}

const EMPTY: MFDoc = {
  id: '', code: null, title: '', sb_id: '', status: 'draft', phase: 'analyzing', ver: null, editing: false, keep_previous: true, saved_kept: 0,
  counts: { found: 0, kept: 0, numberCheck: 0, queries: 0 }, version: 0, created_at: '', updated_at: '',
};

/** `/mi/new` — 빈 최종본 + ① Storyboard 고르기 팝업(보드 MI1 · MI1_Branch = Gate content=mi).
 *  같은 Storyboard 의 저장 전 초안이 있으면 서버가 그 초안을 돌려준다 → 이어서 연다. 「수정」(이미 있는 MI)은 ② 검색 고치기 팝업으로 */
export function MiNewPage() {
  const [sp] = useSearchParams();
  const nav = useNavigate();
  const qc = useQueryClient();
  const flows = useMiFlows();
  useShellPage({ section: M.label, title: '새로 만들기', hasTask: false });
  if (sp.get('rq') && !sp.get('sb')) return <Navigate to={`/mi/legacy/new?${sp.toString()}`} replace />;
  return (
    <>
      <ContentDetail content="mi" status="new" title={`새 ${M.short}`} sbIds={[]} steps={M.steps} done={0} onStep={() => undefined}>
        <MiViewBody d={EMPTY} done={0} status="new" onStep={() => undefined} />
      </ContentDetail>
      <StepModal open content="mi" title={`새 ${M.short}`} mode="new" note="Storyboard를 고르면 MI가 그 Storyboard에 연결돼요 · 고르기 전에 닫으면 목록으로"
        steps={M.steps} current={1} done={0} onStep={() => undefined} onClose={() => nav('/mi')}>
        <GateScreen content="mi" initialSb={sp.get('sb')} autoStart={sp.get('auto') === '1'} drafts={draftRows(flows.data?.items ?? [])} openStep="search"
          onStart={async ({ sbId }) => {
            // 만든 문서(분석 중)를 캐시에 먼저 넣어 ② 팝업이 분석 단계부터 그리게 한다(빠른 모델이면 첫 조회 때 이미 끝나 있다)
            const { doc: d, reused } = await mfApi.create(sbId);
            qc.setQueryData(mfKey(d.id), d);
            void qc.invalidateQueries({ queryKey: mfListKey });
            if (reused) toast(`작성 중이던 ${d.code ?? 'MI'} 초안을 이어서 열어요`);
            return `${mfRoute(d.id)}?step=search`;
          }} />
      </StepModal>
    </>
  );
}

/** 저장한 MI 를 다시 읽기 시작하기 전(응답 전) — 서버 분석 단계와 같은 이름 */
const firstSteps = (sb: string) => [
  { key: 'read', label: `Storyboard ${sb} 읽기`, state: 'run' as const, note: '' },
  { key: 'extract', label: '고객사 · 업종 · 공간 · 요구 뽑기', state: 'wait' as const, note: '' },
  { key: 'queries', label: '시장 · 고객사 · 사용자 검색어 만들기', state: 'wait' as const, note: '' },
];

/** 고치기 팝업에서 「고친 것」 — 담은 정보(문장) · 켠 검색어 · 검색 조건. 문서 판(version)은 AI 다시 읽기 · 검색에도 바뀌어 쓰지 않는다 */
const sigItems = (d: MFDoc) => JSON.stringify(itemsOf(d).filter((x) => x.kept).map((x) => [x.id, x.summary]));
const sigQs = (d: MFDoc) => JSON.stringify([GROUPS.map((g) => qsOf(d)[g.key].filter((q) => q.on !== false).map((q) => q.text)), d.filters?.period ?? null, d.filters?.sourceTypes ?? []]);

/**
 * 저장된 MI 의 고치기 팝업 — 처음 모양(AI 가 일하지 않을 때)을 기억해, 닫을 때 바뀌었으면 true(저장할지 묻는다).
 * ② 를 열면 AI 가 Storyboard 를 다시 읽어 검색어가 바뀔 수 있다 → 다시 읽는 동안은 검색어 기준만 새로 잡는다(담은 정보 고침은 그대로 남는다).
 */
function useMiEditGuard(open: boolean, d: MFDoc | undefined, ready: boolean, rereading: boolean) {
  const base = useRef<{ items: string | null; qs: string | null }>({ items: null, qs: null });
  useEffect(() => {
    if (!open) { base.current = { items: null, qs: null }; return; }
    if (rereading) { base.current.qs = null; return; }
    if (!d || !ready) return;
    if (base.current.items == null) base.current.items = sigItems(d);
    if (base.current.qs == null) base.current.qs = sigQs(d);
  }, [open, d, ready, rereading]);
  return () => !!d && ((base.current.items != null && sigItems(d) !== base.current.items) || (base.current.qs != null && sigQs(d) !== base.current.qs));
}

/** `/mi/flow/:id` — 최종본(보드 View content=mi) + 단계 팝업(② MI2_Loading · MI2 / ③ MI3 — 저장된 것은 고치기 팝업) */
function Detail({ id }: { id: string }) {
  const q = useMiFlow(id);
  const actions = useMfActions(id);
  const { step, open, close } = useStepParam(KEYS);
  const d = q.data;
  const saved = miSaved(d);
  const flow = useFlow(d?.sb_id ?? null);
  const cell = flow.data?.cells.find((c) => c.key === 'mi');
  const sbIds = d?.sb_id ? [d.sb_id, ...(cell?.shared ?? []).filter((x) => x !== d.sb_id)] : [];
  const popup = step != null && step >= 2 ? step : null;
  const code = d?.code ?? 'MI';
  useShellPage({ section: M.label, title: d ? (saved ? code : d.title || M.short) : M.short, hasTask: false });

  const busy = isBusy(d);
  const prog = d?.progress ?? null;
  const paced = usePacedSteps(prog?.steps ?? [], busy, `${prog?.kind ?? ''}:${prog?.job_id ?? ''}`);

  // 작성 중을 열면(목록 · 작업 내역 · 새로 고침) 이어서 할 단계 팝업을 연다 — 처음 한 번만(닫으면 작성 중 최종본)
  const auto = useRef(false);
  useEffect(() => {
    if (!d || auto.current) return;
    auto.current = true;
    if (miSaved(d)) return;
    // Gate 의 「초안 이어 쓰기」는 늘 `?step=search` 로 연다 — 이미 웹 검색을 마친 초안이면 ③ 정제로
    if (step == null || (step === 2 && d.phase === 'refine')) open(d.phase === 'refine' ? 3 : 2);
  }, [d, step, open]);

  // 아직 웹 검색을 마치지 않은 초안의 ③(주소로 연 경우) → ② 검색
  useEffect(() => {
    if (d && popup === 3 && !miSaved(d) && miDone(d) < 2) open(2);
  }, [d, popup, open]);

  // 저장한 MI 의 ② 검색 팝업 — Storyboard 를 다시 읽고 고치기 시작(보드 MI2_Loading 「MI-01 v1 고치기」). 실패하면 지금 검색어로
  const [finishing, setFinishing] = useState(false);
  const [reread, setReread] = useState<'idle' | 'run' | 'fail'>('idle');
  const pendingRead = !!d && saved && !d.editing && !busy && popup === 2 && !finishing && reread !== 'fail';
  useEffect(() => {
    if (popup !== 2) { setReread('idle'); }
    if (popup == null) setFinishing(false);
  }, [popup]);
  useEffect(() => {
    if (!pendingRead || reread !== 'idle') return;
    setReread('run');
    actions.analyze().catch((e) => { toast(errMsg(e, 'Storyboard를 다시 읽지 못했어요')); setReread('fail'); });
  }, [pendingRead, reread, actions]);

  // ② 에서 웹 검색을 지켜봤으면 다 찾은 뒤 ③ 정제 팝업으로(보드 MI2 「웹 검색 후 정제로」) — 넘어갈 때까지 검색 중 카드를 그대로
  const [watching, setWatching] = useState(false);
  useEffect(() => {
    if (!d) return;
    if (busy && prog?.kind === 'search') { if (!watching) setWatching(true); return; }
    if (!watching || !paced.settled) return;
    if (popup === 2 && d.phase === 'refine') open(3); else setWatching(false);
  }, [d, busy, prog?.kind, paced.settled, popup, open, watching]);
  useEffect(() => { if (popup !== 2) setWatching(false); }, [popup]);

  const ready = !busy && !pendingRead && paced.settled;
  const dirty = useMiEditGuard(saved && popup != null, d, ready, pendingRead || (busy && prog?.kind === 'analyze'));
  const { ask, dialog } = useCloseAsk();
  const nextVer = (d?.ver ?? 0) + 1;
  /** 저장(:finish) → 문서를 새로 읽고 팝업을 닫는다(최종본). 실패하면 던진다 */
  const finish = async () => {
    setFinishing(true);
    try { await actions.finish(); await actions.refresh(); close(); } catch (e) { setFinishing(false); throw e; }
  };
  const onClose = async () => {
    if (saved && d && dirty()) {
      const a = await ask({ title: '고친 내용을 저장할까요?', saveLabel: `저장 · v${nextVer}`,
        message: `저장하면 ${code} v${nextVer}로 연결된 Storyboard에 반영돼요. 저장하지 않으면 고친 내용은 이 MI에만 남고 Storyboard에는 아직 반영되지 않아요.` });
      if (a === 'stay') return;
      if (a === 'save') { try { await finish(); } catch (e) { toast(errMsg(e, '저장하지 못했어요')); } return; }
    }
    close();
  };

  if (q.isError) return <div className="wm-page"><ErrorState message="MI를 불러오지 못했어요 · 지워졌거나 주소가 바뀌었을 수 있어요" onRetry={() => q.refetch()} /></div>;
  if (!d) return <div className="wm-page"><Skeleton h={520} r={16} /></div>;

  const done = saved ? 3 : miDone(d);
  const status = saved ? 'saved' : popup ? 'new' : 'draft';
  const c = d.counts;
  const view: 'analyze' | 'searching' | 'search' | 'refine' =
    pendingRead || (prog?.kind === 'analyze' && (d.phase === 'analyzing' || !paced.settled)) ? 'analyze'
      : prog?.kind === 'search' && (d.phase === 'searching' || !paced.settled || (watching && popup === 2)) ? 'searching'
        : popup === 3 ? 'refine' : 'search';
  const nq = GROUPS.reduce((a, g) => a + nOn(qsOf(d)[g.key]), 0);
  const editNote = `저장하면 ${code} v${nextVer} · ${sbIds.join(' · ') || 'Storyboard'}에 반영돼요`;
  // 저장 시각 — 허브 이력의 이 MI 저장(고치기 팝업에서 AI 가 다시 읽거나 담기만 바꿔도 문서 updated_at 은 바뀐다)
  const savedAt = (flow.data?.history ?? []).filter((h) => h.key === 'mi' && h.ref === code && h.ver === d.ver).at(-1)?.at ?? d.updated_at;

  return (
    <>
      <ContentDetail content="mi" status={status} title={d.title || M.short} refVer={saved ? `${code} v${d.ver ?? 1}` : null}
        meta={saved ? `${whenText(savedAt)} 저장 · 담은 정보 ${c.kept} (찾은 ${c.found}) · 수치 원문 확인 ${c.numberCheck}` : undefined}
        sbIds={sbIds} steps={M.steps} done={done} onStep={open} json="mi">
        <MiViewBody d={d} done={done} status={status} onStep={open} />
      </ContentDetail>
      <StepModal open={popup != null} content="mi" title={d.title || M.short} mode={saved ? 'edit' : 'new'} ver={`${code} v${d.ver ?? 1}`} sbId={d.sb_id}
        note={saved ? editNote : 'MI를 저장하면 이 Storyboard에 연결돼요'}
        steps={M.steps} current={popup ?? 2} done={saved ? 3 : Math.max(done, (popup ?? 2) - 1)} onStep={open} onClose={() => void onClose()}>
        {popup != null && (
          <FlowScreen pad="22px 40px 22px 40px" gap={view === 'refine' ? 12 : 14} className="mif-screen">
            {view === 'analyze' && <LoadingView kind="analyze" steps={pendingRead || d.phase === 'done' ? firstSteps(d.sb_id) : paced.view} summary={nq ? `검색어 ${nq}개 · 1–2분` : undefined} />}
            {view === 'searching' && <LoadingView kind="search" steps={paced.view} summary={`검색어 ${nq}개 · 1–2분`} />}
            {view === 'search' && <SearchView key={`${d.id}:${prog?.job_id ?? ''}`} doc={d} actions={actions} />}
            {view === 'refine' && (
              <RefineView key={d.id} doc={d} actions={actions} onBack={() => open(2)} onSave={finish} saveLabel={saved ? `MI 저장 · v${nextVer}` : 'MI 저장'} />
            )}
          </FlowScreen>
        )}
      </StepModal>
      {dialog}
    </>
  );
}

/** `/mi/flow/:id` — 다른 MI 로 옮겨 가면 화면 상태를 새로 */
export function MiDetailPage() {
  const { id = '' } = useParams();
  return <Detail key={id} id={id} />;
}
