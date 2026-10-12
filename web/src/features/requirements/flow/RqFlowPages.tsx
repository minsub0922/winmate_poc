/**
 * 고객 요구사항 새 흐름(보드 webapp1 v62 — RQ0 · View content=rq · RQ_Draft · 단계 팝업 RQ1 · RQ1_Edit) — docs/scenarios/11-content-flow.md §6.
 * 상세는 최종본 한 장이고 단계(① 요구사항 입력 한 단계 · 사전 작업 없음)는 그 위 팝업이다(페이지 이동 · 완료 화면 없음).
 *   /requirements                 RQ0  목록(보드 List content=rq · 저장된 것 = 허브, 작성 중 = /v1/rq-flows)
 *   /requirements/new             빈 최종본 + ① 요구사항 입력 팝업(RQ1). 첫 입력 때 문서가 생기면 주소만 `/requirements/flow/:id?step=input` 로(같은 화면 · 입력 그대로).
 *                                 아무것도 적지 않고 닫으면 목록, 적었으면 작성 중 최종본(RQ_Draft)
 *   /requirements/flow/:id        최종본(저장됨 RQ_View · 작성 중 RQ_Draft). `?step=input` ① 입력 팝업 — 작성 중을 열면 처음 한 번 팝업이 열린 채로.
 *                                 저장된 것은 머리의 단계 칩 → 고치기 팝업(RQ1_Edit: 저장 · vN+1 · 고친 뒤 닫으면 물음)
 *   저장하면(:finish) 팝업이 닫히고 최종본 — 처음 저장이면 Storyboard 가 자동으로 만들어진다(안내 토스트).
 */
import { useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import {
  CONTENT, ContentDetail, ContentListScreen, DetailFollow, StepModal, useCloseAsk, useEditGuard, useFlow, useShellPage, useStepParam, whenText,
  type DraftRow,
} from '@/shell';
import { ErrorState, Skeleton, josa, toast } from '@/ui';
import { rfKey, rfListKey, rfRoute, useRfDelete, useRqFlow, useRqFlows, type RFDoc, type RFStageOut } from './api';
import { Editor, type EditorCtl } from './Editor';
import { euro } from './form';
import { RqViewBody, rfDone, rfName, rfSaved } from './RqView';
import './rqflow.css';

const M = CONTENT.rq;
/** 팝업 단계 키(`?step=`) — 요구사항은 사전 작업이 없어 ① 요구사항 입력 하나 */
const KEYS = ['input'] as const;
const NEW_NOTE = '저장하면 이 요구사항으로 Storyboard가 자동으로 만들어져요';

/** RQ0 — 보드 List(content=rq). 아무것도 적지 않은 초안은 보이지 않는다 · 저장 전 초안은 줄에 손을 올리면 ×(지우기) */
export function RqListScreen() {
  const flows = useRqFlows();
  const remove = useRfDelete();
  const drafts: DraftRow[] = (flows.data?.items ?? [])
    .filter((m) => m.status !== 'done' && (m.title !== '새 요구사항' || m.counts.reqs > 0))
    .map((m) => ({ title: m.title, ref: m.code, to: rfRoute(m.id), sbIds: m.sb_ids, when: m.updated_at,
      onDelete: m.ver === 0 && !m.sb_ids.length ? () => remove(m.id) : undefined }));
  return <ContentListScreen content="rq" drafts={drafts} />;
}

/** 저장 뒤 안내 — 완료 화면 대신(처음 저장: Storyboard 자동 생성 · 다시 저장: 연결된 Storyboard 에 반영) */
function savedToast(out: RFStageOut) {
  const sb = out.sb_id;
  if (!sb) { toast('저장했어요 · Storyboard를 만들지 못했어요. 다시 저장하면 다시 만들어요'); return; }
  const name = out.sb_name ?? sb;
  const n = 1 + (out.flow_sync?.synced?.length ?? 0);
  toast(out.created ? `Storyboard ‘${name}’(${sb})${josa(sb, '이', '가')} 자동으로 만들어졌어요`
    : `${out.doc.code} v${out.doc.ver} 저장 · 연결된 Storyboard ${n}개에 반영했어요`);
}

/** 최종본 + ① 입력 팝업. id 가 없으면 `/requirements/new`(빈 최종본 + 팝업) */
function RqDetail({ id, onCreated }: { id: string | undefined; onCreated: (d: RFDoc) => void }) {
  const nav = useNavigate();
  const qc = useQueryClient();
  const q = useRqFlow(id);
  const { step, open } = useStepParam(KEYS);
  const ctl = useRef<EditorCtl>(null);
  const d = q.data;
  const isNew = !id;
  const saved = rfSaved(d);
  const popup = isNew || step === 1;
  const sbIds0 = d?.sb_ids ?? [];
  const flow = useFlow(saved ? sbIds0[0] ?? null : null);
  const cellOf = (k: string) => flow.data?.cells.find((c) => c.key === k);
  const sbIds = saved ? [...new Set([...sbIds0, ...(cellOf('rq')?.shared ?? [])])] : [];
  // 상단바 제목(보드 View META): 저장됨 = 코드 · 새로(입력 팝업이 열린 저장 전) = 「새로 만들기」 · 작성 중 = 이름
  useShellPage({ section: M.label, title: saved ? d!.code : popup || !d ? '새로 만들기' : rfName(d), hasTask: false });

  // 작성 중을 열면(목록 · 작업 내역 · 새로 고침) ① 입력 팝업을 연다 — 처음 한 번만(닫으면 작성 중 최종본).
  // 새로 만들기는 팝업이 이미 열려 있다(첫 입력으로 문서가 생겨 주소가 바뀌어도 같은 화면이라 다시 열지 않는다)
  const auto = useRef(isNew);
  useEffect(() => {
    if (!d || auto.current) return;
    auto.current = true;
    if (!rfSaved(d) && step == null) open(1);
  }, [d, step, open]);

  const dirty = useEditGuard(saved && popup, d?.version);
  const { ask, dialog } = useCloseAsk();
  const nextVer = (d?.ver ?? 0) + 1;
  const code = d?.code ?? 'RQ';

  // 팝업 닫기 = `?step` 만 뺀 최종본 주소. 절대 경로로 바꾼다 — 첫 입력 · 저장 중에 `/requirements/new` 에서 `/requirements/flow/:id` 로 주소가 바뀌어도 같은 화면
  const showView = (docId: string) => {
    const p = new URLSearchParams(window.location.search);
    p.delete('step');
    const qs = p.toString();
    nav(`${rfRoute(docId)}${qs ? `?${qs}` : ''}`, { replace: true });
  };
  const onFinished = (out: RFStageOut) => {
    qc.setQueryData(rfKey(out.doc.id), out.doc);
    void qc.invalidateQueries({ queryKey: rfListKey });
    savedToast(out);
    showView(out.doc.id);
  };
  const onClose = async () => {
    const c = ctl.current;
    const pending = !!c?.pending();
    if (c) await c.flush();
    const cur = c?.doc() ?? d ?? null;
    // 아무것도 적지 않은 새 요구사항 — 초안을 만들지 않고 목록으로
    if (!cur) { nav('/requirements'); return; }
    if (rfSaved(cur) && (pending || dirty())) {
      const a = await ask({ title: '고친 내용을 저장할까요?', saveLabel: `저장 · v${nextVer}`,
        message: `저장하면 ${code} v${nextVer}로 연결된 Storyboard에 반영돼요. 저장하지 않으면 고친 내용은 이 요구사항에만 남고 Storyboard에는 아직 반영되지 않아요.` });
      if (a === 'stay') return;
      if (a === 'save') { await c?.save(); return; }
    }
    showView(cur.id);
  };

  if (id && q.isError) {
    return <div className="wm-page"><ErrorState message="요구사항을 불러오지 못했어요 · 지워졌거나 주소가 바뀌었을 수 있어요" onRetry={() => q.refetch()} /></div>;
  }
  if (id && !d) return <div className="wm-page"><Skeleton h={520} r={16} /></div>;

  const status = saved ? 'saved' : popup || !d ? 'new' : 'draft';
  const done = rfDone(d);
  const c = d?.counts;
  const sb = sbIds[0];
  const dssCell = cellOf('dss');
  const hasDss = dssCell?.state === 'done' && !!dssCell.ref;
  const dssCounts = (flow.data?.stages?.dss as { counts?: { spaces?: number; products?: number; solutions?: number } } | null | undefined)?.counts;
  const follow = saved && sb ? (
    <DetailFollow items={[{
      to: hasDss && dssCell?.route ? dssCell.route : `/dss/new?sb=${encodeURIComponent(sb)}&auto=1`, icon: CONTENT.dss.icon, title: CONTENT.dss.label,
      desc: hasDss && dssCounts ? `공간 ${dssCounts.spaces ?? 0} · 제품 ${dssCounts.products ?? 0} · 솔루션 ${dssCounts.solutions ?? 0}` : `${sb}${euro(sb)} 공간마다 제품 · 솔루션을 골라요`,
      ref: hasDss ? `${dssCell!.ref} v${dssCell!.ver ?? 1}` : null,
    }]} />
  ) : undefined;
  const meta = saved && c
    ? [`${whenText(d!.saved_at ?? d!.updated_at)} 저장`, `키맨 ${c.keymen}`, `요구 ${c.reqs}`, c.check ? `확인 필요 ${c.check}` : ''].filter(Boolean).join(' · ')
    : status === 'draft' && d ? `작성 중 · ${M.steps.length}단계 중 ${done}단계 마침 · ${whenText(d.updated_at)} · 저장하면 Storyboard가 만들어져요` : undefined;
  const editNote = sbIds.length ? `저장하면 ${code} v${nextVer} · 연결된 Storyboard ${sbIds.length}개(${sbIds.join(' · ')})에 반영돼요`
    : `저장하면 ${code} v${nextVer} · Storyboard가 자동으로 만들어져요`;
  // 보드 View · RQ1: 저장 전 팝업 머리와 새로 만들기 최종본은 「새 요구사항」, 작성 중 · 저장됨은 프로젝트명(없으면 고객사)
  const title = status === 'new' || !d ? M.newLabel : rfName(d);

  return (
    <>
      <ContentDetail content="rq" status={status} title={title} refVer={saved ? `${code} v${d!.ver}` : null} meta={meta}
        sbIds={sbIds} steps={M.steps} done={done} onStep={open} json="rq" follow={follow}>
        <RqViewBody d={d ?? null} status={status} onStep={open} />
      </ContentDetail>
      <StepModal open={popup} content="rq" title={saved ? title : M.newLabel} mode={saved ? 'edit' : 'new'} ver={`${code} v${d?.ver ?? 1}`} sbId={saved ? sb ?? null : null}
        note={saved ? editNote : NEW_NOTE} steps={M.steps} current={1} done={done} onStep={open} onClose={() => void onClose()}>
        <Editor initial={d ?? null} ctl={ctl} mode={saved ? 'edit' : 'new'} saveLabel={saved ? `저장 · v${nextVer}` : '저장'} onFinished={onFinished}
          onCreated={(doc) => { onCreated(doc); nav(`${rfRoute(doc.id)}?step=${KEYS[0]}`, { replace: true }); }} />
      </StepModal>
      {dialog}
    </>
  );
}

/**
 * `/requirements/new` · `/requirements/flow/:id` — 같은 화면. 첫 입력으로 문서가 생겨 주소가 바뀔 때는 화면(팝업 · 입력 · 포커스)을 그대로 두고,
 * 다른 요구사항 · 새로 만들기로 옮겨 갈 때만 새로 그린다.
 */
export function RqFlowPage() {
  const { id } = useParams();
  const created = useRef<string | null>(null);
  const [key, setKey] = useState(0);
  const [prev, setPrev] = useState(id);
  if (id !== prev) {
    setPrev(id);
    if (!(id && id === created.current)) setKey((k) => k + 1);
  }
  // 주소가 바뀐 뒤에는 잊는다(뒤로 가기로 같은 id 에 다시 오면 새로 그린다)
  useEffect(() => { created.current = null; }, [id]);
  return <RqDetail key={key} id={id} onCreated={(doc) => { created.current = doc.id; }} />;
}
