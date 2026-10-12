/**
 * 경쟁사 분석 새 흐름(보드 webapp1 v62 — CA0 · 최종본 View content=ca · CA_View · CA_Draft + 단계 팝업 CA1 · CA2 · CA2_Info · CA2_Pc · CA2_AI · CA2_Edit).
 * 상세는 최종본 한 장이고 단계는 그 위 팝업이다(페이지 이동 없음) — docs/scenarios/11-content-flow.md CF-09 · CF-12.
 *   /competitor            CA0  목록(보드 List content=ca · 저장된 것 = 허브, 작성 중 = /v1/ca-flows)
 *   /competitor/new        빈 최종본 + ① Storyboard 팝업(보드 CA1 = Gate content=ca · `?sb=&auto=1` 이면 바로 만든다). 고르기 전에 닫으면 목록
 *   /competitor/flow/:id   최종본(저장됨 · 작성 중). `?step=list` ② 경쟁사 리스트업 팝업(CA2 · 탭 `&tab=info|pc`)
 *                          — 작성 중을 열면 ② 팝업이 열린 채로(처음 한 번). 저장된 것은 머리의 단계 칩 → 고치기 팝업(CA2_Edit · 저장 · vN)
 * 후속 작업 없음. 이전 흐름의 목록 · 새로 만들기는 /competitor/legacy · /competitor/legacy/new(나머지 /competitor/:id/... 그대로).
 */
import { useEffect, useRef, useState } from 'react';
import { Navigate, useNavigate, useParams, useSearchParams } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import {
  CONTENT, ContentDetail, ContentListScreen, GateScreen, StepModal, useCloseAsk, useEditGuard, useFlow, useShellPage, useStepParam, whenText,
  type DraftRow,
} from '@/shell';
import { ErrorState, Skeleton, toast } from '@/ui';
import { cfKey, cfListKey, cfRoute, createCaFlow, useCaFlow, useCaFlows, useCfActions, useCfDelete, type CFListItem } from './api';
import { CaViewBody, caDone, caSaved } from './CaView';
import { Editor, errText } from './Editor';
import './caflow.css';

const M = CONTENT.ca;
/** 팝업 단계 키(`?step=`) — ① Storyboard(사전 작업) · ② 경쟁사 리스트업 */
const KEYS = ['sb', 'list'] as const;

const draftRows = (items: CFListItem[]) => items.filter((m) => m.status !== 'done')
  .map((m) => ({ title: m.title, ref: m.code ?? null, to: cfRoute(m.id), sbIds: m.sb_id ? [m.sb_id] : [], when: m.updated_at }));

/** CA0 — 보드 List(content=ca). 작성 중 초안은 이 서비스 목록에서 — 손을 올리면 ×(지우기) */
export function CaListScreen() {
  const flows = useCaFlows();
  const remove = useCfDelete();
  const drafts: DraftRow[] = draftRows(flows.data?.items ?? []).map((r) => ({ ...r, onDelete: () => remove(r.to.split('/').pop()!) }));
  return <ContentListScreen content="ca" drafts={drafts} />;
}

/** `/competitor/new` — 빈 최종본 + ① Storyboard 고르기 팝업(보드 CA1 = Gate content=ca).
 *  Storyboard 화면의 「만들기」는 `?sb=<id>&auto=1` 로 와서 고르기를 건너뛰고 ② 팝업으로 간다(CF-07).
 *  같은 Storyboard 의 저장 전 초안이 있으면 서버가 그 초안을 돌려준다 → 이어서 연다(초안이 늘지 않음).
 *  이전 흐름의 정의서 진입(`?input=requirements&rq=`)은 이전 화면으로. */
export function CaNewPage() {
  const [sp] = useSearchParams();
  const nav = useNavigate();
  const qc = useQueryClient();
  const flows = useCaFlows();
  useShellPage({ section: M.label, title: '새로 만들기', hasTask: false });
  if (sp.get('input')) return <Navigate to={`/competitor/legacy/new?${sp.toString()}`} replace />;
  return (
    <>
      <ContentDetail content="ca" status="new" title={`새 ${M.short}`} sbIds={[]} steps={M.steps} done={0} onStep={() => undefined}>
        <CaViewBody d={null} done={0} status="new" onStep={() => undefined} />
      </ContentDetail>
      <StepModal open content="ca" title={`새 ${M.short}`} mode="new" note="Storyboard를 고르면 경쟁사 분석이 그 Storyboard에 연결돼요 · 고르기 전에 닫으면 목록으로"
        steps={M.steps} current={1} done={0} onStep={() => undefined} onClose={() => nav('/competitor')}>
        <GateScreen content="ca" initialSb={sp.get('sb')} autoStart={sp.get('auto') === '1'} drafts={draftRows(flows.data?.items ?? [])} openStep="list"
          onStart={async ({ sbId }) => {
            const { doc: d, reused } = await createCaFlow({ sb_id: sbId });
            qc.setQueryData(cfKey(d.id), d);
            void qc.invalidateQueries({ queryKey: cfListKey });
            if (reused) toast(`작성 중이던 ${d.code ?? M.short} 초안을 이어서 열어요`);
            return `${cfRoute(d.id)}?step=list`;
          }} />
      </StepModal>
    </>
  );
}

