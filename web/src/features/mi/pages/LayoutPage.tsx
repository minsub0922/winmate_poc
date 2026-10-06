/** MI3L — 레이아웃 바꾸기 · 데이터 적합도 `/mi/:id/slides/:sheet?requested=&text=` (§4.18) */
import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { Thumb, cx, toast } from '@/ui';
import { chooseLayout, errText, qk, slideRequest, useAnalysis, useCandidates, type LayoutOption, type TemplateCandidate } from '../api';
import { Agent, BigButton, Dock, ErrorBand, Ic, LoadingCard, MiPage, P, Pill, PromptInput, SecButton, UserBubble, useAid, useMiShell } from '../parts';

export function LayoutPage() {
  const aid = useAid();
  const { sheet } = useParams();
  const [sp, setSp] = useSearchParams();
  const nav = useNavigate();
  const qc = useQueryClient();
  const a = useAnalysis(aid);
  useMiShell(a.data, 3, { complete: true });
  const requested = sp.get('requested');
  const text = sp.get('text');
  const c = useCandidates(aid, sheet, { requested, text });
  const v = c.data;
  const [pick, setPick] = useState<'A' | 'B' | 'C' | null>(null);
  const [pin, setPin] = useState<boolean | null>(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => { setPick(null); setPin(null); }, [sheet, requested]);

  const opts = v?.options ?? [];
  const rec = opts.find((o) => o.recommended)?.key ?? opts[0]?.key ?? null;
  const chosen: LayoutOption | undefined = opts.find((o) => o.key === (pick ?? rec));
  const pinned = pin ?? v?.sheet.pinned ?? false;

  async function go() {
    if (!aid || !sheet || !chosen) return;
    setBusy(true);
    try {
      const r = await chooseLayout(aid, sheet, { option: chosen.key, template: chosen.template || v?.requested || v?.sheet.template_code || '', pin: pinned });
      if (r.job) { nav(`/mi/${aid}/run?then=slides`); return; }
      await qc.invalidateQueries({ queryKey: qk.slides(aid) });
      void qc.invalidateQueries({ queryKey: ['mi', 'export-view', aid] });
      nav(`/mi/${aid}/slides`);
    } catch (e) { toast(errText(e)); } finally { setBusy(false); }
  }

  async function axes(t: string) {
    if (!aid) return;
    try {
      const r = await slideRequest(aid, t);
      const next = new URLSearchParams(sp);
      next.set('text', t);
      if (r.kind === 'layout' && r.requested) next.set('requested', r.requested);
      if (r.kind === 'layout' && r.sheet_id && r.sheet_id !== sheet) { nav(`/mi/${aid}/slides/${r.sheet_id}?${next.toString()}`); return; }
      setSp(next, { replace: true });
      void qc.invalidateQueries({ queryKey: ['mi', 'candidates', aid] });
    } catch (e) { toast(errText(e)); }
  }

  const others = (v?.others ?? []) as Array<{ id: string; sheet_name: string; count: number }>;
  const eta = chosen?.eta_s ? ` (약 ${chosen.eta_s}초)` : '';
  return (
    <MiPage dock={
      <Dock title="레이아웃 바꾸기" meta={`${v?.sheet.sheet_name ?? ''} · 나머지 시트는 그대로`}
        right={others.map((o) => <Pill key={o.id} to={`/mi/${aid}/slides/${o.id}`}>{o.sheet_name} {o.count}종 보기</Pill>)}
        row={
          <div className="mi-dock__row">
            <PromptInput label="레이아웃 요청" placeholder="축 지정 (예: 가로는 가격대, 세로는 관리 편의)" onSend={axes} />
            <SecButton to={`/mi/${aid}/slides`}>취소</SecButton>
            <BigButton onClick={() => void go()} busy={busy} disabled={!chosen} testId="mi3l-go">{chosen ? `${chosen.key}로 진행${eta}` : '진행'}</BigButton>
          </div>
        } />
    }>
      {(v?.request_text || text) && <UserBubble>{v?.request_text || text}</UserBubble>}
      <Agent text={v?.explanation ?? '고를 수 있는 레이아웃과 데이터 적합도를 보고 있어요.'}>
        {c.isError && <ErrorBand onRetry={() => void c.refetch()} />}
        {!v && !c.isError && <LoadingCard lines={5} />}
        {v && opts.length > 0 && (
          <div className="mi-lopts" role="radiogroup" aria-label="진행 방법">
            {opts.map((o) => (
              <div key={o.key} role="radio" aria-checked={o.key === chosen?.key} tabIndex={0} className="mi-lopt" data-key={o.key}
                onClick={() => setPick(o.key)} onKeyDown={(e) => { if (e.key === ' ' || e.key === 'Enter') { e.preventDefault(); setPick(o.key); } }}>
                <span className="mi-opt__radio" style={{ marginTop: 0, alignSelf: 'center' }} />
                <span className="mi-lopt__k">{o.key}</span>
                <span className="mi-lopt__t">{o.title}</span>
                {o.recommended && <span className="mi-rec">추천</span>}
                <span className="mi-lopt__d" title={o.desc}>{o.desc}</span>
              </div>
            ))}
          </div>
        )}
        {v && (
          <div className="mi-sheets" data-testid="mi3l-templates">
            <div className="mi-sheets__head">
              <span className="mi-sheets__title" style={{ fontWeight: 700 }}>{v.head.split(' · ').slice(0, 2).join(' · ')}{v.head.split(' · ').length > 2 &&
                <span className="mi-sub"> · {v.head.split(' · ').slice(2).join(' · ')}</span>}</span>
              <span className="mi-sheets__hint">필요한 데이터가 있는지로 적합도를 매겨요</span>
            </div>
            <div className="mi-tpls">
              {v.templates.map((t) => <Tpl key={t.code} t={t} />)}
            </div>
            <label className="mi-check" style={{ minHeight: 22 }}>
              <input type="checkbox" checked={pinned} onChange={(e) => setPin(e.target.checked)} />이 시트 고정 — 데이터가 바뀌어도 다시 고르지 않아요
            </label>
          </div>
        )}
        {v && <Link to={`/mi/${aid}/slides`} className="mi-link mi-link--muted" style={{ alignSelf: 'flex-start' }}>슬라이드 구성으로</Link>}
      </Agent>
    </MiPage>
  );
}

