/**
 * MI_View — 저장한 Market Intelligence 보기(보드 webapp1 View content=mi · MI_View). 저장 뒤 · 목록 · 작업 내역 · 허브에서 열면 이 화면이다.
 * 검색 조건 띠(h44: 기간 · 출처 칩 | 검색어 줄) → 시장 · 고객사 · 사용자 세 칸(1fr × 3 · gap 12 · 담은 정보만) → 아래 안내 한 줄. 후속 작업 없음.
 * 값은 MI 문서에서 그린다. 저장한 MI 를 고치는 중(편집 화면에서 다시 검색 · 정제 중)이면 문서에는 아직 저장 안 한 값이 있으므로
 * 마지막으로 저장한 판(허브 flow.json stages.mi — :finish 가 문서에서 만든 그대로)을 보여 준다.
 */
import { useState } from 'react';
import { FlowContentView, useFlow, whenText } from '@/shell';
import { Skeleton } from '@/ui';
import { GROUPS, itemsOf, qsOf, type MFDoc, type MFFilters, type MFItem, type MFSource } from './api';
import { OriginDialog, srcLine } from './RefineStep';

/** 보기에 그리는 판 하나(문서 또는 허브 stages.mi 에서) */
interface Saved {
  ver: number;
  savedAt: string | null;
  queries: Record<'market' | 'customer' | 'user', string[]>;
  filters: Pick<MFFilters, 'period' | 'sourceTypes'>;
  counts: { found: number; kept: number; numberCheck: number };
  items: MFItem[];
}

interface StageMi {
  ref?: string; ver?: number;
  queries?: Partial<Record<'market' | 'customer' | 'user', string[]>>;
  filters?: { period?: MFFilters['period']; sourceTypes?: string[] };
  counts?: { found?: number; kept?: number; numberCheck?: number };
  items?: Array<{ id: string; group: MFItem['group']; summary: string; source: MFSource; addedIn?: string | null; numberCheck?: MFItem['numberCheck'] }>;
}

/** 문서 그대로(저장 직후 · 고치는 중이 아님) */
function fromDoc(d: MFDoc): Saved {
  const qs = qsOf(d);
  const on = (g: keyof typeof qs) => qs[g].filter((q) => q.on !== false && q.text.trim()).map((q) => q.text);
  return {
    ver: d.ver ?? 1, savedAt: d.updated_at,
    queries: { market: on('market'), customer: on('customer'), user: on('user') },
    filters: { period: d.filters?.period ?? '최근 1년', sourceTypes: d.filters?.sourceTypes ?? [] },
    counts: { found: d.counts.found, kept: d.counts.kept, numberCheck: d.counts.numberCheck },
    items: itemsOf(d).filter((x) => x.kept),
  };
}

/** 마지막으로 저장한 판(허브 stages.mi) — 문서에 같은 id 의 줄이 있으면 그것으로 「원문」(검색 결과 글)을 연다 */
function fromStage(st: StageMi, d: MFDoc, savedAt: string | null): Saved {
  const byId = new Map(itemsOf(d).map((x) => [x.id, x]));
  return {
    ver: st.ver ?? d.ver ?? 1, savedAt,
    queries: { market: st.queries?.market ?? [], customer: st.queries?.customer ?? [], user: st.queries?.user ?? [] },
    filters: { period: st.filters?.period ?? '최근 1년', sourceTypes: st.filters?.sourceTypes ?? [] },
    counts: { found: st.counts?.found ?? 0, kept: st.counts?.kept ?? 0, numberCheck: st.counts?.numberCheck ?? 0 },
    items: (st.items ?? []).map((x) => {
      const it = byId.get(x.id);
      return { ...(it ?? { summary_orig: x.summary, addedIn: x.addedIn ?? '', edited: false }), id: x.id, group: x.group, summary: x.summary,
        source: x.source, kept: true, numberCheck: x.numberCheck ?? null } as MFItem;
    }),
  };
}

