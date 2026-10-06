/**
 * 키맨 색(보드 COL 5색) · 키맨 아바타 · 점 · 가중치 막대 · − / + 스테퍼 — RQ1 · RQ2 · RQ3 · RQ5 · RQ6 · RQ7B, SB · MI 키맨 가중치.
 *
 * 규칙(requirements 서버 domain.py 와 같음, 01-requirements §4.6):
 * - 균등: floor(100/n), 앞 키맨부터 나머지 +1(2명 50·50, 3명 34·33·33)
 * - −/+: 5의 배수로 맞춰 이동, 나머지는 현재 비율대로(최대 나머지 반올림, 각 ≥ 5, 합 100)
 * - 막대 경계 끌기: 이웃한 두 키맨 사이 1% 단위, 각 ≥ 5
 *
 *   <WeightBar items={keymen.map((k) => ({ id: k.id, name: k.name, colorIndex: k.color_index, weight: k.weight }))} onCommit={save} />
 *   <WeightStepper label={k.name} value={k.weight} onStep={(d) => save(stepWeights(values, i, d))} />
 */
import { useRef, useState, type CSSProperties, type ReactNode } from 'react';
import { cx } from './controls';

export const WEIGHT_MIN = 5;

/** 키맨 색 클래스(`wm-km` · `wm-km--1..4`) — color_index 0..4 순환. 바탕 · 글자 토큰 `--wm-km-{i}-bg` · `--wm-km-{i}-fg` */
export function kmClass(colorIndex: number): string {
  const i = ((Math.trunc(colorIndex) % 5) + 5) % 5;
  return i === 0 ? 'wm-km' : `wm-km wm-km--${i}`;
}
/** 키맨 색 토큰 쌍(직접 스타일에 쓸 때) */
export const kmColors = (colorIndex: number) => {
  const i = ((Math.trunc(colorIndex) % 5) + 5) % 5;
  return { bg: `var(--wm-km-${i}-bg)`, fg: `var(--wm-km-${i}-fg)` };
};

export function equalWeights(n: number): number[] {
  if (n <= 0) return [];
  const base = Math.floor(100 / n);
  const rem = 100 - base * n;
  return Array.from({ length: n }, (_, i) => base + (i < rem ? 1 : 0));
}

function equalSplit(total: number, n: number): number[] {
  const base = Math.floor(total / n);
  const rem = total - base * n;
  return Array.from({ length: n }, (_, i) => base + (i < rem ? 1 : 0));
}

/** 비율대로 total 을 정수로 나눈다(최대 나머지 반올림, 각 ≥ minimum). */
export function distributeWeights(shares: number[], total: number, minimum = WEIGHT_MIN): number[] {
  const n = shares.length;
  if (n === 0) return [];
  if (total < minimum * n) return equalSplit(total, n);
  const w = shares.map((s) => Math.max(Number(s) || 0, 0));
  const fixed = new Map<number, number>();
  for (let round = 0; round < n; round++) {
    const free = w.map((_, i) => i).filter((i) => !fixed.has(i));
    const remaining = total - [...fixed.values()].reduce((a, b) => a + b, 0);
    const ssum = free.reduce((a, i) => a + w[i], 0);
    const raw = new Map(free.map((i) => [i, ssum > 0 ? (remaining * w[i]) / ssum : remaining / free.length]));
    const low = free.filter((i) => (raw.get(i) ?? 0) < minimum);
    if (low.length === 0) {
      const floors = new Map(free.map((i) => [i, Math.floor(raw.get(i)!)]));
      let left = remaining - [...floors.values()].reduce((a, b) => a + b, 0);
      const order = [...free].sort((a, b) => (raw.get(b)! - floors.get(b)!) - (raw.get(a)! - floors.get(a)!) || a - b);
      for (const i of order) {
        if (left <= 0) break;
        floors.set(i, floors.get(i)! + 1);
        left -= 1;
      }
      for (const [i, v] of floors) fixed.set(i, v);
      break;
    }
    for (const i of low) fixed.set(i, minimum);
  }
  return w.map((_, i) => fixed.get(i) ?? 0);
}

/** −/+ 스테퍼 한 번(direction +1 | -1) — 5의 배수로 맞추고 나머지는 비율대로 */
export function stepWeights(values: number[], index: number, direction: 1 | -1, minimum = WEIGHT_MIN): number[] {
  const n = values.length;
  const cur = values[index];
  let target = direction > 0 ? (Math.floor(cur / 5) + 1) * 5 : Math.floor((cur - 1) / 5) * 5;
  target = Math.max(minimum, Math.min(100 - minimum * (n - 1), target));
  if (target === cur) return [...values];
  const others = values.map((_, i) => i).filter((i) => i !== index);
  const shares = distributeWeights(others.map((i) => values[i]), 100 - target, minimum);
  const out = [...values];
  out[index] = target;
  others.forEach((i, j) => { out[i] = shares[j]; });
  return out;
}

/** 경계 끌기 — 경계 i(키맨 i 와 i+1 사이)를 delta(%)만큼 옮긴다. 두 키맨만 바뀐다. */
export function moveWeightBoundary(values: number[], i: number, delta: number, minimum = WEIGHT_MIN): number[] {
  if (i < 0 || i >= values.length - 1) return [...values];
  const pair = values[i] + values[i + 1];
  const left = Math.max(minimum, Math.min(pair - minimum, values[i] + Math.round(delta)));
  const out = [...values];
  out[i] = left;
  out[i + 1] = pair - left;
  return out;
}

