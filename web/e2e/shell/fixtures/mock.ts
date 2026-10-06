/**
 * 라우트 흉내(page.route) — kb(§7.2) · workspace(§7.3) · image(내 생성 이미지).
 * kb 세션이 끝나기 전에도 셸을 검증하려고 둔다. 실제 kb 가 떠 있으면 `kbIsUp()` 으로 실데이터 테스트를 따로 돌린다.
 */
import type { Page, Route } from '@playwright/test';
import * as D from './kb-data';

type Json = Record<string, unknown> | unknown[];
const json = (route: Route, body: Json, status = 200) => route.fulfill({ status, contentType: 'application/json; charset=utf-8', body: JSON.stringify(body) });
const notFound = (route: Route, what: string) => json(route, { error: { code: 'NOT_FOUND', message: `${what} 을(를) 찾을 수 없습니다`, details: {} } }, 404);

function svg(id: string) {
  let h = 0;
  for (const c of id) h = (h * 31 + c.charCodeAt(0)) % 360;
  return `<svg xmlns="http://www.w3.org/2000/svg" width="320" height="200" viewBox="0 0 320 200"><rect width="320" height="200" fill="hsl(${h},35%,82%)"/>`
    + `<rect x="40" y="30" width="240" height="140" rx="6" fill="hsl(${h},30%,62%)"/><text x="160" y="110" font-family="sans-serif" font-size="18" text-anchor="middle" fill="#fff">${id}</text></svg>`;
}

const lc = (s: string) => s.toLowerCase();
const matches = (q: string, ...fields: Array<string | null | undefined>) => fields.some((f) => !!f && lc(f).includes(lc(q)));

function searchProducts(q: string, limit: number, kinds: string[]) {
  const out: Array<Record<string, unknown>> = [];
  const famRow = (f: ReturnType<typeof D.allFamilies>[number]) => {
    const ms = D.MODELS.filter((m) => m.family.id === f.id);
    const sizes = ms.map((m) => m.values.size.display).join(' / ');
    const cat = D.familyCategory(f.id);
    const l2 = Object.values(D.L2).flat().find((c) => c.id === cat);
    const name = f.series_label ? `${f.name} (${f.series_label})` : f.name;
    const i = lc(name).indexOf(lc(q));
    return { kind: 'family', id: f.id, display_name: name, label: f.name, family_name: f.name, category_path: ['사이니지', l2?.name ?? ''],
      meta_line: [l2?.name, sizes, ms[0]?.values.resolution.display].filter(Boolean).join(' · '), thumb: f.thumb, highlight: i >= 0 ? [[i, i + q.length]] : [] };
  };
  if (kinds.includes('family')) {
    // 시리즈 코드(`QMC`)는 별칭 일치로 맨 앞(§7.2.5 A1)
    for (const f of D.allFamilies()) if (f.series_label && lc(f.series_label).startsWith(lc(q))) out.push(famRow(f));
    for (const f of D.allFamilies()) if (!out.some((o) => o.id === f.id) && matches(q, f.name)) out.push(famRow(f));
  }
  if (kinds.includes('model')) {
    for (const m of D.MODELS) {
      if (!matches(q, m.model_code, m.display_name, m.family.name, m.family.series_label)) continue;
      const i = lc(m.display_name).indexOf(lc(q));
      out.push({ kind: 'model', id: m.id, display_name: m.display_name, label: m.display_name, model_code: m.model_code, family_name: m.family.name,
        category_path: ['사이니지'], meta_line: `${m.family.name} · ${m.values.size.display} · ${m.values.resolution.display}`, thumb: m.thumb, highlight: i >= 0 ? [[i, i + q.length]] : [] });
    }
  }
  return out.slice(0, limit);
}

export interface KbMockOptions {
  /** 이 경로들은 500 으로 실패 */
  failPaths?: RegExp[];
  /** 응답 지연(ms) */
  delay?: number;
  /** 요청 기록 */
  calls?: string[];
}

