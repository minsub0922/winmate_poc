/**
 * 전략 수립 Storyboard — 타입 · API · 잡 구독 · 문구 도우미.
 * 타입은 contracts/storyboard.json 에서 생성한 `@/api/gen/storyboard`(make contracts SERVICE=storyboard).
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api, ApiError, unwrap } from '@/api/client';
import { useJob, type JobEvent } from '@/api/jobs';
import { toast } from '@/ui';
import { useShellPage } from '@/shell/ShellContext';
import type { components } from '@/api/gen/storyboard';
import type { components as RqComponents } from '@/api/gen/requirements';

type S = components['schemas'];
export type Sb = S['Storyboard'];
export type SbListItem = S['StoryboardListItem'];
export type PlanningQuestion = S['PlanningQuestion'];
export type PlanningAnswer = S['PlanningAnswer'];
export type DirectionOption = S['DirectionOption'];
export type KeyMessage = S['KeyMessage'];
export type Flag = S['Flag'];
export type Section = S['Section'];
export type Space = S['Space'];
export type Slot = S['Slot'];
export type Segment = S['Segment'];
export type SlotQuestion = S['SlotQuestion'];
export type Group = S['Group'];
export type Discussion = S['Discussion'];
export type Revision = S['Revision'];
export type Compare = S['Compare'];
export type ChangeEntry = S['ChangeEntry'];
export type SyncPreview = S['SyncPreview'];
export type TraceItem = S['TraceItem'];
export type TraceOption = S['TraceOption'];
export type Extension = S['Extension'];
export type SchedulePhase = S['SchedulePhase'];
export type HandoffCard = S['HandoffCard'];
export type BadgeStyle = S['Badge']['style'];
export type RqListItem = RqComponents['schemas']['RequirementListItem'];

export const SECTION_NAME = '전략 수립 Storyboard';
export const STEPS = ['요구사항 불러오기', '기획 방향', '목차 · 서사', '요구 추적', '일정 · 공유'];
export const SLOT_KEYS = ['action', 'trigger', 'response', 'exception', 'metric'] as const;
export type SlotKey = (typeof SLOT_KEYS)[number];
export const SLOT_SHORT: Record<SlotKey, string> = { action: '행위', trigger: '트리거', response: '반응', exception: '예외', metric: '지표' };
export const SLOT_FULL: Record<SlotKey, string> = { action: '사용자 행위', trigger: '트리거', response: '시스템 반응', exception: '예외', metric: '성공 지표' };
export const STATUS_TEXT: Record<Section['status'], string> = {
  confirmed: '확정', reviewing: '검토 중', needs_confirmation: '확인 필요', writing: '작성 중', tbd: 'TBD',
};
export const STATUS_STYLE: Record<Section['status'], BadgeStyle> = {
  confirmed: 'fill', reviewing: 'line', needs_confirmation: 'soft', writing: 'draft', tbd: 'tbd',
};

// ── API ───────────────────────────────────────────────────

export const sbKey = (id: string | undefined) => ['storyboard', id ?? ''] as const;
const P = (sb_id: string) => ({ params: { path: { sb_id } } });

export const sbApi = {
  get: async (id: string) => unwrap(await api.storyboard.GET('/v1/storyboards/{sb_id}', P(id))),
  create: async (requirement_id: string | null) => {
    const r = await api.storyboard.POST('/v1/storyboards', { body: { requirement_id } });
    return unwrap(r);
  },
  patch: async (id: string, body: S['PatchStoryboardBody']) => unwrap(await api.storyboard.PATCH('/v1/storyboards/{sb_id}', { ...P(id), body })),
  putRequirement: async (id: string, requirement_id: string) =>
    unwrap(await api.storyboard.PUT('/v1/storyboards/{sb_id}/requirement', { ...P(id), body: { requirement_id } })),
  patchSettings: async (id: string, body: S['SettingsPatch']) =>
    unwrap(await api.storyboard.PATCH('/v1/storyboards/{sb_id}/settings', { ...P(id), body })),
  answer: async (id: string, qid: string, body: S['PutPlanningAnswer']) =>
    unwrap(await api.storyboard.PUT('/v1/storyboards/{sb_id}/planning/{qid}', { params: { path: { sb_id: id, qid } }, body })),
  startDirection: async (id: string, skip_planning = false) =>
    unwrap(await api.storyboard.POST('/v1/storyboards/{sb_id}/direction', { ...P(id), body: { skip_planning } })),
  patchDirection: async (id: string, body: S['PatchDirection']) =>
    unwrap(await api.storyboard.PATCH('/v1/storyboards/{sb_id}/direction', { ...P(id), body })),
  patchMessage: async (id: string, kmsg: string, text: string) =>
    unwrap(await api.storyboard.PATCH('/v1/storyboards/{sb_id}/key-messages/{kmsg}', { params: { path: { sb_id: id, kmsg } }, body: { text } })),
  flag: async (id: string, kmsg: string, flg: string, action: 'apply' | 'revert') => {
    const opts = { params: { path: { sb_id: id, kmsg, flg } } };
    return unwrap(action === 'apply'
      ? await api.storyboard.POST('/v1/storyboards/{sb_id}/key-messages/{kmsg}/flags/{flg}/apply', opts)
      : await api.storyboard.POST('/v1/storyboards/{sb_id}/key-messages/{kmsg}/flags/{flg}/revert', opts));
  },
  startOutline: async (id: string, body: S['PostOutlineBody'] = { retry: false }) =>
    unwrap(await api.storyboard.POST('/v1/storyboards/{sb_id}/outline', { ...P(id), body })),
  spaceQuestions: async (id: string, spc: string) =>
    unwrap(await api.storyboard.POST('/v1/storyboards/{sb_id}/spaces/{spc}/questions', { params: { path: { sb_id: id, spc } } })),
  putSlot: async (id: string, spc: string, slot: SlotKey, body: S['PutSlot']) =>
    unwrap(await api.storyboard.PUT('/v1/storyboards/{sb_id}/spaces/{spc}/slots/{slot}', { params: { path: { sb_id: id, spc, slot } }, body })),
  compose: async (id: string, spc: string) =>
    unwrap(await api.storyboard.POST('/v1/storyboards/{sb_id}/spaces/{spc}/compose', { params: { path: { sb_id: id, spc } } })),
  agenda: async (id: string) => unwrap(await api.storyboard.POST('/v1/storyboards/{sb_id}/discussions/agenda', P(id))),
  createRevision: async (id: string, body: S['PostRevision']) =>
    unwrap(await api.storyboard.POST('/v1/storyboards/{sb_id}/revisions', { ...P(id), body })),
  revision: async (id: string, rev: string) =>
    unwrap(await api.storyboard.GET('/v1/storyboards/{sb_id}/revisions/{rev}', { params: { path: { sb_id: id, rev } } })),
  applyRevision: async (id: string, rev: string) =>
    unwrap(await api.storyboard.POST('/v1/storyboards/{sb_id}/revisions/{rev}/apply', { params: { path: { sb_id: id, rev } } })),
  discardRevision: async (id: string, rev: string) =>
    unwrap(await api.storyboard.POST('/v1/storyboards/{sb_id}/revisions/{rev}/discard', { params: { path: { sb_id: id, rev } } })),
  save: async (id: string, note?: string) => unwrap(await api.storyboard.POST('/v1/storyboards/{sb_id}/save', { ...P(id), body: { note: note ?? null } })),
  compare: async (id: string, from?: number | null, to?: string | null) =>
    unwrap(await api.storyboard.GET('/v1/storyboards/{sb_id}/compare', { params: { path: { sb_id: id }, query: { from: from ?? undefined, to: to || undefined } } })),
  revert: async (id: string, chg: string) =>
    unwrap(await api.storyboard.POST('/v1/storyboards/{sb_id}/changes/{chg}/revert', { params: { path: { sb_id: id, chg } } })),
  sync: async (id: string, body: S['RequirementSyncRequest']) =>
    unwrap(await api.storyboard.POST('/v1/storyboards/{sb_id}/requirement-sync', { ...P(id), body })),
  preview: async (id: string, syp: string) =>
    unwrap(await api.storyboard.GET('/v1/storyboards/{sb_id}/sync-previews/{syp}', { params: { path: { sb_id: id, syp } } })),
  resolve: async (id: string, rq_item_id: string, body: S['PutResolution']) =>
    unwrap(await api.storyboard.PUT('/v1/storyboards/{sb_id}/trace/items/{rq_item_id}/resolution', { params: { path: { sb_id: id, rq_item_id } }, body })),
  ackExtensions: async (id: string) => unwrap(await api.storyboard.POST('/v1/storyboards/{sb_id}/trace/extensions/acknowledge', P(id))),
  exportFile: async (id: string, body: S['ExportRequest']) => unwrap(await api.storyboard.POST('/v1/storyboards/{sb_id}/exports', { ...P(id), body })),
  share: async (id: string) => unwrap(await api.storyboard.POST('/v1/storyboards/{sb_id}/share', P(id))),
  review: async (id: string) => unwrap(await api.storyboard.POST('/v1/storyboards/{sb_id}/review-requests', { ...P(id), body: {} })),
  handoffs: async (id: string) => unwrap(await api.storyboard.GET('/v1/storyboards/{sb_id}/handoffs', P(id))),
  handoff: async (id: string, target: 'proposal' | 'mi' | 'scenario') =>
    unwrap(await api.storyboard.POST('/v1/storyboards/{sb_id}/handoffs/{target}', { params: { path: { sb_id: id, target } } })),
};

/** 정의서 목록(SB1) — requirements 가 직접 준다 */
export async function savedRequirements(limit = 5): Promise<RqListItem[]> {
  const r = unwrap(await api.requirements.GET('/v1/requirements', { params: { query: { has_version: true, limit } } }));
  return r.items;
}

