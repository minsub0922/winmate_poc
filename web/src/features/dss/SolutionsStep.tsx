/**
 * DSS · 솔루션(보드 webapp1 DS4 · DS4_AI) — 0개 이상 고른다. 카드 2열(본문 좌우 120 → 940).
 *   카드: 체크 · 이름 · 설명 · 함께 쓰는 제품(서비스가 DSS 제품으로 계산) · AI 추천이면 점선 + 근거 · 상세(셸 솔루션 상세 시트 SolutionDetail)
 *   고른 솔루션끼리 같은 역할이면 주황 안내(예: MagicINFO와 VXT는 둘 다 사이니지 CMS).
 * 관련 있는 솔루션(함께 쓰는 제품 · 요구 · 업종)이 먼저 보이고, 나머지는 「솔루션 n개 더 보기」.
 */
import { useMemo, useState } from 'react';
import { FlowBar, useOpenDetail, useShellPage } from '@/shell';
import { ErrorState, FlowScreen, Skeleton, cx, toast } from '@/ui';
import { useSolutionOptions, type DSDoc, type DSSolutionOption, type DsActions } from './api';
import { AiBtn, BackIcon, CheckIcon } from './parts';
import { addedRefs, dsOnAdd, dsShell } from './shellcfg';

const errMsg = (e: unknown, fb: string) => (e as Error)?.message || fb;

function SolutionCard({ o, on, accepted, onToggle }: { o: DSSolutionOption; on: boolean; accepted: boolean; onToggle: () => void }) {
  const openDetail = useOpenDetail();
  const rec = o.rec && !on;
  return (
    <div className={cx('ds-sol', on ? 'ds-sol--on' : rec && 'ds-sol--rec')} data-solution={o.id}>
      <button type="button" className="ds-solbtn" role="checkbox" aria-checked={on} onClick={onToggle}>
        <span className={cx('ds-box', on && 'ds-box--on')} aria-hidden>{on && <CheckIcon />}</span>
        <span className="ds-soltxt">
          <span className="ds-soltop"><span className="ds-solname">{o.name}</span>
            {rec && <span className="ds-tag ds-tag--ai-pending">AI 추천</span>}
            {on && accepted && <span className="ds-tag ds-tag--ai-accepted">AI 추천 · 수락</span>}</span>
          {o.desc && <span className="ds-soldesc">{o.desc}</span>}
          <span className="ds-sollinks"><b>함께 쓰는 제품</b> · {o.links.length ? o.links.join(' · ') : '—'}</span>
          {(rec || (on && accepted)) && o.why && <span className="ds-solwhy">근거 · {o.why}</span>}
        </span>
      </button>
      <button type="button" className="ds-ghost ds-ghost--32" aria-label={`${o.name} 상세`} onClick={() => openDetail('solution', o.id)}>상세</button>
    </div>
  );
}

