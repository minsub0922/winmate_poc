/**
 * 공간 시나리오(SC) 화면 공용 — 경로 · 스텝바 · 조사 · 시각 문구(09-scenario §1 · §2 · §4).
 * W 말풍선은 LLM 이 쓰지 않고 상태 값으로 채우는 템플릿이다(§1 화면 원칙).
 */
export const SECTION = '공간 시나리오 생성';
export const STEPS = ['시나리오 유형', '공간 시나리오 입력', '솔루션 · 제품 입력', '시나리오 생성'];

/** 이전 흐름 경로 — 목록 · 새로 만들기는 /scenario/legacy 아래(새 흐름 목록 · Gate 가 /scenario · /scenario/new) */
export const route = {
  list: () => '/scenario/legacy',
  newType: () => '/scenario/legacy/new',
  template: (industry?: string | null) => (industry ? `/scenario/legacy/new/template?industry=${industry}` : '/scenario/legacy/new/template'),
  fromBirdseye: (beId?: string | null) => (beId ? `/scenario/legacy/new/birdseye?birdseye=${beId}` : '/scenario/legacy/new/birdseye'),
  type: (id: string) => `/scenario/${id}/type`,
  input: (id: string) => `/scenario/${id}/input`,
  timeline: (id: string) => `/scenario/${id}/timeline`,
  solutions: (id: string) => `/scenario/${id}/solutions`,
  recommend: (id: string) => `/scenario/${id}/solutions/recommend`,
  generate: (id: string, jobId: string) => `/scenario/${id}/generate/${jobId}`,
  result: (id: string) => `/scenario/${id}/result`,
  scene: (id: string, sceneId: string) => `/scenario/${id}/scenes/${sceneId}`,
  send: (id: string) => `/scenario/${id}/send`,
  resync: (id: string) => `/scenario/${id}/birdseye`,
};

/** 스텝바(§1): SC1·SC1T=1, SC1B·SC2·SC2E=2, SC3·SC3R=3, SC4G·SC4·SC4E=4, SC5=4 + complete */
export const stepper = (current: number, complete = false) => ({ steps: STEPS, current, complete });

// ── 조사(§1: 앞말 발음 — 한글 받침 · 숫자 읽는 소리 · 영문 마지막 글자) ──
const DIGIT_BATCHIM: Record<string, boolean> = { '0': true, '1': true, '2': false, '3': true, '4': false, '5': false, '6': true, '7': true, '8': true, '9': false };
const EN_BATCHIM = new Set(['b', 'c', 'd', 'g', 'k', 'l', 'm', 'n', 'p', 't']);
export function hasBatchim(word: string): boolean | null {
  const w = word.replace(/[\s)\]」』"'.,·]+$/u, '');
  const ch = w.slice(-1);
  if (!ch) return null;
  const code = ch.charCodeAt(0);
  if (code >= 0xac00 && code <= 0xd7a3) return (code - 0xac00) % 28 !== 0;
  if (ch in DIGIT_BATCHIM) return DIGIT_BATCHIM[ch];
  const lower = ch.toLowerCase();
  if (/[a-z]/.test(lower)) {
    if (/(ll|ng)$/i.test(w)) return true;
    return EN_BATCHIM.has(lower);
  }
  return null;
}
/** josa('장면 2', '은', '는') → '는' · 모르면 뒤엣것 */
export const josa = (word: string, withB: string, without: string) => (hasBatchim(word) ? withB : without);
/** '장면 2는' 처럼 붙여 준다 */
export const withJosa = (word: string, withB: string, without: string) => `${word}${josa(word, withB, without)}`;

// ── 시각(SC0 「수정」: 방금 · 오늘 HH:mm · 어제 HH:mm · M월 D일) ──
const SEOUL = 'Asia/Seoul';
function parts(d: Date) {
  const f = new Intl.DateTimeFormat('en-CA', { timeZone: SEOUL, year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false });
  const o: Record<string, string> = {};
  for (const p of f.formatToParts(d)) o[p.type] = p.value;
  return { y: Number(o.year), m: Number(o.month), d: Number(o.day), hh: o.hour === '24' ? '00' : o.hour, mm: o.minute };
}
export function whenLabel(iso?: string | null, now: Date = new Date()): string {
  if (!iso) return '';
  const t = new Date(iso);
  if (Number.isNaN(t.getTime())) return '';
  const diff = (now.getTime() - t.getTime()) / 1000;
  if (diff < 60) return '방금';
  const a = parts(t);
  const b = parts(now);
  const dayKey = (x: { y: number; m: number; d: number }) => Date.UTC(x.y, x.m - 1, x.d);
  const days = Math.round((dayKey(b) - dayKey(a)) / 86_400_000);
  if (days === 0) return `오늘 ${a.hh}:${a.mm}`;
  if (days === 1) return `어제 ${a.hh}:${a.mm}`;
  return `${a.m}월 ${a.d}일`;
}
/** 「방금」 · 「12분 전」 · 「어제」 · 「9월 24일」 — 마지막 저장 · 이미지 버전 줄 */
export function agoLabel(iso?: string | null, now: Date = new Date()): string {
  if (!iso) return '';
  const t = new Date(iso);
  if (Number.isNaN(t.getTime())) return '';
  const diff = Math.max(0, (now.getTime() - t.getTime()) / 1000);
  if (diff < 60) return '방금';
  if (diff < 3600) return `${Math.floor(diff / 60)}분 전`;
  const a = parts(t);
  const b = parts(now);
  const days = Math.round((Date.UTC(b.y, b.m - 1, b.d) - Date.UTC(a.y, a.m - 1, a.d)) / 86_400_000);
  if (days === 0) return `${Math.floor(diff / 3600)}시간 전`;
  if (days === 1) return '어제';
  return `${a.m}월 ${a.d}일`;
}
/** ETA 「약 20초 남음」 · 「약 2분 남음」(07 §10.5 규칙과 같음) */
export function etaLabel(s?: number | null): string {
  if (s === null || s === undefined || !Number.isFinite(s)) return '';
  if (s <= 5) return '곧 끝나요';
  if (s < 60) return `약 ${Math.max(5, Math.round(s / 5) * 5)}초 남음`;
  return `약 ${Math.round(s / 60)}분 남음`;
}

/** 「장면 3 · 4」(번호 목록) */
export const sceneList = (nos: number[]) => (nos.length ? `장면 ${nos.join(' · ')}` : '');

/** `[00]` · `[확정 필요]` 토큰을 강조할 수 있게 나눈다 */
export function splitTokens(text: string): Array<{ t: string; mark: boolean }> {
  const out: Array<{ t: string; mark: boolean }> = [];
  const re = /\[(?:00|확정 필요|확인 필요)\]/g;
  let last = 0;
  for (let m = re.exec(text); m; m = re.exec(text)) {
    if (m.index > last) out.push({ t: text.slice(last, m.index), mark: false });
    out.push({ t: m[0], mark: true });
    last = m.index + m[0].length;
  }
  if (last < text.length) out.push({ t: text.slice(last), mark: false });
  return out;
}

export const TYPE_UPPER: Record<string, string> = { with: 'WITH 솔루션', without: 'WITHOUT 솔루션' };
export const TYPE_ROW: Record<string, string> = { with: 'with 솔루션', without: 'without' };