export async function mockKb(page: Page, opts: KbMockOptions = {}) {
  await page.route('**/api/kb/v1/**', async (route) => {
    const url = new URL(route.request().url());
    const p = url.pathname.replace(/^\/api\/kb\/v1/, '');
    const sp = url.searchParams;
    opts.calls?.push(`${p}${url.search}`);
    if (opts.delay) await new Promise((r) => setTimeout(r, opts.delay));
    if (opts.failPaths?.some((re) => re.test(p))) return json(route, { error: { code: 'UPSTREAM_UNAVAILABLE', message: '실패(흉내)', details: {} } }, 503);

    if (p.startsWith('/_fixture/img/')) return route.fulfill({ status: 200, contentType: 'image/svg+xml', body: svg(p.split('/').pop()!.replace('.svg', '')) });
    if (p === '/meta') return json(route, { kb_version: 'v1-fixture', collected_at: D.COLLECTED, counts: { case_pages: 198, deployments: 218, families: 605, models: 1067, image_assets: 10251 } });
    if (p === '/categories') {
      const parent = sp.get('parent_id');
      return json(route, { items: parent ? D.L2[parent] ?? [] : D.L1, next_cursor: null });
    }
    if (p === '/families') return json(route, { items: D.FAMILIES[sp.get('category_id') ?? ''] ?? [], next_cursor: null });
    if (p === '/models') {
      const famId = sp.get('family_id');
      const catId = sp.get('category_id');
      const q = sp.get('q');
      let items = D.MODELS;
      if (famId) items = items.filter((m) => m.family.id === famId);
      else if (catId) {
        const cats = catId.startsWith('top_') ? (D.L2[catId] ?? []).map((c) => c.id) : [catId];
        items = items.filter((m) => cats.includes(D.familyCategory(m.family.id)));
      }
      if (q) items = items.filter((m) => matches(q, m.model_code, m.display_name, m.family.name, m.family.series_label));
      items = [...items].sort((a, b) => a.family.id.localeCompare(b.family.id) || a.values.size.inch - b.values.size.inch);
      return json(route, { columns: D.COLUMNS, items, next_cursor: null });
    }
    if (p === '/products/search') {
      return json(route, { items: searchProducts(sp.get('q') ?? '', Number(sp.get('limit') ?? 5), (sp.get('kinds') ?? 'model,family').split(',')) });
    }
    let m = /^\/models\/([^/]+)(\/images|\/cases)?$/.exec(p);
    if (m) {
      const code = decodeURIComponent(m[1]);
      const d = D.modelDetail(code);
      if (!d) return notFound(route, code);
      if (m[2] === '/images') return json(route, { items: d.family.id === 'fam_G000182628' ? D.PRODUCT_IMAGES : [], total: d.counts.images });
      if (m[2] === '/cases') {
        const match = sp.get('match');
        const base = D.MODEL_CASES;
        return json(route, { ...base, items: match && match !== 'usage' ? [] : base.items });
      }
      return json(route, d);
    }
    if (p === '/solutions') {
      const q = sp.get('q');
      const ind = sp.get('industry');
      let items = D.SOLUTIONS;
      if (ind) items = items.filter((s) => (s.industries as string[]).includes(ind));
      if (q) items = items.filter((s) => matches(q, s.name as string, s.desc as string));
      return json(route, { items });
    }
    m = /^\/solutions\/([^/]+)(\/images|\/cases)?$/.exec(p);
    if (m) {
      const id = decodeURIComponent(m[1]);
      const d = D.solutionDetail(id);
      if (!d) return notFound(route, id);
      if (m[2] === '/images') return json(route, id === 'magicinfo' ? D.MAGICINFO_IMAGES : { groups: [{ key: 'official', label: '공식 소개 이미지', source_label: null, items: [] }, { key: 'case', label: '도입사례 사진', source_label: 'samsung.com 고객 도입사례', items: [] }], total: 0 });
      if (m[2] === '/cases') return json(route, id === 'magicinfo' ? D.MAGICINFO_CASES : { corpus: { count: 198, checked_at: D.COLLECTED }, total: 0, title_explicit: [], body_mentions: [] });
      return json(route, d);
    }
    if (p === '/images/search') {
      const q = sp.get('q') ?? '';
      const source = sp.get('source') ?? 'all';
      const hit = q.includes('메뉴보드') || q.includes('카페') ? D.IMAGE_SEARCH : [];
      const off = hit.filter((i) => i.rights === 'official');
      const cas = hit.filter((i) => i.rights === 'customer_case');
      const items = source === 'official' ? off : source === 'case' ? cas : hit;
      return json(route, { counts: { all: off.length + cas.length, official: off.length, case: cas.length }, items: items.map(D.cardOf), next_cursor: null });
    }
    m = /^\/images\/([^/]+)$/.exec(p);
    if (m) {
      const im = D.ALL_IMAGES.find((i) => i.id === m![1]);
      return im ? json(route, im) : notFound(route, m[1]);
    }
    if (p === '/cases/search') {
      if (sp.get('region')) return json(route, { error: { code: 'UNSUPPORTED_FILTER', message: '지역 필터는 아직 지원하지 않습니다', details: { filters: ['region'] } } }, 400);
      const q = sp.get('q') ?? '';
      const period = sp.get('period') ?? 'all';
      let vertical: { id: string; name: string; from: string } | null = null;
      const vId = sp.get('vertical_id');
      if (vId) {
        const v = D.VERTICALS.find((x) => x.id === vId);
        vertical = v ? { id: v.id, name: v.name, from: 'user' } : null;
      } else if (sp.get('infer_vertical') === 'true') {
        if (q.includes('호텔')) vertical = { id: 'kr_hotel', name: '호텔', from: 'inferred' };
        else if (q.includes('프랜차이즈') || q.includes('메뉴보드') || q.includes('카페')) vertical = { id: 'kr_retail_fnb', name: '유통/요식', from: 'inferred' };
      }
      let items = q.includes('호텔') ? [D.HOTEL_CASE] : D.CASES;
      if (vertical) items = items.filter((c) => c.vertical.id === vertical!.id || (vertical!.id === 'kr_retail_fnb' && c.vertical.id.startsWith('kr_retail')));
      const years = period === '1y' ? 1 : period === '3y' ? 3 : period === '5y' ? 5 : 0;
      if (years) {
        const cut = new Date(D.TODAY);
        cut.setFullYear(cut.getFullYear() - years);
        items = items.filter((c) => c.date && new Date(c.date) >= cut);
      }
      return json(route, { corpus: { count: D.CORPUS_BY_PERIOD[period] ?? 198, checked_at: D.COLLECTED }, applied: { vertical }, items, next_cursor: null });
    }
    if (p === '/verticals') return json(route, { items: D.VERTICALS });
    return notFound(route, p);
  });
  // image 서비스 `내 생성 이미지` — 비어 있음
  await page.route('**/api/image/v1/**', (route) => json(route, { items: [], next_cursor: null }));
  // export 썸네일은 아직 없음
  await page.route('**/api/export/v1/templates/**', (route) => route.fulfill({ status: 404, body: '' }));
}

