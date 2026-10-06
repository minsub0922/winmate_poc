/**
 * 템플릿 썸네일(§5.12 Thumb) — 120×68 레이아웃 그림. 입력: kind(레이아웃 종류) · n(항목 수 1–5).
 * 원본 보드 파일이 없어(G-UI-1) 셸이 그린 도식이다. export 카탈로그 썸네일이 있으면 그것을 먼저 쓴다:
 *   <Thumb code="MS-A" kind="kpi4" n={4} />   → /api/export/v1/templates/MS-A/thumbnail.png, 못 받으면 kind 도식
 *   <Thumb kind="barline" n={3} dim />         → 고를 수 없는 후보(opacity .45)
 * 모르는 kind 는 `table` 그림(보드 tplOf 기본값).
 */
import { useEffect, useState, type ReactNode } from 'react';
import { cx } from './controls';

const C = {
  brand: '#1428a0', soft: '#eaeefb', mid: '#b8c3ee', line: '#d5d9e0', gray: '#f0f2f5', ink: '#c5cbd6', dark: '#596170', white: '#ffffff', ok: '#9fd3bf',
};

type El = ReactNode;
let keySeq = 0;
const k = () => `t${keySeq++}`;
const R = (x: number, y: number, w: number, h: number, fill: string, r = 1.5, stroke?: string) =>
  <rect key={k()} x={x} y={y} width={Math.max(0, w)} height={Math.max(0, h)} rx={r} fill={fill} stroke={stroke} strokeWidth={stroke ? 0.8 : undefined} />;
const Ci = (cx: number, cy: number, r: number, fill: string, stroke?: string) =>
  <circle key={k()} cx={cx} cy={cy} r={r} fill={fill} stroke={stroke} strokeWidth={stroke ? 1 : undefined} />;
const L = (x1: number, y1: number, x2: number, y2: number, stroke = C.line, w = 1.2) =>
  <line key={k()} x1={x1} y1={y1} x2={x2} y2={y2} stroke={stroke} strokeWidth={w} strokeLinecap="round" />;
const P = (d: string, fill = 'none', stroke = C.brand, w = 1.4) =>
  <path key={k()} d={d} fill={fill} stroke={stroke} strokeWidth={w} strokeLinecap="round" strokeLinejoin="round" />;
/** 글 줄들 */
const lines = (x: number, y: number, w: number, count: number, gap = 4.5, last = 0.6) =>
  Array.from({ length: count }, (_, i) => R(x, y + i * gap, i === count - 1 ? w * last : w, 2, C.ink, 1));
/** 사진 자리(산 모양) */
const photo = (x: number, y: number, w: number, h: number, fill = C.gray) => [
  R(x, y, w, h, fill, 2),
  P(`M${x + 2} ${y + h - 2} L${x + w * 0.38} ${y + h * 0.45} L${x + w * 0.58} ${y + h * 0.7} L${x + w * 0.72} ${y + h * 0.55} L${x + w - 2} ${y + h - 2}`, 'none', C.mid, 1.2),
  Ci(x + w * 0.75, y + h * 0.3, Math.min(w, h) * 0.08, C.mid),
];
/** n 칸으로 나눈 x 위치 */
const cols = (n: number, x = 6, w = 108, gap = 4) => {
  const cw = (w - gap * (n - 1)) / n;
  return Array.from({ length: n }, (_, i) => ({ x: x + i * (cw + gap), w: cw }));
};
const title = (w = 46) => [R(6, 5, w, 4, C.dark, 1.2), R(6, 11.5, w * 0.6, 2, C.ink, 1)];

