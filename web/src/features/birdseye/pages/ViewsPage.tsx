/** BE5V — 시점 · 조명 바꾸기(`/birdseye/:id/views`, §4.11): 전/후 비교 3 · 만든 컷 · 시점 4 · 조명 3 · 도입 전 컷 · 시점 설명 · 톤 모드. */
import { useMemo, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { Toggle, relativeTime, toast } from '@/ui';
import { be, errText, qk, useBe, useCuts, useLayout, useSpace, type Cut } from '../api';
import { Agent, BePage, Dock, DockLink, Echo, FieldLabel, Loading, MainButton, Pill, SubButton, jo, useBeShell } from '../ui';
import { TONES } from './LayoutPage';

type Preset = 'aerial45' | 'entrance' | 'product_front' | 'top';
const LIGHTS = [{ value: 'day', label: '주간' }, { value: 'evening', label: '저녁' }, { value: 'night', label: '야간' }] as const;
type LightV = typeof LIGHTS[number]['value'];
const LIGHT_LABEL: Record<string, string> = { day: '주간', evening: '저녁', night: '야간' };
/** 화면 표시는 FHD 렌디션(없으면 원본) */
const showUrl = (c?: Cut) => (c ? (c.display_url ?? c.image_url ?? undefined) : undefined);

export default function ViewsPage() {
  const { id = '' } = useParams();
  const [sp] = useSearchParams();
  const nav = useNavigate();
  const qc = useQueryClient();
  const bq = useBe(id);
  const cq = useCuts(id);
  const lq = useLayout(id);
  const sq = useSpace(id);
  const toneMode = sp.get('mode') === 'tone';
  const request = sp.get('request');
  const [views, setViews] = useState<Preset[]>([]);
  const [lights, setLights] = useState<LightV[]>([]);
  const [before, setBefore] = useState(false);
  const [custom, setCustom] = useState('');
  const [tone, setTone] = useState<string | null>(null);
  const [cmp, setCmp] = useState<'side' | 'slide' | 'daynight'>('side');
  const [slide, setSlide] = useState(50);
  const [busy, setBusy] = useState(false);
  useBeShell(bq.data, 5);

  const cuts = (cq.data ?? []).filter((c) => c.status !== 'canceled' && c.status !== 'failed');
  const b = bq.data;
  const primary = cuts.find((c) => c.id === b?.primary_cut_id) ?? cuts.find((c) => !c.before && ['done', 'check', 'draft'].includes(c.status));
  const lightsSel: LightV[] = lights.length ? lights : [((primary?.light as LightV) ?? 'day')];
  const lay = lq.data?.layout;
  const bigName = useMemo(() => {
    const disp = (lay?.items ?? []).filter((it) => it.kind === 'product' && it.mount !== 'window_facing');
    const big = disp.sort((a, b2) => b2.w * b2.h - a.w * a.h)[0];
    return big ? (big.tiny || big.short || '제품') : null;
  }, [lay]);
  const curTone = tone ?? primary?.tone ?? b?.tone ?? 'warm_wood';
  const lv = b?.layout_version ?? 0;
  const exists = (preset: string, light: string, bf: boolean, tn: string, custom_text?: string) =>
    cuts.some((c) => !c.stale && c.layout_version === lv && c.view.preset === preset && c.light === light && c.before === bf && c.tone === tn
      && (preset !== 'custom' || c.view.custom_text === custom_text));
  const specs = useMemo(() => {
    const out: Array<{ preset: string; light: string; before: boolean; custom?: string }> = [];
    if (toneMode && primary) {
      if (curTone !== primary.tone || views.length === 0) {
        out.push({ preset: primary.view.preset, light: primary.light, before: false, custom: primary.view.custom_text ?? undefined });
      }
    }
    const vs: Array<{ preset: string; custom?: string }> = views.map((v) => ({ preset: v }));
    if (custom.trim()) vs.push({ preset: 'custom', custom: custom.trim() });
    for (const v of vs) for (const l of lightsSel) for (const bf of before ? [false, true] : [false]) out.push({ preset: v.preset, light: l, before: bf, custom: v.custom });
    return out.filter((s) => !exists(s.preset, s.light, s.before, curTone, s.custom));
  }, [views, lightsSel, before, custom, cuts, curTone, toneMode]); // eslint-disable-line react-hooks/exhaustive-deps
  const N = specs.length;

  if (bq.isLoading || cq.isLoading) return <Loading />;
  const spaceName = sq.data?.space_name || '공간';
  const beforeCut = primary ? cuts.find((c) => c.before && c.view.preset === primary.view.preset && ['done', 'check', 'draft'].includes(c.status)) : undefined;
  const nightCut = primary ? cuts.find((c) => !c.before && c.view.preset === primary.view.preset && c.light !== primary.light && ['done', 'check', 'draft'].includes(c.status)) : undefined;
  const leftCut = cmp === 'daynight' ? primary : beforeCut;
  const rightCut = cmp === 'daynight' ? nightCut : primary;
  const w = beforeCut
    ? `배치는 그대로 두고 카메라와 조명만 바꿨어요. 도입 전 컷은 같은 시점에서 제품과 가구를 뺀 모습이라 지금 ${jo(spaceName, '과', '와')} 나란히 비교할 수 있습니다.`
    : '배치는 그대로 두고 카메라와 조명만 바꿔 새 컷을 만들어요.';
  const queued = cuts.filter((c) => c.status === 'queued');
  const status = (c: Cut) => {
    if (leftCut?.id === c.id && cmp !== 'daynight') return '비교 중 · 도입 전';
    if (rightCut?.id === c.id && cmp !== 'daynight') return '비교 중 · 도입 후';
    if ((leftCut?.id === c.id || rightCut?.id === c.id) && cmp === 'daynight') return `비교 중 · ${LIGHT_LABEL[c.light]}`;
    if (c.status === 'running') return `생성 중 ${Math.round(c.progress)}%`;
    if (c.status === 'queued') { const k = queued.findIndex((x) => x.id === c.id) + 1; return k === 1 ? '대기열 1' : `대기열 ${k}`; }
    if (c.status === 'check') return '확인 필요';
    return `완료 · ${relativeTime(c.finished_at ?? c.created_at)}`;
  };
  const make = async () => {
    setBusy(true);
    try {
      let firstRoute: string | null = null;
      if (toneMode && primary && tone && tone !== primary.tone) await be.patch(id, { tone: tone as never });
      const groups = new Map<string, typeof specs>();
      for (const s of specs.filter((x) => !x.before)) { const k = `${s.light}|${s.before}`; if (!groups.has(k)) groups.set(k, []); groups.get(k)!.push(s); }
      for (const list of groups.values()) {
        const acc = await be.createCuts(id, {
          views: list.map((s) => (s.preset === 'custom' ? { custom_text: s.custom } : { preset: s.preset as never })), lights: [list[0].light as LightV],
          before: false, tone: curTone as never, primary: false, auto_extra: false,
        });
        firstRoute = firstRoute ?? acc.route ?? null;
      }
      const bf = specs.filter((s) => s.before);
      for (const s of bf) {
        const acc = await be.createCuts(id, { views: [s.preset === 'custom' ? { custom_text: s.custom } : { preset: s.preset as never }], lights: [s.light as LightV], before: true,
          tone: curTone as never, primary: false, auto_extra: false });
        firstRoute = firstRoute ?? acc.route ?? null;
      }
      // 첫 컷의 진행 화면으로 바로 간다(목록을 다시 읽느라 기다리지 않는다 — 대기열 순서는 BE5G 가 보여 준다)
      void qc.invalidateQueries({ queryKey: qk.cuts(id) });
      nav(firstRoute ?? `/birdseye/${id}/result`);
    } catch (e) { toast(errText(e)); setBusy(false); }
  };
  const toggleView = (v: Preset) => setViews((cur) => (cur.includes(v) ? cur.filter((x) => x !== v) : [...cur, v]));
  /** 처음 고르는 조명은 기본값(주 컷 조명)을 갈아 끼운다 — 「입구 시점 + The Wall 정면, 야간」 = 2컷(§4.11). 그다음부터는 여러 개 */
  const toggleLight = (l: LightV) => setLights((cur) => {
    if (!cur.length) return [l];
    return cur.includes(l) ? cur.filter((x) => x !== l) : [...cur, l];
  });

  return (
    <BePage testId="be5v" dock={(
      <Dock title="시점 · 조명 바꾸기" meta={<>5 / 5 · 새로 만들 컷 <span data-testid="be5v-n">{N}</span></>}
        right={beforeCut ? <DockLink to={`/birdseye/${id}/export?map=BV-B`}>전/후 2컷을 제안서 '두 시점 비교'로</DockLink> : undefined}
        foot={(
          <>
            <div className="be-prompt" style={{ flex: 1 }}>
              <label htmlFor="be5v-custom" className="wm-sr-only">시점 설명</label>
              <input id="be5v-custom" value={custom} onChange={(e) => setCustom(e.target.value)} placeholder="원하는 시점을 말로 설명해도 돼요 (예: 2층 난간에서 내려다본 시점)" />
            </div>
            <SubButton to={`/birdseye/${id}/result`}>결과로</SubButton>
            <MainButton onClick={make} busy={busy} disabled={N === 0} reason="새로 만들 컷이 없어요" testId="be5v-make">선택한 {N}컷 생성</MainButton>
          </>
        )}>
        {toneMode && (
          <div className="be-row">
            <FieldLabel>인테리어 톤</FieldLabel>
            {TONES.map((t) => <Pill key={t.value} on={curTone === t.value} swatch={t.swatch} onClick={() => setTone(t.value)}>{t.label}</Pill>)}
          </div>
        )}
        <div className="be-row">
          <FieldLabel>시점</FieldLabel>
          <Pill on={views.includes('aerial45')} onClick={() => toggleView('aerial45')}>조감 45°</Pill>
          <Pill on={views.includes('entrance')} onClick={() => toggleView('entrance')} testId="be5v-entrance">입구 시점</Pill>
          {bigName && <Pill on={views.includes('product_front')} onClick={() => toggleView('product_front')} testId="be5v-front">{bigName} 정면</Pill>}
          <Pill on={views.includes('top')} onClick={() => toggleView('top')}>탑뷰</Pill>
        </div>
        <div className="be-row">
          <FieldLabel>조명</FieldLabel>
          {LIGHTS.map((l) => <Pill key={l.value} on={lightsSel.includes(l.value)} onClick={() => toggleLight(l.value)} testId={`be5v-light-${l.value}`}>{l.label}</Pill>)}
          <span className="be-sep" />
          <Toggle checked={before} onChange={setBefore}>도입 전 컷도</Toggle>
        </div>
      </Dock>
    )}>
      {request && <Echo text={request} />}
      <Agent text={w}>
        <div className="be-row" role="group" aria-label="비교 보기">
          <Pill on={cmp === 'side'} onClick={() => setCmp('side')} disabled={!beforeCut} title="도입 전 컷이 있어야 비교할 수 있어요">나란히</Pill>
          <Pill on={cmp === 'slide'} onClick={() => setCmp('slide')} disabled={!beforeCut} title="도입 전 컷이 있어야 비교할 수 있어요">겹쳐 밀기</Pill>
          <Pill on={cmp === 'daynight'} onClick={() => setCmp('daynight')} disabled={!nightCut} title="같은 시점의 다른 조명 컷이 있어야 해요">주간 / 야간</Pill>
        </div>
        {cmp === 'slide' && leftCut && rightCut ? (
          <div className="be-slider">
            <img src={showUrl(rightCut)} alt="도입 후" />
            <img src={showUrl(leftCut)} alt="도입 전" style={{ clipPath: `inset(0 ${100 - slide}% 0 0)` }} />
            <input type="range" min={0} max={100} value={slide} onChange={(e) => setSlide(Number(e.target.value))} aria-label="겹쳐 밀기" />
          </div>
        ) : (
          <div className="be-compare" data-testid="be5v-compare">
            <figure>
              <div className="be-preview">{showUrl(leftCut) ? <img src={showUrl(leftCut)} alt="" /> : null}</div>
              <figcaption>{cmp === 'daynight' ? <><b>{primary?.label}</b></> : <><b>도입 전 · 현재 {spaceName}</b>제품 · 가구를 뺀 같은 시점</>}</figcaption>
            </figure>
            <figure>
              <div className="be-preview">{showUrl(rightCut) ? <img src={showUrl(rightCut)} alt="" /> : null}</div>
              <figcaption>{cmp === 'daynight' ? <b>{nightCut?.label}</b> : <b>도입 후 · {primary?.view.label} {LIGHT_LABEL[primary?.light ?? 'day']}</b>}</figcaption>
            </figure>
          </div>
        )}
        <div className="be-sec">
          <div className="be-sec__head"><b>만든 컷</b><span>· {cuts.length}</span><span style={{ marginLeft: 'auto' }}>테두리 표시된 2컷을 비교 중</span></div>
          <div className="be-cutrows" data-testid="be5v-cuts">
            {cuts.map((c) => (
              <div key={c.id} className={leftCut?.id === c.id || rightCut?.id === c.id ? 'be-cutrow be-cutrow--cmp' : 'be-cutrow'}>
                {c.thumb_url ? <img src={c.thumb_url} alt="" /> : <span className="ph" />}
                <span className="grow">{c.id === primary?.id && <span className="be-tagline">원본</span>}{c.label}</span>
                <span className="st">{status(c)}</span>
              </div>
            ))}
          </div>
        </div>
      </Agent>
    </BePage>
  );
}
