/**
 * 솔루션 고르기 팝업(보드 webapp1 v63 SolPicker 820×700 · DS4 · DS4_AI) — 화면의 솔루션 칸 「+ 고르기」 · 「AI 솔루션 추천」이 연다.
 *   머리 72: 「솔루션 고르기 · 0개 이상」 · 한 줄 · AI 솔루션 추천(36) · 닫기
 *   카드: 체크 · 이름 · AI 추천(점선 · 근거) · 설명 · 함께 쓰는 제품(서비스가 DSS 제품으로 계산) · 상세(셸 솔루션 시트)
 *   겹침 안내(같은 역할 둘) · 바닥 72: 고른 수 · 취소 · 고른 솔루션 넣기
 * 고른 것은 「넣기」를 눌러야 문서에 들어간다(취소 · 닫기 = 그대로). 관련 있는 솔루션(함께 쓰는 제품 · 요구 · 업종)이 먼저, 나머지는 「솔루션 n개 더 보기」.
 */
import { useEffect, useMemo, useRef, useState } from 'react';
import { useOpenDetail, useShellUrl } from '@/shell';
import { Modal, Skeleton, ErrorState, cx, toast } from '@/ui';
import { useSolutionOptions, type DSDoc, type DSSolutionOption, type DsActions } from './api';
import { CheckIcon, STAR, XIcon } from './parts';

const errMsg = (e: unknown, fb: string) => (e as Error)?.message || fb;

/** 카드(보드 SolPicker) — AI 추천이면 고른 뒤에도 「AI 추천」 태그 · 근거가 남는다(선은 고름 2px 가 이긴다) */
function Card({ o, on, rec, onToggle }: { o: DSSolutionOption; on: boolean; rec: boolean; onToggle: () => void }) {
  const openDetail = useOpenDetail();
  return (
    <div className={cx('ds-solc', on ? 'ds-solc--on' : rec && 'ds-solc--rec')} data-solution={o.id}>
      <button type="button" className="ds-solc__btn" role="checkbox" aria-checked={on} onClick={onToggle}>
        <span className={cx('ds-solc__box', on && 'ds-solc__box--on')} aria-hidden>{on && <CheckIcon />}</span>
        <span className="ds-solc__txt">
          <span className="ds-solc__top"><span className="ds-solc__name">{o.name}</span>{rec && <span className="ds-solc__ai">AI 추천</span>}</span>
          <span className="ds-solc__desc">{o.desc ? `${o.desc} · ` : ''}<b>함께 쓰는 제품</b> {o.links.length ? o.links.join(' · ') : '—'}</span>
          {rec && o.why && <span className="ds-solc__why">근거 · {o.why}</span>}
        </span>
      </button>
      <button type="button" className="ds-solc__more" aria-label={`${o.name} 상세`} onClick={() => openDetail('solution', o.id)}>상세</button>
    </div>
  );
}

