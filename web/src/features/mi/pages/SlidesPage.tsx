/** MI3P — 결과 → 슬라이드 구성 `/mi/:id/slides` (§4.17) */
import { useState } from 'react';
import { useNavigate } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { Thumb, cx, toast } from '@/ui';
import { errText, patchSlide, qk, slideRequest, useAnalysis, useSlides, type Mode, type SlidePlan } from '../api';
import { useLastScreen } from '../hooks';
import { Agent, BigButton, Dock, ErrorBand, Ic, LoadingCard, MiPage, ModeChip, P, Pill, PromptInput, SecButton, UserBubble, useAid, useMiShell } from '../parts';

const ORDER = ['고정한 시트는 그대로', '업종 레이아웃', '데이터 모양', '메시지 (왜 · 얼마나 · 누구)'];

export function SlidesPage() {
  const aid = useAid();
  const nav = useNavigate();
  const qc = useQueryClient();
  const a = useAnalysis(aid);
  useMiShell(a.data, 3, { complete: true });
  useLastScreen(aid, 'slides');
  const sl = useSlides(aid);
  const v = sl.data;
  const [sel, setSel] = useState<string | null>(null);
  const [said, setSaid] = useState<Array<{ q: string; a?: string }>>([]);

  async function patch(s: SlidePlan, body: { included?: boolean; template_code?: string; pinned?: boolean }) {
    if (!aid) return;
    try {
      await patchSlide(aid, s.id, body);
      await qc.invalidateQueries({ queryKey: qk.slides(aid) });
      void qc.invalidateQueries({ queryKey: ['mi', 'export-view', aid] });
    } catch (e) { toast(errText(e)); }
  }

  async function request(text: string) {
    if (!aid) return;
    const i = said.length;
    setSaid((x) => [...x, { q: text }]);
    try {
      const r = await slideRequest(aid, text);
      if (r.kind === 'layout' && r.sheet_id) {
        nav(`/mi/${aid}/slides/${r.sheet_id}?requested=${encodeURIComponent(r.requested ?? '')}&text=${encodeURIComponent(text)}`);
        return;
      }
      await qc.invalidateQueries({ queryKey: qk.slides(aid) });
      setSaid((x) => x.map((y, j) => (j === i ? { ...y, a: r.message || (r.kind === 'include' ? `시트 구성을 바꿨어요 · ${r.changed.length}개` : '구성 요청을 알아듣지 못했어요') } : y)));
    } catch (e) {
      setSaid((x) => x.map((y, j) => (j === i ? { ...y, a: errText(e) } : y)));
    }
  }

  const rows = v?.rows ?? [];
  const target = sel ?? rows[0]?.id;
  const h = (v?.header ?? {}) as { title?: string; industry?: number; generic?: number };
  const foot = (v?.footer ?? '슬라이드 구성').split(' · ');
  return (
    <MiPage dock={
      <Dock title={foot[0]} meta={foot.slice(1).join(' · ')}
        right={<>
          <Pill onClick={() => target && nav(`/mi/${aid}/slides/${target}`)} disabled={!target}>레이아웃 바꾸기</Pill>
          <Pill to={`/mi/${aid}/result?panel=sources`}>출처 보기</Pill>
        </>}
        row={
          <div className="mi-dock__row">
            <PromptInput label="구성 요청" placeholder="구성 요청 (예: 경쟁 환경은 포지셔닝 맵으로)" onSend={request} />
            <SecButton to={`/mi/${aid}/result`}>결과로</SecButton>
            <BigButton to={`/mi/${aid}/export`} testId="mi3p-send">제안서로 보내기</BigButton>
          </div>
        } />
    }>
      <Agent text="분석 결과의 데이터 모양을 보고 시트마다 레이아웃을 골랐어요. 업종 레이아웃이 있으면 그것부터, 없으면 데이터 모양과 메시지로 골랐습니다.">
        {sl.isError && <ErrorBand onRetry={() => void sl.refetch()} />}
        {!v && !sl.isError && <LoadingCard lines={6} />}
        {v && (
          <div className="mi-card" data-testid="mi3p-card">
            <div className="mi-card__head">
              <Ic d={P.monitor} size={16} w={2} className="mi-brand" />
              <span className="mi-card__title">슬라이드 구성</span>
              <span className="mi-note mi-ell" data-testid="mi3p-head">{h.title}</span>
              <span className="mi-grow" />
              <span className="mi-note" style={{ whiteSpace: 'nowrap' }}>업종 레이아웃 <b className="mi-brand">{h.industry ?? 0}</b> · 범용 <b style={{ color: 'var(--wm-text)' }}>{h.generic ?? 0}</b></span>
            </div>
            {rows.map((s) => <SlideRow key={s.id} s={s} sel={s.id === sel} onSelect={() => setSel(s.id)} onPatch={(b) => void patch(s, b)} />)}
          </div>
        )}
        {v && (
          <div className="mi-order">
            <b>고르는 순서</b>
            {ORDER.map((t, i) => (
              <span key={t} className="mi-order__step"><b>{i + 1}</b>{t}{i < ORDER.length - 1 && <Ic d={P.chevR} size={12} w={2.4} className="mi-sub" />}</span>
            ))}
          </div>
        )}
      </Agent>
      {said.map((x, i) => (
        <div key={i} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <UserBubble>{x.q}</UserBubble>
          {x.a && <Agent text={x.a} />}
        </div>
      ))}
    </MiPage>
  );
}

