/**
 * VP 새 흐름(보드 webapp1 v62 — VP0 · View content=vp · VP_Draft · 단계 팝업 VP1 · VP2 · VP2_AI · VP2_Pick · VP2_Detail · VP2_Edit)
 * 상세는 최종본 한 장이고 단계는 그 위 팝업이다(페이지 이동 없음) — docs/scenarios/11-content-flow.md.
 *   /vp                 VP0  목록(보드 List content=vp · 저장 전 초안 줄은 × 로 지운다)
 *   /vp/new             빈 최종본 + ① Storyboard 팝업(보드 VP1 = Gate content=vp · `?sb=&auto=1` 이면 고르기를 건너뛰고 바로 ② 팝업). 고르기 전에 닫으면 목록
 *   /vp/values/:id      최종본(저장됨 · 작성 중). `?step=values` ② 가치 · 고객의 니즈 팝업 — 작성 중을 열면 그 팝업이 열린 채로(처음 한 번),
 *                       저장된 것은 머리의 단계 칩 → 고치기 팝업(저장 · vN+1 · 닫을 때 고친 게 있으면 물음)
 *   /vp/values/new      예전 주소 — `?text=`(요구 문장)면 Storyboard 없이 맵을 만들어 ② 팝업으로, 아니면 /vp/new(`sb` 가 있으면 자동 시작)
 */
import { useEffect, useRef, useState } from 'react';
import { Navigate, useNavigate, useParams, useSearchParams } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import {
  CONTENT, ContentDetail, ContentListScreen, GateScreen, StepModal, useCloseAsk, useEditGuard, useFlow, useShellPage, useStepParam, whenText,
  type DraftRow,
} from '@/shell';
import { ErrorState, Skeleton, toast } from '@/ui';
import { createValueMap, deleteValueMap, dssChangeText, startValueMap, useValueMap, useValueMaps, useVmActions, vmKey, vmListKey, type VMDoc } from './api';
import { ValuesStep } from './ValuesStep';
import { VpViewBody, vpDone, vpSaved } from './VpView';

const M = CONTENT.vp;
/** 팝업 단계 키(`?step=`) — ① Storyboard(사전 작업) · ② 가치 · 고객의 니즈 */
const KEYS = ['sb', 'values'] as const;
export const vpRoute = (id: string) => `/vp/values/${id}`;
const errMsg = (e: unknown, fb: string) => (e as Error)?.message || fb;

const draftRows = (items: { id: string; title: string; code?: string | null; sb_id?: string | null; status: string; updated_at?: string | null }[]) =>
  items.filter((m) => m.status !== 'done').map((m) => ({ title: m.title, ref: m.code ?? null, to: vpRoute(m.id), sbIds: m.sb_id ? [m.sb_id] : [], when: m.updated_at }));

/** VP0 — 보드 List(content=vp). 저장 전 초안은 줄의 × 로 지운다(셸이 확인을 묻는다) */
export function VpListScreen() {
  const maps = useValueMaps();
  const qc = useQueryClient();
  const drafts: DraftRow[] = draftRows(maps.data?.items ?? []).map((r) => ({ ...r, onDelete: async () => {
    const id = r.to.split('/').pop()!;
    await deleteValueMap(id);
    qc.removeQueries({ queryKey: vmKey(id) });
    for (const queryKey of [vmListKey, ['ws', 'items'], ['ws', 'recent'], ['ws', 'counts']]) void qc.invalidateQueries({ queryKey });
  } }));
  return <ContentListScreen content="vp" drafts={drafts} />;
}

const EMPTY: VMDoc = {
  id: '', code: null, title: '', sb_id: null, context_text: null, candidates: [], items: [], status: 'draft', ver: null, dss_ref: null, dss_ver: null,
  dss_changed: null, last_resync: null, counts: { items: 0, values: 0, needs: 0, needs_missing: 0, pending: 0 }, version: 0, created_at: '', updated_at: '',
};

/** 빈 최종본(새로 만들기 · ② 자리표시) */
function EmptyView() {
  return (
    <ContentDetail content="vp" status="new" title={`새 ${M.short}`} sbIds={[]} steps={M.steps} done={0} onStep={() => undefined}>
      <VpViewBody d={EMPTY} done={0} status="new" onStep={() => undefined} />
    </ContentDetail>
  );
}

