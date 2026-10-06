/**
 * SC1T · 업종 템플릿에서 시작(§4.3) — 업종 16 타일 · 검색, 유형, 장면 프리셋 3, 대표 공간 · 요구 · 자주 쓰인 것 → 골격 잡 → SC2E.
 * `?industry=FB&preset=1` 로 고른 값을 URL 에 둔다.
 */
import { useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router';
import { useQuery } from '@tanstack/react-query';
import { ErrorState } from '@/ui';
import { useShellPage } from '@/shell';
import { errMessage, scApi } from '../api';
import { qk } from '../hooks';
import { route, SECTION, stepper } from '../lib';
import { Btn, Card, Ico, Loading, NextButton, Note, P, Screen, W } from '../parts';

export default function TemplatePage() {
  const nav = useNavigate();
  const [sp, setSp] = useSearchParams();
  const [q, setQ] = useState('');
  const [type, setType] = useState<'with' | 'without'>('with');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const project = sp.get('project');
  const inds = useQuery({ queryKey: [...qk.industries(), project], queryFn: () => scApi.industries(project), staleTime: 300_000 });
  useShellPage({ section: SECTION, title: '새 작업', stepper: stepper(1), sidebarGroup: 'scenario' });

  const items = inds.data?.items ?? [];
  const code = sp.get('industry') || inds.data?.default_code || 'FB';
  const presetIdx = Math.min(3, Math.max(1, Number(sp.get('preset') || 1)));
  const sel = items.find((i) => i.code === code) ?? items[0];
  const shown = useMemo(() => {
    const t = q.trim();
    if (!t) return items;
    return items.filter((i) => [i.name, i.short, ...i.spaces].some((s) => s.includes(t)));
  }, [items, q]);
  const pick = (c: string, preset = 1) => setSp((p) => { const n = new URLSearchParams(p); n.set('industry', c); n.set('preset', String(preset)); return n; }, { replace: true });

  if (inds.isLoading) return <Loading />;
  if (inds.isError || !sel) return <div style={{ padding: 40 }}><ErrorState message="업종 템플릿을 불러오지 못했어요" onRetry={() => inds.refetch()} /></div>;

  const start = async () => {
    setBusy(true); setErr(null);
    try {
      const r = await scApi.fromTemplate({ industry: sel.code, preset_index: presetIdx, type, project_id: project || undefined });
      nav(route.timeline(r.scenario_id));
    } catch (e) { setErr(errMessage(e)); setBusy(false); }
  };

  const dock = (
    <Card title={sel.name} meta="장면 프리셋 하나 선택 · 1 / 4" testId="sc1t-card"
      right={(
        <div className="sc-row">
          <span className="sc-label">유형</span>
          <div className="sc-segb" role="group" aria-label="유형">
            <button type="button" aria-pressed={type === 'with'} onClick={() => setType('with')} data-testid="sc1t-type-with">WITH 솔루션</button>
            <button type="button" aria-pressed={type === 'without'} onClick={() => setType('without')} data-testid="sc1t-type-without">WITHOUT</button>
          </div>
        </div>
      )}>
      <div className="sc-presets" role="radiogroup" aria-label="장면 프리셋" data-testid="sc1t-presets">
        {sel.presets.map((p, i) => (
          <button key={p.t} type="button" role="radio" aria-checked={presetIdx === i + 1} className="sc-preset" onClick={() => pick(sel.code, i + 1)} data-testid="sc1t-preset">
            <div className="sc-row" style={{ width: '100%', justifyContent: 'space-between', gap: 6 }}>
              <span className="sc-preset__t">{p.t}</span>
              <span className={presetIdx === i + 1 ? 'sc-tag sc-tag--solid' : 'sc-tag'}>{p.n}</span>
            </div>
            <div className="sc-preset__f">{p.f}</div>
            <div className="sc-preset__r"><Ico d={P.user} size={12} /><span>{p.r}</span></div>
          </button>
        ))}
      </div>
      <div className="sc-kv" style={{ paddingTop: 10 }} data-testid="sc1t-spaces">
        <span className="sc-label">대표 공간</span>
        {sel.spaces.map((s) => <span key={s} className="sc-chip sc-chip--line sc-chip--plain"><Ico d={P.pin} size={11} sw={2.2} color="var(--wm-text-muted)" />{s}</span>)}
      </div>
      <div className="sc-kv" data-testid="sc1t-needs">
        <span className="sc-label">장면에 담을 요구</span>
        {sel.needs.map((s) => <span key={s} className="sc-chip sc-chip--plain">{s}</span>)}
      </div>
      {err && <div className="sc-card__sec"><Note tone="err">{err}</Note></div>}
      <div className="sc-card__foot sc-card__foot--split">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 2, minWidth: 0, flex: 1 }}>
          <span className="sc-hint sc-hint--sm">솔루션 · 제품 단계에 미리 채움 <span style={{ color: 'var(--wm-text-subtle)' }}>· 이 업종에서 자주 쓰인 순</span></span>
          <span className="wm-ellipsis" style={{ fontSize: 12.5 }} data-testid="sc1t-used">{sel.used_line}</span>
        </div>
        <div className="sc-row" style={{ flexShrink: 0 }}>
          <Btn to={route.newType()} testId="sc1t-blank">빈 시나리오로</Btn>
          <NextButton onClick={() => void start()} busy={busy} testId="sc1t-start">이 골격으로 시작</NextButton>
        </div>
      </div>
    </Card>
  );

  return (
    <Screen dock={dock} tight testId="sc1t">
      <div className="sc-w">
        <span className="sc-w__logo" aria-hidden="true">W</span>
        <div className="sc-w__body" style={{ gap: 8 }}>
          <div className="sc-w__text">업종을 고르면 그 업종 도입사례에 자주 나온 공간과 장면으로 시나리오 골격을 미리 채워 드립니다.</div>
          <div className="sc-row" style={{ justifyContent: 'space-between', minHeight: 30 }}>
            <div className="sc-label">업종 {items.length}개 <span style={{ color: 'var(--wm-text-subtle)' }}>· 삼성 B2B 도입사례로 나눔 · 공간 · 장면 프리셋 포함</span></div>
            <div className="sc-search" style={{ width: 210, height: 30 }}>
              <Ico d="M11 4a7 7 0 1 0 0 14a7 7 0 1 0 0-14 M20 20l-4-4" size={13} sw={2.2} color="var(--wm-text-subtle)" />
              <label htmlFor="sc1t-q" className="wm-sr-only">업종 · 공간 검색</label>
              <input id="sc1t-q" value={q} onChange={(e) => setQ(e.target.value)} placeholder="업종 · 공간 검색" autoComplete="off" />
            </div>
          </div>
          <div className="sc-inds" role="radiogroup" aria-label="업종" data-testid="sc1t-tiles">
            {shown.map((i) => (
              <button key={i.code} type="button" role="radio" aria-checked={i.code === sel.code} className="sc-ind" onClick={() => pick(i.code)} data-testid="sc1t-tile" data-code={i.code}>
                <span className="sc-ind__name">{i.name}</span>
                <span className="sc-ind__spaces">{i.space_line}</span>
                <span className="sc-ind__presets"><Ico d={P.play} size={11} sw={2.2} /><span>{i.preset_line}</span></span>
                {i.code === sel.code && <span className="sc-ind__check"><Ico d={P.check} size={10} sw={3} /></span>}
              </button>
            ))}
            {shown.length === 0 && <span className="sc-hint" style={{ gridColumn: '1 / -1' }}>맞는 업종이 없어요</span>}
          </div>
        </div>
      </div>
    </Screen>
  );
}