export function SolPicker({ doc, actions, runAi, onClose: close }: { doc: DSDoc; actions: DsActions; runAi?: boolean; onClose: () => void }) {
  // 셸 솔루션 상세 시트(?detail=)가 위에 떠 있으면 Esc 는 시트만 닫는다(팝업은 그대로)
  const { detail } = useShellUrl();
  const onClose = () => { if (!detail) close(); };
  const [sel, setSel] = useState<string[]>(() => doc.solutions.map((s) => s.id));
  const q = useSolutionOptions(doc.id, sel);
  const [aiBusy, setAiBusy] = useState(false);
  const [saving, setSaving] = useState(false);
  const [all, setAll] = useState(false);
  // 카드 순서는 처음 · AI 추천 뒤에만 서버 순서(관련 높은 순)로 — 고를 때마다 카드가 자리를 옮기지 않게
  const [order, setOrder] = useState<string[] | null>(null);
  const raw = q.data?.items;
  if (raw && !order) setOrder(raw.map((o) => o.id));
  const items = useMemo(() => {
    const list = raw ?? [];
    if (!order) return list;
    const at = new Map(order.map((id, i) => [id, i]));
    return [...list].sort((a, b) => (at.get(a.id) ?? 1e6) - (at.get(b.id) ?? 1e6));
  }, [raw, order]);
  const recIds = new Set(doc.solution_recs.map((r) => r.id));
  const shown = all ? items : items.filter((o) => o.relevant || sel.includes(o.id) || recIds.has(o.id));
  const hidden = items.length - shown.length;
  const title = doc.ver != null ? (doc.code ?? 'DSS') : doc.title || 'DSS';

  const ai = async () => {
    setAiBusy(true);
    try {
      const r = await actions.suggest('solutions');
      const fresh = await q.refetch();
      if (fresh.data) setOrder(fresh.data.items.map((o) => o.id));
      if (!r.added && r.message) toast(r.message);
    } catch (e) { toast(errMsg(e, 'AI 솔루션 추천에 실패했어요. 잠시 후 다시 시도해 주세요.')); } finally { setAiBusy(false); }
  };
  // 「AI 솔루션 추천」으로 열면 바로 돈다(보드 DS4_AI)
  const autoRan = useRef(false);
  useEffect(() => { if (runAi && !autoRan.current) { autoRan.current = true; void ai(); } });   // eslint-disable-line react-hooks/exhaustive-deps

  const put = async () => {
    const same = sel.length === doc.solutions.length && sel.every((id, i) => doc.solutions[i]?.id === id);
    if (same) { close(); return; }
    setSaving(true);
    try { await actions.setSolutions(sel); close(); } catch (e) { toast(errMsg(e, '솔루션을 넣지 못했어요')); setSaving(false); }
  };
  const n = sel.length;
  return (
    <Modal open onClose={onClose} width={820} height={700} ariaLabel="솔루션 고르기" bodyStyle={{ padding: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden', background: 'var(--wm-bg)' }}>
      <div className="ds-solp__head">
        <span className="ds-solp__titles"><span className="ds-solp__t">솔루션 고르기 · 0개 이상</span>
          <span className="ds-solp__sub">{title} 공간 제품과 함께 쓸 솔루션 · 고르지 않아도 저장돼요</span></span>
        <button type="button" className="ds-solp__ai" onClick={() => void ai()} disabled={aiBusy} aria-busy={aiBusy || undefined}>
          <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor" aria-hidden><path d={STAR} /></svg>{aiBusy ? 'AI가 찾는 중…' : 'AI 솔루션 추천'}</button>
        <button type="button" className="ds-solp__x" aria-label="닫기" onClick={onClose}><XIcon size={16} w={2.4} /></button>
      </div>
      <div className="ds-solp__list">
        {q.data?.overlap && <div className="ds-solp__overlap" role="status">{q.data.overlap}</div>}
        {q.isError && <ErrorState message="솔루션 카탈로그를 불러오지 못했어요" onRetry={() => q.refetch()} />}
        {q.isLoading ? <Skeleton h={250} r={14} /> : shown.map((o) => (
          <Card key={o.id} o={o} on={sel.includes(o.id)} rec={o.rec || recIds.has(o.id)}
            onToggle={() => setSel((v) => (v.includes(o.id) ? v.filter((x) => x !== o.id) : [...v, o.id]))} />
        ))}
        {hidden > 0 && <button type="button" className="ds-solp__more" onClick={() => setAll(true)}>솔루션 {hidden}개 더 보기</button>}
        {all && items.some((o) => !o.relevant && !sel.includes(o.id)) && <button type="button" className="ds-solp__more" onClick={() => setAll(false)}>관련 있는 솔루션만 보기</button>}
      </div>
      <div className="ds-solp__foot">
        <span className="ds-solp__line">{n ? `솔루션 ${n}개 골랐어요 · 넣으면 DSS 화면의 솔루션 칸에 들어가요` : '솔루션 없이 닫아도 돼요'}</span>
        <button type="button" className="ds-solp__cancel" onClick={onClose}>취소</button>
        <button type="button" className="ds-solp__ok" onClick={() => void put()} disabled={saving} aria-busy={saving || undefined}>{saving ? '넣는 중…' : '고른 솔루션 넣기'}</button>
      </div>
    </Modal>
  );
}
