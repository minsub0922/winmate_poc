/**
 * 표기 규칙(00-shell §9.2 · §9.3 · §5.1.4) — 화면마다 같은 모양으로 쓰도록 키트에 둔다.
 */

const DEFAULT_TZ = 'Asia/Seoul';

function toDate(v: string | number | Date | null | undefined): Date | null {
  if (v === null || v === undefined || v === '') return null;
  const d = v instanceof Date ? v : new Date(v);
  return Number.isNaN(d.getTime()) ? null : d;
}

/** 시간대 기준 달력 조각(년 · 월 · 일 · 시 · 분). */
function parts(d: Date, tz = DEFAULT_TZ) {
  const f = new Intl.DateTimeFormat('en-US', {
    timeZone: tz, year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
  });
  const o: Record<string, string> = {};
  for (const p of f.formatToParts(d)) o[p.type] = p.value;
  return { y: Number(o.year), m: Number(o.month), d: Number(o.day), h: Number(o.hour) % 24, min: Number(o.minute) };
}

/** KST(기본) 날짜 `YYYY-MM-DD`. 날짜만 있는 문자열은 그대로 돌려준다. */
export function formatDate(iso?: string | null, tz = DEFAULT_TZ) {
  if (!iso) return '';
  if (/^\d{4}-\d{2}-\d{2}$/.test(iso)) return iso;
  const d = toDate(iso);
  if (!d) return iso;
  const p = parts(d, tz);
  return `${p.y}-${String(p.m).padStart(2, '0')}-${String(p.d).padStart(2, '0')}`;
}

/** KST(기본) `YYYY-MM-DD HH:mm` */
export function formatDateTime(iso?: string | null, tz = DEFAULT_TZ) {
  if (!iso) return '';
  const d = toDate(iso);
  if (!d) return iso;
  const p = parts(d, tz);
  return `${formatDate(iso, tz)} ${String(p.h).padStart(2, '0')}:${String(p.min).padStart(2, '0')}`;
}

/** 사람이 읽는 용량(B · KB · MB). 원본/저장본 표기는 formatKB 를 쓴다. */
export function formatBytes(n?: number | null) {
  if (!n && n !== 0) return '';
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(0)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}

/** §9.2 용량: round(bytes ÷ 1024) + 천 단위 쉼표 + ` KB` (739,867 B → `723 KB`) */
export function formatKB(bytes?: number | null) {
  if (bytes === null || bytes === undefined || Number.isNaN(bytes)) return '';
  return `${Math.round(bytes / 1024).toLocaleString('en-US')} KB`;
}

/** 천 단위 쉼표 */
export const formatNumber = (n?: number | null) => (n === null || n === undefined ? '' : n.toLocaleString('en-US'));

/**
 * 시점 표기(§5.1.4 [제안]): 1분 미만 `방금` · 60분 미만 `N분 전` · 24시간 미만 `N시간 전` · 달력상 어제 `어제`
 * · 7일 미만 `N일 전` · 그 이전 `M/D`(올해) / `YYYY-MM-DD`(지난해).
 */
export function relativeTime(iso?: string | null, now: Date = new Date(), tz = DEFAULT_TZ) {
  const d = toDate(iso ?? null);
  if (!d) return '';
  const diff = now.getTime() - d.getTime();
  const min = Math.floor(diff / 60000);
  if (diff < 60000) return '방금';
  if (min < 60) return `${min}분 전`;
  if (min < 24 * 60) return `${Math.floor(min / 60)}시간 전`;
  const a = parts(d, tz);
  const b = parts(now, tz);
  const dayA = Date.UTC(a.y, a.m - 1, a.d);
  const dayB = Date.UTC(b.y, b.m - 1, b.d);
  const days = Math.round((dayB - dayA) / 86400000);
  if (days === 1) return '어제';
  if (days < 7) return `${days}일 전`;
  if (a.y === b.y) return `${a.m}/${a.d}`;
  return formatDate(d.toISOString(), tz);
}

/** 홈 인사말(§5.1.1 [제안]): 05–11:59 아침 · 12–17:59 오후 · 18–04:59 저녁 · 시각을 모르면 `안녕하세요`. */
export function greetingFor(now: Date | null, tz = DEFAULT_TZ) {
  if (!now || Number.isNaN(now.getTime())) return '안녕하세요';
  let h: number;
  try { h = parts(now, tz).h; } catch { return '안녕하세요'; }
  if (h >= 5 && h < 12) return '좋은 아침이에요';
  if (h >= 12 && h < 18) return '좋은 오후예요';
  return '좋은 저녁이에요';
}

/** §9.3 해상도 라벨 */
export function resolutionLabel(w?: number | null, h?: number | null) {
  if (!w || !h) return '';
  const key = `${w}x${h}`;
  const map: Record<string, string> = { '3840x2160': '4K UHD', '1920x1080': 'FHD', '2560x1440': 'QHD', '7680x4320': '8K' };
  return map[key] ?? `${w} × ${h}`;
}

/** `{W} × {H} · {형식} · {KB}` (이미지 정보 · 시트 메타) */
export function formatMediaSize(m?: { width: number; height: number; format?: string | null; bytes?: number | null } | null, sep = ' × ') {
  if (!m || !m.width || !m.height) return '';
  const out = [`${m.width}${sep}${m.height}`];
  if (m.format) out.push(m.format.toUpperCase());
  if (m.bytes !== null && m.bytes !== undefined) out.push(formatKB(m.bytes));
  return out.join(' · ');
}

/**
 * 원본 파일 표시(§9.2): `호스트/경로/` + 파일명(36자 이상이면 앞 8자 + `…` + 확장자).
 * `https://images.samsung.com/kdp/goods/2023/08/29/cc897d99-d2e6-….png` → `images.samsung.com/kdp/goods/2023/08/29/cc897d99….png`
 */
export function shortFileUrl(url?: string | null) {
  if (!url) return '';
  let u: URL;
  try { u = new URL(url); } catch { return url; }
  const path = decodeURIComponent(u.pathname);
  const slash = path.lastIndexOf('/');
  const dir = path.slice(0, slash + 1);
  const file = path.slice(slash + 1);
  let shown = file;
  if (file.length >= 36) {
    const dot = file.lastIndexOf('.');
    const ext = dot > 0 ? file.slice(dot) : '';
    shown = `${file.slice(0, 8)}…${ext}`;
  }
  return `${u.host}${dir}${shown}`;
}

/** 사례 URL 표시(§9.2): `https://www.` 과 끝 `/` 를 뺀다. */
export function displayUrl(url?: string | null) {
  if (!url) return '';
  return url.replace(/^https?:\/\/(www\.)?/, '').replace(/\/$/, '');
}

/** URL 의 도메인(`www.` 제외) */
export function hostOf(url?: string | null) {
  if (!url) return '';
  try { return new URL(url).host.replace(/^www\./, ''); } catch { return ''; }
}

/** 받침 유무로 조사 고르기 — `josa('MagicINFO', '이', '가')` → `가`. 영문은 끝 글자 발음으로 근사(L·M·N·R 은 받침). */
export function josa(word: string, withFinal: string, withoutFinal: string) {
  const w = word.trim();
  if (!w) return withoutFinal;
  const ch = w[w.length - 1];
  const code = ch.charCodeAt(0);
  if (code >= 0xac00 && code <= 0xd7a3) return (code - 0xac00) % 28 > 0 ? withFinal : withoutFinal;
  if (/[0-9]/.test(ch)) return '0136780'.includes(ch) ? withFinal : withoutFinal;
  return /[lmnrLMNR]/.test(ch) ? withFinal : withoutFinal;
}