/** `/competitor/flow/:id` — 최종본(보드 View content=ca) + ② 경쟁사 리스트업 팝업(CA2 / 고치기 CA2_Edit) */
function Detail({ id }: { id: string }) {
  const q = useCaFlow(id);
  const actions = useCfActions(id);
  const { step, open } = useStepParam(KEYS);
  const [, setSp] = useSearchParams();
  const d = q.data;
  const saved = !!d && caSaved(d);
  const flow = useFlow(d?.sb_id ?? null);
  const shared = flow.data?.cells.find((c) => c.key === 'ca')?.shared ?? [];
  const sbIds = d?.sb_id ? [d.sb_id, ...shared.filter((x) => x !== d.sb_id)] : [];
  const popup = step != null && step >= 2 ? step : null;
  const status = saved ? 'saved' : popup ? 'new' : 'draft';
  useShellPage({ section: M.label, title: d ? (saved ? d.code ?? M.short : status === 'new' ? '새로 만들기' : d.title || M.short) : M.short, hasTask: false });

  // 팝업을 닫으면 단계와 함께 팝업 안 탭(`tab`)도 주소에서 뺀다 — 최종본만 남는다
  const close = () => setSp((prev) => { const p = new URLSearchParams(prev); p.delete('step'); p.delete('tab'); return p; }, { replace: true });

  // 작성 중을 열면(목록 · 작업 내역 · 새로 고침) ② 팝업을 연다 — 처음 한 번만(닫으면 작성 중 최종본)
  const auto = useRef(false);
  useEffect(() => {
    if (!d || auto.current) return;
    auto.current = true;
    if (!caSaved(d) && step == null) open(2);
  }, [d, step, open]);

  const dirty = useEditGuard(saved && popup != null, d?.version);
  const { ask, dialog } = useCloseAsk();
  const [saving, setSaving] = useState(false);
  const nextVer = (d?.ver ?? 0) + 1;
  const code = d?.code ?? M.short;
  const finish = async () => {
    setSaving(true);
    try { await actions.finish(); close(); } catch (e) { toast(errText(e)); } finally { setSaving(false); }
  };
  const onClose = async () => {
    if (saving) return;
    if (saved && d && dirty()) {
      const a = await ask({ title: '고친 내용을 저장할까요?', saveLabel: `저장 · v${nextVer}`,
        message: `저장하면 ${code} v${nextVer}로 연결된 Storyboard에 반영돼요. 저장하지 않으면 고친 내용은 이 경쟁사 분석에만 남고 Storyboard에는 아직 반영되지 않아요.` });
      if (a === 'stay') return;
      if (a === 'save') { await finish(); return; }
    }
    close();
  };

  if (q.isError) return <div className="wm-page"><ErrorState message="경쟁사 분석을 불러오지 못했어요 · 지워졌거나 주소가 바뀌었을 수 있어요" onRetry={() => q.refetch()} /></div>;
  if (!d) return <div className="wm-page"><Skeleton h={520} r={16} /></div>;

  const done = caDone(d);
  const c = d.counts;
  const editNote = `저장하면 ${code} v${nextVer} · ${sbIds.join(' · ') || 'Storyboard'}에 반영돼요`;
  return (
    <>
      <ContentDetail content="ca" status={status} title={d.title || M.short} refVer={saved ? `${code} v${d.ver ?? 1}` : null}
        meta={saved ? `${whenText(d.updated_at)} 저장 · 경쟁사 ${c.competitors} · 비교 쌍 ${c.matches}` : undefined}
        sbIds={sbIds} steps={M.steps} done={done} onStep={open} json="ca">
        <CaViewBody d={d} done={done} status={status} onStep={open} />
      </ContentDetail>
      <StepModal open={popup != null} content="ca" title={d.title || M.short} mode={saved ? 'edit' : 'new'} ver={`${code} v${d.ver ?? 1}`} sbId={d.sb_id}
        note={saved ? editNote : 'Storyboard를 그대로 가져왔어요 · 사전 작업 DSS 확인됨'}
        steps={M.steps} current={2} done={saved ? 2 : 1} onStep={open} onClose={() => void onClose()}>
        {popup === 2 && <Editor doc={d} onFinished={close} saveLabel={saved ? `저장 · v${nextVer}` : '저장'} />}
      </StepModal>
      {dialog}
    </>
  );
}

/** `/competitor/flow/:id` — 다른 문서로 옮기면 화면 상태를 새로 시작한다 */
export function CaDetailPage() {
  const { id = '' } = useParams();
  return <Detail key={id} id={id} />;
}
