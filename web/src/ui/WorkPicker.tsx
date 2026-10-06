/**
 * 작업 고르기 대화상자 — "다른 기능의 작업 하나 고르기"(검색 · 목록 · 단일 선택 · 확인). VP0 `Storyboard에서` · `MI 결과에서` · `이전 가치 제안 복제`,
 * SB · MI · 제안서도 같은 모양(05-vp E2 · E3). 데이터: workspace `GET /api/workspace/v1/items?feature=&q=&owner=all&limit=`.
 *
 *   <WorkPickerDialog feature="SB" title="Storyboard 고르기" confirmLabel="이 자료로 시작" onClose={close}
 *     onConfirm={async (it) => { const doc = await createVp({ source: it.item_id }); nav(`/vp/${doc.id}`); }} />
 *   // 복제처럼 칸이 더 필요하면 extra · canConfirm
 *   <WorkPickerDialog feature="VP" title="복제할 가치 제안 고르기" confirmLabel="복제하기" extra={<Field label="새 고객사"><Input … /></Field>}
 *     canConfirm={() => customer.trim().length > 0} disabledReason="원본과 고객사를 정해 주세요" onConfirm={clone} onClose={close} />
 */
import { useEffect, useMemo, useRef, useState, type KeyboardEvent, type ReactNode } from 'react';
import { Button, SearchField } from './controls';
import { Empty, ErrorState, Skeleton } from './display';
import { relativeTime } from './format';
import { Icon } from './icons';
import { Modal } from './overlay';

/** workspace 작업물 색인 항목(필요한 필드만) */
export interface WorkPickItem {
  item_id: string;
  feature: string;
  title: string;
  status?: string;
  route: string;
  summary?: string | null;
  owner?: string;
  owner_name?: string;
  updated_at?: string;
  [k: string]: unknown;
}

/** workspace 작업 목록 — 기능 코드 하나 이상(여러 개면 합쳐 최근 순) */
export async function fetchWorkItems(feature: string | string[], opts: { q?: string; owner?: 'all' | 'me'; limit?: number; signal?: AbortSignal } = {}): Promise<WorkPickItem[]> {
  const codes = Array.isArray(feature) ? feature : [feature];
  const lists = await Promise.all(codes.map(async (f) => {
    const p = new URLSearchParams({ feature: f, owner: opts.owner ?? 'all', limit: String(opts.limit ?? 20) });
    if (opts.q?.trim()) p.set('q', opts.q.trim());
    const r = await fetch(`/api/workspace/v1/items?${p}`, { credentials: 'same-origin', signal: opts.signal });
    if (!r.ok) throw new Error(`items ${r.status}`);
    return ((await r.json()) as { items?: WorkPickItem[] }).items ?? [];
  }));
  return lists.flat().sort((a, b) => (b.updated_at ?? '').localeCompare(a.updated_at ?? ''));
}

export interface WorkPickerDialogProps {
  /** 열림(기본 true — 열 때만 그리면 된다) */
  open?: boolean;
  /** workspace 기능 코드(`SB` · `MI` · `VP` …) 하나 또는 여럿 */
  feature: string | string[];
  title: string;
  /** 확인 버튼 글(기본 `고르기`) */
  confirmLabel?: string;
  /** 확인 — 예외를 던지면 대화상자 아래에 메시지를 보인다(닫지 않음) */
  onConfirm: (item: WorkPickItem) => void | Promise<void>;
  onClose: () => void;
  /** 목록 범위(기본 all — 팀 작업까지) */
  owner?: 'all' | 'me';
  /** 목록 아래 칸(복제의 고객사 입력 등) — 함수면 고른 항목을 받는다 */
  extra?: ReactNode | ((item: WorkPickItem | null) => ReactNode);
  /** 확인 가능 조건(고른 항목이 있고 이것도 참이어야) */
  canConfirm?: (item: WorkPickItem) => boolean;
  /** 확인 버튼이 꺼진 이유(기본 `작업을 골라 주세요`) */
  disabledReason?: string;
  placeholder?: string;
  /** 고를 작업이 없을 때 */
  emptyText?: ReactNode;
  /** 목록에서 뺄 항목 id(지금 작업 등) */
  exclude?: string[];
  /** 행 보조 줄 바꾸기(기본: 요약 · 담당 · 시점) */
  rowSub?: (item: WorkPickItem) => ReactNode;
  width?: number;
  limit?: number;
}

