/**
 * 공간 시나리오 새 흐름(보드 webapp1 v62 — SC0 · 최종본 View content=sc · SC_View · SC_Draft + 단계 팝업 SC1 · SC2 · SC2_AI · SC2_Pick · SC2_Empty · SC2_Edit).
 * 상세는 최종본 한 장이고 단계는 그 위 팝업이다(페이지 이동 없음) — docs/scenarios/11-content-flow.md CF-09 · CF-12.
 *   /scenario              SC0  목록(보드 List content=sc · 저장된 것 = 허브, 작성 중 = /v1/space-sets)
 *   /scenario/new          빈 최종본 + ① Storyboard 팝업(보드 SC1 = Gate content=sc · `?sb=&auto=1` 이면 고르기를 건너뛰고 바로 만든다). 고르기 전에 닫으면 목록
 *   /scenario/spaces/:id   최종본(저장됨 · 작성 중). `?step=spaces` ② 공간 · 시나리오 팝업
 *                          — 작성 중을 열면 ② 팝업이 열린 채로. 저장된 것은 머리의 단계 칩 → 고치기 팝업(저장 · vN+1)
 * 이전 흐름으로 들어오던 주소(`/scenario?image_version=` · `/scenario/new?sb=sb_…|from=|mi=`)는 index.tsx 가 이전 화면으로 나눈다.
 */