// ── workspace 고정 데이터(§6.3 보드 샘플 + §8.0 사용자) ─────
export const WS_ME = { user_id: 'u_test', name: '최민섭', given_name: '민섭', initial: '최', org: 'Samsung Research · AX그룹', role: 'member', timezone: 'Asia/Seoul' };
const ITEMS: Array<[string, string, string]> = [
  ['RQ', 'E 자산운용 용산 AI Ready 오피스', '/requirements/rq_e'], ['RQ', 'F 시행사 동탄 시니어 복합단지', '/requirements/rq_f'], ['RQ', 'G 공사 판교 스타트업 단지', '/requirements/rq_g'],
  ['SB', 'E 자산운용 용산 오피스 제안 기획', '/storyboard/sb_e'], ['SB', 'A 커피 프랜차이즈 매장 리뉴얼', '/storyboard/sb_a'], ['SB', 'B 병원 로비 안내 시스템', '/storyboard/sb_b'], ['SB', 'C 물류센터 스마트 오피스', '/storyboard/sb_c'],
  ['IMG', '카페 매장 메뉴보드 시안', '/image/img_a'], ['IMG', '로비 배경 이미지', '/image/img_b'], ['IMG', '병원 대기실 시나리오 컷', '/image/img_c'],
  ['BE', '강남 플래그십 1층 로비', '/birdseye/be_a'], ['BE', 'B 병원 외래 대기실', '/birdseye/be_b'], ['BE', 'C 물류센터 관제실', '/birdseye/be_c'],
  ['SC', 'A 커피 매장 하루 시나리오', '/scenario/sc_a'], ['SC', 'B 병원 외래 동선 시나리오', '/scenario/sc_b'],
  ['MI', 'A 커피 프랜차이즈 시장·경쟁사 분석', '/mi/mi_a'], ['MI', 'B 병원 환자 동선 분석', '/mi/mi_b'], ['MI', 'C 물류센터 경쟁사 벤치마크', '/mi/mi_c'],
  ['CA', 'A 커피 메뉴보드 경쟁사 분석', '/competitor/ca_a'], ['CA', 'B 병원 안내 사이니지 경쟁사', '/competitor/ca_b'], ['CA', 'C 물류센터 관제 디스플레이 경쟁사', '/competitor/ca_c'],
  ['VP', 'A 커피 메뉴보드 가치 제안', '/vp/vp_a'], ['VP', 'B 병원 이해관계자별 가치', '/vp/vp_b'], ['VP', 'C 물류센터 현장 효과 정리', '/vp/vp_c'],
  ['SP', 'QMC vs QBC 55" 비교', '/spec/sp_qmc_qbc'], ['SP', 'The Wall IAB 146" 스펙', '/spec/sp_iab'], ['SP', 'Flip Pro WA75D 스펙', '/spec/sp_flip'],
  ['PR', 'A 커피 프랜차이즈 메뉴보드 제안', '/proposal/pr_a'], ['PR', 'B 병원 안내 시스템 제안', '/proposal/pr_b'],
];

