// 평면(SVG) — 실제 mm 좌표로 그린다. 원점 = 정면 왼쪽 모서리, X 오른쪽, Y 안쪽(아래).
// 모드: space(BP1 공간) · recog(BP1D 인식) · layout(BP3 배치) · zones(BP3Z 존) · view(읽기 전용)
import { s, h, fmt, SVGNS } from "./dom.js";

const T = 220; // 그림용 벽 두께(mm)
const C = { pri: "#1428a0", priSoft: "rgba(20,40,160,.07)", text: "#121417", t2: "#3d4452", muted: "#596170", faint: "#8a91a0", wall: "#d0d4db", grid: "#eef0f4", fixture: "#8a91a0" };
export const DEFAULT_LAYERS = { grid: true, dims: true, view: true, flow: true, power: false, zones: true, labels: true, warnings: true, fixtures: true };
let UID = 0;

const WALL = {
  front: { a: [1, 0], n: [0, 1] }, back: { a: [1, 0], n: [0, -1] },
  left: { a: [0, 1], n: [1, 0] }, right: { a: [0, 1], n: [-1, 0] },
};
export function wallPoint(sp, wall, t, inset = 0) {
  if (wall === "front") return [t, inset];
  if (wall === "back") return [t, sp.depth - inset];
  if (wall === "left") return [inset, t];
  return [sp.width - inset, t];
}
export function rotRect(cx, cy, w, d, rot) {
  const r = (rot || 0) * Math.PI / 180, c = Math.cos(r), sn = Math.sin(r);
  return [[-w / 2, -d / 2], [w / 2, -d / 2], [w / 2, d / 2], [-w / 2, d / 2]].map(([x, y]) => [cx + x * c - y * sn, cy + x * sn + y * c]);
}
const pts = poly => poly.map(p => p[0].toFixed(1) + "," + p[1].toFixed(1)).join(" ");
const bboxOf = poly => { const xs = poly.map(p => p[0]), ys = poly.map(p => p[1]); return [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)]; };
export function nearestWall(sp, x, y) {
  const c = [["front", y], ["back", sp.depth - y], ["left", x], ["right", sp.width - x]].sort((a, b) => a[1] - b[1]);
  return { wall: c[0][0], dist: c[0][1] };
}
export function openingWallOfAnchor(sp, anchor) {
  if (!anchor) return null;
  if (anchor.startsWith("wall:")) return anchor.split(":")[1];
  if (anchor.startsWith("window:")) { const o = (sp.openings || []).find(o => o.id === anchor.split(":")[1]); return o ? o.wall : null; }
  return null;
}

export class PlanView {
  constructor(box, opts = {}) {
    this.uid = "pv" + (++UID);
    this.box = box;
    this.o = { mode: "layout", tool: "select", snap: 100, editable: true, hud: true, bg: null, ...opts };
    this.o.layers = { ...DEFAULT_LAYERS, ...(opts.layers || {}) };
    this.d = { project: null, v: null, sel: null, focus: null, flags: [], zoneSel: null, extra: null };
    this.zoom = 1; this.cx = null; this.cy = null;
    this.svg = document.createElementNS(SVGNS, "svg");
    this.svg.setAttribute("preserveAspectRatio", "xMidYMid meet");
    this.svg.setAttribute("role", "img");
    this.svg.setAttribute("aria-label", "평면도");
    this.hud = h("div", { class: "hud" + (this.o.hud ? "" : " hidden") });
    box.append(this.svg, this.hud);
    this.drag = null; this.pan = null; this.measure = null; this.cursor = null;
    if (!this.o.static) {
      this.svg.addEventListener("pointerdown", e => this.down(e));
      this.svg.addEventListener("pointermove", e => this.move(e));
      this.svg.addEventListener("pointerup", e => this.up(e));
      this.svg.addEventListener("pointercancel", e => this.up(e, true));
      this.svg.addEventListener("pointerleave", () => { this.cursor = null; this.updateHud(); });
      this.svg.addEventListener("wheel", e => this.wheel(e), { passive: false });
      this.svg.addEventListener("dblclick", e => { if (!e.target.closest("[data-id]")) this.fit(); });
    }
    this.ro = new ResizeObserver(() => this.render());
    this.ro.observe(box);
  }
  destroy() { this.ro.disconnect(); }
  set(patch) { Object.assign(this.d, patch); this.render(); }
  setOpt(patch) {
    if (patch.layers) patch = { ...patch, layers: { ...this.o.layers, ...patch.layers } };
    Object.assign(this.o, patch);
    this.box.classList.toggle("tool-rotate", this.o.tool === "rotate");
    this.box.classList.toggle("tool-measure", this.o.tool === "measure");
    this.box.classList.toggle("tool-zone", this.o.tool === "zone");
    this.box.classList.toggle("tool-outlet", this.o.tool === "outlet");
    this.box.classList.toggle("tool-pillar", this.o.tool === "pillar");
    if (this.o.tool !== "measure") this.measure = null;
    this.render();
  }
  fit() { this.zoom = 1; this.cx = this.cy = null; this.render(); }

  // ── 좌표 ──
  toUser(e) {
    const pt = this.svg.createSVGPoint();
    pt.x = e.clientX; pt.y = e.clientY;
    const m = this.svg.getScreenCTM();
    if (!m) return { x: 0, y: 0 };
    const r = pt.matrixTransform(m.inverse());
    return { x: r.x, y: r.y };
  }
  snapV(v) { const s0 = this.o.snap || 1; return Math.round(v / s0) * s0; }

