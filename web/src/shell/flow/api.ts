/**
 * 새 콘텐츠 흐름(docs/scenarios/11-content-flow.md)의 Storyboard 허브 — contracts/storyboard.json `/v1/flows*` → @/api/gen/storyboard.
 * 콘텐츠 화면은 이 훅과 셸 흐름 화면(ContentListScreen · GateScreen · FlowBar · FlowDoneView)만 쓴다.
 */
import { useQueries, useQuery, useQueryClient } from '@tanstack/react-query';
import { api, unwrap } from '@/api/client';
import type { components } from '@/api/gen/storyboard';

type S = components['schemas'];
export type FlowDoc = S['FlowDoc'];
export type FlowCell = S['FlowCell'];
export type FlowListItem = S['FlowListItem'];
export type FlowContentItem = S['FlowContentItem'];
export type FlowCard = S['FlowCard'];
export type FlowStageOut = S['FlowStageOut'];
export type ContentKey = 'rq' | 'dss' | 'mi' | 'ca' | 'vp' | 'sp' | 'sc';
export type StageKey = ContentKey | 'ppt';

/** 콘텐츠마다 이름 · 문구 · 경로(보드 List · Gate META 그대로) */
export interface ContentMeta {
  key: ContentKey;
  label: string;
  short: string;
  desc: string;
  pre: string;
  post: string;
  newLabel: string;
  /** 기능 URL 첫 조각 */
  base: string;
  /** Gate 스텝바(1 = Storyboard) */
  steps: string[];
  /** 사전 작업 키 · 설명 · 짧은 이름 · 하러 가기 경로 */
  preKey: 'rq' | 'dss' | null;
  preDesc: string;
  preShort: string;
  preHref: string;
  icon: string;
}