/** 검색어 줄(보드: 시장 3 · 고객사 3 · 사용자 3 · <첫 검색어> 외) */
function queryLine(qs: Saved['queries']) {
  const all = GROUPS.flatMap((g) => qs[g.key]);
  if (!all.length) return '—';
  return [...GROUPS.map((g) => `${g.label} ${qs[g.key].length}`), all.length > 1 ? `${all[0]} 외` : all[0]].join(' · ');
}

export function MiView({ doc }: { doc: MFDoc }) {
  const hub = useFlow(doc.sb_id);
  const [orig, setOrig] = useState<MFItem | null>(null);
  const st = (hub.data?.stages as Record<string, unknown> | undefined)?.mi as StageMi | undefined;
  const revising = doc.phase !== 'done' && !!st && st.ref === doc.code;
  const savedAt = revising
    ? [...(hub.data?.history ?? [])].reverse().find((h) => h.key === 'mi' && h.ref === doc.code && (st!.ver == null || h.ver === st!.ver))?.at ?? null
    : null;
  // 고치는 중인데 허브를 아직 못 읽었으면 저장 안 한 값이 잠깐 보이지 않게 기다린다
  if (doc.phase !== 'done' && hub.isLoading) return <div className="wm-page"><Skeleton h={520} r={16} /></div>;
  const v = revising ? fromStage(st!, doc, savedAt) : fromDoc(doc);
  const code = doc.code ?? 'MI';
  const chips = [v.filters.period, ...(v.filters.sourceTypes ?? [])];
  return (
    <FlowContentView stageKey="mi" sbIds={[doc.sb_id]} title={doc.title || 'MI'} refVer={`${code} v${v.ver}`}
      meta={[v.savedAt && `${whenText(v.savedAt)} 저장`, `담은 정보 ${v.counts.kept} (찾은 ${v.counts.found})`, `수치 원문 확인 ${v.counts.numberCheck}`]}>
      <div className="miv">
        <div className="fl-vstrip miv-strip" data-testid="miv-strip">
          <span className="miv-k">검색 조건</span>
          {chips.map((c) => <span key={c} className="miv-chip">{c}</span>)}
          <span className="miv-sep" aria-hidden />
          <span className="miv-k">검색어</span>
          <span className="miv-qline" title={GROUPS.map((g) => `${g.label}: ${v.queries[g.key].join(', ')}`).join('\n')}>{queryLine(v.queries)}</span>
        </div>
        <div className="miv-cols">
          {GROUPS.map((g) => {
            const rows = v.items.filter((x) => x.group === g.label);
            return (
              <section key={g.key} className="fl-vcard miv-col" data-group={g.key} aria-label={`${g.label} 담은 정보`}>
                <div className="miv-colhead"><h2 className="miv-colh">{g.label}</h2><span className="miv-coln">{rows.length}</span></div>
                <div className="miv-list">
                  {rows.map((it) => (
                    <div key={it.id} className="miv-it" data-item={it.id}>
                      <span className="miv-it__t">{it.summary}</span>
                      <span className="miv-it__meta">
                        <span className="fl-vtag">{it.source.type}</span>
                        {srcLine(it) && <span className="miv-it__src">{srcLine(it)}</span>}
                        {it.numberCheck && <span className="fl-vtag fl-vtag--warn" title={(it.numberCheck.values ?? []).join(' · ') || undefined}>수치 원문 확인</span>}
                        {it.source.url
                          ? <a className="miv-orig" href={it.source.url} target="_blank" rel="noreferrer noopener">원문</a>
                          : <button type="button" className="miv-orig" onClick={() => setOrig(it)}>원문</button>}
                      </span>
                    </div>
                  ))}
                  {!rows.length && <span className="miv-empty">담은 정보가 없어요</span>}
                </div>
              </section>
            );
          })}
        </div>
        <span className="fl-vnote">문장은 원문을 줄여 쓴 것이에요 · 수치는 원문에서 확인해요</span>
      </div>
      <OriginDialog item={orig} result={orig ? (doc.results ?? []).find((r) => r.id === orig.result_id) ?? null : null} onClose={() => setOrig(null)} />
    </FlowContentView>
  );
}
