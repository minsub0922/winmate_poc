/**
 * 템플릿 고르기(§3.7 · §4.16, 보드 PRS1Layout · PRS4Layout · PRS5Layout · PRS7Layout · PRS5LayoutInd · PRS1LayoutInd · PRS2LayoutInd · PRX3LayoutInd).
 * `GET …/sheets/{id}/template-options` — 「자동 추천」 = mode auto(추천 코드) · 카드 클릭 / 「직접 선택」 = mode pinned(그 코드) · 제품 수 1–5(공간 제품 소개만).
 * 「이 시트에 적용」 → `PUT …/template` · 「섹션 전체 자동으로」 → `POST …/sections/{key}/templates:auto`(고정 시트가 있으면 확인).
 * 서버가 아직 후보를 주지 못하면(구현 전) 보드 로직으로 후보를 만든다(lib/catalog `templateCandidates`).
 */
import { useEffect, useState } from 'react';
import { Icon, Thumb, useConfirm } from '@/ui';
import { putSheetTemplate, sectionAutoTemplates, useTemplateOptions } from '../api/proposal';
import { errText, isMissing } from '../api/http';
import type { SectionSheet, TemplateOptions } from '../api/types';
import { ErrorBand, LoadingCard, SegCtl } from '../components/parts';
import { ROLES, templateCandidates, tplOf } from '../lib/catalog';

const STAR = 'M12 2l2.2 6.3L20.5 10l-6.3 2.2L12 18.5l-2.2-6.3L3.5 10l6.3-1.7z';

export interface Pick { mode: 'auto' | 'pinned'; code: string; count: number | null }

const sheetCode = (s: SectionSheet) => s.template_info?.code ?? s.template ?? '';

function fallbackOptions(sheet: SectionSheet, industry: string | null, count: number | null): TemplateOptions {
  const role = sheet.role;
  const def = ROLES[role];
  const code = sheetCode(sheet);
  const n = def?.product ? (count ?? sheet.template_info?.product_count ?? (Number(/^P(\d)/.exec(code)?.[1]) || 3)) : null;
  const codes = templateCandidates(role, { solution: sheet.solution_code, industry, productCount: n ?? undefined });
  const recRaw = sheet.template_info?.recommended_code ?? code ?? codes[0];
  const rec = def?.product && n ? `P${n}-${(recRaw || 'P3-A').slice(-1)}` : recRaw || codes[0];
  return {
    sheet: { id: sheet.id, title: sheet.title, role, role_name: sheet.role_name, msg: def?.msg ?? '' }, header_label: '', mode: sheet.template_info?.mode ?? 'auto', current_code: code,
    recommended: { code: rec, reason: sheet.template_info?.reason ?? '' }, reason_line: '',
    variants: codes.map((c) => { const t = tplOf(c); return { code: c, name: t.name, when: t.when, thumb_url: '', kind: 'generic', selected: c === code, available: true }; }),
    product_count: n, pinned_in_section: 0, products_label: '', sheet_label: '',
  };
}