  // ── 그리기 ──
  render() {
    const p = this.d.project;
    if (!p || !p.space) return;
    if (this.drag) { this.dirty = true; return; }
    const sp = p.space, W = sp.width, D = sp.depth;
    const cw = this.box.clientWidth || 800, ch = this.box.clientHeight || 500;
    let m = 2000;
    for (let i = 0; i < 5; i++) { const kk = Math.max((W + 2 * m) / cw, (D + 2 * m) / ch); m = T + (this.o.layers.dims ? 80 : 36) * kk; }
    const bw = W + 2 * m, bh = D + 2 * m;
    const vw = bw / this.zoom, vh = bh / this.zoom;
    const cx = this.cx ?? W / 2, cy = this.cy ?? D / 2;
    this.vb = [cx - vw / 2, cy - vh / 2, vw, vh];
    this.svg.setAttribute("viewBox", this.vb.map(v => v.toFixed(1)).join(" "));
    const k = Math.max(vw / cw, vh / ch);
    this.k = k;
    const px = v => v * k;
    this.px = px;
    const L = this.o.layers, mode = this.o.mode;
    const v = this.d.v || {};
    const geom = v.geom || { placements: {}, fixtures: {} };
    const U = this.uid;
    const ns = { "vector-effect": "non-scaling-stroke" };
    const T_ = (x, y, str, o = {}) => s("text", {
      x, y, "font-size": px(o.size || 11), "font-weight": o.weight || 500, fill: o.fill || C.text,
      "text-anchor": o.anchor || "middle", "dominant-baseline": o.base || "central",
      "paint-order": o.halo === false ? null : "stroke", stroke: o.halo === false ? null : (o.haloColor || "#fff"), "stroke-width": o.halo === false ? null : px(3),
      "stroke-linejoin": "round", class: o.cls || null, "pointer-events": o.pe || "none", ...o.attrs,
    }, str);
    const out = [];

    out.push(s("defs", {},
      s("pattern", { id: U + "hatch", width: px(7), height: px(7), patternUnits: "userSpaceOnUse", patternTransform: "rotate(45)" },
        s("rect", { width: px(7), height: px(7), fill: "rgba(18,20,23,.04)" }),
        s("line", { x1: 0, y1: 0, x2: 0, y2: px(7), stroke: "#121417", "stroke-width": px(1.3), opacity: 0.55 })),
      s("marker", { id: U + "arr", viewBox: "0 0 10 10", refX: 7, refY: 5, markerWidth: px(10), markerHeight: px(10), orient: "auto-start-reverse", markerUnits: "userSpaceOnUse" },
        s("path", { d: "M1,1 L9,5 L1,9 z", fill: C.pri })),
      s("clipPath", { id: U + "room" }, s("rect", { x: 0, y: 0, width: W, height: D }))));

    // 바닥 · 배경 이미지 · 그리드
    out.push(s("rect", { x: 0, y: 0, width: W, height: D, fill: "#fff" }));
    if (this.o.bg && this.o.bg.url) {
      out.push(s("image", { href: this.o.bg.url, x: 0, y: 0, width: W, height: D, preserveAspectRatio: "none", opacity: this.o.bg.opacity ?? 0.35 }));
    }
    if (L.grid) {
      const step = W > 40000 || D > 40000 ? 5000 : 1000;
      const g = [];
      for (let x = step; x < W; x += step) g.push(`M${x},0V${D}`);
      for (let y = step; y < D; y += step) g.push(`M0,${y}H${W}`);
      out.push(s("path", { d: g.join(""), stroke: C.grid, "stroke-width": 1, fill: "none", ...ns }));
    }

    // 존(바탕)
    const zones = p.zones || [];
    const showZones = (L.zones && mode !== "space" && mode !== "recog") || mode === "zones";
    if (showZones) {
      for (const z of zones) {
        const x0 = Math.min(z.x0, z.x1), y0 = Math.min(z.y0, z.y1), x1 = Math.max(z.x0, z.x1), y1 = Math.max(z.y0, z.y1);
        const isSel = mode === "zones" && this.d.zoneSel === z.id;
        const dim = mode === "zones" && this.d.zoneSel && !isSel;
        out.push(s("rect", {
          x: x0, y: y0, width: x1 - x0, height: y1 - y0, fill: isSel ? "rgba(20,40,160,.10)" : "rgba(20,40,160,.045)",
          stroke: C.pri, "stroke-width": isSel ? 2 : 1.2, "stroke-dasharray": isSel ? null : "5 4", ...ns, opacity: dim ? 0.55 : 1,
          "data-id": z.id, "data-kind": "zone", class: mode === "zones" ? "pl-item" : null, "pointer-events": mode === "zones" ? "all" : "none",
        }));
      }
    }

    // 시야각 부채꼴
    if (L.view && mode === "layout") {
      const selG = this.d.sel && geom.placements[this.d.sel];
      let cones = [];
      if (selG && selG.cone) cones = [[this.d.sel, selG, 1]];
      else if (!this.d.sel) {
        const main = Object.entries(geom.placements).filter(([, g]) => g.cone).sort((a, b) => b[1].fw - a[1].fw)[0];
        if (main) cones = [[main[0], main[1], 0.8]];
      }
      const cg = s("g", { "clip-path": `url(#${U}room)`, "pointer-events": "none" });
      for (const [, g, op] of cones) {
        cg.appendChild(s("polygon", { points: pts(g.cone), fill: C.priSoft, stroke: "rgba(20,40,160,.45)", "stroke-width": 1, "stroke-dasharray": "4 4", ...ns, opacity: op }));
      }
      out.push(cg);
      if (cones.length) {
        const cg0 = cones[0][1];
        const c0 = cg0.cone[0], c1 = cg0.cone[1];
        const lx = c0[0] + (c1[0] - c0[0]) * 0.18, ly = c0[1] + (c1[1] - c0[1]) * 0.18;
        out.push(T_(lx, ly, `시야각 ±${geom.view ? geom.view.max_angle_deg : 40}°`, { size: 10.5, fill: C.pri, weight: 600 }));
      }
    }

    // 동선
    if (L.flow && v.flow && v.flow.path && v.flow.path.length > 1 && (mode === "layout" || mode === "zones" || mode === "view")) {
      const path = v.flow.path;
      out.push(s("polyline", { points: pts(path), fill: "none", stroke: C.pri, "stroke-width": 2.2, "stroke-linejoin": "round", ...ns, "marker-end": `url(#${U}arr)`, opacity: 0.85, "pointer-events": "none" }));
      for (let i = 0; i < path.length - 1; i++) {
        const [ax, ay] = path[i], [bx, by] = path[i + 1];
        const len = Math.hypot(bx - ax, by - ay);
        if (len < px(80)) continue;
        const mx = (ax + bx) / 2, my = (ay + by) / 2, ang = Math.atan2(by - ay, bx - ax) * 180 / Math.PI;
        out.push(s("path", { d: `M${-px(4)},${-px(4)} L${px(3)},0 L${-px(4)},${px(4)}`, fill: "none", stroke: C.pri, "stroke-width": 1.8, ...ns, transform: `translate(${mx},${my}) rotate(${ang})`, "pointer-events": "none" }));
      }
      out.push(s("circle", { cx: path[0][0], cy: path[0][1], r: px(4), fill: C.pri, "pointer-events": "none" }));
    }

    // 전원 연결(맨해튼)
    const outlets = sp.outlets || [];
    const met = (v.metrics && v.metrics.placements) || {};
    const maxPow = 2000;
    if (mode === "layout") {
      for (const pl of p.placements || []) {
        const pw = met[pl.id] && met[pl.id].power;
        if (!pw) continue;
        if (!(L.power || this.d.sel === pl.id)) continue;
        const o = outlets.find(o => o.id === pw.outlet);
        if (!o) continue;
        out.push(s("path", { d: `M${pl.x},${pl.y}H${o.x}V${o.y}`, fill: "none", stroke: pw.mm > maxPow ? C.text : C.faint, "stroke-width": 1, "stroke-dasharray": "3 3", ...ns, "pointer-events": "none" }));
        if (pw.mm > maxPow || this.d.sel === pl.id) out.push(T_(o.x + (pl.x - o.x) * 0.5, pl.y + px(9), `${fmt(pw.mm / 1000, 1)} m`, { size: 10, fill: C.t2, weight: 700 }));
      }
    }

    // 집기
    const fixtures = p.fixtures || [];
    if (L.fixtures && mode !== "space" && mode !== "recog") {
      for (const f of fixtures) {
        const gf = geom.fixtures[f.id];
        const poly = gf ? gf.poly : rotRect(f.x, f.y, f.w, f.d, f.rot);
        const isSel = this.d.sel === f.id;
        const grp = s("g", { "data-id": f.id, "data-kind": "fixture", class: mode === "layout" ? "pl-item" : null });
        grp.appendChild(s("polygon", { points: pts(poly), fill: f.type === "rug" ? "rgba(138,145,160,.08)" : "#fff", stroke: C.fixture, "stroke-width": 1.1, "stroke-dasharray": "4 3", ...ns }));
        grp.appendChild(s("polygon", { points: pts(poly), fill: "none", stroke: "transparent", "stroke-width": 12, ...ns, "pointer-events": "all" }));
        if (L.labels) {
          const [bx0, by0, bx1, by1] = bboxOf(poly);
          const label = f.label || (gf && gf.type_label) || f.type;
          const wpx = (bx1 - bx0) / k;
          const fs = wpx > label.length * 11.5 ? 11 : wpx > label.length * 9 ? 9.5 : 0;
          if (fs) grp.appendChild(T_((bx0 + bx1) / 2, (by0 + by1) / 2, label, { size: fs, fill: C.t2, halo: false }));
          else if (isSel || mode === "zones") grp.appendChild(T_((bx0 + bx1) / 2, by1 + px(9), label, { size: 10, fill: C.t2 }));
        }
        out.push(grp);
      }
    }

    // 기둥
    for (const pi of sp.pillars || []) {
      const isSel = this.d.sel === pi.id;
      const g = s("g", { "data-id": pi.id, "data-kind": "pillar", class: mode === "space" ? "pl-item" : null });
      g.appendChild(s("rect", { x: pi.x - pi.w / 2, y: pi.y - pi.d / 2, width: pi.w, height: pi.d, fill: C.muted, stroke: isSel ? C.pri : "none", "stroke-width": 2, ...ns }));
      g.appendChild(s("rect", { x: pi.x - pi.w / 2, y: pi.y - pi.d / 2, width: pi.w, height: pi.d, fill: "none", stroke: "transparent", "stroke-width": 12, ...ns, "pointer-events": "all" }));
      if (mode === "space" || mode === "recog") g.appendChild(T_(pi.x, pi.y + pi.d / 2 + px(10), pi.label || pi.id, { size: 10.5, fill: C.t2 }));
      out.push(g);
    }

    // 삼성 제품
    const pls = p.placements || [];
    if (mode !== "space" && mode !== "recog") {
      for (const pl of pls) {
        const g0 = geom.placements[pl.id];
        if (!g0) continue;
        const grp = s("g", { "data-id": pl.id, "data-kind": "placement", class: mode === "layout" ? "pl-item" : null });
        if (g0.category === "hvac_cassette") {
          const [x0, y0, x1, y1] = bboxOf(g0.poly);
          grp.appendChild(s("polygon", { points: pts(g0.poly), fill: "rgba(20,40,160,.06)", stroke: C.pri, "stroke-width": 1.2, ...ns }));
          grp.appendChild(s("path", { d: `M${x0},${y0}L${x1},${y1}M${x1},${y0}L${x0},${y1}`, stroke: C.pri, "stroke-width": 0.8, ...ns, opacity: 0.6 }));
        } else {
          grp.appendChild(s("polygon", { points: pts(g0.poly), fill: C.pri, stroke: C.pri, "stroke-width": 1, ...ns, opacity: g0.mount === "ceiling_hang" ? 0.78 : 1 }));
          const fx = g0.front[0], fy = g0.front[1];
          const ax = pl.x + fx * g0.fd / 2, ay = pl.y + fy * g0.fd / 2;
          grp.appendChild(s("line", { x1: ax, y1: ay, x2: ax + fx * px(7), y2: ay + fy * px(7), stroke: C.pri, "stroke-width": 1.6, ...ns }));
        }
        grp.appendChild(s("polygon", { points: pts(g0.poly), fill: "none", stroke: "transparent", "stroke-width": 14, ...ns, "pointer-events": "all" }));
        out.push(grp);
      }
      if (L.labels) out.push(...this.productLabels(p, geom, T_));
    }

    // 벽 · 개구부
    out.push(s("path", { d: `M${-T},${-T}H${W + T}V${D + T}H${-T}Z M0,0V${D}H${W}V0Z`, fill: C.wall, "fill-rule": "evenodd", stroke: C.faint, "stroke-width": 1, ...ns, "pointer-events": "none" }));
    for (const o of sp.openings || []) out.push(...this.opening(sp, o, T_));

    // 콘센트
    for (const o of outlets) {
      const isSel = this.d.sel === o.id;
      const g = s("g", { "data-id": o.id, "data-kind": "outlet", class: mode === "space" ? "pl-item" : null });
      g.appendChild(s("circle", { cx: o.x, cy: o.y, r: px(isSel ? 6 : 4.6), fill: "#fff", stroke: isSel ? C.pri : C.text, "stroke-width": 1.4, ...ns }));
      g.appendChild(s("circle", { cx: o.x, cy: o.y, r: px(1.6), fill: isSel ? C.pri : C.text }));
      g.appendChild(s("circle", { cx: o.x, cy: o.y, r: px(9), fill: "transparent", "pointer-events": "all" }));
      if (mode === "layout" || mode === "space" || mode === "recog" || mode === "view") {
        const nw = nearestWall(sp, o.x, o.y);
        let lx = o.x, ly = o.y;
        const off = px(12);
        const pil = (o.on || "").startsWith("pillar:") ? (sp.pillars || []).find(q => q.id === o.on.split(":")[1]) : null;
        if (pil) { const dx = o.x - pil.x, dy = o.y - pil.y, dl = Math.hypot(dx, dy) || 1; lx += dx / dl * off; ly += dy / dl * off; }
        else if (nw.dist < 400) { const n = WALL[nw.wall].n; lx += n[0] * off; ly += n[1] * off; }
        else ly += off;
        g.appendChild(T_(lx, ly, o.label || o.id, { size: 9.5, fill: C.t2, weight: 700 }));
      }
      out.push(g);
    }

    // 치수
    if (L.dims) out.push(...this.dims(sp, T_));

    // 인식 확인 표시(BP1D)
    for (const f of this.d.flags || []) {
      out.push(s("circle", { cx: f.x, cy: f.y, r: px(11), fill: "#fff", stroke: C.text, "stroke-width": 1.6, ...ns }));
      out.push(T_(f.x, f.y, f.no || "?", { size: 11, weight: 800, halo: false }));
      if (f.text) out.push(T_(f.x + px(16), f.y, f.text, { size: 11, anchor: "start", weight: 700 }));
    }

    // 문제 구간 빗금 · 경고 번호
    const warns = (v.warnings || []).filter(w => !w.ignored);
    if (L.warnings && mode === "layout") {
      const active = warns.filter(w => w.level === "warn" || w.level === "error");
      const hatched = new Set(active.flatMap(w => w.targets || []));
      for (const id of hatched) {
        const g0 = geom.placements[id] || geom.fixtures[id];
        if (g0) out.push(s("polygon", { points: pts(g0.poly), fill: `url(#${U}hatch)`, stroke: "none", "pointer-events": "none" }));
      }
      for (const w of warns) {
        const [x, y] = w.at;
        const foc = this.d.focus === w.id;
        if (w.level === "memo") {
          const g = s("g", { "data-wid": w.id, style: "cursor:pointer" });
          g.appendChild(s("rect", { x: x + px(8), y: y - px(19), width: px(30), height: px(15), rx: px(4), fill: foc ? C.pri : "#eef0f4", stroke: C.t2, "stroke-width": 0.8, ...ns }));
          g.appendChild(T_(x + px(23), y - px(11.5), "메모", { size: 9, weight: 700, fill: foc ? "#fff" : C.t2, halo: false }));
          out.push(g);
          continue;
        }
        const r = px(foc ? 12 : 10);
        const g = s("g", { "data-wid": w.id, style: "cursor:pointer" });
        const bx = x + px(13), by = y - px(13);
        g.appendChild(s("line", { x1: x, y1: y, x2: bx, y2: by, stroke: C.text, "stroke-width": 1, ...ns }));
        g.appendChild(s("circle", { cx: x, cy: y, r: px(2.2), fill: C.text }));
        const x_ = bx, y_ = by;
        if (foc) g.appendChild(s("circle", { cx: x_, cy: y_, r: px(18), fill: "none", stroke: C.pri, "stroke-width": 2, ...ns }));
        g.appendChild(s("circle", { cx: x_, cy: y_, r, fill: w.level === "info" ? "#fff" : (w.level === "error" ? "#b3261e" : C.text), stroke: C.text, "stroke-width": 1.5, ...ns }));
        g.appendChild(T_(x_, y_ + px(0.5), String(w.no), { size: foc ? 12 : 10.5, weight: 800, fill: w.level === "info" ? C.text : "#fff", halo: false }));
        out.push(g);
      }
    }

    // 존 번호 · 이름
    if (showZones) {
      for (const z of zones) {
        const x0 = Math.min(z.x0, z.x1), y0 = Math.min(z.y0, z.y1), x1 = Math.max(z.x0, z.x1), y1 = Math.max(z.y0, z.y1);
        const bx = x0 + px(15), by = (y0 < 700 && y1 - y0 > px(40)) ? y1 - px(15) : y0 + px(15);
        out.push(s("circle", { cx: bx, cy: by, r: px(10), fill: C.pri, "pointer-events": "none" }));
        out.push(T_(bx, by + px(0.5), String(z.no), { size: 11, weight: 800, fill: "#fff", halo: false }));
        if (mode === "zones" || L.labels) out.push(T_(bx + px(15), by, z.name || "", { size: 11.5, weight: 700, anchor: "start", fill: C.pri }));
        if (mode === "zones" && this.d.zoneSel === z.id) {
          out.push(T_((x0 + x1) / 2, y1 - px(12), `${fmt(x1 - x0)} × ${fmt(y1 - y0)} · ${fmt((x1 - x0) * (y1 - y0) / 1e6, 1)} ㎡`, { size: 10.5, weight: 700, fill: C.pri }));
          for (const [hx, hy, hn] of [[x0, y0, "nw"], [x1, y0, "ne"], [x0, y1, "sw"], [x1, y1, "se"]]) {
            out.push(s("rect", { x: hx - px(5), y: hy - px(5), width: px(10), height: px(10), fill: "#fff", stroke: C.pri, "stroke-width": 1.6, ...ns, "data-id": z.id, "data-kind": "zone", "data-handle": hn, style: `cursor:${hn === "nw" || hn === "se" ? "nwse" : "nesw"}-resize` }));
          }
        }
      }
    }

    // 선택 표시
    const selId = this.d.sel;
    if (selId) {
      const g0 = geom.placements[selId] || geom.fixtures[selId];
      let poly = g0 && g0.poly;
      if (!poly) { const f = fixtures.find(f => f.id === selId); if (f) poly = rotRect(f.x, f.y, f.w, f.d, f.rot); }
      if (poly) {
        const [x0, y0, x1, y1] = bboxOf(poly);
        const pad = px(5);
        out.push(s("rect", { x: x0 - pad, y: y0 - pad, width: x1 - x0 + 2 * pad, height: y1 - y0 + 2 * pad, fill: "none", stroke: C.pri, "stroke-width": 1.6, "stroke-dasharray": "5 3", ...ns, rx: px(3), "pointer-events": "none" }));
      }
    }

    // 치수 재기
    if (this.measure) {
      const a = this.measure.a, b = this.measure.b || this.measure.hover;
      if (a && b) {
        const d = Math.hypot(b[0] - a[0], b[1] - a[1]);
        out.push(s("line", { x1: a[0], y1: a[1], x2: b[0], y2: b[1], stroke: C.pri, "stroke-width": 1.8, ...ns, "pointer-events": "none" }));
        for (const q of [a, b]) out.push(s("circle", { cx: q[0], cy: q[1], r: px(3.5), fill: C.pri, "pointer-events": "none" }));
        out.push(T_((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 - px(11), `${fmt(d)} mm`, { size: 12, weight: 800, fill: C.pri }));
      } else if (a) out.push(s("circle", { cx: a[0], cy: a[1], r: px(3.5), fill: C.pri }));
    }
    if (this.d.extra) out.push(...this.d.extra(this, T_));

    while (this.svg.firstChild) this.svg.removeChild(this.svg.firstChild);
    for (const el of out) this.svg.appendChild(el);
    this.updateHud();
  }

  productLabels(p, geom, T_) {
    const sp = p.space, px = this.px;
    const groups = new Map();
    for (const pl of p.placements || []) {
      const g0 = geom.placements[pl.id];
      if (!g0) continue;
      const a = pl.anchor || "";
      let key = pl.line + "|" + pl.id;
      if (a.startsWith("window:") || a.startsWith("wall:")) key = pl.line + "|" + a;
      else if (a.startsWith("pillar:")) key = pl.line + "|" + a.split(":").slice(0, 2).join(":");
      else if (g0.category === "hvac_cassette") key = pl.line + "|hvac";
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push([pl, g0]);
    }
    const out = [];
    for (const [key, items] of groups) {
      const [pl0, g0] = items[0];
      const a = pl0.anchor || "";
      const name = items.length > 1 ? `${g0.short} ×${items.length}` : g0.short;
      if (g0.category === "hvac_cassette") {
        for (const [pl] of items) out.push(T_(pl.x, pl.y + px(14), g0.short, { size: 9.5, fill: C.pri, weight: 600 }));
        continue;
      }
      const sel = items.some(([pl]) => pl.id === this.d.sel);
      if (a.startsWith("pillar:")) {
        const pid = a.split(":")[1];
        const pi = (sp.pillars || []).find(x => x.id === pid);
        out.push(T_(pi ? pi.x : pl0.x, (pi ? pi.y + pi.d / 2 : pl0.y) + px(16), name, { size: 10.5, fill: C.pri, weight: 700 }));
        continue;
      }
      const xs = items.map(([pl]) => pl.x), ys = items.map(([pl]) => pl.y);
      const cx = (Math.min(...xs) + Math.max(...xs)) / 2, cy = (Math.min(...ys) + Math.max(...ys)) / 2;
      const inward = a.startsWith("window:") ? [-g0.front[0], -g0.front[1]] : g0.front;
      const off = g0.fd / 2 + px(13);
      let lx = cx + inward[0] * off, ly = cy + inward[1] * off;
      if (items.length > 1 && Math.abs(inward[1]) > 0.5) {
        for (const [pl] of items) out.push(T_(pl.x, pl.y + inward[1] * off, g0.short, { size: 10, fill: C.pri, weight: 700 }));
        continue;
      }
      out.push(T_(lx, ly, name + (sel ? "" : ""), { size: 11, fill: C.pri, weight: 700, anchor: Math.abs(inward[0]) > 0.5 ? (inward[0] > 0 ? "start" : "end") : "middle" }));
    }
    return out;
  }

  opening(sp, o, T_) {
    const px = this.px, W = sp.width, D = sp.depth, out = [];
    const a = o.start, b = o.start + o.length;
    let r;
    if (o.wall === "front") r = [a, -T, b, 0];
    else if (o.wall === "back") r = [a, D, b, D + T];
    else if (o.wall === "left") r = [-T, a, 0, b];
    else r = [W, a, W + T, b];
    const [x0, y0, x1, y1] = r;
    const horiz = o.wall === "front" || o.wall === "back";
    const ns = { "vector-effect": "non-scaling-stroke" };
    const isSel = this.d.sel === o.id;
    const g = s("g", { "data-id": o.id, "data-kind": "opening" });
    g.appendChild(s("rect", { x: x0, y: y0, width: x1 - x0, height: y1 - y0, fill: "#fff", stroke: isSel ? C.pri : "none", "stroke-width": 2, ...ns }));
    const n = WALL[o.wall].n;
    const mid = wallPoint(sp, o.wall, (a + b) / 2);
    const outside = [mid[0] - n[0] * (T + px(11)), mid[1] - n[1] * (T + px(11))];
    if (o.kind === "window") {
      for (const f of [0.35, 0.65]) {
        if (horiz) { const yy = y0 + (y1 - y0) * f; g.appendChild(s("line", { x1: x0, y1: yy, x2: x1, y2: yy, stroke: C.pri, "stroke-width": 1.3, ...ns })); }
        else { const xx = x0 + (x1 - x0) * f; g.appendChild(s("line", { x1: xx, y1: y0, x2: xx, y2: y1, stroke: C.pri, "stroke-width": 1.3, ...ns })); }
      }
      g.appendChild(s("rect", { x: x0, y: y0, width: x1 - x0, height: y1 - y0, fill: "none", stroke: C.pri, "stroke-width": 1, ...ns }));
    } else if (o.kind === "entrance") {
      const ai = [mid[0] - n[0] * T * 0.6, mid[1] - n[1] * T * 0.6];
      const bi = [mid[0] + n[0] * px(26), mid[1] + n[1] * px(26)];
      g.appendChild(s("line", { x1: ai[0], y1: ai[1], x2: bi[0], y2: bi[1], stroke: C.text, "stroke-width": 1.6, ...ns, "marker-end": `url(#${this.uid}arr)` }));
    } else {
      const H = wallPoint(sp, o.wall, a), A = WALL[o.wall].a;
      const P1 = [H[0] + A[0] * o.length, H[1] + A[1] * o.length], P2 = [H[0] + n[0] * o.length, H[1] + n[1] * o.length];
      const sweep = (A[0] * n[1] - A[1] * n[0]) > 0 ? 1 : 0;
      if (o.door_type !== "wall") {
        g.appendChild(s("path", { d: `M${P1[0]},${P1[1]} A${o.length},${o.length} 0 0 ${sweep} ${P2[0]},${P2[1]}`, fill: "none", stroke: C.faint, "stroke-width": 1, "stroke-dasharray": "3 3", ...ns }));
        g.appendChild(s("line", { x1: H[0], y1: H[1], x2: P2[0], y2: P2[1], stroke: C.t2, "stroke-width": 1.4, ...ns }));
      } else {
        g.appendChild(s("rect", { x: x0, y: y0, width: x1 - x0, height: y1 - y0, fill: C.wall, stroke: C.faint, "stroke-width": 1, "stroke-dasharray": "2 2", ...ns }));
      }
    }
    const label = (o.label || o.id) + (o.kind === "door" && o.length ? ` ${fmt(o.length)}` : "");
    const anchor = horiz ? "middle" : (o.wall === "left" ? "end" : "start");
    if (this.o.layers.labels !== false) g.appendChild(T_(outside[0], outside[1], label, { size: 10.5, fill: o.kind === "window" ? C.pri : C.text, weight: 600, anchor, halo: true, haloColor: "#fbfbfc" }));
    return [g];
  }

  dims(sp, T_) {
    const px = this.px, W = sp.width, D = sp.depth, out = [];
    const ns = { "vector-effect": "non-scaling-stroke" };
    const chain = (vals, horiz, off) => {
      const g = s("g", { "pointer-events": "none" });
      const pos = v => horiz ? [v, off] : [off, v];
      const [a0, a1] = [pos(vals[0]), pos(vals[vals.length - 1])];
      g.appendChild(s("line", { x1: a0[0], y1: a0[1], x2: a1[0], y2: a1[1], stroke: C.muted, "stroke-width": 1, ...ns }));
      for (const v of vals) {
        const [x, y] = pos(v);
        const tick = horiz ? { x1: x, y1: y - px(4), x2: x, y2: y + px(4) } : { x1: x - px(4), y1: y, x2: x + px(4), y2: y };
        g.appendChild(s("line", { ...tick, stroke: C.muted, "stroke-width": 1, ...ns }));
      }
      for (let i = 0; i < vals.length - 1; i++) {
        const len = vals[i + 1] - vals[i];
        if (len / this.k < 26) continue;
        const m = (vals[i] + vals[i + 1]) / 2;
        const [x, y] = pos(m);
        const t = T_(horiz ? x : x - px(1), horiz ? y - px(7) : y, fmt(len), { size: 10, fill: C.t2, weight: 700, haloColor: "#fbfbfc", attrs: horiz ? {} : { transform: `rotate(-90 ${x - px(7)} ${y})`, x: x - px(7) } });
        g.appendChild(t);
      }
      return g;
    };
    const front = (sp.openings || []).filter(o => o.wall === "front").flatMap(o => [o.start, o.start + o.length]);
    const fv = [...new Set([0, ...front.map(v => Math.round(v)), W])].sort((a, b) => a - b);
    const o1 = -T - px(32), o2 = -T - px(56);
    if (fv.length > 2) out.push(chain(fv, true, o1));
    out.push(chain([0, W], true, fv.length > 2 ? o2 : o1));
    const pys = [...new Set((sp.pillars || []).map(p => Math.round(p.y)))];
    const lv = [...new Set([0, ...pys, D])].sort((a, b) => a - b);
    if (lv.length > 2) out.push(chain(lv, false, o1));
    out.push(chain([0, D], false, lv.length > 2 ? o2 : o1));
    return out;
  }

  updateHud() {
    if (!this.o.hud) return;
    const parts = [];
    if (this.drag && this.drag.live) parts.push(this.drag.live);
    else if (this.cursor) parts.push(`X ${fmt(this.cursor.x)} · Y ${fmt(this.cursor.y)}`);
    parts.push(`1칸 ${(this.d.project && Math.max(this.d.project.space.width, this.d.project.space.depth) > 40000) ? "5" : "1"} m`);
    if (this.o.snap) parts.push(`스냅 ${fmt(this.o.snap)} mm`);
    if (this.zoom !== 1) parts.push(`${Math.round(this.zoom * 100)}%`);
    this.hud.textContent = parts.join(" · ");
  }

  // ── 조작 ──
  canDrag(kind) {
    if (!this.o.editable) return false;
    const m = this.o.mode;
    return (m === "layout" && (kind === "placement" || kind === "fixture")) || (m === "space" && (kind === "pillar" || kind === "outlet")) || (m === "zones" && kind === "zone");
  }
  findItem(kind, id) {
    const p = this.d.project;
    if (kind === "placement") return (p.placements || []).find(x => x.id === id);
    if (kind === "fixture") return (p.fixtures || []).find(x => x.id === id);
    if (kind === "pillar") return (p.space.pillars || []).find(x => x.id === id);
    if (kind === "outlet") return (p.space.outlets || []).find(x => x.id === id);
    if (kind === "zone") return (p.zones || []).find(x => x.id === id);
    return null;
  }
  select(id, kind) {
    if (this.o.mode === "zones") { this.d.zoneSel = kind === "zone" ? id : null; }
    else this.d.sel = id;
    this.render();
    if (this.o.onSelect) this.o.onSelect(id, kind);
  }

  down(e) {
    if (e.button === 2) return;
    const pt = this.toUser(e);
    const tool = this.o.tool;
    const wEl = e.target.closest("[data-wid]");
    if (wEl && tool === "select") { if (this.o.onWarning) this.o.onWarning(wEl.dataset.wid); return; }
    const el = e.target.closest("[data-id]");
    const snapPt = () => [this.snapV(pt.x), this.snapV(pt.y)];
    if (e.button === 1) { this.startPan(e, pt); return; }
    if (tool === "measure") {
      if (!this.measure || this.measure.b) this.measure = { a: snapPt(), b: null };
      else { this.measure.b = snapPt(); if (this.o.onMeasure) this.o.onMeasure(this.measure); }
      this.render();
      return;
    }
    if (tool === "outlet" && this.o.onCommit) {
      const sp = this.d.project.space;
      if (pt.x < -T || pt.y < -T || pt.x > sp.width + T || pt.y > sp.depth + T) return;
      this.o.onCommit({ type: "outlet-add", ...this.snapToSurface(pt.x, pt.y) });
      return;
    }
    if (tool === "pillar" && this.o.onCommit) {
      const sp = this.d.project.space;
      if (pt.x <= 0 || pt.y <= 0 || pt.x >= sp.width || pt.y >= sp.depth) return;
      this.o.onCommit({ type: "pillar-add", x: this.snapV(pt.x), y: this.snapV(pt.y) });
      return;
    }
    if (tool === "zone" && !(el && el.dataset.handle) && this.o.editable) {
      const [x, y] = snapPt();
      this.drag = { kind: "zone-new", start: [x, y], cur: [x, y], ghost: null, moved: false };
      this.svg.setPointerCapture(e.pointerId);
      return;
    }
    if (el) {
      const kind = el.dataset.kind, id = el.dataset.id;
      if (kind === "opening") { this.select(id, kind); return; }
      if (tool === "rotate" && (kind === "placement" || kind === "fixture") && this.o.editable && this.o.mode === "layout") {
        this.select(id, kind);
        this.o.onCommit && this.o.onCommit({ type: "rotate", kind, id, delta: e.shiftKey ? -90 : 90 });
        return;
      }
      const isSel = this.o.mode === "zones" ? this.d.zoneSel === id : this.d.sel === id;
      if (!isSel) this.select(id, kind);
      if (this.canDrag(kind)) {
        const it = this.findItem(kind, id);
        if (!it) return;
        const groups = [...this.svg.querySelectorAll(`[data-id="${CSS.escape(id)}"]`)];
        this.drag = { kind, id, handle: el.dataset.handle || null, start: [pt.x, pt.y], orig: { ...it }, els: groups, moved: false, dx: 0, dy: 0 };
        this.svg.setPointerCapture(e.pointerId);
      }
      return;
    }
    this.select(null, null);
    this.startPan(e, pt);
  }
  startPan(e, pt) {
    if (this.zoom <= 1.001 && e.button !== 1) return;
    this.pan = { sx: e.clientX, sy: e.clientY, cx: this.cx ?? this.d.project.space.width / 2, cy: this.cy ?? this.d.project.space.depth / 2 };
    this.svg.setPointerCapture(e.pointerId);
  }
  move(e) {
    const pt = this.toUser(e);
    this.cursor = pt;
    if (this.pan) {
      this.cx = this.pan.cx - (e.clientX - this.pan.sx) * this.k;
      this.cy = this.pan.cy - (e.clientY - this.pan.sy) * this.k;
      const vw = this.vb[2], vh = this.vb[3];
      this.vb = [this.cx - vw / 2, this.cy - vh / 2, vw, vh];
      this.svg.setAttribute("viewBox", this.vb.map(v => v.toFixed(1)).join(" "));
      return;
    }
    if (this.measure && !this.measure.b) { this.measure.hover = [this.snapV(pt.x), this.snapV(pt.y)]; this.render(); return; }
    const d = this.drag;
    if (!d) { this.updateHud(); return; }
    if (d.kind === "zone-new") {
      d.cur = [this.snapV(pt.x), this.snapV(pt.y)];
      d.moved = true;
      if (d.ghost) d.ghost.remove();
      const [x0, y0] = d.start, [x1, y1] = d.cur;
      d.ghost = s("rect", { x: Math.min(x0, x1), y: Math.min(y0, y1), width: Math.abs(x1 - x0), height: Math.abs(y1 - y0), fill: "rgba(20,40,160,.08)", stroke: C.pri, "stroke-width": 1.6, "stroke-dasharray": "5 4", "vector-effect": "non-scaling-stroke" });
      this.svg.appendChild(d.ghost);
      d.live = `${fmt(Math.abs(x1 - x0))} × ${fmt(Math.abs(y1 - y0))}`;
      this.updateHud();
      return;
    }
    let dx = this.snapV(pt.x - d.start[0]), dy = this.snapV(pt.y - d.start[1]);
    if (d.kind === "placement" && !e.altKey) {
      const wall = openingWallOfAnchor(this.d.project.space, d.orig.anchor);
      if (wall === "front" || wall === "back") dy = 0;
      else if (wall === "left" || wall === "right") dx = 0;
    }
    if (d.kind === "zone" && d.handle) {
      const z = d.orig, r = { x0: Math.min(z.x0, z.x1), y0: Math.min(z.y0, z.y1), x1: Math.max(z.x0, z.x1), y1: Math.max(z.y0, z.y1) };
      if (d.handle.includes("w")) r.x0 += dx; if (d.handle.includes("e")) r.x1 += dx;
      if (d.handle.includes("n")) r.y0 += dy; if (d.handle.includes("s")) r.y1 += dy;
      d.rect = r;
      if (d.ghost) d.ghost.remove();
      d.ghost = s("rect", { x: Math.min(r.x0, r.x1), y: Math.min(r.y0, r.y1), width: Math.abs(r.x1 - r.x0), height: Math.abs(r.y1 - r.y0), fill: "rgba(20,40,160,.1)", stroke: C.pri, "stroke-width": 2, "vector-effect": "non-scaling-stroke", "pointer-events": "none" });
      this.svg.appendChild(d.ghost);
      d.moved = dx !== 0 || dy !== 0;
      d.live = `${fmt(Math.abs(r.x1 - r.x0))} × ${fmt(Math.abs(r.y1 - r.y0))}`;
      this.updateHud();
      return;
    }
    d.dx = dx; d.dy = dy;
    d.moved = d.moved || dx !== 0 || dy !== 0;
    for (const g of d.els) g.setAttribute("transform", `translate(${dx},${dy})`);
    const nx = d.kind === "zone" ? null : d.orig.x + dx, ny = d.kind === "zone" ? null : d.orig.y + dy;
    d.live = d.kind === "zone" ? `이동 ${fmt(dx)}, ${fmt(dy)}` : `X ${fmt(nx)} · Y ${fmt(ny)}`;
    this.updateHud();
    if (this.o.onDrag && d.kind !== "zone") this.o.onDrag({ kind: d.kind, id: d.id, x: nx, y: ny });
  }
  up(e, cancel = false) {
    if (this.pan) { this.pan = null; this.render(); return; }
    const d = this.drag;
    if (!d) return;
    this.drag = null;
    try { this.svg.releasePointerCapture(e.pointerId); } catch (_) { /* 이미 해제 */ }
    if (d.ghost) d.ghost.remove();
    if (cancel || !d.moved) { if (d.els) for (const g of d.els) g.removeAttribute("transform"); this.render(); return; }
    const C_ = this.o.onCommit;
    if (d.kind === "zone-new") {
      const [x0, y0] = d.start, [x1, y1] = d.cur;
      if (Math.abs(x1 - x0) >= 500 && Math.abs(y1 - y0) >= 500 && C_) C_({ type: "zone-new", x0: Math.min(x0, x1), y0: Math.min(y0, y1), x1: Math.max(x0, x1), y1: Math.max(y0, y1) });
      else this.render();
      return;
    }
    if (d.kind === "zone") {
      const z = d.orig;
      const r = d.rect || { x0: z.x0 + d.dx, y0: z.y0 + d.dy, x1: z.x1 + d.dx, y1: z.y1 + d.dy };
      if (C_) C_({ type: "zone", id: d.id, x0: Math.min(r.x0, r.x1), y0: Math.min(r.y0, r.y1), x1: Math.max(r.x0, r.x1), y1: Math.max(r.y0, r.y1) });
      return;
    }
    if (C_) C_({ type: "move", kind: d.kind, id: d.id, dx: d.dx, dy: d.dy });
    else this.render();
  }
  wheel(e) {
    e.preventDefault();
    const pt = this.toUser(e);
    const f = Math.exp(-e.deltaY * 0.0015);
    const z = Math.min(8, Math.max(1, this.zoom * f));
    if (z === this.zoom) return;
    const sp = this.d.project.space;
    const cx = this.cx ?? sp.width / 2, cy = this.cy ?? sp.depth / 2;
    const r = this.zoom / z;
    this.cx = pt.x + (cx - pt.x) * r;
    this.cy = pt.y + (cy - pt.y) * r;
    this.zoom = z;
    if (z === 1) this.cx = this.cy = null;
    this.render();
  }
  snapToSurface(x, y) {
    const sp = this.d.project.space;
    for (const pi of sp.pillars || []) {
      const dx = x - pi.x, dy = y - pi.y;
      if (Math.abs(dx) <= pi.w / 2 + 250 && Math.abs(dy) <= pi.d / 2 + 250) {
        if (Math.abs(dx) / pi.w > Math.abs(dy) / pi.d) return { x: pi.x + Math.sign(dx || 1) * pi.w / 2, y: this.snapV(y), on: `pillar:${pi.id}` };
        return { x: this.snapV(x), y: pi.y + Math.sign(dy || 1) * pi.d / 2, on: `pillar:${pi.id}` };
      }
    }
    const nw = nearestWall(sp, x, y);
    const cl = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
    if (nw.wall === "front") return { x: cl(this.snapV(x), 0, sp.width), y: 0, on: "wall:front" };
    if (nw.wall === "back") return { x: cl(this.snapV(x), 0, sp.width), y: sp.depth, on: "wall:back" };
    if (nw.wall === "left") return { x: 0, y: cl(this.snapV(y), 0, sp.depth), on: "wall:left" };
    return { x: sp.width, y: cl(this.snapV(y), 0, sp.depth), on: "wall:right" };
  }
}

// 작업 목록용 작은 평면(서버 summary.mini 사용)
export function miniPlan(mini, w = 168, hgt = 110) {
  if (!mini) return null;
  const W = mini.w, D = mini.d, m = Math.max(W, D) * 0.05;
  const k = Math.max((W + 2 * m) / w, (D + 2 * m) / hgt);
  const svg = s("svg", { viewBox: `${-m} ${-m} ${W + 2 * m} ${D + 2 * m}`, width: "100%", height: "100%", preserveAspectRatio: "xMidYMid meet" });
  svg.appendChild(s("rect", { x: 0, y: 0, width: W, height: D, fill: "#fff", stroke: "#8a91a0", "stroke-width": 2 * k }));
  for (const [wall, a, len, kind] of mini.openings || []) {
    const t = 3.2 * k;
    let r = wall === "front" ? [a, -t / 2, len, t] : wall === "back" ? [a, D - t / 2, len, t] : wall === "left" ? [-t / 2, a, t, len] : [W - t / 2, a, t, len];
    svg.appendChild(s("rect", { x: r[0], y: r[1], width: r[2], height: r[3], fill: kind === "window" ? "#1428a0" : "#fff" }));
  }
  for (const [x, y, pw, pd] of mini.pillars || []) svg.appendChild(s("rect", { x: x - pw / 2, y: y - pd / 2, width: pw, height: pd, fill: "#596170" }));
  for (const [poly, kind] of mini.items || []) {
    svg.appendChild(s("polygon", { points: poly.map(p => p.join(",")).join(" "), fill: kind === "p" ? "#1428a0" : "none", stroke: kind === "p" ? "#1428a0" : "#8a91a0", "stroke-width": (kind === "p" ? 1.2 : 1) * k, "stroke-dasharray": kind === "p" ? null : `${3 * k} ${2 * k}` }));
  }
  return svg;
}
