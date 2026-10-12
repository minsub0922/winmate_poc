/**
 * VP 최종본 본문(보드 webapp1 v62 View content=vp · VP_View · VP_Draft) — 칸은 보드 인라인 px 그대로(vpview.css).
 *   h44 줄 「<DSS>에서 n개를 골랐어요 · 고르지 않은 n — 이름들」 → 흰 칸(r14 · 안에서 스크롤)에 제품 · 솔루션마다 줄(210 | 1fr):
 *   왼쪽 종류 태그 · 이름 14.5/700 · 공간 · 「가치 n · 니즈 a/b」 / 오른쪽 가치마다 공간 칩 · 메시지 14.5/700 · 요구 칩 + 고객의 니즈 줄
 *   (채움: “니즈” + 직접 / AI 추론 · 수락, 비움: 주황 점선 「비어 있어요 · 고치기에서 적거나 AI 니즈 추론으로 채워요」).
 *   ② 단계를 마치지 않았으면(저장 전) 칸 전체가 StepSlot(big). 수락하지 않은 AI 후보(점선)는 최종본에 넣지 않는다(허브 stages.vp 와 같다).
 *   요소의 data 속성은 단계 팝업(VP2 · data-value)과 겹치지 않게 data-vitem · data-vvalue.
 */
import { CONTENT, StepSlot, type DetailStatus } from '@/shell';
import { cx } from '@/ui';
import type { VMDoc, VMItem, VMValue } from './api';
import './vpview.css';

const STEP = CONTENT.vp.steps;

/** 저장(한 번이라도 「저장」 → 허브 stages.vp)했는가 — 고쳐도 status 는 done 으로 남는다 */
export const vpSaved = (d: VMDoc) => d.status === 'done' || !!d.ver;

/** 마친 단계 수 — 1(Storyboard · 맵이 있으면) · 2(저장) */
export const vpDone = (d: VMDoc) => (vpSaved(d) ? 2 : 1);

/** 최종본에 들어가는 가치(점선 AI 후보 빼고) · 니즈(점선 AI 추론 빼고) */
const keptValues = (it: VMItem) => it.values.filter((v) => v.by !== 'ai-pending');
const needOf = (v: VMValue) => (v.need && v.need.by !== 'ai-pending' ? v.need : null);

/** 보드 View 머리 줄 — DSS 에서 고른 수 · 고르지 않은 것(+ DSS 밖에서 더함 · DSS 에서 빠짐이 있을 때만) */
export function vpSelection(d: VMDoc) {
  const cand = new Set(d.candidates.map((c) => c.name));
  const chosen = new Set(d.items.map((i) => i.name));
  const fromDss = d.items.filter((i) => cand.has(i.name)).length;
  const excluded = d.candidates.filter((c) => !chosen.has(c.name)).map((c) => c.name);
  const outside = d.items.filter((i) => !cand.has(i.name) && i.dss_status !== 'removed').map((i) => i.name);
  const dropped = d.items.filter((i) => i.dss_status === 'removed').map((i) => i.name);
  const src = d.dss_ref ?? (d.sb_id ? 'DSS' : 'KB 후보');
  const from = d.candidates.length ? `${src}에서 ${fromDss}개를 골랐어요` : `제품 · 솔루션 ${d.items.length}개를 골랐어요`;
  const out = [
    d.candidates.length ? (excluded.length ? `· 고르지 않은 ${excluded.length} — ${excluded.join(' · ')}` : `· ${src}의 제품 · 솔루션을 모두 골랐어요`) : '',
    outside.length ? `· ${d.candidates.length ? `${src} 밖에서 더한` : '직접 더한'} ${outside.length} — ${outside.join(' · ')}` : '',
    dropped.length ? `· DSS에서 빠짐 ${dropped.length} — ${dropped.join(' · ')}` : '',
  ].filter(Boolean).join(' ');
  return { from, out };
}

export function VpViewBody({ d, done, status, onStep }: { d: VMDoc; done: number; status: DetailStatus; onStep: (k: number) => void }) {
  if (done < 2) {
    return <StepSlot n={2} label={STEP[1]} what="제품 · 솔루션별 가치 · 고객의 니즈" next={done === 1} cta={status === 'draft'} onOpen={() => onStep(2)} big />;
  }
  const sel = vpSelection(d);
  return (
    <div className="vpv">
      <div className="fl-vbar vpv-bar">
        <span className="vpv-bar__from">{sel.from}</span>
        {sel.out && <span className="vpv-bar__out" title={sel.out}>{sel.out}</span>}
      </div>
      <div className="fl-vpanel vpv-panel">
        {d.items.map((it) => {
          const vals = keptValues(it);
          const needs = vals.filter((v) => needOf(v)).length;
          return (
            <div key={it.key} className="vpv-item" data-vitem={it.name}>
              <span className="vpv-item__l">
                <span className={cx('fl-vtag', it.kind === 'solution' ? 'vpv-kind--sol' : 'fl-vtag--man')}>{it.kind === 'solution' ? '솔루션' : '제품'}</span>
                <span className="vpv-item__name">{it.name}</span>
                <span className="vpv-item__sp">{it.spaces.length ? it.spaces.join(' · ') : '공간 정하지 않음'}</span>
                <span className="vpv-item__n">{`가치 ${vals.length} · 니즈 ${needs}/${vals.length}`}</span>
              </span>
              <span className="vpv-vals">
                {vals.map((v) => {
                  const need = needOf(v);
                  return (
                    <span key={v.id} className="vpv-val" data-vvalue={v.id}>
                      <span className="vpv-val__top">
                        <span className="vpv-space">{v.space}</span>
                        <span className="vpv-msg">{v.message}</span>
                        {v.req && <span className="vpv-req" title={v.req}>{v.req}</span>}
                      </span>
                      <span className={cx('vpv-need', !need && 'vpv-need--empty')}>
                        <span className="vpv-need__k">고객의 니즈</span>
                        <span className="vpv-need__t">{need ? `“${need.text}”` : '비어 있어요 · 고치기에서 적거나 AI 니즈 추론으로 채워요'}</span>
                        {need && <span className={cx('fl-vtag', need.by === 'manual' ? 'fl-vtag--man' : 'fl-vtag--ai')}>{need.by === 'manual' ? '직접' : 'AI 추론 · 수락'}</span>}
                      </span>
                    </span>
                  );
                })}
                {!vals.length && <span className="vpv-none">적은 가치가 없어요 · 고치기에서 적거나 AI 가치 매칭 추천으로 채워요</span>}
              </span>
            </div>
          );
        })}
        {!d.items.length && <div className="vpv-empty">고른 제품 · 솔루션이 없어요</div>}
      </div>
    </div>
  );
}