export interface WsNotiFixture { id: string; title: string; item_id?: string; feature?: string; route?: string; read?: boolean; minutesAgo?: number; type?: string; by_name?: string; data?: Record<string, unknown> }
export interface WsUserFixture { id: string; username: string; name: string; org?: string; role?: string; disabled?: boolean; has_password?: boolean; last_login_at?: string | null }

export interface WsMockOptions {
  /** 기준 시각(최근 작업 시점 계산) */
  now?: Date;
  /** 항목 없음 */
  empty?: boolean;
  /** 덮어쓸 항목(updated_at 순서 시험) */
  items?: Array<{ feature: string; title: string; route: string; minutesAgo: number }>;
  meFails?: boolean;
  /** `/me` 덮어쓰기(role · username · has_password …) */
  me?: Partial<typeof WS_ME> & { username?: string; has_password?: boolean };
  /** 작업물 알림(없으면 빈 목록) */
  notifications?: WsNotiFixture[];
  /** 사용자 목록(사용자 관리 화면) */
  users?: WsUserFixture[];
  /** 쓰기 요청 기록(`POST /notifications/read {…}` 등) */
  calls?: string[];
}

export async function mockWorkspace(page: Page, opts: WsMockOptions = {}) {
  const now = opts.now ?? new Date('2026-10-06T14:00:00+09:00');
  const src = opts.items ?? ITEMS.map(([feature, title, route], i) => ({ feature, title, route, minutesAgo: 30 + i * 97 }));
  const items = opts.empty ? [] : src.map((it, i) => ({
    item_id: it.route.split('/').pop() ?? `it_${i}`, feature: it.feature, title: it.title, status: 'draft', route: it.route, summary: null, project_id: null, meta: null,
    owner: 'u_test', owner_name: '최민섭', created_at: new Date(now.getTime() - (it.minutesAgo + 600) * 60000).toISOString(),
    updated_at: new Date(now.getTime() - it.minutesAgo * 60000).toISOString(),
  }));
  const notis = (opts.notifications ?? []).map((n) => ({
    id: n.id, recipient: 'u_test', type: n.type ?? 'item_updated', title: n.title, message: null, route: n.route ?? null, ref: null, service: 'spec',
    item: n.item_id ? { feature: n.feature ?? null, id: n.item_id } : null, by: 'u_x', by_name: n.by_name ?? '김영업', read: !!n.read, read_at: null, data: n.data ?? null,
    created_at: new Date(now.getTime() - (n.minutesAgo ?? 5) * 60000).toISOString(),
  }));
  const users = (opts.users ?? []).map((u) => ({ org: '', role: 'member', disabled: false, has_password: true, created_at: null, last_login_at: null, ...u }));
  await page.route('**/api/workspace/v1/**', (route) => {
    const url = new URL(route.request().url());
    const p = url.pathname.replace(/^\/api\/workspace\/v1/, '');
    const method = route.request().method();
    if (method !== 'GET') {
      let body: unknown = null;
      try { body = route.request().postDataJSON(); } catch { body = null; }
      opts.calls?.push(`${method} ${p} ${JSON.stringify(body)}`);
    }
    if (p === '/me') return opts.meFails ? json(route, { error: { code: 'UPSTREAM_UNAVAILABLE', message: 'x', details: {} } }, 503) : json(route, { ...WS_ME, ...opts.me });
    if (p === '/notifications/counts') {
      const unread = notis.filter((n) => !n.read);
      const per = new Map<string, { item_id: string; feature: string | null; unread: number }>();
      for (const n of unread) {
        if (!n.item) continue;
        const cur = per.get(n.item.id) ?? { item_id: n.item.id, feature: n.item.feature, unread: 0 };
        cur.unread += 1;
        per.set(n.item.id, cur);
      }
      return json(route, { unread: unread.length, items: [...per.values()] });
    }
    if (p === '/notifications' && method === 'GET') {
      const limit = Number(url.searchParams.get('limit') ?? 30);
      const list = [...notis].sort((a, b) => b.created_at.localeCompare(a.created_at));
      return json(route, { items: list.slice(0, limit), unread: notis.filter((n) => !n.read).length, next_cursor: null });
    }
    if (p === '/notifications/read' && method === 'POST') {
      const body = (route.request().postDataJSON() ?? {}) as { ids?: string[]; item_id?: string };
      let n = 0;
      for (const x of notis) {
        if (x.read) continue;
        if (body.ids && !body.ids.includes(x.id)) continue;
        if (body.item_id && x.item?.id !== body.item_id) continue;
        x.read = true;
        n += 1;
      }
      return json(route, { updated: n });
    }
    if (p === '/users' && method === 'GET') return json(route, { items: users });
    if (p === '/users' && method === 'POST') {
      const b = route.request().postDataJSON() as { username: string; name: string; org?: string; role?: string };
      if (users.some((u) => u.username.toLowerCase() === b.username.toLowerCase())) {
        return json(route, { error: { code: 'CONFLICT', message: '이미 있는 아이디입니다', details: {} } }, 409);
      }
      const u = { id: `u_${b.username}`, username: b.username, name: b.name, org: b.org ?? '', role: b.role ?? 'member', disabled: false, has_password: true, created_at: now.toISOString(), last_login_at: null };
      users.push(u);
      return json(route, u, 201);
    }
    const um = /^\/users\/([^/]+)$/.exec(p);
    if (um && method === 'PATCH') {
      const u = users.find((x) => x.id === um[1]);
      if (!u) return notFound(route, um[1]);
      const b = route.request().postDataJSON() as Record<string, unknown>;
      Object.assign(u, Object.fromEntries(Object.entries(b).filter(([k]) => k !== 'password')));
      return json(route, u);
    }
    if (p === '/items/counts') {
      const codes = ['RQ', 'SB', 'IMG', 'BE', 'SC', 'MI', 'CA', 'VP', 'SP', 'PR'];
      return json(route, { items: codes.map((c) => ({ feature: c, count: items.filter((i) => i.feature === c).length })) });
    }
    if (p === '/items') {
      const f = url.searchParams.get('feature');
      const limit = Number(url.searchParams.get('limit') ?? 20);
      const list = items.filter((i) => !f || i.feature === f).sort((a, b) => b.updated_at.localeCompare(a.updated_at)).slice(0, limit);
      return json(route, { items: list, next_cursor: null });
    }
    if (p === '/asset-usage') {
      const refs = (url.searchParams.get('refs') ?? '').split(',').filter(Boolean);
      return json(route, { items: refs.map((ref) => ({ ref, proposals: 0, uses: [] })) });
    }
    return notFound(route, p);
  });
}

