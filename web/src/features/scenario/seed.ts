/**
 * 다른 기능에서 넘어온 재료(통합) — SC1 `/scenario/new` 의
 *   `?mi={analysis_id}`(MI4 「공간 시나리오 · 페르소나 n을 시나리오 인물로」) · `?from=mi:{id}` → 페르소나 = 등장인물 + 「[인물] …」 입력 줄
 *   `?from=vp:{vp_id}`(VP4 「공간 시나리오 · 가치 기둥을 장면으로」) → 이해관계자별 가치 · 가치 기둥 · 과제 · 제품 = 입력 줄
 * 읽기는 웹이 게이트웨이로 한다(scenario 서버는 mi · vp 를 consumes 하지 않는다). 원본 문장만 옮기고 지어내지 않는다 — `[00]` · `[확인 필요]` 는 그대로.
 * 읽기 실패면 null(SC1 은 빈 입력으로 그대로 시작).
 */

export type SeedFeature = 'mi' | 'vp';

export interface ScenarioSeed {
  feature: SeedFeature;
  ref: string;
  /** 'Market Intelligence' | 'Value Proposition' */
  label: string;
  title: string;
  customer_name: string | null;
  project_id: string | null;
  /** SC2 입력에 넣을 줄 */
  lines: string[];
  /** SC2 등장인물 칩(MI 페르소나) */
  characters: string[];
  /** SC1 안내 한 줄 */
  note: string;
}

const MAX = 3000;

export function seedSource(sp: URLSearchParams): { feature: SeedFeature; ref: string } | null {
  const [f, ref] = (sp.get('from') ?? '').split(':');
  if ((f === 'mi' || f === 'vp') && ref) return { feature: f, ref };
  const mi = sp.get('mi');
  if (mi) return { feature: 'mi', ref: mi };
  return null;
}

async function getJson<T = any>(url: string): Promise<T> { // eslint-disable-line @typescript-eslint/no-explicit-any
  const r = await fetch(url, { credentials: 'same-origin', headers: { Accept: 'application/json' } });
  if (!r.ok) throw new Error(`${r.status}`);
  return (await r.json()) as T;
}

const clean = (s: unknown): string => (typeof s === 'string' ? s.replace(/\s+/g, ' ').trim() : '');
const push = (arr: string[], v: string) => { if (v && !arr.includes(v)) arr.push(v); };

/** 줄을 MAX 자 안으로(줄 단위로 자른다) */
export function seedText(lines: string[]): string {
  let s = '';
  for (const l of lines) {
    const next = s ? `${s}\n${l}` : l;
    if (next.length > MAX) break;
    s = next;
  }
  return s;
}

interface Persona { role?: string; goal?: string; pain?: string; context?: string }
interface Journey { stage?: string; touchpoint?: string; pain?: string; opportunity?: string }

async function fromMi(ref: string): Promise<ScenarioSeed> {
  const id = encodeURIComponent(ref);
  const a = await getJson(`/api/mi/v1/analyses/${id}`);
  const r = await getJson(`/api/mi/v1/analyses/${id}/result`).catch(() => null);
  const personas: Persona[] = r?.user?.personas ?? [];
  const journey: Journey[] = r?.user?.journey ?? [];
  const lines: string[] = [];
  const characters: string[] = [];
  const customer = clean(a.customer_name);
  if (customer) lines.push(`[고객] ${customer}`);
  for (const p of personas) {
    const role = clean(p.role);
    if (!role) continue;
    push(characters, role);
    const bits = [clean(p.context) && `상황 ${clean(p.context)}`, clean(p.goal) && `원하는 것 ${clean(p.goal)}`, clean(p.pain) && `불편한 점 ${clean(p.pain)}`].filter(Boolean);
    lines.push(`[인물] ${role}${bits.length ? ` — ${bits.join(' · ')}` : ''}`);
  }
  for (const j of journey) {
    const stage = clean(j.stage);
    if (!stage) continue;
    const bits = [clean(j.touchpoint), clean(j.pain) && `불편 ${clean(j.pain)}`, clean(j.opportunity) && `기회 ${clean(j.opportunity)}`].filter(Boolean);
    lines.push(`[여정] ${stage}${bits.length ? ` — ${bits.join(' · ')}` : ''}`);
  }
  const title = clean(a.title) || 'Market Intelligence';
  return {
    feature: 'mi', ref, label: 'Market Intelligence', title, customer_name: customer || null, project_id: a.project_id ?? null,
    lines, characters,
    note: characters.length
      ? `Market Intelligence 「${title}」의 페르소나 ${characters.length}명을 등장인물로, 사용자 여정과 함께 입력에 넣어 둘게요.`
      : `Market Intelligence 「${title}」에 페르소나가 아직 없어요 — 고객사만 이어받아요.`,
  };
}

interface Ref { name?: string; label?: string; code?: string; id?: string }
interface VpSheet {
  role?: string;
  content?: {
    challenges?: Array<{ title?: string }> | null;
    stakeholders?: Array<{ role?: string; value?: string; product_refs?: Ref[] }> | null;
    pillars?: Array<{ title?: string; body?: string; product_refs?: Ref[] }> | null;
  } | null;
}

async function fromVp(ref: string): Promise<ScenarioSeed> {
  const v = await getJson(`/api/vp/v1/vps/${encodeURIComponent(ref)}`);
  const sheets: VpSheet[] = v.sheets ?? [];
  const lines: string[] = [];
  const products: string[] = [];
  const customer = clean(v.customer_name);
  if (customer) lines.push(`[고객] ${customer}`);
  let values = 0;
  const prods = (refs?: Ref[]) => { for (const p of refs ?? []) push(products, clean(p.name ?? p.label ?? p.code)); };
  for (const sh of sheets) {
    const c = sh.content ?? {};
    for (const p of c.pillars ?? []) {
      const t = clean(p.title);
      if (!t) continue;
      lines.push(`[가치] ${t}${clean(p.body) ? ` — ${clean(p.body)}` : ''}`);
      values += 1;
      prods(p.product_refs);
    }
    for (const s of c.stakeholders ?? []) {
      const val = clean(s.value);
      if (!val) continue;
      lines.push(`[가치 · ${clean(s.role) || '고객'}] ${val}`);
      values += 1;
      prods(s.product_refs);
    }
  }
  for (const sh of sheets) for (const ch of sh.content?.challenges ?? []) { const t = clean(ch.title); if (t) lines.push(`[과제] ${t}`); }
  for (const p of products) lines.push(`[제품] ${p}`);
  const title = clean(v.title) || 'Value Proposition';
  return {
    feature: 'vp', ref, label: 'Value Proposition', title, customer_name: customer || null, project_id: v.project_id ?? null,
    lines, characters: [],
    note: values
      ? `Value Proposition 「${title}」의 가치 ${values}줄${products.length ? ` · 제품 ${products.length}개를` : '을'} 장면 재료로 입력에 넣어 둘게요.`
      : `Value Proposition 「${title}」에 아직 가치 문장이 없어요 — 고객사만 이어받아요.`,
  };
}

export async function loadSeed(src: { feature: SeedFeature; ref: string }): Promise<ScenarioSeed> {
  return src.feature === 'mi' ? fromMi(src.ref) : fromVp(src.ref);
}