/** 정의서 최신 저장 버전(SB3V 미리 보기) */
export async function latestRqVersion(rqId: string): Promise<number | null> {
  const r = unwrap(await api.requirements.GET('/v1/requirements/{rq_id}', { params: { path: { rq_id: rqId } } }));
  return r.version || null;
}

// ── 훅 ────────────────────────────────────────────────────

/** 스토리보드 하나. 잡이 돌면(또는 poll) 천천히 다시 읽는다(SSE 가 놓친 것 보완). */
export function useSb(sbId: string | undefined, opts: { poll?: boolean } = {}) {
  return useQuery({
    queryKey: sbKey(sbId),
    queryFn: () => sbApi.get(sbId!),
    enabled: !!sbId,
    refetchInterval: (q) => (q.state.data?.active_job || opts.poll ? 2500 : false),
  });
}

/** 잡 SSE 구독 → 진행 · 단계 · 끝 이벤트마다 스토리보드를 다시 읽는다. 끝나면 onDone. */
export function useJobRefresh(sbId: string | undefined, jobId: string | null | undefined, onDone?: (ok: boolean, job: { error?: { code: string; message: string } | null }) => void) {
  const qc = useQueryClient();
  const timer = useRef<number | null>(null);
  const refresh = useCallback(() => {
    if (timer.current) return;
    timer.current = window.setTimeout(() => {
      timer.current = null;
      void qc.invalidateQueries({ queryKey: sbKey(sbId) });
    }, 350);
  }, [qc, sbId]);
  useEffect(() => () => { if (timer.current) window.clearTimeout(timer.current); }, []);
  const doneRef = useRef(onDone);
  doneRef.current = onDone;
  const j = useJob(jobId, {
    onEvent: (e: JobEvent) => { if (e.type === 'step' || e.type === 'partial' || e.type === 'progress') refresh(); },
    onDone: async (job) => {
      await qc.invalidateQueries({ queryKey: sbKey(sbId) });
      doneRef.current?.(job.status === 'succeeded', job);
    },
  });
  return j;
}