function draw(kind: string, nIn: number): El[] {
  const n = Math.max(1, Math.min(5, Math.round(nIn || 3)));
  keySeq = 0;
  const top = 17;
  const H = 46;
  switch (kind) {
    case 'kpi4': case 'bignum': case 'image2kpi': case 'roi': {
      const m = kind === 'bignum' ? 1 : kind === 'kpi4' ? Math.max(n, 2) : n;
      if (kind === 'image2kpi') {
        return [...title(), ...photo(6, top, 52, H), ...cols(2, 6, 108, 4).slice(0, 1).flatMap(() => []),
          ...Array.from({ length: Math.min(m, 3) }, (_, i) => [R(62, top + i * 16, 52, 13, C.soft, 2), R(65, top + 3 + i * 16, 18, 5, C.brand, 1), R(86, top + 5 + i * 16, 24, 2, C.ink, 1)]).flat()];
      }
      if (kind === 'roi') {
        return [...title(), R(6, top, 50, H, C.soft, 2), R(11, top + 8, 30, 10, C.brand, 1.5), ...lines(11, top + 24, 38, 3),
          ...cols(3, 62, 52, 3).map((c, i) => R(c.x, top + H - 10 - i * 11, c.w, 10 + i * 11, i === 2 ? C.brand : C.mid, 1))];
      }
      return [...title(), ...cols(m).flatMap((c) => [R(c.x, top, c.w, H, C.soft, 2), R(c.x + 4, top + 8, Math.min(c.w - 8, 26), kind === 'bignum' ? 14 : 8, C.brand, 1.5),
        ...lines(c.x + 4, top + (kind === 'bignum' ? 28 : 22), c.w - 8, kind === 'bignum' ? 3 : 2)])];
    }
    case 'barline': case 'hbars': case 'stack': {
      if (kind === 'hbars') {
        return [...title(), ...Array.from({ length: n }, (_, i) => {
          const y = top + 2 + i * (H / n);
          return [R(6, y, 22, 2.5, C.ink, 1), R(32, y - 1, 30 + ((i * 37) % 50), Math.min(6, H / n - 3), i === 0 ? C.brand : C.mid, 1)];
        }).flat()];
      }
      const bars = cols(Math.max(n, 3) + 2, 10, 100, 5);
      const out: El[] = [...title(), L(8, top + H, 112, top + H, C.line, 1)];
      bars.forEach((b, i) => {
        const h = 12 + ((i * 7) % 30);
        if (kind === 'stack') { out.push(R(b.x, top + H - h, b.w, h * 0.5, C.brand, 0.8), R(b.x, top + H - h * 1.0 + 0, b.w, h * 0.5, C.mid, 0.8)); }
        else out.push(R(b.x, top + H - h, b.w, h, C.mid, 0.8));
      });
      if (kind === 'barline') out.push(P(`M${bars.map((b, i) => `${b.x + b.w / 2} ${top + H - 18 - ((i * 7) % 30)}`).join(' L')}`, 'none', C.brand, 1.5));
      return out;
    }
    case 'circles': case 'bubble': case 'donut': case 'quadCircle': case 'radar': case 'scatter': {
      if (kind === 'donut') {
        return [...title(), Ci(32, top + 23, 19, 'none', C.mid), <circle key={k()} cx={32} cy={top + 23} r={19} fill="none" stroke={C.brand} strokeWidth={7}
          strokeDasharray="60 120" transform={`rotate(-90 32 ${top + 23})`} />, Ci(32, top + 23, 15, C.white), ...lines(62, top + 6, 48, Math.max(n, 3), 8)];
      }
      if (kind === 'radar') {
        const cx0 = 60; const cy0 = top + 23;
        const pts = (r: number) => Array.from({ length: 5 }, (_, i) => { const a = -Math.PI / 2 + (i * 2 * Math.PI) / 5; return `${cx0 + r * Math.cos(a)} ${cy0 + r * Math.sin(a)}`; }).join(' L');
        return [...title(), P(`M${pts(21)} Z`, 'none', C.line, 1), P(`M${pts(12)} Z`, 'none', C.line, 1), P(`M${pts(17).split(' L').map((p, i) => (i % 2 ? p : p)).join(' L')} Z`, 'rgba(20,40,160,0.18)', C.brand, 1.2)];
      }
      if (kind === 'scatter') {
        return [...title(), L(10, top + H, 112, top + H), L(10, top, 10, top + H), ...Array.from({ length: 9 }, (_, i) => Ci(18 + i * 10.5, top + H - 6 - ((i * 13) % 34), i === 6 ? 3.5 : 2.2, i === 6 ? C.brand : C.mid))];
      }
      if (kind === 'quadCircle') {
        return [...title(), L(60, top, 60, top + H), L(8, top + H / 2, 112, top + H / 2), Ci(36, top + 11, 6, C.mid), Ci(84, top + 11, 9, C.brand), Ci(34, top + 35, 8, C.soft, C.mid), Ci(88, top + 34, 5, C.mid)];
      }
      if (kind === 'bubble') {
        return [...title(), Ci(30, top + 24, 18, C.soft, C.mid), Ci(64, top + 18, 12, C.mid), Ci(92, top + 28, 15, C.brand), Ci(58, top + 38, 6, C.soft, C.mid)];
      }
      return [...title(), ...cols(n, 6, 108, 6).flatMap((c, i) => [Ci(c.x + c.w / 2, top + 16, Math.min(c.w / 2 - 2, 13), i === 0 ? C.brand : C.soft, i === 0 ? undefined : C.mid),
        ...lines(c.x + 3, top + 34, c.w - 6, 2)])];
    }
    case 'timeline': case 'gantt': case 'path': case 'process': case 'chain': case 'journey': case 'stepsCompare': case 'swimlane': {
      if (kind === 'gantt' || kind === 'swimlane') {
        const rows = Math.max(n, 3);
        return [...title(), ...Array.from({ length: rows }, (_, i) => {
          const y = top + i * (H / rows);
          return [R(6, y + 1, 20, 2.5, C.ink, 1), L(30, y + H / rows - 1, 114, y + H / rows - 1, C.gray, 0.8),
            R(30 + ((i * 17) % 40), y, 28 + ((i * 11) % 30), Math.min(7, H / rows - 3), i % 2 ? C.mid : C.brand, 1.5)];
        }).flat()];
      }
      if (kind === 'stepsCompare') {
        return [...title(), ...[0, 1].flatMap((row) => cols(Math.max(n, 3), 6, 108, 6).map((c, i) => R(c.x, top + 4 + row * 22, c.w, 16, row ? C.soft : (i === 0 ? C.brand : C.mid), 2)))];
      }
      const m = Math.max(n, 3);
      const cs = cols(m, 6, 108, 8);
      const y = kind === 'journey' ? top + 18 : top + 14;
      const out: El[] = [...title(), L(cs[0].x + 6, y, cs[m - 1].x + cs[m - 1].w - 6, y, C.mid, 1.4)];
      if (kind === 'journey') out.push(P(`M${cs.map((c, i) => `${c.x + c.w / 2} ${y - 6 + ((i * 9) % 14)}`).join(' L')}`, 'none', C.brand, 1.4));
      cs.forEach((c, i) => {
        if (kind === 'process' || kind === 'chain') out.push(R(c.x, y - 7, c.w, 14, i === 0 ? C.brand : C.soft, 3, i === 0 ? undefined : C.mid));
        else out.push(Ci(c.x + c.w / 2, y, 4, i === 0 ? C.brand : C.white, C.brand));
        out.push(...lines(c.x + 2, y + 12, c.w - 4, 3));
      });
      return out;
    }
    case 'cards2tier': case 'cards2': case 'cards3img': case 'pillars': case 'list3': case 'tiers': case 'layers': case 'cases': case 'logos': {
      if (kind === 'tiers' || kind === 'layers') {
        const m = Math.max(n, 3);
        return [...title(), ...Array.from({ length: m }, (_, i) => {
          const inset = kind === 'tiers' ? i * 8 : 0;
          return R(6 + inset, top + i * (H / m), 108 - inset * 2, H / m - 3, i === 0 ? C.brand : i === 1 ? C.mid : C.soft, 2);
        })];
      }
      if (kind === 'logos') return [...title(), ...[0, 1].flatMap((r) => cols(5, 6, 108, 5).map((c) => R(c.x, top + 4 + r * 22, c.w, 16, C.gray, 2)))];
      if (kind === 'list3') {
        return [...title(), ...Array.from({ length: Math.max(n, 3) }, (_, i) => [Ci(10, top + 5 + i * 14, 3, C.brand), ...lines(17, top + 4 + i * 14, 92, 2, 4, 0.5)]).flat()];
      }
      const m = kind === 'cards2' || kind === 'cards2tier' ? 2 : Math.max(n, 2);
      return [...title(), ...cols(m).flatMap((c, i) => {
        if (kind === 'cards3img' || kind === 'cases') return [...photo(c.x, top, c.w, 24), ...lines(c.x + 2, top + 29, c.w - 4, 3)];
        if (kind === 'pillars') return [R(c.x, top, c.w, H, C.soft, 2), R(c.x, top, c.w, 7, C.brand, 1.5), ...lines(c.x + 4, top + 13, c.w - 8, 5)];
        if (kind === 'cards2tier') return [R(c.x, top, c.w, 20, i ? C.soft : C.brand, 2), R(c.x, top + 24, c.w, 22, C.gray, 2), ...lines(c.x + 4, top + 29, c.w - 8, 2)];
        return [R(c.x, top, c.w, H, C.soft, 2), R(c.x + 4, top + 5, 16, 5, C.brand, 1), ...lines(c.x + 4, top + 15, c.w - 8, 5)];
      })];
    }
    case 'quad': case 'swot': case 'matrix': case 'grid4': {
      const g = [{ x: 6, y: top }, { x: 61, y: top }, { x: 6, y: top + 24 }, { x: 61, y: top + 24 }];
      return [...title(), ...g.flatMap((p, i) => [R(p.x, p.y, 53, 22, kind === 'swot' ? [C.soft, C.gray, C.gray, C.soft][i] : i === 1 ? C.soft : C.gray, 2),
        ...(kind === 'swot' ? [R(p.x + 3, p.y + 3, 8, 6, C.brand, 1)] : []), ...lines(p.x + (kind === 'swot' ? 14 : 4), p.y + 5, 34, 3)])];
    }
    case 'summary3': case 'statement': case 'callouts': {
      if (kind === 'statement') return [R(10, 18, 100, 6, C.dark, 1.5), R(10, 28, 76, 6, C.dark, 1.5), R(10, 42, 40, 2.5, C.brand, 1), ...lines(10, 50, 60, 2)];
      if (kind === 'callouts') return [...title(), ...photo(28, top, 64, H), Ci(20, top + 8, 4, C.brand), Ci(100, top + 30, 4, C.brand), ...lines(6, top + 16, 18, 3), ...lines(96, top + 38, 18, 2)];
      return [...title(), R(6, top, 108, 12, C.soft, 2), R(10, top + 4, 70, 4, C.brand, 1), ...cols(3, 6, 108, 4).flatMap((c) => lines(c.x, top + 18, c.w, 5))];
    }
    case 'tree': case 'hub': case 'featureMap': {
      if (kind === 'hub') return [...title(), Ci(60, top + 23, 9, C.brand), ...[[22, top + 8], [98, top + 8], [22, top + 38], [98, top + 38], [60, top + 2]].slice(0, Math.max(n, 3) + 1).flatMap(([x, y]) => [L(60, top + 23, x, y, C.mid), Ci(x, y, 6, C.soft, C.mid)])];
      if (kind === 'featureMap') return [...title(), R(44, top + 15, 32, 16, C.brand, 3), ...[[8, top + 2], [8, top + 30], [84, top + 2], [84, top + 30]].flatMap(([x, y]) => [R(x, y, 28, 14, C.soft, 2, C.mid), L(x < 50 ? x + 28 : x, y + 7, x < 50 ? 44 : 76, top + 23, C.mid)])];
      const kids = cols(Math.max(n, 2), 10, 100, 8);
      return [...title(), R(46, top, 28, 11, C.brand, 2), L(60, top + 11, 60, top + 18), L(kids[0].x + kids[0].w / 2, top + 18, kids[kids.length - 1].x + kids[kids.length - 1].w / 2, top + 18),
        ...kids.flatMap((c) => [L(c.x + c.w / 2, top + 18, c.x + c.w / 2, top + 24), R(c.x, top + 24, c.w, 11, C.soft, 2, C.mid), ...lines(c.x + 2, top + 39, c.w - 4, 2)])];
    }
    case 'table': case 'tableHl': case 'specTable': case 'checkTable': case 'specGroups': case 'qtyMatrix': case 'mapTable': {
      const out: El[] = [...title()];
      const rows = 5;
      const cs = cols(kind === 'specTable' || kind === 'specGroups' ? Math.max(n, 2) + 1 : 4, 6, 108, 2);
      if (kind === 'mapTable') { out.push(...photo(6, top, 40, H)); }
      const x0 = kind === 'mapTable' ? 50 : 6;
      const cs2 = kind === 'mapTable' ? cols(3, 50, 64, 2) : cs;
      out.push(R(x0, top, 114 - x0, 7, C.brand, 1.5));
      for (let r = 1; r < rows; r++) {
        const y = top + r * 9.5;
        if (kind === 'tableHl' && r === 2) out.push(R(x0, y - 1.5, 114 - x0, 8, C.soft, 1));
        if (kind === 'specGroups' && r === 2) out.push(R(x0, y, 30, 2.5, C.brand, 1));
        cs2.forEach((c, i) => {
          if (kind === 'checkTable' && i > 0) out.push(Ci(c.x + c.w / 2, y + 1.5, 2.2, (r + i) % 3 ? C.brand : C.line));
          else if (kind === 'qtyMatrix' && i > 0) out.push(R(c.x + 4, y, c.w - 8, 3.5, (r * i) % 3 ? C.mid : C.soft, 1));
          else out.push(R(c.x + 2, y, c.w * (i === 0 ? 0.8 : 0.6), 2.5, C.ink, 1));
        });
        out.push(L(x0, y + 5.5, 114, y + 5.5, C.gray, 0.6));
      }
      return out;
    }
    case 'persona': return [...title(), ...cols(Math.min(Math.max(n, 1), 3)).flatMap((c) => [R(c.x, top, c.w, H, C.soft, 2), Ci(c.x + 10, top + 10, 5.5, C.brand), ...lines(c.x + 19, top + 7, c.w - 23, 2), ...lines(c.x + 4, top + 22, c.w - 8, 4)])];
    case 'funnel': {
      const m = Math.max(n, 3);
      return [...title(), ...Array.from({ length: m }, (_, i) => { const w = 90 - i * (60 / m); const y = top + i * (H / m); return R(60 - w / 2, y, w, H / m - 2, i === m - 1 ? C.brand : i % 2 ? C.mid : C.soft, 2); })];
    }
    case 'asis': return [...title(), R(6, top, 46, H, C.gray, 2), ...lines(10, top + 6, 38, 5), P(`M56 ${top + 23} L64 ${top + 23} M61 ${top + 19} L65 ${top + 23} L61 ${top + 27}`, 'none', C.brand, 1.6), R(68, top, 46, H, C.soft, 2, C.mid), ...lines(72, top + 6, 38, 5)];
    case 'rows': return [...title(), ...Array.from({ length: Math.max(n, 3) }, (_, i) => { const h = H / Math.max(n, 3); return [R(6, top + i * h, 108, h - 3, i % 2 ? C.gray : C.soft, 2), R(9, top + i * h + 3, 14, 2.5, C.brand, 1), ...lines(28, top + i * h + 3, 80, 1)]; }).flat()];
    case 'split': case 'panel': case 'panelLeft': case 'imagePanel': case 'image': case 'image2': case 'zoom': case 'solIntro': case 'solScene': case 'solSceneInd': case 'indVP': case 'indDay': {
      if (kind === 'image') return [...photo(6, 6, 108, 56), R(10, 48, 50, 4, C.white, 1), R(10, 55, 34, 2.5, C.white, 1)];
      if (kind === 'image2') return [...title(), ...photo(6, top, 53, H), ...photo(61, top, 53, H)];
      if (kind === 'zoom') return [...title(), ...photo(6, top, 70, H), Ci(86, top + 20, 13, C.white, C.brand), P(`M95 ${top + 29} L104 ${top + 38}`, 'none', C.brand, 2), ...lines(80, top + 40, 32, 1)];
      if (kind === 'indDay') return [...title(), ...cols(Math.max(n, 3)).flatMap((c, i) => [...photo(c.x, top, c.w, 26, i % 2 ? C.gray : C.soft), R(c.x, top + 30, 12, 2.5, C.brand, 1), ...lines(c.x, top + 35, c.w, 2)])];
      if (kind === 'solScene' || kind === 'solSceneInd') return [...photo(6, 6, 108, 56), ...cols(Math.max(n, 3), 10, 100, 6).map((c) => R(c.x, 46, c.w, 12, C.white, 2, C.mid)), ...(kind === 'solSceneInd' ? [R(10, 10, 22, 6, C.brand, 3)] : [])];
      const left = kind === 'panelLeft' || kind === 'solIntro';
      const imgX = left ? 50 : 6;
      const txtX = left ? 6 : 66;
      return [...title(), ...photo(imgX, top, kind === 'split' ? 54 : 64 - (left ? 0 : 4), H), R(txtX, top, 6, 6, C.brand, 1), ...lines(txtX, top + 10, left ? 38 : 48, kind === 'indVP' ? 3 : 5),
        ...(kind === 'indVP' ? [R(txtX, top + 28, 44, 12, C.soft, 2)] : [])];
    }
    case 'solDiagram': return [...title(), R(44, top, 32, 12, C.brand, 2), ...cols(3, 6, 108, 8).flatMap((c) => [L(60, top + 12, c.x + c.w / 2, top + 24, C.mid), R(c.x, top + 24, c.w, 14, C.soft, 2, C.mid)]), ...lines(6, top + 42, 60, 1)];
    case 'zones': case 'pins': case 'drawing': case 'indMap': case 'scenes': {
      if (kind === 'scenes') return [...title(), ...cols(Math.max(n, 3)).flatMap((c, i) => [...photo(c.x, top, c.w, 30), R(c.x, top + 34, 10, 6, C.brand, 3), ...lines(c.x + 13, top + 35, c.w - 14, 2)]).slice(0, 40)];
      const out: El[] = [...title(), R(6, top, 108, H, C.gray, 2), P(`M6 ${top + 18} L50 ${top + 18} L50 ${top + H} M50 ${top + 26} L114 ${top + 26} M80 ${top} L80 ${top + 26}`, 'none', C.white, 2)];
      if (kind === 'zones') out.push(R(10, top + 4, 36, 10, 'rgba(20,40,160,0.18)', 2), R(56, top + 30, 52, 12, 'rgba(20,40,160,0.18)', 2));
      if (kind === 'pins' || kind === 'indMap') [[24, top + 10], [70, top + 14], [92, top + 36], [30, top + 34]].slice(0, Math.max(n, 2)).forEach(([x, y]) => out.push(Ci(x, y, 3.2, C.brand), Ci(x, y, 1.2, C.white)));
      if (kind === 'drawing') out.push(R(16, top + 6, 14, 6, C.brand, 1), R(62, top + 32, 20, 6, C.brand, 1));
      return out;
    }
    case 'pA': return [...title(), ...cols(Math.max(n, 1) > 4 ? 4 : Math.max(n, 1)).flatMap((c) => [R(c.x, top, c.w, 30, C.gray, 2), R(c.x + c.w * 0.25, top + 6, c.w * 0.5, 18, C.dark, 1), ...lines(c.x + 2, top + 34, c.w - 4, 2)])];
    case 'pB': return [...title(), ...photo(6, top, 70, H), ...Array.from({ length: Math.min(Math.max(n, 1), 3) }, (_, i) => [R(80, top + i * 16, 34, 13, C.soft, 2), R(83, top + 3 + i * 16, 8, 7, C.dark, 1), ...lines(94, top + 4 + i * 16, 17, 2, 3.5)]).flat()];
    case 'pC': return draw('specTable', n);
    case 'pD': case 'pD1': return [...title(), R(6, top, 54, H, C.gray, 2), R(16, top + 8, 34, 24, C.dark, 1.5), R(64, top + 2, 50, 7, C.brand, 1.5), ...lines(64, top + 14, 48, kind === 'pD1' ? 2 : 4), ...(kind === 'pD' ? cols(Math.max(n, 2) - 1 || 1, 64, 50, 3).map((c) => R(c.x, top + 34, c.w, 12, C.soft, 2)) : [])];
    default: return draw('table', n);
  }
}

