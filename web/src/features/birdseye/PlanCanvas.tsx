/**
 * 2D 평면 · 배치안 캔버스(SVG, 엔진 좌표 그대로) — BE1D 인식 결과 · BE4 배치안 · BE4E 직접 수정 · BE0 미리보기.
 * 좌표: m, x → 오른쪽, y → 아래(위 = 정면). 보드 BE4: 외곽 회색 선 · 창 brand 굵은 선 · 기둥 회색 사각 · 제품 brand 채움 ·
 * 가구 점선 · 기둥 랩핑 brand 테두리 · 범례 「삼성 제품」 「가구」 「기둥」.
 */
import { useMemo, useRef, useState, type PointerEvent as RPointerEvent } from 'react';
import type { LayoutGroup, LayoutItem, LayoutWarning, MoveMark, Overlays, PlanGeometry } from './api';

export type Tool = 'move' | 'rotate' | 'measure';
export type Highlight = 'wall' | 'window' | 'door' | 'column' | 'core' | null;

interface Props {
  plan: PlanGeometry;
  items?: LayoutItem[];
  groups?: LayoutGroup[];
  width?: number;
  height?: number;
  overlays?: Overlays | null;
  show?: { fans?: boolean; paths?: boolean; power?: boolean; dims?: boolean };
  warnings?: LayoutWarning[];
  ghosts?: MoveMark[];
  tool?: Tool | null;
  pickPoint?: boolean;
  onMove?: (target: string, dx: number, dy: number) => void;
  onRotate?: (target: string, deg: number) => void;
  onPick?: (x: number, y: number) => void;
  onDragStart?: (target: string) => void;
  highlight?: Highlight;
  legend?: 'basic' | 'edit' | 'plan' | 'none';
  pageImage?: { url: string; box?: number[] | null } | null;
  showImage?: boolean;
  zoom?: number;
  testId?: string;
  ariaLabel?: string;
  compact?: boolean;
}

const PAD = { l: 40, r: 40, t: 24, b: 30 };
const r1 = (v: number) => Math.round(v * 10) / 10;

function bboxOf(plan: PlanGeometry): [number, number, number, number] {
  const xs: number[] = [];
  const ys: number[] = [];
  for (const r of plan.rooms ?? []) for (const p of r.outline) { xs.push(p[0]); ys.push(p[1]); }
  for (const w of plan.walls ?? []) { xs.push(w.a[0], w.b[0]); ys.push(w.a[1], w.b[1]); }
  if (!xs.length) return [0, 0, plan.width_m || 10, plan.height_m || 8];
  return [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)];
}

