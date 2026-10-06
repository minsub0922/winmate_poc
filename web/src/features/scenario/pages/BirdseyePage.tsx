/**
 * SC1B · 조감도에서 이어 만들기(§4.4) — 조감도 작업 고르기, 평면 미리보기(존 번호), 가져올 존(제품 · 가구만 · 빈 존), 시나리오 축 3,
 * 동선 순서(끌어서 바꾸기), 조감도와 연결 유지 → 가져오기 잡 → SC2E.
 * 변경 반영 모드(`/scenario/:id/birdseye`, SC0 「변경 반영하기」): 변경 요약 · 존 변경 배지 · 「바뀐 곳 반영하기」.
 */
import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router';
import { useQuery } from '@tanstack/react-query';
import { cx, ErrorState } from '@/ui';
import { useShellPage } from '@/shell';
import { errMessage, scApi, type BirdseyePreview, type ZoneRow } from '../api';
import { qk, useInvalidate, useScenario } from '../hooks';
import { route, SECTION, stepper } from '../lib';
import { Btn, Card, Echo, Ico, Loading, NextButton, Note, P, Screen, W } from '../parts';

const CHANGE_LABEL: Record<string, string> = { new: '새로', changed: '바뀜', removed: '없어짐' };

export default function BirdseyePage({ resync = false }: { resync?: boolean }) {
  const { id } = useParams();
  const [sp, setSp] = useSearchParams();
  const nav = useNavigate();
  const inv = useInvalidate();
  const sc = useScenario(resync ? id : null);
  const type = (sp.get('type') === 'without' ? 'without' : 'with') as 'with' | 'without';
  const opts = useQuery({ queryKey: qk.beOptions(), queryFn: scApi.birdseyeOptions, staleTime: 30_000, retry: 0 });
  const beId = resync ? sc.data?.birdseye_link?.birdseye_id ?? null : sp.get('birdseye') || opts.data?.items?.[0]?.id || null;
  const prev = useQuery({ queryKey: ['scenario', 'be-preview', beId, resync ? id : null], queryFn: () => scApi.birdseyePreview(beId!, resync ? id : null), enabled: !!beId, retry: 0 });
  const [sel, setSel] = useState<string[] | null>(null);
  const [axis, setAxis] = useState<string | null>(null);
  const [order, setOrder] = useState<string[] | null>(null);
  const [keep, setKeep] = useState(true);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [dragZ, setDragZ] = useState<string | null>(null);

  useEffect(() => { setSel(null); setAxis(null); setOrder(null); }, [beId]);
  useShellPage({ section: SECTION, title: resync ? sc.data?.title ?? '' : '새 작업', stepper: stepper(2), sidebarGroup: 'scenario' });

  const p = prev.data;
  const zones = p?.zones ?? [];
  const selected = sel ?? zones.filter((z) => z.included).map((z) => z.id);
  const curAxis = axis ?? p?.axes?.[0] ?? '방문객 동선';
  const baseOrder = order ?? (p?.order?.length ? p.order : zones.map((z) => z.id));
  const ordered = useMemo(() => {
    const inOrder = baseOrder.filter((z) => selected.includes(z));
    for (const z of selected) if (!inOrder.includes(z)) inOrder.push(z);
    return inOrder;
  }, [baseOrder, selected]);
  const byId = new Map(zones.map((z) => [z.id, z]));

  if ((resync && sc.isLoading) || opts.isLoading || (beId && prev.isLoading)) return <Loading />;
  if (opts.data && opts.data.available === false && !resync) {
    return <Screen testId="sc1b"><W>조감도 서비스에 연결할 수 없어요. 잠시 뒤 다시 시도하거나 빈 시나리오로 시작해 주세요.</W><Btn to={route.newType()}>빈 시나리오로</Btn></Screen>;
  }
  if (!beId) {
    return (
      <Screen testId="sc1b">
        <Echo><b>조감도에서 이어 만들기</b> · {type === 'with' ? 'with 솔루션' : 'without 솔루션'}</Echo>
        <W extra={<div className="sc-row"><Btn to="/birdseye/new" testId="sc1b-new-be">조감도 만들기</Btn><Btn to={route.newType()}>빈 시나리오로</Btn></div>}>
          아직 존 포인트가 있는 조감도 작업이 없어요. 조감도를 먼저 만들거나 빈 시나리오로 시작해 주세요.
        </W>
      </Screen>
    );
  }
  if (prev.isError || !p) return <div style={{ padding: 40 }}><ErrorState message={`조감도를 읽지 못했어요 · ${errMessage(prev.error)}`} onRetry={() => prev.refetch()} /></div>;

  const toggle = (zid: string) => setSel(selected.includes(zid) ? selected.filter((x) => x !== zid) : [...selected, zid]);
  const start = async () => {
    setBusy(true); setErr(null);
    try {
      const r = await scApi.fromBirdseye({ birdseye_id: beId, zone_ids: ordered, axis: curAxis, order: ordered, keep_link: keep, type });
      nav(route.timeline(r.scenario_id));
    } catch (e) { setErr(errMessage(e)); setBusy(false); }
  };
  const apply = async () => {
    if (!id) return;
    setBusy(true); setErr(null);
    try {
      await scApi.resync(id, true);
      await inv.sc(id); await inv.scenes(id);
      const fresh = await scApi.get(id);
      nav(fresh.route);
    } catch (e) { setErr(errMessage(e)); setBusy(false); }
  };
  const k = ordered.length;
  const rs = p.resync;

  const dock = resync ? (
    <Card title="변경 반영" meta="장면의 장소 · 제품만 바꾸고 문장은 그대로 둬요" testId="sc1b-resync-card"
      right={<Link to={`/birdseye/${beId}/zones`} className="sc-link">존 포인트 다시 지정</Link>}
      foot={<>
        <Btn to={route.list()} testId="sc1b-prev">이전</Btn>
        <NextButton onClick={() => void apply()} busy={busy} testId="sc1b-apply">바뀐 곳 반영하기</NextButton>
      </>}>
      <div className="sc-card__sec"><div className="sc-infobox" data-testid="sc1b-summary">
        <Ico d={P.warn} size={16} color="var(--wm-text)" style={{ marginTop: 2 }} />
        <span>{rs?.summary || '바뀐 존이 없어요'} · 제품이 바뀐 장면에는 「이야기 확인」 표시와 이미지 확인 표시가 붙어요.</span>
      </div></div>
      {err && <div className="sc-card__sec"><Note tone="err">{err}</Note></div>}
    </Card>
  ) : (
    <Card title="가져오기 설정" meta={`존 ${k}개 → 장면 ${k}개 · 2 / 4`} testId="sc1b-card"
      right={<Link to={`/birdseye/${beId}/zones`} className="sc-link" data-testid="sc1b-zones-link">존 포인트 다시 지정</Link>}>
      <div className="sc-kv" style={{ paddingTop: 10 }} data-testid="sc1b-axes">
        <span className="sc-label" style={{ width: 72 }}>시나리오 축</span>
        {(p.axes ?? []).map((a) => (
          <button key={a} type="button" className="sc-pill sc-pill--h30" aria-pressed={a === curAxis} onClick={() => setAxis(a)} data-testid="sc1b-axis">
            {a === curAxis && <Ico d={P.check} size={11} sw={3} />}{a}
          </button>
        ))}
      </div>
      <div className="sc-kv" data-testid="sc1b-order">
        <span className="sc-label" style={{ width: 72 }}>동선 순서</span>
        {ordered.map((zid, i) => {
          const z = byId.get(zid);
          return (
            <span key={zid} className="sc-row" style={{ gap: 6 }}>
              {i > 0 && <Ico d={P.arrow} size={14} sw={2.2} color="var(--wm-text-subtle)" />}
              <span className={cx('sc-ochip', dragZ === zid && 'sc-ochip--drag')} draggable data-testid="sc1b-order-chip"
                onDragStart={(e) => { e.dataTransfer.setData('application/x-sc-zone', zid); setDragZ(zid); }} onDragEnd={() => setDragZ(null)}
                onDragOver={(e) => { if (e.dataTransfer.types.includes('application/x-sc-zone')) e.preventDefault(); }}
                onDrop={(e) => {
                  const from = e.dataTransfer.getData('application/x-sc-zone');
                  setDragZ(null);
                  if (!from || from === zid) return;
                  e.preventDefault();
                  const next = ordered.filter((x) => x !== from);
                  next.splice(next.indexOf(zid), 0, from);
                  setOrder(next);
                }}>
                <b className="wm-num">{i + 1}</b>{z?.short_name ?? zid}
              </span>
            </span>
          );
        })}
        <span style={{ fontSize: 11.5, color: 'var(--wm-text-subtle)', marginLeft: 4, whiteSpace: 'nowrap' }}>끌어서 순서 바꾸기</span>
      </div>
      {err && <div className="sc-card__sec"><Note tone="err">{err}</Note></div>}
      <div className="sc-card__foot sc-card__foot--split">
        <label className="sc-row" style={{ gap: 8, minWidth: 0, cursor: 'pointer' }}>
          <input type="checkbox" className="sc-check" checked={keep} onChange={(e) => setKeep(e.target.checked)} data-testid="sc1b-keep" />
          <span style={{ fontSize: 12.5, whiteSpace: 'nowrap' }}>조감도와 연결 유지</span>
          <span className="wm-ellipsis" style={{ fontSize: 12, color: 'var(--wm-text-muted)' }}>· 배치가 바뀌면 알려드려요</span>
        </label>
        <div className="sc-row" style={{ flexShrink: 0 }}>
          <Btn to={route.list()} testId="sc1b-prev">이전</Btn>
          <NextButton onClick={() => void start()} busy={busy} disabled={k === 0} reason="가져올 존을 하나 이상 고르세요" testId="sc1b-start">존으로 장면 만들기</NextButton>
        </div>
      </div>
    </Card>
  );

  return (
    <Screen dock={dock} tight testId="sc1b">
      <Echo testId="sc1b-echo"><b>{resync ? '조감도 변경 반영' : '조감도에서 이어 만들기'}</b> · {resync ? sc.data?.title : type === 'with' ? 'with 솔루션' : 'without 솔루션'}</Echo>
      <W testId="sc1b-w" extra={(
        <>
          {!resync && (
            <div className="sc-row" style={{ gap: 6, minHeight: 32 }} data-testid="sc1b-options">
              <span className="sc-label" style={{ marginRight: 4 }}>조감도 작업</span>
              <div className="sc-row" style={{ gap: 6, overflow: 'auto', flex: 1 }}>
                {(opts.data?.items ?? []).map((b) => (
                  <button key={b.id} type="button" className={cx('sc-bepill', b.id === beId && 'sc-bepill--on')} aria-pressed={b.id === beId}
                    onClick={() => setSp((cur) => { const n = new URLSearchParams(cur); n.set('birdseye', b.id); return n; }, { replace: true })} data-testid="sc1b-option">
                    {b.id === beId && <Ico d={P.cube} size={13} />}<span>{b.title}</span><small>· 존 {b.zone_count}</small>
                  </button>
                ))}
              </div>
              <Link to={`/birdseye/${beId}/result`} className="sc-link" style={{ fontSize: 12 }}>조감도 열기<Ico d="M7 17L17 7M9 7h8v8" size={12} sw={2.2} /></Link>
            </div>
          )}
          {resync && rs && <div className="sc-w__note" data-testid="sc1b-resync-summary"><Ico d={P.warn} size={13} />{rs.summary}</div>}
          <div className="sc-row" style={{ gap: 12, alignItems: 'stretch' }}>
            <PlanMap p={p} selected={selected} />
            <div className="sc-zones" data-testid="sc1b-zones">
              <div className="sc-row" style={{ justifyContent: 'space-between', height: 22 }}>
                <span style={{ fontSize: 13, fontWeight: 600 }} data-testid="sc1b-zones-head">가져올 존 <span style={{ color: 'var(--wm-text-muted)', fontWeight: 500 }}>· {selected.length} / {zones.length} 선택</span></span>
                {!resync && <button type="button" className="sc-link" style={{ fontSize: 12 }} onClick={() => setSel(zones.map((z) => z.id))} data-testid="sc1b-all">모두 선택</button>}
              </div>
              {zones.map((z) => <ZoneItem key={z.id} z={z} on={selected.includes(z.id)} no={ordered.indexOf(z.id) + 1} onToggle={resync ? undefined : () => toggle(z.id)} />)}
            </div>
          </div>
        </>
      )}>
        조감도의 존을 시나리오 공간으로 가져옵니다. 존에 배치된 제품도 함께 넘어와 장면에 바로 들어갑니다.
      </W>
    </Screen>
  );
}

