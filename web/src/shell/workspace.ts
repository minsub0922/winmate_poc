/**
 * workspace 서비스 훅(게이트웨이 `/api/workspace/v1`, 00-shell §7.3) — 사용자 · 작업물 색인 · 사용 이력.
 */
import { useQuery } from '@tanstack/react-query';
import { api, unwrap } from '@/api/client';
import type { components } from '@/api/gen/workspace';
import type { FeatureCode } from './types';

export type WsMe = components['schemas']['Me'];
export type WsItem = components['schemas']['Item'];
export type WsFeatureCount = components['schemas']['FeatureCount'];

export const useMe = () =>
  useQuery({ queryKey: ['ws', 'me'], queryFn: async () => unwrap(await api.workspace.GET('/v1/me')), staleTime: 5 * 60_000, retry: 1 });

export const useItemCounts = () =>
  useQuery({ queryKey: ['ws', 'counts'], queryFn: async () => unwrap(await api.workspace.GET('/v1/items/counts')), refetchInterval: 30_000, retry: 1 });

/** 기능별 작업 항목(사이드바, 최대 5 — §6.3) */
export const useFeatureItems = (code?: FeatureCode | null, limit = 5) =>
  useQuery({
    queryKey: ['ws', 'items', code, limit],
    queryFn: async () => unwrap(await api.workspace.GET('/v1/items', { params: { query: { feature: code!, limit } } })),
    enabled: !!code, refetchInterval: 30_000, retry: 1,
  });

/** 홈 최근 작업(모든 기능, updated_at 내림차순 — §5.1.1) */
export const useRecentItems = (limit = 3) =>
  useQuery({
    queryKey: ['ws', 'recent', limit],
    queryFn: async () => unwrap(await api.workspace.GET('/v1/items', { params: { query: { limit } } })),
    refetchInterval: 60_000, retry: 0,
  });

// ── 작업물 알림(사이드바 배지 · 사용자 메뉴) ─────────────
export type WsNotification = components['schemas']['Notification'];
export type WsNotificationCounts = components['schemas']['NotificationCounts'];
export type WsUser = components['schemas']['UserOut'];

/** 읽지 않은 알림 수 — 전체 · 작업물별(서비스가 아직 옛 판이면 404 → 배지 없음) */
export const useNotificationCounts = () =>
  useQuery({
    queryKey: ['ws', 'notifications', 'counts'],
    queryFn: async () => unwrap(await api.workspace.GET('/v1/notifications/counts')),
    refetchInterval: 30_000, retry: 0, staleTime: 10_000,
  });

/** 내 알림(최근 순) */
export const useNotifications = (limit = 8, enabled = true) =>
  useQuery({
    queryKey: ['ws', 'notifications', 'list', limit],
    queryFn: async () => unwrap(await api.workspace.GET('/v1/notifications', { params: { query: { limit } } })),
    enabled, retry: 0, staleTime: 10_000,
  });

/** 읽음 표시 — ids · item_id 가 없으면 전부 */
export async function markNotificationsRead(body: { ids?: string[]; item_id?: string } = {}) {
  return unwrap(await api.workspace.POST('/v1/notifications/read', { body }));
}

/** 사용자 목록(사용자 관리 화면) */
export const useUsers = (enabled = true) =>
  useQuery({ queryKey: ['ws', 'users'], queryFn: async () => unwrap(await api.workspace.GET('/v1/users')), enabled, retry: 0 });

/** 사용 이력 `Winmate 제안서 {n}건`(§7.3, G-WS-1) */
export const useAssetUsage = (refs: string[]) =>
  useQuery({
    queryKey: ['ws', 'asset-usage', refs],
    queryFn: async () => unwrap(await api.workspace.GET('/v1/asset-usage', { params: { query: { refs: refs.join(',') } } })),
    enabled: refs.length > 0, staleTime: 60_000, retry: 0,
  });

/** 사용 이력 한 건의 글: `Winmate 제안서 {n}건` (모르면 `[확인 필요]`) */
export function usageText(usage: { items?: Array<{ ref: string; proposals: number }> } | undefined, r: string, loading?: boolean) {
  const it = usage?.items?.find((x) => x.ref === r);
  if (it) return `Winmate 제안서 ${it.proposals}건`;
  if (loading) return '…';
  return usage ? 'Winmate 제안서 0건' : '[확인 필요]';
}
