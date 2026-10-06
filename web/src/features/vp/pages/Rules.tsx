/**
 * VPR — 에이전트 라우팅 규칙(읽기 전용 시트, `/vp/rules`) — GET /v1/routing-rules 를 그대로 그린다.
 */
import { Skeleton, ErrorState } from '@/ui';
import { errText, useRules } from '../api';
import { ModeChip } from '../parts';

export function RulesSheet() {
  const r = useRules();
  if (r.isLoading) return <div style={{ padding: 24 }}><Skeleton h={300} /></div>;
  if (r.isError || !r.data) return <div style={{ padding: 24 }}><ErrorState message={errText(r.error)} onRetry={() => r.refetch()} /></div>;
  const d = r.data;
  const packs = d.packs as { title: string; sub: string; ready: number; total: number; cells: Array<{ code: string; name: string; status: string }>; line: string };
  return (
    <div className="vp-rules" data-testid="vp-rules">
      <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', gap: 24 }}>
        <div>
          <div className="vp-rules__eyebrow">{d.eyebrow}</div>
          <h2 className="vp-rules__title">{d.title}</h2>
        </div>
        <div className="vp-rules__legend">
          {d.legend.map((l) => <span key={l.mode} style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}><ModeChip mode={l.mode} />{l.desc}</span>)}
        </div>
      </div>
      <div className="vp-rules__stages">
        {d.stages.map((s) => (
          <div key={s.no} className="vp-rstage">
            <div className="vp-rstage__head"><span className="vp-rno">{s.no}</span><span className="vp-rstage__t">{s.title}</span></div>
            <span className="vp-rstage__sub">{s.sub}</span>
            {s.rules.map((x, i) => (
              <div key={i} className="vp-rrule">
                <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minWidth: 0 }}>
                  <span className="vp-rrule__c">{x.c}</span>
                  <span className="vp-rrule__o">→ {x.o}</span>
                </div>
                <ModeChip mode={x.mode} small />
              </div>
            ))}
          </div>
        ))}
      </div>
      <div className="vp-rband">
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, minHeight: 26 }}>
          <span className="vp-rno">5</span><span className="vp-rstage__t">{d.band_title}</span>
          <span className="vp-card__sub">{d.band_sub}</span>
        </div>
        <div className="vp-rband__row vp-rband__row--head">{d.band_head.map((h) => <span key={h}>{h}</span>)}</div>
        {d.band.map((b, i) => (
          <div key={i} className="vp-rband__row">
            <span style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}><span className="vp-num" style={{ color: 'var(--wm-brand)', fontSize: 12 }}>{b.code}</span><span style={{ fontSize: 12.5, fontWeight: 700 }}>{b.name}</span></span>
            <span className="vp-rband__ind">{b.ind}</span>
            <div className="vp-rband__rules">
              {b.rules.map((x, j) => (
                <span key={j} className="vp-rband__rule">{x.c}<span className={/^[A-Z]{2}-|^VP-/.test(x.t) ? 'vp-tpl' : 'vp-tpl vp-tpl--text'}>{x.t}</span></span>
              ))}
            </div>
          </div>
        ))}
        <div className="vp-rpacks">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 2, flexShrink: 0 }}>
            <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--wm-brand)' }}>{packs.title}</span>
            <span style={{ fontSize: 11.5, color: 'var(--wm-text-muted)' }}>{packs.sub}</span>
          </div>
          <div className="vp-rpacks__grid">
            {packs.cells.map((c) => <span key={c.code} title={c.name} className={c.status === 'ready' ? 'vp-rpacks__cell vp-rpacks__cell--ready' : 'vp-rpacks__cell'} />)}
          </div>
          <span style={{ fontSize: 12, lineHeight: 1.5 }}>{packs.line}</span>
        </div>
      </div>
      <div className="vp-rbottom">
        <div className="vp-rgaps">
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span className="vp-rno">6</span><span className="vp-rstage__t">{d.gaps_title}</span><span className="vp-card__sub">{d.gaps_sub}</span>
          </div>
          <div className="vp-rgaps__grid">
            {d.gaps.map((g, i) => (
              <div key={i} className="vp-rrule">
                <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minWidth: 0 }}>
                  <span className="vp-rrule__c">{g.c}</span>
                  <span className="vp-rrule__o">→ {g.o}</span>
                </div>
                <ModeChip mode={g.mode} small />
              </div>
            ))}
          </div>
        </div>
        <div className="vp-rasks">
          <span className="vp-rasks__t">{d.asks_title}</span>
          {d.asks.map((a) => <div key={String(a.n)} className="vp-rasks__row"><b>{String(a.n)}</b><span>{String(a.t)}</span></div>)}
        </div>
      </div>
    </div>
  );
}
