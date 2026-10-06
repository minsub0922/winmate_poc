/**
 * 검토 코멘트 · 사용자 — workspace 코멘트 API 에 바로 쓴다(§4.22 · §5.11). target = ReviewView.comment_target.
 * 앵커(제안서 시트 기준): {proposal_id, version, sheet_id, element_ref, x, y} — x · y 는 슬라이드 기준 0–1.
 */
import { useQuery } from '@tanstack/react-query';
import { api } from '@/api/client';
import { call } from './http';

const ws = api.workspace;

export interface CommentAnchor { proposal_id?: string; version?: number | null; sheet_id?: string | null; element_ref?: string | null; x?: number | null; y?: number | null }
export interface WsComment {
  id: string; target: string; body: string; anchor?: CommentAnchor | null; parent_id?: string | null;
  author: string; author_name: string; resolved: boolean; created_at: string; updated_at: string;
}

export const commentsKey = (target: string) => ['pr', 'comments', target] as const;
export const useComments = (target: string | null | undefined) =>
  useQuery({
    queryKey: commentsKey(target ?? ''),
    queryFn: async () => ((await call(ws.GET('/v1/comments', { params: { query: { target: target! } } }))).items ?? []) as unknown as WsComment[],
    enabled: !!target, retry: 0, refetchInterval: 20_000,
  });
export const createComment = (b: { target: string; body: string; anchor?: CommentAnchor | null; parent_id?: string | null }) =>
  call(ws.POST('/v1/comments', { body: { target: b.target, body: b.body, anchor: (b.anchor ?? null) as Record<string, unknown> | null, parent_id: b.parent_id ?? null } })) as unknown as Promise<WsComment>;
export const patchComment = (cid: string, b: { body?: string | null; resolved?: boolean | null }) =>
  call(ws.PATCH('/v1/comments/{comment_id}', { params: { path: { comment_id: cid } }, body: { body: b.body ?? null, resolved: b.resolved ?? null } })) as unknown as Promise<WsComment>;

export interface WsUser { id: string; username: string; name: string; org?: string; role?: string }
export const useUsers = (q: string, enabled = true) =>
  useQuery({
    queryKey: ['pr', 'users', q],
    queryFn: async () => ((await call(ws.GET('/v1/users', { params: { query: { q: q || undefined } } }))).items ?? []) as unknown as WsUser[],
    enabled, retry: 0, staleTime: 30_000,
  });
export const useMe = () =>
  useQuery({ queryKey: ['pr', 'me'], queryFn: () => call(ws.GET('/v1/me')), retry: 0, staleTime: 300_000 });
