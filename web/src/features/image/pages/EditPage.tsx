/**
 * IMG3E · 부분 수정(§4.9) — 도구 4(사각형 · 브러시 · 객체 선택 · 지우개) · 크기 3 · 실행 취소/다시 실행 · 편집 / 전·후 비교 ·
 * 수정 기록(버전 미리보기 · 되돌리기) · 수정 영역 카드(이름 · 지시문 · 적용/되돌리기) · 제품 외형 고정 · 빠른 칩 4.
 * 적용은 영역마다 run(edit) — 화면에 머무르며 카드에 진행을 보여 준다. 영역 밖 픽셀은 서버가 바이트 단위로 지킨다.
 */
import { useCallback, useEffect, useMemo, useRef, useState, type PointerEvent as RPointerEvent } from 'react';
import { useLocation, useNavigate, useParams, useSearchParams } from 'react-router';
import { useQuery } from '@tanstack/react-query';
import { Button, cx, ErrorState, Icon, Img, Spinner } from '@/ui';
import { useJob } from '@/api/jobs';
import { errMessage, img, uploadFile, type EditRegion, type Version } from '../api';
import { AskInput, Echo, Ico, Loading, PATH, Pill, Screen, Switch, useImgShell, WSay } from '../components';
import { qk, useCaps, useImage, useInvalidate } from '../hooks';
import { josa, route } from '../lib';

type Tool = 'rect' | 'brush' | 'object' | 'eraser';
interface Stroke { pts: Array<[number, number]>; size: number; erase: boolean }
type Act = { type: 'stroke'; regionId: string } | { type: 'region'; regionId: string; rect: number[] };
const SIZES: Array<{ px: number; label: string; dot: number }> = [{ px: 12, label: '작게', dot: 6 }, { px: 24, label: '보통', dot: 9 }, { px: 48, label: '크게', dot: 13 }];

