/**
 * VP_View — 저장한 가치 · 고객의 니즈 보기(보드 webapp1 View content=vp · VP_View). 저장 뒤 · 목록 · 작업 내역에서 열면 이 화면이다.
 * 띠(h44) 「DSS-xx에서 n개를 골랐어요 · 고르지 않은 n — …」 + 흰 판 하나에 고른 제품 · 솔루션마다 줄(210 | 1fr · gap 18 · 16 20).
 * 수락한 가치만(점선 AI 추천은 빠진다 — flow.json stages.vp 와 같다). 니즈가 비면 주황 점선 줄. 후속 작업 없음.
 */
import { FlowContentView, useFlow, whenText } from '@/shell';
import { cx } from '@/ui';
import type { VMDoc, VMItem, VMValue } from './api';

/** 화면에 보이는 가치 = 수락한 것 · 니즈도 수락한 것만(AI 추론 점선은 비어 있음으로) */
function accepted(it: VMItem) {
  return it.values.filter((v) => v.by !== 'ai-pending').map((v) => ({ ...v, need: v.need && v.need.by !== 'ai-pending' ? v.need : null }));
}

/** 허브에서 — 저장 시각(그 VP 코드의 마지막 반영 · 없으면 문서 고친 시각) · 가져온 DSS 코드(맵에 없을 때) */
function useHub(doc: VMDoc) {
  const q = useFlow(doc.sb_id ?? null);
  const at = (q.data?.history ?? []).filter((h) => h.key === 'vp' && h.ref === (doc.code ?? doc.id)).map((h) => h.at).sort().at(-1);
  const dss = (q.data?.stages as { dss?: { ref?: string } } | undefined)?.dss?.ref;
  return { savedAt: at ?? doc.updated_at, dssRef: doc.dss_ref ?? dss ?? null };
}

/** 띠 — 어디서 몇 개를 골랐는지 · 고르지 않은 것(보드) + DSS 밖에서 더함 · DSS 에서 빠짐(있을 때만) */
function stripText(doc: VMDoc, dssRef: string | null) {
  const picked = new Set(doc.items.map((i) => i.name));
  const fromDss = doc.items.filter((i) => i.from_dss).length;
  const excluded = doc.candidates.filter((c) => !picked.has(c.name)).map((c) => c.name);
  const outside = doc.items.filter((i) => !i.from_dss && i.dss_status !== 'removed').map((i) => i.name);
  const dropped = doc.items.filter((i) => i.dss_status === 'removed').map((i) => i.name);
  const src = dssRef ?? (doc.sb_id ? 'DSS' : '후보');
  const out = [
    excluded.length ? `· 고르지 않은 ${excluded.length} — ${excluded.join(' · ')}` : '',
    outside.length ? `· DSS 밖에서 더함 ${outside.length} — ${outside.join(' · ')}` : '',
    dropped.length ? `· DSS에서 빠짐 ${dropped.length} — ${dropped.join(' · ')}` : '',
  ].filter(Boolean).join(' ');
  return { from: `${src}에서 ${fromDss}개를 골랐어요`, out };
}

function ValueLine({ v }: { v: VMValue }) {
  const need = v.need;
  return (
    <span className="vpv-val" data-value={v.id}>
      <span className="vpv-vtop">
        <span className="vpv-space">{v.space}</span>
        <span className="vpv-msg">{v.message}</span>
        {v.req && <span className="vpv-req">{v.req}</span>}
      </span>
      <span className={cx('vpv-need', !need && 'vpv-need--empty')}>
        <span className="vpv-need__label">고객의 니즈</span>
        <span className="vpv-need__text">{need ? `“${need.text}”` : '비어 있어요 · 편집에서 적거나 AI 니즈 추론으로 채워요'}</span>
        {need && <span className={cx('fl-vtag', need.by !== 'manual' && 'fl-vtag--ai')}>{need.by === 'manual' ? '직접' : 'AI 추론 · 수락'}</span>}
      </span>
    </span>
  );
}

export function VpView({ doc }: { doc: VMDoc }) {
  const { savedAt, dssRef } = useHub(doc);
  const c = doc.counts;
  const s = stripText(doc, dssRef);
  return (
    <FlowContentView stageKey="vp" sbIds={doc.sb_id ? [doc.sb_id] : []} title={doc.title || 'Value Proposition'} refVer={`${doc.code ?? doc.id} v${doc.ver ?? 1}`}
      meta={[savedAt && `${whenText(savedAt)} 저장`, `제품 · 솔루션 ${c.items}`, `가치 ${c.values}`, `고객의 니즈 ${c.needs}/${c.values}`]}>
      <div className="vpv-wrap">
        <div className="fl-vstrip vpv-strip">
          <b>{s.from}</b>
          {s.out && <span>{s.out}</span>}
        </div>
        <div className="fl-vcard vpv-list">
          {doc.items.map((it) => {
            const vals = accepted(it);
            const needs = vals.filter((v) => v.need).length;
            const spaces = it.spaces.length ? it.spaces : [...new Set(vals.map((v) => v.space).filter(Boolean))];
            return (
              <div key={it.key} className="vpv-row" data-item={it.key}>
                <span className="vpv-item">
                  <span className={cx('fl-vtag', it.kind === 'solution' && 'fl-vtag--brand')}>{it.kind === 'solution' ? '솔루션' : '제품'}</span>
                  <span className="vpv-name">{it.name}</span>
                  <span className="vpv-spaces">{spaces.join(' · ') || '—'}</span>
                  <span className="vpv-count">가치 {vals.length} · 니즈 {needs}/{vals.length}</span>
                </span>
                <span className="vpv-values">
                  {vals.map((v) => <ValueLine key={v.id} v={v} />)}
                  {!vals.length && <span className="vpv-none">적은 가치가 없어요</span>}
                </span>
              </div>
            );
          })}
          {!doc.items.length && <div className="vpv-row"><span className="vpv-none">고른 제품 · 솔루션이 없어요</span></div>}
        </div>
      </div>
    </FlowContentView>
  );
}
