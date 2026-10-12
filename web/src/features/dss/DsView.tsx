/**
 * DSS 최종본 본문(보드 webapp1 v62 View content=dss · DS_View · DS_Draft) — 칸은 보드 인라인 px 그대로.
 *   업종 · 공간 · 제품 · 솔루션 수(2fr 1fr 1fr 1fr · h60) → 공간 카드 4열(이름 · 근거 · 제품 · 수량 · 직접/AI) → 솔루션 줄(이름 · 근거 · 직접/AI 추천).
 *   아직 마치지 않은 단계의 칸은 StepSlot(②  공간 · 제품 / ③ 솔루션).
 */
import { StepSlot, type DetailStatus } from '@/shell';
import { cx } from '@/ui';
import type { DSDoc } from './api';
import './dsview.css';

const STEP = ['Storyboard', '공간 · 제품', '솔루션'] as const;

/** 마친 단계 수 — 1(Storyboard) · 2(공간에 제품이 하나라도) · 3(저장) */
export function dsDone(d: DSDoc): number {
  if (d.status === 'done') return 3;
  return d.counts.products > 0 ? 2 : 1;
}

function Fact({ k, v, tag, note, off }: { k: string; v: string; tag?: string; note?: string; off?: boolean }) {
  return (
    <div className="dsv-fact">
      <span className="dsv-fact__k">{k}</span>
      <span className="dsv-fact__row"><span className={cx('dsv-fact__v', off && 'dsv-fact__v--off')}>{off ? '—' : v}</span>
        {!off && tag && <span className="fl-vtag fl-vtag--ai">{tag}</span>}
        {note && <span className="dsv-fact__note">{note}</span>}</span>
    </div>
  );
}

export function DsViewBody({ d, done, status, onStep }: { d: DSDoc; done: number; status: DetailStatus; onStep: (k: number) => void }) {
  const spOn = done >= 2;
  const solOn = done >= 3;
  const spaces = d.spaces.map((s) => ({ ...s, products: s.products.filter((p) => p.by !== 'ai-pending') }));
  const nProd = spaces.reduce((n, s) => n + s.products.length, 0);
  const nQty = spaces.reduce((n, s) => n + s.products.filter((p) => !p.qty || p.qty.includes('[')).length, 0);
  const ind = d.industry;
  const off = (k: number) => `${'①②③'[k - 1]} ${STEP[k - 1]} 단계에서`;
  return (
    <div className="dsv">
      <div className="dsv-facts">
        <Fact k="업종" v={ind?.value ?? '[확인 필요]'} tag={ind?.by === 'ai-accepted' ? 'AI 추론 · 수락' : undefined}
          note={spOn ? (ind?.basis ? `근거 ${ind.basis}` : undefined) : off(2)} off={!spOn} />
        <Fact k="공간" v={String(spaces.length)} off={!spOn} note={spOn ? undefined : off(2)} />
        <Fact k="제품" v={String(nProd)} off={!spOn} note={spOn ? (nQty ? `수량 확인 필요 ${nQty}` : undefined) : off(2)} />
        <Fact k="솔루션" v={String(d.solutions.length)} off={!solOn} note={solOn ? undefined : off(3)} />
      </div>
      {spOn ? (
        <div className="dsv-spaces">
          {spaces.map((s) => {
            const aiSp = s.by === 'ai-accepted' && !s.basis;
            return (
              <div key={s.key} className="dsv-space" data-vspace={s.name}>
                <span className="dsv-space__top"><b>{s.name}</b><span>제품 {s.products.length}</span></span>
                <span className={cx('dsv-space__basis', aiSp && 'dsv-space__basis--ai')}>{aiSp ? 'AI 추천 공간 · 수락' : s.basis ? `근거 · ${s.basis}` : '직접 추가한 공간'}</span>
                <span className="dsv-space__prods">
                  {s.products.map((p) => {
                    const warn = !p.qty || p.qty.includes('[');
                    return (
                      <span key={p.id} className="dsv-prod">
                        <span className="dsv-prod__n" title={p.name}>{p.name}</span>
                        <span className={cx('fl-vtag', warn ? 'fl-vtag--warn' : 'fl-vtag--man')}>{warn ? '확인 필요' : p.qty}</span>
                        <span className={cx('fl-vtag', p.by === 'manual' ? 'fl-vtag--line' : 'fl-vtag--ai')}>{p.by === 'manual' ? '직접' : 'AI'}</span>
                      </span>
                    );
                  })}
                  {!s.products.length && <span className="dsv-prod__none">제품 없음</span>}
                </span>
              </div>
            );
          })}
        </div>
      ) : <StepSlot n={2} label={STEP[1]} what="업종 · 공간 · 공간별 제품" next={done === 1} cta={status === 'draft'} onOpen={() => onStep(2)} big />}
      {solOn ? (
        <div className="dsv-sols">
          <span className="dsv-sols__h">솔루션 {d.solutions.length}</span>
          <span className="dsv-sols__list">
            {d.solutions.map((o) => (
              <span key={o.id} className="dsv-sol" data-vsolution={o.name}><b>{o.name}</b>{o.why && <span>근거 · {o.why}</span>}
                <span className={cx('fl-vtag', o.by === 'manual' ? 'fl-vtag--man' : 'fl-vtag--ai')}>{o.by === 'manual' ? '직접' : 'AI 추천'}</span></span>
            ))}
            {!d.solutions.length && <span className="dsv-sols__none">고른 솔루션이 없어요</span>}
          </span>
        </div>
      ) : <StepSlot n={3} label={STEP[2]} what="솔루션 0개 이상" next={done === 2} cta={status === 'draft'} onOpen={() => onStep(3)} />}
    </div>
  );
}
