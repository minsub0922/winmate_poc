/**
 * PR1 — 고객 · 프로젝트 정보(§4.7, 보드 PR1, 1/6). 입력은 0.8초 디바운스로 자동 저장(PATCH), 「다음: 제안서 유형」 → stage=type → PR2.
 * 최근 Storyboard 제안 카드: workspace 색인(SB, 30일 안, 고객사를 넣었으면 그 고객) → 「채우기」 = PR1L(그 작업 체크).
 */
import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api, unwrap } from '@/api/client';
import { toast } from '@/ui';
import { patchProposal, qk, useProposal } from '../api/proposal';
import { errText } from '../api/http';
import type { Proposal } from '../api/types';
import { Agent, Dock, ErrorBand, LoadingCard, NextButton, PrPage, SrcIcon } from '../components/parts';
import { INDUSTRIES, INDUSTRY_CHIPS } from '../lib/catalog';
import { isAhead, R } from '../lib/routes';
import { useProposalShell } from '../lib/useProposalShell';

interface Draft { name: string; title: string; industry: string; chip: string; who: string; scale: string; due: string; lang: 'ko' | 'en' }
const fromP = (p: Proposal): Draft => ({
  name: p.customer?.name ?? '', title: p.title ?? '', industry: p.customer?.industry_code ?? '', chip: '', who: p.customer?.decision_makers ?? '',
  scale: p.customer?.scale_text ?? '', due: p.schedule?.submit_due ?? '', lang: (p.language as 'ko' | 'en' | undefined) ?? 'ko',
});
/** 업종 칩(넓은 묶음)을 고르면 칩 이름을 보내고 서버가 묶음 안 16업종 후보 중 1위를 고른다(⚠Q9). 「더보기」는 16업종 코드 */
function bodyOf(d: Draft, p: Proposal | undefined) {
  const due = /^\d{4}-\d{2}-\d{2}$/.test(d.due) ? d.due : null;
  return {
    title: d.title,
    customer: {
      name: d.name, industry_code: d.industry || null, industry_label: d.industry ? INDUSTRIES[d.industry] ?? null : null,
      industry_chip: d.chip || null, decision_makers: d.who, scale_text: d.scale,
    },
    schedule: { submit_due: due, presentation: p?.schedule?.presentation ?? null },
    language: d.lang,
  };
}

/** 최근 Storyboard(30일 안 · 고객사 일치) — workspace 색인 */
function useRecentStoryboard(customer: string) {
  return useQuery({
    queryKey: ['pr', 'recent-sb', customer],
    queryFn: async () => {
      const r = unwrap(await api.workspace.GET('/v1/items', { params: { query: { feature: 'SB', limit: 20 } } }));
      const cut = Date.now() - 30 * 86_400_000;
      const c = customer.trim();
      return (r.items ?? []).find((it) => Date.parse(it.updated_at) >= cut && (!c || it.title.includes(c) || String((it.meta as Record<string, unknown> | null)?.customer ?? '').includes(c))) ?? null;
    },
    staleTime: 30_000, retry: 0,
  });
}

