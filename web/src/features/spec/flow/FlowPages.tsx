/**
 * Spec 시트 새 흐름(보드 webapp1 v62 — SP0 · View content=sp · SP_Draft · 단계 팝업 SP1 · SP2 · SP2_Edit) — docs/scenarios/11-content-flow.md §6 `sp`.
 * 상세는 최종본 한 장이고 단계는 그 위 팝업이다(페이지 이동 없음 · 완료 화면 없음).
 *   /spec            SP0  목록(보드 List content=sp · 저장된 것 = 허브, 작성 중 = /v1/spec-flows)
 *   /spec/new        빈 최종본 + ① Storyboard 팝업(보드 SP1 = Gate content=sp). `?sb=&auto=1`(Storyboard · DSS 의 「만들기」)이면 고르기를 건너뛰고
 *                    바로 ② 시트 작성 팝업으로. 고르기 전에 닫으면 목록
 *   /spec/flow/:id   최종본(저장됨 · 작성 중 — 보드 SP_View · SP_Draft) + `?step=sheet` ② 시트 작성 팝업(새로 SP2 · 고치기 SP2_Edit 「저장 · vN」).
 *                    작성 중을 열면 ② 팝업이 열린 채로(처음 한 번). 저장(시트 만들기)하면 XLSX 를 만들고 팝업이 닫혀 최종본이 채워진다.
 * `/spec/new?models=…` · `?from=…` · `?pop=…`(제품 상세 · MI · VP · 조감도에서 넘겨받은 모델 — Storyboard 없음)는 이전 흐름 입력 화면 `/spec/legacy/new` 로 그대로 넘긴다.
 */
import { useEffect, useRef } from 'react';
import { Navigate, useLocation, useNavigate, useParams, useSearchParams } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import {
  CONTENT, ContentDetail, ContentListScreen, GateScreen, StepModal, useCloseAsk, useEditGuard, useFlow, useShellPage, useStepParam, whenText,
  type DraftRow,
} from '@/shell';
import { AiBar, ErrorState, PathIcon, Skeleton, toast } from '@/ui';
import { createSpecFlow, deleteSpecFlow, dssChangeText, sfKey, sfListKey, sfRoute, useSfActions, useSpecFlow, useSpecFlows, useSpecStage } from './api';
import { SheetStep } from './SheetStep';
import { FORMAT_KO, SpViewBody, spDone, spSaved } from './SpView';

const M = CONTENT.sp;
/** 팝업 단계 키(`?step=`) — ① Storyboard(사전 작업) · ② 시트 작성 */
const KEYS = ['sb', 'sheet'] as const;
const DL_ICON = 'M12 4v11 M7 10l5 5 5-5 M5 20h14';
const errMsg = (e: unknown, fb: string) => (e as Error)?.message || fb;

const draftRows = (items: { id: string; title: string; code?: string | null; sb_id?: string | null; status: string; updated_at?: string | null }[]) =>
  items.filter((m) => m.status !== 'done').map((m) => ({ title: m.title, ref: m.code ?? null, to: sfRoute(m.id), sbIds: m.sb_id ? [m.sb_id] : [], when: m.updated_at }));

/** SP0 — 보드 List(content=sp). 작성 중 초안은 이 서비스 목록에서 · 저장 전 초안은 줄의 × 로 지운다(보드에 없음 — 셸이 확인을 묻는다) */
export function SpListScreen() {
  const q = useSpecFlows();
  const qc = useQueryClient();
  const drafts: DraftRow[] = draftRows(q.data?.items ?? []).map((r) => ({ ...r,
    onDelete: async () => { await deleteSpecFlow(r.to.split('/').pop()!); void qc.invalidateQueries({ queryKey: sfListKey }); } }));
  return <ContentListScreen content="sp" drafts={drafts} />;
}

/** `/spec/new` — 빈 최종본 + ① Storyboard 고르기 팝업(보드 SP1 = Gate content=sp).
 *  `?sb=<id>&auto=1` 이면 고르기를 건너뛴다(CF-07). 같은 Storyboard 의 저장 전 초안이 있으면 서버가 그 초안을 돌려준다(이어서 연다). */
