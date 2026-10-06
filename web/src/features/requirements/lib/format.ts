/** 표시 형식 — RQ 보드 규칙(§4.0.3 시간, §0 조사). */

const TZ = 'Asia/Seoul';

function parts(d: Date) {
  const f = new Intl.DateTimeFormat('en-CA', { timeZone: TZ, year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false });
  const p = Object.fromEntries(f.formatToParts(d).map((x) => [x.type, x.value]));
  return { y: Number(p.year), m: Number(p.month), d: Number(p.day), hh: p.hour === '24' ? '00' : p.hour, mm: p.minute };
}

/** `< 1분` 방금 · 오늘 HH:mm · 어제 · 올해 M/D · 그 전 YYYY/M/D */
export function rqTime(iso?: string | null, now: Date = new Date()): string {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  if (now.getTime() - d.getTime() < 60_000) return '방금';
  const a = parts(d);
  const b = parts(now);
  const dayA = Date.UTC(a.y, a.m - 1, a.d);
  const dayB = Date.UTC(b.y, b.m - 1, b.d);
  const days = Math.round((dayB - dayA) / 86_400_000);
  if (days <= 0) return `오늘 ${a.hh}:${a.mm}`;
  if (days === 1) return '어제';
  if (a.y === b.y) return `${a.m}/${a.d}`;
  return `${a.y}/${a.m}/${a.d}`;
}

/** v{n}로/으로 — 3 · 6 · 10(…0) → 으로, ㄹ받침 1 · 7 · 8 과 받침 없는 수 → 로 */
export function ro(n: number): string {
  if (n === 0 || n % 10 === 0) return '으로';
  const d = n % 10;
  return d === 3 || d === 6 ? '으로' : '로';
}

/** v{n}을/를 — 1 · 3 · 6 · 7 · 8 · 0 → 을, 2 · 4 · 5 · 9 → 를 */
export function eul(n: number): string {
  const d = n % 10;
  return [2, 4, 5, 9].includes(d) ? '를' : '을';
}

/** 키맨 색(보드 COL, 4번째부터 Q-9 임시) — 색은 rq.css 의 --rq-km-* 토큰 */
export function kmClass(colorIndex: number): string {
  return `rq-km rq-km--${((colorIndex % 5) + 5) % 5}`;
}

export const initialOf = (name?: string | null) => (name ?? '').trim().slice(0, 1);

export const FIELD_LABEL: Record<string, string> = {
  project_name: '프로젝트명', customer_name: '고객사', final_audience: '최종 제안대상', author_note: '제작자 의견',
};
