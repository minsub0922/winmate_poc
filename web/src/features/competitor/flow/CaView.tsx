/**
 * 경쟁사 분석 최종본 본문(보드 webapp1 v62 View content=ca · CA_View · CA_Draft) — 칸은 보드 인라인 px 그대로(caview.css).
 *   비교 기준 줄(h44 · DSS ref · 제품군 칩 · 판정 합계 우위 · 비슷 · 열위 · 자료 없음)
 *   → 표(머리 40 · 236px + 5축 82px + 주장 1fr · 줄 min 92): 경쟁사 · 직접/AI 웹 탐색 · 위키 한 줄 · 겹치는 공간 | 축마다 비교 쌍 판정을 모은 칩 | 주장 2개
 *   → 꼬리말. 저장 전이면 ② 경쟁사 리스트업 자리표시(StepSlot big).
 * 칸의 data 속성은 단계 팝업(CA2)과 겹치지 않게 data-v* 로 둔다(팝업 뒤 최종본도 DOM 에 있다).
 */
import { StepSlot, type DetailStatus } from '@/shell';
import { cx } from '@/ui';
import { DIMS, type CFCompetitor, type CFDoc, type DimKey } from './api';
import './caview.css';

const STEP2 = '경쟁사 리스트업';

/** 판정 칩 종류 — 비교 쌍마다의 판정 4가지 + 우위 · 열위가 같은 수로 엇갈림 */
type Agg = 'ours-better' | 'similar' | 'ours-worse' | 'no-data' | 'mixed';
const LABEL: Record<Agg, string> = { 'ours-better': '우위', similar: '비슷', 'ours-worse': '열위', 'no-data': '자료 없음', mixed: '엇갈림' };

/** 한 번이라도 저장(:finish)했는지 — 저장하면 Storyboard 에 연결된다 */
export const caSaved = (d: CFDoc) => d.status === 'done' || d.ver != null;
/** 마친 단계 수 — 1(Storyboard) · 2(저장) */
export const caDone = (d: CFDoc) => (caSaved(d) ? 2 : 1);

/**
 * 경쟁사 하나의 한 축 — 비교 쌍 판정을 모은다(보드 renderVals 「경쟁사 분석」 그대로):
 * 우위와 열위가 함께면 많은 쪽(같으면 엇갈림 · 「우위 a · 열위 b」), 아니면 우위 > 열위 > 비슷 > 자료 없음 순 · 「n / m쌍」.
 */
export function aggregate(c: Pick<CFCompetitor, 'matches'>, k: DimKey): { v: Agg; n: string } {
  const n: Record<Exclude<Agg, 'mixed'>, number> = { 'ours-better': 0, similar: 0, 'ours-worse': 0, 'no-data': 0 };
  for (const m of c.matches) n[(m.dims?.[k]?.verdict ?? 'no-data') as Exclude<Agg, 'mixed'>]++;
  const tot = c.matches.length;
  const b = n['ours-better'];
  const w = n['ours-worse'];
  const v: Agg = b && w ? (b === w ? 'mixed' : b > w ? 'ours-better' : 'ours-worse')
    : b ? 'ours-better' : w ? 'ours-worse' : n.similar ? 'similar' : 'no-data';
  if (!tot) return { v, n: '비교 쌍 없음' };
  return { v, n: v === 'mixed' ? `우위 ${b} · 열위 ${w}` : `${n[v]} / ${tot}쌍` };
}

/** 위키 한 줄(보드: 업종 · 규모 · 본사) — 규모 칸에 「· 매출 …」이 붙어 있으면 뗀다 */
const wikiLine = (c: CFCompetitor) => [c.wiki.industry, c.wiki.size.split(/\s*·\s*매출/)[0], c.wiki.hq].filter(Boolean).join(' · ');

function Chip({ v }: { v: Agg }) {
  return <span className={cx('cav-chip', `cav-chip--${v}`)}>{LABEL[v]}</span>;
}

export function CaViewBody({ d, done, status, onStep }: { d: CFDoc | null; done: number; status: DetailStatus; onStep: (k: number) => void }) {
  if (!d || done < 2) {
    return <StepSlot n={2} label={STEP2} what="경쟁사 · 제안 기준 비교 판정 · 주장 포인트" next={done === 1} cta={status === 'draft'} onOpen={() => onStep(2)} big />;
  }
  const comps = d.competitors.filter((c) => c.by !== 'ai-pending');     // 점선 AI 후보는 저장에 들지 않는다
  const t = d.counts.verdicts;
  const tally: Array<[Agg, number]> = [['ours-better', t.oursBetter], ['similar', t.similar], ['ours-worse', t.oursWorse], ['no-data', t.noData]];
  return (
    <div className="cav">
      <div className="fl-vbar cav-bar">
        <span className="cav-bar__from">비교 기준 · {d.basis.from ?? 'DSS'}</span>
        {d.basis.categories.map((cat) => <span key={cat} className="cav-cat">{cat}</span>)}
        <span className="cav-bar__sp" />
        {tally.map(([k, n]) => <span key={k} className="cav-tally" data-vtally={k}><Chip v={k} />{n}</span>)}
      </div>
      <div className="fl-vpanel cav-table">
        <div className="cav-grid cav-head">
          <span>경쟁사 · 겹치는 공간</span>
          {DIMS.map(([k, l]) => <span key={k}>{l}</span>)}
          <span>우리 주장 포인트</span>
        </div>
        <div className="cav-rows">
          {comps.map((c) => (
            <div key={c.id} className="cav-grid cav-row" data-vcomp={c.name}>
              <span className="cav-who">
                <span className="cav-who__top">
                  <b title={c.name}>{c.name}</b>
                  <span className={cx('fl-vtag', c.by === 'manual' ? 'fl-vtag--man' : 'fl-vtag--ai')}>{c.by === 'manual' ? '직접' : 'AI 웹 탐색'}</span>
                </span>
                <span className="cav-who__wiki">{wikiLine(c)}</span>
                {c.spaces.length > 0 && <span className="cav-who__sp">{c.spaces.join(' · ')} 겹침</span>}
              </span>
              {DIMS.map(([k, l]) => {
                const a = aggregate(c, k);
                return (
                  <span key={k} className="cav-cell" data-vdim={k} aria-label={`${c.name} ${l} ${LABEL[a.v]} · ${a.n}`}>
                    <Chip v={a.v} /><span className="cav-cell__n">{a.n}</span>
                  </span>
                );
              })}
              <span className="cav-claims">
                {c.claims.slice(0, 2).map((m, i) => (
                  <span key={`${i}-${m.axis}`} className="cav-claim"><span className="cav-axis">{m.axis}</span><span className="cav-claim__t">{m.text}</span></span>
                ))}
              </span>
            </div>
          ))}
        </div>
      </div>
      <span className="fl-vfoot">판정은 우리 제품 기준 · 경쟁사마다 비교 쌍의 판정을 모은 것 · 수치와 견적은 원문 · 사내 자료로 확인</span>
    </div>
  );
}