/** 잡 id 를 모를 때(공간 다듬기 등) 끝날 때까지 천천히 다시 읽기 */
export function usePoll(sbId: string | undefined, active: boolean, ms = 2000) {
  const qc = useQueryClient();
  useEffect(() => {
    if (!active || !sbId) return undefined;
    const t = window.setInterval(() => { void qc.invalidateQueries({ queryKey: sbKey(sbId) }); }, ms);
    return () => window.clearInterval(t);
  }, [active, sbId, ms, qc]);
}

/** 단계 이벤트(sb.outline 의 classify → map_axes → write_sections → trace) */
export interface StepState { key: string; label: string; state: 'running' | 'done'; done?: number; total?: number }
export function stepsFrom(events: JobEvent[]): Record<string, StepState> {
  const out: Record<string, StepState> = {};
  for (const e of events) {
    if (e.type !== 'step' || !e.data?.key) continue;
    out[e.data.key] = { key: e.data.key, label: e.data.label, state: e.data.state, done: e.data.done, total: e.data.total };
  }
  return out;
}

/** 버튼 동작: 바쁨 · 오류(토스트 + 다시 시도) */
export function useAction() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const run = useCallback(async <T,>(fn: () => Promise<T>, opts: { retry?: boolean; quiet?: boolean } = {}): Promise<T | undefined> => {
    setBusy(true);
    setError(null);
    try {
      return await fn();
    } catch (e) {
      const err = e instanceof ApiError ? e : new ApiError(0, 'ERROR', '요청을 처리하지 못했어요. 다시 시도해 주세요.');
      setError(err);
      if (!opts.quiet) {
        toast(errorText(err), opts.retry === false ? {} : { action: { label: '다시 시도', onClick: () => { void run(fn, opts); } } });
      }
      return undefined;
    } finally {
      setBusy(false);
    }
  }, []);
  return { run, busy, error, setError };
}