export default function EditPage() {
  const { workId = '', imageId = '' } = useParams();
  const [sp, setSp] = useSearchParams();
  const loc = useLocation();
  const nav = useNavigate();
  const inv = useInvalidate();
  const caps = useCaps();
  const [polling, setPolling] = useState(false);
  const iq = useImage(imageId, { poll: polling });
  const rq = useQuery({ queryKey: qk.regions(imageId), queryFn: () => img.regions(imageId), enabled: !!imageId, refetchInterval: polling ? 1_500 : false });
  const image = iq.data;
  const regions = useMemo(() => rq.data?.items ?? [], [rq.data]);
  const applying = regions.some((r) => r.status === 'applying');
  const [globalJob, setGlobalJob] = useState<string | null>(null);
  useEffect(() => { setPolling(applying || !!globalJob); }, [applying, globalJob]);
  const prevApplying = useRef(applying);
  useEffect(() => { if (prevApplying.current && !applying) { void inv.image(imageId); void inv.gallery(); } prevApplying.current = applying; }, [applying, imageId, inv]);
  useJob(globalJob, { onDone: (j) => {
    setGlobalJob(null);
    setNote(j.status === 'succeeded' ? { text: '전체 이미지를 고친 새 버전을 만들었어요', ok: true } : { text: j.error?.message ?? '고치지 못했어요', ok: false });
    void inv.image(imageId); void rq.refetch();
  } });

  const [tool, setTool] = useState<Tool>('rect');
  const [size, setSize] = useState(24);
  const [view, setView] = useState<'edit' | 'compare'>('edit');
  const [activeId, setActiveId] = useState<string | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [split, setSplit] = useState(0.5);
  const [temp, setTemp] = useState<number[] | null>(null);
  const [strokes, setStrokes] = useState<Record<string, Stroke[]>>({});
  const [undo, setUndo] = useState<Act[]>([]);
  const [redo, setRedo] = useState<Array<Act & { stroke?: Stroke }>>([]);
  const [protect, setProtect] = useState(true);
  const [note, setNote] = useState<{ text: string; ok: boolean } | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [dets, setDets] = useState<Array<{ id: string; label: string; box: number[] }> | null>(null);
  const [cw, setCw] = useState(496);
  const wrapRef = useRef<HTMLDivElement>(null);
  const maskRef = useRef<HTMLCanvasElement>(null);
  const drawing = useRef<{ kind: 'rect' | 'brush' | 'split'; x0: number; y0: number; stroke?: Stroke; regionId?: string | null } | null>(null);
  const presetDone = useRef(false);

  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const ro = new ResizeObserver(() => setCw(el.clientWidth || 496));
    ro.observe(el);
    return () => ro.disconnect();
  }, [image?.id]);
  useEffect(() => { if (!activeId && regions.length) setActiveId((regions.find((r) => r.status === 'applied') ?? regions[0]).id); }, [regions, activeId]);
  const active = regions.find((r) => r.id === activeId) ?? null;
  useEffect(() => { if (active) setProtect(active.protect_products); }, [active?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const versions = useMemo(() => image?.versions ?? [], [image]);
  const current = image?.current ?? null;
  const shown: Version | null = (preview ? versions.find((v) => v.id === preview) : null) ?? current;
  const vw = shown?.width ?? 1920; const vh = shown?.height ?? 1080;
  const ch = Math.round(cw * (vh / vw));
  const objectOk = !!caps.data?.features.object_select;

  // 비교 대상: 고른 영역이 적용됐으면 그 전/후, 아니면 현재와 그 앞 버전
  const cmp = useMemo(() => {
    const byId = (id?: string | null) => versions.find((v) => v.id === id) ?? null;
    if (active?.status === 'applied' && active.result_version_id) return { before: byId(active.base_version_id), after: byId(active.result_version_id) };
    const cur = current;
    return { before: byId(cur?.parent_version_id) ?? versions[0] ?? null, after: cur };
  }, [active, versions, current]);
  const canCompare = !!(cmp.before && cmp.after && cmp.before.id !== cmp.after.id);
  useEffect(() => { if (view === 'compare' && !canCompare) setView('edit'); }, [view, canCompare]);
  const appliedCount = regions.filter((r) => r.status === 'applied').length;
  const autoFor = useRef(0);
  useEffect(() => { if (appliedCount > autoFor.current && canCompare) { autoFor.current = appliedCount; setView('compare'); } }, [appliedCount, canCompare]);

  // ── 브러시 마스크 그리기 ─────────────────────────
  const paint = useCallback(() => {
    const c = maskRef.current;
    if (!c) return;
    c.width = cw; c.height = ch;
    const ctx = c.getContext('2d');
    if (!ctx) return;
    ctx.clearRect(0, 0, cw, ch);
    const list = activeId ? strokes[activeId] ?? [] : [];
    for (const s of list) {
      ctx.globalCompositeOperation = s.erase ? 'destination-out' : 'source-over';
      ctx.strokeStyle = 'rgba(20, 40, 160, 0.45)';
      ctx.lineCap = 'round'; ctx.lineJoin = 'round'; ctx.lineWidth = s.size;
      ctx.beginPath();
      s.pts.forEach(([x, y], i) => (i ? ctx.lineTo(x * cw, y * ch) : ctx.moveTo(x * cw, y * ch)));
      if (s.pts.length === 1) ctx.lineTo(s.pts[0][0] * cw + 0.1, s.pts[0][1] * ch);
      ctx.stroke();
    }
    ctx.globalCompositeOperation = 'source-over';
  }, [cw, ch, strokes, activeId]);
  useEffect(() => { paint(); }, [paint]);

  /** 브러시 획 → 버전 크기 마스크 PNG(흰 = 수정) */
  const exportMask = async (list: Stroke[]): Promise<{ file: File; rect: number[] } | null> => {
    const c = document.createElement('canvas');
    c.width = vw; c.height = vh;
    const ctx = c.getContext('2d');
    if (!ctx) return null;
    ctx.fillStyle = '#000'; ctx.fillRect(0, 0, vw, vh);
    let x0 = 1, y0 = 1, x1 = 0, y1 = 0;
    for (const s of list) {
      ctx.globalCompositeOperation = 'source-over';
      ctx.strokeStyle = s.erase ? '#000' : '#fff';
      ctx.lineCap = 'round'; ctx.lineJoin = 'round'; ctx.lineWidth = s.size * (vw / cw);
      ctx.beginPath();
      s.pts.forEach(([x, y], i) => (i ? ctx.lineTo(x * vw, y * vh) : ctx.moveTo(x * vw, y * vh)));
      if (s.pts.length === 1) ctx.lineTo(s.pts[0][0] * vw + 0.5, s.pts[0][1] * vh);
      ctx.stroke();
      if (!s.erase) {
        const r = s.size / 2 / cw; const rv = s.size / 2 / ch;
        for (const [x, y] of s.pts) { x0 = Math.min(x0, x - r); y0 = Math.min(y0, y - rv); x1 = Math.max(x1, x + r); y1 = Math.max(y1, y + rv); }
      }
    }
    if (x1 <= x0 || y1 <= y0) return null;
    const blob: Blob | null = await new Promise((res) => c.toBlob(res, 'image/png'));
    if (!blob) return null;
    return { file: new File([blob], 'mask.png', { type: 'image/png' }), rect: [Math.max(0, x0), Math.max(0, y0), Math.min(1, x1), Math.min(1, y1)] };
  };
  const pushMask = async (regionId: string | null, list: Stroke[]) => {
    const m = await exportMask(list);
    if (!m) return null;
    const up = await uploadFile(m.file, { purpose: 'image_mask' });
    if (regionId) { await img.patchRegion(imageId, regionId, { mask_file_id: up.id, rect: m.rect }); return regionId; }
    const r = await img.addRegion(imageId, { shape: 'brush', mask_file_id: up.id, rect: m.rect });
    return r.region?.id ?? null;
  };

  const pos = (e: RPointerEvent): [number, number] => {
    const b = wrapRef.current!.getBoundingClientRect();
    return [Math.max(0, Math.min(1, (e.clientX - b.left) / b.width)), Math.max(0, Math.min(1, (e.clientY - b.top) / b.height))];
  };
  const onDown = (e: RPointerEvent) => {
    if (!current || preview) return;
    const [x, y] = pos(e);
    (e.currentTarget as Element).setPointerCapture?.(e.pointerId);
    if (view === 'compare') { drawing.current = { kind: 'split', x0: x, y0: y }; setSplit(x); return; }
    if (tool === 'rect') { drawing.current = { kind: 'rect', x0: x, y0: y }; setTemp([x, y, x, y]); return; }
    if (tool === 'brush' || tool === 'eraser') {
      const target = active && active.shape === 'brush' && active.status !== 'applying' ? active.id : null;
      if (tool === 'eraser' && !target) { setNote({ text: '지울 브러시 영역을 먼저 골라 주세요', ok: false }); return; }
      const s: Stroke = { pts: [[x, y]], size, erase: tool === 'eraser' };
      drawing.current = { kind: 'brush', x0: x, y0: y, stroke: s, regionId: target };
      const key = target ?? '__new';
      setStrokes((m) => ({ ...m, [key]: [...(m[key] ?? []), s] }));
      if (!target) setActiveId(null);
    }
  };
  const onMove = (e: RPointerEvent) => {
    const d = drawing.current;
    if (!d) return;
    const [x, y] = pos(e);
    if (d.kind === 'split') { setSplit(x); return; }
    if (d.kind === 'rect') { setTemp([Math.min(d.x0, x), Math.min(d.y0, y), Math.max(d.x0, x), Math.max(d.y0, y)]); return; }
    if (d.kind === 'brush' && d.stroke) {
      d.stroke.pts.push([x, y]);
      const key = d.regionId ?? '__new';
      setStrokes((m) => ({ ...m, [key]: [...(m[key] ?? []).slice(0, -1), { ...d.stroke! }] }));
    }
  };
  const onUp = async () => {
    const d = drawing.current;
    drawing.current = null;
    if (!d || d.kind === 'split') return;
    setNote(null);
    try {
      if (d.kind === 'rect' && temp) {
        const r = temp; setTemp(null);
        if ((r[2] - r[0]) * cw < 8 || (r[3] - r[1]) * ch < 8) return;
        setBusy('region');
        const res = await img.addRegion(imageId, { shape: 'rect', rect: r });
        if (res.region) { setActiveId(res.region.id); setUndo((u) => [...u, { type: 'region', regionId: res.region!.id, rect: r }]); setRedo([]); }
        await rq.refetch();
      } else if (d.kind === 'brush') {
        const key = d.regionId ?? '__new';
        const list = (strokesRef.current[key] ?? []);
        setBusy('region');
        const rid = await pushMask(d.regionId ?? null, list);
        if (rid && !d.regionId) { setStrokes((m) => { const { __new, ...rest } = m; return { ...rest, [rid]: __new ?? [] }; }); setActiveId(rid); }
        if (rid) { setUndo((u) => [...u, { type: 'stroke', regionId: rid }]); setRedo([]); }
        await rq.refetch();
      }
    } catch (e) { setNote({ text: errMessage(e), ok: false }); } finally { setBusy(null); }
  };
  const strokesRef = useRef(strokes);
  strokesRef.current = strokes;

  const doUndo = async () => {
    const last = undo[undo.length - 1];
    if (!last) return;
    setUndo(undo.slice(0, -1));
    try {
      if (last.type === 'region') { await img.deleteRegion(imageId, last.regionId); setRedo((r) => [...r, last]); if (activeId === last.regionId) setActiveId(null); }
      else {
        const list = strokes[last.regionId] ?? [];
        const s = list[list.length - 1];
        const next = list.slice(0, -1);
        setStrokes((m) => ({ ...m, [last.regionId]: next }));
        setRedo((r) => [...r, { ...last, stroke: s }]);
        if (next.length) await pushMask(last.regionId, next); else { await img.deleteRegion(imageId, last.regionId); setActiveId(null); }
      }
      await rq.refetch();
    } catch (e) { setNote({ text: errMessage(e), ok: false }); }
  };
  const doRedo = async () => {
    const last = redo[redo.length - 1];
    if (!last) return;
    setRedo(redo.slice(0, -1));
    try {
      if (last.type === 'region') {
        const res = await img.addRegion(imageId, { shape: 'rect', rect: last.rect });
        if (res.region) { setActiveId(res.region.id); setUndo((u) => [...u, { ...last, regionId: res.region!.id }]); }
      } else if (last.stroke) {
        const exists = regions.some((r) => r.id === last.regionId);
        const list = [...(strokes[last.regionId] ?? []), last.stroke];
        const rid = await pushMask(exists ? last.regionId : null, list);
        if (rid) { setStrokes((m) => ({ ...m, [rid]: list })); setUndo((u) => [...u, { type: 'stroke', regionId: rid }]); setActiveId(rid); }
      }
      await rq.refetch();
    } catch (e) { setNote({ text: errMessage(e), ok: false }); }
  };

  // ── 영역 동작 ────────────────────────────────────
  const apply = async (ids: string[]) => {
    if (!ids.length) return;
    setNote(null);
    try { await img.edit(imageId, { region_ids: ids, protect_products: protect }); await rq.refetch(); setPolling(true); } catch (e) { setNote({ text: errMessage(e), ok: false }); }
  };
  const revert = async (r: EditRegion) => {
    try { await img.revertRegion(imageId, r.id); await Promise.all([rq.refetch(), inv.image(imageId)]); setPreview(null); } catch (e) { setNote({ text: errMessage(e), ok: false }); }
  };
  const saveInstruction = async (r: EditRegion, text: string) => {
    if (text === r.instruction) return;
    try { await img.patchRegion(imageId, r.id, { instruction: text }); await rq.refetch(); } catch (e) { setNote({ text: errMessage(e), ok: false }); }
  };
  const clearAll = async () => {
    for (const r of regions.filter((x) => x.status === 'pending' || x.status === 'failed')) { try { await img.deleteRegion(imageId, r.id); } catch { /* 다음 */ } }
    setActiveId(null); setUndo([]); setRedo([]);
    await rq.refetch();
  };
  const runPreset = async (preset: 'erase_text' | 'erase_people' | 'screen_content') => {
    setBusy(preset); setNote(null);
    try {
      const res = await img.addRegion(imageId, { preset });
      if (res.note && res.global_instruction) {
        setNote({ text: res.note, ok: true });
        const acc = await img.edit(imageId, { mode: 'global', instruction: res.global_instruction, protect_products: protect });
        setGlobalJob(acc.job_id);
      } else if (res.region) setActiveId(res.region.id);
      await rq.refetch();
    } catch (e) { setNote({ text: errMessage(e), ok: false }); } finally { setBusy(null); }
  };
  useEffect(() => {
    const p = sp.get('preset');
    if (!image || presetDone.current || !p || !['erase_text', 'erase_people', 'screen_content'].includes(p)) return;
    presetDone.current = true;
    const next = new URLSearchParams(sp); next.delete('preset'); setSp(next, { replace: true });
    void runPreset(p as 'erase_text' | 'erase_people' | 'screen_content');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [image]);
  const harmonize = async () => {
    if (!active) return;
    setBusy('harm'); setNote(null);
    try { const v = await img.adjust(imageId, { harmonize_region_id: active.id }); setNote({ text: `주변과 밝기를 맞춘 ${v.label} 버전을 만들었어요`, ok: true }); await inv.image(imageId); }
    catch (e) { setNote({ text: errMessage(e), ok: false }); } finally { setBusy(null); }
  };
  const send = async (text: string) => {
    setNote(null);
    if (active && active.status !== 'applying') {
      await saveInstruction(active, text);
      await apply([active.id]);
      return;
    }
    setBusy('ask');
    try {
      const r = await img.interpret(imageId, { text, screen: 'edit' });
      if (r.action === 'region_edit' && (r.region as { rect?: number[] } | null)?.rect) {
        const reg = r.region as { rect: number[]; label?: string };
        const res = await img.addRegion(imageId, { shape: 'rect', rect: reg.rect, instruction: r.instruction || text, label: reg.label });
        if (res.region) { setActiveId(res.region.id); await apply([res.region.id]); }
      } else if (r.action === 'global_edit' || r.action === 'region_edit') {
        const acc = await img.edit(imageId, { mode: 'global', instruction: r.instruction || text, protect_products: protect });
        setGlobalJob(acc.job_id); setNote({ text: '전체 이미지에 적용하는 중이에요', ok: true });
      } else setNote({ text: r.question ?? '어디를 어떻게 바꿀지 조금 더 알려 주세요', ok: false });
      await rq.refetch();
    } catch (e) { setNote({ text: errMessage(e), ok: false }); } finally { setBusy(null); }
  };
  const restore = async (v: Version) => {
    try { await img.restore(imageId, v.n); setPreview(null); await inv.image(imageId); setNote({ text: `${v.short_label || v.label}${josa(v.short_label || v.label, '으로', '로')} 되돌린 새 버전을 만들었어요`, ok: true }); }
    catch (e) { setNote({ text: errMessage(e), ok: false }); }
  };
  const toExport = async () => {
    try { await img.save(imageId); } catch { /* 저장은 IMG4 에서도 한다 */ }
    nav(route.exportTo(workId, imageId));
  };
  const showDetections = async () => {
    setTool('object');
    if (dets || !objectOk) return;
    try { const d = await img.detections(imageId, {}); setDets([...d.boxes].sort((a, b) => (b.box[2] - b.box[0]) * (b.box[3] - b.box[1]) - (a.box[2] - a.box[0]) * (a.box[3] - a.box[1]))); } catch (e) { setNote({ text: errMessage(e), ok: false }); }
  };
  const pickDetection = async (id: string) => {
    try { const res = await img.addRegion(imageId, { shape: 'object', detection_id: id }); if (res.region) setActiveId(res.region.id); await rq.refetch(); } catch (e) { setNote({ text: errMessage(e), ok: false }); }
  };

  useImgShell({ title: image?.work_title || image?.title || '부분 수정', step: 3 });
  if (iq.isLoading) return <Loading />;
  if (!image || !current) return <div className="img-center"><ErrorState message="시안을 불러오지 못했어요" onRetry={() => iq.refetch()} /></div>;

  const echo = (loc.state as { echo?: string } | null)?.echo ?? image.label;
  const firstApplied = regions.find((r) => r.status === 'applied');
  const wText = `바꿀 곳을 사각형이나 브러시로 지정하고 영역마다 지시문을 적어 주세요. 선택한 영역 밖은 그대로 둡니다.${firstApplied
    ? ` 영역 ${firstApplied.n}${josa(String(firstApplied.n), '을', '를')} 먼저 고쳤으니 가운데 손잡이를 끌어 전/후를 비교해 보세요.` : ''}`;
  const product = image.products?.[0];
  const pending = regions.filter((r) => r.status !== 'applied' && r.status !== 'reverted');
  const TOOLS: Array<{ key: Tool; label: string; d: string; off?: boolean; tip?: string }> = [
    { key: 'rect', label: '사각형', d: PATH.rect }, { key: 'brush', label: '브러시', d: PATH.brush },
    { key: 'object', label: '객체 선택', d: PATH.object, off: !objectOk, tip: '지금 모델은 객체 인식을 지원하지 않아요' }, { key: 'eraser', label: '지우개', d: PATH.eraser },
  ];
  const R = (r: number[]) => ({ left: `${r[0] * 100}%`, top: `${r[1] * 100}%`, width: `${(r[2] - r[0]) * 100}%`, height: `${(r[3] - r[1]) * 100}%` });
  return (
    <Screen testid="img3e" composer={
      <div className="wm-composer-wrap">
        <div className="wm-composer">
          <div className="wm-composer__head">
            <span data-testid="img3e-head">{active ? `영역 ${active.n} 지시문` : '영역 지시문'}<small> · 부분 수정</small></span>
            <span className="img-quick">
              <Pill disabled={!!busy || applying} onClick={() => void runPreset('erase_text')}>글자 지우기</Pill>
              <Pill disabled={!!busy || applying} onClick={() => void runPreset('erase_people')}>사람 지우기</Pill>
              <Pill disabled={!!busy || applying} onClick={() => void runPreset('screen_content')}>제품 화면에 콘텐츠 넣기</Pill>
              <Pill disabled={!active || active.status !== 'applied' || !!busy} title={!active || active.status !== 'applied' ? '적용한 영역을 먼저 골라 주세요' : undefined}
                onClick={() => void harmonize()}>주변과 밝기 맞추기</Pill>
            </span>
          </div>
          {note && <div className={cx('img-askline', !note.ok && 'img-err')} role="status" data-testid="img3e-note">{globalJob ? <Spinner /> : <Icon name={note.ok ? 'check' : 'info'} size={13} />}{note.text}</div>}
          <div className="wm-composer__foot">
            <AskInput label="선택한 영역 수정 지시" placeholder="영역을 어떻게 바꿀까요? (예: 시즌 메뉴 사진 넣기)" busy={busy === 'ask'} onSend={send} testid="img3e-ask" />
            <Button h={44} onClick={() => nav(route.result(workId, imageId))}>결과로 돌아가기</Button>
            <Button h={44} variant="primary" onClick={() => void toExport()} iconRight={<Icon name="arrowRight" size={16} strokeWidth={2.2} />}>저장하고 내보내기</Button>
          </div>
        </div>
      </div>
    }>
      <Echo head="부분 수정" text={echo} />
      <WSay text={wText}>
        <div className="img-card">
          <div className="img-edit__bar">
            <div role="group" aria-label="영역 선택 도구" className="img-seg">
              {TOOLS.map((t) => (
                <button key={t.key} type="button" aria-pressed={tool === t.key} disabled={t.off} title={t.off ? t.tip : t.label}
                  onClick={() => (t.key === 'object' ? void showDetections() : setTool(t.key))}>
                  <Ico d={t.d} size={14} />{t.label}
                </button>
              ))}
            </div>
            <span className="img-vsep" />
            <div className="img-sizes" role="group" aria-label="크기">
              <span className="img-label">크기</span>
              {SIZES.map((s) => (
                <button key={s.px} type="button" aria-label={s.label} aria-pressed={size === s.px} onClick={() => setSize(s.px)}>
                  <span style={{ width: s.dot, height: s.dot }} />
                </button>
              ))}
            </div>
            <span style={{ flex: 1 }} />
            <button type="button" className="img-sqbtn" aria-label="실행 취소" disabled={!undo.length} onClick={() => void doUndo()}><Icon name="undo" size={14} /></button>
            <button type="button" className="img-sqbtn" aria-label="다시 실행" disabled={!redo.length} onClick={() => void doRedo()}><Ico d={PATH.redo} size={14} /></button>
            <div role="group" aria-label="보기" className="img-seg" style={{ marginLeft: 4 }}>
              <button type="button" aria-pressed={view === 'edit'} onClick={() => setView('edit')}>편집</button>
              <button type="button" aria-pressed={view === 'compare'} disabled={!canCompare} title={!canCompare ? '비교할 수정 버전이 아직 없어요' : undefined} onClick={() => { setPreview(null); setView('compare'); }}>전/후 비교</button>
            </div>
          </div>
          <div className="img-edit__body">
            <div className="img-edit__main">
              <div ref={wrapRef} className="img-edit__canvas" style={{ height: ch, cursor: view === 'compare' ? 'ew-resize' : tool === 'object' ? 'default' : 'crosshair' }}
                onPointerDown={onDown} onPointerMove={onMove} onPointerUp={() => void onUp()} onPointerCancel={() => void onUp()} data-testid="img3e-canvas">
                {view === 'compare' && canCompare ? (
                  <>
                    <img src={cmp.before!.url} alt={`전 · ${cmp.before!.short_label || cmp.before!.label}`} draggable={false} />
                    <img src={cmp.after!.url} alt={`후 · ${cmp.after!.short_label || cmp.after!.label}`} draggable={false} style={{ clipPath: `inset(0 0 0 ${split * 100}%)` }} />
                    <span className="img-cmp__line" style={{ left: `${split * 100}%` }} />
                    <button type="button" className="img-cmp__knob" style={{ left: `${split * 100}%` }} aria-label="전/후 비교 손잡이" role="slider"
                      aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(split * 100)}
                      onKeyDown={(e) => { if (e.key === 'ArrowLeft') setSplit((s) => Math.max(0, s - 0.05)); if (e.key === 'ArrowRight') setSplit((s) => Math.min(1, s + 0.05)); }}>
                      <Ico d={PATH.compare} size={14} sw={2.4} />
                    </button>
                    <span className="img-cmp__tag img-cmp__tag--before" data-testid="img3e-before">전 · {cmp.before!.short_label || cmp.before!.label}</span>
                    <span className="img-cmp__tag img-cmp__tag--after" data-testid="img3e-after">후 · {cmp.after!.short_label || cmp.after!.label}</span>
                  </>
                ) : (
                  <>
                    <img src={shown?.url} alt={`${image.label} — ${shown?.short_label || shown?.label || ''}`} draggable={false} />
                    <canvas ref={maskRef} width={cw} height={ch} style={{ pointerEvents: 'none' }} />
                  </>
                )}
                {view === 'edit' && !preview && regions.filter((r) => r.rect && r.status !== 'reverted').map((r) => (
                  <span key={r.id} className={cx('img-rect', r.status !== 'applied' && 'img-rect--pending', r.id === activeId && 'img-rect--active')} style={{ ...R(r.rect!), pointerEvents: 'none' }}>
                    <span className="img-rect__n">{r.n}</span>
                  </span>
                ))}
                {view === 'compare' && regions.filter((r) => r.rect && r.status !== 'reverted').map((r) => (
                  <span key={r.id} className={cx('img-rect', r.status !== 'applied' && 'img-rect--pending')} style={{ ...R(r.rect!), pointerEvents: 'none' }}><span className="img-rect__n">{r.n}</span></span>
                ))}
                {temp && <span className="img-rect img-rect--active" style={{ ...R(temp), pointerEvents: 'none' }} />}
                {view === 'edit' && tool === 'object' && dets && dets.map((d) => (
                  <button key={d.id} type="button" className="img-rect img-rect--det" style={{ ...R(d.box), position: 'absolute' }} aria-label={`${d.label} 선택`} title={d.label}
                    onPointerDown={(e) => e.stopPropagation()} onClick={() => void pickDetection(d.id)} />
                ))}
              </div>
              <div className="img-hist" data-testid="img3e-history">
                <span className="img-label">수정 기록</span>
                {versions.map((v, i) => (
                  <span key={v.id} className="img-row" style={{ gap: 8 }}>
                    {i > 0 && <Icon name="chevronRight" size={12} color="var(--wm-text-subtle)" />}
                    <button type="button" className="img-hist__btn" aria-pressed={(preview ?? current.id) === v.id} onClick={() => { setView('edit'); setPreview(v.id === current.id ? null : v.id); }}>
                      <span className="img-hist__img"><Img src={v.thumb_url} alt={`${v.short_label || v.label} 썸네일`} /></span>
                      <span>{v.label}</span>
                    </button>
                  </span>
                ))}
                <span style={{ flex: 1 }} />
                {preview && shown ? (
                  <Button h={32} variant="primary" onClick={() => void restore(shown)}>되돌리기</Button>
                ) : <span className="img-hint" style={{ fontSize: 11.5, color: 'var(--wm-text-subtle)' }}>영역 밖 픽셀은 원본 유지</span>}
              </div>
            </div>
            <div className="img-edit__side">
              <div className="img-row" style={{ justifyContent: 'space-between', minHeight: 18 }}>
                <span style={{ fontSize: 12.5, fontWeight: 600 }}>수정 영역<small style={{ color: 'var(--wm-text-muted)', fontWeight: 500, fontSize: 12.5 }}> · {regions.filter((r) => r.status !== 'reverted').length}</small></span>
                <button type="button" className="img-pill img-pill--h26" style={{ border: 'none', color: 'var(--wm-text-muted)', fontSize: 11.5 }} disabled={!pending.length} onClick={() => void clearAll()}>모두 지우기</button>
              </div>
              {regions.map((r) => <RegionCard key={r.id} r={r} on={r.id === activeId} onPick={() => { setActiveId(r.id); setPreview(null); }}
                onApply={(t) => void (async () => { await saveInstruction(r, t); await apply([r.id]); })()} onRevert={() => void revert(r)}
                onSave={(t) => void saveInstruction(r, t)} />)}
              <button type="button" className="img-addregion" onClick={() => { setTool('rect'); setActiveId(null); setView('edit'); setNote({ text: '사진 위에서 끌어 새 영역을 지정해 주세요', ok: true }); }}>
                <Icon name="plus" size={13} />영역 추가
              </button>
              {product && (
                <div style={{ borderTop: '1px solid var(--wm-line)', paddingTop: 10, display: 'flex', flexDirection: 'column', gap: 4 }}>
                  <div className="img-row" style={{ justifyContent: 'space-between' }}>
                    <span style={{ fontSize: 12.5, fontWeight: 600 }}>제품 외형 고정</span>
                    <Switch label="제품 외형 고정" checked={protect} onChange={(v) => { setProtect(v); if (active) void img.patchRegion(imageId, active.id, { protect_products: v }); }} />
                  </div>
                  <span className="img-hint img-hint--sm" style={{ lineHeight: 1.5 }}>{product.short} 외형 · 비율은 바뀌지 않아요</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </WSay>
    </Screen>
  );
}

function RegionCard({ r, on, onPick, onApply, onRevert, onSave }:
  { r: EditRegion; on: boolean; onPick: () => void; onApply: (text: string) => void; onRevert: () => void; onSave: (t: string) => void }) {
  const [text, setText] = useState(r.instruction);
  useEffect(() => { setText(r.instruction); }, [r.instruction]);
  const applied = r.status === 'applied';
  return (
    <div className={cx('img-region', on && 'img-region--on', applied && 'img-region--applied')} onClick={onPick} data-testid="img3e-region" data-status={r.status}>
      <div className="img-row" style={{ gap: 7 }}>
        <span className="img-region__n">{r.n}</span>
        <span className="img-region__name" title={r.label}>{r.label}</span>
      </div>
      <textarea className="img-region__text" rows={2} value={text} aria-label={`영역 ${r.n} 지시문`} placeholder="지시문을 적어 주세요" readOnly={applied || r.status === 'applying'}
        onChange={(e) => setText(e.target.value)} onBlur={() => onSave(text.trim())} onClick={(e) => e.stopPropagation()} />
      <div className="img-row" style={{ justifyContent: 'space-between' }}>
        <span className={cx('img-region__st', applied && 'img-region__st--on')}>
          {applied ? <Icon name="check" size={12} strokeWidth={2.6} /> : r.status === 'applying' ? <Spinner /> : <Icon name="clock" size={12} />}{r.status_label}
        </span>
        {applied && <button type="button" className="img-mini" onClick={(e) => { e.stopPropagation(); onRevert(); }}>되돌리기</button>}
        {(r.status === 'pending' || r.status === 'reverted') && (
          <button type="button" className="img-mini img-mini--primary" disabled={!text.trim()} title={!text.trim() ? '지시문을 먼저 적어 주세요' : undefined}
            onClick={(e) => { e.stopPropagation(); onApply(text.trim()); }}>적용</button>
        )}
        {r.status === 'failed' && <button type="button" className="img-mini img-mini--primary" onClick={(e) => { e.stopPropagation(); onApply(text.trim()); }}>다시 적용</button>}
      </div>
    </div>
  );
}
