/**
 * 화면 경로. 셸 기능 키가 `proposal` 이라 모든 경로는 `/proposal/...` 이다(10-proposal §2 표의 `/proposals/...` 와 같은 구조).
 */
import type { Proposal, Stage } from '../api/types';
import { TYPES, type ProposalType, type SectionKey } from './catalog';

export const BASE = '/proposal';
const q = (o: Record<string, string | number | null | undefined | boolean>) => {
  const s = new URLSearchParams();
  for (const [k, v] of Object.entries(o)) if (v !== undefined && v !== null && v !== '' && v !== false) s.set(k, String(v));
  const t = s.toString();
  return t ? `?${t}` : '';
};

export const R = {
  list: () => BASE,
  create: (o: Record<string, string | undefined> = {}) => `${BASE}/new${q(o)}`,
  open: (id: string) => `${BASE}/${id}`,
  customer: (id: string) => `${BASE}/${id}/customer`,
  rfp: (id: string) => `${BASE}/${id}/rfp`,
  works: (id: string, check?: string) => `${BASE}/${id}/works${q({ check })}`,
  reuse: (id: string) => `${BASE}/${id}/reuse`,
  type: (id: string) => `${BASE}/${id}/type`,
  compose: (id: string, open?: string | null) => `${BASE}/${id}/compose${q({ open })}`,
  industry: (id: string, extra: Record<string, string> = {}) => `${BASE}/${id}/industry${q(extra)}`,
  section: (id: string, key: string, extra: Record<string, string | null | undefined> = {}) => `${BASE}/${id}/sections/${key}${q(extra)}`,
  template: (id: string, key: string, sheetId: string) => `${BASE}/${id}/sections/${key}/sheets/${sheetId}/template`,
  extract: (id: string, key: string, imp: string) => `${BASE}/${id}/sections/${key}/imports/${imp}`,
  design: (id: string) => `${BASE}/${id}/design`,
  result: (id: string, extra: Record<string, string | number | null | undefined> = {}) => `${BASE}/${id}/result${q(extra)}`,
  preview: (id: string, sheetNo?: number | string | null, extra: Record<string, string | null | undefined> = {}) =>
    `${BASE}/${id}/preview${sheetNo ? `/${sheetNo}` : ''}${q(extra)}`,
  confirm: (id: string) => `${BASE}/${id}/confirm`,
  review: (id: string, sheetNo?: number | string | null) => `${BASE}/${id}/review${sheetNo ? `/${sheetNo}` : ''}`,
  versions: (id: string, extra: Record<string, string | number | null | undefined> = {}) => `${BASE}/${id}/versions${q(extra)}`,
  oneClick: (id: string, jobId: string) => `${BASE}/${id}/one-click/${jobId}`,
  reuseAnalysis: (id: string) => `${BASE}/${id}/reuse/analysis`,
  reuseCriterion: (id: string, no: number | string) => `${BASE}/${id}/reuse/analysis/${no}`,
  reusePlan: (id: string, mode?: 'improve' | 'borrow' | null) => `${BASE}/${id}/reuse/plan${q({ mode })}`,
  reuseSummary: (id: string) => `${BASE}/${id}/reuse/summary`,
};

/** 서버가 준 경로(`/proposals/...` 로 올 수도 있다)를 이 모듈 경로로 */
export function normalizeRoute(route: string | null | undefined): string | null {
  if (!route) return null;
  if (route.startsWith('/proposals/') || route === '/proposals') return route.replace(/^\/proposals/, BASE);
  return route;
}

export const STAGE_STEP: Record<Stage, number> = { customer: 1, type: 2, compose: 3, industry: 3, sections: 4, design: 5, result: 6 };

export function sectionsOf(type: ProposalType | null | undefined): SectionKey[] {
  return TYPES[type ?? 'standard'].secs;
}

/** 제안서가 지금 있는 화면(「이어서 작성」 · 사이드바 항목) */
export function currentRoute(p: Proposal): string {
  if (p.one_click?.status === 'running' && p.one_click.job_id) return R.oneClick(p.id, p.one_click.job_id);
  const server = normalizeRoute(p.route);
  if (server && server !== R.open(p.id)) return server;
  const stage = (p.stage ?? 'customer') as Stage;
  switch (stage) {
    case 'customer':
      if (p.start_mode === 'rfp') return R.rfp(p.id);
      if (p.start_mode === 'works') return R.works(p.id);
      if (p.start_mode === 'reuse') return p.reuse?.reuse_id ? R.reuseAnalysis(p.id) : R.reuse(p.id);
      return R.customer(p.id);
    case 'type': return R.type(p.id);
    case 'compose': return R.compose(p.id);
    case 'industry': return R.industry(p.id);
    case 'sections': {
      const keys = (p.sections ?? []).filter((s) => !s.hidden && s.enabled !== false).map((s) => s.key);
      const key = p.current_section_key ?? keys[0] ?? sectionsOf(p.type as ProposalType | null)[0];
      return R.section(p.id, key, p.reuse ? { view: p.reuse.mode === 'borrow' ? 'guide' : 'compare' } : {});
    }
    case 'design': return R.design(p.id);
    case 'result': return p.reuse && (p.version ?? 0) >= 1 ? R.reuseSummary(p.id) : R.result(p.id);
    default: return R.customer(p.id);
  }
}

const STAGE_ORDER: Stage[] = ['customer', 'type', 'compose', 'industry', 'sections', 'design', 'result'];
/** stage 는 앞으로만 움직인다(§3.1) — 지금보다 뒤 단계일 때만 true */
export function isAhead(target: Stage, current: string | null | undefined): boolean {
  return STAGE_ORDER.indexOf(target) > STAGE_ORDER.indexOf((current ?? 'customer') as Stage);
}

/**
 * 다른 기능에서 넘어온 `?handoff=&link=&feature=` 의 기능 키(통합 규칙).
 * 넘김 id 접두사는 기능마다 겹칠 수 있다(mi · competitor 둘 다 `hof_`) — 그래서 `feature` → 작업 id(`link` · `ref`) 접두사 → 넘김 id 접두사 순으로 정한다.
 */
const ID_FEATURE: Record<string, string> = {
  rq: 'requirements', sb: 'storyboard', mi: 'mi', ca: 'competitor', vp: 'vp', sp: 'spec', img: 'image', imv: 'image', be: 'birdseye', sc: 'scenario',
};
export function featureOfRef(ref: string | null | undefined): string | null {
  const pre = ref && ref.includes('_') ? ref.split('_')[0].toLowerCase() : '';
  return ID_FEATURE[pre] ?? null;
}
export function handoffFeature(sp: URLSearchParams, fallback?: string | null): string {
  const explicit = sp.get('feature');
  if (explicit) return explicit;
  const byRef = featureOfRef(sp.get('link') ?? sp.get('ref'));
  if (byRef) return byRef;
  const h = sp.get('handoff') ?? '';
  if (h.startsWith('sho_')) return 'spec';
  if (h.startsWith('vho_')) return 'vp';
  return fallback ?? (h.startsWith('hof_') ? 'mi' : '');
}