export function SpNewPage() {
  const [sp] = useSearchParams();
  const loc = useLocation();
  const nav = useNavigate();
  const qc = useQueryClient();
  const list = useSpecFlows();
  const legacy = !sp.get('sb') && !!(sp.get('models') || sp.get('from') || sp.get('pop'));
  useShellPage({ section: M.label, title: '새로 만들기', hasTask: false });
  if (legacy) return <Navigate to={`/spec/legacy/new${loc.search}`} replace state={loc.state} />;
  return (
    <>
      <ContentDetail content="sp" status="new" title={`새 ${M.short}`} sbIds={[]} steps={M.steps} done={0} onStep={() => undefined}>
        <SpViewBody d={null} done={0} status="new" onStep={() => undefined} />
      </ContentDetail>
      <StepModal open content="sp" title={`새 ${M.short}`} mode="new" note="Storyboard를 고르면 Spec 시트가 그 Storyboard에 연결돼요 · 고르기 전에 닫으면 목록으로"
        steps={M.steps} current={1} done={0} onStep={() => undefined} onClose={() => nav('/spec')}>
        <GateScreen content="sp" initialSb={sp.get('sb')} autoStart={sp.get('auto') === '1'} drafts={draftRows(list.data?.items ?? [])} openStep="sheet"
          onStart={async ({ sbId }) => {
            const { doc: d, reused } = await createSpecFlow(sbId);
            qc.setQueryData(sfKey(d.id), d);
            void qc.invalidateQueries({ queryKey: sfListKey });
            if (reused) toast(`작성 중이던 ${d.code ?? M.short} 초안을 이어서 열어요`);
            return `${sfRoute(d.id)}?step=sheet`;
          }} />
      </StepModal>
    </>
  );
}

/** 최종본 머리 「XLSX 내려받기」(보드 View spSaved: h38 r10 · 13/600 · 아이콘 14) — 저장 때 만든 파일. 못 만들었으면 눌리지 않는다 */
function XlsxButton({ file, loading }: { file: { name: string; url: string } | null | undefined; loading: boolean }) {
  const label = <><PathIcon d={DL_ICON} size={14} color="currentColor" strokeWidth={2.2} />XLSX 내려받기</>;
  if (file) return <a className="fl-dbtn" href={`${file.url}?download=1`} download={file.name} title={file.name}>{label}</a>;
  return <button type="button" className="fl-dbtn" disabled title={loading ? '파일을 확인하는 중이에요' : 'XLSX를 만들지 못했어요 · 시트 작성에서 다시 저장해 주세요'}>{label}</button>;
}

