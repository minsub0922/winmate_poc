/** MI3 탭 본문 — 시장조사 · 고객사 · 비즈니스 · 사용자 · 경쟁사 → 삼성 강점(§4.7 탭 내용). MI3 · MI3R · 공유 화면이 함께 쓴다. */
import type { ReactNode } from 'react';
import { cx } from '@/ui';
import type { ClaimRef, ResultView } from './api';
import { ClaimText, Cites, CompareGrid, Strengths } from './parts';

type Market = NonNullable<ResultView['market']>;
type Customer = NonNullable<ResultView['customer']>;
type User = NonNullable<ResultView['user']>;
type Comp = NonNullable<ResultView['competitor']>;

const fmt = (v: number | null | undefined) => (v === null || v === undefined ? '[00]' : v.toLocaleString('ko-KR', { maximumFractionDigits: 1 }));

export function Block({ title, sub, children }: { title: ReactNode; sub?: ReactNode; children: ReactNode }) {
  return (
    <div className="mi-block">
      <div className="mi-block__title">{title}{sub && <small>{sub}</small>}</div>
      {children}
    </div>
  );
}

function Claims({ items, onCite, hl, sel }: { items: Array<ClaimRef | null | undefined>; onCite?: (id: string) => void; hl?: boolean; sel?: string | null }) {
  const list = items.filter(Boolean) as ClaimRef[];
  if (!list.length) return <span className="mi-claim mi-cmp__cell--ph">[확인 필요]</span>;
  return (
    <ul style={{ margin: 0, paddingLeft: 18, display: 'flex', flexDirection: 'column', gap: 4 }}>
      {list.map((c) => <li key={c.id}><ClaimText claim={c} onCite={onCite} hl={hl && c.inferred} sel={sel} /></li>)}
    </ul>
  );
}

export function MarketTab({ m, onCite, hl, sel }: { m: Market; onCite?: (id: string) => void; hl?: boolean; sel?: string | null }) {
  const vals = m.size_series.map((p) => p.value ?? 0);
  const max = Math.max(1, ...vals);
  return (
    <>
      <Block title={`시장 규모${m.size_label ? ` · ${m.size_label}` : ''}`} sub={m.size_unit ? `단위 ${m.size_unit}` : undefined}>
        {m.size_series.length > 0 ? (
          <>
            <div className="mi-bars" aria-label="연도별 시장 규모">
              {m.size_series.map((p) => (
                <div key={p.year} className="mi-bars__col">
                  <span className="mi-bars__v">{fmt(p.value)}{p.unit}</span>
                  <div className={cx('mi-bars__bar', p.value === null || p.value === undefined ? 'mi-bars__bar--ph' : '')}
                    style={{ height: `${p.value ? Math.max(6, (p.value / max) * 100) : 30}%` }} />
                </div>
              ))}
            </div>
            <div className="mi-bars__x">{m.size_series.map((p) => <span key={p.year}>{p.year}</span>)}</div>
            <Claims items={m.size_series.map((p) => p.claim)} onCite={onCite} sel={sel} />
          </>
        ) : <span className="mi-claim mi-cmp__cell--ph">연도별 시장 규모 [00]{m.size_unit}</span>}
      </Block>
      {m.cagr && (
        <Block title="성장률" sub={m.cagr.period || undefined}>
          <ClaimText claim={m.cagr.claim} onCite={onCite} sel={sel} />
        </Block>
      )}
      {m.trends.length > 0 && (
        <Block title="도입 트렌드">
          {m.trends.map((t, i) => (
            <div key={i} className="mi-trend">
              <div className="mi-trend__head">{t.title}{t.when && <small>{t.when}</small>}</div>
              <ClaimText claim={t.claim} onCite={onCite} sel={sel} />
              {t.implication && <span className="mi-trend__so">{t.implication}</span>}
            </div>
          ))}
        </Block>
      )}
      {m.regulations.length > 0 && (
        <Block title="규제">
          <Claims items={m.regulations.map((r) => r.claim)} onCite={onCite} sel={sel} />
        </Block>
      )}
      {m.kb_trend && (
        <Block title="사내 사례 DB 도입 경향">
          <ClaimText claim={m.kb_trend} onCite={onCite} sel={sel} />
        </Block>
      )}
    </>
  );
}

