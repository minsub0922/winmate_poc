/**
 * 새 Storyboard 화면(SB0 · SB1) 지역 규칙 — 보드 webapp1 SB0 · SB1 renderVals 의 문구 · 링크를 허브 값(@/shell useFlow · useFlows)으로 만든다.
 */
import { CONTENT, type ContentKey, type FlowCell, type StageKey } from '@/shell';

export const SECTION = '전략 수립 Storyboard';
export const ORDER8: StageKey[] = ['rq', 'dss', 'mi', 'ca', 'vp', 'sp', 'sc', 'ppt'];
export const CONTENT_KEYS: ContentKey[] = ['rq', 'dss', 'mi', 'ca', 'vp', 'sp', 'sc'];

/** 보드 SB0 NAMES(어디까지 입력됐나 문구) */
const NAMES: Record<StageKey, string> = { rq: '요구사항', dss: 'DSS', mi: 'MI', ca: '경쟁사', vp: 'VP', sp: 'Spec', sc: '시나리오', ppt: '제안서' };
/** 보드 SB1 연결된 콘텐츠 줄 이름(C) */
export const ROW_LABEL: Record<ContentKey, string> = { rq: '고객 요구사항', dss: 'DSS', mi: 'MI', ca: '경쟁사 분석', vp: 'Value Proposition', sp: 'Spec 시트', sc: '공간 시나리오' };
/** 보드 SB1 진행 칸 이름(T) */
export const TRACK_LABEL: Record<StageKey, string> = { rq: '요구사항', dss: 'DSS', mi: 'MI', ca: '경쟁사', vp: 'VP', sp: 'Spec', sc: '시나리오', ppt: '제안서' };

export const isDone = (cells: FlowCell[], k: StageKey) => cells.some((c) => c.key === k && c.state === 'done');

/** 보드 SB0 stageOf — 요구사항까지 · DSS까지 · DSS + MI · 경쟁사 … */
export function stageText(cells: FlowCell[]): string {
  if (!isDone(cells, 'dss')) return isDone(cells, 'rq') ? '요구사항까지' : '시작 전';
  const after = (['mi', 'ca', 'vp', 'sp', 'sc'] as StageKey[]).filter((k) => isDone(cells, k)).map((k) => NAMES[k]);
  return after.length ? `DSS + ${after.join(' · ')}` : 'DSS까지';
}

export const stageName = (k?: string | null) => (k && k in NAMES ? NAMES[k as StageKey] : '');

/** 「만들기」 — Gate 를 건너뛰고 이 Storyboard 를 가져가 새로 만들기(CF-07). rq 는 요구사항 새로 만들기, ppt 는 제안서 */
export function makeHref(k: StageKey, sbId: string): string {
  if (k === 'ppt') return `/proposal/new?sb=${encodeURIComponent(sbId)}`;
  if (k === 'rq') return '/requirements/new';
  return `/${CONTENT[k].base}/new?sb=${encodeURIComponent(sbId)}&auto=1`;
}

/** 분기 이름(이름 끝 「· 분기 B」) */
export function branchName(name: string): string {
  const m = /·\s*(분기\s*[A-Z])\s*$/.exec(name);
  return m ? m[1] : '분기';
}

// ── 전체 흐름 · json(보드 SB1_Json: 콘텐츠 값은 한 줄, 배열 · 객체는 접어서 `[ … n ]`) ──

const prim = (v: unknown) => v === null || ['string', 'number', 'boolean'].includes(typeof v);
const s = (v: unknown) => JSON.stringify(v);

function inlineArr(a: unknown[]): string {
  if (!a.length) return '[]';
  if (a.every(prim) && a.length <= 3 && s(a).length <= 40) return `[${a.map(s).join(', ')}]`;
  return `[ … ${a.length} ]`;
}

function inlineVal(v: unknown, depth = 0): string {
  if (prim(v)) return s(v);
  if (Array.isArray(v)) return inlineArr(v);
  const o = v as Record<string, unknown>;
  const ks = Object.keys(o);
  if (!ks.length) return '{}';
  if (depth === 0 && ks.every((k) => prim(o[k])) && ks.length <= 3) return `{ ${ks.map((k) => `${s(k)}: ${s(o[k])}`).join(', ')} }`;
  return `{ … ${ks.length} }`;
}

/** 오른쪽 패널(470 − 테두리 2 − 패딩 32 = 436px · 고정폭 12px ≈ 60칸)에 맞춰 줄을 나눈다 — 한글은 1.7칸으로 센다 */
const COLS = 60;
const cols = (t: string) => [...t].reduce((n, c) => n + (c.charCodeAt(0) > 0x2e80 ? 1.7 : 1), 0);

/** stages.<key> 한 블록 — 보드 SB1_Json 처럼 속성을 이어 쓰다 줄이 차면 6칸 들여 다음 줄로 */
function stageLines(key: string, v: Record<string, unknown>, tail: string): string[] {
  const parts = Object.entries(v).map(([k, x]) => `${s(k)}: ${inlineVal(x)}`);
  const head = `    ${s(key)}: { `;
  const lines: string[] = [];
  let cur = head;
  parts.forEach((p, i) => {
    const piece = p + (i < parts.length - 1 ? ',' : ` }${tail}`);
    if (cur !== head && cols(`${cur} ${piece}`) > COLS) { lines.push(cur); cur = `      ${piece}`; }
    else cur = cur === head ? `${cur}${piece}` : `${cur} ${piece}`;
  });
  lines.push(parts.length ? cur : `    ${s(key)}: {}${tail}`);
  return lines;
}

export function foldFlowJson(fj: Record<string, unknown> | undefined | null): string {
  if (!fj) return '';
  const out = ['{'];
  const keys = Object.keys(fj);
  keys.forEach((k, i) => {
    const comma = i < keys.length - 1 ? ',' : '';
    const v = fj[k];
    if (k === 'stages' && v && typeof v === 'object') {
      out.push('  "stages": {');
      const st = v as Record<string, unknown>;
      const ks = Object.keys(st);
      const full = ks.filter((x) => st[x]);
      const nulls = ks.filter((x) => !st[x]);
      full.forEach((x, j) => out.push(...stageLines(x, st[x] as Record<string, unknown>, j < full.length - 1 || nulls.length ? ',' : '')));
      if (nulls.length) out.push(`    ${nulls.map((x) => `${s(x)}: null`).join(', ')}`);
      out.push(`  }${comma}`);
      return;
    }
    out.push(`  ${s(k)}: ${Array.isArray(v) ? (v.every(prim) ? `[${v.map(s).join(', ')}]` : inlineArr(v)) : inlineVal(v, 1)}${comma}`);
  });
  out.push('}');
  return out.join('\n');
}