function SpDetail({ id }: { id: string }) {
  const q = useSpecFlow(id);
  const act = useSfActions(id);
  const { step, open, close } = useStepParam(KEYS);
  const d = q.data;
  const saved = !!d && spSaved(d);
  const stage = useSpecStage(id, saved);
  const flow = useFlow(d?.sb_id ?? null);
  const cell = flow.data?.cells.find((c) => c.key === 'sp');
  const sbIds = d?.sb_id ? [d.sb_id, ...(cell?.shared ?? []).filter((x) => x !== d.sb_id)] : [];
  const popup = step === 2 ? 2 : null;
  // 상단바 제목(보드 View · SP2 · SP_Draft): 저장됨 = 코드 · 저장 전 팝업이 열려 있으면 「새로 만들기」 · 작성 중 = 이름
  useShellPage({ section: M.label, title: d ? (saved ? d.code ?? M.short : popup ? '새로 만들기' : d.title || M.short) : M.short, hasTask: false });

  // 작성 중을 열면(목록 · 작업 내역 · 새로 고침) ② 시트 작성 팝업을 연다 — 처음 한 번만(닫으면 작성 중 최종본)
  const auto = useRef(false);
  useEffect(() => {
    if (!d || auto.current) return;
    auto.current = true;
    if (!spSaved(d) && step == null) open(2);
  }, [d, step, open]);

  const dirty = useEditGuard(saved && popup != null, d?.version);
  const { ask, dialog } = useCloseAsk();
  const nextVer = (d?.ver ?? 0) + 1;
  const finish = async () => {
    try { await act.finish(); close(); } catch (e) { toast(errMsg(e, '저장하지 못했어요')); }
  };
  const onClose = async () => {
    if (saved && d && dirty()) {
      const a = await ask({ title: '고친 내용을 저장할까요?', saveLabel: `저장 · v${nextVer}`,
        message: `저장하면 ${d.code ?? 'Spec 시트'} v${nextVer}로 XLSX를 다시 만들고 연결된 Storyboard에 반영돼요. 저장하지 않으면 고친 내용은 이 시트에만 남고 Storyboard · XLSX에는 아직 반영되지 않아요.` });
      if (a === 'stay') return;
      if (a === 'save') { await finish(); return; }
    }
    close();
  };

  if (q.isError) return <div className="wm-page"><ErrorState message="Spec 시트를 불러오지 못했어요 · 지워졌거나 주소가 바뀌었을 수 있어요" onRetry={() => q.refetch()} /></div>;
  if (!d) return <div className="wm-page"><Skeleton h={520} r={16} /></div>;

  const done = spDone(d);
  const status = saved ? 'saved' : popup ? 'new' : 'draft';
  const c = d.counts;
  const file = stage.data?.file;
  const editNote = `저장하면 ${d.code ?? 'Spec 시트'} v${nextVer} · ${sbIds.join(' · ') || 'Storyboard'}에 반영돼요`;
  // Storyboard 의 DSS 가 시트를 만든 뒤 바뀌었으면(보드에 없음) 최종본 머리 아래에도 한 줄 — 「다시 가져오기」는 ② 시트 작성 팝업 안에서
  const notice = d.dss_changed ? (
    <AiBar actionLabel="시트 작성에서 다시 가져오기" onAction={() => open(2)}>
      <span data-testid="spv-dss-changed">{dssChangeText(d.dss_changed)}</span>
    </AiBar>
  ) : undefined;

  return (
    <>
      <ContentDetail content="sp" status={status} title={d.title || M.short} refVer={saved ? `${d.code ?? 'SP'} v${d.ver ?? 1}` : null}
        meta={saved ? `${whenText(d.updated_at)} 저장 · 제품 ${c.models} · 항목 ${c.columns} · ${FORMAT_KO[d.format] ?? d.format}`
          : status === 'draft' ? `작성 중 · ${M.steps.length}단계 중 ${done}단계 마침 · ${whenText(d.updated_at)} · 저장하면 ${sbIds[0] ? `${sbIds[0]}에 연결돼요` : 'Storyboard에 연결돼요'}` : undefined}
        sbIds={sbIds} steps={M.steps} done={done} onStep={open} json="sp" notice={notice}
        actions={<XlsxButton file={file} loading={stage.isLoading} />}>
        <SpViewBody d={d} done={done} status={status} onStep={open} fileName={stage.isLoading ? undefined : file?.name ?? null} />
      </ContentDetail>
      <StepModal open={popup != null} content="sp" title={d.title || M.short} mode={saved ? 'edit' : 'new'} ver={`${d.code ?? 'SP'} v${d.ver ?? 1}`} sbId={d.sb_id}
        note={saved ? editNote : 'Storyboard를 그대로 가져왔어요 · 사전 작업 DSS 확인됨'}
        steps={M.steps} current={2} done={saved ? 2 : 1} onStep={open} onClose={() => void onClose()}>
        {popup === 2 && <SheetStep doc={d} saveLabel={saved ? `저장 · v${nextVer}` : '시트 만들기'} onSaved={() => close()} />}
      </StepModal>
      {dialog}
    </>
  );
}

/** `/spec/flow/:id` — 최종본(보드 View content=sp) + 단계 팝업(② SP2 / 고치기 SP2_Edit). 다른 시트로 옮기면 화면 상태를 새로 */
export function SpDetailPage() {
  const { id = '' } = useParams();
  return <SpDetail key={id} id={id} />;
}