/** `/vp/new` — 빈 최종본 + ① Storyboard 고르기 팝업(보드 VP1 = Gate content=vp).
 *  Storyboard 화면의 「만들기」는 `?sb=<id>&auto=1` 로 와서 고르기를 건너뛴다. 같은 Storyboard 의 초안이 있으면 그 초안을 연다.
 *  이전 흐름 들어오기(이전 Storyboard `sb_…` · MI · 요구사항 · 제안서에서 `/vp/new?…`)는 이전 VP 만들기 화면으로. */
export function VpNewPage() {
  const [sp] = useSearchParams();
  const nav = useNavigate();
  const qc = useQueryClient();
  const maps = useValueMaps();
  useShellPage({ section: M.label, title: '새로 만들기', hasTask: false });
  const sb = sp.get('sb');
  if ((sb && sb.startsWith('sb_')) || sp.has('mi') || sp.has('rq') || sp.has('proposal')) return <Navigate to={`/vp/legacy/new?${sp.toString()}`} replace />;
  return (
    <>
      <EmptyView />
      <StepModal open content="vp" title={`새 ${M.short}`} mode="new" note="Storyboard를 고르면 VP가 그 Storyboard에 연결돼요 · 고르기 전에 닫으면 목록으로"
        steps={M.steps} current={1} done={0} onStep={() => undefined} onClose={() => nav('/vp')}>
        <GateScreen content="vp" initialSb={sb} autoStart={sp.get('auto') === '1'} drafts={draftRows(maps.data?.items ?? [])} openStep="values"
          onStart={async ({ sbId }) => {
            const { doc: d, reused } = await startValueMap(sbId);
            qc.setQueryData(vmKey(d.id), d);
            void qc.invalidateQueries({ queryKey: vmListKey });
            if (reused) toast(`작성 중이던 ${d.code ?? 'VP'} 초안을 이어서 열어요`);
            return `${vpRoute(d.id)}?step=values`;
          }} />
      </StepModal>
    </>
  );
}

/** `/vp/values/new` — 예전 주소. `?text=`(요구 문장 · `title=`)면 Storyboard 없이 KB 후보로 맵을 만들어 ② 팝업, 아니면 Gate(`/vp/new`) */
export function VpValuesNewPage() {
  const [sp] = useSearchParams();
  const nav = useNavigate();
  const qc = useQueryClient();
  const text = sp.get('text')?.trim() || '';
  const sb = sp.get('sb');
  const started = useRef(false);
  useShellPage({ section: M.label, title: '새로 만들기', hasTask: false });
  useEffect(() => {
    if (!text || sb || started.current) return;
    started.current = true;
    createValueMap({ title: sp.get('title')?.trim() || '새 VP', context_text: text, select_all: true })
      .then((d) => { qc.setQueryData(vmKey(d.id), d); void qc.invalidateQueries({ queryKey: vmListKey }); nav(`${vpRoute(d.id)}?step=values`, { replace: true }); })
      .catch((e) => { toast(errMsg(e, '만들지 못했어요')); nav('/vp/new', { replace: true }); });
  }, [text, sb, sp, qc, nav]);
  if (!text || sb) return <Navigate to={sb ? `/vp/new?sb=${encodeURIComponent(sb)}&auto=1` : '/vp/new'} replace />;
  return <EmptyView />;
}

