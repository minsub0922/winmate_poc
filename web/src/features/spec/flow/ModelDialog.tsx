/**
 * 제품 줄 하나의 모델 고르기 · 바꾸기 · 수량(보드 SP2 에는 없는 팝업 — 모양은 보드 ProdPicker 760×640 을 따른다).
 * 기본은 같은 제품군 모델(맞춘 모델이 없으면 이름으로 카탈로그 검색), 아래 점선 입력으로 다른 모델을 찾는다.
 * 고르면 바로 그 모델의 공식 카탈로그 값으로 다시 채운다(서버 PATCH rows/{key}). 수량은 DSS 원문을 보여 주고 사람이 정한다.
 */
import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Modal, Skeleton, cx, toast } from '@/ui';
import { modelOptions, WARN_SHORT, type SFDoc } from './api';

export function ModelDialog({ doc, rowKey, onClose, onPick, onQty, onClear }: {
  doc: SFDoc; rowKey: string | null; onClose: () => void;
  onPick: (code: string) => Promise<unknown>; onQty: (qty: number) => Promise<unknown>; onClear: () => Promise<unknown>;
}) {
  const r = doc.rows.find((x) => x.key === rowKey);
  const [q, setQ] = useState('');
  const [term, setTerm] = useState('');
  const [busy, setBusy] = useState<string | null>(null);
  const [qty, setQty] = useState('');
  useEffect(() => { setQ(''); setTerm(''); }, [rowKey]);
  useEffect(() => { setQty(r?.qty == null ? '' : String(r.qty)); }, [rowKey, r?.qty]);
  useEffect(() => { const t = setTimeout(() => setTerm(q.trim()), 300); return () => clearTimeout(t); }, [q]);
  const opts = useQuery({
    queryKey: ['spec', 'flow', doc.id, 'models', rowKey, term, r?.family_id ?? null],
    enabled: !!rowKey, queryFn: () => modelOptions(doc.id, rowKey!, term || undefined),
  });
  if (!r) return null;
  const pick = async (code: string) => {
    setBusy(code);
    try { await onPick(code); } catch (e) { toast((e as Error).message || '모델을 바꾸지 못했어요'); } finally { setBusy(null); }
  };
  const commitQty = () => {
    const t = qty.trim();
    if (!t) { setQty(r.qty == null ? '' : String(r.qty)); return; }
    const n = Math.max(0, Math.min(9999, Math.round(Number(t))));
    if (!Number.isFinite(n) || n === r.qty) { setQty(r.qty == null ? '' : String(r.qty)); return; }
    onQty(n).catch(() => toast('수량을 바꾸지 못했어요'));
  };
  const items = opts.data?.items ?? [];
  const family = opts.data?.basis === 'family';
  return (
    <Modal open={!!r} onClose={onClose} width={760} height={640} ariaLabel={`${r.name} 모델 고르기`}
      bodyStyle={{ padding: '14px 24px', display: 'flex', flexDirection: 'column', gap: 10 }}
      title={<span className="sf-dlg__head"><span className="sf-dlg__t">{r.name} 모델 고르기</span>
        <span className="sf-dlg__s">{r.spaces.join(' · ') || '공간 없음'} · 고른 모델의 값은 공식 카탈로그에서 채워요</span></span>}
      footer={<div className="sf-dlg__foot">
        <label className="sf-dlg__qty">수량
          <input inputMode="numeric" value={qty} placeholder="확인 필요" aria-label={`${r.name} 수량`}
            onChange={(e) => setQty(e.target.value.replace(/[^0-9]/g, '').slice(0, 4))} onBlur={commitQty}
            onKeyDown={(e) => { if (e.key === 'Enter') (e.target as HTMLInputElement).blur(); }} />
        </label>
        <span className="sf-dlg__note" title={r.qty_note ?? undefined}>{r.qty_note ? `DSS · ${r.qty_note}` : 'DSS 수량 없음'}</span>
        <button type="button" className="wm-btn wm-btn--primary wm-btn--h40 sf-dlg__done" onClick={onClose}>완료</button>
      </div>}>
      {!!r.warnings.length && (
        <div className="sf-dlg__warns" role="note">{r.warnings.map((w) => <div key={w.kind}><b>{WARN_SHORT[w.kind] ?? '확인 필요'}</b>{w.text}</div>)}</div>
      )}
      <span className="sf-dlg__group">{family ? `같은 제품군 · ${r.family_name ?? ''}` : `카탈로그 검색 · ‘${term || r.name}’`}</span>
      {opts.isLoading && <Skeleton h={160} r={10} />}
      {!opts.isLoading && !items.length && <div className="sf-dlg__empty">찾은 모델이 없어요 · 아래에서 모델명이나 모델코드로 찾아보세요</div>}
      {!!items.length && (
        <div className="sf-dlg__grid" role="radiogroup" aria-label="고를 수 있는 모델">
          {items.map((o) => { const cur = o.model_code === r.model_code; return (   // 지금 모델은 행에서(목록 응답의 current 는 고른 뒤 낡는다)
            <button key={o.model_code} type="button" role="radio" aria-checked={cur} className={cx('sf-dlg__opt', cur && 'sf-dlg__opt--on')}
              onClick={() => !cur && pick(o.model_code)} disabled={!!busy}>
              <span className={cx('sf-dlg__box', cur && 'sf-dlg__box--on')} aria-hidden>
                {cur && <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="3.4" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12l5 5L20 7" /></svg>}
              </span>
              <span className="sf-dlg__txt"><span className="sf-dlg__name">{o.display_name}</span>
                <span className="sf-dlg__where">{o.model_code}{o.size_inch ? ` · ${o.size_inch}"` : ''}{!family && o.family_name ? ` · ${o.family_name}` : ''}</span></span>
              {(cur || busy === o.model_code) && <span className="sf-dlg__tag">{cur ? '지금' : '바꾸는 중'}</span>}
            </button>
          ); })}
        </div>
      )}
      <label className="wm-sr" htmlFor="sf-dlg-search">카탈로그에서 다른 모델 찾기</label>
      <input id="sf-dlg-search" className="sf-dlg__search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="+ 카탈로그에서 다른 모델 찾기 (모델명 · 모델코드, 예: QM65C)" />
      {r.model_code && (
        <button type="button" className="sf-dlg__clear" onClick={() => onClear().catch(() => toast('모델을 비우지 못했어요'))}>
          카탈로그 모델 비우기 · 값은 [확인 필요]로 남겨요
        </button>
      )}
    </Modal>
  );
}