export function CustomerTab({ c, onCite, hl, sel }: { c: Customer; onCite?: (id: string) => void; hl?: boolean; sel?: string | null }) {
  return (
    <>
      {c.reduced && <div className="mi-band mi-band--muted">고객 공개 자료가 적어 한 줄 요약 중심으로 정리했어요.</div>}
      <Block title="한 줄 요약"><ClaimText claim={c.summary} onCite={onCite} hl={hl} sel={sel} /></Block>
      {c.strategy.length > 0 && <Block title="전략"><Claims items={c.strategy} onCite={onCite} hl={hl} sel={sel} /></Block>}
      {c.expansion.length > 0 && <Block title="투자 · 확장 계획"><Claims items={c.expansion} onCite={onCite} hl={hl} sel={sel} /></Block>}
      {c.structure.length > 0 && (
        <Block title="운영 구조">
          <div className="mi-kv">
            {c.structure.map((s, i) => (
              <div key={i} style={{ display: 'contents' }}>
                <div className="mi-kv__k">{s.label}</div>
                <div><span className="mi-num" style={{ fontWeight: 700 }}>{s.value || '[확인 필요]'}</span>
                  {s.claim && <Cites ns={s.claim.ns ?? []} claimId={s.claim.id} onClick={onCite} on={sel === s.claim.id} />}</div>
              </div>
            ))}
          </div>
        </Block>
      )}
      {c.ops_challenges.length > 0 && (
        <Block title="운영 단계별 과제">
          <div className="mi-kv">
            {c.ops_challenges.map((o, i) => (
              <div key={i} style={{ display: 'contents' }}>
                <div className="mi-kv__k">{o.stage}</div>
                <div><ClaimText claim={o.claim} onCite={onCite} hl={hl} sel={sel} /></div>
              </div>
            ))}
          </div>
        </Block>
      )}
    </>
  );
}

export function UserTab({ u, onCite, hl, sel }: { u: User; onCite?: (id: string) => void; hl?: boolean; sel?: string | null }) {
  return (
    <>
      {u.personas.length > 0 && (
        <Block title={`페르소나 ${u.personas.length}`}>
          <div className="mi-personas">
            {u.personas.slice(0, 3).map((p, i) => (
              <div key={i} className="mi-persona">
                <b>{p.role}</b>
                {p.goal && <span><i>목표</i>{p.goal}</span>}
                {p.pain && <span><i>불편</i>{p.pain}</span>}
                {p.context && <span><i>맥락</i>{p.context}</span>}
                {p.claims[0] && <span><Cites ns={p.claims.flatMap((c) => c.ns ?? [])} claimId={p.claims[0].id} onClick={onCite} on={p.claims.some((c) => c.id === sel)} /></span>}
              </div>
            ))}
          </div>
        </Block>
      )}
      {u.journey.length > 0 && (
        <Block title="여정" sub="단계 → 접점 → 불편 → 기회">
          <div className="mi-journey">
            {u.journey.map((j, i) => (
              <div key={i} className="mi-journey__step">
                <b>{j.stage}</b>
                {j.touchpoint && <span><i>접점</i>{j.touchpoint}</span>}
                {j.pain && <span><i>불편</i>{j.pain}</span>}
                {j.opportunity && <span><i>기회</i>{j.opportunity}</span>}
                {j.claims[0] && <span><Cites ns={j.claims.flatMap((c) => c.ns ?? [])} claimId={j.claims[0].id} onClick={onCite} on={j.claims.some((c) => c.id === sel)} /></span>}
              </div>
            ))}
          </div>
        </Block>
      )}
      {u.composition.length > 0 && (
        <Block title="구성 비율">
          <div className="mi-kv">
            {u.composition.map((c, i) => (
              <div key={i} style={{ display: 'contents' }}>
                <div className="mi-kv__k">{c.label}</div>
                <div><span className="mi-num" style={{ fontWeight: 700 }}>{fmt(c.value)}{c.unit}</span>
                  {c.claim && <Cites ns={c.claim.ns ?? []} claimId={c.claim.id} onClick={onCite} on={sel === c.claim.id} />}</div>
              </div>
            ))}
          </div>
        </Block>
      )}
      {!u.personas.length && !u.journey.length && !u.composition.length && <span className="mi-claim mi-cmp__cell--ph">[확인 필요]</span>}
    </>
  );
}

export function CompetitorTab({ c, onCite, sel, tableExtra }: { c: Comp; onCite?: (id: string) => void; sel?: string | null; tableExtra?: ReactNode }) {
  return (
    <>
      {c.table ? <CompareGrid table={c.table} onCite={onCite} selected={sel} extraRows={tableExtra} /> : <span className="mi-claim mi-cmp__cell--ph">비교표 [확인 필요]</span>}
      <Strengths items={c.strengths} onCite={onCite} />
    </>
  );
}

/** 탭 하나 본문 */
export function TabBody({ r, area, onCite, hl, sel }: { r: ResultView; area: string; onCite?: (id: string) => void; hl?: boolean; sel?: string | null }) {
  if (area === 'market' && r.market) return <MarketTab m={r.market} onCite={onCite} hl={hl} sel={sel} />;
  if (area === 'customer' && r.customer) return <CustomerTab c={r.customer} onCite={onCite} hl={hl} sel={sel} />;
  if (area === 'user' && r.user) return <UserTab u={r.user} onCite={onCite} hl={hl} sel={sel} />;
  if (area === 'competitor' && r.competitor) return <CompetitorTab c={r.competitor} onCite={onCite} sel={sel} />;
  return null;
}
