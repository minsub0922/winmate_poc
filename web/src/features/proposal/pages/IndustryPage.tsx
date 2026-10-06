/**
 * PR3I — 업종 레이아웃 적용(§4.13, 보드 PR3I, 3/6).
 * 감지 업종 + 근거 + 업종 바꾸기(16개 listbox, `GET …/industry?code=`로 다시 계산) · 도입사례 통계 3열.
 * 아래 카드: 계열 3행(MI · VP · 공간 시나리오) — 스위치 · 매핑 줄 · 「시트별로 바꾸기」 · 카드 A/B/C(적용 · 바꿔 쓰기 · 시트 추가 시).
 * 카드/스위치는 바로 저장(`PUT …/industry`, decided 없이) → 「적용 · 섹션 작성 시작」 = decided:true → 첫 섹션(next.route).
 * 「기본 템플릿 유지」 = keep_default · decided → PR3(보드 링크).
 */
import { useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { Icon, Thumb, cx, toast } from '@/ui';
import { putIndustry, qk, useIndustry, useProposal } from '../api/proposal';
import { errText } from '../api/http';
import type { IndustryView } from '../api/types';
import { Agent, Dock, ErrorBand, GhostButton, LoadingCard, NextButton, PrPage, Switch } from '../components/parts';
import { tplOf } from '../lib/catalog';
import { R, normalizeRoute, sectionsOf } from '../lib/routes';
import { useProposalShell } from '../lib/useProposalShell';

const BADGE: Record<string, string> = { applied: '적용', alt: '바꿔 쓰기', add: '시트 추가 시' };
const MODE_TONE: Record<string, string> = { auto: 'pr-modebadge', check: 'pr-modebadge pr-modebadge--line', ask: 'pr-modebadge pr-modebadge--warn', pinned: 'pr-modebadge pr-modebadge--line' };

function Bold({ text, word }: { text: string; word?: string | null }) {
  if (!word || !text.includes(word)) return <>{text}</>;
  const i = text.indexOf(word);
  return <>{text.slice(0, i)}<span style={{ fontWeight: 600 }}>{word}</span>{text.slice(i + word.length)}</>;
}

export function IndustryPage() {
  const { id } = useParams();
  const nav = useNavigate();
  const qc = useQueryClient();
  const pq = useProposal(id);
  const p = pq.data;
  const [code, setCode] = useState<string | null>(null);
  const iq = useIndustry(id, code);
  const [view, setView] = useState<IndustryView | null>(null);
  useEffect(() => { if (iq.data) setView(iq.data); }, [iq.data]);
  const v = view;
  const [busy, setBusy] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  useProposalShell({ p, step: 3, oneClick: { from: 'industry' } });
  useEffect(() => { if (v?.ask && !v.decided) setOpen(true); }, [v?.ask, v?.decided]);
  useEffect(() => {
    if (!open) return;
    const h = (e: MouseEvent) => { if (menuRef.current && !menuRef.current.contains(e.target as Node)) setOpen(false); };
    window.addEventListener('mousedown', h);
    return () => window.removeEventListener('mousedown', h);
  }, [open]);

  const save = async (b: Parameters<typeof putIndustry>[1], tag: string) => {
    if (!id) return null;
    setBusy(tag);
    try {
      const r = await putIndustry(id, { code: code ?? undefined, ...b });
      setView(r);
      qc.setQueryData(qk.sub(id, 'industry', code ?? null), r);
      return r;
    } catch (e) { toast(errText(e)); return null; } finally { setBusy(null); }
  };
  const firstSection = () => {
    if (!p) return R.list();
    const s = p.sections?.find((x) => x.enabled && !x.hidden);
    if (s) return normalizeRoute(s.route) ?? R.section(p.id, s.key);
    const k = sectionsOf(p.type as Parameters<typeof sectionsOf>[0])[0];
    return k ? R.section(p.id, k) : R.compose(p.id);
  };
  const apply = async () => {
    const r = await save({ decided: true }, 'apply');
    if (!r || !id) return;
    void qc.invalidateQueries({ queryKey: qk.p(id) });
    nav(normalizeRoute(r.next?.route) ?? firstSection());
  };
  const keepDefault = async () => {
    const r = await save({ keep_default: true, decided: true }, 'keep');
    if (!r || !id) return;
    void qc.invalidateQueries({ queryKey: qk.p(id) });
    nav(R.compose(id));
  };
  const toggleCard = (fam: IndustryView['families'][number], c: IndustryView['families'][number]['cards'][number]) => {
    if (c.state === 'add' || !fam.on || c.available === false) return;
    const nextState = c.state === 'applied' ? 'alt' : 'applied';
    const cards: Record<string, 'applied' | 'alt'> = { [c.code]: nextState };
    // 같은 시트 대상끼리 전환: 다른 적용 카드 중 바꿔 쓰기 관계(같은 계열의 alt ↔ applied)는 서버가 정한다
    void save({ cards }, `card:${c.code}`);
  };

  if (pq.isError) return <PrPage><ErrorBand message={errText(pq.error, '제안서를 찾을 수 없어요')} onRetry={() => void pq.refetch()} /></PrPage>;
  if (!p || (!v && !iq.isError)) return <PrPage><LoadingCard lines={5} /></PrPage>;
  if (!v) return <PrPage><ErrorBand message={errText(iq.error)} onRetry={() => void iq.refetch()} /></PrPage>;

  const d = v.detected;
  const stats = v.stats ?? {};
  const cols = [stats.needs ?? [], stats.products ?? [], stats.solutions ?? []];
  const colLabels = stats.labels?.length === 3 ? stats.labels
    : ['고객이 요구한 것', '쓰인 제품', '쓰인 솔루션'].map((t) => `${t} · 사례 ${stats.cases ?? 0}건 중`);
  const fams = v.families.filter((f) => f.available !== false);
  const headerLabel = v.header_label?.replace(/^업종 레이아웃 추천 · /, '').replace(/^ · /, '') || `시트 ${v.applied_count}장에 적용 · 3 / 6`;

  const dock = (
    <Dock testId="pr3i-dock" title="업종 레이아웃 추천" meta={<span data-testid="pr3i-header">{headerLabel}</span>}
      right={<span className="pr-legend">
        <span><i className="pr-legend__sw pr-legend__sw--on" />적용</span>
        <span><i className="pr-legend__sw" />바꿔 쓰기</span>
        <span><i className="pr-legend__sw pr-legend__sw--add" />시트 추가 시</span>
      </span>}
      hint={v.footer_note || '업종 레이아웃은 섹션 작성의 템플릿 고르기 맨 앞에도 나와요.'}
      foot={<>
        <GhostButton to={R.type(p.id)}>이전</GhostButton>
        <button type="button" className="pr-btn" onClick={() => void keepDefault()} disabled={!!busy} data-testid="pr3i-keep">기본 템플릿 유지</button>
        <NextButton onClick={() => void apply()} busy={busy === 'apply'} disabled={!!busy && busy !== 'apply' || v.can_apply === false || (v.ask === true && !code && d.mode === 'ask')}
          disabledReason={v.ask ? '업종을 먼저 골라 주세요' : undefined} testId="pr3i-apply">적용 · 섹션 작성 시작</NextButton>
      </>}>
      <div className="pr-colflex" style={{ gap: 8 }} data-testid="pr3i-families">
        {fams.length === 0 && <div className="pr-band pr-band--muted">이 업종은 아직 업종 레이아웃이 없어요. 기본 템플릿으로 작성해요.</div>}
        {fams.map((f) => (
          <div key={f.role} className="pr-famrow" data-testid={`pr3i-fam-${f.role}`}>
            <div className="pr-faminfo">
              <div className="pr-row pr-row--between" style={{ gap: 6 }}>
                <span className="pr-ell" style={{ fontSize: 12.5, fontWeight: 700 }}>{f.name}</span>
                <Switch on={f.on} label={f.switch_label} onChange={(on) => void save({ families: { [f.role]: on } }, `fam:${f.role}`)} disabled={!!busy} />
              </div>
              {f.maps.map((m, i) => <span key={i} className={cx('pr-ell', 'pr-fammap', m.strong && 'pr-fammap--strong')}>{m.text}</span>)}
              <span className="pr-grow" />
              {f.pick_route
                ? <button type="button" className="pr-link" style={{ fontSize: 11.5 }} onClick={() => nav(normalizeRoute(f.pick_route)!)}>시트별로 바꾸기<Icon name="chevronRight" size={11} strokeWidth={2.4} /></button>
                : <span className="pr-link pr-link--muted" style={{ fontSize: 11.5 }} title="섹션 작성에서 시트를 고르면 바꿀 수 있어요">시트별로 바꾸기<Icon name="chevronRight" size={11} strokeWidth={2.4} /></span>}
            </div>
            {f.cards.map((c) => (
              <button key={c.code} type="button" aria-pressed={c.state === 'applied'} className={cx('pr-indcard', `pr-indcard--${c.state}`, !f.on && 'pr-indcard--off')}
                onClick={() => toggleCard(f, c)} disabled={c.state === 'add' || !f.on || busy === `card:${c.code}`} title={c.desc ?? undefined} data-testid="pr3i-card" data-state={c.state}>
                <span className="pr-indcard__thumb">
                  <Thumb code={c.code} kind={tplOf(c.code).kind} n={3} src={c.thumb_url || undefined} />
                  <span className={cx('pr-indbadge', `pr-indbadge--${c.state}`)}>{c.state_label || BADGE[c.state]}</span>
                </span>
                <span className="pr-row" style={{ gap: 5, width: '100%', minWidth: 0 }}>
                  <span className="pr-num" style={{ fontSize: 11, fontWeight: 800, flexShrink: 0 }}>{c.code}</span>
                  <span className="pr-ell" style={{ fontSize: 11, fontWeight: 600 }}>{c.name}</span>
                </span>
              </button>
            ))}
          </div>
        ))}
      </div>
    </Dock>
  );

  return (
    <PrPage testId="pr3i" dock={dock} gap={14} tight>
      <Agent text={<Bold text={v.intro} word={d.label} />} testId="pr3i-agent">
        <div className="pr-card" style={{ padding: '12px 16px', display: 'flex', flexDirection: 'column', gap: 10 }} data-testid="pr3i-detected">
          <div className="pr-row" style={{ gap: 12, minHeight: 44 }}>
            <span className="pr-iconbox" style={{ width: 36, height: 36, borderRadius: 10 }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M5 8h12v5a5 5 0 0 1-5 5h-2a5 5 0 0 1-5-5V8z M17 9h1.5a2.5 2.5 0 0 1 0 5H17 M4 21h16" /></svg>
            </span>
            <span className="pr-colflex pr-grow" style={{ gap: 2 }}>
              <span className="pr-row" style={{ gap: 8 }}>
                <span style={{ fontSize: 15, fontWeight: 700, whiteSpace: 'nowrap' }} data-testid="pr3i-label">{d.label || '업종 미정'}</span>
                {d.mode_label && <span className={MODE_TONE[d.mode ?? 'auto'] ?? 'pr-modebadge'}>{d.mode_label}</span>}
              </span>
              <span className="pr-ell" style={{ fontSize: 12, color: 'var(--wm-text-muted)' }}>{d.evidence_label || (d.evidence?.length ? `근거 · ${d.evidence.join(' · ')}` : '')}</span>
            </span>
            <div className="pr-filter" ref={menuRef}>
              <button type="button" aria-haspopup="listbox" aria-expanded={open} onClick={() => setOpen((o) => !o)} style={{ height: 34, fontWeight: 600 }} data-testid="pr3i-change">
                업종 바꾸기 · {v.options.length}개<Icon name="chevronDown" size={12} color="var(--wm-text-muted)" strokeWidth={2.4} />
              </button>
              {open && (
                <div className="pr-menu" role="listbox" aria-label="업종" style={{ right: 0, left: 'auto', maxHeight: 320, overflowY: 'auto', minWidth: 220 }}>
                  {v.ask && <div className="pr-note" style={{ padding: '6px 10px' }}>업종이 두 갈래로 보여요. 하나를 골라 주세요.</div>}
                  {v.options.map((o) => (
                    <button key={o.code} type="button" role="option" aria-selected={(code ?? d.code) === o.code}
                      onClick={() => { setOpen(false); setCode(o.code); }}>
                      <span className="pr-num" style={{ fontWeight: 800, fontSize: 11, color: 'var(--wm-text-subtle)', width: 22 }}>{o.code}</span>{o.label}
                      {(code ?? d.code) === o.code && <Icon name="check" size={13} color="var(--wm-brand)" strokeWidth={2.6} />}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
          <div style={{ height: 1, background: 'var(--wm-line-soft)' }} />
          <div className="pr-statcols" data-testid="pr3i-stats">
            {cols.map((rows, i) => (
              <div key={i} className="pr-colflex" style={{ gap: 4, minWidth: 0 }}>
                <span style={{ fontSize: 11.5, fontWeight: 600, color: 'var(--wm-text-muted)' }}>{colLabels[i]}</span>
                {rows.length === 0 && <span className="pr-subtle" style={{ fontSize: 11.5 }}>사례가 없어요</span>}
                {rows.slice(0, 3).map((r) => (
                  <div key={r.label} className="pr-statrow">
                    <span className="pr-ell" style={{ fontSize: 11.5 }}>{r.label}</span>
                    <span className="pr-statbar"><span style={{ width: `${Math.round((r.n / Math.max(1, r.of)) * 100)}%` }} /></span>
                    <span className="pr-num pr-brand" style={{ fontSize: 11.5, fontWeight: 800, textAlign: 'right' }}>{r.n}</span>
                  </div>
                ))}
              </div>
            ))}
          </div>
        </div>
      </Agent>
    </PrPage>
  );
}
