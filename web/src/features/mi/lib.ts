/** MI 화면 계산 — 서버 규칙(services/mi/config · rules.py)과 같은 식을 화면에서 즉시 다시 셀 때 쓴다(§10.8 · §4.9). */
import { josa } from '@/ui';
import type { Area, Mode } from './api';

const halfUp = (x: number) => Math.floor(x + 0.5);

/** 남은 시간: 60초 미만 10초 단위 `약 {s}초`, 이상 30초 단위 `약 {m}분` / `약 {m}분 30초` (AC-MI-21) */
export function etaText(etaS: number | null | undefined): string {
  if (etaS === null || etaS === undefined) return '';
  const s = Math.max(0, Math.round(etaS));
  if (s < 60) return `약 ${Math.max(10, halfUp(s / 10) * 10)}초`;
  const halves = halfUp(s / 30);
  const m = Math.floor(halves / 2);
  return halves % 2 ? `약 ${m}분 30초` : `약 ${m}분`;
}

/** 분석 시작 버튼: 처음 예상 `60 + 30 × 영역 수` 초 → 분 단위 반올림 */
export function runLabel(nAreas: number): string {
  const s = 60 + 30 * Math.max(1, nAreas);
  return `분석 시작 (약 ${Math.max(1, halfUp(s / 60))}분)`;
}

/** 가중치 → 비율: 마지막 행 = 100 − 앞 행 합(합계 늘 100%, AC-MI-85) */
export function weightPcts(ws: number[]): number[] {
  const sum = ws.reduce((a, b) => a + b, 0) || 1;
  let acc = 0;
  return ws.map((w, i) => {
    if (i === ws.length - 1) return 100 - acc;
    const p = halfUp((w / sum) * 100);
    acc += p;
    return p;
  });
}

/** 받침에 따라 조사 고르기(`{이름}을`/`{이름}를` 등) */
export const withJosa = (word: string, a: string, b: string) => `${word}${josa(word, a, b)}`;

/** `로`/`으로` — 받침이 없거나 ㄹ 받침이면 `로`(`호텔 · 리조트로`, `호텔로`), 그 밖 받침은 `으로` */
export function withRo(word: string): string {
  const w = word.trim();
  const ch = w[w.length - 1] ?? '';
  const code = ch.charCodeAt(0);
  if (code >= 0xac00 && code <= 0xd7a3) {
    const jong = (code - 0xac00) % 28;
    return `${w}${jong === 0 || jong === 8 ? '로' : '으로'}`;
  }
  return `${w}${josa(w, '으로', '로')}`;
}

export const MODE_LABEL: Record<Mode, string> = { auto: '자동', check: '확인 권장', ask: '선택 필요', pin: '고정' };

export const AREA_SHORT: Record<Area, string> = { market: '시장', customer: '고객', user: '사용자', competitor: '경쟁' };
export const AREA_NAME: Record<Area, string> = { market: '시장조사', customer: '고객사 · 비즈니스', user: '사용자', competitor: '경쟁사 → 삼성 강점' };
/** MI2 범위 카드 제목(고정) */
export const SCOPE_TITLE: Record<Area, string> = {
  market: '비즈니스 시장조사', customer: '고객사 · 비즈니스 분석', user: '비즈니스 사용자 분석', competitor: '경쟁사 분석 → 삼성 강점',
};

/** 진행 막대 폭(0–100) */
export const clampPct = (n: number | null | undefined) => Math.max(0, Math.min(100, Math.round(n ?? 0)));

/** 클립보드 — 실패해도 조용히(사내망 http 에서는 navigator.clipboard 가 없을 수 있다) */
export async function copyText(text: string, html?: string): Promise<boolean> {
  try {
    if (html && typeof ClipboardItem !== 'undefined' && navigator.clipboard?.write) {
      await navigator.clipboard.write([new ClipboardItem({
        'text/plain': new Blob([text], { type: 'text/plain' }), 'text/html': new Blob([html], { type: 'text/html' }),
      })]);
      return true;
    }
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch { /* 아래 대체 */ }
  try {
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.setAttribute('readonly', '');
    ta.style.position = 'fixed';
    ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.select();
    const ok = document.execCommand('copy');
    ta.remove();
    return ok;
  } catch {
    return false;
  }
}

/** TSV → 간단한 HTML 표(표 복사) */
export function tsvToHtml(columns: string[], rows: string[][]): string {
  const esc = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  const head = `<tr>${columns.map((c) => `<th>${esc(c)}</th>`).join('')}</tr>`;
  const body = rows.map((r) => `<tr>${r.map((c) => `<td>${esc(c)}</td>`).join('')}</tr>`).join('');
  return `<table>${head}${body}</table>`;
}

/** 경쟁사 표기 미리보기(§5.6 · MI2C 보드 로직) */
export function namingLabel(c: { letter: string; real_name: string; kind_label?: string | null }, anonymize: boolean, mode: 'letter' | 'type'): string {
  if (!anonymize) return `${c.real_name} · 사내용`;
  return mode === 'type' ? (c.kind_label || `경쟁사 ${c.letter}`) : `경쟁사 ${c.letter}`;
}
