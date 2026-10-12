/**
 * 공간별 제품 매칭 DSS(보드 webapp1 v63 DS0 · DS1 · DS2 · DS2_AI · DS_Draft · DS2_Edit · DS_View · DS_ViewJson · DS4 · DS4_AI) — docs/scenarios/11-content-flow.md §6.
 *   /dss                  DS0  목록(보드 List content=dss · 저장된 것 = 허브, 작성 중 = /v1/dss)
 *   /dss/new              DS1  목록 위 Storyboard 고르기 팝업(셸 GateScreen · `?sb=&auto=1` 이면 바로 만든다)
 *   /dss/:id              상세 한 장 = 셸 ContentDetail + 본문 DsBody(보드 DSBody). 새로 만들기 · 작성 중 · 저장됨 · 고치는 중이 모두 같은 화면이고,
 *                         저장하면 그 자리에서 저장됨으로 바뀐다(완료 화면 · 단계 쿼리 없음 — 예전 `?step=solution` 주소로 와도 이 화면).
 *                         팝업은 솔루션 고르기(SolPicker) · 제품 탐색(ProdPicker)만.
 */
import { useCallback, useMemo, useState } from 'react';
import { useParams, useSearchParams } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { CONTENT, ContentDetail, ContentListScreen, GateScreen, useFlow, useShellPage, type DraftRow, type NextCard } from '@/shell';
import { ErrorState, Skeleton, toast } from '@/ui';
import { createDss, dsListKey, dsRoute, useDsActions, useDsDelete, useDss, useDssList, type DSDoc, type DSStageOut } from './api';
import { DsBody, type Marks } from './DsBody';
import { addedRefs, dsOnAdd } from './shellcfg';
import './dss.css';

const M = CONTENT.dss;

/** 이번 방문에 Gate 팝업으로 막 만든 DSS — 저장 전 상세의 「새로 만들기」(다시 열면 「작성 중」) */
const freshIds = new Set<string>();

/** DS0 — 보드 List(content=dss). 작성 중(저장 전) DSS 는 초안 카드 — 손을 올리면 ×(지우기) */
export function DsListScreen() {
  const list = useDssList();
  const remove = useDsDelete();
  const drafts: DraftRow[] = (list.data?.items ?? []).filter((d) => d.status !== 'done')
    .map((d) => ({ title: d.title, ref: d.code ?? null, to: dsRoute(d.id), sbIds: d.sb_id ? [d.sb_id] : [], when: d.updated_at, onDelete: () => remove(d.id),
      // 지금 단계(보드 List v61 n/3): 솔루션을 하나라도 골랐으면 3 솔루션, 아니면 2 공간 · 제품
      step: d.counts.solutions > 0 ? 3 : 2 }));
  return <ContentListScreen content="dss" drafts={drafts} />;
}

/** DS1 — 목록 위 Storyboard 고르기 팝업(보드 Gate content=dss). Storyboard 화면 · 후속 작업의 「만들기」는 `?sb=<id>&auto=1` 로 와서 고르기를 건너뛴다(CF-07).
 *  같은 Storyboard 의 저장 전 초안이 있으면 서버가 그 초안을 돌려준다 → 이어서 연다(초안이 늘지 않음) */
export function DsGateScreen() {
  const [sp] = useSearchParams();
  const qc = useQueryClient();
  const list = useDssList();
  const remove = useDsDelete();
  const drafts: DraftRow[] = (list.data?.items ?? []).filter((d) => d.status !== 'done')
    .map((d) => ({ title: d.title, ref: d.code ?? null, to: dsRoute(d.id), sbIds: d.sb_id ? [d.sb_id] : [], when: d.updated_at, onDelete: () => remove(d.id),
      step: d.counts.solutions > 0 ? 3 : 2 }));
  return <GateScreen content="dss" initialSb={sp.get('sb')} autoStart={sp.get('auto') === '1'} drafts={drafts}
    onStart={async ({ sbId }) => {
      const { doc: d, reused } = await createDss(sbId);
      qc.setQueryData(['dss', 'doc', d.id], d);
      void qc.invalidateQueries({ queryKey: dsListKey });
      if (reused) toast(`작성 중이던 ${d.code ?? 'DSS'} 초안을 이어서 열어요`);
      else freshIds.add(d.id);
      return dsRoute(d.id);
    }} />;
}

const hasContent = (d: DSDoc) => !!d.industry || d.spaces.length > 0 || d.solutions.length > 0;

/** 저장 토스트 — 「DSS-01 v2 저장 · 연결된 Storyboard 2개에 반영했어요」 */
function savedText(d: DSDoc, out: DSStageOut) {
  const synced = out.flow_sync?.synced ?? [];
  const head = `${out.ref ?? d.code ?? 'DSS'} v${out.ver ?? (d.ver ?? 0) + 1} 저장`;
  if (!d.sb_id) return `${head}했어요`;
  return synced.length ? `${head} · 연결된 Storyboard ${synced.length + 1}개에 반영했어요` : `${head} · ${d.sb_id} 요약본에 반영했어요`;
}