function SlideRow({ s, sel, onSelect, onPatch }: { s: SlidePlan; sel: boolean; onSelect: () => void; onPatch: (b: { included?: boolean; template_code?: string; pinned?: boolean }) => void }) {
  const good = s.fit >= 85;
  return (
    <div className={cx('mi-srow', !s.included && 'mi-srow--off', sel && 'mi-srow--sel')} onClick={onSelect} data-sheet={s.id} data-code={s.template_code} data-testid="mi3p-row">
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4, minWidth: 0 }}>
        <label className="mi-srow__sheet" onClick={(e) => e.stopPropagation()}>
          <input type="checkbox" checked={s.included} aria-label={`${s.sheet_name} 시트 넣기`} onChange={(e) => onPatch({ included: e.target.checked, pinned: true })} />
          <span>{s.sheet_name}</span>
        </label>
        <span className="mi-srow__src">{s.source_label}</span>
        <span className="mi-srow__mode"><ModeChip mode={(s.pinned ? 'pin' : s.include_mode) as Mode} /></span>
      </div>
      <div className={cx('mi-thumb', !s.included && 'mi-thumb--dim')}><Thumb kind={s.thumb_kind} n={3} code={s.template_code} /></div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4, minWidth: 0 }}>
        <div className="mi-row" style={{ alignItems: 'baseline', gap: 7 }}>
          <span className="mi-srow__code">{s.template_code}</span>
          <span className="mi-srow__name">{s.template_name}</span>
          {s.industry_layout && <span className="mi-indtag">업종</span>}
        </div>
        <span className="mi-srow__why" title={s.why}>{s.why}</span>
        <div className="mi-row">
          <div className={cx('mi-fit', good && 'mi-fit--good')}><div style={{ width: `${Math.max(0, s.fit)}%` }} /></div>
          <span className="mi-note" style={{ fontSize: 11.5, whiteSpace: 'nowrap' }}>데이터 적합 <b className="mi-num" style={{ color: 'var(--wm-text)' }}>{s.fit}%</b></span>
        </div>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 3, minWidth: 0 }}>
        <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--wm-text-subtle)' }}>대안</span>
        {(s.alternatives ?? []).map((x) => (
          <button key={x.code} type="button" className="mi-alt" disabled={x.fit < 0} title={x.fit < 0 ? '필요한 데이터가 없어 고를 수 없어요' : `${x.code}로 바꾸기`}
            onClick={(e) => { e.stopPropagation(); onPatch({ template_code: x.code, pinned: true }); }}>
            <b>{x.code}</b><span className={cx(x.fit < 0 && 'mi-alt__no')}>{x.fit < 0 ? '불가' : `${x.fit}%`}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
