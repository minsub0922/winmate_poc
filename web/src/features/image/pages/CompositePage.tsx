/**
 * IMG2P · 현장 사진 제품 합성(§4.5) — 사진 탭 · 벽면 인식 · 배치 캔버스(끌어 이동 · 손잡이 8개 크기 · 원근 4점) · 배열/설치 · 기준 치수 · 토글.
 * 배치는 300ms 디바운스로 `PUT placements` → 응답의 실제 크기 라벨(「가로 약 W mm · 바닥에서 H mm」, 모르면 [00]).
 * 「합성 이미지 4장 생성」 → run(composite) → IMG3G. 현장 사진은 고객 자료라 기밀로 올린다.
 */
import { useCallback, useEffect, useMemo, useRef, useState, type PointerEvent as RPointerEvent } from 'react';
import { useNavigate, useParams } from 'react-router';
import { useQuery } from '@tanstack/react-query';
import { Button, cx, ErrorState, Icon, Img, useDropTarget } from '@/ui';
import { useOpenPopover } from '@/shell';
import { ApiError, errMessage, img, uploadFile, type PlacementGroup, type SitePhoto } from '../api';
import { Ico, Loading, PATH, Screen, Switch, useDebounced, useImgShell, WSay } from '../components';
import { qk, useInvalidate, useWork } from '../hooks';
import { checkUpload, route, UPLOAD_ACCEPT } from '../lib';

type Pt = [number, number];
type Quad = [Pt, Pt, Pt, Pt];
const ARR_LABEL: Record<string, string> = { row3: '가로 3연', col3: '세로 3연', separate: '따로 배치', single: '단독' };
const CANVAS_H = 330;

const toQuad = (q?: number[][] | null): Quad => (q && q.length === 4 ? q.map((p) => [p[0], p[1]] as Pt) as Quad : [[0.3, 0.3], [0.7, 0.3], [0.7, 0.5], [0.3, 0.5]]);
const bbox = (q: Quad) => { const xs = q.map((p) => p[0]); const ys = q.map((p) => p[1]); return { x0: Math.min(...xs), y0: Math.min(...ys), x1: Math.max(...xs), y1: Math.max(...ys) }; };
const isRect = (q: Quad) => Math.abs(q[0][1] - q[1][1]) < 1e-4 && Math.abs(q[3][1] - q[2][1]) < 1e-4 && Math.abs(q[0][0] - q[3][0]) < 1e-4 && Math.abs(q[1][0] - q[2][0]) < 1e-4;
const rectQuad = (x0: number, y0: number, x1: number, y1: number): Quad => [[x0, y0], [x1, y0], [x1, y1], [x0, y1]];
/** 쿼드 안 (u, v) 쌍선형 보간 */
const lerpQ = (q: Quad, u: number, v: number): Pt => [
  (1 - u) * (1 - v) * q[0][0] + u * (1 - v) * q[1][0] + u * v * q[2][0] + (1 - u) * v * q[3][0],
  (1 - u) * (1 - v) * q[0][1] + u * (1 - v) * q[1][1] + u * v * q[2][1] + (1 - u) * v * q[3][1],
];
/** 그룹 사각형을 인식된 면의 원근에 맞춘다(면 bbox 기준 상대 위치 → 면 쿼드로 보간) */
function snapToSurface(g: Quad, s: Quad): Quad {
  const sb = bbox(s);
  const w = Math.max(1e-6, sb.x1 - sb.x0); const h = Math.max(1e-6, sb.y1 - sb.y0);
  return g.map(([x, y]) => lerpQ(s, Math.max(0, Math.min(1, (x - sb.x0) / w)), Math.max(0, Math.min(1, (y - sb.y0) / h)))) as Quad;
}
/** 화면(스크린) 칸들 — 배열별 */
function screensOf(g: PlacementGroup, q: Quad): Quad[] {
  const n = g.arrangement === 'single' ? 1 : Math.max(1, g.qty);
  const gap = g.arrangement === 'separate' ? 0.12 : 0.025;
  const out: Quad[] = [];
  for (let i = 0; i < n; i++) {
    const a = i / n; const b = (i + 1) / n;
    const pad = n > 1 ? gap / 2 : 0;
    const s0 = i === 0 ? 0 : a + pad; const s1 = i === n - 1 ? 1 : b - pad;
    if (g.arrangement === 'col3') out.push([lerpQ(q, 0, s0), lerpQ(q, 1, s0), lerpQ(q, 1, s1), lerpQ(q, 0, s1)]);
    else out.push([lerpQ(q, s0, 0), lerpQ(q, s1, 0), lerpQ(q, s1, 1), lerpQ(q, s0, 1)]);
  }
  return out;
}