function Tpl({ t }: { t: TemplateCandidate }) {
  const st = t.tag === '사용 중' ? 'cur' : t.tag === '요청' ? 'req' : t.tag === '고를 수 없음' ? 'no' : '';
  return (
    <div className={cx('mi-tpl', st === 'cur' && 'mi-tpl--cur', st === 'req' && 'mi-tpl--req', st === 'no' && 'mi-tpl--no')} data-code={t.code} data-testid="mi3l-tpl">
      <div className="mi-row" style={{ alignItems: 'flex-start', gap: 10 }}>
        <div className={cx('mi-thumb', st === 'no' && 'mi-thumb--dim45')}><Thumb kind={t.thumb_kind} n={3} code={t.code} dim={st === 'no'} /></div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 3, minWidth: 0 }}>
          <span className="mi-tpl__code">{t.code}</span>
          <span className="mi-tpl__name">{t.name}</span>
          {t.tag && <span className={cx('mi-tpl__tag', st === 'cur' && 'mi-tpl__tag--cur', st === 'req' && 'mi-tpl__tag--req')}>{t.tag}</span>}
        </div>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
        {t.needs.map((n, i) => (
          <div key={i} className={cx('mi-need', n.ok ? 'mi-need--ok' : 'mi-need--no')}>
            <Ic d={n.ok ? P.check : P.x} size={12} w={3} /><span title={n.need}>{n.need}</span>
          </div>
        ))}
      </div>
      <div className="mi-row">
        <div className={cx('mi-fit mi-fit--grow', t.fit >= 85 && 'mi-fit--good')}><div style={{ width: `${Math.max(0, t.fit)}%` }} /></div>
        <span className={cx('mi-tpl__fit', t.fit < 0 && 'mi-tpl__fit--no')}>{t.fit < 0 ? (t.fit_label || '고를 수 없음') : `적합 ${t.fit}%`}</span>
      </div>
    </div>
  );
}