function ZoneItem({ z, on, no, onToggle }: { z: ZoneRow; on: boolean; no: number; onToggle?: () => void }) {
  const change = z.change && z.change !== 'same' ? CHANGE_LABEL[z.change] : null;
  return (
    <label className={cx('sc-zone', !on && 'sc-zone--off')} data-testid="sc1b-zone" data-state={z.state}>
      {onToggle ? <input type="checkbox" className="sc-check" checked={on} onChange={onToggle} aria-label={`${z.name} 가져오기`} /> : null}
      <span className={cx('sc-zone__n wm-num', !on && 'sc-zone__n--off')}>{z.n}</span>
      <span style={{ display: 'flex', flexDirection: 'column', gap: 1, minWidth: 0, flex: 1 }}>
        <span className="sc-zone__name">{z.name}</span>
        <span className="sc-zone__sub">{z.sub}</span>
      </span>
      {change && <span className={cx('sc-tag', z.change === 'removed' ? 'sc-tag--warn' : 'sc-tag--brand')} data-testid="sc1b-zone-change">{change}</span>}
      <span className={cx('sc-tag', on && 'sc-tag--brand')} data-testid="sc1b-zone-badge">{on && no > 0 ? `장면 ${no}` : '제외'}</span>
    </label>
  );
}