// ── 로그인(게이트웨이 /api/_auth/*) 흉내 ───────────────────
export interface AuthMock {
  /** 지금 로그인했나 */
  signedIn: boolean;
  mode: 'local' | 'none';
  user: { id: string; name: string };
  calls: string[];
}

/** `/api/_auth/me · login · logout` 흉내 — 비밀번호는 `password`(아이디 user.id 에서 `u_` 뺀 것). 돌려준 객체로 상태를 바꾼다. */
export async function mockAuth(page: Page, init: Partial<AuthMock> = {}): Promise<AuthMock> {
  const st: AuthMock = { signedIn: false, mode: 'local', user: { id: 'u_kim', name: '김영업' }, calls: [], ...init };
  await page.route('**/api/_auth/**', async (route) => {
    const url = new URL(route.request().url());
    const method = route.request().method();
    const p = url.pathname;
    st.calls.push(`${method} ${p}`);
    if (p.endsWith('/me')) {
      if (st.mode === 'none' || st.signedIn) return json(route, { ...st.user, auth_mode: st.mode });
      return json(route, { error: { code: 'UNAUTHENTICATED', message: '로그인이 필요합니다', details: {} } }, 401);
    }
    if (p.endsWith('/login') && method === 'POST') {
      const b = route.request().postDataJSON() as { username: string; password: string };
      if (b.username === st.user.id.replace(/^u_/, '') && b.password === 'password') {
        st.signedIn = true;
        return json(route, { ...st.user, auth_mode: st.mode });
      }
      return json(route, { error: { code: 'INVALID_CREDENTIALS', message: '아이디 또는 비밀번호가 맞지 않습니다', details: {} } }, 401);
    }
    if (p.endsWith('/logout') && method === 'POST') {
      st.signedIn = false;
      return route.fulfill({ status: 204, body: '' });
    }
    return notFound(route, p);
  });
  return st;
}

/** 셸 테스트 기본 준비: kb · workspace 흉내 + 고정 시각 */
export async function setupShell(page: Page, opts: { ws?: WsMockOptions; kb?: KbMockOptions; clock?: Date | false } = {}) {
  await mockKb(page, opts.kb);
  await mockWorkspace(page, opts.ws);
  if (opts.clock !== false) await page.clock.setFixedTime(opts.clock ?? opts.ws?.now ?? new Date('2026-10-06T14:00:00+09:00'));
}

/** 실제 kb 서비스가 떠 있나 */
export async function kbIsUp(baseURL: string) {
  try {
    const r = await fetch(`${baseURL}/api/kb/v1/meta`);
    return r.status === 200;
  } catch {
    return false;
  }
}

/** 개발 화면에 남은 호출 기록 */
export async function devLog(page: Page) {
  return page.evaluate(() => (window as unknown as { __wmShellLog?: Array<Record<string, unknown>> }).__wmShellLog ?? []);
}