export default function CompositePage() {
  const { workId = '' } = useParams();
  const nav = useNavigate();
  const inv = useInvalidate();
  const openPop = useOpenPopover();
  const wq = useWork(workId);
  const w = wq.data;
  const photosQ = useQuery({
    queryKey: qk.photos(workId), queryFn: () => img.photos(workId), enabled: !!workId,
    refetchInterval: (q) => ((q.state.data?.items ?? []).some((p) => p.status === 'recognizing') ? 1_500 : false),
  });
  const photos = photosQ.data?.items ?? [];
  const recognizing = photos.some((p) => p.status === 'recognizing');
  const prevRec = useRef(recognizing);
  useEffect(() => { if (prevRec.current && !recognizing) void inv.work(workId); prevRec.current = recognizing; }, [recognizing, inv, workId]);

  const comp = w?.composite;
  const activeId = comp?.active_photo_id ?? photos[0]?.id ?? null;
  const photo = photos.find((p) => p.id === activeId) ?? null;

  const [groups, setGroupsState] = useState<PlacementGroup[]>([]);
  const groupsRef = useRef<PlacementGroup[]>([]);
  const setGroups = useCallback((next: PlacementGroup[] | ((g: PlacementGroup[]) => PlacementGroup[])) => {
    const v = typeof next === 'function' ? next(groupsRef.current) : next;
    groupsRef.current = v;
    setGroupsState(v);
  }, []);
  const [dims, setDims] = useState<{ counter_width_mm: string; install_height_mm: string }>({ counter_width_mm: '', install_height_mm: '' });
  const [opts, setOpts] = useState({ perspective_light_match: true, screen_menu: true });
  const [measures, setMeasures] = useState<Record<string, string>>({});
  const [sel, setSel] = useState<string | null>(null);
  const [persp, setPersp] = useState<string | null>(null);
  const [view, setView] = useState<'edit' | 'photo'>('edit');
  const [zoom, setZoom] = useState(100);
  const [pan, setPan] = useState<{ x: number; y: number } | null>(null);
  const [cw, setCw] = useState(758);
  const [busy, setBusy] = useState<'upload' | 'run' | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [guide, setGuide] = useState(false);
  const [over, setOver] = useState(false);
  const canvasRef = useRef<HTMLDivElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const dragging = useRef(false);
  const syncedKey = useRef<string>('');

  // 서버 → 화면(끄는 중에는 덮지 않는다)
  useEffect(() => {
    if (!comp || dragging.current) return;
    const key = JSON.stringify([comp.active_photo_id, comp.groups, comp.ref_dims, comp.options, comp.measures]);
    if (key === syncedKey.current) return;
    syncedKey.current = key;
    const gs = comp.groups ?? [];
    setGroups(gs);
    setDims({ counter_width_mm: comp.ref_dims?.counter_width_mm ? String(comp.ref_dims.counter_width_mm) : '',
      install_height_mm: comp.ref_dims?.install_height_mm ? String(comp.ref_dims.install_height_mm) : '' });
    setOpts({ perspective_light_match: comp.options?.perspective_light_match ?? true, screen_menu: comp.options?.screen_menu ?? true });
    setMeasures(Object.fromEntries((comp.measures ?? []).map((m) => [m.id, m.label_text])));
    setSel((s) => (s && gs.some((g) => g.id === s) ? s : gs[0]?.id ?? null));
  }, [comp]);

  useEffect(() => {
    const el = canvasRef.current;
    if (!el) return;
    const ro = new ResizeObserver(() => setCw(el.clientWidth || 758));
    ro.observe(el);
    return () => ro.disconnect();
  }, [photo?.id]);

  const pw = photo?.width || 4; const ph = photo?.height || 3;
  const stageW = cw * (zoom / 100);
  const stageH = stageW * (ph / pw);
  // 기본 위치: 첫 그룹(없으면 면) 가운데를 화면 가운데로 — 그룹 이름표(위 28px)가 가려지지 않게
  const firstGroup = groups[0]?.id ?? '';
  const defaultPan = useMemo(() => {
    const g0 = groupsRef.current[0];
    const target = g0 ? bbox(toQuad(g0.quad)) : photo?.surfaces?.[0] ? bbox(toQuad(photo.surfaces[0].quad)) : { x0: 0.5, y0: 0.5, x1: 0.5, y1: 0.5 };
    const cy = ((target.y0 + target.y1) / 2) * stageH;
    const cx = ((target.x0 + target.x1) / 2) * stageW;
    const x = stageW <= cw ? (cw - stageW) / 2 : Math.min(0, Math.max(cw - stageW, cw / 2 - cx));
    let y = CANVAS_H / 2 - cy;
    if (g0) y = Math.max(y, 40 - target.y0 * stageH);
    y = stageH <= CANVAS_H ? (CANVAS_H - stageH) / 2 : Math.min(0, Math.max(CANVAS_H - stageH, y));
    return { x, y };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [photo?.id, stageW, stageH, cw, firstGroup]);
  const off = pan ?? defaultPan;
  useEffect(() => { setPan(null); }, [photo?.id, zoom]);

  const save = useDebounced((p: { groups: PlacementGroup[]; dims: typeof dims; opts: typeof opts }) => {
    if (!photo) return;
    const num = (s: string) => { const n = Number(String(s).replace(/[^\d.]/g, '')); return n > 0 ? n : null; };
    img.placements(workId, { photo_id: photo.id, groups: p.groups, ref_dims: { counter_width_mm: num(p.dims.counter_width_mm), install_height_mm: num(p.dims.install_height_mm) }, options: p.opts })
      .then((r) => {
        setMeasures(Object.fromEntries((r.groups ?? []).map((m) => [m.id, m.label_text])));
        syncedKey.current = JSON.stringify([r.composite.active_photo_id, r.composite.groups, r.composite.ref_dims, r.composite.options, r.composite.measures]);
        void inv.work(workId);
        setErr(null);
      })
      .catch((e) => setErr(errMessage(e)));
  }, 300);
  const commit = useCallback((next: { groups?: PlacementGroup[]; dims?: typeof dims; opts?: typeof opts }) => {
    const g = next.groups ?? groupsRef.current; const d = next.dims ?? dims; const o = next.opts ?? opts;
    if (next.groups) setGroups(g);
    if (next.dims) setDims(d);
    if (next.opts) setOpts(o);
    save({ groups: g, dims: d, opts: o });
  }, [dims, opts, save, setGroups]);

  // ── 끌기 ──────────────────────────────────────────
  const drag = useRef<{ mode: 'move' | 'pan' | 'handle'; id?: string; h?: number; sx: number; sy: number; quad?: Quad; pan?: { x: number; y: number } } | null>(null);
  const onDown = (e: RPointerEvent, mode: 'move' | 'pan' | 'handle', id?: string, h?: number) => {
    if (view !== 'edit' && mode !== 'pan') return;
    e.stopPropagation();
    (e.currentTarget as Element).setPointerCapture?.(e.pointerId);
    const g = groupsRef.current.find((x) => x.id === id);
    drag.current = { mode, id, h, sx: e.clientX, sy: e.clientY, quad: g ? toQuad(g.quad) : undefined, pan: off };
    dragging.current = true;
    if (id) setSel(id);
  };
  const onMove = (e: RPointerEvent) => {
    const d = drag.current;
    if (!d) return;
    const dx = e.clientX - d.sx; const dy = e.clientY - d.sy;
    if (d.mode === 'pan') {
      const x = stageW <= cw ? (cw - stageW) / 2 : Math.min(0, Math.max(cw - stageW, (d.pan?.x ?? 0) + dx));
      const y = stageH <= CANVAS_H ? (CANVAS_H - stageH) / 2 : Math.min(0, Math.max(CANVAS_H - stageH, (d.pan?.y ?? 0) + dy));
      setPan({ x, y });
      return;
    }
    if (!d.quad || !d.id) return;
    const nx = dx / stageW; const ny = dy / stageH;
    let q: Quad;
    if (d.mode === 'move') q = d.quad.map(([x, y]) => [x + nx, y + ny]) as Quad;
    else if (persp === d.id) q = d.quad.map((p, i) => (i === d.h ? [p[0] + nx, p[1] + ny] : p)) as Quad;
    else {
      const b = bbox(d.quad);
      let { x0, y0, x1, y1 } = b;
      const hh = d.h ?? 0; // 0 nw 1 n 2 ne 3 e 4 se 5 s 6 sw 7 w
      if ([0, 6, 7].includes(hh)) x0 = Math.min(x1 - 0.02, x0 + nx);
      if ([2, 3, 4].includes(hh)) x1 = Math.max(x0 + 0.02, x1 + nx);
      if ([0, 1, 2].includes(hh)) y0 = Math.min(y1 - 0.02, y0 + ny);
      if ([4, 5, 6].includes(hh)) y1 = Math.max(y0 + 0.02, y1 + ny);
      q = rectQuad(x0, y0, x1, y1);
    }
    setGroups((gs) => gs.map((g) => (g.id === d.id ? { ...g, quad: q } : g)));
  };
  const onUp = () => {
    const d = drag.current;
    drag.current = null;
    dragging.current = false;
    if (d && d.mode !== 'pan') save({ groups: groupsRef.current, dims, opts });
  };
  const nudge = (id: string, dx: number, dy: number) => commit({ groups: groups.map((g) => (g.id === id ? { ...g, quad: toQuad(g.quad).map(([x, y]) => [x + dx, y + dy]) } : g)) });

  // ── 도구 ──────────────────────────────────────────
  const selected = groups.find((g) => g.id === sel) ?? null;
  const setGroup = (id: string, patch: Partial<PlacementGroup>) => commit({ groups: groups.map((g) => (g.id === id ? { ...g, ...patch } : g)) });
  const duplicate = (g: PlacementGroup) => {
    const q = toQuad(g.quad).map(([x, y]) => [x + 0.04, y + 0.06]) as Quad;
    const ng = { ...g, id: `grp_${Math.random().toString(36).slice(2, 10)}`, quad: q };
    commit({ groups: [...groups, ng] });
    setSel(ng.id);
  };
  const remove = (g: PlacementGroup) => { commit({ groups: groups.filter((x) => x.id !== g.id) }); setPersp(null); };
  const togglePersp = (g: PlacementGroup) => {
    if (persp === g.id) { setPersp(null); return; }
    setPersp(g.id);
    const surf = photo?.surfaces?.find((s) => s.installable);
    const q = toQuad(g.quad);
    if (surf && isRect(q)) setGroup(g.id, { quad: snapToSurface(q, toQuad(surf.quad)) });
  };

  // ── 사진 올리기 ───────────────────────────────────
  const onFiles = async (files: FileList | File[]) => {
    const f = Array.from(files)[0];
    if (!f) return;
    const bad = checkUpload(f);
    if (bad) { setErr(bad); return; }
    setBusy('upload'); setErr(null);
    try {
      const up = await uploadFile(f, { confidential: true, purpose: 'site_photo' });
      await img.addPhoto(workId, up.id);
      await photosQ.refetch();
      void inv.work(workId);
    } catch (e) { setErr(`올리지 못했어요 · ${errMessage(e)}`); } finally { setBusy(null); }
  };
  const selectPhoto = (p: SitePhoto) => {
    if (p.id === activeId) return;
    img.placements(workId, { photo_id: p.id, groups, ref_dims: comp?.ref_dims ?? {}, options: opts })
      .then(() => inv.work(workId)).catch((e) => setErr(errMessage(e)));
  };
  const recognizeAgain = async () => {
    setGuide(false);
    if (!photo) return;
    try { await img.recognize(workId, photo.id); await photosQ.refetch(); } catch (e) { setErr(errMessage(e)); }
  };
  const generate = async () => {
    setBusy('run'); setErr(null);
    try {
      const acc = await img.startRun(workId, { kind: 'composite' });
      void inv.gallery();
      nav(route.run(workId, acc.run_id));
    } catch (e) {
      if (e instanceof ApiError && e.code === 'RUN_IN_PROGRESS' && typeof e.details.run_id === 'string') nav(route.run(workId, e.details.run_id));
      else setErr(errMessage(e));
    } finally { setBusy(null); }
  };
  const addProducts = async (refs: string[]) => {
    try { const r = await img.addProducts(workId, refs); inv.setWork(r.work); syncedKey.current = ''; return r.added; } catch (e) { setErr(errMessage(e)); return []; }
  };

  const products = w?.conditions.products ?? [];
  useImgShell({
    title: w?.title ?? '현장 사진 합성', step: 2, accepts: ['product'], addable: ['product'],
    added: [...groups.map((g) => (g.model_code ? `kb:model:mdl_${g.model_code}` : g.family_id ? `kb:family:${g.family_id}` : '')), ...products.map((p) => (p.model_code ? `kb:model:mdl_${p.model_code}` : ''))].filter(Boolean),
    onAdd: async (_t, refs) => ({ added: await addProducts(refs) }),
  });
  const drop = useDropTarget({ accept: ['product'], onDrop: async (p) => (await addProducts([p.ref])).length > 0 });

  if (wq.isLoading || photosQ.isLoading) return <Loading />;
  if (!w) return <div className="img-center"><ErrorState message="작업을 불러오지 못했어요" onRetry={() => wq.refetch()} /></div>;

  const surfaces = photo && photo.status !== 'recognizing' ? (photo.surfaces ?? []).filter((s) => s.installable) : [];
  const dark = photos.length > 0 && photos.every((p) => p.status === 'low_light');
  const wText = !photo ? '현장 사진을 올리면 설치할 면을 인식해 제품을 올려 드릴게요.'
    : photo.status === 'recognizing' ? '사진에서 설치할 면을 찾고 있어요.'
      : photo.message ?? '설치할 면을 찾지 못했어요. 제품을 끌어 원하는 위치에 놓아 주세요.';
  const P = (p: Pt) => ({ left: off.x + p[0] * stageW, top: off.y + p[1] * stageH });
  const pts = (q: Quad) => q.map((p) => `${off.x + p[0] * stageW},${off.y + p[1] * stageH}`).join(' ');

  return (
    <Screen testid="img2p" composer={
      <div className="wm-composer-wrap">
        <div className="wm-composer" {...drop.props} style={drop.dragging ? { borderColor: 'var(--wm-brand)', boxShadow: 'var(--wm-ring-drop)' } : undefined}>
          <div className="wm-composer__head">
            <span>제품 배치<small> · 현장 사진 합성 · 2 / 3</small></span>
            <button type="button" className="img-pill img-pill--h28 img-pill--brand" style={{ border: 'none' }} onClick={() => openPop('product')}>
              <Icon name="plus" size={13} strokeWidth={2.4} />제품 추가
            </button>
          </div>
          <div style={{ padding: '10px 18px 0 18px', display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            {groups.length === 0 && products.length === 0 && <span className="img-hint img-hint--sm">「제품 추가」로 넣을 제품을 골라 주세요</span>}
            {groups.length === 0 && products.map((p) => (
              <span key={p.model_code ?? p.name} className="img-prodtag"><Ico d={PATH.display} size={14} />{p.name}{p.qty > 1 ? ` ×${p.qty}` : ''}</span>
            ))}
            {groups.map((g) => (
              <button key={g.id} type="button" className="img-prodtag" aria-pressed={g.id === sel && groups.length > 1} onClick={() => setSel(g.id)} data-testid="img2p-product">
                <Ico d={PATH.display} size={14} />{g.name || g.label}{g.qty > 1 ? ` ×${g.qty}` : ''}
              </button>
            ))}
            {selected && (
              <>
                <span className="img-label" style={{ marginLeft: 6 }}>배열</span>
                <span className="img-segb" role="group" aria-label="배열">
                  {(['row3', 'col3', 'separate'] as const).map((a) => (
                    <button key={a} type="button" aria-pressed={selected.arrangement === a} onClick={() => setGroup(selected.id, { arrangement: a })}>{ARR_LABEL[a]}</button>
                  ))}
                </span>
                <span className="img-label" style={{ marginLeft: 6 }}>설치</span>
                <span className="img-segb" role="group" aria-label="설치">
                  {([['wall', '벽 부착'], ['ceiling', '천장 매달기']] as const).map(([m, l]) => (
                    <button key={m} type="button" aria-pressed={selected.mount === m} onClick={() => setGroup(selected.id, { mount: m })}>{l}</button>
                  ))}
                </span>
              </>
            )}
          </div>
          <div style={{ padding: '10px 18px 0 18px', display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
            <span className="img-label">기준 치수</span>
            {([['counter_width_mm', '카운터 폭'], ['install_height_mm', '설치 높이']] as const).map(([k, l]) => (
              <span key={k} className="img-dim">
                <label htmlFor={`img-${k}`}>{l}</label>
                <input id={`img-${k}`} inputMode="numeric" placeholder="[00]" value={dims[k]}
                  onChange={(e) => commit({ dims: { ...dims, [k]: e.target.value.replace(/[^\d]/g, '').slice(0, 6) } })} />
                <span>mm</span>
              </span>
            ))}
            <span style={{ flex: 1 }} />
            <Switch label="원근 · 조명 맞춤" checked={opts.perspective_light_match} onChange={(v) => commit({ opts: { ...opts, perspective_light_match: v } })}>원근 · 조명 맞춤</Switch>
            <Switch label="화면에 메뉴 넣기" checked={opts.screen_menu} onChange={(v) => commit({ opts: { ...opts, screen_menu: v } })}>화면에 메뉴 넣기</Switch>
          </div>
          <div className="wm-composer__foot" style={{ justifyContent: 'space-between' }}>
            <span className={cx('img-hint', err && 'img-err')} role={err ? 'alert' : undefined}>{err ?? '치수를 모르면 비워 두세요. 사진 속 비율로 추정합니다'}</span>
            <div className="img-row">
              <Button h={44} onClick={() => nav(route.newWork(w.id))}>이전</Button>
              <Button h={44} variant="primary" loading={busy === 'run'} disabled={!photo || !!busy || recognizing || groups.length === 0}
                disabledReason={!photo ? '현장 사진을 먼저 올려 주세요' : recognizing ? '사진을 인식하는 중이에요' : '제품을 먼저 추가해 주세요'}
                onClick={() => void generate()} iconRight={<Icon name="arrowRight" size={16} strokeWidth={2.2} />}>합성 이미지 4장 생성</Button>
            </div>
          </div>
        </div>
      </div>
    }>
      <WSay text={wText}>
        {dark && <div className="img-w__warn"><Icon name="info" size={14} />사진이 어두워 합성 결과가 고르지 않을 수 있어요</div>}
        <div className="img-card" style={{ position: 'relative' }}>
          <div className="img-card__bar" style={{ minHeight: 52, padding: '0 12px' }}>
            <div role="tablist" aria-label="현장 사진" className="img-row" style={{ gap: 8 }}>
              {photos.map((p) => (
                <button key={p.id} type="button" role="tab" aria-selected={p.id === activeId} className="img-ptab" onClick={() => selectPhoto(p)} data-status={p.status}>
                  <span className="img-ptab__thumb"><Img src={p.thumb_url} alt={`${p.label} 현장 사진`} /></span>
                  <span style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', minWidth: 0 }}>
                    <span className="img-ptab__label">{p.label}</span>
                    <span className={cx('img-ptab__st', p.status === 'recognized' && 'img-ptab__st--ok')} data-testid="img2p-status">
                      {p.status === 'recognized' ? <Icon name="check" size={11} strokeWidth={2.8} /> : p.status === 'recognizing' ? <Icon name="clock" size={11} /> : <Icon name="info" size={11} />}
                      {p.status_label}
                    </span>
                  </span>
                </button>
              ))}
              <button type="button" className="img-addphoto" onClick={() => fileRef.current?.click()} disabled={busy === 'upload'}>
                <Icon name="plus" size={13} strokeWidth={2.4} />{busy === 'upload' ? '올리는 중…' : '사진 추가'}
              </button>
              <input ref={fileRef} type="file" accept={UPLOAD_ACCEPT} hidden data-testid="img2p-file" onChange={(e) => { if (e.target.files) void onFiles(e.target.files); e.target.value = ''; }} />
            </div>
            <span style={{ flex: 1 }} />
            <button type="button" className="img-pill img-pill--h28 img-pill--brand" style={{ border: 'none', background: 'transparent' }} aria-expanded={guide}
              onClick={() => setGuide(!guide)} disabled={!photo}>
              <Icon name="refresh" size={13} />촬영 가이드 · 다시 인식
            </button>
          </div>
          {guide && (
            <div className="img-popover" style={{ right: 12, top: 56 }} role="dialog" aria-label="촬영 가이드">
              <b style={{ color: 'var(--wm-text)' }}>촬영 가이드</b>
              <ol>
                <li>설치할 벽면이 정면에 가깝게, 가운데에 오도록 찍어 주세요.</li>
                <li>카운터 · 문 같은 기준 물체가 함께 보이면 크기를 더 정확히 맞춰요.</li>
                <li>조명을 켜고 역광은 피해 주세요.</li>
              </ol>
              <div className="img-row" style={{ justifyContent: 'flex-end', marginTop: 10 }}>
                <button type="button" className="img-mini" onClick={() => setGuide(false)}>닫기</button>
                <button type="button" className="img-mini img-mini--primary" onClick={() => void recognizeAgain()}>다시 인식</button>
              </div>
            </div>
          )}
          <div ref={canvasRef} className="img-canvas" data-testid="img2p-canvas" onPointerMove={onMove} onPointerUp={onUp} onPointerCancel={onUp}
            onPointerDown={(e) => photo && onDown(e, 'pan')}>
            {!photo ? (
              <div className={cx('img-canvas__empty', over && 'img-canvas__empty--over')} role="button" tabIndex={0} data-testid="img2p-drop"
                onClick={() => fileRef.current?.click()} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); fileRef.current?.click(); } }}
                onDragOver={(e) => { if (e.dataTransfer?.types?.includes('Files')) { e.preventDefault(); setOver(true); } }} onDragLeave={() => setOver(false)}
                onDrop={(e) => { e.preventDefault(); setOver(false); if (e.dataTransfer.files?.length) void onFiles(e.dataTransfer.files); }}>
                <Ico d={PATH.camera} size={24} />
                <b>{busy === 'upload' ? '올리는 중…' : '현장 사진을 끌어 놓거나 올려 주세요 · JPG · PNG · HEIC'}</b>
              </div>
            ) : (
              <>
                <div className="img-canvas__stage" style={{ left: off.x, top: off.y, width: stageW, height: stageH }}>
                  <img src={photo.url} alt={`${photo.label} 현장 사진`} draggable={false} />
                </div>
                {view === 'edit' && (
                  <svg width={cw} height={CANVAS_H} style={{ position: 'absolute', left: 0, top: 0, overflow: 'visible' }}>
                    {surfaces.map((s, i) => (
                      <polygon key={i} points={pts(toQuad(s.quad))} fill="rgba(20,40,160,0.06)" stroke="var(--wm-brand)" strokeWidth={1.5} strokeDasharray="5 4" style={{ pointerEvents: 'none' }} />
                    ))}
                    {groups.map((g) => {
                      const q = toQuad(g.quad);
                      const on = g.id === sel;
                      return (
                        <g key={g.id} data-testid="img2p-group">
                          {g.mount === 'ceiling' && (() => { const a = lerpQ(q, 0.2, 0); const b = lerpQ(q, 0.8, 0); return (
                            <g stroke="var(--wm-text-2)" strokeWidth={2}>
                              <line x1={off.x + a[0] * stageW} y1={off.y + a[1] * stageH} x2={off.x + a[0] * stageW} y2={off.y + a[1] * stageH - 18} />
                              <line x1={off.x + b[0] * stageW} y1={off.y + b[1] * stageH} x2={off.x + b[0] * stageW} y2={off.y + b[1] * stageH - 18} />
                            </g>); })()}
                          {screensOf(g, q).map((s, i) => (
                            <polygon key={i} points={pts(s)} fill="var(--wm-dark)" stroke="var(--wm-text-2)" strokeWidth={2} style={{ pointerEvents: 'none' }} />
                          ))}
                          <polygon points={pts(q)} fill="rgba(20,40,160,0.04)" stroke={on ? 'var(--wm-brand)' : 'var(--wm-surface)'} strokeWidth={1.5}
                            style={{ cursor: 'move' }} onPointerDown={(e) => onDown(e, 'move', g.id)} />
                        </g>
                      );
                    })}
                  </svg>
                )}
                {view === 'edit' && surfaces[0] && (() => { const b = bbox(toQuad(surfaces[0].quad)); const p = P([b.x0, b.y1]); return (
                  <span className="img-onphoto" style={{ left: p.left + 8, top: Math.min(CANVAS_H - 70, p.top - 32), transform: 'none' }}><Icon name="check" size={12} strokeWidth={2.6} />인식된 벽면 · 설치 가능</span>
                ); })()}
                {view === 'edit' && groups.map((g) => {
                  const q = toQuad(g.quad);
                  const b = bbox(q);
                  const tl = P([b.x0, b.y0]);
                  const bottom = P([(b.x0 + b.x1) / 2, b.y1]);
                  const tr = P([b.x1, b.y0]);
                  const on = g.id === sel;
                  const handles: Pt[] = persp === g.id ? q : [[b.x0, b.y0], [(b.x0 + b.x1) / 2, b.y0], [b.x1, b.y0], [b.x1, (b.y0 + b.y1) / 2], [b.x1, b.y1], [(b.x0 + b.x1) / 2, b.y1], [b.x0, b.y1], [b.x0, (b.y0 + b.y1) / 2]];
                  const hcls = ['corner', 'edge-n', 'corner-ne', 'edge-e', 'corner', 'edge-s', 'corner-sw', 'edge-w'];
                  return (
                    <div key={g.id}>
                      <button type="button" className="img-group__label" style={{ position: 'absolute', left: tl.left, top: tl.top - 28, border: 'none' }}
                        aria-label={`${g.label} ×${g.qty} · ${ARR_LABEL[g.arrangement]} — 화살표로 옮기기`} onClick={() => setSel(g.id)}
                        onPointerDown={(e) => onDown(e, 'move', g.id)}
                        onKeyDown={(e) => {
                          const s = e.shiftKey ? 0.02 : 0.005;
                          const m: Record<string, [number, number]> = { ArrowLeft: [-s, 0], ArrowRight: [s, 0], ArrowUp: [0, -s], ArrowDown: [0, s] };
                          if (m[e.key]) { e.preventDefault(); nudge(g.id, m[e.key][0], m[e.key][1]); }
                        }}>
                        {g.label} ×{g.qty} · {ARR_LABEL[g.arrangement]}
                      </button>
                      {on && handles.map((h, i) => (
                        <span key={i} className={cx('img-handle', persp === g.id ? 'img-handle--persp' : `img-handle--${hcls[i]}`)} style={P(h)}
                          onPointerDown={(e) => onDown(e, 'handle', g.id, i)} aria-hidden="true" />
                      ))}
                      <span className="img-measure" style={{ left: bottom.left, top: bottom.top + 8 }} data-testid="img2p-measure">
                        <Ico d={PATH.measure} size={12} />{measures[g.id] || '가로 약 [00] mm · 바닥에서 [00] mm'}
                      </span>
                      {on && (
                        <div className="img-floattools" style={{ left: Math.min(cw - 96, tr.left + 10), top: Math.max(6, tr.top) }} onPointerDown={(e) => e.stopPropagation()}>
                          <button type="button" aria-label="복제" title="복제" onClick={() => duplicate(g)}><Icon name="copy" size={14} /></button>
                          <button type="button" aria-label="원근 맞춤" title="원근 맞춤" aria-pressed={persp === g.id} onClick={() => togglePersp(g)}><Ico d={PATH.persp} size={14} /></button>
                          <button type="button" aria-label="삭제" title="삭제" onClick={() => remove(g)}><Icon name="trash" size={14} /></button>
                        </div>
                      )}
                    </div>
                  );
                })}
                {photo.status === 'recognizing' && <div className="img-canvas__empty" style={{ background: 'rgba(245,246,248,0.6)', cursor: 'default' }}><b>인식 중</b></div>}
                <div className="img-canvas__view" role="group" aria-label="보기" onPointerDown={(e) => e.stopPropagation()}>
                  <button type="button" aria-pressed={view === 'edit'} onClick={() => setView('edit')}>배치 편집</button>
                  <button type="button" aria-pressed={view === 'photo'} onClick={() => setView('photo')}>원본 사진</button>
                </div>
                <div className="img-canvas__zoom" onPointerDown={(e) => e.stopPropagation()}>
                  <span>끌어서 이동 · 모서리로 크기 조절</span>
                  <span style={{ width: 1, height: 14, background: 'var(--wm-line)' }} />
                  <button type="button" aria-label="축소" onClick={() => setZoom((z) => Math.max(25, z - 25))}>−</button>
                  <b>{zoom}%</b>
                  <button type="button" aria-label="확대" onClick={() => setZoom((z) => Math.min(400, z + 25))}>+</button>
                </div>
              </>
            )}
          </div>
        </div>
      </WSay>
    </Screen>
  );
}
