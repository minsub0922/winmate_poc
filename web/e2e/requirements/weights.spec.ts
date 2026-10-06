/**
 * 가중치 규칙 웹 단위 테스트(§9.1 AC 5 · §10) — 화면이 쓰는 lib/weights.ts 를 그대로 부른다(브라우저 없음).
 */
import { expect, test } from '@playwright/test';
import { distribute, equalWeights, moveBoundary, stepWeights, sum } from '../../src/features/requirements/lib/weights';

test('균등 기본값: floor(100/n), 앞 키맨부터 나머지 +1', () => {
  expect(equalWeights(1)).toEqual([100]);
  expect(equalWeights(2)).toEqual([50, 50]);
  expect(equalWeights(3)).toEqual([34, 33, 33]);
  expect(equalWeights(6)).toEqual([17, 17, 17, 17, 16, 16]);
});

test('스테퍼: 5의 배수로 이동 · 나머지는 비율대로 · 합 100 · 각 ≥ 5', () => {
  const up = stepWeights([34, 33, 33], 0, 1);
  expect(up[0]).toBe(35);
  expect(up).toEqual([35, 33, 32]);
  expect(stepWeights([35, 33, 32], 0, 1)[0]).toBe(40);
  expect(stepWeights([34, 33, 33], 0, -1)[0]).toBe(30);
  // 끝까지 올려도 다른 키맨은 5 아래로 안 내려간다
  let w = [34, 33, 33];
  for (let i = 0; i < 30; i++) w = stepWeights(w, 0, 1);
  expect(w).toEqual([90, 5, 5]);
  // 끝까지 내려도 5
  for (let i = 0; i < 30; i++) w = stepWeights(w, 0, -1);
  expect(w[0]).toBe(5);
  for (const n of [2, 3, 4, 5]) {
    let v = equalWeights(n);
    for (let i = 0; i < 40; i++) {
      v = stepWeights(v, i % n, i % 3 === 0 ? -1 : 1);
      expect(sum(v)).toBe(100);
      expect(Math.min(...v)).toBeGreaterThanOrEqual(5);
      expect(v.every(Number.isInteger)).toBeTruthy();
    }
  }
});

test('경계 끌기: 이웃한 두 키맨만 1% 단위 · 각 ≥ 5', () => {
  expect(moveBoundary([35, 33, 32], 0, 10)).toEqual([45, 23, 32]);
  expect(moveBoundary([35, 33, 32], 1, -40)).toEqual([35, 5, 60]);
  expect(moveBoundary([50, 50], 0, 80)).toEqual([95, 5]);
  expect(sum(moveBoundary([34, 33, 33], 0, 7))).toBe(100);
});

test('비율 나누기: 최대 나머지 반올림 · 최소 보장', () => {
  expect(distribute([33, 33], 65)).toEqual([33, 32]);
  expect(distribute([90, 1, 1], 100)).toEqual([90, 5, 5]);
  expect(sum(distribute([1, 2, 3], 100))).toBe(100);
});
