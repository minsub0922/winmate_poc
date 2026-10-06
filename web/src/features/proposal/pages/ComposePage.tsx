/**
 * PR3 · PR3SolOpen · PR3Quick · PR3Solution — 시트 구성(§4.12, 3/6). 유형마다 같은 화면, 처음 펼친 섹션만 다르다.
 * 체크 · 스위치 → `PUT …/composition` 즉시 저장. 「섹션 작성 시작」 → 업종 감지 · 미결정이면 PR3I, 아니면 첫 섹션(stage=sections).
 * `?open=<섹션 키>` 로 펼칠 섹션을 고른다(SectionStep 「시트 추가 · 빼기」 · PRU3 「시트 구성에서 다듬기」).
 */
import { useEffect, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { Icon, toast } from '@/ui';
import { putComposition, qk, startComposition, useComposition, useProposal } from '../api/proposal';
import { errText, isMissing } from '../api/http';
import type { Composition, CompSection, CompType } from '../api/types';
import { Agent, CheckBox, Dock, ErrorBand, GhostButton, LoadingCard, NextButton, PrPage, Switch } from '../components/parts';
import { COMPOSITION, SECTIONS, SOL_CODES, STN, TYPES, type ProposalType, type SectionKey } from '../lib/catalog';
import { normalizeRoute, R } from '../lib/routes';
import { useProposalShell } from '../lib/useProposalShell';

/** 서버 구성이 아직 없을 때 보드 기본값(부록 E) */
export function fallbackComposition(type: ProposalType): Composition {
  const T = TYPES[type];
  let total = 0;
  const sections: CompSection[] = T.secs.map((key, i) => {
    const defs = COMPOSITION[key];
    const on = defs.filter((d) => d[1] === 1);
    const count = on.reduce((a, d) => a + (SOL_CODES.includes(d[0]) ? 3 : d[2]), 0);
    total += count;
    const opt = T.opt.includes(key);
    return {
      no: i + 1, no_label: String(i + 1).padStart(2, '0'), key, name: SECTIONS[key].name, optional: opt, enabled: true, tag: opt ? '선택' : '필수', switch_label: `${SECTIONS[key].name} 섹션 사용`,
      chips: on.map(([code, , rep]) => ({ code, name: STN[code]?.[0] ?? code, repeat: rep })), more: defs.length - on.length, more_label: `+ ${defs.length - on.length}`, open: false, sheet_count: count,
      types: defs.map(([code, st, rep, src]) => {
        const sol = SOL_CODES.includes(code);
        return { code, name: STN[code]?.[0] ?? code, msg: STN[code]?.[1] ?? '', state: st === 1 ? 'on' : st === 2 ? 'rec' : 'off', src_label: src, template_count: STN[code]?.[2], repeat: rep, dedicated: sol,
          user_set: false, meta: sol ? `전용 3장 · 소개 · 구성도 · 공간 시나리오 · ${src}` : `템플릿 ${STN[code]?.[2] ?? 0}종 · ${src}` } as CompType;
      }),
    };
  });
  return {
    type, type_name: T.name, sections, sheet_total: total, section_count: sections.length, header_label: '', footer_note: '',
    intro: `${T.name}에 넣을 시트를 고르세요. 시트마다 말하는 역할이 정해져 있고, 요구사항과 연결된 자료를 보고 필요한 시트를 미리 골라 두었어요. 템플릿은 섹션 작성 때 내용에 맞춰 고릅니다.`,
    next: { target: 'sections', route: '', label: '섹션 작성 시작' },
  };
}

const typeName = (t: CompType) => (t.repeat && t.repeat > 1 && !t.dedicated && !t.name.includes('×') ? `${t.name} ×${t.repeat}` : t.name);
const typeMeta = (t: CompType) => t.meta ?? (t.dedicated ? `전용 3장 · 소개 · 구성도 · 공간 시나리오 · ${t.src_label ?? ''}` : `템플릿 ${t.template_count ?? 0}종 · ${t.src_label ?? ''}`);

export function ComposePage() {
  const { id } = useParams();
  const [sp, setSp] = useSearchParams();
  const nav = useNavigate();
  const qc = useQueryClient();
  const pq = useProposal(id);
  const p = pq.data;
  const cq = useComposition(id, sp.get('open') ?? undefined);
  const [busy, setBusy] = useState(false);
  const [saving, setSaving] = useState<string | null>(null);
  useProposalShell({ p, step: 3, oneClick: { from: 'compose' } });

  const type: ProposalType = (p?.type as ProposalType | null | undefined) ?? 'standard';
  const fromServer = cq.data && Array.isArray(cq.data.sections) ? cq.data : null;
  const comp: Composition | null = fromServer ?? (p && (cq.isError && isMissing(cq.error)) ? fallbackComposition(type) : null);
  const defaultOpen = (fromServer?.open_key || fromServer?.sections.find((x) => x.open)?.key) ?? comp?.sections[TYPES[type].open]?.key ?? null;
  const [open, setOpen] = useState<string | null>(sp.get('open'));
  useEffect(() => { if (open === null && defaultOpen) setOpen(defaultOpen); }, [defaultOpen, open]);

  const save = async (body: Parameters<typeof putComposition>[1], key: string) => {
    if (!id) return;
    setSaving(key);
    try {
      const r = await putComposition(id, body);
      if (r && Array.isArray(r.sections)) qc.setQueryData(qk.sub(id, 'composition'), r);
      else void qc.invalidateQueries({ queryKey: qk.sub(id, 'composition') });
      void qc.invalidateQueries({ queryKey: qk.p(id) });
    } catch (e) { toast(errText(e)); } finally { setSaving(null); }
  };

  // 「섹션 작성 시작」 — 업종 감지 · 미결정이면 PR3I, 아니면 첫 섹션(서버가 다음 화면을 정한다: `composition:start`)
  const start = async () => {
    if (!p || !comp) return;
    setBusy(true);
    try {
      const r = await startComposition(p.id);
      qc.setQueryData(qk.p(p.id), r.proposal);
      nav(normalizeRoute(r.next.route) ?? R.section(p.id, comp.sections.find((s) => s.enabled)?.key ?? TYPES[type].secs[0]));
    } catch (e) { toast(errText(e)); } finally { setBusy(false); }
  };

  if (pq.isError) return <PrPage><ErrorBand message={errText(pq.error, '제안서를 찾을 수 없어요')} onRetry={() => void pq.refetch()} /></PrPage>;
  if (!p) return <PrPage><LoadingCard /></PrPage>;
  const tName = comp?.type_name ?? TYPES[type].name;

  const dock = (
    <Dock testId="pr3-dock"
      title={<>시트 구성 <span className="pr-muted" style={{ fontWeight: 500 }} data-testid="pr3-meta">· {comp?.header_label || `${tName} · 섹션 ${comp?.section_count ?? comp?.sections.filter((s) => s.enabled).length ?? '·'} · 시트 ${comp?.sheet_total ?? '·'} · 3 / 6`}</span></>}
      right={<GhostLink to={R.type(p.id)}>유형 바꾸기</GhostLink>}
      hint={comp?.footer_note || '시트 수는 따로 정하지 않아요. 공간 · 사례처럼 반복되는 시트는 연결된 항목 수만큼 생깁니다.'}
      foot={<>
        <GhostButton to={R.type(p.id)}>이전</GhostButton>
        <NextButton onClick={() => void start()} busy={busy} disabled={!comp} testId="pr3-start">섹션 작성 시작</NextButton>
      </>}>
      <div className="pr-comp__cols"><span /><span>섹션</span><span>넣을 시트</span><span style={{ textAlign: 'right' }}>사용</span></div>
      {!comp && (cq.isError ? <ErrorBand message={errText(cq.error)} onRetry={() => void cq.refetch()} /> : <LoadingCard lines={4} />)}
      {comp && (
        <div className="pr-comp__list" data-testid="pr3-list">
          {comp.sections.map((s) => {
            const isOpen = open === s.key;
            const chips = s.chips ?? (s.types ?? []).filter((t) => t.state === 'on').map((t) => ({ code: t.code, name: t.name, repeat: t.repeat }));
            const more = s.more ?? (s.types ?? []).filter((t) => t.state !== 'on').length;
            return (
              <div key={s.key} style={{ display: 'flex', flexDirection: 'column', gap: 6 }} data-testid={`pr3-sec-${s.key}`}>
                <div className={['pr-comp__row', isOpen && 'pr-comp__row--open', !s.enabled && 'pr-comp__row--off'].filter(Boolean).join(' ')}>
                  <span className="pr-comp__no">{s.no_label || String(s.no).padStart(2, '0')}</span>
                  <button type="button" className="pr-comp__name" aria-expanded={isOpen}
                    onClick={() => { const n = isOpen ? null : s.key; setOpen(n ?? ''); setSp((cur) => { const x = new URLSearchParams(cur); if (n) x.set('open', n); else x.delete('open'); return x; }, { replace: true }); }}>
                    <span style={{ display: 'inline-flex', transform: isOpen ? 'rotate(90deg)' : undefined }}><Icon name="chevronRight" size={12} color="var(--wm-text-muted)" strokeWidth={2.4} /></span>
                    <span>{s.name}</span>
                    <span className={s.optional ? 'pr-tag pr-tag--dashed' : 'pr-tag'}>{s.tag ?? (s.optional ? '선택' : '필수')}</span>
                  </button>
                  <div className="pr-comp__chips">
                    {chips.map((c) => <span key={c.code} className="pr-comp__chip">{c.name}{(c.repeat ?? 1) > 1 && <b>×{c.repeat}</b>}</span>)}
                    {more > 0 && <span className="pr-comp__more">{s.more_label || `+ ${more}`}</span>}
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                    {s.optional
                      ? <Switch on={s.enabled} label={s.switch_label || `${s.name} 섹션 사용`} disabled={saving === s.key} onChange={(v) => void save([{ key: s.key, enabled: v }], s.key)} />
                      : <span className="pr-comp__req"><Icon name="lock" size={12} />필수</span>}
                  </div>
                </div>
                {isOpen && (
                  <div className="pr-comp__open" role="group" aria-label={`${s.name} 시트 유형`}>
                    {(s.types ?? []).map((t) => (
                      <button key={t.code} type="button" role="checkbox" aria-checked={t.state === 'on'} className={t.state === 'rec' ? 'pr-sheettype pr-sheettype--rec' : 'pr-sheettype'}
                        disabled={saving === s.key || !s.enabled} data-testid={`pr3-type-${t.code}`}
                        onClick={() => void save([{ key: s.key, types: [{ code: t.code, on: t.state !== 'on' }] }], s.key)}>
                        <span className="pr-row" style={{ gap: 7, width: '100%', minWidth: 0 }}>
                          <CheckBox on={t.state === 'on'} />
                          <span className="pr-sheettype__name">{typeName(t)}</span>
                          <span style={{ flex: 1 }} />
                          {t.state === 'rec' && <span className="pr-recpill">추천</span>}
                        </span>
                        <span className="pr-sheettype__msg">“{t.msg}”</span>
                        <span className="pr-sheettype__meta">{typeMeta(t)}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </Dock>
  );

  return (
    <PrPage dock={dock} testId="pr3" tight>
      <Agent testId="pr3-agent" text={comp?.intro || `${tName}에 넣을 시트를 고르세요. 시트마다 말하는 역할이 정해져 있고, 요구사항과 연결된 자료를 보고 필요한 시트를 미리 골라 두었어요. 템플릿은 섹션 작성 때 내용에 맞춰 고릅니다.`} />
      {!fromServer && comp && <div className="pr-band pr-band--muted" data-testid="pr3-fallback">구성 정보를 아직 받지 못해 기본 구성을 보여 드려요.</div>}
    </PrPage>
  );
}

function GhostLink({ to, children }: { to: string; children: React.ReactNode }) {
  const nav = useNavigate();
  return <button type="button" className="pr-link" style={{ height: 28, padding: '0 10px' }} onClick={() => nav(to)}>{children}</button>;
}
export type { SectionKey };