/** `/dss/:id` — 상세 한 장(ContentDetail + DsBody) */
export function DsEditPage() {
  const { id = '' } = useParams();
  const q = useDss(id);
  const d = q.data;
  if (q.isError) return <div className="wm-page"><ShellOnly title="불러오지 못함" /><ErrorState message="DSS를 불러오지 못했어요 · 지워졌거나 주소가 바뀌었을 수 있어요" onRetry={() => q.refetch()} /></div>;
  if (!d) return <div className="wm-page"><ShellOnly title="" /><Skeleton h={520} r={16} /></div>;
  return <DsDetail key={d.id} doc={d} refetch={() => q.refetch()} />;
}

function ShellOnly({ title }: { title: string }) {
  useShellPage({ section: M.label, title, hasTask: false });
  return null;
}

function DsDetail({ doc, refetch }: { doc: DSDoc; refetch: () => Promise<unknown> }) {
  const actions = useDsActions(doc.id);
  const saved = doc.ver != null;
  const changes = doc.changes ?? 0;
  const empty = !saved && (freshIds.has(doc.id) || !hasContent(doc));
  const flow = useFlow(saved ? doc.sb_id : null);

  // 이 화면에서 고친 칸 · 줄(저장한 뒤 · 고친 곳이 있을 때만 보인다 — 저장 · 되돌리기 하면 지운다)
  const [marked, setMarked] = useState<Set<string>>(() => new Set());
  const add = useCallback((...k: string[]) => setMarked((s) => { const n = new Set(s); k.forEach((x) => n.add(x)); return n; }), []);
  const marks: Marks = useMemo(() => ({ has: (k: string) => changes > 0 && marked.has(k), add }), [marked, changes, add]);

  // 셸 상세 시트 · 팝오버의 「현재 작업에 추가」(제품 → 첫 공간, 솔루션 → 고른 솔루션) — ContentDetail 이 셸에 넘긴다
  const first = doc.spaces[0] ? { key: doc.spaces[0].key, name: doc.spaces[0].name } : null;
  const shell = {
    hasTask: true, addable: ['product', 'solution'] as ('product' | 'solution')[], added: addedRefs(doc), onAdd: dsOnAdd(doc, actions, first),
    taskContext: { products: doc.spaces.flatMap((s) => s.products.filter((p) => p.by !== 'ai-pending' && p.ref).map((p) => ({ ref: p.ref!, label: p.name }))) },
  };

  const c = doc.counts;
  const facts = [`공간 ${c.spaces}`, `제품 ${c.products}`, `솔루션 ${c.solutions}`];
  const canSave = c.spaces === 0 ? '공간을 하나 이상 넣어 주세요'
    : c.products === 0 ? '공간에 제품을 하나 이상 넣어 주세요 · 수락하지 않은 추천은 저장되지 않아요' : true;

  // 후속 작업 — 그 Storyboard 에 이미 있으면 「참조 vN · 열기」, 없으면 사전 작업 고르기 없이 바로 만든다
  const cell = (k: string) => flow.data?.cells.find((x) => x.key === k && x.state === 'done') ?? null;
  const next = (key: 'sc' | 'sp', title: string, desc: string, base: string): NextCard => {
    const x = cell(key);
    return { key, title, desc, ref: x?.ref ? `${x.ref}${x.ver ? ` v${x.ver}` : ''}` : null,
      to: x?.route ?? `/${base}/new?sb=${encodeURIComponent(doc.sb_id ?? '')}&auto=1` };
  };
  const nexts = doc.sb_id ? [
    next('sc', CONTENT.sc.label, `공간 ${c.spaces}개에서 사용자가 겪는 장면을 만들어요`, CONTENT.sc.base),
    next('sp', CONTENT.sp.label, `매칭한 제품 ${c.products}개를 스펙 시트로`, CONTENT.sp.base),
  ] : [];

  return (
    <ContentDetail content="dss" saved={saved} changes={changes} empty={empty} title={doc.title} refCode={doc.code} ver={doc.ver}
      savedAt={doc.saved_at} updatedAt={doc.updated_at} facts={facts} sbIds={doc.sb_id ? [doc.sb_id] : []}
      canSave={canSave} nexts={nexts} shell={shell}
      onSave={async () => {
        const out = await actions.finish();
        freshIds.delete(doc.id);
        setMarked(new Set());
        await refetch();
        return out;
      }}
      savedToast={(out) => savedText(doc, out)}
      onRevert={async () => { await actions.revert(); setMarked(new Set()); }}>
      <DsBody doc={doc} actions={actions} marks={marks} />
    </ContentDetail>
  );
}