export function SolutionsStep({ doc, actions, onBack, onSaved }: { doc: DSDoc; actions: DsActions; onBack: () => void; onSaved: (out: Awaited<ReturnType<DsActions['finish']>>) => void }) {
  const q = useSolutionOptions(doc.id);
  useShellPage(dsShell(doc, 3, { addable: ['solution'], added: addedRefs(doc), onAdd: dsOnAdd(doc, actions, null) }));
  const [aiBusy, setAiBusy] = useState(false);
  const [saving, setSaving] = useState(false);
  const [all, setAll] = useState(false);
  const [optimistic, setOptimistic] = useState<string[] | null>(null);
  const selected = optimistic ?? doc.solutions.map((s) => s.id);
  const why = new Map(doc.solutions.map((s) => [s.id, s]));
  // 카드 순서는 처음 불러올 때 · AI 추천 뒤에만 서버 순서(관련 높은 순)로 — 고를 때마다 카드가 자리를 옮기지 않게
  const [order, setOrder] = useState<string[] | null>(null);
  const raw = q.data?.items;
  const items = useMemo(() => {
    const list = raw ?? [];
    if (!order) return list;
    const at = new Map(order.map((id, i) => [id, i]));
    return [...list].sort((a, b) => (at.get(a.id) ?? 1e6) - (at.get(b.id) ?? 1e6));
  }, [raw, order]);
  if (raw && !order) setOrder(raw.map((o) => o.id));
  const shown = all ? items : items.filter((o) => o.relevant || selected.includes(o.id));
  const hidden = items.length - shown.length;
  const c = doc.counts;

  const toggle = async (o: DSSolutionOption) => {
    const next = selected.includes(o.id) ? selected.filter((x) => x !== o.id) : [...selected, o.id];
    setOptimistic(next);
    try { await actions.setSolutions(next); await q.refetch(); } catch (e) { toast(errMsg(e, '솔루션을 바꾸지 못했어요')); } finally { setOptimistic(null); }
  };
  const runAi = async () => {
    setAiBusy(true);
    try {
      const r = await actions.suggest('solutions');
      const fresh = await q.refetch();
      if (fresh.data) setOrder(fresh.data.items.map((o) => o.id));
      if (!r.added && r.message) toast(r.message);
    } catch (e) { toast(errMsg(e, 'AI 솔루션 추천에 실패했어요. 잠시 후 다시 시도해 주세요.')); } finally { setAiBusy(false); }
  };
  const save = async () => {
    setSaving(true);
    try { onSaved(await actions.finish()); } catch (e) { toast(errMsg(e, '저장하지 못했어요')); setSaving(false); }
  };
  const noProducts = c.products === 0;

  return (
    <FlowScreen pad="22px 120px" gap={12} className="ds-screen ds-solscreen"
      bar={<FlowBar sbIds={doc.sb_id ? [doc.sb_id] : []} note={`공간 ${c.spaces} · 제품 ${c.products}`} emptyText="연결된 Storyboard가 없어요" />}>
      <div className="ds-solhead">
        <div className="ds-solhead__t">
          <h1>솔루션을 고르세요 · 0개 이상</h1>
          <span>고르지 않아도 저장할 수 있어요.</span>
        </div>
        <AiBtn size="sol" onClick={() => void runAi()} busy={aiBusy}>AI 솔루션 추천</AiBtn>
      </div>
      {q.data?.overlap && <div className="ds-overlap" role="status">{q.data.overlap}</div>}
      {q.isError && <ErrorState message="솔루션 카탈로그를 불러오지 못했어요" onRetry={() => q.refetch()} />}
      {q.isLoading ? <Skeleton h={250} r={14} /> : (
        <div className="ds-solscroll">
          <div className="ds-solgrid">
            {shown.map((o) => <SolutionCard key={o.id} o={o} on={selected.includes(o.id)} accepted={why.get(o.id)?.by === 'ai-accepted'} onToggle={() => void toggle(o)} />)}
          </div>
          {hidden > 0 && <button type="button" className="ds-more" onClick={() => setAll(true)}>솔루션 {hidden}개 더 보기</button>}
          {all && items.some((o) => !o.relevant && !selected.includes(o.id)) && <button type="button" className="ds-more" onClick={() => setAll(false)}>관련 있는 솔루션만 보기</button>}
        </div>
      )}
      <div className="ds-solfoot">
        <button type="button" className="wm-flow__back" style={{ border: 'none', background: 'none', padding: 0 }} onClick={onBack}><BackIcon />공간 · 제품</button>
        <span style={{ flex: 1 }} />
        <span className={cx('wm-flow__summary', noProducts && 'wm-flow__summary--warn')}>
          {noProducts ? '공간에 제품을 하나 이상 넣어야 저장할 수 있어요' : selected.length ? `솔루션 ${selected.length}개 선택` : '솔루션 없이 저장해도 돼요'}
        </span>
        <button type="button" className="wm-flow__primary" onClick={() => void save()} disabled={saving || noProducts} aria-busy={saving || undefined}>{saving ? '저장 중…' : 'DSS 저장'}</button>
      </div>
    </FlowScreen>
  );
}