export function CustomerPage() {
  const { id } = useParams();
  const nav = useNavigate();
  const qc = useQueryClient();
  const pq = useProposal(id);
  const p = pq.data;
  const [d, setD] = useState<Draft | null>(null);
  const dRef = useRef<Draft | null>(null);
  const timer = useRef<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [more, setMore] = useState(false);
  useProposalShell({ p, step: 1, oneClick: { from: 'customer' } });

  useEffect(() => { if (p && !dRef.current) { dRef.current = fromP(p); setD(dRef.current); } }, [p]);
  const sb = useRecentStoryboard(d?.name ?? '');

  const save = async () => {
    if (timer.current) { window.clearTimeout(timer.current); timer.current = null; }
    if (!id || !dRef.current) return;
    const np = await patchProposal(id, bodyOf(dRef.current, qc.getQueryData<Proposal>(qk.p(id))));
    qc.setQueryData(qk.p(id), np);
  };
  const edit = (k: keyof Draft, v: string) => {
    if (!dRef.current) return;
    dRef.current = { ...dRef.current, [k]: v } as Draft;
    setD(dRef.current);
    if (timer.current) window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => { void save().catch((e) => toast(errText(e))); }, 800);
  };
  // 떠날 때 남은 것을 보낸다
  useEffect(() => () => { if (timer.current) { window.clearTimeout(timer.current); void save().catch(() => undefined); } }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const next = async () => {
    if (!id) return;
    setBusy(true);
    try {
      await save();
      if (isAhead('type', qc.getQueryData<Proposal>(qk.p(id))?.stage)) qc.setQueryData(qk.p(id), await patchProposal(id, { stage: 'type' }));
      nav(R.type(id));
    } catch (e) { toast(errText(e)); } finally { setBusy(false); }
  };

  const chipOn = useMemo(() => INDUSTRY_CHIPS.findIndex((c) => (d?.chip ? c.label === d.chip : !!d?.industry && c.codes.includes(d.industry))), [d?.industry, d?.chip]);
  const pickChip = (i: number | null) => {
    if (!dRef.current) return;
    const c = i === null ? null : INDUSTRY_CHIPS[i];
    dRef.current = { ...dRef.current, chip: c?.label ?? '', industry: c ? (c.codes.includes(dRef.current.industry) ? dRef.current.industry : c.codes[0]) : '' };
    setD(dRef.current);
    if (timer.current) window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => { void save().catch((e) => toast(errText(e))); }, 800);
  };
  const moreLabel = d?.industry && chipOn < 0 ? `더보기 · ${INDUSTRIES[d.industry] ?? d.industry}` : '더보기';

  if (pq.isError) return <PrPage><ErrorBand message={errText(pq.error, '제안서를 찾을 수 없어요')} onRetry={() => void pq.refetch()} /></PrPage>;
  if (!p || !d) return <PrPage><LoadingCard /></PrPage>;

  const dock = (
    <Dock title="고객 · 프로젝트 정보" meta="1 / 6" testId="pr1-dock"
      foot={<NextButton onClick={() => void next()} busy={busy} testId="pr1-next">다음: 제안서 유형</NextButton>}>
      <div className="pr-grid2">
        <div className="pr-field"><label htmlFor="pr1-cust">고객사</label>
          <input id="pr1-cust" className="pr-input" value={d.name} onChange={(e) => edit('name', e.target.value)} /></div>
        <div className="pr-field"><label htmlFor="pr1-proj">프로젝트명</label>
          <input id="pr1-proj" className="pr-input" value={d.title} onChange={(e) => edit('title', e.target.value)} /></div>
        <div className="pr-field">
          <span className="pr-field__label" id="pr1-ind">업종</span>
          <div className="pr-row pr-row--wrap" role="group" aria-labelledby="pr1-ind" style={{ gap: 6, position: 'relative' }}>
            {INDUSTRY_CHIPS.map((c, i) => (
              <button key={c.label} type="button" className="pr-choice" aria-pressed={chipOn === i} onClick={() => pickChip(chipOn === i ? null : i)}>{c.label}</button>
            ))}
            <button type="button" className="pr-choice" aria-pressed={!!d.industry && chipOn < 0} aria-haspopup="listbox" aria-expanded={more} onClick={() => setMore(!more)}>{moreLabel}</button>
            {more && (
              <div className="pr-menu" role="listbox" aria-label="업종 16개" style={{ left: 0, right: 'auto', top: 'auto', bottom: 44, maxHeight: 280, overflowY: 'auto' }}>
                {Object.entries(INDUSTRIES).map(([code, label]) => (
                  <button key={code} type="button" role="option" aria-selected={d.industry === code} onClick={() => { if (dRef.current) dRef.current = { ...dRef.current, chip: '' }; edit('industry', code); setMore(false); }}>{label}</button>
                ))}
              </div>
            )}
          </div>
        </div>
        <div className="pr-field"><label htmlFor="pr1-who">고객 측 의사결정자 · 청중</label>
          <input id="pr1-who" className="pr-input" placeholder="예) 운영본부장, 마케팅팀장, IT팀" value={d.who} onChange={(e) => edit('who', e.target.value)} /></div>
      </div>
      <div className="pr-grid3">
        <div className="pr-field"><label htmlFor="pr1-scale">규모</label>
          <input id="pr1-scale" className="pr-input" value={d.scale} onChange={(e) => edit('scale', e.target.value)} /></div>
        <div className="pr-field"><label htmlFor="pr1-due">제안 제출일</label>
          <input id="pr1-due" className="pr-input" placeholder="2026-10-15" value={d.due} onChange={(e) => edit('due', e.target.value)} /></div>
        <div className="pr-field">
          <span className="pr-field__label" id="pr1-lang">언어</span>
          <div className="pr-row" role="radiogroup" aria-labelledby="pr1-lang" style={{ gap: 6 }}>
            <button type="button" role="radio" className="pr-choice" aria-checked={d.lang === 'ko'} onClick={() => edit('lang', 'ko')}>한국어</button>
            <button type="button" role="radio" className="pr-choice" aria-checked={d.lang === 'en'} onClick={() => edit('lang', 'en')}>English</button>
          </div>
        </div>
      </div>
    </Dock>
  );

  return (
    <PrPage dock={dock} testId="pr1">
      <Agent text="새 제안서를 시작합니다. 고객 정보를 받은 뒤 제안서 유형(표준 · 퀵윈 · Solution형)을 고르고, 섹션별로 작성해 PPTX로 만듭니다. 다른 작업(Storyboard, Market Intelligence, 조감도 등)의 결과는 사이드바에서 끌어와 쓸 수 있습니다. 먼저 고객사와 프로젝트 정보를 알려주세요.">
        {sb.data && (
          <div className="pr-suggest" data-testid="pr1-sb">
            <span className="pr-iconbox"><SrcIcon kind="storyboard" size={16} /></span>
            <span style={{ display: 'flex', flexDirection: 'column', gap: 2, flex: 1, minWidth: 0 }}>
              <span style={{ fontSize: 13, fontWeight: 600 }}>최근 Storyboard &quot;{sb.data.title}&quot;에서 고객·프로젝트 정보를 채울까요?</span>
              <span style={{ fontSize: 12, color: 'var(--wm-text-muted)' }}>고객사, 업종, 규모, 요구사항 요약이 자동으로 입력됩니다.</span>
            </span>
            <button type="button" className="pr-mini pr-mini--primary" style={{ height: 32, padding: '0 12px', fontSize: 12.5, borderRadius: 8 }}
              onClick={() => { void save().catch(() => undefined); nav(R.works(p.id, sb.data!.item_id)); }}>채우기</button>
          </div>
        )}
      </Agent>
    </PrPage>
  );
}
