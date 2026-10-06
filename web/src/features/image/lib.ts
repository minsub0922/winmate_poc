/**
 * 이미지 생성(IMG) 화면 공용 — 경로 · 라벨 · 조사 · 시간 문구(07-image §1 · §4 · §10.5).
 * W 말풍선은 LLM 이 쓰지 않고 상태 값으로 채우는 템플릿이다(§1 화면 원칙).
 */
export const SECTION = '이미지 생성';
export const STEPS = ['이미지 유형', '상세 조건', '생성 결과'];

export const route = {
  list: () => '/image',
  newWork: (workId?: string | null) => (workId ? `/image/new?work=${workId}` : '/image/new'),
  conditions: (w: string) => `/image/w/${w}/conditions`,
  references: (w: string) => `/image/w/${w}/references`,
  composite: (w: string) => `/image/w/${w}/composite`,
  run: (w: string, r: string) => `/image/w/${w}/run/${r}`,
  result: (w: string, image?: string | null, run?: string | null) => {
    const p = new URLSearchParams();
    if (image) p.set('image', image);
    if (run) p.set('run', run);
    const s = p.toString();
    return `/image/w/${w}/result${s ? `?${s}` : ''}`;
  },
  edit: (w: string, i: string) => `/image/w/${w}/edit/${i}`,
  variants: (w: string, i: string) => `/image/w/${w}/variants/${i}`,
  exportTo: (w: string, i: string, version?: string | null) => `/image/w/${w}/export/${i}${version ? `?version=${version}` : ''}`,
};

export const KIND_LABEL: Record<string, string> = { space: '공간', background: '배경', scenario: '시나리오', composite: '현장 사진 합성' };
export const STYLE_LABEL: Record<string, string> = { photo: '실사 렌더', minimal_3d: '미니멀 3D', illustration: '일러스트' };
export const STYLE_SHORT: Record<string, string> = { photo: '실사', minimal_3d: '3D', illustration: '일러스트' };
export const ASPECTS_GEN = ['16:9', '4:3', '1:1'] as const;
export const ASPECTS_ALL = ['16:9', '4:3', '1:1', '9:16'] as const;
export type AspectAll = (typeof ASPECTS_ALL)[number];

/** §10.2 해상도 사다리 */
const SHORT_SIDE = { native: 0, fhd: 1080, uhd: 2160, uhd8k: 4320 } as const;
export function sizeFor(aspect: string, kind: 'fhd' | 'uhd' | 'uhd8k'): [number, number] {
  const [a, b] = aspect.split(':').map(Number);
  const s = SHORT_SIDE[kind];
  if (!a || !b) return [Math.round((s * 16) / 9), s];
  return a >= b ? [Math.round((s * a) / b), s] : [s, Math.round((s * b) / a)];
}
export const sizeLabel = (w?: number | null, h?: number | null) => (w && h ? `${w}×${h}` : '');

// ── 조사(§1: 한글 받침 · 숫자 읽는 소리 · 영문 마지막 글자) ──
const DIGIT_BATCHIM: Record<string, boolean> = { '0': true, '1': true, '2': false, '3': true, '4': false, '5': false, '6': true, '7': true, '8': true, '9': false };
const EN_BATCHIM = new Set(['b', 'c', 'd', 'g', 'k', 'l', 'm', 'n', 'p', 't']);
/** 마지막 글자 발음에 받침이 있나(모르면 null) */
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
/** josa('시안 1', '을', '를') → '을' · '으로/로' 는 ㄹ 받침이면 '로' */
export function josa(word: string, withB: string, withoutB: string): string {
  const b = hasBatchim(word);
  if (withB === '으로') {
    const ch = word.trim().slice(-1);
    const code = ch.charCodeAt(0);
    if (code >= 0xac00 && code <= 0xd7a3 && (code - 0xac00) % 28 === 8) return '로';
    if (ch === '1' || ch === '7' || ch === '8') return '로';
  }
  return b === false ? withoutB : withB;
}
export const withJosa = (word: string, withB: string, withoutB: string) => `${word}${josa(word, withB, withoutB)}`;

/** §10.5 남은 시간 */
export function remainingLabel(s?: number | null): string {
  if (s === null || s === undefined || s < 0) return '';
  if (s >= 60) return `약 ${Math.ceil(s / 60)}분 남음`;
  return `약 ${Math.max(10, Math.round(s / 10) * 10)}초 남음`;
}

export const pct = (v: number) => `${Math.round(Math.max(0, Math.min(100, v)))}%`;

/** 시안 라벨 「시안 1」에서 숫자 */
export const shotNo = (label: string) => (/(\d+)/.exec(label)?.[1] ?? label);

/** 다운로드(같은 출처 링크) — a[download] 클릭 */
export function downloadUrl(url: string, filename?: string) {
  const a = document.createElement('a');
  a.href = url;
  if (filename) a.download = filename;
  a.rel = 'noopener';
  document.body.appendChild(a);
  a.click();
  a.remove();
}

/** 파일 내용 URL에 ?download=1 */
export const withDownload = (url: string) => (url.includes('?') ? `${url}&download=1` : `${url}?download=1`);

/** 업로드 허용(§10.4): JPG · PNG · HEIC, 20MB */
export const UPLOAD_ACCEPT = 'image/jpeg,image/png,image/heic,image/heif,.jpg,.jpeg,.png,.heic,.heif';
export const UPLOAD_MAX = 20 * 1024 * 1024;
export function checkUpload(f: File): string | null {
  const okType = /\.(jpe?g|png|heic|heif)$/i.test(f.name) || /^image\/(jpeg|png|heic|heif)$/.test(f.type);
  if (!okType) return 'JPG · PNG · HEIC 파일만 올릴 수 있어요';
  if (f.size > UPLOAD_MAX) return '20MB 이하 파일만 올릴 수 있어요';
  return null;
}

/** 셸 참조 → 종류 */
export function refKind(r: string): { ns: string; kind: string; id: string } {
  const [ns, kind, ...rest] = r.split(':');
  return { ns: ns ?? '', kind: kind ?? '', id: rest.join(':') };
}
