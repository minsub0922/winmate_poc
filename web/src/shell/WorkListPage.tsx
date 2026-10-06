/**
 * 기능의 `작업 목록` 화면 기본형(보드 RQ0 · CA0 · MI0 · SP0) — workspace 항목을 표로 보인다.
 *   function ListPage() { return <WorkListPage feature="RQ" title="고객 요구사항" newLabel="새 요구사항" />; }
 * 셸 맥락(브레드크럼 `… / 작업 목록`, hasTask=false)도 이 컴포넌트가 설정한다. 상태 글 · 열 · 행 동작은 props 로 바꾼다.
 */
import { useMemo, useState, type ReactNode } from 'react';
import { useQuery } from '@tanstack/react-query';
import { DataTable, FilterTabs, ListPage, ListToolbar, NewButton, RowAction, StatusBadge, TitleCell, relativeTime, type DataColumn, type StatusTone } from '@/ui';
import { api, unwrap } from '@/api/client';
import { shellFeatureByCode } from './catalog';
import { useShellPage } from './ShellContext';
import type { FeatureCode } from './types';
import type { WsItem } from './workspace';

export interface WorkStatus { label: string; tone: StatusTone; icon?: 'check' | 'spin' | 'refresh' | 'warn'; /** 진행 중이면 행 버튼 `이어서`(primary) */ running?: boolean }

const DEFAULT_STATUS: Record<string, WorkStatus> = {
  draft: { label: '작성 중', tone: 'brand', running: true },
  generating: { label: '만드는 중', tone: 'brand', icon: 'spin', running: true },
  running: { label: '진행 중', tone: 'brand', icon: 'spin', running: true },
  awaiting_input: { label: '확인 필요', tone: 'warn', running: true },
  review: { label: '검토 중', tone: 'brand' },
  done: { label: '완료', tone: 'neutral', icon: 'check' },
  saved: { label: '저장됨', tone: 'neutral' },
  failed: { label: '실패', tone: 'danger', icon: 'warn' },
  stale: { label: '업데이트 필요', tone: 'warn', icon: 'refresh' },
};

export interface WorkListPageProps {
  feature: FeatureCode;
  /** 화면 제목(기본: 기능 이름) */
  title?: ReactNode;
  desc?: ReactNode;
  /** `+ {newLabel}` 버튼(기본 `새로 만들기`), 경로 기본 `/<key>/new` */
  newLabel?: string;
  newTo?: string;
  /** 브레드크럼 마지막 조각(기본 `작업 목록`) */
  crumb?: string;
  /** 상태 값 → 알약 글 · 색 */
  statusMap?: Record<string, WorkStatus>;
  /** 추가 열(제목 · 상태 · 수정 · 열기 사이에 넣는다) */
  extraColumns?: Array<DataColumn<WsItem>>;
  /** 표 아래 영역(다른 곳에서 시작 등) */
  footer?: ReactNode;
  banner?: ReactNode;
  emptyText?: ReactNode;
}

export function WorkListPage({ feature, title, desc, newLabel = '새로 만들기', newTo, crumb = '작업 목록', statusMap, extraColumns = [], footer, banner, emptyText }: WorkListPageProps) {
  const f = shellFeatureByCode(feature);
  useShellPage({ section: f?.name, title: crumb, hasTask: false });
  const [q, setQ] = useState('');
  const [filter, setFilter] = useState<'all' | 'running' | 'done'>('all');
  const items = useQuery({
    queryKey: ['ws', 'items', feature, 'list'],
    queryFn: async () => unwrap(await api.workspace.GET('/v1/items', { params: { query: { feature, limit: 100 } } })),
    refetchInterval: 30_000,
  });
  const map = { ...DEFAULT_STATUS, ...statusMap };
  const st = (s: string): WorkStatus => map[s] ?? { label: s, tone: 'neutral' };
  const all = items.data?.items ?? [];
  const rows = useMemo(() => all.filter((it) => (!q || it.title.toLowerCase().includes(q.toLowerCase()))
    && (filter === 'all' || (filter === 'running' ? !!st(it.status).running : !st(it.status).running))), [all, q, filter]); // eslint-disable-line react-hooks/exhaustive-deps
  const now = new Date();
  const columns: Array<DataColumn<WsItem>> = [
    { key: 'title', label: '작업', width: 'minmax(0, 1fr)', render: (it) => <TitleCell title={it.title} sub={it.summary ?? undefined} to={it.route} /> },
    ...extraColumns,
    { key: 'status', label: '상태', width: '190px', render: (it) => { const s = st(it.status); return <StatusBadge size="lg" tone={s.tone} icon={s.icon}>{s.label}</StatusBadge>; } },
    { key: 'when', label: '수정', width: '110px', render: (it) => <span style={{ fontSize: 13, color: 'var(--wm-text-muted)', whiteSpace: 'nowrap' }}>{relativeTime(it.updated_at, now)}</span> },
    { key: 'open', label: '', width: '110px', align: 'end', render: (it) => <RowAction to={it.route} primary={!!st(it.status).running}>{st(it.status).running ? '이어서' : '열기'}</RowAction> },
  ];
  const running = all.filter((it) => st(it.status).running).length;
  return (
    <ListPage
      title={title ?? f?.name ?? feature}
      desc={desc}
      action={<NewButton to={newTo ?? `/${f?.key ?? ''}/new`}>{newLabel}</NewButton>}
      toolbar={<ListToolbar
        left={<FilterTabs value={filter} onChange={setFilter} items={[{ value: 'all', label: '전체', count: all.length }, { value: 'running', label: '진행 중', count: running }, { value: 'done', label: '완료', count: all.length - running }]} />}
        search={{ value: q, onChange: setQ, placeholder: '찾기', label: '작업 검색' }} />}
      banner={banner}
      table={<DataTable rowKey={(it) => it.item_id} rows={rows} columns={columns} loading={items.isLoading} rowHeight={72}
        empty={items.isError ? '작업 목록을 불러오지 못했어요.' : q ? `‘${q}’에 맞는 작업이 없어요.` : emptyText ?? '아직 작업이 없어요. 새로 만들어 보세요.'} />}
      footer={footer}
    />
  );
}