export function WorkPickerDialog({ open = true, feature, title, confirmLabel = '고르기', onConfirm, onClose, owner = 'all', extra, canConfirm, disabledReason,
  placeholder = '작업 이름 · 고객사', emptyText, exclude, rowSub, width = 560, limit = 20 }: WorkPickerDialogProps) {
  const [q, setQ] = useState('');
  const [dq, setDq] = useState('');
  const [items, setItems] = useState<WorkPickItem[] | null>(null);
  const [failed, setFailed] = useState(false);
  const [sel, setSel] = useState<WorkPickItem | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [reload, setReload] = useState(0);
  const listRef = useRef<HTMLDivElement>(null);
  const featureKey = Array.isArray(feature) ? feature.join(',') : feature;
  const now = useMemo(() => new Date(), []);

  useEffect(() => { const t = window.setTimeout(() => setDq(q), 200); return () => window.clearTimeout(t); }, [q]);
  useEffect(() => {
    if (!open) return;
    const ac = new AbortController();
    setFailed(false);
    fetchWorkItems(featureKey.split(','), { q: dq, owner, limit, signal: ac.signal })
      .then((list) => { if (!ac.signal.aborted) setItems(list.filter((i) => !exclude?.includes(i.item_id))); })
      .catch(() => { if (!ac.signal.aborted) { setItems([]); setFailed(true); } });
    return () => ac.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, featureKey, dq, owner, limit, reload]);

  const list = items ?? [];
  const ok = !!sel && (!canConfirm || canConfirm(sel));
  const confirm = async (item: WorkPickItem | null = sel) => {
    if (!item || (canConfirm && !canConfirm(item)) || busy) return;
    setBusy(true);
    setErr(null);
    try {
      await onConfirm(item);
    } catch (e) {
      setErr(e instanceof Error ? e.message : '진행하지 못했어요');
    } finally {
      setBusy(false);
    }
  };
  const move = (e: KeyboardEvent) => {
    if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp') return;
    e.preventDefault();
    if (!list.length) return;
    const i = sel ? list.findIndex((x) => x.item_id === sel.item_id) : -1;
    const next = list[Math.max(0, Math.min(list.length - 1, i + (e.key === 'ArrowDown' ? 1 : -1)))];
    setSel(next);
    listRef.current?.querySelector(`[data-item="${CSS.escape(next.item_id)}"]`)?.scrollIntoView({ block: 'nearest' });
  };
  const sub = (it: WorkPickItem) => rowSub?.(it)
    ?? [it.summary, it.owner_name, it.updated_at ? relativeTime(it.updated_at, now) : null].filter(Boolean).join(' · ');

  return (
    <Modal open={open} onClose={onClose} title={title} width={width} ariaLabel={title}
      footer={<div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', alignItems: 'center', width: '100%' }}>
        {err && <span role="alert" style={{ marginRight: 'auto', fontSize: 12.5, color: 'var(--wm-danger)' }}>{err}</span>}
        <Button h={38} onClick={onClose}>취소</Button>
        <Button h={38} variant="primary" onClick={() => void confirm()} disabled={!ok} loading={busy}
          disabledReason={disabledReason ?? (sel ? '필요한 칸을 채워 주세요' : '작업을 골라 주세요')}>{confirmLabel}</Button>
      </div>}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }} data-testid="work-picker">
        <SearchField value={q} onChange={setQ} label="작업 검색" placeholder={placeholder} autoFocus clearable
          onKeyDown={move} onEnter={() => { if (ok) void confirm(); }} />
        <div className="wm-picklist" role="listbox" aria-label="작업" ref={listRef}>
          {items === null && [0, 1, 2].map((i) => <Skeleton key={i} h={52} r={10} />)}
          {failed && <ErrorState message="작업을 불러오지 못했어요" onRetry={() => setReload((n) => n + 1)} />}
          {items !== null && !failed && list.length === 0 && (
            <Empty size="sm" title={dq ? '찾는 작업이 없어요' : '고를 수 있는 작업이 없어요'}>{emptyText ?? (dq ? '다른 낱말로 찾아 보세요.' : '먼저 그 기능에서 작업을 만들어 주세요.')}</Empty>
          )}
          {list.map((it) => {
            const on = sel?.item_id === it.item_id;
            return (
              <button key={it.item_id} type="button" role="option" aria-selected={on} className="wm-pickrow" data-item={it.item_id}
                onClick={() => setSel(it)} onDoubleClick={() => { setSel(it); void confirm(it); }}>
                <span style={{ display: 'flex', flexDirection: 'column', gap: 2, minWidth: 0, flex: 1 }}>
                  <span className="wm-pickrow__title">{it.title}</span>
                  <span className="wm-pickrow__sub">{sub(it)}</span>
                </span>
                {on && <Icon name="check" size={16} color="var(--wm-brand)" strokeWidth={2.4} />}
              </button>
            );
          })}
        </div>
        {typeof extra === 'function' ? extra(sel) : extra}
      </div>
    </Modal>
  );
}
