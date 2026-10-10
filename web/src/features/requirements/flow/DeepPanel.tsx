/**
 * AI 심층 질의(보드 RQ1_AI 오른쪽 380px) — 「AI 심층 질의로 폼 완성」을 누를 때만 열린다(CF-08).
 * 질문은 AI 결과(ai-pending)라 「폼에 반영」해야 폼에 들어간다(ai-accepted). 「고객에게 확인으로 남기기」면 확인 필요로 남는다.
 */
import { useEffect, useState } from 'react';
import { Skeleton, cx, toast } from '@/ui';
import type { RFDeep } from './api';

const STAR = 'M12 2.5l1.9 5.6 5.6 1.9-5.6 1.9L12 17.5l-1.9-5.6L4.5 10l5.6-1.9z';

export function DeepPanel({ deep, loading, busy, onAnswer, onClose }: {
  deep: RFDeep | null | undefined;
  /** 질문을 찾는 중 */
  loading: boolean;
  /** 답을 반영하는 중 */
  busy: boolean;
  onAnswer: (qid: string, body: { option?: number | null; text?: string | null; later: boolean }) => Promise<void>;
  onClose: () => void;
}) {
  const qs = deep?.questions ?? [];
  const total = qs.length;
  const curIdx = deep?.current ?? null;
  const q = curIdx !== null && curIdx !== undefined ? qs[curIdx] : null;
  const done = !loading && !!deep && !q;
  const [pick, setPick] = useState<number | null>(null);
  const [etc, setEtc] = useState('');
  useEffect(() => { setPick(null); setEtc(''); }, [q?.id]);

  const apply = async () => {
    if (!q || busy) return;
    if (pick === null && !etc.trim()) { toast('보기를 고르거나 직접 입력해 주세요.'); return; }
    await onAnswer(q.id, etc.trim() ? { text: etc.trim(), later: false } : { option: pick, later: false });
  };
  const prog = loading ? '' : done ? `${total} / ${total}` : q ? `${(curIdx ?? 0) + 1} / ${total}` : '';
  return (
    <aside className="rqf-ai" aria-label="AI 심층 질의">
      <div className="rqf-aihead">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="var(--wm-brand)" aria-hidden><path d={STAR} /></svg>
        <b>AI 심층 질의</b>
        <span className="rqf-aiprog" aria-label="진행">{prog}</span>
        <button type="button" className="rqf-x" onClick={onClose} aria-label="닫기">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" aria-hidden><path d="M6 6l12 12M18 6L6 18" /></svg>
        </button>
      </div>
      {loading && (
        <div className="rqf-aibody" role="status" aria-label="부족한 곳을 찾는 중">
          <span className="rqf-ailead">폼에서 부족한 곳을 찾는 중이에요…</span>
          <Skeleton h={22} w="40%" r={6} /><Skeleton h={50} r={8} />
          <Skeleton h={44} r={10} /><Skeleton h={44} r={10} /><Skeleton h={44} r={10} />
        </div>
      )}
      {!loading && q && (
        <>
          <div className="rqf-aibody">
            <span className="rqf-ailead">폼에서 부족한 곳 {total}개를 찾았어요 · 답하면 폼에 바로 반영돼요</span>
            <span className="rqf-aiwhere">{q.tag}</span>
            <span className="rqf-aiq" id={`rqf-q-${q.id}`}>{q.text}</span>
            <div className="rqf-opts" role="group" aria-labelledby={`rqf-q-${q.id}`}>
              {q.options.map((o, i) => (
                <button key={o.label} type="button" className="rqf-opt" aria-pressed={pick === i} onClick={() => { setPick(i); setEtc(''); }}>
                  <span className="rqf-radio" aria-hidden /><span className="rqf-optt">{o.label}</span>
                </button>
              ))}
              <div className="rqf-etc">
                <label htmlFor="rq-ai-etc" className="wm-sr-only">직접 입력</label>
                <input id="rq-ai-etc" placeholder="직접 입력" value={etc} onChange={(e) => { setEtc(e.target.value); if (e.target.value) setPick(null); }}
                  onKeyDown={(e) => { if (e.key === 'Enter' && !e.nativeEvent.isComposing) void apply(); }} />
              </div>
            </div>
          </div>
          <div className="rqf-aifoot">
            <button type="button" className="rqf-later" disabled={busy} onClick={() => void onAnswer(q.id, { later: true })}>고객에게 확인으로 남기기</button>
            <span style={{ flexGrow: 1 }} />
            <button type="button" className={cx('rqf-apply')} disabled={busy} aria-busy={busy || undefined} onClick={() => void apply()}>폼에 반영</button>
          </div>
        </>
      )}
      {done && (
        <div className="rqf-aidone">
          <div className="rqf-aidone__box" role="status">
            <b>{total ? '질의를 마쳤어요' : '더 물을 곳이 없어요'}</b>
            <span>{total ? `${deep?.applied ?? 0}개를 폼에 반영했고, ${deep?.asked ?? 0}개는 고객에게 확인으로 남겼어요.` : '폼에서 비어 있거나 불분명한 곳을 찾지 못했어요.'}</span>
          </div>
          <button type="button" className="rqf-apply rqf-apply--full" onClick={onClose}>닫기</button>
        </div>
      )}
    </aside>
  );
}