export function errorText(e: unknown): string {
  if (e instanceof ApiError) {
    if (e.status === 503 || e.code === 'LLM_UNAVAILABLE') return '지금은 AI를 쓸 수 없어요. 잠시 후 다시 시도해 주세요.';
    return e.message || '요청을 처리하지 못했어요.';
  }
  return '요청을 처리하지 못했어요.';
}

/** 잡 실패 문구(잡 레코드의 error) */
export function jobErrorText(err: { code?: string; message?: string } | null | undefined): string {
  if (!err) return '작업을 끝내지 못했어요.';
  if (err.code === 'LLM_UNAVAILABLE') return '지금은 AI를 쓸 수 없어요. 잠시 후 다시 시도해 주세요.';
  return err.message || '작업을 끝내지 못했어요.';
}

// ── 문구 · 형식 ───────────────────────────────────────────

const TZ = 'Asia/Seoul';
function parts(d: Date) {
  const f = new Intl.DateTimeFormat('en-CA', { timeZone: TZ, year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false });
  const p = Object.fromEntries(f.formatToParts(d).map((x) => [x.type, x.value]));
  return { y: Number(p.year), m: Number(p.month), d: Number(p.day), hh: p.hour === '24' ? '00' : p.hour, mm: p.minute };
}
function dayIndex(d: Date) {
  const p = parts(d);
  return Date.UTC(p.y, p.m - 1, p.d) / 86_400_000;
}

/** SB0 `수정` 칸: 방금 · 오늘 HH:mm · 어제 · M월 D일 */
export function listTime(iso: string | null | undefined, now = new Date()): string {
  if (!iso) return '';
  const t = new Date(iso);
  if (Number.isNaN(t.getTime())) return '';
  if (now.getTime() - t.getTime() < 120_000) return '방금';
  const diff = dayIndex(now) - dayIndex(t);
  const p = parts(t);
  if (diff === 0) return `오늘 ${p.hh}:${p.mm}`;
  if (diff === 1) return '어제';
  if (p.y === parts(now).y) return `${p.m}월 ${p.d}일`;
  return `${p.y}년 ${p.m}월 ${p.d}일`;
}

/** SB1 정의서 줄: `오늘 13:40 저장` */
export function savedTime(iso: string | null | undefined, now = new Date()): string {
  if (!iso) return '';
  const t = new Date(iso);
  if (Number.isNaN(t.getTime())) return '';
  const diff = dayIndex(now) - dayIndex(t);
  const p = parts(t);
  if (diff === 0) return `오늘 ${p.hh}:${p.mm} 저장`;
  if (diff === 1) return `어제 ${p.hh}:${p.mm} 저장`;
  return `${p.m}월 ${p.d}일 저장`;
}

/** SB3V 날짜: `오늘` · `11/8` */
export function shortDate(iso: string | null | undefined, now = new Date()): string {
  if (!iso) return '';
  const t = new Date(iso);
  if (Number.isNaN(t.getTime())) return '';
  if (dayIndex(now) === dayIndex(t)) return '오늘';
  const p = parts(t);
  return `${p.m}/${p.d}`;
}

/** v{n}을/를 — 1·3·6·7·8·10 → 을, 2·4·5·9 → 를 */
export function vEul(n: number): string {
  return `v${n}${[2, 4, 5, 9].includes(n % 10) ? '를' : '을'}`;
}
/** v{n}로/으로 — 3·6·10(0) → 으로, 그 밖 → 로 */
export function vRo(n: number): string {
  return `v${n}${[0, 3, 6].includes(n % 10) ? '으로' : '로'}`;
}
/** 받침 있는 낱말 뒤 을/를 · 은/는 · 으로/로 */
function hasBatchim(word: string): boolean | null {
  const ch = word.trim().slice(-1);
  if (!ch) return null;
  const code = ch.charCodeAt(0);
  if (code >= 0xac00 && code <= 0xd7a3) return (code - 0xac00) % 28 !== 0;
  if (/[0-9]/.test(ch)) return [0, 1, 3, 6, 7, 8].includes(Number(ch));
  return /[lmnr]/i.test(ch) ? true : false;
}
export function eul(word: string) { return `${word}${hasBatchim(word) ? '을' : '를'}`; }
export function iga(word: string) { return `${word}${hasBatchim(word) ? '이' : '가'}`; }
/** 로/으로 조사만(따옴표 뒤에 붙일 때) */
export function roJosa(word: string): string {
  const ch = word.trim().slice(-1);
  const code = ch.charCodeAt(0);
  const rieul = code >= 0xac00 && code <= 0xd7a3 && (code - 0xac00) % 28 === 8;
  return hasBatchim(word) && !rieul ? '으로' : '로';
}
/** v{n}이/가 */
export function vIga(n: number): string {
  return `v${n}${[2, 4, 5, 9].includes(n % 10) ? '가' : '이'}`;
}
export function eun(word: string) { return `${word}${hasBatchim(word) ? '은' : '는'}`; }
export function ro(word: string) { return `${word}${roJosa(word)}`; }

