/**
 * MI 최종본 본문(보드 webapp1 v62 View content=mi · MI_View · MI_Draft) — 칸은 보드 인라인 px 그대로(miview.css).
 *   검색 조건 줄(h44 · 기간 · 출처 칩 | 검색어 「시장 n · 고객사 n · 사용자 n · <첫 시장 검색어> 외」)
 *   → 시장 · 고객사 · 사용자 3열(머리 44 · 담은 정보만: 요약 13.5/600 · 출처 종류 · 이름 · 날짜 · 수치 원문 확인 · 원문) → 아래 한 줄 안내.
 *   아직 마치지 않은 단계의 칸은 StepSlot(② 검색 — 작은 칸 / ③ 정제 — 큰 칸).
 * 요소의 data 속성은 단계 팝업(MI2 · MI3)과 겹치지 않게 data-v… 로 둔다(팝업 뒤 최종본도 DOM 에 있다).
 */
import { useState } from 'react';
import { StepSlot, type DetailStatus } from '@/shell';
import { cx } from '@/ui';
import { GROUPS, itemsOf, nOn, qsOf, type MFDoc, type MFItem } from './api';
import { OriginDialog, srcLine } from './RefineStep';
import './miview.css';

const STEP = ['Storyboard', '검색', '정제'] as const;

/** 저장(완료)한 MI 인가 — 고치는 중(editing)이어도 한 번 저장했으면 저장된 것(서버 is_saved 와 같다) */
export const miSaved = (d: MFDoc | undefined) => !!d && (d.status === 'done' || d.ver != null);

/** 마친 단계 수 — 1(Storyboard) · 2(웹 검색을 마쳐 찾은 정보가 있다) · 3(저장) */
export function miDone(d: MFDoc): number {
  if (miSaved(d)) return 3;
  return d.phase === 'refine' || itemsOf(d).length > 0 ? 2 : 1;
}

/** 검색어 줄(보드 View mi.queryLine) — 켠 검색어만 센다 */
function queryLine(d: MFDoc) {
  const qs = qsOf(d);
  const first = [...qs.market, ...qs.customer, ...qs.user].find((q) => q.on !== false && q.text.trim());
  return GROUPS.map((g) => `${g.label} ${nOn(qs[g.key])}`).join(' · ') + (first ? ` · ${first.text} 외` : '');
}

export function MiViewBody({ d, done, status, onStep }: { d: MFDoc; done: number; status: DetailStatus; onStep: (k: number) => void }) {
  const [orig, setOrig] = useState<MFItem | null>(null);
  const qOn = done >= 2;
  const colOn = done >= 3;
  const kept = itemsOf(d).filter((x) => x.kept);
  const chips = [d.filters?.period ?? '최근 1년', ...(d.filters?.sourceTypes ?? [])];
  return (
    <div className="miv">
      {qOn ? (
        <div className="miv-bar" data-vbar>
          <span className="miv-bar__k">검색 조건</span>
          {chips.map((c) => <span key={c} className="miv-chip">{c}</span>)}
          <span className="miv-bar__sep" aria-hidden />
          <span className="miv-bar__k">검색어</span>
          <span className="miv-bar__q" title={queryLine(d)}>{queryLine(d)}</span>
        </div>
      ) : <StepSlot n={2} label={STEP[1]} what="Storyboard를 읽고 만든 검색어 · 검색 조건" next={done === 1} cta={status === 'draft'} onOpen={() => onStep(2)} />}
      {colOn ? (
        <>
          <div className="miv-cols">
            {GROUPS.map((g) => {
              const rows = kept.filter((x) => x.group === g.label);
              return (
                <div key={g.key} className="miv-col" data-vcol={g.key}>
                  <div className="miv-col__head"><span className="miv-col__t">{g.label}</span><span className="miv-col__n">{rows.length}</span></div>
                  <div className="miv-col__list">
                    {rows.map((it) => (
                      <div key={it.id} className="miv-item" data-vitem={it.id}>
                        <span className="miv-item__t">{it.summary}</span>
                        <span className="miv-item__meta">
                          <span className="fl-vtag fl-vtag--man">{it.source.type}</span>
                          {srcLine(it) && <span className="miv-item__src" title={srcLine(it)}>{srcLine(it)}</span>}
                          {it.numberCheck && <span className="fl-vtag fl-vtag--warn" title={(it.numberCheck.values ?? []).join(' · ') || undefined}>수치 원문 확인</span>}
                          {it.source.url
                            ? <a className="miv-item__orig" href={it.source.url} target="_blank" rel="noreferrer noopener">원문</a>
                            : <button type="button" className="miv-item__orig" onClick={() => setOrig(it)} aria-label={`원문 · ${it.summary}`}>원문</button>}
                        </span>
                      </div>
                    ))}
                    {!rows.length && <span className="miv-col__none">담은 정보가 없어요</span>}
                  </div>
                </div>
              );
            })}
          </div>
          <span className="fl-vfoot miv-foot">문장은 원문을 줄여 쓴 것이에요 · 수치는 원문에서 확인해요</span>
        </>
      ) : <StepSlot n={3} label={STEP[2]} what="시장 · 고객사 · 사용자별로 담은 정보" next={done === 2} cta={status === 'draft'} onOpen={() => onStep(3)} big />}
      <OriginDialog item={orig} result={orig ? (d.results ?? []).find((r) => r.id === orig.result_id) ?? null : null} onClose={() => setOrig(null)} />
    </div>
  );
}