export const THUMB_KINDS = ['kpi4', 'barline', 'circles', 'bubble', 'panel', 'timeline', 'cards2tier', 'quad', 'summary3', 'tree', 'process', 'swot', 'persona', 'journey', 'donut', 'table',
  'scatter', 'stack', 'funnel', 'quadCircle', 'pillars', 'asis', 'rows', 'statement', 'hbars', 'roi', 'split', 'image', 'image2', 'imagePanel', 'callouts', 'zoom', 'path', 'zones',
  'qtyMatrix', 'cards3img', 'tiers', 'hub', 'layers', 'swimlane', 'stepsCompare', 'panelLeft', 'featureMap', 'matrix', 'pins', 'scenes', 'chain', 'cases', 'image2kpi', 'bignum',
  'cards2', 'list3', 'logos', 'tableHl', 'radar', 'grid4', 'gantt', 'mapTable', 'specTable', 'checkTable', 'specGroups', 'drawing', 'solIntro', 'solDiagram', 'solScene',
  'solSceneInd', 'indVP', 'indMap', 'indDay', 'pA', 'pB', 'pC', 'pD', 'pD1'] as const;

/** export 카탈로그 썸네일 주소(있을 수도 있다 — export 세션) */
export const templateThumbUrl = (code: string) => `/api/export/v1/templates/${encodeURIComponent(code)}/thumbnail.png`;

export interface ThumbProps {
  kind?: string;
  /** 항목 수 1–5 */
  n?: number;
  /** 템플릿 코드 — 있으면 export 썸네일을 먼저 시도 */
  code?: string;
  /** 직접 넘기는 이미지 주소(같은 출처) */
  src?: string;
  /** 고를 수 없는 후보(opacity .45) */
  dim?: boolean;
  title?: string;
  className?: string;
}

/** 템플릿 썸네일 120×68 */
export function Thumb({ kind = 'table', n = 3, code, src, dim, title, className }: ThumbProps) {
  const url = src ?? (code ? templateThumbUrl(code) : undefined);
  const [failed, setFailed] = useState(false);
  useEffect(() => { setFailed(false); }, [url]);
  const label = title ?? `${code ? `${code} · ` : ''}${kind} 레이아웃`;
  return (
    <span className={cx('wm-thumb', dim && 'wm-thumb--dim', className)} role="img" aria-label={label} title={title} data-kind={kind} data-n={n}>
      {url && !failed
        ? <img src={url} alt="" draggable={false} onError={() => setFailed(true)} />
        : <svg width="120" height="68" viewBox="0 0 120 68" aria-hidden="true">{draw(kind, n)}</svg>}
    </span>
  );
}