/** 키맨 아바타(원, 이름 첫 글자, 키맨 색) — 28(기본) · 22 · 20 */
export function KeymanAvatar({ name, colorIndex, size = 28, title }: { name?: string | null; colorIndex: number; size?: number; title?: string }) {
  const style: CSSProperties = { width: size, height: size, fontSize: size <= 20 ? 10.5 : size <= 22 ? 11 : 12.5 };
  return <span className={cx('wm-kmav', kmClass(colorIndex))} style={style} title={title ?? name ?? undefined} aria-hidden={title ? undefined : true}>{(name ?? '').trim().slice(0, 1)}</span>;
}

/** 키맨 색 점(8 원) — 질문 태그 · 주제 칩 */
export function KeymanDot({ colorIndex, size = 8 }: { colorIndex: number; size?: number }) {
  return <span className={cx('wm-kmdot', kmClass(colorIndex))} style={size !== 8 ? { width: size, height: size } : undefined} aria-hidden="true" />;
}

export interface WeightItem { id: string; name?: string | null; colorIndex: number; weight: number }

/**
 * 가중치 막대 — 키맨마다 칸(키맨 색 · `{n}%`). `onCommit` 이 있으면 경계를 끌어 1% 단위로 조정(각 ≥ 5) — 놓을 때 onCommit(새 값).
 * 키보드: 경계 손잡이에서 ← / →(1%). size: lg 28(기본) · md 22 · sm 18. `data-weights` 에 지금 값.
 */
export function WeightBar({ items, size = 'lg', onCommit, showPercent = true, label = '키맨 가중치 · 경계를 끌어서 조정', min = WEIGHT_MIN }: {
  items: WeightItem[]; size?: 'sm' | 'md' | 'lg'; onCommit?: (weights: number[]) => void; showPercent?: boolean; label?: string; min?: number;
}) {
  const bar = useRef<HTMLDivElement>(null);
  const [preview, setPreview] = useState<number[] | null>(null);
  const drag = useRef<{ i: number; x: number; start: number[] } | null>(null);
  const values = preview ?? items.map((k) => k.weight ?? 0);
  const interactive = !!onCommit && items.length >= 2;
  const handles: ReactNode[] = [];
  if (interactive) {
    let acc = 0;
    for (let i = 0; i < items.length - 1; i++) {
      acc += values[i];
      handles.push(
        <button key={i} type="button" className="wm-wbar__handle" style={{ left: `${acc}%` }}
          aria-label={`${items[i].name || '키맨'} · ${items[i + 1].name || '키맨'} 경계`}
          aria-valuenow={values[i]} aria-valuemin={min} aria-valuemax={values[i] + values[i + 1] - min} role="slider" aria-orientation="horizontal"
          onPointerDown={(e) => {
            (e.target as HTMLElement).setPointerCapture?.(e.pointerId);
            drag.current = { i, x: e.clientX, start: values };
          }}
          onPointerMove={(e) => {
            const d = drag.current;
            if (!d || !bar.current) return;
            const pct = ((e.clientX - d.x) / bar.current.getBoundingClientRect().width) * 100;
            setPreview(moveWeightBoundary(d.start, d.i, Math.round(pct), min));
          }}
          onPointerUp={() => {
            const d = drag.current;
            drag.current = null;
            if (d && preview && preview.some((v, j) => v !== d.start[j])) onCommit?.(preview);
            setPreview(null);
          }}
          onPointerCancel={() => { drag.current = null; setPreview(null); }}
          onKeyDown={(e) => {
            if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return;
            e.preventDefault();
            const next = moveWeightBoundary(values, i, e.key === 'ArrowLeft' ? -1 : 1, min);
            if (next.some((v, j) => v !== values[j])) onCommit?.(next);
          }} />,
      );
    }
  }
  return (
    <div ref={bar} className={cx('wm-wbar', size !== 'lg' && `wm-wbar--${size}`)} role="group" aria-label={label} data-weights={values.join(',')}>
      {items.map((k, i) => (
        <span key={k.id} className={cx('wm-wbar__seg', kmClass(k.colorIndex))} style={{ flex: `${Math.max(values[i], 0.5)} 1 0` }} title={`${k.name ?? ''} ${values[i]}%`}>
          {showPercent ? `${values[i]}%` : values[i]}
        </span>
      ))}
      {handles}
    </div>
  );
}

/** − / + 스테퍼(h28, 숫자 Manrope 800) — 한 번에 5의 배수로(규칙은 stepWeights) */
export function WeightStepper({ value, onStep, label = '키맨', min = WEIGHT_MIN, max = 100, disabled, 'data-testid': testId }:
  { value: number; onStep: (direction: 1 | -1) => void; label?: string; min?: number; max?: number; disabled?: boolean; 'data-testid'?: string }) {
  return (
    <span className="wm-wstep" data-testid={testId}>
      <button type="button" aria-label={`${label} 가중치 낮추기`} disabled={disabled || value <= min} onClick={() => onStep(-1)}>−</button>
      <span className="wm-num">{value}%</span>
      <button type="button" aria-label={`${label} 가중치 높이기`} disabled={disabled || value >= max} onClick={() => onStep(1)}>+</button>
    </span>
  );
}
