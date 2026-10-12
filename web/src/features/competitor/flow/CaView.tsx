/**
 * CA_View — 저장한 경쟁사 분석 보기(보드 webapp1 View content=ca · CA_View). 저장 뒤 · 목록 · 작업 내역 · 허브 route 로 열면 이 화면이다.
 * 띠 h44(비교 기준 · DSS 참조 · 제품군 칩 · 판정 합계) → 표(머리 h40 · 236px + 5축 82px + 1fr 주장 포인트) → 아래 안내 11.5. 후속 작업 없음.
 * 값은 이 문서(CFDoc)에서만 — 목록에 든 경쟁사(점선 AI 후보 제외)와 그 비교 쌍 판정을 모은다. 위키 값은 문서에 있는 그대로(자리표시 포함).
 */
import { FlowContentView, useFlow, whenText } from '@/shell';
import { cx } from '@/ui';
import { DIMS, VERDICT_LABEL, type CFClaim, type CFCompetitor, type CFDoc, type DimKey, type Verdict } from './api';

type V = NonNullable<Verdict>;
type Agg = V | 'mixed';
const AGG_LABEL: Record<Agg, string> = { ...VERDICT_LABEL, mixed: '엇갈림' };
const TALLY: Array<[V, keyof CFDoc['counts']['verdicts']]> = [['ours-better', 'oursBetter'], ['similar', 'similar'], ['ours-worse', 'oursWorse'], ['no-data', 'noData']];

/** 보드 규칙 — 경쟁사 하나의 한 축: 우위 · 열위가 함께 있으면 많은 쪽(같으면 엇갈림), 아니면 우위 › 열위 › 비슷 › 자료 없음 */
export function aggregate(c: CFCompetitor, k: DimKey): { v: Agg; n: string } {
  const n: Record<V, number> = { 'ours-better': 0, similar: 0, 'ours-worse': 0, 'no-data': 0 };
  for (const m of c.matches) n[((m.dims?.[k]?.verdict) ?? 'no-data') as V]++;
  const b = n['ours-better'];
  const w = n['ours-worse'];
  const v: Agg = b && w ? (b === w ? 'mixed' : b > w ? 'ours-better' : 'ours-worse')
    : b ? 'ours-better' : w ? 'ours-worse' : n.similar ? 'similar' : 'no-data';
  return { v, n: v === 'mixed' ? `우위 ${b} · 열위 ${w}` : `${n[v]} / ${c.matches.length}쌍` };
}

const claimText = (x: CFClaim) => (x.supports ? `${x.text} — ${x.supports}` : x.text);

function Chip({ v }: { v: Agg }) {
  return <span className={cx('cav-chip', `cav-chip--${v}`)}>{AGG_LABEL[v]}</span>;
}

/** 저장 시각 — CA 문서 응답에는 저장 시각이 없어 허브 이력(같은 참조 · 판의 ca 저장)에서 읽는다. 없으면 meta 에서 빠진다 */
function useSavedAt(d: CFDoc): string | null {
  const flow = useFlow(d.sb_id ?? null).data;
  const h = (flow?.history ?? []).filter((x) => x.key === 'ca' && x.ref === d.code && (d.ver == null || x.ver === d.ver));
  return h.length ? h[h.length - 1].at : null;
}

export function CaView({ doc }: { doc: CFDoc }) {
  const savedAt = useSavedAt(doc);
  const comps = doc.competitors.filter((c) => c.by !== 'ai-pending');
  const nPairs = comps.reduce((s, c) => s + c.matches.length, 0);
  const tally = doc.counts.verdicts;
  return (
    <FlowContentView stageKey="ca" sbIds={doc.sb_id ? [doc.sb_id] : []} title={doc.title || '경쟁사 분석'} refVer={`${doc.code ?? doc.id} v${doc.ver ?? 1}`}
      meta={[savedAt && `${whenText(savedAt)} 저장`, `경쟁사 ${comps.length}`, `비교 쌍 ${nPairs}`]}>
      <div className="cav">
        <div className="fl-vstrip cav-strip">
          <span className="cav-from">비교 기준 · {doc.basis.from ?? '[확인 필요]'}</span>
          {doc.basis.categories.map((c) => <span key={c} className="cav-cat">{c}</span>)}
          <span className="cav-grow" />
          {TALLY.map(([v, key]) => <span key={v} className="cav-tally" data-verdict={v}><Chip v={v} />{tally[key]}</span>)}
        </div>
        <div className="fl-vcard cav-card" aria-label="경쟁사별 비교">
          <div className="cav-grid cav-head">
            <span>경쟁사 · 겹치는 공간</span>
            {DIMS.map(([k, l]) => <span key={k}>{l}</span>)}
            <span>우리 주장 포인트</span>
          </div>
          <div className="cav-rows">
            {comps.map((c) => (
              <div key={c.id} className="cav-grid cav-row" data-cid={c.id}>
                <span className="cav-who">
                  <span className="cav-name"><b>{c.name}</b><span className={cx('fl-vtag', c.by !== 'manual' && 'fl-vtag--ai')}>{c.by === 'manual' ? '직접' : 'AI 웹 탐색'}</span></span>
                  <span className="cav-wiki">{[c.wiki.industry, c.wiki.size, c.wiki.hq].join(' · ')}</span>
                  {c.spaces.length > 0 && <span className="cav-space">{c.spaces.join(' · ')} 겹침</span>}
                </span>
                {DIMS.map(([k]) => {
                  const a = aggregate(c, k);
                  return <span key={k} className="cav-dim" data-dim={k}><Chip v={a.v} /><span className="cav-n">{a.n}</span></span>;
                })}
                <span className="cav-claims">
                  {c.claims.slice(0, 2).map((x, i) => (
                    <span key={`${i}-${x.axis}`} className="cav-claim"><span className="cav-axis">{x.axis}</span><span className="cav-ct">{claimText(x)}</span></span>
                  ))}
                  {!c.claims.length && <span className="cav-none">적은 주장이 없어요</span>}
                </span>
              </div>
            ))}
          </div>
        </div>
        <span className="fl-vnote">판정은 우리 제품 기준 · 경쟁사마다 비교 쌍의 판정을 모은 것 · 수치와 견적은 원문 · 사내 자료로 확인</span>
      </div>
    </FlowContentView>
  );
}
