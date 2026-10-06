/** MIR — 에이전트 라우팅 규칙(읽기 전용) `/mi/rules` · MI2A `판단 규칙` · MI1Q `언제 묻는지 보기` 에서 오른쪽 시트로 (§4.3) */
import { useRef } from 'react';
import { useNavigate } from 'react-router';
import { CloseButton, Skeleton, useEscape, useFocusTrap } from '@/ui';
import { useShellPage } from '@/shell';
import { useRules, type Mode, type RoutingRules } from '../api';
import { ErrorBand, Ic, ModeChip, P, SECTION } from '../parts';

/** 규칙 본문 — 서버 설정(GET /v1/routing-rules)을 그대로 그린다(AC-MI-01) */
export function RulesView({ data }: { data: RoutingRules }) {
  const band = (data.layout as { band?: Array<{ code: string; name: string; ind: string; has_industry: boolean; rules: string[][] }>; columns?: string[]; no?: string; title?: string; sub?: string });
  const asks = data.asks as { title?: string; items?: string[]; footer?: string };
  return (
    <div className="mi-rules" data-testid="mi-rules">
      <div className="mi-row" style={{ alignItems: 'flex-end', justifyContent: 'space-between', gap: 24, flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 5, minWidth: 0 }}>
          <span className="mi-rules__eyebrow">{data.header.eyebrow}</span>
          <h1 className="mi-rules__title">{data.header.title}</h1>
          <p className="mi-rules__desc">{data.header.desc}</p>
        </div>
        <div className="mi-rules__legend">
          {data.modes.map((m) => <span key={m.key}><ModeChip mode={m.key as Mode}>{m.label}</ModeChip>{m.desc}</span>)}
        </div>
      </div>
      <div className="mi-rules__stages">
        {data.stages.map((s, i) => (
          <div key={s.no} className="mi-rstage">
            <div className="mi-rstage__head">
              <span className="mi-rno">{s.no}</span><span className="mi-rstage__title">{s.title}</span><span className="mi-grow" />
              {i < data.stages.length - 1 && <Ic d={P.arrow} size={16} />}
            </div>
            <span className="mi-rstage__sub">{s.sub}</span>
            {s.rules.map((r) => (
              <div key={r.c} className="mi-rrule">
                <div className="mi-grow" style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                  <span className="mi-rrule__c">{r.c}</span><span className="mi-rrule__o">→ {r.o}</span>
                </div>
                <ModeChip mode={r.mode as Mode}>{r.mode_label}</ModeChip>
              </div>
            ))}
          </div>
        ))}
      </div>
      <div className="mi-rband">
        <div className="mi-row" style={{ minHeight: 26 }}>
          <span className="mi-rno">{band.no ?? '5'}</span>
          <span className="mi-rstage__title">{band.title}</span>
          <span className="mi-note mi-ell">{band.sub}</span>
        </div>
        <div className="mi-rband__row mi-rband__row--head">{(band.columns ?? []).map((c) => <span key={c}>{c}</span>)}</div>
        {(band.band ?? []).map((b) => (
          <div key={b.code} className="mi-rband__row">
            <span><span className="mi-rband__code">{b.code}</span><span className="mi-rband__name">{b.name}</span></span>
            <span className={b.has_industry ? 'mi-rband__ind' : 'mi-rband__ind mi-rband__ind--none'}>{b.ind}</span>
            <div className="mi-rband__rules">{b.rules.map(([c, t]) => <span key={t} className="mi-rband__chip">{c}<b>{t}</b></span>)}</div>
          </div>
        ))}
      </div>
      <div className="mi-rules__bottom">
        <div className="mi-rstage">
          <div className="mi-rstage__head">
            <span className="mi-rno">{data.gaps.no}</span><span className="mi-rstage__title">{data.gaps.title}</span>
            <span className="mi-note mi-ell">{data.gaps.sub}</span>
          </div>
          <div className="mi-rgaps">
            {data.gaps.rules.map((r) => (
              <div key={r.c} className="mi-rrule">
                <div className="mi-grow" style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                  <span className="mi-rrule__c">{r.c}</span><span className="mi-rrule__o">→ {r.o}</span>
                </div>
                <ModeChip mode={r.mode as Mode}>{r.mode_label}</ModeChip>
              </div>
            ))}
          </div>
        </div>
        <div className="mi-rasks">
          <span className="mi-rasks__title">{asks.title ?? '사람에게 묻는 경우는 이 넷뿐'}</span>
          {(asks.items ?? []).map((t, i) => <div key={t} className="mi-rask"><b>{i + 1}</b><span>{t}</span></div>)}
          <span className="mi-rasks__foot">{asks.footer ?? '답이 없으면 추천값으로 진행 · 하나를 바꾸면 그 뒤 단계만 다시 돕니다'}</span>
        </div>
      </div>
    </div>
  );
}

function RulesBody() {
  const r = useRules();
  if (r.isError) return <div style={{ padding: 40 }}><ErrorBand onRetry={() => void r.refetch()} /></div>;
  if (!r.data) return <div style={{ padding: 40, display: 'flex', flexDirection: 'column', gap: 12 }}><Skeleton w="40%" h={26} /><Skeleton w="70%" h={14} /><Skeleton h={240} /></div>;
  return <RulesView data={r.data} />;
}

/** 오른쪽 시트로 연다(닫으면 원래 화면) */
export function RulesSheet({ open, onClose }: { open: boolean; onClose: () => void }) {
  const ref = useRef<HTMLDivElement>(null);
  useFocusTrap(ref, open);
  useEscape(onClose, open);
  if (!open) return null;
  return (
    <>
      <div className="mi-sheet-scrim" onClick={onClose} aria-hidden="true" />
      <div className="mi-rsheet" role="dialog" aria-modal="true" aria-label="에이전트 라우팅 규칙" ref={ref}>
        <div className="mi-rsheet__close"><CloseButton label="닫기" onClick={onClose} /></div>
        <RulesBody />
      </div>
    </>
  );
}

/** `/mi/rules` — 바로 들어와도 같은 시트(닫으면 뒤로) */
export function RulesPage() {
  useShellPage({ section: SECTION, title: '판단 규칙', hasTask: false, sidebarGroup: 'mi' });
  const nav = useNavigate();
  return <RulesSheet open onClose={() => (window.history.length > 1 ? nav(-1) : nav('/mi'))} />;
}
