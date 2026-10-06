/**
 * 가중치 계산 — 서버(domain.py)와 같은 규칙(§4.6 · §7.2.1 · §10).
 * - 균등: floor(100/n), 앞 키맨부터 나머지 +1(2명 50·50, 3명 34·33·33)
 * - −/+: 5의 배수로 맞춰 이동, 나머지는 현재 비율대로(최대 나머지 반올림, 각 ≥ 5, 합 100)
 * - 막대 경계 끌기: 이웃한 두 키맨 사이 1% 단위, 각 ≥ 5
 */
export const WEIGHT_MIN = 5;

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
export function distribute(shares: number[], total: number, minimum = WEIGHT_MIN): number[] {
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

/** −/+ 스테퍼(§4.6). direction: +1 | -1 */
export function stepWeights(values: number[], index: number, direction: 1 | -1, minimum = WEIGHT_MIN): number[] {
  const n = values.length;
  const cur = values[index];
  let target = direction > 0 ? (Math.floor(cur / 5) + 1) * 5 : Math.floor((cur - 1) / 5) * 5;
  target = Math.max(minimum, Math.min(100 - minimum * (n - 1), target));
  if (target === cur) return [...values];
  const others = values.map((_, i) => i).filter((i) => i !== index);
  const shares = distribute(others.map((i) => values[i]), 100 - target, minimum);
  const out = [...values];
  out[index] = target;
  others.forEach((i, j) => { out[i] = shares[j]; });
  return out;
}

/** 경계 끌기 — 경계 i(키맨 i 와 i+1 사이)를 delta(%)만큼 옮긴다. 두 키맨만 바뀐다. */
export function moveBoundary(values: number[], i: number, delta: number, minimum = WEIGHT_MIN): number[] {
  if (i < 0 || i >= values.length - 1) return [...values];
  const pair = values[i] + values[i + 1];
  const left = Math.max(minimum, Math.min(pair - minimum, values[i] + Math.round(delta)));
  const out = [...values];
  out[i] = left;
  out[i + 1] = pair - left;
  return out;
}

export const sum = (xs: number[]) => xs.reduce((a, b) => a + b, 0);