export function TemplatePanel({ proposalId, sectionKey, sheet, industry, pinnedCount, pick, onPick, onApplied, onClose }: {
  proposalId: string; sectionKey: string; sheet: SectionSheet; industry: string | null; pinnedCount: number;
  pick: Pick | null; onPick: (p: Pick) => void; onApplied: () => void; onClose?: () => void;
}) {
  const isProduct = !!ROLES[sheet.role]?.product;
  const [count, setCount] = useState<number | null>(isProduct ? (sheet.template_info?.product_count ?? null) : null);
  const oq = useTemplateOptions(proposalId, sheet.id, isProduct ? count : null);
  const fromServer = oq.data && Array.isArray(oq.data.variants) ? oq.data : null;
  const o: TemplateOptions | null = fromServer ?? (oq.isError && isMissing(oq.error) ? fallbackOptions(sheet, industry, count) : null);
  const [busy, setBusy] = useState<'apply' | 'auto' | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const { confirm, dialog } = useConfirm();
  const rec = (o?.recommended?.code as string | null | undefined) ?? o?.variants[0]?.code ?? '';

  // 처음: 시트의 지금 상태(자동/직접 · 코드)
  useEffect(() => {
    if (!o || pick) return;
    onPick({ mode: o.mode, code: o.mode === 'auto' ? rec : (o.current_code ?? rec), count: o.product_count ?? null });
  }, [o, pick, onPick, rec]);
  useEffect(() => { if (o?.product_count && count === null) setCount(o.product_count); }, [o?.product_count, count]);

  if (oq.isError && !isMissing(oq.error)) return <ErrorBand message={errText(oq.error)} onRetry={() => void oq.refetch()} />;
  if (!o || !pick) return <LoadingCard lines={3} />;

  const variants = o.variants.slice(0, 5);
  const setCountAnd = (n: number) => {
    setCount(n);
    onPick({ ...pick, count: n, code: pick.mode === 'auto' ? `P${n}-${rec.slice(-1)}` : `P${n}-${pick.code.slice(-1)}` });
  };
  const apply = async () => {
    setBusy('apply'); setErr(null);
    try {
      await putSheetTemplate(proposalId, sheet.id, { mode: pick.mode, code: pick.mode === 'pinned' ? pick.code : null, product_count: isProduct ? count : null });
      onApplied();
    } catch (e) { setErr(errText(e)); } finally { setBusy(null); }
  };
  const allAuto = async () => {
    const pinned = o.pinned_in_section ?? pinnedCount;
    if (pinned > 0 && !(await confirm({ title: '섹션 전체 자동으로', message: o.auto_all_confirm || `직접 고른 ${pinned}장도 자동으로 바꿔요`, confirmLabel: '자동으로 바꾸기' }))) return;
    setBusy('auto'); setErr(null);
    try { await sectionAutoTemplates(proposalId, sectionKey, true); onApplied(); } catch (e) { setErr(errText(e)); } finally { setBusy(null); }
  };
  const reason = (o.recommended?.reason as string | null | undefined) || tplOf(rec).when;
  const head = o.header_label || `${o.sheet.title} · “${o.sheet.msg}”를 보여줄 템플릿 ${variants.length}종`;
  const [hTitle, ...hRest] = head.split(' · ');

  return (
    <div className="pr-panel" data-testid="pr-template-panel">
      <div className="pr-panel__head">
        <Icon name="file" size={16} color="var(--wm-brand)" />
        <div className="pr-panel__title" data-testid="pr-template-head">{hTitle} {hRest.length > 0 && <span className="pr-muted" style={{ fontWeight: 500 }}>· {hRest.join(' · ')}</span>}</div>
        <SegCtl label="템플릿 선택 방식" value={pick.mode} testId="pr-template-mode"
          onChange={(m) => onPick(m === 'auto' ? { ...pick, mode: 'auto', code: isProduct && count ? `P${count}-${rec.slice(-1)}` : rec } : { ...pick, mode: 'pinned' })}
          items={[{ value: 'auto', label: '자동 추천' }, { value: 'pinned', label: '직접 선택' }]} />
        {onClose && <button type="button" className="pr-mini pr-mini--ghost" aria-label="닫기" onClick={onClose}><Icon name="x" size={14} /></button>}
      </div>
      {isProduct && (
        <div className="pr-row" style={{ gap: 6, height: 28 }}>
          <span className="pr-label" style={{ marginRight: 4, whiteSpace: 'nowrap' }}>시트 속 제품</span>
          {[1, 2, 3, 4, 5].map((n) => (
            <button key={n} type="button" className="pr-countpill" aria-pressed={(count ?? o.product_count) === n} aria-label={`제품 ${n}개`} onClick={() => setCountAnd(n)}>{n}</button>
          ))}
          <span className="pr-ell" style={{ fontSize: 12, marginLeft: 6 }}>{o.products_label || (o.products ?? []).join(' · ')}</span>
          <span style={{ flex: 1 }} />
          <span style={{ fontSize: 11.5, color: 'var(--wm-text-subtle)', whiteSpace: 'nowrap' }}>{o.split_note || '6개 이상이면 2장으로 나눠요 (7 → 4 + 3)'}</span>
        </div>
      )}
      <div className="pr-variants" role="radiogroup" aria-label="템플릿" style={{ gridTemplateColumns: `repeat(${Math.max(variants.length, 1)}, minmax(0, 1fr))` }}>
        {variants.map((v) => {
          const t = tplOf(v.code);
          const on = v.code === pick.code;
          return (
            <button key={v.code} type="button" role="radio" aria-checked={on} className="pr-variant" data-code={v.code} disabled={v.available === false}
              onClick={() => onPick({ ...pick, mode: 'pinned', code: v.code })}>
              <span style={{ position: 'relative', width: '100%', height: 68, display: 'flex', justifyContent: 'center' }}>
                <Thumb code={v.code} kind={t.kind} n={t.n} src={v.thumb_url || undefined} dim={v.available === false} />
                {on && pick.mode === 'auto' && <span className="pr-variant__badge"><svg width="9" height="9" viewBox="0 0 24 24" fill="currentColor"><path d={STAR} /></svg>자동</span>}
                {v.code === rec && !(on && pick.mode === 'auto') && <span className="pr-variant__badge pr-variant__badge--rec">추천</span>}
              </span>
              <span className="pr-row" style={{ gap: 6, width: '100%', minWidth: 0 }}>
                <span className={on ? 'pr-radio pr-radio--on' : 'pr-radio'} />
                <span className="pr-variant__code">{v.code}</span>
                <span className="pr-variant__name">{v.name}</span>
              </span>
              <span className="pr-variant__when">{v.when}</span>
            </button>
          );
        })}
      </div>
      {err && <ErrorBand message={err} />}
      <div className="pr-row" style={{ height: 32 }}>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="var(--wm-brand)" style={{ flexShrink: 0 }}><path d={STAR} /></svg>
        <span className="pr-ell pr-grow" style={{ fontSize: 12, color: 'var(--wm-text-muted)' }} data-testid="pr-template-rec">
          {o.reason_line ? <ReasonLine text={o.reason_line} /> : <><span className="pr-num" style={{ fontWeight: 800, color: 'var(--wm-brand)' }}>{rec}</span> 추천 · {reason}</>}
        </span>
        <button type="button" className="pr-btn pr-btn--sm" disabled={!!busy} onClick={() => void allAuto()} data-testid="pr-template-all-auto">섹션 전체 자동으로</button>
        <button type="button" className="pr-btn pr-btn--sm pr-btn--primary" style={{ fontSize: 12.5, padding: '0 14px' }} disabled={!!busy} onClick={() => void apply()} data-testid="pr-template-apply">이 시트에 적용</button>
      </div>
      {dialog}
    </div>
  );
}

/** 「MS-B 추천 · …」 — 앞 코드만 강조 */
function ReasonLine({ text }: { text: string }) {
  const m = /^(\S+)( 추천 · .*)$/.exec(text);
  if (!m) return <>{text}</>;
  return <><span className="pr-num" style={{ fontWeight: 800, color: 'var(--wm-brand)' }}>{m[1]}</span>{m[2]}</>;
}