/** 평면 미리보기(handoff.plan_preview) — 존 번호 원 · 제품 · 가구 */
function PlanMap({ p, selected }: { p: BirdseyePreview; selected: string[] }) {
  const plan = (p.plan ?? {}) as Record<string, unknown>;
  const W_ = Number(plan.width_m) || 0;
  const H_ = Number(plan.height_m) || 0;
  const pts = ((plan.zones as Array<{ id: string; n: number; x?: number | null; y?: number | null }> | undefined) ?? [])
    .filter((z) => typeof z.x === 'number' && typeof z.y === 'number');
  const items = (plan.items as Array<{ kind: string; x: number; y: number; w: number; d: number }> | undefined) ?? [];
  // birdseye 평면 좌표는 미터(width_m × height_m). 0..1 로만 온 미리보기(존 u · v 대신 그리기)는 그대로 비율로 쓴다
  const meters = W_ > 0 && H_ > 0 && [...pts, ...items].some((z) => (z.x as number) > 1 || (z.y as number) > 1);
  const norm = (x: number, y: number) => {
    const fx = meters ? x / W_ : x;
    const fy = meters ? y / H_ : y;
    return { x: 20 + Math.min(1, Math.max(0, fx)) * 380, y: 40 + Math.min(1, Math.max(0, fy)) * 232 };
  };
  const area = (plan.area_label as string | undefined) ?? [plan.area_pyeong ? `${plan.area_pyeong}평` : '', plan.ceiling_h_m ? `층고 ${plan.ceiling_h_m}m` : ''].filter(Boolean).join(' · ');
  return (
    <div className="sc-plan" data-testid="sc1b-plan">
      <div className="sc-plan__tags">
        <span className="sc-plan__count">존 포인트 {Number(plan.zone_count) || p.zones.length}</span>
        {area && <span className="sc-plan__area">{area}</span>}
      </div>
      <div className="sc-plan__legend"><span><i className="sc-plan__lp" />삼성 제품</span><span><i className="sc-plan__lf" />가구</span></div>
      <svg viewBox="0 0 420 316" width="420" height="316" aria-hidden="true">
        <rect x="20" y="40" width="380" height="232" className="sc-plan__floor" />
        {W_ > 0 && H_ > 0 && items.map((it, i) => {
          const a = norm(it.x, it.y);
          const w = Math.max(6, (it.w / W_) * 380);
          const h = Math.max(4, (it.d / H_) * 232);
          return <rect key={i} x={a.x - w / 2} y={a.y - h / 2} width={w} height={h} rx="2" className={it.kind === 'product' ? 'sc-plan__prod' : 'sc-plan__furn'} />;
        })}
        {pts.map((z) => {
          const a = norm(z.x as number, z.y as number);
          const on = selected.includes(z.id);
          return (
            <g key={z.id}>
              <circle cx={a.x} cy={a.y} r="10" className={on ? 'sc-plan__pin' : 'sc-plan__pin sc-plan__pin--off'} />
              <text x={a.x} y={a.y + 4} textAnchor="middle" className={on ? 'sc-plan__pint' : 'sc-plan__pint sc-plan__pint--off'}>{z.n}</text>
            </g>
          );
        })}
      </svg>
      {typeof plan.window_label === 'string' && <span className="sc-plan__window">{plan.window_label}</span>}
    </div>
  );
}