import { useEffect, useRef, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import {
  CONTENT, ContentDetail, ContentListScreen, GateScreen, StepModal, useCloseAsk, useEditGuard, useFlow, useFlowInvalidate, useShellPage, useStepParam, whenText,
  type DraftRow,
} from '@/shell';
import { ErrorState, Skeleton, toast } from '@/ui';
import { createSpaceSet, deleteSpaceSet, dssChangeText, finishSpaceSet, ssKey, ssListKey, useSpaceSet, useSpaceSets, type SSDoc, type SSListItem } from './api';
import { SpacesStep, type SpacesCtl } from './SpacesStep';
import { ScViewBody, scDone, scSaved, scUnsaved } from './ScView';

const M = CONTENT.sc;
/** 팝업 단계 키(`?step=`) — ① Storyboard(사전 작업) · ② 공간 · 시나리오 */
const KEYS = ['sb', 'spaces'] as const;
const route = (id: string) => `/scenario/spaces/${id}`;
const errMsg = (e: unknown, fb: string) => (e as Error)?.message || fb;
/** Storyboard 없이(공간 · 제품을 API 로 주거나 요구 문장으로) 시작한 묶음 */
const NO_SB = '연결된 Storyboard가 없어요 · 요구 문장으로 시작했어요';

/** 한 번도 저장하지 않은 초안 줄(목록 · Gate) — 저장 뒤 고친 묶음은 허브 줄로 보인다 */
const draftRows = (items: SSListItem[]): DraftRow[] => items.filter((m) => m.status !== 'done' && !m.ver)
  .map((m) => ({ title: m.title, ref: m.code ?? null, to: route(m.id), sbIds: m.sb_id ? [m.sb_id] : [], when: m.updated_at }));

/** SC0 — 저장 전 초안(한 번도 저장하지 않은 것)만 줄의 × 로 지운다(보드에 없음 — 셸이 확인을 묻는다) */
export function ScListScreen() {
  const q = useSpaceSets();
  const qc = useQueryClient();
  const drafts: DraftRow[] = draftRows(q.data?.items ?? []).map((r) => ({ ...r,
    onDelete: async () => { await deleteSpaceSet(r.to.split('/').pop()!); void qc.invalidateQueries({ queryKey: ssListKey }); } }));
  return <ContentListScreen content="sc" drafts={drafts} />;
}

/** `/scenario/new` — 빈 최종본 + ① Storyboard 고르기 팝업(보드 SC1 = Gate content=sc).
 *  Storyboard · DSS 화면의 「만들기」는 `?sb=<id>&auto=1` 로 와서 고르기를 건너뛰고 ② 팝업으로 간다(CF-07). 같은 Storyboard 의 초안이 있으면 그 초안을 연다. */
export function ScNewPage() {
  const [sp] = useSearchParams();
  const nav = useNavigate();
  const qc = useQueryClient();
  const list = useSpaceSets();
  useShellPage({ section: M.label, title: '새로 만들기', hasTask: false });
  return (
    <>
      <ContentDetail content="sc" status="new" title={`새 ${M.short}`} sbIds={[]} steps={M.steps} done={0} onStep={() => undefined}>
        <ScViewBody d={null} done={0} status="new" onStep={() => undefined} />
      </ContentDetail>
      <StepModal open content="sc" title={`새 ${M.short}`} mode="new" note="Storyboard를 고르면 공간 시나리오가 그 Storyboard에 연결돼요 · 고르기 전에 닫으면 목록으로"
        steps={M.steps} current={1} done={0} onStep={() => undefined} onClose={() => nav('/scenario')}>
        <GateScreen content="sc" initialSb={sp.get('sb')} autoStart={sp.get('auto') === '1'} drafts={draftRows(list.data?.items ?? [])} openStep="spaces"
          onStart={async ({ sbId }) => {
            const { doc: d, reused } = await createSpaceSet({ sb_id: sbId });
            qc.setQueryData(ssKey(d.id), d);
            void qc.invalidateQueries({ queryKey: ssListKey });
            if (reused) toast(`작성 중이던 ${d.code ?? M.short} 초안을 이어서 열어요`);
            return `${route(d.id)}?step=spaces`;
          }} />
      </StepModal>
    </>
  );
}

/** `/scenario/spaces/:id` — 최종본(보드 View content=sc) + ② 공간 · 시나리오 팝업(SC2 · 고치기 SC2_Edit) */
export function ScDetailPage() {
  const { id = '' } = useParams();
  return <Detail key={id} id={id} />;
}

function Detail({ id }: { id: string }) {
  const q = useSpaceSet(id);
  const qc = useQueryClient();
  const invalFlow = useFlowInvalidate();
  const { step, open, close } = useStepParam(KEYS);
  const d = q.data;
  const saved = !!d && scSaved(d);
  const flow = useFlow(d?.sb_id ?? null);
  const cell = flow.data?.cells.find((c) => c.key === 'sc');
  const sbIds = d?.sb_id ? [d.sb_id, ...(cell?.shared ?? []).filter((x) => x !== d.sb_id)] : [];
  const popup = step === 2 ? 2 : null;
  const status = saved ? 'saved' : popup ? 'new' : 'draft';
  // 상단바 제목(보드 View refId): 저장됨 = 코드 · 새로(팝업) = 「새로 만들기」 · 작성 중 = 이름
  useShellPage({ section: M.label, title: d ? (saved ? d.code ?? M.short : status === 'new' ? '새로 만들기' : d.title || M.short) : M.short, hasTask: false });

  // 작성 중을 열면(목록 · 작업 내역 · 새로 고침) ② 팝업을 연다 — 처음 한 번만(닫으면 작성 중 최종본)
  const auto = useRef(false);
  useEffect(() => {
    if (!d || auto.current) return;
    auto.current = true;
    if (!scSaved(d) && step == null) open(2);
  }, [d, step, open]);

  const ctl = useRef<SpacesCtl | null>(null);
  const dirty = useEditGuard(saved && popup != null, d?.version);
  const { ask, dialog } = useCloseAsk();
  const [saving, setSaving] = useState(false);
  const nextVer = (d?.ver ?? 0) + 1;
  const code = d?.code ?? 'SC';
  /** 저장 응답(stage)을 캐시에 먼저 — 다시 읽기 전에 최종본이 작성 중으로 깜박이지 않게 */
  const onSaved = (ver: unknown) => {
    qc.setQueryData<SSDoc>(ssKey(id), (p) => (p ? { ...p, status: 'done', ver: Number(ver) || (p.ver ?? 0) + 1, dss_changed: p.dss_changed } : p));
    close();
  };
  const onClose = async () => {
    if (saved && d) {
      await ctl.current?.flush();                       // 밀린 자동 저장(600ms)부터 — 고침이 판(version)에 남아야 묻는다
      const latest = qc.getQueryData<SSDoc>(ssKey(id));
      if (dirty() || (latest && latest.version !== d.version)) {
        const a = await ask({ title: '고친 내용을 저장할까요?', saveLabel: `저장 · v${nextVer}`,
          message: `저장하면 ${code} v${nextVer}로 연결된 Storyboard에 반영돼요. 저장하지 않으면 고친 내용은 이 공간 시나리오에만 남고 Storyboard에는 아직 반영되지 않아요.` });
        if (a === 'stay') return;
        if (a === 'save') { await ctl.current?.save(); return; }    // 막는 시나리오가 있으면 그리로 데려가고 팝업은 그대로
      }
    }
    close();
  };
  /** 최종본 안내 줄의 「저장 · vN+1」 — 팝업을 닫고 남은 고침을 허브에 반영 */
  const finishNow = async () => {
    if (saving) return;
    setSaving(true);
    try {
      const out = await finishSpaceSet(id);
      invalFlow();
      void qc.invalidateQueries({ queryKey: ssListKey });
      void qc.invalidateQueries({ queryKey: ssKey(id) });
      onSaved((out.stage as { ver?: number }).ver);
    } catch (e) { toast(errMsg(e, '저장하지 못했어요')); } finally { setSaving(false); }
  };

  if (q.isError) return <div className="wm-page"><ErrorState message="공간 시나리오를 불러오지 못했어요 · 지워졌거나 주소가 바뀌었을 수 있어요" onRetry={() => q.refetch()} /></div>;
  if (!d) return <div className="wm-page"><Skeleton h={520} r={16} /></div>;

  const done = scDone(d);
  const c = d.counts;
  const sb = d.sb_id ?? null;
  const editNote = `저장하면 ${code} v${nextVer}${sbIds.length ? ` · ${sbIds.join(' · ')}` : ''}에 반영돼요`;
  const newNote = sb ? 'Storyboard를 그대로 가져왔어요 · 사전 작업 DSS 확인됨' : 'Storyboard 없이 시작했어요 · 저장해도 Storyboard에는 반영되지 않아요';
  const meta = saved ? `${whenText(d.updated_at)} 저장 · 공간 ${c.spaces} · 시나리오 ${c.scenarios} · 시나리오 없는 공간 ${c.spaces_without_scenario}`
    : status === 'draft' ? `작성 중 · ${M.steps.length}단계 중 ${done}단계 마침 · ${whenText(d.updated_at)} · ${sb ? `저장하면 ${sb}에 연결돼요` : '저장해도 Storyboard에는 반영되지 않아요'}` : undefined;
  // 머리 아래 안내 줄(보드에 없음): Storyboard 의 DSS 가 바뀜 · 저장 뒤 고친 내용이 아직 Storyboard 에 반영되지 않음
  const notice = popup ? null : d.dss_changed ? (
    <div className="scv-notice" role="note" data-testid="scv-dss-changed">
      <span className="scv-notice__t">{dssChangeText(d.dss_changed)}</span>
      <button type="button" className="scv-notice__btn" onClick={() => open(2)}>공간 · 시나리오에서 다시 가져오기</button>
    </div>
  ) : scUnsaved(d) ? (
    <div className="scv-notice scv-notice--warn" role="note" data-testid="scv-unsaved">
      <span className="scv-notice__t">고친 내용이 아직 Storyboard에 반영되지 않았어요 · 저장하면 {code} v{nextVer}</span>
      <button type="button" className="scv-notice__btn" onClick={() => void finishNow()} disabled={saving}>{saving ? '저장 중…' : `저장 · v${nextVer}`}</button>
    </div>
  ) : null;

  return (
    <>
      <ContentDetail content="sc" status={status} title={d.title || M.short} refVer={saved ? `${code} v${d.ver || 1}` : null} meta={meta}
        sbIds={sbIds} sbEmpty={sb ? undefined : NO_SB} steps={M.steps} done={done} onStep={(k) => { if (k >= 2) open(k); }} json="sc" notice={notice}>
        <ScViewBody d={d} done={done} status={status} onStep={open} />
      </ContentDetail>
      <StepModal open={popup != null} content="sc" title={d.title || M.short} mode={saved ? 'edit' : 'new'} ver={`${code} v${d.ver || 1}`} sbId={sb}
        note={saved ? editNote : newNote} steps={M.steps} current={2} done={saved ? 2 : 1} onStep={open} onClose={() => void onClose()}>
        {popup === 2 && (
          <SpacesStep key={d.id} doc={d} ctl={ctl} saveLabel={saved ? `저장 · v${nextVer}` : '저장'}
            onSaved={(out) => onSaved((out.stage as { ver?: number }).ver)} />
        )}
      </StepModal>
      {dialog}
    </>
  );
}
