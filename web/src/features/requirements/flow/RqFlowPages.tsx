/**
 * 고객 요구사항(보드 webapp1 v63 RQ0 · RQ1 · RQ_Draft · RQ1_Edit · RQ_View) — docs/scenarios/11-content-flow.md §6 · docs/handoff/2026-10-12-content-detail-v63.md.
 *   /requirements            RQ0  목록(보드 List content=rq · 저장된 것 = 허브, 작성 중 = /v1/rq-flows)
 *   /requirements/new        RQ1  빈 최종본(사전 작업이 없어 팝업 없이 바로) — 처음 내용이 들어간 때 초안을 만들고 주소를 /flow/:id 로 바꾼다
 *   /requirements/flow/:id   상세 한 장(ContentDetail + RQBody) — 작성 중 · 저장됨 · 고치는 중 모두 같은 화면. 저장하면 그 자리에서 저장됨으로.
 * 완료 화면(FlowDoneView) · 단계 페이지는 없다. 후속 작업(DSS)은 저장된 것에만.
 */
import { useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { uploadFile } from '@/api/client';
import { useJob } from '@/api/jobs';
import { CONTENT, ContentDetail, ContentListScreen, detailMode, useFlow, useShellPage, type DraftRow, type NextCard } from '@/shell';
import { ErrorState, Skeleton, josa, josaRo, toast } from '@/ui';
import { rfApi, rfListKey, rfRoute, useRfDelete, useRqFlow, useRqFlows, type RFDoc, type RFStageOut } from './api';
import { canFinish, countsOf, isEmpty } from './form';
import { RqBody } from './RqBody';
import { errText, useRfEditor } from './useRfEditor';
import './rqflow.css';

const OK_EXT = ['pptx', 'pdf', 'docx', 'txt', 'eml', 'msg'];
const EMPTY_MSG = '프로젝트명 · 고객사 · 요구사항 중 하나는 적어 주세요.';
const WS_KEYS = [['ws', 'items'], ['ws', 'recent'], ['ws', 'counts']] as const;

/** RQ0 — 보드 List(content=rq). 아무것도 적지 않은 초안은 보이지 않는다 · 저장 전 초안은 카드에 손을 올리면 ×(지우기) */
export function RqListScreen() {
  const flows = useRqFlows();
  const remove = useRfDelete();
  const drafts: DraftRow[] = (flows.data?.items ?? [])
    .filter((m) => m.status !== 'done' && (m.title !== '새 요구사항' || m.counts.reqs > 0))
    .map((m) => ({ title: m.title, ref: m.code, to: rfRoute(m.id), sbIds: m.sb_ids, when: m.updated_at,
      onDelete: m.ver === 0 && !m.sb_ids.length ? () => remove(m.id) : undefined }));
  return <ContentListScreen content="rq" drafts={drafts} />;
}

/** 저장 뒤 토스트 — Storyboard 를 만들었는지 · 몇 개에 반영했는지 */
function savedText(out: RFStageOut) {
  const head = `${out.doc.code} v${out.doc.ver} 저장`;
  const sb = out.sb_id;
  if (!sb) return `${head} · Storyboard를 만들지 못했어요 · 다시 저장하면 다시 만들어요`;
  const name = out.sb_name ?? sb;
  if (out.created) return `${head} · Storyboard ‘${name}’(${sb})${josa(sb, '이', '가')} 만들어졌어요`;
  const synced = out.flow_sync?.synced ?? [];
  return synced.length ? `${head} · 연결된 Storyboard ${synced.length + 1}개에 반영했어요` : `${head} · Storyboard ‘${name}’(${sb})에 반영했어요`;
}

/** 후속 작업(보드 View NEXT.rq) — 그 Storyboard 에 DSS 가 있으면 「DSS-01 v1 · 열기」(허브 cell route), 없으면 사전 작업 고르기 없이 새로 */
function useNexts(sbId: string | null, saved: boolean): NextCard[] {
  const flow = useFlow(saved ? sbId : null);
  if (!saved || !sbId) return [];
  const cell = flow.data?.cells.find((c) => c.key === 'dss' && c.state === 'done');
  const dc = ((flow.data?.stages as Record<string, { counts?: { spaces?: number; products?: number; solutions?: number } } | null> | undefined)?.dss?.counts) ?? null;
  if (cell?.route) {
    return [{ key: 'dss', title: CONTENT.dss.label, to: cell.route, ref: cell.ref ? `${cell.ref}${cell.ver ? ` v${cell.ver}` : ''}` : null,
      desc: dc ? `공간 ${dc.spaces ?? 0} · 제품 ${dc.products ?? 0} · 솔루션 ${dc.solutions ?? 0}` : '공간별 제품 · 솔루션' }];
  }
  return [{ key: 'dss', title: CONTENT.dss.label, to: `/dss/new?sb=${encodeURIComponent(sbId)}&auto=1`, ref: null, desc: `${sbId}${josaRo(sbId)} 공간마다 제품 · 솔루션을 골라요` }];
}

function RqDetail({ initial, onCreated }: { initial: RFDoc | null; onCreated: (d: RFDoc) => void }) {
  const qc = useQueryClient();
  const ed = useRfEditor(initial, onCreated);
  const { doc, form, base, edit, docRef, applyDoc } = ed;
  const [uploading, setUploading] = useState<string[]>([]);
  const fileInput = useRef<HTMLInputElement>(null);
  // `/requirements/new` 로 들어와 이번에 만든 것은 저장 전까지 「새로 만들기」(보드 RQ1 — 첫 칸을 떠나며 초안이 생겨도 화면이 바뀌지 않게).
  // 다시 열면 「작성 중」(보드 RQ_Draft).
  const [bornNew] = useState(() => initial == null);
  const fillJob = doc?.fill_job ?? null;
  const filling = !!fillJob || uploading.length > 0;

  const job = useJob(fillJob, {
    onDone: async (j) => {
      if (!docRef.current) return;
      try {
        const fresh = await rfApi.get(docRef.current.id);
        applyDoc(fresh, true);
        const filled = Number((j.result as { filled?: number } | null)?.filled ?? 0);
        if (j.status === 'failed') toast(j.error?.message || '파일을 읽지 못했어요');
        else if (!filled) toast((j.result as { note?: string } | null)?.note || '파일에서 새로 채울 빈 칸을 찾지 못했어요');
        else toast(`파일에서 빈 칸 ${filled}개를 채웠어요`);
      } catch (e) { toast(errText(e)); }
    },
  });

  // SSE 가 끊겨도 채우기가 끝나면 풀리게(4초마다 문서 확인)
  useEffect(() => {
    if (!fillJob) return;
    const t = window.setInterval(async () => {
      const cur = docRef.current;
      if (!cur) return;
      try { const fresh = await rfApi.get(cur.id); if (!fresh.fill_job && docRef.current?.fill_job) applyDoc(fresh, true); } catch { /* 다음 번에 */ }
    }, 4000);
    return () => window.clearInterval(t);
  }, [fillJob, docRef, applyDoc]);

  const refreshLists = () => { for (const queryKey of [rfListKey, ...WS_KEYS]) void qc.invalidateQueries({ queryKey: [...queryKey] }); };

  /** 파일로 채우기 — 빈 칸만(사람이 쓴 값은 덮지 않음). 문서가 없으면 지금 폼으로 만든다 */
  const attach = async (files: File[]) => {
    const ok = files.filter((f) => OK_EXT.includes((f.name.split('.').pop() ?? '').toLowerCase()));
    if (ok.length < files.length) toast('PPTX · PDF · DOCX · TXT · 메일만 넣을 수 있어요');
    if (!ok.length || filling) return;
    setUploading(ok.map((f) => f.name));
    try {
      const d = await ed.ensureDoc();
      if (!(await ed.flush())) return;
      const metas = await Promise.all(ok.map((f) => uploadFile(f, { confidential: true, purpose: 'rq.source' })));
      const acc = await rfApi.fill(d.id, metas.map((m) => m.id));
      applyDoc({ ...(docRef.current ?? d), fill_job: acc.job_id });
    } catch (e) { toast(errText(e)); } finally { setUploading([]); }
  };

  /** 저장(:finish) — 처음이면 Storyboard 자동 생성, 다음부터는 연결된 Storyboard 모두에 반영. 끝나면 같은 화면이 저장됨으로 */
  const save = async () => {
    if (filling) throw new Error('파일에서 폼을 채우는 중이에요. 끝난 뒤 저장해 주세요.');
    await ed.flush();
    if (!canFinish(ed.formRef.current)) throw new Error(EMPTY_MSG);    // 서버 422 EMPTY_FORM 과 같은 규칙 — 빈 초안을 만들지 않게 먼저 본다
    const d = await ed.ensureDoc();
    if (!(await ed.flush())) throw new Error('입력한 내용을 아직 저장하지 못했어요. 다시 시도해 주세요.');
    const out = await rfApi.finish(d.id);
    applyDoc(out.doc, true, true);
    refreshLists();
    return out;
  };

  /** 되돌리기(:revert) — 저장한 판으로. 남은 입력을 먼저 저장해 되돌린 뒤 늦게 덮어쓰지 않게 */
  const revert = async () => {
    if (filling) throw new Error('파일에서 폼을 채우는 중이에요. 끝난 뒤 되돌려 주세요.');
    const d = docRef.current;
    if (!d) return;
    await ed.flush();
    applyDoc(await rfApi.revert(d.id), true, true);
    refreshLists();
  };

  const saved = (doc?.ver ?? 0) > 0;
  const changes = doc?.changes ?? 0;
  const empty = !saved && (bornNew || isEmpty(form));
  const mode = detailMode({ saved, changes, empty });
  const c = countsOf(form);
  const facts = [`키맨 ${c.keymen}`, `요구 ${c.reqs}`, ...(saved && c.check ? [`확인 필요 ${c.check}`] : [])];
  const sbIds = doc?.sb_ids ?? [];
  const nexts = useNexts(sbIds[0] ?? null, saved);
  const sources = doc?.sources ?? [];
  const last = sources[sources.length - 1];
  const progress = job.job && job.job.status === 'running' ? ` · ${job.job.progress ?? 0}%` : '';
  const readFrom = filling ? `${uploading[0] ?? last?.name ?? '파일'} 읽는 중${progress}`
    : last ? `${last.name}에서 읽음${sources.length > 1 ? ` 외 ${sources.length - 1}` : ''}`
      : mode === 'new' ? '아직 읽은 자료 없음' : '직접 입력';
  // 보드: 저장 버튼은 늘 파란색(빈 폼이면 누를 때 안내) — 파일을 채우는 동안만 막는다
  const canSave: boolean | string = filling ? '파일에서 폼을 채우는 중이에요. 끝난 뒤 저장해 주세요.' : true;

  return (
    <ContentDetail content="rq" saved={saved} changes={changes} empty={empty}
      title={saved ? (doc?.title || doc?.customer || CONTENT.rq.newLabel) : CONTENT.rq.newLabel}
      refCode={doc?.code ?? null} ver={doc?.ver ?? null} savedAt={doc?.saved_at ?? null} updatedAt={doc?.updated_at ?? null}
      facts={facts} sbIds={sbIds} onSave={save} onRevert={revert} canSave={canSave} nexts={nexts}
      savedToast={(out) => savedText(out as RFStageOut)}>
      <RqBody form={form} base={base} edit={edit} mode={mode} disabled={filling}
        readFrom={readFrom} readIsSource={filling || !!last} onFiles={(fs) => void attach(fs)} onPick={() => fileInput.current?.click()} fileInput={fileInput} />
    </ContentDetail>
  );
}

function Loading({ error, onRetry }: { error?: boolean; onRetry?: () => void }) {
  useShellPage({ section: CONTENT.rq.label, title: '', hasTask: false });
  if (error) return <div className="wm-page"><ErrorState message="요구사항을 불러오지 못했어요 · 지워졌거나 주소가 바뀌었을 수 있어요" onRetry={onRetry} /></div>;
  return <div className="wm-page"><Skeleton h={520} r={16} /></div>;
}

function Body({ id, onCreated }: { id: string | undefined; onCreated: (d: RFDoc) => void }) {
  const q = useRqFlow(id);
  if (id && q.isError) return <Loading error onRetry={() => q.refetch()} />;
  if (id && !q.data) return <Loading />;
  return <RqDetail initial={q.data ?? null} onCreated={onCreated} />;
}

/** `/requirements/new` · `/requirements/flow/:id` — 새로 만든 문서로 주소가 바뀔 때는 편집 상태를 그대로 둔다 */
export function RqFlowPage() {
  const { id } = useParams();
  const nav = useNavigate();
  const created = useRef<string | null>(null);
  const [key, setKey] = useState(id ?? 'new');
  const [prev, setPrev] = useState(id);
  if (id !== prev) {
    setPrev(id);
    if (!(id && id === created.current)) setKey(id ?? 'new');
  }
  return <Body key={key} id={id} onCreated={(d) => { created.current = d.id; nav(rfRoute(d.id), { replace: true }); }} />;
}
