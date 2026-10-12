/**
 * 공간 시나리오 최종본 본문(보드 webapp1 v62 View content=sc · SC_View · SC_Draft) — 칸은 보드 `<!-- 공간 시나리오 -->` 블록 인라인 px 그대로.
 *   공간(236 · 「공간 · <DSS>」 · 공간 버튼: 이름 14/600 + 「시나리오 n · 제품 n」 / 「시나리오 없음 · 제품 n」 · 고른 공간 #eaeefb)
 *   | 고른 공간(머리: 이름 18/700 · 시나리오 n · 제품 · 솔루션 칩) → 시나리오 카드 2열(이름 15/700 · 직접 / AI <A>안 · 수락 · 사용자 · 제품 · 번호 장면 · 자유 항목).
 *   시나리오가 없는 공간은 점선 칸 「이 공간은 시나리오가 없어요」. 아직 저장하지 않았으면 ② 자리표시(StepSlot · 큰 칸).
 *   본문 요소의 data 속성은 단계 팝업(ss-*)과 겹치지 않게 data-vspace · data-vscenario.
 */
import { useState } from 'react';
import { StepSlot, type DetailStatus } from '@/shell';
import { cx } from '@/ui';
import type { SSDoc, SSScenario } from './api';
import './scview.css';

/** 한 번이라도 저장했나(허브 stages.sc 에 있음) — 저장 뒤 고치면 서버 status 는 draft 로 돌아가지만 ver 는 남는다 */
export const scSaved = (d: SSDoc) => d.status === 'done' || (d.ver ?? 0) > 0;
/** 저장 뒤 고친 내용이 아직 허브에 반영되지 않았나(「저장 · vN+1」 전) */
export const scUnsaved = (d: SSDoc) => scSaved(d) && d.status !== 'done';
/** 마친 단계 수 — 1(Storyboard · 사전 작업) · 2(저장) */
export const scDone = (d: SSDoc) => (scSaved(d) ? 2 : 1);

/** 출처 태그(보드 renderVals: manual = 직접 · 그 밖 = `AI <안>안 · 수락`) */
function byOf(by: string | null | undefined): [string, string] {
  if (!by || by === 'manual') return ['직접', 'fl-vtag--man'];
  return [`AI ${by.split('-').pop()}안 · 수락`, 'fl-vtag--ai'];
}

function Card({ c }: { c: SSScenario }) {
  const [by, tone] = byOf(c.by);
  return (
    <div className="scv-card" data-vscenario={c.title || '새 시나리오'}>
      <span className="scv-card__top"><span className="scv-card__t">{c.title || '새 시나리오'}</span><span className={cx('fl-vtag', tone)}>{by}</span></span>
      <span className="scv-kv"><span className="scv-kv__k">사용자</span><span className={cx(!c.user && 'scv-off')}>{c.user || '사용자 미정'}</span></span>
      <span className="scv-kv"><span className="scv-kv__k">제품</span><span className="scv-pills">{c.products.map((p) => <span key={p} className="scv-pill">{p}</span>)}</span></span>
      {!!c.steps.length && (
        <span className="scv-steps">
          {c.steps.map((t, j) => (
            <span key={j} className="scv-step">
              <span className="scv-step__n">{j + 1}</span>
              <span className={cx('scv-step__t', t.text.includes('[확인 필요]') && 'scv-step__t--warn', !t.text && 'scv-off')}>{t.text || '—'}</span>
              {t.product && <span className="scv-step__p">{t.product}</span>}
            </span>
          ))}
        </span>
      )}
      {c.fields.map((f, i) => <span key={i} className="scv-kv"><span className="scv-kv__k">{f.k}</span><span>{f.v}</span></span>)}
    </div>
  );
}

export function ScViewBody({ d, done, status, onStep }: { d: SSDoc | null; done: number; status: DetailStatus; onStep: (k: number) => void }) {
  const spaces = d?.spaces ?? [];
  // 처음엔 시나리오가 있는 첫 공간(없으면 첫 공간)
  const [pick, setPick] = useState<string | null>(null);
  if (!d || done < 2) return <StepSlot n={2} label="공간 · 시나리오" what="공간 → 시나리오 → 장면" next={done === 1} cta={status === 'draft'} onOpen={() => onStep(2)} big />;
  const cur = spaces.find((s) => s.id === pick) ?? spaces.find((s) => s.scenarios.length) ?? spaces[0];
  return (
    <div className="scv">
      <div className="scv-spaces" aria-label="공간">
        <span className="scv-spaces__h">공간 · {d.dss_ref ?? 'DSS'}</span>
        {spaces.map((s) => {
          const n = s.scenarios.length;
          return (
            <button key={s.id} type="button" className={cx('scv-sp', s.id === cur?.id && 'scv-sp--on')} aria-pressed={s.id === cur?.id} data-vspace={s.name} onClick={() => setPick(s.id)}>
              <span className="scv-sp__name">{s.name}</span>
              <span className={cx('scv-sp__sub', !n && 'scv-sp__sub--none')}>{n ? `시나리오 ${n} · 제품 ${s.products.length}` : `시나리오 없음 · 제품 ${s.products.length}`}</span>
            </button>
          );
        })}
      </div>
      {cur && (
        <div className="scv-main">
          <div className="scv-head">
            <span className="scv-head__name">{cur.name}</span>
            <span className="scv-head__n">시나리오 {cur.scenarios.length}</span>
            <span className="scv-head__fill" />
            {cur.products.map((p) => (
              <span key={p.name} className="scv-prod" data-vproduct={p.name}>
                <span className={cx('scv-prod__k', p.kind === 'solution' && 'scv-prod__k--sol')}>{p.kind === 'solution' ? '솔루션' : '제품'}</span>
                <span className="scv-prod__n">{p.name}</span>
              </span>
            ))}
          </div>
          <div className="scv-body">
            {!cur.scenarios.length && (
              <div className="scv-empty">
                <b>이 공간은 시나리오가 없어요</b>
                <span>단계 칩 「공간 · 시나리오」에서 시나리오를 더할 수 있어요</span>
              </div>
            )}
            {!!cur.scenarios.length && <div className="scv-cards">{cur.scenarios.map((c) => <Card key={c.id} c={c} />)}</div>}
          </div>
        </div>
      )}
    </div>
  );
}