function textW(s: string, size: number): number {
  let w = 0;
  for (const ch of s) w += /[가-힣]/.test(ch) ? size * 0.98 : /[A-Z0-9"]/.test(ch) ? size * 0.64 : /\s/.test(ch) ? size * 0.3 : size * 0.55;
  return w;
}

function corners(it: { x: number; y: number; w: number; d: number; rot_deg?: number }): Array<[number, number]> {
  const t = ((it.rot_deg ?? 0) * Math.PI) / 180;
  const wx = Math.cos(t), wy = Math.sin(t);
  const fx = -Math.sin(t), fy = Math.cos(t);
  const hw = it.w / 2, hd = it.d / 2;
  return [[-hw, -hd], [hw, -hd], [hw, hd], [-hw, hd]].map(([a, b]) => [it.x + a * wx + b * fx, it.y + a * wy + b * fy]);
}

export function PlanCanvas({ plan, items = [], groups = [], width = 760, height = 300, overlays, show = {}, warnings = [], ghosts = [],
  tool = null, pickPoint, onMove, onRotate, onPick, onDragStart, highlight = null, legend = 'basic', pageImage, showImage, zoom = 1,
  testId, ariaLabel = '2D 배치안', compact }: Props) {
  const [minx, miny, maxx, maxy] = useMemo(() => bboxOf(plan), [plan]);
  const pad = compact ? { l: 12, r: 12, t: 12, b: 12 } : PAD;
  const s0 = Math.min((width - pad.l - pad.r) / Math.max(maxx - minx, 1), (height - pad.t - pad.b) / Math.max(maxy - miny, 1));
  const s = s0 * zoom;
  const ox = (width - (maxx - minx) * s) / 2;
  const oy = pad.t + (height - pad.t - pad.b - (maxy - miny) * s) / 2;
  const X = (x: number) => ox + (x - minx) * s;
  const Y = (y: number) => oy + (y - miny) * s;
  const svgRef = useRef<SVGSVGElement>(null);
  type Drag = { target: string; ids: string[]; x0: number; y0: number; dx: number; dy: number };
  const [drag, setDragState] = useState<Drag | null>(null);
  /** 끌기 상태는 ref 로도 들고 있는다 — 빠른 끌기에서 놓는 순간 최신 이동량을 잃지 않게 */
  const dragRef = useRef<Drag | null>(null);
  const setDrag = (d: Drag | null) => { dragRef.current = d; setDragState(d); };
  const [measure, setMeasure] = useState<Array<[number, number]>>([]);

  const toM = (e: { clientX: number; clientY: number }): [number, number] => {
    const r = svgRef.current?.getBoundingClientRect();
    if (!r) return [0, 0];
    const px = ((e.clientX - r.left) / r.width) * width;
    const py = ((e.clientY - r.top) / r.height) * height;
    return [minx + (px - ox) / s, miny + (py - oy) / s];
  };

  const byGroup = useMemo(() => {
    const m = new Map<string, LayoutItem[]>();
    for (const it of items) { if (!m.has(it.group_id)) m.set(it.group_id, []); m.get(it.group_id)!.push(it); }
    return m;
  }, [items]);

  /** 끌기 대상: 좌석 열 묶음 · 가구 여러 개는 묶음째, 그 밖은 항목 하나 */
  const targetOf = (it: LayoutItem): { target: string; ids: string[] } => {
    const g = byGroup.get(it.group_id) ?? [it];
    if (it.kind === 'furniture' && g.length > 1) return { target: it.group_id, ids: g.map((x) => x.id) };
    return { target: it.id, ids: [it.id] };
  };

  const onItemDown = (e: RPointerEvent, it: LayoutItem) => {
    if (!tool && !onDragStart) return;
    e.stopPropagation();
    if (tool === 'rotate') { onRotate?.(it.id, e.shiftKey ? -15 : 15); return; }
    if (tool === 'measure') return;
    const [mx, my] = toM(e);
    const t = targetOf(it);
    (e.target as Element).setPointerCapture?.(e.pointerId);
    setDrag({ ...t, x0: mx, y0: my, dx: 0, dy: 0 });
  };
  const onPointerMove = (e: RPointerEvent) => {
    const cur = dragRef.current;
    if (!cur) return;
    const [mx, my] = toM(e);
    const dx = r1(mx - cur.x0), dy = r1(my - cur.y0);
    if (dx !== cur.dx || dy !== cur.dy) {
      if (!cur.dx && !cur.dy && (dx || dy)) onDragStart?.(cur.target);
      setDrag({ ...cur, dx, dy });
    }
  };
  const onPointerUp = () => {
    const d = dragRef.current;
    if (!d) return;
    setDrag(null);
    if (Math.abs(d.dx) >= 0.1 || Math.abs(d.dy) >= 0.1) onMove?.(d.target, d.dx, d.dy);
  };
  const onBgClick = (e: React.MouseEvent) => {
    const [x, y] = toM(e);
    if (pickPoint) { onPick?.(r1(x), r1(y)); return; }
    if (tool === 'measure') setMeasure((m) => (m.length >= 2 ? [[x, y]] : [...m, [x, y]]));
  };

  const offset = (id: string): [number, number] => (drag && drag.ids.includes(id) ? [drag.dx, drag.dy] : [0, 0]);
  const poly = (pts: Array<[number, number]>) => pts.map(([x, y]) => `${X(x).toFixed(1)},${Y(y).toFixed(1)}`).join(' ');

  // 벽 위 개구부 좌표
  const wallById = new Map((plan.walls ?? []).map((w) => [w.id, w]));
  const openingSeg = (o: { wall_id: string; offset: number; width: number }) => {
    const w = wallById.get(o.wall_id);
    if (!w) return null;
    const L = Math.hypot(w.b[0] - w.a[0], w.b[1] - w.a[1]) || 1;
    const ux = (w.b[0] - w.a[0]) / L, uy = (w.b[1] - w.a[1]) / L;
    return { x1: w.a[0] + ux * o.offset, y1: w.a[1] + uy * o.offset, x2: w.a[0] + ux * (o.offset + o.width), y2: w.a[1] + uy * (o.offset + o.width), ux, uy };
  };
  const windows = (plan.openings ?? []).filter((o) => o.kind === 'window');
  const doors = (plan.openings ?? []).filter((o) => o.kind !== 'window');
  const winLabel = plan.window_label || windows[0]?.label;

  // 묶음 라벨
  const labels = groups.map((g) => {
    const its = (byGroup.get(g.id) ?? []).filter((x) => !x.unplaced);
    if (!its.length) return null;
    const pts = its.flatMap((it) => { const [dx, dy] = offset(it.id); return corners({ ...it, x: it.x + dx, y: it.y + dy }); });
    const x0 = Math.min(...pts.map((p) => X(p[0]))), x1 = Math.max(...pts.map((p) => X(p[0])));
    const y0 = Math.min(...pts.map((p) => Y(p[1]))), y1 = Math.max(...pts.map((p) => Y(p[1])));
    return { g, x0, x1, y0, y1, kind: its[0].kind };
  }).filter(Boolean) as Array<{ g: LayoutGroup; x0: number; x1: number; y0: number; y1: number; kind: string }>;

  const fs = compact ? 8 : 10.5;
  const lab = compact ? [] : placeLabels(labels, fs, width, height);
  /** 창 라벨은 벽 제품 띠와 겹치면 한 줄씩 아래로 */
  const winPos = (() => {
    const x = X(minx) + 8;
    let y = Y(miny) + 14;
    const w = textW(winLabel || '', fs) + 4;
    for (let k = 0; k < 3; k++) {
      const box = { x0: x, y0: y - fs / 2 - 2, x1: x + w, y1: y + fs / 2 + 2 };
      if (!lab.some((l) => l.bar && overlap({ x0: l.bar.x, y0: l.bar.y, x1: l.bar.x + l.bar.w, y1: l.bar.y + l.bar.h }, box))) break;
      y += fs + 8;
    }
    return { x, y };
  })();
  return (
    <div className="be-plan" style={{ width, height }} data-testid={testId}>
      <svg ref={svgRef} width={width} height={height} viewBox={`0 0 ${width} ${height}`} role="img" aria-label={ariaLabel}
        onPointerMove={onPointerMove} onPointerUp={onPointerUp} onPointerLeave={onPointerUp} onClick={onBgClick}
        className={pickPoint ? 'be-plan--pick' : tool === 'measure' ? 'be-plan--measure' : undefined}>
        <defs>
          <pattern id="be-hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
            <line x1="0" y1="0" x2="0" y2="6" className="be-hatch-line" />
          </pattern>
        </defs>
        {showImage && pageImage?.url && (
          <image href={pageImage.url} opacity={0.55} preserveAspectRatio="none"
            {...(() => {
              const b = pageImage.box && pageImage.box.length === 4 ? pageImage.box : [0, 0, 1, 1];
              const fw = (maxx - minx) * s / Math.max(b[2] - b[0], 0.01);
              const fh = (maxy - miny) * s / Math.max(b[3] - b[1], 0.01);
              return { x: X(minx) - b[0] * fw, y: Y(miny) - b[1] * fh, width: fw, height: fh };
            })()} />
        )}
        {/* 바닥 · 외곽 */}
        {(plan.rooms ?? []).map((r) => (
          <polygon key={r.id} points={poly(r.outline as Array<[number, number]>)} className={highlight === 'wall' ? 'be-room be-room--hl' : 'be-room'} />
        ))}
        {(plan.walls ?? []).filter((w) => w.kind === 'interior').map((w) => (
          <line key={w.id} x1={X(w.a[0])} y1={Y(w.a[1])} x2={X(w.b[0])} y2={Y(w.b[1])} className="be-wall-in" />
        ))}
        {/* 코어 */}
        {(plan.cores ?? []).map((k) => (
          <g key={k.id} className={highlight === 'core' ? 'be-hl' : undefined}>
            <polygon points={poly(k.polygon as Array<[number, number]>)} className="be-core" />
            {!compact && (() => {
              const cx = k.polygon.reduce((a, p) => a + p[0], 0) / k.polygon.length;
              const cy = k.polygon.reduce((a, p) => a + p[1], 0) / k.polygon.length;
              const names = (k.kinds ?? []).map((x) => ({ ev: 'EV', stairs: '계단', toilet: '화장실', shaft: '샤프트' } as Record<string, string>)[x] ?? x).join(' · ');
              return <text x={X(cx)} y={Y(cy)} className="be-t be-t--core" textAnchor="middle" dominantBaseline="middle">{names || '코어'}</text>;
            })()}
          </g>
        ))}
        {/* 창 · 문 */}
        {windows.map((o) => {
          const sg = openingSeg(o);
          if (!sg) return null;
          return <line key={o.id} x1={X(sg.x1)} y1={Y(sg.y1)} x2={X(sg.x2)} y2={Y(sg.y2)} className={highlight === 'window' ? 'be-win be-hl-stroke' : 'be-win'} />;
        })}
        {doors.map((o) => {
          const sg = openingSeg(o);
          if (!sg) return null;
          const r = Math.hypot(sg.x2 - sg.x1, sg.y2 - sg.y1) * s;
          const nx = -sg.uy, ny = sg.ux;        // 벽 안쪽(시계 방향 외곽 기준 오른쪽)
          return (
            <g key={o.id} className={highlight === 'door' ? 'be-hl' : undefined}>
              <line x1={X(sg.x1)} y1={Y(sg.y1)} x2={X(sg.x2)} y2={Y(sg.y2)} className="be-door-gap" />
              {!compact && <path d={`M ${X(sg.x1)} ${Y(sg.y1)} L ${X(sg.x1) + nx * r} ${Y(sg.y1) + ny * r} A ${r} ${r} 0 0 ${1} ${X(sg.x2)} ${Y(sg.y2)}`}
                className={o.is_main ? 'be-door be-door--main' : 'be-door'} />}
            </g>
          );
        })}
        {/* 기둥 */}
        {(plan.columns ?? []).map((c) => (
          <rect key={c.id} x={X(c.center[0] - c.w / 2)} y={Y(c.center[1] - c.d / 2)} width={Math.max(c.w * s, 4)} height={Math.max(c.d * s, 4)} rx={2}
            className={highlight === 'column' ? 'be-col-rect be-hl-fill' : 'be-col-rect'} />
        ))}
        {/* 시야각 부채꼴 */}
        {show.fans && overlays?.fans?.map((f) => {
          const a0 = ((f.dir_deg - f.half_angle_deg) * Math.PI) / 180, a1 = ((f.dir_deg + f.half_angle_deg) * Math.PI) / 180;
          const [ax, ay] = f.apex;
          const P = (r: number, a: number) => `${X(ax + r * Math.cos(a)).toFixed(1)} ${Y(ay + r * Math.sin(a)).toFixed(1)}`;
          const R1 = f.min_d * s, R2 = f.max_d * s;
          const d = `M ${P(f.min_d, a0)} L ${P(f.max_d, a0)} A ${R2} ${R2} 0 0 1 ${P(f.max_d, a1)} L ${P(f.min_d, a1)} A ${R1} ${R1} 0 0 0 ${P(f.min_d, a0)} Z`;
          return <path key={f.item_id} d={d} className="be-fan" />;
        })}
        {/* 동선 */}
        {show.paths && overlays?.paths?.map((p, i) => (
          <polyline key={i} points={poly(p.points as Array<[number, number]>)} className="be-path" />
        ))}
        {show.paths && overlays?.bottlenecks?.map((b, i) => (
          <circle key={i} cx={X(b.pos[0])} cy={Y(b.pos[1])} r={5} className="be-bottleneck" />
        ))}
        {/* 원래 위치 유령 */}
        {ghosts.map((g) => (
          <g key={`ghost-${g.item_id}`}>
            <polygon points={poly(corners({ x: g.from_x, y: g.from_y, w: g.w || 0.5, d: Math.max(g.d || 0.1, 0.3), rot_deg: g.rot_deg }))} className="be-ghost" />
            {!compact && <text x={X(g.from_x)} y={Y(g.from_y) - 8} className="be-t be-t--ghost" textAnchor="middle">원래 위치</text>}
          </g>
        ))}
        {/* 항목 */}
        {items.filter((it) => !it.unplaced).map((it) => {
          const [dx, dy] = offset(it.id);
          const thin = it.kind === 'product' && it.d * s < 8;
          const shape = { ...it, x: it.x + dx, y: it.y + dy, d: thin ? 8 / s : it.d };
          const cls = it.kind === 'product' ? 'be-item be-item--product' : it.kind === 'column_wrap' ? 'be-item be-item--wrap' : 'be-item be-item--furn';
          return (
            <polygon key={it.id} points={poly(corners(shape))} className={cls} data-item={it.id}
              style={{ cursor: tool === 'move' || onDragStart ? 'grab' : tool === 'rotate' ? 'alias' : undefined }}
              onPointerDown={(e) => onItemDown(e, it)} />
          );
        })}
        {/* 전원 */}
        {show.power && (plan.power_points ?? []).map((p) => (
          <circle key={p.id} cx={X(p.pos[0])} cy={Y(p.pos[1])} r={4} className="be-power" />
        ))}
        {show.power && overlays?.power_links?.map((l, i) => l.b ? (
          <line key={i} x1={X(l.a[0])} y1={Y(l.a[1])} x2={X(l.b[0])} y2={Y(l.b[1])} className="be-power-link" />
        ) : null)}
        {/* 묶음 라벨 — 다른 묶음 · 이미 놓은 라벨과 겹치지 않는 첫 자리(오른쪽 → 아래 → 왼쪽 → 위) */}
        {lab.map((L) => {
          if (L.bar) {
            return (
              <g key={L.id} pointerEvents="none">
                <rect x={L.bar.x} y={L.bar.y} width={L.bar.w} height={L.bar.h} rx={3} className="be-label-bar" />
                <text x={L.bar.x + L.bar.w / 2} y={L.bar.y + L.bar.h / 2 + 0.5} className="be-t be-t--onbrand" textAnchor="middle" dominantBaseline="middle">{L.text}</text>
              </g>
            );
          }
          return <text key={L.id} x={L.x} y={L.y} className={L.cls} textAnchor={L.anchor} dominantBaseline="middle" pointerEvents="none">{L.text}</text>;
        })}
        {/* 위쪽 라벨 */}
        {!compact && winLabel && <text x={winPos.x} y={winPos.y} className="be-t be-t--brand">{winLabel}</text>}
        {!compact && plan.area_label && <text x={X(maxx) - 8} y={Y(miny) + 14} className="be-t be-t--muted" textAnchor="end">{plan.area_label}</text>}
        {/* 이동 라벨 */}
        {ghosts.map((g) => {
          const it = items.find((x) => x.id === g.item_id);
          if (!it) return null;
          return <text key={`mv-${g.item_id}`} x={X(it.x)} y={Y(it.y) - 14} className="be-t be-t--move" textAnchor="middle">{g.label_ko}</text>;
        })}
        {/* 경고 번호 */}
        {warnings.filter((w) => w.status === 'open' && w.marker).map((w) => (
          <g key={w.id} transform={`translate(${X(w.marker![0])},${Y(w.marker![1])})`} data-testid={`be-warn-marker-${w.n}`}>
            <circle r={10} className="be-warn-dot" />
            <text className="be-t be-t--warn" textAnchor="middle" dominantBaseline="central">{w.n}</text>
          </g>
        ))}
        {/* 치수 재기 */}
        {measure.length >= 1 && <circle cx={X(measure[0][0])} cy={Y(measure[0][1])} r={3} className="be-measure-dot" />}
        {measure.length === 2 && (
          <g>
            <line x1={X(measure[0][0])} y1={Y(measure[0][1])} x2={X(measure[1][0])} y2={Y(measure[1][1])} className="be-measure" />
            <text x={(X(measure[0][0]) + X(measure[1][0])) / 2} y={(Y(measure[0][1]) + Y(measure[1][1])) / 2 - 6} textAnchor="middle" className="be-t be-t--move"
              data-testid="be-measure-label">
              {(Math.hypot(measure[1][0] - measure[0][0], measure[1][1] - measure[0][1])).toFixed(1)} m
            </text>
          </g>
        )}
        {show.dims && (
          <g>
            <text x={(X(minx) + X(maxx)) / 2} y={Y(maxy) + 16} textAnchor="middle" className="be-t be-t--muted">{(maxx - minx).toFixed(1)} m</text>
            <text x={X(maxx) + 6} y={(Y(miny) + Y(maxy)) / 2} className="be-t be-t--muted">{(maxy - miny).toFixed(1)} m</text>
          </g>
        )}
      </svg>
      {legend !== 'none' && !compact && (
        <div className="be-legend">
          {legend === 'plan' ? (
            <>
              <span><i className="be-lg be-lg--wall" />벽</span>
              <span><i className="be-lg be-lg--win" />창</span>
              <span><i className="be-lg be-lg--door" />문</span>
              <span><i className="be-lg be-lg--col" />기둥</span>
              <span><i className="be-lg be-lg--core" />코어</span>
            </>
          ) : (
            <>
              <span><i className="be-lg be-lg--prod" />삼성 제품</span>
              <span><i className="be-lg be-lg--furn" />가구</span>
              {legend === 'basic' && <span><i className="be-lg be-lg--col" />기둥</span>}
              {legend === 'edit' && (
                <>
                  <span><i className="be-lg be-lg--fan" />시야각</span>
                  <span><i className="be-lg be-lg--path" />동선</span>
                  <span><i className="be-lg be-lg--power" />전원</span>
                  <span><i className="be-lg be-lg--warn" />경고</span>
                </>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}


type LabelIn = { g: LayoutGroup; x0: number; x1: number; y0: number; y1: number; kind: string };
type LabelOut = { id: string; text: string; x: number; y: number; anchor: 'start' | 'middle' | 'end'; cls: string;
  bar?: { x: number; y: number; w: number; h: number } };
type Box = { x0: number; y0: number; x1: number; y1: number };
const overlap = (a: Box, b: Box) => a.x0 < b.x1 && b.x0 < a.x1 && a.y0 < b.y1 && b.y0 < a.y1;

/** 라벨 자리 고르기 — 벽 제품(가로)은 띠, 나머지는 후보 자리 중 다른 묶음 · 놓인 라벨과 안 겹치는 첫 자리(없으면 첫 후보) */
function placeLabels(labels: LabelIn[], fs: number, width: number, height: number): LabelOut[] {
  const placed: Box[] = [];
  const out: LabelOut[] = [];
  const h = fs + 4;
  const order = (k: string) => (k === 'product' ? 0 : k === 'column_wrap' ? 1 : 2);
  const sorted = [...labels].sort((a, b) => order(a.kind) - order(b.kind));
  for (const L of sorted) {
    const { g, x0, x1, y0, y1, kind } = L;
    const text = kind === 'product' ? (g.plan_label || g.label) : g.label;
    const tw = textW(text, fs) + 4;
    const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
    if (kind === 'product' && x1 - x0 >= y1 - y0) {
      const w = Math.max(x1 - x0, tw + 8);
      const bh = Math.max(y1 - y0, 18);
      const lx = Math.min(Math.max(cx - w / 2, 2), width - w - 2);
      const bar = { x: lx, y: cy - bh / 2, w, h: bh };
      placed.push({ x0: bar.x, y0: bar.y, x1: bar.x + w, y1: bar.y + bh });
      out.push({ id: g.id, text, x: 0, y: 0, anchor: 'middle', cls: '', bar });
      continue;
    }
    const cls = kind === 'furniture' ? 'be-t be-t--furn' : 'be-t be-t--brand';
    const cands: Array<{ x: number; y: number; anchor: 'start' | 'middle' | 'end' }> = kind === 'furniture'
      ? [{ x: cx, y: cy, anchor: 'middle' }, { x: cx, y: y0 - h / 2 - 3, anchor: 'middle' }, { x: cx, y: y1 + h / 2 + 3, anchor: 'middle' },
        { x: x1 + 6, y: cy, anchor: 'start' }, { x: x0 - 6, y: cy, anchor: 'end' }]
      : [{ x: x1 + 6, y: cy, anchor: 'start' }, { x: cx, y: y1 + h / 2 + 4, anchor: 'middle' }, { x: x0 - 6, y: cy, anchor: 'end' },
        { x: cx, y: y0 - h / 2 - 4, anchor: 'middle' }];
    const boxOf = (c: { x: number; y: number; anchor: string }): Box => {
      const bx0 = c.anchor === 'start' ? c.x : c.anchor === 'end' ? c.x - tw : c.x - tw / 2;
      return { x0: bx0, y0: c.y - h / 2, x1: bx0 + tw, y1: c.y + h / 2 };
    };
    const others = labels.filter((o) => o.g.id !== g.id).map((o) => ({ x0: o.x0, y0: o.y0, x1: o.x1, y1: o.y1 }));
    const fits = (b: Box) => b.x0 >= 0 && b.x1 <= width && b.y0 >= 0 && b.y1 <= height
      && !placed.some((p) => overlap(p, b)) && !others.some((o) => overlap(o, b));
    const pick = cands.find((c) => fits(boxOf(c))) ?? cands[0];
    placed.push(boxOf(pick));
    out.push({ id: g.id, text, x: pick.x, y: pick.y, anchor: pick.anchor, cls });
  }
  return out;
}

