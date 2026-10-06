/**
 * PR2 — 제안서 유형(§4.11, 보드 PR2, 2/6) · OneClickEarly(유형 고르기 전 딸깍 팝오버).
 * 카드 클릭 = 그 유형 저장(`PUT …/type`) + 그 유형의 시트 구성 화면. 「다음: 시트 구성」 = 지금 선택(없으면 추천).
 * `?oneclick=1` 이면 딸깍 팝오버가 열린 채로(OneClickEarly 보드).
 */
import { useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { toast } from '@/ui';
import { patchProposal, putType, qk, useProposal, useTypeOptions } from '../api/proposal';
import { errText } from '../api/http';
import { Agent, Dock, ErrorBand, GhostButton, LoadingCard, NextButton, PrPage, UserBubble } from '../components/parts';
import { SECTIONS, TYPES, type ProposalType } from '../lib/catalog';
import { isAhead, normalizeRoute, R } from '../lib/routes';
import { useProposalShell } from '../lib/useProposalShell';
import { industryLabel } from '../lib/format';

const ORDER: ProposalType[] = ['standard', 'quickwin', 'solution'];
const secLabel = (k: string) => (k === 'spaceScenario' ? SECTIONS.spaceScenario.name : SECTIONS[k as keyof typeof SECTIONS]?.short ?? k);

export function TypePage() {
  const { id } = useParams();
  const [sp] = useSearchParams();
  const nav = useNavigate();
  const qc = useQueryClient();
  const pq = useProposal(id);
  const p = pq.data;
  const opts = useTypeOptions(id);
  const [busy, setBusy] = useState<ProposalType | 'next' | null>(null);
  useProposalShell({ p, step: 2, oneClick: { from: 'type' }, oneClickOpen: sp.get('oneclick') === '1' });

  if (pq.isError) return <PrPage><ErrorBand message={errText(pq.error, '제안서를 찾을 수 없어요')} onRetry={() => void pq.refetch()} /></PrPage>;
  if (!p) return <PrPage><LoadingCard /></PrPage>;

  const rec: ProposalType = opts.data?.recommended?.type ?? (p.type_source === 'recommended' && p.type ? p.type as ProposalType : 'standard');
  const reason = opts.data?.recommended?.reason ?? '요구사항을 모두 담을 수 있는 기본형이라';
  const chosen: ProposalType | null = opts.data ? (opts.data.selected ?? null) : p.type && p.type_source !== 'recommended' ? p.type as ProposalType : null;
  const sel = chosen ?? rec;
  const types = ORDER.map((t) => {
    const s = opts.data?.types?.find((x) => x.type === t);
    return {
      type: t, name: s?.name ?? TYPES[t].name, desc: s?.desc ?? TYPES[t].desc,
      secs: s?.sections?.map((x) => ({ no: x.no, label: x.label, opt: x.optional })) ?? TYPES[t].secs.map((k, i) => ({ no: i + 1, label: secLabel(k), opt: TYPES[t].opt.includes(k) })),
    };
  });

  const choose = async (t: ProposalType, from: ProposalType | 'next') => {
    setBusy(from);
    try {
      const np = await putType(p.id, t);
      if (np?.id) qc.setQueryData(qk.p(p.id), np);
      const cur = np?.stage ?? p.stage;
      if (isAhead('compose', cur)) await patchProposal(p.id, { stage: 'compose' }).then((x) => qc.setQueryData(qk.p(p.id), x)).catch(() => undefined);
      void qc.invalidateQueries({ queryKey: qk.p(p.id) });
      nav(normalizeRoute(opts.data?.types.find((x) => x.type === t)?.route) ?? R.compose(p.id));
    } catch (e) { toast(errText(e)); } finally { setBusy(null); }
  };

  const line = opts.data?.customer_line;
  const summary = [p.customer?.name, p.title, industryLabel(p), p.customer?.scale_text].filter(Boolean);
  const dock = (
    <Dock title="제안서 유형" meta={opts.data?.header_label?.replace(/^제안서 유형 · /, '') || '하나 선택 · 2 / 6'} testId="pr2-dock"
      hint={opts.data?.footer_note || '유형은 섹션 작성 중에도 바꿀 수 있고, 이미 작성한 섹션은 유지됩니다.'}
      foot={<>
        <GhostButton to={R.customer(p.id)}>이전</GhostButton>
        <NextButton onClick={() => void choose(sel, 'next')} busy={busy === 'next'} testId="pr2-next">다음: 시트 구성</NextButton>
      </>}>
      <div className="pr-types" role="group" aria-label="제안서 유형">
        {types.map((t) => (
          <button key={t.type} type="button" className="pr-typecard" aria-pressed={sel === t.type} onClick={() => void choose(t.type, t.type)} disabled={!!busy}
            data-testid={`pr2-type-${t.type}`}>
            <span className="pr-row pr-row--between" style={{ width: '100%' }}>
              <span className="pr-typecard__name">{t.name}</span>
              {rec === t.type && <span className="pr-recbadge">추천</span>}
            </span>
            <span className="pr-typecard__desc">{t.desc}</span>
            <span style={{ display: 'flex', flexDirection: 'column', gap: 4, width: '100%' }}>
              {t.secs.map((s) => (
                <span key={s.no} className={s.opt ? 'pr-typecard__sec pr-typecard__sec--opt' : 'pr-typecard__sec'}>
                  <span className="pr-typecard__no">{s.no}</span><span style={{ flex: 1 }}>{s.label}</span>
                  {s.opt && <span style={{ fontSize: 10.5, color: 'var(--wm-text-muted)' }}>선택</span>}
                </span>
              ))}
            </span>
            <span style={{ flex: 1 }} />
            <span className="pr-typecard__foot">섹션 {t.secs.length} · 넣을 시트는 다음 단계에서 골라요</span>
          </button>
        ))}
      </div>
    </Dock>
  );

  return (
    <PrPage dock={dock} testId="pr2">
      {(line || summary.length > 0) && (
        <UserBubble testId="pr2-summary">
          {line ? <><b>{line.split(' · ')[0]}</b>{line.split(' · ').slice(1).map((s, i) => <span key={i}> · {s}</span>)}</> : <><b>{summary[0]}</b>{summary.slice(1).map((s, i) => <span key={i}> · {s}</span>)}</>}
        </UserBubble>
      )}
      <Agent testId="pr2-agent" text={opts.data?.intro ? <Bold text={opts.data.intro} bold={TYPES[rec].name} /> : <>어떤 형태의 제안서로 만들까요? 유형마다 섹션 구성이 다르고, 점선으로 표시된 섹션과 섹션마다 넣을 시트는 다음 단계에서 고릅니다. {reason} <b>{TYPES[rec].name}</b>를 추천합니다.</>} />
    </PrPage>
  );
}

/** 문장 안 추천 유형 이름만 굵게 */
function Bold({ text, bold }: { text: string; bold: string }) {
  const i = text.lastIndexOf(bold);
  if (i < 0) return <>{text}</>;
  return <>{text.slice(0, i)}<b>{bold}</b>{text.slice(i + bold.length)}</>;
}
