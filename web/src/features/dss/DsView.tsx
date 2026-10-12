/**
 * DS_View — 저장한 DSS 보기(보드 webapp1 View content=dss · DS_View). 저장 뒤 · 목록 · 작업 내역 · 허브 cells[].route 로 열면 이 화면이다.
 * 사실 4칸(업종 2fr | 공간 · 제품 · 솔루션 1fr · h60) · 공간 카드 4열(공간별 제품 · 수량 · 출처) · 솔루션 띠 · 후속 작업 공간 시나리오 · Spec 시트.
 * 값은 DSS 문서 그대로 — 수량이 없으면 주황 「확인 필요」, 업종이 없으면 「—」(지어내지 않는다). 수락하지 않은 AI 추천(ai-pending)은 저장에 들지 않아 보이지 않는다.
 */
import { FlowContentView, useFlow, whenText } from '@/shell';
import { cx } from '@/ui';
import type { DSDoc, DSProduct, DSSpace } from './api';

const kept = (ps: DSProduct[]) => ps.filter((p) => p.by !== 'ai-pending');
/** 수량이 비었거나 [확인 필요] 같은 자리표시면 확인 필요(서버 stages.dss qtyStatus 와 같은 규칙) */
const qtyMissing = (q?: string | null) => !q || !q.trim() || q.includes('[');

/** 공간 근거 줄(보드: 근거 · RQ … / AI 추천 공간 · 수락(초록) / 확장 공간(검은 테두리 알약)) */
function spaceBasis(sp: DSSpace, rqRef?: string | null): { t: string; cls: string } {
  const b = sp.basis?.trim();
  // 요구에 없는 확장 공간(AI 공간 추천 ext) — 서버는 근거 대신 「요구에는 없음 · …」을 남긴다
  if (sp.by !== 'manual' && b?.startsWith('요구에는 없음')) return { t: '확장 공간', cls: 'dsv-basis--ext' };
  if (sp.by !== 'manual' && (!b || !rqRef || !b.startsWith(rqRef))) return { t: 'AI 추천 공간 · 수락', cls: 'dsv-basis--ai' };
  if (b) return { t: `근거 · ${b}`, cls: '' };
  return { t: '직접 추가한 공간', cls: '' };
}

export function DsView({ doc }: { doc: DSDoc }) {
  const sbId = doc.sb_id ?? null;
  const flow = useFlow(sbId);
  // 저장 시각 = 허브 기록(이 DSS 를 마지막으로 Storyboard 에 담은 때) · 허브가 없으면 문서 시각
  const savedAt = flow.data?.history?.slice().reverse().find((h) => h.key === 'dss' && (!doc.code || h.ref === doc.code))?.at ?? doc.updated_at;
  const spaces = doc.spaces.map((sp) => ({ ...sp, products: kept(sp.products) }));
  const nProd = spaces.reduce((n, sp) => n + sp.products.length, 0);
  const nQty = spaces.reduce((n, sp) => n + sp.products.filter((p) => qtyMissing(p.qty)).length, 0);
  const ind = doc.industry;
  const facts: { k: string; v: string; tag?: string; note?: string; muted?: boolean }[] = [
    { k: '업종', v: ind?.value || '—', muted: !ind?.value, tag: ind?.by === 'ai-accepted' ? 'AI 추론 · 수락' : undefined, note: ind?.basis ? `근거 ${ind.basis}` : undefined },
    { k: '공간', v: String(spaces.length) },
    { k: '제품', v: String(nProd), note: nQty ? `수량 확인 필요 ${nQty}` : undefined },
    { k: '솔루션', v: String(doc.solutions.length) },
  ];
  return (
    <FlowContentView stageKey="dss" sbIds={sbId ? [sbId] : []} title={doc.title || 'DSS'} refVer={`${doc.code ?? 'DSS'} v${doc.ver ?? 1}`}
      meta={[savedAt && `${whenText(savedAt)} 저장`, `공간 ${spaces.length}`, `제품 ${nProd}`, `솔루션 ${doc.solutions.length}`]}
      follow={sbId ? [
        { key: 'sc', desc: `공간 ${spaces.length}개에서 사용자가 겪는 장면을 만들어요` },
        { key: 'sp', desc: `매칭한 제품 ${nProd}개를 스펙 시트로` },
      ] : undefined}>
      <div className="dsv-body">
        <div className="dsv-facts">
          {facts.map((f) => (
            <div key={f.k} className="dsv-fact" data-fact={f.k}>
              <span className="dsv-fact__k">{f.k}</span>
              <span className="dsv-fact__row">
                <span className={cx('dsv-fact__v', f.muted && 'dsv-fact__v--muted')}>{f.v}</span>
                {f.tag && <span className="fl-vtag fl-vtag--ai">{f.tag}</span>}
                {f.note && <span className="dsv-fact__note" title={f.note}>{f.note}</span>}
              </span>
            </div>
          ))}
        </div>
        <div className="dsv-spaces">
          {spaces.map((sp) => {
            const b = spaceBasis(sp, doc.rq_ref);
            return (
              <div key={sp.key} className="dsv-space" data-space={sp.name}>
                <span className="dsv-space__top"><span className="dsv-space__name" title={sp.name}>{sp.name}</span><span className="dsv-space__n">제품 {sp.products.length}</span></span>
                <span className={cx('dsv-basis', b.cls)} title={b.t}>{b.t}</span>
                <span className="dsv-prods">
                  {sp.products.map((p) => {
                    const miss = qtyMissing(p.qty);
                    return (
                      <span key={p.id} className="dsv-prod" data-product={p.name}>
                        <span className="dsv-prod__name" title={p.name}>{p.name}</span>
                        <span className={cx('fl-vtag', 'dsv-qty', miss && 'fl-vtag--warn')}>{miss ? '확인 필요' : p.qty}</span>
                        <span className={cx('fl-vtag', 'dsv-by', p.by === 'manual' ? 'fl-vtag--line' : 'fl-vtag--ai')}>{p.by === 'manual' ? '직접' : 'AI'}</span>
                      </span>
                    );
                  })}
                  {!sp.products.length && <span className="dsv-prod dsv-prod--empty">넣은 제품이 없어요</span>}
                </span>
              </div>
            );
          })}
        </div>
        <div className="dsv-sols">
          <span className="dsv-sols__h">솔루션 {doc.solutions.length}</span>
          <span className="dsv-sols__list">
            {doc.solutions.map((o) => (
              <span key={o.id} className="dsv-sol" data-solution={o.id}>
                <span className="dsv-sol__name">{o.name}</span>
                {o.why && <span className="dsv-sol__basis">근거 · {o.why}</span>}
                <span className={cx('fl-vtag', o.by !== 'manual' && 'fl-vtag--ai')}>{o.by === 'manual' ? '직접' : 'AI 추천'}</span>
              </span>
            ))}
            {!doc.solutions.length && <span className="dsv-sol__none">고른 솔루션이 없어요</span>}
          </span>
        </div>
      </div>
    </FlowContentView>
  );
}