/** 첫 코드만 `RQ-` 붙이기: RQ-11 · 07 · 03 */
export function codeList(codes: string[]): string {
  return codes.map((c, i) => (i === 0 ? c : c.replace(/^RQ-/, ''))).join(' · ');
}

/** 섹션 라벨: `Part 1-2 Tech Ready 모델의 성과` · `Part 3 실행 역량` · `Overview` */
export function sectionLabel(s: Section): string {
  if (s.group_key === 'part1' && s.code) return `Part ${s.code} ${s.name}`;
  if (s.group_key === 'part2') return 'Part 2 공간 시나리오';
  if (s.group_key === 'part3') return s.code && s.code !== 'Part 3' ? `Part ${s.code} ${s.name}` : `Part 3 ${s.name}`;
  return s.name;
}

export function groupLabel(key: Group['key']): string {
  return ({ start: '시작', part1: 'Part 1', part2: 'Part 2', part3: 'Part 3', end: '마무리' } as const)[key];
}

/** 빈 공간 이름 줄: `로비 · 라운지` (최대 2, 넘으면 ` 외 {k}`) */
export function emptySpacesLabel(spaces: Space[]): string {
  const names = spaces.map((s) => s.name);
  return names.slice(0, 2).join(' · ') + (names.length > 2 ? ` 외 ${names.length - 2}` : '');
}

export function slotState(sp: Space, k: SlotKey): Slot {
  return (sp.slots?.[k] as Slot | undefined) ?? { state: 'empty', segments: [] };
}
export function firstEmptySlot(sp: Space): SlotKey | null {
  return SLOT_KEYS.find((k) => slotState(sp, k).state === 'empty') ?? null;
}
export function emptySpaces(sb: Sb): Space[] {
  return (sb.outline?.spaces ?? []).filter((s) => s.filled_count === 0);
}
/** 공간을 누르면: 첫 빈 칸 질의, 빈 칸 없으면 결과 */
export function spaceRoute(sbId: string, sp: Space): string {
  const k = firstEmptySlot(sp);
  return k ? `/storyboard/${sbId}/spaces/${sp.id}/q` : `/storyboard/${sbId}/spaces/${sp.id}/done`;
}

/** 청중(기획 질의 audience 의 고른 순서) */
export function audienceNames(sb: Sb): string[] {
  const q = sb.planning?.questions?.find((x) => x.topic === 'audience');
  if (!q) return [];
  const a = sb.planning?.answers?.find((x) => x.question_id === q.id);
  if (!a || a.unknown) return [];
  return (a.selected_option_ids ?? []).map((id) => q.options.find((o) => o.id === id)?.label).filter((x): x is string => !!x);
}

export function selectedDirection(sb: Sb): DirectionOption | undefined {
  const d = sb.direction;
  if (!d) return undefined;
  return d.options?.find((o) => o.id === (d.selected_option_id ?? d.recommended_option_id));
}

/** 잡이 그 종류로 도는 중인가 */
export function runningKind(sb: Sb | undefined, kind: string): boolean {
  return !!sb?.active_job && sb.active_job.kind === kind;
}

/** 클립보드(실패해도 조용히 false) */
export async function copyText(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    try {
      const ta = document.createElement('textarea');
      ta.value = text;
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.select();
      const ok = document.execCommand('copy');
      ta.remove();
      return ok;
    } catch {
      return false;
    }
  }
}

/**
 * 스토리보드 화면의 셸 맥락(§4.0.1): 상단바 `전략 수립 Storyboard / {제목}`, 스텝바(단계 화면만), 사이드바 그룹 storyboard.
 * step = null 이면 스텝바 없음(SB3D · SB4TD). TopBar 팝오버 추가는 받지 않는다(Q-15).
 */
export function useSbShell(sb: Sb | undefined, step: number | null, opts: { complete?: boolean; title?: string } = {}) {
  useShellPage({
    section: SECTION_NAME,
    title: opts.title ?? sb?.title ?? '새 스토리보드',
    hasTask: true,
    sidebarGroup: 'storyboard',
    stepper: step ? { steps: STEPS, current: step, complete: opts.complete } : undefined,
  });
}