export const CONTENT: Record<ContentKey, ContentMeta> = {
  rq: { key: 'rq', label: '고객 요구사항', short: '요구사항', desc: '가장 첫 단위예요. 저장하면 Storyboard가 자동으로 만들어져요.', pre: '없음', post: 'DSS',
    newLabel: '새 요구사항', base: 'requirements', steps: ['요구사항 입력', '저장'], preKey: null, preDesc: '', preShort: '', preHref: '', icon: 'M9 4h6v3H9z M7 5.5H5V21h14V5.5h-2 M8.5 12h7 M8.5 16h5' },
  dss: { key: 'dss', label: '공간별 제품 매칭 DSS', short: 'DSS', desc: 'Storyboard에 공간별 제품 · 솔루션을 골라 넣어요.', pre: 'Storyboard (고객 요구사항)', post: '공간 시나리오 · Spec 시트',
    newLabel: '새 DSS', base: 'dss', steps: ['Storyboard', '공간 · 제품', '솔루션'], preKey: 'rq', preDesc: '고객 요구사항이 연결된 Storyboard', preShort: '요구사항', preHref: '/requirements/new',
    icon: 'M3 21h18 M5 21V9l7-5 7 5v12 M9 21v-6h6v6' },
  mi: { key: 'mi', label: 'Market Intelligence', short: 'MI', desc: 'Storyboard를 바탕으로 웹에서 시장 · 고객사 · 사용자 정보를 모아 정리해요.', pre: '최소 DSS까지 된 Storyboard', post: '없음',
    newLabel: '새 MI', base: 'mi', steps: ['Storyboard', '검색', '정제'], preKey: 'dss', preDesc: '최소 DSS까지 완료된 Storyboard', preShort: 'DSS', preHref: '/dss/new', icon: 'M4 20V10 M10 20V4 M16 20v-8 M22 20H2' },
  ca: { key: 'ca', label: '경쟁사 분석', short: '경쟁사 분석', desc: 'Storyboard의 제품 · 공간을 기준으로 B2B 경쟁사를 리스트업해요.', pre: '최소 DSS까지 된 Storyboard', post: '없음',
    newLabel: '새 경쟁사 분석', base: 'competitor', steps: ['Storyboard', '경쟁사 리스트업'], preKey: 'dss', preDesc: '최소 DSS까지 완료된 Storyboard', preShort: 'DSS', preHref: '/dss/new',
    icon: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18z M12 17a5 5 0 1 0 0-10 5 5 0 0 0 0 10z M12 13a1 1 0 1 0 0-2 1 1 0 0 0 0 2z' },
  vp: { key: 'vp', label: 'Value Proposition', short: 'VP', desc: '제품 · 솔루션마다 고객에게 줄 가치를 뽑아요.', pre: '최소 DSS까지 된 Storyboard', post: '없음',
    newLabel: '새 VP', base: 'vp', steps: ['Storyboard', '가치 · 고객의 니즈'], preKey: 'dss', preDesc: '최소 DSS까지 완료된 Storyboard', preShort: 'DSS', preHref: '/dss/new',
    icon: 'M6 3h12l3 6-9 12L3 9z M3 9h18 M12 21L8 9l4-6 4 6z' },
  sp: { key: 'sp', label: 'Spec 시트 생성', short: 'Spec 시트', desc: 'DSS에서 고른 제품의 스펙 시트를 만들어요.', pre: '최소 DSS까지 된 Storyboard', post: '없음',
    newLabel: '새 Spec 시트', base: 'spec', steps: ['Storyboard', '시트 작성'], preKey: 'dss', preDesc: '최소 DSS까지 완료된 Storyboard', preShort: 'DSS', preHref: '/dss/new',
    icon: 'M6 3h9l4 4v14H6z M14 3v5h5 M9 13h7 M9 17h5' },
  sc: { key: 'sc', label: '공간 시나리오 생성', short: '공간 시나리오', desc: 'Storyboard의 공간마다 사용자 시나리오를 만들어요.', pre: '최소 DSS까지 된 Storyboard', post: '없음',
    newLabel: '새 공간 시나리오', base: 'scenario', steps: ['Storyboard', '공간별 시나리오'], preKey: 'dss', preDesc: '최소 DSS까지 완료된 Storyboard', preShort: 'DSS', preHref: '/dss/new',
    icon: 'M3 5h18v14H3z M10 9l5 3-5 3z' },
};

export const STAGE_LABEL: Record<StageKey, string> = { rq: '요구사항', dss: 'DSS', mi: 'MI', ca: '경쟁사', vp: 'VP', sp: 'Spec', sc: '시나리오', ppt: '제안서' };

export const flowKey = (id: string) => ['storyboard', 'flow', id] as const;

export function useFlow(id: string | null | undefined) {
  return useQuery({ queryKey: flowKey(id || ''), enabled: !!id, queryFn: async () => unwrap(await api.storyboard.GET('/v1/flows/{flow_id}', { params: { path: { flow_id: id! } } })) });
}

/** 여러 Storyboard(콘텐츠 하나가 여러 SB 에 연결) */
export function useFlowsById(ids: string[]) {
  return useQueries({ queries: ids.map((id) => ({
    queryKey: flowKey(id),
    queryFn: async () => unwrap(await api.storyboard.GET('/v1/flows/{flow_id}', { params: { path: { flow_id: id } } })),
  })) });
}

export function useFlows(content?: ContentKey) {
  return useQuery({ queryKey: ['storyboard', 'flows', content ?? 'all'],
    queryFn: async () => unwrap(await api.storyboard.GET('/v1/flows', { params: { query: { limit: 100, content: content ?? null } } })) });
}

export function useFlowContents(key: ContentKey) {
  return useQuery({ queryKey: ['storyboard', 'flow-contents', key],
    queryFn: async () => unwrap(await api.storyboard.GET('/v1/flows/contents/{key}', { params: { path: { key } } })) });
}

export async function branchFlow(id: string, stage: StageKey) {
  return unwrap(await api.storyboard.POST('/v1/flows/{flow_id}:branch', { params: { path: { flow_id: id } }, body: { stage } }));
}

export async function patchFlow(id: string, body: S['FlowPatch']) {
  return unwrap(await api.storyboard.PATCH('/v1/flows/{flow_id}', { params: { path: { flow_id: id } }, body }));
}

export async function suggestKeyMessage(id: string) {
  return unwrap(await api.storyboard.POST('/v1/flows/{flow_id}/key-message:suggest', { params: { path: { flow_id: id } } }));
}

/** 저장 · 분기 뒤 허브 캐시를 새로 */
export function useFlowInvalidate() {
  const qc = useQueryClient();
  return () => qc.invalidateQueries({ queryKey: ['storyboard'] });
}

/** 진행 칸 8 의 보드 스타일 키(rq dss | mi ca vp sp sc | ppt) */
export const ORDER: StageKey[] = ['rq', 'dss', 'mi', 'ca', 'vp', 'sp', 'sc', 'ppt'];
export const doneKeys = (cells: FlowCell[]) => cells.filter((c) => c.state === 'done').map((c) => c.key);