/** `/vp/values/:id` — 최종본(보드 View content=vp) + 단계 팝업(② VP2 · VP2_AI / 고치기 VP2_Edit) */
export function VpDetailPage() {
  const { id = '' } = useParams();
  const q = useValueMap(id);
  const actions = useVmActions(id);
  const { step, open, close } = useStepParam(KEYS);
  const d = q.data;
  const saved = !!d && vpSaved(d);
  const flow = useFlow(d?.sb_id ?? null);
  const shared = flow.data?.cells.find((c) => c.key === 'vp')?.shared ?? [];
  const sbIds = d?.sb_id ? [d.sb_id, ...shared.filter((x) => x !== d.sb_id)] : [];
  const popup = step === 2 ? 2 : null;
  useShellPage({ section: M.label, title: d ? (saved ? d.code ?? M.short : popup ? '새로 만들기' : d.title || M.short) : M.short, hasTask: false });

  // 작성 중을 열면(목록 · 작업 내역 · 새로 고침) ② 팝업을 연다 — 처음 한 번만(닫으면 작성 중 최종본)
  const auto = useRef(false);
  useEffect(() => {
    if (!d || auto.current) return;
    auto.current = true;
    if (!vpSaved(d) && step == null) open(2);
  }, [d, step, open]);

  const dirty = useEditGuard(saved && popup != null, d?.version);
  const { ask, dialog } = useCloseAsk();
  const [saving, setSaving] = useState(false);
  const [resyncNow, setResyncNow] = useState(false);
  const nextVer = (d?.ver ?? 0) + 1;
  const finish = async () => {
    setSaving(true);
    try { await actions.finish(); close(); } catch (e) { toast(errMsg(e, '저장하지 못했어요')); } finally { setSaving(false); }
  };
  const onClose = async () => {
    if (saved && d && dirty()) {
      const a = await ask({ title: '고친 내용을 저장할까요?', saveLabel: `저장 · v${nextVer}`,
        message: `저장하면 ${d.code ?? 'VP'} v${nextVer}로 연결된 Storyboard에 반영돼요. 저장하지 않으면 고친 내용은 이 VP에만 남고 Storyboard에는 아직 반영되지 않아요.` });
      if (a === 'stay') return;
      if (a === 'save') { await finish(); return; }
    }
    close();
  };

  if (q.isError) return <div className="wm-page"><ErrorState message="VP를 불러오지 못했어요 · 지워졌거나 주소가 바뀌었을 수 있어요" onRetry={() => q.refetch()} /></div>;
  if (!d) return <div className="wm-page"><Skeleton h={520} r={16} /></div>;

  const done = vpDone(d);
  const status = saved ? 'saved' : popup ? 'new' : 'draft';
  const c = d.counts;
  const ref = d.code ?? 'VP';
  const editNote = `저장하면 ${ref} v${nextVer} · ${sbIds.join(' · ') || 'Storyboard'}에 반영돼요`;
  const newNote = d.sb_id ? 'Storyboard를 그대로 가져왔어요 · 사전 작업 DSS 확인됨' : '요구 문장으로 시작했어요 · 연결된 Storyboard가 없어요';
  // Storyboard 의 DSS 가 바뀜(보드에 없음) — 안내 줄은 ② 팝업 안(AiBar)에 있고, 최종본에도 같은 문장 한 줄.
  // 최종본의 「다시 가져오기」는 ② 팝업(저장됨이면 고치기)을 열고 바로 다시 가져온다(고친 것이라 저장해야 Storyboard 에 반영)
  const notice = d.dss_changed && popup == null ? (
    <div className="vpv-notice" data-testid="vpv-dss-changed">
      <span>{dssChangeText(d.dss_changed)}</span>
      <button type="button" onClick={() => { setResyncNow(true); open(2); }}>다시 가져오기</button>
    </div>
  ) : undefined;

  return (
    <>
      <ContentDetail content="vp" status={status} title={d.title || M.short} refVer={saved ? `${ref} v${d.ver ?? 1}` : null}
        meta={saved ? `${whenText(d.updated_at)} 저장 · 제품 · 솔루션 ${c.items} · 가치 ${c.values} · 고객의 니즈 ${c.needs}/${c.values}` : undefined}
        sbIds={sbIds} sbEmpty={d.sb_id ? undefined : '연결된 Storyboard가 없어요 · 요구 문장으로 시작했어요'} steps={M.steps} done={done} onStep={open} json="vp" notice={notice}>
        <VpViewBody d={d} done={done} status={status} onStep={open} />
      </ContentDetail>
      <StepModal open={popup != null} content="vp" title={d.title || M.short} mode={saved ? 'edit' : 'new'} ver={`${ref} v${d.ver ?? 1}`} sbId={d.sb_id ?? null}
        note={saved ? editNote : newNote} steps={M.steps} current={2} done={saved ? 2 : 1} onStep={open} onClose={() => void onClose()}>
        {popup === 2 && <ValuesStep doc={d} save={{ label: saved ? `저장 · v${nextVer}` : '저장', onClick: () => void finish(), busy: saving }}
          resyncNow={resyncNow} onResynced={() => setResyncNow(false)} />}
      </StepModal>
      {dialog}
    </>
  );
}
