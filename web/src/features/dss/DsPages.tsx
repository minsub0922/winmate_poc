/**
 * 공간별 제품 매칭 DSS(보드 webapp1 v62 — DS0 · View content=dss · DS_Draft · 단계 팝업 DS1 · DS2 · DS2_AI · DS4 · DS4_AI · DS2_Edit · DS4_Edit)
 * 상세는 최종본 한 장이고 단계는 그 위 팝업이다(페이지 이동 없음) — docs/scenarios/11-content-flow.md CF-09 · CF-12.
 *   /dss                      DS0  목록(보드 List content=dss · 저장된 것 = 허브, 작성 중 = /v1/dss)
 *   /dss/new                  빈 최종본 + ① Storyboard 팝업(보드 Gate content=dss · `?sb=&auto=1` 이면 바로 만든다). 고르기 전에 닫으면 목록
 *   /dss/:id                  최종본(저장됨 · 작성 중). `?step=space` ② 공간 · 제품 팝업 · `?step=solution` ③ 솔루션 팝업
 *                             — 작성 중을 열면 이어서 할 단계 팝업이 열린 채로. 저장된 것은 머리의 단계 칩 → 고치기 팝업(저장 · vN)
 */
import { useEffect, useRef, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import {
  CONTENT, ContentDetail, ContentListScreen, DetailFollow, GateScreen, StepModal, useCloseAsk, useEditGuard, useFlow, useShellPage, useStepParam, whenText,
  type DraftRow,
} from '@/shell';
import { ErrorState, Skeleton, toast } from '@/ui';
import { createDss, dsListKey, dsRoute, useDsActions, useDsDelete, useDss, useDssList, type DSDoc } from './api';
import { DsViewBody, dsDone } from './DsView';
import { SolutionsStep } from './SolutionsStep';
import { SpacesStep } from './SpacesStep';
import './dss.css';

const M = CONTENT.dss;
/** 팝업 단계 키(`?step=`) — ① Storyboard(사전 작업) · ② 공간 · 제품 · ③ 솔루션 */
const KEYS = ['sb', 'space', 'solution'] as const;
const errMsg = (e: unknown, fb: string) => (e as Error)?.message || fb;

const draftRows = (items: { id: string; title: string; code?: string | null; sb_id?: string | null; status: string; updated_at?: string | null; counts?: { products: number } }[]) =>
  items.filter((d) => d.status !== 'done').map((d) => ({ title: d.title, ref: d.code ?? null, to: dsRoute(d.id), sbIds: d.sb_id ? [d.sb_id] : [], when: d.updated_at,
    // 지금 단계(보드 List n/3 · 열면 그 단계 팝업): 공간에 제품이 있으면 ③ 솔루션, 아니면 ② 공간 · 제품
    step: d.counts && d.counts.products > 0 ? 3 : 2 }));

/** DS0 — 보드 List(content=dss). 작성 중(저장 전) DSS 는 초안 줄 — 손을 올리면 ×(지우기) */
export function DsListScreen() {
  const list = useDssList();
  const remove = useDsDelete();
  const drafts: DraftRow[] = draftRows(list.data?.items ?? []).map((r) => ({ ...r, onDelete: () => remove(r.to.split('/').pop()!) }));
  return <ContentListScreen content="dss" drafts={drafts} />;
}

const EMPTY: DSDoc = {
  id: '', code: null, title: '', sb_id: null, rq_ref: null, customer: null, reqs: [], industry_options: [], industry: null, industry_ai: null,
  spaces: [], space_recs: [], solutions: [], solution_recs: [], status: 'draft', ver: null, counts: { spaces: 0, products: 0, solutions: 0, pending: 0 },
  version: 0, created_at: '', updated_at: '',
};

/** `/dss/new` — 빈 최종본 + ① Storyboard 고르기 팝업(보드 DS1 = Gate content=dss).
 *  Storyboard 화면의 「만들기」는 `?sb=<id>&auto=1` 로 와서 고르기를 건너뛴다(CF-07). 같은 Storyboard 의 초안이 있으면 그 초안을 연다. */
export function DsNewPage() {
  const [sp] = useSearchParams();
  const nav = useNavigate();
  const qc = useQueryClient();
  const list = useDssList();
  useShellPage({ section: M.label, title: '새로 만들기', hasTask: false });
  return (
    <>
      <ContentDetail content="dss" status="new" title={`새 ${M.short}`} sbIds={[]} steps={M.steps} done={0} onStep={() => undefined}>
        <DsViewBody d={EMPTY} done={0} status="new" onStep={() => undefined} />
      </ContentDetail>
      <StepModal open content="dss" title={`새 ${M.short}`} mode="new" note="Storyboard를 고르면 DSS가 그 Storyboard에 연결돼요 · 고르기 전에 닫으면 목록으로"
        steps={M.steps} current={1} done={0} onStep={() => undefined} onClose={() => nav('/dss')}>
        <GateScreen content="dss" initialSb={sp.get('sb')} autoStart={sp.get('auto') === '1'} drafts={draftRows(list.data?.items ?? [])} openStep="space"
          onStart={async ({ sbId }) => {
            const { doc: d, reused } = await createDss(sbId);
            qc.setQueryData(['dss', 'doc', d.id], d);
            void qc.invalidateQueries({ queryKey: dsListKey });
            if (reused) toast(`작성 중이던 ${d.code ?? 'DSS'} 초안을 이어서 열어요`);
            return `${dsRoute(d.id)}?step=space`;
          }} />
      </StepModal>
    </>
  );
}

/** `/dss/:id` — 최종본(보드 View content=dss) + 단계 팝업(②  DS2 · ③ DS4 / 고치기 DS2_Edit · DS4_Edit) */
export function DsDetailPage() {
  const { id = '' } = useParams();
  const q = useDss(id);
  const actions = useDsActions(id);
  const { step, open, close } = useStepParam(KEYS);
  const d = q.data;
  const saved = d?.status === 'done';
  const flow = useFlow(d?.sb_id ?? null);
  const cellOf = (k: string) => flow.data?.cells.find((c) => c.key === k);
  const sbIds = d?.sb_id ? [d.sb_id, ...(cellOf('dss')?.shared ?? []).filter((x) => x !== d.sb_id)] : [];
  const popup = step != null && step >= 2 ? step : null;
  useShellPage({ section: M.label, title: d ? (saved ? d.code ?? M.short : d.title || M.short) : M.short, hasTask: false });

  // 작성 중을 열면(목록 · 작업 내역 · 새로 고침) 이어서 할 단계 팝업을 연다 — 처음 한 번만(닫으면 작성 중 최종본)
  const auto = useRef(false);
  useEffect(() => {
    if (!d || auto.current) return;
    auto.current = true;
    if (d.status !== 'done' && step == null) open(Math.min(3, dsDone(d) + 1));
  }, [d, step, open]);

  const dirty = useEditGuard(saved && popup != null, d?.version);
  const { ask, dialog } = useCloseAsk();
  const [saving, setSaving] = useState(false);
  const nextVer = (d?.ver ?? 0) + 1;
  const finish = async () => {
    setSaving(true);
    try { await actions.finish(); close(); } catch (e) { toast(errMsg(e, '저장하지 못했어요')); } finally { setSaving(false); }
  };
  const onClose = async () => {
    if (saved && d && dirty()) {
      const a = await ask({ title: '고친 내용을 저장할까요?', saveLabel: `저장 · v${nextVer}`,
        message: `저장하면 ${d.code ?? 'DSS'} v${nextVer}로 연결된 Storyboard에 반영돼요. 저장하지 않으면 고친 내용은 이 DSS에만 남고 Storyboard에는 아직 반영되지 않아요.` });
      if (a === 'stay') return;
      if (a === 'save') { await finish(); return; }
    }
    close();
  };

  if (q.isError) return <div className="wm-page"><ErrorState message="DSS를 불러오지 못했어요 · 지워졌거나 주소가 바뀌었을 수 있어요" onRetry={() => q.refetch()} /></div>;
  if (!d) return <div className="wm-page"><Skeleton h={520} r={16} /></div>;

  const done = saved ? 3 : dsDone(d);
  const status = saved ? 'saved' : popup ? 'new' : 'draft';
  const c = d.counts;
  const sb = d.sb_id;
  const follow = saved && sb ? (
    <DetailFollow items={(['sc', 'sp'] as const).map((k) => {
      const cell = cellOf(k);
      const has = cell?.state === 'done' && !!cell.ref;
      return {
        to: has && cell?.route ? cell.route : `/${CONTENT[k].base}/new?sb=${encodeURIComponent(sb)}&auto=1`, icon: CONTENT[k].icon, title: CONTENT[k].label,
        desc: k === 'sc' ? `공간 ${c.spaces}개에서 사용자가 겪는 장면을 만들어요` : `매칭한 제품 ${c.products}개를 스펙 시트로`,
        ref: has ? `${cell!.ref} v${cell!.ver ?? 1}` : null,
      };
    })} />
  ) : undefined;
  const editNote = `저장하면 ${d.code ?? 'DSS'} v${nextVer} · ${sbIds.join(' · ') || 'Storyboard'}에 반영돼요`;

  return (
    <>
      <ContentDetail content="dss" status={status} title={d.title || M.short} refVer={saved ? `${d.code ?? 'DSS'} v${d.ver ?? 1}` : null}
        meta={saved ? `${whenText(d.updated_at)} 저장 · 공간 ${c.spaces} · 제품 ${c.products} · 솔루션 ${c.solutions}` : undefined}
        sbIds={sbIds} steps={M.steps} done={done} onStep={open} json="dss" follow={follow} updatedAt={d.updated_at}>
        <DsViewBody d={d} done={done} status={status} onStep={open} />
      </ContentDetail>
      <StepModal open={popup != null} content="dss" title={d.title || M.short} mode={saved ? 'edit' : 'new'} ver={`${d.code ?? 'DSS'} v${d.ver ?? 1}`} sbId={sb}
        note={saved ? editNote : popup === 3 ? `공간 ${c.spaces} · 제품 ${c.products} · 솔루션은 0개도 돼요` : 'DSS를 저장하면 이 Storyboard에 연결돼요'}
        steps={M.steps} current={popup ?? 2} done={saved ? 3 : Math.max(done, (popup ?? 2) - 1)} onStep={open} onClose={() => void onClose()}>
        {popup === 2 && (
          <SpacesStep doc={d} actions={actions} onNext={() => open(3)}
            primary={saved ? { label: `저장 · v${nextVer}`, onClick: () => void finish(), busy: saving } : undefined} />
        )}
        {popup === 3 && (
          <SolutionsStep doc={d} actions={actions} onBack={() => open(2)} onSaved={() => close()}
            backLabel={saved ? '공간 · 제품 고치기' : '이전 · 공간 · 제품'} saveLabel={saved ? `저장 · v${nextVer}` : 'DSS 저장'} />
        )}
      </StepModal>
      {dialog}
    </>
  );
}
